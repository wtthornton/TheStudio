# Epic 46: Actionable Empty States -- Replace Placeholder Text with Guided CTAs

> **Status:** DRAFT -- Pending Meridian Review
> **Epic Owner:** Primary Developer
> **Duration:** 1-2 weeks (2 slices, 7 stories)
> **Created:** 2026-03-23
> **Priority:** P1 -- Empty states are the first thing new users see and they provide zero guidance
> **Depends on:** Epic 34 (React SPA) COMPLETE. No hard dependency on Epic 44 — empty states work independently. CTA "Run setup wizard" in Pipeline empty state is a soft link; renders as plain text if wizard not yet built.
> **Capacity:** Solo developer, 30 hours/week

---

## 1. Title

**Actionable Empty States -- Replace "No Data" Placeholders with Contextual CTAs, Sample Data Previews, and Getting-Started Guidance**

---

## 2. Narrative

Every page in TheStudio starts empty. The Pipeline rail says "No tasks". The Triage queue says "No issues awaiting triage". Analytics shows "No data". The header KPIs read "0 / 0 / $0.00". For an experienced user who just deployed, this is expected. For a new user, it's a dead end -- there's nothing to click, nothing to learn, and no indication of what the page will look like once it's working.

Good empty states are the single highest-ROI UX improvement for a new product. They answer three questions: (1) What will this page show when it has data? (2) Why is it empty right now? (3) What do I do to fill it?

This epic redesigns every empty state in the React SPA and HTMX Admin UI to include:
- **Visual preview** -- a muted illustration or wireframe showing what the page looks like with data
- **Explanation** -- one sentence explaining what belongs here
- **Primary CTA** -- a button that takes the user to the right action (register a repo, configure a webhook, import an issue)
- **Secondary link** -- "Learn more" linking to the help panel (Epic 45) or docs

No new backend APIs. All changes are frontend -- new components replacing existing placeholder strings.

---

## 3. References

| Type | Reference | Relevance |
|------|-----------|-----------|
| Source | `frontend/src/components/ErrorStates.tsx` | Existing `EmptyPipelineRail` component to replace |
| Source | `frontend/src/components/planning/TriageQueue.tsx` | Inline "No issues" text to replace |
| Source | `frontend/src/components/analytics/Analytics.tsx` | "No data" placeholders in charts |
| Source | `src/admin/templates/components/empty_state.html` | Existing HTMX empty state partial |
| Pattern | UX research (Formbricks 2026) | Empty state best practices |

---

## 4. Acceptance Criteria

### AC1: Pipeline Empty State Shows Visual Preview and CTA

When the pipeline has zero tasks, `EmptyPipelineRail` renders: a muted wireframe of the 9-stage pipeline with sample tasks, a heading "Your pipeline is empty", an explanation "Issues flow through 9 stages from Intake to Publish", and a primary CTA "Import an Issue" that opens the GitHub import modal.

**Testable:** Load dashboard with no tasks. Empty state renders with pipeline wireframe, heading, explanation, and import button. Click import button. Import modal opens.

### AC2: Every Tab Has a Dedicated Empty State

All 11 tabs render a custom empty state when they have no data. Each includes: visual context, explanation, and at least one actionable CTA. Tabs covered: Pipeline, Triage, Intent Review, Routing Review, Backlog, Trust Tiers, Budget, Activity Log, Analytics, Reputation, Repos.

**Testable:** Visit each tab with no data. Each renders a unique empty state with CTA (not generic "No data").

### AC3: Admin UI Empty States Are Actionable

The HTMX Admin UI's `empty_state.html` partial is updated to accept CTA parameters (button text, URL, icon). Pages using it (repos, workflows, quarantine, dead-letters) render with relevant CTAs.

**Testable:** Visit `/admin/ui/repos` with no repos registered. Empty state shows "Register your first repository" button pointing to the registration form.

### AC4: Header KPIs Show Onboarding Hint When Zero

When all KPI values are zero (active=0, queued=0, cost=$0.00), the header shows a subtle "Getting started? Run the setup wizard" link instead of just zeroes.

**Testable:** Load dashboard with empty state. Header shows onboarding hint. Register a repo and trigger an issue. Hint disappears once any KPI is non-zero.

---

## 5. Constraints & Non-Goals

- Empty states do not include real sample data -- only muted wireframes/illustrations.
- No demo mode or seed data feature (that would be a separate epic).
- Empty state CTAs use existing modals and pages -- no new forms.
- Animations on empty states should be minimal (no looping animations).

---

## 6. Stakeholders & Roles

| Role | Who | Responsibility |
|------|-----|----------------|
| Primary Developer | Solo | Design, implementation, content |

---

## 7. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| React SPA tabs with actionable empty states | 11/11 tabs render EmptyState component with CTA | Vitest: render each tab with empty data, assert CTA button present |
| Admin UI pages with actionable empty states | 5+ pages use updated empty_state.html with CTA | `grep -r 'cta_text' src/admin/templates/ \| wc -l` >= 5 |
| Header KPI onboarding hint | Shows when all KPIs are zero, hides when any is non-zero | Vitest: two assertions (zero state, non-zero state) |

---

## 8. Context & Assumptions

- Epic 44 (Setup Wizard) may handle initial repo registration, but empty states remain valuable for subsequent tabs and for users who skip the wizard.
- Visual wireframes will be simple SVG or Tailwind-styled divs, not image assets.
- Admin UI changes are minimal -- extending the existing `empty_state.html` partial.

---

## 9. Story Map

### Slice 1: React SPA Empty States (5 stories, ~8h)

| Story | Title | Size | Description |
|-------|-------|------|-------------|
| 46.1 | Create EmptyState base component | S | Reusable `EmptyState` component: icon/illustration slot, heading, description, primary CTA button, optional secondary link. Consistent styling across all tabs. |
| 46.2 | Pipeline and Triage empty states | M | Replace `EmptyPipelineRail` with pipeline wireframe + "Import an Issue" CTA. Replace Triage placeholder with "No issues awaiting triage" + "Configure webhook" CTA. |
| 46.3 | Planning tab empty states | M | Intent Review, Routing Review, and Backlog empty states. Each with relevant explanation and CTA (e.g., "Process an issue first to see intent specifications here"). |
| 46.4 | Configuration tab empty states | S | Trust Tiers, Budget, Repos empty states. CTAs link to registration and settings. |
| 46.5 | Analytics and monitoring empty states | S | Analytics, Activity Log, Reputation empty states. "Process your first issue to see metrics here" with pipeline tab link. Header KPI onboarding hint when all zero. |

### Slice 2: Admin UI Empty States (2 stories, ~3h)

| Story | Title | Size | Description |
|-------|-------|------|-------------|
| 46.6 | Extend empty_state.html partial with CTA support | S | Add optional `cta_text`, `cta_url`, `cta_icon` parameters to the Jinja2 partial. Update all pages that use it. |
| 46.7 | Update Admin UI pages with actionable empty states | S | Repos, Workflows, Quarantine, Dead-Letters pages get specific CTAs. Unit tests verify partial renders CTA when parameters provided. |

---

## 10. Meridian Review Status

**Status:** PENDING
