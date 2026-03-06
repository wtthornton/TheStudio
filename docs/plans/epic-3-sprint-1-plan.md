# Sprint 1 Plan — Epic 3: Execute Tier + Compliance Checker

**Persona:** Helm (Planner & Dev Manager)
**Date:** 2026-03-06
**Epic:** `docs/epics/epic-3-execute-tier-compliance.md`
**Sprint duration:** 2 weeks
**Team:** 1–2 developers
**Predecessor:** Epic 2 complete (learning loop closed: Complexity Index, Outcome Ingestor full, Reputation Engine with tiers/decay/drift, Router uses weights; 98 tests)

---

## Sprint Goal

**Objective:** One repo passes compliance checker and is promoted to Execute tier; full workflow runs successfully on a test issue; 3+ repos registered with at least 2 in Suggest or Execute tier — so that Phase 2 is complete and the platform proves production readiness with governance.

**Test:** The sprint goal is met when:
1. Compliance checker validates rulesets, required reviewers, branch protections, and execution plane health — 8+ test cases
2. Execute tier promotion is blocked until compliance checker passes — 3+ test cases
3. One repo is promoted to Execute tier with audit trail (who, when, compliance score) — verified by Repo Profile query
4. Full workflow (Intake → Context → Intent → Router → Assembler → Implement → Verify → QA → Publish) completes on a test issue in the Execute-tier repo — workflow logs show completion
5. PR created with evidence comment, awaiting human merge — GitHub PR exists with expected structure
6. 3+ repos registered with the platform — Repo Profile query returns ≥3 repos
7. At least 2 repos in Suggest or Execute tier — Repo Profile query shows tier distribution
8. All code passes `ruff` lint and `mypy` type check
9. Compliance results include remediation hints for any failures

**Constraint:** No story is "done" unless its Definition of Done checklist is fully satisfied. One commit per story. Run `mypy` in the edit loop (not just at the end). Run `tapps_quick_check` after every file edit.

---

## Retro Actions from Epic 2

| Action | How addressed in this sprint |
|--------|------------------------------|
| mypy in the edit loop | Enforced in constraint — every file edit, before commit |
| One commit per story | Enforced in constraint; each story is atomic |
| Sprint DoD is the bar | All 9 test criteria must pass; no partial credit |
| Architecture docs as source of truth | All stories reference specific thestudioarc docs; update docs if build diverges |

---

## Capacity and Buffer

- **Commitment:** ~80% of sprint capacity (20 story points of 25 available per 2-week sprint)
- **Buffer:** ~20% for GitHub API integration issues, first-promotion edge cases, and unknowns
- **Total planned:** 20 points across 6 stories

---

## Order of Work

### Phase A — Compliance Checker (days 1–5)

Stories 3.1 and 3.2 build the compliance checker. No dependencies on other Epic 3 stories. Must complete before promotion gate (3.3).

| Order | Story | Points | Size | Rationale |
|-------|-------|--------|------|-----------|
| 1 | **3.1 Compliance Checker — Core Checks** | 5 | L | Foundation. Validates rulesets, required reviewers, branch protections via GitHub API. |
| 2 | **3.2 Compliance Checker — Execution Plane Health** | 3 | M | Validates internal services. Can parallel with 3.1 tail. |

#### Story 3.1 — Compliance Checker Core Checks

**Reference:** `thestudioarc/23-admin-control-ui.md` (Repo Compliance Scorecard, Execute Tier Compliance Gate, Repo Compliance Checker sections)

**Scope:** Implement compliance checker as a platform job that validates GitHub-side governance requirements.

**Definition of Done:**
- [ ] `src/compliance/checker.py`: ComplianceChecker class
  - `check_compliance(repo_id: UUID) -> ComplianceResult`
  - Returns: pass/fail per check, failure reasons, remediation hints, overall score
