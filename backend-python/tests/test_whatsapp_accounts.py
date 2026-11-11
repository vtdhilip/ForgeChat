import unittest
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException

from app.routers.whatsapp_accounts import (
    WhatsAppAccountCreate,
    WhatsAppAccountUpdate,
    create_account,
    update_account,
)


class FakeUniqueViolation(Exception):
    def __init__(self, message: str, constraint_name: str):
        super().__init__(message)
        self.sqlstate = "23505"
        self.constraint_name = constraint_name


class TestWhatsAppAccountsUniqueHandling(unittest.IsolatedAsyncioTestCase):
    async def test_create_reports_phone_id_duplicate_for_phone_constraint(self):
        payload = WhatsAppAccountCreate(
            phoneNumberId="1184958958042348",
            wabaId="1781822016277712",
            accessToken="tok_123",
            verifyToken="vtok_123",
        )
        tenant_ctx = {"org_id": "c7a2249f-e0d5-423d-b82a-06fc901277a5", "user": {"role": "admin"}}
        err = FakeUniqueViolation(
            'duplicate key value violates unique constraint "whatsapp_accounts_phone_number_id_key"',
            "whatsapp_accounts_phone_number_id_key",
        )

        with (
            patch("app.routers.whatsapp_accounts.db.fetchval", new=AsyncMock(return_value=0)),
            patch("app.routers.whatsapp_accounts.fetch_phone_meta", new=AsyncMock(return_value={"verified_name": "Next Click Global", "display_phone_number": "+91 99797 45575"})),
            patch("app.routers.whatsapp_accounts.encrypt", side_effect=lambda v: f"enc:{v}"),
            patch("app.routers.whatsapp_accounts.db.fetchrow", new=AsyncMock(side_effect=err)),
        ):
            with self.assertRaises(HTTPException) as ctx:
                await create_account(payload=payload, tenant_ctx=tenant_ctx, admin={"role": "admin"})

        self.assertEqual(ctx.exception.status_code, 409)
        self.assertEqual(ctx.exception.detail, "This Phone Number ID is already connected")

    async def test_create_reports_org_limit_for_per_org_constraint(self):
        payload = WhatsAppAccountCreate(
            phoneNumberId="999888777666555",
            wabaId="1781822016277712",
            accessToken="tok_123",
            verifyToken="vtok_123",
        )
        tenant_ctx = {"org_id": "c7a2249f-e0d5-423d-b82a-06fc901277a5", "user": {"role": "admin"}}
        err = FakeUniqueViolation(
            'duplicate key value violates unique constraint "idx_whatsapp_accounts_one_per_org"',
            "idx_whatsapp_accounts_one_per_org",
        )

        with (
            patch("app.routers.whatsapp_accounts.db.fetchval", new=AsyncMock(return_value=0)),
            patch("app.routers.whatsapp_accounts.fetch_phone_meta", new=AsyncMock(return_value={"verified_name": "Next Click Global", "display_phone_number": "+91 99797 45575"})),
            patch("app.routers.whatsapp_accounts.encrypt", side_effect=lambda v: f"enc:{v}"),
            patch("app.routers.whatsapp_accounts.db.fetchrow", new=AsyncMock(side_effect=err)),
        ):
            with self.assertRaises(HTTPException) as ctx:
                await create_account(payload=payload, tenant_ctx=tenant_ctx, admin={"role": "admin"})

        self.assertEqual(ctx.exception.status_code, 409)
        self.assertEqual(
            ctx.exception.detail,
            "Only one WhatsApp Business account is allowed per organization. Edit the existing account instead.",
        )

    async def test_update_reports_org_limit_for_default_constraint(self):
        payload = WhatsAppAccountUpdate(wabaId="1781822016277712")
        tenant_ctx = {"org_id": "c7a2249f-e0d5-423d-b82a-06fc901277a5", "user": {"role": "admin"}}
        current = {
            "id": 2,
            "phone_number_id": "999888777666555",
            "waba_id": "111",
            "access_token_encrypted": "enc:tok",
            "display_name": "Next Click Global",
            "display_phone_number": "919979745575",
        }
        err = FakeUniqueViolation(
            'duplicate key value violates unique constraint "idx_whatsapp_accounts_one_default"',
            "idx_whatsapp_accounts_one_default",
        )

        with (
            patch(
                "app.routers.whatsapp_accounts.db.fetchrow",
                new=AsyncMock(side_effect=[current, err]),
            ),
            patch("app.routers.whatsapp_accounts.decrypt", return_value="tok"),
        ):
            with self.assertRaises(HTTPException) as ctx:
                await update_account(account_id=2, payload=payload, tenant_ctx=tenant_ctx, admin={"role": "admin"})

        self.assertEqual(ctx.exception.status_code, 409)
        self.assertEqual(
            ctx.exception.detail,
            "Only one WhatsApp Business account is allowed per organization. Edit the existing account instead.",
        )


if __name__ == "__main__":
    unittest.main()
