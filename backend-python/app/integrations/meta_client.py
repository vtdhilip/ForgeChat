import os
import json
import httpx
from typing import Optional, Dict, Any, List

META_API_VERSION = os.getenv("META_API_VERSION", "v21.0")

class MetaAPIError(Exception):
    """Structured error raised when Meta Graph API returns HTTP 4xx or 5xx."""
    def __init__(self, status_code: int, error_dict: Optional[dict] = None, raw_text: str = ""):
        self.status_code = status_code
        self.error_dict = error_dict or {}
        self.raw_text = raw_text
        
        err = self.error_dict.get("error") if isinstance(self.error_dict, dict) else {}
        if not isinstance(err, dict):
            err = {}
            
        self.message = err.get("message") or (raw_text[:300] if raw_text else "Unknown Meta error")
        self.code = err.get("code")
        self.subcode = err.get("error_subcode")
        self.user_title = err.get("error_user_title")
        self.user_msg = err.get("error_user_msg")
        self.error_data = err.get("error_data")
        
        parts = [f"Meta {status_code}: {self.message}"]
        if self.subcode:
            parts.append(f"(subcode {self.subcode})")
        if self.user_title:
            parts.append(f"({self.user_title})")
        if self.user_msg:
            parts.append(f"- {self.user_msg}")
        elif isinstance(self.error_data, dict):
            if self.error_data.get("details"):
                parts.append(f"- {self.error_data['details']}")
            else:
                try:
                    parts.append(f"- {json.dumps(self.error_data)}")
                except Exception:
                    pass
        elif isinstance(self.error_data, str) and self.error_data:
            parts.append(f"- {self.error_data}")
        super().__init__(" ".join(parts))

    @property
    def is_duplicate(self) -> bool:
        full_text = f"{self.message} {self.user_title or ''} {self.user_msg or ''} {self.error_data or ''}".lower()
        return (
            self.subcode in (2388091, 2388046, 2388024, 2388027) or
            "already exists" in full_text or
            "duplicate" in full_text
        )

def _url(phone_number_id: str, path: str = "messages") -> str:
    return f"https://graph.facebook.com/{META_API_VERSION}/{phone_number_id}/{path}"

async def post_json(endpoint: str, access_token: str, payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            endpoint,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json=payload
        )
        try:
            parsed = resp.json()
        except Exception:
            parsed = None
        
        if resp.status_code >= 400:
            raise MetaAPIError(resp.status_code, parsed, resp.text)
        return parsed or {}

async def send_text(
    access_token: str,
    phone_number_id: str,
    to: str,
    body: str,
    preview_url: bool = False,
    context_message_id: Optional[str] = None
) -> dict:
    data = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": str(to),
        "type": "text",
        "text": {"body": str(body), "preview_url": bool(preview_url)}
    }
    if context_message_id:
        data["context"] = {"message_id": context_message_id}
    return await post_json(_url(phone_number_id), access_token, data)

async def send_template(
    access_token: str,
    phone_number_id: str,
    to: str,
    template_name: str,
    language_code: str = "en",
    components: Optional[List[dict]] = None
) -> dict:
    data = {
        "messaging_product": "whatsapp",
        "to": str(to),
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language_code},
            "components": components or []
        }
    }
    return await post_json(_url(phone_number_id), access_token, data)

async def send_media(
    access_token: str,
    phone_number_id: str,
    to: str,
    media_type: str,
    media_id: Optional[str] = None,
    link: Optional[str] = None,
    caption: Optional[str] = None,
    filename: Optional[str] = None,
    context_message_id: Optional[str] = None
) -> dict:
    media = {}
    if media_id:
        media["id"] = media_id
    elif link:
        media["link"] = link
    else:
        raise ValueError("send_media: media_id or link required")

    if caption and media_type in ("image", "video", "document"):
        media["caption"] = caption
    if filename and media_type == "document":
        media["filename"] = filename

    data = {
        "messaging_product": "whatsapp",
        "to": str(to),
        "type": media_type,
        media_type: media
    }
    if context_message_id:
        data["context"] = {"message_id": context_message_id}
    return await post_json(_url(phone_number_id), access_token, data)

