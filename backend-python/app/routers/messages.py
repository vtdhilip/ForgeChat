import os
import io
import re
import csv
import time
import json
import asyncio
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Union, Tuple
from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File, Form, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.database import db
from app.middleware.auth import (
    get_current_user,
    is_admin_user,
    assert_wa_access,
    assert_contact_access
)
from app.middleware.tenant import get_tenant_context
from app.services.whatsapp_service import normalize_phone
from app.services.message_sender import (
    resolve_account,
    insert_pending_row,
    seconds_since_last_incoming,
    dispatch_send_task
)

router = APIRouter(prefix="/api", tags=["Messages & Contacts"])

DEFAULT_DATA_WINDOW = "INTERVAL '30 days'"
SERVICE_WINDOW_SECONDS = 24 * 3600
MEDIA_DIR = os.getenv("MEDIA_DIR", "/app/media")

def time_range_to_interval(r: Optional[str]) -> Optional[str]:
    mapping = {
        "6h": "INTERVAL '6 hours'",
        "24h": "INTERVAL '24 hours'",
        "7d": "INTERVAL '7 days'",
        "14d": "INTERVAL '14 days'",
        "30d": "INTERVAL '30 days'",
    }
    return mapping.get(r)

def sanitize_context_id(msg_id: Optional[str]) -> Optional[str]:
    if not msg_id or not isinstance(msg_id, str):
        return None
    if msg_id.startswith("local-") or msg_id.startswith("tmp-"):
        return None
    return msg_id

def persist_outbound_media(account_digits: str, message_id: str, file_bytes: bytes, ext: str) -> Tuple[str, int]:
    now = datetime.now(timezone.utc)
    ym = f"{now.year}{now.month:02d}"
    acc = account_digits or "unknown"
    dir_path = os.path.join(MEDIA_DIR, acc, ym)
    os.makedirs(dir_path, exist_ok=True)
    clean_id = re.sub(r"[^A-Za-z0-9._-]", "_", str(message_id))[:200]
    filename = f"{clean_id}.{ext or 'bin'}"
    abs_path = os.path.join(dir_path, filename)
    with open(abs_path, "wb") as f:
        f.write(file_bytes)
    return abs_path, len(file_bytes)

# --- Schemas ---

class ContactSaveRequest(BaseModel):
    waNumber: str
    contactNumber: str
    name: Optional[str] = None
    tags: Optional[List[str]] = None
    customFields: Optional[Dict[str, Any]] = None
    assignedUserId: Optional[Any] = None

class ChangeNumberRequest(BaseModel):
    waNumber: str
    oldNumber: str
    newNumber: str

class MarkReadRequest(BaseModel):
    waNumber: str
    contactNumber: str

class SendMessageRequest(BaseModel):
    fromNumber: str
    toNumber: str
    text: str
    contextMessageId: Optional[str] = None

class ReactMessageRequest(BaseModel):
    fromNumber: str
    toNumber: str
    messageId: str
    emoji: Optional[str] = ""

class StarMessageRequest(BaseModel):
    waNumber: str
    contactNumber: str
    messageId: str
    starred: bool

# --- Endpoints ---

