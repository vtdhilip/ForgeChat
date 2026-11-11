import asyncio
import json
import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

from app.core.database import get_db
from app.core.events import bus
from app.services.message_sender import (
    resolve_account,
    insert_pending_row,
    dispatch_send_task,
)
from app.services.product_catalog import resolve_product_name

logger = logging.getLogger(__name__)

def ist_now() -> Dict[str, Any]:
    ist = datetime.now(timezone(timedelta(hours=5, minutes=30)))
    days = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]
    return {"weekday": days[ist.weekday() if ist.weekday() < 6 else 0], "hour": ist.hour}

def normalize_text(text: Optional[str]) -> str:
    return (text or "").lower().strip()

def matches_keyword(message_body: Optional[str], keyword: Optional[str], match_type: str = "exact", case_sensitive: bool = False) -> bool:
    if not message_body or not keyword:
        return False
    msg = message_body.strip() if case_sensitive else normalize_text(message_body)
    kw = keyword.strip() if case_sensitive else normalize_text(keyword)
    if not kw:
        return False
    if match_type == "contains":
        return kw in msg
    if match_type == "starts":
        return msg.startswith(kw)
    return msg == kw

def _stringify_for_interpolation(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    if isinstance(v, (int, float, bool)):
        return str(v)
    try:
        return json.dumps(v)
    except Exception:
        return str(v)

def field_var_key(name: Optional[str]) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", str(name or "").strip().lower())
    return s.strip("_")

def resolve_variables(text: Optional[str], context: Dict[str, Any]) -> str:
    if not text:
        return ""
    contact = context.get("contact") or {}
    display_name = contact.get("name") or contact.get("profile_name") or ""
    last_msg = context.get("message_body") or context.get("trigger_data", {}).get("message_body") or ""
    order_data = context.get("trigger_data", {}).get("order_data")
    cart_summary = context.get("trigger_data", {}).get("cart_summary") or (last_msg if order_data else None)
    product_text = cart_summary or (contact.get("custom_fields", {}) or {}).get("product") or last_msg

    extra = context.get("extra_lookup") or {}
    raw_subtotal = (order_data or {}).get("total_amount", 359.00)
    subtotal_str = extra.get("subtotal") or (f"{raw_subtotal:.2f}" if raw_subtotal else "359.00")
    shipping_str = extra.get("shipping_fee") or "60.00"
    try:
        total_num = float(subtotal_str) + float(shipping_str)
        order_total_str = extra.get("order_total") or f"{total_num:.2f}"
    except Exception:
        order_total_str = extra.get("order_total") or "419.00"
    order_num_str = extra.get("order_number") or "LN-1001"
    pay_link_str = extra.get("payment_link") or f"https://rzp.io/l/pay-{order_num_str.lower()}"

    lookup = {
        "name": display_name,
        "first_name": display_name.split()[0] if display_name else "",
        "contact_number": contact.get("contact_number") or context.get("contact_number") or "",
        "phone": contact.get("contact_number") or context.get("contact_number") or "",
        "message": last_msg,
        "last_message": last_msg,
        "last_input": last_msg,
        "user_message": last_msg,
        "product": product_text,
        "cart_items": product_text,
        "order_items": product_text,
        "order_number": order_num_str,
        "order_id": order_num_str,
        "subtotal": subtotal_str,
        "shipping_fee": shipping_str,
        "shipping": shipping_str,
        "total_amount": order_total_str,
        "order_total": order_total_str,
        "cart_total": order_total_str,
        "payment_link": pay_link_str,
    }

    form_resp = context.get("trigger_data", {}).get("form_response") or {}
    for k, v in form_resp.items():
        sval = _stringify_for_interpolation(v)
        lk = str(k).lower()
        nk = field_var_key(k)
        if not lookup.get(lk):
            lookup[lk] = sval
        if nk and not lookup.get(nk):
            lookup[nk] = sval

    for k, v in extra.items():
        if v:
            lookup[str(k).lower()] = str(v)

    cf = contact.get("custom_fields") or {}
    for k, v in cf.items():
        sval = _stringify_for_interpolation(v)
        lk = str(k).lower()
        nk = field_var_key(k)
        if not lookup.get(lk):
            lookup[lk] = sval
        if nk and not lookup.get(nk):
            lookup[nk] = sval

    res = text
    for k, v in lookup.items():
        pattern = re.compile(rf"\{{\{{\s*{re.escape(k)}\s*\}}\}}", re.IGNORECASE)
        res = pattern.sub(str(v), res)

    return res

def get_field_value(source: str, field: str, context: Dict[str, Any]) -> Any:
    contact = context.get("contact") or {}
    cf = contact.get("custom_fields") or {}
    if source in ("custom", "system"):
        if field == "name":
            return contact.get("name") or ""
        if field in ("contact_number", "phone"):
            return contact.get("contact_number") or context.get("contact_number") or ""
        if re.search(r"^(last[_ ]?message|message)$", field, re.IGNORECASE):
            return context.get("message_body") or ""
        return cf.get(field, "")
    if source == "tags":
        names = [(t if isinstance(t, str) else (t.get("name") if isinstance(t, dict) else "")) for t in (contact.get("tags") or [])]
        return field if any(str(n).lower() == str(field).lower() for n in names) else ""
    if source == "time":
        t = ist_now()
        if "hour" in field.lower():
            return t["hour"]
        if "day" in field.lower():
            return t["weekday"]
        return "business" if (t["weekday"] != "sunday" and 9 <= t["hour"] < 18) else "after-hours"
    if source == "bot":
        if "intent" in field.lower():
            return cf.get("last_intent") or cf.get("intent") or ""
        if "state" in field.lower():
            return cf.get("bot_state") or ""
        return cf.get(field, "")
    return ""

def evaluate_rule(rule: Dict[str, Any], context: Dict[str, Any]) -> bool:
    source = rule.get("source", "custom")
    field = rule.get("field", "")
    op = rule.get("op", "equals")
    value = rule.get("value", "")

    field_value = get_field_value(source, field, context)
    str_field = str(field_value if field_value is not None else "").lower()
    str_comp = str(value if value is not None else "").lower()

    if op == "equals":
        return str_field == str_comp
    if op == "not equals":
        return str_field != str_comp
    if op == "contains":
        return str_comp in str_field
    if op == "not contains":
        return str_comp not in str_field
    if op == "starts with":
        return str_field.startswith(str_comp)
    if op == "ends with":
        return str_field.endswith(str_comp)
    if op == "is empty":
        return str_field == ""
    if op == "is not empty":
        return str_field != ""
    if op == "greater than":
        try:
            return float(field_value) > float(value)
        except Exception:
            return False
    if op == "less than":
        try:
            return float(field_value) < float(value)
        except Exception:
            return False
    if op == "has tag":
        return str_field != ""
    if op == "not has tag":
        return str_field == ""
    if op == "is true":
        return str_field == "true" or field_value is True
    if op == "is false":
        return str_field == "false" or field_value is False
    return False

def evaluate_conditions(node: Dict[str, Any], context: Dict[str, Any]) -> bool:
    rules = node.get("rules") or []
    if not rules:
        return True
    match_mode = node.get("matchMode", "all")
    results = [evaluate_rule(r, context) for r in rules]
    if match_mode == "any":
        return any(results)
    return all(results)

async def log_step(
    conn,
    execution_id: int,
    node: Dict[str, Any],
    input_data: Dict[str, Any],
    output_data: Dict[str, Any],
    step_status: str,
    error_message: Optional[str] = None,
    wa_message_id: Optional[str] = None,
    wa_message_status: Optional[str] = None,
) -> Dict[str, Any]:
    row = await conn.fetchrow(
        """
        INSERT INTO coexistence.automation_execution_steps
         (execution_id, node_id, node_type, node_name, input_data, output_data, status, completed_at, error_message, wa_message_id, wa_message_status)
         VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
         RETURNING *
        """,
        execution_id,
        node.get("id"),
        node.get("type"),
        node.get("title") or node.get("name") or f"{node.get('type')} node",
        json.dumps(input_data or {}),
        json.dumps(output_data or {}),
        step_status,
        None if step_status == "running" else datetime.now(timezone.utc),
        error_message,
        wa_message_id or (output_data.get("whatsapp", {}) or {}).get("message_id"),
        wa_message_status or (output_data.get("whatsapp", {}) or {}).get("status") or output_data.get("deliveryStatus"),
    )
    return dict(row)

async def update_execution_status(conn, execution_id: int, status: str, error_message: Optional[str] = None):
    await conn.execute(
        """
        UPDATE coexistence.automation_executions
           SET status = $1, completed_at = CASE WHEN $1::text IN ('success', 'error') THEN NOW() ELSE completed_at END,
               error_message = $2
         WHERE id = $3
        """,
        status,
        error_message,
        execution_id,
    )

# ── Node Handlers ──────────────────────────────────────────────────

async def execute_trigger_node(conn, execution_id: int, node: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    td = context.get("trigger_data") or {}
    output = {
        "triggerKind": node.get("triggerKind"),
        "keyword": node.get("keyword"),
        "matchType": node.get("matchType"),
        "whatsapp": {
            "direction": "incoming",
            "message_id": td.get("message_id"),
            "from": context.get("contact_number"),
            "to": td.get("wa_number"),
            "message_type": context.get("message_type"),
            "message_body": context.get("message_body"),
            "status": td.get("status", "received"),
        },
        "contact": context.get("contact") or {"contact_number": context.get("contact_number")},
    }
    return await log_step(conn, execution_id, node, {"triggerKind": node.get("triggerKind")}, output, "success")

async def execute_message_node(conn, execution_id: int, node: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    mode = node.get("messageMode", "direct")
    from_phone = context.get("trigger_data", {}).get("wa_number")
    contact_number = context.get("contact_number")

    account, acc_err = await resolve_account(
        account_id=node.get("whatsappAccountId"),
        from_phone_number=from_phone,
        org_id=context.get("org_id"),
    )
    if not account:
        raise RuntimeError(acc_err or f"No WhatsApp account resolved for {node.get('whatsappAccountId') or from_phone}")

    output = {}
    local_id = None

    if mode == "template":
        template_id = node.get("templateId")
        tpl_row = await conn.fetchrow(
            "SELECT name, body, category, language, buttons, header_type, header_text, footer FROM coexistence.message_templates WHERE id = $1",
            template_id,
        )
        template = dict(tpl_row) if tpl_row else None
        bindings = node.get("bindings") or {}
        components = []
        if bindings:
            keys = sorted(bindings.keys(), key=lambda x: int(x) if x.isdigit() else 0)
            params = [{"type": "text", "text": resolve_variables(str(bindings[k]), context) or " "} for k in keys]
            components.append({"type": "body", "parameters": params})

        body_preview = template.get("body") if template else "Template Message"
        local_id = await insert_pending_row(
            account=account,
            to_number=contact_number,
            message_type="template",
            message_body=body_preview,
            template_meta={
                "header_type": template.get("header_type", "NONE") if template else "NONE",
                "header_text": template.get("header_text") if template else None,
                "footer": template.get("footer") if template else None,
                "buttons": template.get("buttons") if template else [],
            } if template else None,
        )

        asyncio.create_task(
            dispatch_send_task(
                kind="template",
                account=account,
                to=contact_number,
                local_message_id=local_id,
                payload={
                    "name": template.get("name") if template else "",
                    "languageCode": template.get("language", "en") if template else "en",
                    "components": components,
                },
            )
        )

        output = {
            "mode": "template",
            "templateId": template_id,
            "to": contact_number,
            "deliveryStatus": "queued",
            "whatsapp": {"message_id": local_id, "from": from_phone, "to": contact_number, "status": "sending"},
        }
    else:
        dd = node.get("directData") or {}
        direct_type = node.get("directType", "text")
        resolved_body = resolve_variables(dd.get("body") or node.get("messageText") or "", context)

        local_id = await insert_pending_row(
            account=account,
            to_number=contact_number,
            message_type="text",
            message_body=resolved_body,
        )

        asyncio.create_task(
            dispatch_send_task(
                kind="text",
                account=account,
                to=contact_number,
                local_message_id=local_id,
                payload={"body": resolved_body},
            )
        )

        output = {
            "mode": "direct",
            "directType": direct_type,
            "resolvedBody": resolved_body,
            "to": contact_number,
            "deliveryStatus": "queued",
            "whatsapp": {"message_id": local_id, "from": from_phone, "to": contact_number, "status": "sending"},
        }

    step = await log_step(conn, execution_id, node, {"mode": mode, "to": contact_number}, output, "success")

    if node.get("waitForReply") is True:
        hours = max(1, int(node.get("waitTimeoutHours") or 24))
        await conn.execute(
            """
            UPDATE coexistence.automation_executions
               SET status = 'paused',
                   awaiting_node_id = $1,
                   paused_at = NOW(),
                   expires_at = NOW() + ($2 || ' hours')::INTERVAL,
                   wa_number = $3,
                   trigger_data = $4
             WHERE id = $5
            """,
            node.get("id"),
            str(hours),
            context.get("trigger_data", {}).get("wa_number"),
            json.dumps(context.get("trigger_data") or {}),
            execution_id,
        )
        step["__pauseExecution"] = True

    return step

async def execute_condition_node(conn, execution_id: int, node: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    matched = evaluate_conditions(node, context)
    output = {
        "matched": matched,
        "matchMode": node.get("matchMode", "all"),
        "rulesEvaluated": len(node.get("rules") or []),
    }
    return await log_step(conn, execution_id, node, {"rules": node.get("rules") or []}, output, "success")

async def execute_delay_node(conn, execution_id: int, node: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    output = {"delayMode": node.get("delayMode", "duration"), "note": "Delay executed"}
    return await log_step(conn, execution_id, node, {}, output, "success")

async def execute_action_node(conn, execution_id: int, node: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    actions = node.get("actions") or []
    wa_number = context.get("trigger_data", {}).get("wa_number")
    contact_number = context.get("contact_number")
    results = []
    step_status = "success"

    for a in actions:
        kind = a.get("kind")
        val = a.get("value")
        base = {"kind": kind, "value": val}
        try:
            if kind == "Assign to BDA":
                raw_val = resolve_variables(str(val or ""), context).strip()
                user_id = int(raw_val) if raw_val.isdigit() else None
                if not user_id:
                    results.append({**base, "status": "error", "error": "no user selected"})
                    continue
                await conn.execute(
                    """
                    INSERT INTO coexistence.contacts (wa_number, contact_number, assigned_user_id, updated_at)
                    VALUES ($1, $2, $3, NOW())
                    ON CONFLICT (wa_number, contact_number) DO UPDATE
                      SET assigned_user_id = EXCLUDED.assigned_user_id, updated_at = NOW()
                    """,
                    wa_number,
                    contact_number,
                    user_id,
                )
                results.append({**base, "status": "applied", "assignedUserId": user_id})

            elif kind == "Add Tag":
                tag_name = str(val or "").strip()
                if not tag_name:
                    results.append({**base, "status": "error", "error": "no tag selected"})
                    continue
                tag_row = await conn.fetchrow(
                    "SELECT id, name, color, category_id FROM coexistence.tags WHERE LOWER(name) = LOWER($1) LIMIT 1",
                    tag_name,
                )
                if not tag_row:
                    results.append({**base, "status": "error", "error": f"tag '{tag_name}' not found"})
                    continue
                tag_obj = {"id": tag_row["id"], "name": tag_row["name"], "color": tag_row["color"]}

                cur = await conn.fetchrow(
                    "SELECT tags FROM coexistence.contacts WHERE wa_number = $1 AND contact_number = $2",
                    wa_number,
                    contact_number,
                )
                existing = cur["tags"] if cur and cur["tags"] else []
                if isinstance(existing, str):
                    try:
                        existing = json.loads(existing)
                    except Exception:
                        existing = []
                if not any((t.get("id") == tag_row["id"] or str(t.get("name", "")).lower() == tag_name.lower()) for t in existing if isinstance(t, dict)):
                    existing.append(tag_obj)
                    await conn.execute(
                        """
                        INSERT INTO coexistence.contacts (wa_number, contact_number, tags, updated_at)
                        VALUES ($1, $2, $3::jsonb, NOW())
                        ON CONFLICT (wa_number, contact_number) DO UPDATE
                          SET tags = EXCLUDED.tags, updated_at = NOW()
                        """,
                        wa_number,
                        contact_number,
                        json.dumps(existing),
                    )
                results.append({**base, "status": "applied", "tag": tag_obj})

            elif kind == "Remove Tag":
                tag_name = str(val or "").strip()
                cur = await conn.fetchrow(
                    "SELECT tags FROM coexistence.contacts WHERE wa_number = $1 AND contact_number = $2",
                    wa_number,
                    contact_number,
                )
                existing = cur["tags"] if cur and cur["tags"] else []
                if isinstance(existing, str):
                    try:
                        existing = json.loads(existing)
                    except Exception:
                        existing = []
                new_tags = [t for t in existing if not (isinstance(t, dict) and str(t.get("name", "")).lower() == tag_name.lower())]
                await conn.execute(
                    "UPDATE coexistence.contacts SET tags = $3::jsonb, updated_at = NOW() WHERE wa_number = $1 AND contact_number = $2",
                    wa_number,
                    contact_number,
                    json.dumps(new_tags),
                )
                results.append({**base, "status": "applied", "removed": tag_name})

            elif kind == "Set Custom Field":
                raw = str(val or "")
                ix = raw.find("=")
                f_name = (raw[:ix] if ix >= 0 else raw).strip()
                f_val = (raw[ix + 1:] if ix >= 0 else "").strip()
                resolved_v = resolve_variables(f_val, context)

                f_row = await conn.fetchrow(
                    "SELECT id, name FROM coexistence.contact_field_definitions WHERE LOWER(name) = LOWER($1) LIMIT 1",
                    f_name,
                )
                f_id = f_row["id"] if f_row else f"cf-{field_var_key(f_name)}"

                cur = await conn.fetchrow(
                    "SELECT custom_fields FROM coexistence.contacts WHERE wa_number = $1 AND contact_number = $2",
                    wa_number,
                    contact_number,
                )
                cf = cur["custom_fields"] if cur and cur["custom_fields"] else {}
                if isinstance(cf, str):
                    try:
                        cf = json.loads(cf)
                    except Exception:
                        cf = {}
                cf[f_id] = resolved_v
                nk = field_var_key(f_name)
                if nk:
                    cf[nk] = resolved_v

                await conn.execute(
                    """
                    INSERT INTO coexistence.contacts (wa_number, contact_number, custom_fields, updated_at)
                    VALUES ($1, $2, $3::jsonb, NOW())
                    ON CONFLICT (wa_number, contact_number) DO UPDATE
                      SET custom_fields = EXCLUDED.custom_fields, updated_at = NOW()
                    """,
                    wa_number,
                    contact_number,
                    json.dumps(cf),
                )
                results.append({**base, "status": "applied", "field": f_name, "value": resolved_v})
            else:
                results.append({**base, "status": "logged", "note": "Action logged"})
        except Exception as err:
            results.append({**base, "status": "error", "error": str(err)})
            step_status = "error"

    return await log_step(conn, execution_id, node, {"actions": actions}, {"results": results}, step_status)

NODE_HANDLERS = {
    "trigger": execute_trigger_node,
    "message": execute_message_node,
    "condition": execute_condition_node,
    "delay": execute_delay_node,
    "action": execute_action_node,
}

# ── Graph Walker ───────────────────────────────────────────────────

async def walk_from(conn, execution_id: int, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]], start_node_id: str, context: Dict[str, Any], visited: Optional[set] = None) -> Dict[str, bool]:
    if visited is None:
        visited = set()

    current_node_id = start_node_id
    while current_node_id and current_node_id not in visited:
        visited.add(current_node_id)
        node = next((n for n in nodes if n.get("id") == current_node_id), None)
        if not node:
            break

        handler = NODE_HANDLERS.get(node.get("type"))
        step = None
        if handler:
            step = await handler(conn, execution_id, node, context)
            if step and step.get("__pauseExecution"):
                return {"paused": True}
        else:
            await log_step(conn, execution_id, node, {}, {"note": f"Skipped unsupported node type '{node.get('type')}'"}, "skipped")

        from_handle = "default"
        if node.get("type") == "condition" and step and step.get("output_data"):
            out_d = step["output_data"]
            if isinstance(out_d, str):
                try:
                    out_d = json.loads(out_d)
                except Exception:
                    out_d = {}
            from_handle = "yes" if out_d.get("matched") else "no"

        from_edges = [e for e in edges if e.get("from") == current_node_id]
        if from_handle == "default":
            next_edge = next((e for e in from_edges if not e.get("fromHandle") or e.get("fromHandle") == "default"), None) or (from_edges[0] if from_edges else None)
        else:
            next_edge = next((e for e in from_edges if e.get("fromHandle") == from_handle), None)

        current_node_id = next_edge.get("to") if next_edge else None

    return {"paused": False}

async def execute_automation(conn, automation: Dict[str, Any], context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    config = automation.get("config") or {}
    if isinstance(config, str):
        try:
            config = json.loads(config)
        except Exception:
            config = {}

    nodes = config.get("nodes") or []
    edges = config.get("edges") or []
    if not nodes:
        return None

    td = context.get("trigger_data") or {}
    exec_row = await conn.fetchrow(
        """
        INSERT INTO coexistence.automation_executions
         (automation_id, contact_number, trigger_type, trigger_data, status, wa_number)
         VALUES ($1, $2, $3, $4, 'running', $5)
         RETURNING id
        """,
        automation["id"],
        context.get("contact_number"),
        context.get("trigger_type", "keyword"),
        json.dumps(td),
        td.get("wa_number"),
    )
    execution_id = exec_row["id"]

    try:
        trigger_node = next((n for n in nodes if n.get("type") == "trigger"), None)
        if not trigger_node:
            await update_execution_status(conn, execution_id, "error", "No trigger node found")
            return {"id": execution_id}

        res = await walk_from(conn, execution_id, nodes, edges, trigger_node["id"], context)
        if not res.get("paused"):
            await update_execution_status(conn, execution_id, "success")
        return {"id": execution_id}
    except Exception as err:
        logger.error(f"[engine] Automation {automation['id']} execution error: {err}")
        await update_execution_status(conn, execution_id, "error", str(err))
        return {"id": execution_id}

async def resume_automation(execution_id: int, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    async with get_db() as conn:
        claimed = await conn.fetchrow(
            """
            UPDATE coexistence.automation_executions
               SET status = 'running'
             WHERE id = $1 AND status = 'paused' AND expires_at > NOW()
            RETURNING id, automation_id, awaiting_node_id, trigger_data, contact_number
            """,
            execution_id,
        )
        if not claimed:
            return None

        bot_row = await conn.fetchrow(
            "SELECT id, name, config FROM coexistence.chatbots WHERE id = $1",
            claimed["automation_id"],
        )
        if not bot_row:
            await update_execution_status(conn, execution_id, "error", "Automation no longer exists")
            return None

        config = bot_row["config"] or {}
        if isinstance(config, str):
            try:
                config = json.loads(config)
            except Exception:
                config = {}

        nodes = config.get("nodes") or []
        edges = config.get("edges") or []
        awaiting_node_id = claimed["awaiting_node_id"]

        context = {
            "contact_number": record.get("contact_number"),
            "message_body": record.get("message_body"),
            "message_type": record.get("message_type"),
            "trigger_data": {
                "message_id": record.get("message_id"),
                "wa_number": record.get("wa_number"),
                "phone_number_id": record.get("phone_number_id"),
            },
        }

        # Follow outgoing edge from awaiting node
        from_edges = [e for e in edges if e.get("from") == awaiting_node_id]
        if not from_edges:
            await update_execution_status(conn, execution_id, "success")
            return {"id": execution_id}

        start_node_id = from_edges[0].get("to")
        res = await walk_from(conn, execution_id, nodes, edges, start_node_id, context)
        if not res.get("paused"):
            await update_execution_status(conn, execution_id, "success")
        return {"id": execution_id}

async def evaluate_triggers(message_record: Dict[str, Any]) -> List[Dict[str, Any]]:
    executions = []
    try:
        org_id = message_record.get("org_id")
        async with get_db() as conn:
            if org_id:
                automations = await conn.fetch(
                    "SELECT id, name, status, trigger_type, config FROM coexistence.chatbots WHERE status = 'active' AND org_id = $1::uuid",
                    str(org_id),
                )
            else:
                automations = await conn.fetch(
                    "SELECT id, name, status, trigger_type, config FROM coexistence.chatbots WHERE status = 'active'"
                )

            context = {
                "org_id": str(org_id) if org_id else None,
                "contact_number": message_record.get("contact_number"),
                "message_body": message_record.get("message_body"),
                "message_type": message_record.get("message_type"),
                "trigger_type": "keyword",
                "trigger_data": {
                    "message_id": message_record.get("message_id"),
                    "wa_number": message_record.get("wa_number"),
                    "phone_number_id": message_record.get("phone_number_id"),
                    "timestamp": message_record.get("timestamp"),
                    "media_url": message_record.get("media_url"),
                    "media_mime_type": message_record.get("media_mime_type"),
                    "status": message_record.get("status"),
                },
            }

            c_row = await conn.fetchrow(
                "SELECT name, profile_name, tags, custom_fields FROM coexistence.contacts WHERE wa_number = $1 AND contact_number = $2 LIMIT 1",
                message_record.get("wa_number"),
                message_record.get("contact_number"),
            )
            if c_row:
                context["contact"] = {
                    "name": c_row["name"],
                    "profile_name": c_row["profile_name"],
                    "contact_number": message_record.get("contact_number"),
                    "tags": c_row["tags"] or [],
                    "custom_fields": c_row["custom_fields"] or {},
                }

            for bot in automations:
                cfg = bot["config"] or {}
                if isinstance(cfg, str):
                    try:
                        cfg = json.loads(cfg)
                    except Exception:
                        cfg = {}
                nodes = cfg.get("nodes") or []
                trigger_node = next((n for n in nodes if n.get("type") == "trigger"), None)
                if not trigger_node:
                    continue

                trigger_accounts = trigger_node.get("triggerAccounts") or []
                if trigger_accounts and message_record.get("wa_number") not in trigger_accounts:
                    continue

                if trigger_node.get("triggerKind", "keyword") != "keyword":
                    continue

                kw = trigger_node.get("keyword") or ""
                match_type = trigger_node.get("matchType", "exact")
                case_sensitive = bool(trigger_node.get("caseSensitive"))

                if matches_keyword(message_record.get("message_body"), kw, match_type, case_sensitive):
                    logger.info(f"[engine] Keyword match: automation={bot['id']} keyword='{kw}'")
                    execution = await execute_automation(conn, dict(bot), context)
                    if execution:
                        executions.append(execution)

    except Exception as e:
        logger.error(f"[engine] evaluate_triggers error: {e}")

    return executions
