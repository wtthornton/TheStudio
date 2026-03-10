# Epic 15 — End-to-End Integration Testing & Real Repo Onboarding

**Author:** Saga
**Date:** 2026-03-10
**Status:** Draft — Awaiting Meridian Review

---

## 1. Title

Prove the Pipeline Works End-to-End — Build an in-process integration test harness that chains all 9 pipeline stages, validate the full flow with mock providers, baseline latency, and document how to onboard a real GitHub repository.

## 2. Narrative

TheStudio has 1,561 passing unit tests, a Temporal workflow definition that wires all 9 steps, activity stubs that call real pure functions (intake, router) and delegate the rest through Model Gateway and Tool Hub, Docker smoke tests that prove webhook-to-TaskPacket intake works, and Playwright browser tests that verify the Admin UI. Every individual pipeline stage has been tested in isolation. The Temporal workflow (`TheStudioPipelineWorkflow`) exists and compiles. The activity definitions in `src/workflow/activities.py` are wired with proper input/output dataclasses.

But no test has ever executed the full chain: webhook POST through intake through context through intent through router through assembler through implementation through verification through QA through publisher, producing a draft PR with a formatted evidence comment. The pipeline has never run end-to-end.

This gap is not academic. The current activity implementations reveal it concretely: `context_activity` calls `get_model_router()` and `get_tool_policy_engine()` but returns hardcoded defaults. `intent_activity` calls the Model Gateway but returns `goal=params.issue_title` with empty acceptance criteria. `verify_activity` always returns `passed=True`. `publish_activity` returns `pr_number=0`. These stubs were necessary to ship the workflow definition, but they mean the pipeline has never produced a real output from real-shaped input.

This matters now because every preceding epic built toward one goal: processing a real GitHub issue end-to-end with evidence-backed output. Epics 0-10 built the pipeline stages, the domain objects, and the infrastructure. Epics 11-12 hardened the deployment and tested the UI. Epics 13-14 built agent definitions and content enrichment. The only remaining gap is proving the chain works as a connected system and then pointing it at a real repository.

This epic closes that gap in two ways. First, it builds an in-process integration test suite that chains all 9 stages together using mock providers (mock GitHub API, mock LLM responses, in-memory or SQLite database) so the full pipeline can run in CI without Docker, without API keys, and without external services. Second, it produces a step-by-step onboarding guide for registering a real GitHub repository at Observe tier, so the first real-repo run has a documented, repeatable procedure.

**Roadmap linkage:** This epic is the bridge between "the platform is built" and "the platform processes real work." It directly advances the OKR: "TheStudio processes a real GitHub issue end-to-end with evidence-backed output." Without it, the first real-repo run is a manual, undocumented experiment. With it, the first real-repo run is a measured, repeatable operation with a known latency baseline.

**Scope:** This is approximately 1 week of focused work. The epic does not require real LLM API calls, real GitHub App installation, or Docker for CI. It proves the chain works with controlled inputs and mock providers, then documents how to take the next step.

## 3. References

- Pipeline workflow: `src/workflow/pipeline.py` (9-step `TheStudioPipelineWorkflow`)
- Activity definitions: `src/workflow/activities.py` (all 9 activity stubs)
- Workflow trigger: `src/ingress/workflow_trigger.py` (Temporal client)
- Evidence comment format: `src/publisher/evidence_comment.py` (`format_full_evidence_comment`)
- Intake pure function: `src/intake/intake_agent.py` (`evaluate_eligibility`)
- Router pure function: `src/routing/router.py` (`route`)
- Verification gate: `src/verification/gate.py`
- Docker smoke tests (existing): `tests/docker/test_pipeline_smoke.py`, `tests/docker/conftest.py`
- Pipeline stage mapping: `.claude/rules/pipeline-stages.md`
- Architecture overview: `thestudioarc/00-overview.md`
- System runtime flow: `thestudioarc/15-system-runtime-flow.md`
- Repo registration lifecycle: `thestudioarc/00-overview.md` (Repo Registration Lifecycle section)
- Domain objects: `.claude/rules/domain-objects.md`
- Production deployment guide: `docs/deployment.md`
- OKRs: `thestudioarc/personas/MERIDIAN-TEAM-REVIEW-AND-OKRS.md`

