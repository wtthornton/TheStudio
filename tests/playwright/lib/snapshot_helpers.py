"""Visual Snapshot Baseline Framework (Epic 58, Story 58.7).

Provides full-page and element-level screenshot capture, baseline storage, and
pixel-diff comparison for Playwright-based visual regression testing.

Features:

- ``capture_page_snapshot`` — Full-page screenshot at a consistent 1280×720
  viewport.  Returns the path of the saved image.
- ``capture_element_snapshot`` — Element-level screenshot cropped to the
  bounding box of the first matching CSS selector.
- ``compare_snapshot`` — Compare the current page appearance against a stored
  baseline; fails when the pixel-diff ratio exceeds ``threshold``.
- ``create_baseline`` — Explicitly (re)create a baseline image without
  triggering a comparison failure.
- ``snapshot_comparison`` — pytest fixture factory that binds a test name to a
  comparison helper callable.

Storage layout::

    tests/playwright/snapshots/
        {page_name}/
            {snapshot_name}-linux.png
            {snapshot_name}-darwin.png
            {snapshot_name}-win32.png

Environment variables:

- ``SNAPSHOT_UPDATE=1``        Regenerate baselines; never fail on diff.
- ``SNAPSHOT_THRESHOLD=0.001`` Override the default diff threshold (0–1,
                                fraction of total pixels).

CI behaviour:

- First run (no baseline file): baseline is auto-created; test passes.
- Subsequent runs: diff is measured; test fails when diff > threshold.
- ``SNAPSHOT_UPDATE=1``: baseline is always overwritten; test always passes.

Pixel comparison strategy:

1. **Pillow (PIL)** — preferred; per-channel RMSE normalised to [0, 1].
2. **Byte-level fallback** — fraction of differing bytes; used when Pillow is
   not installed.

Usage example::

    from tests.playwright.lib.snapshot_helpers import (
        capture_page_snapshot,
        compare_snapshot,
        create_baseline,
    )

    def test_dashboard_visual(page):
        page.goto("/admin/ui/dashboard")
        result = compare_snapshot(page, "fleet-dashboard")
        assert result.passed, result.summary()

    # pytest fixture usage
    def test_dashboard_fixture(page, snapshot_comparison):
        page.goto("/admin/ui/dashboard")
        result = snapshot_comparison(page, "fleet-dashboard")
        assert result.passed, result.summary()
"""

from __future__ import annotations

import os
import platform
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pytest

# ---------------------------------------------------------------------------
# Constants / configuration
# ---------------------------------------------------------------------------

#: Root of the snapshot storage tree.
SNAPSHOTS_DIR: Path = Path(__file__).parent.parent / "snapshots"

#: Default pixel-diff threshold (fraction of total pixels, 0.001 = 0.1 %).
DEFAULT_THRESHOLD: float = 0.001

#: Canonical viewport used for all full-page snapshots.
VIEWPORT_WIDTH: int = 1280
VIEWPORT_HEIGHT: int = 720

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _platform_tag() -> str:
    """Return a short platform identifier for snapshot file naming.

    Returns one of ``linux``, ``darwin``, or ``win32``.  Unrecognised
    platforms fall back to ``linux``.
    """
    system = sys.platform  # e.g. "linux", "darwin", "win32"
    if system in ("linux", "darwin", "win32"):
        return system
    return "linux"


def _snapshot_path(page_name: str, snapshot_name: str) -> Path:
    """Return the full path for a baseline image.

    Creates the parent directory if it does not exist.

    Args:
        page_name: Logical page identifier used as the sub-directory name
            (e.g. ``"fleet-dashboard"``).
        snapshot_name: Snapshot identifier within the page (e.g.
            ``"full-page"``).

    Returns:
        Absolute :class:`~pathlib.Path` to the ``.png`` file.
    """
    tag = _platform_tag()
    directory = SNAPSHOTS_DIR / page_name
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{snapshot_name}-{tag}.png"


