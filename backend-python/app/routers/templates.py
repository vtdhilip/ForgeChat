import re
import json
import httpx
import time
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File, Form, Request
from pydantic import BaseModel

from app.core.database import db
from app.middleware.auth import get_current_user, require_permission
from app.middleware.tenant import get_tenant_context
from app.services.whatsapp_service import get_account_with_token
from app.services.account_health import mark_account_health
from app.integrations import meta_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/templates", tags=["Templates"])

def extract_vars(t: Optional[str]) -> List[str]:
    if not t:
        return []
    matches = re.findall(r"\{\{(\d+)\}\}", t)
    seen = set()
    res = []
    for m in matches:
        if m not in seen:
            seen.add(m)
            res.append(m)
    res.sort(key=lambda x: int(x))
    return res

def name_ok(n: str) -> bool:
    return bool(re.match(r"^[a-z0-9_]+$", n))

def run_validation(data: dict) -> Dict[str, str]:
    e = {}
    name = data.get("name")
    body = data.get("body")
    header_type = data.get("header_type")
    header_text = data.get("header_text")
    media_handle = data.get("media_handle")
    footer = data.get("footer")
    buttons = data.get("buttons") or []
    samples = data.get("samples") or {}
    category = data.get("category")
    code_expiry = data.get("code_expiry_minutes")

    if not name or not name.strip():
        e["name"] = "Template name is required"
    elif not name_ok(name):
        e["name"] = "Only lowercase letters, numbers, underscores"
    elif len(name) > 512:
        e["name"] = "Max 512 characters"

    if not body or not body.strip():
        e["body"] = "Body text is required"

    hv = extract_vars(header_text) if header_type == "TEXT" else []
    if len(hv) > 1:
        e["headerVars"] = "Header allows only 1 variable — {{1}}"
    if header_text and len(header_text) > 60:
        e["headerTextLen"] = "Header text max 60 characters"

    if header_type in ("IMAGE", "VIDEO", "DOCUMENT") and not (media_handle or "").strip():
        e["mediaHandle"] = "Meta file handle required for media header"

    if extract_vars(footer):
        e["footer"] = "Footer cannot contain variables"
    if footer and len(footer) > 60:
        e["footerLen"] = "Footer max 60 characters"

    bv = extract_vars(body)
    miss = [v for v in bv if not (samples.get(v) or "").strip()]
    if miss:
        e["bodySamples"] = f"Fill samples for: {', '.join(f'{{{{{v}}}}}' for v in miss)}"
    if hv and not (samples.get(hv[0]) or "").strip():
        e["headerSamples"] = f"Fill sample for header {{{{{hv[0]}}}}}"

    url_btns = [b for b in buttons if b.get("type") == "URL"]
    phone_btns = [b for b in buttons if b.get("type") == "PHONE_NUMBER"]
    if len(url_btns) > 2:
        e["btnMaxUrl"] = "Max 2 URL buttons"
    if len(phone_btns) > 1:
        e["btnMaxPhone"] = "Max 1 phone button"

    for i, btn in enumerate(buttons):
        if not (btn.get("text") or "").strip() and btn.get("type") != "OTP":
            e[f"btn_text_{i}"] = "Button text required"
        if btn.get("type") == "URL":
            val = btn.get("value") or ""
            if val and not val.startswith("https://"):
                e[f"btn_url_{i}"] = "URL must start with https://"
            if extract_vars(val) and not (btn.get("urlSample") or "").strip():
                e[f"btn_urlsample_{i}"] = "Sample URL required for dynamic URL variable"
        if btn.get("type") == "PHONE_NUMBER" and btn.get("value"):
            clean = re.sub(r"[\s\-()]", "", btn.get("value") or "")
            if not re.match(r"^\+\d{7,15}$", clean):
                e[f"btn_phone_{i}"] = "Use E.164 format: +919876543210"

    if category == "AUTHENTICATION" and code_expiry is not None and str(code_expiry).strip():
        try:
            n = int(code_expiry)
            if n < 1 or n > 90:
                e["codeExpiry"] = "Expiry must be 1–90 minutes"
        except ValueError:
            e["codeExpiry"] = "Expiry must be 1–90 minutes"

    return e

