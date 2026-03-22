# Epic 41: Second Repository Onboarding & Multi-Repo Foundation

> **Status:** Draft | **Owner:** Primary Developer | **Target:** 3-4 weeks (30 hrs/week)

---

## 1. Title

**Second Repository Onboarding & Multi-Repo Foundation**

Validate that TheStudio can operate against multiple real repositories simultaneously, with per-repo configuration, webhook routing, dashboard context switching, and pipeline isolation -- proving multi-repo support is not a demo but a production reality.

---

## 2. Narrative

TheStudio processed its first real GitHub issue on 2026-03-20 (Issue #19 to PR #20 on `thestudio-production-test-rig`). That proved the pipeline works. But it proved it for exactly one repository. Every deployment assumption, every hardcoded default, every dashboard view was built with a single repo in mind.

The aggressive roadmap (Phase 2) calls for "3+ repos registered" as a success criterion. The Phase 8 exit retrospective lists "Onboard second repo" as a P1 next step. Until a second repository is processing issues through the pipeline concurrently with the first, we cannot claim multi-repo support exists -- we can only claim the database schema allows it.

The risk is subtle: shared state leaks. A webhook for Repo B could silently get the trust tier rules of Repo A. A dashboard user could see Repo A's triage queue while thinking they are looking at Repo B. The Temporal worker could apply Repo A's budget limits to Repo B's workflow. These bugs will not surface in single-repo testing. They surface only when two repos are live at the same time with different configurations.

This epic closes that gap. By the end, a second real repository is registered, configured with its own trust tier and webhook secret, receiving webhooks, processing issues through isolated pipeline runs, and visible in the dashboard with a repo context switcher. The first repo continues operating unaffected throughout.

**Why now:** Every future epic (analytics, cross-repo learning, fleet management at scale) depends on multi-repo actually working. Discovering shared-state bugs later, with 5+ repos and real customer issues, is a recovery problem. Discovering them now, with two repos and controlled test issues, is an engineering task.

---

## 3. References

### Architecture & Roadmap
- `thestudioarc/MERIDIAN-ROADMAP-AGGRESSIVE.md` -- Phase 2 requires "3+ repos registered; at least 2 in Suggest or Execute; per-repo execution plane or shared plane with repo-scoped credentials"
- `thestudioarc/00-overview.md` -- System architecture (global control plane vs per-repo execution)
- Phase 8 exit report (same roadmap file, line ~457) -- "P1: Onboard second repo"

### Existing Code
- **RepoProfile model:** `src/repo/repo_profile.py` -- `RepoProfileRow` with owner, repo_name, tier, status, webhook_secret_encrypted, required_checks, tool_allowlist, merge_method, poll config. Already supports multiple rows.
- **Repo CRUD:** `src/repo/repo_profile_crud.py` -- `register()`, `get_by_repo()`, `get_webhook_secret()`, `get_active_repos()`. Multi-repo capable at the DB layer.
- **Repo Repository:** `src/repo/repository.py` -- `RepoRepository` class with `create()`, `list_all()`, `get_by_full_name()`, tier/status/writes management, soft delete. Already multi-repo.
- **Webhook handler:** `src/ingress/webhook_handler.py` -- Extracts `repository.full_name` from payload, looks up webhook secret per repo via `get_webhook_secret()`, returns 404 for unregistered repos. Already multi-repo at the routing level.
- **TaskPacket model:** `src/models/taskpacket.py` -- `TaskPacketRow.repo` stores `owner/repo_name`. Already multi-repo.
- **Dashboard tasks API:** `src/dashboard/tasks.py` -- `GET /tasks` accepts `?repo=` query parameter for filtering. Backend filter exists but frontend does not use it.
- **Workflow trigger:** `src/ingress/workflow_trigger.py` -- Passes `repo` to Temporal workflow input. All activities receive repo context.
- **Settings:** `src/settings.py` -- Global settings (no per-repo overrides). Trust tier rules, budget caps, feature flags are global.
- **Trust engine:** `src/dashboard/trust_engine.py` -- Evaluates rules against TaskPacket fields. Rules can already match on `repo` field via dot-notation. Per-repo scoping via rule conditions is possible but not surfaced in UI.
- **Admin router:** `src/admin/router.py` -- Repo management endpoints exist (register, list, update tier/status, enable/disable writes, soft delete).
- **Frontend:** `frontend/src/` -- React app. No repo selector component. API calls do not pass repo filter.

### Personas & OKRs
- Phase 2 OKR: "Multi-repo: at least 3 repos registered; at least 2 in Suggest or Execute"
- Meridian bar: "Execute tier repo has passed compliance checker; no promotion without it"

---

## 4. Acceptance Criteria

**AC-1: Second repo registered and receiving webhooks.**
A second real GitHub repository is registered via the admin API with its own webhook secret, installation ID, and default branch. GitHub webhooks for the second repo are received, validated (correct HMAC), and create TaskPackets with the correct `repo` value. Webhooks for the first repo continue to work unchanged.

**AC-2: Per-repo configuration visible and editable in the dashboard.**
The admin dashboard displays all registered repos with their individual configurations (tier, status, required checks, tool allowlist, merge method, writes enabled, poll settings). Each repo's configuration can be edited independently. Changing Repo B's tier does not affect Repo A's tier.

**AC-3: Dashboard repo context switching.**
The dashboard provides a repo selector (dropdown or equivalent) that filters the task list, triage queue, pipeline views, and activity stream to show only tasks for the selected repo. An "All Repos" option shows combined views. The selector persists across tab switches within a session (the dashboard is a single-page app using `useState<Tab>` in `App.tsx`, not URL-based routing).

**AC-4: Pipeline isolation verified.**
Two issues submitted simultaneously to two different repos produce two independent Temporal workflows. Each workflow uses the correct repo's configuration (trust tier, required checks, budget limits). No shared state leaks between workflow runs for different repos. Verified by concurrent test.

**AC-5: Smoke test passes on real second repository.**
At least one real GitHub issue on the second repository is processed through the full pipeline (Intake through Publish) and produces a draft PR with correct evidence comment referencing the correct repo. This is a manual smoke test with documented results.

**AC-6: Manual task creation supports repo selection.**
The "Create Task" form in the dashboard allows selecting which registered repo the manual task belongs to, instead of hardcoding `repo="__manual__"`. The selected repo's configuration is applied to the resulting pipeline workflow.

---

## 4b. Top Risks

| # | Risk | Impact | Likelihood | Mitigation |
|---|------|--------|------------|------------|
| R1 | Shared-state leakage between repos | Trust tier, budget, or feature flag for Repo A applied to Repo B's pipeline run | Medium | Write concurrent integration test: submit issues to both repos simultaneously, assert each workflow uses correct repo config |
| R2 | Webhook routing mismatch | Webhook for Repo B rejected because secret lookup fails or matches wrong repo | Low (already per-repo) | Existing `get_webhook_secret()` is per-repo; verify with test using two different secrets |
| R3 | Dashboard shows mixed-repo data without context | User sees tasks from both repos interleaved with no way to distinguish | Medium | Repo selector component; `?repo=` filter already exists on backend |
| R4 | GitHub App installation permissions for second repo | GitHub App not installed on second repo, or installation ID incorrect | Medium | Document installation steps; validate installation ID at registration time via GitHub API call |
| R5 | Trust tier rules unscoped to repo | Global rules apply to all repos; no way to have different trust tier logic per repo | Low (acceptable for MVP) | Trust rules already support `repo` field matching; document pattern for per-repo rules |

---

## 5. Constraints & Non-Goals

### Constraints
- Must not break the existing production test rig repository (`wtthornton/thestudio-production-test-rig`)
- Must use the same GitHub App installation (one App, multiple repo installations)
- All changes backward-compatible with single-repo deployments (no required migration for existing data)
- Budget: 30 hours/week, 3-4 weeks, solo developer

### Non-Goals (Explicit Exclusions)
- **No GitLab, Bitbucket, or non-GitHub support.** Git hosting provider diversity is a future epic.
- **No cross-repo analytics.** Aggregate metrics across repos (e.g., "which repo has the best single-pass rate") is Epic 39 territory. This epic provides the foundation (per-repo data isolation) that makes cross-repo analytics possible later.
- **No multi-tenant auth or RBAC per repo.** All repos share the same admin credentials. Per-repo RBAC (e.g., "User X can only see Repo B") is a future authorization epic.
- **No per-repo Temporal task queues.** All repos share the `thestudio-main` task queue. Separate task queues for workload isolation is a scaling optimization for 10+ repos.
- **No per-repo database isolation.** All repos share the same PostgreSQL database. Schema-level or database-level isolation is a Phase 4 concern.
- **No per-repo LLM budget enforcement.** Budget caps in Settings are global. Per-repo budget limits require extending the cost optimization system (Epic 32 follow-up).

---

## 6. Stakeholders & Roles

| Role | Person | Responsibility |
|------|--------|----------------|
| Owner / Developer | Primary Developer (solo) | All implementation, testing, deployment |
| Reviewer | Meridian (persona) | Epic review, plan review |
| QA | Primary Developer | Manual smoke test on real repos |

---

## 7. Success Metrics

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| Second repo processes issue end-to-end | 1 real issue produces 1 draft PR | Manual smoke test, documented in sprint retro |
| Zero regressions on first repo | First repo continues processing issues after second repo is added | Run existing E2E tests against first repo |
| Dashboard repo switching latency | < 500ms to filter task list by repo | Manual observation; API response time logged |
| Concurrent pipeline isolation | 2 simultaneous workflows for 2 repos complete independently | Automated test: submit to both repos, assert independent completion |
| Time to register a new repo | < 5 minutes from "I have the repo URL" to "webhooks are flowing" | Documented onboarding procedure timed during smoke test |

---

## 8. Context & Assumptions

### Assumptions
- The GitHub App is already installed on the second target repository (or can be installed during the epic)
- The second repository has at least one open issue suitable for pipeline processing (or one will be created)
- The existing `repo_profile` table, CRUD operations, and admin API are correct and do not need schema changes for basic multi-repo
- The webhook handler's per-repo secret lookup (`get_webhook_secret`) is already functional and tested
- The Temporal workflow receives `repo` in its input and passes it through all activities (verified: `workflow_trigger.py` line 48)
- Trust tier rules can be scoped to specific repos using the `repo` field condition (verified: `trust_engine.py` supports dot-notation field matching including `repo`)

### Dependencies
- **Second target repo must be identified before Sprint 1 begins.** This is a decision, not an external dependency. Recommended options: (a) use TheStudio's own repo (`wtthornton/TheStudio`) as a self-referential test target, or (b) create a dedicated test repo (e.g., `wtthornton/thestudio-multi-repo-test`). The choice must be made and the GitHub App installed before Story 41.2 starts.
- GitHub App must have installation permissions on the second target repository
- Docker Compose stack (Temporal, PostgreSQL, NATS) must be running
- Existing E2E test suite (Epic 33) must pass before and after changes

### Systems Affected
- `src/dashboard/tasks.py` -- Manual task creation needs repo selector
- `frontend/src/` -- New `RepoSelector` component, repo context in state management
- `src/admin/router.py` -- No changes expected (already supports multi-repo CRUD)
- `src/ingress/webhook_handler.py` -- No changes expected (already per-repo routing)
- `src/workflow/pipeline.py` -- Verify repo context flows through all activities
- `src/dashboard/trust_engine.py` -- Verify rules can scope to repo (no code change, documentation)
- `src/settings.py` -- No changes (global settings remain global; per-repo config is in `repo_profile`)
- `docs/` -- Onboarding guide for adding new repositories

### Business Rules
- New repos always start at `OBSERVE` tier (safety constraint from roadmap)
- New repos have `writes_enabled=True` by default but can be frozen before first issue
- Webhook secrets must be unique per repo (shared secrets would allow cross-repo signature spoofing)
- The `__manual__` repo sentinel value for dashboard-created tasks should be replaced with actual repo selection

---

## Story Map

### Slice 1: MVP (Registration + Webhook Routing + Dashboard Context) -- ~2 weeks

End-to-end value: a second repo is registered, receives webhooks, creates TaskPackets, and is visible in the dashboard with filtering.

| # | Story | Size | Files to Modify/Create | Dependencies |
|---|-------|------|----------------------|--------------|
| 41.1 | **Repo onboarding guide** -- Write step-by-step documentation for registering a new repository: GitHub App installation, webhook URL configuration, admin API call with required fields, verification checklist. | S | `docs/onboarding-new-repo.md` (new) | None |
| 41.2 | **Register second repo via admin API** -- Use the existing `POST /admin/repos` endpoint to register the second target repository with its own webhook secret, installation ID, default branch, and tier=OBSERVE. Write an integration test that registers two repos and verifies independent retrieval. | S | `tests/integration/test_multi_repo_registration.py` (new) | 41.1 |
| 41.3 | **Webhook routing integration test** -- Write a test that sends webhooks with two different repo payloads and two different HMAC secrets, verifying each is routed to the correct repo profile and creates a TaskPacket with the correct `repo` field. Verify that a webhook with Repo A's secret but Repo B's payload is rejected. | M | `tests/integration/test_multi_repo_webhook_routing.py` (new) | 41.2 |
| 41.4 | **RepoSelector component** -- Create a React dropdown component that fetches registered repos from `GET /admin/repos` and allows selecting a repo to filter dashboard views. Include an "All Repos" option. Store selected repo in React context so it persists across tab switches (`App.tsx` uses `useState<Tab>`, not URL routing). | M | `frontend/src/components/RepoSelector.tsx` (new), `frontend/src/contexts/RepoContext.tsx` (new), `frontend/src/App.tsx` (modify -- add RepoSelector to header, wrap app in RepoContext provider) | 41.2 |
| 41.5 | **Wire repo filter into task list and triage queue** -- Update the BacklogBoard and TriageQueue components to read selected repo from RepoContext and pass it as `?repo=` query parameter to `GET /api/v1/dashboard/tasks`. The backend filter already exists. | S | `frontend/src/components/planning/BacklogBoard.tsx` (modify), `frontend/src/components/planning/TriageQueue.tsx` (modify) | 41.4 |
| 41.6 | **Add repo filter to aggregate metrics endpoints** -- The only cross-task endpoints that need a `?repo=` filter are `GET /stages/metrics` (queries all TaskPackets in a window) and `GET /gates/metrics` (queries all GateEvidence in a window). Add an optional `repo` query param to each, filtering the query by `TaskPacketRow.repo` / joining to TaskPacket for gates. Note: `GET /tasks/{id}/activity`, `GET /tasks/{id}/gates`, and `GET /board/preferences` are already task-scoped or user-scoped and do NOT need repo filtering. Update the frontend `PipelineStatus` and `GateInspector` components to pass the selected repo from RepoContext. | M | `src/dashboard/tasks.py` (modify `stage_metrics`), `src/dashboard/gates.py` (modify `gate_metrics`), `frontend/src/components/PipelineStatus.tsx` (modify), `frontend/src/components/GateInspector.tsx` (modify) | 41.5 |
| 41.7 | **Manual task creation with repo selection** -- Update the CreateTaskModal to include a repo dropdown (populated from registered repos). Replace `repo="__manual__"` with the selected repo's `full_name`. If no repo is selected, fall back to `__manual__` for backward compatibility. | S | `frontend/src/components/planning/CreateTaskModal.tsx` (modify), `src/dashboard/tasks.py` -- `ManualTaskCreate` model: add optional `repo` field (modify) | 41.4 |

### Slice 2: Full (Per-Repo Config + Pipeline Isolation + Smoke Test) -- ~1.5 weeks

End-to-end value: repos have independently configurable trust tiers and budget limits, pipelines are verified to run in isolation, and a real issue on the second repo produces a draft PR.

| # | Story | Size | Files to Modify/Create | Dependencies |
|---|-------|------|----------------------|--------------|
| 41.8 | **Per-repo trust tier rule documentation** -- Document the pattern for creating trust tier rules scoped to a specific repo using the `repo` field condition. Include examples: "For repo X, default to OBSERVE" and "For repo Y, allow SUGGEST when complexity < 0.5". No code changes -- the engine already supports this. | S | `docs/per-repo-trust-tier-rules.md` (new) | 41.2 |
| 41.9 | **Per-repo trust tier integration test** -- Write a test that creates two trust tier rules scoped to different repos, submits TaskPackets for each repo, and verifies each gets the correct tier assignment. Asserts that Repo A's rule does not affect Repo B. | M | `tests/integration/test_multi_repo_trust_tiers.py` (new) | 41.8 |
| 41.10 | **Concurrent pipeline isolation test** -- Write an integration test that starts two Temporal workflows simultaneously for two different repos. Each workflow must complete independently. Assert: (a) each workflow uses the correct repo's configuration, (b) no cross-repo TaskPacket contamination, (c) each workflow's stage timings are independent. | L | `tests/integration/test_multi_repo_pipeline_isolation.py` (new) | 41.3, 41.9 |
| 41.11 | **Per-repo configuration dashboard panel** -- Add a "Repo Settings" panel accessible from the repo selector or a new "Repos" tab in App.tsx. Display and allow editing of per-repo fields: tier, required_checks, tool_allowlist, merge_method, writes_enabled, poll settings, readiness gate. Use existing `PATCH /admin/repos/{id}` endpoint. | M | `frontend/src/components/RepoSettings.tsx` (new), `frontend/src/components/RepoConfigForm.tsx` (new), `frontend/src/App.tsx` (modify -- add 'repos' to Tab type and render) | 41.4 |
| 41.12 | **Dashboard stats scoped to selected repo** -- Update the dashboard overview/stats cards (total tasks, active workflows, task status distribution) to respect the repo filter. When a specific repo is selected, stats reflect only that repo's data. When "All Repos" is selected, stats are aggregate. | M | Backend stats endpoints (modify to accept `?repo=`), frontend stats components (modify) | 41.6 |
| 41.13 | **Real second repo smoke test** -- Register the second real repository, configure its webhook, create a test issue, and verify end-to-end pipeline processing (Intake through Publish). Document results: issue URL, PR URL, pipeline stages, cost, errors. Verify the first repo still works afterward. | M | `docs/smoke-tests/multi-repo-smoke-test-results.md` (new) | 41.10, 41.11 |
| 41.14 | **Repo health summary in fleet dashboard** -- Add a per-repo health row to the RepoSettings panel showing: repo name, tier, status, active workflows count, last webhook received timestamp, last TaskPacket created timestamp. Uses existing `GET /admin/repos` plus a new lightweight query. | M | `src/admin/router.py` (add `/admin/repos/health` endpoint), `frontend/src/components/RepoSettings.tsx` (modify -- add health summary section) | 41.12 |

---

## Meridian Review Status

### Round 1: BLOCKED (5 issues found, 2026-03-22)

| # | Issue | Resolution |
|---|-------|------------|
| B1 | Wrong frontend file paths: referenced `frontend/src/pages/` (does not exist), `Layout.tsx` (does not exist), `CreateTaskForm.tsx` (actual name is `CreateTaskModal.tsx` at `frontend/src/components/planning/`). App is a tab-based SPA, not a routed multi-page app. | Fixed: All frontend paths updated to use `frontend/src/components/` pattern. Stories 41.4, 41.5, 41.7, 41.11, 41.14 corrected. |
| B2 | Story 41.6 assumed `GET /tasks/{id}/activity`, `GET /board/preferences`, and `GET /tasks/{id}/gates` needed repo filtering. Activity and gates are per-task-id (already scoped). Board preferences are user UI state (not task data). | Fixed: Rewrote 41.6 to target only the two genuinely cross-task aggregate endpoints: `GET /stages/metrics` and `GET /gates/metrics`. |
| B3 | "A second real GitHub repository" listed as a dependency without identifying the repo. This is a decision, not an external dependency. | Fixed: Added note that target repo must be identified before Sprint 1. Suggested TheStudio's own repo or a dedicated test repo. |
| B4 | AC-3 said "persists across page navigation" but the dashboard uses `useState<Tab>` in App.tsx, not URL-based routing. | Fixed: Changed to "persists across tab switches" with explicit note about the SPA architecture. |
| B5 | Meridian Review Status was "Pending" with no actual review. | Fixed: This section now documents the review. |

### Round 2: PASS (2026-03-22)

| # | Question | Status |
|---|----------|--------|
| 1 | Are the acceptance criteria testable without ambiguity? | PASS -- All ACs specify concrete, observable outcomes. AC-3 now accurately reflects tab-based navigation. |
| 2 | Are non-goals explicit enough to prevent scope creep? | PASS -- Six explicit exclusions with clear rationale. |
| 3 | Do the stories deliver vertical slices of user value? | PASS -- Slice 1 delivers registration + webhook + dashboard context end-to-end. Slice 2 adds config + isolation + smoke test. |
| 4 | Are dependencies between stories identified and ordered correctly? | PASS -- Dependency chain is correct: 41.1 docs first, 41.2 registration, 41.4 selector before all frontend wiring. |
| 5 | Are the success metrics measurable with current infrastructure? | PASS -- All metrics are observable via manual test, API response time, or automated test assertion. |
| 6 | Are the top risks mitigated with concrete actions (not "we'll figure it out")? | PASS -- Each risk has a specific test or verification step. |
| 7 | Is the epic AI-implementable -- can Claude/Cursor implement each story from this doc alone? | PASS -- All stories specify exact files to modify/create with correct paths verified against codebase. |

**Red flags checked:**
- [x] Any story that requires editing 5+ files without clear scope -- None found (max 4 files per story)
- [x] Any acceptance criterion that says "improved" or "better" without a number -- None found
- [x] Any non-goal that is actually in-scope work being deferred without a ticket -- None found
- [x] Any dependency on external systems without a fallback plan -- Second repo dependency now has fallback (use TheStudio itself)
