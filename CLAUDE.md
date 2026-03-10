# CLAUDE.md — TheStudio

## What

AI-augmented software delivery platform. GitHub issues in, evidence-backed draft PRs out.

**Tech stack:** Python 3.12+, FastAPI, Pydantic, Temporal, NATS JetStream, PostgreSQL + SQLAlchemy (async), Ruff, pytest
**Architecture:** `thestudioarc/00-overview.md`
**Principles:** `thestudioarc/SOUL.md`

## Commands

- Install: `pip install -e ".[dev]"`
- Test: `pytest`
- Lint: `ruff check .`
- Format: `ruff format .`
- Type check: `mypy src/`
- Server: `uvicorn src.app:app --reload`
- Docker: `docker-compose up`

## Pipeline (9 steps)

Intake → Context → Intent → Router → Assembler → Implement → Verify → QA → Publish

Key domain objects: **TaskPacket** (durable work record), **Intent Specification** (definition of correctness)
Trust tiers: Observe → Suggest → Execute (governs Publisher behavior)
Gates fail closed. Loopbacks carry evidence. Every PR gets an evidence comment.

## Persona Chain

Strategy → **Saga** (epic) → **Meridian** (review) → **Helm** (plan) → **Meridian** (review) → Execution

| Context | Persona | Key file |
|---------|---------|----------|
| Creating or editing an **epic** | **Saga** | `thestudioarc/personas/saga-epic-creator.md` |
| **Sprint planning**, goals, backlog | **Helm** | `thestudioarc/personas/helm-planner-dev-manager.md` |
| **Reviewing** an epic or plan | **Meridian** | `thestudioarc/personas/meridian-vp-success.md` |

No epic or plan committed without Meridian review.

## Project Layout

```
src/intake/        Webhook → eligibility → TaskPacket
src/context/       Enrichment, complexity, risk flags
src/intent/        Intent Builder, constraints, refinement
src/routing/       Expert selection, mandatory coverage
src/assembler/     Merge expert outputs, provenance
src/agent/         Primary Agent (Developer role)
src/verification/  Ruff, pytest, security scan → pass/fail signals
src/qa/            QA Agent, defect taxonomy, intent validation
src/publisher/     Draft PR, evidence comment, lifecycle labels
src/reputation/    Weights, decay, drift detection
src/outcome/       Signal ingestor, quarantine, replay
```

## Coding Conventions

- Type annotations on public interfaces; explicit return types
- Structured logging with correlation_id on all spans
- Async only when needed; no mixing sync/async in same module
- Small functions, explicit exceptions, no global mutable state
- See `thestudioarc/20-coding-standards.md` for full standards

## Key References

- Reset / canonical index: `thestudioarc/personas/TEAM.md`
- Training: `thestudioarc/personas/TRAINING.md`
- OKRs and team review: `thestudioarc/personas/MERIDIAN-TEAM-REVIEW-AND-OKRS.md`
- Aggressive roadmap: `thestudioarc/MERIDIAN-ROADMAP-AGGRESSIVE.md`
- Tooling guide: `thestudioarc/personas/tooling-guide.md`
- Agent roles: `thestudioarc/08-agent-roles.md`
- Intent layer: `thestudioarc/11-intent-layer.md`

## Principles (from SOUL.md)

- Intent is the definition of correctness.
- Verification and QA gates fail closed.
- Prefer small diffs and clear evidence.
- Agents communicate through artifacts and signals, not free-form chat.
