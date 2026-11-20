# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Run the full stack (Docker — the supported path)
- `docker compose up -d` — starts PostgreSQL, Redis, Node backend, and frontend (nginx). Open `http://localhost:8080` and create your admin account in the browser.
- `docker compose --profile tunnel up -d` — adds a Cloudflare Tunnel container so Meta can reach your local webhook (needed for real WhatsApp messages from Mac/Windows).
- `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d` — production overlay with automatic HTTPS via Caddy; requires `DOMAIN` env and DNS pointing at the server.
- `docker compose down -v` — full teardown; destroys the `secrets`, `pgdata`, `redisdata`, `media`, and `uploads` volumes. **Do not delete the `secrets` volume unless you intend to lose the JWT/encryption key and all encrypted WhatsApp tokens.**

### Run the Python FastAPI backend standalone (`backend-python/`)
This is a FastAPI reimplementation mirroring the Node backend routes. It shares the same PostgreSQL `coexistence` schema and does **not** run migrations itself.

- `cd backend-python && pip install -r requirements.txt`
- `cd backend-python && DATABASE_URL=postgresql://postgres:password@localhost:5432/postgres uvicorn app.main:app --host 0.0.0.0 --port 3011`
- Port defaults to 3011 (`PORT` env). `NODE_ENV=development` relaxes cookie secure flag.
- Required at runtime: `DATABASE_URL` (PostgreSQL), `REDIS_URL`. `DATA_DIR` defaults to `/app/data` where `instance.json` (auto-generated `JWT_SECRET` + `ENCRYPTION_KEY`) is written.
- API docs: `http://localhost:3011/api/docs`, OpenAPI: `/api/openapi.json`
- Health: `GET /api/health` → `{"ok": true}`

### Run tests
- Node backend (`backend/`): `cd backend && npm test` → `node --test test/`. Test files: `access.test.js`, `crypto.test.js`, `permissions.test.js`, `webhookSignature.test.js`. Run a single file: `cd backend && node --test test/access.test.js`.
- Python backend: **no test suite exists.** Do not invent one; if asked to add tests, create them under `backend-python/tests/` using `pytest` (not currently a dependency).

### Lint / format / typecheck
- None configured in either backend. No `ruff`, `eslint`, `prettier`, or `mypy` config found.

### Database migrations
- SQL migrations live in `backend/db/migrations/` (numbered, e.g. `056_agent_accept_images.sql`, `057_mcp.sql`).
- Applied automatically on Node backend boot via `backend/src/db/migrate.js`, tracked in `coexistence.schema_migrations`. Idempotent; a failed migration aborts boot.
- Python backend expects the schema to already exist (applied by the Node service or manually). It does not have its own migration runner.

### First boot / admin setup
- No config files required. On first boot the backend auto-generates `JWT_SECRET` and `ENCRYPTION_KEY` and persists them to `instance.json` in `DATA_DIR`.
- Create the admin account via the browser at `http://localhost:8080` (or your domain).
- Headless seed: set `ADMIN_EMAIL` and `ADMIN_PASSWORD` in a root `.env` (next to `docker-compose.yml`); if both are set and no users exist, the admin is created on boot and the setup wizard is skipped.

## Architecture

### Two backends, one database
- **Node backend** (`backend/`): Express app, entry `backend/src/index.js`. Runs migrations on boot, starts BullMQ workers (media, send, agent), status reconciler, and mounts all API routes under `/api`. Port 3001 locally, 3011 in Docker (proxied by nginx on 8080).
- **Python backend** (`backend-python/`): FastAPI app, entry `backend-python/app/main.py`. Port 3011. Mirrors the Node routes one-for-one (same path prefixes, same auth/permission dependencies). Connects to the same PostgreSQL `coexistence` schema and Redis. Does **not** run migrations.
- Both services share the `coexistence` schema in PostgreSQL and the same Redis instance.

### Python backend layout (FastAPI)
- `app/main.py` — app factory: lifespan (connects asyncpg pool, ensures MCP tables), CORS (origins `localhost:8080`, `localhost:5173`, `127.0.0.1:8080`), mounts all routers, global exception handler.
- `app/core/config.py` — `Settings` (pydantic-settings) + `bootstrap_secrets()`: loads/generates `JWT_SECRET` and `ENCRYPTION_KEY` into `DATA_DIR/instance.json`.
- `app/core/database.py` — `Database` class wrapping asyncpg pool; `fetch`/`fetchrow`/`fetchval`/`execute` helpers; `get_db()` context manager; `db` singleton.
- `app/core/security.py` — bcrypt password hashing; PyJWT HS256 access tokens, 24h expiry (`TOKEN_EXPIRE_HOURS`).
- `app/core/crypto.py` — AES-256-GCM encryption for WhatsApp access tokens and other secrets.
- `app/core/permissions.py` — `PAGES`, `ROLE_PAGE_DEFAULTS`, `has_permission()`.
- `app/core/events.py` — `EventBus` SSE broadcaster used by `/api/events`.
- `app/middleware/auth.py` — `get_current_user` (JWT cookie `synapticchat_token` / legacy `forgecrm_token`, or Bearer header; validates token + `is_active` in DB), `require_admin`, `require_permission(page)`, `is_admin_user()`, `assert_wa_access()`, `assert_contact_access()`, `audit_log()`.
- `app/middleware/tenant.py` — `get_tenant_context()`: resolves active org from `synapticchat_active_org`/`forgecrm_active_org` cookie, `x-org-id`/`x-tenant-id` header, or `org_id` query param; falls back to system default org. `require_org_role(*roles)`.
- `app/routers/*.py` — one router per domain: `health`, `auth`, `organizations`, `users`, `categories`, `contact_fields`, `whatsapp_accounts`, `messages`, `media`, `media_library`, `pipelines`, `templates`, `broadcasts`, `events`, `webhooks`, `ai_models`, `chatbots`, `agents`, `dashboard`, `uploads`, `agent_conversation`, `google_integrations`, `mcp`.
- `app/services/*.py` — business logic: `whatsapp_service`, `message_sender`, `agent_router`, `agent_handoff`, `mcp_service`, `google_auth`, `google_sheets`, `template_components`, `product_catalog`, `account_health`, `auth_service`.
- `app/engine/*.py` — `agent_engine.py`, `automation_engine.py`.
- `app/util/pg_storage.py` — PostgreSQL-backed object storage for the media library.
- `app/integrations/meta_client.py` — Meta WhatsApp Cloud API client.

