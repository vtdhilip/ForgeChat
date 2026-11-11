import json
import re
from typing import Optional, List, Dict, Any, Union
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from pydantic import BaseModel

from app.core.database import db
from app.middleware.auth import get_current_user, require_permission

router = APIRouter(prefix="/api/agents", tags=["AI Agents"])

SUPPORTED_PROVIDERS = {"anthropic", "openai"}

def agent_shape(row: dict) -> Optional[dict]:
    if not row:
        return None
    d = dict(row)
    media_groups = d.get("media_groups")
    if isinstance(media_groups, str):
        try:
            media_groups = json.loads(media_groups)
        except Exception:
            media_groups = []
    return {
        "id": d["id"],
        "name": d["name"],
        "description": d.get("description"),
        "systemPrompt": d.get("system_prompt"),
        "aiModelId": d.get("ai_model_id"),
        "aiProvider": d.get("ai_provider"),
        "aiModelLabel": d.get("ai_label"),
        "llmModel": d.get("llm_model"),
        "status": d.get("status") or "active",
        "waAccountId": d.get("wa_account_id"),
        "isActive": d.get("is_active"),
        "contextWindowMessages": d.get("context_window_messages"),
        "maxToolIterations": d.get("max_tool_iterations"),
        "transcribeAudio": bool(d.get("transcribe_audio")),
        "acceptImages": bool(d.get("accept_images")),
        "triggerMode": d.get("trigger_mode") or "any",
        "triggerKeyword": d.get("trigger_keyword") or "",
        "triggerMatchType": d.get("trigger_match_type") or "contains",
        "triggerCaseSensitive": bool(d.get("trigger_case_sensitive")),
        "triggerSessionMinutes": d.get("trigger_session_minutes") if d.get("trigger_session_minutes") is not None else 30,
        "mediaGroups": media_groups or [],
        "createdAt": d["created_at"].isoformat() if d.get("created_at") else None,
        "updatedAt": d["updated_at"].isoformat() if d.get("updated_at") else None,
    }

def tool_shape(row: dict) -> dict:
    d = dict(row)
    cfg = d.get("config")
    if isinstance(cfg, str):
        try:
            cfg = json.loads(cfg)
        except Exception:
            cfg = {}
    return {
        "id": d["id"],
        "agentId": d["agent_id"],
        "toolType": d["tool_type"],
        "config": cfg or {},
        "isEnabled": d.get("is_enabled"),
        "createdAt": d["created_at"].isoformat() if d.get("created_at") else None,
    }

async def fetch_agent(agent_id: int):
    row = await db.fetchrow(
        """
        SELECT a.*, am.provider AS ai_provider, am.label AS ai_label
        FROM coexistence.agents a
        LEFT JOIN coexistence.ai_models am ON am.id = a.ai_model_id
        WHERE a.id = $1
        """,
        agent_id
    )
    return agent_shape(dict(row) if row else None)

class AgentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    systemPrompt: str
    aiModelId: Optional[int] = None
    llmModel: Optional[str] = None
    status: Optional[str] = "active"
    waAccountId: Optional[int] = None
    isActive: Optional[bool] = False
    contextWindowMessages: Optional[int] = 20
    maxToolIterations: Optional[int] = 6
    triggerMode: Optional[str] = "any"
    triggerKeyword: Optional[str] = None
    triggerMatchType: Optional[str] = "contains"
    triggerCaseSensitive: Optional[bool] = False
    triggerSessionMinutes: Optional[int] = 30
    mediaGroups: Optional[List[Any]] = None
    transcribeAudio: Optional[bool] = False
    acceptImages: Optional[bool] = False

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    systemPrompt: Optional[str] = None
    aiModelId: Optional[int] = None
    llmModel: Optional[str] = None
    status: Optional[str] = None
    waAccountId: Optional[int] = None
    isActive: Optional[bool] = None
    contextWindowMessages: Optional[int] = None
    maxToolIterations: Optional[int] = None
    triggerMode: Optional[str] = None
    triggerKeyword: Optional[str] = None
    triggerMatchType: Optional[str] = None
    triggerCaseSensitive: Optional[bool] = None
    triggerSessionMinutes: Optional[int] = None
    mediaGroups: Optional[List[Any]] = None
    transcribeAudio: Optional[bool] = None
    acceptImages: Optional[bool] = None

class ToolCreate(BaseModel):
    toolType: str
    config: Dict[str, Any]
    isEnabled: Optional[bool] = True

class ToolUpdate(BaseModel):
    config: Optional[Dict[str, Any]] = None
    isEnabled: Optional[bool] = None

