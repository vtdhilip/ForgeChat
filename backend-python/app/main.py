from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn

from app.core.config import settings
from app.core.database import db
from app.routers import health, auth, organizations, users

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect to DB pool
    print(f"[Synaptic Chat] Starting Python FastAPI backend on port {settings.PORT}...")
    await db.connect()
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

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"[Unhandled Error] {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": str(exc) if settings.ENVIRONMENT != "production" else "Internal server error"}
    )

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=True)
