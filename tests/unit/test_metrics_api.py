"""Tests for Metrics APIs — single-pass, loopbacks, reopen (Stories 5.4, 5.5)."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

import pytest

from src.admin.metrics import (
    LoopbackMetrics,
    MetricsService,
    ReopenMetrics,
    SinglePassMetrics,
)
from src.outcome.models import OutcomeSignal, SignalEvent
from src.outcome.reopen import ReopenClassification, ReopenOutcome, ReopenSource


@pytest.fixture(autouse=True)
def _clean_stores():
    """Clean outcome stores before each test."""
    from src.outcome.ingestor import clear as clear_ingestor
    from src.outcome.reopen import clear as clear_reopen

    clear_ingestor()
    clear_reopen()
    yield
    clear_ingestor()
    clear_reopen()


def _make_signal(
    event: SignalEvent,
    repo_id: str = "repo-1",
    correlation_id=None,
    hours_ago: int = 0,
) -> OutcomeSignal:
    """Create a test signal."""
    return OutcomeSignal(
        event=event,
        taskpacket_id=uuid4(),
        correlation_id=correlation_id or uuid4(),
        timestamp=datetime.now(UTC) - timedelta(hours=hours_ago),
        payload={"repo_id": repo_id},
    )


class TestSinglePassMetrics:
    """Tests for single-pass success rate computation."""

    def test_empty_signals(self):
        svc = MetricsService()
        result = svc.get_single_pass()
        assert result.total_workflows_7d == 0
        assert result.overall_rate_7d == 0.0

    def test_all_success(self):
        corr1 = uuid4()
        corr2 = uuid4()
        signals = [
            _make_signal(SignalEvent.VERIFICATION_PASSED, correlation_id=corr1),
            _make_signal(SignalEvent.QA_PASSED, correlation_id=corr1),
            _make_signal(SignalEvent.VERIFICATION_PASSED, correlation_id=corr2),
            _make_signal(SignalEvent.QA_PASSED, correlation_id=corr2),
        ]
        with patch("src.admin.metrics.get_signals", return_value=signals):
            svc = MetricsService()
            result = svc.get_single_pass()
            assert result.total_workflows_7d == 2
            assert result.successful_7d == 2
            assert result.overall_rate_7d == 1.0

    def test_mixed_success_failure(self):
        corr1 = uuid4()
        corr2 = uuid4()
        signals = [
            _make_signal(SignalEvent.VERIFICATION_PASSED, correlation_id=corr1),
            _make_signal(SignalEvent.QA_PASSED, correlation_id=corr1),
            _make_signal(SignalEvent.VERIFICATION_FAILED, correlation_id=corr2),
            _make_signal(SignalEvent.VERIFICATION_PASSED, correlation_id=corr2),
        ]
        with patch("src.admin.metrics.get_signals", return_value=signals):
            svc = MetricsService()
            result = svc.get_single_pass()
            assert result.total_workflows_7d == 2
            assert result.successful_7d == 1
            assert result.overall_rate_7d == 0.5

    def test_repo_filter(self):
        corr1 = uuid4()
        corr2 = uuid4()
        signals = [
            _make_signal(SignalEvent.VERIFICATION_PASSED, repo_id="repo-1", correlation_id=corr1),
            _make_signal(SignalEvent.VERIFICATION_PASSED, repo_id="repo-2", correlation_id=corr2),
        ]
        with patch("src.admin.metrics.get_signals", return_value=signals):
            svc = MetricsService()
            result = svc.get_single_pass(repo_filter="repo-1")
            assert result.total_workflows_7d == 1

    def test_time_windows(self):
        corr1 = uuid4()
        corr2 = uuid4()
        signals = [
            _make_signal(SignalEvent.VERIFICATION_PASSED, correlation_id=corr1, hours_ago=24),
            _make_signal(SignalEvent.VERIFICATION_PASSED, correlation_id=corr2, hours_ago=24 * 20),
        ]
        with patch("src.admin.metrics.get_signals", return_value=signals):
            svc = MetricsService()
            result = svc.get_single_pass()
            assert result.total_workflows_7d == 1
            assert result.total_workflows_30d == 2

    def test_to_dict(self):
        metrics = SinglePassMetrics(
            overall_rate_7d=0.75, total_workflows_7d=4, successful_7d=3,
        )
        d = metrics.to_dict()
        assert d["overall_rate_7d"] == 0.75
        assert d["total_workflows_7d"] == 4


class TestLoopbackMetrics:
    """Tests for verification loopback breakdown."""

    def test_empty_signals(self):
        svc = MetricsService()
        result = svc.get_loopbacks()
        assert result.total_loopbacks == 0

    def test_categorized_loopbacks(self):
        signals = [
            OutcomeSignal(
                event=SignalEvent.VERIFICATION_FAILED,
                taskpacket_id=uuid4(),
                correlation_id=uuid4(),
                timestamp=datetime.now(UTC),
                payload={"repo_id": "repo-1", "step": "verify_lint"},
            ),
            OutcomeSignal(
                event=SignalEvent.VERIFICATION_FAILED,
                taskpacket_id=uuid4(),
                correlation_id=uuid4(),
                timestamp=datetime.now(UTC),
                payload={"repo_id": "repo-1", "step": "verify_test"},
            ),
            OutcomeSignal(
                event=SignalEvent.VERIFICATION_FAILED,
                taskpacket_id=uuid4(),
                correlation_id=uuid4(),
                timestamp=datetime.now(UTC),
                payload={"repo_id": "repo-1", "step": "verify_security"},
            ),
        ]
        with patch("src.admin.metrics.get_signals", return_value=signals):
            svc = MetricsService()
            result = svc.get_loopbacks()
            assert result.total_loopbacks == 3
            cats = {c.category: c.count for c in result.categories}
            assert cats["lint"] == 1
            assert cats["test"] == 1
            assert cats["security"] == 1

    def test_other_category(self):
        signals = [
            OutcomeSignal(
                event=SignalEvent.VERIFICATION_FAILED,
                taskpacket_id=uuid4(),
                correlation_id=uuid4(),
                timestamp=datetime.now(UTC),
                payload={"repo_id": "repo-1", "step": "verify_custom"},
            ),
        ]
        with patch("src.admin.metrics.get_signals", return_value=signals):
            svc = MetricsService()
            result = svc.get_loopbacks()
            cats = {c.category: c.count for c in result.categories}
            assert cats["other"] == 1

    def test_repo_filter(self):
        signals = [
            OutcomeSignal(
                event=SignalEvent.VERIFICATION_FAILED,
                taskpacket_id=uuid4(),
                correlation_id=uuid4(),
                timestamp=datetime.now(UTC),
                payload={"repo_id": "repo-1", "step": "verify_lint"},
            ),
            OutcomeSignal(
                event=SignalEvent.VERIFICATION_FAILED,
                taskpacket_id=uuid4(),
                correlation_id=uuid4(),
                timestamp=datetime.now(UTC),
                payload={"repo_id": "repo-2", "step": "verify_test"},
            ),
        ]
        with patch("src.admin.metrics.get_signals", return_value=signals):
            svc = MetricsService()
            result = svc.get_loopbacks(repo_filter="repo-1")
            assert result.total_loopbacks == 1

    def test_to_dict(self):
        metrics = LoopbackMetrics(total_loopbacks=5)
        d = metrics.to_dict()
        assert d["total_loopbacks"] == 5


class TestReopenMetrics:
    """Tests for reopen rate and attribution."""

    def test_no_reopen_data(self):
        svc = MetricsService()
        result = svc.get_reopen()
        assert result.total_reopened == 0
        assert result.note is not None

    def test_with_reopen_outcomes(self):
        outcomes = [
            ReopenOutcome(
                event_id=uuid4(), source=ReopenSource.ISSUE_REOPENED,
                classification=ReopenClassification.INTENT_GAP,
                repo_id="repo-1",
            ),
            ReopenOutcome(
                event_id=uuid4(), source=ReopenSource.REGRESSION_ISSUE,
                classification=ReopenClassification.REGRESSION,
                repo_id="repo-1",
            ),
            ReopenOutcome(
                event_id=uuid4(), source=ReopenSource.ISSUE_REOPENED,
                classification=ReopenClassification.IMPLEMENTATION_BUG,
                repo_id="repo-2",
            ),
        ]
        with patch("src.admin.metrics.get_reopen_outcomes", return_value=outcomes):
            svc = MetricsService()
            result = svc.get_reopen()
            assert result.total_reopened == 3
            assert result.attribution["intent_gap"] == 1
            assert result.attribution["regression"] == 1
            assert result.attribution["implementation_bug"] == 1
            assert result.note is None

    def test_repo_filter(self):
        outcomes = [
            ReopenOutcome(
                event_id=uuid4(), source=ReopenSource.ISSUE_REOPENED,
                classification=ReopenClassification.INTENT_GAP,
                repo_id="repo-1",
            ),
            ReopenOutcome(
                event_id=uuid4(), source=ReopenSource.ISSUE_REOPENED,
                classification=ReopenClassification.REGRESSION,
                repo_id="repo-2",
            ),
        ]
        with patch("src.admin.metrics.get_reopen_outcomes", return_value=outcomes):
            svc = MetricsService()
            result = svc.get_reopen(repo_filter="repo-1")
            assert result.total_reopened == 1

    def test_to_dict_with_note(self):
        metrics = ReopenMetrics(note="No data")
        d = metrics.to_dict()
        assert d["note"] == "No data"
        assert d["reopen_rate"] == 0.0

    def test_to_dict_without_note(self):
        metrics = ReopenMetrics(total_reopened=5, reopen_rate=0.1)
        d = metrics.to_dict()
        assert "note" not in d
