# Concept: Pipeline Stages

TheStudio processes every GitHub issue through a deterministic 9-stage pipeline. Each stage has a clearly defined input, a transformation step, and a gate. Gates fail closed — output only advances to the next stage when the gate passes. Nothing is skipped; nothing proceeds silently on failure.

## The 9 stages

### 1. Intake
**Input:** Raw GitHub webhook payload
**What happens:** Signature verification, eligibility check (repo allowlist, label filter, duplicate guard)
**Gate:** Issue must be from an allowed repo and must not already have a TaskPacket
**Output:** A new `TaskPacket` with status `INTAKE_COMPLETE`

### 2. Context
**Input:** TaskPacket + GitHub API data
**What happens:** Repository history, open PRs, and related issues are fetched. Complexity and risk flags are set (e.g. `TOUCHES_AUTH`, `LARGE_DIFF_RISK`, `DEPENDENCY_CHANGE`)
**Gate:** Context enrichment must complete without API errors
**Output:** TaskPacket enriched with context signals

### 3. Intent
**Input:** Enriched TaskPacket
**What happens:** An Intent Specification is generated from the issue title, body, labels, and context signals. The spec defines correctness: what must be true of the output for the issue to be considered resolved
**Gate:** Intent spec must be parseable and non-empty
**Output:** Intent Specification (stored in TaskPacket and shown in the Intent Review tab)

### 4. Router
**Input:** Intent Specification
**What happens:** Expert agents are selected based on the intent spec. Mandatory coverage rules apply (e.g. Security Reviewer is always included when auth is in scope)
**Gate:** At least one expert agent must be selected
**Output:** Routing plan with agent assignments and confidence scores

### 5. Assembler
**Input:** Routing plan + expert agent outputs
**What happens:** Each selected expert agent analyses the issue within its domain. The Assembler merges their outputs into a unified implementation plan, resolving conflicts and recording provenance for each recommendation
**Gate:** All mandatory experts must respond; no unresolved conflicts
**Output:** Unified implementation plan

### 6. Implement
**Input:** Implementation plan
**What happens:** The Primary Agent (Developer role) generates code changes as a diff. It follows the implementation plan and the constraints in the intent spec
**Gate:** Diff must be non-empty and within the scope defined by the intent spec
**Output:** Code diff + commit message

### 7. Verify
**Input:** Code diff
**What happens:** Automated verification runs in isolation — Ruff lint, pytest (affected test suite), and a security scan. Results are written to the evidence bundle
**Gate:** All checks must pass (configurable: lint warnings may be non-blocking, but errors and test failures are always blocking)
**Output:** Verification signals (pass/fail per check) + evidence entries

### 8. QA
**Input:** Code diff + intent spec + verification signals
**What happens:** The QA Agent compares the diff against the intent specification clause by clause. It checks that every stated requirement is addressed and no out-of-scope change was made
**Gate:** All intent clauses must be satisfied; no out-of-scope changes detected
**Loopback:** On failure, a loopback signal is sent back to stage 6 (Implement) with the specific clause failures
**Output:** QA verdict + evidence entries

### 9. Publish
**Input:** Code diff + evidence bundle + trust tier
**What happens:** Depending on the trust tier — Observe (dashboard only), Suggest (draft PR), Execute (PR + auto-merge if all checks pass)
**Gate:** Trust tier check
**Output:** Draft PR on GitHub with evidence comment (Suggest/Execute) or dashboard proposal (Observe)

## Key invariants

- **Gates fail closed.** A stage that cannot produce valid output halts the task and raises a human-review flag rather than passing degraded output downstream.
- **Loopbacks carry evidence.** Every time a task loops back from QA to Implement, it carries the full rejection reason so the corrective pass is informed.
- **TaskPacket is the single source of truth.** All stage inputs and outputs are stored in the TaskPacket, making the full history queryable at any point.
- **Stages are idempotent.** Replaying a stage with the same inputs produces the same outputs. This enables safe retries after transient failures.

## Monitoring stage health

The **Pipeline Dashboard** shows real-time task counts per stage. Amber colouring on a stage node indicates a gate warning or loopback in progress. Red indicates a hard failure requiring human intervention.

## See also

- **Pipeline Dashboard tab** — real-time view of all active tasks
- **Concept: Webhooks** — how issues enter stage 1
- **Concept: Evidence Bundles** — the evidence written at stages 7, 8, and 9
- **Concept: Trust Tiers** — how stage 9 behaviour is governed
