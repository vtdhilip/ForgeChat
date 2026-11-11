from fastapi import Request, HTTPException, status, Depends
from typing import Dict, Any, Callable, Optional
from app.core.database import db
from app.middleware.auth import get_current_user, is_tenant_admin

class TenantContext:
    def __init__(self, org_id: str, org_role: str, org: Dict[str, Any], user: Optional[Dict[str, Any]] = None):
        self.org_id = org_id
        self.org_role = org_role
        self.org = org
        self.user = user or {}

    def __getitem__(self, item):
        if item == "org_id":
            return self.org_id
        if item == "org_role":
            return self.org_role
        if item == "org":
            return self.org
        if item == "user":
            return self.user
        raise KeyError(item)

    def get(self, item, default=None):
        try:
            return self[item]
        except KeyError:
            return default

async def get_tenant_context(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user)
) -> TenantContext:
    """
    Resolves the active organization for the current user and sets request.state.org_id.
    """
    user_id = user["id"]
    is_super_admin = user.get("role") == "admin"
    
    requested_org_id = (
        request.headers.get("x-org-id") or
        request.headers.get("x-tenant-id") or
        request.cookies.get("synapticchat_active_org") or
        request.cookies.get("forgecrm_active_org") or
        request.query_params.get("org_id") or
        ""
    ).strip()

    query = """
        SELECT o.id, o.name, o.slug, o.plan, o.settings, o.is_active, om.role AS member_role
          FROM coexistence.organizations o
          JOIN coexistence.organization_members om ON om.org_id = o.id
         WHERE om.user_id = $1 AND o.is_active = true
    """
    params = [user_id]
    if requested_org_id:
        query += " AND (o.id::text = $2 OR o.slug = $2)"
        params.append(requested_org_id)
    query += " ORDER BY o.created_at ASC LIMIT 1"

    rows = await db.fetch(query, *params)
    org_data = None
    if rows:
        org_data = rows[0]
    elif is_super_admin:
        # Super admin can access any active organization
        sa_query = "SELECT id, name, slug, plan, settings, is_active FROM coexistence.organizations"
        sa_params = []
        if requested_org_id:
            sa_query += " WHERE id::text = $1 OR slug = $1"
            sa_params.append(requested_org_id)
        sa_query += " ORDER BY created_at ASC LIMIT 1"
        sa_rows = await db.fetch(sa_query, *sa_params)
        if sa_rows:
            org_data = dict(sa_rows[0])
            org_data["member_role"] = "owner"

    if not org_data:
        # Fallback to system default organization
        default_rows = await db.fetch("SELECT id, name, slug, plan, settings FROM coexistence.organizations ORDER BY created_at ASC LIMIT 1")
        if default_rows:
            def_org = default_rows[0]
            await db.execute(
                """
                INSERT INTO coexistence.organization_members (org_id, user_id, role)
                VALUES ($1, $2, 'member')
                ON CONFLICT (org_id, user_id) DO NOTHING
                """,
                def_org["id"], user_id
            )
            org_data = dict(def_org)
            org_data["member_role"] = "member"
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No organization configured in the system"
            )

    org_id_str = str(org_data["id"])
    member_role = org_data.get("member_role", "viewer")
    
    org_dict = {
        "id": org_id_str,
        "name": org_data["name"],
        "slug": org_data["slug"],
        "plan": org_data["plan"],
        "settings": org_data.get("settings") or {},
        "role": member_role,
    }

    ctx = TenantContext(org_id=org_id_str, org_role=member_role, org=org_dict, user=user)
    request.state.org_id = org_id_str
    request.state.org_role = member_role
    request.state.org = org_dict
    return ctx

def require_org_role(*allowed_roles: str) -> Callable:
    async def dependency(ctx: TenantContext = Depends(get_tenant_context)) -> TenantContext:
        if ctx.org_role not in allowed_roles and ctx.org_role != "owner":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Organization role in {allowed_roles} required (current: '{ctx.org_role}')"
            )
        return ctx
    return dependency

async def require_org_admin(ctx: TenantContext = Depends(get_tenant_context)) -> TenantContext:
    if not is_tenant_admin(ctx.user, ctx):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization admin privileges required"
        )
    return ctx
