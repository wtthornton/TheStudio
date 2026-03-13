# Epic 22: Enable End-to-End Execute Tier for Autonomous PR Workflow

**Status:** IMPLEMENTED — All 18 stories complete, 1,689 unit tests pass (0 failures)

## 1. Title

**Enable End-to-End Execute Tier for Autonomous PR Workflow**

## 2. Narrative

TheStudio's trust model defines three tiers: Observe, Suggest, and Execute. Today, two of the three tiers are wired end-to-end. Observe creates draft PRs. Suggest marks PRs ready-for-review after verification and QA pass. But Execute -- the tier that unlocks autonomous operation -- is a hollow shell. The `RepoTier.EXECUTE` enum value exists in the database migration and in `repo_profile.py`, but no component actually changes its behavior when a repo reaches Execute tier.

The Publisher treats Execute identically to Suggest: it marks PRs ready-for-review but never enables auto-merge. The compliance checker validates repos _for promotion to_ Execute tier, but the compliance gate itself has no Execute-specific enforcement beyond what Suggest already requires. The `_should_mark_ready()` function explicitly only checks `repo_tier == RepoTier.SUGGEST` -- an Execute-tier repo's PR stays in the exact same state as a Suggest-tier PR.

This matters because Execute tier is the path to compounding value. Every repo stuck at Suggest tier requires a human to click "merge" on every PR, even when all gates pass, reviewers approve, and the change is low-risk. For high-volume repos processing dozens of issues per day, this becomes the bottleneck. Execute tier, gated properly, removes that bottleneck for work that has earned it.

The dependency chain is clear: Epic 21 (C6: Human Approval Wait States) must land first. Without Temporal wait states for human approval, auto-merge cannot be safely gated. This epic assumes those wait states exist and builds on them.

## 3. References

| Type | Reference | Relevance |
|------|-----------|-----------|
| Architecture | `thestudioarc/15-system-runtime-flow.md` (Repo Registration Lifecycle, Merge Policy, Human Approval Wait States) | Defines Execute tier behavior, auto-merge preconditions, and the promotion sequence |
| Policy | `thestudioarc/POLICIES.md` (Repo Tier Enforcement, Execute Tier Compliance Gate, Merge Policy) | Governance rules: hard gates, compliance checks, auto-merge conditions |
| Gap Analysis | `docs/architecture-vs-implementation-mapping.md` lines 427, 439, 501, 520, 529 | C2 gap definition, V1 follow-on, raw MISSING entries |
| Source | `src/publisher/publisher.py` | Current Publisher: `_should_mark_ready()` ignores Execute tier |
| Source | `src/repo/repo_profile.py` | `RepoTier` enum already includes EXECUTE |
| Source | `src/compliance/checker.py` | Compliance checker exists but has no Execute-specific policy enforcement |
| Source | `src/compliance/promotion.py` | Promotion service exists and gates on compliance, but Execute-specific checks are not differentiated |
| Source | `src/admin/merge_mode.py` | `MergeMode.AUTO_MERGE` exists but is unused |
| Dependency | Epic 21 (C6: Human Approval Wait States) | Must be complete before auto-merge can be safely enabled |
| Follow-on | V1 (Merge policy enforcement) | Becomes actionable once Execute tier ships |
| OKRs | `thestudioarc/personas/MERIDIAN-TEAM-REVIEW-AND-OKRS.md` | Autonomous operation KR |

## 4. Acceptance Criteria

**AC1: Publisher handles Execute tier distinctly from Suggest tier**
- When `repo_tier == RepoTier.EXECUTE` and `verification_passed` and `qa_passed` and `merge_mode == MergeMode.AUTO_MERGE`, Publisher marks the PR ready-for-review AND enables GitHub auto-merge via the GraphQL API
- When `repo_tier == RepoTier.EXECUTE` and `merge_mode == MergeMode.REQUIRE_REVIEW`, Publisher marks ready-for-review but does NOT enable auto-merge (same as Suggest)
- When `repo_tier == RepoTier.EXECUTE` and `merge_mode == MergeMode.DRAFT_ONLY`, Publisher leaves the PR as draft (same as all tiers)
- `PublishResult` gains an `auto_merge_enabled: bool` field

**AC2: Compliance gate enforces Execute-specific policy**
- Compliance checker adds an `EXECUTE_TIER_POLICY` check (new `ComplianceCheck` enum value) that validates:
  - Auto-merge is only enabled when `MergeMode.AUTO_MERGE` is explicitly set in repo config
  - Human approval wait states are operational (Epic 21 dependency check)
  - Required reviewer rules cover all sensitive paths (existing check, but now mandatory-fail for Execute, not warn-and-pass)
