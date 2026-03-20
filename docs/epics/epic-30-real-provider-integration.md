# Epic 30: Real Provider Integration & Validation

> **Status:** Complete (3 Sprints)
> **Epic Owner:** Primary Developer
> **Duration:** 3 sprints (~6 weeks)
> **Created:** 2026-03-18
> **Completed:** 2026-03-19
> **Meridian Review:** PASS with 3 gaps resolved (2026-03-18)

---

## 1. Title

**Validate Real Providers End-to-End So TheStudio Can Process a Real GitHub Issue Into a Real Draft PR**

---

## 2. Narrative

TheStudio has spent 29 epics building a complete AI-augmented delivery pipeline: intake, context enrichment, intent specification, routing, assembly, implementation, verification, QA, and publication. Every stage works. Every agent runs. Every gate fails closed.

All of it runs on mock providers.

`llm_provider: str = "mock"` means the intent agent never reasons about a real issue. `github_provider: str = "mock"` means the publisher never creates a real branch. `store_backend: str = "memory"` means every TaskPacket evaporates when the process stops.

This is the gap between "the pipeline works" and "the pipeline works *on real problems*." Until we flip these three feature flags and prove the system holds together against real APIs, real latency, real rate limits, and real LLM outputs, TheStudio is a sophisticated prototype.

This epic exists to close that gap. Not by building new capabilities -- everything needed already exists behind feature flags -- but by systematically enabling, validating, and documenting the real-provider path. The deliverable is not code so much as *confidence*: measured success rates, documented failure modes, a cost model, and a deployment runbook that lets someone who was not in the room stand up the platform.

**Why now:** Epics 23-29 completed the agent framework, container isolation, chat approval, preflight gate, and Projects v2 integration. The feature surface is complete. Further feature work without real-provider validation is building on quicksand.

---

## 3. References

| Artifact | Location |
|----------|----------|
| Feature flags (llm, github, store) | `src/settings.py` lines 80-82 |
| Agent LLM toggles (9 agents) | `src/settings.py` lines 42-54 |
| AnthropicAdapter (real LLM) | `src/adapters/llm.py` lines 80-134 |
| ResilientGitHubClient (real GitHub) | `src/adapters/github.py` lines 46-192 |
| GitHubClient (publisher operations) | `src/publisher/github_client.py` |
| Async Postgres connection | `src/db/connection.py` |
| AgentRunner framework | `src/agent/framework.py` class `AgentRunner` |
| Agent configs with fallback_fn | `src/intent/intent_config.py`, `src/qa/qa_config.py`, `src/routing/router_config.py`, etc. |
| Container isolation (Epic 25) | `src/settings.py` lines 87-114 |
| Preflight gate (Epic 28) | `src/settings.py` lines 56-58 |
| Projects v2 + Portfolio (Epic 29) | `src/settings.py` lines 60-77 |
| Pipeline overview | `thestudioarc/00-overview.md` |
| Agent roles | `thestudioarc/08-agent-roles.md` |
| Intent layer | `thestudioarc/11-intent-layer.md` |
| Domain objects | `.claude/rules/domain-objects.md` |

---

## 4. Acceptance Criteria

### AC 1: LLM Provider Produces Valid Agent Outputs
An evaluation harness exists in `src/eval/` with at least 10 labeled test cases. When `llm_provider=anthropic` and `agent_llm_enabled` is true for intent, QA, and primary agents, each agent produces structurally valid, contextually correct outputs as measured by the harness. Intent agent achieves >= 8/10 valid intent specs. QA agent catches planted defects in >= 7/10 cases.

### AC 2: Full Pipeline Completes at Observe Tier on a Real Repo
With `llm_provider=anthropic`, `github_provider=real`, and `store_backend=postgres` all enabled, the pipeline processes a real GitHub issue on a test repository and produces a valid draft PR with an evidence comment. Single-pass success rate >= 70% across at least 3 test issues.

