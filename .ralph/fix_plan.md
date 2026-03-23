# Fix Plan — TheStudio

## Sprint 1 — Epic 43 Slice 1: Ralph SDK MVP (week of 2026-03-23)

> Order: 43.1 → 43.2 → 43.3 → 43.4 → 43.5
> Gate: `pytest tests/unit/test_ralph_bridge.py tests/unit/test_primary_agent_ralph.py -v` green
> TESTS_STATUS: DEFERRED until last task in this section

- [x] 43.1: Add `ralph-sdk` path dependency to `pyproject.toml` (`ralph-sdk @ file:///C:/cursor/ralph/ralph-claude-code/sdk`). Verify `from ralph_sdk import RalphAgent, NullStateBackend, TaskInput, TaskResult` succeeds.
- [x] 43.2: Create `src/agent/ralph_bridge.py` with 5 functions: (a) `check_ralph_cli_available() -> bool` — runs `claude --version` via subprocess, 5s timeout, returns False on failure. (b) `taskpacket_to_ralph_input(taskpacket, intent, loopback_context="") -> TaskPacketInput` — maps intent.goal→goal, constraints→list, risk_flags→RiskFlag, complexity→ComplexityBand (0-3=LOW, 4-6=MEDIUM, 7-10=HIGH), trust_tier→TrustTier. (c) `ralph_result_to_evidence(result, taskpacket_id, intent_version, loopback_attempt=0) -> EvidenceBundle` — calls SDK's `to_evidence_bundle()`, maps str→UUID/datetime. (d) `build_ralph_config(role_config, provider, complexity) -> RalphConfig` — sets model, allowed_tools, max_turns by complexity (low=20, med=30, high=50). (e) `build_verification_loopback_context(verification_result) -> str`.
- [x] 43.3: Add `agent_mode: str = "legacy"` to `src/settings.py` (env: `THESTUDIO_AGENT_MODE`). Values: `"legacy"`, `"ralph"`, `"container"`. `agent_mode` supersedes `agent_isolation` — if both set, `agent_mode` wins + deprecation warning. `_validate_execute_tier_isolation()` only applies to container mode.
- [x] 43.4: Refactor `src/agent/primary_agent.py` — add Ralph mode to `implement()` and `handle_loopback()`. When `agent_mode="ralph"`: resolve provider, build RalphConfig, construct `RalphAgent(config, state_backend=NullStateBackend(), correlation_id=...)`, convert TaskPacket→TaskInput via bridge, `await agent.run()`, convert result→EvidenceBundle. Legacy code stays, gated behind `"legacy"` mode. Do not delete existing code.
- [x] 43.5: Unit tests in `tests/unit/test_ralph_bridge.py` + `tests/unit/test_primary_agent_ralph.py`. Test all bridge functions, both dispatch modes, setting overlap (agent_mode vs agent_isolation), CLI check mock.

---

## Sprint 2 — Epic 43 Slices 2+3: State + Cost (week of 2026-03-30)

> Order: 43.6 → 43.7 → 43.8 → 43.9 → 43.10 → 43.11 → 43.12
> Gate: integration tests green, cost recording verified

- [x] 43.6: DB migration — `ralph_agent_state` table (id UUID PK, taskpacket_id UUID, key_name VARCHAR(64), value_json TEXT, updated_at TIMESTAMPTZ). Unique on (taskpacket_id, key_name).
- [x] 43.7: `src/agent/ralph_state.py` — `PostgresStateBackend` implementing all 12 `RalphStateBackend` protocol methods via upsert/select on ralph_agent_state table.
- [x] 43.8: Wire PostgresStateBackend into primary_agent.py. Setting `THESTUDIO_RALPH_STATE_BACKEND` (postgres/null). Session ID TTL: discard if >2h old.
- [x] 43.9: Integration tests `tests/integration/test_ralph_state.py` — round-trip, isolation, concurrent upsert, TTL.
- [ ] 43.10: Cost recording after Ralph run — `ModelCallAudit`, `BudgetEnforcer.record_spend()`, `PipelineBudget.consume()` check before launch.
- [ ] 43.11: `implement_activity` ralph mode with Temporal heartbeat every 30s. Timeout = `ralph_timeout_minutes + 5`. Cancel via `agent.cancel()`.
- [ ] 43.12: Unit tests for cost recording + activity heartbeat.

---

## Sprint 3 — Epic 43 Slice 4: Validation (future, ~8h)

- [ ] 43.13: `/health/ralph` endpoint + startup probe
- [ ] 43.14: Observability spans (SPAN_RALPH_RUN, SPAN_RALPH_ITERATION, etc.)
- [ ] 43.15: E2E integration test — implement + loopback via Ralph, full path

---

## Backlog — Needs Epic (Saga → Meridian → Helm)

**P2: Production Monitoring** — alerts for pipeline failures, cost anomalies, API rate limits, health dashboard
**P3: Intake Haiku Fix** — diagnose parsing failures, tune prompt or route to Sonnet
**P3: Agent Intelligence** — LLM issue scoring (E16), adversarial classification (E20), agentic non-Primary agents (E23)
**P3: Approval/Workflow** — GitHub `/approve` command parsing (E21), fleet-wide auto-merge policies (E22)
**P3: Security** — full SAST/DAST pipeline (E19), automated secret rotation (E11)
**P3: Testing** — a11y audits (E12), Playwright detail page tests (E12)

## Deferred — On Demand

**Epic 27: Multi-Source Webhooks** — 7 stories ready, trigger: non-GitHub source demand

## Completed

Epics 0-42 (270+ stories). Epic 27 deferred by design.
