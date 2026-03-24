# Epic 38 — GitHub Deep Integration: Issue Import, PR Evidence, Projects Sync, and Pipeline Comments

> **Phase:** UI Phase 4 | **Status:** **MVP delivered in repo** (Slices 1–2, stories **38.1–38.12**); Meridian R2 PASS (2026-03-22). **Slices 3–4** (Projects sync, pipeline comments, webhook bridge) not started.
> **Estimated duration:** 5-7 weeks (full epic) | **Stories:** 27 across 4 slices (MVP: Slices 1+2 — **shipped**)
> **Depends on:** Epic 34 (COMPLETE), Epic 35 (COMPLETE), Epic 36 (COMPLETE), Epic 37 (COMPLETE)
> **Kill Criterion:** If after MVP delivery (Slices 1+2), fewer than 20% of pipeline tasks use manual import within 2 weeks, defer Slices 3-4 and proceed to Epic 39. Slices 1+2 shipping alone constitutes a successful epic.

---

## 1. Title

**Make GitHub the natural co-pilot for every pipeline run** — bidirectional sync, evidence-rich PR review, issue import, and live pipeline comments so developers never leave their GitHub workflow to understand what TheStudio is doing.

---

## 2. Narrative

TheStudio processes GitHub issues and produces draft PRs, but the connection is one-way and shallow. A developer who opens a PR sees a Markdown evidence comment — useful, but not explorable. A manager looking at their GitHub Projects board has no idea which issues are in-flight, at what stage, or what they cost. A teammate scanning the issue tracker sees no indication that TheStudio picked up their bug report, let alone that Verify just failed on the second loopback.

This matters now because Phases 1-3 deliver a rich dashboard experience — pipeline visualization, planning tools, interactive controls. But most developers live in GitHub. If TheStudio's intelligence stays locked inside its own dashboard, adoption stalls. The dashboard becomes a monitoring silo that nobody checks until something breaks.

Phase 4 bridges that gap. It makes GitHub a first-class surface for pipeline state:

- **Issue Import** lets developers pull existing backlog items into the pipeline without waiting for webhook triggers.
- **PR Evidence Explorer** gives reviewers a tabbed, explorable view of evidence, diffs, intent, gates, and cost — not just a flat Markdown blob.
- **GitHub Projects Sync** pushes pipeline state (stage, trust tier, cost, complexity) to Projects v2 boards so managers see live status without leaving GitHub.
- **Pipeline Comments** post structured, self-updating status comments on issues so stakeholders track progress in real time.
- **Webhook Bridge** ensures that external GitHub actions (PR reviews, merges, label changes) flow back into the dashboard instantly.

The existing `ProjectsV2Client` (Epic 29, feature-flagged off at `src/github/projects_client.py`) provides the GraphQL foundation for Projects sync. This epic enables it, extends it with new field mappings, and wires the bidirectional webhook loop.

---

## 3. References

| Reference | Location |
|-----------|----------|
| Pipeline UI Master Vision | `docs/design/00-PIPELINE-UI-VISION.md` (Section 8, Phase 4) |
| GitHub Integration Design Spec | `docs/design/04-GITHUB-INTEGRATION-ANALYTICS.md` (Sections 2-4, 6-7) |
| Backend Requirements (Phase 4) | `docs/design/06-BACKEND-REQUIREMENTS.md` (Section 3, Phase 4: B-4.1 through B-4.12) |
| Existing Projects v2 Client | `src/github/projects_client.py` (Epic 29, feature-flagged) |
| Existing Field Mapping | `src/github/projects_mapping.py` (status, tier, risk mappings) |
| Evidence Comment Formatter | `src/publisher/evidence_comment.py` |
| Webhook Handler | `src/ingress/webhook_handler.py` |
| Persona: Reviewer/Stakeholder | `docs/design/00-PIPELINE-UI-VISION.md` Section 6 |
| GitHub Projects v2 API | https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/using-the-api-to-manage-projects |
| OKRs | `thestudioarc/personas/MERIDIAN-TEAM-REVIEW-AND-OKRS.md` |

---

## 4. Acceptance Criteria

