import logging
from typing import Optional, List, Dict, Any
from app.core.database import get_db
from app.core.events import bus

logger = logging.getLogger(__name__)

def emit(event: str, payload: dict):
    try:
        bus.emit(event, payload)
    except Exception as e:
        logger.warning(f"Error emitting event {event}: {e}")

async def perform_handoff(
    agent_id: int,
    handoff_user_ids: Optional[List[int]],
    wa_number: str,
    contact_number: str,
    reason: Optional[str] = None,
    by: Optional[str] = "agent",
    assign_to: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Pick the next eligible BDA round-robin (advancing the agent's cursor
    atomically), assign + pause the conversation.
    `by` = 'agent' | 'keyword' | 'manual:<userId>'.
    Returns {"assigned_user_id": ..., "assigned_user_name": ...}.
    """
    assigned_user_id = int(assign_to) if assign_to is not None else None
    assigned_user_name = None

    async with get_db() as conn:
        # Round-robin choose a BDA if not explicitly specified
        if not assigned_user_id:
            ids = [int(n) for n in (handoff_user_ids or []) if n]
            if ids:
                row = await conn.fetchrow(
                    """
                    UPDATE coexistence.agents
                       SET handoff_rr_pointer = (COALESCE(handoff_rr_pointer, -1) + 1) % $2
                     WHERE id = $1
                    RETURNING handoff_rr_pointer
                    """,
                    agent_id,
                    len(ids),
                )
                if row:
                    idx = ((row["handoff_rr_pointer"] % len(ids)) + len(ids)) % len(ids)
                    assigned_user_id = ids[idx]

        if assigned_user_id:
            ur = await conn.fetchrow(
                "SELECT id, COALESCE(display_name, username) AS name FROM coexistence.forgecrm_users WHERE id = $1 AND is_active = TRUE",
                assigned_user_id,
            )
            if ur:
                assigned_user_name = ur["name"]
            else:
                assigned_user_id = None  # Skip deactivated user

        await conn.execute(
            """
            UPDATE coexistence.contacts
               SET agent_paused = TRUE,
                   assigned_user_id = COALESCE($3, assigned_user_id), updated_at = NOW()
             WHERE wa_number = $1 AND contact_number = $2
            """,
            wa_number,
            contact_number,
            assigned_user_id,
        )

    emit("contact-saved", {"waNumber": wa_number, "contactNumber": contact_number})
    if assigned_user_id:
        emit("contact-assignment-changed", {
            "waNumber": wa_number,
            "contactNumber": contact_number,
            "assignedUserId": assigned_user_id,
        })
    emit("agent-handoff", {
        "waNumber": wa_number,
        "contactNumber": contact_number,
        "assignedUserId": assigned_user_id,
        "assignedUserName": assigned_user_name,
        "reason": reason,
        "by": by,
    })

    return {
        "assignedUserId": assigned_user_id,
        "assignedUserName": assigned_user_name,
    }

async def resume_agent(wa_number: str, contact_number: str, by: Optional[str] = None) -> Dict[str, Any]:
    """Manual 'Return to bot' — clear the pause so the agent answers again."""
    async with get_db() as conn:
        await conn.execute(
            """
            UPDATE coexistence.contacts
               SET agent_paused = FALSE, updated_at = NOW()
             WHERE wa_number = $1 AND contact_number = $2
            """,
            wa_number,
            contact_number,
        )
    emit("agent-resumed", {"waNumber": wa_number, "contactNumber": contact_number, "by": by})
    return {"ok": True}

async def is_conversation_paused(wa_number: str, contact_number: str) -> bool:
    async with get_db() as conn:
        row = await conn.fetchrow(
            "SELECT agent_paused FROM coexistence.contacts WHERE wa_number = $1 AND contact_number = $2",
            wa_number,
            contact_number,
        )
        return bool(row and row["agent_paused"])

def matches_any_handoff_keyword(message_body: Optional[str], keywords: Optional[str]) -> bool:
    if not message_body or not keywords:
        return False
    msg = str(message_body).lower()
    return any(k.strip().lower() in msg for k in str(keywords).split(",") if k.strip())
