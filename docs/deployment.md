# TheStudio — Deployment & Configuration

## Quick Start

```bash
# 1. Clone and install
git clone <repo-url> && cd TheStudio
pip install -e ".[dev]"

# 2. Start backend services (PostgreSQL, Temporal, NATS)
cd infra && docker compose up -d postgres && cd ..

# 3. Run tests
pytest tests/ -m "not integration"

# 4. Start the app
uvicorn src.app:app --reload --port 8000

# 5. Access Admin UI
open http://localhost:8000/admin/ui/
```

## Docker Compose (Full Stack)

```bash
cd infra && docker compose up -d
```

This starts: FastAPI app (`:8000`), PostgreSQL (`:5434`), Temporal (`:7233`), Temporal UI (`:8088`), NATS (`:4222`).

For **local dev** from the repo root, use `docker compose -f docker-compose.dev.yml up -d`. The app is exposed on port 8000. Health check: `curl http://localhost:8000/healthz`.

## Environment Variables

All env vars are prefixed with `THESTUDIO_` (via Pydantic Settings).

### Database

| Variable | Default | Description |
|----------|---------|-------------|
| `THESTUDIO_DATABASE_URL` | `postgresql+asyncpg://thestudio:thestudio_dev@localhost:5434/thestudio` | Async PostgreSQL connection string |

### Feature Flags

| Variable | Default | Options | Description |
|----------|---------|---------|-------------|
| `THESTUDIO_LLM_PROVIDER` | `mock` | `mock`, `anthropic` | LLM provider backend |
| `THESTUDIO_GITHUB_PROVIDER` | `mock` | `mock`, `real` | GitHub API client mode |
| `THESTUDIO_STORE_BACKEND` | `memory` | `memory`, `postgres` | Persistence backend for stores |

All flags default to safe/mock mode. Existing tests are unaffected regardless of flag values.

### LLM Provider (Anthropic)

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `THESTUDIO_ANTHROPIC_API_KEY` | `""` | When `LLM_PROVIDER=anthropic` | Anthropic API key (`sk-ant-api03-...`) |
| `THESTUDIO_ANTHROPIC_AUTH_MODE` | `auto` | No | Auth mode: `auto` (detect by prefix), `api_key`, or `oauth` |
| `THESTUDIO_ANTHROPIC_REFRESH_TOKEN` | `""` | No | OAuth refresh token (`sk-ant-ort01-...`) for dev use only |
| `THESTUDIO_ANTHROPIC_OAUTH_CLIENT_ID` | `9d1c250a-...` | No | Anthropic OAuth client ID |
| `THESTUDIO_AGENT_MODEL` | `claude-sonnet-4-5` | No | Default model for primary agent |
| `THESTUDIO_AGENT_MAX_TURNS` | `30` | No | Max agent conversation turns |
| `THESTUDIO_AGENT_MAX_BUDGET_USD` | `5.0` | No | Max spend per task (USD) |
| `THESTUDIO_AGENT_MAX_LOOPBACKS` | `2` | No | Max QA loopbacks before escalation |

**Auth mode detection:** When `auth_mode=auto`, the adapter detects the key prefix:
- `sk-ant-api03-*` → standard `x-api-key` header
- `sk-ant-oat01-*` → OAuth `Authorization: Bearer` header + `anthropic-beta: oauth-2025-04-20`

**OAuth tokens (development only):** Anthropic restricts OAuth to first-party tools (Claude Code, Claude Desktop). Do not use OAuth tokens for production standalone servers. See the Authentication Modes section below for full details.

### Authentication Modes (Epic 31)

TheStudio supports two authentication modes for the Anthropic API:

#### API Key Mode (Production)

Standard Anthropic API keys (`sk-ant-api03-...`) are sent via the `x-api-key` header. This is the default, supported, and recommended mode for all environments.

```bash
THESTUDIO_ANTHROPIC_API_KEY=sk-ant-api03-...
THESTUDIO_ANTHROPIC_AUTH_MODE=auto   # or explicitly: api_key
```

#### OAuth Bearer Mode (Development Only)

Claude Max subscription OAuth tokens (`sk-ant-oat01-...`) are sent via `Authorization: Bearer` with the `anthropic-beta: oauth-2025-04-20` header. Usage is billed against subscription quota, not per-token.

```bash
THESTUDIO_ANTHROPIC_API_KEY=sk-ant-oat01-...
THESTUDIO_ANTHROPIC_AUTH_MODE=auto   # auto-detects from prefix; or explicitly: oauth
```

**Token refresh:** OAuth tokens expire after 8 hours. The adapter automatically refreshes on 401 using the refresh token. Configure:

