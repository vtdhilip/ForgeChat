import logging
import secrets
from urllib.parse import urlencode
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.core.config import settings
from app.core.database import get_db
from app.middleware.auth import get_current_user, require_admin
from app.services.google_auth import (
    PROVIDER,
    is_configured,
    get_oauth_credentials,
    get_credentials_for_display,
    save_credentials,
    delete_credentials,
    build_auth_url,
    verify_state,
    handle_callback,
    revoke_and_delete,
    can_list_drive_files,
)
from app.services import google_sheets

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/google-integrations", tags=["Google Integrations"])

def frontend_settings_url(status: Optional[str] = None, error: Optional[str] = None, label: Optional[str] = None) -> str:
    base = (settings.CORS_ORIGIN or "/").rstrip("/")
    params = {}
    if status:
        params["google"] = status
    if error:
        params["error"] = error[:200]
    if label:
        params["label"] = label
    qs = f"?{urlencode(params)}" if params else ""
    return f"{base}/#/admin-settings/integrations/google{qs}"

def public_shape(row: dict) -> dict:
    return {
        "id": row["id"],
        "provider": row["provider"],
        "accountLabel": row["account_label"],
        "scopes": row["scopes"] or [],
        "healthStatus": row["health_status"],
        "lastErrorMessage": row["last_error_message"],
        "lastRefreshedAt": row["last_refreshed_at"].isoformat() if row.get("last_refreshed_at") else None,
        "accessTokenExpiresAt": row["access_token_expires_at"].isoformat() if row.get("access_token_expires_at") else None,
        "createdAt": row["created_at"].isoformat() if row.get("created_at") else None,
        "updatedAt": row["updated_at"].isoformat() if row.get("updated_at") else None,
    }

@router.get("/status")
async def get_google_status():
    try:
        creds = await get_oauth_credentials()
        return {
            "configured": bool(creds),
            "redirectUri": creds["redirectUri"] if creds else "",
        }
    except Exception as e:
        logger.error(f"[google-integrations] status error: {e}")
        raise HTTPException(status_code=500, detail="Failed to read Google integration status")

@router.get("/credentials")
async def get_google_credentials(
    reveal: Optional[str] = Query(None),
    admin: dict = Depends(require_admin),
):
    try:
        return await get_credentials_for_display(reveal=(reveal == "1"))
    except Exception as e:
        logger.error(f"[google-integrations] credentials GET error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load Google credentials")

class SaveCredentialsPayload(BaseModel):
    clientId: Optional[str] = None
    clientSecret: Optional[str] = None
    redirectUri: Optional[str] = None

@router.put("/credentials")
async def put_google_credentials(
    payload: SaveCredentialsPayload,
    admin: dict = Depends(require_admin),
):
    try:
        await save_credentials(
            client_id=payload.clientId or "",
            client_secret=payload.clientSecret,
            redirect_uri=payload.redirectUri or "",
            user_id=admin.get("id"),
        )
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[google-integrations] credentials PUT error: {e}")
        raise HTTPException(status_code=500, detail="Failed to save Google credentials")

@router.delete("/credentials")
async def delete_google_credentials(admin: dict = Depends(require_admin)):
    try:
        await delete_credentials()
        return {"ok": True}
    except Exception as e:
        logger.error(f"[google-integrations] credentials DELETE error: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove Google credentials")

@router.get("")
async def list_google_integrations(user: dict = Depends(get_current_user)):
    try:
        async with get_db() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM coexistence.oauth_credentials
                 WHERE user_id = $1 AND provider = $2
                 ORDER BY created_at DESC
                """,
                int(user["id"]),
                PROVIDER,
            )
            return [public_shape(dict(r)) for r in rows]
    except Exception as e:
        logger.error(f"[google-integrations] list error: {e}")
        raise HTTPException(status_code=500, detail="Failed to list Google integrations")

@router.post("/authorize")
async def start_google_authorize(user: dict = Depends(get_current_user)):
    try:
        if not (await is_configured()):
            raise HTTPException(
                status_code=501,
                detail="Google is not configured yet. Add your Google OAuth Client ID, Client Secret, and Redirect URI in Settings → Integrations → Google.",
            )
        nonce = secrets.token_hex(16)
        url = await build_auth_url(user_id=int(user["id"]), nonce=nonce)
        return {"authUrl": url}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[google-integrations] authorize error: {e}")
        raise HTTPException(status_code=500, detail=str(e) or "Failed to start Google authorization")

# Public OAuth callback endpoint
@router.get("/callback")
async def google_oauth_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
):
    if error:
        return RedirectResponse(frontend_settings_url(status="error", error=str(error)), status_code=302)
    if not code or not state:
        return RedirectResponse(frontend_settings_url(status="error", error="Missing code or state"), status_code=302)

    payload = verify_state(state)
    if not payload:
        return RedirectResponse(frontend_settings_url(status="error", error="Invalid or expired state"), status_code=302)

    try:
        row = await handle_callback(code=code, user_id=int(payload["uid"]))
        return RedirectResponse(frontend_settings_url(status="connected", label=row.get("account_label")), status_code=302)
    except Exception as e:
        logger.error(f"[google-integrations] callback error: {e}")
        return RedirectResponse(frontend_settings_url(status="error", error=str(e) or "OAuth callback failed"), status_code=302)

@router.get("/{cred_id}/spreadsheets")
async def list_user_spreadsheets(
    cred_id: int,
    q: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
):
    async with get_db() as conn:
        row = await conn.fetchrow(
            "SELECT id, scopes FROM coexistence.oauth_credentials WHERE id = $1 AND user_id = $2 AND provider = $3",
            cred_id,
            int(user["id"]),
            PROVIDER,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Not found")

    if not can_list_drive_files(row["scopes"]):
        raise HTTPException(
            status_code=409,
            detail={
                "error": "This Google account was connected without permission to list your spreadsheets. Reconnect it to grant read access to your Drive.",
                "code": "DRIVE_SCOPE_MISSING",
            },
        )

    try:
        files = await google_sheets.list_spreadsheets(cred_id, query=q or "")
        return files
    except Exception as e:
        logger.error(f"[google-integrations] list spreadsheets error: {e}")
        raise HTTPException(status_code=500, detail=str(e) or "Failed to list spreadsheets")

@router.get("/{cred_id}/spreadsheets/{spreadsheet_id}/tabs")
async def list_spreadsheet_tabs(
    cred_id: int,
    spreadsheet_id: str,
    user: dict = Depends(get_current_user),
):
    async with get_db() as conn:
        row = await conn.fetchrow(
            "SELECT id FROM coexistence.oauth_credentials WHERE id = $1 AND user_id = $2 AND provider = $3",
            cred_id,
            int(user["id"]),
            PROVIDER,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Not found")

    try:
        tabs = await google_sheets.list_sheet_tabs(cred_id, spreadsheet_id)
        return tabs
    except Exception as e:
        logger.error(f"[google-integrations] list tabs error: {e}")
        raise HTTPException(status_code=500, detail=str(e) or "Failed to list sheet tabs")

@router.delete("/{cred_id}")
async def delete_google_integration(
    cred_id: int,
    user: dict = Depends(get_current_user),
):
    async with get_db() as conn:
        row = await conn.fetchrow(
            "SELECT id FROM coexistence.oauth_credentials WHERE id = $1 AND user_id = $2",
            cred_id,
            int(user["id"]),
        )
    if not row:
        raise HTTPException(status_code=404, detail="Not found")

    try:
        ok = await revoke_and_delete(cred_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Not found")
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[google-integrations] delete error: {e}")
        raise HTTPException(status_code=500, detail="Failed to disconnect Google account")
