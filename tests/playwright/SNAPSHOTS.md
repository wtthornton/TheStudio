# Visual Snapshot Baseline Framework

Epic 58, Story 58.7 — `tests/playwright/lib/snapshot_helpers.py`

---

## Overview

The snapshot framework provides full-page and element-level visual regression
testing for TheStudio's Admin UI pages.  Baselines are stored as PNG files and
compared on each test run using a configurable pixel-diff threshold.

---

## Storage Layout

```
tests/playwright/snapshots/
    {page_name}/
        {snapshot_name}-linux.png
        {snapshot_name}-darwin.png
        {snapshot_name}-win32.png
```

- **`page_name`** — logical grouping (e.g. `fleet-dashboard`, `repo-management`)
- **`snapshot_name`** — identifier within the page (e.g. `full-page`, `sidebar`)
- **Platform suffix** — prevents cross-platform false positives caused by
  font rendering or subpixel differences between operating systems

---

## Workflow

### First run (no baseline)

The framework **automatically creates a baseline** and the test passes.  No
manual step is needed.

### Subsequent runs

The actual screenshot is compared against the stored baseline using
pixel-diff analysis.  The test **passes** when the diff ratio is within the
configured threshold.

### Accepting changes

When intentional visual changes have been made, regenerate all baselines by
setting `SNAPSHOT_UPDATE=1`:

```bash
SNAPSHOT_UPDATE=1 pytest tests/playwright/
```

This overwrites every baseline with the current screenshot and all tests pass.

### Updating a single baseline

Call `create_baseline()` explicitly in a one-off script or test:

```python
from tests.playwright.lib.snapshot_helpers import create_baseline

def test_regenerate(page):
    page.goto("/admin/ui/dashboard")
    result = create_baseline(page, "full-page", page_name="fleet-dashboard")
    assert result.passed
```

---

## Configuration

| Environment variable  | Default | Description                                         |
|-----------------------|---------|-----------------------------------------------------|
| `SNAPSHOT_UPDATE`     | `0`     | Set to `1` to regenerate all baselines on this run |
| `SNAPSHOT_THRESHOLD`  | `0.001` | Max allowed diff ratio (fraction 0–1, default 0.1%) |

---

## API Reference

### `capture_page_snapshot(page, name, page_name="default") → Path`

Capture a full-page screenshot at the canonical **1280×720** viewport and save
it to `tests/playwright/snapshots/{page_name}/{name}-{platform}.png`.

### `capture_element_snapshot(page, selector, name, page_name="default") → Path`

Capture a screenshot of the first element matching `selector`.  The element is
scrolled into view before capture.  Saved as
`tests/playwright/snapshots/{page_name}/{name}-element-{platform}.png`.

### `compare_snapshot(page, name, page_name="default", threshold=None) → SnapshotResult`

Compare the current page appearance against the stored baseline.

| State                        | Outcome                                          |
|------------------------------|--------------------------------------------------|
| No baseline exists           | Baseline auto-created; `passed=True`, `is_new_baseline=True` |
| `SNAPSHOT_UPDATE=1` set      | Baseline overwritten; `passed=True`, `is_update_mode=True`  |
| diff ≤ threshold             | `passed=True`                                    |
| diff > threshold             | `passed=False`; `summary()` shows both file paths |

### `create_baseline(page, name, page_name="default") → SnapshotResult`

Unconditionally (re)create the baseline.  Always returns `passed=True`.

### `snapshot_comparison` pytest fixture

```python
def test_fleet_dashboard(page, snapshot_comparison):
    page.goto("/admin/ui/dashboard")
    result = snapshot_comparison(page, "full-page", page_name="fleet-dashboard")
    assert result.passed, result.summary()
```

---

## SnapshotResult fields

| Field           | Type            | Description                                      |
|-----------------|-----------------|--------------------------------------------------|
| `passed`        | `bool`          | `True` when the comparison succeeded             |
| `snapshot_name` | `str`           | Snapshot identifier                              |
| `baseline_path` | `Path`          | Path to the baseline PNG on disk                 |
| `actual_path`   | `Path \| None`  | Path to the actual screenshot (non-None on fail) |
| `diff_ratio`    | `float \| None` | Pixel-diff ratio 0–1                             |
| `threshold`     | `float`         | Threshold that was applied                       |
| `is_new_baseline` | `bool`        | `True` when baseline was created this run        |
| `is_update_mode`  | `bool`        | `True` when `SNAPSHOT_UPDATE=1` was active       |
| `.summary()`    | `str`           | One-line human-readable outcome message          |

---

## Pixel Comparison Strategy

1. **Pillow (PIL)** — preferred; per-channel absolute difference normalised to
   `[0, 1]` over total pixels × channels.
2. **Byte-level fallback** — fraction of differing bytes; used when Pillow is
   not installed.  Less accurate but dependency-free.

Install Pillow for accurate comparison:

```bash
pip install pillow
```

---

## CI Integration

Snapshots should be **committed** to the repository so they serve as stable
baselines across CI runs.  The `.gitignore` pattern `*-actual-*.png` ensures
that only baseline files are tracked (actual captures during failed comparisons
are excluded).

Add to your CI pipeline:

```yaml
- name: Run visual snapshot tests
  run: pytest tests/playwright/test_lib_snapshot_helpers.py -v
  env:
    SNAPSHOT_THRESHOLD: "0.002"   # 0.2% tolerance for CI font rendering
```

To update baselines in CI (e.g. on a dedicated "update snapshots" workflow):

```yaml
env:
  SNAPSHOT_UPDATE: "1"
```

---

## Adding a New Page Baseline

1. Write a test that navigates to the page and calls `compare_snapshot`.
2. Run the test once — the baseline is auto-created.
3. Commit the new `*.png` file in `tests/playwright/snapshots/`.
4. Subsequent CI runs compare against this committed baseline.
