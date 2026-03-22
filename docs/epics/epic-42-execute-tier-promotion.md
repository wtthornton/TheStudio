# Epic 42: Execute Tier Promotion -- Auto-Merge with Human Gates

> **Status:** DRAFT -- Awaiting Meridian Review
> **Epic Owner:** Primary Developer
> **Duration:** 3-4 weeks (2 slices, 13 stories)
> **Created:** 2026-03-22
> **Capacity:** Solo developer, 30 hours/week

---

## 1. Title

**Auto-Merged PRs Are Safe, Monitored, and Self-Correcting Through Execute Tier Promotion**

---

## 2. Narrative

TheStudio has three trust tiers: Observe (report only), Suggest (draft PR), and Execute (auto-merge). The first two are live. The third is a lie.

Here is what exists today. Epic 22 wired the Publisher to differentiate Execute from Suggest. The `_should_enable_auto_merge()` function checks five gates -- Execute tier, AUTO_MERGE mode, verification passed, QA passed, human approval received -- and calls GitHub's GraphQL `enablePullRequestAutoMerge` mutation. Epic 37 delivered the trust tier rule engine: operators define rules that evaluate TaskPacket metadata (category, complexity, lines changed, cost, file paths) and assign a task-level trust tier (observe/suggest/execute). Safety bounds cap the tier at SUGGEST when line counts exceed limits, loopbacks pile up, or repos match mandatory-review patterns. The `task_trust_tier` field lives on TaskPacketRow, assigned at pipeline start by a Temporal activity.

Here is what does not exist. The Publisher's `publish()` function takes a `repo_tier: RepoTier` parameter -- a repo-level setting from `repo_profile.py`. It does not read `task_trust_tier` from the TaskPacket. So even when the rule engine assigns `execute` to a task, the Publisher ignores it. No task has ever been auto-merged through the pipeline because the wiring between task-level trust and Publisher behavior is broken.

Worse, there is no post-merge monitoring. If an auto-merged PR gets reverted, TheStudio does not know. If the merged code creates a follow-up issue within 24 hours, TheStudio does not learn. The outcome ingestor consumes verification and QA signals but has no concept of merge outcomes. Without feedback, the system cannot self-correct. It would auto-merge with the confidence of a system that has never been wrong, because it has never checked.

And the dashboard has no visibility into auto-merged tasks. The trust tier rule engine has no concept of historical outcomes. A rule that promotes bug fixes to Execute tier cannot know that the last three auto-merged bug fixes were all reverted.

This epic closes three gaps simultaneously:

1. **Publisher reads task_trust_tier.** The task-level tier from the rule engine becomes the source of truth for Publisher behavior, replacing the repo-level `repo_tier` parameter for tier branching. Repo-level settings remain as a ceiling -- a repo at SUGGEST tier cannot be overridden to EXECUTE by a task-level rule.

2. **Post-merge monitoring.** A new outcome signal type (`merge_succeeded`, `merge_reverted`, `post_merge_issue`) feeds the outcome ingestor. A lightweight poll watches merged PRs for reverts and follow-up issues within a configurable window (default: 24 hours). Revert detection produces a negative reputation indicator.

3. **Automatic tier demotion on failure.** When a revert is detected for an auto-merged PR, the trust tier rule that matched is flagged, the task category's success rate is updated, and if the success rate drops below a configurable threshold (default: 90%), the rule is automatically deactivated. The operator is notified. The system self-corrects.

Why now: Epic 37 delivered the rule engine and safety bounds. Epic 22 delivered the auto-merge plumbing. The only thing between the current state and working auto-merge is the wiring, the monitoring, and the courage to trust the system -- which requires the ability to detect and correct mistakes.

---

## 3. References