```bash
THESTUDIO_ANTHROPIC_REFRESH_TOKEN=sk-ant-ort01-...   # Refresh token
THESTUDIO_ANTHROPIC_OAUTH_CLIENT_ID=9d1c250a-...     # Default provided; override if needed
```

Refresh rotates the access token (and optionally the refresh token). If refresh fails, the adapter raises an error — there is no silent fallback.

**How to obtain tokens:** Run `claude setup-token` or extract tokens during `claude login`.

#### TOS Limitations and Production Recommendation

Anthropic restricts OAuth token usage to first-party tools (Claude Code, Claude Desktop). Third-party applications using OAuth have received legal requests to remove support. Specifically:

- **First-party use** (Claude Code, Claude Desktop): Supported — OAuth is the default auth.
- **Third-party use** (standalone servers, custom apps): Not sanctioned. Anthropic has sent legal requests to third-party tools (OpenClaw, OpenCode) removing OAuth support.
- **1M context window** is unavailable with OAuth tokens (200k max).

**Recommendation:** Use API keys for production. Use OAuth only for local development and testing where cost savings from the Max subscription are beneficial. Monitor Anthropic's official API docs for any sanctioned third-party OAuth path.

#### Cost Comparison

| Method | Per-Issue Cost (6 agents) | Monthly (10 issues/day) | Monthly (50 issues/day) | Notes |
|--------|--------------------------|------------------------|------------------------|-------|
| **API Keys (Haiku + Sonnet)** | ~$0.087 | ~$39 | ~$195 | Recommended for production |
| **API Keys (Sonnet only)** | ~$0.12 | ~$54 | ~$270 | No model routing |
| **Max Subscription (OAuth)** | $0 marginal | $200 flat | $200 flat | Dev only; TOS risk for standalone servers |
| **API Keys + Cost Optimization** | ~$0.044 | ~$20 | ~$98 | Routing + caching + batch (Epic 32) |

Cost optimization (Epic 32) reduces API key costs by ~50% through model routing (cheap agents → Haiku), prompt caching, and batch API for async agents. This is the recommended cost reduction strategy for production.

### Per-Agent LLM Toggles (Epic 23)

Each agent can be individually switched from rule-based fallback to real LLM. All default to `false`.

```bash
THESTUDIO_AGENT_LLM_ENABLED='{"primary_agent": true, "developer": true, "intake_agent": true, "context_agent": true, "intent_agent": true, "router_agent": true, "recruiter_agent": true, "assembler_agent": true, "qa_agent": true, "preflight_agent": true}'
```

> **Note:** `developer` is the runtime agent_name for the Primary Agent (distinct from the settings key `primary_agent`). Both should be `true` for the Primary Agent to use LLM.

**Measured per-agent costs (Epic 30 Sprint 2 baselines, single issue):**

| Agent | Model Class | Model | Cost/Issue |
|-------|-------------|-------|------------|
| intake_agent | FAST | Haiku 4.5 | $0.0007 |
| context_agent | FAST | Haiku 4.5 | $0.0047 |
| intent_agent | BALANCED | Sonnet 4.6 | $0.031 |
| router_agent | BALANCED | Sonnet 4.6 | $0.014 |
| assembler_agent | BALANCED | Sonnet 4.6 | $0.031 |
| qa_agent | BALANCED | Sonnet 4.6 | $0.005 |
| **Total (6 agents)** | | | **$0.087** |

Projected monthly costs: ~$39 at 10 issues/day, ~$195 at 50 issues/day.

### Poll Intake (Epic 17 — Backup when webhooks unavailable)

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `THESTUDIO_INTAKE_POLL_ENABLED` | `false` | No | Enable issue polling (backup when no public URL) |
| `THESTUDIO_INTAKE_POLL_INTERVAL_MINUTES` | `10` | No | Global poll interval in minutes (5–60) |
| `THESTUDIO_INTAKE_POLL_TOKEN` | `""` | When poll enabled | GitHub PAT or installation token for API calls |

**When to use polling:** No public URL (local dev, air-gapped, NAT-only) or webhooks misconfigured. Prefer webhooks when a public URL exists.

**Per-repo override:** Each repo can override the global poll interval via Admin UI or `PATCH /admin/repos/{id}/profile` with `poll_enabled` and `poll_interval_minutes`. When `poll_interval_minutes` is null on a repo, the global `THESTUDIO_INTAKE_POLL_INTERVAL_MINUTES` is used.

**Rate limit handling:** The poller honors GitHub's `retry-after` header and uses exponential backoff (capped at 15 minutes) on consecutive rate limits. When `x-ratelimit-remaining` drops below 50, remaining repos are skipped until the next cycle.

See [docs/ingress.md](ingress.md) for architecture details on webhook vs poll paths.

