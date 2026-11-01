import logging
import re
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.core.database import get_db
from app.middleware.auth import get_current_user, assert_contact_access
from app.services.agent_handoff import perform_handoff, resume_agent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent-conversation", tags=["Agent Conversation"])

async def active_agent_for_wa_number(wa_number: str) -> Optional[Dict[str, Any]]:
    clean_num = re.sub(r"\D", "", wa_number or "")
    async with get_db() as conn:
        row = await conn.fetchrow(
            """
            SELECT a.id, a.name
              FROM coexistence.agents a
              JOIN coexistence.whatsapp_accounts w ON w.id = a.wa_account_id
             WHERE a.is_active = TRUE
               AND regexp_replace(w.display_phone_number, '\\D', '', 'g') = $1
             LIMIT 1
            """,
            clean_num,
        )
        return dict(row) if row else None

@router.get("")
async def get_agent_conversation_status(
    waNumber: str = Query(..., alias="waNumber"),
    contactNumber: str = Query(..., alias="contactNumber"),
    user: dict = Depends(get_current_user),
):
    if not waNumber or not contactNumber:
        raise HTTPException(status_code=400, detail="waNumber and contactNumber are required")
    await assert_contact_access(user, waNumber, contactNumber)

    agent = await active_agent_for_wa_number(waNumber)
    async with get_db() as conn:
        row = await conn.fetchrow(
            """
            SELECT agent_paused
              FROM coexistence.contacts WHERE wa_number = $1 AND contact_number = $2
            """,
            waNumber,
            contactNumber,
        )
        c = dict(row) if row else {}

    return {
        "hasAgent": bool(agent),
        "agentId": agent["id"] if agent else None,
        "agentName": agent["name"] if agent else None,
        "paused": bool(c.get("agent_paused")),
        "pausedBy": None,
        "pausedReason": None,
        "pausedAt": None,
    }

class ConversationActionPayload(BaseModel):
    waNumber: str
    contactNumber: str

@router.post("/pause")
async def pause_agent_conversation(
    payload: ConversationActionPayload,
    user: dict = Depends(get_current_user),
):
    wa_number = payload.waNumber
    contact_number = payload.contactNumber
    if not wa_number or not contact_number:
        raise HTTPException(status_code=400, detail="waNumber and contactNumber are required")
    await assert_contact_access(user, wa_number, contact_number)

    agent = await active_agent_for_wa_number(wa_number)
    if not agent:
        raise HTTPException(status_code=400, detail="No active AI agent on this number.")

    who = user.get("displayName") or user.get("username") or f"user {user.get('id')}"
    res = await perform_handoff(
        agent_id=agent["id"],
        handoff_user_ids=[],
        wa_number=wa_number,
        contact_number=contact_number,
        reason=f"Taken over by {who}",
        by=f"manual:{user.get('id')}",
        assign_to=user.get("id"),
    )
    return {
        "ok": True,
        "paused": True,
        "assignedUserId": res.get("assignedUserId"),
        "assignedUserName": res.get("assignedUserName"),
    }

@router.post("/resume")
async def resume_agent_conversation(
    payload: ConversationActionPayload,
    user: dict = Depends(get_current_user),
):
    wa_number = payload.waNumber
    contact_number = payload.contactNumber
    if not wa_number or not contact_number:
        raise HTTPException(status_code=400, detail="waNumber and contactNumber are required")
    await assert_contact_access(user, wa_number, contact_number)

    await resume_agent(
        wa_number=wa_number,
        contact_number=contact_number,
        by=f"manual:{user.get('id')}",
    )
    return {"ok": True, "paused": False}
