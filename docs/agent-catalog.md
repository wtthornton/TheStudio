# TheStudio Agent Catalog

**Date:** 2026-03-12
**Scope:** All 8 pipeline agents + 1 platform service (Publisher)
**Methodology:** Architecture docs cross-referenced against `src/` implementation. Gaps flagged where code diverges from design.

---

## How to Read This Document

Each agent entry covers:
- **Purpose** — what it does in the pipeline
- **System Prompt** — the prompt template or guidance given to the LLM
- **Tools** — what tools/capabilities the agent has access to
- **Lifecycle** — when it starts, how long it runs, when it ends
- **Model Class** — which LLM tier it uses (fast/balanced/strong)
- **Inputs / Outputs** — what it consumes and produces
- **Gaps** — where implementation diverges from architecture

---

## 1. Intake Agent

**Pipeline stage:** 1 — Intake
**Source:** `src/intake/intake_agent.py`
**Architecture:** `thestudioarc/08-agent-roles.md` (step 1), `thestudioarc/15-system-runtime-flow.md`

### Purpose

First agent in the pipeline. Evaluates whether a GitHub issue is eligible for automation, selects a base role, applies overlays from risk labels, and computes the EffectiveRolePolicy.

### System Prompt

| Architecture | Implementation |
|---|---|
| LLM-powered agent with classification prompt | **GAP: No system prompt. No LLM call.** Pure function (`evaluate_eligibility()`) with deterministic rule matching. |

### Tools

| Architecture | Implementation |
|---|---|
| Reads GitHub issue metadata, labels, repo profile | Receives pre-fetched parameters (labels, repo status, issue text) |
| Adversarial input detection | **THERE** — calls `detect_suspicious_patterns()` on issue title + body |
| No write access to GitHub | Correct — no GitHub writes |

### Lifecycle

| Property | Value |
|---|---|
| **Triggered by** | Temporal workflow start (`intake_activity`) |
| **Timeout** | 2 minutes |
| **Retries** | 2 (exponential backoff) |
| **Duration** | Milliseconds (pure function, no I/O beyond adversarial check) |
| **Terminates when** | Returns `IntakeResult` (accepted or rejected) |
| **Escalation** | Repo not registered or tier blocks |

### Model Class

| Architecture | Implementation |
|---|---|
| Fast model, strict token caps | **GAP: No model call.** Rule-based only. |

### Inputs

- GitHub issue labels, title, body
- Repo registration status, pause status
- Active workflow check
- Event delivery ID

### Outputs

- `IntakeResult`: accepted/rejected + EffectiveRolePolicy (base role + overlays)
- `IntakeRejection` with structured reason on failure
- Risk flags (adversarial input warnings)

### Gaps

| Gap | Severity |
|---|---|
| No LLM — architecture expects LLM-based classification | Phase 0 simplification (D3) |
| No admin override of role selection | Documented as deferred (D5) |

---

## 2. Context Manager Agent

**Pipeline stage:** 2 — Context
**Source:** `src/context/context_manager.py`
**Architecture:** `thestudioarc/03-context-manager.md`

### Purpose

Scoping engine. Enriches the TaskPacket with scope analysis, risk flags, complexity index, and service context packs. Prevents "garbage in, garbage out" for downstream agents.

### System Prompt

| Architecture | Implementation |
|---|---|
| LLM-powered with progressive disclosure guidance | **GAP: No system prompt. No LLM call.** Deterministic functions: `analyze_scope()`, `flag_risks()`, `compute_complexity_index()`, `get_context_packs()`. |

### Tools

| Architecture | Implementation |
|---|---|
| Repo read tools, service context pack lookup | `analyze_scope()` (regex), `flag_risks()` (keyword), `get_context_packs()` (registry lookup) |
| Read-only — no GitHub writes | Correct |
| Context-retrieval suite via Tool Hub | **Workflow stub** references Tool Hub access; actual `enrich_taskpacket()` uses direct functions |

### Lifecycle

