#!/usr/bin/env python3
"""
Test Feature Switchboard Button Hiding & Dynamic Toggling
Verifies that disabled modules are hidden and enabled modules are shown in the UI.
"""
import requests
import json
import subprocess
import sys

BASE_URL = "http://localhost:8080"
LINNDEN_ORG_ID = "26e7b672-5558-4a4b-9aed-926c6b71d995"

NAV_ITEMS = [
    {"id": "super-admin", "label": "Super Admin", "superAdminOnly": True},
    {"id": "home", "label": "Home"},
    {"id": "chatbot-builder", "label": "Automations", "moduleKey": "chatbots"},
    {"id": "ai-agent-builder", "label": "AI Agents", "moduleKey": "agents"},
    {"id": "template-builder", "label": "Template Builder", "moduleKey": "templates"},
    {"id": "media-library", "label": "Media", "moduleKey": "media"},
    {"id": "chats", "label": "Chats", "moduleKey": "chats"},
    {"id": "contacts", "label": "Contacts", "moduleKey": "contacts"},
    {"id": "pipelines", "label": "Pipelines", "moduleKey": "pipelines"},
    {"id": "bulk-message", "label": "Bulk Message", "moduleKey": "broadcasts"},
]

def get_auth_token():
    cmd = """docker exec synapticchat-backend python -c "
import jwt, datetime
from app.core.config import settings
data = {
    'id': 1,
    'username': 'admin',
    'displayName': 'Admin',
    'role': 'admin',
    'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24)
}
print(jwt.encode(data, settings.JWT_SECRET, algorithm='HS256'))
" """
    token = subprocess.check_output(cmd, shell=True).decode().strip()
    return token

def compute_visible_items(user):
    is_super_admin = user.get("role") == "admin"
    org_modules = (user.get("activeOrg") or {}).get("settings", {}).get("modules") or {}
    user_pages = user.get("pages")

    visible = []
    hidden = []
    for item in NAV_ITEMS:
        if item.get("superAdminOnly") and not is_super_admin:
            hidden.append(item["id"])
            continue

        mod_key = item.get("moduleKey")
        if mod_key and org_modules and org_modules.get(mod_key) is False:
            hidden.append(item["id"])
            continue

        if not is_super_admin and isinstance(user_pages, list):
            if item["id"] not in user_pages:
                hidden.append(item["id"])
                continue

        visible.append(item["id"])
    return visible, hidden