## 4. Acceptance Criteria

**AC-1: An in-process integration test executes all 9 pipeline stages as a connected chain.**
A single pytest test sends a simulated webhook payload and asserts that data flows through Intake, Context, Intent, Router, Assembler, Implement, Verify, QA, and Publish in sequence. Each stage receives the output of the previous stage (not hardcoded inputs). No Docker, no external services, no real API keys required. The test uses mock providers for GitHub API, LLM calls, and database persistence. The test passes in GitHub Actions CI.

**AC-2: The smoke test produces a complete evidence comment.**
The end-to-end test asserts that the pipeline's final output includes a formatted evidence comment (matching `format_full_evidence_comment` structure) containing: TaskPacket ID, correlation ID, intent version, verification result, acceptance criteria checklist, files changed section, and the `<!-- thestudio-evidence -->` marker. Sections must not be empty placeholder values.

**AC-3: A loopback integration test forces a failure and verifies retry.**
A test configures the mock verification provider to fail on the first attempt and pass on the second. The test asserts: the pipeline loops back from Verify to Implement, the loopback count increments, the second Verify attempt passes, and the pipeline continues to QA and Publish. The `PipelineOutput.verification_loopbacks` field equals 1.

**AC-4: The pipeline runs through Temporal's test server.**
At least one integration test uses `temporalio.testing.WorkflowEnvironment` to execute `TheStudioPipelineWorkflow` with mock activities. The test verifies the workflow completes successfully, returns a `PipelineOutput` with `success=True`, and exercises the activity call sequence defined in `src/workflow/pipeline.py`.

**AC-5: Pipeline latency is measured and recorded.**
The integration test suite measures wall-clock time for the full pipeline run (webhook to publish output) and per-stage timing. Results are printed to stdout in a parseable format (e.g., `TIMING: total=1.23s intake=0.05s context=0.12s ...`) and documented in a baseline file (`docs/pipeline-latency-baseline.md`) with the initial measurements and the hardware/configuration used.

**AC-6: An onboarding guide documents real-repo registration at Observe tier.**
A document (`docs/onboarding-real-repo.md`) provides step-by-step instructions for: installing the GitHub App on a repository, configuring webhooks (issues, labels, PR events), creating a Repo Profile via the Admin API, verifying the registration via the Admin UI, and sending a test webhook to confirm intake works. The guide specifies Observe tier (read-only, no PR writes) and explicitly states what will and will not happen at each tier.

**AC-7: All discovered integration gaps are documented or fixed.**
Any bugs, missing wiring, or broken data contracts discovered during end-to-end testing are either fixed in this epic or logged as GitHub issues with clear reproduction steps. A summary of discovered issues is added to the latency baseline document.

### 4b. Top Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Activity stubs return hardcoded values that do not exercise real logic | High | Medium | Replace stubs with configurable mock providers that return realistic shaped data |
| Temporal test server has version compatibility issues | Medium | Medium | Pin `temporalio` version; fall back to direct workflow function call if test server fails |
| Evidence comment format breaks when fed real-shaped data | Medium | High | AC-2 validates the full comment structure with assertions on every required section |
| Loopback logic has an off-by-one in the retry counter | Medium | High | AC-3 explicitly tests the counter value and boundary conditions |
| Onboarding guide references endpoints that do not exist yet | Low | Medium | Verify every endpoint and Admin UI page referenced in the guide against the running app |

## 5. Constraints & Non-Goals

**Constraints:**
- All integration tests must pass without Docker (in-process only, using mocks and test fixtures)
- All integration tests must pass without real API keys (GitHub, LLM providers)
- Tests must be runnable in GitHub Actions CI without special secrets or service containers
- Mock providers must return realistically shaped data (valid UUIDs, non-empty strings, proper field types) — not empty defaults
- The Temporal test must use `temporalio.testing` — not a deployed Temporal server
- The onboarding guide targets Observe tier only (no Suggest or Execute tier instructions)

