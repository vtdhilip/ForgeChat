import os
import sys
import unittest
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.middleware.auth import is_tenant_admin, assert_wa_access  # noqa: E402
from app.routers.messages import get_numbers  # noqa: E402
from app.engine.automation_engine import execute_message_node, evaluate_triggers  # noqa: E402


class TestTenantNumbersAndTriggers(unittest.IsolatedAsyncioTestCase):
    def test_org_owner_with_bda_sales_role_is_tenant_admin(self):
        user = {"id": 3, "role": "bda_sales"}
        owner_ctx = {"org_id": "381bc6a0-f5d2-4e30-b341-6a361a627a99", "org_role": "owner", "user": user}
        member_ctx = {"org_id": "381bc6a0-f5d2-4e30-b341-6a361a627a99", "org_role": "member", "user": user}

        self.assertTrue(is_tenant_admin(user, owner_ctx))
        self.assertFalse(is_tenant_admin(user, member_ctx))
        self.assertTrue(is_tenant_admin({"id": 1, "role": "admin"}, member_ctx))

    async def test_assert_wa_access_scopes_to_active_org_and_allows_org_owner(self):
        user = {"id": 3, "role": "bda_sales"}
        owner_ctx = {"org_id": "381bc6a0-f5d2-4e30-b341-6a361a627a99", "org_role": "owner", "user": user}

        with patch("app.middleware.auth.db.fetchrow", new=AsyncMock(return_value={"?column?": 1})):
            self.assertTrue(await assert_wa_access(user, "919979745575", owner_ctx))

        with patch("app.middleware.auth.db.fetchrow", new=AsyncMock(return_value=None)):
            with self.assertRaises(HTTPException) as ctx:
                await assert_wa_access(user, "918248933981", owner_ctx)
        self.assertEqual(ctx.exception.status_code, 403)

    async def test_get_numbers_filters_by_org_id_and_allows_org_owner(self):
        user = {"id": 3, "role": "bda_sales"}
        owner_ctx = {"org_id": "381bc6a0-f5d2-4e30-b341-6a361a627a99", "org_role": "owner", "user": user}

        acc_rows = [{
            "wa_number": "919979745575",
            "account_name": "Next Click Global",
            "last_message_time": None,
            "message_count": 1,
        }]
        with patch("app.routers.messages.db.fetch", new=AsyncMock(side_effect=[acc_rows, [], [], []])) as mock_fetch:
            res = await get_numbers(tenant_ctx=owner_ctx)

        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["wa_number"], "919979745575")
        first_call_sql, *first_call_params = mock_fetch.call_args_list[0].args
        self.assertIn("org_id", first_call_sql)
        self.assertIn("381bc6a0-f5d2-4e30-b341-6a361a627a99", first_call_params)
        self.assertNotIn("assigned_user_id", first_call_sql)

    async def test_execute_message_node_unpacks_resolve_account_tuple(self):
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value={"id": 1})
        node = {"id": "n1", "type": "message", "messageMode": "direct", "directData": {"body": "Hello!"}}
        context = {"contact_number": "918072840065", "org_id": "org-1", "trigger_data": {"wa_number": "919979745575"}}
        acc = {"id": 10, "phoneNumberId": "1415669018300896", "displayPhoneNumber": "919979745575", "accessToken": "tok"}

        with (
            patch("app.engine.automation_engine.resolve_account", new=AsyncMock(return_value=(acc, None))),
            patch("app.engine.automation_engine.insert_pending_row", new=AsyncMock(return_value="local-1")),
            patch("app.engine.automation_engine.dispatch_send_task", new=AsyncMock()) as mock_dispatch,
        ):
            step = await execute_message_node(conn, 99, node, context)

        self.assertEqual(step["id"], 1)
        self.assertEqual(mock_dispatch.call_args.kwargs["kind"], "text")
        self.assertEqual(mock_dispatch.call_args.kwargs["to"], "918072840065")
        self.assertEqual(mock_dispatch.call_args.kwargs["local_message_id"], "local-1")

    async def test_evaluate_triggers_scopes_chatbots_to_message_org_id(self):
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=[])
        conn.fetchrow = AsyncMock(return_value=None)

        class _Ctx:
            async def __aenter__(self):
                return conn
            async def __aexit__(self, *args):
                return False

        with patch("app.engine.automation_engine.get_db", return_value=_Ctx()):
            await evaluate_triggers({
                "org_id": "381bc6a0-f5d2-4e30-b341-6a361a627a99",
                "wa_number": "919979745575",
                "contact_number": "918072840065",
                "message_body": "Hi",
            })

        bot_sql, *bot_params = conn.fetch.call_args.args
        self.assertIn("org_id", bot_sql)
        self.assertEqual(bot_params, ["381bc6a0-f5d2-4e30-b341-6a361a627a99"])


if __name__ == "__main__":
    unittest.main()