**AC-1: Issue Import.** A developer can browse open GitHub issues (with label/search filters), select one or more, and import them as TaskPackets. Imported issues appear in the triage queue (if triage mode is enabled per Phase 2) or start the pipeline directly. Issues already in the pipeline are visually marked and cannot be re-imported.

**AC-2: PR Evidence Explorer.** When a TaskPacket reaches Publish, the dashboard provides a tabbed viewer with at minimum: (a) rendered evidence comment, (b) diff view, (c) intent specification, (d) gate results summary, (e) cost breakdown. Reviewer actions (Approve & Merge, Request Changes, Close PR, View on GitHub) are functional and call the GitHub API.

**AC-3: GitHub Projects Sync — Outbound.** When `projects_v2_enabled` is turned on and a project is configured, every TaskPacket stage transition pushes updated Status, Trust Tier, Cost, and Complexity fields to the linked Projects v2 board. New TaskPackets are auto-added to the project.

**AC-4: GitHub Projects Sync — Inbound.** When a user manually changes an item's status on the GitHub Projects board (e.g., drags to "Done"), TheStudio receives the `projects_v2_item` webhook and updates the TaskPacket accordingly (e.g., triggers abort if still in pipeline).

**AC-5: Projects Sync Configuration.** The dashboard exposes a configuration UI where the developer can: connect a project, map stage groups to status values, select which custom fields to sync, and toggle sync behaviors (auto-add, respect manual overrides, auto-close issues).

**AC-6: Pipeline Comments.** When a TaskPacket progresses through stages, TheStudio creates a single structured comment on the linked GitHub issue (at Context entry) and edits it in place at each subsequent stage transition. The final update includes the PR link. Comments are configurable (enable/disable per repo).

**AC-7: Webhook Bridge.** GitHub webhook events (PR reviewed, PR merged, PR closed, issue commented, issue labeled, check completed) are parsed, published to NATS JetStream on `github.event.*` subjects, and propagated to the SSE stream so the dashboard updates in real time.

**AC-8: No regression.** Existing webhook intake (`POST /webhook/github`), evidence comment generation, and Projects v2 client tests continue passing. The `projects_v2_enabled` feature flag remains the gate for Projects sync — nothing activates without explicit opt-in.

### 4b. Top Risks

| # | Risk | Impact | Mitigation |
|---|------|--------|------------|
| R1 | GitHub Projects v2 API requires PAT with `project` scope; standard GITHUB_TOKEN lacks it | Sync silently fails | Validate token scopes on project connect; surface clear error if missing |
| R2 | GraphQL rate limits (5000 points/hour) under heavy sync | Status updates lag or fail | Batch mutations, cache field/option IDs (already in client), exponential backoff |
| R3 | Phase 2 TRIAGE status may not exist yet when this epic starts | Import-to-triage path breaks | Import defaults to "direct to pipeline" if TRIAGE status unavailable; guard with runtime check |
| R4 | Bidirectional sync creates feedback loops (TheStudio pushes status, GitHub fires webhook, TheStudio processes webhook) | Infinite update loop | Tag outbound updates with a marker; skip webhook events that originated from TheStudio |
| R5 | Evidence JSON schema not defined | Frontend/backend contract unclear | Define schema in Slice 2 before frontend work; use Pydantic model |

---

## 5. Constraints & Non-Goals

### Constraints

- **GitHub-only.** No GitLab, Bitbucket, or other forge support.
- **Single repo.** Multi-repo GitHub Projects sync is out of scope (per vision doc Section 9).
- **Existing auth.** Uses the same admin auth as the current panel. No new RBAC or user accounts.
- **Feature-flagged.** Projects sync remains behind `projects_v2_enabled`. Issue import and PR evidence are always available once Phase 4 deploys.
- **SSE infrastructure required.** The SSE-over-NATS bridge from Phase 0 (B-0.2) must be operational before the webhook bridge (Slice 4) can propagate events to the browser.
- **No view mutations.** GitHub Projects v2 API does not support creating or editing project views programmatically. Sync is limited to items and fields.

### Non-Goals

