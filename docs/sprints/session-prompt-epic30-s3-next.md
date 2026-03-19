# Session Prompt: Epic 30 Sprint 3 — Continue Execution

## Context

Epic 30 Sprint 3 (Feature Flag Activation & Deployment) is in progress. Sprint plan: `docs/sprints/sprint-epic30-s3.md`. Meridian review: 7/7 PASS, plan is COMMITTABLE.

## What's Done

- **Sprint plan** committed and Meridian-reviewed (7/7 PASS)
- **Items 1-6** (bug fixes F7/F8/F9, eval re-run, Story 30.11 deployment runbook, Story 30.9 Projects v2 + Portfolio) completed in prior sessions
- **Item 7 — Story 30.10** (Preflight + Container Isolation): COMPLETE
  - 40 integration tests passing in `tests/integration/test_story_30_10_preflight_container.py`
  - Docker-compose env vars added to all 3 files (dev, standard, prod): `PREFLIGHT_ENABLED`, `PREFLIGHT_TIERS`, `AGENT_ISOLATION`, `AGENT_ISOLATION_FALLBACK`
  - `infra/docker-compose.yml` updated with docker.sock mount + agent-net network (was missing)
  - `docs/deployment.md` Steps 5-6 updated with verification instructions
- **Stories 30.13 + 30.14** created, Meridian-reviewed (7/7 PASS): `docs/sprints/stories-30-13-and-30-14.md`

## What's Next (Priority Order)

### 1. Commit Story 30.10 work (if not already committed)
All changes are tested and lint-clean. Files changed:
- `docker-compose.dev.yml` — preflight + container isolation env vars
- `infra/docker-compose.yml` — preflight + container isolation env vars + docker.sock + agent-net
- `infra/docker-compose.prod.yml` — preflight + container isolation env vars
- `docs/deployment.md` — Steps 5-6 verification instructions
- `tests/integration/test_story_30_10_preflight_container.py` — 40 tests (NEW)
- `docs/sprints/sprint-epic30-s3.md` — sprint plan (NEW)
- `docs/sprints/stories-30-13-and-30-14.md` — future stories (NEW)

### 2. Story 30.14: Add Approval Auto-Bypass Feature Flag (3-4h, M)
This is the higher-value next step because it unblocks Execute-tier pipeline testing for Story 30.12 and beyond. Full spec in `docs/sprints/stories-30-13-and-30-14.md`.

Key tasks:
- Add `approval_auto_bypass: bool = False` to `src/settings.py`
- Add `@model_validator` rejecting bypass + `github_provider=real` + `llm_provider=anthropic`
- Add `approval_auto_bypass: bool = False` to `PipelineInput` in `src/workflow/pipeline.py`
- Add `approval_bypassed: bool = False` to `PipelineOutput`
- Change pipeline.py line 624: `if params.repo_tier in APPROVAL_REQUIRED_TIERS and not params.approval_auto_bypass:`
- Add elif clause logging bypass + setting `output.approval_bypassed = True`
- Wire `settings.approval_auto_bypass` into `src/ingress/workflow_trigger.py` arg dict (line 35-38)
- Add env var to all 3 docker-compose files (dev/staging=true, prod=false)
- Update `docs/FEATURE-FLAGS.md` and `docs/deployment.md`
- Write `tests/integration/test_story_30_14_approval_bypass.py` (>= 8 tests)

### 3. Story 30.13: Fix Model Gateway Audit Tests (1-2h, S)
Fix the pre-existing `test_gateway_enforcement.py` failure. Two bugs:
- Tests don't enable `agent_llm_enabled` feature flag → fallback path runs, 0 audit records
- `_record_audit()` at `src/agent/framework.py:421-431` doesn't populate `overlays` field

Fix: Add `overlays=list(context.overlays)` to `_record_audit()` ModelCallAudit construction. Update tests to enable feature flags and mock LLM calls.

### 4. Story 30.12: Suggest Tier Validation (6h, compressible)
Most complex item. Requires real GitHub operations. Now unblocked by Story 30.14 (approval bypass). Defer if time runs short.

## Pre-existing Failures
- `tests/unit/test_gateway_enforcement.py:46` — Story 30.13 addresses this
- No other known failures

## Sprint Budget
- ~10.5h remaining for Items 7+8, plus 6.5h buffer
- Story 30.10 used ~2h of the 4h estimate (came in under budget)
- Remaining: ~8.5h committed + 6.5h buffer = 15h available

## Key Files
- Sprint plan: `docs/sprints/sprint-epic30-s3.md`
- Stories 30.13/30.14: `docs/sprints/stories-30-13-and-30-14.md`
- Settings: `src/settings.py`
- Pipeline: `src/workflow/pipeline.py` (approval gate at line 624, APPROVAL_REQUIRED_TIERS at line 76)
- Workflow trigger: `src/ingress/workflow_trigger.py` (PipelineInput wiring point)
- AgentRunner: `src/agent/framework.py` (_record_audit at 411-440, feature flag at 232-239)
- Feature flags: `docs/FEATURE-FLAGS.md`
- Deployment: `docs/deployment.md`
