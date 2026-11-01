import os
import hashlib
import time
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File, Form, Response
from pydantic import BaseModel

from app.core.database import db
from app.middleware.auth import get_current_user, require_permission
from app.util import pg_storage
from app.integrations import meta_client
from app.services.whatsapp_service import get_account_with_token

router = APIRouter(prefix="/api/media-library", tags=["Media Library"])

def infer_media_type(mime: str) -> str:
    if mime.startswith("image/"):
        return "image"
    if mime.startswith("video/"):
        return "video"
    if mime.startswith("audio/"):
        return "audio"
    return "document"

def row_to_media(r: dict) -> dict:
    return {
        "id": r["id"],
        "filename": r["filename"],
        "originalName": r["original_name"],
        "name": r["name"],
        "mimeType": r["mime_type"],
        "sizeBytes": int(r["size_bytes"]),
        "mediaType": r["media_type"],
        "sha256": r["sha256"],
        "autoResync": r["auto_resync"],
        "notes": r["notes"],
        "whatsappAccountId": r["whatsapp_account_id"],
        "uploadedAt": r["uploaded_at"].isoformat() if r.get("uploaded_at") else None,
    }

def row_to_sync(r: dict) -> dict:
    return {
        "id": r["id"],
        "mediaId": r["media_id"],
        "accountId": r["account_id"],
        "metaMediaId": r["meta_media_id"],
        "syncedAt": r["synced_at"].isoformat() if r.get("synced_at") else None,
        "expiresAt": r["expires_at"].isoformat() if r.get("expires_at") else None,
        "status": r["status"],
        "lastError": r["last_error"],
        "attempts": r["attempts"],
        "updatedAt": r["updated_at"].isoformat() if r.get("updated_at") else None,
    }

async def mark_expired():
    try:
        await db.execute("""
            UPDATE coexistence.media_meta_sync
            SET status = 'expired', updated_at = NOW()
            WHERE status = 'synced' AND expires_at IS NOT NULL AND expires_at < NOW()
        """)
    except Exception as e:
        print(f"[mediaLibrary] mark_expired failed: {e}")

class MediaUpdate(BaseModel):
    name: Optional[str] = None
    notes: Optional[str] = None
    autoResync: Optional[bool] = None

@router.get("")
async def list_media(accountId: Optional[int] = None, user: dict = Depends(get_current_user)):
    await mark_expired()
    params = []
    acc_filter = ""
    if accountId:
        params.append(accountId)
        acc_filter = f"AND (whatsapp_account_id = ${len(params)} OR whatsapp_account_id IS NULL)"

    media_rows = await db.fetch(
        f"SELECT * FROM coexistence.media_library WHERE deleted_at IS NULL {acc_filter} ORDER BY uploaded_at DESC LIMIT 500",
        *params
    )
    ids = [r["id"] for r in media_rows]
    syncs = []
    if ids:
        s_params = [ids]
        s_acc = ""
        if accountId:
            s_params.append(accountId)
            s_acc = "AND account_id = $2"
        syncs = await db.fetch(
            f"SELECT * FROM coexistence.media_meta_sync WHERE media_id = ANY($1::bigint[]) {s_acc}",
            *s_params
        )

    syncs_by_media = {}
    for s in syncs:
        syncs_by_media.setdefault(s["media_id"], []).append(row_to_sync(dict(s)))

    return {
        "media": [{**row_to_media(dict(m)), "syncs": syncs_by_media.get(m["id"], [])} for m in media_rows]
    }

@router.post("")
async def upload_media(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    accountId: Optional[int] = Form(None),
    user: dict = Depends(require_permission("media-library"))
):
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="No file uploaded")

    mime = file.content_type or "application/octet-stream"
    sha = hashlib.sha256(contents).hexdigest()
    ext = os.path.splitext(file.filename or "")[1].lower()
    stored = f"{int(time.time() * 1000)}-{os.urandom(6).hex()}{ext}"
    object_key = f"library/{stored}"
    m_type = infer_media_type(mime)

    target_account_id = accountId
    if not target_account_id:
        def_row = await db.fetchrow("SELECT id FROM coexistence.whatsapp_accounts ORDER BY is_default DESC, id ASC LIMIT 1")
        target_account_id = def_row["id"] if def_row else None

    await pg_storage.ensure_bucket()
    await pg_storage.put_object(object_key, contents, mime)

    clean_name = name[:255] if name else None
    clean_notes = notes[:500] if notes else None

    row = await db.fetchrow(
        """
        INSERT INTO coexistence.media_library
          (filename, original_name, name, mime_type, size_bytes, media_type,
           storage_backend, storage_key, sha256, notes, uploaded_by, whatsapp_account_id)
        VALUES ($1, $2, $3, $4, $5, $6, 'postgres', $7, $8, $9, $10, $11)
        RETURNING *
        """,
        stored, file.filename, clean_name, mime, len(contents), m_type,
        object_key, sha, clean_notes, user.get("id"), target_account_id
    )
    return {"media": row_to_media(dict(row))}

