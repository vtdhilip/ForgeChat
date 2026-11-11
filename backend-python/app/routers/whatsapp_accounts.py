from fastapi import APIRouter, HTTPException, Depends, Query, Request
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from app.core.database import db
from app.core.crypto import encrypt, decrypt, mask_secret
from app.middleware.auth import get_current_user, require_permission
from app.middleware.tenant import get_tenant_context
from app.services.whatsapp_service import fetch_phone_meta, get_account_by_phone_number

router = APIRouter(prefix="/api/whatsapp-accounts", tags=["WhatsApp Accounts"])

def public_shape(row: dict, include_secrets: bool = False) -> Optional[dict]:
    if not row:
        return None
    out = {
        "id": row["id"],
        "displayName": row.get("display_name"),
        "displayPhoneNumber": row.get("display_phone_number"),
        "phoneNumberId": row.get("phone_number_id"),
        "wabaId": row.get("waba_id"),
        "metaAppId": row.get("meta_app_id"),
        "isDefault": row.get("is_default"),
        "isActive": row.get("is_active"),
        "healthStatus": row.get("health_status") or "unknown",
        "lastErrorAt": row["last_error_at"].isoformat() if row.get("last_error_at") else None,
        "lastErrorMessage": row.get("last_error_message"),
        "lastSuccessAt": row["last_success_at"].isoformat() if row.get("last_success_at") else None,
        "createdAt": row["created_at"].isoformat() if row.get("created_at") else None,
        "updatedAt": row["updated_at"].isoformat() if row.get("updated_at") else None,
    }
    if include_secrets:
        dec_token = decrypt(row.get("access_token_encrypted"))
        out["accessTokenMasked"] = mask_secret(dec_token) if dec_token else ""
        out["verifyToken"] = decrypt(row.get("verify_token_encrypted")) or ""
    return out

class WhatsAppAccountCreate(BaseModel):
    phoneNumberId: str
    wabaId: str
    accessToken: str
    verifyToken: Optional[str] = None
    metaAppId: Optional[str] = None

class WhatsAppAccountUpdate(BaseModel):
    phoneNumberId: Optional[str] = None
    wabaId: Optional[str] = None
    accessToken: Optional[str] = None
    verifyToken: Optional[str] = None
    metaAppId: Optional[str] = None
    isActive: Optional[bool] = None

@router.get("")
async def list_accounts(
    activeOnly: Optional[str] = None,
    tenant_ctx: dict = Depends(get_tenant_context)
):
    user = tenant_ctx["user"]
    org_id = tenant_ctx.get("org_id")
    
    query = "SELECT * FROM coexistence.whatsapp_accounts WHERE ($1::boolean IS NULL OR is_active = $1)"
    params = [True if activeOnly == "true" else None]

    if org_id:
        params.append(org_id)
        query += f" AND org_id = ${len(params)}"

    query += " ORDER BY is_default DESC, display_name ASC"
    rows = await db.fetch(query, *params)
    org_features = (tenant_ctx.get("org") or {}).get("settings", {}).get("features", {})
    include_secrets = user.get("role") == "admin" or bool(org_features.get("allow_wa_config"))
    return [public_shape(dict(r), include_secrets=include_secrets) for r in rows]

@router.get("/by-phone/{phone}")
async def resolve_by_phone(phone: str, user: dict = Depends(get_current_user)):
    acc = await get_account_by_phone_number(phone)
    if not acc:
        raise HTTPException(status_code=404, detail="No WhatsApp Business account registered for this phone")
    return {
        "id": acc["id"],
        "displayName": acc["displayName"],
        "displayPhoneNumber": acc["displayPhoneNumber"],
        "phoneNumberId": acc["phoneNumberId"],
        "wabaId": acc["wabaId"],
        "isActive": acc["isActive"]
    }

@router.get("/{account_id}")
async def get_account(account_id: int, tenant_ctx: dict = Depends(get_tenant_context)):
    user = tenant_ctx["user"]
    org_id = tenant_ctx.get("org_id")

    query = "SELECT * FROM coexistence.whatsapp_accounts WHERE id = $1"
    params = [account_id]
    if org_id and user.get("role") != "admin":
        params.append(org_id)
        query += f" AND org_id = ${len(params)}"

    row = await db.fetchrow(query, *params)
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    return public_shape(dict(row), include_secrets=True)

@router.post("", status_code=201)
async def create_account(
    payload: WhatsAppAccountCreate,
    tenant_ctx: dict = Depends(get_tenant_context),
    admin: dict = Depends(require_permission("admin-settings:whatsapp-accounts"))
):
    phone_number_id = payload.phoneNumberId.strip()
    waba_id = payload.wabaId.strip()
    access_token = payload.accessToken.strip()
    org_id = tenant_ctx.get("org_id")

    if not phone_number_id or not waba_id or not access_token:
        raise HTTPException(status_code=400, detail="Phone Number ID, WhatsApp Business Account ID and Permanent Access Token are required")

    if org_id:
        existing = await db.fetchval("SELECT COUNT(*)::int FROM coexistence.whatsapp_accounts WHERE org_id = $1", org_id)
        if existing and existing >= 1:
            raise HTTPException(status_code=409, detail="Only one WhatsApp Business account is allowed per organization. Edit the existing account instead.")

    display_name = f"WhatsApp {waba_id}"
    display_phone_number = ""
    try:
        meta = await fetch_phone_meta(phone_number_id, access_token)
        if meta.get("verified_name"):
            display_name = meta["verified_name"]
        if meta.get("display_phone_number"):
            display_phone_number = "".join(filter(str.isdigit, str(meta["display_phone_number"])))
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Couldn't verify this WhatsApp number with Meta. Double-check your Phone Number ID and access token. Meta said: {e}"
        )

    enc_token = encrypt(access_token)
    enc_verify = encrypt((payload.verifyToken or "").strip())

    try:
        row = await db.fetchrow(
            """
            INSERT INTO coexistence.whatsapp_accounts
              (display_name, display_phone_number, phone_number_id, waba_id, meta_app_id,
               access_token_encrypted, verify_token_encrypted, is_default, is_active, org_id)
            VALUES ($1, $2, $3, $4, $5, $6, $7, TRUE, TRUE, $8)
            RETURNING *
            """,
            display_name, display_phone_number, phone_number_id, waba_id,
            payload.metaAppId.strip() if payload.metaAppId else None,
            enc_token, enc_verify, org_id
        )
    except Exception as err:
        if "unique" in str(err).lower() or "23505" in str(err):
            raise HTTPException(status_code=409, detail="This Phone Number ID is already connected")
        raise HTTPException(status_code=500, detail="Failed to create WhatsApp Business account")

    return public_shape(dict(row), include_secrets=True)