### GitHub Integration

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `THESTUDIO_GITHUB_APP_ID` | `""` | When `GITHUB_PROVIDER=real` | GitHub App ID |
| `THESTUDIO_GITHUB_PRIVATE_KEY_PATH` | `""` | When `GITHUB_PROVIDER=real` | Path to GitHub App private key PEM |
| `THESTUDIO_WEBHOOK_SECRET` | `""` | When `GITHUB_PROVIDER=real` | GitHub webhook HMAC secret |

#### GitHub App Setup

1. Go to **Settings > Developer settings > GitHub Apps > New GitHub App**
2. Configure:
   - **Name:** `TheStudio-<your-org>` (must be globally unique)
   - **Homepage URL:** Your deployment URL
   - **Webhook URL:** `https://<your-domain>/webhook/github`
   - **Webhook secret:** Generate and save to `THESTUDIO_WEBHOOK_SECRET`

3. **Repository permissions:**
   | Permission | Access | Purpose |
   |-----------|--------|---------|
   | Contents | Read & Write | Create branches, read files |
   | Issues | Read & Write | Read issues, post comments |
   | Pull requests | Read & Write | Create PRs, post evidence comments |
   | Metadata | Read | Repository info |
   | Projects | Read & Write | Projects v2 board sync |

4. **Subscribe to events:** `issues`, `issue_comment`, `pull_request`, `pull_request_review`

5. After creating the app:
   - Note the **App ID** → `THESTUDIO_GITHUB_APP_ID`
   - Generate a **private key** → save as PEM, set path in `THESTUDIO_GITHUB_PRIVATE_KEY_PATH`
   - Install the app on your target repository or organization

### Approval and Chat (Epic 24)

| Variable | Default | Description |
|----------|---------|-------------|
| `THESTUDIO_SLACK_APPROVAL_WEBHOOK_URL` | `""` | Slack incoming webhook URL for approval notifications |

### Preflight Plan Review (Epic 28)

| Variable | Default | Description |
|----------|---------|-------------|
| `THESTUDIO_PREFLIGHT_ENABLED` | `false` | Enable preflight plan quality gate |
| `THESTUDIO_PREFLIGHT_TIERS` | `["execute"]` | Trust tiers that require preflight review |

### GitHub Projects v2 (Epic 29)

| Variable | Default | Description |
|----------|---------|-------------|
| `THESTUDIO_PROJECTS_V2_ENABLED` | `false` | Enable Projects v2 board sync |
| `THESTUDIO_PROJECTS_V2_OWNER` | `""` | GitHub org or user that owns the project |
| `THESTUDIO_PROJECTS_V2_NUMBER` | `0` | Project number (visible in project URL) |
| `THESTUDIO_PROJECTS_V2_TOKEN` | `""` | Token with `project` scope |

### Meridian Portfolio Review (Epic 29)

| Variable | Default | Description |
|----------|---------|-------------|
| `THESTUDIO_MERIDIAN_PORTFOLIO_ENABLED` | `false` | Enable scheduled portfolio health reviews |
| `THESTUDIO_MERIDIAN_PORTFOLIO_GITHUB_ISSUE` | `false` | Post health report to a pinned GitHub issue |
| `THESTUDIO_MERIDIAN_PORTFOLIO_REPO` | `""` | Repo for health report issue (`owner/repo`) |
| `THESTUDIO_MERIDIAN_THRESHOLDS` | `{"blocked_ratio":0.20,...}` | Health check thresholds (blocked ratio, failure rate, etc.) |

### Cost Optimization (Epic 32)

| Variable | Default | Description |
|----------|---------|-------------|
| `THESTUDIO_COST_OPTIMIZATION_ROUTING_ENABLED` | `false` | Route cheap agents to FAST (Haiku) |
| `THESTUDIO_COST_OPTIMIZATION_CACHING_ENABLED` | `false` | Send prompt caching headers |
| `THESTUDIO_COST_OPTIMIZATION_BATCH_ENABLED` | `false` | Use Batch API for async agents |
| `THESTUDIO_COST_OPTIMIZATION_BUDGET_TIERS` | `{"observe": 2.0, "suggest": 5.0, "execute": 8.0}` | Per-issue budget caps by tier |

### Container Isolation (Epic 25)

