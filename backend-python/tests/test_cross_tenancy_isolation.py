import asyncio
import httpx
from app.core.security import create_access_token
from app.core.database import db

async def run_tests():
    print("=== STARTING CROSS-TENANT ISOLATION AUDIT ===")

    await db.connect()
    user_linnden = await db.fetchrow("SELECT * FROM coexistence.forgecrm_users WHERE username = 'admin'")
    user_ncg = await db.fetchrow("SELECT * FROM coexistence.forgecrm_users WHERE username = 'nextclickglobal'")

    token_linnden = create_access_token({
        "id": user_linnden["id"],
        "username": user_linnden["username"],
        "displayName": user_linnden["display_name"],
        "role": user_linnden["role"]
    })

    token_ncg = create_access_token({
        "id": user_ncg["id"],
        "username": user_ncg["username"],
        "displayName": user_ncg["display_name"],
        "role": user_ncg["role"]
    })

    headers_linnden = {"Authorization": f"Bearer {token_linnden}"}
    headers_ncg = {"Authorization": f"Bearer {token_ncg}"}

    client = httpx.AsyncClient(base_url="http://localhost:3011", timeout=30.0)

    errors = []

    async def check_endpoint(name, path, linnden_expected_min, ncg_expected_max):
        r_linnden = await client.get(path, headers=headers_linnden)
        r_ncg = await client.get(path, headers=headers_ncg)

        if r_linnden.status_code != 200:
            errors.append(f"[{name}] Linnden GET {path} returned status {r_linnden.status_code}: {r_linnden.text}")
            return
        if r_ncg.status_code != 200:
            errors.append(f"[{name}] NCG GET {path} returned status {r_ncg.status_code}: {r_ncg.text}")
            return

        data_linnden = r_linnden.json()
        data_ncg = r_ncg.json()

        items_linnden = data_linnden if isinstance(data_linnden, list) else data_linnden.get("items", data_linnden.get("chatbots", data_linnden.get("data", [])))
        items_ncg = data_ncg if isinstance(data_ncg, list) else data_ncg.get("items", data_ncg.get("chatbots", data_ncg.get("data", [])))

        count_l = len(items_linnden) if isinstance(items_linnden, list) else 1
        count_n = len(items_ncg) if isinstance(items_ncg, list) else 1

        print(f"[{name}] LINNDEN count: {count_l} (min {linnden_expected_min}) | NCG count: {count_n} (max {ncg_expected_max})")

        if count_l < linnden_expected_min:
            errors.append(f"[{name}] LINNDEN count {count_l} < expected min {linnden_expected_min}")
        if count_n > ncg_expected_max:
            errors.append(f"[{name}] NCG count {count_n} > expected max {ncg_expected_max} (DATA LEAK!)")

    # 1. Automations (Chatbots)
    await check_endpoint("Automations", "/api/chatbots", linnden_expected_min=1, ncg_expected_max=0)

    # 2. Message Templates
    await check_endpoint("Message Templates", "/api/templates", linnden_expected_min=1, ncg_expected_max=0)

    # 3. Broadcasts
    await check_endpoint("Broadcasts", "/api/broadcasts", linnden_expected_min=0, ncg_expected_max=0)

    # 4. Pipelines: both have their own pipeline, so check disjoint IDs
    r_l_pipe = await client.get("/api/pipelines", headers=headers_linnden)
    r_n_pipe = await client.get("/api/pipelines", headers=headers_ncg)
    if r_l_pipe.status_code != 200 or r_n_pipe.status_code != 200:
        errors.append(f"[Pipelines] Fetch error L:{r_l_pipe.status_code} N:{r_n_pipe.status_code}")
    else:
        l_ids = {p["id"] for p in r_l_pipe.json()}
        n_ids = {p["id"] for p in r_n_pipe.json()}
        overlap = l_ids.intersection(n_ids)
        print(f"[Pipelines] LINNDEN pipelines: {l_ids} | NCG pipelines: {n_ids} | Overlap: {overlap}")
        if overlap:
            errors.append(f"[Pipelines] Overlapping pipelines between tenants: {overlap} (DATA LEAK!)")

    # 5. Media Library
    await check_endpoint("Media Library", "/api/media-library", linnden_expected_min=0, ncg_expected_max=0)

    # 6. AI Agent Builder
    await check_endpoint("AI Agents", "/api/agents", linnden_expected_min=0, ncg_expected_max=0)

    # 7. AI Models
    await check_endpoint("AI Models", "/api/ai-models", linnden_expected_min=0, ncg_expected_max=0)

    # 8. Categories
    await check_endpoint("Categories", "/api/categories", linnden_expected_min=0, ncg_expected_max=0)

    # 9. Tags
    await check_endpoint("Tags", "/api/tags", linnden_expected_min=0, ncg_expected_max=0)

    # 10. Contact Fields
    await check_endpoint("Contact Fields", "/api/contact-fields", linnden_expected_min=1, ncg_expected_max=0)

    # 11. WhatsApp Accounts
    await check_endpoint("WhatsApp Accounts", "/api/whatsapp-accounts", linnden_expected_min=1, ncg_expected_max=0)

    # 12. Dashboard Stats
    r_l_dash = await client.get("/api/dashboard", headers=headers_linnden)
    r_n_dash = await client.get("/api/dashboard", headers=headers_ncg)
    print(f"[Dashboard Stats] LINNDEN status: {r_l_dash.status_code} | NCG status: {r_n_dash.status_code}")
    if r_l_dash.status_code != 200:
        errors.append(f"[Dashboard] Linnden status {r_l_dash.status_code}")
    if r_n_dash.status_code != 200:
        errors.append(f"[Dashboard] NCG status {r_n_dash.status_code}")
    else:
        ncg_dash = r_n_dash.json()
        print(f"[Dashboard Stats] NCG summary: contacts={ncg_dash.get('totalContacts')}, automations={ncg_dash.get('activeAutomations')}")
        if ncg_dash.get("activeAutomations", 0) > 0:
            errors.append(f"[Dashboard Stats] NCG sees {ncg_dash.get('activeAutomations')} active automations from LINNDEN! (DATA LEAK!)")

    # 13. Team Members
    await check_endpoint("Team Members", "/api/team-members", linnden_expected_min=0, ncg_expected_max=0)

    # 14. WhatsApp Number Access & Contacts Isolation
    wa_linnden = await db.fetchval("SELECT display_phone_number FROM coexistence.whatsapp_accounts WHERE org_id = '26e7b672-5558-4a4b-9aed-926c6b71d995' LIMIT 1")
    if wa_linnden:
        clean_wa = "".join(filter(str.isdigit, wa_linnden))
        r_l_contacts = await client.get(f"/api/contacts?waNumber={clean_wa}", headers=headers_linnden)
        r_n_contacts = await client.get(f"/api/contacts?waNumber={clean_wa}", headers=headers_ncg)
        print(f"[Contacts/Chat Access] Linnden access to own number: {r_l_contacts.status_code} | NCG access to Linnden number: {r_n_contacts.status_code}")
        if r_l_contacts.status_code != 200:
            errors.append(f"[Contacts/Chat Access] Linnden failed to access own contacts: {r_l_contacts.status_code}")
        if r_n_contacts.status_code != 403:
            errors.append(f"[Contacts/Chat Access] NCG was not rejected with 403 when accessing Linnden number! Status: {r_n_contacts.status_code} (DATA LEAK!)")

    # 15. Cross-tenant modification attempt: NCG tries to GET Linnden's chatbot
    chatbot_id = await db.fetchval("SELECT id FROM coexistence.chatbots WHERE org_id = '26e7b672-5558-4a4b-9aed-926c6b71d995' LIMIT 1")
    if chatbot_id:
        r_hack = await client.get(f"/api/chatbots/{chatbot_id}", headers=headers_ncg)
        print(f"[Cross-Tenant Read] NCG access to Linnden chatbot {chatbot_id}: status={r_hack.status_code}")
        if r_hack.status_code != 404:
            errors.append(f"[Cross-Tenant Read] NCG was able to access Linnden chatbot {chatbot_id}! Status: {r_hack.status_code}")

    # 16. Cross-tenant modification attempt: NCG tries to GET Linnden's template
    template_id = await db.fetchval("SELECT id FROM coexistence.message_templates WHERE org_id = '26e7b672-5558-4a4b-9aed-926c6b71d995' LIMIT 1")
    if template_id:
        r_hack_tpl = await client.get(f"/api/templates/{template_id}", headers=headers_ncg)
        print(f"[Cross-Tenant Read] NCG access to Linnden template {template_id}: status={r_hack_tpl.status_code}")
        if r_hack_tpl.status_code != 404:
            errors.append(f"[Cross-Tenant Read] NCG was able to access Linnden template {template_id}! Status: {r_hack_tpl.status_code}")

    # 17. Cross-tenant modification attempt: NCG tries to GET Linnden's pipeline
    pipeline_id = await db.fetchval("SELECT id FROM coexistence.pipelines WHERE org_id = '26e7b672-5558-4a4b-9aed-926c6b71d995' LIMIT 1")
    if pipeline_id:
        r_hack_pipe = await client.get(f"/api/pipelines/{pipeline_id}/deals", headers=headers_ncg)
        print(f"[Cross-Tenant Read] NCG access to Linnden pipeline {pipeline_id} deals: status={r_hack_pipe.status_code}")
        if r_hack_pipe.status_code != 404:
            errors.append(f"[Cross-Tenant Read] NCG was able to access Linnden pipeline {pipeline_id} deals! Status: {r_hack_pipe.status_code}")

    await client.aclose()
    await db.disconnect()

    print("\n=== AUDIT RESULTS ===")
    if errors:
        print(f"FAILED with {len(errors)} errors:")
        for err in errors:
            print(f"  - {err}")
        return False
    else:
        print("ALL TESTS PASSED! Strict multi-tenant isolation confirmed across all tabs and endpoints.")
        return True

if __name__ == "__main__":
    success = asyncio.run(run_tests())
    exit(0 if success else 1)
