# TheStudio

![Python](https://img.shields.io/badge/python-%3E%3D3.12-blue) ![Version](https://img.shields.io/badge/version-0.1.0-blue)

AI-augmented software delivery platform that turns GitHub issues into ready-for-review pull requests using expert agents, verification gates, and intent-driven quality.

## Overview

TheStudio receives GitHub issue events via webhook, enriches them with context (scope, risk, complexity), builds an Intent Specification, routes to domain experts, implements changes via a Primary Agent, runs deterministic verification and QA gates, and publishes draft PRs with full evidence.

**Key capabilities:**
- 9-step pipeline: Intake → Context → Intent → Router → Assembler → Implement → Verify → QA → Publish
- Trust-tiered repo lifecycle: Observe → Suggest → Execute
- Reputation-weighted expert routing with decay and drift detection
- Admin UI with fleet dashboard, workflow console, compliance scorecard
- Model gateway with routing rules, fallback chains, and budget enforcement

## Architecture

Architecture docs live in [`thestudioarc/`](thestudioarc/). Key references:

| Doc | Description |
|-----|-------------|
| [00-overview](thestudioarc/00-overview.md) | Full system architecture |
| [08-agent-roles](thestudioarc/08-agent-roles.md) | Agent role definitions |
| [11-intent-layer](thestudioarc/11-intent-layer.md) | Intent specification |
| [15-system-runtime-flow](thestudioarc/15-system-runtime-flow.md) | Runtime pipeline |
| [23-admin-control-ui](thestudioarc/23-admin-control-ui.md) | Admin console |
| [SOUL.md](thestudioarc/SOUL.md) | Core principles |

## Frontend Style Standard

Frontend UI/UX standards are defined in one canonical document:

- `docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md`

This is the single source of truth for style and interaction patterns across:

- `/admin/ui/*` (HTMX Admin Console)
- `/dashboard/*` (React Pipeline app)

If any other doc conflicts with it, the style guide takes precedence.

## Tech Stack

- **Runtime:** Python 3.12+, FastAPI, Pydantic
- **Workflow:** Temporal (activity-based pipeline)
- **Messaging:** NATS JetStream (verification/QA signals)
- **Database:** PostgreSQL + SQLAlchemy (async)
- **LLM:** Anthropic Claude via adapter layer
- **Observability:** OpenTelemetry (traces, metrics)
- **Linting:** Ruff (lint + format)
- **Testing:** pytest

## Getting Started

```bash
# Clone and install
git clone <repository-url>
cd thestudio
pip install -e '.[dev]'

# Run tests
pytest

# Start the server (local dev)
uvicorn src.app:app --reload
```

**WSL / Bash on Windows:** Do not `source` the Windows `.venv\Scripts\activate` with a `c:/...` path — use `/mnt/c/...` paths and a Linux venv instead. See [docs/WSL.md](docs/WSL.md).

### Docker Deployment

```bash
cd infra
cp .env.example .env
# Edit .env — set THESTUDIO_ENCRYPTION_KEY (required), POSTGRES_PASSWORD, etc.

# Vendor ralph-sdk (required before first build)
cp -r /path/to/ralph-claude-code/sdk/* vendor/ralph-sdk/

# Development (mock providers)
docker compose up -d

# Production (real providers, Caddy TLS, resource limits)
docker compose -f docker-compose.prod.yml up -d
```

**Services:** app, postgres, temporal, nats, caddy (TLS reverse proxy), backup sidecar

**Agent modes** (controls how the Primary Agent writes code):
| Mode | Set via | Description |
|------|---------|-------------|
| `legacy` | `THESTUDIO_AGENT_MODE=legacy` | Claude Agent SDK → Anthropic API (direct HTTP, no CLI needed) |
| `ralph` | `THESTUDIO_AGENT_MODE=ralph` | Ralph SDK → `claude` CLI subprocess (in app process) |
| `container` | `THESTUDIO_AGENT_MODE=container` | Ralph SDK → `claude` CLI in **isolated Docker container** (production default) |

Container mode runs agents on the `agent-net` network with no access to Postgres, Temporal, or NATS. See [docs/architecture/agent-container-isolation.md](docs/architecture/agent-container-isolation.md).

**Health checks:**
| Endpoint | Purpose |
|----------|---------|
| `/healthz` | Liveness (Docker healthcheck, load balancers) |
| `/readyz` | Readiness (DB connectivity) |
| `/health/ralph` | Agent mode status — reports `agent_mode`, SDK/CLI availability |

**URLs:** Dev at `http://localhost:8000`. Production at `https://localhost:9443` (Caddy, self-signed TLS). See [docs/URLs.md](docs/URLs.md) for the full reference.

**Database backup:**
```bash
cd infra && ./backup-db.sh  # saves to infra/backups/, rotates last 30
```

## Project Structure

```
src/
├── adapters/        # GitHub, LLM provider adapters
├── admin/           # Admin UI API, RBAC, audit, metrics
├── agent/           # Primary Agent, developer role
├── assembler/       # Expert output merger
├── compliance/      # Tier compliance checker, promotion
├── context/         # Context Manager, complexity, risk
├── db/              # SQLAlchemy models, migrations
├── evals/           # Eval framework and suites
├── experts/         # Expert library, CRUD
├── ingress/         # Webhook handler, deduplication
├── intake/          # Intake Agent, eligibility
├── intent/          # Intent Builder, refinement
├── models/          # TaskPacket model
├── observability/   # Tracing, correlation, middleware
├── outcome/         # Outcome Ingestor, quarantine, replay
├── publisher/       # PR creation, evidence comments
├── qa/              # QA Agent, defect taxonomy
├── recruiting/      # Expert Recruiter, templates
├── repo/            # Repo profile, tier promotion
├── reputation/      # Reputation Engine, decay, drift
├── routing/         # Expert Router
├── verification/    # Verification Gate, runners
└── workflow/        # Temporal pipeline, activities
```

## API Reference

See [docs/API_REFERENCE.md](docs/API_REFERENCE.md) for the full API surface.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, coding standards, and PR workflow.

## Security

See [SECURITY.md](SECURITY.md) for security policies and reporting.

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.
