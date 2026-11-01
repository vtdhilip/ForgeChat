import json
import logging
import secrets
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Header, Query, Request, status
from pydantic import BaseModel

from app.core.config import settings
from app.core.database import get_db
from app.core.crypto import hash_api_key
from app.middleware.auth import require_admin
from app.services import mcp_service
from app.routers.agents import (
    AgentCreate,
    AgentUpdate,
    ToolCreate,
    ToolUpdate,
    fetch_agent,
    agent_shape,
    tool_shape,
)

logger = logging.getLogger(__name__)

# Admin router mounted at /api/mcp
mcp_admin_router = APIRouter(prefix="/api/mcp", tags=["MCP Admin"])

# API router mounted at /api/mcp/v1
mcp_api_router = APIRouter(prefix="/api/mcp/v1", tags=["MCP API"])

# ── Admin Router Handlers ──────────────────────────────────────────

@mcp_admin_router.get("/settings")
async def get_settings(admin: dict = Depends(require_admin)):
    try:
        return await mcp_service.load_settings()
    except Exception as e:
        logger.error(f"[mcp] settings get error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load MCP settings")

class SettingsUpdatePayload(BaseModel):
    masterEnabled: Optional[bool] = None
    capabilities: Optional[Dict[str, bool]] = None

@mcp_admin_router.put("/settings")
async def update_settings(payload: SettingsUpdatePayload, admin: dict = Depends(require_admin)):
    try:
        cur = await mcp_service.load_settings()
        master_enabled = payload.masterEnabled if payload.masterEnabled is not None else cur.get("masterEnabled", False)
        caps = dict(cur.get("capabilities", {}))
        if payload.capabilities:
            for k in mcp_service.CAPABILITY_KEYS:
                if k in payload.capabilities:
                    caps[k] = bool(payload.capabilities[k])
        async with get_db() as conn:
            await conn.execute(
                """
                UPDATE coexistence.mcp_settings
                   SET master_enabled = $1, capabilities = $2, updated_at = NOW()
                 WHERE id = 1
                """,
                master_enabled,
                json.dumps(caps),
            )
        return await mcp_service.load_settings()
    except Exception as e:
        logger.error(f"[mcp] settings put error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update MCP settings")

def key_shape(r: dict) -> dict:
    return {
        "id": r["id"],
        "label": r["label"],
        "keyPrefix": r["key_prefix"],
        "keyLast4": r["key_last4"],
        "isEnabled": r["is_enabled"],
        "lastUsedAt": r["last_used_at"].isoformat() if r.get("last_used_at") else None,
        "createdAt": r["created_at"].isoformat() if r.get("created_at") else None,
    }

@mcp_admin_router.get("/keys")
async def list_keys(admin: dict = Depends(require_admin)):
    async with get_db() as conn:
        rows = await conn.fetch("SELECT * FROM coexistence.mcp_api_keys ORDER BY created_at DESC")
        return [key_shape(dict(r)) for r in rows]

class KeyCreatePayload(BaseModel):
    label: str

