# TheStudio — URL Reference

Single source of truth for all base URLs, ports, and key paths. Use this when configuring tools, test rigs, or documentation.

## Base URLs by environment

| Environment | Base URL | Port(s) | Notes |
|-------------|----------|---------|--------|
| **Dev (Docker)** | `http://localhost:8000` | 8000 | `docker compose -f docker-compose.dev.yml up -d` |
| **Dev (local uvicorn)** | `http://localhost:8000` | 8000 | `uvicorn src.app:app --reload --port 8000` from repo root |
| **Production (HTTP default)** | `http://localhost:9080` | 9080 | `infra/docker-compose.prod.yml`; `THESTUDIO_HTTPS_ENABLED=false` (default) |
| **Production (HTTPS)** | `https://localhost:9443` | 9080, 9443 | Set `THESTUDIO_HTTPS_ENABLED=true` in `infra/.env` for TLS |
| **Production (dedicated 80/443)** | `http://localhost` or `https://localhost` | 80, 443 | Edit Caddy ports in prod compose to `80:80`, `443:443` |

No trailing slash on base URLs. Configurable via `THESTUDIO_BASE_URL` (production test rig), `PLAYWRIGHT_BASE_URL` (Playwright), or env in deployment.

**Root `/`:** Redirects 302 to `/dashboard/` when the React frontend is built, otherwise to `/admin/ui/`.

**HTTPS feature flag:** `THESTUDIO_HTTPS_ENABLED` (default: `false`). When `false`, Caddy serves HTTP only on port 80 (host 9080) — use `http://localhost:9080`. When `true`, Caddy serves HTTPS on 443 (host 9443) and redirects HTTP→HTTPS — use `https://localhost:9443`.

---

## Health (unauthenticated)

| Path | Method | Expected | Purpose |
|------|--------|----------|---------|
| `/healthz` | GET | 200, `{"status":"ok"}` | Liveness (Docker, load balancers) |
| `/readyz` | GET | 200, `{"status":"ready"}` | Readiness (DB connectivity) |
| `/health/ralph` | GET | 200, `{"status":"ok", ...}` | Ralph agent mode readiness (SDK + CLI) |

The `/health/ralph` endpoint returns `agent_mode`, `sdk_importable`, `cli_available`, and `status` (`ok` / `degraded` / `unavailable`). Returns 503 when `agent_mode=ralph` but required components are missing.

**Examples:**
- Dev: `http://localhost:8000/healthz`
- Prod (HTTP): `http://localhost:9080/healthz`
- Prod (HTTPS): `https://localhost:9443/healthz` (use `-k` with curl for self-signed cert)

---

## Admin API (authenticated)

Prefix: `/admin`. Authentication differs by environment:
- **Dev** (`LLM_PROVIDER=mock`): Auto-authenticated as `dev-admin@localhost` — no credentials needed.
- **Production**: Caddy enforces HTTP Basic Auth on all `/admin/*` routes. The authenticated username is forwarded as `X-User-ID` to the app's RBAC system. Default username: `admin`. Set `ADMIN_USER` and `ADMIN_PASSWORD_HASH` in `infra/.env`.

| Path | Method | Purpose |
|------|--------|---------|
| `/admin/health` | GET | Fleet health (Temporal, NATS, DB) |
| `/admin/repos` | GET | List repos |
| `/admin/repos` | POST | Register repo (JSON or form) |
| `/admin/repos/{id}` | GET | Repo detail |
| `/docs` | GET | OpenAPI (Swagger) UI |

**Examples:**
- Dev: `http://localhost:8000/admin/health`, `http://localhost:8000/docs`
- Prod (HTTP): `http://localhost:9080/admin/health` (browser prompts for Basic Auth)
- Prod (HTTPS): `https://localhost:9443/admin/health`, `https://localhost:9443/docs`

---

## Admin UI (HTML pages)

Prefix: `/admin/ui`. Same auth as Admin API (see above).

| Path | Page |
|------|------|
| `/admin/ui/` or `/admin/ui/dashboard` | Fleet Dashboard |
| `/admin/ui/repos` | Repo Management |
| `/admin/ui/workflows` | Workflow Console |
| `/admin/ui/audit` | Audit Log |
| `/admin/ui/metrics` | Metrics |
| `/admin/ui/experts` | Expert Performance |
| `/admin/ui/tools` | Tool Hub |
| `/admin/ui/models` | Model Gateway |
| `/admin/ui/compliance` | Compliance Scorecard |
| `/admin/ui/quarantine` | Quarantine |
| `/admin/ui/dead-letters` | Dead-Letter |
| `/admin/ui/planes` | Execution Planes |
| `/admin/ui/settings` | Settings |

**Entry points:**
- Dev: **http://localhost:8000/admin/ui/** or **http://localhost:8000/admin/ui/dashboard**
- Prod (HTTP): **http://localhost:9080/admin/ui/** (browser prompts for Basic Auth)
- Prod (HTTPS): **https://localhost:9443/admin/ui/** or **https://localhost:9443/admin/ui/dashboard**

---

## Webhook

| Path | Method | Purpose |
|------|--------|---------|
| `/webhook/github` | POST | GitHub webhook (requires `X-Hub-Signature-256`, etc.) |

**Example:** `POST http://localhost:9080/webhook/github` (prod HTTP) or `POST https://localhost:9443/webhook/github` (prod HTTPS).

---

## Quick reference

| What | Dev | Production (HTTP default) | Production (HTTPS) |
|------|-----|---------------------------|--------------------|
| App base | http://localhost:8000 | http://localhost:9080 | https://localhost:9443 |
| Admin UI home | http://localhost:8000/admin/ui/ | http://localhost:9080/admin/ui/ | https://localhost:9443/admin/ui/ |
| Health | http://localhost:8000/healthz | http://localhost:9080/healthz | https://localhost:9443/healthz |
| OpenAPI docs | http://localhost:8000/docs | http://localhost:9080/docs | https://localhost:9443/docs |

See `docs/deployment.md` for full deployment and `docs/production-test-rig-contract.md` for test rig contract.
