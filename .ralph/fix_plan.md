# Fix Plan — TheStudio

> Active Sprints: `docs/sprints/sprint-epic37-38-s1-s2-s3.md` (Meridian PASS 2026-03-22)
> Sprint 1: Epic 37 Test Debt (10 stories, week of 2026-03-23)
> Sprint 2: Epic 38 Slice 1 + Slice 2 Backend (7 stories, week of 2026-03-30)
> Sprint 3: Epic 38 Slice 2 Frontend (5 stories, week of 2026-04-06)

---

## Sprint 1 — Epic 37 Test Debt Paydown

> All 28 Epic 37 feature stories are COMPLETE but shipped with zero test coverage.
> This sprint writes tests only — no new features, no production code changes.
> Gate: all tests green before Sprint 2 begins.

- [x] T37.10: Test infrastructure setup — create `tests/dashboard/__init__.py` + `tests/dashboard/conftest.py` with async DB session fixture, mock Temporal client, sample TaskPacketRow factory, mock NATS message fixture. Verify `pytest tests/dashboard/ --co` succeeds.
- [x] T37.1: Pydantic model validation tests — `tests/dashboard/test_models_steering_audit.py`, `test_models_trust_config.py`, `test_models_budget_config.py`, `test_models_notification.py`. Test all enums, required fields, optional fields, `from_attributes` ORM loading, ge constraints, max_length, range validation.
- [x] T37.2: Trust engine tests — `tests/dashboard/test_trust_engine.py`. Test all 6 condition operators (equals, not_equals, less_than, greater_than, contains, matches_glob), `_resolve_field` with dot-notation, `_rule_matches` AND logic, `evaluate_trust_tier` first-match-wins, safety bounds override, default tier fallback, `_cap_tier` logic.
- [x] T37.4: Steering API tests — `tests/dashboard/test_steering.py`. Test all 5 endpoints (pause/resume/abort/redirect/retry) with happy path, 404, 409, 400 status codes. Test `GET /steering/audit` and `GET /tasks/{id}/audit`. Test `_detect_current_stage` helper. Mock Temporal client and DB.
- [x] T37.3: Trust router tests — `tests/dashboard/test_trust_router.py`. Test rules CRUD (create/read/update/delete + 404), safety bounds get/put, default tier get/set, `active_only` filter.
- [x] T37.5: Budget checker tests — `tests/dashboard/test_budget_checker.py`. Test `_check_budget_thresholds` all branches (below cap, above cap with/without pause, approach with/without downgrade, debounce flag). Test `_pause_all_active_workflows` with empty/populated results. Test `_on_message` JSON parsing + ack-always. Test `_downgrade_activated` module-level flag reset.
- [x] T37.6: Budget router tests — `tests/dashboard/test_budget_router.py`. Test all 6 endpoints (summary, history, by-stage, by-model, config get, config put). Test `window_hours` query param validation.
- [x] T37.7: Notification generator tests — `tests/dashboard/test_notification_generator.py`. Test all 4 builder functions (`_notification_for_gate_fail`, `_notification_for_cost_update`, `_notification_for_steering_action`, `_notification_for_trust_tier`). Test `_safe_task_id`, `_on_message` dispatch + ack-always, `_BUILDERS` dict.
- [x] T37.8: Notification router tests — `tests/dashboard/test_notification_router.py`. Test list (with unread_only, type filter, pagination), mark-read (+ 404), mark-all-read.
- [x] T37.9: Temporal signal handler tests — `tests/workflow/test_steering_signals.py`. Test all 5 signal handlers (pause_task, resume_task, abort_task, redirect_task, retry_stage). Test state mutations, audit activity calls, idempotency, invalid redirect targets, retry with no current stage. Use `temporalio.testing.WorkflowEnvironment` pattern from `test_approval_wait.py`.

---

## Sprint 2 — Epic 38 Slice 1 (Issue Import) + Slice 2 Backend

> Epic: `docs/epics/epic-38-phase4-github-integration.md` (Meridian PASS 2026-03-22)
> Recommended sequence: 38.5 → 38.1 → 38.6 → 38.2 → 38.7 → 38.3 → 38.4

