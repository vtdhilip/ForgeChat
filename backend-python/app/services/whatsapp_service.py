import re
import os
import httpx
from typing import Optional, Dict, Any
from app.core.database import db
from app.core.crypto import encrypt, decrypt

def normalize_phone(p: Optional[str]) -> str:
    return re.sub(r"\D", "", str(p or ""))

async def fetch_phone_meta(phone_number_id: str, access_token: str) -> Dict[str, Any]:
    version = os.getenv("META_API_VERSION", "v21.0")
    api_url = f"https://graph.facebook.com/{version}/{phone_number_id}?fields=display_phone_number,verified_name"
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(api_url, headers={"Authorization": f"Bearer {access_token}"})
        try:
            body = resp.json()
        except Exception:
            body = {}
        if resp.status_code >= 400:
            err_msg = body.get("error", {}).get("message") or resp.text or f"HTTP {resp.status_code}"
            raise Exception(err_msg)
        return body

def row_to_creds(r: Optional[dict]) -> Optional[Dict[str, Any]]:
    if not r:
        return None
    return {
        "id": r["id"],
        "displayName": r.get("display_name"),
        "displayPhoneNumber": r.get("display_phone_number"),
        "phoneNumberId": r.get("phone_number_id"),
        "wabaId": r.get("waba_id"),
        "accessToken": decrypt(r.get("access_token_encrypted")),
        "isActive": r.get("is_active"),
        "orgId": r.get("org_id")
    }

async def get_account_with_token(account_id: int) -> Optional[Dict[str, Any]]:
    row = await db.fetchrow(
        "SELECT * FROM coexistence.whatsapp_accounts WHERE id = $1",
        account_id
    )
    return row_to_creds(dict(row) if row else None)

async def get_single_account(org_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    if org_id:
        row = await db.fetchrow(
            "SELECT * FROM coexistence.whatsapp_accounts WHERE org_id = $1 ORDER BY is_default DESC, id ASC LIMIT 1",
            org_id
        )
        if row:
            return row_to_creds(dict(row))
    row = await db.fetchrow(
        "SELECT * FROM coexistence.whatsapp_accounts ORDER BY is_default DESC, id ASC LIMIT 1"
    )
    return row_to_creds(dict(row) if row else None)

async def get_account_by_phone_number(phone_or_id: str, org_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    norm = normalize_phone(phone_or_id)
    if not norm:
        return None
    
    if org_id:
        row = await db.fetchrow(
            """
            SELECT * FROM coexistence.whatsapp_accounts
            WHERE org_id = $1 AND (regexp_replace(display_phone_number, '\\D', '', 'g') = $2 OR phone_number_id = $3)
            LIMIT 1
            """,
            org_id, norm, str(phone_or_id)
        )
        if row:
            return row_to_creds(dict(row))

    row = await db.fetchrow(
        """
        SELECT * FROM coexistence.whatsapp_accounts
        WHERE regexp_replace(display_phone_number, '\\D', '', 'g') = $1 OR phone_number_id = $2
        LIMIT 1
        """,
        norm, str(phone_or_id)
    )
    return row_to_creds(dict(row) if row else None)
