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

    user_row = await db.fetchrow(
        "SELECT id, username, email, display_name, role, permissions, is_active FROM coexistence.forgecrm_users WHERE id = $1",
        payload["id"]
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
