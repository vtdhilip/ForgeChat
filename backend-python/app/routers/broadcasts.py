import json
import asyncio
from typing import Optional, List, Dict, Any, Union
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from pydantic import BaseModel

from app.core.database import db
from app.middleware.auth import get_current_user, require_permission
from app.services.whatsapp_service import normalize_phone
from app.services.message_sender import (
    resolve_account,
    insert_pending_row,
    dispatch_send_task
)
from app.services.template_components import build_template_components, resolve_template_text
from app.routers.media_library import sync_media_to_account

router = APIRouter(prefix="/api/broadcasts", tags=["Broadcasts"])

async def load_contact_context(numbers: List[str]) -> Dict[str, dict]:
    cleaned = list({normalize_phone(n) for n in numbers if normalize_phone(n)})
    if not cleaned:
        return {}
    rows = await db.fetch(
        """
        SELECT regexp_replace(contact_number, '\\D', '', 'g') AS num, name, custom_fields, tags
        FROM coexistence.contacts
        WHERE regexp_replace(contact_number, '\\D', '', 'g') = ANY($1::text[])
        """,
        cleaned
    )
    return {r["num"]: dict(r) for r in rows}

async def get_broadcast_with_logs(broadcast_id: int) -> Optional[dict]:
    b_rows = await db.fetch(
        """
        SELECT b.*, t.name AS template_name,
               (SELECT COUNT(*) FROM coexistence.broadcast_logs WHERE broadcast_id = b.id) AS log_count,
               (SELECT MAX(sent_at) FROM coexistence.broadcast_logs WHERE broadcast_id = b.id) AS last_activity
        FROM coexistence.broadcasts b
        LEFT JOIN coexistence.message_templates t ON t.id = b.template_id
        WHERE b.id = $1
        """,
        broadcast_id
    )
    if not b_rows:
        return None
    b = dict(b_rows[0])

    logs_rows = await db.fetch(
        "SELECT * FROM coexistence.broadcast_logs WHERE broadcast_id = $1 ORDER BY sent_at DESC LIMIT 100",
        broadcast_id
    )

    agg = await db.fetchrow(
        """
        SELECT COUNT(*)::int AS recipient_count,
               MAX(sent_at) AS sent_at,
               CASE
                 WHEN COUNT(*) FILTER (WHERE status = 'PENDING') > 0 THEN 'SENDING'
                 WHEN COUNT(*) FILTER (WHERE status = 'failed') > 0 AND COUNT(*) FILTER (WHERE status IN ('sent','delivered','read')) = 0 THEN 'FAILED'
                 WHEN COUNT(*) FILTER (WHERE status = 'failed') > 0 THEN 'PARTIAL'
                 WHEN COUNT(*) FILTER (WHERE status IN ('sent','delivered','read')) > 0 THEN 'SENT'
                 ELSE 'UNKNOWN'
               END AS status
        FROM coexistence.broadcast_logs
        WHERE broadcast_id = $1 AND action = 'BROADCAST'
        """,
        broadcast_id
    )

    logs = []
    if agg and agg["recipient_count"] > 0:
        logs.append({
            "id": f"broadcast-{broadcast_id}",
            "action": "BROADCAST",
            "sent_to": f"{agg['recipient_count']} contact{'s' if agg['recipient_count'] != 1 else ''}",
            "status": agg["status"],
            "sent_at": agg["sent_at"].isoformat() if agg.get("sent_at") else None,
            "wa_message_id": None,
            "error_message": None,
            "_recipientCount": agg["recipient_count"]
        })

    for lr in logs_rows:
        if lr["action"] == "TEST":
            d = dict(lr)
            if d.get("sent_at"):
                d["sent_at"] = d["sent_at"].isoformat()
            logs.append(d)

    b["logs"] = logs
    if b.get("created_at"):
        b["created_at"] = b["created_at"].isoformat()
    if b.get("updated_at"):
        b["updated_at"] = b["updated_at"].isoformat()
    if b.get("last_activity"):
        b["last_activity"] = b["last_activity"].isoformat()

    return b

class BroadcastCreate(BaseModel):
    from_number: str
    recipient_numbers: List[Any]
    template_id: Optional[int] = None
    status: Optional[str] = "DRAFT"
    test_number: Optional[str] = None
    name: Optional[str] = None
    variable_mapping: Optional[Dict[str, Any]] = None
    message_type: Optional[str] = "template"
    body: Optional[str] = None
    url: Optional[str] = None
    media_library_id: Optional[int] = None
    caption: Optional[str] = None

