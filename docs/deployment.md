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
open http://localhost:8000/admin/
```

## Docker Compose (Full Stack)

```bash
cd infra && docker compose up -d
```

This starts: FastAPI app (`:8000`), PostgreSQL (`:5434`), Temporal (`:7233`), Temporal UI (`:8088`), NATS (`:4222`).

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
| `THESTUDIO_ANTHROPIC_API_KEY` | `""` | When `LLM_PROVIDER=anthropic` | Anthropic API key |
| `THESTUDIO_AGENT_MODEL` | `claude-sonnet-4-5` | No | Default model for primary agent |
| `THESTUDIO_AGENT_MAX_TURNS` | `30` | No | Max agent conversation turns |
| `THESTUDIO_AGENT_MAX_BUDGET_USD` | `5.0` | No | Max spend per task (USD) |
| `THESTUDIO_AGENT_MAX_LOOPBACKS` | `2` | No | Max QA loopbacks before escalation |

### GitHub Integration

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `THESTUDIO_GITHUB_APP_ID` | `""` | When `GITHUB_PROVIDER=real` | GitHub App ID |
| `THESTUDIO_GITHUB_PRIVATE_KEY_PATH` | `""` | When `GITHUB_PROVIDER=real` | Path to GitHub App private key |

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

## Secret Generation

All secrets go in `infra/.env`. Start from the template:

```bash
cd infra
cp .env.example .env
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

### Start the stack
```bash
docker compose -f docker-compose.prod.yml up -d
```

The startup order is:
1. **postgres** — database (waits for healthcheck)
2. **temporal-migrations** — one-shot schema setup (runs and exits)
3. **temporal** — workflow engine (waits for migrations to complete)
4. **nats** — message bus
5. **app** — TheStudio application
6. **caddy** — TLS reverse proxy (waits for app healthcheck)
7. **backup** — daily backup sidecar

### Verify health
```bash
# Wait for all services
bash wait-for-stack.sh

# Check HTTPS endpoint
curl -k https://localhost/healthz
# Expected: {"status":"ok"}

# Check service status
docker compose -f docker-compose.prod.yml ps
```

## TLS Configuration

### Self-signed (default)

Works out of the box. The Caddyfile uses `tls internal` which generates a self-signed certificate. Clients will see a certificate warning — add an exception or use `curl -k`.

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
# Re-run migrations
docker compose -f docker-compose.prod.yml run --rm temporal-migrations
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
