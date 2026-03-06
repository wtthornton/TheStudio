# Sprint 3 Plan — Epic 0: Prove the Pipe (Final Sprint)

**Persona:** Helm (Planner & Dev Manager)
**Date:** 2026-03-05
**Epic:** `docs/epics/epic-0-foundation.md`
**Sprint duration:** 3 weeks (weeks 7-9) + week 10 integration buffer
**Team:** 1-2 developers
**Predecessor:** Sprint 2 (complete — Context Manager, Intent Builder, Verification Gate landed)

---

## Sprint Goal

**Objective:** Primary Agent (Developer role) implements code changes from an Intent Specification using Claude Agent SDK with `claude-sonnet-4-5`, produces an evidence bundle, and handles verification loopbacks (max 2); Publisher creates a draft PR on GitHub with an evidence comment (TaskPacket ID, intent summary, verification result), lifecycle labels, and idempotency guard — so that Epic 0 is complete: the full pipe from GitHub issue to draft PR is proven end-to-end.

**Test:** The sprint goal is met when:
1. Primary Agent reads an Intent Specification and produces code changes in a target repo (Developer role, tool allowlist enforced)
2. Evidence bundle is produced and persisted (files_changed, test_results, lint_results)
3. Verification failure triggers loopback: agent receives failure evidence, retries, produces new evidence bundle; max 2 loopbacks enforced; task fails after exceeding max
4. Publisher creates a draft PR on GitHub via API with correct title (from intent goal)
5. Evidence comment contains TaskPacket ID, intent summary, and verification result
6. Lifecycle labels applied: `agent:in-progress` then `agent:done`
7. Idempotency key (TaskPacket ID + intent version) prevents duplicate PRs on retry
8. TaskPacket status transitions through: `intent_built` -> `in_progress` -> `verification_passed` -> `published`
9. All code passes `ruff` lint and `mypy` type check
10. Sprint 1 and Sprint 2 tests still pass (no regression)

**Constraint:** No story is "done" unless its Definition of Done checklist is fully satisfied. This is the final sprint of Epic 0 — the full pipe must be proven.

---

## Order of Work

### Phase A — Primary Agent (weeks 7-8)

Story 0.5 starts on day 1. Its dependencies are satisfied:
- 0.4 Intent Builder — landed Sprint 2
- 0.6 Verification Gate — landed Sprint 2
- 0.8 Repo Profile (tool allowlist) — landed Sprint 1

| Order | Story | Points | Size | Rationale |
|-------|-------|--------|------|-----------|
| 1 | **0.5 Primary Agent** | 13 | XL | Critical path. Unblocks 0.7 (Publisher). Largest story in Epic 0. |

### Phase B — Publisher (weeks 8-9)

Story 0.7 starts once 0.5 evidence bundle interface is stable (can begin with mock evidence in parallel if 2 developers).

| Order | Story | Points | Size | Rationale |
|-------|-------|--------|------|-----------|
| 2 | **0.7 Publisher** | 8 | L | Final step in the pipe. Can develop with mock GitHub API. |

### Timeline (2 developers)

```
Week 7:  [Dev1: 0.5 Primary Agent]           [Dev2: 0.7 Publisher (mock evidence)]
Week 8:  [Dev1: 0.5 Primary Agent cont.]     [Dev2: 0.7 Publisher (GitHub API)]
Week 9:  [Dev1: integration + loopback test]  [Dev2: 0.7 integration + idempotency]
Week 10: [integration buffer — end-to-end pipe validation]
```

### Timeline (1 developer)

```
Week 7:  [0.5 Primary Agent >>>>>>>>>>>>>>>>>>>>>>>>]
Week 8:  [0.5 Primary Agent (loopback + evidence) >>]
Week 9:  [0.7 Publisher >>>>>>>>>>>>>>>>>>>] [buffer]
Week 10: [integration buffer — end-to-end validation]
```

---

## Dependencies