class BroadcastUpdate(BaseModel):
    from_number: Optional[str] = None
    recipient_numbers: Optional[List[Any]] = None
    template_id: Optional[int] = None
    test_number: Optional[str] = None
    name: Optional[str] = None
    variable_mapping: Optional[Dict[str, Any]] = None
    message_type: Optional[str] = None
    body: Optional[str] = None
    url: Optional[str] = None
    media_library_id: Optional[int] = None
    caption: Optional[str] = None

class BroadcastTestRequest(BaseModel):
    test_number: str

@router.get("")
async def list_broadcasts(status: Optional[str] = None, user: dict = Depends(get_current_user)):
    params = []
    status_filter = ""
    if status and status != "all":
        params.append(status)
        status_filter = f"WHERE display_status = ${len(params)}"

    query = f"""
      WITH base AS (
         SELECT b.*, t.name AS template_name,
                (SELECT COUNT(*) FROM coexistence.broadcast_logs WHERE broadcast_id = b.id) AS log_count,
                (SELECT MAX(sent_at) FROM coexistence.broadcast_logs WHERE broadcast_id = b.id) AS last_activity,
                (
                  SELECT
                    CASE
                      WHEN b.status = 'DRAFT' THEN 'DRAFT'
                      WHEN b.status = 'SENDING' THEN 'SENDING'
                      WHEN COUNT(*) FILTER (WHERE bl.status = 'PENDING') > 0 THEN 'SENDING'
                      WHEN COUNT(*) FILTER (WHERE bl.status = 'failed') > 0
                       AND COUNT(*) FILTER (WHERE bl.status IN ('sent','delivered','read')) = 0 THEN 'FAILED'
                      WHEN COUNT(*) FILTER (WHERE bl.status = 'failed') > 0 THEN 'PARTIAL'
                      WHEN COUNT(*) FILTER (WHERE bl.status IN ('sent','delivered','read')) > 0 THEN 'SENT'
                      ELSE b.status
                    END
                  FROM coexistence.broadcast_logs bl
                  WHERE bl.broadcast_id = b.id AND bl.action = 'BROADCAST'
                ) AS display_status
         FROM coexistence.broadcasts b
         LEFT JOIN coexistence.message_templates t ON t.id = b.template_id
       )
       SELECT * FROM base
       {status_filter}
       ORDER BY created_at DESC
    """
    rows = await db.fetch(query, *params)
    out = []
    for r in rows:
        d = dict(r)
        d["status"] = d.get("display_status") or d.get("status")
        if d.get("created_at"):
            d["created_at"] = d["created_at"].isoformat()
        if d.get("updated_at"):
            d["updated_at"] = d["updated_at"].isoformat()
        if d.get("last_activity"):
            d["last_activity"] = d["last_activity"].isoformat()
        out.append(d)
    return out

@router.get("/{broadcast_id}")
async def get_broadcast(broadcast_id: int, user: dict = Depends(get_current_user)):
    data = await get_broadcast_with_logs(broadcast_id)
    if not data:
        raise HTTPException(status_code=404, detail="Broadcast not found")
    return data

@router.post("", status_code=201)
async def create_broadcast(payload: BroadcastCreate, user: dict = Depends(require_permission("bulk-message"))):
    if not payload.from_number or not payload.recipient_numbers:
        raise HTTPException(status_code=400, detail="from_number and recipient_numbers required")
    if len(payload.recipient_numbers) > 5000:
        raise HTTPException(status_code=400, detail="Too many recipients (max 5000 per broadcast)")

    msg_type = payload.message_type or "template"
    if msg_type == "template" and not payload.template_id:
        raise HTTPException(status_code=400, detail="template_id required for template broadcasts")

    async with db.pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                """
                INSERT INTO coexistence.broadcasts
                 (from_number, recipient_numbers, template_id, status, test_number, name,
                  variable_mapping, message_type, body, url, media_library_id, caption, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, NOW())
                RETURNING *
                """,
                payload.from_number, json.dumps(payload.recipient_numbers),
                payload.template_id, payload.status or "DRAFT",
                payload.test_number, payload.name,
                json.dumps(payload.variable_mapping or {}),
                msg_type, payload.body, payload.url,
                payload.media_library_id, payload.caption
            )
            broadcast = dict(row)
            if payload.test_number:
                await conn.execute(
                    """
                    INSERT INTO coexistence.broadcast_logs (broadcast_id, action, sent_to, status)
                    VALUES ($1, 'TEST', $2, 'PENDING')
                    """,
                    broadcast["id"], payload.test_number
                )

    if broadcast.get("created_at"):
        broadcast["created_at"] = broadcast["created_at"].isoformat()
    if broadcast.get("updated_at"):
        broadcast["updated_at"] = broadcast["updated_at"].isoformat()
    return broadcast