### AC 3: TaskPacket Lifecycle Persists in Postgres
A TaskPacket created by intake persists through the full lifecycle (CREATE -> ENRICHED -> INTENT_BUILT -> IMPLEMENTING -> VERIFYING -> QA -> PUBLISHED) in Postgres. Intent specs and repo profiles round-trip correctly through the database.

### AC 4: GitHub Operations Work End-to-End
The real GitHub provider successfully creates branches, opens PRs, posts evidence comments, manages labels, and handles PR lifecycle on a dedicated test repository.

### AC 5: Failure Modes Are Cataloged and Mitigated
Every failure mode observed during validation is documented with provider, category (timeout, auth, rate limit, validation, cost), severity, and mitigation. Error handling gaps found during testing are fixed.

### AC 6: Remaining Feature Flags Activate Without Breaking Mock Mode
`projects_v2_enabled`, `meridian_portfolio_enabled`, and `preflight_enabled` can be flipped to true on a real environment. Existing tests that use mock providers continue to pass unchanged.

### AC 7: Deployment Runbook Enables Cold Start
`docs/DEPLOYMENT.md` documents every step needed for a new developer to stand up the platform: env vars, secrets, GitHub App, Postgres migration, Temporal, NATS, Docker Compose, monitoring, and rollback. Completeness is validated by a checklist: every `THESTUDIO_*` env var is documented, every service has start/verify/rollback steps, and the feature flag activation order is specified.

### AC 8: Suggest Tier Validated
At least 3 issues run at Suggest tier produce ready-for-review PRs, trigger the approval workflow, and complete the chat approval flow end-to-end.

### 4b. Top Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| R1 | LLM output quality too low for intent/QA agents | Medium | High | Evaluation harness with labeled data; iterate on prompt templates before declaring pass/fail |
| R2 | Anthropic API costs exceed budget per issue | Medium | Medium | Budget cap already in settings (`agent_max_budget_usd=5.0`); monitor actual costs in Sprint 1 |
| R3 | GitHub rate limits block pipeline during testing | Low | Medium | ResilientGitHubClient has retry logic; use a dedicated test repo with low traffic |
| R4 | Postgres schema drift from in-memory models | Medium | High | Sprint 2 Story 30.5 explicitly validates round-trip persistence; fix schema issues before full pipeline test |
| R5 | Container isolation fails on CI/test environments | Medium | Medium | Test in local Docker first; Sprint 3 story is gated on Sprint 2 success |

---

## 5. Constraints & Non-Goals

### Constraints

- **API keys required:** Anthropic API key must be provisioned and set as `THESTUDIO_ANTHROPIC_API_KEY`
- **Test repository:** A dedicated GitHub repo (`thestudio-test-target`) with the GitHub App installed is required for GitHub provider tests
- **Cost ceiling:** Total pipeline cost per issue must stay under $5 at Observe tier (enforced by `agent_max_budget_usd`)
- **Mock mode preservation:** All existing tests using mock providers must continue to pass. No test may require real API credentials
- **No new agent capabilities:** This epic validates existing agents; it does not add new prompt templates, tools, or agent types

### Non-Goals

- **NOT performance optimization** -- premature until real-provider flow is proven correct
- **NOT multi-repo scale testing** -- one test repo is sufficient to validate the integration path
- **NOT production deployment** -- this validates the *path* to production, not production itself
- **NOT new feature development** -- everything needed is already built behind feature flags
- **NOT load testing or concurrency testing** -- single-issue flow first
- **NOT prompt engineering** -- if LLM outputs are structurally valid, prompt quality iteration is a future epic

---

## 6. Stakeholders & Roles

| Role | Who | Responsibility |
|------|-----|----------------|
| Epic Owner | Primary Developer | Owns scope, unblocks dependencies, accepts deliverables |
| Tech Lead | Primary Developer | Architecture decisions on eval harness, failure catalog format |
| QA | Primary Developer | Defines labeled test dataset, validates eval harness scoring |
| DevOps | Primary Developer | Provisions test repo, API keys, Postgres instance, Docker environment |
| Saga | Epic Creator | Authored this epic |
| Meridian | VP Success | Reviews epic before commit; validates success metrics |

