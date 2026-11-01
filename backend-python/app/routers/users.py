import random
import re
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from app.core.database import db
from app.core.security import hash_password
from app.core.permissions import PAGES, ROLE_PAGE_DEFAULTS
from app.middleware.auth import require_admin

router = APIRouter(prefix="/api/users", tags=["Users"])

VALID_ROLES = set(ROLE_PAGE_DEFAULTS.keys())

def generate_password(length: int = 12) -> str:
    alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789!@#$%'
    return ''.join(random.choice(alphabet) for _ in range(length))

def shape_user(row: dict, wa_assignments: List[str] = None) -> dict:
    return {
        "id": row["id"],
        "username": row["username"],
        "email": row["email"],
        "displayName": row["display_name"],
        "role": row["role"],
        "isActive": row["is_active"],
        "permissions": row["permissions"],
        "lastLoginAt": row["last_login_at"].isoformat() if row.get("last_login_at") else None,
        "createdAt": row["created_at"].isoformat() if row.get("created_at") else None,
        "updatedAt": row["updated_at"].isoformat() if row.get("updated_at") else None,
        "createdBy": row.get("created_by"),
        "assignedWaNumbers": wa_assignments or []
    }

async def load_assignments(user_ids: List[int]) -> Dict[int, List[str]]:
    if not user_ids:
        return {}
    rows = await db.fetch(
        "SELECT user_id, wa_number FROM coexistence.user_wa_assignments WHERE user_id = ANY($1::bigint[])",
        user_ids
    )
    mapping = {}
    for r in rows:
        mapping.setdefault(r["user_id"], []).append(r["wa_number"])
    return mapping

class UserCreate(BaseModel):
    username: str
    email: str
    displayName: str
    password: Optional[str] = None
    role: Optional[str] = "bda_sales"
    permissions: Optional[Dict[str, Any]] = None
    assignedWaNumbers: Optional[List[str]] = None

class UserUpdate(BaseModel):
    displayName: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    permissions: Optional[Dict[str, Any]] = None
    isActive: Optional[bool] = None
    assignedWaNumbers: Optional[List[str]] = None

class ResetPasswordRequest(BaseModel):
    password: Optional[str] = None

@router.get("")
async def list_users(user: dict = Depends(require_admin)):
    rows = await db.fetch("SELECT * FROM coexistence.forgecrm_users ORDER BY created_at")
    user_ids = [r["id"] for r in rows]
    assignments = await load_assignments(user_ids)
    return [shape_user(r, assignments.get(r["id"], [])) for r in rows]

@router.get("/{user_id}")
async def get_user(user_id: int, user: dict = Depends(require_admin)):
    row = await db.fetchrow("SELECT * FROM coexistence.forgecrm_users WHERE id = $1", user_id)
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    assignments = await load_assignments([user_id])
    return shape_user(row, assignments.get(user_id, []))

@router.post("")
async def create_user(payload: UserCreate, admin: dict = Depends(require_admin)):
    if payload.role and payload.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Role must be one of: {', '.join(VALID_ROLES)}")

    final_password = (payload.password or "").strip() or generate_password()
    hashed_pw = hash_password(final_password)

    async with db.pool.acquire() as conn:
        async with conn.transaction():
            user_row = await conn.fetchrow(
                """
                INSERT INTO coexistence.forgecrm_users
                  (username, email, password, display_name, role, permissions, created_by)
                VALUES ($1, LOWER($2), $3, $4, $5, $6, $7)
                RETURNING *
                """,
                payload.username.strip(),
                payload.email.strip(),
                hashed_pw,
                payload.displayName.strip(),
                payload.role or "bda_sales",
                payload.permissions,
                admin["id"]
            )

            new_user_id = user_row["id"]
            wa_list = payload.assignedWaNumbers or []
            clean_was = []
            for wa in wa_list:
                clean = re.sub(r'\D', '', str(wa))
                if clean:
                    await conn.execute(
                        "INSERT INTO coexistence.user_wa_assignments (user_id, wa_number) VALUES ($1, $2) ON CONFLICT DO NOTHING",
                        new_user_id, clean
                    )
                    clean_was.append(clean)

    resp = shape_user(user_row, clean_was)
    resp["temporaryPassword"] = final_password if not payload.password else None
    return resp