- [x] 38.5: `EvidencePayload` Pydantic model — `src/publisher/evidence_payload.py`. Structured JSON schema with sections: task_summary, intent, gate_results, cost_breakdown, provenance, files_changed. Unit tests at `tests/publisher/test_evidence_payload.py`.
- [x] 38.1: `GET /api/v1/dashboard/github/issues` — `src/dashboard/github_router.py` (new). List repo issues from GitHub REST API with label/status/search filters, 5-min TTL cache, paginated. Filter out pull requests. Register router in `src/dashboard/router.py`. Tests with mocked GitHub API.
- [x] 38.6: `format_evidence_json()` — add to `src/publisher/evidence_comment.py`. Generate `EvidencePayload` alongside existing Markdown evidence comment. Extract data from TaskPacket and related records. Handle missing data gracefully. Tests at `tests/publisher/test_evidence_json.py`.
- [x] 38.2: `POST /api/v1/dashboard/github/import` — `src/dashboard/github_router.py`. Batch import selected issues as TaskPackets. Check for duplicates. Set `source_name="dashboard_import"`. Respect triage mode (TRIAGE status if enabled, RECEIVED + start workflow if not). `taskpacket_crud.create()` already accepts `source_name`.
- [x] 38.7: `GET /api/v1/dashboard/tasks/:id/evidence` — return `EvidencePayload` JSON for a TaskPacket. 404 on missing task. Tests at `tests/dashboard/test_evidence_endpoint.py`.
- [ ] 38.3: Import modal frontend — `frontend/src/components/github/ImportModal.tsx`. Repo selector (from admin settings), label/status filters, search, issue list with checkboxes, import mode toggle (triage vs direct), "already in pipeline" detection. Wire into dashboard navigation.
- [ ] 38.4: Integration test — `tests/integration/test_issue_import.py`. Import 2 issues, verify TaskPackets created with `source_name="dashboard_import"`, verify duplicate blocked, test triage mode, test direct mode. Mocked GitHub API.

---

## Sprint 3 — Epic 38 Slice 2 Frontend + Integration Tests

> Recommended sequence: 38.9 → 38.10 → 38.8 → 38.11 → 38.12
> Sprint 3 runs at 63% utilization to absorb Sprint 2 carryover.

- [ ] 38.9: `POST /api/v1/dashboard/tasks/:id/pr/approve` — `src/dashboard/pr_router.py` (new). Approve and merge PR via GitHub REST API. Fetch TaskPacket, extract PR number, call merge endpoint. Handle 404, 409 (no PR), GitHub API errors. Tests with mocked GitHub API.
- [ ] 38.10: `POST /api/v1/dashboard/tasks/:id/pr/request-changes` — `src/dashboard/pr_router.py`. Post PR review comment via GitHub API with event="REQUEST_CHANGES". Optionally trigger loopback signal to Temporal workflow. Tests.
- [ ] 38.8: PR Evidence Explorer frontend — `frontend/src/components/pr/EvidenceExplorer.tsx`. Tabbed viewer (Evidence, Diff, Intent, Gates, Cost) consuming `GET /tasks/:id/evidence` JSON. Loading states, error handling, empty states.
- [ ] 38.11: Reviewer action buttons frontend — `frontend/src/components/pr/ReviewerActions.tsx`. Approve & Merge (with confirmation), Request Changes (with textarea), Close PR, View on GitHub. Success/error feedback.
- [ ] 38.12: Integration test — `tests/integration/test_pr_evidence_explorer.py`. Evidence JSON generated for published TaskPacket. Approve action calls GitHub merge API. Request-changes calls review API. Error cases: task not published, task has no PR.

---

## Upcoming — Sprint-Planned After Current Block

### Epic 38 Slices 3+4 (if MVP succeeds)

> Decision point after Sprint 3: if <20% of tasks use manual import, defer and proceed to Epic 39.

- [ ] 38.13-38.20: Slice 3 — GitHub Projects Sync (8 stories)
- [ ] 38.21-38.27: Slice 4 — Pipeline Comments + Webhook Bridge (7 stories)

