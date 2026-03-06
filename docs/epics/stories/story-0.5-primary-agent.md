# Story 0.5 -- Primary Agent: single Developer role implementing from intent

<!-- docsmcp:start:user-story -->

> **As a** TheStudio platform, **I want** a single Primary Agent with a Developer role that implements code changes based on an Intent Specification, produces an evidence bundle, and respects a tool allowlist, **so that** the system can generate code changes that are traceable to intent and verifiable

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 13 | **Size:** XL
**Epic:** 0 — Foundation: Prove the Pipe
**Sprint:** 3 (weeks 7-9)
**Depends on:** Story 0.4 (Intent Builder), Story 0.6 (Verification Gate)

<!-- docsmcp:end:sizing -->

---

<!-- docsmcp:start:description -->
## Description

The Primary Agent is the component that actually implements code changes. In Phase 0, there is a single role: Developer. No Router, no Assembler, no expert consultation — one agent reads the Intent Specification and produces a code change with an evidence bundle.

The Developer role:
1. Reads the Intent Specification (goal, constraints, acceptance criteria, non-goals)
2. Reads the repo context (files, structure, existing code)
3. Implements the change using only tools on the allowlist
4. Runs initial checks (lint, tests if applicable)
5. Produces an evidence bundle: what changed, test results, lint results
6. Updates TaskPacket status to "in_progress" during work, then hands off to Verification

On verification failure loopback (max 2 in Phase 0):
- Agent receives verification failure evidence
- Reads the failure reason
- Attempts to fix
- Produces a new evidence bundle

<!-- docsmcp:end:description -->

---

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Define Developer role configuration (`src/agent/roles/developer.py`)
  - Role name, description, capabilities
  - Tool allowlist (read files, write files, run tests, run lint — no deploy, no DB admin)
  - System prompt template incorporating intent
- [ ] Implement Primary Agent orchestrator (`src/agent/primary_agent.py`)
  - Accept TaskPacket ID + Intent Specification
  - Set up agent context (repo clone/checkout, tool configuration)
  - Execute implementation loop
  - Produce evidence bundle on completion
  - Handle loopback (receive verification failure, re-attempt)
- [ ] Implement tool allowlist enforcement (`src/agent/tool_allowlist.py`)
  - Define allowed tools per role
  - Block any tool call not on the allowlist
  - Log blocked attempts for audit
- [ ] Implement evidence bundle creation (`src/agent/evidence.py`)
  - Structure: files_changed (list), test_results (pass/fail/skip counts), lint_results (error/warning counts), agent_reasoning (summary)
  - Persist as JSON linked to TaskPacket
- [ ] Implement loopback handler (`src/agent/loopback.py`)
  - Accept verification failure evidence
  - Provide failure context to agent for retry
  - Track loopback count (max 2 for Phase 0)
  - Fail task if max loopbacks exceeded
- [ ] Add OpenTelemetry spans (`src/agent/primary_agent.py`)
  - Span: `agent.implement` (full implementation cycle)
  - Span: `agent.loopback` (each retry attempt)
  - Attributes: correlation_id, role, loopback_count, tool_calls_count
- [ ] Write tests (`tests/test_primary_agent.py`)
  - Unit tests for tool allowlist enforcement
  - Unit tests for evidence bundle creation
  - Integration test: intent -> implementation -> evidence bundle
  - Integration test: loopback flow (failure -> retry -> success)

<!-- docsmcp:end:tasks -->

---

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Primary Agent reads Intent Specification and produces code changes in the target repo
- [ ] Only tools on the allowlist are used; blocked tools are logged
- [ ] Evidence bundle is produced with files_changed, test_results, lint_results
- [ ] Evidence bundle is persisted and linked to TaskPacket
- [ ] TaskPacket status is "in_progress" during implementation
- [ ] On verification failure loopback, agent re-reads failure evidence and retries
- [ ] Loopback count is tracked; task fails after max 2 loopbacks
- [ ] OpenTelemetry spans emitted for implementation and loopback cycles

<!-- docsmcp:end:acceptance-criteria -->

---

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

- [ ] All acceptance criteria pass
- [ ] Unit tests for tool allowlist (allowed tool passes, blocked tool logged)
- [ ] Unit tests for evidence bundle (all fields present, valid structure)
- [ ] Integration test: simple intent -> code change -> evidence
- [ ] Integration test: loopback 1 -> fix -> success
- [ ] Integration test: loopback 3 -> max exceeded -> task failed
- [ ] Code passes ruff lint and mypy type check

