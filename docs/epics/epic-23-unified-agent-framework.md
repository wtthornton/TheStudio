# Epic 23 — Unified Agent Framework: Convert All Pipeline Nodes to LLM-Powered Agents

**Author:** Saga
**Date:** 2026-03-12
**Status:** In Progress — Sprint 2 started (2026-03-16)
**Target Sprint:** Multi-sprint (estimated 3-4 sprints after Epic 22 completes)
**Sprint 1:** Complete (Stories 1.1-1.10, AgentRunner framework + Primary Agent refactor)
**Sprint 2:** In Progress (Intake Agent + Context Agent conversion delivered 2026-03-16)
**Prerequisites:** Epic 19 (Gateway Wiring) must be complete. Epic 22 (Execute Tier) recommended.

---

## 1. Title

Unified Agent Framework: Convert All Pipeline Nodes to LLM-Powered Agents — Build a common `AgentRunner` base class with shared system prompt templating, Model Gateway integration, structured output parsing, observability, and budget enforcement, then convert all 7 rule-based pipeline nodes (Intake, Context Manager, Intent Builder, Expert Router, Expert Recruiter, Assembler, QA Agent) into true LLM-powered agents that share this infrastructure with the existing Primary Agent.

## 2. Narrative

TheStudio has 8 agents in its pipeline. One of them works. The Primary Agent (Developer role) uses the Claude Agent SDK with a system prompt, tool access, Model Gateway routing, budget enforcement, and audit logging. The other 7 nodes — Intake, Context Manager, Intent Builder, Expert Router, Expert Recruiter, Assembler, and QA Agent — are Phase 0 rule-based stubs. They use regex, keyword matching, and hardcoded logic where the architecture documents describe LLM-powered reasoning.

This was a valid Phase 0 tradeoff. The pipeline needed to run end-to-end before individual nodes could be enriched. But the gap is now limiting:

**Intake classification is brittle.** `evaluate_eligibility()` maps labels to roles via a static dictionary. It cannot reason about issue text, infer work type from context, or detect subtle risk signals beyond exact keyword matches. The architecture describes an agent that reads issue content and selects roles with judgment.

**Context enrichment is shallow.** `analyze_scope()` and `flag_risks()` use regex patterns. They cannot identify impacted services from natural language descriptions, reason about cross-service dependencies, or produce meaningful complexity assessments for novel work. The architecture describes an agent that uses progressive disclosure and structured reasoning.

**Intent extraction misses semantics.** `extract_goal()` takes the issue title and first paragraph. `extract_acceptance_criteria()` looks for markdown checkboxes. Neither can synthesize implicit requirements, identify missing constraints, or reason about invariants. The architecture describes an agent that consults intent experts via the Router and produces rich Intent Specifications.

**The Router is a scoring formula.** `route()` computes `trust_tier_score * (1 + weight * confidence)` and returns the top expert per class. It cannot reason about whether staged vs parallel consultation is appropriate, or whether a shadow expert should be included for evaluation. The architecture describes an agent that makes these judgment calls.

**The Assembler is keyword matching.** `_detect_conflicts()` looks for overlapping assumptions between expert outputs. `_resolve_with_intent()` does case-insensitive string containment checks. Neither can perform semantic conflict resolution, synthesize multi-expert reasoning into a coherent plan, or identify subtle contradictions. The architecture describes an agent that uses LLM synthesis.

**QA validation is mechanical.** `validate()` checks for keyword overlap between acceptance criteria and evidence keys. It cannot reason about whether implementation actually satisfies intent, identify edge cases not covered by explicit criteria, or make severity judgments based on context. The architecture describes an agent that performs intent-first validation with domain reasoning.

The fix is not to write 7 independent agent implementations. The Primary Agent already solved the hard problems: Claude Agent SDK integration, Model Gateway routing, budget enforcement, system prompt templating, audit logging, and observability. But this infrastructure is locked inside `src/agent/primary_agent.py` and `src/agent/developer_role.py`. It cannot be reused.

This epic extracts the common agent infrastructure into a shared framework, then converts each pipeline node to use it. The result: 8 agents that share one architecture, one set of operational controls, and one pattern for system prompts, tool access, output parsing, and observability. When a new agent pattern is needed (Architect role, Planner role), it slots into the framework with a config file and a system prompt — not a copy-paste of 200 lines of gateway wiring.

### Why Not Just Add LLM Calls to Existing Functions?

Three reasons:

1. **Operational consistency.** Every agent must route through the Model Gateway, enforce budgets, record audit trails, and emit observability spans. Without a shared base, each conversion would re-implement these independently, creating 7 slightly different approaches to the same problems.

2. **Testability.** A common agent framework means common test patterns: mock the LLM, assert the system prompt, verify structured output parsing, check audit records. Without it, each agent needs bespoke test infrastructure.

3. **Model class routing.** The architecture (doc 26) assigns different model classes to different pipeline steps. The Model Gateway already supports this via the `step` parameter in `select_model()`. A shared framework makes step-to-model-class mapping declarative, not buried in each module.

### What Changes and What Doesn't

**Changes:** How each node reasons (LLM replaces regex/keywords). How each node is configured (shared `AgentConfig` replaces ad-hoc parameters). How each node reports (shared audit and observability).

**Does NOT change:** Pipeline orchestration (Temporal workflow activities are unchanged). Domain models (TaskPacket, IntentSpec, ExpertOutput, etc. are unchanged). Gate contracts (fail-closed behavior unchanged). Signal emission patterns (unchanged).

The rule-based logic is preserved as **fallback behavior** when the LLM is unavailable or budget is exhausted. This is not a rip-and-replace — it's a lift into a framework that enables LLM reasoning while preserving deterministic fallback.

## 3. References

| Artifact | Location |
|----------|----------|
| Agent Catalog (all 8 agents documented) | `docs/agent-catalog.md` |
| Architecture-vs-implementation mapping | `docs/architecture-vs-implementation-mapping.md` |
| Architecture overview | `thestudioarc/00-overview.md` |
| Context Manager architecture | `thestudioarc/03-context-manager.md` |
| Expert Recruiter architecture | `thestudioarc/04-expert-recruiter.md` |
| Expert Router architecture | `thestudioarc/05-expert-router.md` |
| Assembler architecture | `thestudioarc/07-assembler.md` |
| Agent Roles architecture | `thestudioarc/08-agent-roles.md` |
| Intent Layer architecture | `thestudioarc/11-intent-layer.md` |
| QA Quality Layer architecture | `thestudioarc/14-qa-quality-layer.md` |
| System Runtime Flow | `thestudioarc/15-system-runtime-flow.md` |
| Model Runtime and Routing | `thestudioarc/26-model-runtime-and-routing.md` |
| Primary Agent (reference implementation) | `src/agent/primary_agent.py` |
| Developer Role (system prompt template) | `src/agent/developer_role.py` |
| Evidence Bundle | `src/agent/evidence.py` |
| Model Gateway | `src/admin/model_gateway.py` |
| Workflow activities | `src/workflow/activities.py` |
| Existing agent implementations | `src/intake/intake_agent.py`, `src/context/context_manager.py`, `src/intent/intent_builder.py`, `src/routing/router.py`, `src/recruiting/recruiter.py`, `src/assembler/assembler.py`, `src/qa/qa_agent.py` |
| Coding standards | `thestudioarc/20-coding-standards.md` |
| Pipeline stage mapping | `.claude/rules/pipeline-stages.md` |
| Hermes Agent (comparative analysis) | `github.com/NousResearch/hermes-agent` (v0.2.0, MIT) — patterns P1-P4 adopted from this analysis |
| Hermes memory tool (reference for P2, P3) | `hermes-agent/tools/memory_tool.py` — `_scan_memory_content()`, `MemoryStore` |
| Hermes iteration budget (reference for P4) | `hermes-agent/run_agent.py` — `IterationBudget` class |