| Property | Value |
|---|---|
| **Triggered by** | Temporal `context_activity` after Intake passes |
| **Timeout** | 10 minutes |
| **Retries** | 3 (exponential backoff) |
| **Duration** | Sub-second for pure functions; async DB read/write for TaskPacket update |
| **Terminates when** | Returns `ContextOutput` (scope, risk flags, complexity, packs) |
| **Escalation** | Repeated failure or missing pack gap |

### Model Class

| Architecture | Implementation |
|---|---|
| Fast or balanced for summarization; prefer deterministic tools | **GAP: No model call.** All deterministic. Workflow stub records Model Gateway audit but actual enrichment is rule-based. |

### Inputs

- TaskPacket ID, repo, issue title, issue body
- Service Context Pack registry

### Outputs

- Enriched TaskPacket with: scope, risk flags, complexity index (5 dimensions), context packs
- `ContextPackSignal` events (pack_used / pack_missing)

### Gaps

| Gap | Severity |
|---|---|
| No LLM — architecture expects agent judgment for scope analysis | Phase 0 simplification |
| No open questions / uncertainty recording | Documented as deferred (D4) |

---

## 3. Intent Builder Agent

**Pipeline stage:** 3 — Intent
**Source:** `src/intent/intent_builder.py`
**Architecture:** `thestudioarc/11-intent-layer.md`

### Purpose

Defines what correctness means before implementation begins. Produces a versioned Intent Specification with goal, constraints, acceptance criteria, and non-goals.

### System Prompt

| Architecture | Implementation |
|---|---|
| LLM agent that consults intent experts via Router | **GAP: No system prompt. No LLM call.** Rule-based extraction using regex patterns for checkboxes, bullet lists, "out of scope" sections. |

### Tools

| Architecture | Implementation |
|---|---|
| Read TaskPacket, consult Router for intent experts | Reads TaskPacket from DB; no Router consultation |
| Intent versioning and refinement | **THERE** — `refinement.py` supports version increment and update |

### Lifecycle

| Property | Value |
|---|---|
| **Triggered by** | Temporal `intent_activity` after Context completes |
| **Timeout** | 10 minutes |
| **Retries** | 2 (exponential backoff) |
| **Duration** | Sub-second (regex extraction + DB writes) |
| **Terminates when** | Returns `IntentOutput` with intent_spec_id, version, goal, criteria |
| **Escalation** | Missing required fields or conflicting constraints |
| **Can be re-invoked** | Yes — refinement loop when QA or Assembler request it |

### Model Class

| Architecture | Implementation |
|---|---|
| Balanced by default; strong when security/compliance/billing overlays | **GAP: No model call.** Workflow stub records gateway audit but `build_intent()` is rule-based. |

### Inputs

- TaskPacket (enriched) with risk flags
- Issue title and body
- Prior intent version (for refinement)

### Outputs

- `IntentSpecRead`: goal, constraints, acceptance criteria, non-goals, version
- Updated TaskPacket with intent reference

### Gaps

| Gap | Severity |
|---|---|
| No LLM — architecture expects semantic extraction | Phase 0 simplification (D3) |
| No invariant identification ("what must not change") | Valuable gap (V7) |
| No expert consultation via Router for intent refinement | Phase 0 simplification |

---

## 4. Expert Router Agent

**Pipeline stage:** 4 — Router
**Source:** `src/routing/router.py`
**Architecture:** `thestudioarc/05-expert-router.md`

### Purpose

Single entry point for expert consultation. Selects expert subsets based on risk flags, mandatory coverage, and reputation weights. Enforces budget limits.

### System Prompt

| Architecture | Implementation |
|---|---|
| LLM agent for synthesis and selection reasoning | **GAP: No system prompt. No LLM call.** Pure function `route()` with algorithmic scoring: `trust_tier_score * (1 + weight * confidence)`. |

### Tools

| Architecture | Implementation |
|---|---|
| Expert Library query (class + capability tags) | **THERE** — receives `available_experts` list, filters by class |
| Reputation Engine lookup | **THERE** — injectable `ReputationLookupFn` |
| Recruiter callback on gaps | **THERE** — emits `RecruiterRequest` when no candidates found |
| Escalation triggers | **THERE** — `EscalationRequest` on high-risk + budget exhaustion or low confidence |

