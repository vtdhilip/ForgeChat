import os
import time
import json
import re
import asyncio
from typing import Optional, Dict, Any, Tuple
from app.core.database import db
from app.services.whatsapp_service import (
    get_account_by_phone_number,
    get_account_with_token,
    get_single_account,
    normalize_phone
)
from app.services.account_health import mark_account_health, classify_meta_error
from app.integrations import meta_client

def local_message_id() -> str:
    now_ms = int(time.time() * 1000)
    rand_hex = os.urandom(6).hex()
    return f"local-{now_ms}-{rand_hex}"

async def resolve_account(
    account_id: Optional[int] = None,
    from_phone_number: Optional[str] = None,
    org_id: Optional[str] = None
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    try:
        acc = None
        if account_id:
            acc = await get_account_with_token(account_id)
        elif from_phone_number:
            acc = await get_account_by_phone_number(from_phone_number, org_id)
        
        if not acc:
            acc = await get_single_account(org_id)

        if not acc:
            return None, f"No WhatsApp Business account registered for {from_phone_number or f'id={account_id}'}"
        if not acc.get("isActive"):
            return None, f"WhatsApp Business account \"{acc.get('displayName')}\" is inactive"
        if not acc.get("accessToken"):
            return None, "Access token missing (re-enter in Settings)"
        
        return acc, None
    except Exception as err:
        return None, str(err)

async def insert_pending_row(
    account: Dict[str, Any],
    to_number: str,
    message_type: str,
    message_body: Optional[str] = None,
    media_url: Optional[str] = None,
    media_mime: Optional[str] = None,
    template_meta: Optional[dict] = None,
    context_message_id: Optional[str] = None
) -> str:
    msg_id = local_message_id()
    raw_payload = json.dumps({"origin": "outbound", "queued_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    t_meta = json.dumps(template_meta) if template_meta else None
    display_phone = normalize_phone(account.get("displayPhoneNumber") or "")
    to_clean = normalize_phone(to_number)

    await db.execute(
        """
        INSERT INTO coexistence.chat_history
          (message_id, phone_number_id, wa_number, contact_number, to_number,
           direction, message_type, message_body, raw_payload,
           media_url, media_mime_type, status, timestamp, template_meta, context_message_id)
        VALUES ($1, $2, $3, $4, $5, 'outgoing', $6, $7, $8, $9, $10, 'sending', NOW(), $11, $12)
        """,
        msg_id,
        account["phoneNumberId"],
        display_phone,
        to_clean,
        to_clean,
        message_type,
        message_body,
        raw_payload,
        media_url,
        media_mime,
        t_meta,
        context_message_id
    )
    return msg_id

async def mark_sent(local_id: str, wamid: str):
    await db.execute(
        """
        UPDATE coexistence.chat_history
        SET message_id = $1, status = 'sent', error_message = NULL
        WHERE message_id = $2
        """,
        wamid, local_id
    )

async def mark_failed(local_id: str, error_message: str):
    await db.execute(
        """
        UPDATE coexistence.chat_history
        SET status = 'failed', error_message = $1
        WHERE message_id = $2
        """,
        (error_message or "send failed")[:500], local_id
    )

async def seconds_since_last_incoming(account_phone_number_id: str, contact_number: str) -> Optional[int]:
    norm = normalize_phone(contact_number)
    val = await db.fetchval(
        """
        SELECT EXTRACT(EPOCH FROM (NOW() - MAX(timestamp))) AS seconds
        FROM coexistence.chat_history
        WHERE phone_number_id = $1
          AND contact_number = $2
          AND direction = 'incoming'
        """,
        account_phone_number_id, norm
    )
    return int(val) if val is not None else None

async def dispatch_send_task(
    kind: str,
    account: Dict[str, Any],
    to: str,
    local_message_id: Optional[str] = None,
    payload: Optional[dict] = None,
    origin_ref: Optional[dict] = None
):
    payload = payload or {}
    token = account["accessToken"]
    phone_id = account["phoneNumberId"]
    clean_to = normalize_phone(to)

    try:
        if kind == "text":
            res = await meta_client.send_text(
                access_token=token,
                phone_number_id=phone_id,
                to=clean_to,
                body=payload.get("body", ""),
                preview_url=payload.get("previewUrl", False),
                context_message_id=payload.get("contextMessageId")
            )
        elif kind == "template":
            res = await meta_client.send_template(
                access_token=token,
                phone_number_id=phone_id,
                to=clean_to,
                template_name=payload.get("name", ""),
                language_code=payload.get("languageCode", "en"),
                components=payload.get("components", [])
            )
        elif kind == "media":
            res = await meta_client.send_media(
                access_token=token,
                phone_number_id=phone_id,
                to=clean_to,
                media_type=payload.get("type", "image"),
                media_id=payload.get("mediaId"),
                link=payload.get("link"),
                caption=payload.get("caption"),
                filename=payload.get("filename"),
                context_message_id=payload.get("contextMessageId")
            )
        elif kind == "reaction":
            res = await meta_client.send_reaction(
                access_token=token,
                phone_number_id=phone_id,
                to=clean_to,
                message_id=payload.get("messageId", ""),
                emoji=payload.get("emoji", "")
            )
        else:
            raise ValueError(f"Unknown send kind: {kind}")

        wamid = None
        messages = res.get("messages", [])
        if messages and len(messages) > 0:
            wamid = messages[0].get("id")

        if not wamid and kind != "reaction":
            raise Exception("Meta returned no message id")

        if local_message_id and wamid:
            await mark_sent(local_message_id, wamid)

        await mark_account_health(account["id"], "healthy")

        if origin_ref and origin_ref.get("kind") == "broadcast_log" and origin_ref.get("id"):
            await db.execute(
                "UPDATE coexistence.broadcast_logs SET status = 'sent', wamid = $1, error_message = NULL WHERE id = $2",
                wamid, origin_ref["id"]
            )
    except Exception as err:
        print(f"[dispatch_send] Failed to send {kind} to {clean_to}: {err}")
        cls = classify_meta_error(err)
        await mark_account_health(account["id"], cls, str(err))
        if local_message_id:
            await mark_failed(local_message_id, str(err))
        if origin_ref and origin_ref.get("kind") == "broadcast_log" and origin_ref.get("id"):
            await db.execute(
                "UPDATE coexistence.broadcast_logs SET status = 'failed', error_message = $1 WHERE id = $2",
                str(err)[:500], origin_ref["id"]
            )