## 4. Acceptance Criteria

### Foundation: Unified Agent Framework

1. **`AgentConfig` dataclass exists.** `src/agent/framework.py` contains an `AgentConfig` frozen dataclass with fields: `agent_name` (str), `pipeline_step` (str), `model_class` (str — "fast", "balanced", "strong"), `system_prompt_template` (str), `tool_allowlist` (list[str] — empty for non-tool-using agents), `max_turns` (int), `max_budget_usd` (float), `permission_mode` (str), `output_schema` (type[BaseModel] | None — for structured output parsing), `fallback_fn` (Callable | None — rule-based fallback when LLM unavailable), `block_on_threat` (bool — when True, detected injection patterns in input block the LLM call and trigger fallback; default True for intake, False for others; see Hermes analysis P2), `compress_threshold` (float — 0.0-1.0, context compression trigger for agentic mode; default 0.5; see Hermes analysis P7), `compress_model_class` (str — model class for compression summarization; default "fast"; see Hermes analysis P7).

2. **`AgentRunner` class exists.** `src/agent/framework.py` contains an `AgentRunner` class with methods:
   - `__init__(self, config: AgentConfig)` — stores config, initializes tracer.
   - `async run(self, context: AgentContext) -> AgentResult` — the main execution method.
   - `build_system_prompt(self, context: AgentContext) -> str` — renders the system prompt template with context variables.
   - `_resolve_provider(self, overlays, repo_tier, complexity) -> ProviderConfig` — calls Model Gateway with step and model class from config.
   - `_check_budget(self, task_id: str) -> None` — calls `BudgetEnforcer.check_budget()`; raises `BudgetExceededError` if over limit.
   - `_record_audit(self, ...) -> None` — creates `ModelCallAudit` record.
   - `_parse_output(self, raw: str) -> BaseModel | str` — parses agent output against `output_schema` if configured; returns raw string if no schema.

3. **`AgentContext` dataclass exists.** Contains all inputs an agent might need: `taskpacket_id` (UUID | None), `correlation_id` (UUID | None), `repo` (str), `issue_title` (str), `issue_body` (str), `labels` (list[str]), `risk_flags` (dict), `complexity` (str), `overlays` (list[str]), `repo_tier` (str), `intent` (IntentSpecRead | None), `expert_outputs` (list | None), `evidence` (dict | None), `extra` (dict — agent-specific context), `per_repo_notes` (list[str] — bounded operational notes for this repo, injected as frozen snapshot; see Hermes analysis P3), `pipeline_budget` (PipelineBudget | None — shared cost counter across all agents for this task; see Hermes analysis P4).

4. **`AgentResult` dataclass exists.** Contains: `agent_name` (str), `raw_output` (str), `parsed_output` (BaseModel | None), `model_used` (str), `tokens_estimated` (int), `cost_estimated` (float), `duration_ms` (int), `used_fallback` (bool — True if rule-based fallback was used instead of LLM), `operational_notes` (list[str] — optional agent-emitted notes about repo-specific observations for future tasks; see Hermes analysis P3), `threat_flags` (list[str] — injection patterns detected in input; see Hermes analysis P2).

5. **`AgentRunner.run()` follows a standard lifecycle:**
   a. Start observability span with `agent_name` and `pipeline_step`.
   b. Resolve provider via Model Gateway (step from config, overlays from context).
   c. Check per-agent budget AND pipeline-wide budget (`PipelineBudget`). Either exhaustion triggers fallback. (Hermes analysis P4)
   d. Build system prompt from template + context. **Freeze it** — store as `self._frozen_prompt`. Multi-turn tool loops reuse the frozen prompt on every iteration, never reconstruct. Per-repo operational notes are included in the frozen snapshot. (Hermes analysis P1, P3)
   d-ii. **Scan inputs for injection.** Run `scan_agent_input()` on issue title, body, and rendered system prompt. Log any threat matches. If `block_on_threat` is enabled in config and threats are detected, skip LLM call and trigger fallback. Populate `AgentResult.threat_flags`. (Hermes analysis P2)
   e. Build user prompt from context (agent-specific logic via overridable method `build_user_prompt()`).
   f. Call Claude Agent SDK (or LLM completion API for non-tool agents).
   g. Record audit and spend. Update `PipelineBudget` with actual cost.
   h. Parse output against schema. Extract `operational_notes` if present. (Hermes analysis P3)
   i. Return `AgentResult`.
   j. On any LLM failure: if `fallback_fn` is configured, call it and set `used_fallback=True`.

6. **Two execution modes exist.** `AgentRunner` supports:
   - **Agentic mode** (tool loop): For agents that need tool access (Primary Agent). Uses `claude_agent_sdk.query()` with `allowed_tools`.
   - **Completion mode** (single LLM call): For agents that need reasoning but not tool access (most pipeline agents). Uses a simpler API call that returns structured text. Selection is automatic: if `tool_allowlist` is non-empty, uses agentic mode; otherwise, completion mode.

7. **Primary Agent is refactored to use `AgentRunner`.** `src/agent/primary_agent.py` is refactored so that `implement()` and `handle_loopback()` create an `AgentRunner` with `DeveloperAgentConfig` and call `runner.run()`. All existing tests pass. This proves the framework works before converting other agents.

8. **All existing tests pass.** The framework refactor does not break any existing test.

### Agent Conversion: Intake Agent

9. **`IntakeAgentConfig` exists.** `src/intake/intake_config.py` defines the agent config:
   - `pipeline_step = "intake"`
   - `model_class = "fast"` (per doc 26: "Intake and classification — fast model, strict token caps")
   - System prompt template instructs the LLM to: evaluate eligibility, select base role from issue content (not just labels), apply overlays from risk analysis, detect adversarial patterns, and return structured output.
   - `tool_allowlist = []` (completion mode — no tools needed)
   - `max_turns = 1`
   - `max_budget_usd = 0.10`
   - `output_schema = IntakeAgentOutput` (Pydantic model: accepted, rejection_reason, base_role, overlays, risk_flags, reasoning)
   - `fallback_fn = evaluate_eligibility` (existing rule-based function)

10. **LLM-powered intake can reason about issue content.** The intake agent reads issue title and body to infer work type when labels are ambiguous. For example, an issue titled "Refactor auth middleware" without a `type:refactor` label is still classified as Architect role. The rule-based fallback only triggers when the LLM is unavailable.

11. **Adversarial detection is enhanced.** The LLM-based intake can detect prompt injection patterns beyond the regex patterns in `detect_suspicious_patterns()`. The existing detector remains as a pre-filter (runs before LLM call); the LLM adds a second layer of reasoning.

12. **`intake_activity` calls the agent.** The Temporal activity creates an `AgentRunner` with `IntakeAgentConfig`, builds context from `IntakeInput`, and calls `runner.run()`. On LLM failure, falls back to `evaluate_eligibility()`.

### Agent Conversion: Context Manager Agent

13. **`ContextAgentConfig` exists.** `src/context/context_config.py` defines:
   - `pipeline_step = "context"`
   - `model_class = "fast"` (per doc 26: "fast or balanced for summarization; prefer deterministic tools")
   - System prompt template instructs the LLM to: analyze scope from issue content, identify impacted services, assess risk, compute complexity rationale, and identify open questions.
   - `max_turns = 1`
   - `max_budget_usd = 0.20`
   - `output_schema = ContextAgentOutput` (scope, risk_flags, complexity_rationale, open_questions, impacted_services)
   - `fallback_fn = enrich_taskpacket` (existing deterministic enrichment)

14. **LLM enrichment supplements deterministic analysis.** The deterministic functions (`analyze_scope()`, `flag_risks()`, `compute_complexity_index()`) run first. The LLM then reviews their output plus the raw issue content and can: add risk flags the regex missed, refine the complexity rationale, identify open questions for the Intent Builder, and flag missing service context packs.

