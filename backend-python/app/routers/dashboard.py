import os
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from app.core.database import db
from app.middleware.auth import get_current_user, is_tenant_admin
from app.middleware.tenant import get_tenant_context
from app.services.whatsapp_service import normalize_phone

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

RANGE_DAYS = {"7d": 7, "30d": 30, "90d": 90}
LEAD_SOURCE_CATEGORY = os.getenv("LEAD_SOURCE_CATEGORY", "Lead Source")

async def get_connected_wa(org_id: Optional[str] = None) -> Optional[str]:
    if org_id:
        row = await db.fetchrow(
            "SELECT display_phone_number AS wa FROM coexistence.whatsapp_accounts WHERE org_id = $1::uuid AND is_active = true ORDER BY is_default DESC, id ASC LIMIT 1",
            org_id
        )
    else:
        row = await db.fetchrow(
            "SELECT display_phone_number AS wa FROM coexistence.whatsapp_accounts WHERE is_active = true ORDER BY is_default DESC, id ASC LIMIT 1"
        )
    if not row or not row.get("wa"):
        return None
    return normalize_phone(row["wa"])

def apply_scope(sql: str, params: list, admin: bool, uid: int, kind: str, wa: Optional[str]):
    out = list(params)
    clause = ""
    if wa:
        out.append(wa)
        wp = f"${len(out)}"
        clause += f" AND c.wa_number = {wp}" if kind == "contacts" else f" AND ch.wa_number = {wp}"
    else:
        clause += " AND FALSE"

    if not admin:
        out.append(uid)
        up = f"${len(out)}"
        if kind == "contacts":
            clause += f" AND c.assigned_user_id = {up}"
        else:
            clause += f" AND EXISTS (SELECT 1 FROM coexistence.contacts sc WHERE sc.wa_number = ch.wa_number AND sc.contact_number = ch.contact_number AND sc.assigned_user_id = {up})"

    return sql.replace("/*SCOPE*/", clause), out

def pct(cur: int, prev: int) -> Optional[int]:
    if not prev or prev <= 0:
        return None
    return round(((cur - prev) / prev) * 100)

