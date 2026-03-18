"""Meridian Portfolio Review — Temporal scheduled workflow.

Epic 29 AC 14: MeridianPortfolioReviewWorkflow runs on a Temporal schedule
(default daily at 09:00 UTC). Collects board state, runs the Meridian agent,
persists results, and optionally posts to GitHub.

Epic 29 AC 15: Results stored in portfolio_reviews table.
Epic 29 AC 17: Optional GitHub issue posting.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING

from temporalio import activity, workflow
from temporalio.common import RetryPolicy

if TYPE_CHECKING:
    from src.meridian.portfolio_config import PortfolioReviewOutput

logger = logging.getLogger(__name__)


# --- Activity I/O ---


@dataclass
class PortfolioReviewInput:
    """Input for the portfolio review activity."""

    owner: str
    project_number: int
    token: str


@dataclass
class PortfolioReviewActivityOutput:
    """Output of the portfolio review activity."""

    overall_health: str = ""
    flags_json: str = "[]"
    metrics_json: str = "{}"
    recommendations_json: str = "[]"
    reviewed_at: str = ""
    persisted: bool = False
    github_issue_posted: bool = False
    error: str = ""


# --- Activity ---


@activity.defn
async def portfolio_review_activity(
    params: PortfolioReviewInput,
) -> PortfolioReviewActivityOutput:
    """Run the full portfolio review: collect, evaluate, persist, optionally post.

    Steps:
    1. Collect board snapshot via ProjectsV2Client
    2. Run Meridian portfolio agent (or fallback)
    3. Persist results to portfolio_reviews table
    4. Optionally post to GitHub issue
    """
    from datetime import UTC, datetime

    from src.observability.conventions import SPAN_MERIDIAN_PORTFOLIO_REVIEW
    from src.observability.tracing import get_tracer
    from src.settings import settings

    tracer = get_tracer("thestudio.meridian.portfolio_workflow")

    with tracer.start_as_current_span(SPAN_MERIDIAN_PORTFOLIO_REVIEW):
        try:
            # 1. Collect snapshot
            from src.meridian.portfolio_collector import collect_portfolio

            snapshot = await collect_portfolio(
                owner=params.owner,
                project_number=params.project_number,
                token=params.token,
            )

            # 2. Run agent (or fallback)
            from src.agent.framework import AgentContext, AgentRunner
            from src.meridian.portfolio_config import (
                MERIDIAN_PORTFOLIO_CONFIG,
                PortfolioReviewOutput,
            )

            # Prepare snapshot data for the agent context
            snapshot_data = {
                "items": [
                    {
                        "title": i.title,
                        "number": i.number,
                        "repo": i.repo,
                        "status": i.status,
                        "risk_tier": i.risk_tier,
                        "automation_tier": i.automation_tier,
                        "state": i.state,
                        "original_status": i.state,
                    }
                    for i in snapshot.items
                ],
                "items_by_status": {
                    status: [
                        {
                            "title": i.title,
                            "number": i.number,
                            "repo": i.repo,
                            "status": i.status,
                            "risk_tier": i.risk_tier,
                            "original_status": i.state,
                        }
                        for i in items
                    ]
                    for status, items in snapshot.items_by_status.items()
                },
                "items_by_repo": {
                    repo: [
                        {
                            "title": i.title,
                            "number": i.number,
                            "repo": i.repo,
                            "status": i.status,
                        }
                        for i in items
                    ]
                    for repo, items in snapshot.items_by_repo.items()
                },
            }

            # Format thresholds for system prompt
            thresholds = settings.meridian_thresholds
            board_summary = _format_board_summary(snapshot_data)

            context = AgentContext(
                extra={
                    "snapshot_data": snapshot_data,
                    "board_snapshot": board_summary,
                    "blocked_ratio_pct": str(int(thresholds.get("blocked_ratio", 0.20) * 100)),
                    "high_risk_concurrent": str(int(thresholds.get("high_risk_concurrent", 3))),
                    "repo_concentration_pct": str(
                        int(thresholds.get("repo_concentration", 0.50) * 100)
                    ),
                    "failure_rate_pct": str(int(thresholds.get("failure_rate", 0.30) * 100)),
                    "reviewed_at": datetime.now(UTC).isoformat(),
                },
            )

            runner = AgentRunner(MERIDIAN_PORTFOLIO_CONFIG)
            result = await runner.run(context)

            # Parse result
            review: PortfolioReviewOutput | None = None
            if result.parsed_output is not None and isinstance(
                result.parsed_output, PortfolioReviewOutput
            ):
                review = result.parsed_output
            elif result.raw_output:
                data = json.loads(result.raw_output)
                review = PortfolioReviewOutput.model_validate(data)

            if review is None:
                return PortfolioReviewActivityOutput(
                    error="no_review_output",
                )

            # 3. Persist to DB
            persisted = await _persist_review(review)

            # 4. Optionally post to GitHub
            github_posted = False
            if settings.meridian_portfolio_github_issue:
                github_posted = await _post_github_issue(review, params.token)

            return PortfolioReviewActivityOutput(
                overall_health=review.overall_health.value,
                flags_json=json.dumps([f.model_dump() for f in review.flags]),
                metrics_json=json.dumps(review.metrics),
                recommendations_json=json.dumps(review.recommendations),
                reviewed_at=review.reviewed_at.isoformat(),
                persisted=persisted,
                github_issue_posted=github_posted,
            )

        except Exception:
            logger.exception("meridian.portfolio_review.failed")
            return PortfolioReviewActivityOutput(error="review_exception")


def _format_board_summary(snapshot_data: dict) -> str:
    """Format snapshot data as a readable board summary for the LLM prompt."""
    lines: list[str] = []

    items_by_status = snapshot_data.get("items_by_status", {})
    for status in ["Queued", "In Progress", "In Review", "Blocked", "Done"]:
        items = items_by_status.get(status, [])
        lines.append(f"\n### {status} ({len(items)} items)")
        for item in items[:20]:  # Limit per status
            risk = f" [Risk: {item['risk_tier']}]" if item.get("risk_tier") else ""
            lines.append(
                f"- {item.get('repo', '?')}/#{item.get('number', '?')}: "
                f"{item.get('title', 'Untitled')}{risk}"
            )

    items_by_repo = snapshot_data.get("items_by_repo", {})
    lines.append("\n### Repo Distribution")
    for repo, items in sorted(items_by_repo.items()):
        lines.append(f"- {repo}: {len(items)} items")

    return "\n".join(lines)


async def _persist_review(review: PortfolioReviewOutput) -> bool:
    """Persist a portfolio review to the database."""
    try:
        from src.db.connection import get_async_session
        from src.db.models import PortfolioReviewRow

        async with get_async_session() as session:
            row = PortfolioReviewRow(
                reviewed_at=review.reviewed_at,
                overall_health=review.overall_health.value,
                flags=[f.model_dump() for f in review.flags],
                metrics=review.metrics,
                recommendations=review.recommendations,
            )
            session.add(row)
            await session.commit()
            logger.info("meridian.portfolio_review.persisted")
            return True
    except Exception:
        logger.warning("meridian.portfolio_review.persist_failed", exc_info=True)
        return False


async def _post_github_issue(
    review: PortfolioReviewOutput,
    token: str,
) -> bool:
    """Create or update a pinned GitHub issue with the health report."""
    try:
        from src.meridian.portfolio_config import format_health_report_markdown
        from src.settings import settings

        if not settings.meridian_portfolio_repo:
            logger.warning("meridian.github_issue.no_repo_configured")
            return False

        repo = settings.meridian_portfolio_repo
        title = f"[Meridian] Portfolio Health Review — {review.reviewed_at.strftime('%Y-%m-%d')}"
        body = format_health_report_markdown(review)

        # Use httpx to create/update the issue via REST API
        import httpx

        headers = {
            "Authorization": f"bearer {token}",
            "Accept": "application/vnd.github+json",
        }

        # Search for existing Meridian issue
        async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
            search_resp = await client.get(
                f"https://api.github.com/repos/{repo}/issues",
                params={
                    "state": "open",
                    "labels": "meridian-health",
                    "per_page": 1,
                },
            )
            search_resp.raise_for_status()
            existing = search_resp.json()

            if existing:
                # Update existing issue
                issue_number = existing[0]["number"]
                await client.patch(
                    f"https://api.github.com/repos/{repo}/issues/{issue_number}",
                    json={"title": title, "body": body},
                )
                logger.info(
                    "meridian.github_issue.updated",
                    extra={"repo": repo, "issue_number": issue_number},
                )
            else:
                # Create new issue
                resp = await client.post(
                    f"https://api.github.com/repos/{repo}/issues",
                    json={
                        "title": title,
                        "body": body,
                        "labels": ["meridian-health"],
                    },
                )
                resp.raise_for_status()
                logger.info(
                    "meridian.github_issue.created",
                    extra={"repo": repo},
                )

        return True
    except Exception:
        logger.warning("meridian.github_issue.failed", exc_info=True)
        return False


# --- Temporal Workflow (AC 14) ---


@workflow.defn
class MeridianPortfolioReviewWorkflow:
    """Temporal scheduled workflow for periodic portfolio health reviews.

    Default schedule: daily at 09:00 UTC.
    Feature-flagged via settings.meridian_portfolio_enabled.
    """

    @workflow.run
    async def run(self, params: PortfolioReviewInput) -> PortfolioReviewActivityOutput:
        return await workflow.execute_activity(
            portfolio_review_activity,
            params,
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(
                maximum_attempts=3,
                initial_interval=timedelta(seconds=10),
            ),
        )
