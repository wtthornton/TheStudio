# Epic 45: Contextual Help System -- Route-Aware Help Panel and Inline Tooltips

> **Status:** DRAFT -- Pending Meridian Review
> **Epic Owner:** Primary Developer
> **Duration:** 2-3 weeks (3 slices, 9 stories)
> **Created:** 2026-03-23
> **Priority:** P2 -- Users get stuck on complex features with no in-app guidance
> **Depends on:** Epic 34 (React SPA) COMPLETE. Epic 44 (Setup Wizard) is soft dependency — help panel works without wizard but wizard can link to help content.
> **Capacity:** Solo developer, 30 hours/week

---

## 1. Title

**Contextual Help System -- Route-Aware Help Panel and Inline Tooltips Provide In-App Guidance Without Leaving the Dashboard**

---

## 2. Narrative

TheStudio has 11 tabs in the React SPA and 15 pages in the Admin UI. Each tab surfaces domain-specific concepts: Intent Specifications, Trust Tiers, Reputation Weights, Evidence Bundles, Expert Routing, Loopback Cycles. None of these are self-explanatory. There are no tooltips on any form field, no "What is this?" links, no help panel, and no contextual documentation.

The documentation exists -- `thestudioarc/` has architecture docs, `docs/deployment.md` covers configuration, `docs/URLs.md` covers endpoints. But it's all external. A user configuring Trust Tiers in the Admin UI has to context-switch to a Markdown file in a git repo to understand what "Observe" vs "Suggest" vs "Execute" means.

This epic adds two things:

1. **Help Panel** -- a collapsible `?` sidebar in the React SPA that renders route-specific Markdown content. When the user is on the Pipeline tab, it shows pipeline help. On Triage, triage help. Content lives as `.md` files in `frontend/src/help/` and is bundled at build time. The panel includes a search bar (Fuse.js for client-side fuzzy search across all help content).

2. **Inline Tooltips** -- using `react-tooltip` (MIT, most popular React tooltip library) on form fields, KPI cards, and configuration controls across both React SPA and HTMX Admin UI. Tooltips provide one-line explanations on hover.

No external services. No API calls. All content is static Markdown shipped with the frontend build.

---

## 3. References

| Type | Reference | Relevance |
|------|-----------|-----------|
| Library | `react-tooltip` (MIT) | Tooltip component for React |
| Library | `fuse.js` (MIT, 18k stars) | Client-side fuzzy search |
| Library | `react-markdown` (MIT) | Markdown renderer for React |
| Source | `frontend/src/App.tsx` | Panel toggle integration |
| Source | `thestudioarc/` | Source content for help articles |
| Source | `docs/deployment.md` | Source content for configuration help |

---

## 4. Acceptance Criteria

### AC1: Help Panel Opens and Shows Route-Specific Content

Clicking the `?` button in the header bar opens a right-side panel (320px wide, slide-in animation). The panel renders Markdown content matched to the currently active tab. Switching tabs updates the panel content without closing it. Clicking `?` again or pressing Escape closes the panel.

**Testable:** Open Pipeline tab, click `?`. Panel shows pipeline help. Switch to Triage tab. Panel updates to triage help without reopening.

### AC2: Help Content Is Searchable

The help panel has a search bar at the top. Typing a query filters all help articles across all tabs using fuzzy matching. Results show article title and a snippet. Clicking a result navigates to that tab and shows the full article.

**Testable:** Type "trust tier" in search. Results include Trust Tiers help and any article mentioning trust tiers. Click result. Panel shows full article, active tab switches to Trust Tiers.

### AC3: Inline Tooltips on Key UI Elements

At least 30 tooltip instances are added across the React SPA:
- All KPI cards in the header bar (active, queued, cost)
- All pipeline stage names (9 stages)
- Trust tier labels (Observe, Suggest, Execute)
- Budget fields (per-issue cap, per-tier limits)
- Triage queue column headers
- Intent editor field labels

**Testable:** Hover over any pipeline stage name. Tooltip appears within 200ms with a one-line description. Tooltip disappears on mouse leave.

### AC4: Admin UI (HTMX) Gets Tooltip Support

The Jinja2 Admin UI at `/admin/ui/` gets `title` attributes and a lightweight tooltip CSS treatment on key form fields and dashboard metrics. No JavaScript library required -- CSS-only tooltips using `[data-tooltip]::after`.

**Testable:** Hover over a metric card on the Admin dashboard. CSS tooltip shows description.

---

## 5. Constraints & Non-Goals

