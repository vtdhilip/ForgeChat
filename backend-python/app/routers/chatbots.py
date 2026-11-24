import json
import math
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from pydantic import BaseModel

from app.core.database import db
from app.middleware.auth import get_current_user, require_permission
from app.middleware.tenant import get_tenant_context

router = APIRouter(prefix="/api/chatbots", tags=["Chatbots & Automations"])
executions_router = APIRouter(prefix="/api/executions", tags=["Chatbot Executions"])

SUPPORTED_TYPES = {"trigger", "message", "condition", "delay", "action", "handoff", "subflow", "api", "ai"}

def sanitize_to_linear(config: Any) -> Any:
    if not isinstance(config, dict):
        return config
    nodes = config.get("nodes")
    edges = config.get("edges")
    if not isinstance(nodes, list):
        return config

    keep_nodes = [n for n in nodes if isinstance(n, dict) and n.get("type") in SUPPORTED_TYPES]
    valid_ids = {n.get("id") for n in keep_nodes if n.get("id")}
    keep_edges = [
        e for e in (edges if isinstance(edges, list) else [])
        if isinstance(e, dict) and e.get("from") in valid_ids and e.get("to") in valid_ids
    ]
    return {**config, "nodes": keep_nodes, "edges": keep_edges}

def shape_bot(r: dict) -> dict:
    d = dict(r)
    if d.get("created_at"):
        d["created_at"] = d["created_at"].isoformat()
    if d.get("updated_at"):
        d["updated_at"] = d["updated_at"].isoformat()
    if d.get("config") and isinstance(d["config"], str):
        try:
            parsed = json.loads(d["config"])
            if isinstance(parsed, str):
                parsed = json.loads(parsed)
            d["config"] = parsed
        except Exception:
            pass
    return d

def shape_execution(r: dict) -> dict:
    d = dict(r)
    if d.get("started_at"):
        d["started_at"] = d["started_at"].isoformat()
    if d.get("completed_at"):
        d["completed_at"] = d["completed_at"].isoformat()
    if d.get("created_at"):
        d["created_at"] = d["created_at"].isoformat()
    if d.get("trigger_data") and isinstance(d["trigger_data"], str):
        try:
            d["trigger_data"] = json.loads(d["trigger_data"])
        except Exception:
            pass
    return d

def shape_step(r: dict) -> dict:
    d = dict(r)
    if d.get("started_at"):
        d["started_at"] = d["started_at"].isoformat()
    if d.get("completed_at"):
        d["completed_at"] = d["completed_at"].isoformat()
    if d.get("created_at"):
        d["created_at"] = d["created_at"].isoformat()
    if d.get("input_data") and isinstance(d["input_data"], str):
        try:
            d["input_data"] = json.loads(d["input_data"])
        except Exception:
            pass
    if d.get("output_data") and isinstance(d["output_data"], str):
        try:
            d["output_data"] = json.loads(d["output_data"])
        except Exception:
            pass
    return d

class ChatbotCreate(BaseModel):
    name: str
    description: Optional[str] = None
    status: Optional[str] = "draft"
    trigger_type: Optional[str] = "keyword"
    config: Optional[Dict[str, Any]] = None

class ChatbotUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    trigger_type: Optional[str] = None
    config: Optional[Dict[str, Any]] = None

@router.get("")
async def list_chatbots(tenant_ctx: dict = Depends(get_tenant_context)):
    org_id = tenant_ctx["org_id"]
    rows = await db.fetch(
        """
        SELECT id, name, description, status, trigger_type, config, created_at, updated_at
        FROM coexistence.chatbots
        WHERE org_id = $1::uuid
        ORDER BY updated_at DESC
        """,
        org_id
    )
    return [shape_bot(dict(r)) for r in rows]

@router.get("/{bot_id}")
async def get_chatbot(bot_id: int, tenant_ctx: dict = Depends(get_tenant_context)):
    org_id = tenant_ctx["org_id"]
    row = await db.fetchrow(
        """
        SELECT id, name, description, status, trigger_type, config, created_at, updated_at
        FROM coexistence.chatbots
        WHERE id = $1 AND org_id = $2::uuid
        """,
        bot_id, org_id
    )
    if not row:
        raise HTTPException(status_code=404, detail="Chatbot not found")
    return shape_bot(dict(row))

@router.post("", status_code=201)
async def create_chatbot(
    payload: ChatbotCreate,
    tenant_ctx: dict = Depends(get_tenant_context),
    user: dict = Depends(require_permission("chatbot-builder"))
):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")

    org_id = tenant_ctx["org_id"]
    sanitized = sanitize_to_linear(payload.config) if payload.config else {}
    row = await db.fetchrow(
        """
        INSERT INTO coexistence.chatbots (name, description, status, trigger_type, config, org_id)
        VALUES ($1, $2, $3, $4, $5, $6::uuid)
        RETURNING *
        """,
        name, payload.description, payload.status or "draft", payload.trigger_type or "keyword", json.dumps(sanitized), org_id
    )
    return shape_bot(dict(row))

