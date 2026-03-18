"""Meridian Portfolio Review Agent configuration and output models.

Epic 29 AC 10-12: Defines MERIDIAN_PORTFOLIO_CONFIG with agent_name="meridian_portfolio",
max_turns=1, max_budget_usd=1.00. System prompt implements 6 health checks (AC 11).
Output model: PortfolioReviewOutput with HealthFlag (AC 12).

Also contains the GitHub issue health report formatter (Story 29.9, AC 17).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from src.agent.framework import AgentConfig, AgentContext

# --- Output Models (AC 12) ---


class HealthStatus(StrEnum):
    """Overall portfolio health status."""

    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"


class HealthFlagSeverity(StrEnum):
    """Severity of a health flag."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class HealthFlag(BaseModel):
    """A single health concern flagged by the portfolio review."""

    category: str = Field(description="Health check category that triggered this flag")
    severity: HealthFlagSeverity = Field(description="Severity of the flag")
    description: str = Field(description="Human-readable description of the concern")
    affected_items: list[str] = Field(
        default_factory=list,
        description="List of affected item identifiers (repo/issue#)",
    )


class PortfolioReviewOutput(BaseModel):
    """Structured output from the Meridian portfolio review agent (AC 12)."""

    overall_health: HealthStatus = Field(
        description="Overall health assessment: healthy, warning, or critical",
    )
    flags: list[HealthFlag] = Field(
        default_factory=list,
        description="List of health concerns with category, severity, and affected items",
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Actionable recommendations for improving portfolio health",
    )
    metrics: dict[str, float] = Field(
        default_factory=dict,
        description="Computed health metrics (ratios, counts, etc.)",
    )
    reviewed_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp of the review",
    )


# --- System Prompt (AC 10-11) ---

MERIDIAN_PORTFOLIO_SYSTEM_PROMPT = """\
You are Meridian, the VP of Success for TheStudio — an AI-augmented software \
delivery platform. You are performing a periodic portfolio health review.

## Your Role
You review the current state of all active work across repos on the GitHub \
Projects v2 board. You identify operational health concerns and provide \
actionable recommendations. You are advisory — you do NOT block tasks or \
modify pipeline behavior.

## Portfolio Data
You receive a snapshot of the Projects v2 board with items grouped by status \
and repo. Each item has: title, repo, status (Queued, In Progress, In Review, \
Blocked, Done), risk tier, and automation tier.

## Health Checks (evaluate ALL six)

### 1. Throughput Health
Ratio of Blocked items to total active items (Queued + In Progress + In Review + Blocked).
Flag if Blocked > {blocked_ratio_pct}% of active items.

### 2. Risk Concentration
Count of High-risk items with status "In Progress" simultaneously.
Flag if > {high_risk_concurrent} high-risk items in progress.

### 3. Approval Bottleneck
Items in "In Review" status. Flag each that has been in review for an \
extended period (note: you may not have timestamp data, so flag all In Review \
items if count exceeds a reasonable threshold).

### 4. Repo Balance
Items per repo as percentage of total active items.
Flag if any single repo has > {repo_concentration_pct}% of total active items.

### 5. Failure Rate
Items with status "Done" that were marked FAILED as percentage of all Done items.
Flag if > {failure_rate_pct}%.

### 6. Stale Items
Items in "Queued" status. Flag if there are items that appear to be stale \
(in practice, all Queued items should be monitored).

## Decision Rules
- overall_health = "healthy" if zero flags
- overall_health = "warning" if any flags with severity low or medium
- overall_health = "critical" if any flags with severity high or critical

## Board Snapshot
{board_snapshot}

## Output
Respond with a JSON object matching this schema:
{{
  "overall_health": "healthy|warning|critical",
  "flags": [
    {{
      "category": "throughput|risk_concentration|approval_bottleneck|...",
      "severity": "low|medium|high|critical",
      "description": "What the concern is",
      "affected_items": ["repo/issue#"]
    }}
  ],
  "recommendations": ["Actionable recommendation"],
  "metrics": {{"blocked_ratio": 0.0, "high_risk_in_progress": 0}},
  "reviewed_at": "{reviewed_at}"
}}
"""


# --- Fallback Function ---