15. **Context pack signals still emit.** The existing `ContextPackSignal` emission (pack_used, pack_missing) is preserved.

### Agent Conversion: Intent Builder Agent

16. **`IntentAgentConfig` exists.** `src/intent/intent_config.py` defines:
   - `pipeline_step = "intent"`
   - `model_class = "balanced"` (per doc 26: "balanced by default; strong when security/compliance/billing overlays")
   - System prompt template instructs the LLM to: extract the goal statement, derive constraints from risk flags and issue content, identify acceptance criteria (including implicit ones), extract non-goals, identify invariants (what must not change), and flag assumptions and open questions.
   - `max_turns = 1`
   - `max_budget_usd = 0.50`
   - `output_schema = IntentAgentOutput` (goal, constraints, invariants, acceptance_criteria, non_goals, assumptions, open_questions)
   - `fallback_fn = build_intent` (existing regex-based builder)

17. **LLM-based intent extraction captures invariants.** The architecture (doc 11) lists invariants as a first-class field. The LLM extracts "what must not change" from issue context — closing gap V7 from the architecture mapping.

18. **LLM-based intent extraction synthesizes implicit criteria.** When an issue says "add pagination to the user list endpoint," the LLM can infer implicit criteria like "existing filters still work," "page size has a reasonable default," and "total count is returned."

### Agent Conversion: Expert Router Agent

19. **`RouterAgentConfig` exists.** `src/routing/router_config.py` defines:
   - `pipeline_step = "routing"`
   - `model_class = "balanced"` (per doc 26: "balanced for synthesis")
   - System prompt template instructs the LLM to: review the required expert classes, available candidates, reputation data, and risk context, then decide: which experts to select, whether to use parallel or staged consultation, whether shadow experts should be included, and whether any selection warrants escalation.
   - `max_turns = 1`
   - `max_budget_usd = 0.30`
   - `output_schema = RouterAgentOutput` (selections with pattern, shadow_recommendations, staged_rationale, escalation_flags)
   - `fallback_fn = route` (existing algorithmic router)

20. **LLM router can select staged vs parallel consultation.** The LLM can reason about whether expert outputs have dependencies (e.g., security review should complete before partner API review) and recommend staged consultation — closing gap V9.

21. **LLM router can recommend shadow experts.** For new/probationary experts, the LLM can recommend running them in shadow mode alongside a trusted expert — closing gap V8.

22. **Algorithmic scoring remains the backbone.** The LLM reviews and optionally adjusts the algorithmic `route()` output. It does not replace the scoring formula — it augments it with judgment on patterns and escalation.

### Agent Conversion: Expert Recruiter Agent

