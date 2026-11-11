import os
import sys
import unittest
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.permissions import effective_pages  # noqa: E402
from app.middleware.auth import is_tenant_admin  # noqa: E402
from app.routers.organizations import OnboardRequest, super_admin_onboard  # noqa: E402
from app.routers.users import UserCreate, create_user, list_users  # noqa: E402


class _Tx:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


class _Pool:
    def __init__(self, conn):
        self._conn = conn

    def acquire(self):
        conn = self._conn

        class _Acq:
            async def __aenter__(self_inner):
                return conn

            async def __aexit__(self_inner, *args):
                return False

        return _Acq()


class TestOrgAdminOnboarding(unittest.IsolatedAsyncioTestCase):
    def test_effective_pages_and_tenant_admin_for_org_admin(self):
        user = {"id": 3, "role": "org_admin", "permissions": None}
        active_org = {
            "id": "org-1",
            "role": "owner",
            "settings": {
                "modules": {"chats": True, "contacts": True, "pipelines": True, "orders": False},
                "features": {"allow_wa_config": True},
            },
        }
        pages = effective_pages(user, active_org)
        self.assertTrue(is_tenant_admin(user, {"org_id": "org-1", "org_role": "owner", "user": user}))
        self.assertIn("admin-settings:users", pages)
        self.assertIn("admin-settings:whatsapp-accounts", pages)
        self.assertIn("pipelines", pages)

    async def test_manual_onboarding_creates_user_as_org_admin(self):
        conn = AsyncMock()
        conn.transaction = lambda: _Tx()
        conn.fetchrow = AsyncMock(
            side_effect=[
                {"id": "381bc6a0-f5d2-4e30-b341-6a361a627a99", "name": "Acme", "slug": "acme"},
                {"id": 99},
            ]
        )
        conn.execute = AsyncMock()

        payload = OnboardRequest(
            name="Acme",
            contactEmail="owner@acme.com",
            adminUsername="acmeadmin",
            adminPassword="Secret123!",
        )
        with (
            patch("app.routers.organizations.db.fetchrow", new=AsyncMock(return_value=None)),
            patch("app.routers.organizations.db.pool", _Pool(conn)),
            patch("app.routers.organizations.hash_password", return_value="hashed"),
        ):
            res = await super_admin_onboard(payload, user={"id": 1, "role": "admin"})

        self.assertTrue(res["success"])
        user_insert_sql = conn.fetchrow.call_args_list[1].args[0]
        self.assertIn("'org_admin'", user_insert_sql)
        self.assertNotIn("'bda_sales'", user_insert_sql)

    async def test_org_admin_cannot_create_super_admin_and_list_is_org_scoped(self):
        org_admin_ctx = {
            "org_id": "381bc6a0-f5d2-4e30-b341-6a361a627a99",
            "org_role": "owner",
            "user": {"id": 3, "role": "org_admin"},
        }
        with self.assertRaises(HTTPException) as ctx:
            await create_user(
                UserCreate(username="bad", email="bad@x.com", displayName="Bad", role="admin"),
                tenant_ctx=org_admin_ctx,
            )
        self.assertEqual(ctx.exception.status_code, 403)

        with (
            patch("app.routers.users.db.fetch", new=AsyncMock(return_value=[])) as mock_fetch,
            patch("app.routers.users.load_assignments", new=AsyncMock(return_value={})),
        ):
            await list_users(tenant_ctx=org_admin_ctx)

        list_sql, *list_params = mock_fetch.call_args.args
        self.assertIn("organization_members", list_sql)
        self.assertEqual(list_params, ["381bc6a0-f5d2-4e30-b341-6a361a627a99"])


if __name__ == "__main__":
    unittest.main()
