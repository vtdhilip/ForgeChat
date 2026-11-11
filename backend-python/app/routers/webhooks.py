import os
import json
import asyncio
import hmac
import hashlib
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Request, Response, Query
from app.core.database import db
from app.core.config import settings
from app.core.crypto import decrypt
from app.core.events import bus
from app.services.whatsapp_service import normalize_phone

router = APIRouter(prefix="/api", tags=["Webhooks"])

STATUS_RANK = {
    "sending": 0,
    "sent": 1,
    "delivered": 2,
    "read": 3,
    "played": 3,
    "failed": 2
}

@router.get("/webhook")
@router.get("/webhook/whatsapp")
async def verify_webhook(
    request: Request,
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
):
    if hub_mode == "subscribe" and hub_verify_token:
        # Check env token with default fallback
        expected_token = os.getenv("META_WEBHOOK_VERIFY_TOKEN") or getattr(settings, "META_WEBHOOK_VERIFY_TOKEN", None) or "synapticchat_verify_token"
        if expected_token and hub_verify_token == expected_token:
            return Response(content=hub_challenge or "", media_type="text/plain")

        # Check DB whatsapp accounts
        accounts = await db.fetch("SELECT verify_token_encrypted FROM coexistence.whatsapp_accounts WHERE is_active = true")
        for a in accounts:
            dec = decrypt(a["verify_token_encrypted"])
            if dec and dec == hub_verify_token:
                return Response(content=hub_challenge or "", media_type="text/plain")

    raise HTTPException(status_code=403, detail="Verification failed")

def extract_webhook_phone_number_ids(body: Any) -> List[str]:
    """Collect unique metadata.phone_number_id values from a Meta webhook payload."""
    if not isinstance(body, dict):
        return []
    seen: list[str] = []
    for entry in body.get("entry") or []:
        if not isinstance(entry, dict):
            continue
        for change in entry.get("changes") or []:
            if not isinstance(change, dict):
                continue
            value = change.get("value") or {}
            metadata = value.get("metadata") if isinstance(value, dict) else None
            pid = metadata.get("phone_number_id") if isinstance(metadata, dict) else None
            if pid:
                pid_str = str(pid).strip()
                if pid_str and pid_str not in seen:
                    seen.append(pid_str)
    return seen


def _configured_global_meta_secrets() -> List[str]:
    """Return global Meta App Secrets from env/settings (supports comma-separated lists)."""
    raw_sources = [
        getattr(settings, "META_APP_SECRET", "") or "",
        getattr(settings, "META_APP_SECRETS", "") or "",
        os.getenv("META_APP_SECRETS", "") or "",
    ]
    secrets: list[str] = []
    for src in raw_sources:
        for item in str(src).split(","):
            s = item.strip()
            if s and s not in secrets:
                secrets.append(s)
    return secrets


async def resolve_webhook_secrets(body: Any) -> List[str]:
    """Resolve per-account Meta App Secrets by phone_number_id, falling back to global secrets."""
    phone_number_ids = extract_webhook_phone_number_ids(body)
    if phone_number_ids:
        rows = await db.fetch(
            """
            SELECT meta_app_secret_encrypted
            FROM coexistence.whatsapp_accounts
            WHERE is_active = TRUE
              AND phone_number_id = ANY($1::text[])
              AND meta_app_secret_encrypted IS NOT NULL
            """,
            phone_number_ids,
        )
        per_account: list[str] = []
        for row in rows:
            dec = decrypt(row.get("meta_app_secret_encrypted"))
            if dec and dec not in per_account:
                per_account.append(dec)
        if per_account:
            return per_account
    return _configured_global_meta_secrets()


def verify_meta_signature(
    raw_body: bytes,
    signature_header: Optional[str],
    secrets: Optional[List[str]] = None,
) -> Optional[bool]:
    candidate_secrets = _configured_global_meta_secrets() if secrets is None else [s for s in secrets if s]
    if not candidate_secrets:
        return None
    if not signature_header or not signature_header.startswith("sha256=") or not raw_body:
        return False
    for secret in candidate_secrets:
        expected = "sha256=" + hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
        if hmac.compare_digest(expected, signature_header):
            return True
    return False


