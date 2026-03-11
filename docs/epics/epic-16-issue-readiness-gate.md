# Epic 16 — Issue Readiness Gate

**Author:** Saga
**Date:** 2026-03-10
**Status:** Approved — Meridian Round 3 passed, ready to commit
**Target Sprint:** Sprint 17–18 (weeks of 2026-03-17 to 2026-03-28)

---

## 1. Title

Issue Readiness Gate — Assess incoming GitHub issue quality after context enrichment, block low-quality issues with structured clarification requests, and learn from outcome signals to improve the gate over time.

## 2. Narrative

TheStudio is a platform that connects to **other teams' repositories** and converts their GitHub issues into evidence-backed draft PRs. The pipeline's 9 stages assume the incoming issue contains enough signal to build a correct Intent Specification — a goal, constraints, acceptance criteria, and scope boundaries. When issues meet that bar, the pipeline delivers single-pass success. When they don't, the system pays for it downstream.

**The problem is measurable today.** The Intent Builder (`src/intent/intent_builder.py:187-188`) has a fallback: when the issue body contains no extractable acceptance criteria, it generates `"Implementation satisfies: {issue_title}"` — a tautology that tells QA nothing. The Context Manager's own architecture doc (`thestudioarc/03-context-manager.md`) states its intent is "to prevent garbage in, garbage out," but it only enriches — it never gates on quality. The QA defect taxonomy (`thestudioarc/14-qa-quality-layer.md`) defines `intent_gap` as a first-class defect category for "acceptance criteria missing, conflicting, or untestable; requirements unclear." Every `intent_gap` defect means the pipeline spent compute on implementation, verification, and QA before discovering the issue was never clear enough to build from.

**The persona chain solves this for TheStudio's own development.** Meridian reviews Saga's epics and Helm's plans against a 7-question checklist before work is committed. She catches vague goals, untestable acceptance criteria, missing dependencies, and scope creep. But this discipline exists only internally — external teams whose repos connect to TheStudio get no quality gate on their issue inputs. Their issues flow directly from Intake through Context to Intent with no readiness assessment.

**This epic adds a Readiness Gate between Context enrichment and Intent building.** After Context has enriched the TaskPacket with complexity, risk flags, service context, and impacted surfaces — information that may answer questions the raw issue left open — the Readiness Gate evaluates whether the enriched issue has sufficient signal to define correctness. If it does, the issue flows to Intent normally. If it doesn't, the gate produces a structured clarification request posted back to the GitHub issue via Publisher, and the TaskPacket enters a `clarification_requested` hold state until the submitter responds.

**Why after Context, not before Intake?** Three reasons:
1. **Context enrichment answers questions.** A terse issue like "fix login timeout" may be ambiguous on its own, but after Context identifies the impacted service, attaches the Service Context Pack, and computes risk flags, the scope may be obvious. Gating before enrichment would reject issues that Context could have made actionable.
2. **Complexity Index drives gate calibration.** A low-complexity bug fix ("button color wrong on settings page") needs less issue detail than a high-complexity cross-service migration. The gate should be proportional, and Complexity Index — computed by Context — is the calibration input.
3. **Risk flags drive mandatory questions.** If Context flags `risk:auth` or `risk:billing`, the gate can require explicit security or billing acceptance criteria. Without risk flags, the gate would apply the same bar to every issue.

**Trust tier alignment:** The gate respects the existing three-tier model:
- **Observe:** Gate scores the issue and records readiness metrics, but does not block or post comments. This gives teams visibility into their issue quality before they enable automation.
- **Suggest:** Gate holds low-readiness issues and posts a clarification comment. The pipeline proceeds only after the submitter responds or a human overrides.
- **Execute:** Gate is mandatory. Low-readiness issues are blocked with a structured clarification request. High-risk issues with low readiness are escalated to human review.

**Learning loop:** The Outcome Ingestor already tracks `intent_gap` defects from QA. This epic connects that signal back to the Readiness Gate: issues that passed the gate but later triggered `intent_gap` defects become training data for gate calibration. Over time, the gate learns which readiness dimensions predict downstream failures and adjusts thresholds accordingly.

**Roadmap linkage:** This epic directly advances the OKR "single-pass success rate" by reducing the number of issues that enter the pipeline with insufficient signal. It is the bridge between "the platform processes issues" and "the platform ensures issues are worth processing." It also advances "time to market" by eliminating compute wasted on issues that will loop back or produce `intent_gap` defects.

**Scope:** This is approximately 2–3 weeks of work across 2 sprints. Sprint 1 builds the readiness scoring engine and gate infrastructure. Sprint 2 adds the clarification loop, learning feedback, and Admin UI integration.

## 3. References

- Context Manager architecture: `thestudioarc/03-context-manager.md` (enrichment, complexity, risk flags)
- Intent Layer architecture: `thestudioarc/11-intent-layer.md` (what the gate protects)
- Intent Builder implementation: `src/intent/intent_builder.py` (fallback at line 187-188)
- QA defect taxonomy: `thestudioarc/14-qa-quality-layer.md` (`intent_gap` category)
- System runtime flow: `thestudioarc/15-system-runtime-flow.md` (pipeline steps)
- Intake Agent implementation: `src/intake/intake_agent.py` (current eligibility checks)
- Pipeline workflow: `src/workflow/pipeline.py` (where the gate inserts)
- Activity definitions: `src/workflow/activities.py` (new readiness activity)
- Publisher architecture: `thestudioarc/00-overview.md` (Publisher is the only GitHub writer)
- Meridian review checklist: `thestudioarc/personas/meridian-review-checklist.md` (model for readiness dimensions)
- Outcome Ingestor: `thestudioarc/12-outcome-ingestor.md` (learning signal source)
- Reputation Engine: `thestudioarc/06-reputation-engine.md` (weight update patterns)
- Repo registration lifecycle: `thestudioarc/00-overview.md` (trust tiers: Observe/Suggest/Execute)
- Admin UI: `thestudioarc/23-admin-control-ui.md` (metrics exposure)
- Domain objects: `.claude/rules/domain-objects.md` (TaskPacket, Intent Specification)
- Pipeline stage mapping: `.claude/rules/pipeline-stages.md`
- Existing epics for format reference: `docs/epics/epic-15-e2e-integration-real-repo.md`
- OKRs: `thestudioarc/personas/MERIDIAN-TEAM-REVIEW-AND-OKRS.md`