### Lifecycle

| Property | Value |
|---|---|
| **Triggered by** | Temporal `router_activity` after Intent completes |
| **Timeout** | 15 minutes |
| **Retries** | 2 (exponential backoff) |
| **Duration** | Milliseconds (pure function, no I/O) |
| **Terminates when** | Returns `ConsultPlan` (selections, recruiter requests, rationale) |
| **Escalation** | Budget exceeded, missing coverage, low confidence on high risk |

### Model Class

| Architecture | Implementation |
|---|---|
| Balanced for synthesis | **GAP: No model call.** Algorithmic scoring only. |

### Inputs

- EffectiveRolePolicy (mandatory expert classes, budget)
- Risk flags from TaskPacket
- Available experts from Expert Library
- Reputation weights (optional injectable)

### Outputs

- `ConsultPlan`: selected experts with scores, recruiter requests, rationale, budget remaining, escalations

### Gaps

| Gap | Severity |
|---|---|
| No LLM — architecture expects reasoning for selection | Phase 0 simplification |
| All consults are parallel — no staged or shadow patterns | Valuable gap (V8, V9) |

---

## 5. Expert Recruiter Agent

**Pipeline stage:** 4 — Router (sub-step)
**Source:** `src/recruiting/recruiter.py`
**Architecture:** `thestudioarc/04-expert-recruiter.md`

### Purpose

Manages expert supply. When the Router finds no eligible expert for a required class, the Recruiter searches for existing experts, selects a template, constructs an expert pack, runs qualification, and registers the new expert.

### System Prompt

| Architecture | Implementation |
|---|---|
| LLM agent with skill-pack orientation | **GAP: No system prompt. No LLM call.** Template-based creation with deterministic qualification harness. |

### Tools

| Architecture | Implementation |
|---|---|
| Expert Library CRUD | **THERE** — `search_experts()`, `create_expert()`, `update_expert_version()` |
| Template catalog | **THERE** — `templates.py` with vetted patterns |
| Qualification harness | **THERE** — `qualification.py` with safety checks |

### Lifecycle

| Property | Value |
|---|---|
| **Triggered by** | Router emits `RecruiterRequest` (not a separate Temporal activity) |
| **Timeout** | Runs within Router's 15-minute timeout |
| **Duration** | Async DB operations (search, create/update expert) |
| **Terminates when** | Returns `RecruitmentResult` (success/failure + expert) |

### Model Class

| Architecture | Implementation |
|---|---|
| Not specified (implied balanced) | **GAP: No model call.** Template-based only. |

### Inputs

- `RecruiterRequest` (expert class, capability tags, reason)
- Expert Library (existing experts)
- Template catalog

### Outputs

- `RecruitmentResult`: expert (created/existing/version_updated/failed) + qualification result

### Gaps

| Gap | Severity |
|---|---|
| No LLM — architecture expects agent judgment for pack construction | Phase 0 simplification |
| No tool policy binding formalized in code | Structural gap |
| 8-step pipeline described in docs; code combines several steps | Structural gap |

---

## 6. Assembler Agent

**Pipeline stage:** 5 — Assembler
**Source:** `src/assembler/assembler.py`
**Architecture:** `thestudioarc/07-assembler.md`

### Purpose

Merges expert outputs into a single executable plan. Resolves conflicts using intent as tie-breaker. Records provenance for attribution and learning.

### System Prompt

| Architecture | Implementation |
|---|---|
| LLM agent for synthesis, conflict resolution, plan generation | **GAP: No system prompt. No LLM call.** Deterministic merging with keyword-based conflict detection and intent constraint matching. |

### Tools

| Architecture | Implementation |
|---|---|
| Read intent constraints and expert outputs | **THERE** — receives as function parameters |
| Conflict resolution with intent tie-breaking | **THERE** — `_resolve_with_intent()` uses keyword matching |
| QA handoff mapping | **THERE** — `_build_qa_handoff()` maps criteria to validations |
| Provenance record | **THERE** — full `ProvenanceRecord` with expert attribution |
| Escalation on high-risk conflicts | **THERE** — `EscalationRequest` on unresolved high-risk conflicts |