@router.get("/numbers")
async def get_numbers(user: dict = Depends(get_current_user)):
    is_admin = is_admin_user(user)
    params = []
    extra_filter = ""
    if not is_admin:
        params.append(user["id"])
        extra_filter = f"AND wa_number IN (SELECT DISTINCT wa_number FROM coexistence.contacts WHERE assigned_user_id = ${len(params)})"

    query = f"""
      SELECT
        wa_number,
        MAX(timestamp) AS last_message_time,
        COUNT(*) AS message_count
      FROM coexistence.chat_history
      WHERE timestamp >= NOW() - {DEFAULT_DATA_WINDOW} {extra_filter}
        AND regexp_replace(wa_number, '[^0-9]', '', 'g') IN (
          SELECT regexp_replace(display_phone_number, '[^0-9]', '', 'g')
          FROM coexistence.whatsapp_accounts
          WHERE display_phone_number IS NOT NULL
        )
      GROUP BY wa_number
      ORDER BY last_message_time DESC
    """
    rows = await db.fetch(query, *params)

    # Unread chats
    unread_params = []
    unread_join = ""
    unread_assign = ""
    if not is_admin:
        unread_params.append(user["id"])
        unread_join = "JOIN coexistence.contacts c ON c.wa_number = ch.wa_number AND c.contact_number = ch.contact_number"
        unread_assign = f"AND c.assigned_user_id = ${len(unread_params)}"

    unread_query = f"""
      SELECT ch.wa_number, COUNT(DISTINCT ch.contact_number) AS unread_chats
      FROM coexistence.chat_history ch
      LEFT JOIN coexistence.conversation_reads cr
        ON cr.wa_number = ch.wa_number AND cr.contact_number = ch.contact_number
      {unread_join}
      WHERE ch.direction = 'incoming'
        AND ch.timestamp >= NOW() - {DEFAULT_DATA_WINDOW}
        AND ch.timestamp > COALESCE(cr.last_read_at, 'epoch'::timestamptz)
        {unread_assign}
      GROUP BY ch.wa_number
    """
    unread_rows = await db.fetch(unread_query, *unread_params)
    unread_map = {r["wa_number"]: int(r["unread_chats"]) for r in unread_rows}

    wa_numbers = [r["wa_number"] for r in rows]
    name_map = {}
    team_map = {}
    if wa_numbers:
        norm_wa = [normalize_phone(w) for w in wa_numbers]
        name_rows = await db.fetch(
            """
            SELECT wa_number, COALESCE(name, profile_name) AS name
            FROM coexistence.contacts
            WHERE contact_number = wa_number AND wa_number = ANY($1::text[])
            """,
            wa_numbers
        )
        for r in name_rows:
            name_map[r["wa_number"]] = r["name"]

        team_rows = await db.fetch(
            """
            SELECT name, profile_picture_url,
                   regexp_replace(phone_number, '[^0-9]', '', 'g') AS norm
            FROM coexistence.team_members
            WHERE regexp_replace(phone_number, '[^0-9]', '', 'g') = ANY($1::text[])
            """,
            norm_wa
        )
        for r in team_rows:
            if r["norm"] not in team_map:
                team_map[r["norm"]] = dict(r)

    result = []
    for r in rows:
        norm = normalize_phone(r["wa_number"])
        tm = team_map.get(norm)
        result.append({
            "wa_number": r["wa_number"],
            "last_message_time": r["last_message_time"].isoformat() if r["last_message_time"] else None,
            "message_count": int(r["message_count"]),
            "display_name": (tm.get("name") if tm else None) or name_map.get(r["wa_number"]),
            "profile_picture_url": tm.get("profile_picture_url") if tm else None,
            "unread_chats": unread_map.get(r["wa_number"], 0)
        })
    return result