## 4. Acceptance Criteria

**AC-1: A Readiness Scoring Engine evaluates enriched issues across defined dimensions.**
A function `score_readiness(enriched_taskpacket, issue_title, issue_body, complexity_index, risk_flags) -> ReadinessScore` exists in `src/readiness/scorer.py`. It evaluates 6 dimensions:
1. **Goal clarity** — Can a goal statement be extracted beyond the title alone? (Does the body contain a problem description > 20 words?)
2. **Acceptance criteria** — Are testable acceptance criteria present? (Checkboxes, bullet lists under "acceptance criteria" or "requirements" headings, or structured issue form fields)
3. **Scope boundaries** — Are non-goals or out-of-scope items stated? (Required for complexity >= medium)
4. **Risk coverage** — For each risk flag set by Context, is there a corresponding constraint or acknowledgment in the issue? (e.g., `risk:auth` requires security-related acceptance criteria)
5. **Reproduction / context** — For bug-type issues, are reproduction steps or environment details present?
6. **Dependency awareness** — For feature-type issues at complexity >= high, are external dependencies mentioned?

Each dimension produces a score (0.0–1.0) and a human-readable reason. The composite `ReadinessScore` includes: `overall_score` (weighted average), `dimension_scores` (dict), `missing_dimensions` (list of dimensions that scored below threshold), `recommended_questions` (list of specific clarification questions), and `gate_decision` (pass/hold/escalate).

**AC-2: The Readiness Gate integrates into the pipeline between Context and Intent.**
A new Temporal activity `readiness_activity` exists in `src/workflow/activities.py`. The pipeline workflow in `src/workflow/pipeline.py` calls this activity after `context_activity` and before `intent_activity`. The activity:
- Calls `score_readiness()` with the enriched TaskPacket data
- If `gate_decision == "pass"`: proceeds to Intent normally
- If `gate_decision == "hold"`: updates TaskPacket status to `clarification_requested`, emits a `readiness_hold` signal, and returns a `ReadinessOutput` with `proceed=False` and `clarification_questions`
- If `gate_decision == "escalate"`: updates TaskPacket status to `human_review_required` and emits a `readiness_escalate` signal

The gate checks the repo's trust tier to determine enforcement level:
- Observe: always passes (scores are recorded but not enforced)
- Suggest: holds low-readiness issues
- Execute: holds low-readiness issues; escalates high-risk + low-readiness combinations

**AC-3: Clarification requests are posted to GitHub via Publisher.**
When the gate holds an issue, a structured clarification comment is posted to the GitHub issue via the Publisher path (not directly by the readiness agent). The comment includes:
- A header: "TheStudio needs more information before this issue can be processed"
- A numbered list of specific questions (from `recommended_questions`), each tied to a readiness dimension
- A checklist format so the submitter can address each question
- A footer explaining that the issue will be re-evaluated when the submitter responds or edits the issue body
- The `<!-- thestudio-readiness -->` HTML comment marker for programmatic detection

The comment does NOT reveal internal scoring, complexity index values, or pipeline internals. It reads as a helpful, professional request for clarification.

**AC-4: Issue updates trigger re-evaluation.**
When a held issue receives a comment or body edit (detected via GitHub webhook), the pipeline re-evaluates readiness:
- The Ingress Service recognizes `issue_comment.created` and `issues.edited` events for issues in `clarification_requested` status
- A re-evaluation workflow runs the Readiness Gate again with the updated issue content
- If readiness now passes, the TaskPacket status moves to `ready` and the pipeline resumes from Intent
- If readiness still fails, the existing clarification comment is updated (not duplicated) with remaining questions
- A maximum of 3 re-evaluation cycles is enforced. After 3 holds, the issue is escalated to human review regardless of tier.

**AC-5: Gate thresholds are calibrated by Complexity Index.**
The readiness gate does not apply the same bar to every issue. Thresholds are based on `complexity_index["score"]` — the numeric score sub-field of the TaskPacket's `complexity_index` JSON dict (which also contains `band` and `dimensions` fields):
- **Low complexity** (`complexity_index["score"]` < 3): Only goal clarity and acceptance criteria are required. Scope boundaries and dependency awareness are informational only.
- **Medium complexity** (`complexity_index["score"]` 3–6): All 6 dimensions are evaluated. Scope boundaries become required.
- **High complexity** (`complexity_index["score"]` > 6): All 6 dimensions are required. Missing any dimension triggers a hold. Risk coverage failures trigger escalation.

Thresholds are configurable per repo profile and globally via Admin API. Default thresholds are defined in `src/readiness/config.py`.

**AC-6: Outcome signals feed back into gate calibration.**
The Outcome Ingestor connects `intent_gap` defects from QA to the Readiness Gate:
- When QA emits a `qa_defect` signal with `category=intent_gap`, the Outcome Ingestor records a `readiness_miss` event linking the original `ReadinessScore` to the downstream failure
- A `readiness_miss` means the gate passed an issue that later caused an `intent_gap` defect
- The `ReadinessCalibrator` (batch job or periodic task) analyzes `readiness_miss` events and adjusts dimension weights:
  - Dimensions that consistently missed on issues that later failed get higher weights
  - Dimensions that flagged issues that later succeeded get lower weights
- Weight adjustments are logged and auditable. No adjustment exceeds ±10% per calibration cycle.
- Calibration runs per-repo (repo-specific patterns) and globally (cross-repo patterns)

**AC-7: Readiness metrics are exposed in the Admin UI.**
The Admin API exposes readiness gate metrics:
- Pass/hold/escalate rate per repo (time series)
- Average readiness score per repo (time series)
- Top missing dimensions per repo (ranked list)
- Re-evaluation success rate (how often clarification resolves the hold)
- `readiness_miss` rate (issues that passed but caused `intent_gap` defects)
- Dimension weight history (for calibration transparency)

