# Epic 47: Interactive Product Tours -- Guided Walkthroughs for Core Workflows

> **Status:** DRAFT -- Pending Meridian Review
> **Epic Owner:** Primary Developer
> **Duration:** 2 weeks (2 slices, 8 stories)
> **Created:** 2026-03-23
> **Priority:** P2 -- Users need guided tours to understand complex multi-step workflows
> **Depends on:** Epic 34 (React SPA) COMPLETE. Epic 44 and 46 are soft dependencies — tours skip when target elements are absent (empty states), and the wizard link in AC1 degrades to a standalone beacon if wizard is not built.
> **Capacity:** Solo developer, 30 hours/week

---

## 1. Title

**Interactive Product Tours -- React Joyride Walkthroughs Guide Users Through Pipeline, Triage, Analytics, and Configuration Workflows**

---

## 2. Narrative

TheStudio's UI surfaces complex workflows that span multiple panels and concepts. The pipeline visualization has 9 stages with gate inspectors, loopback arcs, and activity streams. The triage queue involves accepting/rejecting issues, editing intent specs, and reviewing routing decisions. The analytics dashboard has 11 sub-components with throughput charts, bottleneck analysis, and drift alerts.

Even after completing the setup wizard (Epic 44), users encounter these complex pages without knowing what the UI elements mean or how the workflow progresses. A help panel (Epic 45) answers questions when asked, but doesn't proactively guide users through the interface.

Interactive product tours solve this. Using React Joyride v3 (MIT, 7.6k stars, React-native, accessible), this epic adds 4 guided tours that highlight UI elements in sequence, explain their purpose, and walk users through the core workflows. Tours trigger on first visit to each tab (stored in localStorage) and are re-launchable from the help menu.

React Joyride v3 (released March 2026) provides ARIA roles, keyboard navigation, focus trapping, and a 30% smaller bundle than v2. It uses a beacon-based activation model where pulsing dots indicate available tours.

---

## 3. References

| Type | Reference | Relevance |
|------|-----------|-----------|
| Library | React Joyride v3 (MIT, 7.6k stars) | Tour engine with accessibility |
| Source | `frontend/src/components/PipelineStatus.tsx` | Pipeline stage nodes to highlight |
| Source | `frontend/src/components/planning/TriageQueue.tsx` | Triage workflow elements |
| Source | `frontend/src/components/analytics/Analytics.tsx` | Analytics dashboard elements |
| Source | `frontend/src/components/TrustConfiguration.tsx` | Trust tier config elements |
| Pattern | UX best practice | Max 5-7 steps per tour, action-oriented |

---

## 4. Acceptance Criteria

### AC1: Pipeline Tour Covers Core Visualization

On first visit to the Pipeline tab, a beacon pulses on the pipeline rail. Clicking it (or auto-starting if Epic 44 wizard just completed) launches a 5-7 step tour covering: pipeline rail (9 stages overview), stage nodes (click to inspect), gate inspector panel, activity stream, and minimap. Each step has a title, description, and "Got it" / "Next" buttons.

**Testable:** Clear localStorage. Visit Pipeline tab. Beacon appears. Click beacon. Tour highlights pipeline rail with explanation. Complete all steps. Beacon does not reappear on next visit.

### AC2: Triage Tour Covers Decision Workflow

On first visit to the Triage tab (when issues exist), a tour walks through: triage queue layout, issue card fields, accept/reject buttons, intent editor panel, and routing preview. The tour is skipped if the queue is empty (empty state handles that case).

**Testable:** Visit Triage tab with at least one issue. Tour highlights triage card. Complete tour. Visit again. Tour does not repeat.

### AC3: All Tours Are Accessible

Tours support keyboard navigation (Tab/Shift-Tab to move between elements, Enter to advance, Escape to close). Tour overlays have ARIA roles. Focus is trapped within the active tooltip during the tour.

**Testable:** Start any tour. Navigate through all steps using only keyboard. Verify focus is trapped. Press Escape. Tour closes and focus returns to previous element.