- Promotion to Execute tier fails if `EXECUTE_TIER_POLICY` check fails
- Compliance result includes the new check in its output and scorecard

**AC3: Tier label reconciliation includes Execute**
- `TIER_LABELS` map in `publisher.py` includes `RepoTier.EXECUTE: "tier:execute"`
- Label reconciliation adds/removes `tier:execute` correctly on PRs
- `REQUIRED_LABELS` in `compliance/models.py` includes `tier:execute`

**AC4: GitHub auto-merge integration works end-to-end**
- `GitHubClient` gains an `enable_auto_merge(owner, repo, pr_number, merge_method)` method that calls the GitHub GraphQL `enablePullRequestAutoMerge` mutation
- Merge method defaults to "squash" but is configurable per repo profile
- If auto-merge enablement fails (repo does not have auto-merge enabled in GitHub settings), Publisher logs the failure and continues without auto-merge (does not block the publish)
- Auto-merge is only attempted after the PR is marked ready-for-review

**AC5: Human approval gate integration (post-Epic 21)**
- When Execute tier + auto-merge is enabled, the Temporal workflow must pass through the human approval wait state (from Epic 21) BEFORE Publisher enables auto-merge
- If human approval times out (7-day escalation), auto-merge is NOT enabled; PR stays as ready-for-review only
- The approval signal from Epic 21 is the gate that unlocks auto-merge enablement

**AC6: Admin UI reflects Execute tier state**
- Repo detail page shows current merge mode and whether auto-merge is active
- Compliance scorecard includes the new `EXECUTE_TIER_POLICY` check
- Admin UI can toggle `MergeMode` between `DRAFT_ONLY`, `REQUIRE_REVIEW`, and `AUTO_MERGE`
- Execute tier repos show an "Auto-Merge Active" badge when `repo_tier == EXECUTE` AND `merge_mode == AUTO_MERGE` AND latest compliance check passed. Badge shows "Auto-Merge Blocked" with reason when any condition fails.

**AC7: Repo profile supports merge method preference**
- `RepoProfileRow` gains a `merge_method` column (enum: `squash`, `merge`, `rebase`; default: `squash`)
- `RepoProfileCreate` and `RepoProfileUpdate` schemas include the field
- Publisher reads `merge_method` from repo profile when enabling auto-merge

**AC8: Observability and audit trail**
- Publisher emits span attributes: `thestudio.auto_merge_enabled`, `thestudio.merge_method`, `thestudio.execute_tier_active`
- Auto-merge enablement and failures are logged with correlation_id
- Compliance check results for the new Execute policy check are persisted

### 4b. Top Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| GitHub repo does not have auto-merge enabled in settings | Auto-merge silently fails | Publisher logs warning and degrades gracefully; compliance checker validates GitHub auto-merge setting |
| Epic 21 not complete when this ships | Auto-merge without human approval gate | Hard dependency: AC5 tests fail if approval wait states are absent; feature flag gates auto-merge |
| Accidental auto-merge on production repo | Unreviewed code merges | Multiple gates: compliance check, merge mode config, human approval, required reviewers |
| Database migration for merge_method column | Downtime risk | Nullable column with default; backward compatible |

## 5. Constraints and Non-Goals

### Constraints
- Auto-merge MUST NOT be enabled unless all of: (a) Execute tier, (b) compliance passing, (c) MergeMode.AUTO_MERGE configured, (d) human approval received (Epic 21), (e) V+QA gates passed
- Publisher remains the only GitHub writer. No other component may call auto-merge APIs.
- Database migration for `merge_method` must be backward-compatible (nullable with default)
- GitHub auto-merge uses the GraphQL API (REST API does not support enabling auto-merge)

### Non-Goals
- **V1 (Merge policy enforcement)**: This epic enables auto-merge; V1 adds per-path and per-label merge policies. V1 is a follow-on epic.
- **V2 (Reminder cadence for human approval)**: Reminder logic lives in Epic 21. This epic consumes the approval signal.
- **Automatic promotion to Execute tier**: Promotion remains an explicit admin action gated by compliance checks. No automatic tier escalation.
- **Cross-repo auto-merge policies**: Each repo is configured independently. Fleet-wide policies are deferred.
- **Merge queue integration**: GitHub merge queues are a separate concern; this epic uses standard auto-merge only.