| Variable | Default | Description |
|----------|---------|-------------|
| `THESTUDIO_AGENT_ISOLATION` | `process` | `process` (in-process) or `container` (Docker) |
| `THESTUDIO_AGENT_ISOLATION_FALLBACK` | `{"observe":"allow","suggest":"allow","execute":"deny"}` | Fallback policy per tier |
| `THESTUDIO_AGENT_CONTAINER_CPU_LIMIT` | `{"observe":1.0,"suggest":2.0,"execute":4.0}` | CPU limits per tier |
| `THESTUDIO_AGENT_CONTAINER_MEMORY_MB` | `{"observe":512,"suggest":1024,"execute":2048}` | Memory limits per tier |
| `THESTUDIO_AGENT_CONTAINER_TIMEOUT_SECONDS` | `{"observe":300,"suggest":600,"execute":1200}` | Timeout per tier |

> **Security invariant:** Execute tier MUST have `"deny"` fallback. The app validates this on startup and refuses to start if Execute tier allows fallback to in-process.

### Infrastructure

| Variable | Default | Description |
|----------|---------|-------------|
| `THESTUDIO_TEMPORAL_HOST` | `localhost:7233` | Temporal gRPC endpoint |
| `THESTUDIO_TEMPORAL_NAMESPACE` | `default` | Temporal namespace |
| `THESTUDIO_TEMPORAL_TASK_QUEUE` | `thestudio-main` | Temporal task queue name |
| `THESTUDIO_NATS_URL` | `nats://localhost:4222` | NATS/JetStream URL |

### Security

| Variable | Default | Description |
|----------|---------|-------------|
| `THESTUDIO_ENCRYPTION_KEY` | `generate-a-real-fernet-key-for-production` | Fernet key for secret encryption |

**Production:** Generate a real key with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.

### Observability

| Variable | Default | Description |
|----------|---------|-------------|
| `THESTUDIO_OTEL_SERVICE_NAME` | `thestudio` | OpenTelemetry service name |
| `THESTUDIO_OTEL_EXPORTER` | `console` | `console` or `otlp` |
| `THESTUDIO_OTEL_OTLP_ENDPOINT` | `http://localhost:4317` | OTLP collector endpoint |

## Feature Flag Activation Order

Activate flags in this order. Verify each step before proceeding to the next.

### Step 1: Core providers (required for any real processing)
```bash
THESTUDIO_LLM_PROVIDER=anthropic
THESTUDIO_GITHUB_PROVIDER=real
THESTUDIO_STORE_BACKEND=postgres
```
**Verify:** `curl -sk https://localhost:9443/readyz` returns `{"status":"ready"}`.

### Step 2: Per-agent LLM (start cheap, add expensive)
```bash
# Phase A: FAST-class agents (Haiku, ~$0.005/issue)
THESTUDIO_AGENT_LLM_ENABLED='{"intake_agent": true, "context_agent": true}'

# Phase B: All agents (Haiku + Sonnet, ~$0.087/issue)
THESTUDIO_AGENT_LLM_ENABLED='{"primary_agent": true, "developer": true, "intake_agent": true, "context_agent": true, "intent_agent": true, "router_agent": true, "recruiter_agent": true, "assembler_agent": true, "qa_agent": true}'
```

### Step 3: Projects v2 sync (read-write to GitHub Projects board)
```bash
THESTUDIO_PROJECTS_V2_ENABLED=true
THESTUDIO_PROJECTS_V2_OWNER=<org-or-user>
THESTUDIO_PROJECTS_V2_NUMBER=<project-number>
# Token is optional if GitHub App has project scope; otherwise set a PAT:
# THESTUDIO_PROJECTS_V2_TOKEN=ghp_xxx
```
**Verify:** Process a test issue. Check the GitHub Projects v2 board — the item should appear with Status=Queued, then update through In Progress → Done as the pipeline runs. Sync is best-effort: failures log warnings but never block the pipeline.

**Verify (Admin UI):** Navigate to `/admin/ui/` → Compliance Scorecard. The `projects_v2` check should show real pass/fail status (not the old stub).

### Step 4: Meridian portfolio review (periodic health reports)
```bash
THESTUDIO_MERIDIAN_PORTFOLIO_ENABLED=true
THESTUDIO_MERIDIAN_PORTFOLIO_GITHUB_ISSUE=true
THESTUDIO_MERIDIAN_PORTFOLIO_REPO=<owner/repo>
```
**Verify:** A Temporal scheduled workflow `MeridianPortfolioReviewWorkflow` runs daily at 09:00 UTC. Check Temporal UI (`http://localhost:8088`) for schedule registration. The review collects Projects v2 board state, evaluates 6 health checks (throughput, risk concentration, approval bottleneck, repo balance, failure rate, stale items), persists results to the `portfolio_reviews` table, and optionally posts a health report issue.

**Verify (Admin UI):** Navigate to `/admin/ui/portfolio-health`. The dashboard should show the latest review: overall health indicator (green/yellow/red), flags with severity, recommendations, and a 7-review trend table.