@router.get("/contacts")
async def get_contacts(
    waNumber: str = Query(...),
    timeRange: Optional[str] = "24h",
    user: dict = Depends(get_current_user)
):
    await assert_wa_access(user, waNumber)
    interval = time_range_to_interval(timeRange)
    time_filter = f"AND timestamp >= NOW() - {interval}" if interval else f"AND timestamp >= NOW() - {DEFAULT_DATA_WINDOW}"

    params = [waNumber]
    join_kind = "LEFT JOIN"
    assign_filter = ""
    if not is_admin_user(user):
        join_kind = "INNER JOIN"
        params.append(user["id"])
        assign_filter = f"AND c.assigned_user_id = ${len(params)}"

    query = f"""
      SELECT
        ch.contact_number,
        MAX(ch.timestamp) AS last_message_time,
        COUNT(*) AS message_count,
        COUNT(*) FILTER (
          WHERE ch.direction = 'incoming'
            AND ch.timestamp > COALESCE(cr.last_read_at, 'epoch'::timestamptz)
        ) AS unread_count,
        (SELECT CASE
                  WHEN NULLIF(ch2.message_body, '') IS NOT NULL THEN ch2.message_body
                  WHEN ch2.message_type IN ('audio','voice') THEN '🎵 Audio'
                  WHEN ch2.message_type = 'image'   THEN '📷 Photo'
                  WHEN ch2.message_type = 'video'   THEN '🎥 Video'
                  WHEN ch2.message_type = 'document' THEN '📄 Document'
                  WHEN ch2.message_type = 'location' THEN '📍 Location'
                  WHEN ch2.message_type = 'contacts' THEN '👤 Contact'
                  WHEN ch2.message_type = 'sticker'  THEN 'Sticker'
                  WHEN ch2.message_type = 'template' THEN 'Template message'
                  WHEN ch2.message_type = 'interactive' THEN 'Interactive message'
                  WHEN ch2.message_type IN ('unsupported','unknown') THEN 'Unsupported message'
                  ELSE NULL
                END
         FROM coexistence.chat_history ch2
         WHERE ch2.wa_number = $1 AND ch2.contact_number = ch.contact_number
           AND ch2.message_type NOT IN ('reaction','status')
         ORDER BY ch2.timestamp DESC LIMIT 1) AS last_message,
        COALESCE(c.name, c.profile_name) AS name,
        c.tags,
        c.assigned_user_id,
        u.display_name AS assigned_user_name,
        u.role        AS assigned_user_role
      FROM coexistence.chat_history ch
      {join_kind} coexistence.contacts c
        ON c.wa_number = ch.wa_number AND c.contact_number = ch.contact_number
      LEFT JOIN coexistence.forgecrm_users u ON u.id = c.assigned_user_id
      LEFT JOIN coexistence.conversation_reads cr
        ON cr.wa_number = ch.wa_number AND cr.contact_number = ch.contact_number
      WHERE ch.wa_number = $1 {time_filter} {assign_filter}
      GROUP BY ch.contact_number, c.name, c.profile_name, c.tags, c.assigned_user_id, u.display_name, u.role, cr.last_read_at
      ORDER BY last_message_time DESC
    """
    rows = await db.fetch(query, *params)
    out = []
    for r in rows:
        tags = r["tags"] if r["tags"] is not None else []
        if isinstance(tags, str):
            try:
                tags = json.loads(tags)
            except Exception:
                tags = []
        out.append({
            "contact_number": r["contact_number"],
            "last_message_time": r["last_message_time"].isoformat() if r["last_message_time"] else None,
            "message_count": int(r["message_count"]),
            "unread_count": int(r["unread_count"]),
            "last_message": r["last_message"],
            "name": r["name"],
            "tags": tags,
            "assigned_user_id": r["assigned_user_id"],
            "assigned_user_name": r["assigned_user_name"],
            "assigned_user_role": r["assigned_user_role"]
        })
    return out

@router.post("/contacts/save")
async def save_contact(payload: ContactSaveRequest, user: dict = Depends(get_current_user)):
    wa_number = payload.waNumber.strip()
    contact_number = payload.contactNumber.strip()
    if not wa_number or not contact_number:
        raise HTTPException(status_code=400, detail="waNumber and contactNumber required")

    if payload.name and len(payload.name) > 255:
        raise HTTPException(status_code=400, detail="Name too long (max 255 characters)")

    is_admin = is_admin_user(user)
    if not is_admin:
        await assert_contact_access(user, wa_number, contact_number)

    clean_name = payload.name.strip() if payload.name and payload.name.strip() else None
    tags_json = json.dumps(payload.tags or [])
    cf_json = json.dumps(payload.customFields) if payload.customFields is not None else None

    set_assign = False
    assign_val = None
    if not is_admin:
        set_assign = True
        assign_val = user["id"]
    elif payload.assignedUserId is not None:
        set_assign = True
        assign_val = int(payload.assignedUserId) if str(payload.assignedUserId).strip() else None

    await db.execute(
        """
        INSERT INTO coexistence.contacts
          (wa_number, contact_number, name, tags, custom_fields, assigned_user_id, updated_at)
        VALUES ($1, $2, $3, $4, COALESCE($5::jsonb, '{}'::jsonb), $6, NOW())
        ON CONFLICT (wa_number, contact_number)
        DO UPDATE SET
          name = COALESCE(EXCLUDED.name, coexistence.contacts.name),
          tags = EXCLUDED.tags,
          custom_fields = COALESCE($5::jsonb, coexistence.contacts.custom_fields),
          assigned_user_id = CASE WHEN $7::boolean THEN $6 ELSE coexistence.contacts.assigned_user_id END,
          updated_at = NOW()
        """,
        wa_number, contact_number, clean_name, tags_json, cf_json, assign_val, set_assign
    )
    return {"ok": True}

