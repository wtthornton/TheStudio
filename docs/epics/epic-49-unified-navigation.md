# Epic 49: Unified Navigation -- Bridge React SPA and Admin UI into a Coherent Experience

> **Status:** DRAFT -- Pending Meridian Review
> **Epic Owner:** Primary Developer
> **Duration:** 1-2 weeks (2 slices, 6 stories)
> **Created:** 2026-03-23
> **Priority:** P2 -- Two disconnected UIs confuse users who don't know both exist
> **Depends on:** Epic 34 (React SPA) COMPLETE. No dependency on Epic 44 — navigation links work regardless of wizard existence.
> **Capacity:** Solo developer, 30 hours/week

---

## 1. Title

**Unified Navigation -- Cross-Links, Shared Header, and Navigation Sidebar Bridge the React SPA and HTMX Admin UI into a Single Coherent Experience**

---

## 2. Narrative

TheStudio has two separate frontends that share no navigation:

1. **React SPA** at `/dashboard/` -- Pipeline visualization, triage, analytics, real-time monitoring. Built with React 19, Vite, Tailwind, SSE.
2. **HTMX Admin UI** at `/admin/ui/` -- Fleet dashboard, repo management, workflows, settings, audit. Built with Jinja2, HTMX, Tailwind CDN.

A user on `/dashboard/` has no way to discover `/admin/ui/` exists. A user on `/admin/ui/repos` has no way to jump to the React SPA's Pipeline tab to see their repo's issues flowing. The two UIs were built in different epics with different tech stacks and never connected.

This creates real confusion: "Where do I register a repo?" (Admin UI). "Where do I see my pipeline?" (React SPA). "Where are the settings?" (Admin UI). "Where are the analytics?" (React SPA). The user must know two URLs, two navigation patterns, and two mental models.

This epic adds:

1. **Shared navigation bar** -- A persistent top bar on both UIs with links to the other. The React SPA gets an "Admin" link to `/admin/ui/`. The Admin UI gets a "Dashboard" link to `/dashboard/`.
2. **Context-aware cross-links** -- Deep links between specific pages: clicking a repo name in the SPA links to its Admin settings page. Clicking "View Pipeline" in the Admin workflow console links to the SPA Pipeline tab filtered to that repo.
3. **App switcher** -- A dropdown in the nav bar showing both apps with descriptions, similar to how Google Workspace shows the app grid.

No backend changes. Both UIs continue to use their own tech stacks. The cross-links are standard `<a href>` tags.

---

## 3. References

| Type | Reference | Relevance |
|------|-----------|-----------|
| Source | `frontend/src/App.tsx` | React SPA header where admin links are added |
| Source | `frontend/src/components/HeaderBar.tsx` | React SPA header bar |
| Source | `src/admin/templates/base.html` | Admin UI base layout with sidebar |
| Source | `frontend/src/components/planning/BacklogBoard.tsx` | Repo names that could deep-link to admin |
| Docs | `docs/URLs.md` | All URL paths for both UIs |

---

## 4. Acceptance Criteria

### AC1: React SPA Has Admin UI Links

The React SPA header bar includes an "Admin" link/button that opens `/admin/ui/` in the same tab. An app switcher dropdown shows both "Pipeline Dashboard" (current) and "Admin Console" with descriptions and icons.

**Testable:** Open `/dashboard/`. Locate "Admin" link in header. Click it. `/admin/ui/` loads. App switcher dropdown shows both apps.

### AC2: Admin UI Has SPA Dashboard Link

The HTMX Admin UI sidebar (or header) includes a "Pipeline Dashboard" link to `/dashboard/`. The link is visually distinct (e.g., different icon) to indicate it goes to a different app.

**Testable:** Open `/admin/ui/`. Locate "Pipeline Dashboard" link. Click it. `/dashboard/` loads.

### AC3: Deep Links Between Specific Pages