**Thresholds:** Default health check thresholds are documented in `docs/FEATURE-FLAGS.md`. Override via `THESTUDIO_MERIDIAN_THRESHOLDS` JSON env var if needed.

### Step 5: Preflight plan review gate
```bash
THESTUDIO_PREFLIGHT_ENABLED=true
# Optional: restrict to specific tiers (default: only Execute tier)
# THESTUDIO_PREFLIGHT_TIERS='["execute"]'
```
**Verify:** Process a test issue at Execute trust tier. The pipeline log should show a `preflight_activity` step between Assembler and Implement. Check the Temporal workflow history — a `PREFLIGHT` step should appear with `approved: true/false`. For non-Execute tiers (Observe, Suggest), preflight is skipped by default.

**Verify (settings validation):** Restart the app with `THESTUDIO_PREFLIGHT_ENABLED=true`. The app should start normally. The preflight agent uses `model_class=fast` (Haiku) and costs ~$0.01 per review.

**Verify (tier filtering):** Set `THESTUDIO_PREFLIGHT_TIERS='["execute", "suggest"]'` to also run preflight for Suggest tier issues. Observe tier issues should still skip preflight.

### Step 6: Container isolation (requires Docker socket mount)
```bash
THESTUDIO_AGENT_ISOLATION=container
# Fallback policy per tier (defaults shown — do NOT change execute to "allow"):
# THESTUDIO_AGENT_ISOLATION_FALLBACK='{"observe":"allow","suggest":"allow","execute":"deny"}'
```
**Verify (Docker available):** With Docker running, process a test issue. The pipeline log should show `implement_activity` launching a container (look for `container.launch` structured log events with container ID, CPU/memory limits, and timing).

**Verify (security invariant):** The app **refuses to start** if you set `THESTUDIO_AGENT_ISOLATION=container` with `execute` fallback set to `"allow"`. This is enforced by the `_validate_execute_tier_isolation` model validator in `src/settings.py`. This prevents untrusted Execute-tier code from silently falling back to in-process execution.

**Verify (fallback behavior):** If Docker is unavailable:
- **Observe/Suggest tiers:** Fall back to in-process execution (logged as `isolation.fallback`).
- **Execute tier:** Task fails with `ContainerUnavailableError` (fails closed). This is the correct security behavior — Execute tier must not run without isolation.

**Verify (resource limits):** Container resource limits escalate by tier:
| Tier | CPU | Memory | Timeout |
|------|-----|--------|---------|
| Observe | 1.0 cores | 512 MB | 5 min |
| Suggest | 2.0 cores | 1024 MB | 10 min |
| Execute | 4.0 cores | 2048 MB | 20 min |

### Approval Auto-Bypass (Dev/Test Only)

| Variable | Default | Description |
|----------|---------|-------------|
| `THESTUDIO_APPROVAL_AUTO_BYPASS` | `false` | Skip approval gate for all tiers (dev/test only) |

> **Safety:** A startup validator blocks `approval_auto_bypass=true` when both `github_provider=real` AND `llm_provider=anthropic`. This prevents bypassing approval in full production mode.

### Step 7: Cost optimization (after baselines measured)
```bash
THESTUDIO_COST_OPTIMIZATION_ROUTING_ENABLED=true
THESTUDIO_COST_OPTIMIZATION_CACHING_ENABLED=true
```

After each step, rebuild: `docker compose -f docker-compose.prod.yml up -d --build`

## P0 Test Suite

Run after deployment to validate the full stack:

```bash
# Health check only
./scripts/run-p0-tests.sh --health

# Full P0 (skip eval to save ~$5)
./scripts/run-p0-tests.sh --skip-eval

# Full P0 including eval (25 tests, ~$5, ~70 min)
./scripts/run-p0-tests.sh
```

Results saved to `docs/eval-results/`. Test suites:
- **p0-deployed:** Docker stack health, API endpoint validation
- **eval:** Agent quality validation against real Claude (25 tests)
- **github-integration:** Real GitHub API operations (4 tests)
- **postgres-integration:** Database lifecycle validation (6 tests)

---

## CI Pipeline

GitHub Actions runs on every push to `master` and all PRs:
- Python 3.12, `pip install -e ".[dev]"`
- `pytest tests/ -m "not integration" --cov=src --cov-fail-under=75`
- Fails on test failure or coverage below 75%

See `.github/workflows/ci.yml`.

## Running Integration Tests

Integration tests require a running PostgreSQL:

```bash
cd infra && docker compose up -d postgres
pytest tests/ -m integration
```

---

# Production Deployment

Deploy TheStudio on a single Linux host with Docker Compose. This section covers the hardened production stack (`infra/docker-compose.prod.yml`).