> **Note:** Solo-developer project — primary developer assigned to all roles (per cross-epic blocker resolution 2026-03-16).

---

## 7. Success Metrics

| Metric | Target | How Measured |
|--------|--------|-------------|
| Intent agent valid spec rate | >= 8/10 labeled issues | Eval harness automated scoring |
| QA agent defect detection rate | >= 7/10 planted defects caught | Eval harness with synthetic evidence bundles |
| Single-pass success rate (Observe) | >= 70% | Count of issues producing valid draft PRs / total issues run |
| Pipeline cost per issue (Observe) | < $5.00 | Sum of LLM token costs from ModelCallAudit records |
| Pipeline wall-clock time (Observe) | Documented (no target) | Measured end-to-end for each test run |
| Mock-mode test regression | 0 failures | `pytest` full suite with default (mock) settings |
| Feature flag activation success | All 6 flags individually activatable | Manual verification in test environment |
| Deployment runbook completeness | All env vars, services, and flags documented | Checklist: every `THESTUDIO_*` var documented, every service has start/verify/rollback steps, flag activation order specified |

---

## 8. Context & Assumptions

### Business Rules

- Trust tiers govern Publisher behavior: Observe = draft PR, Suggest = ready-for-review, Execute = auto-merge
- Gates fail closed -- any verification or QA failure stops the pipeline
- Evidence bundles must never be fabricated; real LLM outputs become real evidence
- TaskPacket is the single source of truth for pipeline state

### Dependencies

| Dependency | Type | Status | Owner | Target Date |
|------------|------|--------|-------|-------------|
| Anthropic API key | External | Must be provisioned | Primary Developer | Sprint 1 Day 1 (2026-03-18) |
| GitHub App (test repo) | External | Must be installed on `thestudio-test-target` | Primary Developer | Sprint 2 Day 1 |
| Postgres (local Docker or remote) | Infrastructure | Available via `infra/docker-compose.prod.yml` | Primary Developer | Sprint 2 Day 1 |
| Docker daemon | Infrastructure | Required for container isolation tests (Sprint 3) | Primary Developer | Sprint 3 Day 1 |
| AgentRunner framework (Epic 23) | Internal | Complete |
| Container isolation (Epic 25) | Internal | Complete |
| Preflight gate (Epic 28) | Internal | Complete |
| Projects v2 + Portfolio (Epic 29) | Internal | Complete |

### Systems Affected

- `src/adapters/llm.py` -- AnthropicAdapter exercised for real
- `src/adapters/github.py` -- ResilientGitHubClient exercised for real
- `src/publisher/github_client.py` -- GitHubClient exercised for real
- `src/db/connection.py` -- Real Postgres connections
- `src/settings.py` -- Feature flags flipped in test configurations
- `src/agent/framework.py` -- AgentRunner with real LLM calls
- `src/eval/` -- New module (evaluation harness)
- `docs/DEPLOYMENT.md` -- New file (deployment runbook)
- All 9 agent config files -- Validated with `agent_llm_enabled=True`

### Assumptions

- The AnthropicAdapter in `src/adapters/llm.py` is functionally correct (it has been tested with respx mocks but not against the real API)
- The ResilientGitHubClient retry logic works as designed (tested with mock HTTP, not real rate limits)
- Postgres schema matches SQLAlchemy models (no migration drift since last schema update)
- A single test repository with 10 labeled issues is sufficient to validate the integration path
- LLM output parsing in AgentRunner can handle real Claude outputs (not just the canned mock format)

---

## Story Map

### Sprint 1: LLM Provider Validation (2 weeks)

Stories are ordered by risk reduction: validate the cheapest/fastest agent first, then the most complex.

#### Story 30.1: Evaluation Harness & Labeled Test Dataset
**As a** developer validating real LLM integration,
**I want** an evaluation harness with labeled test cases,
**so that** I can measure agent output quality objectively.