@router.put("/{broadcast_id}")
async def update_broadcast(broadcast_id: int, payload: BroadcastUpdate, user: dict = Depends(require_permission("bulk-message"))):
    ex = await db.fetchrow("SELECT status FROM coexistence.broadcasts WHERE id = $1", broadcast_id)
    if not ex:
        raise HTTPException(status_code=404, detail="Broadcast not found")
    if ex["status"] != "DRAFT":
        raise HTTPException(status_code=403, detail="Only DRAFT broadcasts can be edited")

    row = await db.fetchrow(
        """
        UPDATE coexistence.broadcasts SET
          from_number = COALESCE($1, from_number),
          recipient_numbers = COALESCE($2, recipient_numbers),
          template_id = COALESCE($3, template_id),
          test_number = COALESCE($4, test_number),
          name = COALESCE($5, name),
          variable_mapping = COALESCE($6, variable_mapping),
          message_type = COALESCE($7, message_type),
          body = COALESCE($8, body),
          url = COALESCE($9, url),
          media_library_id = COALESCE($10, media_library_id),
          caption = COALESCE($11, caption),
          updated_at = NOW()
        WHERE id = $12
        RETURNING *
        """,
        payload.from_number,
        json.dumps(payload.recipient_numbers) if payload.recipient_numbers is not None else None,
        payload.template_id,
        payload.test_number,
        payload.name,
        json.dumps(payload.variable_mapping) if payload.variable_mapping is not None else None,
        payload.message_type,
        payload.body,
        payload.url,
        payload.media_library_id,
        payload.caption,
        broadcast_id
    )
    d = dict(row)
    if d.get("created_at"):
        d["created_at"] = d["created_at"].isoformat()
    if d.get("updated_at"):
        d["updated_at"] = d["updated_at"].isoformat()
    return d

@router.delete("/{broadcast_id}")
async def delete_broadcast(broadcast_id: int, user: dict = Depends(require_permission("bulk-message"))):
    res = await db.execute("DELETE FROM coexistence.broadcasts WHERE id = $1", broadcast_id)
    if res.endswith(" 0"):
        raise HTTPException(status_code=404, detail="Broadcast not found")
    return {"ok": True}

