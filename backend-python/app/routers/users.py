import secrets
import re
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from app.core.database import db
from app.core.security import hash_password
from app.core.permissions import PAGES, ROLE_PAGE_DEFAULTS
from app.middleware.tenant import require_org_admin

router = APIRouter(prefix="/api/users", tags=["Users"])

VALID_ROLES = set(ROLE_PAGE_DEFAULTS.keys())


def _member_role_for_user(user_role: str) -> str:
    return "admin" if user_role in ("admin", "org_admin") else "member"


async def _load_scoped_user(user_id: int, org_id: str, is_super: bool) -> dict:
    if is_super:
        row = await db.fetchrow("SELECT * FROM coexistence.forgecrm_users WHERE id = $1", user_id)
    else:
        row = await db.fetchrow(
            """
            SELECT u.*
              FROM coexistence.forgecrm_users u
              JOIN coexistence.organization_members om ON om.user_id = u.id
             WHERE u.id = $1 AND om.org_id = $2::uuid AND u.role <> 'admin'
            """,
            user_id,
            org_id,
        )
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return dict(row)

def generate_password(length: int = 12) -> str:
    alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789!@#$%'
    return ''.join(secrets.choice(alphabet) for _ in range(length))

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
async def list_users(tenant_ctx: dict = Depends(require_org_admin)):
    caller = tenant_ctx["user"]
    if caller.get("role") == "admin":
        rows = await db.fetch("SELECT * FROM coexistence.forgecrm_users ORDER BY created_at")
    else:
        rows = await db.fetch(
            """
            SELECT u.*
              FROM coexistence.forgecrm_users u
              JOIN coexistence.organization_members om ON om.user_id = u.id
             WHERE om.org_id = $1::uuid AND u.role <> 'admin'
             ORDER BY u.created_at
            """,
            tenant_ctx["org_id"],
        )
    user_ids = [r["id"] for r in rows]
    assignments = await load_assignments(user_ids)
    return [shape_user(r, assignments.get(r["id"], [])) for r in rows]

@router.get("/{user_id}")
async def get_user(user_id: int, tenant_ctx: dict = Depends(require_org_admin)):
    caller = tenant_ctx["user"]
    row = await _load_scoped_user(user_id, tenant_ctx["org_id"], caller.get("role") == "admin")
    assignments = await load_assignments([user_id])
    return shape_user(row, assignments.get(user_id, []))

@router.post("")
async def create_user(payload: UserCreate, tenant_ctx: dict = Depends(require_org_admin)):
    admin = tenant_ctx["user"]
    is_super = admin.get("role") == "admin"
    username = payload.username.strip()
    if not username or len(username) > 64:
        raise HTTPException(status_code=400, detail="Username must be between 1 and 64 characters")
    email = payload.email.strip().lower()
    if not email or len(email) > 255 or "@" not in email:
        raise HTTPException(status_code=400, detail="Valid email is required (max 255 characters)")
    display_name = payload.displayName.strip()
    if not display_name or len(display_name) > 128:
        raise HTTPException(status_code=400, detail="Display name must be between 1 and 128 characters")

    target_role = payload.role or "bda_sales"
    if target_role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Role must be one of: {', '.join(VALID_ROLES)}")
    if not is_super and target_role == "admin":
        raise HTTPException(status_code=403, detail="Only super admins can assign the platform admin role")

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
                username,
                email,
                hashed_pw,
                display_name,
                target_role,
                payload.permissions,
                admin["id"]
            )

            new_user_id = user_row["id"]
            await conn.execute(
                """
                INSERT INTO coexistence.organization_members (org_id, user_id, role)
                VALUES ($1::uuid, $2, $3)
                ON CONFLICT (org_id, user_id) DO UPDATE SET role = EXCLUDED.role
                """,
                tenant_ctx["org_id"],
                new_user_id,
                _member_role_for_user(target_role),
            )
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
async def update_user(user_id: int, payload: UserUpdate, tenant_ctx: dict = Depends(require_org_admin)):
    admin = tenant_ctx["user"]
    is_super = admin.get("role") == "admin"
    await _load_scoped_user(user_id, tenant_ctx["org_id"], is_super)

    updates = []
    params = [user_id]

    if payload.displayName is not None:
        dn = payload.displayName.strip()
        if not dn or len(dn) > 128:
            raise HTTPException(status_code=400, detail="Display name must be between 1 and 128 characters")
        params.append(dn)
        updates.append(f"display_name = ${len(params)}")

    if payload.email is not None:
        em = payload.email.strip().lower()
        if not em or len(em) > 255 or "@" not in em:
            raise HTTPException(status_code=400, detail="Valid email is required (max 255 characters)")
        params.append(em)
        updates.append(f"email = ${len(params)}")

    if payload.role is not None:
        if payload.role not in VALID_ROLES:
            raise HTTPException(status_code=400, detail=f"Invalid role: {payload.role}")
        if not is_super and payload.role == "admin":
            raise HTTPException(status_code=403, detail="Only super admins can assign the platform admin role")
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
            if payload.role is not None:
                await conn.execute(
                    """
                    UPDATE coexistence.organization_members
                       SET role = CASE WHEN role = 'owner' THEN 'owner' ELSE $3 END
                     WHERE org_id = $1::uuid AND user_id = $2
                    """,
                    tenant_ctx["org_id"],
                    user_id,
                    _member_role_for_user(payload.role),
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
async def delete_user(user_id: int, tenant_ctx: dict = Depends(require_org_admin)):
    admin = tenant_ctx["user"]
    is_super = admin.get("role") == "admin"
    if user_id == admin["id"]:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    user_to_delete = await _load_scoped_user(user_id, tenant_ctx["org_id"], is_super)
    if user_to_delete["role"] == "admin":
        count = await db.fetchval("SELECT COUNT(*)::int FROM coexistence.forgecrm_users WHERE role = 'admin' AND is_active = true")
        if count <= 1:
            raise HTTPException(status_code=400, detail="Cannot delete the last active administrator")

    await db.execute("DELETE FROM coexistence.forgecrm_users WHERE id = $1", user_id)
    return {"ok": True}

@router.post("/{user_id}/reset-password")
async def reset_password(user_id: int, payload: ResetPasswordRequest, tenant_ctx: dict = Depends(require_org_admin)):
    admin = tenant_ctx["user"]
    await _load_scoped_user(user_id, tenant_ctx["org_id"], admin.get("role") == "admin")

    new_pw = (payload.password or "").strip() or generate_password()
    hashed_pw = hash_password(new_pw)
    await db.execute("UPDATE coexistence.forgecrm_users SET password = $1, updated_at = NOW() WHERE id = $2", hashed_pw, user_id)
    return {"ok": True, "password": new_pw if not payload.password else None}