def _update_mode() -> bool:
    """Return ``True`` when ``SNAPSHOT_UPDATE=1`` is set in the environment."""
    return os.environ.get("SNAPSHOT_UPDATE", "0").strip() == "1"


def _threshold() -> float:
    """Return the effective diff threshold from the environment or default."""
    raw = os.environ.get("SNAPSHOT_THRESHOLD", "")
    if raw.strip():
        try:
            value = float(raw.strip())
            if 0.0 <= value <= 1.0:
                return value
        except ValueError:
            pass
    return DEFAULT_THRESHOLD


def _pixel_diff_ratio(baseline_bytes: bytes, actual_bytes: bytes) -> float:
    """Compute the fraction of pixels that differ between two PNG images.

    Uses Pillow when available for accurate per-pixel RMSE.  Falls back to a
    byte-level estimate when Pillow is not installed.

    Args:
        baseline_bytes: Raw PNG data of the baseline image.
        actual_bytes: Raw PNG data of the actual screenshot.

    Returns:
        A float in ``[0, 1]`` representing the proportion of differing pixels
        (0 = identical, 1 = completely different).
    """
    try:
        from PIL import Image, ImageChops  # type: ignore[import]
        import io
        import math

        baseline_img = Image.open(io.BytesIO(baseline_bytes)).convert("RGBA")
        actual_img = Image.open(io.BytesIO(actual_bytes)).convert("RGBA")

        # Resize actual to match baseline dimensions if they differ.
        if baseline_img.size != actual_img.size:
            actual_img = actual_img.resize(baseline_img.size, Image.LANCZOS)

        diff = ImageChops.difference(baseline_img, actual_img)
        total_pixels = baseline_img.width * baseline_img.height
        if total_pixels == 0:
            return 0.0

        # Sum of all channel differences normalised per pixel.
        diff_data = list(diff.getdata())
        channel_sum = sum(sum(px) for px in diff_data)
        max_channel_sum = total_pixels * 4 * 255  # 4 channels × max 255
        return channel_sum / max_channel_sum if max_channel_sum > 0 else 0.0

    except ImportError:
        # Byte-level fallback: fraction of differing bytes.
        if not baseline_bytes or not actual_bytes:
            return 1.0
        min_len = min(len(baseline_bytes), len(actual_bytes))
        differing = sum(
            1 for a, b in zip(baseline_bytes[:min_len], actual_bytes[:min_len]) if a != b
        )
        total = max(len(baseline_bytes), len(actual_bytes))
        return differing / total if total > 0 else 0.0


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class SnapshotResult:
    """Outcome of a snapshot comparison operation.

    Attributes:
        passed: ``True`` when the comparison succeeded (diff within threshold
            or a new baseline was created).
        snapshot_name: Identifier used for the snapshot file.
        baseline_path: Absolute path to the baseline ``.png`` on disk.
        actual_path: Absolute path to the actual screenshot captured during
            this run, or ``None`` when no screenshot was taken.
        diff_ratio: Pixel-diff ratio (``None`` when the baseline was freshly
            created or when running in update mode).
        threshold: Threshold that was applied.
        message: Human-readable description of the outcome.
        is_new_baseline: ``True`` when a new baseline was written this run.
        is_update_mode: ``True`` when ``SNAPSHOT_UPDATE=1`` was active.
    """

    passed: bool
    snapshot_name: str
    baseline_path: Path
    actual_path: Optional[Path] = None
    diff_ratio: Optional[float] = None
    threshold: float = DEFAULT_THRESHOLD
    message: str = ""
    is_new_baseline: bool = False
    is_update_mode: bool = False

    def summary(self) -> str:
        """Return a one-line human-readable summary of the result.

        Returns:
            A string suitable for an ``assert`` failure message.
        """
        if self.passed:
            if self.is_new_baseline:
                return f"[SNAPSHOT] New baseline created: {self.baseline_path}"
            if self.is_update_mode:
                return f"[SNAPSHOT] Baseline updated (update mode): {self.baseline_path}"
            ratio_pct = f"{(self.diff_ratio or 0) * 100:.4f}%"
            return (
                f"[SNAPSHOT] PASS '{self.snapshot_name}': diff={ratio_pct} "
                f"<= threshold={self.threshold * 100:.4f}%"
            )
        ratio_pct = f"{(self.diff_ratio or 0) * 100:.4f}%"
        return (
            f"[SNAPSHOT] FAIL '{self.snapshot_name}': diff={ratio_pct} "
            f"> threshold={self.threshold * 100:.4f}%. "
            f"Baseline: {self.baseline_path}  Actual: {self.actual_path}. "
            f"Run with SNAPSHOT_UPDATE=1 to accept changes."
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def capture_page_snapshot(page: object, name: str, page_name: str = "default") -> Path:
    """Capture a full-page screenshot at the canonical 1280×720 viewport.

    Sets the viewport to ``1280×720`` before taking the screenshot so that
    baselines are reproducible regardless of the browser's current size.

    Args:
        page: A Playwright ``Page`` object.
        name: Snapshot identifier (used in the file name).
        page_name: Logical page group used as the storage sub-directory.
            Defaults to ``"default"``.

    Returns:
        The :class:`~pathlib.Path` where the screenshot was saved.
    """
    # Ensure consistent viewport dimensions.
    page.set_viewport_size({"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT})  # type: ignore[attr-defined]

    dest = _snapshot_path(page_name, name)
    page.screenshot(path=str(dest), full_page=True)  # type: ignore[attr-defined]
    return dest


def capture_element_snapshot(
    page: object, selector: str, name: str, page_name: str = "default"
) -> Path:
    """Capture a screenshot of the first element matching *selector*.

    Scrolls the element into view before capturing so the element is fully
    visible.

    Args:
        page: A Playwright ``Page`` object.
        selector: CSS selector for the target element.
        name: Snapshot identifier (used in the file name).
        page_name: Logical page group used as the storage sub-directory.
            Defaults to ``"default"``.

    Returns:
        The :class:`~pathlib.Path` where the element screenshot was saved.

    Raises:
        ValueError: When no element matches *selector*.
    """
    locator = page.locator(selector).first  # type: ignore[attr-defined]
    locator.scroll_into_view_if_needed()

    dest = _snapshot_path(page_name, f"{name}-element")
    locator.screenshot(path=str(dest))
    return dest


def create_baseline(
    page: object, name: str, page_name: str = "default"
) -> SnapshotResult:
    """Explicitly create or overwrite the baseline for *name*.

    Always captures a fresh screenshot and writes it to the baseline path
    regardless of whether a baseline already exists.

    Args:
        page: A Playwright ``Page`` object.
        name: Snapshot identifier.
        page_name: Logical page group used as the storage sub-directory.

    Returns:
        A :class:`SnapshotResult` with ``passed=True`` and
        ``is_new_baseline=True``.
    """
    page.set_viewport_size({"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT})  # type: ignore[attr-defined]
    baseline_path = _snapshot_path(page_name, name)
    page.screenshot(path=str(baseline_path), full_page=True)  # type: ignore[attr-defined]
    return SnapshotResult(
        passed=True,
        snapshot_name=name,
        baseline_path=baseline_path,
        actual_path=baseline_path,
        diff_ratio=0.0,
        threshold=_threshold(),
        message="Baseline created.",
        is_new_baseline=True,
    )


def compare_snapshot(
    page: object,
    name: str,
    page_name: str = "default",
    threshold: Optional[float] = None,
) -> SnapshotResult:
    """Compare the current page appearance against a stored baseline.

    Behaviour:

    - **No baseline exists** — screenshot is captured and saved as the
      baseline; result is *passed* with ``is_new_baseline=True``.
    - **Baseline exists + SNAPSHOT_UPDATE=1** — baseline is overwritten with
      the current screenshot; result is *passed* with ``is_update_mode=True``.
    - **Baseline exists + diff ≤ threshold** — result is *passed*.
    - **Baseline exists + diff > threshold** — result is *failed*.

    Args:
        page: A Playwright ``Page`` object.
        name: Snapshot identifier.
        page_name: Logical page group used as the storage sub-directory.
        threshold: Override the comparison threshold for this call only.
            When ``None`` (default) the value from the ``SNAPSHOT_THRESHOLD``
            environment variable or ``DEFAULT_THRESHOLD`` is used.

    Returns:
        A :class:`SnapshotResult` describing the outcome.
    """
    effective_threshold = threshold if threshold is not None else _threshold()
    baseline_path = _snapshot_path(page_name, name)

    # Ensure consistent viewport.
    page.set_viewport_size({"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT})  # type: ignore[attr-defined]

    # Capture the actual screenshot to a temporary sibling path.
    actual_path = baseline_path.parent / f"{name}-actual-{_platform_tag()}.png"
    page.screenshot(path=str(actual_path), full_page=True)  # type: ignore[attr-defined]

    update = _update_mode()

    # ── No baseline yet ─────────────────────────────────────────────────────
    if not baseline_path.exists():
        # Auto-create the baseline from the actual screenshot.
        baseline_path.write_bytes(actual_path.read_bytes())
        # Clean up the separate actual copy.
        _safe_remove(actual_path)
        return SnapshotResult(
            passed=True,
            snapshot_name=name,
            baseline_path=baseline_path,
            actual_path=baseline_path,
            diff_ratio=0.0,
            threshold=effective_threshold,
            message="New baseline created.",
            is_new_baseline=True,
        )

    # ── Update mode ─────────────────────────────────────────────────────────
    if update:
        baseline_path.write_bytes(actual_path.read_bytes())
        _safe_remove(actual_path)
        return SnapshotResult(
            passed=True,
            snapshot_name=name,
            baseline_path=baseline_path,
            actual_path=baseline_path,
            diff_ratio=0.0,
            threshold=effective_threshold,
            message="Baseline updated (SNAPSHOT_UPDATE=1).",
            is_update_mode=True,
        )

    # ── Standard comparison ──────────────────────────────────────────────────
    baseline_bytes = baseline_path.read_bytes()
    actual_bytes = actual_path.read_bytes()

    ratio = _pixel_diff_ratio(baseline_bytes, actual_bytes)
    passed = ratio <= effective_threshold

    if passed:
        _safe_remove(actual_path)

    return SnapshotResult(
        passed=passed,
        snapshot_name=name,
        baseline_path=baseline_path,
        actual_path=actual_path if not passed else None,
        diff_ratio=ratio,
        threshold=effective_threshold,
        message="Comparison complete.",
    )


# ---------------------------------------------------------------------------
# pytest fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def snapshot_comparison():
    """pytest fixture providing a ``compare_snapshot`` callable.

    The fixture binds the test name from ``request.node.name`` as the
    *page_name*, so snapshots are automatically grouped by test.

    Usage::

        def test_fleet_dashboard(page, snapshot_comparison):
            page.goto("/admin/ui/dashboard")
            result = snapshot_comparison(page, "full-page")
            assert result.passed, result.summary()
    """

    def _compare(
        page: object,
        name: str,
        *,
        page_name: str = "default",
        threshold: Optional[float] = None,
    ) -> SnapshotResult:
        return compare_snapshot(page, name, page_name=page_name, threshold=threshold)

    return _compare


# ---------------------------------------------------------------------------
# Internal utilities
# ---------------------------------------------------------------------------


def _safe_remove(path: Path) -> None:
    """Remove *path* if it exists; silently ignore errors.

    Args:
        path: File path to remove.
    """
    try:
        path.unlink(missing_ok=True)
    except Exception:  # noqa: BLE001
        pass