@router.get("")
async def list_agents(user: dict = Depends(get_current_user)):
    rows = await db.fetch(
        """
        SELECT a.*,
               am.provider AS ai_provider,
               am.label    AS ai_label,
               (SELECT COUNT(*)::int FROM coexistence.agent_tools t WHERE t.agent_id = a.id) AS tool_count,
               (SELECT MAX(started_at) FROM coexistence.agent_runs r WHERE r.agent_id = a.id) AS last_run_at
        FROM coexistence.agents a
        LEFT JOIN coexistence.ai_models am ON am.id = a.ai_model_id
        ORDER BY a.updated_at DESC
        """
    )
    out = []
    for r in rows:
        d = agent_shape(dict(r))
        d["toolCount"] = r["tool_count"]
        d["lastRunAt"] = r["last_run_at"].isoformat() if r.get("last_run_at") else None
        out.append(d)
    return out

@router.get("/{agent_id}")
async def get_agent(agent_id: int, user: dict = Depends(get_current_user)):
    agent = await fetch_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    tools = await db.fetch("SELECT * FROM coexistence.agent_tools WHERE agent_id = $1 ORDER BY id", agent_id)
    return {**agent, "tools": [tool_shape(dict(t)) for t in tools]}

@router.post("", status_code=201)
async def create_agent(payload: AgentCreate, admin: dict = Depends(require_permission("ai-agent-builder"))):
    name = payload.name.strip()
    if not name or not payload.systemPrompt:
        raise HTTPException(status_code=400, detail="name and systemPrompt are required")

    status = "draft" if payload.status == "draft" else "active"
    ai_model_id = payload.aiModelId
    llm_model = payload.llmModel.strip() if payload.llmModel else None

    if status == "active":
        if not ai_model_id or not llm_model:
            raise HTTPException(status_code=400, detail="An active agent needs a connected AI model and a model selection.")

    is_active = bool(payload.isActive) if status == "active" else False
    trigger_mode = "keyword" if payload.triggerMode == "keyword" else "any"
    trigger_kw = payload.triggerKeyword.strip()[:200] if payload.triggerKeyword else None

    try:
        row = await db.fetchrow(
            """
            INSERT INTO coexistence.agents
              (name, description, system_prompt, ai_model_id, llm_model,
               status, wa_account_id, is_active,
               context_window_messages, max_tool_iterations,
               trigger_mode, trigger_keyword, trigger_match_type,
               trigger_case_sensitive, trigger_session_minutes, media_groups,
               transcribe_audio, accept_images)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18)
            RETURNING id
            """,
            name, payload.description.strip() if payload.description else None,
            payload.systemPrompt, ai_model_id, llm_model,
            status, payload.waAccountId, is_active,
            max(1, min(100, payload.contextWindowMessages or 20)),
            max(1, min(20, payload.maxToolIterations or 6)),
            trigger_mode, trigger_kw, payload.triggerMatchType or "contains",
            bool(payload.triggerCaseSensitive),
            max(1, min(1440, payload.triggerSessionMinutes or 30)),
            json.dumps(payload.mediaGroups or []),
            bool(payload.transcribeAudio),
            bool(payload.acceptImages)
        )
        return await fetch_agent(row["id"])
    except Exception as err:
        if "unique" in str(err).lower() or "23505" in str(err):
            raise HTTPException(status_code=409, detail="Another agent is already active on this WhatsApp account. Disable it first.")
        raise HTTPException(status_code=500, detail="Failed to create agent")