@router.patch("/{user_id}")
async def update_user(user_id: int, payload: UserUpdate, admin: dict = Depends(require_admin)):
    current = await db.fetchrow("SELECT * FROM coexistence.forgecrm_users WHERE id = $1", user_id)
    if not current:
        raise HTTPException(status_code=404, detail="User not found")

    updates = []
    params = [user_id]

    if payload.displayName is not None:
        params.append(payload.displayName.strip())
        updates.append(f"display_name = ${len(params)}")

    if payload.email is not None:
        params.append(payload.email.strip().lower())
        updates.append(f"email = ${len(params)}")

    if payload.role is not None:
        if payload.role not in VALID_ROLES:
            raise HTTPException(status_code=400, detail=f"Invalid role: {payload.role}")
        params.append(payload.role)
        updates.append(f"role = ${len(params)}")

    if payload.permissions is not None:
        params.append(payload.permissions)
        updates.append(f"permissions = ${len(params)}")

    if payload.isActive is not None:
        params.append(payload.isActive)
        updates.append(f"is_active = ${len(params)}")

    async with db.pool.acquire() as conn:
        async with conn.transaction():
            if updates:
                updates.append("updated_at = NOW()")
                await conn.execute(
                    f"UPDATE coexistence.forgecrm_users SET {', '.join(updates)} WHERE id = $1",
                    *params
                )

            if payload.assignedWaNumbers is not None:
                await conn.execute("DELETE FROM coexistence.user_wa_assignments WHERE user_id = $1", user_id)
                clean_was = []
                for wa in payload.assignedWaNumbers:
                    clean = re.sub(r'\D', '', str(wa))
                    if clean:
                        await conn.execute(
                            "INSERT INTO coexistence.user_wa_assignments (user_id, wa_number) VALUES ($1, $2) ON CONFLICT DO NOTHING",
                            user_id, clean
                        )
                        clean_was.append(clean)

    updated_row = await db.fetchrow("SELECT * FROM coexistence.forgecrm_users WHERE id = $1", user_id)
    assignments = await load_assignments([user_id])
    return shape_user(updated_row, assignments.get(user_id, []))

@router.delete("/{user_id}")
async def delete_user(user_id: int, admin: dict = Depends(require_admin)):
    if user_id == admin["id"]:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    count = await db.fetchval("SELECT COUNT(*)::int FROM coexistence.forgecrm_users WHERE role = 'admin' AND is_active = true")
    user_to_delete = await db.fetchrow("SELECT role FROM coexistence.forgecrm_users WHERE id = $1", user_id)
    if user_to_delete and user_to_delete["role"] == "admin" and count <= 1:
        raise HTTPException(status_code=400, detail="Cannot delete the last active administrator")

    await db.execute("DELETE FROM coexistence.forgecrm_users WHERE id = $1", user_id)
    return {"ok": True}

@router.post("/{user_id}/reset-password")
async def reset_password(user_id: int, payload: ResetPasswordRequest, admin: dict = Depends(require_admin)):
    user_row = await db.fetchrow("SELECT id FROM coexistence.forgecrm_users WHERE id = $1", user_id)
    if not user_row:
        raise HTTPException(status_code=404, detail="User not found")

    new_pw = (payload.password or "").strip() or generate_password()
    hashed_pw = hash_password(new_pw)
    await db.execute("UPDATE coexistence.forgecrm_users SET password = $1, updated_at = NOW() WHERE id = $2", hashed_pw, user_id)
    return {"ok": True, "password": new_pw if not payload.password else None}
