from fastapi import Request, HTTPException, status, Depends
from typing import Optional, Dict, Any, Callable
from app.core.config import settings
from app.core.security import decode_access_token
from app.core.database import db
from app.core.permissions import has_permission

async def get_current_user(request: Request) -> Dict[str, Any]:
    """
    FastAPI dependency that validates the JWT cookie (or Bearer header)
    and verifies active status in the database.
    """
    token = request.cookies.get(settings.COOKIE_NAME) or request.cookies.get(settings.LEGACY_COOKIE_NAME)
    
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized"
        )

    payload = decode_access_token(token)
    if not payload or not payload.get("id"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    try:
        user_id = int(payload["id"])
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject"
        )

    user_row = await db.fetchrow(
        "SELECT id, username, email, display_name, role, permissions, is_active FROM coexistence.forgecrm_users WHERE id = $1",
        user_id
    )
    if not user_row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    if user_row.get("is_active") is False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account disabled"
        )

    # Attach user to request state
    user_dict = dict(user_row)
    request.state.user = user_dict
    return user_dict

async def require_admin(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return user

def require_permission(page: str) -> Callable:
    async def dependency(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        if not has_permission(user, page):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied for '{page}'"
            )
        return user
    return dependency

def is_admin_user(user: Dict[str, Any]) -> bool:
    return user.get("role") == "admin"

async def assert_wa_access(user: Dict[str, Any], wa_number: str):
    if is_admin_user(user):
        return True
    clean = "".join(filter(str.isdigit, str(wa_number or "")))
    row = await db.fetchrow(
        "SELECT 1 FROM coexistence.contacts WHERE wa_number = $1 AND assigned_user_id = $2 LIMIT 1",
        clean, user["id"]
    )
    if not row:
        raise HTTPException(status_code=403, detail="You do not have access to this WhatsApp number")
    return True

async def assert_contact_access(user: Dict[str, Any], wa_number: str, contact_number: str):
    if is_admin_user(user):
        return True
    clean_wa = "".join(filter(str.isdigit, str(wa_number or "")))
    clean_contact = "".join(filter(str.isdigit, str(contact_number or "")))
    row = await db.fetchrow(
        "SELECT 1 FROM coexistence.contacts WHERE wa_number = $1 AND contact_number = $2 AND assigned_user_id = $3 LIMIT 1",
        clean_wa, clean_contact, user["id"]
    )
    if not row:
        raise HTTPException(status_code=403, detail="You do not have access to this conversation")
    return True

async def audit_log(actor: Optional[dict], action: str, target_type: Optional[str] = None, target_id: Optional[str] = None, payload: Optional[dict] = None):
    try:
        import json
        await db.execute(
            """
            INSERT INTO coexistence.user_audit_log
              (actor_user_id, actor_username, action, target_type, target_id, payload)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            actor.get("id") if actor else None,
            actor.get("username") if actor else None,
            action,
            target_type,
            str(target_id) if target_id is not None else None,
            json.dumps(payload) if payload else None
        )
    except Exception as e:
        print(f"[audit] write failed: {e}")

