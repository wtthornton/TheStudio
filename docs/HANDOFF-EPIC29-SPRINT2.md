# Handoff Prompt — Epic 29 Sprint 2: Meridian Portfolio Review

> **STATUS: COMPLETE (2026-03-18)** — All 5 stories delivered, 60 tests passing.
>
> Original handoff prompt preserved below for reference.

---

## Context

You are continuing work on **TheStudio**, an AI-augmented software delivery platform. The codebase is a Python 3.12+ / FastAPI / Temporal / Pydantic project.

**Epic 29** (GitHub Projects v2 + Meridian Portfolio Review) has two sprints. **Sprint 1 is complete. Sprint 2 is next.**

### What's Done

**Epic 28 — Preflight Plan Review Gate: COMPLETE**
- Preflight agent config, activity, pipeline integration, observability, evidence comment
- 46 tests in `tests/preflight/`

**Epic 29 Sprint 1 — Projects v2 Core Sync: COMPLETE (63 new tests)**
- Story 29.0: GitHub App permissions — **manual prerequisite**, must verify `project` scope (read:project, write:project) in the GitHub App settings UI before deploying
- Story 29.1: `src/github/projects_client.py` — GraphQL client with caching, `src/github/projects_mapping.py` — status/tier/risk mappings (45 tests)
- Story 29.2: `update_project_status_activity` in `src/workflow/activities.py`, pipeline wiring in `src/workflow/pipeline.py` at 5 status transitions (RECEIVED, ENRICHED, INTENT_BUILT, AWAITING_APPROVAL, PUBLISHED), settings in `src/settings.py` (`projects_v2_enabled`, `projects_v2_owner`, `projects_v2_number`, `meridian_*`) (10 tests)
- Story 29.3: Publisher integration handled by pipeline-level sync
- Story 29.4: Real `_check_projects_v2()` in `src/compliance/checker.py` — queries fields, validates required set, checks items (8 tests)

All feature-flagged off by default. Lint clean. 109 tests across `tests/github/` and `tests/preflight/`.

### What's Next: Sprint 2 — Meridian Portfolio Review

5 stories to implement. The epic file is `docs/epics/epic-29-github-projects-v2-meridian-portfolio-review.md` — read it for full ACs.

| # | Story | Size | Key Files | Notes |
|---|-------|------|-----------|-------|
| 29.5 | **Portfolio Data Collector** | M | `src/meridian/portfolio_collector.py` | Uses `ProjectsV2Client.get_project_items()` to snapshot board state. Returns `PortfolioSnapshot` with items grouped by repo and status. |
| 29.6 | **Meridian Portfolio Review Agent** | M | `src/meridian/portfolio_config.py` | AgentRunner-based agent. System prompt implements 6 health checks (AC 11): blocked ratio >20%, high-risk concurrent >3, review stale >48h, repo concentration >50%, failure rate >30%, queued stale >7d. Output model: `PortfolioReviewOutput` (AC 12). |
| 29.7 | **Scheduled Review Workflow** | M | `src/meridian/portfolio_workflow.py`, Alembic migration | Temporal scheduled workflow `MeridianPortfolioReviewWorkflow`. Default daily at 09:00 UTC. Persists to `portfolio_reviews` table. Feature-flagged via `settings.meridian_portfolio_enabled`. |
| 29.8 | **Admin UI Health Dashboard** | M | `src/admin/ui_router.py`, templates | New page at `/admin/ui/portfolio-health`. Shows latest review: health indicator, flags with severity, recommendations, 7-review trend. Uses existing HTMX pattern. |
| 29.9 | **GitHub Issue Health Report** | S | `src/meridian/portfolio_config.py` | Optional (`settings.meridian_portfolio_github_issue`). Creates/updates pinned issue in configurable repo with markdown health report. |

### Key Architecture Decisions Already Made

1. **Settings exist**: `meridian_portfolio_enabled`, `meridian_portfolio_github_issue`, `meridian_portfolio_repo`, `meridian_thresholds` are already in `src/settings.py`
2. **OTel spans defined**: `SPAN_MERIDIAN_PORTFOLIO_REVIEW` and `SPAN_MERIDIAN_PORTFOLIO_COLLECT` in `src/observability/conventions.py`
3. **GraphQL client ready**: `ProjectsV2Client.get_project_items()` returns items with field values — the collector just needs to call it and shape the data
4. **AgentRunner pattern**: Follow `src/preflight/preflight_config.py` or `src/qa/qa_config.py` for the agent config pattern (AgentConfig + output schema + fallback function)
5. **Feature-flagged, off by default**: Both portfolio review and GitHub issue posting are opt-in
6. **Advisory, not a gate**: Portfolio review produces reports and flags. It does NOT block tasks or modify pipeline behavior
7. **Thresholds are configurable**: Defaults in `settings.meridian_thresholds` dict. Tests should validate the default values

### Key References

| What | Where |
|------|-------|
| Epic (full ACs) | `docs/epics/epic-29-github-projects-v2-meridian-portfolio-review.md` |
| Status tracker | `docs/epics/EPIC-STATUS-TRACKER.md` |
| Agent framework | `src/agent/framework.py` (AgentConfig, AgentRunner, AgentContext) |
| Preflight config (pattern to follow) | `src/preflight/preflight_config.py` |
| QA config (another pattern) | `src/qa/qa_config.py` |
| Projects v2 client | `src/github/projects_client.py` |
| Settings | `src/settings.py` |
| Observability conventions | `src/observability/conventions.py` |
| Existing Admin UI router | `src/admin/ui_router.py` |
| Alembic migrations | `alembic/versions/` |
| Architecture overview | `thestudioarc/00-overview.md` |
| Meridian persona | `thestudioarc/personas/meridian-vp-success.md` |

### Commands

```bash
pip install -e ".[dev]"     # Install
pytest                       # Run all tests
pytest tests/github/ tests/preflight/ -v   # Run Epic 28+29 tests
ruff check .                 # Lint
ruff format .                # Format
```

### Implementation Order

1. **29.5** first — the collector is a pure data-shaping layer over `get_project_items()`
2. **29.6** next — the agent config + output model + fallback. Depends on 29.5 for input data
3. **29.7** next — the Temporal workflow ties 29.5 + 29.6 together + DB persistence
4. **29.8** next — Admin UI page reads from the `portfolio_reviews` table
5. **29.9** last — optional GitHub issue posting, simplest story

### Quality Checklist

- [ ] All new Python files pass `ruff check` and `ruff format`
- [ ] Each story has tests in `tests/meridian/` or `tests/github/`
- [ ] `PortfolioReviewOutput` model matches AC 12 exactly
- [ ] Health check thresholds match `settings.meridian_thresholds` defaults
- [ ] Alembic migration for `portfolio_reviews` table
- [ ] Feature flags default to off
- [ ] No changes to existing pipeline behavior when flags are off
- [ ] Update `EPIC-STATUS-TRACKER.md` when Sprint 2 is complete
