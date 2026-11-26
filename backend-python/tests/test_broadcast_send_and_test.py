import os
import sys
import unittest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.routers.broadcasts import _parse_json, router, test_broadcast, BroadcastTestRequest
from app.services.message_sender import dispatch_send_task


class TestBroadcastParsingAndRoutes(unittest.TestCase):
    def test_parse_json_handles_strings_and_defaults(self):
        self.assertEqual(_parse_json('{"1": "name"}', {}), {"1": "name"})
        self.assertEqual(_parse_json('[{"contact_number": "9198"}]', []), [{"contact_number": "9198"}])
        self.assertEqual(_parse_json({"1": "name"}, {}), {"1": "name"})
        self.assertEqual(_parse_json("bad-json", {}), {})
        self.assertEqual(_parse_json('["a"]', {}), {})

    def test_broadcast_test_route_is_registered(self):
        paths = {(r.path, tuple(sorted(r.methods))) for r in router.routes}
        self.assertIn(("/api/broadcasts/{broadcast_id}/test", ("POST",)), paths)


class TestDispatchSendBroadcastLogColumn(unittest.IsolatedAsyncioTestCase):
    async def test_dispatch_updates_wa_message_id_column(self):
        mock_execute = AsyncMock(return_value="UPDATE 1")
        with patch("app.services.message_sender.meta_client.send_template", new=AsyncMock(return_value={"messages": [{"id": "wamid.123"}]})), \
             patch("app.services.message_sender.mark_sent", new=AsyncMock()), \
             patch("app.services.message_sender.mark_account_health", new=AsyncMock()), \
             patch("app.services.message_sender.db.execute", mock_execute):
            await dispatch_send_task(
                kind="template",
                account={"id": 10, "accessToken": "tok", "phoneNumberId": "pid"},
                to="918072840065",
                local_message_id="local-1",
                payload={"name": "msg_1", "languageCode": "en", "components": []},
                origin_ref={"kind": "broadcast_log", "id": 5},
            )

        sql = mock_execute.call_args[0][0]
        self.assertIn("wa_message_id = $1", sql)
        self.assertNotIn("wamid =", sql)

    async def test_test_broadcast_sends_and_returns_logs(self):
        fake_broadcast = {
            "id": 2,
            "from_number": "919979745575",
            "message_type": "template",
            "variable_mapping": '{"1": "name"}',
            "media_library_id": None,
            "t_id": 12,
            "t_name": "msg_1",
            "t_language": "en",
            "t_body": "Hi {{1}}",
            "t_header_type": "NONE",
            "t_header_text": None,
            "t_footer": None,
            "t_buttons": "[]",
            "t_samples": '{"1": "User"}',
            "t_header_media_library_id": None,
        }
        mock_dispatch = AsyncMock()
        with patch("app.routers.broadcasts._fetch_broadcast_with_template", new=AsyncMock(return_value=fake_broadcast)), \
             patch("app.routers.broadcasts.resolve_account", new=AsyncMock(return_value=({"id": 10, "phoneNumberId": "pid", "accessToken": "tok"}, None))), \
             patch("app.routers.broadcasts.db.fetchval", new=AsyncMock(return_value=99)), \
             patch("app.routers.broadcasts.db.execute", new=AsyncMock()), \
             patch("app.routers.broadcasts.insert_pending_row", new=AsyncMock(return_value="local-2")), \
             patch("app.routers.broadcasts.dispatch_send_task", mock_dispatch), \
             patch("app.routers.broadcasts.get_broadcast_with_logs", new=AsyncMock(return_value={"id": 2, "logs": [{"id": 99, "action": "TEST"}], "statusRollup": {}})):
            res = await test_broadcast(
                2,
                BroadcastTestRequest(test_number="918072840065"),
                tenant_ctx={"org_id": "381bc6a0-f5d2-4e30-b341-6a361a627a99"},
                user={"id": 1},
            )

        self.assertEqual(res["id"], 2)
        self.assertEqual(mock_dispatch.await_count, 1)


if __name__ == "__main__":
    unittest.main()