def build_payload(data: dict) -> dict:
    name = data.get("name")
    category = data.get("category")
    language = data.get("language")
    header_type = data.get("header_type") or "NONE"
    header_text = data.get("header_text")
    media_handle = data.get("media_handle")
    body = data.get("body")
    footer = data.get("footer")
    buttons = data.get("buttons") or []
    samples = data.get("samples") or {}
    security_rec = data.get("security_recommendation")
    code_expiry = data.get("code_expiry_minutes")
    allow_cat_change = data.get("allow_category_change")

    components = []

    if header_type != "NONE":
        hc = {"type": "HEADER", "format": header_type}
        if header_type == "TEXT":
            hc["text"] = header_text
            hv = extract_vars(header_text)
            if hv:
                hc["example"] = {"header_text": [samples.get(hv[0]) or "Sample"]}
        else:
            if media_handle:
                hc["example"] = {"header_handle": [media_handle]}
        components.push(hc) if hasattr(components, 'push') else components.append(hc)

    bc = {"type": "BODY", "text": body}
    if security_rec and category == "AUTHENTICATION":
        bc["add_security_recommendation"] = True
    bv = extract_vars(body)
    if bv:
        bc["example"] = {"body_text": [[samples.get(v) or f"sample_{v}" for v in bv]]}
    components.append(bc)

    if category != "AUTHENTICATION" and footer:
        components.append({"type": "FOOTER", "text": footer})
    if category == "AUTHENTICATION" and code_expiry:
        components.append({"type": "FOOTER", "code_expiration_minutes": int(code_expiry)})

    if buttons:
        btns = []
        for b in buttons:
            b_type = b.get("type")
            if b_type == "OTP":
                item = {
                    "type": "OTP",
                    "otp_type": b.get("otpType") or "COPY_CODE",
                    "text": b.get("text") or "Copy Code"
                }
                if b.get("otpType") == "ONE_TAP":
                    item["autofill_text"] = "Autofill"
                    item["package_name"] = b.get("packageName") or ""
                    item["signature_hash"] = b.get("signatureHash") or ""
                btns.append(item)
            elif b_type == "URL":
                item = {"type": "URL", "text": b.get("text"), "url": b.get("value")}
                if extract_vars(b.get("value")):
                    item["example"] = [b.get("urlSample") or b.get("value")]
                btns.append(item)
            elif b_type == "PHONE_NUMBER":
                btns.append({"type": "PHONE_NUMBER", "text": b.get("text"), "phone_number": b.get("value")})
            elif b_type == "COPY_CODE":
                btns.append({"type": "COPY_CODE", "example": [b.get("value") or "PROMO50"]})
            else:
                btns.append({"type": "QUICK_REPLY", "text": b.get("text")})
        components.append({"type": "BUTTONS", "buttons": btns})

    return {
        "name": name,
        "language": language,
        "category": category,
        "allow_category_change": allow_cat_change,
        "components": components
    }

def shape_template(r: dict) -> dict:
    d = dict(r)
    for dt_col in ("created_at", "updated_at", "submitted_at", "last_synced_at"):
        if d.get(dt_col):
            d[dt_col] = d[dt_col].isoformat()
    return d

def map_meta_status(status: Optional[str]) -> str:
    s = (status or "PENDING").upper()
    if s == "APPROVED":
        return "APPROVED"
    if s == "REJECTED":
        return "REJECTED"
    if s in ("PAUSED", "DISABLED", "DRAFT"):
        return s
    return "SUBMITTED"

