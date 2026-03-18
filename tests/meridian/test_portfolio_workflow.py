"""Tests for the Meridian portfolio review workflow (Story 29.7).

Validates: Temporal workflow definition, activity I/O, board summary formatting,
and DB model for portfolio_reviews table.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from src.meridian.portfolio_workflow import (
    MeridianPortfolioReviewWorkflow,
    PortfolioReviewActivityOutput,
    PortfolioReviewInput,
    _format_board_summary,
    portfolio_review_activity,
)

# --- PortfolioReviewInput ---


class TestPortfolioReviewInput:
    def test_fields(self):
        inp = PortfolioReviewInput(owner="org", project_number=1, token="tok")
        assert inp.owner == "org"
        assert inp.project_number == 1
        assert inp.token == "tok"


# --- PortfolioReviewActivityOutput ---


class TestPortfolioReviewActivityOutput:
    def test_defaults(self):
        out = PortfolioReviewActivityOutput()
        assert out.overall_health == ""
        assert out.persisted is False
        assert out.github_issue_posted is False
        assert out.error == ""

    def test_success_output(self):
        out = PortfolioReviewActivityOutput(
            overall_health="healthy",
            flags_json="[]",
            metrics_json='{"blocked_ratio": 0.05}',
            recommendations_json='["Keep it up"]',
            reviewed_at="2026-03-17T09:00:00+00:00",
            persisted=True,
        )
        assert out.overall_health == "healthy"
        assert out.persisted is True


# --- _format_board_summary ---


class TestFormatBoardSummary:
    def test_empty_snapshot(self):
        data = {"items_by_status": {}, "items_by_repo": {}}
        summary = _format_board_summary(data)
        assert "Queued (0 items)" in summary
        assert "In Progress (0 items)" in summary
        assert "Repo Distribution" in summary

    def test_with_items(self):
        data = {
            "items_by_status": {
                "In Progress": [
                    {"repo": "org/repo-a", "number": 1, "title": "Bug fix", "risk_tier": "High"},
                ],
                "Blocked": [
                    {"repo": "org/repo-b", "number": 2, "title": "Feature", "risk_tier": ""},
                ],
            },
            "items_by_repo": {
                "org/repo-a": [{"number": 1}],
                "org/repo-b": [{"number": 2}],
            },
        }
        summary = _format_board_summary(data)
        assert "In Progress (1 items)" in summary
        assert "Blocked (1 items)" in summary
        assert "[Risk: High]" in summary
        assert "org/repo-a: 1 items" in summary


# --- portfolio_review_activity ---


class TestPortfolioReviewActivity:
    @pytest.mark.asyncio
    async def test_returns_error_on_exception(self):
        """Activity returns error output on exception, not raising."""
        params = PortfolioReviewInput(owner="org", project_number=1, token="tok")

        with patch(
            "src.meridian.portfolio_collector.collect_portfolio",
            side_effect=Exception("API down"),
        ):
            result = await portfolio_review_activity(params)

        assert result.error == "review_exception"
        assert result.overall_health == ""

    @pytest.mark.asyncio
    async def test_successful_review(self):
        """Activity completes full review cycle."""
        from src.meridian.portfolio_collector import PortfolioItem, PortfolioSnapshot

        snapshot = PortfolioSnapshot(
            collected_at=datetime.now(UTC),
            total_items=2,
            items=[
                PortfolioItem("PVTI_1", "Bug", 1, "org/repo-a", status="In Progress"),
                PortfolioItem("PVTI_2", "Feature", 2, "org/repo-b", status="Queued"),
            ],
            items_by_status={
                "In Progress": [
                    PortfolioItem("PVTI_1", "Bug", 1, "org/repo-a", status="In Progress"),
                ],
                "Queued": [
                    PortfolioItem("PVTI_2", "Feature", 2, "org/repo-b", status="Queued"),
                ],
            },
            items_by_repo={
                "org/repo-a": [
                    PortfolioItem("PVTI_1", "Bug", 1, "org/repo-a", status="In Progress"),
                ],
                "org/repo-b": [
                    PortfolioItem("PVTI_2", "Feature", 2, "org/repo-b", status="Queued"),
                ],
            },
        )

        with (
            patch(
                "src.meridian.portfolio_collector.collect_portfolio",
                new_callable=AsyncMock,
                return_value=snapshot,
            ),
            patch(
                "src.meridian.portfolio_workflow._persist_review",
                new_callable=AsyncMock,
                return_value=False,
            ),
        ):
            params = PortfolioReviewInput(owner="org", project_number=1, token="tok")
            result = await portfolio_review_activity(params)

        assert result.error == ""
        assert result.overall_health in ("healthy", "warning", "critical")
        assert result.reviewed_at != ""


# --- MeridianPortfolioReviewWorkflow ---


class TestMeridianPortfolioReviewWorkflow:
    def test_workflow_class_exists(self):
        """Workflow class is importable and has run method."""
        assert hasattr(MeridianPortfolioReviewWorkflow, "run")


# --- DB Model ---


class TestPortfolioReviewRow:
    def test_model_importable(self):
        from src.db.models import PortfolioReviewRow

        assert PortfolioReviewRow.__tablename__ == "portfolio_reviews"

    def test_model_fields(self):
        from src.db.models import PortfolioReviewRow

        columns = {c.name for c in PortfolioReviewRow.__table__.columns}
        assert "id" in columns
        assert "reviewed_at" in columns
        assert "overall_health" in columns
        assert "flags" in columns
        assert "metrics" in columns
        assert "recommendations" in columns


# --- Migration ---


class TestMigration024:
    def test_sql_up_creates_table(self):
        import importlib

        mod = importlib.import_module("src.db.migrations.024_portfolio_reviews")
        sql = " ".join(mod.SQL_UP)
        assert "portfolio_reviews" in sql
        assert "overall_health" in sql
        assert "flags" in sql

    def test_sql_down_drops_table(self):
        import importlib

        mod = importlib.import_module("src.db.migrations.024_portfolio_reviews")
        sql = " ".join(mod.SQL_DOWN)
        assert "DROP TABLE" in sql