@router.get("/contacts/import/template")
async def get_import_template():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Name", "Phone Number"])
    writer.writerow(["John Doe", "919876543210"])
    csv_bytes = output.getvalue().encode("utf-8")
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="contacts-import-template.csv"'}
    )

@router.post("/contacts/import")
async def import_contacts(
    waNumber: str = Form(...),
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user)
):
    clean_wa = normalize_phone(waNumber)
    if not clean_wa:
        raise HTTPException(status_code=400, detail="waNumber required")

    is_admin = is_admin_user(user)
    if not is_admin:
        await assert_wa_access(user, clean_wa)

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="The sheet has no data rows.")

    rows = []
    fname = (file.filename or "").lower()
    if fname.endswith(".csv"):
        text = contents.decode("utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        for r in reader:
            rows.append(r)
    else:
        try:
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(contents), data_only=True)
            sheet = wb.active
            headers = None
            for row in sheet.iter_rows(values_only=True):
                if not headers:
                    headers = [str(c or "").strip() for c in row]
                    continue
                row_dict = {}
                for h, val in zip(headers, row):
                    if h:
                        row_dict[h] = str(val or "").strip()
                if any(row_dict.values()):
                    rows.append(row_dict)
        except Exception:
            raise HTTPException(status_code=400, detail="Could not read the file. Upload a valid .csv or .xlsx sheet.")

    if not rows:
        raise HTTPException(status_code=400, detail="The sheet has no data rows.")

    imported = 0
    updated = 0
    skipped = []
    seen = set()

    for idx, r in enumerate(rows):
        row_num = idx + 2
        name = ""
        phone = ""
        for k, v in r.items():
            norm_k = re.sub(r"[^a-z0-9]", "", k.lower())
            if norm_k in {"name", "fullname", "contactname", "customername"}:
                name = str(v or "").strip()
            if norm_k in {"phone", "phonenumber", "phoneno", "mobile", "mobilenumber", "mobileno", "whatsapp", "whatsappnumber", "contactnumber", "number", "msisdn"}:
                phone = normalize_phone(v)

        if not phone:
            skipped.append({"row": row_num, "reason": "Missing phone number"})
            continue
        if len(phone) < 7:
            skipped.append({"row": row_num, "reason": f"Invalid phone {phone}"})
            continue
        if not name:
            skipped.append({"row": row_num, "reason": "Missing name"})
            continue
        if phone in seen:
            skipped.append({"row": row_num, "reason": "Duplicate phone in sheet"})
            continue
        seen.add(phone)

        if is_admin:
            res = await db.fetchrow(
                """
                INSERT INTO coexistence.contacts (wa_number, contact_number, name, tags, custom_fields, updated_at)
                VALUES ($1, $2, $3, '[]'::jsonb, '{}'::jsonb, NOW())
                ON CONFLICT (wa_number, contact_number)
                DO UPDATE SET name = COALESCE(EXCLUDED.name, coexistence.contacts.name), updated_at = NOW()
                RETURNING (xmax = 0) AS inserted
                """,
                clean_wa, phone, name
            )
        else:
            res = await db.fetchrow(
                """
                INSERT INTO coexistence.contacts (wa_number, contact_number, name, tags, custom_fields, assigned_user_id, updated_at)
                VALUES ($1, $2, $3, '[]'::jsonb, '{}'::jsonb, $4, NOW())
                ON CONFLICT (wa_number, contact_number)
                DO UPDATE SET name = COALESCE(EXCLUDED.name, coexistence.contacts.name),
                              assigned_user_id = COALESCE(coexistence.contacts.assigned_user_id, EXCLUDED.assigned_user_id),
                              updated_at = NOW()
                RETURNING (xmax = 0) AS inserted
                """,
                clean_wa, phone, name, user["id"]
            )
        if res and res.get("inserted"):
            imported += 1
        else:
            updated += 1

    return {"ok": True, "imported": imported, "updated": updated, "skipped": skipped, "total": len(rows)}

