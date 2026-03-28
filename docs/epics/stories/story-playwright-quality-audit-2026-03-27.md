# Story: Playwright quality audit — findings (pilot: Triage tab)

**Type:** Technical debt / test alignment  
**Date:** 2026-03-27  
**Scope:** Pilot run of the “intent → tests → run → story” workflow on **Pipeline Dashboard → Triage** (`/dashboard/?tab=triage`).  
**Related:** `docs/playwright/PLAYWRIGHT-QUALITY-ROADMAP.md`

---

## Summary

After fixing **SPA navigation** (`tests/playwright/conftest.py`: use `load` instead of `networkidle`) and aligning **API tests** with the backend enum (`status=triage`, not `triaging`), the six Triage Playwright modules were executed together.

**Result (initial):** 17 failed, 21 passed, 32 skipped, 5 xfailed (runtime ~2 min for Triage-only).

**Result (2026-03-27 follow-up):** **6 failed**, 27 passed, 37 skipped, 5 xfailed after setup-wizard bypass + token assertion fix + triage snapshot baseline refresh.

---

## Infrastructure (fixed)

| Issue | Resolution |
|-------|------------|
| 30s timeouts in `navigate()` | `page.goto(..., wait_until="load")` + `wait_for_load_state("load")` — `networkidle` is unreliable for React/HTMX SPAs. |
| Setup wizard blocks dashboard | Autouse fixture in `tests/playwright/pipeline_dashboard/conftest.py`: `add_init_script` sets `localStorage thestudio_setup_complete=true` before JS runs (matches `wizardStorage.ts`). |
| Wrong surface token in style test | `test_surface_app_token_registered` now checks **`--color-bg-surface`** (canonical in `theme.css`); `--color-surface-app` does not exist in the React bundle. |
| Triage snapshots | Regenerated with `SNAPSHOT_UPDATE=1` after wizard no longer appears in captures. |

---

## API / contract

| Issue | Detail |
|-------|--------|
| Wrong query param in tests | Tests used `?status=triaging`; API expects **`triage`** (matches `frontend/src/lib/api.ts` `fetchTriageTasks`). **Fixed** in `test_pd_triage_api.py`. |

---

## Functional / interaction

| Issue | Detail |
|-------|--------|
| Tab switch test timeout | **Resolved** — autouse init script marks setup complete; tab navigation tests no longer blocked by wizard overlay. |

---

## Accessibility (serious) — remaining

| Check | Failure |
|-------|---------|
| Focus visible | **14** tab bar / chrome buttons missing focus ring (wizard controls removed from count). |
| Touch targets | **1** link: `Learn about triage mode` (153×20px). |
| axe | **color-contrast** (serious); **scrollable-region-focusable** (serious). |

---

## Style / design tokens

| Issue | Detail |
|-------|--------|
| ~~`--color-surface-app`~~ | **Resolved** in tests — assert `--color-bg-surface` instead (see `frontend/src/theme.css`). |

---

## Style issues (rollup for backlog)

1. ~~`--color-surface-app`~~ — superseded by `--color-bg-surface` in tests.  
2. **Focus rings** — addressed in UI (2026-03-27): `primaryNavTabClass` + `data-dashboard-shell` global `:focus` outline fallback in `frontend/src/index.css` (Playwright uses `element.focus()` without `:focus-visible`).  
3. **Contrast** — Header KPI labels and connection indicator bumped `text-gray-400` → `text-gray-300`; EmptyState body `gray-400` → `gray-300`; secondary link `gray-100`.  
4. **Scrollable regions** — `HelpPanel` body uses `overflow-hidden` when closed; `overflow-y-auto` + `tabIndex={0}` when open. Notification dropdown list already has `tabIndex={0}`. Primary nav has `tabIndex={0}`.  
5. **Touch targets** — EmptyState secondary link: `min-h-8`, `py-2.5`, `px-4`, `box-border`. Notification bell `min-h-9 min-w-9`.

**Deploy note:** Rebuild/restart the app so `frontend/dist` is copied into the running image (e.g. `docker compose build app && docker compose up -d`) before expecting Playwright on `:9080` to go green.

---

## Acceptance criteria (story closure)

- [x] Wizard does not block cross-tab interaction tests without explicit “setup path” coverage.  
- [ ] axe serious violations on Triage tab = 0 (or waived with documented exceptions).  
- [x] Surface background token asserted against real CSS (`--color-bg-surface`).  
- [ ] Re-run `tests/playwright/pipeline_dashboard/test_pd_triage_*.py` — all non-xfail tests green (**6 failures remain**: 4 a11y, 2 were snapshots → snapshots refreshed).  

---

## Next pages (order suggestion)

1. Remaining Pipeline Dashboard tabs (Pipeline, Intent Review, …) using the same six-file pattern.  
2. Admin fleet pages (`test_dashboard_*.py`, …) per `PLAYWRIGHT-QUALITY-ROADMAP.md`.
