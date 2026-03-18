# Epic 29 — GitHub Projects v2 Integration + Meridian Portfolio Review

**Author:** Saga
**Date:** 2026-03-17
**Status:** Complete (2026-03-18). Both sprints delivered. Meridian review passed.
**Sprint 1 Delivered:** 2026-03-17. Stories 29.0–29.4. 63 tests.
**Sprint 2 Delivered:** 2026-03-18. Stories 29.5–29.9. 60 tests.
**Prerequisites:** None hard-required. Publisher (step 9) is the integration point. Sprint 1 can validate with synthetic project data; Epic 15 real-repo output is not required.

---

## 1. Title

GitHub Projects v2 Integration + Meridian Portfolio Review — Implement the spec'd-but-unbuilt Projects v2 lifecycle synchronization so every TaskPacket's status is visible on a unified project board, then add a periodic Meridian review agent that reads the board state and flags portfolio-level health concerns.

## 2. Narrative

TheStudio's architecture spec defines a full GitHub Projects v2 integration. The overview doc (`thestudioarc/00-overview.md`, lines 293-337) specifies six status fields (Backlog, Queued, In Progress, In Review, Blocked, Done), automation tier fields, risk tiers, priority, owner, and repo — plus workflow automations that keep the board in sync with pipeline state. The compliance checker has a `_check_projects_v2()` method that's stubbed to always pass with a note: "Projects v2 check not yet implemented."

**None of this is built.** The Publisher doesn't update project fields. The workflow doesn't sync status transitions. The compliance check is a no-op. The unified multi-repo project board that was designed to "give humans a single view of the ecosystem without a custom UI" doesn't exist.

This matters for two reasons:

**First, visibility.** The Admin UI provides a platform-internal view of workflows and tasks. But GitHub Projects v2 is where humans already work — it's the board they check, the view they share in standups, the dashboard they link in status updates. Without Projects v2 sync, humans must switch to the Admin UI to see pipeline state. That's friction that reduces adoption.

**Second, Meridian has no data to review.** Meridian is defined as the VP of Success who reviews epics and plans before commit. But there's a bigger Meridian-shaped gap: nobody reviews the health of the delivery operation as a whole. Are tasks piling up in "Blocked"? Is one repo consuming all capacity? Are approval bottlenecks forming? Are high-risk items accumulating in parallel? These are portfolio-level questions that Meridian is designed to ask — but she needs a data source to ask them against. The Projects v2 board is that data source.

This epic has two parts:

1. **Projects v2 synchronization.** The Publisher updates project fields on every status transition. The workflow automations from the spec are implemented. The compliance checker validates the integration. The unified board exists and reflects reality.

2. **Meridian Portfolio Review.** A scheduled agent (daily or weekly) reads the project board state via GitHub's GraphQL API, computes health metrics, and produces a structured assessment. This is not a per-task gate — it's a periodic "state of the operation" review that flags concerns before they become crises.

### Why now

1. **The spec exists and is detailed.** The architecture doc defines exactly what fields, what automations, and why. This is implementation, not design.
2. **Real repo onboarding (Epic 15) will generate real board data.** Once the pipeline processes real issues, the board needs to reflect that reality.
3. **The compliance checker is stubbed.** The `PROJECTS_V2` compliance check passes unconditionally today. For Execute tier repos, this is a gap — the compliance gate should verify Projects v2 integration is actually working.

### Why Meridian at the project level

Meridian currently exists only as a documentation persona — she reviews epics and plans manually via Claude Code or Cursor. This epic gives her a programmatic role: periodic portfolio health review. The distinction:

| Aspect | Meridian (epic/plan review) | Meridian (portfolio review) |
|--------|---------------------------|---------------------------|
| Trigger | Manual, pre-commit | Scheduled (daily/weekly) |
| Input | Epic markdown, plan markdown | Projects v2 board state (live data) |
| Output | Pass/fail with gaps | Health report with flags |
| Action | Block commit until fixed | Notify + recommend (advisory) |
| Scope | Single epic or plan | All active work across repos |

