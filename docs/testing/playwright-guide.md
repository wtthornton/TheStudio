# Playwright Testing Guide

> **Status:** Active (v0.3.0, 2026-03-26)
> **Test count:** 110 test files, ~2,200 test cases across 16 admin pages
> **Infrastructure:** Epic 58 (shared libs), Epics 59-74 (per-page suites)
> **Framework:** pytest-playwright (Python, not @playwright/test)

---

## Quick Start

```bash
# 1. Ensure the Docker stack is running
cd infra && docker compose -f docker-compose.prod.yml up -d

# 2. Verify the app is healthy
curl http://localhost:9080/healthz
# → {"status":"ok"}

# 3. Install test dependencies (if not already)
pip install -e ".[dev]"
python -m playwright install chromium

# 4. Run all Playwright tests
pytest tests/playwright/ -q

# 5. Run tests for a specific page
pytest tests/playwright/test_dashboard_*.py -q

# 6. Run a specific test category across all pages
pytest tests/playwright/ -k "style" -q
pytest tests/playwright/ -k "a11y" -q
pytest tests/playwright/ -k "intent" -q
```

## Prerequisites

| Requirement | How to verify |
|-------------|---------------|
| Docker stack running | `curl http://localhost:9080/healthz` returns `{"status":"ok"}` |
| `ADMIN_PASSWORD` in `infra/.env` | Plaintext password (not hash) — used for Caddy basic auth |
| `ADMIN_USER` in `infra/.env` | Default: `admin` |
| Chromium installed | `python -m playwright install chromium` |
| pytest-playwright | `pip show pytest-playwright` (included in `.[dev]`) |

## Architecture

```
tests/playwright/
├── conftest.py                    # Fixtures: base_url, auth, navigate(), console_errors
├── lib/                           # Shared assertion libraries (Epic 58)
│   ├── __init__.py
│   ├── style_assertions.py        # Color/token validation (58.1)
│   ├── typography_assertions.py   # Font size/weight/family checks (58.2)
│   ├── component_validators.py    # Card, table, badge, button recipes (58.3)
│   ├── api_helpers.py             # API endpoint response validation (58.4)
│   ├── interaction_helpers.py     # Click, HTMX swap, form helpers (58.5)
│   ├── accessibility_helpers.py   # axe-core, focus, ARIA, contrast (58.6)
│   └── snapshot_helpers.py        # Visual regression baselines (58.7)
├── test_dashboard_intent.py       # Epic 59.1
├── test_dashboard_api.py          # Epic 59.2
├── test_dashboard_style.py        # Epic 59.3
├── test_dashboard_interactions.py # Epic 59.4
├── test_dashboard_a11y.py         # Epic 59.5
├── test_dashboard_snapshot.py     # Epic 59.6
├── test_repos_*.py                # Epic 60 (6 files)
├── test_workflows_*.py            # Epic 61 (6 files)
├── ...                            # Epics 62-74 follow the same pattern
├── test_all_pages.py              # Cross-page smoke tests
└── test_style_guide_compliance.py # Global style guide checks
```

### 6-Story Pattern (per page)

Every admin page has 6 test files following this pattern:

| Suffix | Story | What it tests | Shared lib |
|--------|-------|--------------|------------|
| `_intent.py` | N.1 | Page delivers its purpose (semantic content) | — |
| `_api.py` | N.2 | Backing API endpoints return valid JSON | `api_helpers.py` |
| `_style.py` | N.3 | Style guide compliance (colors, tokens, typography, components) | `style_assertions.py`, `component_validators.py` |
| `_interactions.py` | N.4 | Buttons, forms, HTMX swaps, toggles work | `interaction_helpers.py` |
| `_a11y.py` | N.5 | WCAG 2.2 AA (focus, keyboard, ARIA, contrast, axe-core) | `accessibility_helpers.py` |
| `_snapshot.py` | N.6 | Visual regression baseline screenshot | `snapshot_helpers.py` |

### Pages Covered