@router.put("/{account_id}")
async def update_account(
    account_id: int,
    payload: WhatsAppAccountUpdate,
    tenant_ctx: dict = Depends(get_tenant_context),
    admin: dict = Depends(require_permission("admin-settings:whatsapp-accounts"))
):
    org_id = tenant_ctx.get("org_id")
    if org_id and admin.get("role") != "admin":
        current = await db.fetchrow("SELECT * FROM coexistence.whatsapp_accounts WHERE id = $1 AND org_id = $2", account_id, org_id)
    else:
        current = await db.fetchrow("SELECT * FROM coexistence.whatsapp_accounts WHERE id = $1", account_id)
    if not current:
        raise HTTPException(status_code=404, detail="Not found")

    new_phone_id = payload.phoneNumberId.strip() if payload.phoneNumberId is not None else current["phone_number_id"]
    new_waba = payload.wabaId.strip() if payload.wabaId is not None else current["waba_id"]
    token_changed = bool(payload.accessToken and payload.accessToken.strip())
    effective_token = payload.accessToken.strip() if token_changed else decrypt(current["access_token_encrypted"])

    display_name = current["display_name"]
    display_phone_number = current["display_phone_number"]

    if (payload.phoneNumberId is not None and new_phone_id != current["phone_number_id"]) or token_changed:
        try:
            meta = await fetch_phone_meta(new_phone_id, effective_token)
            if meta.get("verified_name"):
                display_name = meta["verified_name"]
            if meta.get("display_phone_number"):
                display_phone_number = "".join(filter(str.isdigit, str(meta["display_phone_number"])))
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Couldn't verify this WhatsApp number with Meta. Double-check your Phone Number ID and access token. Meta said: {e}"
            )

    sets = ["updated_at = NOW()"]
    params = [account_id]

    params.append(display_name)
    sets.append(f"display_name = ${len(params)}")

    params.append(display_phone_number)
    sets.append(f"display_phone_number = ${len(params)}")

    params.append(new_phone_id)
    sets.append(f"phone_number_id = ${len(params)}")

    params.append(new_waba)
    sets.append(f"waba_id = ${len(params)}")

    if payload.metaAppId is not None:
        params.append(payload.metaAppId.strip() if payload.metaAppId else None)
        sets.append(f"meta_app_id = ${len(params)}")

    if token_changed:
        params.append(encrypt(effective_token))
        sets.append(f"access_token_encrypted = ${len(params)}")
        sets.append("health_status = 'unknown'")
        sets.append("last_error_message = NULL")

    if payload.verifyToken is not None:
        params.append(encrypt(payload.verifyToken.strip()))
        sets.append(f"verify_token_encrypted = ${len(params)}")

    if payload.isActive is not None:
        params.append(payload.isActive)
        sets.append(f"is_active = ${len(params)}")

    query = f"UPDATE coexistence.whatsapp_accounts SET {', '.join(sets)} WHERE id = $1 RETURNING *"
    try:
        updated_row = await db.fetchrow(query, *params)
    except Exception as err:
        if "unique" in str(err).lower() or "23505" in str(err):
            raise HTTPException(status_code=409, detail="This Phone Number ID is already connected")
        raise HTTPException(status_code=500, detail="Failed to update WhatsApp Business account")

    return public_shape(dict(updated_row), include_secrets=True)

@router.delete("/{account_id}")
async def delete_account(
    account_id: int,
    tenant_ctx: dict = Depends(get_tenant_context),
    admin: dict = Depends(require_permission("admin-settings:whatsapp-accounts"))
):
    org_id = tenant_ctx.get("org_id")
    cnt = await db.fetchval("SELECT COUNT(*)::int FROM coexistence.whatsapp_accounts WHERE ($1::uuid IS NULL OR org_id = $1)", org_id if admin.get("role") != "admin" else None)
    if cnt and cnt <= 1:
        raise HTTPException(status_code=409, detail="Cannot delete the only WhatsApp Business account. Edit it to change the connected number.")
    
    if org_id and admin.get("role") != "admin":
        result = await db.execute("DELETE FROM coexistence.whatsapp_accounts WHERE id = $1 AND org_id = $2", account_id, org_id)
    else:
        result = await db.execute("DELETE FROM coexistence.whatsapp_accounts WHERE id = $1", account_id)
    if result.endswith(" 0"):
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True}
