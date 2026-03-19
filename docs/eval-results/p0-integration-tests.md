# P0 Integration Test Results

> **Date:** 2026-03-18 (updated 2026-03-19)
> **Epic:** 33 — P0 Deployment Test Harness
> **Total Duration:** ~69 min (eval) + ~6s (P0 deployed) + ~7s (GitHub) + ~2s (Postgres)
> **Total API Cost:** ~$5 (eval suite only)

---

## Summary

| Suite | Tests | Passed | Failed | Notes |
|-------|-------|--------|--------|-------|
| P0 deployed (Docker/Caddy) | 12 | **12** | 0 | Webhook, admin, persistence through Caddy |
| Eval (real Claude) | 25 | **25** | 0 | Intent, primary, QA, routing — all pass |
| GitHub integration | 4 | **4** | 0 | Full PR lifecycle with real GitHub API |
| Postgres integration | 6 | **6** | 0 | Lifecycle, enrichment, dedup via test DB |
| **Total** | **47** | **47** | **0** | |

---

## P0 Deployed Tests (12/12 PASS)

All tests run against the Docker stack through Caddy reverse proxy (https://localhost:9443).

| Test | Result |
|------|--------|
| test_healthz_through_caddy | PASS |
| test_webhook_rejects_unsigned_payload | PASS |
| test_webhook_rejects_bad_signature | PASS |
| test_webhook_accepts_valid_payload | PASS |
| test_admin_health | PASS |
| test_list_repos | PASS |
| test_register_and_query_repo | PASS |
| test_workflow_created_after_webhook | PASS |
| test_postgres_healthy_via_admin | PASS |
| test_webhook_persists_workflow | PASS |
| test_repos_persist_across_requests | PASS |
| test_audit_log_persists | PASS |

**Architecture:** Caddy (TLS + Basic Auth) → App (FastAPI) → Postgres/Temporal/NATS
**Auth:** Webhook routes: HMAC-SHA256 signature. Admin routes: HTTP Basic Auth via Caddy → X-User-ID header → RBAC.

---

## Eval Suite (25/25 PASS, ~69 min, ~$5)

| Test | Result |
|------|--------|
| Intent: all_cases_parse | PASS |
| Intent: pass_rate_at_least_8_of_10 | PASS |
| Intent: goal_non_empty_all_cases | PASS |
| Intent: constraints_non_empty | PASS |
| Intent: invariants_for_breaking_changes | PASS |
| Intent: acs_are_specific | PASS |
| Intent: total_cost_under_budget | PASS |
| Intent: detailed_results_logged | PASS |
| Primary: all_cases_produce_output | PASS |
| Primary: summaries_are_coherent | PASS |
| Primary: file_changes_suggested | PASS |
| Primary: total_cost_under_budget | PASS |
| Primary: no_timeouts | PASS |
| QA: all_cases_parse | PASS |
| QA: defect_detection_rate | PASS |
| QA: clean_bundles_no_severe_defects | PASS |
| QA: total_cost_under_budget | PASS |
| Routing: intake_classification_accuracy | PASS |
| Routing: intake_cost_under_budget | PASS |
| Routing: context_enrichment_quality | PASS |
| Routing: context_cost_under_budget | PASS |
| Routing: router_expert_selection | PASS |
| Routing: router_cost_under_budget | PASS |
| Routing: assembler_plan_quality | PASS |
| Routing: assembler_cost_under_budget | PASS |

---

## GitHub Integration (4/4 PASS)

| Test | Result |
|------|--------|
| Get default branch | PASS |
| Get branch SHA | PASS |
| Create branch + PR lifecycle | PASS |
| Invalid repo returns classified error | PASS |

**Target repo:** `wtthornton/thestudio-production-test-rig`
**Token:** OAuth token from `gh auth token`

---

## Postgres Integration (6/6 PASS)

| Test | Result |
|------|--------|
| Full lifecycle roundtrip | PASS |
| Enrichment fields survive roundtrip | PASS |
| Intent spec persists | PASS |
| Deduplication across sessions | PASS |
| Correlation ID lookup | PASS |
| Model audit roundtrip | PASS |

**Database:** `thestudio_test` (separate from production to avoid schema destruction)

---

## How to Re-Run

```bash
# All suites via runner script (~$5 for eval, free for others)
./scripts/run-p0-tests.sh

# Skip eval to save cost
./scripts/run-p0-tests.sh --skip-eval

# Health check only
./scripts/run-p0-tests.sh --health

# Individual suites
pytest tests/p0/ -m p0 -v                                        # P0 deployed
pytest tests/eval/ -m requires_api_key -v                         # Eval (~$5)
pytest tests/integration/test_real_github.py -m integration -v    # GitHub
pytest tests/integration/test_postgres_backend.py -m integration -v  # Postgres
```

**Prerequisites:**
- Docker stack running: `cd infra && docker compose -f docker-compose.prod.yml up -d`
- `infra/.env` with credentials (THESTUDIO_ANTHROPIC_API_KEY, POSTGRES_PASSWORD, ADMIN_PASSWORD)
- `gh auth login` for GitHub token
- Admin user bootstrapped in user_roles table (auto-done by runner script conftest)