@router.get("")
async def get_dashboard(
    range: Optional[str] = "7d",
    funnelCategory: Optional[str] = None,
    tenant_ctx: dict = Depends(get_tenant_context),
):
    user = tenant_ctx["user"]
    admin = is_tenant_admin(user, tenant_ctx)
    uid = user["id"]
    r_key = range if range in RANGE_DAYS else "7d"
    days = RANGE_DAYS[r_key]
    connected_wa = await get_connected_wa(tenant_ctx["org_id"])

    async def q(sql: str, params: list, kind: str):
        query_sql, query_params = apply_scope(sql, params, admin, uid, kind, connected_wa)
        return await db.fetch(query_sql, *query_params)

    cat_row = await db.fetchrow(
        "SELECT id FROM coexistence.categories WHERE LOWER(name) = LOWER($1) ORDER BY created_at LIMIT 1",
        LEAD_SOURCE_CATEGORY
    )
    lead_source_cat_id = cat_row["id"] if cat_row else None

    # Contacts
    c_rows = await q(
        """
        SELECT
          count(*)::int AS total,
          count(*) FILTER (WHERE c.created_at >= NOW() - ($1 * INTERVAL '1 day'))::int AS new_in_range,
          count(*) FILTER (WHERE c.created_at >= NOW() - ($1 * INTERVAL '1 day') * 2
                             AND c.created_at <  NOW() - ($1 * INTERVAL '1 day'))::int AS prev_new
        FROM coexistence.contacts c
        WHERE TRUE /*SCOPE*/
        """,
        [days], "contacts"
    )
    contact_row = dict(c_rows[0]) if c_rows else {"total": 0, "new_in_range": 0, "prev_new": 0}

    # Leads
    lead_row = {"new_in_range": 0, "prev_new": 0}
    if lead_source_cat_id:
        l_rows = await q(
            """
            SELECT
              count(DISTINCT c.id) FILTER (WHERE c.created_at >= NOW() - ($1 * INTERVAL '1 day'))::int AS new_in_range,
              count(DISTINCT c.id) FILTER (WHERE c.created_at >= NOW() - ($1 * INTERVAL '1 day') * 2
                                 AND c.created_at <  NOW() - ($1 * INTERVAL '1 day'))::int AS prev_new
            FROM coexistence.contacts c,
                 jsonb_array_elements(COALESCE(c.tags, '[]'::jsonb)) t
            WHERE (t->>'category_id') = $2 /*SCOPE*/
            """,
            [days, lead_source_cat_id], "contacts"
        )
        if l_rows:
            lead_row = dict(l_rows[0])

    # Messages
    m_rows = await q(
        """
        SELECT
          count(DISTINCT (ch.wa_number, ch.contact_number))
            FILTER (WHERE ch.timestamp >= NOW() - ($1 * INTERVAL '1 day'))::int AS active_convos,
          count(*) FILTER (WHERE ch.direction='outgoing'
                             AND ch.timestamp >= NOW() - ($1 * INTERVAL '1 day'))::int AS sent,
          count(*) FILTER (WHERE ch.direction='incoming'
                             AND ch.timestamp >= NOW() - ($1 * INTERVAL '1 day'))::int AS received,
          count(*) FILTER (WHERE ch.direction='outgoing'
                             AND ch.timestamp >= NOW() - ($1 * INTERVAL '1 day') * 2
                             AND ch.timestamp <  NOW() - ($1 * INTERVAL '1 day'))::int AS prev_sent
        FROM coexistence.chat_history ch
        WHERE TRUE /*SCOPE*/
        """,
        [days], "chat"
    )
    msg_row = dict(m_rows[0]) if m_rows else {"active_convos": 0, "sent": 0, "received": 0, "prev_sent": 0}

    # Responses
    r_rows = await q(
        """
        WITH conv AS (
          SELECT ch.wa_number, ch.contact_number,
                 bool_or(ch.direction='incoming') AS has_in,
                 bool_or(ch.direction='outgoing') AS has_out
          FROM coexistence.chat_history ch
          WHERE ch.timestamp >= NOW() - ($1 * INTERVAL '1 day') /*SCOPE*/
          GROUP BY ch.wa_number, ch.contact_number
        )
        SELECT count(*) FILTER (WHERE has_in)::int AS inbound_convos,
               count(*) FILTER (WHERE has_in AND has_out)::int AS replied_convos
        FROM conv
        """,
        [days], "chat"
    )
    resp_row = dict(r_rows[0]) if r_rows else {"inbound_convos": 0, "replied_convos": 0}

    # Open conversations
    open_row = {"open_convos": 0}
    if lead_source_cat_id:
        o_rows = await q(
            """
            WITH last_in AS (
              SELECT ch.wa_number, ch.contact_number, max(ch.timestamp) AS last_in_ts
              FROM coexistence.chat_history ch
              WHERE ch.direction='incoming' /*SCOPE*/
              GROUP BY ch.wa_number, ch.contact_number
            )
            SELECT count(*)::int AS open_convos
            FROM last_in li
            LEFT JOIN coexistence.conversation_reads r
              ON r.wa_number = li.wa_number AND r.contact_number = li.contact_number
            WHERE (r.last_read_at IS NULL OR li.last_in_ts > r.last_read_at)
              AND EXISTS (
                SELECT 1 FROM coexistence.contacts lc,
                     jsonb_array_elements(COALESCE(lc.tags, '[]'::jsonb)) lt
                WHERE lc.wa_number = li.wa_number
                  AND lc.contact_number = li.contact_number
                  AND (lt->>'category_id') = $1
              )
            """,
            [lead_source_cat_id], "chat"
        )
        if o_rows:
            open_row = dict(o_rows[0])

    response_rate = (
        round((resp_row["replied_convos"] / resp_row["inbound_convos"]) * 100)
        if resp_row["inbound_convos"] > 0
        else 0
    )

    kpis = [
        {
            "key": "contacts",
            "label": "Total Contacts",
            "value": contact_row["total"],
            "unit": "",
            "delta": pct(contact_row["new_in_range"], contact_row["prev_new"]),
            "sub": f"+{contact_row['new_in_range']} new",
            "tooltip": "All contacts captured." if admin else "Contacts assigned to you.",
        },
        {
            "key": "newLeads",
            "label": "New Leads",
            "value": lead_row["new_in_range"],
            "unit": "",
            "delta": pct(lead_row["new_in_range"], lead_row["prev_new"]),
            "sub": f"in last {days}d",
            "tooltip": f"New contacts tagged under the “{LEAD_SOURCE_CATEGORY}” category.",
        },
        {
            "key": "open",
            "label": "Open Conversations",
            "value": open_row["open_convos"],
            "unit": "",
            "delta": None,
            "sub": "awaiting reply",
            "tooltip": "Conversations awaiting a reply.",
        },
        {
            "key": "sent",
            "label": "Messages Sent",
            "value": msg_row["sent"],
            "unit": "",
            "delta": pct(msg_row["sent"], msg_row["prev_sent"]),
            "sub": f"{msg_row['received']} received",
            "tooltip": "Outbound WhatsApp messages in the period.",
        },
        {
            "key": "response",
            "label": "Response Rate",
            "value": response_rate,
            "unit": "%",
            "delta": None,
            "sub": f"{resp_row['replied_convos']}/{resp_row['inbound_convos']} replied",
            "tooltip": "Share of inbound conversations that received at least one reply.",
        },
    ]

    automations = None
    broadcasts = None
    alerts = []

    if admin:
        auto_counts = await db.fetchrow(
            """
            SELECT count(*) FILTER (WHERE status='active')::int AS active,
                   count(*)::int AS total
            FROM coexistence.chatbots
            """
        )
        run_row = await db.fetchrow(
            """
            SELECT count(*)::int AS total,
                   count(*) FILTER (WHERE status='success')::int AS success,
                   count(*) FILTER (WHERE status='error')::int AS error,
                   count(*) FILTER (WHERE status='paused')::int AS paused
            FROM coexistence.automation_executions
            WHERE started_at >= NOW() - ($1 * INTERVAL '1 day')
            """,
            days
        )
        automations = {
            "active": auto_counts["active"],
            "total": auto_counts["total"],
            "runs": dict(run_row) if run_row else {"total": 0, "success": 0, "error": 0, "paused": 0},
            "successRate": round((run_row["success"] / run_row["total"]) * 100) if run_row and run_row["total"] > 0 else None,
        }
        kpis.append({
            "key": "automations",
            "label": "Active Automations",
            "value": auto_counts["active"],
            "unit": "",
            "delta": None,
            "sub": f"of {auto_counts['total']} total",
            "tooltip": "Automation flows currently enabled.",
        })

        bc_summary = await db.fetchrow(
            """
            SELECT count(*)::int AS campaigns
            FROM coexistence.broadcasts
            WHERE created_at >= NOW() - ($1 * INTERVAL '1 day')
            """,
            days
        )
        recent_bc = await db.fetch(
            """
            SELECT b.id, b.name, b.message_type AS "messageType", b.status,
                   b.created_at AS "createdAt",
                   count(*) FILTER (WHERE l.action='BROADCAST')::int AS recipients,
                   count(*) FILTER (WHERE l.action='BROADCAST' AND l.status='SENT')::int AS sent,
                   count(*) FILTER (WHERE l.action='BROADCAST' AND l.status='FAILED')::int AS failed
            FROM coexistence.broadcasts b
            LEFT JOIN coexistence.broadcast_logs l ON l.broadcast_id = b.id
            GROUP BY b.id
            ORDER BY b.created_at DESC
            LIMIT 5
            """
        )
        broadcasts = {
            "campaigns": bc_summary["campaigns"] if bc_summary else 0,
            "recent": [
                {
                    **dict(r),
                    "createdAt": r["createdAt"].isoformat() if r.get("createdAt") else None
                }
                for r in recent_bc
            ]
        }
    else:
        kpis.append({
            "key": "convos",
            "label": "Active Conversations",
            "value": msg_row["active_convos"],
            "unit": "",
            "delta": None,
            "sub": f"{msg_row['received']} received",
            "tooltip": "Your customer threads with at least one message.",
        })

    all_cats = await db.fetch("SELECT id, name FROM coexistence.categories ORDER BY name")

    return {
        "range": r_key,
        "scope": "admin" if admin else "bda",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "kpis": kpis,
        "funnel": {"categories": [dict(c) for c in allCats] if 'allCats' in locals() else [dict(c) for c in all_cats], "stages": [], "total": 0},
        "tagDistribution": [],
        "automations": automations,
        "broadcasts": broadcasts,
        "alerts": alerts,
    }