Both are Meridian. One challenges artifacts before they're committed. The other challenges the operation while it's running. Same persona, different cadence.

## 3. References

| Artifact | Location |
|----------|----------|
| Projects v2 spec | `thestudioarc/00-overview.md` (lines 293-337) |
| Projects v2 spec (runtime flow) | `thestudioarc/15-system-runtime-flow.md` (lines 171-213) |
| Publisher (integration point) | `src/publisher/publisher.py` |
| Existing GitHub REST client | `src/publisher/github_client.py` (REST only — GraphQL client is new) |
| Evidence comment | `src/publisher/evidence_comment.py` |
| Compliance checker (stubbed) | `src/compliance/checker.py` (`_check_projects_v2`) |
| Compliance models | `src/compliance/models.py` (`PROJECTS_V2` check) |
| Compliance scorecard | `src/admin/compliance_scorecard.py` |
| Pipeline workflow | `src/workflow/pipeline.py` |
| Activity definitions | `src/workflow/activities.py` |
| Settings | `src/settings.py` |
| Meridian persona | `thestudioarc/personas/meridian-vp-success.md` |
| Meridian review checklist | `thestudioarc/personas/meridian-review-checklist.md` |
| Team reset | `thestudioarc/personas/TEAM.md` |
| **GitHub GraphQL: ProjectV2 type** | https://docs.github.com/en/graphql/reference/objects#projectv2 |
| **GitHub GraphQL: updateProjectV2ItemFieldValue** | https://docs.github.com/en/graphql/reference/mutations#updateprojectv2itemfieldvalue |
| **GitHub GraphQL: addProjectV2ItemById** | https://docs.github.com/en/graphql/reference/mutations#addprojectv2itembyid |

**GraphQL implementation note:** The Projects v2 mutation pattern is multi-step: (1) query project ID by owner + number, (2) query field IDs for the project, (3) query option IDs for single-select fields (Status, Tier, etc.), (4) call `updateProjectV2ItemFieldValue` with project ID + item ID + field ID + value. Cache project/field/option IDs after first resolution to avoid redundant queries.
| Agent framework | `src/agent/framework.py` |
| Observability conventions | `src/observability/conventions.py` |
| Policies | `thestudioarc/POLICIES.md` |

## 4. Acceptance Criteria

### Part 1: Projects v2 Synchronization

#### Project Field Management

1. **GitHub Projects v2 client exists.** `src/github/projects_client.py` contains a `ProjectsV2Client` class that uses GitHub's GraphQL API to: find a project by repo, get/set item field values (Status, Automation Tier, Risk Tier, Priority, Owner, Repo), and add items to a project. Authentication uses the existing GitHub App token.

2. **Field value mapping exists.** `src/github/projects_mapping.py` maps TaskPacket status to Projects v2 Status field values:

   | TaskPacket Status | Projects v2 Status |
   |---|---|
   | RECEIVED | Queued |
   | ENRICHED | Queued |
   | INTENT_BUILT | In Progress |
   | IN_PROGRESS | In Progress |
   | VERIFICATION_PASSED | In Progress |
   | AWAITING_APPROVAL | In Review |
   | CLARIFICATION_REQUESTED | Blocked |
   | HUMAN_REVIEW_REQUIRED | Blocked |
   | PUBLISHED | Done |
   | FAILED | Done |
   | REJECTED | Done |

3. **Automation Tier field is set from repo profile.** When a TaskPacket is created, the Automation Tier field is set to the repo's trust tier (Observe, Suggest, Execute).

4. **Risk Tier field is set from context enrichment.** After Context Manager runs, the Risk Tier field is set based on `complexity_index` band (low → Low, medium → Medium, high → High).

#### Publisher Integration

5. **Publisher updates Projects v2 on publish.** `publish_activity` calls `ProjectsV2Client.set_status("Done")` after successful PR creation. If the project is not configured or the API call fails, the publish continues — Projects v2 sync is best-effort, not a gate.