| Story | Depends on | Dependency type | Status |
|-------|-----------|-----------------|--------|
| 0.5 Primary Agent | 0.4 Intent Builder (IntentSpecRead) | Code dependency | Landed Sprint 2 |
| 0.5 Primary Agent | 0.6 Verification Gate (VerificationResult) | Code dependency | Landed Sprint 2 |
| 0.5 Primary Agent | 0.8 Repo Profile (tool allowlist) | Code dependency | Landed Sprint 1 |
| 0.5 Primary Agent | Claude Agent SDK (`claude_agent_sdk`) | External dependency | Available on PyPI |
| 0.7 Publisher | 0.5 Primary Agent (evidence bundle) | Code dependency | Sprint 3 — critical path |
| 0.7 Publisher | 0.6 Verification Gate (verification result) | Code dependency | Landed Sprint 2 |
| 0.7 Publisher | GitHub API (installation token) | External dependency | GitHub App provisioned Sprint 1 |

**Critical path:** 0.5 -> 0.7. Publisher cannot publish without evidence bundle from Primary Agent.

**New external dependency:** `claude_agent_sdk` package. Must be added to `pyproject.toml`. Risk: SDK API surface may differ from expectations. Mitigation: read SDK docs before coding (day 1 spike).

---

## Estimation Reasoning

### 0.5 Primary Agent — 13 points (XL)

- **Why this size:** Claude Agent SDK integration (new external dependency), Developer role configuration with system prompt template, tool allowlist enforcement at SDK registration level, evidence bundle creation and persistence, loopback handler (Temporal activity retry with new context), OTel instrumentation. Multiple integration points: IntentSpec, VerificationGate, TaskPacket status transitions.
- **What's assumed:** Claude Agent SDK provides tool registration API where we can control which tools are available. `claude-sonnet-4-5` is the model for Phase 0.
- **What's unknown:** Claude Agent SDK API surface (tool registration, conversation management, structured output). How the SDK handles tool-use failures. Whether the SDK supports async natively.
- **Risk:** High. First LLM integration in the system. SDK API may not match expectations. Mitigation: day-1 spike on SDK (read docs, build hello-world agent with tool use). If SDK has blockers, fall back to direct Anthropic API with httpx.

### 0.7 Publisher — 8 points (L)

- **Why this size:** GitHub API integration (branch creation, PR creation, comments, labels), idempotency guard (lookup-before-create), evidence comment formatting, lifecycle label management. Well-understood GitHub API pattern.
- **What's assumed:** GitHub App is installed and configured (Sprint 1 infra). PyGitHub or httpx available. Branch naming convention is straightforward.
- **What's unknown:** GitHub API rate limiting behavior under retries. Whether draft PR creation requires specific permissions.
- **Risk:** Low-medium. GitHub API is well-documented. Mitigation: test with mock API first; real API integration in final integration buffer.

---

## Capacity and Buffer

| Item | Points |
|------|--------|
| Sprint 3 committed stories | 21 |
| Team capacity (1-2 devs x 3 weeks) | ~28-30 points |
| Buffer (integration, unknowns, SDK spike) | ~7-9 points (~25-30%) |