def _portfolio_fallback(context: AgentContext) -> str:
    """Rule-based portfolio health evaluation when LLM is unavailable.

    Implements the same 6 health checks using simple thresholds from settings.
    """
    from src.settings import settings

    thresholds = settings.meridian_thresholds
    snapshot_data = context.extra.get("snapshot_data", {})
    items_by_status = snapshot_data.get("items_by_status", {})
    items_by_repo = snapshot_data.get("items_by_repo", {})
    all_items = snapshot_data.get("items", [])

    flags: list[dict] = []
    metrics: dict[str, float] = {}

    # Active items = Queued + In Progress + In Review + Blocked
    active_statuses = {"Queued", "In Progress", "In Review", "Blocked"}
    active_items = [i for i in all_items if i.get("status") in active_statuses]
    active_count = len(active_items)

    # 1. Throughput health: blocked ratio
    blocked_items = items_by_status.get("Blocked", [])
    blocked_ratio = len(blocked_items) / active_count if active_count > 0 else 0.0
    metrics["blocked_ratio"] = round(blocked_ratio, 3)
    if blocked_ratio > thresholds.get("blocked_ratio", 0.20):
        flags.append(
            {
                "category": "throughput",
                "severity": "high" if blocked_ratio > 0.4 else "medium",
                "description": (
                    f"Blocked items ({len(blocked_items)}) represent "
                    f"{blocked_ratio:.0%} of active items (threshold: "
                    f"{thresholds.get('blocked_ratio', 0.20):.0%})"
                ),
                "affected_items": [
                    f"{i.get('repo', '?')}/#{i.get('number', '?')}" for i in blocked_items
                ],
            }
        )

    # 2. Risk concentration: high-risk in progress
    in_progress = items_by_status.get("In Progress", [])
    high_risk_in_progress = [i for i in in_progress if i.get("risk_tier") == "High"]
    metrics["high_risk_in_progress"] = len(high_risk_in_progress)
    max_concurrent = int(thresholds.get("high_risk_concurrent", 3))
    if len(high_risk_in_progress) > max_concurrent:
        flags.append(
            {
                "category": "risk_concentration",
                "severity": "high",
                "description": (
                    f"{len(high_risk_in_progress)} high-risk items in progress "
                    f"(threshold: {max_concurrent})"
                ),
                "affected_items": [
                    f"{i.get('repo', '?')}/#{i.get('number', '?')}" for i in high_risk_in_progress
                ],
            }
        )

    # 3. Approval bottleneck: items in review
    in_review = items_by_status.get("In Review", [])
    metrics["in_review_count"] = len(in_review)
    # Without timestamps, flag if count is noteworthy (> 0 is informational)
    if len(in_review) > 0:
        flags.append(
            {
                "category": "approval_bottleneck",
                "severity": "low" if len(in_review) <= 2 else "medium",
                "description": f"{len(in_review)} items awaiting review",
                "affected_items": [
                    f"{i.get('repo', '?')}/#{i.get('number', '?')}" for i in in_review
                ],
            }
        )

    # 4. Repo balance: concentration
    repo_concentration = thresholds.get("repo_concentration", 0.50)
    for repo_name, repo_items in items_by_repo.items():
        repo_active = [i for i in repo_items if i.get("status") in active_statuses]
        ratio = len(repo_active) / active_count if active_count > 0 else 0.0
        if ratio > repo_concentration and active_count > 1:
            flags.append(
                {
                    "category": "repo_balance",
                    "severity": "medium",
                    "description": (
                        f"Repo '{repo_name}' has {ratio:.0%} of active items "
                        f"(threshold: {repo_concentration:.0%})"
                    ),
                    "affected_items": [f"{repo_name}/#{i.get('number', '?')}" for i in repo_active],
                }
            )

    # 5. Failure rate
    done_items = items_by_status.get("Done", [])
    failed_items = [i for i in done_items if i.get("original_status") == "FAILED"]
    failure_rate = len(failed_items) / len(done_items) if done_items else 0.0
    metrics["failure_rate"] = round(failure_rate, 3)
    max_failure = thresholds.get("failure_rate", 0.30)
    if failure_rate > max_failure and len(done_items) > 0:
        flags.append(
            {
                "category": "failure_rate",
                "severity": "high",
                "description": (
                    f"Failure rate {failure_rate:.0%} exceeds threshold "
                    f"{max_failure:.0%} ({len(failed_items)}/{len(done_items)} tasks)"
                ),
                "affected_items": [
                    f"{i.get('repo', '?')}/#{i.get('number', '?')}" for i in failed_items
                ],
            }
        )

    # 6. Stale items: queued
    queued_items = items_by_status.get("Queued", [])
    metrics["queued_count"] = len(queued_items)
    if len(queued_items) > 0:
        flags.append(
            {
                "category": "stale_items",
                "severity": "low" if len(queued_items) <= 3 else "medium",
                "description": f"{len(queued_items)} items in Queued status",
                "affected_items": [
                    f"{i.get('repo', '?')}/#{i.get('number', '?')}" for i in queued_items
                ],
            }
        )

    # Determine overall health
    severities = {f["severity"] for f in flags}
    if "critical" in severities or "high" in severities:
        overall_health = "critical"
    elif flags:
        overall_health = "warning"
    else:
        overall_health = "healthy"

    recommendations: list[str] = []
    if blocked_ratio > thresholds.get("blocked_ratio", 0.20):
        recommendations.append("Investigate blocked items and resolve blockers.")
    if len(high_risk_in_progress) > max_concurrent:
        recommendations.append("Reduce concurrent high-risk work to limit blast radius.")
    if len(queued_items) > 5:
        recommendations.append("Review queued items for stale or low-priority work.")

    return json.dumps(
        {
            "overall_health": overall_health,
            "flags": flags,
            "recommendations": recommendations,
            "metrics": metrics,
            "reviewed_at": datetime.now(UTC).isoformat(),
        }
    )


