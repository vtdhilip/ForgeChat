from typing import Optional, Dict, Any, List
from app.core.database import db
from app.core.permissions import effective_pages

async def load_user_session(user_id: Any, requested_org_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Constructs the full session object matching Node's loadUserSession:
    identity, role, effective pages, assigned WA numbers, organizations, and activeOrg.
    """
    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        return None

    user_row = await db.fetchrow(
        """
        SELECT id, username, email, display_name, role, permissions, is_active, last_login_at
          FROM coexistence.forgecrm_users WHERE id = $1
        """,
        uid
    )
    if not user_row:
        return None

    wa_rows = await db.fetch(
        "SELECT wa_number FROM coexistence.user_wa_assignments WHERE user_id = $1",
        uid
    )

    is_super_admin = user_row["role"] == "admin"

    if is_super_admin:
        orgs_query = """
            SELECT o.id, o.name, o.slug, o.plan, o.settings, o.is_active,
                   om.role AS member_role
              FROM coexistence.organizations o
              LEFT JOIN coexistence.organization_members om ON om.org_id = o.id AND om.user_id = $1
             ORDER BY o.created_at ASC
        """
    else:
        orgs_query = """
            SELECT o.id, o.name, o.slug, o.plan, o.settings, o.is_active,
                   om.role AS member_role
              FROM coexistence.organizations o
              JOIN coexistence.organization_members om ON om.org_id = o.id AND om.user_id = $1
             WHERE o.is_active = true
             ORDER BY o.created_at ASC
        """

    org_rows = await db.fetch(orgs_query, uid)

    active_org = None
    if org_rows:
        if requested_org_id:
            active_org = next(
                (o for o in org_rows if str(o["id"]) == str(requested_org_id) or o["slug"] == requested_org_id),
                org_rows[0]
            )
        else:
            active_org = org_rows[0]

    pages = list(effective_pages(user_row))

    organizations = []
    for o in org_rows:
        organizations.append({
            "id": str(o["id"]),
            "name": o["name"],
            "slug": o["slug"],
            "plan": o["plan"],
            "settings": o["settings"] or {},
            "role": o["member_role"] or ("owner" if is_super_admin else "viewer")
        })

    active_org_dict = None
    if active_org:
        active_org_dict = {
            "id": str(active_org["id"]),
            "name": active_org["name"],
            "slug": active_org["slug"],
            "plan": active_org["plan"],
            "settings": active_org["settings"] or {},
            "role": active_org["member_role"] or ("owner" if is_super_admin else "viewer")
        }

    return {
        "id": user_row["id"],
        "username": user_row["username"],
        "email": user_row["email"],
        "displayName": user_row["display_name"],
        "role": user_row["role"],
        "isActive": user_row["is_active"],
        "permissions": user_row["permissions"],
        "pages": pages,
        "assignedWaNumbers": [r["wa_number"] for r in wa_rows],
        "organizations": organizations,
        "activeOrg": active_org_dict
    }