- Help content is static Markdown, not fetched from a CMS or API.
- No AI-powered help (AnythingLLM is explicitly excluded per user decision).
- No video tutorials or animated GIFs in help content.
- Help panel is React SPA only; Admin UI gets tooltips only (no panel).
- Internationalization is not in scope.

---

## 6. Stakeholders & Roles

| Role | Who | Responsibility |
|------|-----|----------------|
| Primary Developer | Solo | Implementation, content authoring |

---

## 7. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Help content coverage | 11/11 tabs have dedicated help articles | `ls frontend/src/help/*.md \| wc -l` = 11+ |
| Tooltip coverage | 30+ tooltips across React SPA | `grep -r 'data-tooltip-id' frontend/src/ \| wc -l` >= 30 |
| Admin UI tooltip coverage | 15+ tooltips across HTMX templates | `grep -r 'data-tooltip' src/admin/templates/ \| wc -l` >= 15 |
| Search works | Fuse.js returns results for "trust tier", "pipeline", "webhook" | Vitest: 3 search query assertions |

---

## 8. Context & Assumptions

- Help content will be authored by the primary developer based on existing docs.
- Markdown files are bundled by Vite at build time (no runtime file loading).
- Fuse.js index is built once on component mount from all help files.
- react-tooltip v5+ supports React 19.

---

## 9. Story Map

### Slice 1: Help Panel Infrastructure (4 stories, ~6h)

| Story | Title | Size | Description |
|-------|-------|------|-------------|
| 45.1 | Install dependencies, create HelpPanel shell | S | `npm install react-tooltip react-markdown fuse.js`. Create `frontend/src/components/help/HelpPanel.tsx` with slide-in/out animation, close button, Escape key handler. |
| 45.2 | Create HelpMenu dropdown component | S | Create `frontend/src/components/help/HelpMenu.tsx` — dropdown triggered by `?` icon in HeaderBar. Menu items: "Help Panel" (toggles panel), "Setup Wizard" (placeholder, wired by Epic 44), "Guided Tours" (placeholder, wired by Epic 47), "API Docs" (link to `/docs`). **This component is the shared help menu referenced by Epics 44, 47, and 50.** |
| 45.3 | Add HelpMenu to HeaderBar, wire HelpPanel toggle | S | Mount `HelpMenu` in HeaderBar. "Help Panel" item toggles `helpOpen` state in App.tsx. HelpPanel renders conditionally. |
| 45.4 | Route-aware content loading | M | Create `frontend/src/help/` directory with 11 Markdown files (one per tab). `HelpPanel` reads the active tab and renders matching content via `react-markdown`. Import `.md` files as raw strings via Vite's `?raw` import. |

### Slice 2: Search & Help Content (3 stories, ~6h)

| Story | Title | Size | Description |
|-------|-------|------|-------------|
| 45.5 | Add Fuse.js search to HelpPanel | M | Build Fuse.js index from all help articles on mount. Search bar at top of panel. Typing filters to matching articles with title + snippet. Clicking result loads full article and switches tab. |
| 45.6 | Author help content for all 11 tabs | M | Write Markdown help articles: Pipeline, Triage, Intent Review, Routing Review, Backlog, Trust Tiers, Budget, Activity Log, Analytics, Reputation, Repos. Each article: 200-400 words, covers "What is this?", "Key concepts", "How to use". |
| 45.7 | Author help content for configuration concepts | S | Cross-cutting help articles: "Understanding Trust Tiers", "How Webhooks Work", "Evidence Bundles Explained", "Pipeline Stages Overview". Referenced from multiple tab articles. |

### Slice 3: Inline Tooltips (3 stories, ~5h)

| Story | Title | Size | Description |
|-------|-------|------|-------------|
| 45.8 | Add react-tooltip to React SPA components | M | Add tooltip instances to HeaderBar KPIs, PipelineStatus stage names, TrustConfiguration labels, BudgetDashboard fields. Minimum 30 tooltips. Consistent styling (dark bg, white text, 200ms delay). |
| 45.9 | Add CSS tooltips to Admin UI templates | S | Add `data-tooltip` attributes and CSS `::after` tooltip treatment to Jinja2 templates: dashboard metric cards, repo settings fields, workflow status labels. Minimum 15 tooltips. |
| 45.10 | Unit tests for HelpPanel, HelpMenu, and tooltips | S | Vitest tests: panel opens/closes, route switching updates content, search filters results, Escape closes panel, HelpMenu renders all items, tooltip renders on hover. |

---

## 10. Meridian Review Status

**Status:** PENDING