| Type | Reference | Relevance |
|------|-----------|-----------|
| Source | `src/publisher/publisher.py` | Publisher with `_should_enable_auto_merge()`, `_try_enable_auto_merge()`, five-gate safety check. Uses `repo_tier` parameter. |
| Source | `src/publisher/github_client.py` | `enable_auto_merge()` via GraphQL, `mark_ready_for_review()` |
| Source | `src/dashboard/trust_engine.py` | `evaluate_trust_tier()` -- rule engine that assigns task-level tier with safety bounds |
| Source | `src/dashboard/models/trust_config.py` | `TrustTierRuleRow`, `TrustSafetyBoundsRow`, `SafeBoundsRead`, CRUD functions |
| Source | `src/models/taskpacket.py` | `TaskPacketRow.task_trust_tier` field (TaskTrustTier enum: observe/suggest/execute) |
| Source | `src/admin/merge_mode.py` | `MergeMode` enum (DRAFT_ONLY, REQUIRE_REVIEW, AUTO_MERGE), per-repo in-memory store |
| Source | `src/repo/repo_profile.py` | `RepoTier` enum (OBSERVE, SUGGEST, EXECUTE), `merge_method` column |
| Source | `src/reputation/engine.py` | `update_weight()`, `AsyncReputationEngine`, decay/drift/tier computation |
| Source | `src/outcome/ingestor.py` | `ingest_signal()`, `SignalEvent` enum, `ReputationIndicator` model |
| Source | `src/outcome/models.py` | `SignalEvent`, `OutcomeType`, `ReputationIndicator` -- currently only V+QA signals |
| Source | `src/workflow/activities.py` | `assign_trust_tier` activity -- calls `evaluate_trust_tier()` at pipeline start |
| Epic | `docs/epics/epic-22-execute-tier.md` | Execute tier end-to-end: Publisher branching, GraphQL auto-merge, compliance gate |
| Epic | `docs/epics/epic-37-phase3-interactive-controls.md` | Trust tier rule engine, safety bounds, task-level trust tier on TaskPacket |
| Architecture | `thestudioarc/15-system-runtime-flow.md` | Defines Execute tier behavior and promotion sequence |
| Architecture | `thestudioarc/12-outcome-ingestor.md` | Outcome signal processing, quarantine, reputation indicators |
| OKRs | `thestudioarc/personas/MERIDIAN-TEAM-REVIEW-AND-OKRS.md` | Autonomous operation KR |

---

## 4. Acceptance Criteria

### AC1: Publisher Uses Task-Level Trust Tier for Behavior Branching

The Publisher reads `task_trust_tier` from the TaskPacket to determine tier behavior (observe = report only, suggest = draft PR marked ready-for-review, execute = auto-merge). The repo-level `RepoTier` acts as a ceiling: if the repo is at SUGGEST, a task-level `execute` tier is downgraded to SUGGEST. The five-gate auto-merge check from Epic 22 (`_should_enable_auto_merge()`) remains intact -- this change only affects which tier value feeds into that function. When `task_trust_tier` is null (legacy TaskPackets), the Publisher falls back to `repo_tier`.

**Testable:** A test creates a TaskPacket with `task_trust_tier = execute` on a repo with `RepoTier.EXECUTE` and `MergeMode.AUTO_MERGE`, passes all gates, and verifies `auto_merge_enabled = True` on the `PublishResult`. A second test sets `task_trust_tier = execute` but `RepoTier = SUGGEST` and verifies auto-merge is NOT enabled (ceiling enforcement).

### AC2: Pre-Merge Safety Checks Enforce Safety Bounds at Publish Time

Before enabling auto-merge, the Publisher re-evaluates safety bounds (max_auto_merge_lines, max_auto_merge_cost, max_loopbacks, mandatory_review_patterns) against the current TaskPacket state. This catches cases where the task was assigned Execute tier at pipeline start but accumulated loopbacks or grew in diff size during implementation. If any safety bound is violated, auto-merge is blocked and the PR is published as ready-for-review (Suggest behavior) instead. The safety check result is logged with the correlation_id.

**Testable:** A test creates a TaskPacket assigned `execute` tier, sets its `loopback_count` above `max_loopbacks`, and verifies auto-merge is blocked. The `PublishResult` shows `auto_merge_enabled = False` and `marked_ready = True`.

### AC3: Post-Merge Monitoring Detects Reverts and Follow-Up Issues

New outcome signal types (`MERGE_SUCCEEDED`, `MERGE_REVERTED`, `POST_MERGE_ISSUE`) are added to `SignalEvent`. A polling-based monitor checks merged PRs for: (a) revert commits on the default branch that reference the PR number within a configurable window (default: 24h), and (b) new issues opened that reference the PR within the same window. The monitor is implemented as a Temporal activity that runs after publish for Execute-tier tasks. Each detected revert or issue produces a `ReputationIndicator` with negative weight.

