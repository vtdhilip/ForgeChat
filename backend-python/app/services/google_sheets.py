import json
import logging
import re
from datetime import datetime
from typing import Optional, Dict, Any, List
import httpx

from app.core.config import settings
from app.services.google_auth import get_access_token
from app.services.product_catalog import resolve_product_name
from app.util.url_validator import is_safe_external_url

logger = logging.getLogger(__name__)

def col_letter(idx: int) -> str:
    s = ""
    n = int(idx)
    while n >= 0:
        s = chr(65 + (n % 26)) + s
        n = (n // 26) - 1
    return s

def norm_cell(v: Any) -> str:
    return str(v or "").strip().lower()

def digits_only(v: Any) -> str:
    return re.sub(r"\D", "", str(v or ""))

def key_match(cell: Any, key: Any) -> bool:
    nc = norm_cell(cell)
    nk = norm_cell(key)
    if nc and nc == nk:
        return True
    dc = digits_only(cell)
    dk = digits_only(key)
    return bool(dc and dc == dk)

def parse_start(range_a1: str) -> Dict[str, int]:
    m = re.search(r"!\$?([A-Z]+)\$?(\d+)", str(range_a1 or ""))
    if not m:
        return {"row": 1, "col": 0}
    col_str = m.group(1)
    col = 0
    for ch in col_str:
        col = col * 26 + (ord(ch) - 64)
    return {"row": int(m.group(2)), "col": col - 1}

async def list_spreadsheets(credential_id: int, query: str = "", page_size: int = 50) -> List[Dict[str, Any]]:
    token = await get_access_token(credential_id)
    safe_query = query.replace("'", "\\'").strip()[:100]
    q_parts = [
        "mimeType='application/vnd.google-apps.spreadsheet'",
        "trashed=false",
    ]
    if safe_query:
        q_parts.append(f"name contains '{safe_query}'")
    q = " and ".join(q_parts)

    url = "https://www.googleapis.com/drive/v3/files"
    params = {
        "q": q,
        "pageSize": max(1, min(100, page_size)),
        "fields": "files(id,name,modifiedTime)",
        "orderBy": "modifiedTime desc",
    }
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(timeout=15.0) as http:
        resp = await http.get(url, params=params, headers=headers)
        if resp.status_code != 200:
            raise RuntimeError(f"Drive API error: {resp.text}")
        data = resp.json()
        return data.get("files", [])

async def list_sheet_tabs(credential_id: int, spreadsheet_id: str) -> List[Dict[str, Any]]:
    token = await get_access_token(credential_id)
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}"
    params = {"fields": "sheets(properties(sheetId,title,gridProperties(rowCount,columnCount)))"}
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(timeout=15.0) as http:
        resp = await http.get(url, params=params, headers=headers)
        if resp.status_code != 200:
            raise RuntimeError(f"Sheets API error: {resp.text}")
        data = resp.json()
        out = []
        for s in data.get("sheets", []):
            p = s.get("properties", {})
            gp = p.get("gridProperties", {})
            out.append({
                "sheetId": p.get("sheetId"),
                "title": p.get("title"),
                "rowCount": gp.get("rowCount"),
                "columnCount": gp.get("columnCount"),
            })
        return out

