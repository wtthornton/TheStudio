"""Unit tests for src/admin/model_spend.py — Epic 10 AC4."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from src.admin.model_gateway import ModelCallAudit
from src.admin.model_spend import (
    SpendReport,
    SpendSummary,
    _aggregate,
    get_spend_report,
)


def _make_audit(
    provider: str = "openai",
    model: str = "gpt-4",
    step: str = "intent",
    cost: float = 0.01,
    tokens_in: int = 100,
    tokens_out: int = 50,
    latency_ms: float = 200.0,
    error_class: str | None = None,
    created_at: datetime | None = None,
) -> ModelCallAudit:
    return ModelCallAudit(
        provider=provider,
        model=model,
        step=step,
        cost=cost,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        latency_ms=latency_ms,
        error_class=error_class,
        created_at=created_at or datetime.now(UTC),
    )


class TestSpendSummary:
    def test_to_dict(self):
        s = SpendSummary(
            key="openai",
            total_cost=0.123456789,
            total_tokens_in=1000,
            total_tokens_out=500,
            call_count=10,
            avg_latency_ms=150.123,
            error_count=1,
        )
        d = s.to_dict()
        assert d["key"] == "openai"
        assert d["total_cost"] == 0.123457  # rounded to 6
        assert d["total_tokens"] == 1500
        assert d["avg_latency_ms"] == 150.1  # rounded to 1
        assert d["error_count"] == 1

    def test_defaults(self):
        s = SpendSummary(key="test")
        assert s.total_cost == 0.0
        assert s.call_count == 0


class TestSpendReport:
    def test_to_dict_empty(self):
        r = SpendReport(window_hours=48)
        d = r.to_dict()
        assert d["total_cost"] == 0.0
        assert d["total_calls"] == 0
        assert d["by_provider"] == []
        assert d["window_hours"] == 48


class TestAggregate:
    def test_empty_records(self):
        assert _aggregate([], lambda r: r.provider) == []

    def test_single_group(self):
        records = [_make_audit(cost=0.01), _make_audit(cost=0.02)]
        result = _aggregate(records, lambda r: r.provider)
        assert len(result) == 1
        assert result[0].key == "openai"
        assert result[0].total_cost == pytest.approx(0.03)
        assert result[0].call_count == 2

    def test_multiple_groups(self):
        records = [
            _make_audit(provider="openai", cost=0.05),
            _make_audit(provider="anthropic", cost=0.10),
            _make_audit(provider="openai", cost=0.03),
        ]
        result = _aggregate(records, lambda r: r.provider)
        # Sorted by cost desc: anthropic (0.10) > openai (0.08)
        assert result[0].key == "anthropic"
        assert result[0].total_cost == pytest.approx(0.10)
        assert result[1].key == "openai"
        assert result[1].total_cost == pytest.approx(0.08)

    def test_tokens_aggregation(self):
        records = [
            _make_audit(tokens_in=100, tokens_out=50),
            _make_audit(tokens_in=200, tokens_out=100),
        ]
        result = _aggregate(records, lambda r: r.provider)
        assert result[0].total_tokens_in == 300
        assert result[0].total_tokens_out == 150

    def test_avg_latency_excludes_zero(self):
        records = [
            _make_audit(latency_ms=100.0),
            _make_audit(latency_ms=0.0),
            _make_audit(latency_ms=200.0),
        ]
        result = _aggregate(records, lambda r: r.provider)
        assert result[0].avg_latency_ms == pytest.approx(150.0)

    def test_error_counting(self):
        records = [
            _make_audit(error_class=None),
            _make_audit(error_class="rate_limit"),
            _make_audit(error_class="timeout"),
        ]
        result = _aggregate(records, lambda r: r.provider)
        assert result[0].error_count == 2

    def test_group_by_step(self):
        records = [
            _make_audit(step="intent", cost=0.01),
            _make_audit(step="qa", cost=0.02),
            _make_audit(step="intent", cost=0.03),
        ]
        result = _aggregate(records, lambda r: r.step or "unknown")
        keys = [s.key for s in result]
        assert "intent" in keys
        assert "qa" in keys


class TestGetSpendReport:
    @patch("src.admin.model_spend.get_model_audit_store")
    def test_empty_store(self, mock_get_store):
        mock_store = MagicMock()
        mock_store.query.return_value = []
        mock_get_store.return_value = mock_store

        report = get_spend_report(window_hours=24)
        assert report.total_cost == 0.0
        assert report.total_calls == 0
        assert report.window_hours == 24

    @patch("src.admin.model_spend.get_model_audit_store")
    def test_filters_by_window(self, mock_get_store):
        now = datetime.now(UTC)
        old = now - timedelta(hours=48)

        mock_store = MagicMock()
        mock_store.query.return_value = [
            _make_audit(cost=0.10, created_at=now),
            _make_audit(cost=0.05, created_at=old),  # Outside window
        ]
        mock_get_store.return_value = mock_store

        report = get_spend_report(window_hours=24)
        assert report.total_cost == pytest.approx(0.10)
        assert report.total_calls == 1

    @patch("src.admin.model_spend.get_model_audit_store")
    def test_breakdowns_populated(self, mock_get_store):
        now = datetime.now(UTC)
        mock_store = MagicMock()
        mock_store.query.return_value = [
            _make_audit(provider="openai", model="gpt-4", step="intent", cost=0.05, created_at=now),
            _make_audit(provider="anthropic", model="claude", step="qa", cost=0.03, created_at=now),
        ]
        mock_get_store.return_value = mock_store

        report = get_spend_report()
        assert len(report.by_provider) == 2
        assert len(report.by_step) == 2
        assert len(report.by_model) == 2
        assert report.total_cost == pytest.approx(0.08)
        assert report.total_calls == 2
