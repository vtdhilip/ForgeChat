import os
import httpx
from typing import Optional, Dict, Any, List

META_API_VERSION = os.getenv("META_API_VERSION", "v21.0")

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
            err_msg = parsed.get("error", {}).get("message") if parsed else resp.text[:300]
            raise Exception(f"Meta {resp.status_code}: {err_msg}")
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
            raise Exception(f"Meta upload error {resp.status_code}: {resp.text[:300]}")
        parsed = resp.json()
        media_id = parsed.get("id")
        if not media_id:
            raise Exception("Meta media upload did not return an ID")
        return media_id