@router.get("")
async def list_templates(
    accountId: Optional[str] = None,
    status: Optional[str] = None,
    q: Optional[str] = None,
    tenant_ctx: dict = Depends(get_tenant_context)
):
    org_id = tenant_ctx.get("org_id")
    where = []
    params = []

    if org_id:
        params.append(org_id)
        where.append(f"(t.org_id = ${len(params)}::uuid OR wa.org_id = ${len(params)}::uuid)")

    if accountId == "unassigned":
        where.append("t.whatsapp_account_id IS NULL")
    elif accountId:
        params.append(int(accountId))
        where.append(f"t.whatsapp_account_id = ${len(params)}")

    if status and status != "all":
        params.append(status)
        where.append(f"t.status = ${len(params)}")

    if q and q.strip():
        params.append(f"%{q.strip().lower()}%")
        where.append(f"(lower(t.name) LIKE ${len(params)} OR lower(t.body) LIKE ${len(params)})")

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    query = f"""
      SELECT t.id, t.name, t.category, t.language, t.header_type, t.header_text, t.media_handle,
             t.header_media_library_id, t.body, t.footer,
             t.buttons, t.samples, t.security_recommendation, t.code_expiry_minutes,
             t.allow_category_change, t.status, t.meta_template_id, t.submitted_at,
             t.quality_score, t.rejection_reason, t.previous_category, t.last_synced_at,
             t.template_group_key,
             t.created_at, t.updated_at,
             t.whatsapp_account_id AS "whatsappAccountId",
             wa.display_name AS "whatsappAccountName",
             wa.display_phone_number AS "whatsappAccountPhone",
             (SELECT COUNT(*) FROM coexistence.broadcasts WHERE template_id = t.id)::int AS "broadcastCount",
             (SELECT COUNT(*) FROM coexistence.broadcast_logs bl
               JOIN coexistence.broadcasts b ON b.id = bl.broadcast_id
              WHERE b.template_id = t.id AND bl.action = 'BROADCAST')::int AS "sendCount"
      FROM coexistence.message_templates t
      LEFT JOIN coexistence.whatsapp_accounts wa ON wa.id = t.whatsapp_account_id
      {where_sql}
      ORDER BY t.updated_at DESC
    """
    rows = await db.fetch(query, *params)
    return [shape_template(dict(r)) for r in rows]

@router.get("/{template_id}")
async def get_template(template_id: int, tenant_ctx: dict = Depends(get_tenant_context)):
    org_id = tenant_ctx.get("org_id")
    where_org = ""
    params = [template_id]
    if org_id:
        params.append(org_id)
        where_org = f"AND (t.org_id = ${len(params)}::uuid OR wa.org_id = ${len(params)}::uuid)"

    query = f"""
      SELECT t.id, t.name, t.category, t.language, t.header_type, t.header_text, t.media_handle,
             t.header_media_library_id, t.body, t.footer,
             t.buttons, t.samples, t.security_recommendation, t.code_expiry_minutes,
             t.allow_category_change, t.status, t.meta_template_id, t.submitted_at,
             t.quality_score, t.rejection_reason, t.previous_category, t.last_synced_at,
             t.template_group_key,
             t.created_at, t.updated_at,
             t.whatsapp_account_id AS "whatsappAccountId",
             wa.display_name AS "whatsappAccountName",
             wa.display_phone_number AS "whatsappAccountPhone",
             (SELECT COUNT(*) FROM coexistence.broadcasts WHERE template_id = t.id)::int AS "broadcastCount",
             (SELECT COUNT(*) FROM coexistence.broadcast_logs bl
               JOIN coexistence.broadcasts b ON b.id = bl.broadcast_id
              WHERE b.template_id = t.id AND bl.action = 'BROADCAST')::int AS "sendCount"
      FROM coexistence.message_templates t
      LEFT JOIN coexistence.whatsapp_accounts wa ON wa.id = t.whatsapp_account_id
      WHERE t.id = $1 {where_org}
    """
    row = await db.fetchrow(query, *params)
    if not row:
        raise HTTPException(status_code=404, detail="Template not found")
    return shape_template(dict(row))

