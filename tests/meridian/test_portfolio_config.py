"""Tests for the Meridian portfolio review agent config and output models (Story 29.6).

Validates: PortfolioReviewOutput model (AC 12), health checks (AC 11),
agent config (AC 10), fallback function, and markdown formatter (Story 29.9).
"""

from __future__ import annotations

import json
from datetime import datetime

from src.agent.framework import AgentConfig, AgentContext
from src.meridian.portfolio_config import (
    MERIDIAN_PORTFOLIO_CONFIG,
    HealthFlag,
    HealthFlagSeverity,
    HealthStatus,
    PortfolioReviewOutput,
    _portfolio_fallback,
    format_health_report_markdown,
)

# --- Agent Config (AC 10) ---


class TestAgentConfig:
    def test_config_is_agent_config(self):
        assert isinstance(MERIDIAN_PORTFOLIO_CONFIG, AgentConfig)

    def test_agent_name(self):
        assert MERIDIAN_PORTFOLIO_CONFIG.agent_name == "meridian_portfolio"

    def test_max_turns(self):
        assert MERIDIAN_PORTFOLIO_CONFIG.max_turns == 1

    def test_max_budget(self):
        assert MERIDIAN_PORTFOLIO_CONFIG.max_budget_usd == 1.00

    def test_pipeline_step(self):
        assert MERIDIAN_PORTFOLIO_CONFIG.pipeline_step == "portfolio_review"

    def test_output_schema(self):
        assert MERIDIAN_PORTFOLIO_CONFIG.output_schema is PortfolioReviewOutput

    def test_has_fallback(self):
        assert MERIDIAN_PORTFOLIO_CONFIG.fallback_fn is not None

    def test_no_tools(self):
        assert MERIDIAN_PORTFOLIO_CONFIG.tool_allowlist == []


# --- Output Model (AC 12) ---


class TestPortfolioReviewOutput:
    def test_healthy_output(self):
        output = PortfolioReviewOutput(
            overall_health=HealthStatus.HEALTHY,
            flags=[],
            recommendations=[],
            metrics={},
        )
        assert output.overall_health == HealthStatus.HEALTHY
        assert output.flags == []

    def test_warning_output_with_flags(self):
        flag = HealthFlag(
            category="throughput",
            severity=HealthFlagSeverity.MEDIUM,
            description="Blocked items > 20%",
            affected_items=["org/repo-a/#1"],
        )
        output = PortfolioReviewOutput(
            overall_health=HealthStatus.WARNING,
            flags=[flag],
            recommendations=["Investigate blocked items"],
            metrics={"blocked_ratio": 0.25},
        )
        assert output.overall_health == HealthStatus.WARNING
        assert len(output.flags) == 1
        assert output.flags[0].category == "throughput"

    def test_reviewed_at_has_default(self):
        output = PortfolioReviewOutput(overall_health=HealthStatus.HEALTHY)
        assert isinstance(output.reviewed_at, datetime)

    def test_serialization_roundtrip(self):
        output = PortfolioReviewOutput(
            overall_health=HealthStatus.CRITICAL,
            flags=[
                HealthFlag(
                    category="risk_concentration",
                    severity=HealthFlagSeverity.HIGH,
                    description="Too many high-risk items",
                    affected_items=["repo/a/#1", "repo/b/#2"],
                )
            ],
            recommendations=["Reduce concurrent high-risk work"],
            metrics={"high_risk_in_progress": 5},
        )
        data = output.model_dump()
        restored = PortfolioReviewOutput.model_validate(data)
        assert restored.overall_health == HealthStatus.CRITICAL
        assert len(restored.flags) == 1


class TestHealthStatus:
    def test_enum_values(self):
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.WARNING.value == "warning"
        assert HealthStatus.CRITICAL.value == "critical"


class TestHealthFlagSeverity:
    def test_enum_values(self):
        assert HealthFlagSeverity.LOW.value == "low"
        assert HealthFlagSeverity.MEDIUM.value == "medium"
        assert HealthFlagSeverity.HIGH.value == "high"
        assert HealthFlagSeverity.CRITICAL.value == "critical"


# --- Fallback Function (AC 11 health checks) ---


