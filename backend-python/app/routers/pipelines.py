from fastapi import APIRouter, HTTPException, Depends, Query, Request
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from app.core.database import db
from app.middleware.auth import get_current_user, require_admin, is_admin_user, audit_log

router = APIRouter(prefix="/api", tags=["Pipelines & Deals"])

DEFAULT_STAGES = [
    {"name": "New Lead",      "probability": 10,  "stage_type": "open", "color": "#3B82F6"},
    {"name": "Qualified",     "probability": 30,  "stage_type": "open", "color": "#EAB308"},
    {"name": "Proposal Sent", "probability": 50,  "stage_type": "open", "color": "#F97316"},
    {"name": "Negotiation",   "probability": 70,  "stage_type": "open", "color": "#A855F7"},
    {"name": "Won",           "probability": 100, "stage_type": "won",  "color": "#16A34A"},
    {"name": "Lost",          "probability": 0,   "stage_type": "lost", "color": "#DC2626"},
]

def stage_shape(r: dict) -> dict:
    return {
        "id": r["id"],
        "pipelineId": r["pipeline_id"],
        "name": r["name"],
        "probability": r["probability"],
        "position": r["position"],
        "stageType": r["stage_type"],
        "color": r["color"],
    }

def pipeline_shape(r: dict, stages: List[dict] = None) -> dict:
    stages = stages or []
    return {
        "id": r["id"],
        "name": r["name"],
        "isDefault": r["is_default"],
        "position": r["position"],
        "stages": [stage_shape(dict(s)) for s in stages],
    }

def deal_shape(r: dict) -> dict:
    return {
        "id": r["id"],
        "pipelineId": r["pipeline_id"],
        "stageId": r["stage_id"],
        "title": r["title"],
        "value": float(r["value"]) if r.get("value") is not None else 0.0,
        "currency": r.get("currency"),
        "status": r.get("status"),
        "assignedUserId": r.get("assigned_user_id"),
        "assignedUserName": r.get("assigned_user_name"),
        "contactWaNumber": r.get("contact_wa_number"),
        "contactNumber": r.get("contact_number"),
        "contactName": r.get("contact_name"),
        "expectedCloseDate": r["expected_close_date"].isoformat() if r.get("expected_close_date") else None,
        "notes": r.get("notes"),
        "position": r.get("position"),
        "wonAt": r["won_at"].isoformat() if r.get("won_at") else None,
        "lostAt": r["lost_at"].isoformat() if r.get("lost_at") else None,
        "createdAt": r["created_at"].isoformat() if r.get("created_at") else None,
        "updatedAt": r["updated_at"].isoformat() if r.get("updated_at") else None,
    }

def status_for_stage_type(stage_type: str) -> str:
    if stage_type == "won":
        return "won"
    if stage_type == "lost":
        return "lost"
    return "open"

async def sync_contact_assignment(wa_number: Optional[str], contact_number: Optional[str], assignee_id: Optional[int]):
    if not wa_number or not contact_number or not assignee_id:
        return
    await db.execute(
        """
        UPDATE coexistence.contacts
        SET assigned_user_id = $1, updated_at = NOW()
        WHERE wa_number = $2 AND contact_number = $3
        """,
        assignee_id, wa_number, contact_number
    )

async def get_stage_in_pipeline(stage_id: int, pipeline_id: int):
    return await db.fetchrow(
        "SELECT * FROM coexistence.pipeline_stages WHERE id = $1 AND pipeline_id = $2",
        stage_id, pipeline_id
    )

# --- Schemas ---

class PipelineCreate(BaseModel):
    name: str

class PipelineUpdate(BaseModel):
    name: str

class StageCreate(BaseModel):
    name: str
    probability: Optional[int] = 0
    color: Optional[str] = None
    stageType: Optional[str] = "open"

class StageUpdate(BaseModel):
    name: Optional[str] = None
    probability: Optional[int] = None
    color: Optional[str] = None
    stageType: Optional[str] = None
    position: Optional[int] = None

class DealCreate(BaseModel):
    pipelineId: int
    stageId: Optional[int] = None
    title: str
    value: Optional[float] = 0.0
    currency: Optional[str] = "INR"
    assignedUserId: Optional[int] = None
    contactWaNumber: Optional[str] = None
    contactNumber: Optional[str] = None
    contactName: Optional[str] = None
    expectedCloseDate: Optional[str] = None
    notes: Optional[str] = None