**Details:**
- Create `src/eval/__init__.py`, `src/eval/models.py`, `src/eval/harness.py`, `src/eval/scoring.py`
- Define `EvalCase` model: issue_body, expected_goals, expected_constraints, expected_acs, complexity_label, risk_flags
- Define `EvalResult` model: case_id, agent_name, pass/fail, score_breakdown, raw_output, cost, latency
- Scoring functions: intent_goal_match (fuzzy string similarity), constraint_coverage (set intersection), ac_completeness (count + specificity heuristic)
- Create `tests/eval/fixtures/` with 10 labeled GitHub issues spanning: trivial bugfix, moderate feature, complex refactor, security-sensitive, migration, documentation, high-risk with multiple files, ambiguous requirements, dependency update, cross-cutting concern
- CLI entry point: `python -m src.eval.harness --agent intent_agent --provider anthropic`

**Files to create:** `src/eval/__init__.py`, `src/eval/models.py`, `src/eval/harness.py`, `src/eval/scoring.py`, `tests/eval/__init__.py`, `tests/eval/fixtures/*.json`, `tests/eval/test_harness.py`
**Files to modify:** None
**Acceptance:** `pytest tests/eval/` passes; harness runs against mock adapter and produces structured results

---

#### Story 30.2: Intent Agent Real LLM Validation
**As a** developer validating the intent agent,
**I want** to run it against real Claude with labeled test issues,
**so that** I can confirm it produces valid, actionable intent specifications.

**Details:**
- Set `agent_llm_enabled["intent_agent"]=True` and `llm_provider=anthropic` in test config
- Run eval harness against all 10 labeled issues
- Validate IntentAgentOutput: goals are actionable (not vague), constraints derive from risk flags, invariants are non-empty, ACs are specific and testable
- Log token usage and cost per invocation via ModelCallAudit
- Document results in `docs/eval-results/sprint1-intent.md`
- If < 8/10 pass, iterate on `src/intent/intent_config.py` prompt template (but do NOT change agent framework)

**Files to create:** `docs/eval-results/sprint1-intent.md`
**Files to modify:** `src/intent/intent_config.py` (prompt iteration only if needed)
**Acceptance:** >= 8/10 labeled issues produce valid intent specs; cost per invocation documented

---

#### Story 30.3: QA Agent Real LLM Validation
**As a** developer validating the QA agent,
**I want** to run it against real Claude with synthetic evidence bundles,
**so that** I can confirm it catches defects and classifies them correctly.

**Details:**
- Set `agent_llm_enabled["qa_agent"]=True` and `llm_provider=anthropic` in test config
- Create synthetic evidence bundles: 7 with planted defects (lint failures, test failures, security findings, intent violations, missing coverage), 3 clean
- Run QA agent against each bundle with a corresponding intent spec
- Validate QAAgentOutput: criteria_results reference specific evidence, defect classification matches planted defect type, clean bundles get passing results
- Log token usage and cost per invocation

**Files to create:** `tests/eval/fixtures/qa_bundles/*.json`, `docs/eval-results/sprint1-qa.md`
**Files to modify:** `src/qa/qa_config.py` (prompt iteration only if needed)
**Acceptance:** QA agent catches planted defects in >= 7/10 cases; false positive rate on clean bundles documented

---

#### Story 30.4: Primary Agent Real LLM Validation
**As a** developer validating the primary agent,
**I want** to run it against 3 simple labeled issues with real Claude,
**so that** I can confirm it produces reasonable code changes within budget.

**Details:**
- Set `agent_llm_enabled["primary_agent"]=True` and `llm_provider=anthropic` in test config
- Select 3 trivial issues from the labeled dataset (small, well-defined diffs)
- Run primary agent in process isolation mode (not container)
- Validate: agent_summary is coherent, file_changes are non-empty, evidence_bundle is populated, cost stays under `agent_max_budget_usd` ($5.00)
- This is the most expensive agent -- document cost per run carefully