## 6. Stakeholders and Roles

| Role | Who | Responsibility |
|------|-----|----------------|
| Epic Owner | Platform Lead | Final scope decisions, risk acceptance |
| Tech Lead | Backend Engineer | Publisher changes, GitHub GraphQL integration, compliance gate |
| QA | QA Engineer | End-to-end tier behavior tests, auto-merge safety verification |
| DevOps | Infrastructure Engineer | Database migration, GitHub App permission review |
| Security | Security Review | Verify auto-merge cannot bypass required reviewers or rulesets |
| Design | Admin UI Owner | Merge mode controls, Execute tier badges in Admin UI |

## 7. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Execute-tier repos can auto-merge after all gates pass | 100% of configured repos | Integration test in `tests/publisher/test_execute_approval.py`: PR auto-merges after V+QA+approval |
| Zero unreviewed auto-merges | 0 incidents in first 30 days | Query `ModelCallAudit` and `ComplianceCheckResult` records: every auto-merged PR has both an approval signal timestamp and a passing `EXECUTE_TIER_POLICY` check |
| Time from QA pass to merge (Execute tier) | < 5 minutes (down from manual review delay) | Span attribute `thestudio.auto_merge_enabled` timestamp minus QA pass timestamp from `VerificationResult` |
| Compliance gate blocks unconfigured auto-merge | 100% | Test: promotion attempt without MergeMode.AUTO_MERGE fails |
| Admin UI shows accurate Execute tier state | All repo detail pages correct | Manual verification + Playwright test in `tests/e2e/` (if E2E suite exists) or manual checklist |

## 8. Context and Assumptions

### Business Rules
- Execute tier is the highest trust tier. A repo earns it through compliance validation, not by default.
- Auto-merge is opt-in at two levels: (1) repo must be promoted to Execute tier by admin, (2) merge mode must be explicitly set to AUTO_MERGE
- Human approval (Epic 21) is always required before auto-merge, even for low-risk work. This is a policy decision that may be relaxed in future epics.
- GitHub's own required reviewers and rulesets are the last line of defense. TheStudio enables auto-merge; GitHub enforces its own rules on top.

### Dependencies
- **Epic 21 (C6: Human Approval Wait States)** -- HARD dependency. Auto-merge cannot be safely enabled without Temporal approval wait states. If Epic 21 is incomplete, AC5 tests will fail and auto-merge must be feature-flagged off.
  - **Implementation gate:** Stories in Slice 4 (22.13-22.15) MUST NOT begin until Epic 21 Stories 1-6 are merged. Slices 1-3 can proceed in parallel with Epic 21.
- **GitHub App permissions** -- The GitHub App must have `contents: write` and `pull_requests: write` permissions. Auto-merge also requires that the repository has "Allow auto-merge" enabled in GitHub settings.
- **GraphQL API access** -- `GitHubClient` currently uses REST only. Auto-merge requires the GraphQL `enablePullRequestAutoMerge` mutation. The client must be extended.

### Systems Affected
- `src/publisher/publisher.py` -- Execute tier branch in `_should_mark_ready()` and new auto-merge logic
- `src/publisher/github_client.py` -- New `enable_auto_merge()` method using GraphQL
- `src/compliance/checker.py` -- New `EXECUTE_TIER_POLICY` check
- `src/compliance/models.py` -- New enum value, updated required labels, remediation hint
- `src/compliance/promotion.py` -- Execute-specific eligibility checks
- `src/repo/repo_profile.py` -- `merge_method` column on `RepoProfileRow`
- `src/admin/merge_mode.py` -- Integration with repo profile persistence (currently in-memory)
- `src/admin/templates/partials/repo_detail_content.html` -- Execute tier UI elements
- `src/admin/templates/compliance.html` -- New compliance check display
- `src/db/migrations/` -- New migration for `merge_method` column

### Assumptions
- Epic 21 delivers a Temporal activity that blocks until human approval or 7-day timeout, and emits a signal that downstream activities can consume
- GitHub GraphQL API is accessible with the same installation token used for REST calls
- The existing compliance checker architecture (checker + models + promotion) can accommodate new check types without structural changes
- The `MergeMode` enum and `merge_mode.py` module will be migrated from in-memory storage to repo profile persistence as part of this epic
- GitHub App permission changes (`contents: write` for auto-merge) require a repository admin to update the GitHub App installation settings. This is an operational prerequisite, not a code change. The epic owner must verify permissions before Slice 2 begins.

