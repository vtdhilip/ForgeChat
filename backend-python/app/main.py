from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn

from app.core.config import settings
from app.core.database import db
from app.routers import (
    health,
    auth,
    organizations,
    users,
    categories,
    contact_fields,
    whatsapp_accounts,
    messages,
    media,
    media_library,
    pipelines,
    templates,
    broadcasts,
    events,
    webhooks,
    ai_models,
    chatbots,
    agents,
    dashboard,
    uploads,
    agent_conversation,
    google_integrations,
    mcp,
)
from app.services.mcp_service import ensure_mcp_tables

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect to DB pool
    print(f"[Synaptic Chat] Starting Python FastAPI backend on port {settings.PORT}...")
    await db.connect()
    try:
        await ensure_mcp_tables()
    except Exception as e:
        print(f"[MCP] Warning: ensure_mcp_tables failed: {e}")
    yield
    # Shutdown: Close DB pool
    print("[Synaptic Chat] Shutting down Python FastAPI backend...")
    await db.disconnect()

app = FastAPI(
    title="Synaptic Chat API",
    description="Multi-tenant WhatsApp Business Inbox, CRM & AI Agent Engine (FastAPI)",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://localhost:5173", "http://127.0.0.1:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routers
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(organizations.router)
app.include_router(users.router)
app.include_router(categories.router)
app.include_router(contact_fields.router)
app.include_router(whatsapp_accounts.router)
app.include_router(messages.router)
app.include_router(media.router)
app.include_router(media_library.router)
app.include_router(pipelines.router)
app.include_router(templates.router)
app.include_router(broadcasts.router)
app.include_router(events.router)
app.include_router(webhooks.router)
app.include_router(ai_models.router)
app.include_router(chatbots.router)
app.include_router(agents.router)
app.include_router(dashboard.router)
app.include_router(uploads.router)
app.include_router(agent_conversation.router)
app.include_router(google_integrations.router)
app.include_router(mcp.mcp_admin_router)
app.include_router(mcp.mcp_api_router)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"[Unhandled Error] {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": str(exc) if settings.ENVIRONMENT != "production" else "Internal server error"}
    )

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=True)
