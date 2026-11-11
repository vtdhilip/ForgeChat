from fastapi import APIRouter, Response, Request, HTTPException, status, Depends
from pydantic import BaseModel
from typing import Optional
from app.core.config import settings
from app.core.database import db
from app.core.security import verify_password, hash_password, create_access_token
from app.services.auth_service import load_user_session
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/api/auth", tags=["Auth"])

class SetupRequest(BaseModel):
    username: Optional[str] = "admin"
    email: str
    password: str
    displayName: Optional[str] = "Admin"

class LoginRequest(BaseModel):
    email: str
    password: str

@router.get("/status")
async def auth_status():
    count = await db.fetchval("SELECT COUNT(*)::int FROM coexistence.forgecrm_users")
    return {"setupRequired": count == 0}

@router.post("/setup")
async def auth_setup(payload: SetupRequest, response: Response, request: Request):
    count = await db.fetchval("SELECT COUNT(*)::int FROM coexistence.forgecrm_users")
    if count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Setup already completed. Please sign in."
        )

    hashed_pw = hash_password(payload.password)
    user_row = await db.fetchrow(
        """
        INSERT INTO coexistence.forgecrm_users (username, email, password, display_name, role)
        VALUES ($1, $2, $3, $4, 'admin')
        RETURNING id, username, email, display_name, role
        """,
        (payload.username or "admin").strip().lower(),
        payload.email.strip().lower(),
        hashed_pw,
        payload.displayName or "Admin"
    )

    token = create_access_token({
        "id": user_row["id"],
        "username": user_row["username"],
        "displayName": user_row["display_name"],
        "role": user_row["role"]
    })

    is_secure = request.url.scheme == "https" or bool(settings.CORS_ORIGIN and settings.CORS_ORIGIN.startswith("https"))
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=is_secure,
        max_age=settings.TOKEN_EXPIRE_HOURS * 3600
    )

    session = await load_user_session(user_row["id"])
    return {"user": session}

@router.post("/login")
async def auth_login(payload: LoginRequest, response: Response, request: Request):
    if len(payload.email) > 255 or len(payload.password) > 256:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid credentials format"
        )

    email = payload.email.strip().lower()
    user_row = await db.fetchrow(
        "SELECT * FROM coexistence.forgecrm_users WHERE email = $1",
        email
    )
    if not user_row or not verify_password(payload.password, user_row["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    if user_row.get("is_active") is False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled. Contact an administrator."
        )

    token = create_access_token({
        "id": user_row["id"],
        "username": user_row["username"],
        "displayName": user_row["display_name"],
        "role": user_row["role"]
    })

    is_secure = request.url.scheme == "https" or bool(settings.CORS_ORIGIN and settings.CORS_ORIGIN.startswith("https"))
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=is_secure,
        max_age=settings.TOKEN_EXPIRE_HOURS * 3600
    )

    # Stamp last login
    await db.execute(
        "UPDATE coexistence.forgecrm_users SET last_login_at = NOW() WHERE id = $1",
        user_row["id"]
    )

    session = await load_user_session(user_row["id"])
    return {"user": session}

@router.get("/me")
async def auth_me(request: Request, user: dict = Depends(get_current_user)):
    active_org_id = (
        request.cookies.get("synapticchat_active_org") or
        request.cookies.get("forgecrm_active_org") or
        request.headers.get("x-org-id") or
        None
    )
    session = await load_user_session(user["id"], active_org_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if session.get("isActive") is False:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")
    return {"user": session}

@router.post("/logout")
async def auth_logout(response: Response):
    response.delete_cookie(key=settings.COOKIE_NAME)
    response.delete_cookie(key=settings.LEGACY_COOKIE_NAME)
    return {"ok": True}