**Non-Goals:**
- Real LLM calls or real GitHub API calls in CI (those are manual smoke tests, not automated CI)
- Performance optimization (this epic measures baseline, it does not optimize)
- Production deployment of the pipeline against a real repo (that is the next epic)
- Modifying `docker-compose.dev.yml` or `infra/docker-compose.prod.yml`
- Building a test framework for external service contracts (contract testing is a future epic)
- Testing the Admin UI integration with live pipeline data (covered by Epic 12 Playwright tests)
- Multi-repo support or Execute-tier testing

## 6. Stakeholders & Roles

| Role | Who | Responsibility |
|------|-----|---------------|
| **Epic Owner** | Platform Lead | Scope decisions, priority calls, approve onboarding guide |
| **Tech Lead** | Core Engineer | Integration test harness architecture, mock provider design, Temporal test setup |
| **QA** | Quality Engineer | Review test coverage, validate loopback test, confirm evidence comment assertions |
| **DevOps** | Infrastructure Engineer | Validate CI integration, confirm tests run without special CI configuration |
| **Documentation** | Tech Writer / Engineer | Review onboarding guide for completeness and followability |

## 7. Success Metrics

| Metric | Target | How Measured |
|--------|--------|-------------|
| Integration test pass rate in CI | 100% on every PR | GitHub Actions test results |
| Pipeline stages exercised end-to-end | 9/9 | Test assertions verify each stage produced output |
| Loopback path coverage | Verification loopback + QA loopback tested | Dedicated test cases for each path |
| Evidence comment completeness | All 7 required sections non-empty | String assertions in AC-2 test |
| Latency baseline documented | Total pipeline time < 5s with mocks | Timing output from integration tests |
| Onboarding guide followable | A developer who did not write the guide can register a repo in < 30 minutes | Manual walkthrough by a second team member |
| Integration gaps discovered and tracked | 100% of discovered issues logged | GitHub issues or inline fixes with commit messages |

## 8. Context & Assumptions