### Auth & tenancy model
- JWT cookie (`synapticchat_token`, legacy `forgecrm_token`), HttpOnly, 24h expiry. `get_current_user` validates the token and checks `is_active` in `coexistence.forgecrm_users`.
- `require_admin` → `role == 'admin'` (super admin, cross-org). `require_permission(page)` → page-level permission from the user's `permissions` JSONB.
- Every state-changing request resolves an active organization via `get_tenant_context`. Non-admin users are scoped to contacts where `assigned_user_id = user.id`; `assert_wa_access` / `assert_contact_access` enforce this per-WhatsApp-number / per-conversation.
- Organizations are onboarded via `POST /api/organizations/super-admin/onboard` (admin only), which creates the org, an admin user, and an `organization_members` owner row.

### Key domains
- **WhatsApp accounts** — encrypted Meta access/verify tokens, phone number ID, WABA ID, webhook verification (`GET /api/webhook` hub.challenge).
- **Messages & contacts** — 24-hour customer-service window enforcement, contact assignment, message reactions/star, media storage on disk (`MEDIA_DIR`), Range-request media serving.
- **Templates** — WhatsApp message template builder with validation, Meta submission/sync, broadcast count tracking.
- **Broadcasts** — bulk messaging (max 5000 recipients), template or text, per-recipient logs, send queuing via `dispatch_send_task`.
- **Pipelines & Deals** — sales Kanban: pipelines, stages (open/won/lost), deals with metrics, contact search.
- **AI Agents** — system prompt + AI model + tools, trigger mode (keyword/any), session window, media groups, run history.
- **Chatbots** — drag-and-drop automation flows (trigger/message/condition/delay/action nodes).
- **MCP** — Model Context Protocol server (`/api/mcp` admin, `/api/mcp/v1` bearer-key API) for managing agents from Claude; capabilities-gated (discovery, create_agent, update_agent, delete, manage_tools).
- **Dashboard** — KPIs (contacts, leads, open conversations, messages sent, response rate), admin-only automation/broadcast summaries.

### Environment variables (Python backend)
- `DATABASE_URL` — PostgreSQL connection string (default points at `forgecrm-db:5432`, the Docker service name).
- `REDIS_URL` — Redis (default `redis://redis:6379`).
- `PORT` — default `3011`.
- `NODE_ENV` / `ENVIRONMENT` — default `production` (affects cookie `secure` flag and error detail).
- `JWT_SECRET`, `SYNAPTICCHAT_ENCRYPTION_KEY` — auto-generated if unset; persisted to `instance.json`.
- `ADMIN_EMAIL`, `ADMIN_PASSWORD` — headless admin seed.
- `CORS_ORIGIN`, `DOMAIN`, `META_APP_SECRET`, `META_API_VERSION`, `SHOPIFY_STORE_DOMAIN`, `SHOPIFY_ADMIN_API_ACCESS_TOKEN`, `RAZORPAY_KEY_ID/SECRET`, `SHIPROCKET_*`, `GOOGLE_SHEET_WEBHOOK_URL`.

### README highlights
- Deploy requirement: Docker only. The backend auto-generates secrets and applies migrations on first boot.
- Real WhatsApp messages need a public HTTPS webhook URL Meta can reach: `{publicUrl}/api/webhook/whatsapp`. Local installs use the built-in Cloudflare Tunnel (`docker compose --profile tunnel up -d`); server installs use their domain.
- MCP server: enable in Settings → MCP Tools, generate an `sck_live_…` key, connect via the remote URL shown on that page.
- Keep the `secrets` Docker volume — losing it makes encrypted WhatsApp tokens undecryptable.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- When graphify-out/graph.json exists, run `graphify query "<question>"` before your first grep, search or source-file read for a codebase question, and put this rule in every subagent prompt that explores code. Read raw files only for lines the graph or an earlier read already located. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
- A committed graphify-out/graph.json is rewritten whole on every build, so a large diff to it in a pull request is expected. Do not flag it as churn or suggest skipping the graph rebuild or its hooks.