async def read(credential_id: int, spreadsheet_id: str, sheet_name: str, args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    token = await get_access_token(credential_id)
    args = args or {}
    range_param = args.get("range")
    if range_param:
        r = range_param if "!" in range_param else f"'{sheet_name}'!{range_param}"
    else:
        r = f"'{sheet_name}'"

    url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{r}"
    params = {"valueRenderOption": "UNFORMATTED_VALUE"}
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(timeout=15.0) as http:
        resp = await http.get(url, params=params, headers=headers)
        if resp.status_code != 200:
            raise RuntimeError(f"Sheets read error: {resp.text}")
        data = resp.json()
        rows = data.get("values", [])
        max_rows = max(1, min(500, int(args.get("max_rows") or 100)))
        return {
            "range": data.get("range"),
            "rowCount": len(rows),
            "truncated": len(rows) > max_rows,
            "rows": rows[:max_rows],
        }

async def append(credential_id: int, spreadsheet_id: str, sheet_name: str, args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    token = await get_access_token(credential_id)
    args = args or {}
    values = args.get("values") or []
    if not isinstance(values, list) or not values:
        raise ValueError("append requires args.values as a non-empty array")

    url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/'{sheet_name}':append"
    params = {"valueInputOption": "USER_ENTERED", "insertDataOption": "INSERT_ROWS"}
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=15.0) as http:
        resp = await http.post(url, params=params, headers=headers, json={"values": [values]})
        if resp.status_code != 200:
            raise RuntimeError(f"Sheets append error: {resp.text}")
        data = resp.json()
        updates = data.get("updates", {})
        return {
            "updatedRange": updates.get("updatedRange"),
            "updatedRows": updates.get("updatedRows"),
            "updatedColumns": updates.get("updatedColumns"),
        }

async def update(credential_id: int, spreadsheet_id: str, sheet_name: str, args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    token = await get_access_token(credential_id)
    args = args or {}
    range_arg = args.get("range")
    if not range_arg:
        raise ValueError("update requires args.range (e.g. 'A2:C2' or 'Sheet1!B5')")
    values = args.get("values")
    if not isinstance(values, list):
        raise ValueError("update requires args.values as a 2D array of rows")

    r = range_arg if "!" in range_arg else f"'{sheet_name}'!{range_arg}"
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{r}"
    params = {"valueInputOption": "USER_ENTERED"}
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=15.0) as http:
        resp = await http.put(url, params=params, headers=headers, json={"values": values})
        if resp.status_code != 200:
            raise RuntimeError(f"Sheets update error: {resp.text}")
        data = resp.json()
        return {
            "updatedRange": data.get("updatedRange"),
            "updatedRows": data.get("updatedRows"),
            "updatedColumns": data.get("updatedColumns"),
        }

async def upsert(credential_id: int, spreadsheet_id: str, sheet_name: str, args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args = args or {}
    key_column = args.get("key_column")
    key_value = args.get("key_value")
    fields = args.get("fields")

    if not key_column:
        raise ValueError('upsert requires args.key_column (e.g. "Phone Number")')
    if key_value is None or key_value == "":
        raise ValueError("upsert requires args.key_value")
    if not fields or not isinstance(fields, dict):
        raise ValueError('upsert requires args.fields as a dictionary')

    token = await get_access_token(credential_id)
    url_read = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/'{sheet_name}'!A1:Z2000"
    params_read = {"valueRenderOption": "UNFORMATTED_VALUE"}
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(timeout=15.0) as http:
        resp = await http.get(url_read, params=params_read, headers=headers)
        if resp.status_code != 200:
            raise RuntimeError(f"Sheets read error during upsert: {resp.text}")
        read_data = resp.json()

    rows = read_data.get("values", [])
    start = parse_start(read_data.get("range", ""))

    h_idx = -1
    for i, r in enumerate(rows):
        if any(norm_cell(c) == norm_cell(key_column) for c in (r or [])):
            h_idx = i
            break

    if h_idx == -1:
        raise ValueError(f'Could not find a header row containing "{key_column}" in tab "{sheet_name}".')

    header = rows[h_idx]
    def col_of(name: str) -> int:
        for idx, c in enumerate(header):
            if norm_cell(c) == norm_cell(name):
                return idx
        return -1

    key_col = col_of(key_column)
    writes = []
    skipped_unknown = []
    for name, value in fields.items():
        c = col_of(name)
        if c == -1:
            skipped_unknown.append(name)
        else:
            writes.append({"col": c, "value": value})

    if not writes:
        raise ValueError(f'None of the given field names matched a column header in "{sheet_name}". Headers: {[h for h in header if h]}')

    d_idx = -1
    for i in range(h_idx + 1, len(rows)):
        row_vals = rows[i] or []
        cell_val = row_vals[key_col] if key_col < len(row_vals) else None
        if key_match(cell_val, key_value):
            d_idx = i
            break

    async def write_span(abs_row: int, min_c: int, max_c: int, span: List[Any]):
        url_write = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/'{sheet_name}'!{col_letter(min_c)}{abs_row}:{col_letter(max_c)}{abs_row}"
        async with httpx.AsyncClient(timeout=15.0) as http:
            res = await http.put(
                url_write,
                params={"valueInputOption": "USER_ENTERED"},
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={"values": [span]},
            )
            if res.status_code != 200:
                raise RuntimeError(f"Sheets write error: {res.text}")

    if d_idx != -1:
        abs_row = start["row"] + d_idx
        cols = [w["col"] for w in writes]
        min_c, max_c = min(cols), max(cols)
        existing = rows[d_idx] or []
        span = []
        for c in range(min_c, max_c + 1):
            w = next((x for x in writes if x["col"] == c), None)
            if w:
                span.append(w["value"])
            else:
                span.append(existing[c] if c < len(existing) and existing[c] is not None else "")
        await write_span(abs_row, min_c, max_c, span)
        return {
            "action": "updated",
            "row": abs_row,
            "key": {"column": key_column, "value": key_value},
            "wrote": [header[w["col"]] for w in writes],
            "skippedUnknownColumns": skipped_unknown,
        }

    last_non_empty = -1
    for i, r in enumerate(rows):
        if any(str(c or "").strip() for c in (r or [])):
            last_non_empty = i

    target_row = start["row"] + last_non_empty + 1
    max_c = max(key_col, *[w["col"] for w in writes])
    row_arr = ["" for _ in range(max_c + 1)]
    row_arr[key_col] = key_value
    for w in writes:
        row_arr[w["col"]] = w["value"]

    await write_span(target_row, 0, max_c, row_arr)
    return {
        "action": "appended",
        "row": target_row,
        "key": {"column": key_column, "value": key_value},
        "wrote": [header[w["col"]] for w in writes],
        "skippedUnknownColumns": skipped_unknown,
    }

async def execute_op(op: str, tool_config: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
    allowed = tool_config.get("ops") or []
    if op not in allowed:
        raise ValueError(f"Operation '{op}' is not enabled for this Sheets tool. Enabled: {', '.join(allowed) or 'none'}")

    cred_id = tool_config.get("google_account_id")
    spreadsheet_id = tool_config.get("spreadsheet_id")
    sheet_name = tool_config.get("sheet_name")

    if op == "read":
        return await read(cred_id, spreadsheet_id, sheet_name, args)
    if op == "append":
        return await append(cred_id, spreadsheet_id, sheet_name, args)
    if op == "update":
        return await update(cred_id, spreadsheet_id, sheet_name, args)
    if op == "upsert":
        return await upsert(cred_id, spreadsheet_id, sheet_name, args)
    raise ValueError(f"Unknown Sheets op: {op}")

async def format_product_items(product: Any, items: Any) -> str:
    if product and isinstance(product, str) and not product.strip().startswith(("[", "{")):
        return product

    raw = items or product
    if not raw:
        return "1x LINNDEN Premium Modal Trunks"

    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            return raw

    if isinstance(raw, dict):
        raw = [raw]

    if isinstance(raw, list) and raw:
        parts = []
        for it in raw:
            qty = int(it.get("quantity") or 1)
            name = it.get("title") or it.get("name") or it.get("product_name")
            if not name or name == "Product" or name.isdigit():
                if it.get("product_retailer_id"):
                    try:
                        name = await resolve_product_name(it["product_retailer_id"])
                    except Exception:
                        name = "LINNDEN Premium Modal Trunks"
            if not name or name.isdigit():
                name = "LINNDEN Premium Modal Trunks"
            price = f" (₹{it.get('item_price') or it.get('price')})" if (it.get("item_price") or it.get("price")) else ""
            parts.append(f"{qty}x {name}{price}")
        return ", ".join(parts)

    return "1x LINNDEN Premium Modal Trunks"

async def append_order_to_google_sheet(order: Dict[str, Any]) -> bool:
    webhook_url = settings.GOOGLE_SHEET_WEBHOOK_URL or settings.GOOGLE_SHEETS_WEBHOOK_URL
    if not webhook_url:
        return False

    if not is_safe_external_url(webhook_url, allow_http=False):
        logger.warning(f"[googleSheets] Blocked unsafe Google Sheets webhook URL: {webhook_url}")
        return False

    try:
        product_formatted = await format_product_items(order.get("product"), order.get("items"))
        payload = {
            "action": "append_order",
            "date": datetime.now().strftime("%d/%m/%Y, %I:%M:%S %p"),
            "order_number": order.get("order_number") or order.get("order_id") or "",
            "customer_name": order.get("contact_name") or order.get("name") or "WhatsApp Customer",
            "phone": order.get("contact_number") or order.get("phone") or "",
            "product_items": product_formatted,
            "items": product_formatted,
            "product": product_formatted,
            "order_items": product_formatted,
            "item_name": product_formatted,
            "products": product_formatted,
            "subtotal": order.get("subtotal") or "0.00",
            "shipping": order.get("shipping_fee") or "60.00",
            "total_amount": order.get("total_amount") or order.get("order_total") or "0.00",
            "delivery_address": order.get("delivery_address") or order.get("address") or "",
            "payment_link": order.get("payment_link") or "",
            "status": order.get("status") or "unpaid",
        }
        async with httpx.AsyncClient(timeout=10.0) as http:
            res = await http.post(webhook_url, json=payload)
            return res.is_success
    except Exception as e:
        logger.error(f"[googleSheets] Error appending order to Google Sheet: {e}")
        return False

async def update_order_payment_in_google_sheet(
    order_number: str,
    status: str = "paid",
    payment_id: str = "",
    courier: str = "",
    tracking_number: str = "",
    tracking_url: str = "",
) -> bool:
    webhook_url = settings.GOOGLE_SHEET_WEBHOOK_URL or settings.GOOGLE_SHEETS_WEBHOOK_URL
    if not webhook_url:
        return False

    if not is_safe_external_url(webhook_url, allow_http=False):
        logger.warning(f"[googleSheets] Blocked unsafe Google Sheets webhook URL: {webhook_url}")
        return False

    try:
        payload = {
            "action": "update_status",
            "order_number": order_number,
            "status": status.upper(),
            "payment_id": payment_id or "",
            "courier": courier or "",
            "tracking_number": tracking_number or "",
            "tracking_url": tracking_url or "",
            "updated_at": datetime.now().strftime("%d/%m/%Y, %I:%M:%S %p"),
        }
        async with httpx.AsyncClient(timeout=10.0) as http:
            res = await http.post(webhook_url, json=payload)
            return res.is_success
    except Exception as e:
        logger.error(f"[googleSheets] Error updating order status in Google Sheet: {e}")
        return False