- **Analytics dashboards.** Throughput, bottleneck, and failure analysis belong to Phase 5 (Epic 39+). This epic touches GitHub data but does not build aggregate analytics.
- **Diff annotation by expert.** The design spec describes color-coded expert attribution per diff hunk (Section 3.3). This requires assembler-level provenance tracking that does not exist yet. Deferred to a future enhancement. The Diff tab in Slice 2 shows a standard diff without expert annotations.
- **Auto-merge from dashboard.** The "Approve & Merge" action is wired to the GitHub API, but auto-merge (Execute tier, no human click) is Epic 22 scope, not this epic.
- **Mobile or responsive layout.** Desktop-first per vision doc.
- **GitHub issue creation from dashboard.** This epic imports existing issues; it does not create new GitHub issues from the dashboard.
- **Notification integrations.** Slack/Discord/email for pipeline events are deferred (Phase 3+ consideration per vision doc).

---

## 6. Stakeholders & Roles

| Role | Who | Responsibility |
|------|-----|----------------|
| Epic Owner | Solo Developer | All implementation, testing, deployment |
| Design | Design Specs 04 + 06 | Wireframes and interaction patterns defined in design docs |
| Tech Lead | Solo Developer | Architecture decisions, API contracts |
| QA | Automated test suite | Unit tests per story, integration tests per slice |
| External | GitHub API | GraphQL (Projects v2) + REST (issues, PRs, comments) |
| Review | Meridian | Epic review before commit; story-level review at slice boundaries |

---

## 7. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Issue import adoption | 60%+ of pipeline tasks originate from manual import (vs webhook-only) within 30 days of launch | TaskPacket source field |
| PR evidence engagement | Evidence Explorer is used for 50%+ of published TaskPackets (at least one tab viewed) within 30 days of launch | Server-side: count of `GET /tasks/:id/evidence` requests vs total PUBLISHED TaskPackets |
| Projects sync accuracy | 95%+ of TaskPacket stage transitions produce a corresponding `update_project_status_activity` success log within 60 seconds | Server-side: compare `pipeline.stage.exit` event count to `projects.sync.success` audit log count per period |
| Pipeline comment usefulness | Developers report (via feedback) that issue comments reduce dashboard visits for status checks | Qualitative feedback; dashboard visit frequency delta |
| Webhook bridge latency | GitHub events appear in SSE stream within 2 seconds of webhook receipt | Event timestamp comparison |
| Zero feedback loops | No infinite update cycles between TheStudio and GitHub Projects | Monitor for >2 consecutive updates on the same item within 10 seconds |

---

## 8. Context & Assumptions

### Business Rules

- **Import deduplication.** If a GitHub issue already has a TaskPacket, import is blocked for that issue. The UI shows "already in pipeline" with a link to the existing TaskPacket.
- **Comment idempotency.** Pipeline comments use a single comment per TaskPacket, edited in place. The comment is identified by the `<!-- thestudio-evidence -->` marker (same pattern as `src/publisher/evidence_comment.py`).
- **Sync conflict resolution.** When both TheStudio and a GitHub user update the same field simultaneously, the most recent write wins. TheStudio tags its own updates with a `thestudio-sync` marker in metadata to detect and skip self-triggered webhooks.
- **Evidence JSON.** The evidence comment is already generated as Markdown (`src/publisher/evidence_comment.py`). This epic adds a parallel structured JSON representation (`EvidencePayload` Pydantic model) that the frontend consumes for the tabbed explorer. The Markdown version continues to be posted on GitHub PRs.

### Dependencies

| Dependency | Status | Impact if Missing |
|------------|--------|-------------------|
| Phase 0 SSE bridge (B-0.2) | Required before Slice 4 | Webhook bridge cannot propagate events to browser |
| Phase 2 TRIAGE status (B-2.1) | Optional | Import defaults to "direct to pipeline" mode |
| `ProjectsV2Client` (Epic 29) | Implemented, feature-flagged off | Slice 3 enables and extends it |
| `projects_mapping.py` (Epic 29) | Implemented | Slice 3 adds Cost and Complexity field mappings |
| Evidence comment formatter | Implemented | Slice 2 adds JSON output alongside Markdown |
| Webhook handler | Implemented | Slice 4 extends with NATS publishing |

### Systems Affected