6. **Status transitions update Projects v2.** A new `update_project_status_activity` is called at key status transitions in the workflow: RECEIVED→Queued, INTENT_BUILT→In Progress, AWAITING_APPROVAL→In Review, PUBLISHED→Done, FAILED→Done. The activity is best-effort with retry but no failure propagation.

7. **Projects v2 sync is feature-flagged.** `settings.projects_v2_enabled: bool = False`. When disabled, no GraphQL calls are made. No latency impact.

#### Compliance

8. **Compliance checker validates Projects v2.** `_check_projects_v2()` is implemented: queries the GitHub API to verify the project exists, required fields are configured (Status, Automation Tier, Risk Tier, Priority, Owner, Repo), and at least one item has been synced. Replaces the current stub.

9. **Compliance scorecard shows real status.** The Admin UI compliance scorecard shows actual Projects v2 configuration status, not the current always-pass stub.

### Part 2: Meridian Portfolio Review

#### Review Agent

10. **Meridian portfolio review agent config exists.** `src/meridian/__init__.py` and `src/meridian/portfolio_config.py` define `MERIDIAN_PORTFOLIO_CONFIG` with `agent_name="meridian_portfolio"`, `max_turns=1`, `max_budget_usd=1.00`. System prompt implements portfolio health checks.

11. **Portfolio health checks are defined with tested defaults.** The Meridian portfolio agent evaluates the following checks. The numeric thresholds below are the **tested defaults** shipped in `settings.meridian_thresholds` (AC 19). They are configurable per deployment, but tests validate these specific values:
    - **Throughput health:** Ratio of Done to In Progress to Blocked. Flag if Blocked > 20% of active items.
    - **Risk concentration:** Count of High-risk items In Progress simultaneously. Flag if > 3.
    - **Approval bottleneck:** Items in In Review for > 48 hours. Flag each.
    - **Repo balance:** Items per repo. Flag if any repo has > 50% of total active items.
    - **Failure rate:** Tasks reaching Done with status=FAILED as percentage of total. Flag if > 30%.
    - **Stale items:** Items in Queued for > 7 days. Flag each.

12. **Portfolio review output model exists.** `PortfolioReviewOutput` with fields: `overall_health` (enum: healthy, warning, critical), `flags` (list of `HealthFlag` with category, severity, description, affected_items), `recommendations` (list of strings), `metrics` (dict of computed values), `reviewed_at` (datetime).

13. **Portfolio data collector exists.** `src/meridian/portfolio_collector.py` queries the GitHub Projects v2 API to collect current board state: all items with their field values, grouped by repo and status. Returns a `PortfolioSnapshot` that the agent evaluates.

#### Scheduling and Output

14. **Portfolio review runs on a Temporal schedule.** A Temporal scheduled workflow `MeridianPortfolioReviewWorkflow` runs the portfolio review at a configurable interval (default: daily at 09:00 UTC). The schedule is created on app startup when `settings.meridian_portfolio_enabled=True`.

15. **Portfolio review results are persisted.** Results are stored in a `portfolio_reviews` DB table with: id, reviewed_at, overall_health, flags (JSON), metrics (JSON), recommendations (JSON). Alembic migration creates the table.

16. **Portfolio review results are visible in Admin UI.** A new Admin UI page at `/admin/ui/portfolio-health` displays the latest review results: overall health indicator, flag list with severity, recommendations, and trend over last 7 reviews.

17. **Portfolio review posts to GitHub.** If `settings.meridian_portfolio_github_issue=True`, the review creates or updates a pinned issue in a configurable repo (e.g., `thestudio-meta`) with the health report in markdown format. Issue title: `[Meridian] Portfolio Health Review — {date}`.

#### Configuration

18. **Meridian portfolio review is feature-flagged.** `settings.meridian_portfolio_enabled: bool = False`. When disabled, no schedule is created and no reviews run.