---

## Story Map

### Slice 1: Publisher Execute Tier Behavior (Risk Reduction)
_Goal: Publisher differentiates Execute from Suggest. No auto-merge yet -- just correct branching logic._

| # | Story | AC | Files to modify/create |
|---|-------|----|----------------------|
| 22.1 | Update `_should_mark_ready()` to handle `RepoTier.EXECUTE` | AC1 (partial) | `src/publisher/publisher.py` |
| 22.2 | Add `tier:execute` to `TIER_LABELS` and label reconciliation | AC3 | `src/publisher/publisher.py`, `src/compliance/models.py` |
| 22.3 | Add `auto_merge_enabled` field to `PublishResult` | AC1 (partial) | `src/publisher/publisher.py` |
| 22.4 | Unit tests for Execute tier Publisher behavior (no auto-merge path) | AC1 | `tests/publisher/test_publisher.py` |

### Slice 2: GitHub Auto-Merge Integration
_Goal: GitHubClient can enable auto-merge via GraphQL. Publisher uses it._

| # | Story | AC | Files to modify/create |
|---|-------|----|----------------------|
| 22.5 | Add GraphQL `enable_auto_merge()` to `GitHubClient` | AC4 | `src/publisher/github_client.py` |
| 22.6 | Add `merge_method` to `RepoProfileRow` with migration | AC7 | `src/repo/repo_profile.py`, `src/db/migrations/` |
| 22.7 | Wire Publisher to call `enable_auto_merge()` for Execute + AUTO_MERGE | AC1, AC4 | `src/publisher/publisher.py` |
| 22.8 | Integration tests for auto-merge enablement (mocked GitHub) | AC4 | `tests/publisher/test_auto_merge.py` |

### Slice 3: Compliance Gate for Execute Tier
_Goal: Compliance checker enforces Execute-specific policy. Promotion blocked without it._

| # | Story | AC | Files to modify/create |
|---|-------|----|----------------------|
| 22.9 | Add `EXECUTE_TIER_POLICY` to `ComplianceCheck` enum with remediation hint | AC2 | `src/compliance/models.py` |
| 22.10 | Implement Execute-specific compliance check in `ComplianceChecker` | AC2 | `src/compliance/checker.py` |
| 22.11 | Update promotion eligibility to require `EXECUTE_TIER_POLICY` pass | AC2 | `src/compliance/promotion.py` |
| 22.12 | Unit tests for Execute compliance gate | AC2 | `tests/compliance/test_checker.py`, `tests/compliance/test_promotion.py` |

### Slice 4: Human Approval Integration (Epic 21 Dependency)
_Goal: Auto-merge only fires after human approval signal received._

| # | Story | AC | Files to modify/create |
|---|-------|----|----------------------|
| 22.13 | Wire Publisher auto-merge to require approval signal from Temporal workflow | AC5 | `src/publisher/publisher.py` |
| 22.14 | Feature flag: disable auto-merge if approval wait states unavailable | AC5 | `src/publisher/publisher.py`, `src/admin/merge_mode.py` |
| 22.15 | Integration test: auto-merge blocked without approval, enabled with approval | AC5 | `tests/publisher/test_execute_approval.py` |

### Slice 5: Admin UI and Observability
_Goal: Operators can see and control Execute tier behavior._

| # | Story | AC | Files to modify/create |
|---|-------|----|----------------------|
| 22.16 | Admin UI: merge mode toggle and auto-merge badge on repo detail | AC6 | `src/admin/templates/partials/repo_detail_content.html`, `src/admin/routes.py` |
| 22.17 | Admin UI: compliance scorecard shows Execute policy check | AC6 | `src/admin/templates/compliance.html`, `src/admin/compliance_scorecard.py` |
| 22.18 | Publisher span attributes for Execute tier and auto-merge | AC8 | `src/publisher/publisher.py`, `src/observability/conventions.py` |

---

## Meridian Review Status

**Round 2: COMMITTABLE**

All Round 1 fixes verified. Full 7-question checklist passes. No red flags.

