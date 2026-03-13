# Epic 23 — Unified Agent Framework: Convert All Pipeline Nodes to LLM-Powered Agents

**Author:** Saga
**Date:** 2026-03-12
**Status:** Draft — Awaiting Meridian Review
**Target Sprint:** Multi-sprint (estimated 3-4 sprints after Epic 22 completes)
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

## 4. Acceptance Criteria

### Foundation: Unified Agent Framework

1. **`AgentConfig` dataclass exists.** `src/agent/framework.py` contains an `AgentConfig` frozen dataclass with fields: `agent_name` (str), `pipeline_step` (str), `model_class` (str — "fast", "balanced", "strong"), `system_prompt_template` (str), `tool_allowlist` (list[str] — empty for non-tool-using agents), `max_turns` (int), `max_budget_usd` (float), `permission_mode` (str), `output_schema` (type[BaseModel] | None — for structured output parsing), `fallback_fn` (Callable | None — rule-based fallback when LLM unavailable).

2. **`AgentRunner` class exists.** `src/agent/framework.py` contains an `AgentRunner` class with methods:
   - `__init__(self, config: AgentConfig)` — stores config, initializes tracer.
   - `async run(self, context: AgentContext) -> AgentResult` — the main execution method.
   - `build_system_prompt(self, context: AgentContext) -> str` — renders the system prompt template with context variables.
   - `_resolve_provider(self, overlays, repo_tier, complexity) -> ProviderConfig` — calls Model Gateway with step and model class from config.
   - `_check_budget(self, task_id: str) -> None` — calls `BudgetEnforcer.check_budget()`; raises `BudgetExceededError` if over limit.
   - `_record_audit(self, ...) -> None` — creates `ModelCallAudit` record.
   - `_parse_output(self, raw: str) -> BaseModel | str` — parses agent output against `output_schema` if configured; returns raw string if no schema.

3. **`AgentContext` dataclass exists.** Contains all inputs an agent might need: `taskpacket_id` (UUID | None), `correlation_id` (UUID | None), `repo` (str), `issue_title` (str), `issue_body` (str), `labels` (list[str]), `risk_flags` (dict), `complexity` (str), `overlays` (list[str]), `repo_tier` (str), `intent` (IntentSpecRead | None), `expert_outputs` (list | None), `evidence` (dict | None), `extra` (dict — agent-specific context).

4. **`AgentResult` dataclass exists.** Contains: `agent_name` (str), `raw_output` (str), `parsed_output` (BaseModel | None), `model_used` (str), `tokens_estimated` (int), `cost_estimated` (float), `duration_ms` (int), `used_fallback` (bool — True if rule-based fallback was used instead of LLM).

5. **`AgentRunner.run()` follows a standard lifecycle:**
   a. Start observability span with `agent_name` and `pipeline_step`.
   b. Resolve provider via Model Gateway (step from config, overlays from context).
   c. Check budget.
   d. Build system prompt from template + context.
   e. Build user prompt from context (agent-specific logic via overridable method `build_user_prompt()`).
   f. Call Claude Agent SDK (or LLM completion API for non-tool agents).
   g. Record audit and spend.
   h. Parse output against schema.
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

## 5. Constraints & Non-Goals

### Constraints

- **No changes to domain models.** TaskPacket, IntentSpec, ExpertOutput, ConsultPlan, AssemblyPlan, QAResult, and all other domain models are unchanged. The framework adapts to existing models, not the reverse.
- **No changes to Temporal workflow structure.** Activities are still called in the same order with the same timeouts. Only the internal implementation of each activity changes.
- **No changes to pipeline contracts.** Gates still fail closed. Loopbacks still carry evidence. Signals still emit to JetStream. The pipeline's external behavior is unchanged.
- **Rule-based fallback is mandatory.** Every agent must work without the LLM. This is not optional — it's a safety net for budget exhaustion, provider outages, and parsing failures.
- **Feature flags per agent.** Each agent can be toggled between LLM and rule-based independently. This allows gradual rollout and instant rollback.
- **Model Gateway is the only path to LLMs.** No agent bypasses the gateway. No hardcoded model names outside of config defaults.
- **Python 3.12+, existing dependencies only.** No new dependencies except potentially `instructor` or equivalent for structured output (evaluate before adding).
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
| Tech Lead | Backend Engineer (TBD — assign before sprint start) | Owns framework design and all 7 agent conversions |
| QA | QA Engineer (TBD — assign before sprint start) | Validates AC, writes comparison tests (LLM vs rule-based) |
| Saga | Epic Creator | Authored this epic; available for scope clarification |
| Meridian | VP Success | Reviews this epic before commit; reviews sprint plans |

