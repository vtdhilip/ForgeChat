from fastapi import APIRouter, HTTPException, Depends, Query, Request
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from app.core.database import db
from app.core.crypto import encrypt, decrypt, mask_secret
from app.middleware.auth import get_current_user, require_admin

router = APIRouter(prefix="/api/ai-models", tags=["AI Models"])

SUPPORTED = {"anthropic", "openai"}
PROVIDER_LABELS = {"anthropic": "Anthropic Claude", "openai": "OpenAI"}

def shape_model(row: dict, reveal: bool = False) -> Optional[dict]:
    if not row:
        return None
    api_key = decrypt(row.get("api_key_encrypted"))
    return {
        "id": row["id"],
        "provider": row["provider"],
        "providerLabel": PROVIDER_LABELS.get(row["provider"], row["provider"]),
        "label": row.get("label"),
        "apiKeyMasked": mask_secret(api_key or ""),
        "apiKey": api_key if reveal else None,
        "createdAt": row["created_at"].isoformat() if row.get("created_at") else None,
        "updatedAt": row["updated_at"].isoformat() if row.get("updated_at") else None,
    }

class AIModelCreate(BaseModel):
    provider: str
    apiKey: str
    label: Optional[str] = None

class AIModelUpdate(BaseModel):
    apiKey: Optional[str] = None
    label: Optional[str] = None

@router.get("")
async def list_ai_models(user: dict = Depends(get_current_user)):
    rows = await db.fetch("SELECT * FROM coexistence.ai_models ORDER BY created_at DESC")
    return [shape_model(dict(r)) for r in rows]

@router.get("/{model_id}")
async def get_ai_model(
    model_id: int,
    reveal: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    row = await db.fetchrow("SELECT * FROM coexistence.ai_models WHERE id = $1", model_id)
    if not row:
        raise HTTPException(status_code=404, detail="AI Model not found")
    should_reveal = reveal == "1" and user.get("role") == "admin"
    return shape_model(dict(row), reveal=should_reveal)

@router.post("", status_code=201)
async def create_ai_model(payload: AIModelCreate, admin: dict = Depends(require_admin)):
    provider = payload.provider.strip().lower()
    if provider not in SUPPORTED:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")
    api_key = payload.apiKey.strip()
    if not api_key:
        raise HTTPException(status_code=400, detail="API key is required")

    enc_key = encrypt(api_key)
    row = await db.fetchrow(
        """
        INSERT INTO coexistence.ai_models (provider, api_key_encrypted, label)
        VALUES ($1, $2, $3)
        RETURNING *
        """,
        provider, enc_key, payload.label.strip() if payload.label else None
    )
    return shape_model(dict(row), reveal=True)

@router.put("/{model_id}")
async def update_ai_model(model_id: int, payload: AIModelUpdate, admin: dict = Depends(require_admin)):
    ex = await db.fetchrow("SELECT * FROM coexistence.ai_models WHERE id = $1", model_id)
    if not ex:
        raise HTTPException(status_code=404, detail="AI Model not found")

    sets = ["updated_at = NOW()"]
    params = [model_id]
    if payload.apiKey:
        params.append(encrypt(payload.apiKey.strip()))
        sets.append(f"api_key_encrypted = ${len(params)}")
    if payload.label is not None:
        params.append(payload.label.strip() if payload.label else None)
        sets.append(f"label = ${len(params)}")

    query = f"UPDATE coexistence.ai_models SET {', '.join(sets)} WHERE id = $1 RETURNING *"
    row = await db.fetchrow(query, *params)
    return shape_model(dict(row), reveal=True)

@router.delete("/{model_id}")
async def delete_ai_model(model_id: int, admin: dict = Depends(require_admin)):
    res = await db.execute("DELETE FROM coexistence.ai_models WHERE id = $1", model_id)
    if res.endswith(" 0"):
        raise HTTPException(status_code=404, detail="AI Model not found")
    return {"ok": True}