**Shared Docker host:** The stack uses Compose project name `thestudio-prod` and host ports **9080** (HTTP) and **9443** (HTTPS). By default, `THESTUDIO_HTTPS_ENABLED=false` — Caddy serves HTTP only. Admin UI: **http://localhost:9080/admin/ui/** — health: **http://localhost:9080/healthz**. Set `THESTUDIO_HTTPS_ENABLED=true` in `infra/.env` for HTTPS (self-signed TLS). Full URL reference: **docs/URLs.md**.

**Production test rig (multi-repo):** A dedicated repo runs tests against this deployment without starting Docker. See `docs/production-test-rig-contract.md` and the scaffold in `thestudio-production-test-rig/`.

**Sprint milestone narrative:** For a dated, issue-specific account of one real end-to-end production-style run (infra checklist, code touchpoints, and follow-ups), see [docs/sprints/production-deployment-summary.md](sprints/production-deployment-summary.md).

## Prerequisites

- Linux host (Ubuntu 22.04+, Debian 12+, or similar) with a public IP
- Docker Engine 24+ and Docker Compose v2.20+
- At least 2 GB RAM, 10 GB disk
- (Optional) Domain name with DNS pointing to the host — required for Let's Encrypt TLS
- Ports 80 and 443 available on the host firewall

Verify:
```bash
docker --version        # Docker Engine 24+
docker compose version  # Docker Compose v2.20+
```

## Docker Image

The `Dockerfile` uses a **multi-stage build** (builder + runtime) to minimize the production image:

- **Builder stage:** installs `gcc`, `libpq-dev`, compiles native extensions, installs all Python deps.
- **Runtime stage:** copies only `libpq5` (runtime) + `curl` (healthcheck) + installed site-packages. No compiler toolchain.

### Vendored dependencies

`ralph-sdk` is not on PyPI and is vendored locally. Before building:

```bash
cp -r /path/to/ralph-claude-code/sdk/* vendor/ralph-sdk/
```

The Dockerfile rewrites the local dev path in `pyproject.toml` to `vendor/ralph-sdk` at build time via `sed`.

### .dockerignore

A `.dockerignore` file excludes `.git/`, `tests/`, `docs/`, caches, `.env` files, and `infra/` from the build context (~7 MB vs full repo).

## Quick start (first-time production)

To bring the production stack up with **mock** LLM/GitHub (no real API keys):

```bash
cd infra
./setup-prod-env.sh --mock    # Creates .env with generated secrets and mock providers
./check-env.sh                # Validate
docker compose -f docker-compose.prod.yml up -d
./wait-for-stack.sh           # Optional: wait until /healthz is ready
```

Then open **http://localhost:9080/admin/ui/** (enter Basic Auth credentials — default user: `admin`). See **docs/URLs.md** for all URLs. To enable HTTPS (self-signed TLS), add `THESTUDIO_HTTPS_ENABLED=true` to `infra/.env` and recreate Caddy. To use **real** Anthropic and GitHub later, edit `infra/.env` with real keys and set `THESTUDIO_LLM_PROVIDER=anthropic`, `THESTUDIO_GITHUB_PROVIDER=real`, then `docker compose -f docker-compose.prod.yml up -d --force-recreate app`.

## Secret Generation

All secrets go in `infra/.env`. Either use the setup script (recommended for first-time) or the template:

```bash
cd infra
./setup-prod-env.sh [--mock]   # Generates secrets and creates .env; use --mock for mock providers
# OR
cp .env.example .env           # Then fill in values manually
```

Generate each required secret:

```bash
# PostgreSQL password (min 12 characters)
python3 -c "import secrets; print(secrets.token_urlsafe(24))"

# Fernet encryption key
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Webhook secret
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Fill in `infra/.env`:
```ini
POSTGRES_PASSWORD=<generated>
THESTUDIO_ENCRYPTION_KEY=<generated>
THESTUDIO_ANTHROPIC_API_KEY=sk-ant-...
THESTUDIO_WEBHOOK_SECRET=<generated>

# Admin UI Basic Auth (Caddy)
ADMIN_USER=admin
ADMIN_PASSWORD_HASH=<generated — see Admin Authentication below>
```

## First-Time Setup

### Validate secrets
```bash
cd infra
bash check-env.sh
```

Expected output:
```
=== TheStudio Pre-Flight Environment Check ===
Loading: ./infra/.env

OK:   POSTGRES_PASSWORD is set (32 chars)
OK:   THESTUDIO_ENCRYPTION_KEY is set and valid base64
OK:   THESTUDIO_ANTHROPIC_API_KEY is set
OK:   THESTUDIO_WEBHOOK_SECRET is set

--- Checking for known insecure values ---
OK:   No known insecure defaults found in .env