@router.post("/{broadcast_id}/send")
async def send_broadcast(broadcast_id: int, user: dict = Depends(require_permission("bulk-message"))):
    query = """
      SELECT b.*, t.id AS t_id, t.name AS t_name, t.language AS t_language, t.body AS t_body,
             t.header_type AS t_header_type, t.header_text AS t_header_text, t.footer AS t_footer,
             t.buttons AS t_buttons, t.samples AS t_samples,
             t.header_media_library_id AS t_header_media_library_id
      FROM coexistence.broadcasts b
      LEFT JOIN coexistence.message_templates t ON t.id = b.template_id
      WHERE b.id = $1
    """
    b_row = await db.fetchrow(query, broadcast_id)
    if not b_row:
        raise HTTPException(status_code=404, detail="Broadcast not found")
    b = dict(b_row)

    acc, err = await resolve_account(from_phone_number=b["from_number"])
    if err or not acc:
        raise HTTPException(status_code=400, detail=err or "Account not found")

    recipients = b.get("recipient_numbers") or []
    if isinstance(recipients, str):
        try:
            recipients = json.loads(recipients)
        except Exception:
            recipients = []

    if not recipients:
        raise HTTPException(status_code=400, detail="No recipients selected")

    template = None
    if b.get("message_type") == "template":
        template = {
            "id": b["t_id"],
            "name": b["t_name"],
            "language": b["t_language"],
            "body": b["t_body"],
            "header_type": b["t_header_type"],
            "header_text": b["t_header_text"],
            "footer": b["t_footer"],
            "buttons": b["t_buttons"],
            "samples": b["t_samples"],
            "header_media_library_id": b["t_header_media_library_id"]
        }

    contact_ctx = await load_contact_context(
        [r if isinstance(r, str) else r.get("contact_number") for r in recipients]
    )

    resolved_media_id = None
    tpl_ht = str(template.get("header_type") or "").upper() if template else ""
    needs_header_media = b.get("message_type") == "template" and tpl_ht in ("IMAGE", "VIDEO", "DOCUMENT")
    media_source_id = b.get("media_library_id") or (template.get("header_media_library_id") if needs_header_media and template else None)

    if (b.get("message_type") in ("image", "video", "audio", "document") or needs_header_media) and media_source_id:
        try:
            sync = await sync_media_to_account(media_source_id, acc["id"])
            resolved_media_id = sync.get("metaMediaId")
        except Exception as e:
            print(f"[broadcasts] Media sync failed: {e}")

    await db.execute("UPDATE coexistence.broadcasts SET status = 'SENDING', updated_at = NOW() WHERE id = $1", broadcast_id)

    enqueued = 0
    for r in recipients:
        base = {"contact_number": r, "name": ""} if isinstance(r, str) else r
        clean_contact = normalize_phone(base.get("contact_number"))
        ctx = contact_ctx.get(clean_contact, {})
        recipient = {
            **base,
            "name": base.get("name") or ctx.get("name") or "",
            "custom_fields": ctx.get("custom_fields") or base.get("custom_fields") or {},
            "tags": ctx.get("tags") if isinstance(ctx.get("tags"), list) else base.get("tags") or []
        }

        log_id = await db.fetchval(
            """
            INSERT INTO coexistence.broadcast_logs (broadcast_id, action, sent_to, status)
            VALUES ($1, 'BROADCAST', $2, 'PENDING') RETURNING id
            """,
            broadcast_id, recipient["contact_number"]
        )

        msg_type = b.get("message_type") or "template"
        try:
            if msg_type == "template":
                components = build_template_components(
                    template=template,
                    values=b.get("variable_mapping"),
                    header_media_id=resolved_media_id,
                    recipient=recipient
                )
                resolved_body = resolve_template_text(
                    template["body"], b.get("variable_mapping") or {}, template.get("samples") or {}, recipient
                )
                local_id = await insert_pending_row(
                    account=acc,
                    to_number=recipient["contact_number"],
                    message_type="template",
                    message_body=resolved_body or f"Template: {template['name']}",
                    template_meta={
                        "header_type": template.get("header_type") or "NONE",
                        "header_text": template.get("header_text"),
                        "header_media_library_id": b.get("media_library_id") or template.get("header_media_library_id"),
                        "footer": template.get("footer"),
                        "buttons": template.get("buttons") or []
                    }
                )
                asyncio.create_task(dispatch_send_task(
                    kind="template",
                    account=acc,
                    to=clean_contact,
                    local_message_id=local_id,
                    payload={
                        "name": template["name"],
                        "languageCode": template.get("language") or "en",
                        "components": components
                    },
                    origin_ref={"kind": "broadcast_log", "id": log_id}
                ))
                enqueued += 1
            else:
                body = (b.get("body") or "").replace("{{contact.name}}", recipient.get("name") or "")
                local_id = await insert_pending_row(
                    account=acc,
                    to_number=recipient["contact_number"],
                    message_type="text",
                    message_body=body
                )
                asyncio.create_task(dispatch_send_task(
                    kind="text",
                    account=acc,
                    to=clean_contact,
                    local_message_id=local_id,
                    payload={"body": body},
                    origin_ref={"kind": "broadcast_log", "id": log_id}
                ))
                enqueued += 1
        except Exception as job_err:
            await db.execute(
                "UPDATE coexistence.broadcast_logs SET status = 'failed', error_message = $1 WHERE id = $2",
                str(job_err)[:500], log_id
            )

    await db.execute("UPDATE coexistence.broadcasts SET status = 'SENT', updated_at = NOW() WHERE id = $1", broadcast_id)
    data = await get_broadcast_with_logs(broadcast_id)
    return {**data, "enqueued": enqueued}