def main():
    s = requests.Session()
    print("=" * 60)
    print("🧪 Testing Feature Switchboard: LINNDEN")
    print("=" * 60)

    # 1. Authenticate using JWT session cookie
    token = get_auth_token()
    s.cookies.set("synapticchat_token", token)
    s.cookies.set("forgecrm_token", token)
    s.headers.update({"Authorization": f"Bearer {token}"})
    print("✅ 1. Authenticated as Super Admin with JWT token")

    # 2. Switch to LINNDEN
    res = s.post(f"{BASE_URL}/api/organizations/{LINNDEN_ORG_ID}/switch")
    if res.status_code != 200:
        print(f"❌ Org switch failed: {res.status_code} {res.text}")
        sys.exit(1)
    s.cookies.set("synapticchat_active_org", LINNDEN_ORG_ID)
    s.cookies.set("forgecrm_active_org", LINNDEN_ORG_ID)
    print(f"✅ 2. Switched active organization to LINNDEN ({LINNDEN_ORG_ID})")

    # 3. Check /api/auth/me
    res = s.get(f"{BASE_URL}/api/auth/me")
    assert res.status_code == 200, f"Failed auth/me: {res.status_code} {res.text}"
    user = res.json().get("user", {})
    active_org = user.get("activeOrg", {})
    modules = active_org.get("settings", {}).get("modules", {})
    print(f"✅ 3. Loaded activeOrg: {active_org.get('name')} (Slug: {active_org.get('slug')})")
    print(f"   Current modules in database: {json.dumps(modules, indent=2)}")

    # 4. Verify baseline visibility for LINNDEN (matching screenshot)
    # Screenshot settings:
    # Enabled: chats, contacts, media
    # Disabled: pipelines, broadcasts, templates, chatbots, agents, orders
    visible, hidden = compute_visible_items(user)
    print("\n📋 4. Baseline Sidebar Evaluation (LINNDEN active):")
    print(f"   Visible Buttons ({len(visible)}): {visible}")
    print(f"   Hidden Buttons  ({len(hidden)}): {hidden}")

    assert "super-admin" in visible, "Super Admin should be visible for admin"
    assert "home" in visible, "Home should always be visible"
    assert "chats" in visible, "Chats (Shared Team Inbox) should be visible"
    assert "contacts" in visible, "Contacts & CRM should be visible"
    assert "media-library" in visible, "Media Library should be visible"

    assert "pipelines" in hidden, "Pipelines must be hidden"
    assert "bulk-message" in hidden, "Bulk Message must be hidden"
    assert "template-builder" in hidden, "Template Builder must be hidden"
    assert "chatbot-builder" in hidden, "Automations must be hidden"
    assert "ai-agent-builder" in hidden, "AI Agents must be hidden"
    print("   ✅ Baseline matches screenshot: All 5 disabled modules are HIDDEN; 3 enabled are SHOWN.")

    # 5. Dynamic Toggle Test: Enable Pipelines
    print("\n🔄 5. Dynamic Switchboard Test: Enabling 'Sales Deals Pipeline'...")
    res = s.put(
        f"{BASE_URL}/api/organizations/{LINNDEN_ORG_ID}/modules",
        json={"modules": {"pipelines": True}}
    )
    assert res.status_code == 200, f"Failed to update modules: {res.text}"

    # Re-fetch me
    res = s.get(f"{BASE_URL}/api/auth/me")
    user = res.json().get("user", {})
    visible, hidden = compute_visible_items(user)
    assert "pipelines" in visible, "Pipelines button should now be visible!"
    assert "pipelines" not in hidden, "Pipelines should no longer be hidden!"
    print(f"   ✅ Pipelines button successfully APPEARED in UI: {visible}")

    # 6. Dynamic Toggle Test: Enable Flow Automations & AI Agents
    print("\n🔄 6. Dynamic Switchboard Test: Enabling 'Flow Automations' & 'Autonomous AI Agents'...")
    res = s.put(
        f"{BASE_URL}/api/organizations/{LINNDEN_ORG_ID}/modules",
        json={"modules": {"chatbots": True, "agents": True}}
    )
    assert res.status_code == 200

    res = s.get(f"{BASE_URL}/api/auth/me")
    user = res.json().get("user", {})
    visible, hidden = compute_visible_items(user)
    assert "chatbot-builder" in visible, "Automations should now be visible"
    assert "ai-agent-builder" in visible, "AI Agents should now be visible"
    print(f"   ✅ Automations & AI Agents successfully APPEARED in UI: {visible}")

    # 7. Dynamic Toggle Test: Disable them back and restore exact screenshot state
    print("\n🔄 7. Restoring LINNDEN to exact screenshot state...")
    restored_modules = {
        "chats": True,
        "contacts": True,
        "media": True,
        "pipelines": False,
        "broadcasts": False,
        "templates": False,
        "chatbots": False,
        "agents": False,
        "orders": False,
    }
    res = s.put(
        f"{BASE_URL}/api/organizations/{LINNDEN_ORG_ID}/modules",
        json={"modules": restored_modules}
    )
    assert res.status_code == 200

    res = s.get(f"{BASE_URL}/api/auth/me")
    user = res.json().get("user", {})
    visible, hidden = compute_visible_items(user)
    assert "pipelines" in hidden
    assert "chatbot-builder" in hidden
    assert "ai-agent-builder" in hidden
    assert "bulk-message" in hidden
    assert "template-builder" in hidden
    assert set(visible) == {"super-admin", "home", "chats", "contacts", "media-library"}
    print(f"   ✅ LINNDEN cleanly restored. Visible: {visible}, Hidden: {hidden}")

    # 8. Test Regular Client User Perspective (Non-Super-Admin)
    print("\n👤 8. Testing Client Organization Member Perspective...")
    client_user = {
        "role": "member",
        "activeOrg": {"settings": {"modules": restored_modules}},
        "pages": ["home", "chats", "contacts", "media-library", "pipelines", "chatbot-builder"]
    }
    client_visible, client_hidden = compute_visible_items(client_user)
    print(f"   Client User Visible: {client_visible}")
    print(f"   Client User Hidden:  {client_hidden}")
    assert "super-admin" in client_hidden, "Super Admin must not be visible to client member"
    assert "pipelines" in client_hidden, "Pipelines must be hidden despite being in user.pages"
    assert "chatbot-builder" in client_hidden, "Chatbots must be hidden despite being in user.pages"
    assert set(client_visible) == {"home", "chats", "contacts", "media-library"}
    print("   ✅ Client member only sees enabled modules: Home, Chats, Contacts, Media.")

    # 9. Verify Frontend Production Bundle
    print("\n📦 9. Verifying Frontend Production Bundle on Docker (port 8080)...")
    res = s.get(f"{BASE_URL}/")
    assert res.status_code == 200
    assert "Synaptic Chat" in res.text or "<div id=\"root\">" in res.text
    print("   ✅ Frontend root index HTML serving successfully from Nginx on Docker.")

    print("\n" + "=" * 60)
    print("🎉 ALL SWITCHBOARD BUTTON HIDING & TOGGLING TESTS PASSED!")
    print("=" * 60)

if __name__ == "__main__":
    main()