@router.post("", status_code=201)
async def create_template(
    request: Request,
    tenant_ctx: dict = Depends(get_tenant_context),
    user: dict = Depends(require_permission("template-builder"))
):
    org_id = tenant_ctx.get("org_id")
    data = await request.json()
    errors = run_validation(data)
    if errors:
        raise HTTPException(status_code=400, detail={"error": "Validation failed", "errors": errors})

    wa_id = data.get("whatsappAccountId")
    if wa_id:
        if org_id:
            wa_acc = await db.fetchrow(
                "SELECT id FROM coexistence.whatsapp_accounts WHERE id = $1 AND org_id = $2::uuid",
                wa_id, org_id
            )
            if not wa_acc:
                raise HTTPException(status_code=403, detail="WhatsApp account does not belong to your organization")
        dup = await db.fetchval(
            """
            SELECT id FROM coexistence.message_templates
            WHERE whatsapp_account_id = $1 AND lower(name) = lower($2) AND language = $3
            LIMIT 1
            """,
            wa_id, data["name"], data["language"]
        )
        if dup:
            raise HTTPException(
                status_code=409,
                detail=f"A template with name \"{data['name']}\" in language \"{data['language']}\" already exists on this WhatsApp Account."
            )

    row = await db.fetchrow(
        """
        INSERT INTO coexistence.message_templates
         (name, category, language, header_type, header_text, media_handle, body, footer,
          buttons, samples, security_recommendation, code_expiry_minutes, allow_category_change, status,
          whatsapp_account_id, template_group_key, header_media_library_id, org_id)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18::uuid)
        RETURNING *
        """,
        data["name"], data["category"], data["language"], data.get("header_type") or "NONE",
        data.get("header_text"), data.get("media_handle"), data["body"],
        data.get("footer"), data.get("buttons") or [], data.get("samples") or {},
        bool(data.get("security_recommendation")), data.get("code_expiry_minutes"),
        data.get("allow_category_change") is not False, "DRAFT",
        wa_id, str(data["name"]).lower(),
        data.get("header_media_library_id"),
        org_id
    )
    return shape_template(dict(row))

@router.put("/{template_id}")
async def update_template(
    template_id: int,
    request: Request,
    tenant_ctx: dict = Depends(get_tenant_context),
    user: dict = Depends(require_permission("template-builder"))
):
    org_id = tenant_ctx.get("org_id")
    params = [template_id]
    where_org = ""
    if org_id:
        params.append(org_id)
        where_org = f"AND (t.org_id = ${len(params)}::uuid OR wa.org_id = ${len(params)}::uuid)"

    tpl = await db.fetchrow(
        f"""
        SELECT t.* FROM coexistence.message_templates t
        LEFT JOIN coexistence.whatsapp_accounts wa ON wa.id = t.whatsapp_account_id
        WHERE t.id = $1 {where_org}
        """,
        *params
    )
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")

    if tpl["status"] in ("SUBMITTED", "PENDING"):
        raise HTTPException(status_code=409, detail="Template is under Meta review — wait for approval/rejection before editing")
    if tpl["status"] == "DISABLED":
        raise HTTPException(status_code=409, detail="DISABLED templates cannot be edited — duplicate and resubmit instead")

    data = await request.json()
    errors = run_validation(data)
    if errors:
        raise HTTPException(status_code=400, detail={"error": "Validation failed", "errors": errors})

    is_approved_edit = tpl["status"] in ("APPROVED", "PAUSED")
    if is_approved_edit:
        if data.get("name") and data["name"] != tpl["name"]:
            raise HTTPException(status_code=400, detail="Cannot rename an APPROVED template — duplicate it instead")
        if data.get("language") and data["language"] != tpl["language"]:
            raise HTTPException(status_code=400, detail="Cannot change language on an APPROVED template — add a translation instead")

    new_status = "DRAFT"
    wa_id = data.get("whatsappAccountId", tpl["whatsapp_account_id"])
    if wa_id and org_id:
        wa_acc = await db.fetchrow("SELECT id FROM coexistence.whatsapp_accounts WHERE id = $1 AND org_id = $2::uuid", wa_id, org_id)
        if not wa_acc:
            raise HTTPException(status_code=403, detail="WhatsApp account does not belong to your organization")

    if is_approved_edit:
        if not wa_id or not tpl.get("meta_template_id"):
            raise HTTPException(status_code=400, detail="Template missing account link or Meta ID — cannot edit at Meta")
        account = await get_account_with_token(wa_id)
        if not account or not account.get("accessToken"):
            raise HTTPException(status_code=400, detail="WhatsApp account credentials missing")
        payload = build_payload(data)
        try:
            await meta_client.edit_template(account["wabaId"], account["accessToken"], tpl["meta_template_id"], payload)
            new_status = "SUBMITTED"
            await mark_account_health(account["id"], "healthy")
        except Exception as err:
            await mark_account_health(account["id"], "unknown_error", str(err))
            raise HTTPException(status_code=400, detail=f"Meta edit failed: {err}")

    row = await db.fetchrow(
        """
        UPDATE coexistence.message_templates
        SET name = $1, category = $2, language = $3, header_type = $4, header_text = $5,
            media_handle = $6, body = $7, footer = $8, buttons = $9, samples = $10,
            security_recommendation = $11, code_expiry_minutes = $12,
            allow_category_change = $13, status = $14, whatsapp_account_id = $15,
            template_group_key = $16, header_media_library_id = $17, updated_at = NOW()
        WHERE id = $18
        RETURNING *
        """,
        data.get("name", tpl["name"]), data.get("category", tpl["category"]),
        data.get("language", tpl["language"]), data.get("header_type") or "NONE",
        data.get("header_text"), data.get("media_handle"), data["body"],
        data.get("footer"), data.get("buttons") or [], data.get("samples") or {},
        bool(data.get("security_recommendation")), data.get("code_expiry_minutes"),
        data.get("allow_category_change") is not False, new_status,
        wa_id, str(data.get("name", tpl["name"])).lower(),
        data.get("header_media_library_id"),
        template_id
    )
    return shape_template(dict(row))

