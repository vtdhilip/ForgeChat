import json
import logging
from typing import Optional, Dict, Any, List
from app.core.database import get_db
from app.core.crypto import hash_api_key
from app.services import google_sheets

logger = logging.getLogger(__name__)

MODEL_CATALOG = {
    "anthropic": [
        {"value": "claude-opus-4-7", "label": "Claude Opus 4.7 (most capable)"},
        {"value": "claude-sonnet-4-6", "label": "Claude Sonnet 4.6 (balanced)"},
        {"value": "claude-haiku-4-5-20251001", "label": "Claude Haiku 4.5 (fastest)"},
    ],
    "openai": [
        {"value": "gpt-4o", "label": "GPT-4o"},
        {"value": "gpt-4o-mini", "label": "GPT-4o mini"},
        {"value": "gpt-4-turbo", "label": "GPT-4 Turbo"},
    ],
}
PROVIDER_LABELS = {
    "anthropic": "Anthropic Claude",
    "openai": "OpenAI",
    "claude_code": "Claude Code",
}
CAPABILITY_KEYS = ["discovery", "create_agent", "update_agent", "manage_tools", "delete"]

async def ensure_mcp_tables():
    async with get_db() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS coexistence.mcp_api_keys (
              id           BIGSERIAL PRIMARY KEY,
              label        TEXT NOT NULL,
              key_prefix   TEXT NOT NULL,
              key_last4    TEXT NOT NULL,
              key_hash     TEXT NOT NULL UNIQUE,
              is_enabled   BOOLEAN NOT NULL DEFAULT TRUE,
              last_used_at TIMESTAMPTZ,
              created_by   BIGINT REFERENCES coexistence.forgecrm_users(id) ON DELETE SET NULL,
              created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS coexistence.mcp_settings (
              id             INT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
              master_enabled BOOLEAN NOT NULL DEFAULT FALSE,
              capabilities   JSONB NOT NULL DEFAULT '{"discovery":true,"create_agent":true,"update_agent":true,"manage_tools":true,"delete":true}'::jsonb,
              updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        await conn.execute("INSERT INTO coexistence.mcp_settings (id) VALUES (1) ON CONFLICT DO NOTHING")

async def load_settings() -> Dict[str, Any]:
    async with get_db() as conn:
        row = await conn.fetchrow("SELECT master_enabled, capabilities FROM coexistence.mcp_settings WHERE id = 1")
        if not row:
            return {"masterEnabled": False, "capabilities": {}}
        caps = row["capabilities"]
        if isinstance(caps, str):
            try:
                caps = json.loads(caps)
            except Exception:
                caps = {}
        return {"masterEnabled": bool(row["master_enabled"]), "capabilities": caps or {}}

async def validate_key(raw_key: str) -> Dict[str, Any]:
    key = str(raw_key or "").strip()
    if not key:
        raise ValueError("Missing API key")
    h = hash_api_key(key)
    async with get_db() as conn:
        row = await conn.fetchrow("SELECT * FROM coexistence.mcp_api_keys WHERE key_hash = $1", h)
        if not row or not row["is_enabled"]:
            raise PermissionError("Invalid or disabled API key")
        settings = await load_settings()
        if not settings.get("masterEnabled"):
            raise PermissionError("MCP access is disabled")
        await conn.execute("UPDATE coexistence.mcp_api_keys SET last_used_at = NOW() WHERE id = $1", row["id"])
        return {"keyId": row["id"], "capabilities": settings.get("capabilities", {})}

async def list_wa_accounts() -> List[Dict[str, Any]]:
    async with get_db() as conn:
        rows = await conn.fetch(
            """
            SELECT id, display_name, display_phone_number, is_active, is_default
              FROM coexistence.whatsapp_accounts ORDER BY is_default DESC, display_name
            """
        )
        return [
            {
                "id": r["id"],
                "displayName": r["display_name"],
                "phoneNumber": r["display_phone_number"],
                "isActive": r["is_active"],
                "isDefault": r["is_default"],
            }
            for r in rows
        ]

async def list_models() -> List[Dict[str, Any]]:
    async with get_db() as conn:
        rows = await conn.fetch("SELECT id, provider, label FROM coexistence.ai_models ORDER BY created_at DESC")
        out = []
        for r in rows:
            prov = r["provider"]
            if prov in MODEL_CATALOG:
                out.append({
                    "aiModelId": r["id"],
                    "provider": prov,
                    "providerLabel": PROVIDER_LABELS.get(prov, prov),
                    "label": r["label"],
                    "models": MODEL_CATALOG[prov],
                })
        return out

async def list_google_accounts() -> List[Dict[str, Any]]:
    async with get_db() as conn:
        rows = await conn.fetch(
            "SELECT id, account_label, health_status FROM coexistence.oauth_credentials WHERE provider = 'google' ORDER BY created_at DESC"
        )
        return [{"id": r["id"], "label": r["account_label"], "status": r["health_status"]} for r in rows]

async def search_spreadsheets(google_account_id: int, q: str = "", page_size: int = 50) -> List[Dict[str, Any]]:
    if not google_account_id:
        raise ValueError("googleAccountId is required")
    return await google_sheets.list_spreadsheets(int(google_account_id), query=q, page_size=page_size)

async def list_sheet_tabs(google_account_id: int, spreadsheet_id: str) -> List[Dict[str, Any]]:
    if not google_account_id or not spreadsheet_id:
        raise ValueError("googleAccountId and spreadsheetId are required")
    return await google_sheets.list_sheet_tabs(int(google_account_id), spreadsheet_id)

async def read_sheet_values(google_account_id: int, spreadsheet_id: str, tab: str, range_a1: Optional[str] = None, max_rows: int = 100) -> Dict[str, Any]:
    if not google_account_id or not spreadsheet_id or not tab:
        raise ValueError("googleAccountId, spreadsheetId, and tab are required")
    return await google_sheets.read(
        int(google_account_id),
        spreadsheet_id,
        tab,
        args={"range": range_a1, "max_rows": max_rows},
    )

async def list_media(media_type: Optional[str] = None, name: Optional[str] = None) -> List[Dict[str, Any]]:
    async with get_db() as conn:
        conds = []
        args = []
        if media_type:
            args.append(media_type)
            conds.append(f"media_type = ${len(args)}")
        if name:
            args.append(f"%{name}%")
            conds.append(f"name ILIKE ${len(args)}")
        where = f"WHERE {' AND '.join(conds)}" if conds else ""
        rows = await conn.fetch(
            f"SELECT id, name, media_type, mime_type, file_size, created_at FROM coexistence.media_library {where} ORDER BY created_at DESC LIMIT 100",
            *args,
        )
        return [dict(r) for r in rows]

async def list_templates(wa_account_id: Optional[int] = None) -> List[Dict[str, Any]]:
    async with get_db() as conn:
        if wa_account_id:
            rows = await conn.fetch("SELECT * FROM coexistence.templates WHERE wa_account_id = $1 ORDER BY name", int(wa_account_id))
        else:
            rows = await conn.fetch("SELECT * FROM coexistence.templates ORDER BY name")
        return [dict(r) for r in rows]

async def get_template(template_id: int) -> Optional[Dict[str, Any]]:
    async with get_db() as conn:
        row = await conn.fetchrow("SELECT * FROM coexistence.templates WHERE id = $1", int(template_id))
        return dict(row) if row else None
