import os
import sys
import json
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.integrations.meta_client import MetaAPIError
from app.routers.templates import build_payload, _match_template

class TestMatchTemplate(unittest.TestCase):
    def setUp(self):
        self.templates = [
            {"id": "1001", "name": "msg_1", "language": "en", "status": "APPROVED"},
            {"id": "1002", "name": "msg_1", "language": "es_ES", "status": "PENDING"},
            {"id": "1003", "name": "welcome", "language": "en_US", "status": "APPROVED"}
        ]

    def test_exact_match(self):
        m = _match_template(self.templates, "msg_1", "en")
        self.assertIsNotNone(m)
        self.assertEqual(m["id"], "1001")

    def test_base_language_match(self):
        # Local is es, Meta is es_ES
        m = _match_template(self.templates, "msg_1", "es")
        self.assertIsNotNone(m)
        self.assertEqual(m["id"], "1002")

        # Local is en, Meta is en_US for welcome
        m2 = _match_template(self.templates, "welcome", "en")
        self.assertIsNotNone(m2)
        self.assertEqual(m2["id"], "1003")

    def test_different_language_no_match(self):
        # Local is fr, none exists
        m = _match_template(self.templates, "msg_1", "fr")
        self.assertIsNone(m)

    def test_different_name_no_match(self):
        m = _match_template(self.templates, "nonexistent", "en")
        self.assertIsNone(m)

class TestMetaAPIError(unittest.TestCase):
    def test_meta_api_error_user_title_and_msg(self):
        err_payload = {
            "error": {
                "message": "Invalid parameter",
                "code": 100,
                "error_subcode": 2388091,
                "error_user_title": "Template Name Already Exists",
                "error_user_msg": "A template with this name and language already exists."
            }
        }
        err = MetaAPIError(400, err_payload)
        self.assertEqual(err.status_code, 400)
        self.assertEqual(err.code, 100)
        self.assertEqual(err.subcode, 2388091)
        self.assertTrue(err.is_duplicate)
        self.assertIn("Meta 400: Invalid parameter", str(err))
        self.assertIn("(Template Name Already Exists)", str(err))
        self.assertIn("A template with this name and language already exists.", str(err))

    def test_meta_api_error_error_data_details(self):
        err_payload = {
            "error": {
                "message": "Invalid parameter",
                "code": 100,
                "error_data": {
                    "details": "A template with name msg_1 and language en already exists."
                }
            }
        }
        err = MetaAPIError(400, err_payload)
        self.assertTrue(err.is_duplicate)
        self.assertIn("A template with name msg_1 and language en already exists.", str(err))

    def test_meta_api_error_non_duplicate(self):
        err_payload = {
            "error": {
                "message": "Session has expired",
                "code": 190
            }
        }
        err = MetaAPIError(401, err_payload)
        self.assertFalse(err.is_duplicate)
        self.assertEqual(err.status_code, 401)
        self.assertEqual(str(err), "Meta 401: Session has expired")


class TestBuildPayload(unittest.TestCase):
    def test_build_payload_marketing_with_samples(self):
        data = {
            "name": "msg_1 ",
            "category": "MARKETING",
            "language": "en ",
            "body": "Hi {{1}}, welcome!",
            "samples": {"1": "Dhilip"},
            "allow_category_change": True
        }
        payload = build_payload(data)
        self.assertEqual(payload["name"], "msg_1")
        self.assertEqual(payload["language"], "en")
        self.assertEqual(payload["category"], "MARKETING")
        self.assertEqual(payload["allow_category_change"], True)
        self.assertEqual(len(payload["components"]), 1)
        body_comp = payload["components"][0]
        self.assertEqual(body_comp["type"], "BODY")
        self.assertEqual(body_comp["example"]["body_text"], [["Dhilip"]])

    def test_build_payload_omits_none_allow_category_change(self):
        data = {
            "name": "msg_2",
            "category": "UTILITY",
            "language": "en",
            "body": "Your order is ready.",
            "allow_category_change": None
        }
        payload = build_payload(data)
        self.assertNotIn("allow_category_change", payload)

    def test_build_payload_omits_allow_category_change_for_auth(self):
        data = {
            "name": "otp_template",
            "category": "AUTHENTICATION",
            "language": "en",
            "body": "Your code is {{1}}.",
            "samples": {1: "123456"},
            "allow_category_change": True,
            "code_expiry_minutes": 10
        }
        payload = build_payload(data)
        self.assertNotIn("allow_category_change", payload)
        self.assertEqual(payload["category"], "AUTHENTICATION")
        footer_comp = next((c for c in payload["components"] if c["type"] == "FOOTER"), None)
        self.assertIsNotNone(footer_comp)
        self.assertEqual(footer_comp["code_expiration_minutes"], 10)

    def test_build_payload_handles_stringified_json_inputs(self):
        data = {
            "name": "msg_json",
            "category": "MARKETING",
            "language": "en",
            "body": "Hello {{1}}",
            "samples": json.dumps({"1": "John"}),
            "buttons": json.dumps([{"type": "QUICK_REPLY", "text": "Unsubscribe"}])
        }
        payload = build_payload(data)
        body_comp = next((c for c in payload["components"] if c["type"] == "BODY"), None)
        self.assertEqual(body_comp["example"]["body_text"], [["John"]])
        btn_comp = next((c for c in payload["components"] if c["type"] == "BUTTONS"), None)
        self.assertIsNotNone(btn_comp)
        self.assertEqual(btn_comp["buttons"][0]["text"], "Unsubscribe")

if __name__ == '__main__':
    unittest.main()