| System | Change |
|--------|--------|
| `src/github/projects_client.py` | Enable, extend with custom field creation for Cost/Complexity |
| `src/github/projects_mapping.py` | Add Cost and Complexity field mappings |
| `src/publisher/evidence_comment.py` | Add `format_evidence_json()` returning structured dict |
| `src/ingress/webhook_handler.py` | Extend to publish parsed events to NATS JetStream |
| `src/workflow/activities.py` | Add pipeline comment creation/update activity |
| `src/workflow/pipeline.py` | Wire comment activity at stage transitions |
| `src/settings.py` | Add `pipeline_comments_enabled` feature flag |
| `src/dashboard/` (new) | API endpoints for import, PR actions, Projects config |
| `src/models/taskpacket.py` | Add `source` field (webhook vs import) if not present |
| `src/db/migrations/` | New migration for any schema changes |
| Frontend (`dashboard/`) | Import modal, PR evidence viewer, Projects config UI |

---

## Story Map

### MVP Designation

| Slice | MVP? | Rationale |
|-------|------|-----------|
| Slice 1: Issue Import | **MVP** | Core intake — import issues without webhooks |
| Slice 2: PR Evidence Explorer | **MVP** | Core output — review pipeline results with evidence |
| Slice 3: GitHub Projects Sync | Full | Integration — enhances visibility but not blocking |
| Slice 4: Pipeline Comments + Webhook Bridge | Full | Quality of life — keeps GitHub stakeholders informed |

---

### Slice 1: Issue Import & Triage (MVP)

> End-to-end value: Developer can pull GitHub issues into the pipeline from the dashboard.

| # | Story | Type | Files to Modify/Create | Est. |
|---|-------|------|------------------------|------|
| 38.1 | `GET /api/v1/dashboard/github/issues` — List repo issues from GitHub REST API with label/status/search filters, cached (5-min TTL), paginated | Backend | `src/dashboard/github_router.py` (new), `src/dashboard/__init__.py` | M |
| 38.2 | `POST /api/v1/dashboard/github/import` — Batch import selected issues as TaskPackets; check for duplicates; respect triage mode if available. **Intake boundary:** Import creates TaskPackets directly via `taskpacket_crud.py` (same as webhook handler), bypassing `src/intake/` eligibility checks since the developer has manually selected the issues. Sets `source_name="dashboard_import"` to distinguish from webhook intake. If `TRIAGE_MODE_ENABLED`, creates in TRIAGE status; otherwise creates in RECEIVED and starts Temporal workflow. | Backend | `src/dashboard/github_router.py`, `src/models/taskpacket_crud.py` | M |
| 38.3 | Import modal frontend — repo selector (uses existing admin settings repo config), label/status filters, search, issue list with checkboxes, import mode toggle (triage vs direct), "already in pipeline" detection | Frontend | `frontend/src/components/github/ImportModal.tsx` (new) | M |
| 38.4 | Integration test: import 2 issues, verify TaskPackets created, verify duplicate blocked | Test | `tests/integration/test_issue_import.py` (new) | S |

### Slice 2: PR Evidence Explorer (MVP)

> End-to-end value: Reviewer can explore PR evidence through a structured, tabbed interface.

| # | Story | Type | Files to Modify/Create | Est. |
|---|-------|------|------------------------|------|
| 38.5 | `EvidencePayload` Pydantic model — structured JSON schema for evidence (task summary, intent, gate results, cost breakdown, provenance, files changed) | Backend | `src/publisher/evidence_payload.py` (new) | M |
| 38.6 | `format_evidence_json()` — generate `EvidencePayload` alongside existing Markdown evidence comment | Backend | `src/publisher/evidence_comment.py` | M |
| 38.7 | `GET /api/v1/dashboard/tasks/:id/evidence` — Return `EvidencePayload` JSON for a TaskPacket | Backend | `src/dashboard/task_router.py` (new or extend) | S |
| 38.8 | PR Evidence Explorer frontend — tabbed viewer (Evidence, Diff, Intent, Gates, Cost) consuming evidence JSON | Frontend | `frontend/src/components/pr/EvidenceExplorer.tsx` (new) | L |
| 38.9 | `POST /api/v1/dashboard/tasks/:id/pr/approve` — Approve and merge PR via GitHub REST API | Backend | `src/dashboard/pr_router.py` (new) | M |
| 38.10 | `POST /api/v1/dashboard/tasks/:id/pr/request-changes` — Post PR review comment via GitHub API + create loopback signal | Backend | `src/dashboard/pr_router.py` | M |
| 38.11 | Reviewer action buttons frontend — Approve & Merge, Request Changes, Close PR, View on GitHub | Frontend | `frontend/src/components/pr/ReviewerActions.tsx` (new) | S |
| 38.12 | Integration test: evidence JSON generated for published TaskPacket, reviewer actions call GitHub API | Test | `tests/integration/test_pr_evidence_explorer.py` (new) | M |