@router.post("/contacts/change-number")
async def change_number(payload: ChangeNumberRequest, user: dict = Depends(get_current_user)):
    wa_number = normalize_phone(payload.waNumber)
    old_number = normalize_phone(payload.oldNumber)
    new_number = normalize_phone(payload.newNumber)

    if not wa_number or not old_number or not new_number:
        raise HTTPException(status_code=400, detail="waNumber, oldNumber and newNumber required")
    if len(new_number) < 7:
        raise HTTPException(status_code=400, detail="Enter a valid phone number (digits only, at least 7 digits)")

    await assert_contact_access(user, wa_number, old_number)

    if new_number == old_number:
        return {"ok": True, "contactNumber": new_number, "unchanged": True}

    async with db.pool.acquire() as conn:
        async with conn.transaction():
            src = await conn.fetchval(
                "SELECT 1 FROM coexistence.contacts WHERE wa_number = $1 AND contact_number = $2",
                wa_number, old_number
            )
            if not src:
                raise HTTPException(status_code=404, detail="Contact not found")

            clash = await conn.fetchval(
                "SELECT 1 FROM coexistence.contacts WHERE wa_number = $1 AND contact_number = $2",
                wa_number, new_number
            )
            if clash:
                raise HTTPException(status_code=409, detail="A contact with that number already exists for this WhatsApp number")

            await conn.execute("UPDATE coexistence.contacts SET contact_number = $3, updated_at = NOW() WHERE wa_number = $1 AND contact_number = $2", wa_number, old_number, new_number)
            await conn.execute("UPDATE coexistence.chat_history SET contact_number = $3 WHERE wa_number = $1 AND contact_number = $2", wa_number, old_number, new_number)
            await conn.execute("UPDATE coexistence.conversation_reads SET contact_number = $3 WHERE wa_number = $1 AND contact_number = $2", wa_number, old_number, new_number)
            await conn.execute("UPDATE coexistence.message_reactions SET contact_number = $3 WHERE wa_number = $1 AND contact_number = $2", wa_number, old_number, new_number)
            await conn.execute("UPDATE coexistence.automation_executions SET contact_number = $3 WHERE wa_number = $1 AND contact_number = $2", wa_number, old_number, new_number)
            await conn.execute("UPDATE coexistence.deals SET contact_number = $3 WHERE contact_wa_number = $1 AND contact_number = $2", wa_number, old_number, new_number)

    return {"ok": True, "contactNumber": new_number}

@router.delete("/contact")
async def delete_contact(
    waNumber: str = Query(...),
    contactNumber: str = Query(...),
    user: dict = Depends(get_current_user)
):
    await assert_contact_access(user, waNumber, contactNumber)
    result = await db.execute(
        "DELETE FROM coexistence.contacts WHERE wa_number = $1 AND contact_number = $2",
        waNumber, contactNumber
    )
    return {"ok": True}

@router.get("/saved-contacts")
async def get_saved_contacts(waNumber: str = Query(...), user: dict = Depends(get_current_user)):
    await assert_wa_access(user, waNumber)
    params = [waNumber]
    assign_filter = ""
    if not is_admin_user(user):
        params.append(user["id"])
        assign_filter = f"AND c.assigned_user_id = ${len(params)}"

    query = f"""
      SELECT c.contact_number, COALESCE(c.name, c.profile_name) AS name, c.tags, c.custom_fields, c.created_at, c.updated_at,
             c.assigned_user_id, u.display_name AS assigned_user_name, u.role AS assigned_user_role
      FROM coexistence.contacts c
      LEFT JOIN coexistence.forgecrm_users u ON u.id = c.assigned_user_id
      WHERE c.wa_number = $1 AND COALESCE(c.name, c.profile_name) IS NOT NULL AND COALESCE(c.name, c.profile_name) <> '' {assign_filter}
      ORDER BY COALESCE(c.name, c.profile_name) ASC
    """
    rows = await db.fetch(query, *params)
    out = []
    for r in rows:
        tags = r["tags"] if r["tags"] is not None else []
        if isinstance(tags, str):
            try:
                tags = json.loads(tags)
            except Exception:
                tags = []
        out.append({
            "contact_number": r["contact_number"],
            "name": r["name"],
            "tags": tags,
            "custom_fields": r["custom_fields"],
            "created_at": r["created_at"].isoformat() if r.get("created_at") else None,
            "updated_at": r["updated_at"].isoformat() if r.get("updated_at") else None,
            "assigned_user_id": r["assigned_user_id"],
            "assigned_user_name": r["assigned_user_name"],
            "assigned_user_role": r["assigned_user_role"]
        })
    return out