@router.post("/{template_id}/duplicate")
async def duplicate_template(
    template_id: int,
    tenant_ctx: dict = Depends(get_tenant_context),
    user: dict = Depends(require_permission("template-builder"))
):
    org_id = tenant_ctx.get("org_id")
    where_org = ""
    params = [template_id]
    if org_id:
        params.append(org_id)
        where_org = f"AND (t.org_id = ${len(params)}::uuid OR wa.org_id = ${len(params)}::uuid)"

    tpl = await db.fetchrow(
        f"""
        SELECT t.* FROM coexistence.message_templates t
        LEFT JOIN coexistence.whatsapp_accounts wa ON wa.id = t.whatsapp_account_id
        WHERE t.id = $1 {where_org}
        """,
        *params
    )
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")

    new_name = f"{tpl['name']}_copy_{int(time.time())}"[:512]
    row = await db.fetchrow(
        """
        INSERT INTO coexistence.message_templates
         (name, category, language, header_type, header_text, media_handle, body, footer,
          buttons, samples, security_recommendation, code_expiry_minutes, allow_category_change, status,
          whatsapp_account_id, template_group_key, header_media_library_id, org_id)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,'DRAFT',$14,$15,$16,$17::uuid)
        RETURNING *
        """,
        new_name, tpl["category"], tpl["language"], tpl["header_type"],
        tpl["header_text"], tpl["media_handle"], tpl["body"],
        tpl["footer"], tpl["buttons"] or [], tpl["samples"] or {},
        tpl["security_recommendation"], tpl["code_expiry_minutes"],
        tpl["allow_category_change"], tpl["whatsapp_account_id"],
        new_name.lower(), tpl["header_media_library_id"], org_id or tpl.get("org_id")
    )
    return shape_template(dict(row))

@router.delete("/{template_id}")
async def delete_template(
    template_id: int,
    tenant_ctx: dict = Depends(get_tenant_context),
    user: dict = Depends(require_permission("template-builder"))
):
    org_id = tenant_ctx.get("org_id")
    where_org = ""
    params = [template_id]
    if org_id:
        params.append(org_id)
        where_org = f"AND (t.org_id = ${len(params)}::uuid OR wa.org_id = ${len(params)}::uuid)"

    row = await db.fetchrow(
        f"""
        SELECT t.* FROM coexistence.message_templates t
        LEFT JOIN coexistence.whatsapp_accounts wa ON wa.id = t.whatsapp_account_id
        WHERE t.id = $1 {where_org}
        """,
        *params
    )
    if not row:
        raise HTTPException(status_code=404, detail="Template not found")

    if row.get("whatsapp_account_id") and row.get("status") in ("APPROVED", "SUBMITTED", "PENDING", "PAUSED"):
        acc = await get_account_with_token(row["whatsapp_account_id"])
        if acc and acc.get("wabaId") and acc.get("accessToken"):
            try:
                await meta_client.delete_template(acc["wabaId"], acc["accessToken"], row["name"])
            except Exception as e:
                logger.warning(f"[templates] Meta delete error (ignoring to delete local): {e}")

    await db.execute("DELETE FROM coexistence.message_templates WHERE id = $1", template_id)
    return {"ok": True}