@router.post("/webhook")
@router.post("/webhook/whatsapp")
async def process_whatsapp_webhook(request: Request):
    raw_body = await request.body()
    sig_header = request.headers.get("x-hub-signature-256") or request.headers.get("X-Hub-Signature-256")
    valid_json = True
    try:
        body = json.loads(raw_body.decode("utf-8")) if raw_body else {}
    except Exception:
        body = {}
        valid_json = False

    secrets = await resolve_webhook_secrets(body)
    sig = verify_meta_signature(raw_body, sig_header, secrets=secrets)
    if sig is False:
        raise HTTPException(status_code=403, detail="Invalid webhook signature")
    if sig is None:
        pass  # In dev without META_APP_SECRET configured, accept but log in production

    if not valid_json:
        return {"ok": True, "stored": 0}

    if not body or body.get("object") != "whatsapp_business_account":
        return {"ok": True, "stored": 0}

    entries = body.get("entry") or []
    status_updates = []
    incoming_events = []

    async with db.pool.acquire() as conn:
        async with conn.transaction():
            for entry in entries:
                for change in entry.get("changes", []):
                    value = change.get("value") or {}
                    if value.get("messaging_product") != "whatsapp":
                        continue

                    metadata = value.get("metadata") or {}
                    phone_number_id = metadata.get("phone_number_id", "")
                    display_phone = normalize_phone(metadata.get("display_phone_number", ""))

                    # Profile names
                    contact_profiles = {}
                    for c in value.get("contacts", []):
                        wa_id = c.get("wa_id")
                        pname = (c.get("profile") or {}).get("name")
                        if wa_id and pname:
                            contact_profiles[wa_id] = pname

                    # Status receipts
                    for status_obj in value.get("statuses", []):
                        s_status = status_obj.get("status")
                        s_msg_id = status_obj.get("id")
                        s_recipient = normalize_phone(status_obj.get("recipient_id"))
                        new_rank = STATUS_RANK.get(s_status, 0)

                        failed_err = None
                        if s_status == "failed":
                            errs = status_obj.get("errors") or []
                            if errs:
                                e = errs[0]
                                failed_err = f"[{e.get('code')}] {e.get('title') or e.get('message')}"

                        upd = await conn.fetchrow(
                            """
                            UPDATE coexistence.chat_history
                            SET status = $1,
                                error_message = CASE WHEN $1 = 'failed' AND $4::text IS NOT NULL THEN $4 ELSE error_message END
                            WHERE message_id = $2
                              AND $3 > (CASE status
                                          WHEN 'sending' THEN 0 WHEN 'sent' THEN 1 WHEN 'delivered' THEN 2
                                          WHEN 'read' THEN 3 WHEN 'played' THEN 3 WHEN 'failed' THEN 2 ELSE 0 END)
                            RETURNING wa_number, contact_number, message_id
                            """,
                            s_status, s_msg_id, new_rank, failed_err
                        )
                        if upd:
                            status_updates.append({
                                "waNumber": upd["wa_number"],
                                "contactNumber": upd["contact_number"],
                                "messageId": upd["message_id"],
                                "status": s_status
                            })

                    # Incoming messages
                    for msg in value.get("messages", []):
                        m_id = msg.get("id")
                        m_from = normalize_phone(msg.get("from"))
                        m_type = msg.get("type", "unknown")
                        m_timestamp = (
                            datetime.fromtimestamp(int(msg["timestamp"]), timezone.utc)
                            if msg.get("timestamp")
                            else datetime.now(timezone.utc)
                        )
                        context_id = (msg.get("context") or {}).get("id")

                        body_text = None
                        media_url = None
                        media_mime = None

                        if m_type == "text":
                            body_text = (msg.get("text") or {}).get("body")
                        elif m_type in ("image", "video", "audio", "document"):
                            media_data = msg.get(m_type) or {}
                            body_text = media_data.get("caption") or f"{m_type.capitalize()} message"
                            media_url = media_data.get("id")
                            media_mime = media_data.get("mime_type")
                        elif m_type == "reaction":
                            rx = msg.get("reaction") or {}
                            target_id = rx.get("message_id")
                            emoji = rx.get("emoji")
                            if target_id:
                                if emoji:
                                    await conn.execute(
                                        """
                                        INSERT INTO coexistence.message_reactions
                                          (wa_number, contact_number, target_message_id, direction, emoji, reactor, updated_at)
                                        VALUES ($1,$2,$3,'incoming',$4,$5,NOW())
                                        ON CONFLICT (target_message_id, direction)
                                        DO UPDATE SET emoji = EXCLUDED.emoji, reactor = EXCLUDED.reactor, updated_at = NOW()
                                        """,
                                        display_phone, m_from, target_id, emoji, m_from
                                    )
                                else:
                                    await conn.execute(
                                        "DELETE FROM coexistence.message_reactions WHERE target_message_id = $1 AND direction = 'incoming'",
                                        target_id
                                    )
                            continue

                        # Resolve tenant org_id
                        acc_row = await conn.fetchrow(
                            "SELECT org_id FROM coexistence.whatsapp_accounts WHERE phone_number_id = $1 OR display_phone_number = $2 LIMIT 1",
                            phone_number_id, display_phone
                        )
                        org_id = acc_row["org_id"] if acc_row else None

                        await conn.execute(
                            """
                            INSERT INTO coexistence.chat_history
                              (message_id, phone_number_id, wa_number, contact_number, to_number,
                               direction, message_type, message_body, raw_payload, media_url,
                               media_mime_type, status, timestamp, context_message_id, org_id)
                            VALUES ($1,$2,$3,$4,$5,'incoming',$6,$7,$8,$9,$10,'received',$11,$12,$13)
                            ON CONFLICT (message_id) DO UPDATE SET
                              status = EXCLUDED.status,
                              raw_payload = EXCLUDED.raw_payload,
                              org_id = COALESCE(coexistence.chat_history.org_id, EXCLUDED.org_id)
                            """,
                            m_id, phone_number_id, display_phone, m_from, display_phone,
                            m_type, body_text, json.dumps(body), media_url,
                            media_mime, m_timestamp, context_id, org_id
                        )

                        # Trigger Automations & AI Agent routing asynchronously
                        record = {
                            "org_id": str(org_id) if org_id else None,
                            "message_id": m_id,
                            "phone_number_id": phone_number_id,
                            "wa_number": display_phone,
                            "contact_number": m_from,
                            "direction": "incoming",
                            "message_type": m_type,
                            "message_body": body_text,
                            "media_url": media_url,
                            "media_mime_type": media_mime,
                            "timestamp": m_timestamp.isoformat() if m_timestamp else None,
                            "status": "received",
                        }
                        incoming_events.append({
                            "orgId": str(org_id) if org_id else None,
                            "waNumber": display_phone,
                            "contactNumber": m_from,
                            "messageId": m_id,
                        })
                        from app.engine.automation_engine import evaluate_triggers
                        from app.services.agent_router import route_if_active
                        asyncio.create_task(evaluate_triggers(record))
                        asyncio.create_task(route_if_active(record))

                        p_name = contact_profiles.get(msg.get("from"))
                        if p_name:
                            await conn.execute(
                                """
                                INSERT INTO coexistence.contacts (wa_number, contact_number, profile_name, org_id)
                                VALUES ($1, $2, $3, $4)
                                ON CONFLICT (wa_number, contact_number) DO UPDATE SET
                                  profile_name = EXCLUDED.profile_name,
                                  org_id = COALESCE(coexistence.contacts.org_id, EXCLUDED.org_id),
                                  updated_at = NOW()
                                """,
                                display_phone, m_from, p_name, org_id
                            )

    # Emit real-time updates to SSE subscribers
    for ev in incoming_events:
        await bus.emit("new-message", ev)
    for u in status_updates:
        await bus.emit("message-status", u)

    return {"ok": True}

