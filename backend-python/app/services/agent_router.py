import asyncio
import logging
import re
from typing import Optional, Dict, Any

from app.core.database import get_db
from app.engine.automation_engine import matches_keyword
from app.services.agent_handoff import is_conversation_paused, matches_any_handoff_keyword, perform_handoff
from app.engine.agent_engine import run_agent

logger = logging.getLogger(__name__)

async def route_if_active(record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not record or record.get("direction") != "incoming":
        return None
    if record.get("message_type") in ("status", "reaction"):
        return None
    if not record.get("contact_number"):
        return None

    is_audio = record.get("message_type") in ("audio", "voice") and bool(record.get("media_url"))
    is_image = record.get("message_type") == "image" and bool(record.get("media_url"))
    has_text = not is_audio and bool(record.get("message_body") and record.get("message_body").strip())

    if not has_text and not is_audio and not is_image:
        return None

    wa_clean = re.sub(r"\D", "", record.get("wa_number") or "")
    phone_id = str(record.get("phone_number_id") or "")

    async with get_db() as conn:
        row = await conn.fetchrow(
            """
            SELECT a.id, a.wa_account_id, a.trigger_mode, a.trigger_keyword,
                   a.trigger_match_type, a.trigger_case_sensitive, a.trigger_session_minutes,
                   a.transcribe_audio, a.accept_images,
                   a.handoff_enabled, a.handoff_user_ids, a.handoff_keywords
              FROM coexistence.agents a
              JOIN coexistence.whatsapp_accounts w ON w.id = a.wa_account_id
             WHERE a.is_active = TRUE
               AND (regexp_replace(w.display_phone_number, '\\D', '', 'g') = $1
                    OR w.phone_number_id = $2)
             LIMIT 1
            """,
            wa_clean,
            phone_id,
        )
        if not row:
            return None
        agent = dict(row)

    # Human handoff check
    if await is_conversation_paused(record.get("wa_number"), record.get("contact_number")):
        return {"agentId": agent["id"], "skipped": "paused_for_human"}

    if is_audio and not has_text and not agent.get("transcribe_audio"):
        return None
    if is_image and not has_text and not agent.get("accept_images"):
        return None

    trigger_mode = agent.get("trigger_mode") or "any"
    if trigger_mode in ("keyword", "new"):
        engages = False
        if trigger_mode == "keyword":
            engages = has_text and matches_keyword(
                record.get("message_body"),
                agent.get("trigger_keyword"),
                agent.get("trigger_match_type", "exact"),
                bool(agent.get("trigger_case_sensitive")),
            )
        else:
            async with get_db() as conn:
                prior = await conn.fetch(
                    """
                    SELECT 1 FROM coexistence.chat_history
                     WHERE wa_number = $1 AND contact_number = $2 AND direction = 'incoming'
                       AND ($3::text IS NULL OR message_id IS DISTINCT FROM $3)
                     LIMIT 1
                    """,
                    record.get("wa_number") or "",
                    record.get("contact_number"),
                    record.get("message_id"),
                )
                engages = len(prior) == 0

        if not engages:
            window_min = agent.get("trigger_session_minutes") or 30
            async with get_db() as conn:
                recent = await conn.fetch(
                    """
                    SELECT 1 FROM coexistence.agent_runs
                     WHERE agent_id = $1 AND contact_number = $2
                       AND started_at > NOW() - make_interval(mins => $3)
                     LIMIT 1
                    """,
                    agent["id"],
                    record.get("contact_number"),
                    window_min,
                )
                if not recent:
                    return None

    # Keyword handoff check
    if agent.get("handoff_enabled") and has_text:
        if matches_any_handoff_keyword(record.get("message_body"), agent.get("handoff_keywords")):
            await perform_handoff(
                agent_id=agent["id"],
                handoff_user_ids=agent.get("handoff_user_ids"),
                wa_number=record.get("wa_number"),
                contact_number=record.get("contact_number"),
                reason="Customer asked for a human (keyword).",
                by="keyword",
            )
            return {"agentId": agent["id"], "handedOff": True}

    # Dispatch agent run in background
    asyncio.create_task(
        run_agent(
            agent_id=agent["id"],
            contact_number=record.get("contact_number"),
            inbound_message_id=record.get("message_id"),
            inbound_text=record.get("message_body") if has_text else None,
        )
    )
    return {"agentId": agent["id"]}