### AC4: Tours Are Re-Launchable

Each tour can be re-launched from the help menu: "Replay Pipeline Tour", "Replay Triage Tour", etc. Re-launching clears the per-tour localStorage flag and starts the tour.

**Testable:** Complete Pipeline tour. Open help menu. Click "Replay Pipeline Tour". Tour starts again.

---

## 5. Constraints & Non-Goals

- Tours are React SPA only. HTMX Admin UI does not get tours (tooltips from Epic 45 cover it).
- Tours do not modify data or trigger actions -- they are read-only overlays.
- Tours do not span across tabs (each tour is contained within one tab).
- No tours for the setup wizard itself (it is already guided).
- Tour step content is hardcoded in TypeScript, not loaded from Markdown.

---

## 6. Stakeholders & Roles

| Role | Who | Responsibility |
|------|-----|----------------|
| Primary Developer | Solo | Implementation, step content authoring |

---

## 7. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Tour coverage | 4 tour definitions in registry | `Object.keys(tourRegistry).length` >= 4 in unit test |
| Steps per tour | 5-7 per tour (best practice maximum) | Vitest: assert each tour definition has 5-7 steps |
| Tour localStorage lifecycle | Start sets flag, completion sets done, re-launch clears | Vitest: 3 lifecycle assertions per tour |

---

## 8. Context & Assumptions

- React Joyride v3 supports React 19 (confirmed in release notes).
- Tours require the target UI elements to be rendered (tours are skipped on empty states).
- Tour step definitions use CSS selectors or `data-tour` attributes to target elements.
- localStorage keys follow pattern `thestudio_tour_{name}_complete`.

---

## 9. Story Map

### Slice 1: Tour Infrastructure + Pipeline Tour (4 stories, ~6h)

| Story | Title | Size | Description |
|-------|-------|------|-------------|
| 47.1 | Install React Joyride v3, create TourProvider | S | `npm install react-joyride`. Create `frontend/src/components/tours/TourProvider.tsx` wrapping App with Joyride context. Shared styles (dark tooltip bg, white text, accent border). |
| 47.2 | Create tour registry and localStorage manager | S | `frontend/src/components/tours/registry.ts`: defines tour step arrays keyed by tab name. `useTourState(tourName)` hook manages localStorage flags and start/complete lifecycle. |
| 47.3 | Pipeline tour: 6-step walkthrough | M | Steps: (1) Pipeline rail overview, (2) Stage node -- click to inspect, (3) Active stage pulse indicator, (4) Gate Inspector panel, (5) Activity Stream, (6) Minimap with task cards. Add `data-tour` attributes to target components. |
| 47.4 | Add tour beacons to tab content | S | Beacon component that pulses on first visit. Clicking beacon starts tour. Beacon hidden after tour completion. Beacon placement per-tab near the top-right of content area. |

### Slice 2: Remaining Tours + Re-launch (4 stories, ~6h)

| Story | Title | Size | Description |
|-------|-------|------|-------------|
| 47.5 | Triage tour: 5-step walkthrough | S | Steps: (1) Queue overview, (2) Triage card fields, (3) Accept/Reject actions, (4) Intent editor, (5) Routing preview. Skipped when queue is empty. |
| 47.6 | Analytics tour: 5-step walkthrough | S | Steps: (1) Period selector, (2) Summary KPI cards, (3) Throughput chart, (4) Bottleneck bars, (5) Expert performance table. |
| 47.7 | Repo & Trust Configuration tour: 5-step walkthrough | S | Steps: (1) Repo selector, (2) Repo settings form, (3) Trust tier dropdown, (4) Tier descriptions, (5) Budget limits. |
| 47.8 | Add tour re-launch to help menu, unit tests | S | Help menu section "Guided Tours" with 4 replay links. Vitest tests: tour starts on first visit, does not restart after completion, re-launch clears flag. |

---

## 10. Meridian Review Status

**Status:** PENDING