### Slice 3: GitHub Projects Sync

> End-to-end value: Pipeline state visible on GitHub Projects board without visiting the dashboard.

| # | Story | Type | Files to Modify/Create | Est. |
|---|-------|------|------------------------|------|
| 38.13 | Enable `ProjectsV2Client` — remove feature-flag guard for sync when `projects_v2_enabled=True`; validate token scopes on connect | Backend | `src/workflow/pipeline.py`, `src/workflow/activities.py`, `src/settings.py` | S |
| 38.14 | Extend field mapping — add Cost (number) and Complexity (single-select) custom fields to `projects_mapping.py`. Add `create_custom_field()` GraphQL mutation to `ProjectsV2Client` (net-new capability — the client currently reads fields but cannot create them). Auto-create fields on first sync if they do not exist on the project. | Backend | `src/github/projects_mapping.py`, `src/github/projects_client.py` | M |
| 38.15 | GitHub-to-TheStudio sync — subscribe to `projects_v2_item` webhook events; update TaskPacket status when item status changes on GitHub board; skip self-triggered events | Backend | `src/ingress/webhook_handler.py`, `src/github/projects_sync.py` (new) | M |
| 38.16 | `GET /PUT /api/v1/dashboard/github/projects/config` — Projects sync configuration (project selection, field mapping, sync behaviors) | Backend | `src/dashboard/github_router.py` | M |
| 38.17 | `POST /api/v1/dashboard/github/projects/sync` — Force full sync (re-push all active TaskPackets to GitHub project) | Backend | `src/dashboard/github_router.py` | M |
| 38.18 | Projects sync configuration UI — connect project, map fields, toggle behaviors, test sync, force sync | Frontend | `frontend/src/components/github/ProjectsSyncConfig.tsx` (new) | M |
| 38.19 | Feedback loop guard — tag outbound GraphQL mutations with `thestudio-sync` client mutation ID; detect and skip inbound webhooks triggered by own mutations | Backend | `src/github/projects_client.py`, `src/github/projects_sync.py` | M |
| 38.20 | Integration test: stage transition pushes to Projects v2; manual GitHub status change updates TaskPacket; self-triggered webhook skipped | Test | `tests/integration/test_projects_sync.py` (new) | M |

### Slice 4: Pipeline Comments + Webhook Bridge

> End-to-end value: Stakeholders see live pipeline status on GitHub issues; external GitHub events flow into the dashboard in real time.

| # | Story | Type | Files to Modify/Create | Est. |
|---|-------|------|------------------------|------|
| 38.21 | Pipeline comment template — Markdown template with stage progress table, cost, model, trust tier; uses `<!-- thestudio-pipeline-status -->` marker for idempotent edits | Backend | `src/publisher/pipeline_comment.py` (new) | M |
| 38.22 | Pipeline comment activity — Temporal activity that creates comment on first call, edits in place on subsequent calls; final update includes PR link | Backend | `src/workflow/activities.py`, `src/workflow/pipeline.py` | M |
| 38.23 | `pipeline_comments_enabled` feature flag + per-repo configuration | Backend | `src/settings.py`, `src/admin/settings_service.py` | S |
| 38.24 | Webhook bridge — extend `webhook_handler.py` to parse PR and issue events, publish to NATS JetStream on `github.event.*` subjects | Backend | `src/ingress/webhook_handler.py` | M |
| 38.25 | SSE propagation — extend `src/dashboard/events.py` to include `github.event.*` subjects in the NATS stream subscription (currently only subscribes to `pipeline.>`). May require adding `github.>` as a second subject filter on the `THESTUDIO_PIPELINE` stream, or creating a second stream. Dashboard receives real-time GitHub events via existing SSE bridge. | Backend | `src/dashboard/events.py` (extend) | S |
| 38.26 | PR status and issue updates in dashboard — consume `github.event.*` SSE events to update PR Evidence Explorer (review status) and triage queue (new comments/labels) in real time | Frontend | `frontend/src/hooks/useGitHubEvents.ts` (new) | M |
| 38.27 | Integration test: stage transition posts comment on issue; comment edited on next transition; webhook events published to NATS | Test | `tests/integration/test_pipeline_comments.py` (new) | M |