@router.put("/{media_id}")
async def update_media(
    media_id: int,
    payload: MediaUpdate,
    user: dict = Depends(require_permission("media-library"))
):
    fields = []
    vals = [media_id]
    if payload.autoResync is not None:
        vals.append(payload.autoResync)
        fields.append(f"auto_resync = ${len(vals)}")
    if payload.name is not None:
        vals.append(payload.name[:255] if payload.name else None)
        fields.append(f"name = ${len(vals)}")
    if payload.notes is not None:
        vals.append(payload.notes[:500] if payload.notes else None)
        fields.append(f"notes = ${len(vals)}")

    if not fields:
        raise HTTPException(status_code=400, detail="Nothing to update")

    query = f"UPDATE coexistence.media_library SET {', '.join(fields)} WHERE id = $1 AND deleted_at IS NULL RETURNING *"
    row = await db.fetchrow(query, *vals)
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    return {"media": row_to_media(dict(row))}

@router.delete("/{media_id}")
async def delete_media(media_id: int, user: dict = Depends(require_permission("media-library"))):
    row = await db.fetchrow(
        "UPDATE coexistence.media_library SET deleted_at = NOW() WHERE id = $1 AND deleted_at IS NULL RETURNING storage_key",
        media_id
    )
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    await pg_storage.remove_object(row["storage_key"])
    return {"ok": True}

@router.get("/{media_id}/download")
async def download_media(media_id: int, user: dict = Depends(get_current_user)):
    row = await db.fetchrow(
        "SELECT storage_key, mime_type, original_name, name FROM coexistence.media_library WHERE id = $1 AND deleted_at IS NULL",
        media_id
    )
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    data = await pg_storage.get_object_buffer(row["storage_key"])
    display_name = row["name"] or row["original_name"] or f"media-{media_id}"
    return Response(
        content=data,
        media_type=row["mime_type"],
        headers={"Content-Disposition": f'inline; filename="{display_name}"'}
    )

async def sync_media_to_account(media_id: int, account_id: int) -> dict:
    media = await db.fetchrow(
        "SELECT * FROM coexistence.media_library WHERE id = $1 AND deleted_at IS NULL",
        media_id
    )
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    if media["whatsapp_account_id"] is not None and int(media["whatsapp_account_id"]) != int(account_id):
        raise HTTPException(status_code=400, detail="This media belongs to a different WhatsApp account")

    account = await get_account_with_token(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="WhatsApp account not found")

    await db.execute(
        """
        INSERT INTO coexistence.media_meta_sync
          (media_id, account_id, status, attempts, updated_at)
        VALUES ($1, $2, 'syncing', 1, NOW())
        ON CONFLICT (media_id, account_id) DO UPDATE
          SET status = 'syncing', attempts = coexistence.media_meta_sync.attempts + 1, updated_at = NOW()
        """,
        media_id, account_id
    )

    try:
        buf = await pg_storage.get_object_buffer(media["storage_key"])
        meta_id = await meta_client.upload_media(
            access_token=account["accessToken"],
            phone_number_id=account["phoneNumberId"],
            file_bytes=buf,
            mime_type=media["mime_type"],
            filename=media["original_name"]
        )
        row = await db.fetchrow(
            """
            UPDATE coexistence.media_meta_sync
            SET meta_media_id = $1, status = 'synced', synced_at = NOW(),
                expires_at = NOW() + INTERVAL '28 days',
                last_error = NULL, updated_at = NOW()
            WHERE media_id = $2 AND account_id = $3
            RETURNING *
            """,
            meta_id, media_id, account_id
        )
        return row_to_sync(dict(row))
    except Exception as err:
        await db.execute(
            """
            UPDATE coexistence.media_meta_sync
            SET status = 'failed', last_error = $1, updated_at = NOW()
            WHERE media_id = $2 AND account_id = $3
            """,
            str(err)[:500], media_id, account_id
        )
        raise HTTPException(status_code=502, detail=f"Sync to Meta failed: {err}")

@router.post("/{media_id}/sync/{account_id}")
async def sync_media_endpoint(
    media_id: int,
    account_id: int,
    user: dict = Depends(require_permission("media-library"))
):
    sync = await sync_media_to_account(media_id, account_id)
    return {"sync": sync}