### Lifecycle

| Property | Value |
|---|---|
| **Triggered by** | Temporal `assembler_activity` after Router completes |
| **Timeout** | 10 minutes |
| **Retries** | 2 (exponential backoff) |
| **Duration** | Milliseconds (pure function) |
| **Terminates when** | Returns `AssemblyPlan` (steps, conflicts, risks, QA handoff, provenance) |
| **Escalation** | Unresolved conflicts in high-risk domains |

### Model Class

| Architecture | Implementation |
|---|---|
| Balanced; strong for multi-domain conflicts | **GAP: No model call.** Keyword matching only. |

### Inputs

- Expert outputs (structured recommendations, risks, validations, assumptions)
- Intent constraints and acceptance criteria
- TaskPacket ID, correlation ID, intent version

### Outputs

- `AssemblyPlan`: plan steps, conflicts (resolved/unresolved), risks, QA handoff, provenance, intent refinement request, escalations

### Gaps

| Gap | Severity |
|---|---|
| No LLM — architecture expects synthesis and reasoning | Phase 0 simplification |
| Conflict detection is assumption-overlap only | Keyword matching, not semantic |

---

## 7. Primary Agent (Developer)

**Pipeline stage:** 6 — Implement
**Source:** `src/agent/primary_agent.py`, `src/agent/developer_role.py`
**Architecture:** `thestudioarc/08-agent-roles.md`

### Purpose

The only **true agentic loop** in the system. Uses Claude Agent SDK to implement code changes against a target repository, guided by the Intent Specification. Produces an evidence bundle.

### System Prompt

**THERE — Full implementation.** Template in `developer_role.py`:

```
You are a Developer Agent for TheStudio. Your job is to implement code changes
in a target repository according to a precise Intent Specification.

## Rules
1. Implement ONLY what the intent goal describes...
2. Respect all constraints...
3. Write tests that map to acceptance criteria...
4. Produce small, focused diffs...
5. Do not modify files outside the repository working directory.
6. Run lint and test commands to verify before finishing.

## Intent Specification
**Goal:** {goal}
**Constraints:** {constraints}
**Acceptance Criteria:** {acceptance_criteria}
**Non-Goals:** {non_goals}

## Context
- Repository: {repo}
- TaskPacket ID: {taskpacket_id}
- Complexity: {complexity}
- Risk flags: {risk_flags}
```

### Tools

| Tool | Status |
|---|---|
| Read | **THERE** |
| Write | **THERE** |
| Edit | **THERE** |
| Glob | **THERE** |
| Grep | **THERE** |
| Bash | **THERE** |
| Permission mode | `acceptEdits` |

### Lifecycle

| Property | Value |
|---|---|
| **Triggered by** | Temporal `implement_activity` after Assembler completes |
| **Timeout** | 60 minutes |
| **Retries** | 2 (exponential backoff) |
| **Duration** | Minutes to tens of minutes (full agentic loop with tool use) |
| **Max turns** | 30 (configurable via `settings.agent_max_turns`) |
| **Max budget** | $5.00 USD default (per-task, from `DeveloperRoleConfig`) |
| **Terminates when** | Agent produces `ResultMessage` or budget/turns exhausted |
| **Loopback** | `handle_loopback()` re-invokes with verification failure context |
| **Escalation** | Repeated same-category failures |

### Model Class

| Architecture | Implementation |
|---|---|
| Balanced by default; strong for complex/high-risk | **THERE** — Model Gateway integration with `_resolve_provider()`, fallback chains, budget enforcement |

Default model: `claude-sonnet-4-5`

### Inputs

- TaskPacket (from DB)
- Intent Specification (from DB)
- Repository path (local checkout)
- DeveloperRoleConfig (tool allowlist, model, budget)
- Overlays, repo tier, complexity (for Model Gateway routing)

