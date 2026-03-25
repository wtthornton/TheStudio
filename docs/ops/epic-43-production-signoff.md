# Epic 43 — Production Sign-Off Checklist

> **Purpose:** Gate checklist before flipping `THESTUDIO_AGENT_MODE=ralph` in production.
> **Status:** APPROVED — ops sign-off granted 2026-03-25. Production flip authorized.
> **Date:** 2026-03-25
> **Sign-off by:** Primary Developer (solo operator)

---

## Pre-requisites (all met)

- [x] Epic 51 (Ralph vendored SDK parity) — COMPLETE
- [x] Epic 42 (Execute Tier Promotion) — COMPLETE
- [x] Epic 32 (Model Routing & Cost Optimization) — COMPLETE
- [x] All 15 stories (43.1–43.15) implemented and committed
- [x] 92 unit tests passing (bridge, primary_agent, cost, heartbeat, SDK features)
- [x] 10 integration tests passing (E2E implement + loopback, state backend)
- [x] Vendored SDK updated to v2.0.3 from upstream and reinstalled (2026-03-25)

## Staging Validation

- [ ] **Deploy to staging** with `THESTUDIO_AGENT_MODE=ralph`
- [ ] **Verify `/health/ralph`** returns `{"available": true, "version": "..."}`
  - Confirms Claude CLI binary is accessible in the runtime environment
- [ ] **Process 3+ real GitHub issues** through the Ralph path at Observe tier
  - Compare output quality (files_changed, agent_summary) vs legacy baseline
  - Confirm EvidenceBundle is well-formed with intent, acceptance criteria, verification
- [ ] **Check `ralph_agent_state` table** — verify session IDs are being persisted
  - `SELECT taskpacket_id, key_name, value_json FROM ralph_agent_state ORDER BY updated_at DESC LIMIT 10;`
- [ ] **Check `ModelCallAudit` records** — verify cost tracking for Ralph runs
  - `SELECT step, role, provider, cost_usd FROM model_call_audit WHERE step='primary_agent' ORDER BY created_at DESC LIMIT 10;`
- [ ] **Test a loopback scenario** — trigger a verification failure, confirm session continuity
  - The second implement call should load the session_id from the first call

## Success Metrics Validation

| Metric | Target | How to verify |
|--------|--------|---------------|
| Session ID reuse across loopbacks | >= 80% | Query `ralph_agent_state` WHERE key_name='session_id'; compare taskpacket_ids with loopback count > 0 |
| Zero spend when circuit breaker OPEN | $0.00 | Query `model_call_audit` WHERE circuit_breaker_state='OPEN'; sum(cost_usd) should be 0 |
| ModelCallAudit coverage | 100% | Count Ralph implement runs vs ModelCallAudit records with step='primary_agent' |
| files_changed non-empty | >= 95% | Count EvidenceBundles from Ralph runs where files_changed is non-empty |

## Production Flip

- [x] **Ops sign-off granted** (2026-03-25) — authorized to set `THESTUDIO_AGENT_MODE=ralph` in production
- [ ] Set `THESTUDIO_AGENT_MODE=ralph` in production environment
- [ ] Monitor first 10 production tasks — check OTel spans (`ralph.run`, `ralph.iteration`)
- [ ] Confirm Temporal heartbeats are visible in Temporal UI for Ralph activities
- [ ] Verify budget enforcement: `PipelineBudget` consumed correctly, no overspend

## Rollback Plan

If issues arise after production flip:
1. Set `THESTUDIO_AGENT_MODE=legacy` — immediate rollback, zero code changes
2. The `ralph_agent_state` table can remain — it is not read in legacy mode
3. Legacy path is fully preserved in `primary_agent.py` behind the feature flag

## Issue Found During Validation

The vendored SDK was upgraded from v2.0.2 to v2.0.3 (from upstream `ralph-claude-code/sdk`). Key API changes: `context_management` → `context`, `cost_tracking` → `cost`, `decomposition` moved into `agent`, `StallDetector` split into `FastTripDetector`/`DeferredTestDetector`/`ConsecutiveTimeoutDetector`, `tests_status` removed from `RalphStatus`. All 98 Ralph tests updated and passing. **Ensure deployment builds install from `vendor/ralph-sdk/`, not from a cached wheel.**
