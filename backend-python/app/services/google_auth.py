import base64
import json
import logging
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from urllib.parse import urlencode
import httpx
import jwt

from app.core.config import settings
from app.core.database import get_db
from app.core.crypto import encrypt, decrypt

logger = logging.getLogger(__name__)

PROVIDER = "google"

SHEETS_SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
    "openid",
    "email",
    "profile",
]

DRIVE_LIST_SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive",
]

STATE_TTL_SECONDS = 10 * 60

def can_list_drive_files(scopes: Optional[List[str]] = None) -> bool:
    s = scopes or []
    return any(scope in DRIVE_LIST_SCOPES for scope in s)

async def get_oauth_credentials() -> Optional[Dict[str, Any]]:
    async with get_db() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, client_id_encrypted, client_secret_encrypted, redirect_uri, updated_at
              FROM coexistence.google_oauth_credentials
             ORDER BY id DESC LIMIT 1
            """
        )
        if not row:
            return None
        client_id = decrypt(row["client_id_encrypted"])
        client_secret = decrypt(row["client_secret_encrypted"])
        if not client_id or not client_secret or not row["redirect_uri"]:
            return None
        return {
            "id": row["id"],
            "clientId": client_id,
            "clientSecret": client_secret,
            "redirectUri": row["redirect_uri"],
            "updatedAt": row["updated_at"].isoformat() if row["updated_at"] else None,
        }

async def is_configured() -> bool:
    creds = await get_oauth_credentials()
    return creds is not None

async def get_credentials_for_display(reveal: bool = False) -> Dict[str, Any]:
    creds = await get_oauth_credentials()
    if not creds:
        return {"configured": False}
    out = {
        "configured": True,
        "clientId": creds["clientId"],
        "redirectUri": creds["redirectUri"],
        "updatedAt": creds["updatedAt"],
    }
    if reveal:
        out["clientSecret"] = creds["clientSecret"]
    return out

async def save_credentials(client_id: str, client_secret: Optional[str], redirect_uri: str, user_id: Optional[int] = None):
    c_id = str(client_id or "").strip()
    c_redirect = str(redirect_uri or "").strip()
    c_secret = str(client_secret or "").strip()

    if not c_id:
        raise ValueError("Client ID is required.")
    if not c_redirect:
        raise ValueError("Redirect URI is required.")

    async with get_db() as conn:
        existing = await conn.fetchrow(
            "SELECT id, client_secret_encrypted FROM coexistence.google_oauth_credentials ORDER BY id DESC LIMIT 1"
        )

        if c_secret:
            secret_enc = encrypt(c_secret)
        elif existing:
            secret_enc = existing["client_secret_encrypted"]
        else:
            raise ValueError("Client Secret is required when configuring Google for the first time.")

        if not existing:
            await conn.execute(
                """
                INSERT INTO coexistence.google_oauth_credentials
                  (client_id_encrypted, client_secret_encrypted, redirect_uri, updated_by)
                VALUES ($1, $2, $3, $4)
                """,
                encrypt(c_id),
                secret_enc,
                c_redirect,
                user_id,
            )
        else:
            await conn.execute(
                """
                UPDATE coexistence.google_oauth_credentials
                   SET client_id_encrypted = $1,
                       client_secret_encrypted = $2,
                       redirect_uri = $3,
                       updated_by = $4,
                       updated_at = NOW()
                 WHERE id = $5
                """,
                encrypt(c_id),
                secret_enc,
                c_redirect,
                user_id,
                existing["id"],
            )

async def delete_credentials():
    async with get_db() as conn:
        await conn.execute("DELETE FROM coexistence.google_oauth_credentials")

def sign_state(user_id: int, nonce: str) -> str:
    payload = {
        "uid": user_id,
        "n": nonce,
        "kind": "google_oauth_state",
        "exp": int(time.time()) + STATE_TTL_SECONDS,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")

def verify_state(state: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(state, settings.JWT_SECRET, algorithms=["HS256"])
        if payload.get("kind") != "google_oauth_state":
            return None
        return payload
    except Exception:
        return None

async def build_auth_url(user_id: int, nonce: str, scopes: Optional[List[str]] = None) -> str:
    creds = await get_oauth_credentials()
    if not creds:
        raise RuntimeError("Google is not configured yet. Add your Google OAuth Client ID, Client Secret, and Redirect URI in Settings → Integrations → Google.")

    state = sign_state(user_id, nonce)
    params = {
        "client_id": creds["clientId"],
        "redirect_uri": creds["redirectUri"],
        "response_type": "code",
        "scope": " ".join(scopes or SHEETS_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

async def handle_callback(code: str, user_id: int) -> Dict[str, Any]:
    creds = await get_oauth_credentials()
    if not creds:
        raise RuntimeError("Google OAuth is not configured")

    async with httpx.AsyncClient(timeout=15.0) as http:
        resp = await http.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": creds["clientId"],
                "client_secret": creds["clientSecret"],
                "redirect_uri": creds["redirectUri"],
                "grant_type": "authorization_code",
            },
        )
        if resp.status_code != 200:
            logger.error(f"[googleAuth] Token exchange failed: {resp.text}")
            raise RuntimeError(f"Google token exchange failed: {resp.text}")

        tokens = resp.json()

    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        raise RuntimeError(
            "Google did not return a refresh token. Revoke the app from your Google Account → Security → Third-party access, then try connecting again."
        )

    # Derive email from id_token
    email = None
    id_token = tokens.get("id_token")
    if id_token:
        try:
            parts = id_token.split(".")
            if len(parts) >= 2:
                payload_str = base64.urlsafe_b64decode(parts[1] + "==").decode("utf-8")
                id_data = json.loads(payload_str)
                email = id_data.get("email")
        except Exception as e:
            logger.warning(f"[googleAuth] Error decoding id_token: {e}")

    account_label = email or f"google-{int(time.time() * 1000)}"
    scopes = (tokens.get("scope") or "").split()
    expires_in = tokens.get("expires_in")
    expires_at = datetime.fromtimestamp(time.time() + expires_in, tz=timezone.utc) if expires_in else None

    async with get_db() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO coexistence.oauth_credentials
               (user_id, provider, account_label,
                refresh_token_encrypted, access_token_encrypted, access_token_expires_at,
                scopes, health_status, last_refreshed_at)
             VALUES ($1, $2, $3, $4, $5, $6, $7, 'ok', NOW())
             ON CONFLICT (user_id, provider, account_label) DO UPDATE
                SET refresh_token_encrypted = EXCLUDED.refresh_token_encrypted,
                    access_token_encrypted  = EXCLUDED.access_token_encrypted,
                    access_token_expires_at = EXCLUDED.access_token_expires_at,
                    scopes                  = EXCLUDED.scopes,
                    health_status           = 'ok',
                    last_error_message      = NULL,
                    last_refreshed_at       = NOW(),
                    updated_at              = NOW()
             RETURNING *
            """,
            user_id,
            PROVIDER,
            account_label,
            encrypt(refresh_token),
            encrypt(tokens.get("access_token") or ""),
            expires_at,
            scopes,
        )
        return dict(row)

