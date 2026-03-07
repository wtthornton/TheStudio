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