# --- Razorpay Webhook ---

@router.post("/razorpay/webhook")
async def razorpay_webhook(request: Request):
    secret = os.getenv("RAZORPAY_WEBHOOK_SECRET")
    signature = request.headers.get("X-Razorpay-Signature") or request.headers.get("x-razorpay-signature")
    raw_body = await request.body()

    if secret:
        if not signature:
            raise HTTPException(status_code=400, detail="Missing X-Razorpay-Signature header")
        expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise HTTPException(status_code=400, detail="Invalid signature")

    try:
        body = json.loads(raw_body.decode("utf-8")) if raw_body else {}
    except Exception:
        return {"status": "ignored"}

    event = body.get("event")
    if event in ("payment_link.paid", "order.paid", "payment.captured"):
        payload = body.get("payload", {})
        entity = payload.get("payment_link", {}).get("entity") or payload.get("payment", {}).get("entity") or {}
        order_id = entity.get("reference_id") or entity.get("order_id")
        if order_id:
            await db.execute(
                "UPDATE coexistence.orders SET status = 'paid', updated_at = NOW() WHERE order_number = $1 OR id::text = $1",
                str(order_id)
            )

    return {"status": "ok"}

# --- Shiprocket Webhook ---

@router.post("/shiprocket/webhook")
@router.post("/logistics/webhook")
@router.post("/tracking/webhook")
async def shiprocket_webhook(request: Request):
    token_secret = os.getenv("SHIPROCKET_WEBHOOK_TOKEN") or os.getenv("LOGISTICS_WEBHOOK_SECRET")
    if token_secret:
        inbound_token = (
            request.headers.get("x-api-key")
            or request.headers.get("x-shiprocket-token")
            or request.query_params.get("token")
        )
        if not inbound_token or not hmac.compare_digest(token_secret, inbound_token):
            raise HTTPException(status_code=401, detail="Unauthorized logistics webhook")

    try:
        body = await request.json()
    except Exception:
        return {"status": "ignored"}

    order_id = str(body.get("order_id") or body.get("orderId") or body.get("order_number") or "").strip()
    status_str = str(body.get("current_status") or body.get("status") or "").upper().strip()
    courier = str(body.get("courier_name") or body.get("courier") or "").strip()
    awb = str(body.get("awb") or body.get("awb_code") or body.get("tracking_number") or "").strip()

    if order_id or awb:
        await db.execute(
            """
            UPDATE coexistence.orders
            SET status = COALESCE($1, status),
                courier = COALESCE($2, courier),
                tracking_number = COALESCE($3, tracking_number),
                updated_at = NOW()
            WHERE order_number = $4 OR tracking_number = $3
            """,
            status_str or None, courier or None, awb or None, order_id
        )

    return {"status": "ok"}