@router.put("/{bot_id}")
async def update_chatbot(
    bot_id: int,
    payload: ChatbotUpdate,
    tenant_ctx: dict = Depends(get_tenant_context),
    user: dict = Depends(require_permission("chatbot-builder"))
):
    if payload.name is not None and not payload.name.strip():
        raise HTTPException(status_code=400, detail="Name is required")

    org_id = tenant_ctx["org_id"]
    sanitized = json.dumps(sanitize_to_linear(payload.config)) if payload.config is not None else None
    row = await db.fetchrow(
        """
        UPDATE coexistence.chatbots SET
          name = COALESCE($1, name),
          description = $2,
          status = COALESCE($3, status),
          trigger_type = COALESCE($4, trigger_type),
          config = COALESCE($5, config),
          updated_at = NOW()
        WHERE id = $6 AND org_id = $7::uuid
        RETURNING *
        """,
        payload.name.strip() if payload.name else None,
        payload.description,
        payload.status,
        payload.trigger_type,
        sanitized,
        bot_id,
        org_id
    )
    if not row:
        raise HTTPException(status_code=404, detail="Chatbot not found")
    return shape_bot(dict(row))

@router.delete("/{bot_id}")
async def delete_chatbot(
    bot_id: int,
    tenant_ctx: dict = Depends(get_tenant_context),
    user: dict = Depends(require_permission("chatbot-builder"))
):
    org_id = tenant_ctx["org_id"]
    res = await db.execute("DELETE FROM coexistence.chatbots WHERE id = $1 AND org_id = $2::uuid", bot_id, org_id)
    if res.endswith(" 0"):
        raise HTTPException(status_code=404, detail="Chatbot not found")
    return {"ok": True}

@router.post("/{bot_id}/duplicate", status_code=201)
async def duplicate_chatbot(
    bot_id: int,
    tenant_ctx: dict = Depends(get_tenant_context),
    user: dict = Depends(require_permission("chatbot-builder"))
):
    org_id = tenant_ctx["org_id"]
    src = await db.fetchrow(
        "SELECT name, description, trigger_type, config FROM coexistence.chatbots WHERE id = $1 AND org_id = $2::uuid",
        bot_id, org_id
    )
    if not src:
        raise HTTPException(status_code=404, detail="Chatbot not found")

    row = await db.fetchrow(
        """
        INSERT INTO coexistence.chatbots (name, description, status, trigger_type, config, org_id)
        VALUES ($1, $2, 'inactive', $3, $4, $5::uuid)
        RETURNING id, name, description, status, trigger_type, config, created_at, updated_at
        """,
        f"{src['name']} (copy)", src["description"], src["trigger_type"], src["config"], org_id
    )
    return shape_bot(dict(row))

@router.get("/{bot_id}/export")
async def export_chatbot(
    bot_id: int,
    tenant_ctx: dict = Depends(get_tenant_context),
    user: dict = Depends(require_permission("chatbot-builder"))
):
    org_id = tenant_ctx["org_id"]
    row = await db.fetchrow(
        "SELECT name, description, trigger_type, config FROM coexistence.chatbots WHERE id = $1 AND org_id = $2::uuid",
        bot_id, org_id
    )
    if not row:
        raise HTTPException(status_code=404, detail="Chatbot not found")

    config = row["config"]
    if isinstance(config, str):
        try:
            config = json.loads(config)
        except Exception:
            pass

    return {
        "type": "synapticchat.automation",
        "version": 1,
        "automation": {
            "name": row["name"],
            "description": row["description"],
            "trigger_type": row["trigger_type"],
            "config": config or {},
        },
    }

@router.post("/import", status_code=201)
async def import_chatbot(
    request: Request,
    tenant_ctx: dict = Depends(get_tenant_context),
    user: dict = Depends(require_permission("chatbot-builder"))
):
    payload = await request.json() or {}
    if payload.get("type") not in ("synapticchat.automation", "forgechat.automation") or not payload.get("automation") or not payload["automation"].get("name"):
        raise HTTPException(status_code=400, detail="That file is not a Synaptic Chat automation export.")

    org_id = tenant_ctx["org_id"]
    a = payload["automation"]
    sanitized = sanitize_to_linear(a.get("config")) or {}
    row = await db.fetchrow(
        """
        INSERT INTO coexistence.chatbots (name, description, status, trigger_type, config, org_id)
        VALUES ($1, $2, 'inactive', $3, $4, $5::uuid)
        RETURNING id, name, description, status, trigger_type, config, created_at, updated_at
        """,
        f"{str(a['name']).strip()} (imported)"[:200], a.get("description"), a.get("trigger_type") or "keyword", json.dumps(sanitized), org_id
    )
    return shape_bot(dict(row))