def _make_snapshot_data(
    *,
    queued: int = 0,
    in_progress: int = 0,
    in_review: int = 0,
    blocked: int = 0,
    done: int = 0,
    high_risk_in_progress: int = 0,
    failed_done: int = 0,
    repos: dict[str, int] | None = None,
) -> dict:
    """Build snapshot_data for fallback testing."""
    items = []
    counter = 1

    def _item(status, risk="", repo="org/repo-a", orig=""):
        nonlocal counter
        item = {
            "title": f"Item {counter}",
            "number": counter,
            "repo": repo,
            "status": status,
            "risk_tier": risk,
            "original_status": orig,
        }
        counter += 1
        return item

    for _ in range(queued):
        items.append(_item("Queued"))

    for i in range(in_progress):
        risk = "High" if i < high_risk_in_progress else "Low"
        items.append(_item("In Progress", risk=risk))

    for _ in range(in_review):
        items.append(_item("In Review"))

    for _ in range(blocked):
        items.append(_item("Blocked"))

    for i in range(done):
        orig = "FAILED" if i < failed_done else "PUBLISHED"
        items.append(_item("Done", orig=orig))

    # Override repos if specified
    if repos:
        items = []
        counter = 1
        for repo_name, count in repos.items():
            for _ in range(count):
                items.append(_item("In Progress", repo=repo_name))

    # Build grouped dicts
    items_by_status: dict[str, list] = {}
    items_by_repo: dict[str, list] = {}
    for item in items:
        items_by_status.setdefault(item["status"], []).append(item)
        items_by_repo.setdefault(item["repo"], []).append(item)

    return {
        "items": items,
        "items_by_status": items_by_status,
        "items_by_repo": items_by_repo,
    }


class TestPortfolioFallback:
    def test_healthy_portfolio(self):
        """No flags when everything is clean (single-item portfolio)."""
        # A single active item cannot trigger repo_concentration (needs > 1)
        snapshot = _make_snapshot_data(in_progress=1)
        context = AgentContext(extra={"snapshot_data": snapshot})
        raw = _portfolio_fallback(context)
        data = json.loads(raw)
        assert data["overall_health"] == "healthy"
        assert len(data["flags"]) == 0

    def test_blocked_ratio_flag(self):
        """Flags throughput when blocked > 20% of active."""
        # 3 blocked out of 10 active = 30%
        snapshot = _make_snapshot_data(in_progress=5, in_review=2, blocked=3)
        context = AgentContext(extra={"snapshot_data": snapshot})
        raw = _portfolio_fallback(context)
        data = json.loads(raw)
        throughput_flags = [f for f in data["flags"] if f["category"] == "throughput"]
        assert len(throughput_flags) == 1
        assert data["metrics"]["blocked_ratio"] == 0.3

    def test_high_risk_concentration_flag(self):
        """Flags risk when > 3 high-risk items in progress."""
        snapshot = _make_snapshot_data(in_progress=5, high_risk_in_progress=4)
        context = AgentContext(extra={"snapshot_data": snapshot})
        raw = _portfolio_fallback(context)
        data = json.loads(raw)
        risk_flags = [f for f in data["flags"] if f["category"] == "risk_concentration"]
        assert len(risk_flags) == 1
        assert data["metrics"]["high_risk_in_progress"] == 4

    def test_no_risk_flag_at_threshold(self):
        """No risk flag when exactly at threshold (3)."""
        snapshot = _make_snapshot_data(in_progress=5, high_risk_in_progress=3)
        context = AgentContext(extra={"snapshot_data": snapshot})
        raw = _portfolio_fallback(context)
        data = json.loads(raw)
        risk_flags = [f for f in data["flags"] if f["category"] == "risk_concentration"]
        assert len(risk_flags) == 0

    def test_approval_bottleneck_flag(self):
        """Flags items in review."""
        snapshot = _make_snapshot_data(in_progress=3, in_review=3)
        context = AgentContext(extra={"snapshot_data": snapshot})
        raw = _portfolio_fallback(context)
        data = json.loads(raw)
        review_flags = [f for f in data["flags"] if f["category"] == "approval_bottleneck"]
        assert len(review_flags) == 1

    def test_repo_concentration_flag(self):
        """Flags when one repo has > 50% of active items."""
        snapshot = _make_snapshot_data(repos={"org/repo-a": 8, "org/repo-b": 2})
        context = AgentContext(extra={"snapshot_data": snapshot})
        raw = _portfolio_fallback(context)
        data = json.loads(raw)
        repo_flags = [f for f in data["flags"] if f["category"] == "repo_balance"]
        assert len(repo_flags) == 1
        assert "org/repo-a" in repo_flags[0]["description"]

    def test_stale_items_flag(self):
        """Flags queued items."""
        snapshot = _make_snapshot_data(queued=4, in_progress=2)
        context = AgentContext(extra={"snapshot_data": snapshot})
        raw = _portfolio_fallback(context)
        data = json.loads(raw)
        stale_flags = [f for f in data["flags"] if f["category"] == "stale_items"]
        assert len(stale_flags) == 1
        assert data["metrics"]["queued_count"] == 4

    def test_critical_health_on_high_severity(self):
        """Critical health when high-severity flags exist."""
        # 5 blocked out of 8 active = 62.5% → high severity
        snapshot = _make_snapshot_data(in_progress=3, blocked=5)
        context = AgentContext(extra={"snapshot_data": snapshot})
        raw = _portfolio_fallback(context)
        data = json.loads(raw)
        assert data["overall_health"] == "critical"

    def test_empty_snapshot(self):
        """Healthy when no items at all."""
        snapshot = _make_snapshot_data()
        context = AgentContext(extra={"snapshot_data": snapshot})
        raw = _portfolio_fallback(context)
        data = json.loads(raw)
        assert data["overall_health"] == "healthy"

    def test_metrics_present(self):
        """Metrics dict is always populated."""
        snapshot = _make_snapshot_data(in_progress=3, blocked=1)
        context = AgentContext(extra={"snapshot_data": snapshot})
        raw = _portfolio_fallback(context)
        data = json.loads(raw)
        assert "blocked_ratio" in data["metrics"]
        assert "high_risk_in_progress" in data["metrics"]
        assert "queued_count" in data["metrics"]

    def test_reviewed_at_present(self):
        """Output includes reviewed_at timestamp."""
        snapshot = _make_snapshot_data()
        context = AgentContext(extra={"snapshot_data": snapshot})
        raw = _portfolio_fallback(context)
        data = json.loads(raw)
        assert "reviewed_at" in data
        assert data["reviewed_at"] != ""