### Outputs

- `EvidenceBundle`: taskpacket_id, intent_version, files_changed, agent_summary, loopback_attempt
- Model audit record (provider, tokens, cost)

### Gaps

| Gap | Severity |
|---|---|
| Architect role not implemented | Deferred (D1) |
| Planner role not implemented | Deferred (D2) |

---

## 8. QA Agent

**Pipeline stage:** 8 — QA
**Source:** `src/qa/qa_agent.py`
**Architecture:** `thestudioarc/14-qa-quality-layer.md`

### Purpose

Intent-first validation. Validates implementation against acceptance criteria, classifies defects by category and severity, blocks on intent gaps, and triggers loopback or intent refinement.

### System Prompt

| Architecture | Implementation |
|---|---|
| LLM agent for judgment and validation | **GAP: No system prompt. No LLM call.** Deterministic keyword matching against evidence dictionary. |

### Tools

| Architecture | Implementation |
|---|---|
| Read evidence bundle | **THERE** — receives evidence dict |
| Read intent and QA handoff | **THERE** — receives criteria and handoff mappings |
| Consult QA experts via Router | **GAP** — no Router consultation (V10) |
| Defect taxonomy (8 categories) | **THERE** — full `DefectCategory` enum |
| Severity classification (S0-S3) | **THERE** — full `Severity` enum |
| Signal emission (qa_passed/defect/rework) | **THERE** — via JetStream |

### Lifecycle

| Property | Value |
|---|---|
| **Triggered by** | Temporal `qa_activity` after Verification passes |
| **Timeout** | 30 minutes |
| **Retries** | 2 (exponential backoff) |
| **Duration** | Milliseconds (deterministic validation) |
| **Terminates when** | Returns `QAResult` (passed/failed + defects + loopback/refinement) |
| **Loopback** | Emits `LoopbackRequest` with defect list and intent mapping |
| **Escalation** | Defect pressure high or intent gap |

### Model Class

| Architecture | Implementation |
|---|---|
| Balanced; strong for high-risk or repeated loops | **GAP: No model call.** Workflow stub records gateway audit but `validate()` is rule-based. |

### Inputs

- Acceptance criteria from Intent Specification
- QA handoff mappings from Assembler
- Evidence bundle from implementation/verification

### Outputs

- `QAResult`: passed/failed, criteria results, defects (category + severity), loopback request, intent refinement request
- `has_intent_gap` flag (blocks qa_passed)

### Gaps

| Gap | Severity |
|---|---|
| No LLM — architecture expects reasoning for validation | Phase 0 simplification |
| No QA expert consultation via Router | Valuable gap (V10) |
| Reopen event handling in QA | Deferred (D6) — outcome module handles it |

---

## 9. Publisher (Platform Service — NOT an Agent)

**Pipeline stage:** 9 — Publish
**Source:** `src/publisher/publisher.py`
**Architecture:** `thestudioarc/15-system-runtime-flow.md`

### Purpose

The **only writer to GitHub**. Creates draft PRs, posts evidence comments, manages lifecycle labels, reconciles tier labels. Deterministic — no LLM.

### System Prompt

None. Publisher is explicitly a platform service, not an agent.

### Tools

| Tool | Status |
|---|---|
| GitHub API (create PR, comments, labels) | **THERE** — via `GitHubClient` |
| Idempotency guard (branch lookup) | **THERE** — `find_pr_by_head()` |
| Evidence comment formatting | **THERE** — `format_evidence_comment()` with `EVIDENCE_COMMENT_MARKER` |
| Tier label reconciliation | **THERE** — add/remove tier labels |
| Merge mode awareness | **THERE** — `DRAFT_ONLY`, `REQUIRE_REVIEW`, `AUTO_MERGE` |

### Lifecycle

| Property | Value |
|---|---|
| **Triggered by** | Temporal `publish_activity` after QA passes |
| **Timeout** | 5 minutes |
| **Retries** | 5 (fast retry — idempotency guard prevents duplicates) |
| **Duration** | Seconds (GitHub API calls) |
| **Terminates when** | Returns `PublishResult` (PR number, URL, created/updated, marked_ready) |