@router.post("/{template_id}/submit")
async def submit_template_endpoint(
    template_id: int,
    tenant_ctx: dict = Depends(get_tenant_context),
    user: dict = Depends(require_permission("template-builder"))
):
    org_id = tenant_ctx.get("org_id")
    where_org = ""
    params = [template_id]
    if org_id:
        params.append(org_id)
        where_org = f"AND (t.org_id = ${len(params)}::uuid OR wa.org_id = ${len(params)}::uuid)"

    tpl = await db.fetchrow(
        f"""
        SELECT t.* FROM coexistence.message_templates t
        LEFT JOIN coexistence.whatsapp_accounts wa ON wa.id = t.whatsapp_account_id
        WHERE t.id = $1 {where_org}
        """,
        *params
    )
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")

    wa_id = tpl["whatsapp_account_id"]
    if not wa_id:
        raise HTTPException(status_code=400, detail="Template must be linked to a WhatsApp Account before submitting")

    acc = await get_account_with_token(wa_id)
    if not acc or not acc.get("accessToken") or not acc.get("wabaId"):
        raise HTTPException(status_code=400, detail="WhatsApp Account credentials missing")

    payload = build_payload(dict(tpl))
    try:
        res = await meta_client.submit_template(acc["wabaId"], acc["accessToken"], payload)
        meta_id = res.get("id")
        meta_status = map_meta_status(res.get("status"))
        row = await db.fetchrow(
            """
            UPDATE coexistence.message_templates
            SET status = $1, meta_template_id = $2, submitted_at = NOW(), updated_at = NOW()
            WHERE id = $3
            RETURNING *
            """,
            meta_status, meta_id, template_id
        )
        await mark_account_health(acc["id"], "healthy")
        return shape_template(dict(row))
    except Exception as err:
        err_msg = str(err)
        # If template already exists on Meta (e.g. from a prior submission where DB update failed),
        # look it up on Meta and synchronize the local row.
        if "already exists" in err_msg.lower():
            try:
                meta_list = await meta_client.list_templates(acc["wabaId"], acc["accessToken"])
                match = next((m for m in meta_list if m.get("name") == tpl["name"] and m.get("language") == tpl["language"]), None)
                if match:
                    m_status = map_meta_status(match.get("status"))
                    m_id = match.get("id")
                    row = await db.fetchrow(
                        """
                        UPDATE coexistence.message_templates
                        SET status = $1, meta_template_id = COALESCE(meta_template_id, $2),
                            submitted_at = COALESCE(submitted_at, NOW()), updated_at = NOW(),
                            last_synced_at = NOW()
                        WHERE id = $3
                        RETURNING *
                        """,
                        m_status, m_id, template_id
                    )
                    await mark_account_health(acc["id"], "healthy")
                    return shape_template(dict(row))
            except Exception as sync_err:
                logger.warning(f"[templates] auto-sync fallback failed: {sync_err}")

        is_auth = "401" in str(err) or "190" in str(err)
        await mark_account_health(acc["id"], "invalid_token" if is_auth else "unknown_error", str(err))
        raise HTTPException(status_code=400, detail=str(err))

