# Fix Plan — TheStudio: Epic 36 — Phase 2: Planning Experience

> Epic: `docs/epics/epic-36-phase2-planning-experience.md`
> Sprint plan: `docs/epics/epic-36-sprint-plan.md`
> Sprint 4 stories: `docs/epics/epic-36-sprint4-story-decomposition.md`
> Slice 3 stories: `docs/epics/epic-36-slice3-story-decomposition.md`
> Status: Slices 1+2 backend COMPLETE, Slice 2 frontend IN PROGRESS (Sprint 4)

---

## Epic 36 — Phase 2: Planning Experience

### Slice 1: Triage Queue (COMPLETE)

#### Backend
- [x] 36.1: Add TRIAGE status to TaskPacket model — enum, transitions (TRIAGE->RECEIVED, TRIAGE->REJECTED, TRIAGE->FAILED), triage_enrichment JSON column, rejection_reason column, issue_title/issue_body columns, Alembic migration
- [x] 36.2: Conditional triage mode in webhook handler — `triage_mode_enabled` setting, webhook creates TRIAGE status when enabled, skips workflow start
- [x] 36.3: Triage action endpoints — POST accept (TRIAGE->RECEIVED + start workflow), POST reject (TRIAGE->REJECTED + reason), PATCH edit (title/description while in TRIAGE), all with 409 on wrong status
- [x] 36.4: Context pre-scan for triage enrichment — `prescan_issue()` in `src/context/prescan.py`, produces file_count_estimate/complexity_hint/cost_estimate_range, called from webhook handler in triage mode

#### Frontend
- [x] 36.5: Triage queue frontend — TriageQueue.tsx, TriageCard.tsx (with enrichment badges), EditPanel.tsx (slide-in editor), inline reject dropdown, triage-store.ts (Zustand)
- [x] 36.6: Triage SSE events — emit_triage_created/accepted/rejected via NATS, frontend subscribes via Phase 0 SSE bridge

### Slice 2: Intent Specification Review (Backend COMPLETE, Frontend Sprint 4)

#### Backend
- [x] 36.7: Add `source` column to IntentSpecRow — `source: str` with default "auto", updated Pydantic schemas, CRUD passes source through
- [x] 36.7a: Raise MAX_INTENT_VERSIONS cap — changed from 2 to 10, configurable via `settings.max_intent_versions`
- [x] 36.8: Temporal workflow wait point after Intent stage — `approve_intent`/`reject_intent` signal handlers, `workflow.wait_condition()`, 30-day safety timeout (escalates, does NOT auto-approve), feature-flagged via `intent_review_enabled`
- [x] 36.9: Intent review API endpoints — GET `/tasks/{id}/intent` (spec + version history), POST `.../approve` (Temporal signal), POST `.../reject` (Temporal signal + reason)
- [x] 36.10: Intent edit and refinement endpoints — PUT `/tasks/{id}/intent` (creates new version with source=developer), POST `.../refine` (constructs RefinementTrigger, creates version with source=refinement)

#### Frontend (Sprint 4 — Meridian PASS 2026-03-21)

- [x] 36.11a: Intent API types + functions — extend `TaskPacketRead` with `issue_title`, `issue_body`, `scope`, `risk_flags`, `complexity_index` (optional fields). Add `IntentSpecRead` interface (9 fields), `IntentResponse` interface, 5 API functions (fetchIntent, approveIntent, rejectIntent, editIntent, refineIntent). File: `frontend/src/lib/api.ts`. (S, 2h)

- [x] 36.11b: Intent Zustand store — `intent-store.ts` with state (taskId, current, versions, selectedVersion, loading, error, mode, refineModalOpen, saving) and actions (loadIntent, approve, reject, saveEdit, requestRefine, selectVersion, setMode, setRefineModalOpen, reset). Re-fetches after mutations. File: `frontend/src/stores/intent-store.ts`. Depends on 36.11a. (S, 2h)

- [x] 36.11c: SourceContext + IntentSpec display components — two pure display components. SourceContext: left panel showing issue title/body (plain `<pre>`), enrichment (complexity score bar, risk flags checklist, scope/files). IntentSpec: right panel showing goal, constraints (bullet list), acceptance criteria (numbered list), non-goals (strikethrough bullets), source badge (color-coded), version + timestamp. Files: `frontend/src/components/planning/SourceContext.tsx`, `IntentSpec.tsx`. Depends on 36.11a. (M, 4h)

- [x] 36.11d: IntentEditor container + routing + action buttons — container component with split-pane layout (`grid-cols-[2fr_3fr]`). Fetches own task via `fetchTaskDetail(taskId)`. Four action buttons (Approve/Edit/Refine/Reject). Reject inline confirmation with reason. VersionSelector dropdown. Loading/error states. Wired into App.tsx as third tab. Files: `frontend/src/components/planning/IntentEditor.tsx`, `VersionSelector.tsx`, modify `App.tsx`. Depends on 36.11a, 36.11b, 36.11c. (M, 4h)

- [x] 36.11e: Intent edit mode form — `IntentEditMode.tsx` replaces right panel when editing. Goal textarea, constraints/AC/non-goals as editable lists (add/remove items). `EditableList` sub-component. Save calls `store.saveEdit()`, Cancel returns to view mode. Empty strings filtered on save. Save disabled when unchanged. File: `frontend/src/components/planning/IntentEditMode.tsx`, modify IntentEditor.tsx. Depends on 36.11d. (M, 4h)

