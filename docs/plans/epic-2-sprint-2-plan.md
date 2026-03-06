# Sprint 2 Plan — Epic 2: Learning + Multi-Repo (Hardening + Trust Dynamics)

**Persona:** Helm (Planner & Dev Manager)
**Date:** 2026-03-06
**Epic:** `docs/epics/epic-2-learning-multi-repo.md`
**Sprint duration:** 2 weeks
**Team:** 1–2 developers
**Predecessor:** Epic 2 Sprint 1 complete (Stories 2.1, 2.2, 2.5, 2.7 delivered; learning loop closed; 100+ new tests)

---

## Sprint Goal

**Objective:** Outcome Ingestor handles malformed and uncorrelated signals via quarantine, dead-letter, and replay mechanisms; reopen events are captured and attributed; Reputation Engine persists trust tiers, applies time-based decay, and acts on drift — so that the learning loop is hardened against bad data and reputation stays fresh.

**Test:** The sprint goal is met when:
1. Outcome Ingestor quarantines signals that violate correlation rules (missing correlation_id, unknown TaskPacket, invalid category); quarantined events are queryable with failure reason — 8+ test cases
2. Dead-letter stream receives signals that fail parsing/validation after N attempts; raw payload and failure reason preserved — 4+ test cases
3. Quarantined events can be corrected and replayed; replay is deterministic (same input → same aggregates) — 5+ test cases
4. Reopen events (issue reopened, regression issue, rollback PR) are ingested, linked to original TaskPacket, and classified (intent_gap, implementation_bug, regression, governance_failure) — 6+ test cases
5. Reputation Engine persists trust tiers (shadow, probation, trusted) in database; tier transitions are computed on write, not read — 5+ test cases
6. Time-based decay reduces weights for stale experts (no recent outcomes); decay runs on configurable schedule — 4+ test cases
7. Drift detection triggers tier transitions: sustained decline → demotion, sustained improvement → promotion; transitions emit `trust_tier_changed` signal — 5+ test cases
8. All code passes `ruff` lint and `mypy` type check
9. Database migrations run cleanly on Sprint 1 schema

**Constraint:** No story is "done" unless its Definition of Done checklist is fully satisfied. One commit per story. Run `mypy` in the edit loop (not just at the end). Run `tapps_quick_check` after every file edit.

---

## Retro Actions from Sprint 1

| Action | How addressed in this sprint |
|--------|------------------------------|
| mypy errors caught late | mypy in the edit loop — every file edit, before commit |
| One commit per story | Enforced in constraint; each story is atomic |
| Sprint DoD is the bar | All 7 test criteria must pass; no partial credit |
| Estimate infra setup as real story | Story 2.3 includes dead-letter stream setup (JetStream consumer) as part of scope, not assumed |

---

## Capacity and Buffer

- **Commitment:** ~80% of sprint capacity (21 story points of 26 available per 2-week sprint)
- **Buffer:** ~20% for integration issues, Sprint 1 edge cases, and unknowns
- **Total planned:** 21 points across 3 stories

---

## Order of Work

### Phase A — Ingestor Hardening (week 1)

Story 2.3 hardens the Outcome Ingestor against bad data. It has no dependencies on other Sprint 2 stories. Story 2.4 (reopen events) can start in parallel once 2.3 quarantine patterns are established.

| Order | Story | Points | Size | Rationale |
|-------|-------|--------|------|-----------|
| 1 | **2.3 Quarantine + Dead-Letter + Replay** | 8 | L | Foundation for data integrity. No Sprint 2 dependencies. Unblocks safe operation in production. |
| 2 | **2.4 Reopen Event Handling** | 5 | M | High-signal quality feedback. Can start once 2.3 quarantine patterns exist. Parallel-safe with 2.3 tail. |

#### Story 2.3 — Quarantine + Dead-Letter + Replay

**Reference:** `thestudioarc/12-outcome-ingestor.md` lines 83–105