async def mark_unhealthy(credential_id: int, message: str):
    try:
        async with get_db() as conn:
            await conn.execute(
                """
                UPDATE coexistence.oauth_credentials
                   SET health_status = 'error',
                       last_error_message = $1,
                       updated_at = NOW()
                 WHERE id = $2
                """,
                str(message or "")[:1000],
                credential_id,
            )
    except Exception as e:
        logger.error(f"[googleAuth] mark_unhealthy failed: {e}")

async def get_access_token(credential_id: int) -> str:
    async with get_db() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM coexistence.oauth_credentials WHERE id = $1",
            credential_id,
        )
        if not row:
            raise RuntimeError("OAuth credential not found")

        now_ts = time.time()
        expires_at_dt = row["access_token_expires_at"]
        expires_ts = expires_at_dt.timestamp() if expires_at_dt else 0
        cached = decrypt(row["access_token_encrypted"])

        if cached and expires_ts > now_ts + 60:
            return cached

        refresh_token = decrypt(row["refresh_token_encrypted"])
        if not refresh_token:
            await mark_unhealthy(credential_id, "Refresh token missing or unreadable; reconnect this Google account.")
            raise RuntimeError("Refresh token unavailable; reconnect this Google account.")

    # Refresh via Google token endpoint
    creds = await get_oauth_credentials()
    if not creds:
        raise RuntimeError("Google OAuth app credentials not configured")

    async with httpx.AsyncClient(timeout=15.0) as http:
        resp = await http.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": creds["clientId"],
                "client_secret": creds["clientSecret"],
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
        if resp.status_code != 200:
            await mark_unhealthy(credential_id, f"Refresh failed: {resp.text}")
            raise RuntimeError(f"Google refresh failed: {resp.text}")

        tok_data = resp.json()

    new_access = tok_data.get("access_token")
    expires_in = tok_data.get("expires_in")
    new_expiry = datetime.fromtimestamp(time.time() + expires_in, tz=timezone.utc) if expires_in else None

    async with get_db() as conn:
        await conn.execute(
            """
            UPDATE coexistence.oauth_credentials
               SET access_token_encrypted = $1,
                   access_token_expires_at = $2,
                   health_status = 'ok',
                   last_error_message = NULL,
                   last_refreshed_at = NOW(),
                   updated_at = NOW()
             WHERE id = $3
            """,
            encrypt(new_access),
            new_expiry,
            credential_id,
        )

    return new_access

async def revoke_and_delete(credential_id: int) -> bool:
    async with get_db() as conn:
        row = await conn.fetchrow(
            "SELECT refresh_token_encrypted FROM coexistence.oauth_credentials WHERE id = $1",
            credential_id,
        )
        if not row:
            return False

        refresh_token = decrypt(row["refresh_token_encrypted"])
        if refresh_token:
            try:
                async with httpx.AsyncClient(timeout=10.0) as http:
                    await http.post(
                        "https://oauth2.googleapis.com/revoke",
                        params={"token": refresh_token},
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                    )
            except Exception as e:
                logger.warning(f"[googleAuth] revokeToken failed: {e}")

        res = await conn.execute("DELETE FROM coexistence.oauth_credentials WHERE id = $1", credential_id)
        return "DELETE 1" in res
