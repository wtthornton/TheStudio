"""Pipeline status comment formatter for GitHub issues.

Creates and updates a structured Markdown comment on the linked GitHub issue
at each pipeline stage transition. Uses the <!-- thestudio-pipeline-status -->
marker for idempotent in-place edits (same pattern as evidence_comment.py).

A single comment per TaskPacket is maintained on the original issue —
created on Context entry, edited at each stage transition, and finalised
on Publish with a link to the draft PR.

Epic 38 Slice 4, Story 38.21.

Architecture reference: thestudioarc/15-system-runtime-flow.md
"""

from __future__ import annotations

from datetime import UTC, datetime

# Marker used to identify pipeline status comments for idempotent in-place updates.
# Must be unique across all TheStudio comment types.
PIPELINE_COMMENT_MARKER = "<!-- thestudio-pipeline-status -->"

# Human-readable stage labels for the progress table
_STAGE_LABELS: dict[str, str] = {
    "intake": "Intake",
    "context": "Context Enrichment",
    "readiness": "Readiness Gate",
    "intent": "Intent Specification",
    "awaiting_intent_review": "Awaiting Intent Review",
    "router": "Expert Routing",
    "awaiting_routing_review": "Awaiting Routing Review",
    "assembler": "Assembler",
    "preflight": "Preflight Review",
    "implement": "Implementation",
    "verify": "Verification",
    "qa": "Quality Assurance",
    "awaiting_approval": "Awaiting Approval",
    "publish": "Publish",
}

# Canonical ordered pipeline stages shown in the progress table.
# Intermediate wait states (awaiting_*) are omitted for brevity.
_DISPLAY_STAGES: list[str] = [
    "intake",
    "context",
    "intent",
    "router",
    "assembler",
    "implement",
    "verify",
    "qa",
    "publish",
]


def _stage_icon(stage: str, current_stage: str, completed_stages: list[str]) -> str:
    """Return the progress icon for a stage row.

    - ✅ completed
    - 🔄 currently executing
    - ⏳ not yet started
    """
    if stage in completed_stages:
        return "✅"
    if stage == current_stage:
        return "🔄"
    return "⏳"


def format_pipeline_comment(
    taskpacket_id: str,
    current_stage: str,
    completed_stages: list[str] | None = None,
    trust_tier: str = "observe",
    cost_usd: float = 0.0,
    model: str = "",
    pr_url: str = "",
    status: str = "in_progress",
) -> str:
    """Format a pipeline status comment for a GitHub issue.

    Called at each stage transition to produce an updated comment body.
    The caller is responsible for creating or editing the comment via the
    GitHub API.

    Args:
        taskpacket_id: The TaskPacket UUID for this pipeline run.
        current_stage: The stage currently executing.
        completed_stages: Stages that have completed successfully.
        trust_tier: Automation trust tier (observe / suggest / execute).
        cost_usd: Cumulative LLM cost in USD (0.0 = not yet known).
        model: LLM model name used in this run.
        pr_url: URL of the draft PR (empty until Publish stage).
        status: Summary status — one of: in_progress, passed, failed, complete.

    Returns:
        Full Markdown comment body including the HTML marker.
    """
    completed: list[str] = completed_stages or []
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    # Stage progress table rows
    rows: list[str] = []
    for stage in _DISPLAY_STAGES:
        label = _STAGE_LABELS.get(stage, stage.replace("_", " ").title())
        icon = _stage_icon(stage, current_stage, completed)
        rows.append(f"| {icon} | {label} |")
    stages_table = "\n".join(rows)

    # Overall status badge
    status_badges: dict[str, str] = {
        "in_progress": "🔄 In Progress",
        "passed": "✅ Passed",
        "failed": "❌ Failed",
        "complete": "✅ Complete — PR Ready",
    }
    status_badge = status_badges.get(status, "🔄 In Progress")

    # Optional PR link block
    pr_block = f"\n**Draft PR:** {pr_url}\n" if pr_url else ""

    # Cost display — show placeholder until first model call completes
    cost_display = f"${cost_usd:.4f}" if cost_usd > 0 else "Calculating…"

    # Model display — fallback to em-dash if not yet known
    model_display = model if model else "—"

    return f"""{PIPELINE_COMMENT_MARKER}

## 🤖 TheStudio Pipeline Status

**Status:** {status_badge}
**Trust Tier:** `{trust_tier}`
**Estimated Cost:** {cost_display}
**Model:** {model_display}
**Last Updated:** {now}
{pr_block}
### Stage Progress

| | Stage |
|---|---|
{stages_table}

---
*Managed by [TheStudio](https://github.com) — TaskPacket `{taskpacket_id}`*
"""
