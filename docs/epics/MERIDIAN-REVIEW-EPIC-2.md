# Meridian Review — Epic 2: Learning + Multi-Repo

**Reviewer:** Meridian (VP Success)
**Date:** 2026-03-06
**Epic:** `docs/epics/epic-2-learning-multi-repo.md`
**Checklist:** `thestudioarc/personas/meridian-review-checklist.md`

---

## Epic Review — 7 Questions

### 1. One measurable success metric — What is it, and how will we read it?

**Pass.**

Primary metric: **"Reputation weights update after task completion"** — 100% of completed tasks (V+QA outcomes) trigger reputation update.

How we read it: Query Reputation Engine for `weight_updated` signals linked to TaskPackets. This is measurable via signal stream audit and Reputation Engine logs.

Secondary metrics are also well-defined:
- Router uses reputation weights (100% of selections include weight/confidence in rationale)
- Single-pass success rate visible in Admin UI by repo
- Execute tier promotion with compliance checker passed

All metrics have clear measurement methods (query, dashboard, audit).

---

### 2. Top three risks — How are we mitigating each?

**Pass.**

Risks table in Section 8 identifies six risks. Top three by impact:

| Risk | Mitigation |
|------|------------|
| **Attribution wrong → reputation punishes wrong expert** (High) | Enforce provenance minimum record; intent_gap vs implementation_bug attribution rules in code. References `06-reputation-engine.md` attribution principles. |
| **Compliance Checker too loose → unsafe repos promoted** (High) | Checklist from `23-admin-control-ui.md`; manual review of first promotions. |
| **Admin UI scope creep → timebox blown** (High) | Core modules only (Fleet, Repo, Task Console, RBAC, Audit); Expert Performance Console full deferred to Phase 3. |

Each risk has a specific mitigation. The attribution risk mitigation references the architecture doc and ties to AC-3 (Reputation Engine attribution rules enforced).

---

### 3. Non-goals in writing — What are we explicitly not doing?

**Pass.**

Section 5 explicitly lists 9 non-goals:
- Model Gateway (Phase 4)
- Tool Hub/MCP (Phase 4)
- Expert Performance Console full (Phase 3)
- Evals suite (Phase 3)
- Single-pass 60% target (Phase 3)
- Service Context Packs production use (Phase 3)
- Auto-merge (human merge even in Execute)
- OpenClaw integration (Phase 4)
- Second execution plane (Phase 4)

These align with the roadmap phases and prevent scope creep.

---

### 4. External dependencies — Written or agreed commitment (owner, date)?

**Pass with note.**

Dependencies table in Section 8 shows all dependencies are complete from Epic 0/1:
- PostgreSQL, Temporal, NATS JetStream: Running
- Epic 1 codebase (355 tests): Complete
- thestudioarc/ docs: Published

**Note:** No external team or vendor dependencies. The 3+ repos for multi-repo are internal test repos. If production repos are expected, ownership/timeline must be clarified before Sprint 1 planning.

---

### 5. Link to goal/OKR — Why this epic now?

**Pass.**

Section 2 (Narrative) connects to strategy:
- "The aggressive roadmap demands visible metrics (single-pass success, loopback counts) by Phase 2 end."
- "Every sprint without the learning loop is a sprint of wasted outcome data."

References:
- `thestudioarc/MERIDIAN-ROADMAP-AGGRESSIVE.md` lines 108–135 (Phase 2 spec)
- Phase numbering and timebox align with roadmap

The "why now" is explicit: signals are flowing but dead-ending, and operations have no visibility.

---

### 6. Testable acceptance criteria — Verifiable by human or script?

**Pass.**

All 10 ACs have checkbox items that are verifiable:
- AC-1: "Complexity Index computed by Context Manager and stored on TaskPacket" — schema inspection + code test
- AC-2: "Quarantined signals have reason" — signal stream query
- AC-3: "Trust tier transitions shadow → probation → trusted" — state machine test
- AC-5: "Promotion blocked until all required checks pass" — integration test
- AC-7: "Audit log: All control actions logged" — log query
- AC-10: "All metrics use Complexity Index normalization where applicable" — code audit

No "user feels good" criteria. All items are deterministic and testable.

---

### 7. AI-ready — Can Cursor/Claude implement from this epic alone?

**Pass.**

The epic includes:
- Architecture doc references for every component (06, 12, 22, 23, 15)
- Explicit constraints and non-goals
- Story decomposition with dependencies
- Lessons learned references for process discipline
- Attribution rules (intent_gap vs implementation_bug) spelled out

An agent reading this epic + the referenced thestudioarc docs has enough context to:
1. Understand what "done" means for each AC
2. Know which components to build
3. Know what is out of scope
4. Know the process requirements (one commit per story, mypy in edit loop, integration tests for data layers)

---

## Red Flags Check

| Red Flag | Present? |
|----------|----------|
| Vague success | No — primary metric is explicit and measurable |
| No test for done | No — all ACs have testable criteria |
| No scope boundaries | No — non-goals section is explicit |
| Missing dependencies | No — all dependencies are complete |
| Unrealistic scope/time | **Watch** — 17 stories in 10–12 weeks is aggressive; Helm must sequence carefully |
| Disconnected from strategy | No — roadmap Phase 2 is explicitly referenced |
| "The AI will figure it out" | No — architecture docs are referenced for each component |

---

## Verdict

**PASS** — Epic 2 is approved for sprint planning.

**Watch item:** 17 stories in 10–12 weeks (aggressive). Helm should:
1. Front-load learning loop (Complexity Index → Outcome Ingestor → Reputation Engine → Router) before Admin UI
2. Consider Admin UI stories as a "core" batch that can be cut if timebox pressure requires scope reduction
3. Multi-repo (2.16, 2.17) depends on other repos being available; confirm repo availability before sprint commitment

**Handoff to Helm:** Define Sprint 1 plan with testable sprint goal. Recommended focus: learning loop (stories 2.1–2.7) before Admin UI.

---

*Meridian — VP Success. Bar passed. Watch the timebox.*