### Inputs

- TaskPacket, Intent Specification, Evidence Bundle, Verification Result
- GitHub client, repo tier, QA passed status

### Outputs

- Draft PR on GitHub with evidence comment
- Lifecycle labels (agent:done, tier:observe/suggest)
- `PublishResult` with PR metadata

---

## 10. Verification Gate (Platform Service — NOT an Agent)

**Pipeline stage:** 7 — Verify
**Source:** `src/verification/gate.py`
**Architecture:** `thestudioarc/13-verification-gate.md`

### Purpose

Deterministic quality check orchestrator. Runs ruff, pytest, and security scans against code changes. Gates fail closed. Triggers loopback on failure (max 2).

### System Prompt

None. Verification Gate is a deterministic gate, not an agent.

### Lifecycle

| Property | Value |
|---|---|
| **Triggered by** | Temporal `verify_activity` after Implementation completes |
| **Timeout** | 45 minutes |
| **Retries** | 3 (bounded — see flake policy) |
| **Max loopbacks** | 2 (hardcoded `MAX_LOOPBACKS`) |
| **Duration** | Seconds to minutes (runs pytest, ruff, security scan) |

---

## Summary: Agent Maturity Matrix

| # | Agent | Has LLM? | Has System Prompt? | Has Tool Loop? | Lifecycle |
|---|---|---|---|---|---|
| 1 | Intake Agent | No (rule-based) | No | No | ~ms, 2min timeout |
| 2 | Context Manager | No (rule-based) | No | No | ~ms, 10min timeout |
| 3 | Intent Builder | No (regex) | No | No | ~ms, 10min timeout |
| 4 | Expert Router | No (algorithmic) | No | No | ~ms, 15min timeout |
| 5 | Expert Recruiter | No (template) | No | No | ~ms, within Router |
| 6 | Assembler | No (keyword matching) | No | No | ~ms, 10min timeout |
| **7** | **Primary Agent** | **Yes (Claude SDK)** | **Yes (full template)** | **Yes (30 turns)** | **Minutes, 60min timeout** |
| 8 | QA Agent | No (keyword matching) | No | No | ~ms, 30min timeout |

**Key finding:** Only 1 of 8 agents (Primary Agent/Developer) currently uses an LLM with a system prompt and agentic tool loop. The remaining 7 are Phase 0 rule-based implementations. The architecture intends all 8 to be LLM-powered — upgrading them is a Phase 2+ effort.

---

## Dependency Chain (Agent Execution Order)

```
Intake (2min) ──→ Context (10min) ──→ Readiness Gate ──→ Intent (10min) ──→ Router (15min)
                                                                              │
                                                                              ├── Recruiter (if gaps)
                                                                              ▼
                                                                          Assembler (10min)
                                                                              │
                                                                              ▼
                                                                      Primary Agent (60min)
                                                                              │
                                                                              ▼
                                                                     Verification Gate (45min)
                                                                         │         │
                                                                    pass ▼    fail ▼ (loopback ×2)
                                                                      QA Agent (30min)
                                                                         │         │
                                                                    pass ▼    fail ▼ (loopback)
                                                                       Publisher (5min)
```

**Total pipeline timeout budget:** ~197 minutes (worst case with no loopbacks)
**With max loopbacks (2 verify + QA):** adds up to 3 × (60min + 45min + 30min) = +405 minutes theoretical max

---

## Readiness Gate (Bonus — Not an Agent)

**Pipeline stage:** 2.5 — between Context and Intent
**Source:** `src/readiness/scorer.py` (called via `readiness_activity`)

Scores issue quality before intent building. Pure scoring engine (no LLM). Gate decision determines whether pipeline proceeds or holds for clarification questions.

| Property | Value |
|---|---|
| **Triggered by** | Temporal `readiness_activity` after Context |
| **Duration** | Milliseconds (pure function) |
| **Outputs** | `ReadinessActivityOutput`: proceed/hold, score, missing dimensions, clarification questions |
