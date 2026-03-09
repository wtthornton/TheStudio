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

# Start the server
uvicorn src.app:app --reload

# Run with Docker
docker-compose up
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
