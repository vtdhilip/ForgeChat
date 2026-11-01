from typing import List, Dict, Any, Set, Optional

PAGES = [
    'home', 'chats', 'contacts', 'pipelines', 'bulk-message', 'template-builder',
    'chatbot-builder', 'media-library', 'about',
    'admin-settings:general', 'admin-settings:tags', 'admin-settings:category',
    'admin-settings:fields', 'admin-settings:whatsapp-accounts',
    'admin-settings:users', 'admin-settings:mcp',
]

ROLE_PAGE_DEFAULTS = {
    'admin': list(PAGES),
    'bda_sales': [
        'home', 'chats', 'contacts', 'pipelines', 'about',
        'admin-settings:general',
    ],
    'viewer': ['home', 'about'],
}

def effective_pages(user: Optional[Dict[str, Any]]) -> Set[str]:
    if not user:
        return set()
    role = user.get("role", "viewer")
    base = ROLE_PAGE_DEFAULTS.get(role, [])
    overrides = user.get("permissions") or {}
    if not isinstance(overrides, dict):
        overrides = {}
    
    grant = overrides.get("grant") or []
    if not isinstance(grant, list):
        grant = []
    revoke = set(overrides.get("revoke") or [])
    if not isinstance(revoke, (set, list)):
        revoke = set()
    
    pages = set(base)
    for p in grant:
        pages.add(p)
    for p in revoke:
        pages.discard(p)
    return pages

def has_permission(user: Optional[Dict[str, Any]], page: str) -> bool:
    if not user:
        return False
    if user.get("role") == "admin":
        return True
    return page in effective_pages(user)

def is_admin(user: Optional[Dict[str, Any]]) -> bool:
    return user.get("role") == "admin" if user else False