async def send_reaction(
    access_token: str,
    phone_number_id: str,
    to: str,
    message_id: str,
    emoji: str
) -> dict:
    data = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": str(to),
        "type": "reaction",
        "reaction": {
            "message_id": message_id,
            "emoji": emoji or ""
        }
    }
    return await post_json(_url(phone_number_id), access_token, data)

async def upload_media(
    access_token: str,
    phone_number_id: str,
    file_bytes: bytes,
    mime_type: str,
    filename: Optional[str] = None
) -> str:
    url = _url(phone_number_id, "media")
    async with httpx.AsyncClient(timeout=60.0) as client:
        files = {
            "file": (filename or "upload", file_bytes, mime_type)
        }
        data = {
            "messaging_product": "whatsapp",
            "type": mime_type
        }
        resp = await client.post(
            url,
            headers={"Authorization": f"Bearer {access_token}"},
            data=data,
            files=files
        )
        if resp.status_code >= 400:
            try:
                parsed = resp.json()
            except Exception:
                parsed = None
            raise MetaAPIError(resp.status_code, parsed, resp.text)
        parsed = resp.json()
        media_id = parsed.get("id")
        if not media_id:
            raise Exception("Meta media upload did not return an ID")
        return media_id

async def submit_template(waba_id: str, access_token: str, payload: dict) -> dict:
    url = f"https://graph.facebook.com/{META_API_VERSION}/{waba_id}/message_templates"
    return await post_json(url, access_token, payload)

async def delete_template(waba_id: str, access_token: str, name: str) -> bool:
    url = f"https://graph.facebook.com/{META_API_VERSION}/{waba_id}/message_templates"
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.delete(
            url,
            params={"name": name},
            headers={"Authorization": f"Bearer {access_token}"}
        )
        if resp.status_code >= 400:
            try:
                parsed = resp.json()
            except Exception:
                parsed = None
            raise MetaAPIError(resp.status_code, parsed, resp.text)
        return True

async def list_templates(
    waba_id: str,
    access_token: str,
    fields: Optional[str] = None,
    name: Optional[str] = None,
    limit: int = 100
) -> List[dict]:
    f = fields or "name,language,status,category,previous_category,quality_score,rejected_reason,id"
    url = f"https://graph.facebook.com/{META_API_VERSION}/{waba_id}/message_templates"
    params: Dict[str, Any] = {"fields": f, "limit": limit}
    if name:
        params["name"] = name
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            url,
            params=params,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        if resp.status_code >= 400:
            # Only if a request with name filter failed with 400, retry without name filter and filter in Python
            if name and resp.status_code == 400:
                all_templates = await list_templates(waba_id, access_token, fields=fields, name=None, limit=limit)
                return [t for t in all_templates if t.get("name") == name]
            try:
                parsed = resp.json()
            except Exception:
                parsed = None
            raise MetaAPIError(resp.status_code, parsed, resp.text)
        data = resp.json()
        return data.get("data", [])

async def get_template(
    template_id: str,
    access_token: str,
    fields: Optional[str] = None
) -> Optional[dict]:
    f = fields or "name,language,status,category,previous_category,quality_score,rejected_reason,id"
    url = f"https://graph.facebook.com/{META_API_VERSION}/{template_id}"
    params = {"fields": f}
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            url,
            params=params,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        if resp.status_code >= 400:
            try:
                parsed = resp.json()
            except Exception:
                parsed = None
            raise MetaAPIError(resp.status_code, parsed, resp.text)
        return resp.json()

async def edit_template(
    target_id: str,
    access_token: str,
    payload_or_template_id: Any,
    maybe_payload: Optional[dict] = None
) -> dict:
    if maybe_payload is not None:
        template_id = payload_or_template_id
        payload = maybe_payload
    else:
        template_id = target_id
        payload = payload_or_template_id
    url = f"https://graph.facebook.com/{META_API_VERSION}/{template_id}"
    return await post_json(url, access_token, payload)