### Epic 39 — Phase 5: Analytics & Learning (Meridian PASS 2026-03-22, 24 stories)

> Epic: `docs/epics/epic-39-phase5-analytics-learning.md`
> Depends on: Epic 38 MVP (for PR merge status data)
> Duration: 5-6 weeks (includes Slice 0 data prerequisites)

- [ ] 39.0a-39.0c: Slice 0 — Data Prerequisites (3 stories: completed_at column, pr_merge_status field, outcome signal DB persistence)
- [ ] 39.1-39.11: Slice 1 — Operational Analytics (11 stories: throughput, bottlenecks, categories, failures, summary cards, frontend)
- [ ] 39.12-39.21: Slice 2 — Reputation & Outcomes (10 stories: expert performance, outcomes feed, drift detection, frontend)

### Epic 40 — Remote Verification & Advanced Issue Processing (Meridian PASS 2026-03-22, 15 stories)

> Epic: `docs/epics/epic-40-remote-verification.md`
> Priority: P0 — blocks processing harder issues (multi-file, bug fixes, refactoring)
> Duration: 3-4 weeks

- [ ] 40.0-40.8: Slice 1 MVP — Local subprocess verification (9 stories: repo clone, test runner, lint runner, orchestrator, verify activity integration)
- [ ] 40.9-40.14: Slice 2 — Container mode verification (6 stories: container Dockerfile, container runner, evidence enrichment, observability)

### Epic 41 — Second Repo Onboarding & Multi-Repo Foundation (Meridian PASS 2026-03-22, 14 stories)

> Epic: `docs/epics/epic-41-multi-repo-onboarding.md`
> Priority: P1 — validates multi-repo support
> Duration: 3-4 weeks

- [ ] 41.1-41.7: Slice 1 MVP — Registration, webhook routing, dashboard repo selector, repo filtering (7 stories)
- [ ] 41.8-41.14: Slice 2 — Per-repo config, concurrent pipeline isolation, smoke test, fleet health (7 stories)

### Epic 42 — Execute Tier Promotion: Auto-Merge with Human Gates (Meridian PASS 2026-03-22, 13 stories)

> Epic: `docs/epics/epic-42-execute-tier-promotion.md`
> Priority: P2 — depends on Epic 40 (remote verification should be complete before enabling auto-merge)
> Duration: 3-4 weeks

- [ ] 42.1-42.7: Slice 1 MVP — Publisher branching by task_trust_tier, safety bounds re-check, auto-merge execution, dry-run mode (7 stories)
- [ ] 42.8-42.13: Slice 2 — Post-merge monitoring, auto-demotion on failure, outcome tracking, dashboard API (6 stories)

### Epic 27 — Multi-Source Webhooks (Deferred, Meridian Conditional Pass)

> Epic: `docs/epics/epic-27-webhook-triggers-multi-source-intake.md`
> Priority: P1 backlog — trigger: when second repo onboarding reveals inability to handle non-GitHub sources
> 7 stories, fully decomposed, ready to implement when demand appears

---

## Epic Sequence & Dependencies

```
Current (Sprints 1-3):
  E37 Tests → E38 MVP (Slices 1+2)

Next (sprint-plan after Sprint 3):
  E38 Slices 3+4 (conditional)  OR  E39 Analytics
                                       |
                                    E40 Remote Verification (P0)
                                       |
                                    E41 Multi-Repo (P1)
                                       |
                                    E42 Execute Tier (P2, depends on E40)
                                       |
                                    E27 Multi-Source Webhooks (P1 backlog, on demand)
```

---

## Completed Epics

- **Epic 37** — Phase 3: Interactive Controls & Governance (28 stories, tests pending Sprint 1)
- **Epic 36** — Phase 2: Planning Experience (29 stories across 4 slices)
- **Epic 35** — Phase 1: Pipeline Visibility (63 stories)
- **Epic 34** — Phase 0: SSE PoC + Frontend Scaffolding (14 stories)
- **Epics 0-33** — All prior epics (Epic 27 deferred)
