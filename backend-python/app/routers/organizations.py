import re
import secrets
from fastapi import APIRouter, HTTPException, status, Depends, Response
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from app.core.database import db
from app.core.security import hash_password
from app.middleware.auth import get_current_user, require_admin

router = APIRouter(prefix="/api/organizations", tags=["Organizations"])

def slugify(name: str) -> str:
    cleaned = re.sub(r'[^a-z0-9]+', '-', (name or '').lower().strip()).strip('-')
    return cleaned or f"org-{secrets.randbelow(9000) + 1000}"

class OnboardRequest(BaseModel):
    name: str
    plan: Optional[str] = "starter"
    contactEmail: Optional[str] = None
    contactPhone: Optional[str] = None
    adminUsername: Optional[str] = None
    adminPassword: Optional[str] = None
    modules: Optional[Dict[str, bool]] = Field(default_factory=dict)
    features: Optional[Dict[str, bool]] = Field(default_factory=dict)
    quotas: Optional[Dict[str, int]] = Field(default_factory=dict)

class ModuleUpdateRequest(BaseModel):
    modules: Optional[Dict[str, bool]] = None
    features: Optional[Dict[str, bool]] = None
    quotas: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    plan: Optional[str] = None

@router.get("/super-admin/overview")
async def super_admin_overview(user: dict = Depends(require_admin)):
    stats = await db.fetchrow(
        """
        SELECT
          (SELECT COUNT(*)::int FROM coexistence.organizations) AS total_orgs,
          (SELECT COUNT(*)::int FROM coexistence.organizations WHERE is_active = true) AS active_orgs,
          (SELECT COUNT(*)::int FROM coexistence.whatsapp_accounts WHERE is_active = true) AS total_wa_accounts,
          (SELECT COUNT(*)::int FROM coexistence.contacts) AS total_contacts,
          (SELECT COUNT(*)::int FROM coexistence.chat_history) AS total_messages,
          (SELECT COUNT(*)::int FROM coexistence.orders) AS total_orders,
          (SELECT COUNT(*)::int FROM coexistence.forgecrm_users) AS total_users
        """
    )
    return {"success": True, "stats": stats}

@router.post("/super-admin/onboard")
async def super_admin_onboard(payload: OnboardRequest, user: dict = Depends(require_admin)):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Client organization name is required")

    slug = slugify(name)
    existing_slug = await db.fetchrow("SELECT 1 FROM coexistence.organizations WHERE slug = $1", slug)
    if existing_slug:
        slug = f"{slug}-{secrets.randbelow(9000) + 1000}"

    modules = payload.modules or {}
    features = payload.features or {}
    quotas = payload.quotas or {}

    client_settings = {
        "order_prefix": f"{name[:3].upper()}-",
        "currency": "INR",
        "contact_email": payload.contactEmail or "",
        "contact_phone": payload.contactPhone or "",
        "modules": {
            "chats": modules.get("chats", True),
            "contacts": modules.get("contacts", True),
            "pipelines": bool(modules.get("pipelines", False)),
            "broadcasts": bool(modules.get("broadcasts", False)),
            "templates": modules.get("templates", True),
            "chatbots": bool(modules.get("chatbots", False)),
            "agents": bool(modules.get("agents", False)),
            "media": modules.get("media", True),
            "orders": bool(modules.get("orders", False)),
        },
        "features": {
            "allow_export": bool(features.get("allow_export", False)),
            "allow_byok_ai": bool(features.get("allow_byok_ai", False)),
            "allow_wa_config": bool(features.get("allow_wa_config", False)),
        },
        "quotas": {
            "max_users": quotas.get("max_users", 5),
            "max_wa_numbers": quotas.get("max_wa_numbers", 1),
            "max_broadcasts": quotas.get("max_broadcasts", 1000),
            "max_ai_tokens": quotas.get("max_ai_tokens", 50000),
        },
    }

    async with db.pool.acquire() as conn:
        async with conn.transaction():
            org_row = await conn.fetchrow(
                """
                INSERT INTO coexistence.organizations (name, slug, plan, settings, is_active)
                VALUES ($1, $2, $3, $4, true)
                RETURNING *
                """,
                name, slug, payload.plan or "starter", client_settings
            )

            client_user_id = None
            if payload.adminUsername and payload.adminPassword and payload.contactEmail:
                hashed_pw = hash_password(payload.adminPassword)
                user_row = await conn.fetchrow(
                    """
                    INSERT INTO coexistence.forgecrm_users (username, email, password, display_name, role)
                    VALUES ($1, $2, $3, $4, 'bda_sales')
                    ON CONFLICT (email) DO UPDATE SET display_name = EXCLUDED.display_name
                    RETURNING id
                    """,
                    payload.adminUsername.strip(),
                    payload.contactEmail.strip().lower(),
                    hashed_pw,
                    f"{name} Admin"
                )
                client_user_id = user_row["id"]
                await conn.execute(
                    """
                    INSERT INTO coexistence.organization_members (org_id, user_id, role)
                    VALUES ($1, $2, 'owner')
                    ON CONFLICT (org_id, user_id) DO UPDATE SET role = 'owner'
                    """,
                    org_row["id"], client_user_id
                )

    return {
        "success": True,
        "organization": dict(org_row),
        "clientUserId": client_user_id,
        "message": f"Client '{name}' onboarded successfully."
    }