## 7. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Framework adoption | 8/8 agents use `AgentRunner` | Grep: zero direct `claude_agent_sdk.query()` calls outside `AgentRunner` |
| Model Gateway coverage | 100% of agent LLM calls route through gateway | `ModelCallAudit` records exist for every agent invocation |
| Fallback reliability | Fallback triggers correctly when LLM unavailable | Integration test: disable LLM, verify all agents produce valid output via fallback |
| Output parsing success rate | > 90% of LLM responses parse successfully | Log metric: `parse_success / total_calls` per agent |
| Cost per task | < $3.00 average across all 8 agents combined | Audit log: sum of cost per task across all steps |
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

1. **Claude Agent SDK supports a completion-only mode** (or we can use the Anthropic Messages API directly for non-tool agents). If the SDK requires tool definitions, we abstract the LLM call behind `AgentRunner._call_llm()` with two implementations.
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
| 1.5 | **`AgentRunner` — structured output parsing** — Implement `_parse_output()` with Pydantic `model_validate_json()`. Fallback on parse failure. | S | Reliable structured output | `src/agent/framework.py` |
| 1.6 | **`AgentRunner` — observability and fallback** — Implement span creation, fallback dispatch, feature flag check, `build_system_prompt()`, `build_user_prompt()`. | M | Complete lifecycle | `src/agent/framework.py` |
| 1.7 | **Feature flag infrastructure** — Add `AGENT_LLM_ENABLED` dict to settings. `AgentRunner.run()` checks flag before LLM call. | S | Per-agent toggle | `src/settings.py`, `src/agent/framework.py` |
| 1.8 | **Refactor Primary Agent to use `AgentRunner`** — Convert `implement()` and `handle_loopback()` to create `AgentRunner` with `DeveloperAgentConfig`. All existing agent tests must pass. | L | Framework proven with real agent | `src/agent/primary_agent.py`, `src/agent/developer_role.py` |
| 1.9 | **Framework unit tests** — Test `AgentRunner` lifecycle: provider resolution, budget check, audit recording, fallback dispatch, feature flag, structured output parsing, observability spans. | M | Confidence in framework | `tests/agent/test_framework.py` |
| 1.10 | **Integration test: Primary Agent through framework** — End-to-end test: `implement()` calls `AgentRunner`, gateway selects model, audit recorded, evidence bundle produced. | M | Prove no regression | `tests/agent/test_primary_agent_framework.py` |

### Sprint 2: Intake + Context + Intent + Router Conversions

| # | Story | Size | Value | Files |
|---|-------|------|-------|-------|
| 2.1 | **Intake Agent config + output schema** — Define `IntakeAgentConfig`, `IntakeAgentOutput`, system prompt template. | S | Config ready | `src/intake/intake_config.py` |
| 2.2 | **Intake Agent conversion** — Wire `AgentRunner` into `intake_activity`. LLM classifies from issue content; `evaluate_eligibility()` as fallback. | M | LLM-powered intake | `src/intake/intake_agent.py`, `src/workflow/activities.py` |
| 2.3 | **Intake Agent tests** — Test: LLM classification, fallback on failure, adversarial detection, structured output parsing. | M | Confidence | `tests/intake/test_intake_llm.py` |
| 2.4 | **Context Manager config + output schema** — Define `ContextAgentConfig`, `ContextAgentOutput`, system prompt template. | S | Config ready | `src/context/context_config.py` |
| 2.5 | **Context Manager conversion** — Wire `AgentRunner` into `context_activity`. Deterministic functions run first, LLM reviews and augments. | M | LLM-enriched context | `src/context/context_manager.py`, `src/workflow/activities.py` |
| 2.6 | **Context Manager tests** — Test: LLM augmentation, fallback, signal emission preserved. | M | Confidence | `tests/context/test_context_llm.py` |
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
└── fallback_fn: Callable | None

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
└── extra: dict

AgentResult (dataclass)
├── agent_name: str
├── raw_output: str
├── parsed_output: BaseModel | None
├── model_used: str
├── tokens_estimated: int
├── cost_estimated: float
├── duration_ms: int
└── used_fallback: bool

AgentRunner
├── __init__(config: AgentConfig)
├── async run(context: AgentContext) -> AgentResult
├── build_system_prompt(context: AgentContext) -> str
├── build_user_prompt(context: AgentContext) -> str   [overridable]
├── _resolve_provider(...) -> ProviderConfig
├── _check_budget(task_id) -> None
├── _record_audit(...) -> None
├── _call_llm_agentic(...) -> str     [tool loop via SDK]
├── _call_llm_completion(...) -> str  [single call via API]
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
