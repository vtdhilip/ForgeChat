import re
import json
from typing import Optional, List, Dict, Any, Union

def extract_var_indexes(text: Optional[str]) -> List[str]:
    matches = re.findall(r"\{\{\s*(\d+)\s*\}\}", str(text or ""))
    seen = set()
    out = []
    for m in matches:
        if m not in seen:
            seen.add(m)
            out.append(m)
    out.sort(key=lambda x: int(x))
    return out

def as_array(v: Any) -> list:
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        try:
            p = json.loads(v)
            if isinstance(p, list):
                return p
        except Exception:
            pass
    return []

def as_object(v: Any) -> dict:
    if isinstance(v, dict):
        return v
    if isinstance(v, str):
        try:
            p = json.loads(v)
            if isinstance(p, dict):
                return p
        except Exception:
            pass
    return {}

def resolve_template_param(src: Any, recipient: Optional[dict] = None) -> str:
    s = str(src or "").strip()
    if not s:
        return ""
    ctx = recipient or {}
    if s == "name":
        return ctx.get("name") or ""
    if s == "contact_number":
        return ctx.get("contact_number") or ""
    if s.startswith("custom_fields."):
        field_id = s[len("custom_fields."):]
        cf = ctx.get("custom_fields") or {}
        val = cf.get(field_id)
        return str(val) if val is not None else ""
    if s.startswith("category_tag."):
        cat_id = s[len("category_tag."):]
        tags = ctx.get("tags") or []
        for t in tags:
            if isinstance(t, dict) and str(t.get("category_id")) == str(cat_id):
                return t.get("name") or ""
        return ""

    out = s
    out = re.sub(r"\{\{\s*contact\.name\s*\}\}", ctx.get("name") or "", out)
    out = re.sub(r"\{\{\s*contact\.number\s*\}\}", ctx.get("contact_number") or "", out)
    out = re.sub(r"\{\{\s*name\s*\}\}", ctx.get("name") or "", out)
    out = re.sub(r"\{\{\s*contact_number\s*\}\}", ctx.get("contact_number") or "", out)
    return out

def resolve_value(values: dict, samples: dict, key: str, recipient: Optional[dict] = None) -> str:
    mapped = values.get(key) if values.get(key) is not None and values.get(key) != "" else samples.get(key, "")
    return resolve_template_param(mapped, recipient)

def resolve_template_text(text: Optional[str], values: dict, samples: dict, recipient: Optional[dict] = None) -> str:
    def replacer(match):
        n = match.group(1)
        v = resolve_value(values, samples, n, recipient)
        return v if v else f"{{{{{n}}}}}"

    return re.sub(r"\{\{\s*(\d+)\s*\}\}", replacer, str(text or ""))

def build_template_components(
    template: Optional[dict] = None,
    values: Optional[dict] = None,
    header_media_id: Optional[str] = None,
    recipient: Optional[dict] = None
) -> List[dict]:
    tpl = template or {}
    components = []
    samples = as_object(tpl.get("samples"))
    vals = as_object(values)

    ht = str(tpl.get("header_type") or "NONE").upper()
    if ht in ("IMAGE", "VIDEO", "DOCUMENT"):
        if header_media_id:
            key = ht.lower()
            components.append({
                "type": "header",
                "parameters": [{"type": key, key: {"id": header_media_id}}]
            })
    elif ht == "TEXT":
        hv = extract_var_indexes(tpl.get("header_text"))
        if hv:
            components.append({
                "type": "header",
                "parameters": [{"type": "text", "text": resolve_value(vals, samples, k, recipient) or " "} for k in hv]
            })

    body_vars = extract_var_indexes(tpl.get("body"))
    if body_vars:
        components.append({
            "type": "body",
            "parameters": [{"type": "text", "text": resolve_value(vals, samples, k, recipient) or " "} for k in body_vars]
        })

    for index, btn in enumerate(as_array(tpl.get("buttons"))):
        btn_type = str(btn.get("type") or "").upper()
        if btn_type in ("COPY_CODE", "OTP"):
            code = btn.get("value") or btn.get("coupon_code") or btn.get("example") or ""
            if code:
                components.append({
                    "type": "button",
                    "sub_type": "copy_code",
                    "index": str(index),
                    "parameters": [{"type": "coupon_code", "coupon_code": str(code)}]
                })
        elif btn_type == "URL":
            url_str = str(btn.get("value") or "")
            if re.search(r"\{\{\s*\d+\s*\}\}", url_str):
                idx = extract_var_indexes(url_str)[0] if extract_var_indexes(url_str) else "1"
                suffix = btn.get("urlSample") or resolve_value(vals, samples, idx, recipient) or " "
                components.append({
                    "type": "button",
                    "sub_type": "url",
                    "index": str(index),
                    "parameters": [{"type": "text", "text": str(suffix)}]
                })

    return components
