# Playwright quality roadmap — index & status

**Last updated:** 2026-03-27 (follow-up: wizard bypass, token fix, triage snapshots)  
**Purpose:** Track the intent-review → test hardening → run → story (failures + style) workflow for every Playwright surface, and record progress.

**Collection size:** ~3,385 parametrized test cases (e.g. `[chromium]`) from **183** test modules under `tests/playwright/`.

**Prerequisites:** App reachable at `PLAYWRIGHT_BASE_URL` (default `http://localhost:9080`); `GET /healthz` must return 200.

---

## Process (repeat per page / tab)

| Step | Action |
|------|--------|
| 1 | **Read** the test module(s) for that page (typically six layers: `intent`, `api`, `style`, `interactions`, `a11y`, `snapshot`). |
| 2 | **Intent statement:** Ensure the module docstring states what the page does for operators and why (see Epic 59 / Story 76 patterns). |
| 3 | **Gap vs intent:** If the live UI does not meet the docstring, open or update a **story** (failure list, AC). |
| 4 | **Review** implementation (`frontend/src/…`, `src/…` routes/templates) against intent. |
| 5 | **Extend tests** for missing fields, labels, counts, API contracts, and visible copy. |
| 6 | **Run** that page’s tests (or full `tests/playwright/` when ready). |
| 7 | **Story:** Record failures, API mismatches, and **style** issues (tokens, contrast, focus rings). |
| 8 | **Update this roadmap** row → next page. |

**Shared infrastructure:**

- `tests/playwright/conftest.py` — `navigate()` uses `load`, not `networkidle`.
- `tests/playwright/pipeline_dashboard/conftest.py` — autouse `_dashboard_bypass_setup_wizard` sets `thestudio_setup_complete` so Epic 44 modal does not cover the dashboard under test.

---

## Surfaces at a glance

| Area | Routes / scope | Test modules (×6 + extras) | Roadmap status |
|------|----------------|---------------------------|----------------|
| **Admin HTMX** | `/admin/ui/*` | `test_<page>_{intent,api,style,interactions,a11y,snapshot}.py` | Not started — bulk |
| **React Pipeline Dashboard** | `/dashboard/?tab=…` | `pipeline_dashboard/test_pd_<tab>_*.py` + `test_pd_cross_tab_compliance.py` | **Pilot: Triage tab** (see below) |
| **Cross-cutting** | Multiple | `test_smoke.py`, `test_all_pages.py`, `test_url_docs.py`, `test_rendering_quality.py`, `test_epic75_a11y.py`, `test_style_guide_compliance.py`, `test_htmx_interactions.py` | Not started |
| **Shared libs** | N/A | `test_lib_*.py` (7 modules) | Not started |

---

## Pilot: Pipeline Dashboard — Triage tab (`?tab=triage`)

| Step | Status | Notes |
|------|--------|--------|
| Intent docstrings | Done | Already present in `test_pd_triage_*.py` (Story 76.3). |
| `navigate()` / timeouts | Done | `conftest.navigate` uses `wait_until="load"` (fixes SPA `networkidle` hangs). |
| API tests vs backend | Done | `test_pd_triage_api.py` updated: query param **`status=triage`** (matches `frontend/src/lib/api.ts` and API enum; was incorrectly `triaging`). |
| Run triage API module | Done | `test_pd_triage_api.py`: **8 passed**, 5 skipped (2026-03-27). |
| Run full triage suite | Partial | **4 failed** (a11y only), 27 passed, 37 skipped, 5 xfailed — after wizard bypass + `--color-bg-surface` + snapshot refresh (2026-03-27). |
| Story (failures + style) | Updated | `docs/epics/stories/story-playwright-quality-audit-2026-03-27.md` |

---

## Full test module index (183 files)

<details>
<summary><strong>pipeline_dashboard/</strong> (79 files)</summary>

- `test_pd_activity_a11y.py` … `test_pd_activity_style.py`
- `test_pd_analytics_a11y.py` … `test_pd_analytics_style.py`
- `test_pd_api_a11y.py` … `test_pd_api_style.py`
- `test_pd_board_a11y.py` … `test_pd_board_style.py`
- `test_pd_budget_a11y.py` … `test_pd_budget_style.py`
- `test_pd_cross_tab_compliance.py`
- `test_pd_intent_a11y.py` … `test_pd_intent_style.py`
- `test_pd_pipeline_a11y.py` … `test_pd_pipeline_style.py`
- `test_pd_repos_a11y.py` … `test_pd_repos_style.py`
- `test_pd_reputation_a11y.py` … `test_pd_reputation_style.py`
- `test_pd_routing_a11y.py` … `test_pd_routing_style.py`
- `test_pd_triage_a11y.py` … `test_pd_triage_style.py`
- `test_pd_trust_a11y.py` … `test_pd_trust_style.py`

</details>

<details>
<summary><strong>Admin UI (root of tests/playwright)</strong> (96 files)</summary>

- `test_audit_*.py` (6), `test_compliance_*.py` (6), `test_cost_dashboard_*.py` (6)
- `test_dashboard_*.py` (6), `test_dead_letters_*.py` (6), `test_detail_pages_*.py` (6)
- `test_experts_*.py` (6), `test_metrics_*.py` (6), `test_models_*.py` (6)
- `test_planes_*.py` (6), `test_portfolio_health_*.py` (6), `test_quarantine_*.py` (6)
- `test_repos_*.py` (6), `test_settings_*.py` (6), `test_tools_*.py` (6)
- `test_workflows_*.py` (6)
- `test_epic75_a11y.py`, `test_all_pages.py`, `test_smoke.py`, `test_url_docs.py`, `test_rendering_quality.py`, `test_style_guide_compliance.py`, `test_htmx_interactions.py`

</details>

<details>
<summary><strong>Lib / helpers</strong> (7 files)</summary>

- `test_lib_accessibility_helpers.py`, `test_lib_api_helpers.py`, `test_lib_component_validators.py`
- `test_lib_interaction_helpers.py`, `test_lib_snapshot_helpers.py`, `test_lib_style_assertions.py`, `test_lib_typography_assertions.py`

</details>

---

## How to run

```bash
# Full suite (long — thousands of tests)
set PLAYWRIGHT_BASE_URL=http://127.0.0.1:9080
pytest tests/playwright/ -q

# Single tab (example: triage)
pytest tests/playwright/pipeline_dashboard/test_pd_triage_*.py -q
```

---

## Changelog

| Date | Change |
|------|--------|
| 2026-03-27 | Initial roadmap; Triage pilot; `navigate()` load fix; API `status=triage` alignment; story file for failures. |
| 2026-03-27 | Dashboard autouse setup-wizard bypass; triage style test uses `--color-bg-surface`; triage PNG baselines regenerated; Triage failures down to **4** (focus, touch target, axe ×2). |
| 2026-03-27 | **UI follow-up:** tab focus rings + `data-dashboard-shell` CSS fallback; HelpPanel scroll when closed; EmptyState link touch/contrast; HeaderBar/ConnectionIndicator contrast; notification/repo/import/help/app-switcher rings. **Rebuild app** to validate Playwright. |