**Scope:** Implement quarantine rules, dead-letter stream, operator replay path. Signals that violate correlation or validation rules must not poison learning.

**Definition of Done:**
- [ ] `src/outcome/quarantine.py`: QuarantineStore class
  - `quarantine(event, reason: QuarantineReason) -> quarantine_id`
  - `list_quarantined(repo_id?, category?, limit, offset) -> list[QuarantinedEvent]`
  - `get_quarantined(quarantine_id) -> QuarantinedEvent` (includes raw payload, failure reason, timestamp)
  - `mark_corrected(quarantine_id, corrected_payload) -> None`
- [ ] `src/outcome/dead_letter.py`: DeadLetterStore class
  - Events that fail parsing/validation after `max_attempts` (default 3) are moved to dead-letter
  - Stores: raw payload, failure reason, attempt count, timestamp
  - `list_dead_letters(limit, offset) -> list[DeadLetterEvent]`
- [ ] Quarantine rules implemented in `src/outcome/ingestor.py`:
  - Missing `correlation_id` → quarantine (reason: `missing_correlation_id`)
  - Unknown `task_packet_id` → quarantine (reason: `unknown_task_packet`)
  - Unknown `repo_id` → quarantine (reason: `unknown_repo`)
  - Invalid `category` or `severity` values → quarantine (reason: `invalid_category`, `invalid_severity`)
  - Duplicate event with conflicting payload → quarantine (reason: `idempotency_conflict`)
- [ ] Dead-letter rules implemented:
  - Parse failure after N attempts → dead-letter
  - Validation failure after N attempts → dead-letter
- [ ] Replay mechanism in `src/outcome/replay.py`:
  - `replay_quarantined(quarantine_id) -> ReplayResult`
  - Replay is deterministic: same ordered events → same aggregates
  - Replayed events are marked as replayed with original quarantine_id link
- [ ] Migration creates `quarantined_events` table:
  - `quarantine_id` (uuid pk), `event_payload` (jsonb), `reason` (enum), `repo_id`, `category`, `created_at`, `corrected_at`, `replayed_at`
- [ ] Migration creates `dead_letter_events` table:
  - `id` (uuid pk), `raw_payload` (bytea), `failure_reason` (text), `attempt_count` (int), `created_at`
- [ ] JetStream dead-letter consumer configured (stream: `outcome-dead-letter`)
- [ ] Signals emitted: `event_quarantined`, `event_dead_lettered`, `event_replayed`
- [ ] 8+ unit tests: each quarantine reason, dead-letter after max attempts, replay determinism
- [ ] 4+ dead-letter tests: parse failure, validation failure, payload preservation
- [ ] 5+ replay tests: successful replay, replay of corrected event, deterministic aggregation
- [ ] `ruff` clean, `mypy` clean (run mypy after each file edit)
- [ ] Integration test: end-to-end quarantine → correct → replay flow with real JetStream + Postgres

**Unknowns / risks:**
- JetStream dead-letter consumer setup may require additional configuration. Mitigation: treat stream setup as explicit task in DoD; document in `docs/architecture/outcome-ingestor-hardening.md`.
- Replay determinism depends on ordered event processing. Mitigation: replay function takes ordered event list, not stream position.

---

#### Story 2.4 — Reopen Event Handling

**Reference:** `thestudioarc/12-outcome-ingestor.md` lines 110–127

**Scope:** Ingest reopen events (issue reopened, regression issue, rollback PR), link to original TaskPacket, classify, and update metrics.

**Definition of Done:**
- [ ] `src/outcome/reopen.py`: ReopenEventProcessor class
  - `process_reopen(event: ReopenEvent) -> ReopenOutcome`
  - Links reopen to original TaskPacket via issue/PR reference
  - Classifies reopen: `intent_gap`, `implementation_bug`, `regression`, `governance_failure`
- [ ] ReopenEvent sources handled:
  - GitHub webhook: issue reopened after merge (issue linked to merged PR)
  - GitHub webhook: new issue referencing PR with `regression` label
  - GitHub webhook: rollback PR merged (reverts commits from original PR)