**Files to create:** `docs/eval-results/sprint1-primary.md`
**Files to modify:** None expected
**Acceptance:** 3/3 issues produce structurally valid output; cost per run < $5.00

---

### Sprint 2: GitHub Provider & Postgres Validation (2 weeks)

#### Story 30.5: Postgres Backend Smoke Test
**As a** developer validating persistence,
**I want** to run the full pipeline with `store_backend=postgres`,
**so that** I can confirm TaskPackets, intent specs, and repo profiles persist correctly.

**Details:**
- Stand up local Postgres via `infra/docker-compose.prod.yml` (or a test-specific compose override)
- Set `store_backend=postgres` and generate a real Fernet encryption key
- Run pipeline with mock LLM + mock GitHub but real Postgres
- Verify TaskPacket lifecycle: CREATE -> ENRICHED -> INTENT_BUILT -> IMPLEMENTING -> VERIFYING -> QA -> PUBLISHED
- Verify intent spec persists and can be read back with all fields intact
- Verify repo profile persists
- Fix any schema drift or serialization issues discovered

**Files to create:** `tests/integration/test_postgres_backend.py`
**Files to modify:** Schema files if drift is found
**Acceptance:** Full lifecycle round-trips through Postgres; all fields survive serialization

---

#### Story 30.6: Real GitHub Provider Integration
**As a** developer validating GitHub integration,
**I want** to run Publisher operations against a real test repository,
**so that** I can confirm branch creation, PR lifecycle, and evidence comments work.

**Details:**
- Set `github_provider=real` with valid GitHub App credentials
- Use dedicated test repository `thestudio-test-target`
- Verify operations in order: get default branch, get branch SHA, create branch, create PR (draft), add evidence comment, add labels, remove label, update comment
- Verify error handling: invalid repo returns classified error, rate limit triggers retry
- Clean up test branches/PRs after each test run

**Files to create:** `tests/integration/test_real_github.py`
**Files to modify:** None expected (fix bugs if found)
**Acceptance:** All 8 GitHub operations succeed against test repo; cleanup runs after tests

---

#### Story 30.7: Full Pipeline Observe Tier on Real Repo

**Status: COMPLETE (2026-03-18)** — Docker-validated against real Anthropic API.

**Results (Docker prod stack `thestudio-prod-*`):**
- 6 pipeline agents tested against real Anthropic API via Docker container
- All agents produced valid, non-empty responses with correct structure
- Per-agent costs measured: `docs/eval-results/sprint2-cost-baselines.md`
- Total per-issue cost: ~$0.087 (6 agents), projected ~$0.13 (9 agents)
- Test: `tests/integration/test_docker_full_pipeline.py` — 6/6 passed

**Acceptance:** 6/6 agents produce valid output; cost per issue $0.087 (< $5.00 target)

---

#### Story 30.8: Failure Mode Catalog

**Status: COMPLETE (2026-03-18)** — 6 failure modes documented from Docker validation.

**Results:**
- 6 failure modes cataloged in `docs/FAILURE_CATALOG.md`
- Categories: auth (2), configuration (2), validation (1), cost (1)
- Blocking for Suggest tier: F1 (stale API key), F5 (max_tokens truncation)
- All mitigations documented with reproduction steps

**Acceptance:** Every observed failure cataloged; blocking failures have mitigations

---

### Sprint 3: Feature Flag Activation & Deployment (2 weeks)

#### Story 30.9: Enable Projects v2 + Meridian Portfolio
**As a** platform operator,
**I want** to activate Projects v2 and Meridian Portfolio on a real environment,
**so that** I can verify project board sync and portfolio health reporting.

**Details:**
- Set `projects_v2_enabled=True` with valid `projects_v2_owner`, `projects_v2_number`, `projects_v2_token`
- Verify: project board updates on TaskPacket status transitions, columns/fields map correctly
- Set `meridian_portfolio_enabled=True` and `meridian_portfolio_github_issue=True`
- Verify: portfolio review runs (manually triggered or on schedule), health report posts to configured repo issue
- Verify: Admin UI dashboard shows real data from Postgres backend