@router.get("/contact")
async def get_single_contact(
    waNumber: str = Query(...),
    contactNumber: str = Query(...),
    user: dict = Depends(get_current_user)
):
    await assert_contact_access(user, waNumber, contactNumber)
    row = await db.fetchrow(
        """
        SELECT c.contact_number, COALESCE(c.name, c.profile_name) AS name, c.tags, c.custom_fields, c.created_at, c.updated_at,
               c.assigned_user_id,
               u.display_name AS assigned_user_name,
               u.role AS assigned_user_role
        FROM coexistence.contacts c
        LEFT JOIN coexistence.forgecrm_users u ON u.id = c.assigned_user_id
        WHERE c.wa_number = $1 AND c.contact_number = $2
        LIMIT 1
        """,
        waNumber, contactNumber
    )
    if not row:
        return {"contact_number": contactNumber, "name": None, "tags": []}

    d = dict(row)
    tags = d.get("tags") or []
    if isinstance(tags, str):
        try:
            tags = json.loads(tags)
        except Exception:
            tags = []
    d["tags"] = tags
    if d.get("created_at"):
        d["created_at"] = d["created_at"].isoformat()
    if d.get("updated_at"):
        d["updated_at"] = d["updated_at"].isoformat()
    return d

@router.post("/messages/mark-read")
async def mark_read(payload: MarkReadRequest, user: dict = Depends(get_current_user)):
    await assert_contact_access(user, payload.waNumber, payload.contactNumber)
    await db.execute(
        """
        INSERT INTO coexistence.conversation_reads (wa_number, contact_number, last_read_at)
        VALUES ($1, $2, NOW())
        ON CONFLICT (wa_number, contact_number)
        DO UPDATE SET last_read_at = NOW()
        """,
        payload.waNumber, payload.contactNumber
    )
    return {"ok": True}

@router.get("/messages")
async def get_messages(
    waNumber: str = Query(...),
    contactNumber: str = Query(...),
    page: int = Query(1),
    limit: int = Query(50),
    search: Optional[str] = "",
    direction: Optional[str] = "all",
    user: dict = Depends(get_current_user)
):
    await assert_contact_access(user, waNumber, contactNumber)
    page_num = max(1, page)
    limit_num = min(200, max(1, limit))
    offset = (page_num - 1) * limit_num

    params = [waNumber, contactNumber]
    conditions = [
        "wa_number = $1",
        "contact_number = $2",
        f"timestamp >= NOW() - {DEFAULT_DATA_WINDOW}",
        "message_type <> 'status'"
    ]

    trimmed_search = (search or "").strip()[:200]
    if trimmed_search:
        params.append(f"%{trimmed_search}%")
        conditions.append(f"COALESCE(message_body, '') ILIKE ${len(params)}")

    if direction == "incoming":
        params.append("incoming")
        conditions.append(f"direction = ${len(params)}")
    elif direction == "outgoing":
        params.append("outgoing")
        conditions.append(f"direction = ${len(params)}")

    where_clause = " AND ".join(conditions)
    total = await db.fetchval(f"SELECT COUNT(*)::int FROM coexistence.chat_history WHERE {where_clause}", *params)

    params.extend([limit_num, offset])
    query = f"""
      SELECT * FROM coexistence.chat_history
      WHERE {where_clause}
      ORDER BY timestamp DESC
      LIMIT ${len(params) - 1} OFFSET ${len(params)}
    """
    rows = await db.fetch(query, *params)

    ids = [r["message_id"] for r in rows if r["message_id"]]
    rx_map = {}
    if ids:
        rx_rows = await db.fetch(
            "SELECT target_message_id, direction, emoji FROM coexistence.message_reactions WHERE target_message_id = ANY($1::text[])",
            ids
        )
        for rx in rx_rows:
            rx_map.setdefault(rx["target_message_id"], []).append({
                "emoji": rx["emoji"],
                "direction": rx["direction"]
            })

    shaped = []
    for r in rows:
        d = dict(r)
        d.pop("raw_payload", None)
        d["reactions"] = rx_map.get(d.get("message_id"), [])
        if d.get("timestamp"):
            d["timestamp"] = d["timestamp"].isoformat()
        if d.get("media_downloaded_at"):
            d["media_downloaded_at"] = d["media_downloaded_at"].isoformat()
        shaped.append(d)

    shaped.reverse()
    return {
        "messages": shaped,
        "total": total or 0,
        "page": page_num,
        "totalPages": (total + limit_num - 1) // limit_num if total else 0
    }