@router.put("/{org_id}/modules")
async def update_org_modules(org_id: str, payload: ModuleUpdateRequest, user: dict = Depends(require_admin)):
    current = await db.fetchrow(
        "SELECT settings, plan, is_active FROM coexistence.organizations WHERE id::text = $1",
        org_id
    )
    if not current:
        raise HTTPException(status_code=404, detail="Organization not found")

    existing_settings = current.get("settings") or {}
    updated_settings = {
        **existing_settings,
        "modules": {**(existing_settings.get("modules") or {}), **(payload.modules or {})} if payload.modules is not None else existing_settings.get("modules", {}),
        "features": {**(existing_settings.get("features") or {}), **(payload.features or {})} if payload.features is not None else existing_settings.get("features", {}),
        "quotas": {**(existing_settings.get("quotas") or {}), **(payload.quotas or {})} if payload.quotas is not None else existing_settings.get("quotas", {}),
    }

    updates = ["settings = $1", "updated_at = NOW()"]
    params = [updated_settings]

    if payload.is_active is not None:
        params.append(bool(payload.is_active))
        updates.append(f"is_active = ${len(params)}")

    if payload.plan is not None:
        params.append(str(payload.plan))
        updates.append(f"plan = ${len(params)}")

    params.append(str(org_id))
    org_id_placeholder = f"${len(params)}"

    updated = await db.fetchrow(
        f"""
        UPDATE coexistence.organizations
           SET {', '.join(updates)}
         WHERE id::text = {org_id_placeholder}
         RETURNING *
        """,
        *params
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Organization not found")

    return {
        "success": True,
        "message": "Client features updated successfully",
        "organization": dict(updated)
    }

@router.get("")
async def list_organizations(user: dict = Depends(get_current_user)):
    user_id = user["id"]
    is_super_admin = user.get("role") == "admin"

    if is_super_admin:
        query = """
            SELECT o.id, o.name, o.slug, o.plan, o.settings, o.is_active, o.created_at,
                   om.role AS member_role,
                   (SELECT COUNT(*) FROM coexistence.organization_members WHERE org_id = o.id)::int AS member_count,
                   (SELECT COUNT(*) FROM coexistence.whatsapp_accounts WHERE org_id = o.id)::int AS wa_count
              FROM coexistence.organizations o
              LEFT JOIN coexistence.organization_members om ON om.org_id = o.id AND om.user_id = $1
             ORDER BY o.created_at ASC
        """
    else:
        query = """
            SELECT o.id, o.name, o.slug, o.plan, o.settings, o.is_active, o.created_at,
                   om.role AS member_role,
                   (SELECT COUNT(*) FROM coexistence.organization_members WHERE org_id = o.id)::int AS member_count,
                   (SELECT COUNT(*) FROM coexistence.whatsapp_accounts WHERE org_id = o.id)::int AS wa_count
              FROM coexistence.organizations o
              JOIN coexistence.organization_members om ON om.org_id = o.id AND om.user_id = $1
             WHERE o.is_active = true
             ORDER BY o.created_at ASC
        """

    rows = await db.fetch(query, user_id)
    return {
        "organizations": [
            {
                "id": str(r["id"]),
                "name": r["name"],
                "slug": r["slug"],
                "plan": r["plan"],
                "settings": r.get("settings") or {},
                "isActive": r["is_active"],
                "role": r["member_role"] or ("owner" if is_super_admin else "viewer"),
                "memberCount": r["member_count"],
                "waCount": r["wa_count"],
                "createdAt": r["created_at"].isoformat() if r["created_at"] else None,
            }
            for r in rows
        ]
    }

class SwitchOrgPayload(BaseModel):
    org_id: str

async def _do_switch_org(org_id: str, response: Response, user: dict):
    user_id = user["id"]
    is_super_admin = user.get("role") == "admin"

    if is_super_admin:
        org = await db.fetchrow(
            """
            SELECT o.id, o.name, o.slug, o.plan, o.settings, om.role
              FROM coexistence.organizations o
              LEFT JOIN coexistence.organization_members om ON om.org_id = o.id AND om.user_id = $2
             WHERE o.id::text = $1 OR o.slug = $1
            """,
            org_id, user_id
        )
    else:
        org = await db.fetchrow(
            """
            SELECT o.id, o.name, o.slug, o.plan, o.settings, om.role
              FROM coexistence.organizations o
              JOIN coexistence.organization_members om ON om.org_id = o.id AND om.user_id = $2
             WHERE (o.id::text = $1 OR o.slug = $1) AND o.is_active = true
            """,
            org_id, user_id
        )

    if not org:
        raise HTTPException(status_code=403, detail="Access denied to this organization")

    org_id_str = str(org["id"])
    response.set_cookie(
        key="synapticchat_active_org",
        value=org_id_str,
        httponly=False,
        samesite="lax",
        max_age=365 * 86400
    )
    response.set_cookie(
        key="forgecrm_active_org",
        value=org_id_str,
        httponly=False,
        samesite="lax",
        max_age=365 * 86400
    )

    return {
        "success": True,
        "activeOrg": {
            "id": org_id_str,
            "name": org["name"],
            "slug": org["slug"],
            "plan": org["plan"],
            "settings": org["settings"] or {},
            "role": org["role"] or ("owner" if is_super_admin else "viewer"),
        }
    }

@router.post("/switch")
async def switch_organization_post(payload: SwitchOrgPayload, response: Response, user: dict = Depends(get_current_user)):
    return await _do_switch_org(payload.org_id, response, user)

@router.post("/{org_id}/switch")
async def switch_organization(org_id: str, response: Response, user: dict = Depends(get_current_user)):
    return await _do_switch_org(org_id, response, user)
