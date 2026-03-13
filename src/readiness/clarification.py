"""Clarification comment formatter — generates GitHub issue comments.

Produces a friendly, jargon-free comment asking the submitter to provide
additional information for dimensions the readiness gate flagged as missing.

The comment must NOT contain internal pipeline terminology: score, threshold,
complexity index, weight, dimension, or similar technical language.
"""

from __future__ import annotations

from src.readiness.models import ReadinessDimension, ReadinessScore

# Mapping from dimension to a user-friendly section label.
_SECTION_LABELS: dict[ReadinessDimension, str] = {
    ReadinessDimension.GOAL_CLARITY: "Problem or Goal",
    ReadinessDimension.ACCEPTANCE_CRITERIA: "What Done Looks Like",
    ReadinessDimension.SCOPE_BOUNDARIES: "What's Out of Scope",
    ReadinessDimension.RISK_COVERAGE: "Risks or Sensitive Areas",
    ReadinessDimension.REPRODUCTION_CONTEXT: "Steps to Reproduce",
    ReadinessDimension.DEPENDENCY_AWARENESS: "Dependencies",
}

# HTML marker for idempotent comment detection and update.
_MARKER = "<!-- thestudio-readiness -->"


def format_clarification_comment(
    readiness_score: ReadinessScore,
    repo_name: str,
) -> str:
    """Format a GitHub-flavored markdown comment for a held issue.

    Args:
        readiness_score: The readiness score with recommended questions.
        repo_name: Repository name for context (e.g., "acme/widgets").

    Returns:
        Markdown string suitable for posting as a GitHub issue comment.
    """
    lines: list[str] = [_MARKER, ""]

    # Header
    lines.append("## More Information Needed")
    lines.append("")

    # Intro
    lines.append(
        "Thanks for opening this issue! To help us get started quickly, "
        "could you provide a bit more detail on the following?"
    )
    lines.append("")

    # Questions as a numbered checklist
    for i, question in enumerate(readiness_score.recommended_questions, 1):
        lines.append(f"{i}. [ ] {question}")

    lines.append("")

    # Footer
    lines.append(
        "Once you've updated the issue with this information, "
        "we'll automatically re-evaluate and proceed."
    )
    lines.append("")
    lines.append(
        f"*This comment was generated for `{repo_name}`. "
        "Edit the issue above and we'll take another look.*"
    )

    return "\n".join(lines)
