"""Qualification harness — validates expert packs before registration.

Architecture reference: thestudioarc/04-expert-recruiter.md (Step 6)

Fast safety and usability checks:
- Expert produces outputs in the expected structure
- Expert stays within scope (tool policy compliance)
- Expert includes risks and validations
- Expert identifies uncertainty
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class QualificationResult:
    """Result of running the qualification harness."""

    passed: bool
    failures: tuple[str, ...]


def qualify_expert_definition(
    definition: dict[str, object],
    tool_policy: dict[str, object],
) -> QualificationResult:
    """Run qualification harness on an expert pack.

    Checks structure, scope, and tool compliance per 04-expert-recruiter.md.
    """
    failures: list[str] = []

    # Check 1: Expected structure — must have scope_boundaries and expected_outputs
    if not definition.get("scope_boundaries"):
        failures.append("Missing or empty scope_boundaries")

    if not definition.get("expected_outputs"):
        failures.append("Missing or empty expected_outputs")

    # Check 2: Operating procedure must exist
    if not definition.get("operating_procedure"):
        failures.append("Missing or empty operating_procedure")

    # Check 3: Failure modes should be documented
    if not definition.get("failure_modes"):
        failures.append("Missing or empty failure_modes")

    # Check 4: Tool policy must be explicit (not empty)
    if not tool_policy:
        failures.append("Tool policy is empty — must be explicit")

    # Check 5: Tool policy must deny repo_write and publish (read-only default)
    denied = tool_policy.get("denied_suites", [])
    if isinstance(denied, list):
        if "repo_write" not in denied:
            failures.append("Tool policy does not deny repo_write")
        if "publish" not in denied:
            failures.append("Tool policy does not deny publish")

    return QualificationResult(
        passed=len(failures) == 0,
        failures=tuple(failures),
    )