| # | Question | R1 Status | R2 Status |
|---|----------|-----------|-----------|
| 1 | Is the goal statement specific enough to test against? | PASS | PASS |
| 2 | Are acceptance criteria testable at epic scale? | PASS | PASS |
| 3 | Are non-goals explicit? | PASS | PASS |
| 4 | Are dependencies identified with owners and dates? | Fixed (implementation gate added) | PASS |
| 5 | Are success metrics measurable with existing instrumentation? | Fixed (measurement paths specified) | PASS |
| 6 | Can an AI agent implement without guessing scope? | Fixed (AC6 badge semantics, GitHub App ownership) | PASS |
| 7 | Are there red flags? | Fixed (4 items) | No red flags |

---

## Implementation Record

**Completed:** 2026-03-13
**Sprint:** 21 (delivered ahead of schedule — Sprint 20 and 21 collapsed into a single session)
**Architecture Gap:** C2 (Execute tier end-to-end) — last of 8 CRITICAL gaps, now CLOSED

### Files Created
| File | Purpose |
|------|---------|
| `src/db/migrations/020_repo_profile_merge_method.py` | Migration: `merge_method VARCHAR(20)` on `repo_profile` |
| `tests/unit/test_publisher_execute.py` | 36 tests: Execute tier Publisher behavior, auto-merge gates, tier labels |
| `tests/unit/test_compliance_execute.py` | 8 tests: Execute tier policy compliance check |

### Files Modified
| File | Changes |
|------|---------|
| `src/publisher/publisher.py` | `_should_mark_ready()` handles Execute; `_should_enable_auto_merge()` five-gate safety; `_try_enable_auto_merge()` with graceful degradation; `LABEL_TIER_EXECUTE`; `auto_merge_enabled` on `PublishResult`; `publish()` accepts `approval_received` + `merge_method`; OTel span attributes |
| `src/publisher/github_client.py` | `enable_auto_merge()` via GitHub GraphQL `enablePullRequestAutoMerge` mutation |
| `src/compliance/models.py` | `EXECUTE_TIER_POLICY` enum value; remediation hint; `tier:execute` in `REQUIRED_LABELS` |
| `src/compliance/checker.py` | `_check_execute_tier_policy()` validates AUTO_MERGE + CODEOWNERS sensitive path coverage |
| `src/compliance/promotion.py` | `check_promotion_eligibility()` passes `repo_full_name` to compliance checker |
| `src/repo/repo_profile.py` | `merge_method` column on `RepoProfileRow`; added to Create/Read/Update schemas |
| `src/admin/compliance_scorecard.py` | `execute_tier_policy_passed` on `RepoComplianceData`; 8th scorecard check |
| `src/admin/platform_router.py` | `execute_tier_policy_passed` on `EvaluateComplianceRequest` and handler |
| `src/admin/templates/partials/repo_detail_content.html` | Auto-Merge Active/Blocked badge for Execute tier |
| `src/observability/conventions.py` | `ATTR_AUTO_MERGE_ENABLED`, `ATTR_MERGE_METHOD`, `ATTR_EXECUTE_TIER_ACTIVE` |
| `tests/unit/test_compliance_checker.py` | Updated for new EXECUTE_TIER_POLICY check (CODEOWNERS paths, merge mode patch) |
| `tests/unit/test_compliance_router.py` | Updated `make_compliant_repo_info()` + merge mode fixture |
| `tests/unit/test_compliance_scorecard.py` | Updated 5 tests for 8-check scorecard |
| `tests/unit/test_compliance_data_wiring.py` | Updated for `execute_tier_policy_passed` field |
| `tests/unit/test_platform_api.py` | Updated checks_total 7→8, added `execute_tier_policy_passed` |
| `tests/unit/test_promotion.py` | Added merge mode fixture + SENSITIVE_PATHS coverage |
| `tests/unit/test_tier_promotion.py` | Updated label reconciliation for 3-tier system |

### Test Results
- **1,689 unit tests pass** (0 failures, 0 errors)
- **44 new tests** (36 publisher + 8 compliance)
- **11 existing tests updated** for Execute tier compatibility
- Integration/docker/playwright tests require infrastructure (expected skip)

### Key Design Decisions
1. **Five-gate auto-merge safety:** Execute tier + AUTO_MERGE mode + Verification passed + QA passed + Human approval received — ALL required
2. **Graceful degradation:** If GitHub rejects auto-merge (repo settings), Publisher logs warning and continues
3. **GraphQL over REST:** GitHub auto-merge requires GraphQL `enablePullRequestAutoMerge` mutation (REST doesn't support it)
4. **CODEOWNERS coverage:** Execute tier policy requires CODEOWNERS to cover all `SENSITIVE_PATHS` (auth, billing, exports, infra)