=== Summary ===
All checks passed. Ready to deploy.
```

### Run Temporal schema setup (first time only)
```bash
bash temporal-schema-setup.sh
```

This creates the Temporal database and applies schema migrations. It's idempotent — safe to run again if you're unsure whether it's been done. On subsequent deploys, the `temporal-migrations` init container handles this automatically during `docker compose up`.

### Start the stack
```bash
docker compose -f docker-compose.prod.yml up -d
```

The startup order is:
1. **postgres** — database (waits for healthcheck)
2. **temporal-migrations** — one-shot schema setup (runs and exits)
3. **temporal** — workflow engine (waits for migrations to complete)
4. **nats** — JetStream message bus (waits for healthcheck)
5. **app** — TheStudio application (waits for postgres, temporal, and nats healthy)
6. **caddy** — TLS reverse proxy (waits for app healthcheck)
7. **backup** — daily backup sidecar
8. **pg-proxy** — optional socat proxy for host DB access (localhost:5434 only)

### Verify health
```bash
# Wait for all services
bash wait-for-stack.sh

# Default: HTTP (THESTUDIO_HTTPS_ENABLED=false)
curl http://localhost:9080/healthz
# Expected: {"status":"ok"}

# Check readiness (DB connectivity)
curl http://localhost:9080/readyz
# Expected: {"status":"ready"}

# Check Ralph agent mode status
curl http://localhost:9080/health/ralph
# Expected: {"agent_mode":"legacy","sdk_importable":true,"cli_available":false,"status":"ok",...}

# With HTTPS enabled (THESTUDIO_HTTPS_ENABLED=true): use https://localhost:9443 and curl -k
# Full URL reference: docs/URLs.md

# Check service status
docker compose -f docker-compose.prod.yml ps
```

## TLS / HTTPS (feature flag)

**Default:** `THESTUDIO_HTTPS_ENABLED=false` — Caddy serves HTTP only on port 80 (host 9080). Use `http://localhost:9080`.

**To enable HTTPS:** Set `THESTUDIO_HTTPS_ENABLED=true` in `infra/.env`, then `docker compose -f docker-compose.prod.yml up -d --force-recreate caddy`. Caddy uses `Caddyfile` (self-signed TLS) instead of `Caddyfile.http`. Use `https://localhost:9443` (accept cert warning or `curl -k`).

### Self-signed (when HTTPS enabled)

The Caddyfile uses `tls internal` which generates a self-signed certificate. Clients will see a certificate warning — add an exception or use `curl -k`.

### Let's Encrypt (requires domain)

Edit `infra/Caddyfile`:
```
studio.example.com {
    tls you@example.com
    reverse_proxy app:8000 {
        health_uri /healthz
        health_interval 10s
    }
    log {
        output stdout
        format console
    }
}
```

Ensure ports 80 and 443 are open in your firewall. Caddy handles certificate issuance and renewal automatically.

```bash
docker compose -f docker-compose.prod.yml restart caddy
```

## Admin Authentication

Production uses **HTTP Basic Auth** at the Caddy layer to protect all `/admin/*` routes (API and UI). Caddy forwards the authenticated username as `X-User-ID` to the FastAPI app, which resolves permissions via the RBAC system (`user_roles` table).

In dev mode (`LLM_PROVIDER=mock`), auth is bypassed — the app auto-authenticates as `dev-admin@localhost`.

### Setup

1. **Generate a password hash:**
   ```bash
   docker run --rm caddy:2.9-alpine caddy hash-password --plaintext 'YOUR_SECURE_PASSWORD'
   ```

2. **Add credentials to `infra/.env`**. Docker Compose interpolates `$` as variable references, so **double every `$` in the hash** (`$$2a$$14$$...`):
   ```ini
   ADMIN_USER=admin
   ADMIN_PASSWORD=YourSecurePassword
   # The hash below has every $ doubled for Docker Compose escaping:
   ADMIN_PASSWORD_HASH=$$2a$$14$$abcdef...rest-of-hash...
   ```
   **Tip:** Use this one-liner to generate an already-escaped hash:
   ```bash
   docker run --rm caddy:2.9-alpine caddy hash-password --plaintext 'YOUR_PASSWORD' | sed 's/\$/\$\$/g'
   ```

3. **Seed the admin user in the RBAC table** (first time only):
   ```bash
   docker compose -f docker-compose.prod.yml exec postgres \
       psql -U thestudio -d thestudio -c \
       "INSERT INTO user_roles (id, user_id, role, created_by) VALUES (gen_random_uuid(), 'admin', 'admin', 'seed') ON CONFLICT (user_id) DO NOTHING;"
   ```