@router.get("/contact-names")
async def get_contact_names(waNumber: str = Query(...), user: dict = Depends(get_current_user)):
    await assert_wa_access(user, waNumber)
    params = [waNumber]
    assign_filter = ""
    if not is_admin_user(user):
        params.append(user["id"])
        assign_filter = f"AND assigned_user_id = ${len(params)}"

    rows = await db.fetch(
        f"SELECT contact_number, COALESCE(name, profile_name) AS name FROM coexistence.contacts WHERE wa_number = $1 {assign_filter}",
        *params
    )
    return {r["contact_number"]: r["name"] for r in rows}

@router.get("/messages/window-status")
async def get_window_status(
    waNumber: str = Query(...),
    contactNumber: str = Query(...),
    user: dict = Depends(get_current_user)
):
    acc, err = await resolve_account(from_phone_number=waNumber)
    if err or not acc:
        return {"canSendFreeForm": False, "reason": err, "windowSeconds": SERVICE_WINDOW_SECONDS}

    secs = await seconds_since_last_incoming(acc["phoneNumberId"], contactNumber)
    return {
        "canSendFreeForm": secs is not None and secs <= SERVICE_WINDOW_SECONDS,
        "lastIncomingSecondsAgo": secs,
        "windowSeconds": SERVICE_WINDOW_SECONDS,
        "accountId": acc["id"],
        "accountName": acc["displayName"]
    }

@router.post("/messages/react")
async def react_message(payload: ReactMessageRequest, user: dict = Depends(get_current_user)):
    from_num = payload.fromNumber.strip()
    to_num = payload.toNumber.strip()
    msg_id = payload.messageId.strip()
    emoji = (payload.emoji or "").strip()

    await assert_contact_access(user, from_num, to_num)
    acc, err = await resolve_account(from_phone_number=from_num)
    if err or not acc:
        raise HTTPException(status_code=409, detail=err or "Account not found")

    secs = await seconds_since_last_incoming(acc["phoneNumberId"], to_num)
    if secs is None or secs > SERVICE_WINDOW_SECONDS:
        raise HTTPException(status_code=409, detail="Outside 24-hour customer service window.")

    clean_wa = normalize_phone(from_num)
    clean_to = normalize_phone(to_num)

    if emoji:
        await db.execute(
            """
            INSERT INTO coexistence.message_reactions
              (wa_number, contact_number, target_message_id, direction, emoji, updated_at)
            VALUES ($1, $2, $3, 'outgoing', $4, NOW())
            ON CONFLICT (target_message_id, direction)
            DO UPDATE SET emoji = EXCLUDED.emoji, updated_at = NOW()
            """,
            clean_wa, clean_to, msg_id, emoji
        )
    else:
        await db.execute(
            """
            DELETE FROM coexistence.message_reactions
            WHERE target_message_id = $1 AND direction = 'outgoing'
              AND wa_number = $2 AND contact_number = $3
            """,
            msg_id, clean_wa, clean_to
        )

    asyncio.create_task(dispatch_send_task(
        kind="reaction",
        account=acc,
        to=clean_to,
        payload={"messageId": msg_id, "emoji": emoji}
    ))

    return {"ok": True, "messageId": msg_id, "emoji": emoji, "direction": "outgoing"}

@router.post("/messages/star")
async def star_message(payload: StarMessageRequest, user: dict = Depends(get_current_user)):
    await assert_contact_access(user, payload.waNumber, payload.contactNumber)
    clean_wa = normalize_phone(payload.waNumber)
    clean_to = normalize_phone(payload.contactNumber)

    res = await db.execute(
        """
        UPDATE coexistence.chat_history SET starred = $1
        WHERE message_id = $2 AND wa_number = $3 AND contact_number = $4
        """,
        bool(payload.starred), payload.messageId, clean_wa, clean_to
    )
    if res.endswith(" 0"):
        raise HTTPException(status_code=404, detail="Message not found")
    return {"ok": True, "messageId": payload.messageId, "starred": bool(payload.starred)}