| Epic | Page | URL | Test files |
|------|------|-----|------------|
| 59 | Fleet Dashboard | `/admin/ui/dashboard` | `test_dashboard_*.py` |
| 60 | Repo Management | `/admin/ui/repos` | `test_repos_*.py` |
| 61 | Workflow Console | `/admin/ui/workflows` | `test_workflows_*.py` |
| 62 | Audit Log | `/admin/ui/audit` | `test_audit_*.py` |
| 63 | Metrics | `/admin/ui/metrics` | `test_metrics_*.py` |
| 64 | Expert Performance | `/admin/ui/experts` | `test_experts_*.py` |
| 65 | Tool Hub | `/admin/ui/tools` | `test_tools_*.py` |
| 66 | Model Gateway | `/admin/ui/models` | `test_models_*.py` |
| 67 | Compliance Scorecard | `/admin/ui/compliance` | `test_compliance_*.py` |
| 68 | Quarantine | `/admin/ui/quarantine` | `test_quarantine_*.py` |
| 69 | Dead-Letter Inspector | `/admin/ui/dead-letters` | `test_dead_letters_*.py` |
| 70 | Execution Planes | `/admin/ui/planes` | `test_planes_*.py` |
| 71 | Settings | `/admin/ui/settings` | `test_settings_*.py` |
| 72 | Cost Dashboard | `/admin/ui/cost-dashboard` | `test_cost_dashboard_*.py` |
| 73 | Portfolio Health | `/admin/ui/portfolio-health` | `test_portfolio_health_*.py` |
| 74 | Detail Pages | `/{entity}/{id}` | `test_detail_pages_*.py` |

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PLAYWRIGHT_BASE_URL` | `http://localhost:9080` | Target app URL |
| `PLAYWRIGHT_USER_ID` | `admin` | X-User-ID header for admin auth |
| `PLAYWRIGHT_HTTP_USER` | Falls back to `ADMIN_USER` | Caddy basic auth username |
| `PLAYWRIGHT_HTTP_PASSWORD` | Falls back to `ADMIN_PASSWORD` | Caddy basic auth password |

### Auth Flow

1. **Caddy basic auth** — `ADMIN_USER` / `ADMIN_PASSWORD` from `infra/.env` is sent as HTTP Basic credentials on every request
2. **App-level auth** — `X-User-ID: admin` header is added to all requests via `browser_context_args` fixture
3. **Auto-skip** — if `/healthz` is unreachable, all tests skip with a message

### Running Against Different Environments

```bash
# Local Docker (default)
pytest tests/playwright/ -q

# Local dev server (no Caddy)
PLAYWRIGHT_BASE_URL=http://localhost:8000 pytest tests/playwright/ -q

# Remote staging
PLAYWRIGHT_BASE_URL=https://staging.example.com \
PLAYWRIGHT_HTTP_USER=admin \
PLAYWRIGHT_HTTP_PASSWORD=secret \
pytest tests/playwright/ -q
```

## Common Commands

```bash
# Run all tests (full suite, ~30 min)
pytest tests/playwright/ -q

# Run one page's tests (~2 min)
pytest tests/playwright/test_dashboard_*.py -q

# Run one test category across all pages
pytest tests/playwright/ -k "intent" -q      # semantic content
pytest tests/playwright/ -k "api" -q          # API endpoints
pytest tests/playwright/ -k "style" -q        # style guide compliance
pytest tests/playwright/ -k "interactions" -q # interactive elements
pytest tests/playwright/ -k "a11y" -q         # accessibility
pytest tests/playwright/ -k "snapshot" -q     # visual regression

# Run with verbose output (see test names)
pytest tests/playwright/test_audit_a11y.py -v

# Run a single test
pytest tests/playwright/test_audit_a11y.py::TestAuditFilterAria::test_filter_controls_have_accessible_labels -v

# Stop on first failure
pytest tests/playwright/ -x -q

# Show only failures (short traceback)
pytest tests/playwright/ -q --tb=line

# Run headed (visible browser)
pytest tests/playwright/test_dashboard_intent.py --headed

# Run with slow-mo for debugging
pytest tests/playwright/test_dashboard_intent.py --headed --slowmo=500

# Generate HTML report (requires pytest-html)
pytest tests/playwright/ --html=playwright-report.html --self-contained-html
```

## Shared Libraries (Epic 58)

### `style_assertions.py` — Color & Token Validation

