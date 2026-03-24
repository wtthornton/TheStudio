# Epic 50: Feature Spotlights -- Highlight New Capabilities After Upgrades

> **Status:** DRAFT -- Meridian FAIL (2026-03-23), reworked. Deferred until Epics 44+45+48 ship (they create the elements to spotlight).
> **Epic Owner:** Primary Developer
> **Duration:** 1 week (1 slice, 5 stories)
> **Created:** 2026-03-23
> **Priority:** P3 -- New features go unnoticed after deployment upgrades
> **Depends on:** Epic 34 (React SPA) COMPLETE. Epic 44 (Setup Wizard), Epic 45 (Help Panel), Epic 48 (Scalar API Docs) must be COMPLETE before spotlights can reference their UI elements. Epic 47 (Product Tours) is a soft dependency — spotlights work without tours but share similar UX patterns.
> **Capacity:** Solo developer, 30 hours/week

---

## 1. Title

**Feature Spotlights -- Driver.js Highlights New and Changed Features After Deployments So Users Discover Capabilities Without Reading Changelogs**

---

## 2. Narrative

TheStudio ships new features regularly (43 epics to date). Each deployment adds or changes UI elements, endpoints, and behaviors. Users have no way to know what changed unless they read the CHANGELOG or happen to notice something different.

Feature spotlights solve this with a lightweight "What's New" overlay that appears once after a version upgrade. Using Driver.js (MIT, 25.5k stars, 5kb, zero dependencies), the spotlight highlights 1-3 specific UI elements that are new or changed, with a brief description of what they do and why they matter.

Unlike product tours (Epic 47) which teach workflows, spotlights are version-specific announcements. They appear once per version, take 10-30 seconds, and then disappear forever. They answer: "What changed since my last visit?"

The version is read from the app's build metadata (injected by Vite at build time from `pyproject.toml`). Spotlights are defined as a simple registry mapping version ranges to highlight definitions. When the user's last-seen version (localStorage) is older than the current version, matching spotlights fire.

---

## 3. References

| Type | Reference | Relevance |
|------|-----------|-----------|
| Library | Driver.js (MIT, 25.5k stars, ~5kb) | Lightweight element highlighting |
| Source | `frontend/src/App.tsx` | Entry point for spotlight trigger |
| Source | `frontend/vite.config.ts` | Build-time version injection |
| Source | `pyproject.toml` | Version source (`version = "0.1.0"`) |
| Standard | `docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md` (Section 10) | Canonical guidance UX rules for spotlights (frequency, step budget, layering, replay) |
| Source | `CHANGELOG.md` | Source of what changed per version |

---

## 4. Acceptance Criteria

### AC1: Spotlight Fires Once After Version Upgrade

When the app version (from build metadata) is newer than `localStorage.getItem('thestudio_last_seen_version')`, the spotlight overlay fires automatically after the dashboard loads (500ms delay). After dismissal, `last_seen_version` is updated to the current version. The spotlight does not fire on subsequent visits.

**Testable:** Set `last_seen_version` to "0.0.9". Load dashboard (current version "0.1.0"). Spotlight fires. Dismiss it. Reload. Spotlight does not fire again.

### AC2: Spotlight Highlights Specific UI Elements

Each spotlight definition targets 1-3 UI elements by CSS selector or `data-spotlight` attribute. Driver.js highlights the element with a popover containing: title, description (1-2 sentences), and "Got it" button. Multiple highlights are shown sequentially.

**Testable:** Define a spotlight targeting the Pipeline rail and the Help button. Spotlight first highlights pipeline rail with description. Click "Next". Spotlight moves to help button. Click "Got it". Overlay closes.

### AC3: Spotlight Registry Is Easy to Maintain

Spotlights are defined in `frontend/src/components/spotlights/registry.ts` as a typed array:
```typescript
{ version: "0.2.0", highlights: [{ selector: "[data-spotlight='help-panel']", title: "New: Help Panel", description: "..." }] }
```
Adding a new spotlight for a future version requires adding one entry to this array. No other files need modification.

**Testable:** Add a new entry to the registry with a future version. Manually set `last_seen_version` to a version before it. Reload. New spotlight fires.

### AC4: Version Is Injected at Build Time

Vite injects the version from `pyproject.toml` as `import.meta.env.VITE_APP_VERSION` at build time. The app reads this for spotlight version comparison. Fallback to "0.0.0" if not available (dev mode).

**Testable:** Build the frontend. Inspect `import.meta.env.VITE_APP_VERSION` in browser console. Matches `pyproject.toml` version.

---

## 5. Constraints & Non-Goals

- Spotlights are React SPA only. HTMX Admin UI is not modified.
- Spotlights do not show a changelog or release notes -- they highlight UI elements.
- No "What's New" page or modal with a list of changes (just element highlights).
- Spotlights do not block the UI -- users can click away to dismiss at any time.
- Maximum 3 highlights per version (respect user attention).
- Spotlights must comply with style-guide guidance standards: concise per-version budget, explicit dismiss/replay behavior, and non-overlapping primary guidance layers.

---

## 6. Stakeholders & Roles

| Role | Who | Responsibility |
|------|-----|----------------|
| Primary Developer | Solo | Implementation, spotlight content authoring per release |

---

## 7. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Spotlight fires on version mismatch | Setting old version in localStorage triggers spotlight | Vitest: set `last_seen_version` to old value, assert Driver.js activates |
| Spotlight does not fire on same version | Same version in localStorage skips spotlight | Vitest: assert Driver.js does not activate |
| Registry is extensible | Adding a new entry to registry.ts is the only change needed for a new spotlight | Code review: no files outside registry.ts touched to add spotlight |
| Version injected at build time | `import.meta.env.VITE_APP_VERSION` matches pyproject.toml | Vitest: env var is defined and non-empty |

---

## 8. Context & Assumptions

- Driver.js is framework-agnostic and works via `useEffect` in React.
- Driver.js v1.4+ supports popover customization (dark theme, position control).
- Version comparison uses semver ordering.
- Spotlights must be defined before each release -- this is a manual step in the release process.
- In development mode (no build version), spotlights never fire automatically.

---

## 9. Story Map

### Slice 1: Full Implementation (5 stories, ~5h)

| Story | Title | Size | Description |
|-------|-------|------|-------------|
| 50.1 | Install Driver.js, create spotlight infrastructure | S | `npm install driver.js`. Create `frontend/src/components/spotlights/SpotlightProvider.tsx` and `registry.ts`. SpotlightProvider reads version from build metadata, compares to localStorage, fires matching spotlights. |
| 50.2 | Inject app version at Vite build time | S | Update `vite.config.ts` to read version from `pyproject.toml` (or a version file) and expose as `VITE_APP_VERSION`. Fallback to "0.0.0" in dev. |
| 50.3 | Create initial spotlight definitions | S | Define 2-3 spotlights for the current version highlighting: Help panel button (Epic 45), Setup wizard re-launch, API docs tab (Epic 48). Use `data-spotlight` attributes on target elements. |
| 50.4 | Style Driver.js popovers to match dark theme | S | Custom CSS for Driver.js popovers: dark background (gray-900), white text, accent border (blue-500), "Got it" / "Next" buttons matching Tailwind theme. |
| 50.5 | Unit tests and release documentation | S | Vitest: spotlight fires when version is newer, does not fire when same version, registry schema validation. Add "How to add a spotlight" section to `frontend/README.md`. |

---

## 10. Meridian Review Status

**Status:** PENDING