**Testable:** A test simulates a merged PR, mocks a revert commit detected by the monitor, and verifies that a `MERGE_REVERTED` signal is produced and an `OutcomeSignal` record is persisted. A second test verifies the 24h window is respected (events outside the window are ignored).

### AC4: Automatic Rule Deactivation on Sustained Failure

When a `MERGE_REVERTED` signal is processed for an auto-merged TaskPacket, the system looks up the trust tier rule that matched (stored on the TaskPacket or in the evaluation audit log). The rule's success rate is updated. If the success rate drops below a configurable threshold (default: 90% over the last 20 auto-merges under that rule), the rule is automatically deactivated (`active = false`) and a notification is generated. The rule can be manually reactivated by the operator after investigation.

**Testable:** A test creates a rule that assigns Execute tier, processes 20 merge outcomes (18 success, 2 reverts = 90%), then processes a 21st outcome (revert, dropping to 85.7%), and verifies the rule is deactivated. A second test at exactly 90% verifies the rule stays active.

### AC5: Dashboard Shows Auto-Merge Outcomes and Rule Health

A new dashboard section displays: (a) a list of auto-merged TaskPackets with their outcome (merged, reverted, issue detected), (b) per-rule success rates for rules that assign Execute tier, (c) deactivated rules with the reason and timestamp. Data is served by new API endpoints under `/api/v1/dashboard/auto-merge/`. The list supports time-range filtering (1d, 7d, 30d).

**Testable:** The API endpoint `/api/v1/dashboard/auto-merge/outcomes` returns a JSON list of auto-merge outcomes. The endpoint `/api/v1/dashboard/auto-merge/rule-health` returns per-rule success rates. Both accept `period` query parameters.

### AC6: Gradual Rollout via Rule Targeting

Auto-merge is not an all-or-nothing switch. Operators use the existing rule engine to target specific task categories, complexity bands, or repos for Execute tier. A "dry run" mode is available on individual rules: when dry_run is enabled, the rule engine evaluates the rule and logs what would have happened, but assigns SUGGEST instead of EXECUTE. This lets operators validate rule behavior before going live. The dry run flag is a boolean column on `TrustTierRuleRow`.

**Testable:** A test creates a rule with `dry_run = true` that matches a TaskPacket. The evaluation result shows `tier = SUGGEST` but the audit log records `raw_tier = EXECUTE` and `dry_run = true`. Disabling dry_run and re-evaluating returns `tier = EXECUTE`.

### 4b. Top Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Auto-merging bad code** | Broken main branch, production incidents | Five-gate safety check (Epic 22) + real-time safety bound re-check at publish time (AC2) + post-merge revert detection (AC3) + automatic rule deactivation (AC4). Defense in depth. |
| **Revert detection timing** | Late detection means more damage from bad merges | 24h polling window with 15-minute check intervals. For high-confidence repos, the window can be shortened. First check runs 30 minutes after merge. |
| **False confidence from small sample sizes** | Rule promoted to Execute with 3 successes, then fails | Rule health requires a minimum of 20 auto-merges before the success rate threshold activates. Below 20 samples, the rule stays active but dashboard shows "insufficient data" warning. |
| **Repo-level ceiling vs task-level tier confusion** | Operator sets task rule to Execute but repo is at Suggest, wonders why it is not auto-merging | Dashboard explicitly shows both tiers and which one is the effective ceiling. Log messages include both values. |
| **Polling load on GitHub API** | Rate limit exhaustion from checking merged PRs | Batch PR checks per repo (one API call returns multiple PRs). Exponential backoff on rate limits. Only poll repos with recent Execute-tier merges. |

---

## 5. Constraints and Non-Goals

### Constraints

- Publisher remains the single writer to GitHub. No other component may call auto-merge or merge APIs.
- The five-gate auto-merge check from Epic 22 (`_should_enable_auto_merge()`) is not weakened. This epic adds the task-tier wiring and post-merge feedback loop around it.
- Auto-merge only occurs on repos that have explicitly opted in via `MergeMode.AUTO_MERGE` in their repo profile. There is no implicit opt-in.
- Repo-level `RepoTier` is a hard ceiling. A task-level Execute assignment on a SUGGEST repo results in SUGGEST behavior. This is not configurable.
- Database migrations must be backward-compatible (nullable columns with defaults, additive enum values).
- Post-merge polling uses the GitHub REST API with the same installation token. No additional credentials required.