**Assumptions:**
- The `temporalio` Python SDK supports `WorkflowEnvironment` for in-process workflow testing (confirmed in temporalio docs)
- The existing activity definitions in `src/workflow/activities.py` can be replaced with mock implementations for testing without modifying production code (Temporal's activity mocking pattern)
- The `evaluate_eligibility` function in `src/intake/intake_agent.py` and `route` function in `src/routing/router.py` are pure functions that work without database or external service dependencies (confirmed by reading the code)
- The Admin API endpoints for repo registration (`POST /admin/repos`) exist and work (confirmed by `tests/docker/conftest.py` fixture)
- The evidence comment format in `src/publisher/evidence_comment.py` is the canonical format and will not change during this epic

**Dependencies:**
- `temporalio` Python SDK (already in dependencies)
- `pytest-asyncio` for async test support (already in dependencies)
- `httpx` for HTTP testing (already in dependencies)
- All 9 pipeline stage modules must be importable without side effects (database connections, external service calls)
- Epic 11 deployment guide (`docs/deployment.md`) for cross-referencing in onboarding guide

**Systems Affected:**
- `tests/integration/` — new test directory for integration tests
- `src/workflow/activities.py` — may need minor changes to support dependency injection for mock providers
- `docs/` — new onboarding and latency baseline documents
- `.github/workflows/` — CI configuration to include integration tests
- `conftest.py` — root-level fixtures for mock providers

**Business Rules:**
- Gates fail closed: if the mock verification provider returns `passed=False` and loopbacks are exhausted, the pipeline must fail — not skip the gate
- Loopback caps are enforced: `MAX_VERIFICATION_LOOPBACKS = 2` and `MAX_QA_LOOPBACKS = 2` per `src/workflow/pipeline.py`
- Publisher is the only writer to GitHub: even in tests, no other activity should produce GitHub API calls
- Observe tier produces no GitHub writes: the onboarding guide must make this explicit

---

## Story Map

Stories are ordered by vertical slice: end-to-end value first, edge cases and documentation second.

---

### Story 15.1: In-Process Integration Test Harness with Mock Providers

**As a** developer running the test suite,
**I want** a test harness that wires all 9 pipeline stages together in-process with mock providers,
**so that** I can run the full pipeline without Docker, databases, or API keys.

**Details:**
- Create `tests/integration/conftest.py` with fixtures for:
  - Mock LLM provider that returns configurable responses (default: echo the input goal as intent, return a simple implementation plan)
  - Mock GitHub client that records all API calls but makes no real HTTP requests
  - In-memory or SQLite-backed database session (if activities need persistence)
  - Mock `ModelRouter` and `ToolPolicyEngine` that return valid defaults
- Create mock activity implementations that replace the stubs in `src/workflow/activities.py` for testing:
  - `mock_context_activity`: returns realistic `ContextOutput` with populated scope, risk flags, and complexity
  - `mock_intent_activity`: returns `IntentOutput` with a real goal derived from issue title, 3+ acceptance criteria, and a valid `intent_spec_id` (UUID)
  - `mock_assembler_activity`: returns `AssemblerOutput` with 3+ plan steps and populated QA handoff
  - `mock_implement_activity`: returns `ImplementOutput` with 2+ files in `files_changed` and a meaningful `agent_summary`
  - `mock_verify_activity`: configurable pass/fail (default: pass)
  - `mock_qa_activity`: configurable pass/fail (default: pass)
  - `mock_publish_activity`: returns `PublishOutput` with `pr_number=42`, `pr_url="https://github.com/test-org/test-repo/pull/42"`, `created=True`
- The real `intake_activity` and `router_activity` should be used (they are pure functions with no external dependencies).
- All mocks must return properly typed dataclass instances matching the activity output types.

**Acceptance Criteria:**
- `tests/integration/conftest.py` exists with all fixtures documented.
- Mock activities return non-trivial, realistically shaped data (no empty strings, no zero IDs, no empty lists for required fields).
- `pytest tests/integration/ -v` discovers and collects tests without import errors.
- No fixture requires Docker, network access, or environment variables to initialize.

**Files to create:**
- `tests/integration/__init__.py`
- `tests/integration/conftest.py`
- `tests/integration/mock_providers.py`

---

### Story 15.2: Full Pipeline Smoke Test — Webhook to Draft PR

**As a** developer verifying the pipeline,
**I want** a single test that runs the entire 9-stage pipeline from a simulated webhook payload to a draft PR output,
**so that** I can confirm data flows correctly through every stage.

**Details:**
- Create `tests/integration/test_full_pipeline.py` with a test that:
  1. Constructs a `PipelineInput` with realistic fields (taskpacket_id=UUID, correlation_id=UUID, labels=["agent:run", "type:bug"], repo="test-org/test-repo", issue_title="Fix login timeout", issue_body="Users report 30s timeout on login page")
  2. Executes the pipeline by calling the activity chain in sequence (not through Temporal — that is Story 15.5)
  3. Asserts each stage produced output: intake accepted, context has risk flags, intent has goal and criteria, router selected experts, assembler produced plan steps, implement returned files, verify passed, QA passed, publish returned a PR URL
  4. Asserts the final `PipelineOutput` has `success=True`, `pr_number > 0`, and `pr_url` is non-empty
- The test should capture the output of each stage in a dict for assertion and debugging.
- If any stage fails, the test error message should identify which stage failed and what output it produced.

**Acceptance Criteria:**
- `test_full_pipeline_happy_path` passes and asserts all 9 stages produced valid output.
- The test runs in < 5 seconds (no network calls, no disk I/O beyond imports).
- The test does not require any environment variables or configuration files.
- Test output on failure clearly identifies the failing stage.

**Files to create:**
- `tests/integration/test_full_pipeline.py`

---

### Story 15.3: Loopback Integration Test — Verification Failure and Retry

**As a** developer verifying gate enforcement,
**I want** a test that forces a verification failure and confirms the pipeline loops back correctly,
**so that** I can prove gates fail closed and loopbacks carry evidence.

**Details:**
- Create a test in `tests/integration/test_loopback.py` that:
  1. Configures `mock_verify_activity` to fail on the first call and pass on the second
  2. Runs the pipeline through the implementation-verification loop
  3. Asserts: `mock_implement_activity` was called twice (once for initial attempt, once for loopback), `mock_verify_activity` was called twice, the loopback attempt counter incremented, the final `PipelineOutput` has `verification_loopbacks=1` and `success=True`
- Create a second test that:
  1. Configures `mock_verify_activity` to always fail
  2. Runs the pipeline and asserts it fails closed after `MAX_VERIFICATION_LOOPBACKS` (2) retries
  3. Asserts `PipelineOutput.success=False` and `step_reached="verify"`
- Create a third test for QA loopback:
  1. Configures `mock_qa_activity` to fail on the first call and pass on the second
  2. Asserts `PipelineOutput.qa_loopbacks=1` and `success=True`

**Acceptance Criteria:**
- Three loopback tests pass: verification retry success, verification exhaustion failure, QA retry success.
- Verification exhaustion test confirms `MAX_VERIFICATION_LOOPBACKS` is enforced (not off-by-one).
- Each test asserts the exact loopback count in `PipelineOutput`.
- Tests confirm gates fail closed — exhausted retries produce `success=False`, never skip the gate.

**Files to create:**
- `tests/integration/test_loopback.py`

---

### Story 15.4: Evidence Comment Validation — End-to-End Format Check

**As a** reviewer reading an agent-produced PR,
**I want** the evidence comment to contain all required sections with real data,
**so that** I can validate correctness without reading the full diff.

**Details:**
- Create a test in `tests/integration/test_evidence_comment.py` that:
  1. Runs the full pipeline (reusing the harness from Story 15.1)
  2. Captures the inputs that `publish_activity` would pass to `format_full_evidence_comment`
  3. Calls `format_full_evidence_comment` with those inputs
  4. Asserts the output string contains:
     - `<!-- thestudio-evidence -->` marker
     - `## TheStudio Evidence` header
     - `**TaskPacket ID**` with a non-empty UUID
     - `**Correlation ID**` with a non-empty UUID
     - `**Intent Version**` with `v1` or higher
     - `**Verification**` with `PASSED` or `FAILED`
     - `### Intent Summary` section with non-empty goal
     - `### Acceptance Criteria` section with at least one checkbox item
     - `### What Changed` section with at least one file path
     - `### Verification Results` table with at least one row
     - `### Expert Coverage` section
     - `### Loopback Summary` section
     - Footer: `Generated by TheStudio`
- The test should fail if any required section is missing or contains only placeholder text.

**Acceptance Criteria:**
- Evidence comment test validates all 7 required sections from the architecture spec.
- The test uses real-shaped data from the pipeline run (not manually constructed inputs).
- Assertions use string matching, not exact equality (format may evolve, structure must not).
- The test catches regressions: if `format_full_evidence_comment` signature changes, the test breaks with a clear error.

**Files to create:**
- `tests/integration/test_evidence_comment.py`

---

### Story 15.5: Temporal Workflow Integration Test

**As a** developer verifying workflow orchestration,
**I want** a test that runs `TheStudioPipelineWorkflow` through Temporal's test server,
**so that** I can confirm the workflow definition, activity wiring, and retry policies work correctly.

**Details:**
- Create `tests/integration/test_temporal_workflow.py` that:
  1. Uses `temporalio.testing.WorkflowEnvironment.start_time_skipping()` to create a test environment
  2. Registers `TheStudioPipelineWorkflow` and mock activity implementations
  3. Starts the workflow with a valid `PipelineInput`
  4. Awaits the workflow result and asserts `PipelineOutput.success=True`
  5. Verifies the activity execution order matches the 9-step sequence
- Create a second test that verifies loopback behavior through the Temporal test server:
  1. Register a mock verify activity that fails once then passes
  2. Assert the workflow completes with `verification_loopbacks=1`
- Tests must handle Temporal's async patterns correctly (`pytest-asyncio`).
- If the `temporalio.testing` module is not available or has compatibility issues, document the issue and fall back to a direct `workflow.run()` call with mocked `workflow.execute_activity`.

**Acceptance Criteria:**
- At least one test executes `TheStudioPipelineWorkflow` through `WorkflowEnvironment`.
- The test verifies the workflow completes and returns a valid `PipelineOutput`.
- The test runs without a deployed Temporal server (fully in-process).
- The test is marked with `@pytest.mark.integration` for selective CI execution.

**Files to create:**
- `tests/integration/test_temporal_workflow.py`

---

### Story 15.6: Pipeline Latency Baseline

**As a** platform operator planning capacity,
**I want** measured per-stage and total pipeline latency with mock providers,
**so that** I have a baseline for detecting regressions and planning real-workload capacity.

**Details:**
- Add timing instrumentation to the full pipeline test (Story 15.2):
  1. Wrap each stage call with `time.perf_counter()` start/stop
  2. Print a timing summary to stdout in parseable format: `TIMING: total=1.234s intake=0.012s context=0.045s intent=0.032s router=0.008s assembler=0.015s implement=0.021s verify=0.010s qa=0.018s publish=0.009s`
  3. Assert total time < 5 seconds (with mocks, the pipeline should be fast)
- Create `docs/pipeline-latency-baseline.md` documenting:
  - Date, hardware/OS, Python version, key dependency versions
  - Per-stage timing from the first CI run
  - Expected variance (mock providers have near-zero latency; real providers will be 10-100x slower)
  - Methodology for re-running the baseline
  - Known integration gaps discovered during testing (list of issues found)

**Acceptance Criteria:**
- Timing output is printed to stdout on every integration test run.
- `docs/pipeline-latency-baseline.md` exists with initial measurements.
- Baseline document includes methodology section so future measurements are comparable.
- Total pipeline time with mocks is documented and < 5 seconds.

**Files to create:**
- `docs/pipeline-latency-baseline.md`

**Files to modify:**
- `tests/integration/test_full_pipeline.py` — add timing instrumentation

---

### Story 15.7: Real Repo Onboarding Guide

**As a** platform operator onboarding the first real repository,
**I want** step-by-step instructions for registering a GitHub repo at Observe tier,
**so that** I can complete the registration without guessing or reading source code.

**Details:**
- Create `docs/onboarding-real-repo.md` covering:
  1. **Prerequisites:** Running TheStudio stack (reference `docs/deployment.md`), GitHub account with admin access to target repo, GitHub App created and installed (or instructions to create one)
  2. **GitHub App setup:** Required permissions (issues: read, pull requests: write, contents: read), webhook URL configuration, webhook secret generation
  3. **Repo registration via Admin API:**
     - `POST /admin/repos` with `owner`, `repo`, `installation_id`, `default_branch`
     - Expected response (201 with repo profile)
     - Verification: `GET /admin/repos` should list the new repo
  4. **Repo registration via Admin UI:**
     - Navigate to Settings > Repositories page
     - Fill in the registration form
     - Verify the repo appears in the dashboard
  5. **Webhook verification:**
     - Create a test issue in the GitHub repo
     - Check the Admin UI workflow console for intake activity
     - Expected behavior at Observe tier: TaskPacket created, no PR written
  6. **Tier explanation:**
     - Observe: read-only, creates TaskPackets, no GitHub writes
     - Suggest: creates draft PRs, human must review and merge
     - Execute: full automation with gates, human merge still required by default
  7. **Troubleshooting:** Webhook signature failures, repo not found, intake rejection reasons
- Every API endpoint referenced must be verified against the actual router definitions.
- Include expected responses and error messages so the operator knows what success and failure look like.

**Acceptance Criteria:**
- `docs/onboarding-real-repo.md` exists and covers all 7 sections.
- Every API endpoint mentioned exists in the codebase (verifiable by grep).
- The guide specifies Observe tier and explicitly states no GitHub writes will occur.
- A developer who did not author the guide can follow it to register a repo via the Admin API.
- The guide cross-references `docs/deployment.md` for infrastructure prerequisites.

**Files to create:**
- `docs/onboarding-real-repo.md`

---

## Meridian Review Status

### Round 1: Pending

This epic requires Meridian review before implementation begins. The review should validate:
1. Are the acceptance criteria testable at epic scale?
2. Is the scope bounded (1 week, no real API keys, no production deployment)?
3. Do the stories deliver end-to-end value in vertical slices?
4. Are there missing dependencies or circular assumptions?
5. Does the onboarding guide reference endpoints that actually exist?
6. Is the latency baseline methodology reproducible?
7. Are the mock providers realistic enough to catch real integration bugs?
