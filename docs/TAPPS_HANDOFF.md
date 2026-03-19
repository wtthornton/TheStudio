# TAPPS Handoff

> Project-wide quality and delivery status as of 2026-03-18.

## Project Status

**Phases 0–6 complete.** Phase 7 (Real Provider Integration & Cost Optimization) in progress.
30 epics tracked. Epic 27 (Multi-Source Webhooks) deferred — no current demand.
Epics 30-32 actively delivering against Docker production environment.

---

## Delivery Summary

| Epic | Title | Phase | Status |
|------|-------|-------|--------|
| 0 | Foundation | 0 | Complete |
| 1 | Full Flow + Experts | 1 | Complete |
| 2 | Learning + Multi-repo | 2 | Complete |
| 3 | Execute Tier Compliance | 2 | Complete |
| 4 | Admin UI Core | 2 | Complete (9/9 stories) |
| 5 | Observability & Quality | 3 | Complete |
| 6 | Phase 3 Completion | 3 | Complete |
| 7 | Platform Maturity | 4 | Complete (2 sprints) |
| 8 | Production Readiness | 4 | Complete (2 sprints) |
| 9 | Docker Test Rig | 4 | Complete |
| 10 | Docker Test Hardening | 4 | Complete |
| 11 | Production Hardening Phase 1 | 4 | Complete |
| 12 | Playwright Admin UI Tests | 4 | Complete |
| 13 | Agent Persona Infrastructure | 4 | Complete |
| 14 | Agent Content Enrichment | 4 | Complete |
| 15 | E2E Integration & Real Repo Onboarding | 5 | Complete (all 7 stories, 2026-03-17) |
| 16 | Issue Readiness Gate | 5 | Complete (Sprint 17: 16.1-16.4, Sprint 18: 16.5-16.8) |
| 17 | Poll for Issues (Backup) | 5 | Complete (all 8 stories, 2 sprints) |
| 18 | Production E2E Test Suite | 5 | Complete (5 slices, full contract coverage) |
| 19 | Critical Gaps Batch 1 | 5 | Complete (Sprint 19) |
| 20 | Critical Gaps Batch 2 | 5 | Complete (Sprint 19) |
| 21 | Human Approval Wait States | 5 | Complete (9 stories, 2026-03-13) |
| 22 | Execute Tier End-to-End | 5 | Complete (18 stories, auto-merge gating) |
| 23 | Unified Agent Framework | 5 | Complete (3 sprints, 8/8 agents, 215+ tests, 2026-03-16) |
| 24 | Chat Approval Workflows | 5 | Complete (6 stories, 2 sprints, 56+ tests, 2026-03-17) |
| 25 | Container Isolation | 5 | Complete (7 stories, 3 sprints, 35+ tests, 2026-03-17) |
| 26 | File-Based Expert Packaging | 5 | Complete (6 stories, 2026-03-16) |
| 27 | Multi-Source Webhooks | 5 | **Deferred** — no current demand |
| 28 | Preflight Plan Review Gate | 6 | Complete |
| 29 | GitHub Projects v2 + Meridian Portfolio Review | 6 | Complete |
| 30 | Real Provider Integration & Validation | 7 | **Sprint 1 Complete, Sprint 2 Stories 30.7-30.8 Complete** |
| 31 | Anthropic Max OAuth Token Support | 7 | **Stories 31.2-31.5 Complete** (Docker-validated) |
| 32 | Model Routing & Cost Optimization | 7 | **Slice 1 Stories 32.0, 32.4, 32.5 Complete** |

---

## Phase 7 Deliverables (2026-03-18)

### Epic 31: OAuth Adapter (Stories 31.2-31.5)
- OAuth token auto-detection (`sk-ant-oat01-*` → Bearer auth)
- Token refresh on 401 with refresh token rotation
- Feature flag: `THESTUDIO_ANTHROPIC_AUTH_MODE` (auto/api_key/oauth)
- 23 unit tests passing, 3 Docker integration tests passing
- Docker compose files updated with new env vars

### Epic 30 Sprint 2 (Stories 30.7-30.8)
- Full pipeline tested against Docker prod stack (6/6 agents, real Anthropic API)
- Per-issue cost measured: **$0.087** (far under $5 target)
- Failure catalog: 9 failure modes documented (F1-F9)

### Epic 32 Slice 1 (Stories 32.0, 32.4, 32.5)
- Per-agent cost baselines measured against Docker
- Prompt caching implementation (cache_control blocks, beta headers, cache token tracking)
- Cost optimization routing already implemented and tested (11 unit tests)

### Routing Eval Re-run (8 tests, real API, ~$0.35)
- 4/4 cost tests PASS (all agents under budget)
- 4/4 quality tests FAIL (prompt/schema issues — F7, F8, F9 in failure catalog)

---

## Per-Agent Cost Baselines (Story 32.0)

| Agent | Model | Cost | Latency |
|-------|-------|------|---------|
| intake_agent | Haiku | $0.0007 | 1.8s |
| context_agent | Haiku | $0.0047 | 8.9s |
| intent_agent | Sonnet | $0.0309 | 38.5s |
| router_agent | Sonnet | $0.0142 | 16.4s |
| assembler_agent | Sonnet | $0.0309 | 35.3s |
| qa_agent | Sonnet | $0.0053 | 8.7s |
| **Total (6 agents)** | | **$0.087** | |
| Projected/issue (9 agents) | | ~$0.13 | |
| Monthly @ 50 issues/day | | ~$195 | |

---

## Codebase Metrics (2026-03-18)

| Metric | Value |
|--------|-------|
| Source files (src/) | 155+ |
| Test files (tests/) | 115+ |
| Tests passing | 1,767+ |
| Pre-existing failures | 7 (workflow/gateway enforcement) |
| Coverage | 84% |

---

## Known Issues (Failure Catalog)

| ID | Category | Severity | Description |
|----|----------|----------|-------------|
| F1 | auth | Critical | Stale API key in Docker container |
| F4 | auth | High | OAuth without refresh token |
| F8 | validation | High | Assembler qa_handoff schema mismatch |
| F5 | validation | Medium | Intent/assembler hits max_tokens |
| F7 | validation | Medium | Router template vars not injected |
| F9 | validation | Medium | Eval scoring too strict for real LLM |
| F2 | config | Medium | No host port mapping for app |
| F3 | config | Low | pg-proxy not auto-started |
| F6 | cost | Low | Prompt caching not active for short prompts |

See `docs/FAILURE_CATALOG.md` for full details.

---

## Next Actions

1. **Fix F8** — Assembler `qa_handoff.criterion` schema: `str` → `str | list[str]` (10 min)
2. **Fix F7** — Router template variable injection in eval context builder (15 min)
3. **Fix F9** — Calibrate intake/context eval scoring thresholds (30 min)
4. **Re-run routing eval** after fixes to confirm quality gates pass (~$0.35)
5. **Rebuild Docker container** with real API key from `infra/.env` (F1)
6. **Epic 30 Sprint 3** — Feature flag activation, deployment runbook, Suggest tier validation
7. **Epic 32 Slice 2** — Budget controls (trust-tier caps, admin UI)
8. **Epic 32 Slice 3** — Prompt caching with production-length system prompts