19. **Health thresholds are configurable.** `settings.meridian_thresholds` with defaults: `blocked_ratio=0.20`, `high_risk_concurrent=3`, `review_stale_hours=48`, `repo_concentration=0.50`, `failure_rate=0.30`, `queued_stale_days=7`.

### 4b. Top Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| GitHub Projects v2 GraphQL API is complex and poorly documented | High | Medium — integration takes longer | Start with minimal field set (Status only). Add fields incrementally. Use GitHub's GraphQL Explorer to validate queries. |
| GraphQL API rate limits hit during sync | Medium | Low — sync is best-effort | Batch updates. Cache project/field IDs. Retry with backoff. Sync failures don't block the pipeline. |
| Projects v2 not configured on target repos | High | Low — feature is opt-in | Feature flag. Compliance check warns but doesn't block (unless Execute tier). |
| Portfolio review flags are noisy (too many warnings) | Medium | Medium — review becomes ignored | Configurable thresholds. Start conservative (high thresholds). Tune based on real data. |
| Portfolio snapshot is stale (board updated between collection and review) | Low | Low — advisory, not a gate | Snapshot timestamp included in output. Review acknowledges point-in-time nature. |

## 5. Constraints & Non-Goals

### Constraints

- **Projects v2 sync is best-effort.** Sync failures produce warnings, not pipeline failures. The pipeline must work without Projects v2.
- **Publisher remains the only GitHub writer.** Projects v2 field updates are made by activities called from the workflow, consistent with Publisher-only-writes principle. The Meridian portfolio agent reads only.
- **GraphQL, not REST.** GitHub Projects v2 requires the GraphQL API. The existing REST-based GitHub client is not used for project operations.
- **Feature-flagged, off by default.** Both Projects v2 sync and Meridian portfolio review are opt-in.
- **Meridian portfolio review is advisory.** It produces reports and flags. It does not block tasks, reject plans, or modify pipeline behavior. It's a notification, not a gate.
- **Python 3.12+, existing dependencies.** `httpx` for GraphQL calls (already in deps). No new dependencies.

### Non-Goals

