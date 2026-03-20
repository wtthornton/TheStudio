"""Unit tests for src/admin/model_spend.py — Epic 10 AC4."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from src.admin.model_gateway import ModelCallAudit
from src.admin.model_spend import (
    SpendReport,
    SpendSummary,
    TierBudgetUtilization,
    _aggregate,
    get_budget_utilization,
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
    cache_creation_tokens: int = 0,
    cache_read_tokens: int = 0,
    repo: str = "",
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
        cache_creation_tokens=cache_creation_tokens,
        cache_read_tokens=cache_read_tokens,
        repo=repo,
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


class TestCacheMetrics:
    """Epic 32, Stories 32.10-32.11: Cache token tracking and hit rate."""

    def test_spend_report_cache_defaults(self):
        r = SpendReport()
        assert r.total_cache_creation_tokens == 0
        assert r.total_cache_read_tokens == 0
        assert r.cache_hit_rate == 0.0

    def test_spend_report_cache_in_dict(self):
        r = SpendReport(
            total_cache_creation_tokens=1000,
            total_cache_read_tokens=800,
            cache_hit_rate=0.4444,
        )
        d = r.to_dict()
        assert d["total_cache_creation_tokens"] == 1000
        assert d["total_cache_read_tokens"] == 800
        assert d["cache_hit_rate"] == 0.4444

    @patch("src.admin.model_spend.get_model_audit_store")
    def test_cache_hit_rate_computed(self, mock_get_store):
        now = datetime.now(UTC)
        mock_store = MagicMock()
        mock_store.query.return_value = [
            _make_audit(
                cost=0.01, created_at=now,
                cache_creation_tokens=1000, cache_read_tokens=0,
            ),
            _make_audit(
                cost=0.01, created_at=now,
                cache_creation_tokens=0, cache_read_tokens=1000,
            ),
        ]
        mock_get_store.return_value = mock_store

        report = get_spend_report()
        assert report.total_cache_creation_tokens == 1000
        assert report.total_cache_read_tokens == 1000
        # 1000 read / (1000 creation + 1000 read) = 0.5
        assert report.cache_hit_rate == pytest.approx(0.5)

    @patch("src.admin.model_spend.get_model_audit_store")
    def test_cache_hit_rate_zero_when_no_cache(self, mock_get_store):
        now = datetime.now(UTC)
        mock_store = MagicMock()
        mock_store.query.return_value = [
            _make_audit(cost=0.01, created_at=now),
        ]
        mock_get_store.return_value = mock_store

        report = get_spend_report()
        assert report.cache_hit_rate == 0.0

    @patch("src.admin.model_spend.get_model_audit_store")
    def test_cache_hit_rate_high_when_all_cached(self, mock_get_store):
        now = datetime.now(UTC)
        mock_store = MagicMock()
        mock_store.query.return_value = [
            _make_audit(
                cost=0.01, created_at=now,
                cache_creation_tokens=0, cache_read_tokens=2000,
            ),
        ]
        mock_get_store.return_value = mock_store

        report = get_spend_report()
        assert report.cache_hit_rate == pytest.approx(1.0)


class TestByRepoAggregation:
    """Epic 32, Story 32.12: Per-repo spend breakdown."""

    def test_spend_report_by_repo_defaults_empty(self):
        r = SpendReport()
        assert r.by_repo == []

    def test_spend_report_by_repo_in_dict(self):
        r = SpendReport(by_repo=[SpendSummary(key="org/repo-a", total_cost=0.05, call_count=3)])
        d = r.to_dict()
        assert len(d["by_repo"]) == 1
        assert d["by_repo"][0]["key"] == "org/repo-a"

    @patch("src.admin.model_spend.get_model_audit_store")
    def test_by_repo_aggregation(self, mock_get_store):
        now = datetime.now(UTC)
        mock_store = MagicMock()
        mock_store.query.return_value = [
            _make_audit(cost=0.05, created_at=now, repo="org/repo-a"),
            _make_audit(cost=0.03, created_at=now, repo="org/repo-b"),
            _make_audit(cost=0.02, created_at=now, repo="org/repo-a"),
        ]
        mock_get_store.return_value = mock_store

        report = get_spend_report()
        assert len(report.by_repo) == 2
        keys = {s.key for s in report.by_repo}
        assert keys == {"org/repo-a", "org/repo-b"}
        # Sorted by cost desc: repo-a (0.07) > repo-b (0.03)
        assert report.by_repo[0].key == "org/repo-a"
        assert report.by_repo[0].total_cost == pytest.approx(0.07)
        assert report.by_repo[0].call_count == 2

    @patch("src.admin.model_spend.get_model_audit_store")
    def test_by_repo_unknown_when_empty(self, mock_get_store):
        now = datetime.now(UTC)
        mock_store = MagicMock()
        mock_store.query.return_value = [
            _make_audit(cost=0.01, created_at=now, repo=""),
        ]
        mock_get_store.return_value = mock_store

        report = get_spend_report()
        assert len(report.by_repo) == 1
        assert report.by_repo[0].key == "unknown"


class TestByDayAggregation:
    """Epic 32, Story 32.12: Per-day spend breakdown for time-series."""

    def test_spend_report_by_day_defaults_empty(self):
        r = SpendReport()
        assert r.by_day == []

    def test_spend_report_by_day_in_dict(self):
        r = SpendReport(by_day=[SpendSummary(key="2026-03-19", total_cost=0.10, call_count=5)])
        d = r.to_dict()
        assert len(d["by_day"]) == 1
        assert d["by_day"][0]["key"] == "2026-03-19"

    @patch("src.admin.model_spend.get_model_audit_store")
    def test_by_day_aggregation(self, mock_get_store):
        now = datetime.now(UTC)
        day1 = now.replace(hour=10, minute=0, second=0, microsecond=0) - timedelta(days=1)
        day2 = now.replace(hour=14, minute=0, second=0, microsecond=0)
        day1_key = day1.strftime("%Y-%m-%d")
        day2_key = day2.strftime("%Y-%m-%d")
        mock_store = MagicMock()
        mock_store.query.return_value = [
            _make_audit(cost=0.05, created_at=day1),
            _make_audit(cost=0.03, created_at=day2),
            _make_audit(cost=0.02, created_at=day1),
        ]
        mock_get_store.return_value = mock_store

        report = get_spend_report(window_hours=48)
        assert len(report.by_day) == 2
        keys = {s.key for s in report.by_day}
        assert keys == {day1_key, day2_key}
        # Sorted by cost desc: day1 (0.07) > day2 (0.03)
        assert report.by_day[0].key == day1_key
        assert report.by_day[0].total_cost == pytest.approx(0.07)

    @patch("src.admin.model_spend.get_model_audit_store")
    def test_by_day_single_day(self, mock_get_store):
        now = datetime.now(UTC)
        mock_store = MagicMock()
        mock_store.query.return_value = [
            _make_audit(cost=0.01, created_at=now),
            _make_audit(cost=0.02, created_at=now),
        ]
        mock_get_store.return_value = mock_store

        report = get_spend_report()
        assert len(report.by_day) == 1
        assert report.by_day[0].call_count == 2
        assert report.by_day[0].total_cost == pytest.approx(0.03)


class TestBudgetUtilization:
    """Epic 32, Story 32.14: Budget utilization per trust tier."""

    def test_tier_budget_utilization_to_dict(self):
        u = TierBudgetUtilization(
            tier="observe", budget_limit=2.00,
            current_spend=0.5, active_tasks=3, utilization_pct=25.0,
        )
        d = u.to_dict()
        assert d["tier"] == "observe"
        assert d["budget_limit"] == 2.0
        assert d["current_spend"] == 0.5
        assert d["active_tasks"] == 3
        assert d["utilization_pct"] == 25.0

    @patch("src.admin.model_spend.get_model_audit_store")
    def test_returns_all_three_tiers(self, mock_get_store):
        mock_store = MagicMock()
        mock_store.query.return_value = []
        mock_get_store.return_value = mock_store

        result = get_budget_utilization()
        assert len(result) == 3
        tiers = [u.tier for u in result]
        assert tiers == ["observe", "suggest", "execute"]

    @patch("src.admin.model_spend.get_model_audit_store")
    def test_zero_spend_when_no_records(self, mock_get_store):
        mock_store = MagicMock()
        mock_store.query.return_value = []
        mock_get_store.return_value = mock_store

        result = get_budget_utilization()
        for u in result:
            assert u.current_spend == 0.0
            assert u.active_tasks == 0
            assert u.utilization_pct == 0.0
            assert u.budget_limit > 0

    @patch("src.admin.model_spend.get_model_audit_store")
    def test_aggregates_spend_by_tier(self, mock_get_store):
        now = datetime.now(UTC)
        mock_store = MagicMock()
        mock_store.query.return_value = [
            _make_audit(cost=0.50, created_at=now, step="intent"),
            _make_audit(cost=0.30, created_at=now, step="qa"),
        ]
        mock_get_store.return_value = mock_store

        result = get_budget_utilization()
        observe = next(u for u in result if u.tier == "observe")
        assert observe.current_spend == pytest.approx(0.80)

    @patch("src.admin.model_spend.get_model_audit_store")
    def test_counts_distinct_tasks(self, mock_get_store):
        from uuid import uuid4
        now = datetime.now(UTC)
        tid1, tid2 = uuid4(), uuid4()
        mock_store = MagicMock()
        mock_store.query.return_value = [
            ModelCallAudit(task_id=tid1, cost=0.10, created_at=now),
            ModelCallAudit(task_id=tid1, cost=0.05, created_at=now),
            ModelCallAudit(task_id=tid2, cost=0.08, created_at=now),
        ]
        mock_get_store.return_value = mock_store

        result = get_budget_utilization()
        observe = next(u for u in result if u.tier == "observe")
        assert observe.active_tasks == 2

    @patch("src.admin.model_spend.get_model_audit_store")
    def test_utilization_percentage(self, mock_get_store):
        now = datetime.now(UTC)
        mock_store = MagicMock()
        mock_store.query.return_value = [
            _make_audit(cost=1.00, created_at=now),
        ]
        mock_get_store.return_value = mock_store

        result = get_budget_utilization()
        observe = next(u for u in result if u.tier == "observe")
        # Default observe budget is $2.00 (cost-optimized) or $5.00
        assert observe.utilization_pct > 0

    @patch("src.admin.model_spend.get_model_audit_store")
    def test_filters_by_window(self, mock_get_store):
        now = datetime.now(UTC)
        old = now - timedelta(hours=48)
        mock_store = MagicMock()
        mock_store.query.return_value = [
            _make_audit(cost=0.50, created_at=now),
            _make_audit(cost=0.30, created_at=old),
        ]
        mock_get_store.return_value = mock_store

        result = get_budget_utilization(window_hours=24)
        observe = next(u for u in result if u.tier == "observe")
        assert observe.current_spend == pytest.approx(0.50)