```python
from tests.playwright.lib.style_assertions import (
    assert_color_matches,       # compare computed CSS color to expected
    assert_token_registered,    # verify CSS custom property exists on :root
    get_computed_color,         # extract rgba from element
)
```

### `typography_assertions.py` — Font Checks

```python
from tests.playwright.lib.typography_assertions import (
    assert_font_family,         # verify font-family includes expected value
    assert_font_size_range,     # verify font-size is within expected range
    assert_font_weight,         # verify font-weight matches
)
```

### `component_validators.py` — Component Recipes

```python
from tests.playwright.lib.component_validators import (
    assert_card_recipe,         # validate card structure (bg, border, radius, padding)
    assert_table_recipe,        # validate table (headers, rows, hover states)
    assert_badge_recipe,        # validate badge (colors, text, border-radius)
)
```

### `api_helpers.py` — API Endpoint Validation

```python
from tests.playwright.lib.api_helpers import (
    fetch_json,                 # GET endpoint, assert 200, return parsed JSON
    assert_json_schema,         # validate response has required keys
)
```

### `accessibility_helpers.py` — WCAG 2.2 AA

```python
from tests.playwright.lib.accessibility_helpers import (
    run_axe_audit,              # inject axe-core, run audit, return violations
    assert_focus_visible,       # verify element shows focus indicator
    assert_aria_attribute,      # check ARIA attribute exists and has value
)
```

### `snapshot_helpers.py` — Visual Regression

```python
from tests.playwright.lib.snapshot_helpers import (
    take_baseline_snapshot,     # capture and save baseline screenshot
    compare_snapshot,           # compare current to baseline with threshold
)
```

## Writing New Tests

### Adding a test for a new page

1. Create 6 files following the pattern: `test_{pagename}_{type}.py`
2. Import `navigate` from `conftest.py` for page navigation
3. Use shared libs from `tests/playwright/lib/` for assertions
4. Mark all tests with `pytestmark = pytest.mark.playwright`

### Test template

```python
"""Epic N.1 — {Page Name}: Page Intent & Semantic Content."""

import pytest
from tests.playwright.conftest import navigate

pytestmark = pytest.mark.playwright

PAGE_URL = "/admin/ui/{pagename}"


class TestPageContent:
    def test_page_loads(self, page, base_url: str) -> None:
        navigate(page, f"{base_url}{PAGE_URL}")
        assert page.title() or page.locator("h1, h2").count() > 0

    def test_key_content_visible(self, page, base_url: str) -> None:
        navigate(page, f"{base_url}{PAGE_URL}")
        body = page.locator("body").inner_text()
        assert "Expected Content" in body
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| All tests skipped: "App stack is not running" | Start Docker: `cd infra && docker compose -f docker-compose.prod.yml up -d` |
| 401 Unauthorized on all pages | Ensure `ADMIN_PASSWORD` (plaintext, not hash) is in `infra/.env` |
| Tests hang on `page.goto()` | Check Caddy is running: `docker compose ps caddy` |
| `playwright._impl._errors.Error: Browser closed` | Run `python -m playwright install chromium` |
| Snapshot tests fail on CI | Snapshots are platform-dependent; set `--update-snapshots` on first CI run |
| `assert_focus_visible` TypeError | Check function signature matches `accessibility_helpers.py` |

## Baseline Results (v0.3.0, 2026-03-26)

| Metric | Value |
|--------|-------|
| Total test cases | ~2,200 |
| Passed | 1,291 |
| Failed | 392 |
| Skipped | 549 |
| Duration | ~32 min |
| Pass rate (non-skipped) | 77% |

Known failure categories (Epic 76 tracks fixes):
- Design token name mismatches (tests assert tokens not in `:root`)
- Typography assertion calibration (expected vs actual font values)
- axe-core integration API misuse in test code
- `assert_focus_visible()` function signature mismatch
- Kanban view tests assume board visible on initial render
- Tools API endpoint shape mismatch

## References

- Style guide: `docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md`
- Epic 58 (infra): `docs/epics/epic-58-playwright-test-infrastructure.md`
- Epics 59-74: `docs/epics/epic-{N}-*-playwright-suite.md`
- conftest.py: `tests/playwright/conftest.py`
- Shared libs: `tests/playwright/lib/`