- [ ] GitHub API checks implemented:
  - `rulesets_configured`: At least one ruleset exists with required status checks
  - `required_reviewers`: Required reviewer rules exist for sensitive paths (auth/**, billing/**, exports/**, infra/**) if those paths exist
  - `branch_protection`: Default branch has protection enabled (require PR, dismiss stale reviews)
  - `labels_exist`: Standard labels exist (agent:in-progress, agent:queued, agent:done, agent:blocked)
  - `projects_v2`: Projects v2 integration configured OR explicitly waived in Repo Profile
- [ ] `src/compliance/models.py`: ComplianceResult, ComplianceCheck, ComplianceCheckResult
  - ComplianceCheck: `check_name`, `passed`, `failure_reason`, `remediation_hint`
  - ComplianceResult: `repo_id`, `overall_passed`, `score` (0-100), `checks: list[ComplianceCheckResult]`, `checked_at`
- [ ] Compliance results persisted to database:
  - Migration creates `compliance_results` table: `id` (uuid pk), `repo_id`, `overall_passed`, `score`, `checks` (jsonb), `checked_at`, `triggered_by`
- [ ] Remediation hints for each failure:
  - `rulesets_configured`: "Create a ruleset in GitHub settings with required status checks for CI"
  - `required_reviewers`: "Add CODEOWNERS or required reviewer rule for {path}"
  - `branch_protection`: "Enable branch protection on {default_branch} requiring PR reviews"
  - `labels_exist`: "Create labels: agent:in-progress, agent:queued, agent:done, agent:blocked"
  - `projects_v2`: "Configure Projects v2 integration or set projects_v2_waived: true in Repo Profile"
- [ ] Compliance checker is idempotent: same repo state → same result
- [ ] 5+ unit tests: each check pass/fail, remediation hints present
- [ ] 3+ integration tests: full compliance check against test repo (mock GitHub API responses)
- [ ] `ruff` clean, `mypy` clean (run mypy after each file edit)

**Unknowns / risks:**
- GitHub API rate limits during compliance check. Mitigation: cache API responses during single check run; batch GraphQL queries where possible.
- Rulesets API is relatively new (2023). Mitigation: use REST API v3 for rulesets; fall back to branch protection rules if rulesets unavailable.

---

#### Story 3.2 — Compliance Checker Execution Plane Health

**Reference:** `thestudioarc/23-admin-control-ui.md` (Execute Tier Compliance Gate)

**Scope:** Add execution plane health checks to compliance checker.

**Definition of Done:**
- [ ] Execution plane health checks added to ComplianceChecker:
  - `execution_plane_health`: Workspace healthy, workers responding, verification runner operational
  - `publisher_idempotency`: Publisher idempotency guard operational (TaskPacket lookup-before-create)
  - `credentials_scoped`: Repo credentials are scoped correctly (not over-permissioned)
- [ ] Health check implementation:
  - Workspace: verify workspace directory exists and is accessible
  - Workers: verify at least one worker is registered and healthy (Temporal worker status)
  - Verification runner: verify ruff/pytest can be invoked in workspace
  - Publisher idempotency: verify idempotency key lookup returns expected results for test key
  - Credentials: verify GitHub token scope matches expected permissions for tier
- [ ] Remediation hints for each failure:
  - `execution_plane_health`: "Verify execution plane is deployed: workspace at {path}, workers registered in Temporal"
  - `publisher_idempotency`: "Verify Publisher idempotency guard is operational; check TaskPacket lookup API"
  - `credentials_scoped`: "Review GitHub token scope; Execute tier requires {expected_scope}, found {actual_scope}"
- [ ] 3+ unit tests: each execution plane check pass/fail
- [ ] `ruff` clean, `mypy` clean

**Unknowns / risks:**
- Execution plane health checks require access to internal services. Mitigation: use existing health check endpoints where available; add lightweight checks where needed.

---

### Phase B — Execute Tier Promotion (days 6–8)

Story 3.3 implements the promotion gate. Depends on 3.1 and 3.2.

| Order | Story | Points | Size | Rationale |
|-------|-------|--------|------|-----------|
| 3 | **3.3 Execute Tier Promotion Gate** | 5 | M | Depends on 3.1, 3.2. Promotion blocked until compliance passes. Audit trail required. |

#### Story 3.3 — Execute Tier Promotion Gate

**Reference:** `thestudioarc/23-admin-control-ui.md` (Execute Tier Compliance Gate, Repo Registration Lifecycle)

**Scope:** Implement promotion workflow that gates Execute tier on compliance check results.

**Definition of Done:**
- [ ] `src/compliance/promotion.py`: PromotionService class
  - `request_promotion(repo_id: UUID, target_tier: RepoTier, triggered_by: str) -> PromotionResult`
  - `check_promotion_eligibility(repo_id: UUID, target_tier: RepoTier) -> EligibilityResult`
- [ ] Promotion workflow:
  1. Check current tier (must be Suggest to promote to Execute)
  2. Run compliance checker
  3. If compliance passes, update Repo Profile tier to Execute
  4. Record audit metadata: who triggered, when, compliance score, all check results
  5. Emit `tier_changed` signal with actor, from_tier, to_tier, compliance_score, timestamp
- [ ] Promotion blocked if:
  - Current tier is not Suggest (must progress Observe → Suggest → Execute)
  - Compliance checker fails any required check
- [ ] Tier demotion supported:
  - `demote_tier(repo_id: UUID, target_tier: RepoTier, reason: str, triggered_by: str) -> DemotionResult`
  - Execute → Suggest demotion if compliance drifts or issues emerge
- [ ] Audit trail persisted:
  - Migration creates `tier_transitions` table: `id` (uuid pk), `repo_id`, `from_tier`, `to_tier`, `triggered_by`, `compliance_score`, `compliance_result_id`, `reason`, `transitioned_at`
- [ ] Signals emitted: `tier_changed`, `promotion_blocked`
- [ ] 3+ unit tests: promotion success, promotion blocked (compliance fail), demotion
- [ ] 2+ integration tests: full promotion flow with compliance check
- [ ] `ruff` clean, `mypy` clean

**Unknowns / risks:**
- Tier transition during active workflow could cause issues. Mitigation: promotion is blocked if repo has active (non-terminal) workflows.

---

### Phase C — First Promotion + Multi-Repo (days 9–14)

Stories 3.4, 3.5, and 3.6 prove the system works. Depends on 3.3.

| Order | Story | Points | Size | Rationale |
|-------|-------|--------|------|-----------|
| 4 | **3.4 First Repo Promotion** | 3 | M | Depends on 3.3. Prove one repo reaches Execute with full workflow. |
| 5 | **3.5 Multi-Repo Registration** | 2 | M | Independent of 3.4. Register 2 additional repos with profiles. |
| 6 | **3.6 Multi-Repo Tier Promotion** | 2 | S | Depends on 3.3, 3.5. Promote at least 1 additional repo to Suggest/Execute. |

#### Story 3.4 — First Repo Promotion

**Reference:** `thestudioarc/23-admin-control-ui.md`, `docs/epics/epic-3-execute-tier-compliance.md` AC-4

**Scope:** Promote one repo to Execute tier, run full workflow on test issue, verify PR created.

**Definition of Done:**
- [ ] Select candidate repo for Execute tier promotion:
  - Recommendation: TheStudio repo itself (we know the codebase, can control test issues)
  - Alternative: A fork or test repo with known good state
- [ ] Ensure candidate repo passes compliance checker:
  - Fix any compliance failures before promotion
  - Document compliance state in `docs/architecture/execute-tier-promotion.md`
- [ ] Promote repo to Execute tier:
  - Call `PromotionService.request_promotion(repo_id, RepoTier.EXECUTE, "helm-sprint-1")`
  - Verify promotion succeeds and audit trail recorded
- [ ] Create test issue in Execute-tier repo:
  - Simple, well-defined task (e.g., "Add logging to function X")
  - Issue body includes clear acceptance criteria
- [ ] Run full workflow on test issue:
  - Intake → Context → Intent → Router → Assembler → Implement → Verify → QA → Publish
  - Monitor workflow progress via Temporal UI or logs
- [ ] Verify PR created:
  - PR exists in GitHub with draft or ready-for-review status
  - Evidence comment present with TaskPacket ID, intent summary, verification result
  - Standard labels applied
  - PR awaits human merge (no auto-merge)
- [ ] Document results:
  - Workflow timeline screenshot or log excerpt
  - PR URL and evidence comment
  - Any issues encountered and how resolved
- [ ] No code changes required (this is a verification/promotion story)

**Unknowns / risks:**
- First full workflow in Execute tier may expose edge cases. Mitigation: have buffer time; document issues for future sprints.
- Test issue may hit unexpected failures. Mitigation: choose simple task; be prepared to diagnose and fix.

---

#### Story 3.5 — Multi-Repo Registration

**Reference:** `docs/epics/epic-3-execute-tier-compliance.md` AC-5

**Scope:** Register 2 additional repos with Repo Profiles.

**Definition of Done:**
- [ ] Identify 2 additional repos for registration:
  - Can be test repos, forks, or real repos
  - Must have: valid GitHub repo, ability to create webhook, ability to configure rulesets (or waive)
- [ ] Create Repo Profile for each repo:
  - Language, build commands, required checks
  - Risk paths (if any)
  - Initial tier: Observe
- [ ] Register repos with platform:
  - Webhook configured and receiving events
  - Credentials scoped correctly (per-repo tokens)
  - Execution plane can access workspace
- [ ] Verify registration:
  - Repo Profile query returns all 3 repos
  - Each repo has distinct credentials (no cross-repo leakage)
- [ ] Document registered repos in `docs/architecture/multi-repo-setup.md`:
  - Repo name, purpose, tier, profile summary
- [ ] 2+ tests: verify repo registration, verify credential isolation

**Unknowns / risks:**
- Repo credential setup may be manual. Mitigation: document process; automate in future sprint.

---

#### Story 3.6 — Multi-Repo Tier Promotion

**Reference:** `docs/epics/epic-3-execute-tier-compliance.md` AC-5

**Scope:** Promote at least 1 additional repo to Suggest or Execute tier.

**Definition of Done:**
- [ ] For at least 1 of the newly registered repos:
  - Run compliance checker
  - Fix any compliance failures OR promote to Suggest (lower bar than Execute)
  - Promote to Suggest or Execute tier
- [ ] Verify tier distribution:
  - Repo Profile query shows: ≥1 repo in Execute, ≥1 repo in Suggest or Execute (total ≥2 in higher tiers)
- [ ] Document tier promotion in `docs/architecture/multi-repo-setup.md`
- [ ] No new code required (uses existing promotion service)

**Unknowns / risks:**
- Additional repos may not pass compliance. Mitigation: Suggest tier has lower bar (no full compliance required); can promote to Suggest as fallback.

---

## What's Explicitly Out This Sprint

| Item | Why | When |
|------|-----|------|
| Admin UI | Separate epic (Epic 4). This sprint provides API/CLI visibility only. | Epic 4 |
| Compliance drift monitoring | Continuous monitoring is Phase 4. This sprint checks at promotion time. | Phase 4 |
| Auto-merge | Human merge default. Auto-merge is a later enhancement. | Phase 4 |
| Expert Performance Console | Phase 3/4 deliverable. | Phase 3 |
| Second execution plane | Multi-repo uses shared plane. Dedicated per-repo planes are Phase 4. | Phase 4 |

---

## Dependencies

| Story | Depends on | Status |
|-------|-----------|--------|
| 3.1 Compliance Checker Core | Repo Profile, GitHub API access | Repo Profile complete (Epic 1); GitHub API available |
| 3.2 Compliance Checker Execution Plane | 3.1 (checker infrastructure), execution plane APIs | 3.1 in sprint; execution plane exists (Epic 0/1) |
| 3.3 Execute Tier Promotion | 3.1, 3.2 (compliance checker complete) | In sprint |
| 3.4 First Repo Promotion | 3.3 (promotion gate) | In sprint |
| 3.5 Multi-Repo Registration | Repo Profile | Complete (Epic 1); independent of 3.1-3.4 |
| 3.6 Multi-Repo Tier Promotion | 3.3, 3.5 | In sprint |

**Cross-dependency risk:** Stories 3.1 → 3.2 → 3.3 → 3.4 are sequential. Stories 3.5 can run in parallel. Story 3.6 depends on 3.3 and 3.5. Mitigation: start 3.5 early (can parallel with 3.1); 3.6 is small and can complete in buffer time.

---

## Timeline

### 2 developers

| Days | Dev 1 | Dev 2 |
|------|-------|-------|
| 1–3 | 3.1 Compliance Checker Core | 3.5 Multi-Repo Registration |
| 4–5 | 3.2 Compliance Checker Execution Plane | 3.5 Multi-Repo Registration (complete) |
| 6–8 | 3.3 Execute Tier Promotion | Support 3.3 / buffer |
| 9–11 | 3.4 First Repo Promotion | 3.6 Multi-Repo Tier Promotion |
| 12–14 | Buffer / documentation | Buffer / documentation |

### 1 developer

| Days | Work |
|------|------|
| 1–4 | 3.1 Compliance Checker Core |
| 5–6 | 3.2 Compliance Checker Execution Plane |
| 7–9 | 3.3 Execute Tier Promotion |
| 10–11 | 3.4 First Repo Promotion + 3.5 Multi-Repo Registration |
| 12–13 | 3.6 Multi-Repo Tier Promotion |
| 14 | Buffer |

---

## Sprint Definition of Done

The sprint is done when:
1. All 6 stories pass their Definition of Done checklists
2. All tests pass (unit + integration)
3. `ruff` and `mypy` clean across all new and modified files
4. Migrations run cleanly on Epic 2 schema
5. `tapps_validate_changed` passes on all modified files
6. One commit per story, each with passing CI
7. **One repo in Execute tier:** Compliance passed, promotion recorded with audit trail
8. **Full workflow complete:** Test issue → PR with evidence comment, awaiting human merge
9. **Multi-repo proven:** 3+ repos registered, ≥2 in Suggest or Execute tier

---

*Sprint 1 plan created by Helm. Awaiting Meridian review before execution.*
