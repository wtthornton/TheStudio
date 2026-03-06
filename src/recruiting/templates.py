"""Expert templates — vetted patterns for expert creation.

Architecture reference: thestudioarc/04-expert-recruiter.md (Step 3: Template selection)
Templates define expected outputs, common failure modes, default tool boundaries,
evaluation rubric, and escalation triggers.
"""

from dataclasses import dataclass

from src.experts.expert import ExpertClass, TrustTier


@dataclass(frozen=True)
class ExpertTemplate:
    """A vetted pattern for creating new experts."""

    template_id: str
    name_prefix: str
    expert_class: ExpertClass
    default_capability_tags: list[str]
    scope_description: str
    default_trust_tier: TrustTier
    tool_policy: dict[str, object]
    definition_skeleton: dict[str, object]


# Curated template catalog (per 04-expert-recruiter.md)
TEMPLATE_CATALOG: dict[str, ExpertTemplate] = {
    "security-review": ExpertTemplate(
        template_id="security-review",
        name_prefix="security-review",
        expert_class=ExpertClass.SECURITY,
        default_capability_tags=["auth", "secrets", "crypto", "injection"],
        scope_description=(
            "Review code changes for security vulnerabilities including "
            "authentication, authorization, secret handling, cryptographic "
            "operations, and injection risks."
        ),
        default_trust_tier=TrustTier.PROBATION,
        tool_policy={
            "allowed_suites": ["repo_read", "analysis"],
            "denied_suites": ["repo_write", "publish"],
            "read_only": True,
        },
        definition_skeleton={
            "scope_boundaries": [
                "Auth and authorization flows",
                "Secret and credential handling",
                "Cryptographic operations",
                "Input validation and injection prevention",
            ],
            "expected_outputs": [
                "Security findings list with severity (S0-S3)",
                "Remediation recommendations",
                "Risk assessment for identified patterns",
            ],
            "operating_procedure": [
                "Review intent constraints for security requirements",
                "Analyze changed files for security patterns",
                "Check for OWASP Top 10 vulnerability classes",
                "Produce structured findings with severity and category",
            ],
            "failure_modes": [
                "Missing context on auth model -> request missing inputs",
                "Conflicting security requirements -> escalate",
            ],
        },
    ),
    "qa-validation": ExpertTemplate(
        template_id="qa-validation",
        name_prefix="qa-validation",
        expert_class=ExpertClass.QA_VALIDATION,
        default_capability_tags=[
            "intent_validation", "acceptance_criteria", "defect_classification",
        ],
        scope_description=(
            "Validate implementation against Intent Specification acceptance "
            "criteria. Classify defects by category and severity."
        ),
        default_trust_tier=TrustTier.PROBATION,
        tool_policy={
            "allowed_suites": ["repo_read", "test_runner", "analysis"],
            "denied_suites": ["repo_write", "publish"],
            "read_only": True,
        },
        definition_skeleton={
            "scope_boundaries": [
                "Intent Specification acceptance criteria validation",
                "Defect classification (category + severity)",
                "Regression detection",
                "Edge case identification",
            ],
            "expected_outputs": [
                "Acceptance criteria checklist (pass/fail per criterion)",
                "Defect list with category, severity, and intent mapping",
                "Intent gap identification (blocks qa_passed)",
            ],
            "operating_procedure": [
                "Parse acceptance criteria from Intent Specification",
                "Map implementation evidence to each criterion",
                "Identify gaps between intent and implementation",
                "Classify defects using taxonomy",
                "Assign severity: S0 critical, S1 high, S2 medium, S3 low",
            ],
            "failure_modes": [
                "Missing acceptance criteria -> request intent refinement",
                "Cannot determine pass/fail -> flag as intent_gap",
            ],
        },
    ),
}


def select_template(
    expert_class: ExpertClass,
    capability_tags: list[str],
) -> ExpertTemplate | None:
    """Select the narrowest template that fits the capability request.

    Per 04-expert-recruiter.md: choose the narrowest template that fits.
    Returns None if no template matches.
    """
    best: ExpertTemplate | None = None
    best_overlap = 0

    for template in TEMPLATE_CATALOG.values():
        if template.expert_class != expert_class:
            continue
        # Score by tag overlap
        overlap = len(set(template.default_capability_tags) & set(capability_tags))
        if overlap > best_overlap or best is None:
            best = template
            best_overlap = overlap

    return best