The Admin UI displays these metrics on a "Readiness" tab in the repo detail view and on the global dashboard.

**AC-8: The Readiness Gate has comprehensive test coverage.**
- Unit tests for `score_readiness()` covering all 6 dimensions, edge cases (empty body, no labels, all risk flags), and complexity-based threshold calibration
- Unit tests for clarification question generation (questions are specific, not generic)
- Integration test: full pipeline with a low-readiness issue that triggers hold → clarification → re-evaluation → pass → Intent → completion
- Integration test: high-risk + low-readiness issue triggers escalation
- Integration test: Observe tier records scores but does not block
- All tests pass without Docker, API keys, or external services

### 4b. Top Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Gate is too strict — blocks legitimate issues that Context could have resolved | Medium | High | Placing the gate after Context enrichment (not before Intake) lets enrichment answer questions first. Complexity-based thresholds prevent over-gating simple issues. Observe tier lets teams see scores before enforcement. |
| Gate is too lenient — passes issues that still cause `intent_gap` defects | Medium | Medium | Learning loop (AC-6) adjusts weights based on outcome signals. Initial thresholds are conservative (favor holding over passing). |
| Clarification comments annoy submitters or feel robotic | Medium | High | Comment template is professionally written, asks specific questions (not generic "please provide more detail"), and includes a checklist format. Template is reviewable in Admin UI. |
| Re-evaluation loop becomes infinite or spammy | Low | High | Hard cap of 3 re-evaluations before escalation. Comment updates (not duplicates). Rate limiting on webhook processing. |
| Calibration loop oscillates (weights swing back and forth) | Medium | Medium | ±10% cap per calibration cycle. Minimum sample size before adjustment. Calibration history is logged and auditable. |
| Pipeline latency increases with new gate step | Low | Low | Gate is a lightweight scoring function (no LLM calls in Phase 1). Expected latency < 50ms. |
| Existing pipeline tests break when new activity is inserted | Medium | Medium | New activity is inserted with a feature flag. Tests updated in Story 16.8. Existing tests continue to pass with gate disabled. |

## 5. Constraints & Non-Goals

**Constraints:**
- The Readiness Gate MUST sit after Context enrichment (not before Intake) — enrichment may resolve ambiguity
- The gate MUST NOT write to GitHub directly — all writes go through Publisher path
- The gate MUST respect trust tiers — Observe tier never blocks, Suggest tier holds, Execute tier holds and escalates
- Phase 1 scoring is rule-based (no LLM calls) — LLM-assisted scoring is a future enhancement
- Clarification comments MUST NOT reveal internal pipeline state, complexity scores, or scoring weights to external users
- Gate thresholds MUST be configurable per repo profile (repos have different issue quality norms)
- Calibration weight adjustments MUST be capped at ±10% per cycle and logged for audit
- The gate MUST be insertable with a feature flag so existing pipelines are not disrupted during rollout
- Re-evaluation is capped at 3 cycles before mandatory escalation
- All code follows existing conventions: type annotations on public interfaces, structured logging with correlation_id, async where needed