@router.post("/{template_id}/sync")
async def sync_template_endpoint(
    template_id: int,
    tenant_ctx: dict = Depends(get_tenant_context),
    user: dict = Depends(require_permission("template-builder"))
):
    org_id = tenant_ctx.get("org_id")
    where_org = ""
    params = [template_id]
    if org_id:
        params.append(org_id)
        where_org = f"AND (t.org_id = ${len(params)}::uuid OR wa.org_id = ${len(params)}::uuid)"

    tpl = await db.fetchrow(
        f"""
        SELECT t.* FROM coexistence.message_templates t
        LEFT JOIN coexistence.whatsapp_accounts wa ON wa.id = t.whatsapp_account_id
        WHERE t.id = $1 {where_org}
        """,
        *params
    )
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")

    wa_id = tpl["whatsapp_account_id"]
    if not wa_id:
        return shape_template(dict(tpl))

    acc = await get_account_with_token(wa_id)
    if not acc or not acc.get("accessToken") or not acc.get("wabaId"):
        return shape_template(dict(tpl))

    try:
        meta_list = await meta_client.list_templates(acc["wabaId"], acc["accessToken"])
        match = next((m for m in meta_list if m.get("name") == tpl["name"] and m.get("language") == tpl["language"]), None)
        if match:
            local_status = map_meta_status(match.get("status", tpl["status"]))
            row = await db.fetchrow(
                """
                UPDATE coexistence.message_templates
                SET status = $1, quality_score = $2, rejection_reason = $3,
                    previous_category = $4, meta_template_id = COALESCE(meta_template_id, $5),
                    last_synced_at = NOW(), updated_at = NOW()
                WHERE id = $6
                RETURNING *
                """,
                local_status,
                match.get("quality_score", {}).get("score") if isinstance(match.get("quality_score"), dict) else match.get("quality_score"),
                match.get("rejected_reason"),
                match.get("previous_category"),
                match.get("id"),
                template_id
            )
            return shape_template(dict(row))
    except Exception as e:
        logger.error(f"[templates] sync error: {e}")

    return shape_template(dict(tpl))

@router.post("/sync-all")
async def sync_all_templates_endpoint(
    tenant_ctx: dict = Depends(get_tenant_context),
    user: dict = Depends(require_permission("template-builder"))
):
    org_id = tenant_ctx.get("org_id")
    if org_id:
        accounts = await db.fetch("SELECT id FROM coexistence.whatsapp_accounts WHERE is_active = true AND org_id = $1::uuid", org_id)
    else:
        accounts = await db.fetch("SELECT id FROM coexistence.whatsapp_accounts WHERE is_active = true")

    total_synced = 0
    for a in accounts:
        acc = await get_account_with_token(a["id"])
        if not acc or not acc.get("accessToken") or not acc.get("wabaId"):
            continue
        try:
            meta_list = await meta_client.list_templates(acc["wabaId"], acc["accessToken"])
            for m in meta_list:
                m_name = m.get("name")
                m_lang = m.get("language")
                m_status = m.get("status")
                if m_name and m_lang and m_status:
                    local_status = map_meta_status(m_status)
                    await db.execute(
                        """
                        UPDATE coexistence.message_templates
                        SET status = $1, quality_score = $2, rejection_reason = $3,
                            meta_template_id = COALESCE(meta_template_id, $4),
                            last_synced_at = NOW(), updated_at = NOW()
                        WHERE whatsapp_account_id = $5 AND lower(name) = lower($6) AND language = $7
                        """,
                        local_status,
                        m.get("quality_score", {}).get("score") if isinstance(m.get("quality_score"), dict) else m.get("quality_score"),
                        m.get("rejected_reason"),
                        m.get("id"),
                        acc["id"], m_name, m_lang
                    )
                    total_synced += 1
        except Exception as e:
            logger.error(f"[templates] sync_all for account {acc['id']} failed: {e}")

    return {"ok": True, "synced": total_synced}

@router.get("/{template_id}/payload")
async def preview_template_payload(template_id: int, tenant_ctx: dict = Depends(get_tenant_context)):
    org_id = tenant_ctx.get("org_id")
    where_org = ""
    params = [template_id]
    if org_id:
        params.append(org_id)
        where_org = f"AND (t.org_id = ${len(params)}::uuid OR wa.org_id = ${len(params)}::uuid)"

    tpl = await db.fetchrow(
        f"""
        SELECT t.* FROM coexistence.message_templates t
        LEFT JOIN coexistence.whatsapp_accounts wa ON wa.id = t.whatsapp_account_id
        WHERE t.id = $1 {where_org}
        """,
        *params
    )
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    return build_payload(dict(tpl))