<!-- docsmcp:end:definition-of-done -->

---

<!-- docsmcp:start:test-cases -->
## Test Cases

| # | Scenario | Input | Expected Output |
|---|----------|-------|-----------------|
| 1 | Simple implementation | Intent: "Add hello endpoint" | Code change + evidence bundle |
| 2 | Tool allowlist pass | Agent calls "read_file" | Tool executes normally |
| 3 | Tool allowlist block | Agent calls "drop_database" | Tool blocked, attempt logged |
| 4 | Evidence bundle | After implementation | files_changed, test_results, lint_results present |
| 5 | Loopback success | Verification failure -> retry | Second attempt succeeds, loopback_count=1 |
| 6 | Max loopbacks | 3 verification failures | Task status = failed after loopback 2 |
| 7 | Status tracking | During implementation | TaskPacket status = in_progress |
| 8 | OTel spans | Any implementation | Spans for agent.implement and agent.loopback emitted |

<!-- docsmcp:end:test-cases -->

---

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- **Agent framework:** Claude Agent SDK (`claude_agent_sdk`). The Primary Agent is a Claude Agent SDK agent with tool use.
- **Model:** `claude-sonnet-4-5` for Phase 0 Developer role. Model ID is configurable per role for future phases.
- **System prompt contract:** The Developer role system prompt has three sections:
  1. **Role** — "You are a Developer agent. You implement code changes based on an Intent Specification."
  2. **Intent injection** — The full Intent Specification (goal, constraints, acceptance criteria, non-goals) is injected as a structured block.
  3. **Constraints** — Tool allowlist enforcement rules, repo conventions from Repo Profile, and output format for the evidence bundle.
- **Tool allowlist** is enforced at the Claude Agent SDK tool-registration level — only allowed tools are registered with the agent. The agent physically cannot call tools not on the list.
- **Evidence bundle** is the primary artifact for Verification Gate (Story 0.6) and Publisher (Story 0.7).
- **Loopback** is a Temporal activity retry with new context (verification failure evidence). Not a prompt retry — the agent receives a fresh Claude Agent SDK invocation with the original intent plus the failure evidence appended.
- **Architecture references:**
  - Agent roles: `thestudioarc/08-agent-roles.md` (Developer role)
  - System runtime flow: `thestudioarc/15-system-runtime-flow.md` (Step 5: Execute)
  - Architecture guardrails: `thestudioarc/22-architecture-guardrails.md`

<!-- docsmcp:end:technical-notes -->

---

## Files Affected

| File | Action | Description |
|------|--------|-------------|
| `src/agent/__init__.py` | Create | Package init |
| `src/agent/primary_agent.py` | Create | Agent orchestrator |
| `src/agent/roles/__init__.py` | Create | Roles package |
| `src/agent/roles/developer.py` | Create | Developer role config + prompt |
| `src/agent/tool_allowlist.py` | Create | Tool allowlist enforcement |
| `src/agent/evidence.py` | Create | Evidence bundle creation |
| `src/agent/loopback.py` | Create | Loopback handler |
| `tests/test_primary_agent.py` | Create | Unit and integration tests |

---

<!-- docsmcp:start:dependencies -->
## Dependencies

- **Story 0.4 (Intent Builder):** Agent reads Intent Specification
- **Story 0.6 (Verification Gate):** Agent hands off to verification; receives loopback on failure
- **Story 0.8 (Repo Profile):** Tool allowlist is defined in repo profile

<!-- docsmcp:end:dependencies -->

---

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [x] **I**ndependent -- Depends on Intent Builder and Verification Gate interfaces (can mock)
- [x] **N**egotiable -- LLM choice, prompt structure, exact tool list are flexible
- [x] **V**aluable -- The agent is the core value — it produces the actual code changes
- [x] **E**stimable -- 13 points (XL), most complex story in Phase 0
- [ ] **S**mall -- Large story; may need sub-tasking during sprint planning
- [x] **T**estable -- 8 test cases covering implementation, allowlist, loopback, evidence

<!-- docsmcp:end:invest -->

---

*Story created by Saga. Part of Epic 0 — Foundation: Prove the Pipe.*