- [ ] Classification logic:
  - Reopen within 7 days + same acceptance criteria failing → `intent_gap`
  - Reopen within 7 days + new failure mode → `implementation_bug`
  - Reopen after 7 days + related feature broken → `regression`
  - Reopen + compliance/review bypass detected → `governance_failure`
- [ ] Reopen metrics updated:
  - `reopen_rate` per repo (rolling 30-day window)
  - `reopen_rate` per role + overlays (EffectiveRolePolicy)
  - `reopen_rate` per expert set (experts consulted on original task)
- [ ] Attribution applied per `thestudioarc/12-outcome-ingestor.md` lines 124–127:
  - `intent_gap` reopen → impacts intent quality metrics (not expert weights)
  - `regression` reopen → impacts execution and expert guidance per provenance
- [ ] ReputationIndicator emitted for reopen events with `outcome_type: reopen` and classification
- [ ] Signals emitted: `reopen_event_processed`, `reopen_attributed`
- [ ] 6+ unit tests: each classification type, TaskPacket linking, metric updates, attribution routing
- [ ] `ruff` clean, `mypy` clean (run mypy after each file edit)
- [ ] Integration test: GitHub webhook → ReopenEvent → classification → indicator with real Postgres

**Unknowns / risks:**
- Linking reopen to original TaskPacket may fail if issue/PR references are ambiguous. Mitigation: require explicit reference or fall back to "unlinked reopen" with manual review flag.

---

### Phase B — Trust Dynamics (week 2)

Story 2.6 adds trust tier persistence, decay, and drift-driven transitions to the Reputation Engine. It depends on Sprint 1 Story 2.5 (Reputation Engine core).

| Order | Story | Points | Size | Rationale |
|-------|-------|--------|------|-----------|
| 3 | **2.6 Trust Tier Transitions + Decay + Drift** | 8 | L | Depends on 2.5 (Sprint 1). Prevents stale overconfidence. Closes trust dynamics loop. |

#### Story 2.6 — Trust Tier Transitions + Decay + Drift

**Reference:** `thestudioarc/06-reputation-engine.md` lines 26–43, 90–98

**Scope:** Persist trust tiers, apply time-based decay, trigger tier transitions based on drift.

**Definition of Done:**
- [ ] Migration adds columns to `expert_reputation` table:
  - `trust_tier` (enum: shadow, probation, trusted), default `shadow`
  - `tier_changed_at` (timestamp)
  - `last_outcome_at` (timestamp) — for decay calculation
  - `drift_direction` (enum: improving, stable, declining), default `stable`
  - `drift_score` (float) — rolling window trend
- [ ] Trust tier logic in `src/reputation/tiers.py`:
  - `TrustTier` enum: `shadow`, `probation`, `trusted`
  - `compute_tier(weight, confidence, sample_count, drift_direction) -> TrustTier`
  - Thresholds (configurable):
    - `shadow`: confidence < 0.3 OR sample_count < 5
    - `probation`: confidence >= 0.3 AND sample_count >= 5 AND (weight < 0.6 OR drift == declining)
    - `trusted`: confidence >= 0.5 AND sample_count >= 10 AND weight >= 0.6 AND drift != declining
- [ ] Tier transitions computed on indicator write (not on read):
  - After weight update, recompute tier
  - If tier changed, update `trust_tier` and `tier_changed_at`
  - Emit `trust_tier_changed` signal with old_tier, new_tier, reason
- [ ] Decay logic in `src/reputation/decay.py`:
  - `apply_decay(expert_reputation) -> DecayResult`
  - Decay rate: weight reduced by `decay_rate` (default 0.02) per `decay_period` (default 7 days) of inactivity
  - Decay floor: weight cannot drop below `decay_floor` (default 0.3) from decay alone
  - Decay triggers confidence reduction proportional to time since last outcome
- [ ] Decay scheduler:
  - Runs on configurable schedule (default: daily at 02:00 UTC)
  - Processes all experts with `last_outcome_at` older than `decay_period`
  - Emits `decay_applied` signal per expert affected