**Commitment ratio:** 21 / 30 = 70% (intentionally lower than Sprint 2's 80%).

**Why more buffer:**
- Claude Agent SDK is a new external dependency with unknown API surface (1-2 days spike)
- First LLM call in the system — prompt engineering iteration expected
- End-to-end integration must work (this is the final sprint; the pipe must be proven)
- Week 10 is explicitly an integration buffer for Epic 0 completion validation

**Buffer allocation:**
- Claude Agent SDK learning curve and spike: 1-2 days
- Prompt engineering iteration for Developer role: 1 day
- Evidence bundle format iteration: 0.5 day
- GitHub API integration testing: 0.5 day
- End-to-end pipe validation (webhook -> TaskPacket -> Context -> Intent -> Agent -> Verify -> Publish): 1-2 days
- Sprint 2 retro action items (if any): 0.5 day

---

## What's Out (Not in Sprint 3)

| Item | Why not now |
|------|-------------|
| Router / Assembler | Phase 1 — not needed for single Developer role |
| Expert consultation | Phase 1 — no expert bench yet |
| QA Agent | Phase 1 — manual QA acceptable for Phase 0 |
| Execute tier | Phase 2 — Observe tier (draft PR only) is sufficient |
| Real repo checkout | Phase 0 can use a local test repo; real workspace isolation is Phase 1 |

After Sprint 3, Epic 0 is complete. The full pipe is proven: Issue -> TaskPacket -> Context -> Intent -> Primary Agent -> Verification -> Publisher -> Draft PR with evidence.

---

## Retro Actions from Sprint 2

**Sprint 2 retrospective not yet conducted.** This plan assumes Sprint 2 delivered as planned. If retro surfaces issues, Helm will amend this plan before Sprint 3 starts.

**Recommended retro questions for Sprint 2:**
1. Did Context Manager scope analysis produce useful enrichment for Intent Builder?
2. Did JetStream integration in Verification Gate cause friction (flagged as medium risk)?
3. Did Intent Builder produce intents that are clear enough for a Primary Agent to implement from?
4. Were there any TaskPacket migration issues from adding enrichment/intent fields?
5. Any process improvements for Sprint 3?

---

## Risks and Mitigations (Sprint 3 specific)

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Claude Agent SDK API differs from expectations | Medium | High | Day-1 spike: read docs, build hello-world agent. Fallback: direct Anthropic API with httpx. |
| Agent produces low-quality code from intent | Medium | Medium | Manual review of first 3 agent outputs. Tune system prompt. Phase 0 target is "pipe works," not "high quality." |
| GitHub API rate limits on PR creation retries | Low | Medium | Idempotency guard prevents duplicate PRs. Exponential backoff on 403/429. |
| Loopback flow complex to test | Medium | Medium | Unit test loopback with mocked verification. Integration test with controlled failing checks. |
| End-to-end integration fails in week 10 | Low | High | Start integration testing mid-sprint (week 8-9), not just week 10. |
| `claude-sonnet-4-5` unavailable or rate-limited | Low | High | Model ID is configurable in Developer role config. Can swap to another model. |

---

## Definition of Done (Sprint Level)

The sprint is done when:
1. All 2 stories (0.5, 0.7) meet their individual Definition of Done
2. All code passes `ruff` lint and `mypy` type check
3. Sprint 1 and Sprint 2 tests still pass (no regression)
4. Integration test: Intent Specification -> Primary Agent implements -> evidence bundle produced
5. Integration test: Verification failure -> loopback -> agent retries -> succeeds or exhausts
6. Integration test: Publisher creates draft PR with evidence comment and lifecycle labels
7. Integration test: Duplicate publish -> idempotency guard -> update existing PR
8. End-to-end status chain verified: received -> enriched -> intent_built -> in_progress -> verification_passed -> published

---

## Sub-tasking for Story 0.5 (XL Story Breakdown)

Story 0.5 is XL (13 points). Break into sub-tasks for daily tracking:

| Sub-task | Est. | Description |
|----------|------|-------------|
| SDK spike | 0.5d | Read Claude Agent SDK docs, build hello-world with tool use |
| Developer role config | 0.5d | Role name, system prompt template, model config |
| Tool allowlist | 0.5d | Define allowed tools, enforce at SDK registration level |
| Primary Agent orchestrator | 1.5d | Accept TaskPacket + IntentSpec, set up context, execute loop |
| Evidence bundle | 0.5d | Structure, creation, persistence linked to TaskPacket |
| Loopback handler | 1d | Accept verification failure, provide context, track count, fail on max |
| OTel spans | 0.5d | agent.implement, agent.loopback spans with attributes |
| Unit tests | 1d | Tool allowlist, evidence bundle, loopback logic |
| Integration tests | 1d | Intent -> implement -> evidence; loopback flow |

---

## Async-Readability Notes

**For anyone reading this later (human or AI):**

- Sprint 3 builds the final two components of the Phase 0 pipe: the agent that implements (Primary Agent) and the service that publishes (Publisher).
- After Sprint 3, the system can: receive a webhook (Sprint 1) -> create a TaskPacket (Sprint 1) -> enrich with scope/risk/complexity (Sprint 2) -> build an Intent Specification (Sprint 2) -> implement code changes via Claude Agent SDK (Sprint 3) -> verify against repo checks with loopback (Sprint 2) -> publish a draft PR with evidence comment and lifecycle labels (Sprint 3).
- The critical path is: 0.5 Primary Agent -> 0.7 Publisher. Publisher cannot publish without evidence bundle.
- Claude Agent SDK with `claude-sonnet-4-5` is the model choice per epic technical notes.
- If something is blocked, check: (1) is `claude_agent_sdk` installed? (2) is the ANTHROPIC_API_KEY set? (3) did Intent Builder produce a valid IntentSpec? (4) is GitHub App token available?
- After Sprint 3, Epic 0 is complete. Next: Epic 1 (Full flow + experts).

---

*Plan created by Helm. Pending Meridian review before commit.*
