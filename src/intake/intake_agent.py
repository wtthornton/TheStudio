"""Intake Agent — eligibility evaluation, role selection, overlay application.

Architecture reference: thestudioarc/08-agent-roles.md (role selection lifecycle, step 1)
Architecture reference: thestudioarc/15-system-runtime-flow.md (Intake Agent responsibilities)

The Intake Agent is the first step in the workflow. It:
1. Evaluates whether a GitHub issue event is eligible for automation
2. Selects a base role from issue type labels
3. Applies overlays from risk labels and issue form fields
4. Computes the EffectiveRolePolicy attached to the TaskPacket

Eligibility contract:
- Eligible: issue has `agent:run` label, repo is registered, repo tier allows automation
- Reject: missing `agent:run`, unregistered repo, repo paused, issue already has active workflow
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from src.intake.adversarial import detect_suspicious_patterns
from src.intake.effective_role import (
    RISK_LABEL_TO_OVERLAY,
    BaseRole,
    EffectiveRolePolicy,
    Overlay,
)

# Issue type labels → base role mapping
TYPE_LABEL_TO_ROLE: dict[str, BaseRole] = {
    "type:bug": BaseRole.DEVELOPER,
    "type:feature": BaseRole.DEVELOPER,
    "type:chore": BaseRole.DEVELOPER,
    "type:docs": BaseRole.DEVELOPER,
    "type:security": BaseRole.DEVELOPER,
    "type:refactor": BaseRole.ARCHITECT,
}


@dataclass(frozen=True)
class IntakeRejection:
    """Structured rejection record. Persisted, not silent."""

    event_id: str
    repo: str
    reason: str
    timestamp: datetime


@dataclass(frozen=True)
class IntakeResult:
    """Result of intake evaluation — either accepted or rejected."""

    accepted: bool
    rejection: IntakeRejection | None = None
    effective_role: EffectiveRolePolicy | None = None
    risk_flags: dict[str, bool] = field(default_factory=dict)


def evaluate_eligibility(
    labels: list[str],
    repo: str,
    repo_registered: bool,
    repo_paused: bool,
    has_active_workflow: bool,
    event_id: str,
    issue_title: str = "",
    issue_body: str = "",
) -> IntakeResult:
    """Evaluate whether an issue event is eligible for automation.

    Returns IntakeResult with either an EffectiveRolePolicy (accepted)
    or an IntakeRejection (rejected).
    """
    now = datetime.now(UTC)

    # Check eligibility gates in order
    if "agent:run" not in labels:
        return IntakeResult(
            accepted=False,
            rejection=IntakeRejection(
                event_id=event_id,
                repo=repo,
                reason="Missing agent:run label",
                timestamp=now,
            ),
        )

    if not repo_registered:
        return IntakeResult(
            accepted=False,
            rejection=IntakeRejection(
                event_id=event_id,
                repo=repo,
                reason="Repository not registered",
                timestamp=now,
            ),
        )

    if repo_paused:
        return IntakeResult(
            accepted=False,
            rejection=IntakeRejection(
                event_id=event_id,
                repo=repo,
                reason="Repository is paused",
                timestamp=now,
            ),
        )

    if has_active_workflow:
        return IntakeResult(
            accepted=False,
            rejection=IntakeRejection(
                event_id=event_id,
                repo=repo,
                reason="Issue already has active workflow",
                timestamp=now,
            ),
        )

    # Check for adversarial input patterns
    combined_text = f"{issue_title} {issue_body}" if issue_title or issue_body else ""
    risk_flags: dict[str, bool] = {}
    if combined_text.strip():
        suspicious = detect_suspicious_patterns(combined_text)
        blocking = [p for p in suspicious if p.severity == "block"]
        warnings = [p for p in suspicious if p.severity == "warning"]

        if blocking:
            return IntakeResult(
                accepted=False,
                rejection=IntakeRejection(
                    event_id=event_id,
                    repo=repo,
                    reason=f"Adversarial input detected: {blocking[0].pattern_name}",
                    timestamp=now,
                ),
            )

        if warnings:
            risk_flags["risk_adversarial_input"] = True

    # Select base role from issue type labels
    base_role = _select_base_role(labels)

    # Apply overlays from risk labels
    overlays = _select_overlays(labels)

    # Compute EffectiveRolePolicy
    effective_role = EffectiveRolePolicy.compute(base_role, overlays)

    return IntakeResult(accepted=True, effective_role=effective_role, risk_flags=risk_flags)


def _select_base_role(labels: list[str]) -> BaseRole:
    """Select base role from issue type labels.

    Priority: explicit type label > default (Developer).
    If type:refactor → Architect. All others → Developer.
    """
    for label in labels:
        if label in TYPE_LABEL_TO_ROLE:
            return TYPE_LABEL_TO_ROLE[label]
    return BaseRole.DEVELOPER


def _select_overlays(labels: list[str]) -> list[Overlay]:
    """Select overlays from risk labels."""
    overlays: list[Overlay] = []
    for label in labels:
        overlay = RISK_LABEL_TO_OVERLAY.get(label)
        if overlay is not None:
            overlays.append(overlay)
    return overlays
