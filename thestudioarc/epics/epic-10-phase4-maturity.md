# Epic 10 — Phase 4 Maturity: Close the Gaps

> Saga — Epic Creator | Created: 2026-03-09

## Title

Complete Phase 4 platform maturity: quarantine UI, merge mode, model spend visibility, timing metrics, execution plane management, and compliance gate hardening.

## Narrative

Epics 7–9 delivered the major Phase 4 subsystems (Tool Hub, Model Gateway, Compliance Scorecard, Operational Targets, real adapters, integration tests). But Meridian's Phase 4 exit criteria require operational completeness — admins must be able to manage quarantined events, control merge behavior, see model spend, track lead/cycle time from real workflow events, manage execution planes, and rely on a hardened compliance gate. These are the last-mile features that turn a buildable platform into an operable one.

**Business value:** Without these, operators fly blind on quarantine backlogs, model costs, and merge safety. The platform can build software but can't be administered at scale.

## References

- Phase 4 exit criteria: `thestudioarc/MERIDIAN-ROADMAP-AGGRESSIVE.md` (Phase 4 section)
- Quarantine store: `src/outcome/quarantine.py`
- Dead-letter store: `src/outcome/dead_letter.py`
- Model gateway + audit: `src/admin/model_gateway.py`
- Operational targets: `src/admin/operational_targets.py`
- Compliance promotion: `src/compliance/promotion.py`
- Execution plane health: `src/compliance/execution_plane.py`
- UI router: `src/admin/ui_router.py`
- Templates: `src/admin/templates/`

## Acceptance Criteria

### AC1: Quarantine Operations UI
- Admin UI page at `/admin/ui/quarantine` listing quarantined events with reason, category, repo, and timestamp.
- Detail view showing payload, correction controls (mark corrected, replay, delete).
- Partial endpoint `GET /partials/quarantine` with filtering by reason and repo.
- Wired to existing `QuarantineStore`.

### AC2: Dead-Letter Operations UI
- Admin UI page at `/admin/ui/dead-letters` listing dead-letter events with failure reason, attempt count, and timestamp.
- Detail view with payload inspection and delete action.
- Partial endpoint `GET /partials/dead-letters`.
- Wired to existing `DeadLetterStore`.

### AC3: Merge Mode Controls
- `MergeMode` enum: `DRAFT_ONLY`, `REQUIRE_REVIEW`, `AUTO_MERGE`.
- Per-repo merge mode stored in repo profile.
- Admin UI controls on repo detail page to set merge mode.
- Publisher respects merge mode when creating PRs.

### AC4: Model Spend Dashboard
- Aggregation functions: spend by repo, by step, by provider, by time window.
- Admin UI partial `GET /partials/model-spend` showing spend breakdown tables.
- Integrated into the existing Models page or a new `/admin/ui/model-spend` page.

### AC5: Lead Time / Cycle Time Data Wiring
- `OperationalTargetsService` queries workflow events (TaskPacket timestamps) instead of injected empty lists.
- `intake_created_at` and `pr_opened_at` timestamps captured on TaskPacket or workflow output.
- Lead time = `pr_opened_at - intake_created_at`; cycle time = `merge_ready_at - pr_opened_at`.
- Targets page shows real data when available, "Insufficient Data" when not.

### AC6: Execution Plane Management
- `ExecutionPlane` dataclass: plane_id, name, region, status (active/paused/draining), repo_ids, created_at.
- `ExecutionPlaneRegistry`: register, list, assign repos, pause/resume, health summary.
- Admin UI section on dashboard or dedicated page showing planes, assigned repos, health.

### AC7: Compliance Gate Hardening
- Promotion audit trail persisted (not just in-memory list).
- Failed compliance checks produce structured remediation items.
- Admin UI shows promotion history with compliance scores on repo detail page.

## Constraints & Non-Goals

### Constraints
- All new UI follows existing HTMX + Tailwind + Jinja2 patterns.
- No new JS frameworks — keep HTMX-driven.
- In-memory stores acceptable (persistent DB is a future concern).
- No real external service calls — mock/stub backends.

### Non-Goals
- **Not** implementing real database persistence (in-memory is fine).
- **Not** building alerting/notification systems.
- **Not** implementing OpenClaw sidecar (remains optional/deferred).
- **Not** onboarding real repos — proving the admin surface works.

## Stakeholders & Roles

- **Owner:** Engineering (execution)
- **Reviewer:** Meridian (quality bar)

## Success Metrics

- All 7 ACs pass manual verification via admin UI navigation.
- All new endpoints return valid HTML partials with test data.
- All new Python files pass TAPPS quality gate (score ≥ 70, security ≥ 50).
- Existing tests continue to pass (zero regressions).

## Context & Assumptions

- Existing stores (QuarantineStore, DeadLetterStore, ModelAuditStore) are functional and tested.
- UI router pattern is well-established — new pages follow the same template.
- In-memory storage is acceptable for this epic; database persistence is a future concern.

---

## Meridian Review

**Reviewed: 2026-03-09 | Verdict: PASS**

All 7 checklist items satisfied: measurable ACs with file paths, risks identified (UI complexity, merge mode safety), non-goals explicit, no external dependencies, maps to Phase 4 exit criteria, testable, AI-ready.

---

## Sprint Plan (Helm)

**Sprint Goal:** All 7 acceptance criteria implemented and passing TAPPS quality gates.

**Order of work:**

### Sprint 1 (AC1, AC2, AC3): Quarantine UI + Dead-Letter UI + Merge Mode
- Highest operator visibility impact — admins can't manage failures without these.
- AC3 (merge mode) is small and self-contained.

### Sprint 2 (AC4, AC5): Model Spend Dashboard + Timing Metrics
- Depends on existing model audit store and operational targets service.
- AC5 wires real data into the targets service.

### Sprint 3 (AC6, AC7): Execution Plane Management + Compliance Hardening
- AC6 is new infrastructure; AC7 hardens existing promotion flow.
- Both are lower risk since underlying systems already work.