4. **Restart Caddy:**
   ```bash
   docker compose -f docker-compose.prod.yml up -d caddy
   ```

### How it works

1. Browser requests `/admin/ui/dashboard`
2. Caddy responds with `401 WWW-Authenticate: Basic` — browser shows login dialog
3. On success, Caddy forwards `X-User-ID: <username>` to the app
4. The app's RBAC system resolves the user's role from `user_roles` table
5. Permissions are enforced per-route (ADMIN, OPERATOR, VIEWER)

### Adding users

```bash
# Add an operator user
docker compose -f docker-compose.prod.yml exec postgres \
    psql -U thestudio -d thestudio -c \
    "INSERT INTO user_roles (id, user_id, role, created_by) VALUES (gen_random_uuid(), 'operator1', 'operator', 'admin') ON CONFLICT (user_id) DO NOTHING;"
```

Then add the user's credentials to the Caddyfile `basic_auth` block, or use environment variables for multiple users.

### Password rotation

```bash
# 1. Generate new hash
docker run --rm caddy:2.9-alpine caddy hash-password --plaintext 'NEW_PASSWORD'
# 2. Update ADMIN_PASSWORD_HASH in infra/.env (double all $ signs)
# 3. Restart Caddy
docker compose -f docker-compose.prod.yml up -d caddy
```

## Post-Deployment Verification

### Run the full restart resilience test
```bash
bash verify-restart.sh
```

Expected output:
```
=== TheStudio Restart Resilience Verification ===
--- Phase 1: Starting stack ---
...
PASS: App healthy before restart
--- Phase 4: Full stack restart (down + up) ---
...
PASS: App healthy after restart
PASS: PostgreSQL data persisted across restart
PASS: NATS is running after restart
PASS: Temporal healthy after restart
=== Summary ===
All verifications passed. Stack survives restart with data intact.
```

### Check logs
```bash
docker compose -f docker-compose.prod.yml logs --tail=50        # all
docker compose -f docker-compose.prod.yml logs temporal          # specific
docker compose -f docker-compose.prod.yml logs backup            # backups
```

## Backups

A sidecar container runs `pg_dump` daily at 02:00 UTC. Backups are compressed and stored in `infra/backups/`. Backups older than 30 days are automatically deleted.

### Manual backup
```bash
bash backup-db.sh
```

### Check backup status
```bash
docker compose -f docker-compose.prod.yml logs backup
ls -la backups/
```

### Restore from backup
```bash
# Stop the app first
docker compose -f docker-compose.prod.yml stop app

# Restore (replace with actual backup filename)
bash restore-db.sh backups/thestudio_20260310_020000.sql.gz

# Restart
docker compose -f docker-compose.prod.yml start app
```

## Secret Rotation

### PostgreSQL password
```bash
# 1. Generate new password
python3 -c "import secrets; print(secrets.token_urlsafe(24))"
# 2. Update POSTGRES_PASSWORD in infra/.env
# 3. Change in PostgreSQL:
docker compose -f docker-compose.prod.yml exec postgres \
    psql -U thestudio -c "ALTER USER thestudio PASSWORD 'NEW_PASSWORD_HERE';"
# 4. Restart dependent services:
docker compose -f docker-compose.prod.yml restart app temporal backup
```

### Encryption key
```bash
# WARNING: Rotating makes previously encrypted data unreadable.
# Decrypt/export data first.
# 1. Generate: python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# 2. Update THESTUDIO_ENCRYPTION_KEY in infra/.env
# 3. docker compose -f docker-compose.prod.yml restart app
```

### Anthropic API key / Webhook secret
```bash
# 1. Update the value in infra/.env
# 2. For webhook secret: also update in GitHub App settings
# 3. docker compose -f docker-compose.prod.yml restart app
```

## Troubleshooting

### App fails to start
```bash
docker compose -f docker-compose.prod.yml logs app --tail=50
# Common: bad DATABASE_URL, missing encryption key — run check-env.sh
```

### Temporal schema errors
```bash
# Re-run migrations (option A: via compose)
docker compose -f docker-compose.prod.yml run --rm temporal-migrations

# Re-run migrations (option B: via helper script)
bash temporal-schema-setup.sh

# Check logs
docker compose -f docker-compose.prod.yml logs temporal --tail=50
```

### HTTPS certificate issues
```bash
docker compose -f docker-compose.prod.yml logs caddy
# Let's Encrypt: ensure ports 80/443 open. Self-signed: use curl -k
```

### Backup sidecar not running
```bash
docker compose -f docker-compose.prod.yml ps backup
docker compose -f docker-compose.prod.yml exec backup crontab -l
```

### Port conflicts
```bash
ss -tlnp | grep -E ':80|:443'
```