@router.post("/messages/send", status_code=202)
async def send_message(payload: SendMessageRequest, user: dict = Depends(get_current_user)):
    from_num = payload.fromNumber.strip()
    to_num = payload.toNumber.strip()
    text = payload.text.strip()

    if not from_num or not to_num or not text:
        raise HTTPException(status_code=400, detail="fromNumber, toNumber, text required")
    if len(text) > 4096:
        raise HTTPException(status_code=400, detail="Message too long (max 4096 characters)")

    await assert_contact_access(user, from_num, to_num)
    acc, err = await resolve_account(from_phone_number=from_num)
    if err or not acc:
        raise HTTPException(status_code=400, detail=err or "Account lookup failed")

    secs = await seconds_since_last_incoming(acc["phoneNumberId"], to_num)
    if secs is None or secs > SERVICE_WINDOW_SECONDS:
        raise HTTPException(
            status_code=409,
            detail="Outside 24-hour customer service window. Send an approved template instead."
        )

    ctx_id = sanitize_context_id(payload.contextMessageId)
    local_id = await insert_pending_row(
        account=acc,
        to_number=to_num,
        message_type="text",
        message_body=text,
        context_message_id=ctx_id
    )

    has_link = bool(re.search(r"https?://\S+", text, re.IGNORECASE))
    asyncio.create_task(dispatch_send_task(
        kind="text",
        account=acc,
        to=to_num,
        local_message_id=local_id,
        payload={"body": text, "previewUrl": has_link, "contextMessageId": ctx_id}
    ))

    return {"ok": True, "messageId": local_id, "status": "sending"}

@router.post("/messages/send-media", status_code=202)
async def send_media_msg(
    fromNumber: str = Form(...),
    toNumber: str = Form(...),
    caption: Optional[str] = Form(""),
    contextMessageId: Optional[str] = Form(None),
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user)
):
    await assert_contact_access(user, fromNumber, toNumber)
    acc, err = await resolve_account(from_phone_number=fromNumber)
    if err or not acc:
        raise HTTPException(status_code=400, detail=err or "Account not found")

    secs = await seconds_since_last_incoming(acc["phoneNumberId"], toNumber)
    if secs is None or secs > SERVICE_WINDOW_SECONDS:
        raise HTTPException(status_code=409, detail="Outside 24-hour customer service window.")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="file required")

    mime = file.content_type or "application/octet-stream"
    kind = "document"
    if mime.startswith("image/"):
        kind = "image"
    elif mime.startswith("video/"):
        kind = "video"
    elif mime.startswith("audio/"):
        kind = "audio"

    from app.integrations.meta_client import upload_media
    try:
        media_id = await upload_media(
            access_token=acc["accessToken"],
            phone_number_id=acc["phoneNumberId"],
            file_bytes=file_bytes,
            mime_type=mime,
            filename=file.filename
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Meta upload error: {e}")

    ctx_id = sanitize_context_id(contextMessageId)
    local_id = await insert_pending_row(
        account=acc,
        to_number=toNumber,
        message_type=kind,
        message_body=caption or file.filename,
        media_mime=mime,
        context_message_id=ctx_id
    )

    ext = (file.filename or "").split(".")[-1].lower() if "." in (file.filename or "") else "bin"
    abs_path, size = persist_outbound_media(
        account_digits=normalize_phone(acc.get("displayPhoneNumber")),
        message_id=local_id,
        file_bytes=file_bytes,
        ext=ext
    )

    await db.execute(
        """
        UPDATE coexistence.chat_history
        SET media_storage_path = $1, media_status = 'stored',
            media_size_bytes = $2, media_filename = $3,
            media_downloaded_at = NOW()
        WHERE message_id = $4
        """,
        abs_path, size, file.filename, local_id
    )

    asyncio.create_task(dispatch_send_task(
        kind="media",
        account=acc,
        to=toNumber,
        local_message_id=local_id,
        payload={
            "type": kind,
            "mediaId": media_id,
            "caption": caption or None,
            "filename": file.filename if kind == "document" else None,
            "contextMessageId": ctx_id
        }
    ))

    return {"ok": True, "messageId": local_id, "status": "sending", "mediaId": media_id}