### Non-Goals

- **CI/CD integration** -- This epic does not integrate with CI status checks. GitHub's own branch protection rules handle CI gating. That integration is future work.
- **Multi-user approval workflows** -- This epic uses the single-approval gate from Epic 21. RBAC-based multi-approver workflows are a separate concern.
- **Merge queue integration** -- GitHub merge queues are a separate feature. This epic uses standard auto-merge only.
- **Real-time revert detection via webhooks** -- This epic uses polling. Webhook-based revert detection (faster but more complex) is a follow-on optimization.
- **Cross-repo auto-merge policies** -- Each repo is configured independently. Fleet-wide policy management is deferred.
- **Automatic rule creation** -- The system deactivates failing rules but does not create new ones. Rule creation remains a manual operator action.

---

## 6. Stakeholders and Roles

| Role | Who | Responsibility |
|------|-----|----------------|
| Epic Owner / Tech Lead / QA | Primary Developer (solo) | All implementation, testing, scope decisions |

---

## 7. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Task-level trust tier drives Publisher behavior | 100% of new TaskPackets | Unit test: `publish()` reads `task_trust_tier` and applies ceiling logic correctly |
| Auto-merge success rate (no reverts within 24h) | > 95% for rules at threshold (rolling 30-day window, minimum 20 auto-merges before evaluation begins) | Query `auto_merge_outcomes` table: count(reverted) / count(total) grouped by rule_id over trailing 30 days |
| Revert detection latency | p95 < 60 minutes from revert commit to signal | p95 of timestamp delta between revert commit `authored_date` and `MERGE_REVERTED` signal `timestamp` |
| Failing rules auto-deactivated | 100% of rules below threshold | Query `trust_tier_rules` where `active = false` and `deactivation_reason IS NOT NULL` |
| Dashboard displays accurate rule health | All Execute-tier rules shown with correct success rates | API test: `/api/v1/dashboard/auto-merge/rule-health` returns correct percentages for known test data |
| Dry-run rules produce audit data without affecting behavior | 100% of dry-run evaluations logged as SUGGEST | Unit test: dry_run=true rule evaluation returns SUGGEST with raw_tier=EXECUTE in result |

---

## 8. Context and Assumptions

### Business Rules