---

## Meridian Review Status

### Round 1: CONDITIONAL PASS (2026-03-22)

**Overall Verdict: CONDITIONAL PASS — 6 blockers identified.**

| # | Question | Verdict | Detail |
|---|----------|---------|--------|
| 1 | Scope bounded and achievable? | **CONDITIONAL PASS** | Missing kill criterion for partial-ship scenario |
| 2 | Acceptance criteria testable? | **PASS** | All 8 ACs testable. AC-2 tab list pinned to 5 tabs. |
| 3 | Non-goals explicit? | **PASS** | 7 explicit non-goals, well-bounded |
| 4 | Dependencies identified? | **CONDITIONAL PASS** | SSE stream subject filter gap; intake boundary unclear |
| 5 | Success metrics measurable? | **CONDITIONAL PASS** | 2 metrics required frontend analytics not provisioned |
| 6 | Story map ordered by risk? | **PASS** | Correct: REST → schema → GraphQL → infrastructure |
| 7 | AI agent can implement? | **CONDITIONAL PASS** | 5 stories had wrong frontend paths; SSE file reference wrong |

### Blockers Found and Fixed

1. ~~**Frontend paths wrong.**~~ **FIXED:** All `dashboard/src/features/...` paths changed to `frontend/src/components/...` or `frontend/src/hooks/...`
2. ~~**SSE file reference wrong.**~~ **FIXED:** Story 38.25 now references `src/dashboard/events.py` with note about NATS stream subject expansion
3. ~~**Missing kill criterion.**~~ **FIXED:** Kill criterion added to epic header (20% import adoption threshold)
4. ~~**Unmeasurable success metrics.**~~ **FIXED:** PR evidence engagement and Projects sync accuracy metrics replaced with server-side measurable proxies
5. ~~**Intake boundary unclear.**~~ **FIXED:** Story 38.2 now specifies import creates TaskPackets via `taskpacket_crud.py` directly, sets `source_name="dashboard_import"`, respects triage mode
6. ~~**Missing field-creation capability.**~~ **FIXED:** Story 38.14 now explicitly notes `create_custom_field()` is net-new GraphQL mutation work

### Implementation rollup (MVP — 2026-03-24)

| Area | Location |
|------|----------|
| Issue list + import API | `src/dashboard/github_router.py`, `tests/dashboard/test_github_router.py`, `tests/integration/test_issue_import.py` |
| Import UI | `frontend/src/components/github/ImportModal.tsx` |
| Evidence JSON + Markdown | `src/publisher/evidence_payload.py`, `src/publisher/evidence_comment.py`, `tests/publisher/test_evidence_payload.py`, `tests/publisher/test_evidence_json.py` |
| Evidence API | `src/dashboard/tasks.py` (`GET /tasks/{id}/evidence`), `tests/dashboard/test_evidence_endpoint.py` |
| PR explorer + reviewer actions | `frontend/src/components/pr/EvidenceExplorer.tsx`, `ReviewerActions.tsx`, `src/dashboard/pr_router.py`, `tests/integration/test_pr_evidence_explorer.py` |

### Round 2: PASS (2026-03-22)

**Overall Verdict: PASS — All 6 blockers resolved. Epic approved for Helm sprint planning.**

| # | Question | R1 Verdict | R2 Verdict |
|---|----------|------------|------------|
| 1 | Scope bounded? | CONDITIONAL | **PASS** |
| 2 | ACs testable? | PASS | **PASS** |
| 3 | Non-goals explicit? | PASS | **PASS** |
| 4 | Dependencies identified? | CONDITIONAL | **PASS** |
| 5 | Metrics measurable? | CONDITIONAL | **PASS** |
| 6 | Story map risk-ordered? | PASS | **PASS** |
| 7 | AI agent can implement? | CONDITIONAL | **PASS** |