@router.put("/{agent_id}")
async def update_agent(agent_id: int, payload: AgentUpdate, admin: dict = Depends(require_permission("ai-agent-builder"))):
    ex = await db.fetchrow("SELECT * FROM coexistence.agents WHERE id = $1", agent_id)
    if not ex:
        raise HTTPException(status_code=404, detail="Agent not found")

    sets = ["updated_at = NOW()"]
    params = [agent_id]

    if payload.name is not None:
        params.append(payload.name.strip())
        sets.append(f"name = ${len(params)}")
    if payload.description is not None:
        params.append(payload.description.strip() if payload.description else None)
        sets.append(f"description = ${len(params)}")
    if payload.systemPrompt is not None:
        params.append(payload.systemPrompt)
        sets.append(f"system_prompt = ${len(params)}")
    if payload.aiModelId is not None:
        params.append(payload.aiModelId or None)
        sets.append(f"ai_model_id = ${len(params)}")
    if payload.llmModel is not None:
        params.append(payload.llmModel.strip() if payload.llmModel else None)
        sets.append(f"llm_model = ${len(params)}")
    if payload.status is not None:
        params.append(payload.status)
        sets.append(f"status = ${len(params)}")
    if payload.waAccountId is not None:
        params.append(payload.waAccountId or None)
        sets.append(f"wa_account_id = ${len(params)}")
    if payload.isActive is not None:
        params.append(bool(payload.isActive))
        sets.append(f"is_active = ${len(params)}")
    if payload.contextWindowMessages is not None:
        params.append(max(1, min(100, payload.contextWindowMessages)))
        sets.append(f"context_window_messages = ${len(params)}")
    if payload.maxToolIterations is not None:
        params.append(max(1, min(20, payload.maxToolIterations)))
        sets.append(f"max_tool_iterations = ${len(params)}")
    if payload.triggerMode is not None:
        params.append(payload.triggerMode)
        sets.append(f"trigger_mode = ${len(params)}")
    if payload.triggerKeyword is not None:
        params.append(payload.triggerKeyword.strip() if payload.triggerKeyword else None)
        sets.append(f"trigger_keyword = ${len(params)}")
    if payload.triggerMatchType is not None:
        params.append(payload.triggerMatchType)
        sets.append(f"trigger_match_type = ${len(params)}")
    if payload.triggerCaseSensitive is not None:
        params.append(bool(payload.triggerCaseSensitive))
        sets.append(f"trigger_case_sensitive = ${len(params)}")
    if payload.triggerSessionMinutes is not None:
        params.append(max(1, min(1440, payload.triggerSessionMinutes)))
        sets.append(f"trigger_session_minutes = ${len(params)}")
    if payload.mediaGroups is not None:
        params.append(json.dumps(payload.mediaGroups))
        sets.append(f"media_groups = ${len(params)}")
    if payload.transcribeAudio is not None:
        params.append(bool(payload.transcribeAudio))
        sets.append(f"transcribe_audio = ${len(params)}")
    if payload.acceptImages is not None:
        params.append(bool(payload.acceptImages))
        sets.append(f"accept_images = ${len(params)}")

    query = f"UPDATE coexistence.agents SET {', '.join(sets)} WHERE id = $1 RETURNING id"
    try:
        row = await db.fetchrow(query, *params)
        return await fetch_agent(row["id"])
    except Exception as err:
        if "unique" in str(err).lower() or "23505" in str(err):
            raise HTTPException(status_code=409, detail="Another agent is already active on this WhatsApp account. Disable it first.")
        raise HTTPException(status_code=500, detail="Failed to update agent")

@router.delete("/{agent_id}")
async def delete_agent(agent_id: int, admin: dict = Depends(require_permission("ai-agent-builder"))):
    res = await db.execute("DELETE FROM coexistence.agents WHERE id = $1", agent_id)
    if res.endswith(" 0"):
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"ok": True}

# --- Nested Tools ---

@router.post("/{agent_id}/tools", status_code=201)
async def add_tool(agent_id: int, payload: ToolCreate, admin: dict = Depends(require_permission("ai-agent-builder"))):
    row = await db.fetchrow(
        """
        INSERT INTO coexistence.agent_tools (agent_id, tool_type, config, is_enabled)
        VALUES ($1, $2, $3, $4) RETURNING *
        """,
        agent_id, payload.toolType, json.dumps(payload.config), payload.isEnabled is not False
    )
    return tool_shape(dict(row))

@router.put("/{agent_id}/tools/{tool_id}")
async def update_tool(agent_id: int, tool_id: int, payload: ToolUpdate, admin: dict = Depends(require_permission("ai-agent-builder"))):
    sets = []
    params = [agent_id, tool_id]
    if payload.config is not None:
        params.append(json.dumps(payload.config))
        sets.append(f"config = ${len(params)}")
    if payload.isEnabled is not None:
        params.append(bool(payload.isEnabled))
        sets.append(f"is_enabled = ${len(params)}")

    if not sets:
        raise HTTPException(status_code=400, detail="No updatable fields provided")

    query = f"UPDATE coexistence.agent_tools SET {', '.join(sets)} WHERE agent_id = $1 AND id = $2 RETURNING *"
    row = await db.fetchrow(query, *params)
    if not row:
        raise HTTPException(status_code=404, detail="Tool not found")
    return tool_shape(dict(row))

@router.delete("/{agent_id}/tools/{tool_id}")
async def delete_tool(agent_id: int, tool_id: int, admin: dict = Depends(require_permission("ai-agent-builder"))):
    res = await db.execute("DELETE FROM coexistence.agent_tools WHERE agent_id = $1 AND id = $2", agent_id, tool_id)
    if res.endswith(" 0"):
        raise HTTPException(status_code=404, detail="Tool not found")
    return {"ok": True}

# --- Runs ---

@router.get("/{agent_id}/runs")
async def get_agent_runs(agent_id: int, limit: int = Query(50), user: dict = Depends(get_current_user)):
    rows = await db.fetch(
        """
        SELECT id, agent_id, contact_number, inbound_message_id, status,
               total_input_tokens, total_output_tokens, final_reply, error_message,
               started_at, ended_at
        FROM coexistence.agent_runs
        WHERE agent_id = $1
        ORDER BY started_at DESC
        LIMIT $2
        """,
        agent_id, max(1, min(200, limit))
    )
    out = []
    for r in rows:
        d = dict(r)
        if d.get("started_at"):
            d["started_at"] = d["started_at"].isoformat()
        if d.get("ended_at"):
            d["ended_at"] = d["ended_at"].isoformat()
        out.append(d)
    return out