- Execute tier is earned, not default. A task reaches Execute only when: (a) the repo is at Execute tier, (b) the rule engine assigns Execute based on task metadata, (c) safety bounds are not violated, (d) all five gates pass (Execute tier + AUTO_MERGE mode + V pass + QA pass + human approval).
- Auto-merge is reversible at three levels: (1) operator deactivates the rule, (2) operator changes repo merge mode away from AUTO_MERGE, (3) operator demotes repo from Execute tier.
- A reverted auto-merge is a trust failure. The system treats it as a signal to tighten, not loosen.
- Post-merge monitoring is advisory for the first version. It produces signals and deactivates rules, but does not automatically roll back code (that is GitHub's revert workflow, done by humans).

### Dependencies

- **Epic 22 (Execute Tier End-to-End)** -- COMPLETE. Publisher has auto-merge logic, GitHubClient has `enable_auto_merge()`, compliance gate has Execute policy. This epic builds on all of it.
- **Epic 37 (Phase 3 Interactive Controls)** -- COMPLETE. Trust tier rule engine, safety bounds, `task_trust_tier` on TaskPacket, `evaluate_trust_tier()` activity in the Temporal workflow. This epic consumes the rule engine output.
- **Epic 21 (Human Approval Wait States)** -- Must be complete for the approval gate in the five-gate check. The `approval_received` parameter on `publish()` comes from the Temporal approval signal.
- **GitHub API** -- Post-merge monitoring requires `GET /repos/{owner}/{repo}/pulls/{pr_number}` (merge status), `GET /repos/{owner}/{repo}/commits` (revert detection), and `GET /repos/{owner}/{repo}/issues` (follow-up detection). All available with current installation token permissions.

### Systems Affected

| System | Impact |
|--------|--------|
| `src/publisher/publisher.py` | Read `task_trust_tier` from TaskPacket, add ceiling enforcement, add pre-publish safety bound re-check |
| `src/outcome/models.py` | New `SignalEvent` values: `MERGE_SUCCEEDED`, `MERGE_REVERTED`, `POST_MERGE_ISSUE` |
| `src/outcome/ingestor.py` | Handle new merge signal types, produce reputation indicators for merge outcomes |
| `src/dashboard/trust_engine.py` | Return matched rule ID in evaluation result (already present in `EvaluationResult.matched_rule_id`) |
| `src/dashboard/models/trust_config.py` | Add `dry_run` boolean column to `TrustTierRuleRow`, add rule success tracking columns |
| `src/workflow/activities.py` | New `monitor_post_merge` activity for revert/issue detection |
| `src/publisher/github_client.py` | New methods: `get_pr_merge_status()`, `check_for_reverts()`, `check_for_linked_issues()` |
| `src/db/migrations/` | New migration for `dry_run` column, auto-merge outcome tracking table, rule success columns |
| `src/dashboard/` | New API endpoints for auto-merge outcomes and rule health |
| `src/models/taskpacket.py` | New fields: `auto_merged`, `matched_rule_id` (for post-merge tracking back to the rule) |

### Assumptions

- The existing `EvaluationResult.matched_rule_id` from `evaluate_trust_tier()` is not currently persisted on `TaskPacketRow`; must be added by Story 42.3.
- GitHub's REST API reliably surfaces revert commits within the polling window. Reverts created via GitHub's "Revert" button include a standardized commit message pattern (`Revert "..."`) that can be matched.
- The outcome ingestor can be extended with new `SignalEvent` types without breaking existing JetStream consumers (additive change to the enum).
- The trust tier rule engine's `list_rules()` function performs well enough for per-publish evaluation (currently loads all active rules; for v1 this is acceptable with < 100 rules).
- Post-merge monitoring runs as a Temporal activity with a 24h duration, checking at 15-minute intervals. This is well within Temporal's activity timeout capabilities.

---

## Story Map

### Slice 1: MVP -- Publisher Wiring + Safety Checks + Auto-Merge (Risk Reduction)

_Goal: A TaskPacket with `task_trust_tier = execute` actually auto-merges when all gates pass. Safety bounds are re-checked at publish time. Dry-run mode lets operators validate rules before going live._

| # | Story | AC | Est | Files to modify/create |
|---|-------|----|-----|----------------------|
| 42.1 | **Publisher reads task_trust_tier from TaskPacket** -- Modify `publish()` to read `task_trust_tier` from the loaded TaskPacket and use it for tier branching. Apply repo-level `RepoTier` as ceiling (min of repo tier and task tier). Fall back to `repo_tier` param when `task_trust_tier` is null. **Note:** Reuse `_cap_tier()` from `src/dashboard/trust_engine.py` for the ceiling comparison between `RepoTier` and `TaskTrustTier` -- import it or extract to a shared utility rather than re-implementing min-tier logic. | AC1 | 3h | `src/publisher/publisher.py` |
| 42.2 | **Pre-publish safety bound re-check** -- Before enabling auto-merge, re-evaluate safety bounds against current TaskPacket state (loopback_count, diff_lines from scope, repo against mandatory_review_patterns). If any bound is violated, downgrade to SUGGEST behavior. Log the override with correlation_id. **Note:** Publisher imports `get_safety_bounds` directly from `src/dashboard/models/trust_config.py`. `max_auto_merge_cost` is defined on `SafetyBoundsRow` but is NOT currently checked by the trust engine (`src/dashboard/trust_engine.py` omits it); this story must add the cost check to the publish-time re-evaluation so that tasks exceeding the cost cap are downgraded to SUGGEST. | AC2 | 3h | `src/publisher/publisher.py`, `src/dashboard/models/trust_config.py` (import `get_safety_bounds`) |
| 42.3 | **Add matched_rule_id and auto_merged fields to TaskPacket** -- Add `matched_rule_id: UUID | None` (the trust tier rule that matched) and `auto_merged: bool` (whether this task was actually auto-merged) to `TaskPacketRow`. Create migration. Persist `matched_rule_id` in the `assign_trust_tier` activity. Set `auto_merged` in the Publisher after successful auto-merge enablement. | AC1, AC4 | 2h | `src/models/taskpacket.py`, `src/workflow/activities.py`, `src/publisher/publisher.py`, `src/db/migrations/` |
| 42.4 | **Add dry_run flag to TrustTierRuleRow** -- Add `dry_run: bool = false` column to `TrustTierRuleRow` with migration. Update `evaluate_trust_tier()`: when the matched rule has `dry_run = true`, return `tier = SUGGEST` but set `raw_tier` to the rule's assigned tier and add `dry_run = true` to the `EvaluationResult`. Add `dry_run: bool = False` as a keyword argument to `EvaluationResult.__init__()` (alongside the existing `raw_tier`, `matched_rule_id`, `safety_capped`, `reason` kwargs). Update CRUD schemas. | AC6 | 3h | `src/dashboard/models/trust_config.py`, `src/dashboard/trust_engine.py`, `src/db/migrations/` |
| 42.5 | **Unit tests for Publisher task-tier wiring** -- Tests covering: (a) task_trust_tier=execute + repo Execute + all gates = auto-merge, (b) task_trust_tier=execute + repo Suggest = no auto-merge (ceiling), (c) task_trust_tier=null = fallback to repo_tier, (d) safety bound violation at publish time = downgrade, (e) dry_run rule = SUGGEST behavior with EXECUTE audit trail. | AC1, AC2, AC6 | 4h | `tests/unit/test_publisher_task_tier.py` |
| 42.6 | **Integration test: end-to-end auto-merge with task tier** -- Test that calls `publish()` with a fully wired TaskPacket (task_trust_tier=execute, matched_rule_id set, repo at Execute, MergeMode.AUTO_MERGE, V+QA+approval passed) and verifies the full flow: safety re-check, auto-merge enabled, auto_merged flag set on TaskPacket. Uses mocked GitHubClient. | AC1, AC2 | 3h | `tests/integration/test_execute_tier_e2e.py` |

**Slice 1 Total: ~18h (1 week)**

### Slice 2: Full -- Post-Merge Monitoring + Auto-Demotion + Dashboard

_Goal: The system watches merged PRs for reverts, automatically deactivates failing rules, and provides dashboard visibility into auto-merge health._

| # | Story | AC | Est | Files to modify/create |
|---|-------|----|-----|----------------------|
| 42.7 | **Add merge outcome signal types** -- Add `MERGE_SUCCEEDED`, `MERGE_REVERTED`, `POST_MERGE_ISSUE` to `SignalEvent` enum. Add corresponding `OutcomeType` handling in the ingestor. Produce negative-weight `ReputationIndicator` for reverts (weight: -0.8) and post-merge issues (weight: -0.4). Produce positive-weight indicator for successful merges that survive the monitoring window (weight: +0.3). | AC3 | 3h | `src/outcome/models.py`, `src/outcome/ingestor.py` |
| 42.8 | **Post-merge monitor Temporal activity** -- New activity `monitor_post_merge` that: (a) waits 30 minutes after merge, (b) polls GitHub every 15 minutes for 24h, checking for revert commits and linked issues, (c) emits `MERGE_SUCCEEDED` if no problems found after window closes, or `MERGE_REVERTED`/`POST_MERGE_ISSUE` on detection. Add `check_for_reverts()` and `check_for_linked_issues()` to GitHubClient. | AC3 | 5h | `src/workflow/activities.py`, `src/publisher/github_client.py` |
| 42.9 | **Wire post-merge monitor into pipeline workflow** -- After `publish()` succeeds with `auto_merge_enabled = true`, schedule the `monitor_post_merge` activity as a detached workflow (does not block the main pipeline). Pass TaskPacket ID, PR number, repo, and merge timestamp. | AC3 | 2h | `src/workflow/pipeline.py` |
| 42.10 | **Auto-merge outcome tracking table** -- Create `auto_merge_outcomes` table: `id UUID PK`, `taskpacket_id UUID FK`, `rule_id UUID FK`, `pr_number INT`, `repo VARCHAR`, `merged_at TIMESTAMP`, `outcome VARCHAR` (succeeded/reverted/issue_detected), `detected_at TIMESTAMP NULL`, `revert_sha VARCHAR NULL`, `linked_issue_number INT NULL`. Create migration. Add CRUD functions. | AC4, AC5 | 3h | `src/db/migrations/`, `src/dashboard/models/auto_merge_outcomes.py` |
| 42.11 | **Rule success rate tracking and auto-deactivation** -- On each `MERGE_SUCCEEDED` or `MERGE_REVERTED` outcome, update the matched rule's success metrics. When a rule has >= 20 auto-merges and its success rate drops below the configurable threshold (default: 90%), set `active = false` and `deactivation_reason = "auto: success rate {rate}% below threshold {threshold}%"`. Generate a notification. | AC4 | 4h | `src/dashboard/models/trust_config.py`, `src/dashboard/trust_engine.py`, new `src/dashboard/rule_health.py` |
| 42.12 | **Dashboard API: auto-merge outcomes and rule health** -- Two new endpoints: `GET /api/v1/dashboard/auto-merge/outcomes?period=7d` returns paginated list of auto-merge outcomes with filters. `GET /api/v1/dashboard/auto-merge/rule-health` returns per-rule success rates, sample counts, and deactivation status. | AC5 | 3h | `src/dashboard/auto_merge_router.py`, `src/dashboard/app.py` (register router) |
| 42.13 | **Unit and integration tests for post-merge monitoring** -- Tests covering: (a) revert detection from GitHub commit data, (b) linked issue detection, (c) 24h window boundary enforcement, (d) rule auto-deactivation at threshold, (e) rule stays active at exactly threshold, (f) insufficient samples warning, (g) API endpoints return correct data. | AC3, AC4, AC5 | 4h | `tests/unit/test_post_merge_monitor.py`, `tests/unit/test_rule_health.py`, `tests/unit/test_auto_merge_api.py` |

**Slice 2 Total: ~24h (1.5 weeks)**

**Epic Total: ~42h (3-4 weeks at 30h/week)**

---

## Meridian Review Status

### Round 1: BLOCKERS FOUND

| # | Question | Status | Notes |
|---|----------|--------|-------|
| 1 | Is the goal statement specific enough to test against? | PASS | Title and narrative clearly scope three gaps: Publisher wiring, post-merge monitoring, auto-demotion. |
| 2 | Are acceptance criteria testable at epic scale? | PASS | All six ACs include concrete testable scenarios with expected outputs. |
| 3 | Are non-goals explicit? | PASS | Six non-goals are well-scoped (CI/CD, merge queue, webhooks, cross-repo, multi-approver, auto-rule creation). |
| 4 | Are dependencies identified with owners and dates? | PASS | Epic 21, 22, 37 dependencies identified with completion status. GitHub API requirements listed. |
| 5 | Are success metrics measurable with existing instrumentation? | BLOCKED | Auto-merge success rate lacked measurement window and minimum sample size. Revert detection latency used absolute instead of percentile. |
| 6 | Can an AI agent implement without guessing scope? | BLOCKED | Story 42.1 did not specify how to compute tier ceiling (reimplementing vs reusing `_cap_tier`). Story 42.2 did not clarify `max_auto_merge_cost` is unchecked by the trust engine and needs adding. Story 42.4 did not specify `dry_run` kwarg on `EvaluationResult.__init__()`. Section 8 assumption about `matched_rule_id` was ambiguous. |
| 7 | Are there red flags? | PASS | Defense-in-depth (five gates + safety re-check + monitoring + auto-deactivation) addresses the primary risk of auto-merging bad code. |

**Blockers found (4):**

| # | Blocker | Resolution |
|---|---------|------------|
| B1 | Section 8 assumption about `matched_rule_id` was ambiguous ("already persisted or can be persisted") | Rewritten to: "is not currently persisted on `TaskPacketRow`; must be added by Story 42.3." |
| B2 | Auto-merge success rate metric had no measurement window or minimum sample size | Added: "rolling 30-day window, minimum 20 auto-merges before evaluation begins" |
| B3 | Revert detection latency used absolute threshold instead of percentile | Changed from "< 60 minutes" to "p95 < 60 minutes" |
| B4 | Stories 42.1, 42.2, 42.4 lacked implementation specifics for AI-implementability | 42.1: reuse `_cap_tier()` from trust_engine.py. 42.2: import `get_safety_bounds` directly, add `max_auto_merge_cost` check (not in trust engine today). 42.4: add `dry_run: bool = False` kwarg to `EvaluationResult.__init__()`. |

### Round 2: PASS

All four blockers resolved. Epic is AI-implementable without scope ambiguity.