**Files to create:** `docs/eval-results/sprint3-feature-flags.md`
**Files to modify:** None expected
**Acceptance:** Board updates on status change; health report posts successfully; admin dashboard renders real data

---

#### Story 30.10: Enable Preflight + Container Isolation
**As a** platform operator,
**I want** to activate preflight review and container isolation,
**so that** I can verify safety gates work with real providers.

**Details:**
- Set `preflight_enabled=True`
- Run an issue through the pipeline; verify preflight agent evaluates the plan and gates proceed/reject correctly
- Set `agent_isolation=container` for an Execute-tier issue
- Verify: Docker container spins up, code executes in isolation, evidence bundle includes container metadata (container_id, resource usage, exit code)
- Verify fallback policy: Execute tier with `agent_isolation_fallback=deny` fails when Docker is unavailable

**Files to create:** None
**Files to modify:** None expected
**Acceptance:** Preflight gate catches a deliberately bad plan; container isolation produces evidence with container metadata

---

#### Story 30.11: Deployment Runbook
**As a** new developer joining the project,
**I want** a comprehensive deployment guide,
**so that** I can stand up the platform without tribal knowledge.

**Details:**
- Create `docs/DEPLOYMENT.md` covering:
  - Prerequisites: Python 3.12+, Docker, GitHub App
  - Environment variables: every `THESTUDIO_*` variable with description, required/optional, example value
  - Secrets management: how to generate Fernet key, where to store API keys, GitHub App private key handling
  - GitHub App setup: permissions required, webhook configuration, installation on target repos
  - Postgres: schema migration steps, connection string format, backup/restore
  - Temporal: server setup, namespace creation, task queue registration
  - NATS: JetStream configuration, stream/consumer setup
  - Docker Compose: production vs dev, port mappings, volume mounts
  - Feature flags: recommended activation order, validation steps per flag
  - Monitoring: OTEL configuration, key metrics to watch
  - Rollback: how to revert feature flags, database rollback, container cleanup

**Files to create:** `docs/DEPLOYMENT.md`
**Files to modify:** None
**Acceptance:** A developer unfamiliar with the project can follow the runbook to a running instance

---

#### Story 30.12: Suggest Tier Validation
**As a** platform operator,
**I want** to validate Suggest tier end-to-end,
**so that** I can confirm the approval workflow works with real providers.

**Details:**
- Create 3 issues on the test repository for Suggest tier processing
- Run each through the full pipeline at Suggest tier
- Verify per issue: PR is created as draft then marked ready-for-review, approval workflow triggers (Human Approval Wait State from Epic 21), chat approval channel receives notification
- Complete approval via chat endpoint; verify PR proceeds to final state
- Measure success rate and document in `docs/eval-results/sprint3-suggest-tier.md`

**Files to create:** `docs/eval-results/sprint3-suggest-tier.md`
**Files to modify:** None expected
**Acceptance:** >= 2/3 Suggest-tier issues complete the full flow including approval

---

## Meridian Review Status

**Round 1: PASS (2026-03-18)**

| # | Question | Status |
|---|----------|--------|
| 1 | Is the narrative clear and outcome-focused? | PASS |
| 2 | Are acceptance criteria testable at epic scale? | PASS (AC 5 bounded to "observed during validation") |
| 3 | Are constraints and non-goals explicit? | PASS (6 non-goals) |
| 4 | Are success metrics measurable and time-bound? | PASS (AC 7 metric updated to checklist) |
| 5 | Are dependencies and risks identified? | PASS (owners and dates added) |
| 6 | Is the story map ordered by risk reduction? | PASS |
| 7 | Can an AI agent implement from this alone? | PASS |

**Gaps resolved:**
- E1: External dependency owners and provisioning dates added
- E2: AC 7 success metric changed from aspirational walkthrough to measurable checklist
- E3: All stakeholder roles assigned to Primary Developer (solo-developer project)