- [x] 36.11f: Refinement modal — `RefinementModal.tsx` with backdrop overlay, feedback textarea (10-char minimum), submit/cancel/escape. Submit calls `store.requestRefine()`. File: `frontend/src/components/planning/RefinementModal.tsx`, modify IntentEditor.tsx. Depends on 36.11d. (S, 3h)

- [x] 36.11g: Version diff + component tests — `VersionDiff.tsx` with field-level comparison (Set-based exact match: added=green, removed=red, unchanged=plain). "Compare Versions" toggle in IntentEditor. `IntentEditor.test.tsx` with 15 test cases covering loading, split-pane, sections, source badge, version selector, approve, reject, edit, refine, diff. Files: `frontend/src/components/planning/VersionDiff.tsx`, `__tests__/IntentEditor.test.tsx`, modify IntentEditor.tsx. Depends on 36.11e, 36.11f. (M, 3h)

### Slice 3: Complexity Dashboard + Expert Routing Preview (Meridian PASS 2026-03-21)

> Story decomposition: `docs/epics/epic-36-slice3-story-decomposition.md`
> Two parallel tracks: Track A (complexity, frontend-only) and Track B (routing, backend+frontend)

#### Track A: Complexity Dashboard (frontend-only — all data exists on TaskPacketRead)

- [x] 36.13a: MetricCard + RiskFlags display components — `MetricCard.tsx` (label, value, icon, color), `RiskFlags.tsx` (checklist from `risk_flags` dict, red/green icons, null="pending"). Pure display, no API calls. (S, 2h)

- [x] 36.13b: FileHeatmap component — `FileHeatmap.tsx` renders `scope` data: file count, component list, file references grouped by directory with intensity bars. Null="Scope: pending". (S, 2h)

- [x] 36.13c: ComplexityDashboard container — `ComplexityDashboard.tsx` assembles score bar (color-coded by band: low=green, medium=amber, high=red), 3 MetricCards (files affected, risk flag count, expert coverage with integer thresholds: green>=2, amber=1, red=0), FileHeatmap + RiskFlags in bottom row. Depends on 36.13a, 36.13b. (M, 3h)

#### Track B: Routing Review (backend + frontend)

- [x] 36.14a: Routing review setting + Pydantic schema — add `routing_review_enabled: bool = False` to settings.py. Create `src/routing/routing_result.py` with `ExpertSelectionRead` (7 fields: expert_id, expert_class, pattern, reputation_weight/confidence, selection_score, selection_reason) and `RoutingResultRead`. (S, 2h)

- [x] 36.14b: Temporal wait point after Router — `approve_routing`/`override_routing` signal handlers in pipeline.py. `AWAITING_ROUTING_REVIEW` step enum. 30-day safety timeout. Feature-flagged via `routing_review_enabled` on PipelineInput. Mirrors intent wait point pattern. Depends on 36.14a. (M, 4h)

- [x] 36.14c: Routing review API endpoints + storage — GET `/tasks/{id}/routing`, POST `.../approve`, POST `.../override`. Add `routing_result` JSONB column to TaskPacketRow (Alembic migration). Update `router_activity()` to persist full ConsultPlan data (not reduced RouterOutput) using DB session (following intent_activity pattern). Files: planning.py, activities.py, taskpacket.py, migration. Depends on 36.14a, 36.14b. (M, 4h)

- [x] 36.14d: Routing backend tests — `test_routing_result.py` (Pydantic schema round-trip), `test_routing_endpoints.py` (GET 404/200, POST approve/override with mocked Temporal). Depends on 36.14a-c. (S, 2h)

- [ ] 36.15a: Routing API client + Zustand store — add `ExpertSelectionRead`, `RoutingResultRead` interfaces and 3 API functions (fetchRouting, approveRouting, overrideRouting) to api.ts. Create `routing-store.ts` (loadRouting, approve, override, reset). Depends on 36.14c. (S, 3h)

- [ ] 36.15b: ExpertCard + RoutingPreview components — `ExpertCard.tsx` (expert class badge, MANDATORY lock icon, reputation weight color, remove button for AUTO only). `RoutingPreview.tsx` container (loads routing on mount, expert card grid, rationale, budget, approve button). Depends on 36.15a. (M, 3h)

- [ ] 36.15c: AddExpertDropdown + component tests — `AddExpertDropdown.tsx` (select from available expert classes, excludes already-selected). Wire into RoutingPreview. `RoutingPreview.test.tsx` with 13 test cases. Depends on 36.15b. (M, 3h)

### Slice 4: Backlog Board + Manual Task Creation (NOT STARTED)

- [ ] 36.16: Backlog board frontend — Kanban view with 6 columns (Triage, Planning, Building, Verify, Done, Rejected). Cards with issue#/title/category/complexity/cost. Click to detail.
- [ ] 36.17: Board state persistence — POST/GET `/api/v1/dashboard/board/preferences`, PostgreSQL table for column width/collapse/sort.
- [ ] 36.18: Manual task creation endpoint — POST `/api/v1/dashboard/tasks` (title, description, optional category/priority/acceptance_criteria/skip_triage). skip_triage=true starts workflow immediately.
- [ ] 36.19: Manual task creation frontend — modal with title, Markdown description, category/priority dropdowns, acceptance criteria list, skip triage checkbox.
- [ ] 36.20: Historical comparison query (stretch) — GET `.../comparison` returns stats from similar past TaskPackets. Only when >5 similar tasks exist.

---

## Completed Epics

- **Epic 34** — Phase 0: SSE PoC + Frontend Scaffolding (all 14 stories COMPLETE)
- **Epic 35** — Phase 1: Pipeline Visibility (all 63 stories across S1-S4 COMPLETE)
- **Epics 0-33** — All prior epics COMPLETE