class DealUpdate(BaseModel):
    stageId: Optional[int] = None
    title: Optional[str] = None
    value: Optional[float] = None
    currency: Optional[str] = None
    assignedUserId: Optional[int] = None
    contactWaNumber: Optional[str] = None
    contactNumber: Optional[str] = None
    contactName: Optional[str] = None
    expectedCloseDate: Optional[str] = None
    notes: Optional[str] = None

class DealMove(BaseModel):
    stageId: int

# --- Pipelines Routes ---

@router.get("/pipelines")
async def list_pipelines(user: dict = Depends(get_current_user)):
    pipes = await db.fetch("SELECT * FROM coexistence.pipelines ORDER BY is_default DESC, position ASC, id ASC")
    stages = await db.fetch("SELECT * FROM coexistence.pipeline_stages ORDER BY position ASC, id ASC")
    by_pipe = {}
    for s in stages:
        by_pipe.setdefault(s["pipeline_id"], []).append(dict(s))
    return [pipeline_shape(dict(p), by_pipe.get(p["id"], [])) for p in pipes]

@router.post("/pipelines", status_code=201)
async def create_pipeline(payload: PipelineCreate, admin: dict = Depends(require_admin)):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Pipeline name is required")

    async with db.pool.acquire() as conn:
        async with conn.transaction():
            pos_row = await conn.fetchrow("SELECT COALESCE(MAX(position), -1) + 1 AS pos FROM coexistence.pipelines")
            pipe = await conn.fetchrow(
                """
                INSERT INTO coexistence.pipelines (name, is_default, position, created_by)
                VALUES ($1, FALSE, $2, $3) RETURNING *
                """,
                name, pos_row["pos"], admin["id"]
            )
            for idx, s in enumerate(DEFAULT_STAGES):
                await conn.execute(
                    """
                    INSERT INTO coexistence.pipeline_stages (pipeline_id, name, probability, position, stage_type, color)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    pipe["id"], s["name"], s["probability"], idx, s["stage_type"], s["color"]
                )
            stages = await conn.fetch(
                "SELECT * FROM coexistence.pipeline_stages WHERE pipeline_id = $1 ORDER BY position ASC",
                pipe["id"]
            )

    await audit_log(actor=admin, action="pipeline.create", target_type="pipeline", target_id=str(pipe["id"]), payload={"name": pipe["name"]})
    return pipeline_shape(dict(pipe), [dict(s) for s in stages])

@router.put("/pipelines/{pipeline_id}")
async def update_pipeline(pipeline_id: int, payload: PipelineUpdate, admin: dict = Depends(require_admin)):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Pipeline name is required")
    row = await db.fetchrow(
        "UPDATE coexistence.pipelines SET name = $1, updated_at = NOW() WHERE id = $2 RETURNING *",
        name, pipeline_id
    )
    if not row:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return pipeline_shape(dict(row))

@router.delete("/pipelines/{pipeline_id}")
async def delete_pipeline(pipeline_id: int, admin: dict = Depends(require_admin)):
    cnt = await db.fetchval("SELECT COUNT(*)::int FROM coexistence.pipelines")
    if cnt and cnt <= 1:
        raise HTTPException(status_code=409, detail="Cannot delete the only pipeline. Create another first.")
    res = await db.execute("DELETE FROM coexistence.pipelines WHERE id = $1", pipeline_id)
    if res.endswith(" 0"):
        raise HTTPException(status_code=404, detail="Pipeline not found")
    await audit_log(actor=admin, action="pipeline.delete", target_type="pipeline", target_id=str(pipeline_id))
    return {"ok": True}

# --- Stages Routes ---

@router.post("/pipelines/{pipeline_id}/stages", status_code=201)
async def add_stage(pipeline_id: int, payload: StageCreate, admin: dict = Depends(require_admin)):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Stage name is required")
    pipe = await db.fetchrow("SELECT 1 FROM coexistence.pipelines WHERE id = $1", pipeline_id)
    if not pipe:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    pos = await db.fetchval("SELECT COALESCE(MAX(position), -1) + 1 FROM coexistence.pipeline_stages WHERE pipeline_id = $1", pipeline_id)
    prob = max(0, min(100, payload.probability or 0))
    stype = payload.stageType if payload.stageType in ("open", "won", "lost") else "open"

    row = await db.fetchrow(
        """
        INSERT INTO coexistence.pipeline_stages (pipeline_id, name, probability, position, stage_type, color)
        VALUES ($1, $2, $3, $4, $5, $6) RETURNING *
        """,
        pipeline_id, name, prob, pos, stype, payload.color
    )
    return stage_shape(dict(row))

@router.put("/stages/{stage_id}")
async def update_stage(stage_id: int, payload: StageUpdate, admin: dict = Depends(require_admin)):
    sets = ["updated_at = NOW()"]
    params = [stage_id]
    if payload.name is not None:
        params.append(payload.name.strip())
        sets.append(f"name = ${len(params)}")
    if payload.probability is not None:
        params.append(max(0, min(100, payload.probability)))
        sets.append(f"probability = ${len(params)}")
    if payload.color is not None:
        params.append(payload.color)
        sets.append(f"color = ${len(params)}")
    if payload.stageType is not None and payload.stageType in ("open", "won", "lost"):
        params.append(payload.stageType)
        sets.append(f"stage_type = ${len(params)}")
    if payload.position is not None:
        params.append(payload.position)
        sets.append(f"position = ${len(params)}")

    query = f"UPDATE coexistence.pipeline_stages SET {', '.join(sets)} WHERE id = $1 RETURNING *"
    row = await db.fetchrow(query, *params)
    if not row:
        raise HTTPException(status_code=404, detail="Stage not found")
    return stage_shape(dict(row))

@router.delete("/stages/{stage_id}")
async def delete_stage(stage_id: int, admin: dict = Depends(require_admin)):
    deal_cnt = await db.fetchval("SELECT COUNT(*)::int FROM coexistence.deals WHERE stage_id = $1", stage_id)
    if deal_cnt and deal_cnt > 0:
        raise HTTPException(status_code=409, detail="Move or delete the deals in this stage first.")
    res = await db.execute("DELETE FROM coexistence.pipeline_stages WHERE id = $1", stage_id)
    if res.endswith(" 0"):
        raise HTTPException(status_code=404, detail="Stage not found")
    return {"ok": True}

# --- Deals Routes ---

@router.get("/deals/contact-search")
async def contact_search(q: Optional[str] = "", admin: dict = Depends(require_admin)):
    query_str = (q or "").strip()
    if not query_str:
        return []
    like = f"%{query_str}%"
    digits = "".join(filter(str.isdigit, query_str))
    rows = await db.fetch(
        """
        SELECT wa_number, contact_number, COALESCE(name, profile_name) AS name
        FROM coexistence.contacts
        WHERE COALESCE(name, '') ILIKE $1
           OR COALESCE(profile_name, '') ILIKE $1
           OR ($2 <> '' AND contact_number ILIKE $3)
        ORDER BY COALESCE(name, profile_name) NULLS LAST
        LIMIT 15
        """,
        like, digits, f"%{digits}%"
    )
    return [{"waNumber": r["wa_number"], "contactNumber": r["contact_number"], "name": r["name"]} for r in rows]

@router.get("/deals/metrics")
async def get_deal_metrics(pipelineId: int = Query(...), user: dict = Depends(get_current_user)):
    params = [pipelineId]
    scope = ""
    if not is_admin_user(user):
        params.append(user["id"])
        scope = f"AND d.assigned_user_id = ${len(params)}"

    query = f"""
      SELECT
         COUNT(*)                                     FILTER (WHERE d.status='open')  AS total_deals,
         COALESCE(SUM(d.value)                        FILTER (WHERE d.status='open'),0) AS pipeline_value,
         COALESCE(AVG(d.value)                        FILTER (WHERE d.status='open'),0) AS avg_deal_size,
         COALESCE(SUM(d.value * s.probability/100.0) FILTER (WHERE d.status='open'),0) AS weighted_value,
         COUNT(*) FILTER (WHERE d.status='won'  AND d.won_at  >= date_trunc('month', NOW())) AS won_this_month,
         COUNT(*) FILTER (WHERE d.status='lost' AND d.lost_at >= date_trunc('month', NOW())) AS lost_this_month
       FROM coexistence.deals d
       JOIN coexistence.pipeline_stages s ON s.id = d.stage_id
       WHERE d.pipeline_id = $1 {scope}
    """
    row = await db.fetchrow(query, *params)
    return {
        "totalDeals": int(row["total_deals"]),
        "pipelineValue": float(row["pipeline_value"]),
        "avgDealSize": float(row["avg_deal_size"]),
        "weightedValue": float(row["weighted_value"]),
        "wonThisMonth": int(row["won_this_month"]),
        "lostThisMonth": int(row["lost_this_month"]),
    }

@router.get("/deals")
async def list_deals(pipelineId: int = Query(...), user: dict = Depends(get_current_user)):
    params = [pipelineId]
    scope = ""
    if not is_admin_user(user):
        params.append(user["id"])
        scope = f"AND d.assigned_user_id = ${len(params)}"

    query = f"""
      SELECT d.*, COALESCE(u.display_name, u.username) AS assigned_user_name
      FROM coexistence.deals d
      LEFT JOIN coexistence.forgecrm_users u ON u.id = d.assigned_user_id
      WHERE d.pipeline_id = $1 {scope}
      ORDER BY d.position ASC, d.created_at ASC
    """
    rows = await db.fetch(query, *params)
    return [deal_shape(dict(r)) for r in rows]

@router.post("/deals", status_code=201)
async def create_deal(payload: DealCreate, admin: dict = Depends(require_admin)):
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Deal title is required")

    stage = None
    if payload.stageId:
        stage = await get_stage_in_pipeline(payload.stageId, payload.pipelineId)
        if not stage:
            raise HTTPException(status_code=400, detail="Stage does not belong to this pipeline")
    else:
        stage = await db.fetchrow(
            "SELECT * FROM coexistence.pipeline_stages WHERE pipeline_id = $1 ORDER BY position ASC LIMIT 1",
            payload.pipelineId
        )
        if not stage:
            raise HTTPException(status_code=400, detail="Pipeline has no stages")

    assigned_user_id = payload.assignedUserId
    contact_wa = "".join(filter(str.isdigit, payload.contactWaNumber or "")) or None
    contact_num = "".join(filter(str.isdigit, payload.contactNumber or "")) or None

    if not assigned_user_id and contact_wa and contact_num:
        assigned_user_id = await db.fetchval(
            "SELECT assigned_user_id FROM coexistence.contacts WHERE wa_number = $1 AND contact_number = $2",
            contact_wa, contact_num
        )

    stype = stage["stage_type"]
    status_str = status_for_stage_type(stype)
    pos = await db.fetchval("SELECT COALESCE(MAX(position), -1) + 1 FROM coexistence.deals WHERE stage_id = $1", stage["id"])

    close_dt = None
    if payload.expectedCloseDate:
        try:
            close_dt = datetime.fromisoformat(payload.expectedCloseDate)
        except Exception:
            close_dt = None

    row = await db.fetchrow(
        f"""
        INSERT INTO coexistence.deals
          (pipeline_id, stage_id, title, value, currency, status, assigned_user_id,
           contact_wa_number, contact_number, contact_name, expected_close_date, notes,
           position, won_at, lost_at, created_by)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,
                {'NOW()' if status_str == 'won' else 'NULL'}, {'NOW()' if status_str == 'lost' else 'NULL'}, $14)
        RETURNING *
        """,
        payload.pipelineId, stage["id"], title,
        payload.value or 0.0, (payload.currency or "INR").strip(), status_str, assigned_user_id,
        contact_wa, contact_num, payload.contactName,
        close_dt, payload.notes,
        pos, admin["id"]
    )
    created = dict(row)
    await sync_contact_assignment(created.get("contact_wa_number"), created.get("contact_number"), created.get("assigned_user_id"))
    return deal_shape(created)

@router.put("/deals/{deal_id}")
async def update_deal(deal_id: int, payload: DealUpdate, admin: dict = Depends(require_admin)):
    ex = await db.fetchrow("SELECT * FROM coexistence.deals WHERE id = $1", deal_id)
    if not ex:
        raise HTTPException(status_code=404, detail="Deal not found")

    stage_id = ex["stage_id"]
    status_str = ex["status"]
    if payload.stageId is not None and payload.stageId != ex["stage_id"]:
        stage = await get_stage_in_pipeline(payload.stageId, ex["pipeline_id"])
        if not stage:
            raise HTTPException(status_code=400, detail="Stage does not belong to this deal's pipeline")
        stage_id = stage["id"]
        status_str = status_for_stage_type(stage["stage_type"])

    sets = ["updated_at = NOW()"]
    params = [deal_id]

    if payload.title is not None:
        params.append(payload.title.strip())
        sets.append(f"title = ${len(params)}")
    if payload.value is not None:
        params.append(payload.value)
        sets.append(f"value = ${len(params)}")
    if payload.currency is not None:
        params.append(payload.currency.strip())
        sets.append(f"currency = ${len(params)}")
    if payload.assignedUserId is not None:
        params.append(payload.assignedUserId or None)
        sets.append(f"assigned_user_id = ${len(params)}")
    if payload.contactWaNumber is not None:
        clean = "".join(filter(str.isdigit, payload.contactWaNumber)) or None
        params.append(clean)
        sets.append(f"contact_wa_number = ${len(params)}")
    if payload.contactNumber is not None:
        clean = "".join(filter(str.isdigit, payload.contactNumber)) or None
        params.append(clean)
        sets.append(f"contact_number = ${len(params)}")
    if payload.contactName is not None:
        params.append(payload.contactName)
        sets.append(f"contact_name = ${len(params)}")
    if payload.expectedCloseDate is not None:
        close_dt = None
        try:
            close_dt = datetime.fromisoformat(payload.expectedCloseDate) if payload.expectedCloseDate else None
        except Exception:
            pass
        params.append(close_dt)
        sets.append(f"expected_close_date = ${len(params)}")
    if payload.notes is not None:
        params.append(payload.notes)
        sets.append(f"notes = ${len(params)}")

    params.append(stage_id)
    sets.append(f"stage_id = ${len(params)}")

    params.append(status_str)
    sets.append(f"status = ${len(params)}")

    won_expr = "COALESCE(won_at, NOW())" if status_str == "won" else "NULL"
    lost_expr = "COALESCE(lost_at, NOW())" if status_str == "lost" else "NULL"
    sets.append(f"won_at = {won_expr}")
    sets.append(f"lost_at = {lost_expr}")

    query = f"UPDATE coexistence.deals SET {', '.join(sets)} WHERE id = $1 RETURNING *"
    updated_row = await db.fetchrow(query, *params)
    updated = dict(updated_row)

    if payload.assignedUserId is not None:
        await sync_contact_assignment(updated.get("contact_wa_number"), updated.get("contact_number"), updated.get("assigned_user_id"))

    return deal_shape(updated)

@router.post("/deals/{deal_id}/move")
async def move_deal(deal_id: int, payload: DealMove, user: dict = Depends(get_current_user)):
    ex = await db.fetchrow("SELECT * FROM coexistence.deals WHERE id = $1", deal_id)
    if not ex:
        raise HTTPException(status_code=404, detail="Deal not found")

    if not is_admin_user(user) and ex.get("assigned_user_id") != user["id"]:
        raise HTTPException(status_code=403, detail="You can only move deals assigned to you")

    stage = await get_stage_in_pipeline(payload.stageId, ex["pipeline_id"])
    if not stage:
        raise HTTPException(status_code=400, detail="Stage does not belong to this deal's pipeline")

    status_str = status_for_stage_type(stage["stage_type"])
    pos = await db.fetchval("SELECT COALESCE(MAX(position), -1) + 1 FROM coexistence.deals WHERE stage_id = $1", stage["id"])
    won_expr = "COALESCE(won_at, NOW())" if status_str == "won" else "NULL"
    lost_expr = "COALESCE(lost_at, NOW())" if status_str == "lost" else "NULL"

    query = f"""
      UPDATE coexistence.deals
      SET stage_id = $1, status = $2, position = $3, updated_at = NOW(),
          won_at = {won_expr}, lost_at = {lost_expr}
      WHERE id = $4 RETURNING *
    """
    row = await db.fetchrow(query, stage["id"], status_str, pos, deal_id)
    return deal_shape(dict(row))

@router.delete("/deals/{deal_id}")
async def delete_deal(deal_id: int, admin: dict = Depends(require_admin)):
    res = await db.execute("DELETE FROM coexistence.deals WHERE id = $1", deal_id)
    if res.endswith(" 0"):
        raise HTTPException(status_code=404, detail="Deal not found")
    await audit_log(actor=admin, action="deal.delete", target_type="deal", target_id=str(deal_id))
    return {"ok": True}