- **Not building a custom project board UI.** The Admin UI gets a health dashboard page. The actual project board is GitHub's native Projects v2 UI.
- **Not bidirectional sync.** Changes made in the GitHub Projects v2 UI are not propagated back to TheStudio. The pipeline is the source of truth for TaskPacket status; Projects v2 is a read-only view (from GitHub's perspective, TheStudio writes to it).
- **Not replacing the Admin UI.** Projects v2 supplements the Admin UI with a GitHub-native view. The Admin UI remains the authoritative operational console.
- **Not implementing all spec'd automations in Sprint 1.** The architecture spec lists workflow automations (label-triggered status changes). Sprint 1 delivers status sync. Automation rules are Sprint 2.
- **Not adding Meridian as a pipeline gate.** Portfolio review is periodic and advisory. Per-TaskPacket plan review is Epic 28 (Preflight), a separate persona.
- **Not training a custom model.** Portfolio review uses the standard Model Gateway with a well-crafted system prompt.

## 6. Stakeholders & Roles

| Role | Who | Responsibility |
|------|-----|----------------|
| Epic Owner | Primary Developer | Accepts scope, reviews AC |
| Tech Lead | Primary Developer | Owns GraphQL integration, Meridian agent, scheduling |
| QA | Primary Developer | Validates sync accuracy, review quality |
| Saga | Epic Creator | Authored this epic |
| Meridian | VP Success | Reviews this epic before commit |

## 7. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Projects v2 sync accuracy | 100% of PUBLISHED tasks have correct Status=Done on board | Query project board after each publish, compare to TaskPacket status |
| Sync latency | < 5 seconds from status transition to board update | Span duration for `update_project_status_activity` p95 |
| Compliance check real | `_check_projects_v2()` returns real pass/fail, not stub | Compliance scorecard shows actual configuration status |
| Portfolio review runs | 100% of scheduled reviews execute successfully | Temporal schedule execution history — zero missed schedules over rolling 7-day window |
| Flag volume trend | Decreasing or stable flag count over rolling 4-week window | Automated: compare `portfolio_reviews.flags` JSON array length across consecutive reviews. Rising trend indicates systemic issues not being addressed. |
| Review completion rate | 100% of reviews produce a valid `PortfolioReviewOutput` | Automated: `portfolio_reviews` rows with non-null `overall_health` / total scheduled runs |
| Sync coverage | > 95% of active TaskPackets have a corresponding Projects v2 item | Automated: count of TaskPackets in non-terminal status with a project item ID / total non-terminal TaskPackets. Requires adding `project_item_id` field to TaskPacket or a mapping table. |

## 8. Context & Assumptions

### Systems Affected

| System | Impact |
|--------|--------|
| `src/github/__init__.py` | **New** — Package for GitHub API clients |
| `src/github/projects_client.py` | **New** — Projects v2 GraphQL client |
| `src/github/projects_mapping.py` | **New** — Status field mappings |
| `src/meridian/__init__.py` | **New** — Package |
| `src/meridian/portfolio_config.py` | **New** — Meridian portfolio agent config |
| `src/meridian/portfolio_collector.py` | **New** — Board state collector |
| `src/meridian/portfolio_workflow.py` | **New** — Temporal scheduled workflow |
| `src/publisher/publisher.py` | **Modified** — Add Projects v2 status update |
| `src/workflow/pipeline.py` | **Modified** — Add `update_project_status_activity` calls |
| `src/workflow/activities.py` | **Modified** — Add project status and portfolio review activities |
| `src/compliance/checker.py` | **Modified** — Implement `_check_projects_v2()` |
| `src/admin/compliance_scorecard.py` | **Modified** — Show real Projects v2 status |
| `src/admin/ui_router.py` | **Modified** — Add portfolio health page |
| `src/settings.py` | **Modified** — Add Projects v2 and Meridian settings |
| `src/observability/conventions.py` | **Modified** — Add project sync and portfolio review spans |
| `alembic/versions/` | **New** — Migration for `portfolio_reviews` table |

### Assumptions

1. **GitHub App has Projects v2 permissions.** The `project` scope (read:project, write:project) is required. Existing GitHub App installations may need permission updates.
2. **GraphQL API is stable.** GitHub Projects v2 GraphQL API is GA. The `ProjectV2` type and field mutation APIs are documented and supported.
3. **One project per organization.** TheStudio uses a single GitHub Project as the unified board across repos. Multi-project support is future work.
4. **Temporal schedules are available.** The Temporal server supports scheduled workflows. This is a standard Temporal feature available in the current deployment.
5. **The Admin UI template system (HTMX) supports the health dashboard.** The existing Admin UI uses HTMX for dynamic content. The portfolio health page follows the same pattern.

### Dependencies

| Dependency | Type | Owner | Status | Required By |
|------------|------|-------|--------|-------------|
| GitHub App `project` scope (read:project, write:project) | Infrastructure | Primary Developer | **Action required** — verify current App permissions, update if needed. **Gating task: Story 29.0 must complete before any Sprint 1 work begins.** | Story 29.0 (Day 1 of Sprint 1) |
| GitHub Projects v2 GraphQL API reference | Knowledge | Primary Developer | Available — [GitHub docs: ProjectV2](https://docs.github.com/en/graphql/reference/objects#projectv2). Key types: `ProjectV2`, `ProjectV2Item`, `ProjectV2FieldValue`. Key mutation: `updateProjectV2ItemFieldValue`. | Story 29.1 |
| Epic 15 (Real Repo Onboarding) | Soft scheduling | Primary Developer | In Progress | Not required — Sprint 1 validates with synthetic project data. Real-repo data improves Sprint 2 portfolio review quality but is not blocking. |
| Existing REST `GitHubClient` (`src/publisher/github_client.py`) | Reference only | — | Complete | Note: `ProjectsV2Client` uses a separate GraphQL httpx client path (`https://api.github.com/graphql`), not the existing REST client. |

- **Downstream unblocks:** GitHub-native visibility for stakeholders. Compliance checker accuracy for Execute tier promotion. Portfolio-level health monitoring.

---

## Story Map

### Sprint 1: Projects v2 Core Sync

| # | Story | Size | Value | Files |
|---|-------|------|-------|-------|
| 29.0 | **Verify GitHub App Permissions** | XS | **Gating** — all Sprint 1 work blocked until this completes | None (infrastructure verification). Verify GitHub App has `project` scope (read:project, write:project). Update App permissions if needed. Confirm with a test GraphQL query (`query { viewer { login } }` against `https://api.github.com/graphql`). |
| 29.1 | **Projects v2 GraphQL Client** | M | Foundation — all sync depends on this | `src/github/projects_client.py`, `src/github/projects_mapping.py` |
| 29.2 | **Pipeline Status Sync Activity** | M | Status transitions reflected on board. Includes adding `project_item_id` field to TaskPacket (or mapping table) for sync coverage tracking (see Success Metric: Sync coverage). | `src/workflow/activities.py`, `src/workflow/pipeline.py`, `src/settings.py`, `src/models/task_packet.py` (new field), migration |
| 29.3 | **Publisher Projects v2 Integration** | S | Published tasks show as Done | `src/publisher/publisher.py` |
| 29.4 | **Compliance Checker Implementation** | S | Real pass/fail replaces stub | `src/compliance/checker.py`, `src/admin/compliance_scorecard.py` |

### Sprint 2: Meridian Portfolio Review

| # | Story | Size | Value | Files |
|---|-------|------|-------|-------|
| 29.5 | **Portfolio Data Collector** | M | Reads board state via GraphQL | `src/meridian/portfolio_collector.py` |
| 29.6 | **Meridian Portfolio Review Agent** | M | Evaluates health, produces flags | `src/meridian/portfolio_config.py` |
| 29.7 | **Scheduled Review Workflow** | M | Runs on Temporal schedule, persists results | `src/meridian/portfolio_workflow.py`, migration |
| 29.8 | **Admin UI Health Dashboard** | M | Visualizes review results | `src/admin/ui_router.py`, templates |
| 29.9 | **GitHub Issue Health Report (Optional)** | S | Posts review to pinned issue | `src/meridian/portfolio_config.py` |

---

## Persona Update

This epic extends the Meridian persona to operate at two levels:

| Level | Trigger | Scope | Output |
|-------|---------|-------|--------|
| **Epic/Plan Review** (existing) | Manual, pre-commit | Single epic or plan | Pass/fail + gaps |
| **Portfolio Review** (new, this epic) | Scheduled, periodic | All active work across repos | Health report + flags |

The TEAM.md persona chain should be updated to reflect:

```
1. Strategy / OKRs
2. Saga → Epic
3. Meridian → Epic review (existing)
4. Helm → Plan
5. Meridian → Plan review (existing)
6. Execution (pipeline)
7. Meridian → Portfolio review (new — periodic, advisory)
8. Outcome feedback
```

---

## Meridian Review Status

### Round 1: Conditional Pass (2026-03-17)

**Verdict:** 5/7 PASS, 2 GAP. Strong epic with honest narrative and concrete ACs. Compliance stub claim verified against actual source.

| # | Question | Verdict |
|---|----------|---------|
| 1 | Goal specific enough to test? | PASS |
| 2 | AC testable at epic scale? | PASS |
| 3 | Non-goals explicit? | PASS |
| 4 | Dependencies with owners/dates? | GAP |
| 5 | Success metrics measurable? | GAP |
| 6 | AI agent can implement without guessing? | CONDITIONAL PASS |
| 7 | Narrative compelling? | PASS |

**Gaps identified and resolved:**

| # | Issue | Resolution |
|---|-------|------------|
| 1 | No dependencies table. GitHub App permissions need owner + date. Epic 15 validation strategy unclear. | **Resolved** — Dependencies table added with 4 entries: App permissions (action required), GraphQL reference (available), Epic 15 (soft scheduling), REST client (reference only). Sprint 1 validates with synthetic data. |
| 2 | 3 of 7 success metrics unmeasurable: "actionable flags," "false flag rate," "board adoption" lack tracking mechanisms. | **Resolved** — Replaced with automatically observable metrics: flag volume trend (DB query), review completion rate (DB query), sync coverage (TaskPacket-to-project-item ratio). |
| 3 | GraphQL query structure not provided. Multi-step mutation pattern (`ProjectV2` → field IDs → option IDs → `updateProjectV2ItemFieldValue`) is non-obvious. | **Resolved** — GraphQL types, mutations, and implementation note added to References section. Links to GitHub docs included. |
| 4 | AC 11 thresholds unclear if defaults or examples. | **Resolved** — Clarified as tested defaults shipped in `settings.meridian_thresholds`, configurable per deployment. |

**Should fix (non-blocking, addressed):**
- Note that `ProjectsV2Client` uses separate GraphQL httpx path — added to dependencies table.
- Health dashboard visualization format — deferred to story-level detail (acceptable for epic scope).

**Status: All gaps resolved. Ready to commit.**

---

## Sprint 2 Delivery Notes (2026-03-18)

**Sprint 2: Meridian Portfolio Review — COMPLETE (60 tests)**

| # | Story | Status | Tests | Key Deliverables |
|---|-------|--------|-------|------------------|
| 29.5 | Portfolio Data Collector | **Complete** | 17 | `src/meridian/portfolio_collector.py` — `PortfolioSnapshot` with items grouped by repo/status, `_parse_item()`, `_extract_field_value()`, OTel span |
| 29.6 | Meridian Portfolio Review Agent | **Complete** | 26 | `src/meridian/portfolio_config.py` — `MERIDIAN_PORTFOLIO_CONFIG` (AgentRunner), `PortfolioReviewOutput` model (AC 12), 6 health checks in `_portfolio_fallback()` (AC 11), `format_health_report_markdown()` |
| 29.7 | Scheduled Review Workflow | **Complete** | 13 | `src/meridian/portfolio_workflow.py` — Temporal `MeridianPortfolioReviewWorkflow`, `portfolio_review_activity()`, `_persist_review()`, DB migration 024 (`portfolio_reviews` table), `PortfolioReviewRow` ORM model |
| 29.8 | Admin UI Health Dashboard | **Complete** | 4 | `/admin/ui/portfolio-health` page + HTMX partial, health indicator (green/yellow/red), metrics grid, flags with severity cards, 7-review trend table, nav link |
| 29.9 | GitHub Issue Health Report | **Complete** | (in 29.6/29.7) | `_post_github_issue()` in workflow, `format_health_report_markdown()` in config, feature-flagged via `meridian_portfolio_github_issue` |

**Health Checks Implemented (AC 11):**
1. Throughput — blocked ratio >20% of active items
2. Risk Concentration — >3 high-risk items in progress concurrently
3. Approval Bottleneck — items stalled in review
4. Repo Balance — >50% of active items in a single repo
5. Failure Rate — >30% of completed items failed
6. Stale Items — items queued >7 days

**New Files Created:**
- `src/meridian/__init__.py`, `portfolio_collector.py`, `portfolio_config.py`, `portfolio_workflow.py`
- `src/db/migrations/024_portfolio_reviews.py`
- `src/admin/templates/portfolio_health.html`, `partials/portfolio_health_content.html`
- `tests/meridian/__init__.py`, `test_portfolio_collector.py`, `test_portfolio_config.py`, `test_portfolio_workflow.py`, `test_admin_portfolio_health.py`

**Combined Epic 29 Totals:**
- Sprint 1: 63 tests (GraphQL client, status mapping, pipeline sync, compliance checker)
- Sprint 2: 60 tests (portfolio collector, review agent, workflow, admin UI, issue report)
- **Total: 123 tests across `tests/github/` and `tests/meridian/`**
