import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import httpx

from app.core.database import get_db
from app.core.crypto import decrypt
from app.services.google_sheets import execute_op as execute_sheets_op
from app.services.message_sender import (
    resolve_account,
    insert_pending_row,
    dispatch_send_task,
)

logger = logging.getLogger(__name__)

async def build_tools_for_agent(agent: Dict[str, Any], send_ctx: Optional[Dict[str, Any]] = None):
    async with get_db() as conn:
        rows = await conn.fetch(
            "SELECT * FROM coexistence.agent_tools WHERE agent_id = $1 AND is_enabled = TRUE ORDER BY id",
            agent["id"],
        )

    tools = []
    executors = {}

    for r in rows:
        cfg = r["config"] or {}
        if isinstance(cfg, str):
            try:
                cfg = json.loads(cfg)
            except Exception:
                cfg = {}

        if r["tool_type"] == "google_sheets":
            ops = cfg.get("ops") or []
            base_desc = f"Google Sheet '{cfg.get('spreadsheet_name') or cfg.get('spreadsheet_id')}' tab '{cfg.get('sheet_name')}'"

            if "read" in ops:
                name = f"google_sheets_read_{r['id']}"
                tools.append({
                    "name": name,
                    "description": f"Read rows from {base_desc}.",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "range": {"type": "string", "description": "Optional A1 range"},
                            "max_rows": {"type": "integer", "description": "Max rows to return"},
                        },
                    },
                })
                executors[name] = lambda args, c=cfg: execute_sheets_op("read", c, args)

            if "append" in ops:
                name = f"google_sheets_append_{r['id']}"
                tools.append({
                    "name": name,
                    "description": f"Append row to {base_desc}.",
                    "input_schema": {
                        "type": "object",
                        "properties": {"values": {"type": "array", "items": {"type": "string"}}},
                        "required": ["values"],
                    },
                })
                executors[name] = lambda args, c=cfg: execute_sheets_op("append", c, args)

            if "upsert" in ops:
                name = f"google_sheets_upsert_{r['id']}"
                tools.append({
                    "name": name,
                    "description": f"Upsert row in {base_desc}.",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "key_column": {"type": "string"},
                            "key_value": {"type": "string"},
                            "fields": {"type": "object"},
                        },
                        "required": ["key_column", "key_value", "fields"],
                    },
                })
                executors[name] = lambda args, c=cfg: execute_sheets_op("upsert", c, args)

    return tools, executors

async def run_agent(agent_id: int, contact_number: str, inbound_message_id: Optional[str] = None, inbound_text: Optional[str] = None) -> Dict[str, Any]:
    async with get_db() as conn:
        agent_row = await conn.fetchrow(
            """
            SELECT a.*, m.provider, m.api_key_encrypted, w.display_phone_number, w.phone_number_id
              FROM coexistence.agents a
              LEFT JOIN coexistence.ai_models m ON m.id = a.ai_model_id
              JOIN coexistence.whatsapp_accounts w ON w.id = a.wa_account_id
             WHERE a.id = $1
            """,
            agent_id,
        )
        if not agent_row:
            return {"status": "error", "error": "Agent not found"}
        agent = dict(agent_row)

        run_row = await conn.fetchrow(
            """
            INSERT INTO coexistence.agent_runs
             (agent_id, contact_number, status, inbound_message_id, inbound_text, started_at)
             VALUES ($1, $2, 'running', $3, $4, NOW())
             RETURNING id
            """,
            agent_id,
            contact_number,
            inbound_message_id,
            inbound_text,
        )
        run_id = run_row["id"]

    try:
        api_key = decrypt(agent["api_key_encrypted"]) if agent.get("api_key_encrypted") else None
        if not api_key:
            raise RuntimeError("AI model API key not found or not decryptable")

        # Fetch recent chat history
        limit = max(2, min(50, agent.get("context_window_messages") or 10))
        async with get_db() as conn:
            hist_rows = await conn.fetch(
                """
                SELECT direction, message_body, message_type, created_at
                  FROM coexistence.chat_history
                 WHERE contact_number = $1
                 ORDER BY created_at DESC
                 LIMIT $2
                """,
                contact_number,
                limit,
            )
        messages_hist = list(reversed([dict(r) for r in hist_rows]))

        tools, executors = await build_tools_for_agent(agent)

        provider = agent.get("provider", "openai").lower()
        model_name = agent.get("llm_model") or ("gpt-4o" if provider == "openai" else "claude-sonnet-4-6")
        system_prompt = agent.get("system_prompt") or "You are a helpful AI assistant."

        reply_text = ""

        if provider == "openai":
            conv = [{"role": "system", "content": system_prompt}]
            for m in messages_hist:
                role = "user" if m.get("direction") == "incoming" else "assistant"
                conv.append({"role": role, "content": m.get("message_body") or ""})

            # Format tools for OpenAI
            openai_tools = [
                {
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t["description"],
                        "parameters": t["input_schema"],
                    },
                }
                for t in tools
            ]

            async with httpx.AsyncClient(timeout=45.0) as http:
                payload = {"model": model_name, "messages": conv}
                if openai_tools:
                    payload["tools"] = openai_tools

                resp = await http.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json=payload,
                )
                if resp.status_code != 200:
                    raise RuntimeError(f"OpenAI error: {resp.text}")

                res_json = resp.json()
                msg = res_json["choices"][0]["message"]
                reply_text = msg.get("content") or ""

        elif provider == "anthropic":
            conv = []
            for m in messages_hist:
                role = "user" if m.get("direction") == "incoming" else "assistant"
                conv.append({"role": role, "content": m.get("message_body") or ""})

            anthropic_tools = [
                {
                    "name": t["name"],
                    "description": t["description"],
                    "input_schema": t["input_schema"],
                }
                for t in tools
            ]

            async with httpx.AsyncClient(timeout=45.0) as http:
                payload = {
                    "model": model_name,
                    "system": system_prompt,
                    "messages": conv,
                    "max_tokens": 1024,
                }
                if anthropic_tools:
                    payload["tools"] = anthropic_tools

                resp = await http.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                if resp.status_code != 200:
                    raise RuntimeError(f"Anthropic error: {resp.text}")

                res_json = resp.json()
                for block in res_json.get("content", []):
                    if block.get("type") == "text":
                        reply_text += block.get("text", "")

        # Dispatch final reply text to customer via WhatsApp
        if reply_text.strip():
            account, _ = await resolve_account(account_id=agent.get("wa_account_id"))
            if account:
                local_id = await insert_pending_row(
                    account=account,
                    to_number=contact_number,
                    message_type="text",
                    message_body=reply_text.strip(),
                )
                asyncio.create_task(
                    dispatch_send_task(
                        kind="text",
                        account=account,
                        to=contact_number,
                        local_message_id=local_id,
                        payload={"body": reply_text.strip()},
                    )
                )

        async with get_db() as conn:
            await conn.execute(
                """
                UPDATE coexistence.agent_runs
                   SET status = 'completed', outbound_text = $1, completed_at = NOW()
                 WHERE id = $2
                """,
                reply_text.strip(),
                run_id,
            )

        return {"status": "completed", "runId": run_id, "reply": reply_text}

    except Exception as e:
        logger.error(f"[agentEngine] Run error for agent {agent_id}: {e}")
        async with get_db() as conn:
            await conn.execute(
                "UPDATE coexistence.agent_runs SET status = 'error', error_message = $1, completed_at = NOW() WHERE id = $2",
                str(e),
                run_id,
            )
        return {"status": "error", "runId": run_id, "error": str(e)}
