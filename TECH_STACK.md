# Tech Stack

## Project Type
- **Type:** AI-augmented software delivery platform
- **Confidence:** 0.95
- **Reason:** Architecture docs define agent roles, intent layer, verification gates, and publisher flow

## Languages
- Python 3.12+ (primary, per `thestudioarc/20-coding-standards.md`)

## Frameworks
- **FastAPI** — Webhook ingress and API endpoints
- **Temporal** — Durable workflow orchestration (retry, timeout, correlation)
- **Claude Agent SDK** (`claude_agent_sdk`) — Primary Agent implementation (model: `claude-sonnet-4-5`)

## Libraries
- **NATS JetStream** — Event streaming for verification/QA signals
- **OpenTelemetry** — Distributed tracing with correlation_id
- **SQLAlchemy / Alembic** — PostgreSQL ORM and migrations
- **Ruff** — Linting and formatting
- **pytest** — Test runner
- **Bandit** — Security static analysis
- **structlog** — Structured logging

## Domains
- agent-orchestration
- github-integration
- code-quality
- intent-specification
- verification-qa

## Context7 Priority (for doc lookups)
- temporal-python
- nats-py
- fastapi
- opentelemetry-python
- sqlalchemy
- claude-agent-sdk

## Infrastructure
- **CI:** Yes (GitHub Actions — `.github/workflows/tapps-quality.yml`)
- **Docker:** Yes (PostgreSQL, Temporal, NATS JetStream — local dev)
- **Tests:** Yes (pytest)
- **Database:** PostgreSQL (native UUID, JSON columns, strong constraints)
- **Package managers:** pip / uv

## MCP Servers
- **tapps-mcp** — Code quality, scoring, experts (17 built-in + 6 custom domains)
- **docs-mcp** — Documentation generation and validation (14 tools)
- **Context7** — Library documentation lookup
- **Playwright** — Browser automation for acceptance testing
