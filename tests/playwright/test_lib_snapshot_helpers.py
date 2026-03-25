"""Unit tests for snapshot_helpers.py (Epic 58, Story 58.7).

All tests use ``unittest.mock.MagicMock`` to simulate a Playwright ``Page``
object — no live browser or filesystem writes are required (temporary
directories are used for isolation).

Test matrix:

- _platform_tag: returns recognised platform tokens
- _snapshot_path: directory is auto-created; file name includes platform tag
- _update_mode: env var parsing (0, 1, missing)
- _threshold: env var parsing (valid float, out-of-range, missing, invalid)
- _pixel_diff_ratio: identical bytes returns 0.0; fully-different returns > 0
- SnapshotResult.summary: new-baseline, update-mode, pass, fail variants
- capture_page_snapshot: viewport set, screenshot called, path returned
- capture_element_snapshot: locator.scroll + screenshot called, path returned
- create_baseline: always passes, is_new_baseline=True
- compare_snapshot (no baseline): auto-creates, passed=True, is_new_baseline=True
- compare_snapshot (update mode): overwrites baseline, passed=True, is_update_mode=True
- compare_snapshot (pass): diff <= threshold → passed=True
- compare_snapshot (fail): diff > threshold → passed=False, actual_path set
- compare_snapshot (custom threshold override): respects per-call threshold
- snapshot_comparison fixture: returns a callable that delegates to compare_snapshot
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, call, patch

import pytest

# Ensure the module can be imported without a live Playwright installation.
from tests.playwright.lib.snapshot_helpers import (
    DEFAULT_THRESHOLD,
    VIEWPORT_HEIGHT,
    VIEWPORT_WIDTH,
    SnapshotResult,
    _pixel_diff_ratio,
    _platform_tag,
    _threshold,
    _update_mode,
    capture_element_snapshot,
    capture_page_snapshot,
    compare_snapshot,
    create_baseline,
    snapshot_comparison,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_page(screenshot_bytes: bytes = b"PNG_DATA") -> MagicMock:
    """Return a MagicMock Playwright Page."""
    page = MagicMock()
    # page.screenshot writes bytes to path and returns None.
    def _screenshot_side_effect(path: str = "", full_page: bool = False, **_kw):
        if path:
            Path(path).write_bytes(screenshot_bytes)

    page.screenshot.side_effect = _screenshot_side_effect
    page.set_viewport_size.return_value = None

    # page.locator().first.screenshot writes bytes.
    locator_mock = MagicMock()
    locator_mock.scroll_into_view_if_needed.return_value = None

    def _element_screenshot(path: str = "", **_kw):
        if path:
            Path(path).write_bytes(screenshot_bytes)

    locator_mock.screenshot.side_effect = _element_screenshot
    page.locator.return_value.first = locator_mock
    return page


# ---------------------------------------------------------------------------
# _platform_tag
# ---------------------------------------------------------------------------


class TestPlatformTag:
    def test_linux(self):
        with patch.object(sys, "platform", "linux"):
            assert _platform_tag() == "linux"

    def test_darwin(self):
        with patch.object(sys, "platform", "darwin"):
            assert _platform_tag() == "darwin"

    def test_win32(self):
        with patch.object(sys, "platform", "win32"):
            assert _platform_tag() == "win32"

    def test_unknown_falls_back_to_linux(self):
        with patch.object(sys, "platform", "freebsd"):
            assert _platform_tag() == "linux"


# ---------------------------------------------------------------------------
# _update_mode
# ---------------------------------------------------------------------------


class TestUpdateMode:
    def test_not_set(self, monkeypatch):
        monkeypatch.delenv("SNAPSHOT_UPDATE", raising=False)
        assert _update_mode() is False

    def test_zero(self, monkeypatch):
        monkeypatch.setenv("SNAPSHOT_UPDATE", "0")
        assert _update_mode() is False

    def test_one(self, monkeypatch):
        monkeypatch.setenv("SNAPSHOT_UPDATE", "1")
        assert _update_mode() is True

    def test_whitespace(self, monkeypatch):
        monkeypatch.setenv("SNAPSHOT_UPDATE", " 1 ")
        assert _update_mode() is True

    def test_other_value(self, monkeypatch):
        monkeypatch.setenv("SNAPSHOT_UPDATE", "yes")
        assert _update_mode() is False


# ---------------------------------------------------------------------------
# _threshold
# ---------------------------------------------------------------------------


class TestThreshold:
    def test_default_when_not_set(self, monkeypatch):
        monkeypatch.delenv("SNAPSHOT_THRESHOLD", raising=False)
        assert _threshold() == DEFAULT_THRESHOLD

    def test_valid_float(self, monkeypatch):
        monkeypatch.setenv("SNAPSHOT_THRESHOLD", "0.005")
        assert _threshold() == pytest.approx(0.005)

    def test_zero(self, monkeypatch):
        monkeypatch.setenv("SNAPSHOT_THRESHOLD", "0.0")
        assert _threshold() == 0.0

    def test_one(self, monkeypatch):
        monkeypatch.setenv("SNAPSHOT_THRESHOLD", "1.0")
        assert _threshold() == 1.0

    def test_out_of_range_falls_back(self, monkeypatch):
        monkeypatch.setenv("SNAPSHOT_THRESHOLD", "1.5")
        assert _threshold() == DEFAULT_THRESHOLD

    def test_invalid_string_falls_back(self, monkeypatch):
        monkeypatch.setenv("SNAPSHOT_THRESHOLD", "high")
        assert _threshold() == DEFAULT_THRESHOLD

    def test_empty_string_falls_back(self, monkeypatch):
        monkeypatch.setenv("SNAPSHOT_THRESHOLD", "")
        assert _threshold() == DEFAULT_THRESHOLD


# ---------------------------------------------------------------------------
# _pixel_diff_ratio
# ---------------------------------------------------------------------------


class TestPixelDiffRatio:
    def test_identical_bytes(self):
        data = b"\x00\x01\x02\x03" * 100
        assert _pixel_diff_ratio(data, data) == 0.0

    def test_completely_different(self):
        baseline = bytes([0x00] * 200)
        actual = bytes([0xFF] * 200)
        ratio = _pixel_diff_ratio(baseline, actual)
        assert ratio > 0.0

    def test_empty_inputs(self):
        ratio = _pixel_diff_ratio(b"", b"")
        assert ratio == 0.0 or ratio == 1.0  # either is acceptable for empty data

    def test_ratio_bounded_0_to_1(self):
        ratio = _pixel_diff_ratio(b"\xAA" * 50, b"\x55" * 50)
        assert 0.0 <= ratio <= 1.0


# ---------------------------------------------------------------------------
# SnapshotResult.summary
# ---------------------------------------------------------------------------


class TestSnapshotResultSummary:
    def test_new_baseline_summary(self, tmp_path):
        result = SnapshotResult(
            passed=True,
            snapshot_name="test",
            baseline_path=tmp_path / "test-linux.png",
            is_new_baseline=True,
        )
        assert "New baseline" in result.summary()
        assert "test-linux.png" in result.summary()

    def test_update_mode_summary(self, tmp_path):
        result = SnapshotResult(
            passed=True,
            snapshot_name="test",
            baseline_path=tmp_path / "test-linux.png",
            is_update_mode=True,
        )
        assert "updated" in result.summary().lower()

    def test_pass_summary(self, tmp_path):
        result = SnapshotResult(
            passed=True,
            snapshot_name="test",
            baseline_path=tmp_path / "test-linux.png",
            diff_ratio=0.0001,
            threshold=0.001,
        )
        summary = result.summary()
        assert "PASS" in summary
        assert "test" in summary

    def test_fail_summary(self, tmp_path):
        actual = tmp_path / "test-actual-linux.png"
        result = SnapshotResult(
            passed=False,
            snapshot_name="test",
            baseline_path=tmp_path / "test-linux.png",
            actual_path=actual,
            diff_ratio=0.05,
            threshold=0.001,
        )
        summary = result.summary()
        assert "FAIL" in summary
        assert "SNAPSHOT_UPDATE=1" in summary


# ---------------------------------------------------------------------------
# capture_page_snapshot
# ---------------------------------------------------------------------------


class TestCapturePageSnapshot:
    def test_sets_viewport(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "tests.playwright.lib.snapshot_helpers.SNAPSHOTS_DIR", tmp_path
        )
        page = _make_page()
        capture_page_snapshot(page, "full-page", page_name="dashboard")
        page.set_viewport_size.assert_called_once_with(
            {"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT}
        )

    def test_calls_screenshot(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "tests.playwright.lib.snapshot_helpers.SNAPSHOTS_DIR", tmp_path
        )
        page = _make_page()
        result_path = capture_page_snapshot(page, "full-page", page_name="dashboard")
        page.screenshot.assert_called_once()
        call_kwargs = page.screenshot.call_args[1]
        assert call_kwargs.get("full_page") is True
        assert "full-page" in call_kwargs.get("path", "")

    def test_returns_path(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "tests.playwright.lib.snapshot_helpers.SNAPSHOTS_DIR", tmp_path
        )
        page = _make_page()
        result_path = capture_page_snapshot(page, "full-page", page_name="dashboard")
        assert isinstance(result_path, Path)
        assert "full-page" in str(result_path)


# ---------------------------------------------------------------------------
# capture_element_snapshot
# ---------------------------------------------------------------------------


class TestCaptureElementSnapshot:
    def test_scrolls_into_view(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "tests.playwright.lib.snapshot_helpers.SNAPSHOTS_DIR", tmp_path
        )
        page = _make_page()
        capture_element_snapshot(page, ".sidebar", "sidebar", page_name="dashboard")
        page.locator.return_value.first.scroll_into_view_if_needed.assert_called_once()

    def test_calls_element_screenshot(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "tests.playwright.lib.snapshot_helpers.SNAPSHOTS_DIR", tmp_path
        )
        page = _make_page()
        result_path = capture_element_snapshot(
            page, ".sidebar", "sidebar", page_name="dashboard"
        )
        page.locator.return_value.first.screenshot.assert_called_once()

    def test_returns_path(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "tests.playwright.lib.snapshot_helpers.SNAPSHOTS_DIR", tmp_path
        )
        page = _make_page()
        result_path = capture_element_snapshot(
            page, ".sidebar", "sidebar", page_name="dashboard"
        )
        assert isinstance(result_path, Path)
        assert "sidebar-element" in str(result_path)


# ---------------------------------------------------------------------------
# create_baseline
# ---------------------------------------------------------------------------


class TestCreateBaseline:
    def test_always_passes(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "tests.playwright.lib.snapshot_helpers.SNAPSHOTS_DIR", tmp_path
        )
        page = _make_page()
        result = create_baseline(page, "full-page", page_name="dashboard")
        assert result.passed is True

    def test_is_new_baseline_flag(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "tests.playwright.lib.snapshot_helpers.SNAPSHOTS_DIR", tmp_path
        )
        page = _make_page()
        result = create_baseline(page, "full-page", page_name="dashboard")
        assert result.is_new_baseline is True

    def test_diff_ratio_is_zero(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "tests.playwright.lib.snapshot_helpers.SNAPSHOTS_DIR", tmp_path
        )
        page = _make_page()
        result = create_baseline(page, "full-page", page_name="dashboard")
        assert result.diff_ratio == 0.0

    def test_overwrites_existing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "tests.playwright.lib.snapshot_helpers.SNAPSHOTS_DIR", tmp_path
        )
        page1 = _make_page(b"OLD_DATA")
        result1 = create_baseline(page1, "page", page_name="test-page")
        assert result1.baseline_path.read_bytes() == b"OLD_DATA"

        page2 = _make_page(b"NEW_DATA")
        result2 = create_baseline(page2, "page", page_name="test-page")
        assert result2.baseline_path.read_bytes() == b"NEW_DATA"


# ---------------------------------------------------------------------------
# compare_snapshot — no baseline (auto-create)
# ---------------------------------------------------------------------------


class TestCompareSnapshotNoBaseline:
    def test_auto_creates_baseline(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "tests.playwright.lib.snapshot_helpers.SNAPSHOTS_DIR", tmp_path
        )
        monkeypatch.delenv("SNAPSHOT_UPDATE", raising=False)
        page = _make_page()
        result = compare_snapshot(page, "full-page", page_name="new-page")
        assert result.passed is True
        assert result.is_new_baseline is True

    def test_baseline_file_created_on_disk(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "tests.playwright.lib.snapshot_helpers.SNAPSHOTS_DIR", tmp_path
        )
        monkeypatch.delenv("SNAPSHOT_UPDATE", raising=False)
        page = _make_page(b"SCREENSHOT_DATA")
        result = compare_snapshot(page, "full-page", page_name="new-page")
        assert result.baseline_path.exists()
        assert result.baseline_path.read_bytes() == b"SCREENSHOT_DATA"

    def test_diff_ratio_is_zero(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "tests.playwright.lib.snapshot_helpers.SNAPSHOTS_DIR", tmp_path
        )
        monkeypatch.delenv("SNAPSHOT_UPDATE", raising=False)
        page = _make_page()
        result = compare_snapshot(page, "full-page", page_name="new-page")
        assert result.diff_ratio == 0.0


# ---------------------------------------------------------------------------
# compare_snapshot — update mode
# ---------------------------------------------------------------------------


class TestCompareSnapshotUpdateMode:
    def test_update_mode_passes(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "tests.playwright.lib.snapshot_helpers.SNAPSHOTS_DIR", tmp_path
        )
        monkeypatch.setenv("SNAPSHOT_UPDATE", "1")

        # Create an existing baseline.
        page = _make_page(b"OLD")
        (tmp_path / "upd-page").mkdir(parents=True, exist_ok=True)
        tag = _platform_tag()
        (tmp_path / "upd-page" / f"full-page-{tag}.png").write_bytes(b"OLD")

        page2 = _make_page(b"NEW")
        result = compare_snapshot(page2, "full-page", page_name="upd-page")
        assert result.passed is True
        assert result.is_update_mode is True

    def test_update_mode_overwrites_baseline(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "tests.playwright.lib.snapshot_helpers.SNAPSHOTS_DIR", tmp_path
        )
        monkeypatch.setenv("SNAPSHOT_UPDATE", "1")

        tag = _platform_tag()
        (tmp_path / "upd-page2").mkdir(parents=True, exist_ok=True)
        (tmp_path / "upd-page2" / f"full-page-{tag}.png").write_bytes(b"OLD_BYTES")

        page = _make_page(b"NEW_BYTES")
        result = compare_snapshot(page, "full-page", page_name="upd-page2")
        assert result.baseline_path.read_bytes() == b"NEW_BYTES"


# ---------------------------------------------------------------------------
# compare_snapshot — standard comparison (pass / fail)
# ---------------------------------------------------------------------------


class TestCompareSnapshotComparison:
    def _seed_baseline(self, snapshots_dir: Path, page_name: str, name: str, data: bytes):
        tag = _platform_tag()
        d = snapshots_dir / page_name
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{name}-{tag}.png").write_bytes(data)

    def test_identical_screenshot_passes(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "tests.playwright.lib.snapshot_helpers.SNAPSHOTS_DIR", tmp_path
        )
        monkeypatch.delenv("SNAPSHOT_UPDATE", raising=False)
        self._seed_baseline(tmp_path, "pg", "snap", b"SAME_DATA")

        page = _make_page(b"SAME_DATA")
        result = compare_snapshot(page, "snap", page_name="pg")
        assert result.passed is True

    def test_diff_above_threshold_fails(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "tests.playwright.lib.snapshot_helpers.SNAPSHOTS_DIR", tmp_path
        )
        monkeypatch.delenv("SNAPSHOT_UPDATE", raising=False)
        monkeypatch.setenv("SNAPSHOT_THRESHOLD", "0.0")  # zero tolerance

        self._seed_baseline(tmp_path, "pg2", "snap", b"\x00" * 100)

        page = _make_page(b"\xFF" * 100)
        result = compare_snapshot(page, "snap", page_name="pg2")
        assert result.passed is False
        assert result.diff_ratio is not None
        assert result.diff_ratio > 0

    def test_failed_result_includes_actual_path(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "tests.playwright.lib.snapshot_helpers.SNAPSHOTS_DIR", tmp_path
        )
        monkeypatch.delenv("SNAPSHOT_UPDATE", raising=False)
        monkeypatch.setenv("SNAPSHOT_THRESHOLD", "0.0")

        self._seed_baseline(tmp_path, "pg3", "snap", b"\x00" * 50)
        page = _make_page(b"\xFF" * 50)
        result = compare_snapshot(page, "snap", page_name="pg3")
        assert result.actual_path is not None

    def test_custom_threshold_override(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "tests.playwright.lib.snapshot_helpers.SNAPSHOTS_DIR", tmp_path
        )
        monkeypatch.delenv("SNAPSHOT_UPDATE", raising=False)
        self._seed_baseline(tmp_path, "pg4", "snap", b"\x00" * 100)

        page = _make_page(b"\xFF" * 100)
        # With threshold=1.0 (100% allowed) it should pass regardless of diff.
        result = compare_snapshot(page, "snap", page_name="pg4", threshold=1.0)
        assert result.passed is True
        assert result.threshold == 1.0

    def test_passed_result_cleans_up_actual_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "tests.playwright.lib.snapshot_helpers.SNAPSHOTS_DIR", tmp_path
        )
        monkeypatch.delenv("SNAPSHOT_UPDATE", raising=False)
        self._seed_baseline(tmp_path, "pg5", "snap", b"SAME_DATA")

        page = _make_page(b"SAME_DATA")
        result = compare_snapshot(page, "snap", page_name="pg5")
        assert result.passed is True
        # actual_path is None when test passes (file was cleaned up).
        assert result.actual_path is None


# ---------------------------------------------------------------------------
# snapshot_comparison fixture
# ---------------------------------------------------------------------------


def test_snapshot_comparison_fixture_returns_callable(snapshot_comparison):
    """snapshot_comparison fixture yields a callable."""
    assert callable(snapshot_comparison)


def test_snapshot_comparison_fixture_delegates_to_compare_snapshot(
    snapshot_comparison, tmp_path, monkeypatch
):
    """snapshot_comparison fixture callable creates baseline on first use."""
    monkeypatch.setattr(
        "tests.playwright.lib.snapshot_helpers.SNAPSHOTS_DIR", tmp_path
    )
    monkeypatch.delenv("SNAPSHOT_UPDATE", raising=False)
    page = _make_page()
    result = snapshot_comparison(page, "full-page", page_name="fixture-test")
    assert isinstance(result, SnapshotResult)
    assert result.is_new_baseline is True
