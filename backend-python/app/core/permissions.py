from typing import List, Dict, Any, Set, Optional

PAGES = [
    'home', 'chats', 'contacts', 'pipelines', 'bulk-message', 'template-builder',
    'chatbot-builder', 'ai-agent-builder', 'media-library', 'about',
    'admin-settings:general', 'admin-settings:tags', 'admin-settings:category',
    'admin-settings:fields', 'admin-settings:whatsapp-accounts',
    'admin-settings:integrations', 'admin-settings:users', 'admin-settings:mcp',
]

MODULE_TO_PAGE = {
    'chats': 'chats',
    'contacts': 'contacts',
    'pipelines': 'pipelines',
    'broadcasts': 'bulk-message',
    'templates': 'template-builder',
    'chatbots': 'chatbot-builder',
    'agents': 'ai-agent-builder',
    'media': 'media-library',
}

ROLE_PAGE_DEFAULTS = {
    'admin': list(PAGES),
    'org_admin': [
        'home', 'chats', 'contacts', 'pipelines', 'bulk-message',
        'template-builder', 'chatbot-builder', 'ai-agent-builder',
        'media-library', 'about',
        'admin-settings:general', 'admin-settings:tags',
        'admin-settings:category', 'admin-settings:fields',
        'admin-settings:users',
    ],
    'bda_sales': [
        'home', 'chats', 'contacts', 'pipelines', 'about',
        'admin-settings:general',
    ],
    'viewer': ['home', 'about'],
}

def effective_pages(user: Optional[Dict[str, Any]], active_org: Optional[Dict[str, Any]] = None) -> Set[str]:
    if not user:
        return set()
    role = user.get("role", "viewer")
    if role == "admin":
        return set(PAGES)

    base = ROLE_PAGE_DEFAULTS.get(role, [])
    pages = set(base)

    org_settings = (active_org or {}).get("settings") or {}
    org_modules = org_settings.get("modules") if isinstance(org_settings.get("modules"), dict) else None
    org_features = org_settings.get("features") if isinstance(org_settings.get("features"), dict) else {}
    member_role = (active_org or {}).get("role") or (active_org or {}).get("member_role") or ""

    # Tenant owners/admins can manage their workspace settings tabs (guarded by feature switchboard)
    if member_role in ("owner", "admin"):
        pages.update([
            'home', 'about',
            'admin-settings:general',
            'admin-settings:tags',
            'admin-settings:category',
            'admin-settings:fields',
        ])
        if org_features.get("allow_wa_config"):
            pages.add('admin-settings:whatsapp-accounts')

    # Apply Feature Switchboard module gates for non-viewer org users
    if org_modules is not None and role != 'viewer':
        for mod_key, page_name in MODULE_TO_PAGE.items():
            if org_modules.get(mod_key) is True:
                pages.add(page_name)
            elif org_modules.get(mod_key) is False:
                pages.discard(page_name)

    overrides = user.get("permissions") or {}
    if not isinstance(overrides, dict):
        overrides = {}

    grant = overrides.get("grant") or []
    if not isinstance(grant, list):
        grant = []
    revoke = set(overrides.get("revoke") or [])
    if not isinstance(revoke, (set, list)):
        revoke = set()

    for p in grant:
        mod_for_p = next((mk for mk, pn in MODULE_TO_PAGE.items() if pn == p), None)
        if org_modules is not None and mod_for_p and org_modules.get(mod_for_p) is False:
            continue
        pages.add(p)
    for p in revoke:
        pages.discard(p)
    return pages

def has_permission(user: Optional[Dict[str, Any]], page: str, active_org: Optional[Dict[str, Any]] = None) -> bool:
    if not user:
        return False
    if user.get("role") == "admin":
        return True
    return page in effective_pages(user, active_org)

def is_admin(user: Optional[Dict[str, Any]]) -> bool:
    return user.get("role") == "admin" if user else False