**Non-Goals:**
- LLM-powered issue analysis or rewriting (future epic — Phase 2 of readiness gate)
- Auto-fixing issues (the gate asks questions, it does not rewrite the submitter's issue)
- Replacing human judgment for high-risk decisions (escalation goes to humans, not to a smarter model)
- Modifying the Meridian persona or review checklist (the gate is inspired by Meridian, not a replacement)
- Scoring PR quality (this gate is for issues/requirements, not for code review)
- Real-time scoring during issue authoring (GitHub does not support pre-submit hooks; scoring happens on webhook)
- Multi-language support for clarification comments (English only in Phase 1)
- Blocking issues at Observe tier (Observe is read-only by design)
- Modifying the Context Manager or Intent Builder logic (this epic adds a new stage, not changes existing ones)

## 6. Stakeholders & Roles

| Role | Who | Responsibility |
|------|-----|---------------|
| **Epic Owner** | Platform Lead | Scope decisions, priority calls, approve gate thresholds and clarification templates |
| **Tech Lead** | Core Engineer | Readiness scoring engine architecture, pipeline integration, calibration loop design |
| **QA** | Quality Engineer | Test coverage, validate gate behavior at all trust tiers, review clarification comment quality |
| **UX/Content** | Technical Writer | Review clarification comment templates for tone, clarity, and professionalism |
| **DevOps** | Infrastructure Engineer | Admin API endpoints, metrics exposure, feature flag setup |
| **External Team Rep** | Beta Repo Maintainer | User-test clarification comments, provide feedback on gate behavior at Observe tier |

*Note: Role assignments are placeholders for a solo-developer project. All roles are fulfilled by the primary developer; the external team rep role is a future beta test checkpoint.*

## 7. Success Metrics

| Metric | Target | How Measured |
|--------|--------|-------------|
| `intent_gap` defect rate reduction | 50% reduction within 4 weeks of Execute-tier enforcement (measured on Suggest + Execute tier repos only; Observe tier excluded since gate does not block there) | QA defect signals filtered by `category=intent_gap`, compared to pre-gate baseline per repo |
| Readiness gate hold rate | 15–30% of issues held at Suggest/Execute tier (too low = gate is useless, too high = gate is too strict) | `readiness_hold` signal count / total issues processed |
| Clarification resolution rate | 70%+ of held issues resolve within 1 re-evaluation cycle | `readiness_pass` after hold / total holds |
| Pipeline single-pass success rate improvement | 10% improvement within 4 weeks | Verification + QA pass on first attempt, compared to pre-gate baseline |
| Submitter satisfaction | No increase in issue abandonment rate after gate deployment | Issues that receive clarification request but are never updated, compared to baseline |
| Gate latency | < 100ms p99 | OpenTelemetry span timing on `readiness_activity` |
| Calibration stability | Weight drift < 5% per week after initial 2-week burn-in | Calibration log analysis |

## 8. Context & Assumptions

**Assumptions:**
- The Context Manager's `Complexity Index` is computed and available on the TaskPacket before the Readiness Gate runs (confirmed by pipeline order: Context runs before the gate)
- Risk flags (`risk_security`, `risk_breaking`, `risk_cross_team`, `risk_data`) are set by Context and available on the TaskPacket (confirmed by `src/intake/effective_role.py` and Context Manager responsibilities)
- The Publisher can post structured comments to GitHub issues (not just PRs) — if not currently supported, Story 16.4 adds this capability
- GitHub webhook events `issue_comment.created` and `issues.edited` are received by the Ingress Service (confirmed by `thestudioarc/00-overview.md` webhook configuration)
- The Outcome Ingestor already persists `qa_defect` signals with category classification (confirmed by `thestudioarc/14-qa-quality-layer.md`)
- The Admin UI framework supports adding new tabs and metric views (confirmed by existing Admin UI patterns in `src/admin/`)
- The Temporal workflow supports inserting a new activity between existing steps without breaking the activity chain (standard Temporal pattern)
- Feature flags can be implemented via repo profile fields (new field: `readiness_gate_enabled: bool`)

**Dependencies:**
- **[BLOCKING — VERIFIED]** Context Manager must compute and persist Complexity Index on TaskPacket before readiness scoring. **Status: Confirmed** — `complexity_index` field exists on TaskPacket model (`src/models/taskpacket.py:127`), and Context Manager architecture specifies this responsibility. Owner: Tech Lead. **Verified: 2026-03-10.**
- **[BLOCKING — VERIFIED]** Publisher must support posting comments to GitHub issues (not just creating PRs). **Status: Already works.** The `add_comment()` method in `src/publisher/github_client.py` uses the GitHub Issues API endpoint (`/repos/{owner}/{repo}/issues/{number}/comments`), which works for both issues and PRs (PRs are issues in GitHub's API). The `pr_number` parameter name is misleading but functionally correct for issues. Owner: Tech Lead. **Verified: 2026-03-10.**
- **[RESOLVED]** Epic 15 integration tests (for validating gate insertion does not break existing pipeline flow). **Status: Complete** — committed in `5e5b0a8` on 2026-03-10.
- `intent_gap` defect signals from QA — already implemented across 12 source files including `src/qa/defect.py`, `src/outcome/ingestor.py`, and `src/workflow/activities.py`. Verified: 2026-03-10.

**Systems Affected:**
- `src/readiness/` — NEW module (scorer, config, models)
- `src/workflow/pipeline.py` — modified to insert readiness activity
- `src/workflow/activities.py` — new `readiness_activity`
- `src/models/taskpacket.py` — new status values (`clarification_requested`, `human_review_required`)
- `src/publisher/` — new capability: post clarification comments to issues
- `src/ingress/` — handle re-evaluation triggers from issue updates
- `src/outcome/` — connect `intent_gap` signals to readiness calibration
- `src/admin/` — new API endpoints and UI tab for readiness metrics
- `tests/unit/test_readiness/` — unit tests for scoring engine
- `tests/integration/` — integration tests for gate behavior

**Business Rules:**
- Gates fail closed: if the readiness scorer errors, the issue is held (not passed through)
- Publisher is the only GitHub writer: the readiness gate produces a clarification request, Publisher posts it
- Observe tier is read-only: readiness scores are recorded but never block issues or post comments
- The gate does not replace human judgment: escalation always goes to a human, never to a "smarter" automated review
- Clarification comments are professional and specific: they name what's missing, not just "please provide more detail"
- The gate is additive: it does not modify the Context Manager, Intent Builder, or existing pipeline stages

---

## Story Map

Stories are ordered by vertical slice: scoring engine first, pipeline integration second, learning loop third, Admin UI last.

---

### Story 16.1: Readiness Score Data Model and Configuration

**As a** platform developer,
**I want** a well-defined data model for readiness scores and configurable thresholds,
**so that** the scoring engine and gate have clear contracts to build against.

**Details:**
- Create `src/readiness/__init__.py`
- Create `src/readiness/models.py` with:
  - `ReadinessDimension` enum: `GOAL_CLARITY`, `ACCEPTANCE_CRITERIA`, `SCOPE_BOUNDARIES`, `RISK_COVERAGE`, `REPRODUCTION_CONTEXT`, `DEPENDENCY_AWARENESS`
  - `DimensionScore` dataclass: `dimension: ReadinessDimension`, `score: float` (0.0–1.0), `reason: str`, `required: bool`
  - `GateDecision` enum: `PASS`, `HOLD`, `ESCALATE`
  - `ReadinessScore` dataclass: `overall_score: float`, `dimension_scores: dict[ReadinessDimension, DimensionScore]`, `missing_dimensions: list[ReadinessDimension]`, `recommended_questions: list[str]`, `gate_decision: GateDecision`, `complexity_tier: str`, `timestamp: datetime`
  - `ReadinessOutput` dataclass (activity output): `proceed: bool`, `score: ReadinessScore`, `clarification_questions: list[str]`, `hold_reason: str | None`
- Create `src/readiness/config.py` with:
  - `ReadinessThresholds` dataclass: per-dimension pass thresholds, overall pass threshold, dimension weights
  - `DEFAULT_THRESHOLDS` for low/medium/high complexity tiers
  - Thresholds loadable from repo profile override

**Acceptance Criteria:**
- All data models are frozen dataclasses with type annotations
- `GateDecision` logic is deterministic given scores and thresholds
- Default thresholds exist for all 3 complexity tiers
- Unit tests validate threshold loading and decision logic

**Files to create:**
- `src/readiness/__init__.py`
- `src/readiness/models.py`
- `src/readiness/config.py`
- `tests/unit/test_readiness/__init__.py`
- `tests/unit/test_readiness/test_models.py`

---

### Story 16.2: Readiness Scoring Engine — 6-Dimension Evaluator

**As a** platform developer,
**I want** a scoring engine that evaluates issue quality across 6 readiness dimensions,
**so that** the gate can make informed pass/hold/escalate decisions.

**Details:**
- Create `src/readiness/scorer.py` with `score_readiness()` function
- Implement 6 dimension scorers (rule-based, no LLM):
  1. **Goal clarity:** Check if issue body contains a problem description beyond the title. Score based on: body length > 50 chars (0.3), contains "problem" / "bug" / "feature" / "should" keywords (0.3), first paragraph is a coherent statement not just a heading (0.4)
  2. **Acceptance criteria:** Reuse `extract_acceptance_criteria()` from `src/intent/intent_builder.py`. Score: 0 criteria = 0.0, 1 criterion = 0.5, 2+ criteria = 0.8, criteria with checkbox format = 1.0
  3. **Scope boundaries:** Reuse `extract_non_goals()` from `src/intent/intent_builder.py`. Score: 0 non-goals and complexity >= medium = 0.0, 1+ non-goals = 0.7, explicit "out of scope" section = 1.0
  4. **Risk coverage:** For each risk flag in the TaskPacket, check if the issue body mentions related terms (security, auth, billing, migration, etc.). Score: all risk flags covered = 1.0, partial = proportional, no risk flags = 1.0 (n/a)
  5. **Reproduction context:** For bug-type issues, check for "steps to reproduce", "expected", "actual", "environment" sections. Score: 0 = 0.0, partial = 0.5, full = 1.0. For non-bug issues: 1.0 (n/a)
  6. **Dependency awareness:** For complexity >= high, check for mentions of "depends on", "requires", "blocked by", team names, or external service mentions. Score: mentions found = 1.0, none found and complexity high = 0.3, complexity < high = 1.0 (n/a)
- Compute `overall_score` as weighted average using complexity-tier-appropriate weights from config
- Generate `recommended_questions` for each dimension that scored below threshold — questions must be specific (e.g., "What are the expected vs actual behaviors?" not "Please provide more detail")
- Determine `gate_decision` based on overall score, missing required dimensions, and trust tier

**Acceptance Criteria:**
- `score_readiness()` returns a complete `ReadinessScore` for any valid input
- Each dimension scorer has independent unit tests with edge cases
- Question generation produces specific, actionable questions (no generic prompts)
- The scoring function is pure (no I/O, no database, no external calls) and runs < 10ms
- Reuses existing extraction functions from `intent_builder.py` (no duplication)

**Files to create:**
- `src/readiness/scorer.py`
- `tests/unit/test_readiness/test_scorer.py`

---

### Story 16.3: Pipeline Integration — Readiness Activity and Workflow Insertion

**As a** platform operator,
**I want** the readiness gate to run automatically between Context and Intent in the pipeline,
**so that** low-quality issues are caught before the pipeline spends compute on them.

**Details:**
- Create `readiness_activity` in `src/workflow/activities.py`:
  - Input: `ReadinessInput` dataclass with `taskpacket_id`, `issue_title`, `issue_body`, `complexity_index`, `risk_flags`, `issue_type`, `trust_tier`, `repo_id`
  - Calls `score_readiness()` from `src/readiness/scorer.py`
  - If `gate_decision == PASS`: returns `ReadinessOutput(proceed=True, ...)`
  - If `gate_decision == HOLD`: updates TaskPacket status, emits `readiness_hold` signal, returns `ReadinessOutput(proceed=False, clarification_questions=[...])`
  - If `gate_decision == ESCALATE`: updates TaskPacket status, emits `readiness_escalate` signal, returns `ReadinessOutput(proceed=False, ...)`
- Modify `src/workflow/pipeline.py` to insert `readiness_activity` between `context_activity` and `intent_activity`:
  - Add feature flag check: `if repo_profile.readiness_gate_enabled:`
  - If gate returns `proceed=False`, the workflow enters a **Temporal signal wait** using `workflow.wait_condition()` or `workflow.wait_signal("readiness_cleared")`. Signal-based waiting is the correct pattern because re-evaluation is triggered by external webhook events (issue edits/comments), not by elapsed time. The Ingress Service sends the `readiness_cleared` signal to the workflow when it processes a re-evaluation trigger (Story 16.5).
  - If gate returns `proceed=True`, the workflow continues to `intent_activity` normally
  - Timeout: if no re-evaluation signal arrives within 7 days, the workflow fails with `gate_decision=TIMEOUT` and the TaskPacket is moved to `stale` status
- **Trust tier resolution:** The `trust_tier` for the readiness activity input is read from the repo profile (`repo_profile.tier`, type `RepoTier` enum with values `observe`, `suggest`, `execute`, defined in `src/repo/repo_profile.py`) in the pipeline workflow, the same way the existing pipeline resolves repo-level configuration. The pipeline workflow already receives `repo_id` in `PipelineInput`; it queries the repo profile at workflow start and passes `repo_profile.tier` to the readiness activity input as `trust_tier`.
- Add `readiness_gate_enabled: bool = False` to repo profile model (default off for backward compatibility)
- Emit structured log: `readiness.gate.evaluated` with `correlation_id`, `overall_score`, `gate_decision`, `missing_dimensions`

**Acceptance Criteria:**
- Pipeline workflow compiles and existing tests pass with `readiness_gate_enabled=False` (no behavior change)
- With `readiness_gate_enabled=True`, the readiness activity runs between Context and Intent
- A high-readiness issue passes through the gate without delay
- A low-readiness issue in Suggest/Execute tier triggers a hold
- A low-readiness issue in Observe tier passes through (score recorded only)
- Structured logging includes all required fields

**Files to modify:**
- `src/workflow/activities.py` — add `readiness_activity`
- `src/workflow/pipeline.py` — insert gate after context, before intent
- `src/models/taskpacket.py` — add `clarification_requested` and `human_review_required` status values

**Files to create:**
- `tests/unit/test_readiness/test_activity.py`

---

### Story 16.4: Clarification Comment via Publisher

**As a** submitter of a GitHub issue,
**I want** to receive a clear, specific, professional request for clarification when my issue needs more detail,
**so that** I can provide the right information without guessing what the system needs.

**Details:**
- Create `src/readiness/clarification.py` with `format_clarification_comment(readiness_score: ReadinessScore, repo_name: str) -> str`:
  - Header: `## More Information Needed`
  - Intro paragraph: Professional, friendly explanation that TheStudio analyzed the issue and needs more detail to proceed
  - Numbered question list: Each question tied to a specific missing dimension, with context about why it matters
  - Checklist format: Each question has a checkbox so the submitter can track what they've addressed
  - Footer: "When you've addressed these questions, edit the issue description or add a comment and we'll re-evaluate automatically."
  - HTML marker: `<!-- thestudio-readiness -->` for programmatic detection
  - The comment MUST NOT mention scores, thresholds, complexity index, or internal pipeline concepts
- Verify Publisher can post comments to GitHub issues (not just PRs):
  - If `src/publisher/` already supports issue comments, use existing capability
  - If not, add `post_issue_comment(repo, issue_number, body)` to Publisher
- The readiness activity calls Publisher to post the comment when `gate_decision == HOLD`

**Example clarification comment for a bug with no reproduction steps and no acceptance criteria:**
```markdown
## More Information Needed

TheStudio needs a bit more detail before it can work on this issue.

- [ ] **What should happen vs what actually happens?** Describing the expected and actual behavior helps us verify the fix is correct.
- [ ] **How can we reproduce this?** Steps to reproduce, browser/OS, or a minimal example help us find the root cause.
- [ ] **How will we know this is fixed?** Adding acceptance criteria (e.g., "Login completes within 3 seconds") gives us a clear definition of done.

When you've addressed these questions, edit the issue description or add a comment and we'll re-evaluate automatically.

<!-- thestudio-readiness -->
```

**Acceptance Criteria:**
- Clarification comment is professional, specific, and actionable
- Comment contains `<!-- thestudio-readiness -->` marker
- Comment does not reveal internal scoring or pipeline state
- Publisher posts the comment via its standard GitHub write path (not a direct API call from readiness)
- Unit tests validate comment generation for all 6 dimension combinations
- Comment is under 1000 characters for typical 2-3 question scenarios (concise, not walls of text)

**Files to create:**
- `src/readiness/clarification.py`
- `tests/unit/test_readiness/test_clarification.py`

**Files to modify:**
- `src/publisher/` — add issue comment capability if not present

---

### Story 16.5: Re-Evaluation on Issue Update

**As a** submitter who responded to a clarification request,
**I want** my issue to be automatically re-evaluated when I update it,
**so that** I don't have to wait for a human to manually restart the pipeline.

**Details:**
- **Expand webhook handler to support `issue_comment` events (significant change):**
  - The current webhook handler in `src/ingress/webhook_handler.py` (line 74) filters on event type (`x_github_event == "issues"`) and rejects non-issue events. It currently accepts ALL issue action types (opened, edited, closed, etc.) without filtering on specific actions. This story must:
    1. Add `"issue_comment"` to the accepted event types in the webhook handler
    2. Parse `issue_comment.created` payloads (different structure from `issues` payloads — the issue data is nested under `payload.issue`, not at the top level)
    3. For re-evaluation purposes, handle `issues` events with `action == "edited"` (already accepted by the handler but not specifically processed for readiness re-evaluation)
    4. Validate HMAC signatures for the new event types (same secret, but verify payload structure compatibility)
  - This is NOT a one-line filter change — it requires new payload parsing logic and test coverage for the different payload shapes
- Modify `src/ingress/` to handle re-evaluation triggers:
  - When `issue_comment.created` or `issues.edited` webhook arrives for an issue with TaskPacket status `clarification_requested`:
    - Look up the existing TaskPacket by repo + issue number
    - Send a `readiness_cleared` Temporal signal to the waiting workflow (see Story 16.3 for signal-based wait pattern)
    - The workflow re-runs Context → Readiness Gate with updated issue content
    - If gate passes: update TaskPacket status to `ready`, resume pipeline from Intent
    - If gate still fails: update existing clarification comment (via Publisher) with remaining questions
    - If re-evaluation count >= 3: escalate to human review regardless of score
  - Debounce: if multiple updates arrive within 60 seconds, only process the last one
- Add `readiness_evaluation_count: int` to TaskPacket to track re-evaluation cycles
- Add `readiness_hold_comment_id: str | None` to TaskPacket to enable comment updates (not duplicates)

**Acceptance Criteria:**
- Webhook handler accepts `issue_comment.created` events (not just `issues` events)
- Webhook handler accepts `issues.edited` events (not just `issues.opened` and `issues.labeled`)
- `issue_comment` payload parsing correctly extracts issue number and body from nested structure
- HMAC validation works for `issue_comment` event payloads
- Issue body edit triggers re-evaluation for issues in `clarification_requested` status
- Issue comment triggers re-evaluation for issues in `clarification_requested` status
- Re-evaluation sends `readiness_cleared` Temporal signal to the waiting workflow
- Re-evaluation that passes resumes the pipeline from Intent (not from Intake)
- Re-evaluation that fails updates the existing comment (does not post a new one)
- 3rd failed re-evaluation escalates to human review
- Debouncing prevents rapid-fire re-evaluations
- Non-held issues are not affected by comment/edit webhooks (no spurious re-evaluations)
- Unit tests cover all new webhook event types and payload parsing

**Files to modify:**
- `src/ingress/webhook_handler.py` — expand event type filter, add `issue_comment` parsing
- `src/ingress/` — add re-evaluation trigger handling
- `src/models/taskpacket.py` — add `readiness_evaluation_count`, `readiness_hold_comment_id`
- `src/workflow/pipeline.py` — handle `readiness_cleared` signal to resume from Intent

**Files to create:**
- `tests/unit/test_readiness/test_reevaluation.py`

---

### Story 16.6: Outcome Signal Feedback — `intent_gap` to Readiness Calibration

**As a** platform operator,
**I want** the readiness gate to learn from downstream `intent_gap` defects,
**so that** gate thresholds improve over time and fewer bad issues slip through.

**Details:**
- Create `src/readiness/calibrator.py` with:
  - `ReadinessCalibrator` class that:
    - Queries `readiness_miss` events (issues where gate passed but QA reported `intent_gap`)
    - Analyzes which dimensions were scored high on issues that later failed
    - Adjusts dimension weights: increase weight on dimensions that consistently missed, decrease on dimensions that over-flagged
    - Caps weight adjustment at ±10% per calibration cycle
    - Requires minimum 20 samples before making adjustments
    - Logs all adjustments with before/after weights, sample size, and rationale
  - `record_readiness_miss(taskpacket_id, readiness_score, defect_category)` function called by Outcome Ingestor when `intent_gap` is detected
- Modify `src/outcome/` to call `record_readiness_miss()` when a `qa_defect` signal with `category=intent_gap` is received and the TaskPacket has a stored `ReadinessScore`
- Calibration runs as a periodic task (daily or on-demand via Admin API)
- Per-repo calibration (repos have different issue quality norms) and global calibration (cross-repo patterns)

**Acceptance Criteria:**
- `readiness_miss` events are recorded when `intent_gap` defects occur on gate-passed issues
- Calibrator adjusts weights based on accumulated miss data
- Weight adjustments are capped at ±10% per cycle
- Minimum sample size of 20 is enforced before any adjustment
- All adjustments are logged with full audit trail
- Unit tests verify calibration math with synthetic miss data
- Unit test verifies weight cap enforcement

**Files to create:**
- `src/readiness/calibrator.py`
- `tests/unit/test_readiness/test_calibrator.py`

**Files to modify:**
- `src/outcome/` — add `record_readiness_miss()` call on `intent_gap` detection

---

### Story 16.7: Admin UI — Readiness Metrics Dashboard

**As a** platform operator,
**I want** to see readiness gate metrics in the Admin UI,
**so that** I can monitor issue quality trends, gate effectiveness, and calibration behavior.

**Details:**
- Add Admin API endpoints:
  - `GET /admin/readiness/metrics?repo_id=&period=7d` — returns pass/hold/escalate counts, average scores, top missing dimensions
  - `GET /admin/readiness/calibration?repo_id=` — returns current dimension weights, recent adjustments, miss rate
  - `PUT /admin/readiness/thresholds?repo_id=` — update per-repo threshold overrides
  - `POST /admin/readiness/calibrate?repo_id=` — trigger on-demand calibration
- Add "Readiness" tab to repo detail view in Admin UI:
  - Time-series chart: pass/hold/escalate rates over time
  - Bar chart: top missing dimensions (which questions are most commonly asked)
  - Table: recent held issues with scores and resolution status
  - Calibration panel: current weights, last adjustment date, miss rate
- Add readiness summary to global dashboard:
  - Aggregate pass/hold/escalate rate across all repos
  - Repos with highest hold rates (may need issue template improvements)

**Acceptance Criteria:**
- All 4 Admin API endpoints exist and return correctly shaped responses
- Readiness tab renders in Admin UI with charts and tables
- Threshold updates via Admin API are reflected in subsequent gate evaluations
- On-demand calibration can be triggered from Admin UI
- Unit tests for API endpoints
- (If Admin UI uses Playwright tests) One Playwright test verifying the Readiness tab loads

**Files to create:**
- `src/admin/readiness_routes.py`
- `tests/unit/test_admin/test_readiness_routes.py`

**Files to modify:**
- `src/admin/router.py` — register readiness routes
- Admin UI templates/components — add Readiness tab

---

### Story 16.8: Integration Tests and Pipeline Compatibility

**As a** developer maintaining the pipeline,
**I want** comprehensive integration tests for the readiness gate,
**so that** I can verify gate behavior end-to-end and ensure it does not break existing pipeline tests.

**Details:**
- Create integration tests in `tests/integration/test_readiness_gate.py`:
  1. **Happy path — high-readiness issue passes gate:** Issue with clear goal, acceptance criteria, and scope boundaries → gate passes → pipeline continues to Intent → completes normally
  2. **Hold path — low-readiness issue at Suggest tier:** Issue with just a title and no body → gate holds → clarification comment generated → re-evaluation with improved issue → gate passes → pipeline completes
  3. **Escalation path — high-risk + low-readiness at Execute tier:** Issue with `risk:auth` flag but no security-related acceptance criteria → gate escalates → human review required
  4. **Observe tier — scores recorded, not enforced:** Low-readiness issue at Observe tier → gate records score → pipeline continues to Intent without hold
  5. **Feature flag off — gate skipped:** Issue processed with `readiness_gate_enabled=False` → no readiness activity runs → pipeline behaves exactly as before
  6. **Re-evaluation cap — 3 holds then escalate:** Issue fails readiness 3 times → escalated to human review
- Verify all existing integration tests from Epic 15 still pass with the gate feature flag off
- Add mock readiness activity to Epic 15's mock providers (`tests/integration/mock_providers.py`)

**Acceptance Criteria:**
- All 6 integration test scenarios pass
- All existing integration tests pass unchanged (gate feature flag defaults to off)
- Mock readiness activity is available for other integration tests
- Tests run without Docker, API keys, or external services
- Test for Observe tier confirms no GitHub writes occur

**Files to create:**
- `tests/integration/test_readiness_gate.py`

**Files to modify:**
- `tests/integration/mock_providers.py` — add mock readiness activity
- `tests/integration/conftest.py` — add readiness fixtures if needed

---

### Story 16.9: Issue Template Recommendations (Documentation)

**As a** platform operator onboarding a new repository,
**I want** recommended GitHub issue templates that align with readiness gate expectations,
**so that** submitters provide the right information upfront and reduce hold rates.

**Details:**
- Create `docs/issue-templates/` directory with recommended GitHub issue form templates:
  - `bug-report.yml` — includes: description, steps to reproduce, expected behavior, actual behavior, environment, acceptance criteria checklist
  - `feature-request.yml` — includes: problem statement, proposed solution, acceptance criteria, out of scope, dependencies
  - `refactor.yml` — includes: what and why, scope boundaries, acceptance criteria, affected services
- Each template maps to readiness dimensions:
  - Description field → goal clarity
  - Steps to reproduce → reproduction context
  - Acceptance criteria field → acceptance criteria dimension
  - Out of scope field → scope boundaries dimension
- Create `docs/readiness-gate-guide.md` documenting:
  - What the readiness gate does (user-facing explanation, no internal architecture details)
  - How to write issues that pass the gate on first evaluation
  - How to respond to clarification requests
  - FAQ: "Will this slow me down?" "Can I override it?" "How does it learn?"
- Add readiness gate section to `docs/ONBOARDING.md`

**Acceptance Criteria:**
- 3 issue form templates exist in `docs/issue-templates/`
- Templates are valid GitHub issue form YAML (can be copied into `.github/ISSUE_TEMPLATE/`)
- `docs/readiness-gate-guide.md` exists and is written for external teams (not internal developers)
- Onboarding doc references the readiness gate and links to the guide
- Each template field maps to at least one readiness dimension (documented in a comment in the YAML)

**Files to create:**
- `docs/issue-templates/bug-report.yml`
- `docs/issue-templates/feature-request.yml`
- `docs/issue-templates/refactor.yml`
- `docs/readiness-gate-guide.md`

**Files to modify:**
- `docs/ONBOARDING.md` — add readiness gate section

---

## Sprint Mapping (Suggested)

Sprints are **2 weeks (10 working days)** each. Capacity assumes 80% commitment / 20% buffer per sprint (8 effective days).

### Sprint 17 — Foundation and Gate (Stories 16.1–16.4)
- 16.1: Data model and config (1 day)
- 16.2: Scoring engine (2 days)
- 16.3: Pipeline integration (2 days)
- 16.4: Clarification comment (1 day)
- **Total: 6 days / 8 available — 2 days buffer**
- **Sprint goal:** A developer can enable the readiness gate on a test repo, submit a low-quality issue, and receive a structured clarification comment. The gate passes high-quality issues without delay. **Test:** Enable gate on a test repo, submit an issue with only a title, verify a clarification comment appears within 30 seconds.

### Sprint 18 — Learning and Polish (Stories 16.5–16.9)
- 16.5: Re-evaluation on issue update (3 days — increased to account for webhook handler expansion)
- 16.6: Outcome signal feedback (1 day)
- 16.7: Admin UI metrics (2 days)
- 16.8: Integration tests (1 day)
- 16.9: Issue templates and documentation (1 day)
- **Total: 8 days / 8 available — at capacity, no buffer. If Story 16.5 webhook changes are larger than expected, Story 16.9 can slip to Sprint 19.**
- **Sprint goal:** The readiness gate learns from downstream failures, operators can monitor gate behavior in Admin UI, and external teams have documentation and templates to write gate-ready issues. **Test:** Submit a low-quality issue, respond to clarification, verify re-evaluation passes and pipeline completes. View readiness metrics in Admin UI.

---

## Meridian Review Status

### Round 1: Conditional Pass — 3 gaps addressed

**Date:** 2026-03-10
**Verdict:** Conditional Pass with 3 blocking gaps

| # | Gap | Resolution |
|---|-----|------------|
| 1 | Dependencies had owners but no dates; Publisher issue-comment capability listed as "needs verification" | All dependencies now have verification dates (2026-03-10). Publisher `add_comment()` verified — uses GitHub Issues API which works for both PRs and issues. Epic 15 marked as resolved (commit `5e5b0a8`). |
| 2 | Temporal wait-state mechanism ambiguous ("signal or timer-based recheck") — "the AI will figure it out" | Story 16.3 now commits to signal-based waiting via `workflow.wait_signal("readiness_cleared")`. Signal-based is correct because re-evaluation is triggered by external webhook events, not elapsed time. Added 7-day timeout to `stale` status. |
| 3 | Trust tier access pattern unspecified — implementing agent would have to guess | Story 16.3 now specifies: `trust_tier` is read from `repo_profile.tier`, resolved at workflow start from `PipelineInput.repo_id`. |

**Advisory items addressed:**
- Story 16.5 expanded to explicitly call out webhook handler expansion as significant work (new event types, payload parsing, HMAC validation) with dedicated acceptance criteria
- Sprint length clarified as 2 weeks (10 days) with 80/20 capacity/buffer split. Sprint 18 at capacity with Story 16.9 as overflow candidate.
- 50% `intent_gap` reduction target now specifies measurement scope: Suggest + Execute tier repos only (Observe excluded since gate does not block there)

### Round 2: Conditional Pass — 3 inaccuracies fixed

**Date:** 2026-03-10
**Verdict:** Conditional Pass — Round 1 dependency and signal fixes verified as solid. 3 factual inaccuracies found that would trip up an implementing agent.

| # | Issue | Resolution |
|---|-------|------------|
| 1 | Story 16.3 referenced `repo_profile.automation_tier` — field does not exist. Correct field is `repo_profile.tier` (type `RepoTier`, defined in `src/repo/repo_profile.py:46`) | Fixed: all references now use `repo_profile.tier` with type annotation and source file reference |
| 2 | Story 16.5 claimed webhook handler only handles `opened` and `labeled` actions — incorrect, handler accepts all issue actions without filtering | Fixed: description now accurately states handler filters on event type only, accepts all actions |
| 3 | AC-5 used "CI < 3" without specifying it refers to `complexity_index["score"]` sub-field of the JSON dict | Fixed: thresholds now explicitly reference `complexity_index["score"]` |

**Advisory items:**
- Sprint 18 at capacity (8/8 days) — overflow plan documented (Story 16.9 to Sprint 19). Acceptable.
- 50% `intent_gap` reduction target measured on Suggest + Execute tier only (already addressed in Round 1 fixes).

### Round 3: PASS — Ready to commit

**Date:** 2026-03-10
**Verdict:** All 7 checklist questions pass. All Round 1 and Round 2 gaps resolved. No new concerns.

**Status: Ready to commit. Hand to Helm for sprint planning.**
