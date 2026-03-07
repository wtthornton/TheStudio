"""Tests for Success Gate Service (Story 6.6)."""

from unittest.mock import patch

from src.admin.metrics import LoopbackEntry, LoopbackMetrics, SinglePassMetrics
from src.admin.success_gate import SuccessGateResult, SuccessGateService


def _mock_single_pass(rate, total):
    return SinglePassMetrics(
        overall_rate_30d=rate,
        total_workflows_30d=total,
        successful_30d=int(total * rate),
    )


def _mock_loopbacks(lint=2, test=3, security=1, other=1):
    total = lint + test + security + other
    return LoopbackMetrics(
        total_loopbacks=total,
        categories=[
            LoopbackEntry(category="lint", count=lint, percentage=lint / total * 100 if total else 0),
            LoopbackEntry(category="test", count=test, percentage=test / total * 100 if total else 0),
            LoopbackEntry(category="security", count=security, percentage=security / total * 100 if total else 0),
            LoopbackEntry(category="other", count=other, percentage=other / total * 100 if total else 0),
        ],
    )


class TestSuccessGateService:
    """Tests for SuccessGateService.check()."""

    def test_gate_passes_above_threshold(self):
        svc = SuccessGateService()
        with (
            patch("src.admin.success_gate.get_metrics_service") as mock_ms,
        ):
            mock_ms.return_value.get_single_pass.return_value = _mock_single_pass(0.75, 20)
            mock_ms.return_value.get_loopbacks.return_value = _mock_loopbacks()
            result = svc.check(threshold=0.60)

        assert result.met is True
        assert result.current_rate == 0.75
        assert result.insufficient_data is False

    def test_gate_fails_below_threshold(self):
        svc = SuccessGateService()
        with patch("src.admin.success_gate.get_metrics_service") as mock_ms:
            mock_ms.return_value.get_single_pass.return_value = _mock_single_pass(0.45, 20)
            mock_ms.return_value.get_loopbacks.return_value = _mock_loopbacks()
            result = svc.check(threshold=0.60)

        assert result.met is False
        assert result.current_rate == 0.45

    def test_gate_passes_at_exactly_threshold(self):
        svc = SuccessGateService()
        with patch("src.admin.success_gate.get_metrics_service") as mock_ms:
            mock_ms.return_value.get_single_pass.return_value = _mock_single_pass(0.60, 20)
            mock_ms.return_value.get_loopbacks.return_value = _mock_loopbacks()
            result = svc.check(threshold=0.60)

        assert result.met is True

    def test_insufficient_data_passes(self):
        svc = SuccessGateService()
        with patch("src.admin.success_gate.get_metrics_service") as mock_ms:
            mock_ms.return_value.get_single_pass.return_value = _mock_single_pass(0.33, 3)
            mock_ms.return_value.get_loopbacks.return_value = _mock_loopbacks()
            result = svc.check(threshold=0.60, min_samples=10)

        assert result.met is True
        assert result.insufficient_data is True
        assert result.sample_count == 3

    def test_category_breakdown_included(self):
        svc = SuccessGateService()
        with patch("src.admin.success_gate.get_metrics_service") as mock_ms:
            mock_ms.return_value.get_single_pass.return_value = _mock_single_pass(0.50, 20)
            mock_ms.return_value.get_loopbacks.return_value = _mock_loopbacks(lint=5, test=3, security=1, other=1)
            result = svc.check()

        assert result.category_breakdown["lint"] == 5
        assert result.category_breakdown["test"] == 3

    def test_custom_threshold(self):
        svc = SuccessGateService()
        with patch("src.admin.success_gate.get_metrics_service") as mock_ms:
            mock_ms.return_value.get_single_pass.return_value = _mock_single_pass(0.55, 20)
            mock_ms.return_value.get_loopbacks.return_value = _mock_loopbacks()
            result = svc.check(threshold=0.50)

        assert result.met is True
        assert result.threshold == 0.50

    def test_repo_filter_passed_through(self):
        svc = SuccessGateService()
        with patch("src.admin.success_gate.get_metrics_service") as mock_ms:
            mock_ms.return_value.get_single_pass.return_value = _mock_single_pass(0.70, 15)
            mock_ms.return_value.get_loopbacks.return_value = _mock_loopbacks()
            result = svc.check(repo_filter="my-repo")

        mock_ms.return_value.get_single_pass.assert_called_once_with(repo_filter="my-repo")
        mock_ms.return_value.get_loopbacks.assert_called_once_with(repo_filter="my-repo")

    def test_to_dict(self):
        result = SuccessGateResult(
            met=True, current_rate=0.75, threshold=0.60,
            sample_count=20, window_days=28,
            category_breakdown={"lint": 2, "test": 3},
        )
        d = result.to_dict()
        assert d["met"] is True
        assert d["current_rate"] == 0.75
        assert d["threshold"] == 0.60
        assert d["sample_count"] == 20
        assert d["window_days"] == 28
        assert d["insufficient_data"] is False
        assert d["category_breakdown"]["lint"] == 2