@router.get("/{bot_id}/executions")
async def list_chatbot_executions(
    bot_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    startDate: Optional[str] = None,
    endDate: Optional[str] = None,
    messageStatus: Optional[str] = None,
    tenant_ctx: dict = Depends(get_tenant_context),
):
    org_id = tenant_ctx["org_id"]
    # Check bot belongs to org
    bot = await db.fetchrow("SELECT id FROM coexistence.chatbots WHERE id = $1 AND org_id = $2::uuid", bot_id, org_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Chatbot not found")

    offset = (page - 1) * limit
    where_clauses = ["e.automation_id = $1", "e.org_id = $2::uuid"]
    params: List[Any] = [bot_id, org_id]

    if status and status != "all":
        params.append(status)
        where_clauses.append(f"e.status = ${len(params)}")

    if startDate:
        try:
            params.append(datetime.fromisoformat(startDate.replace("Z", "+00:00")))
            where_clauses.append(f"e.started_at >= ${len(params)}")
        except Exception:
            pass

    if endDate:
        try:
            params.append(datetime.fromisoformat(endDate.replace("Z", "+00:00")))
            where_clauses.append(f"e.started_at <= ${len(params)}")
        except Exception:
            pass

    join_clause = ""
    if messageStatus and messageStatus != "all":
        params.append(messageStatus)
        join_clause = f"JOIN coexistence.automation_execution_steps s ON s.execution_id = e.id AND s.wa_message_status = ${len(params)}"

    where_sql = "WHERE " + " AND ".join(where_clauses)
    count_sql = f"SELECT COUNT(DISTINCT e.id) FROM coexistence.automation_executions e {join_clause} {where_sql}"
    total = await db.fetchval(count_sql, *params) or 0

    data_params = list(params)
    data_params.append(limit)
    limit_p = len(data_params)
    data_params.append(offset)
    offset_p = len(data_params)

    data_sql = f"""
        SELECT DISTINCT e.id, e.automation_id, e.status, e.trigger_type, e.trigger_data, e.contact_number,
               e.started_at, e.completed_at, e.error_message, e.created_at
        FROM coexistence.automation_executions e
        {join_clause}
        {where_sql}
        ORDER BY e.started_at DESC
        LIMIT ${limit_p} OFFSET ${offset_p}
    """
    rows = await db.fetch(data_sql, *data_params)

    return {
        "executions": [shape_execution(dict(r)) for r in rows],
        "total": total,
        "page": page,
        "totalPages": math.ceil(total / limit) if total > 0 else 1,
    }

# --- Execution Routes ---

@executions_router.get("/{exec_id}")
async def get_execution(
    exec_id: int,
    tenant_ctx: dict = Depends(get_tenant_context)
):
    org_id = tenant_ctx["org_id"]
    exec_row = await db.fetchrow(
        """
        SELECT id, automation_id, status, trigger_type, trigger_data, contact_number,
               started_at, completed_at, error_message, created_at
        FROM coexistence.automation_executions
        WHERE id = $1 AND org_id = $2::uuid
        """,
        exec_id, org_id
    )
    if not exec_row:
        raise HTTPException(status_code=404, detail="Execution not found")

    step_rows = await db.fetch(
        """
        SELECT id, execution_id, node_id, node_type, node_name, input_data, output_data,
               status, started_at, completed_at, error_message, wa_message_id, wa_message_status, created_at
        FROM coexistence.automation_execution_steps
        WHERE execution_id = $1
        ORDER BY started_at ASC
        """,
        exec_id
    )

    result = shape_execution(dict(exec_row))
    result["steps"] = [shape_step(dict(s)) for s in step_rows]
    return result

@executions_router.post("/{exec_id}/cancel")
async def cancel_execution(
    exec_id: int,
    tenant_ctx: dict = Depends(get_tenant_context),
    user: dict = Depends(require_permission("chatbot-builder"))
):
    org_id = tenant_ctx["org_id"]
    row = await db.fetchrow(
        """
        UPDATE coexistence.automation_executions
           SET status = 'cancelled',
               completed_at = NOW(),
               error_message = COALESCE(error_message, 'Cancelled by user')
         WHERE id = $1 AND org_id = $2::uuid AND status IN ('running', 'paused', 'queued')
         RETURNING *
        """,
        exec_id, org_id
    )
    if not row:
        raise HTTPException(status_code=409, detail="Execution is already finished — nothing to stop.")
    return shape_execution(dict(row))