At least 5 context-aware cross-links exist:
1. SPA: repo name in Repos tab links to `/admin/ui/repos/{id}` (admin settings)
2. SPA: "Settings" in header links to `/admin/ui/settings`
3. Admin: workflow row links to `/dashboard/?tab=pipeline&repo={owner/repo}`
4. Admin: repo "View Pipeline" button links to SPA filtered by that repo
5. Admin: "Real-time" indicator links to `/dashboard/?tab=pipeline`

**Testable:** Click repo name in SPA Repos tab. Admin repo detail page opens. Click "View Pipeline" in Admin workflow list. SPA opens with pipeline tab active.

### AC4: SPA Handles URL Parameters for Deep Links

The React SPA reads `?tab=` and `?repo=` query parameters on load. `?tab=pipeline` opens the Pipeline tab. `?repo=owner/repo` sets the repo context filter. This enables deep links from Admin UI and bookmarking.

**Testable:** Navigate to `/dashboard/?tab=analytics&repo=myorg/myrepo`. SPA loads with Analytics tab active and repo filter set to `myorg/myrepo`.

---

## 5. Constraints & Non-Goals

- The two UIs remain separate applications with separate tech stacks. No rewrite to unify them.
- No shared authentication state (both use the same Caddy Basic Auth in production).
- No iframe embedding of one UI inside the other.
- The Admin UI sidebar navigation is not changed structurally -- only a link to the SPA is added.
- Mobile responsiveness of the cross-navigation is not in scope.

---

## 6. Stakeholders & Roles

| Role | Who | Responsibility |
|------|-----|----------------|
| Primary Developer | Solo | Implementation |

---

## 7. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| SPA → Admin links | 3+ links from React SPA to Admin UI | `grep -r 'admin/ui' frontend/src/ \| wc -l` >= 3 |
| Admin → SPA links | 2+ links from Admin UI to React SPA | `grep -r '/dashboard' src/admin/templates/ \| wc -l` >= 2 |
| URL parameter handling | `?tab=` and `?repo=` parsed on load | Vitest: 2 assertions (tab param, repo param) |
| App switcher renders | Dropdown with both apps in React SPA header | Vitest: component render assertion |

---

## 8. Context & Assumptions

- React SPA uses client-side tab state (no URL routing currently). AC4 adds query parameter support.
- Admin UI uses Jinja2 server-side rendering. Links to SPA are static `<a>` tags.
- Both UIs are served from the same origin (port 8000 in dev, 9443 via Caddy in prod).
- The app switcher is a simple dropdown, not a full portal experience.

---

## 9. Story Map

### Slice 1: Navigation Infrastructure (3 stories, ~4h)

| Story | Title | Size | Description |
|-------|-------|------|-------------|
| 49.1 | Add app switcher dropdown to React SPA HeaderBar | S | Dropdown in top-right of HeaderBar. Two items: "Pipeline Dashboard" (current, checkmark), "Admin Console" (link to `/admin/ui/`). Icon + description for each. |
| 49.2 | Add SPA link to Admin UI base template | S | "Pipeline Dashboard" link in `base.html` sidebar (above or below existing navigation). Distinct icon (chart/pipeline). Opens `/dashboard/` in same tab. |
| 49.3 | Add URL query parameter handling to React SPA | M | Parse `?tab=` and `?repo=` from `window.location.search` on mount. Set active tab and repo context accordingly. Update browser URL when tab changes (replaceState, no full navigation). |

### Slice 2: Context-Aware Deep Links (3 stories, ~4h)

| Story | Title | Size | Description |
|-------|-------|------|-------------|
| 49.4 | Add deep links from SPA to Admin UI | S | Repo names in SPA Repos tab link to `/admin/ui/repos/{id}`. "Settings" link in header/help menu goes to `/admin/ui/settings`. |
| 49.5 | Add deep links from Admin UI to SPA | S | "View Pipeline" button on workflow rows links to `/dashboard/?tab=pipeline&repo={owner/repo}`. Repo detail page gets "Open in Dashboard" link. |
| 49.6 | Unit tests for cross-navigation | S | Vitest: URL parameter parsing sets correct tab and repo. Links render with correct hrefs. App switcher dropdown opens/closes. |

---

## 10. Meridian Review Status

**Status:** PENDING
