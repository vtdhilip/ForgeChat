import json
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel

from app.core.database import db
from app.middleware.auth import get_current_user, require_permission

router = APIRouter(prefix="/api/chatbots", tags=["Chatbots & Automations"])

SUPPORTED_TYPES = {"trigger", "message", "condition", "delay", "action"}

def sanitize_to_linear(config: Any) -> Any:
    if not isinstance(config, dict):
        return config
    nodes = config.get("nodes")
    edges = config.get("edges")
    if not isinstance(nodes, list):
        return config

    keep_nodes = [n for n in nodes if isinstance(n, dict) and n.get("type") in SUPPORTED_TYPES]
    valid_ids = {n.get("id") for n in keep_nodes if n.get("id")}
    keep_edges = [
        e for e in (edges if isinstance(edges, list) else [])
        if isinstance(e, dict) and e.get("from") in valid_ids and e.get("to") in valid_ids
    ]
    return {**config, "nodes": keep_nodes, "edges": keep_edges}

def shape_bot(r: dict) -> dict:
    d = dict(r)
    if d.get("created_at"):
        d["created_at"] = d["created_at"].isoformat()
    if d.get("updated_at"):
        d["updated_at"] = d["updated_at"].isoformat()
    return d

class ChatbotCreate(BaseModel):
    name: str
    description: Optional[str] = None
    status: Optional[str] = "draft"
    trigger_type: Optional[str] = "keyword"
    config: Optional[Dict[str, Any]] = None

class ChatbotUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    trigger_type: Optional[str] = None
    config: Optional[Dict[str, Any]] = None

@router.get("")
async def list_chatbots(user: dict = Depends(get_current_user)):
    rows = await db.fetch(
        """
        SELECT id, name, description, status, trigger_type, config, created_at, updated_at
        FROM coexistence.chatbots
        ORDER BY updated_at DESC
        """
    )
    return [shape_bot(dict(r)) for r in rows]

@router.get("/{bot_id}")
async def get_chatbot(bot_id: int, user: dict = Depends(get_current_user)):
    row = await db.fetchrow(
        """
        SELECT id, name, description, status, trigger_type, config, created_at, updated_at
        FROM coexistence.chatbots WHERE id = $1
        """,
        bot_id
    )
    if not row:
        raise HTTPException(status_code=404, detail="Chatbot not found")
    return shape_bot(dict(row))

@router.post("", status_code=201)
async def create_chatbot(payload: ChatbotCreate, user: dict = Depends(require_permission("chatbot-builder"))):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")

    sanitized = sanitize_to_linear(payload.config) if payload.config else {}
    row = await db.fetchrow(
        """
        INSERT INTO coexistence.chatbots (name, description, status, trigger_type, config)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING *
        """,
        name, payload.description, payload.status or "draft", payload.trigger_type or "keyword", json.dumps(sanitized)
    )
    return shape_bot(dict(row))

@router.put("/{bot_id}")
async def update_chatbot(bot_id: int, payload: ChatbotUpdate, user: dict = Depends(require_permission("chatbot-builder"))):
    if payload.name is not None and not payload.name.strip():
        raise HTTPException(status_code=400, detail="Name is required")

    sanitized = json.dumps(sanitize_to_linear(payload.config)) if payload.config is not None else None
    row = await db.fetchrow(
        """
        UPDATE coexistence.chatbots SET
          name = COALESCE($1, name),
          description = $2,
          status = COALESCE($3, status),
          trigger_type = COALESCE($4, trigger_type),
          config = COALESCE($5, config),
          updated_at = NOW()
        WHERE id = $6
        RETURNING *
        """,
        payload.name.strip() if payload.name else None,
        payload.description,
        payload.status,
        payload.trigger_type,
        sanitized,
        bot_id
    )
    if not row:
        raise HTTPException(status_code=404, detail="Chatbot not found")
    return shape_bot(dict(row))

@router.delete("/{bot_id}")
async def delete_chatbot(bot_id: int, user: dict = Depends(require_permission("chatbot-builder"))):
    res = await db.execute("DELETE FROM coexistence.chatbots WHERE id = $1", bot_id)
    if res.endswith(" 0"):
        raise HTTPException(status_code=404, detail="Chatbot not found")
    return {"ok": True}