@mcp_admin_router.post("/keys", status_code=status.HTTP_201_CREATED)
async def create_key(payload: KeyCreatePayload, admin: dict = Depends(require_admin)):
    label = payload.label.strip()
    if not label:
        raise HTTPException(status_code=400, detail="A label is required")

    plain = "fck_live_" + secrets.token_urlsafe(24)
    key_prefix = plain[:13]
    key_last4 = plain[-4:]
    key_h = hash_api_key(plain)

    async with get_db() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO coexistence.mcp_api_keys (label, key_prefix, key_last4, key_hash, created_by)
            VALUES ($1, $2, $3, $4, $5) RETURNING *
            """,
            label,
            key_prefix,
            key_last4,
            key_h,
            int(admin["id"]),
        )
        data = key_shape(dict(row))
        data["key"] = plain
        return data

class KeyUpdatePayload(BaseModel):
    label: Optional[str] = None
    isEnabled: Optional[bool] = None

@mcp_admin_router.put("/keys/{key_id}")
async def update_key(key_id: int, payload: KeyUpdatePayload, admin: dict = Depends(require_admin)):
    sets = []
    params = []
    if payload.label is not None:
        params.append(payload.label.strip())
        sets.append(f"label = ${len(params)}")
    if payload.isEnabled is not None:
        params.append(bool(payload.isEnabled))
        sets.append(f"is_enabled = ${len(params)}")
    if not sets:
        raise HTTPException(status_code=400, detail="No updatable fields provided")

    params.append(key_id)
    query = f"UPDATE coexistence.mcp_api_keys SET {', '.join(sets)} WHERE id = ${len(params)} RETURNING *"
    async with get_db() as conn:
        row = await conn.fetchrow(query, *params)
        if not row:
            raise HTTPException(status_code=404, detail="Not found")
        return key_shape(dict(row))

@mcp_admin_router.delete("/keys/{key_id}")
async def delete_key(key_id: int, admin: dict = Depends(require_admin)):
    async with get_db() as conn:
        res = await conn.execute("DELETE FROM coexistence.mcp_api_keys WHERE id = $1", key_id)
        if "DELETE 0" in res:
            raise HTTPException(status_code=404, detail="Not found")
        return {"ok": True}

@mcp_admin_router.get("/install")
async def get_install_info(request: Request, admin: dict = Depends(require_admin)):
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.headers.get("host", settings.DOMAIN))
    base = f"{proto}://{host}"
    api_url = f"{base}/api/mcp/v1"
    remote_url = f"{base}/api/mcp/http/<YOUR_KEY>"
    server_path = "/root/synaptic-chat/mcp-server/src/index.js"
    return {
        "remoteUrl": remote_url,
        "apiUrl": api_url,
        "serverPath": server_path,
        "configSnippet": {
            "mcpServers": {
                "synapticchat-agents": {
                    "command": "node",
                    "args": [server_path],
                    "env": {
                        "SYNAPTICCHAT_API_URL": api_url,
                        "SYNAPTICCHAT_API_KEY": "sck_live_PASTE_YOUR_KEY",
                    },
                }
            }
        },
    }

# ── API Router Bearer Auth & Gating ─────────────────────────────────

async def get_mcp_context(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    raw_key = authorization.split(" ", 1)[1].strip()
    try:
        ctx = await mcp_service.validate_key(raw_key)
        return ctx
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"[mcp] auth error: {e}")
        raise HTTPException(status_code=500, detail="Authentication failed")

def require_cap(cap_name: str):
    async def dep(mcp: dict = Depends(get_mcp_context)):
        if not mcp.get("capabilities", {}).get(cap_name):
            raise HTTPException(
                status_code=403,
                detail=f"The '{cap_name}' capability is disabled for MCP access.",
            )
        return mcp
    return dep

# ── API Router Discovery Endpoints ──────────────────────────────────

@mcp_api_router.get("/wa-accounts")
async def mcp_list_wa_accounts(mcp: dict = Depends(require_cap("discovery"))):
    return await mcp_service.list_wa_accounts()

@mcp_api_router.get("/models")
async def mcp_list_models(mcp: dict = Depends(require_cap("discovery"))):
    return await mcp_service.list_models()

@mcp_api_router.get("/google-accounts")
async def mcp_list_google_accounts(mcp: dict = Depends(require_cap("discovery"))):
    return await mcp_service.list_google_accounts()

@mcp_api_router.get("/spreadsheets")
async def mcp_search_spreadsheets(
    googleAccountId: int = Query(...),
    q: Optional[str] = Query(""),
    pageSize: int = Query(50),
    mcp: dict = Depends(require_cap("discovery")),
):
    try:
        return await mcp_service.search_spreadsheets(googleAccountId, q=q or "", page_size=pageSize)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@mcp_api_router.get("/spreadsheets/{spreadsheet_id}/tabs")
async def mcp_list_sheet_tabs(
    spreadsheet_id: str,
    googleAccountId: int = Query(...),
    mcp: dict = Depends(require_cap("discovery")),
):
    try:
        return await mcp_service.list_sheet_tabs(googleAccountId, spreadsheet_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@mcp_api_router.get("/spreadsheets/{spreadsheet_id}/values")
async def mcp_read_sheet_values(
    spreadsheet_id: str,
    googleAccountId: int = Query(...),
    tab: str = Query(...),
    range: Optional[str] = Query(None),
    maxRows: int = Query(100),
    mcp: dict = Depends(require_cap("discovery")),
):
    try:
        return await mcp_service.read_sheet_values(googleAccountId, spreadsheet_id, tab, range_a1=range, max_rows=maxRows)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@mcp_api_router.get("/media")
async def mcp_list_media(
    type: Optional[str] = Query(None),
    name: Optional[str] = Query(None),
    mcp: dict = Depends(require_cap("discovery")),
):
    return await mcp_service.list_media(media_type=type, name=name)

@mcp_api_router.get("/templates")
async def mcp_list_templates(
    waAccountId: Optional[int] = Query(None),
    mcp: dict = Depends(require_cap("discovery")),
):
    return await mcp_service.list_templates(wa_account_id=waAccountId)

@mcp_api_router.get("/templates/{template_id}")
async def mcp_get_template(
    template_id: int,
    mcp: dict = Depends(require_cap("discovery")),
):
    tpl = await mcp_service.get_template(template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="Not found")
    return tpl

# ── API Router Agent Endpoints ──────────────────────────────────────

@mcp_api_router.get("/agents")
async def mcp_list_agents(mcp: dict = Depends(require_cap("discovery"))):
    async with get_db() as conn:
        rows = await conn.fetch(
            """
            SELECT a.*, m.provider AS ai_provider, m.label AS ai_label
              FROM coexistence.agents a
              LEFT JOIN coexistence.ai_models m ON m.id = a.ai_model_id
             ORDER BY a.created_at DESC
            """
        )
        return [agent_shape(dict(r)) for r in rows]

@mcp_api_router.get("/agents/{agent_id}")
async def mcp_get_agent(agent_id: int, mcp: dict = Depends(require_cap("discovery"))):
    res = await fetch_agent(agent_id)
    if not res:
        raise HTTPException(status_code=404, detail="Not found")
    return res

@mcp_api_router.post("/agents", status_code=status.HTTP_201_CREATED)
async def mcp_create_agent(payload: AgentCreate, mcp: dict = Depends(require_cap("create_agent"))):
    admin_ctx = {"id": mcp["keyId"], "role": "admin"}
    from app.routers.agents import create_agent
    return await create_agent(payload, admin=admin_ctx)

@mcp_api_router.put("/agents/{agent_id}")
async def mcp_update_agent(agent_id: int, payload: AgentUpdate, mcp: dict = Depends(require_cap("update_agent"))):
    admin_ctx = {"id": mcp["keyId"], "role": "admin"}
    from app.routers.agents import update_agent
    return await update_agent(agent_id, payload, admin=admin_ctx)

@mcp_api_router.delete("/agents/{agent_id}")
async def mcp_delete_agent(agent_id: int, mcp: dict = Depends(require_cap("delete"))):
    admin_ctx = {"id": mcp["keyId"], "role": "admin"}
    from app.routers.agents import delete_agent
    return await delete_agent(agent_id, admin=admin_ctx)

@mcp_api_router.post("/agents/{agent_id}/tools", status_code=status.HTTP_201_CREATED)
async def mcp_add_tool(agent_id: int, payload: ToolCreate, mcp: dict = Depends(require_cap("manage_tools"))):
    admin_ctx = {"id": mcp["keyId"], "role": "admin"}
    from app.routers.agents import add_tool
    return await add_tool(agent_id, payload, admin=admin_ctx)

@mcp_api_router.put("/agents/{agent_id}/tools/{tool_id}")
async def mcp_update_tool(agent_id: int, tool_id: int, payload: ToolUpdate, mcp: dict = Depends(require_cap("manage_tools"))):
    admin_ctx = {"id": mcp["keyId"], "role": "admin"}
    from app.routers.agents import update_tool
    return await update_tool(agent_id, tool_id, payload, admin=admin_ctx)

@mcp_api_router.delete("/agents/{agent_id}/tools/{tool_id}")
async def mcp_delete_tool(agent_id: int, tool_id: int, mcp: dict = Depends(require_cap("delete"))):
    admin_ctx = {"id": mcp["keyId"], "role": "admin"}
    from app.routers.agents import delete_tool
    return await delete_tool(agent_id, tool_id, admin=admin_ctx)
