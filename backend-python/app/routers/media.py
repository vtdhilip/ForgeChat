import os
import re
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query, Request, Response
from fastapi.responses import FileResponse, StreamingResponse
from app.core.database import db
from app.middleware.auth import get_current_user, assert_contact_access

router = APIRouter(prefix="/api/media", tags=["Media"])

MEDIA_DIR = os.getenv("MEDIA_DIR", "/app/media")

def resolve_safe(abs_path: str) -> Optional[str]:
    if not abs_path:
        return None
    resolved = os.path.realpath(abs_path)
    base = os.path.realpath(MEDIA_DIR)
    if not resolved.startswith(base + os.sep) and resolved != base:
        return None
    return resolved

@router.get("/{message_id}")
async def get_media(
    message_id: str,
    request: Request,
    download: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    row = await db.fetchrow(
        """
        SELECT message_id, message_type, media_storage_path, media_mime_type,
               media_status, media_filename, message_body, wa_number, contact_number
        FROM coexistence.chat_history
        WHERE message_id = $1
        """,
        message_id
    )
    if not row:
        raise HTTPException(status_code=404, detail="Message not found")

    await assert_contact_access(user, row["wa_number"], row["contact_number"])

    if row["media_status"] != "stored" or not row["media_storage_path"]:
        raise HTTPException(status_code=404, detail="Media not available")

    safe_path = resolve_safe(row["media_storage_path"])
    if not safe_path or not os.path.isfile(safe_path):
        raise HTTPException(status_code=404, detail="File missing on disk")

    mime = row["media_mime_type"] or "application/octet-stream"
    file_size = os.path.getsize(safe_path)
    fname = row["media_filename"] or row["message_body"] or message_id
    clean_fname = re.sub(r"[^\w. -]", "_", fname)

    content_disposition = (
        f'attachment; filename="{clean_fname}"'
        if download == "1" or row["message_type"] == "document"
        else f'inline; filename="{clean_fname}"'
    )

    headers = {
        "Accept-Ranges": "bytes",
        "Cache-Control": "private, max-age=86400",
        "Content-Disposition": content_disposition
    }

    # Handle Range header
    range_header = request.headers.get("Range")
    if range_header:
        m = re.match(r"bytes=(\d*)-(\d*)", range_header)
        if m:
            start_str, end_str = m.groups()
            start = int(start_str) if start_str else 0
            end = int(end_str) if end_str else file_size - 1
            if end >= file_size:
                end = file_size - 1
            if start > end or start >= file_size:
                return Response(status_code=416, headers={"Content-Range": f"bytes */{file_size}"})

            chunk_len = end - start + 1
            headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
            headers["Content-Length"] = str(chunk_len)

            def iter_file():
                with open(safe_path, "rb") as f:
                    f.seek(start)
                    remaining = chunk_len
                    while remaining > 0:
                        chunk = f.read(min(remaining, 64 * 1024))
                        if not chunk:
                            break
                        remaining -= len(chunk)
                        yield chunk

            return StreamingResponse(iter_file(), status_code=206, media_type=mime, headers=headers)

    return FileResponse(safe_path, media_type=mime, headers=headers)

@router.post("/{message_id}/retry")
async def retry_media(message_id: str, user: dict = Depends(get_current_user)):
    row = await db.fetchrow(
        "SELECT wa_number, contact_number FROM coexistence.chat_history WHERE message_id = $1",
        message_id
    )
    if not row:
        raise HTTPException(status_code=404, detail="Message not found")

    await assert_contact_access(user, row["wa_number"], row["contact_number"])
    return {"ok": True, "message": "Retry queued"}