- [ ] Drift detection in `src/reputation/drift.py`:
  - `compute_drift(recent_outcomes: list[ReputationIndicator], window_size: int) -> DriftDirection`
  - Rolling window (default 10 outcomes)
  - `improving`: trend slope > +0.05
  - `stable`: trend slope between -0.05 and +0.05
  - `declining`: trend slope < -0.05
- [ ] Drift-triggered transitions:
  - Sustained `declining` (3+ consecutive drift computations) → demote tier (trusted → probation, probation → shadow)
  - Sustained `improving` (3+ consecutive drift computations) + thresholds met → promote tier
- [ ] Signals emitted: `trust_tier_changed`, `decay_applied`, `drift_detected`
- [ ] 5+ trust tier tests: tier computation, transition on write, threshold edge cases
- [ ] 4+ decay tests: decay application, decay floor, confidence reduction, inactive expert
- [ ] 5+ drift tests: drift computation, sustained decline demotion, sustained improvement promotion
- [ ] `ruff` clean, `mypy` clean (run mypy after each file edit)
- [ ] Integration test: indicator stream → weight updates → drift detection → tier transition with real Postgres

**Unknowns / risks:**
- Decay rate and thresholds may need tuning after observing real distributions. Mitigation: all thresholds configurable; document defaults in `docs/architecture/reputation-trust-dynamics.md`.
- Drift computation requires sufficient sample size. Mitigation: drift is `stable` when sample_count < window_size.

---

## What's Explicitly Out This Sprint

| Item | Why | When |
|------|-----|------|
| 2.8 Compliance Checker | Unrelated to hardening/trust dynamics | Sprint 3 |
| 2.9 Execute tier promotion | Depends on Compliance Checker | Sprint 3 |
| 2.10–2.15 Admin UI | Core learning loop must be hardened first | Sprint 3–4 |
| 2.16–2.17 Multi-repo | Admin UI + Compliance Checker needed | Sprint 4 |

---

## Dependencies

| Story | Depends on | Status |
|-------|-----------|--------|
| 2.3 Quarantine + DL + Replay | Sprint 1 Outcome Ingestor (2.2) | Complete |
| 2.4 Reopen Event Handling | Sprint 1 Outcome Ingestor (2.2), GitHub webhook infrastructure | 2.2 complete; webhook infra exists (Epic 1) |
| 2.6 Trust Tier Transitions | Sprint 1 Reputation Engine (2.5) | Complete |

**Cross-dependency risk:** All three stories depend on Sprint 1 deliverables (complete). Stories 2.3 and 2.4 are independent of 2.6. Mitigation: 2.3 and 2.4 can run in parallel; 2.6 can run in parallel with 2.3/2.4 tail work.

---

## Timeline

### 2 developers

| Week | Dev 1 | Dev 2 |
|------|-------|-------|
| 1 | 2.3 Quarantine + DL + Replay | 2.4 Reopen Event Handling |
| 2 | 2.6 Trust Tier Transitions | 2.6 Trust Tier Transitions (pair) or buffer |

### 1 developer

| Week | Work |
|------|------|
| 1 | 2.3 Quarantine + DL + Replay |
| 2 | 2.4 Reopen Event Handling + 2.6 Trust Tier Transitions |

---

## Sprint Definition of Done

The sprint is done when:
1. All 3 stories pass their Definition of Done checklists
2. All tests pass (unit + integration)
3. `ruff` and `mypy` clean across all new and modified files
4. Migrations run cleanly on Sprint 1 schema
5. `tapps_validate_changed` passes on all modified files
6. One commit per story, each with passing CI
7. Hardening verified: quarantine + dead-letter + replay path tested end-to-end; no silent signal drop
8. Trust dynamics verified: tier transitions persist; decay applies to inactive experts; drift triggers demotion/promotion

---

*Sprint 2 plan created by Helm. Awaiting Meridian review before execution.*