# --- Agent Config (AC 10) ---

MERIDIAN_PORTFOLIO_CONFIG = AgentConfig(
    agent_name="meridian_portfolio",
    pipeline_step="portfolio_review",
    model_class="balanced",
    system_prompt_template=MERIDIAN_PORTFOLIO_SYSTEM_PROMPT,
    tool_allowlist=[],
    max_turns=1,
    max_budget_usd=1.00,
    output_schema=PortfolioReviewOutput,
    fallback_fn=_portfolio_fallback,
    block_on_threat=False,
)


# --- GitHub Issue Health Report (Story 29.9, AC 17) ---


def format_health_report_markdown(review: PortfolioReviewOutput) -> str:
    """Format a PortfolioReviewOutput as a markdown health report for GitHub issues."""
    health_emoji = {
        HealthStatus.HEALTHY: "GREEN",
        HealthStatus.WARNING: "YELLOW",
        HealthStatus.CRITICAL: "RED",
    }

    lines: list[str] = []
    lines.append(f"# Portfolio Health: {review.overall_health.value.upper()}")
    lines.append("")
    lines.append(
        f"**Status:** {health_emoji.get(review.overall_health, '?')} {review.overall_health.value}"
    )
    lines.append(f"**Reviewed:** {review.reviewed_at.strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("")

    # Metrics
    if review.metrics:
        lines.append("## Metrics")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        for key, value in sorted(review.metrics.items()):
            if isinstance(value, float) and value < 1.0:
                lines.append(f"| {key} | {value:.1%} |")
            else:
                lines.append(f"| {key} | {value} |")
        lines.append("")

    # Flags
    if review.flags:
        lines.append("## Health Flags")
        lines.append("")
        for flag in review.flags:
            severity_label = flag.severity.value.upper()
            lines.append(f"### [{severity_label}] {flag.category}")
            lines.append("")
            lines.append(flag.description)
            if flag.affected_items:
                lines.append("")
                lines.append("**Affected items:**")
                for item in flag.affected_items[:10]:  # Limit to 10
                    lines.append(f"- {item}")
                if len(flag.affected_items) > 10:
                    lines.append(f"- ... and {len(flag.affected_items) - 10} more")
            lines.append("")
    else:
        lines.append("## No Health Flags")
        lines.append("")
        lines.append("All checks passed. The portfolio is healthy.")
        lines.append("")

    # Recommendations
    if review.recommendations:
        lines.append("## Recommendations")
        lines.append("")
        for rec in review.recommendations:
            lines.append(f"- {rec}")
        lines.append("")

    lines.append("---")
    lines.append("*Generated by Meridian Portfolio Review (TheStudio)*")

    return "\n".join(lines)
