# TheStudio — URL Reference

Single source of truth for all base URLs, ports, and key paths. Use this when configuring tools, test rigs, or documentation.

## Base URLs by environment

| Environment | Base URL | Port(s) | Notes |
|-------------|----------|---------|--------|
| **Dev (Docker)** | `http://localhost:8000` | 8000 | `docker compose -f docker-compose.dev.yml up -d` |
| **Dev (local uvicorn)** | `http://localhost:8000` | 8000 | `uvicorn src.app:app --reload --port 8000` from repo root |
| **Production (shared host)** | `https://localhost:9443` | 9080 (HTTP), 9443 (HTTPS) | `infra/docker-compose.prod.yml`; Caddy on 9080/9443 |
| **Production (dedicated 80/443)** | `https://localhost` or your domain | 80, 443 | Edit Caddy ports in prod compose to `80:80`, `443:443` |

No trailing slash on base URLs. Configurable via `THESTUDIO_BASE_URL` (production test rig), `PLAYWRIGHT_BASE_URL` (Playwright), or env in deployment.

---

## Health (unauthenticated)

| Path | Method | Expected | Purpose |
|------|--------|----------|---------|
| `/healthz` | GET | 200, `{"status":"ok"}` | Liveness (Docker, load balancers) |
| `/readyz` | GET | 200, `{"status":"ready"}` | Readiness (DB connectivity) |

**Examples:**
- Dev: `http://localhost:8000/healthz`
- Prod: `https://localhost:9443/healthz` (use `-k` with curl for self-signed cert)

---

## Admin API (authenticated)

Prefix: `/admin`. Use `X-User-ID` header (e.g. `dev-admin@localhost` for mock).

| Path | Method | Purpose |
|------|--------|---------|
| `/admin/health` | GET | Fleet health (Temporal, NATS, DB) |
| `/admin/repos` | GET | List repos |
| `/admin/repos` | POST | Register repo (JSON or form) |
| `/admin/repos/{id}` | GET | Repo detail |
| `/docs` | GET | OpenAPI (Swagger) UI |

**Examples:**
- Dev: `http://localhost:8000/admin/health`, `http://localhost:8000/docs`
- Prod: `https://localhost:9443/admin/health`, `https://localhost:9443/docs`

---

## Admin UI (HTML pages)

Prefix: `/admin/ui`. Same auth as Admin API (mock: `X-User-ID: dev-admin@localhost`).

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
- Prod: **https://localhost:9443/admin/ui/** or **https://localhost:9443/admin/ui/dashboard**

---

## Webhook

| Path | Method | Purpose |
|------|--------|---------|
| `/webhook/github` | POST | GitHub webhook (requires `X-Hub-Signature-256`, etc.) |

**Example:** `POST https://localhost:9443/webhook/github` (prod).

---

## Quick reference

| What | Dev | Production (shared ports) |
|------|-----|----------------------------|
| App base | http://localhost:8000 | https://localhost:9443 |
| Admin UI home | http://localhost:8000/admin/ui/ | https://localhost:9443/admin/ui/ |
| Health | http://localhost:8000/healthz | https://localhost:9443/healthz |
| OpenAPI docs | http://localhost:8000/docs | https://localhost:9443/docs |

See `docs/deployment.md` for full deployment and `docs/production-test-rig-contract.md` for test rig contract.
