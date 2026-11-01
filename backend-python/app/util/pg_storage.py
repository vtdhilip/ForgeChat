from typing import Optional
from app.core.database import db

async def ensure_bucket():
    await db.execute("""
        CREATE TABLE IF NOT EXISTS coexistence.media_objects (
          object_key  TEXT PRIMARY KEY,
          data        BYTEA NOT NULL,
          mime_type   TEXT,
          size_bytes  BIGINT,
          created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

async def put_object(object_key: str, buffer: bytes, mime_type: Optional[str] = None):
    await db.execute(
        """
        INSERT INTO coexistence.media_objects (object_key, data, mime_type, size_bytes)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (object_key) DO UPDATE
          SET data = EXCLUDED.data,
              mime_type = EXCLUDED.mime_type,
              size_bytes = EXCLUDED.size_bytes
        """,
        object_key, buffer, mime_type, len(buffer)
    )

async def get_object_buffer(object_key: str) -> bytes:
    data = await db.fetchval(
        "SELECT data FROM coexistence.media_objects WHERE object_key = $1",
        object_key
    )
    if data is None:
        raise Exception(f"Media object not found: {object_key}")
    return bytes(data)

async def remove_object(object_key: str):
    try:
        await db.execute("DELETE FROM coexistence.media_objects WHERE object_key = $1", object_key)
    except Exception:
        pass