23. **`RecruiterAgentConfig` exists.** `src/recruiting/recruiter_config.py` defines:
   - `pipeline_step = "routing"` (runs within Router's step)
   - `model_class = "balanced"`
   - System prompt template instructs the LLM to: analyze the capability gap, search for close-match experts, construct an expert pack definition with scope boundaries, operating procedure, expected outputs, edge cases, and tool policy.
   - `max_turns = 1`
   - `max_budget_usd = 0.30`
   - `output_schema = RecruiterAgentOutput` (expert_name, scope_description, definition, tool_policy, trust_tier_recommendation, creation_rationale)
   - `fallback_fn = recruit` (existing template-based recruiter)

24. **LLM-constructed expert packs are richer.** The LLM can produce more nuanced scope boundaries, operating procedures, and edge case documentation than the template skeleton alone. The qualification harness still validates the result.

### Agent Conversion: Assembler Agent

25. **`AssemblerAgentConfig` exists.** `src/assembler/assembler_config.py` defines:
   - `pipeline_step = "assembler"`
   - `model_class = "balanced"` (per doc 26: "balanced for conflict resolution; strong for multi-domain conflicts")
   - System prompt template instructs the LLM to: review all expert outputs, identify conflicts (semantic, not just keyword overlap), resolve conflicts using intent constraints, synthesize a coherent implementation plan with checkpoints, map acceptance criteria to validation steps, and produce provenance records.
   - `max_turns = 1`
   - `max_budget_usd = 0.50`
   - `output_schema = AssemblerAgentOutput` (plan_steps, conflicts with resolution, risks, qa_handoff, provenance_decisions)
   - `fallback_fn = assemble` (existing keyword-based assembler)

26. **LLM assembler performs semantic conflict detection.** Instead of checking assumption string overlap, the LLM can identify when two experts recommend contradictory approaches (e.g., one recommends in-memory caching while another recommends database-backed state) even when they use different terminology.

27. **Provenance is richer.** The LLM provides decision rationale (why expert A's recommendation was preferred over expert B's) beyond "Expert recommendation."

### Agent Conversion: QA Agent

28. **`QAAgentConfig` exists.** `src/qa/qa_config.py` defines:
   - `pipeline_step = "qa_eval"`
   - `model_class = "balanced"` (per doc 26: "balanced by default; strong for high-risk or repeated loops")
   - System prompt template instructs the LLM to: review each acceptance criterion against the evidence bundle, determine if implementation satisfies intent (not just keyword match), classify any defects by the 8-category taxonomy and S0-S3 severity, identify edge cases not covered by explicit criteria, and flag intent gaps.
   - `max_turns = 1`
   - `max_budget_usd = 0.50`
   - `output_schema = QAAgentOutput` (criteria_results with pass/fail and reasoning, defects with category/severity/description, intent_gaps, edge_case_concerns)
   - `fallback_fn = validate` (existing keyword-based QA)

29. **LLM QA agent reasons about intent satisfaction.** Instead of keyword-matching evidence keys, the LLM reads the agent summary, file changes, test results, and lint results, then determines if the acceptance criteria are actually met. A criterion like "pagination works correctly" requires more than finding the word "pagination" in evidence.

30. **LLM QA agent identifies uncovered edge cases.** The LLM can flag scenarios like "what happens with empty result sets?" or "is there a max page size?" that aren't in the explicit acceptance criteria but are implied by the intent.

### Cross-Cutting

31. **All 8 agents use the same `AgentRunner`.** No agent has bespoke LLM call infrastructure. Every agent's LLM interaction flows through `AgentRunner.run()`.

32. **All 8 agents route through Model Gateway.** Every agent's `pipeline_step` maps to a routing rule in the Model Gateway. Each uses the model class specified in doc 26.

33. **All 8 agents have audit records.** Every LLM call produces a `ModelCallAudit` record with correlation_id, task_id, step, provider, model, tokens, and cost.

34. **All 8 agents have observability spans.** Every agent call produces an OpenTelemetry span with agent_name, pipeline_step, model_used, duration_ms, and used_fallback.

35. **All 8 agents have rule-based fallback.** When the LLM is unavailable, budget is exhausted, or the output cannot be parsed, every agent falls back to its existing rule-based function. The fallback is logged and the `AgentResult.used_fallback` flag is set.

36. **All Temporal activities are updated.** Each `*_activity` function in `src/workflow/activities.py` creates an `AgentRunner` with the appropriate config and calls `runner.run()`. Activity timeouts are unchanged.

37. **Feature flag controls LLM enablement per agent.** A configuration dict in `src/settings.py` (e.g., `AGENT_LLM_ENABLED: dict[str, bool]`) allows enabling/disabling LLM mode per agent. Default: all enabled. When disabled for an agent, `AgentRunner.run()` immediately calls the fallback function.

38. **Structured output validation.** When `output_schema` is configured, `AgentRunner._parse_output()` attempts to parse the LLM response as JSON matching the Pydantic model. If parsing fails (malformed output), the fallback function is called and `used_fallback=True`.

### 4b. Top Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| LLM output is inconsistent across runs — pipeline becomes non-deterministic | High | High — affects reproducibility and debugging | Rule-based fallback always available; structured output schemas constrain LLM freedom; log both LLM and fallback paths for comparison |
| LLM costs blow up with 8 agents per task instead of 1 | High | Medium — budget controls exist but defaults may be wrong | Conservative budget defaults (most agents < $0.50); fast model class for Intake and Context; feature flag to disable per-agent |
| Completion mode (single LLM call, no tools) may not be expressive enough for some agents | Medium | Medium — agent quality is limited | Start with completion mode; promote to agentic mode (tool loop) for specific agents if quality is insufficient. Intent Builder and QA are most likely candidates |
| Claude Agent SDK may not support completion-only mode cleanly | Medium | Medium — need alternative API path | Abstract the LLM call behind `AgentRunner._call_llm()` so SDK and direct API calls are interchangeable |
| Structured output parsing fails frequently | Medium | Medium — frequent fallbacks degrade quality | Use Pydantic with `model_validate_json()`; include explicit JSON format instructions in system prompts; log parse failures for prompt tuning |
| Refactoring Primary Agent to use framework breaks existing behavior | Medium | High — only working agent breaks | Primary Agent conversion is Story 1 (highest risk first); comprehensive test coverage before and after; feature flag allows instant rollback |
| LLM-augmented Intake rejects valid issues or accepts invalid ones | Medium | Medium — false positives/negatives | Run LLM and rule-based in parallel during rollout (shadow mode); compare results before switching |

## 4c. Findings from Hermes Agent Analysis (NousResearch/hermes-agent)

A comparative analysis of NousResearch's Hermes Agent (v0.2.0, ~8k stars, MIT license) was conducted to evaluate whether its agent runtime, memory system, or self-improvement features should be adopted or adapted for TheStudio's `AgentRunner`. Hermes is a single-agent personal assistant with a tool-calling loop, memory, skills, and multi-platform messaging. The full analysis is documented below; only patterns with clear applicability to TheStudio's pipeline architecture are proposed for adoption.

### Patterns to Adopt

#### P1. Frozen System Prompt Snapshot (Critical — Sprint 1)

**What Hermes does:** Memory content is loaded at session start and frozen into the system prompt. Mid-session writes update disk but never mutate the system prompt. This preserves Anthropic's prefix cache for the entire session.

**Why it matters for TheStudio:** Each `AgentRunner.run()` call builds a system prompt from the template + context. For multi-turn agents (Primary Agent), the system prompt should be frozen at the start of the run and never reconstructed between turns. This preserves prefix caching and reduces token waste. For single-turn completion agents, this is already the natural behavior.

**Implementation:** Add to `AgentRunner.run()`: build the system prompt once at step (d) in the lifecycle, store it as `self._frozen_prompt`, and pass it to all subsequent LLM calls within the same run. The `build_system_prompt()` method is called exactly once per `run()` invocation.

**Acceptance criteria addition:** AC 5d (revised): "System prompt is built once per `run()` invocation and frozen. Multi-turn tool loops reuse the frozen prompt on every iteration. No mid-run prompt reconstruction."

#### P2. Prompt Injection Scanning for Agent Inputs (Critical — Sprint 1)

**What Hermes does:** `_scan_memory_content()` runs regex patterns against any content destined for the system prompt, blocking prompt injection payloads (`ignore previous instructions`, `you are now`, `disregard your rules`), exfiltration attempts (`curl` with secrets, reading credential files), and invisible unicode characters used for injection.

**Why it matters for TheStudio:** Issue titles and bodies from GitHub are untrusted external input. They flow into agent system prompts and user prompts via `AgentContext.issue_title` and `AgentContext.issue_body`. Expert system prompt templates from `EXPERT.md` files (Epic 26) are version-controlled but could be contributed by external parties. Without scanning, a crafted GitHub issue could inject instructions into any pipeline agent.

**Implementation:** Add `src/agent/prompt_guard.py` with:
- `scan_agent_input(text: str) -> list[ThreatMatch]` — scans text for injection/exfiltration patterns
- `scan_system_prompt(template: str, rendered: str) -> list[ThreatMatch]` — scans the final rendered prompt
- Integrated into `AgentRunner.run()` before the LLM call. Threats are logged, flagged in the `AgentResult`, and optionally block the LLM call (configurable: `block_on_threat` in `AgentConfig`, default `True` for intake, `False` for others — intake is the most exposed).
- Pattern set: prompt injection, role hijacking, instruction override, credential exfiltration, invisible unicode. Extensible via config.

**Acceptance criteria addition:** AC 5d-ii: "All agent inputs (issue title, body, expert prompts) are scanned for injection patterns before LLM call. Detected threats are logged with threat type and blocked when `block_on_threat` is enabled."

#### P3. Bounded Agent Operational Memory (High Value — Sprint 1)

**What Hermes does:** Two character-limited flat files (2,200 chars for agent notes, 1,375 chars for user profile). Hard cap forces curation — you must `replace` or `remove` before you can `add` when full. Entries are `§`-delimited, deduplicated on load, and atomically written.

**Why it matters for TheStudio:** Pipeline agents currently have no per-repo operational knowledge. The Reputation Engine tracks expert performance (structured, quantitative), but there's no place for unstructured operational notes like "this repo's CI takes 4 minutes," "tests are flaky on the auth module — retry once," or "maintainer prefers small PRs under 200 lines." These notes could improve agent decisions across tasks for the same repo.

**Implementation:** Add `per_repo_notes` field to `AgentContext` (loaded from a bounded store keyed by repo). Agents can emit notes in their `AgentResult.operational_notes` (optional list[str]). Notes are persisted to the repo profile, capped at 2,000 chars, oldest-first eviction. Injected into the system prompt as a frozen snapshot (pattern P1). No mid-run mutation.

**Not a tool call** — unlike Hermes, TheStudio agents don't manage memory interactively. Notes are a structured output field that the pipeline persists. The bounded cap prevents bloat.

**Acceptance criteria addition:** AC 4 (revised `AgentContext`): Add `per_repo_notes: list[str]` field. AC 4 (revised `AgentResult`): Add `operational_notes: list[str]` field (optional, default empty).

#### P4. Iteration Budget with Shared Counter (High Value — Sprint 1)

**What Hermes does:** `IterationBudget` is a thread-safe counter shared between a parent agent and all its subagents. `consume()` returns False when the budget is exhausted. `refund()` gives back iterations for programmatic (non-LLM) tool calls. The budget resets per user turn.

**Why it matters for TheStudio:** The Primary Agent uses `max_turns` from `DeveloperRoleConfig`, but there's no shared budget across the pipeline. If the Intent Builder, Router, and Assembler each spend their max budget, the Primary Agent may have nothing left. A pipeline-wide iteration/cost budget prevents runaway spend across all 8 agents for a single task.

**Implementation:** Add `PipelineBudget` to `src/agent/framework.py`:
- Created once per TaskPacket workflow execution
- Passed through `AgentContext.pipeline_budget`
- Each `AgentRunner.run()` calls `pipeline_budget.consume(estimated_cost)` before the LLM call
- If exhausted, the agent falls back to rule-based (same as `BudgetExceededError` path)
- Thread-safe (Temporal activities may run concurrently for Router fan-out)

**Acceptance criteria addition:** AC 5b (revised): "Budget check includes both per-agent budget (`AgentConfig.max_budget_usd`) and pipeline-wide budget (`PipelineBudget`). Pipeline budget exhaustion triggers fallback, not error."

### Patterns to Adapt (Lower Priority — Post-Sprint 1)

#### P5. Post-Task Refinement Nudge (Medium Value — Sprint 3+)

**What Hermes does:** After N tool calls without a skill update, injects a system nudge: "Save the approach as a skill if it's reusable, or update any existing skill you used if it was wrong or incomplete."

**TheStudio adaptation:** After a QA failure or verification loopback, the QA Agent or Verification Gate could emit a structured `refinement_signal` identifying which expert's prompt or which pipeline stage contributed to the failure. This feeds into the Reputation Engine (already exists) but also flags the expert's `EXPERT.md` system prompt for human review.

This is not an agent self-modifying its own prompts (too risky for a pipeline). It's a signal that says "this expert's guidance led to a QA failure for this pattern — consider updating the expert prompt." The signal is visible in Admin UI.

**Not included in Sprint 1-3 scope.** Documented here as a future enhancement that connects Epic 23 (agent framework) with Epic 26 (file-based experts) and the Reputation Engine.

#### P6. Session Search for Past Task Recall (Medium Value — Future Epic)

**What Hermes does:** SQLite FTS5 full-text search over past conversations, with LLM-powered summarization of matching sessions. Enables "how did I handle this last time?" recall.

**TheStudio adaptation:** Agents could query past TaskPackets for the same repo with similar risk flags or complexity. The Outcome Ingestor already stores structured outcomes. Adding FTS over `agent_summary` fields from `EvidenceBundle` would enable: "Last time this repo had a security-flagged issue, the Primary Agent needed 2 loopbacks because the test suite configuration was non-standard." This context could be injected into agent system prompts (pattern P1, frozen snapshot).

**Not included in Sprint 1-3 scope.** Requires schema addition to outcome storage. Documented for future epic scoping.

#### P7. Context Compression for Multi-Turn Agents (Medium Value — Sprint 1)

**What Hermes does:** `ContextCompressor` monitors token usage. When conversation exceeds 50% of the context window, it preserves the first 3 + last 4 turns, LLM-summarizes everything in between into ~2,500 tokens using a cheap model, and cleans up orphan tool-call references.

**Independently confirmed by:** HomeIQ's Hermes analysis (Feature #4) — they correctly identified that crude truncation is inferior to intelligent compression for multi-turn agents.

**Why it matters for TheStudio:** Only the Primary Agent runs multi-turn tool loops (20+ iterations for complex tasks). The Claude Agent SDK manages its own context, but when the agent hits the context limit, behavior degrades silently. A compression step between tool loop iterations would preserve early context (the intent, constraints, acceptance criteria) that gets pushed out by accumulated tool outputs.

**Implementation:** Add `compress_threshold` (float, 0.0-1.0, default 0.5) and `compress_model_class` (str, default "fast") to `AgentConfig`. In `_call_llm_agentic()`, after each tool loop iteration, check token estimate against threshold. If exceeded, summarize middle turns using the fast model, preserving first N (system prompt + initial user prompt + first assistant response) and last M (recent tool outputs and assistant responses). Only applies to agentic mode; completion mode is single-turn and never needs compression.

**Acceptance criteria addition:** AC 6 (revised): "Agentic mode includes context compression. When estimated tokens exceed `compress_threshold * context_window`, middle turns are summarized via fast model before the next iteration. First 3 and last 4 turns are preserved verbatim."

### Patterns Evaluated and Rejected

| Pattern | Hermes Implementation | Why Not for TheStudio |
|---------|----------------------|----------------------|
| **Interactive memory management** | Agent calls `memory(action="add")` tool mid-conversation | TheStudio agents communicate via artifacts and signals (SOUL.md). No mid-pipeline interactive memory. Operational notes (P3) are a structured output field, not a tool call. |
| **Memory nudge injection** | System appends "[System: Consider saving...]" to user messages | Pollutes structured prompts. TheStudio uses post-task hooks in Temporal workflow, not prompt injection. |
| **Skill auto-creation** | Agent creates `SKILL.md` files after complex tasks | Expert system prompts (`EXPERT.md`, Epic 26) serve this role. Self-modifying prompts in an automated pipeline are a safety risk. Refinement signals (P5) are the safer alternative. |
| **Honcho dialectic user modeling** | External service builds user model through conversation analysis | TheStudio's "users" are GitHub issues, not humans. Repo profiling already exists. |
| **Session DB with FTS5** | SQLite for conversation persistence and search | TheStudio uses PostgreSQL + SQLAlchemy (async). Past task recall (P6) should use the existing DB, not a parallel SQLite store. |
| **Hermes `AIAgent` as runtime** | Replace `claude_agent_sdk.query()` with `AIAgent.run_conversation()` | Wrong abstraction: 6,265-line sync-first monolith using OpenAI API. Loses Claude-native features (extended thinking, permission modes). Massive surface area of unused features (TUI, messaging gateway, Honcho, 40+ tools). |
| **Subagent delegation** (HomeIQ #2) | Hermes spawns child `AIAgent` instances for parallel subtasks | TheStudio's Temporal pipeline IS delegation — 9 specialized stages with scoped context and structured handoffs. Adding ad-hoc subagent spawning would create a second orchestration layer competing with Temporal. |
| **Mixture of Agents / multi-model consensus** (HomeIQ #6) | Query 3-4 models in parallel, synthesize best answer | TheStudio already has two independent validation stages (Verification Gate + QA Agent). Multi-model consensus adds latency and cost to a 9-stage pipeline. Hallucination risk is better addressed by structured output schemas + Pydantic validation (AC 38). |
| **Trajectory recording** (HomeIQ #8) | Full conversation capture in ShareGPT format for fine-tuning | TheStudio has `ModelCallAudit`, OpenTelemetry traces, and Evidence Bundles. Structured pipeline data is more useful than raw conversation logs. Fine-tuning is Phase 4+ at earliest. Future story for Primary Agent only if needed. |

### Impact on Story Map

Patterns P1-P4 add scope to Sprint 1 (framework foundation). Estimated additions:

| Story | Addition | Size Impact |
|-------|----------|-------------|
| 1.1 (`AgentConfig` / `AgentContext` / `AgentResult`) | Add `per_repo_notes` to context, `operational_notes` to result, `block_on_threat` to config | S → S (field additions) |
| 1.2 (`AgentRunner` core) | Add `PipelineBudget` integration alongside per-agent budget | M → M (budget is already the pattern) |
| 1.6 (`AgentRunner` observability/fallback) | Add frozen prompt snapshot logic, injection scanning call | M → L (two new behaviors in lifecycle) |
| **New: 1.11** | **`prompt_guard.py` — injection scanning module** | **M** (new file, ~100 lines + tests) |
| **New: 1.12** | **`PipelineBudget` — shared pipeline-wide cost counter** | **S** (new class, ~60 lines + tests) |
| **New: 1.13** | **Context compression for agentic mode** — mid-loop summarization via fast model (confirmed by HomeIQ analysis) | **M** (new method + tests, ~200 lines) |

Net Sprint 1 impact: +3 stories (2 M, 1 S). Total Sprint 1 goes from 10 stories to 13.

## 5. Constraints & Non-Goals

### Constraints

- **No changes to domain models.** TaskPacket, IntentSpec, ExpertOutput, ConsultPlan, AssemblyPlan, QAResult, and all other domain models are unchanged. The framework adapts to existing models, not the reverse.
- **No changes to Temporal workflow structure.** Activities are still called in the same order with the same timeouts. Only the internal implementation of each activity changes.
- **No changes to pipeline contracts.** Gates still fail closed. Loopbacks still carry evidence. Signals still emit to JetStream. The pipeline's external behavior is unchanged.
- **Rule-based fallback is mandatory.** Every agent must work without the LLM. This is not optional — it's a safety net for budget exhaustion, provider outages, and parsing failures.
- **Feature flags per agent.** Each agent can be toggled between LLM and rule-based independently. This allows gradual rollout and instant rollback.
- **Model Gateway is the only path to LLMs.** No agent bypasses the gateway. No hardcoded model names outside of config defaults.
- **Python 3.12+, existing dependencies only.** No new dependencies except potentially `instructor` or equivalent for structured output. **Pre-sprint action:** Tech Lead must evaluate `instructor` vs native Pydantic `model_validate_json()` and decide before Sprint 1 planning. Story 1.5 implements the chosen approach.
- **Existing tests must not break.** All 1,685+ tests pass after each conversion.

### Non-Goals

- **Not building Architect or Planner roles.** This epic converts existing agents to use LLMs. Adding new base roles (D1, D2) is a separate epic.
- **Not adding tool access to non-Primary agents.** All converted agents use completion mode (single LLM call). Adding tools (e.g., letting Intent Builder read repo files) is future work per agent.
- **Not building agent-to-agent communication.** Agents communicate through artifacts (TaskPacket, IntentSpec, etc.) and signals, not conversations. This is by design (SOUL.md) and does not change.
- **Not implementing full Claude Agent SDK for all agents.** Most agents use completion mode. Only Primary Agent uses the full agentic loop with tool access. Promoting other agents to agentic mode is a future decision per agent.
- **Not optimizing prompts.** This epic builds the framework and writes initial prompts. Prompt optimization based on eval results is a separate, ongoing effort.
- **Not building an eval harness for agent quality.** `src/evals/` has existing eval infrastructure. Extending it for the 7 new LLM agents is a follow-up epic.
- **Not replacing the Verification Gate or Publisher.** These are platform services, not agents. They remain deterministic.

## 6. Stakeholders & Roles

| Role | Who | Responsibility |
|------|-----|----------------|
| Epic Owner | Platform Lead (TBD — assign before sprint start) | Accepts epic scope, reviews AC completion |
| Tech Lead | **Must be assigned before Sprint 1 planning.** Gates framework design decisions (completion mode, `instructor`, output parsing strategy). Cannot be deferred. | Owns framework design and all 7 agent conversions |
| QA | QA Engineer (TBD — assign before sprint start) | Validates AC, writes comparison tests (LLM vs rule-based) |
| Saga | Epic Creator | Authored this epic; available for scope clarification |
| Meridian | VP Success | Reviews this epic before commit; reviews sprint plans |

## 7. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Framework adoption | 8/8 agents use `AgentRunner` | Grep: zero direct `claude_agent_sdk.query()` calls outside `AgentRunner` |
| Model Gateway coverage | 100% of agent LLM calls route through gateway | `ModelCallAudit` records exist for every agent invocation |
| Fallback reliability | Fallback triggers correctly when LLM unavailable | Integration test: disable LLM, verify all agents produce valid output via fallback |
| Output parsing success rate | > 90% of LLM responses parse successfully | Log metric: `agent.parse_success / (agent.parse_success + agent.parse_failure)` per agent. Instrumented in Story 1.5. |
| Cost per task (mean) | < $3.00 mean across all tasks (current baseline: ~$0.80 — Primary Agent only, 7 stubs at $0.00). Worst case per Appendix C is $7.40 if all agents hit max budget. Suggest-tier pipeline budget ($7.50) caps this. Target assumes most agents use fast model and single-turn completion. | Audit log: sum of `cost_estimated` per task across all steps. Track P50/P90 in addition to mean. |
| Zero regression | All pre-existing tests pass | CI green on merge |
| Feature flag works | Each agent independently toggleable | Integration test: disable one agent's LLM, verify only that agent uses fallback |
| Observability | Every agent call has a span | Trace export: spans exist for all 8 agent names |

## 8. Context & Assumptions

### Systems Affected

| System | Impact |
|--------|--------|
| `src/agent/framework.py` | **New file** — `AgentConfig`, `AgentContext`, `AgentResult`, `AgentRunner` |
| `src/agent/primary_agent.py` | **Modified** — refactored to use `AgentRunner` |
| `src/agent/developer_role.py` | **Modified** — becomes `DeveloperAgentConfig` using `AgentConfig` |
| `src/intake/intake_agent.py` | **Modified** — LLM-powered with `evaluate_eligibility` as fallback |
| `src/intake/intake_config.py` | **New file** — `IntakeAgentConfig` and `IntakeAgentOutput` |
| `src/context/context_manager.py` | **Modified** — LLM supplements deterministic enrichment |
| `src/context/context_config.py` | **New file** — `ContextAgentConfig` and `ContextAgentOutput` |
| `src/intent/intent_builder.py` | **Modified** — LLM-powered with `build_intent` as fallback |
| `src/intent/intent_config.py` | **New file** — `IntentAgentConfig` and `IntentAgentOutput` |
| `src/routing/router.py` | **Modified** — LLM augments algorithmic routing |
| `src/routing/router_config.py` | **New file** — `RouterAgentConfig` and `RouterAgentOutput` |
| `src/recruiting/recruiter.py` | **Modified** — LLM-powered expert pack construction |
| `src/recruiting/recruiter_config.py` | **New file** — `RecruiterAgentConfig` and `RecruiterAgentOutput` |
| `src/assembler/assembler.py` | **Modified** — LLM-powered conflict resolution and plan synthesis |
| `src/assembler/assembler_config.py` | **New file** — `AssemblerAgentConfig` and `AssemblerAgentOutput` |
| `src/qa/qa_agent.py` | **Modified** — LLM-powered intent validation |
| `src/qa/qa_config.py` | **New file** — `QAAgentConfig` and `QAAgentOutput` |
| `src/workflow/activities.py` | **Modified** — all activities use `AgentRunner` |
| `src/settings.py` | **Modified** — add `AGENT_LLM_ENABLED` feature flag dict |
| `src/admin/model_gateway.py` | **Unchanged** — already supports step-based routing |

### Assumptions

1. **Claude Agent SDK supports a completion-only mode** (or we can use the Anthropic Messages API directly for non-tool agents). If the SDK requires tool definitions, we abstract the LLM call behind `AgentRunner._call_llm()` with two implementations. **Pre-sprint action:** Tech Lead must investigate SDK completion-mode support and decide SDK vs direct Messages API before Sprint 1 planning. Story 1.4 implements whichever path is chosen — it must not also be the investigation.
2. **Structured JSON output is reliable with Claude.** System prompts can instruct Claude to return JSON matching a Pydantic schema. Parse failures trigger fallback, not crashes.
3. **Fast model class is sufficient for Intake and Context.** These agents need classification and extraction, not complex reasoning. If quality is insufficient, the model class can be upgraded to balanced via config change.
4. **Budget defaults are conservative.** Most agents are single-turn completion calls. $0.10-$0.50 per agent per task. Total pipeline cost stays under $3.00 for typical tasks.
5. **Rule-based functions remain the source of truth for the pipeline contract.** LLM agents augment quality but the pipeline works correctly with fallback-only mode. This is the safety net for production.
6. **The 7 non-Primary agents do not need tool access in Phase 1.** They receive all necessary context as input parameters. Tool access (e.g., letting Intent Builder read repo files) is a future enhancement per agent.

### Dependencies

- **Upstream:** Epic 19 (Gateway Wiring) must be complete — `AgentRunner` depends on Model Gateway integration patterns established there.
- **Recommended:** Epic 22 (Execute Tier) — the framework supports tier-based model class escalation, which is more useful with all three tiers available.
- **Downstream unblocks:** D1 (Architect role), D2 (Planner role) — new roles become trivial to add with the framework. V7 (Invariant identification) — closed by Intent Builder conversion. V8 (Shadow consulting), V9 (Staged consults) — closed by Router conversion.

---

## Story Map

Stories are ordered by risk reduction (highest-risk first). Sprint 1 builds the framework and proves it with the Primary Agent. Sprints 2-3 convert the remaining agents in pipeline order.

### Sprint 1: Framework + Primary Agent Conversion

| # | Story | Size | Value | Files |
|---|-------|------|-------|-------|
| 1.1 | **`AgentConfig`, `AgentContext`, `AgentResult` dataclasses** — Define the shared data model for all agents. Frozen dataclasses with sensible defaults. | S | Foundation for all agents | `src/agent/framework.py` |
| 1.2 | **`AgentRunner` core — provider resolution, budget, audit** — Implement `_resolve_provider()`, `_check_budget()`, `_record_audit()` by extracting patterns from `primary_agent.py`. | M | Shared operational controls | `src/agent/framework.py` |
| 1.3 | **`AgentRunner` — agentic mode (tool loop)** — Implement `_call_llm_agentic()` that wraps `claude_agent_sdk.query()`. Extract from `primary_agent._run_agent()`. | M | Tool-using agents work | `src/agent/framework.py` |
| 1.4 | **`AgentRunner` — completion mode (single call)** — Implement `_call_llm_completion()` for non-tool agents. Uses Messages API or SDK without tools. Returns raw text. | M | Non-tool agents work | `src/agent/framework.py` |
| 1.5 | **`AgentRunner` — structured output parsing + instrumentation** — Implement `_parse_output()` with Pydantic `model_validate_json()`. Fallback on parse failure. Emit `agent.parse_success` and `agent.parse_failure` counters per agent name to support the "> 90% parsing success rate" metric (Section 7). | S | Reliable structured output; metric instrumentation | `src/agent/framework.py` |
| 1.6 | **`AgentRunner` — observability and fallback** — Implement span creation, fallback dispatch, feature flag check, `build_system_prompt()`, `build_user_prompt()`. | M | Complete lifecycle | `src/agent/framework.py` |
| 1.7 | **Feature flag infrastructure** — Add `AGENT_LLM_ENABLED` dict to settings. `AgentRunner.run()` checks flag before LLM call. | S | Per-agent toggle | `src/settings.py`, `src/agent/framework.py` |
| 1.8 | **Refactor Primary Agent to use `AgentRunner`** — Convert `implement()` and `handle_loopback()` to create `AgentRunner` with `DeveloperAgentConfig`. All existing agent tests must pass. | L | Framework proven with real agent | `src/agent/primary_agent.py`, `src/agent/developer_role.py` |
| 1.9 | **Framework unit tests** — Test `AgentRunner` lifecycle: provider resolution, budget check, audit recording, fallback dispatch, feature flag, structured output parsing, observability spans. | M | Confidence in framework | `tests/agent/test_framework.py` |
| 1.10 | **Integration test: Primary Agent through framework** — End-to-end test: `implement()` calls `AgentRunner`, gateway selects model, audit recorded, evidence bundle produced. | M | Prove no regression | `tests/agent/test_primary_agent_framework.py` |
| 1.11 | **Prompt injection guard** — `src/agent/prompt_guard.py` with `scan_agent_input()` and `scan_system_prompt()`. Regex pattern set for prompt injection, role hijacking, instruction override, credential exfiltration, invisible unicode. Integrated into `AgentRunner.run()` before LLM call. Configurable `block_on_threat` per agent. Adopted from Hermes Agent's `_scan_memory_content()` pattern (P2). | M | Defense against crafted GitHub issues | `src/agent/prompt_guard.py`, `tests/agent/test_prompt_guard.py` |
| 1.12 | **Pipeline budget** — `PipelineBudget` class in `src/agent/framework.py`. Thread-safe shared cost counter across all agents for a single TaskPacket. Created per workflow execution, passed via `AgentContext`. Exhaustion triggers fallback, not error. Adopted from Hermes Agent's `IterationBudget` pattern (P4). | S | Prevent runaway pipeline spend | `src/agent/framework.py`, `tests/agent/test_pipeline_budget.py` |
| 1.13 | **Context compression for agentic mode** — `_compress_context()` method in `AgentRunner`. When token estimate exceeds `compress_threshold * context_window` during tool loop, summarize middle turns via fast model, preserving first 3 + last 4 turns. Handles orphan tool-call cleanup. Only applies to agentic mode. Adopted from Hermes Agent's `ContextCompressor` pattern (P7), independently confirmed by HomeIQ analysis. | M | Prevent context overflow in long Primary Agent runs | `src/agent/framework.py`, `tests/agent/test_context_compression.py` |

### Sprint 2: Intake + Context + Intent + Router Conversions

**Sprint 2 Status:** Stories 2.1, 2.3, 2.4, 2.6 complete (2026-03-16). Stories 2.2, 2.5, 2.7-2.12 pending.

| # | Story | Size | Value | Files | Status |
|---|-------|------|-------|-------|--------|
| 2.1 | **Intake Agent config + output schema** — Define `IntakeAgentConfig`, `IntakeAgentOutput`, system prompt template. | S | Config ready | `src/intake/intake_config.py` | **Done** |
| 2.2 | **Intake Agent conversion** — Wire `AgentRunner` into `intake_activity`. LLM classifies from issue content; `evaluate_eligibility()` as fallback. | M | LLM-powered intake | `src/intake/intake_agent.py`, `src/workflow/activities.py` | Pending |
| 2.3 | **Intake Agent tests** — Test: LLM classification, fallback on failure, adversarial detection, structured output parsing. | M | Confidence | `tests/intake/test_intake_config.py` | **Done** (22 tests) |
| 2.4 | **Context Manager config + output schema** — Define `ContextAgentConfig`, `ContextAgentOutput`, system prompt template. | S | Config ready | `src/context/context_config.py` | **Done** |
| 2.5 | **Context Manager conversion** — Wire `AgentRunner` into `context_activity`. Deterministic functions run first, LLM reviews and augments. | M | LLM-enriched context | `src/context/context_manager.py`, `src/workflow/activities.py` | Pending |
| 2.6 | **Context Manager tests** — Test: LLM augmentation, fallback, signal emission preserved. | M | Confidence | `tests/context/test_context_config.py` | **Done** (20 tests) |
| 2.7 | **Intent Builder config + output schema** — Define `IntentAgentConfig`, `IntentAgentOutput` (includes invariants field — closes V7), system prompt template. | S | Config ready | `src/intent/intent_config.py` |
| 2.8 | **Intent Builder conversion** — Wire `AgentRunner` into `intent_activity`. LLM extracts semantic intent; `build_intent()` as fallback. | M | LLM-powered intent | `src/intent/intent_builder.py`, `src/workflow/activities.py` |
| 2.9 | **Intent Builder tests** — Test: semantic extraction, invariant identification, implicit criteria synthesis, fallback. | M | Confidence | `tests/intent/test_intent_llm.py` |
| 2.10 | **Router Agent config + output schema** — Define `RouterAgentConfig`, `RouterAgentOutput` (includes staged/shadow fields — closes V8, V9), system prompt template. | S | Config ready | `src/routing/router_config.py` |
| 2.11 | **Router Agent conversion** — Wire `AgentRunner` into `router_activity`. Algorithmic `route()` runs first, LLM reviews and adjusts patterns/escalations. | M | LLM-augmented routing | `src/routing/router.py`, `src/workflow/activities.py` |
| 2.12 | **Router Agent tests** — Test: staged consultation recommendation, shadow expert recommendation, escalation reasoning, fallback. | M | Confidence | `tests/routing/test_router_llm.py` |

### Sprint 3: Recruiter + Assembler + QA Conversions + Integration

| # | Story | Size | Value | Files |
|---|-------|------|-------|-------|
| 3.1 | **Recruiter Agent config + output schema** — Define `RecruiterAgentConfig`, `RecruiterAgentOutput`, system prompt template. | S | Config ready | `src/recruiting/recruiter_config.py` |
| 3.2 | **Recruiter Agent conversion** — Wire `AgentRunner` into recruitment flow. LLM constructs expert packs; template-based as fallback. | M | LLM-powered recruitment | `src/recruiting/recruiter.py` |
| 3.3 | **Recruiter Agent tests** — Test: LLM pack construction, qualification harness still validates, fallback. | M | Confidence | `tests/recruiting/test_recruiter_llm.py` |
| 3.4 | **Assembler Agent config + output schema** — Define `AssemblerAgentConfig`, `AssemblerAgentOutput`, system prompt template. | S | Config ready | `src/assembler/assembler_config.py` |
| 3.5 | **Assembler Agent conversion** — Wire `AgentRunner` into `assembler_activity`. LLM performs semantic conflict resolution and plan synthesis; keyword-based as fallback. | L | LLM-powered assembly | `src/assembler/assembler.py`, `src/workflow/activities.py` |
| 3.6 | **Assembler Agent tests** — Test: semantic conflict detection, intent-based resolution reasoning, provenance enrichment, fallback. | M | Confidence | `tests/assembler/test_assembler_llm.py` |
| 3.7 | **QA Agent config + output schema** — Define `QAAgentConfig`, `QAAgentOutput`, system prompt template. | S | Config ready | `src/qa/qa_config.py` |
| 3.8 | **QA Agent conversion** — Wire `AgentRunner` into `qa_activity`. LLM reasons about intent satisfaction; keyword-based as fallback. | L | LLM-powered QA | `src/qa/qa_agent.py`, `src/workflow/activities.py` |
| 3.9 | **QA Agent tests** — Test: intent satisfaction reasoning, edge case identification, defect classification, severity judgment, fallback. | M | Confidence | `tests/qa/test_qa_llm.py` |
| 3.10 | **Full pipeline integration test** — End-to-end test: all 8 agents use `AgentRunner`, all produce `ModelCallAudit` records, feature flags work, fallback works for each. | L | Complete validation | `tests/integration/test_full_pipeline_agents.py` |
| 3.11 | **Documentation update** — Update `docs/agent-catalog.md` to reflect LLM-powered status. Update `docs/architecture-vs-implementation-mapping.md` to close relevant gaps. | S | Docs match reality | `docs/agent-catalog.md`, `docs/architecture-vs-implementation-mapping.md` |

---

## Architecture Gaps Closed by This Epic

| Gap ID | Description | Closed by Story |
|--------|-------------|-----------------|
| V7 | Invariant identification in intent | 2.7, 2.8 |
| V8 | Shadow consulting in Router | 2.10, 2.11 |
| V9 | Parallel vs staged consult decisions | 2.10, 2.11 |
| D3 (partial) | LLM-based intent extraction | 2.7, 2.8 |
| Phase 0 stubs | 7 rule-based agents → LLM-powered | All conversion stories |

---

## Appendix A: `AgentRunner` Class Diagram

```
AgentConfig (frozen dataclass)
├── agent_name: str
├── pipeline_step: str
├── model_class: str
├── system_prompt_template: str
├── tool_allowlist: list[str]
├── max_turns: int
├── max_budget_usd: float
├── permission_mode: str
├── output_schema: type[BaseModel] | None
├── fallback_fn: Callable | None
├── block_on_threat: bool              [P2: injection guard]
├── compress_threshold: float          [P7: context compression trigger]
└── compress_model_class: str          [P7: model for compression]

AgentContext (dataclass)
├── taskpacket_id: UUID | None
├── correlation_id: UUID | None
├── repo: str
├── issue_title: str
├── issue_body: str
├── labels: list[str]
├── risk_flags: dict
├── complexity: str
├── overlays: list[str]
├── repo_tier: str
├── intent: IntentSpecRead | None
├── expert_outputs: list | None
├── evidence: dict | None
├── extra: dict
├── per_repo_notes: list[str]          [P3: bounded operational memory]
└── pipeline_budget: PipelineBudget | None  [P4: shared cost counter]

AgentResult (dataclass)
├── agent_name: str
├── raw_output: str
├── parsed_output: BaseModel | None
├── model_used: str
├── tokens_estimated: int
├── cost_estimated: float
├── duration_ms: int
├── used_fallback: bool
├── operational_notes: list[str]       [P3: repo-specific observations]
└── threat_flags: list[str]            [P2: detected injection patterns]

PipelineBudget                          [P4: from Hermes IterationBudget]
├── max_total_usd: float
├── consume(cost: float) -> bool       [thread-safe]
├── remaining: float                   [property]
└── used: float                        [property]

AgentRunner
├── __init__(config: AgentConfig)
├── async run(context: AgentContext) -> AgentResult
├── build_system_prompt(context: AgentContext) -> str
├── build_user_prompt(context: AgentContext) -> str   [overridable]
├── _resolve_provider(...) -> ProviderConfig
├── _check_budget(task_id) -> None     [checks both per-agent and pipeline budget]
├── _scan_inputs(...) -> list[str]     [P2: injection scanning]
├── _record_audit(...) -> None
├── _call_llm_agentic(...) -> str     [tool loop via SDK]
├── _call_llm_completion(...) -> str  [single call via API]
├── _compress_context(...) -> list    [P7: mid-loop context compression]
└── _parse_output(raw: str) -> BaseModel | str
```

## Appendix B: Model Class Assignments (from doc 26)

| Agent | Pipeline Step | Default Model Class | Escalation Trigger |
|-------|--------------|--------------------|--------------------|
| Intake | `intake` | fast | — |
| Context Manager | `context` | fast | — |
| Intent Builder | `intent` | balanced | Security/compliance/billing overlays → strong |
| Expert Router | `routing` | balanced | — |
| Expert Recruiter | `routing` | balanced | — |
| Assembler | `assembler` | balanced | Multi-domain conflicts → strong |
| Primary Agent | `primary_agent` | balanced | Complex refactors, migrations, high-risk → strong |
| QA Agent | `qa_eval` | balanced | High-risk overlays, repeated defect loops → strong |

## Appendix C: Budget Defaults

| Agent | Max Budget | Rationale |
|-------|-----------|-----------|
| Intake | $0.10 | Fast model, single classification call |
| Context Manager | $0.20 | Fast model, scope analysis |
| Intent Builder | $0.50 | Balanced model, semantic extraction |
| Expert Router | $0.30 | Balanced model, selection reasoning |
| Expert Recruiter | $0.30 | Balanced model, pack construction |
| Assembler | $0.50 | Balanced model, conflict resolution |
| Primary Agent | $5.00 | Balanced/strong model, multi-turn tool loop |
| QA Agent | $0.50 | Balanced model, intent validation |
| **Total per task** | **$7.40** | **Worst case, all agents use LLM** |

## Appendix D: Pipeline Budget Defaults (P4)

| Tier | Pipeline Budget | Rationale |
|------|----------------|-----------|
| Observe | $5.00 | Conservative — most agents should use fallback for low-trust repos |
| Suggest | $8.50 | Full pipeline, all agents LLM-enabled. Provides $1.10 margin above $7.40 worst case (previously $0.10). |
| Execute | $10.00 | Higher ceiling for auto-merge repos where quality matters most |

Pipeline budget is checked **in addition to** per-agent budgets. Either limit triggers fallback. The pipeline budget prevents the scenario where 8 agents each spend their max ($7.40 total) when the task only warranted a $2.00 pipeline.

## Appendix E: Prompt Injection Patterns (P2)

Initial pattern set for `prompt_guard.py`, derived from Hermes Agent's `_scan_memory_content()` and extended for TheStudio's threat model:

| Category | Example Pattern | Threat |
|----------|----------------|--------|
| Prompt injection | `ignore (previous\|all\|above) instructions` | Override agent system prompt |
| Role hijacking | `you are now` | Change agent identity/behavior |
| Instruction override | `system prompt override`, `disregard your rules` | Bypass pipeline constraints |
| Credential exfiltration | `curl.*\$(KEY\|TOKEN\|SECRET)` | Steal secrets via tool calls |
| Secret file access | `cat.*(\.env\|credentials\|\.pgpass)` | Read sensitive files |
| Invisible unicode | U+200B, U+200C, U+200D, U+2060, U+FEFF, U+202A-E | Hidden injection payloads |
| TheStudio-specific | `skip verification`, `bypass gate`, `auto-approve` | Circumvent pipeline gates |