# --- Settings threshold defaults (AC 19) ---


class TestThresholdDefaults:
    def test_default_thresholds(self):
        """Verify settings.meridian_thresholds has the expected defaults."""
        from src.settings import Settings

        s = Settings()
        assert s.meridian_thresholds["blocked_ratio"] == 0.20
        assert s.meridian_thresholds["high_risk_concurrent"] == 3
        assert s.meridian_thresholds["review_stale_hours"] == 48
        assert s.meridian_thresholds["repo_concentration"] == 0.50
        assert s.meridian_thresholds["failure_rate"] == 0.30
        assert s.meridian_thresholds["queued_stale_days"] == 7


# --- Markdown Formatter (Story 29.9) ---


class TestFormatHealthReportMarkdown:
    def test_healthy_report(self):
        review = PortfolioReviewOutput(
            overall_health=HealthStatus.HEALTHY,
            metrics={"blocked_ratio": 0.05},
        )
        md = format_health_report_markdown(review)
        assert "HEALTHY" in md
        assert "No Health Flags" in md
        assert "Generated by Meridian" in md

    def test_warning_report_with_flags(self):
        review = PortfolioReviewOutput(
            overall_health=HealthStatus.WARNING,
            flags=[
                HealthFlag(
                    category="throughput",
                    severity=HealthFlagSeverity.MEDIUM,
                    description="Too many blocked items",
                    affected_items=["org/repo-a/#1", "org/repo-a/#2"],
                )
            ],
            recommendations=["Unblock stuck items"],
            metrics={"blocked_ratio": 0.25},
        )
        md = format_health_report_markdown(review)
        assert "WARNING" in md
        assert "throughput" in md
        assert "Too many blocked items" in md
        assert "Unblock stuck items" in md
        assert "25.0%" in md

    def test_critical_report(self):
        review = PortfolioReviewOutput(
            overall_health=HealthStatus.CRITICAL,
            flags=[
                HealthFlag(
                    category="risk_concentration",
                    severity=HealthFlagSeverity.CRITICAL,
                    description="5 high-risk items in progress",
                ),
            ],
        )
        md = format_health_report_markdown(review)
        assert "CRITICAL" in md
        assert "risk_concentration" in md

    def test_affected_items_truncated(self):
        review = PortfolioReviewOutput(
            overall_health=HealthStatus.WARNING,
            flags=[
                HealthFlag(
                    category="stale_items",
                    severity=HealthFlagSeverity.LOW,
                    description="Many queued items",
                    affected_items=[f"org/repo/#i{i}" for i in range(15)],
                ),
            ],
        )
        md = format_health_report_markdown(review)
        assert "and 5 more" in md

    def test_metrics_table(self):
        review = PortfolioReviewOutput(
            overall_health=HealthStatus.HEALTHY,
            metrics={"blocked_ratio": 0.1, "high_risk_in_progress": 2},
        )
        md = format_health_report_markdown(review)
        assert "| Metric | Value |" in md
        assert "blocked_ratio" in md
