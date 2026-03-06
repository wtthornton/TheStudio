"""Seed the Expert Library with vetted templates.

Sprint 1 seeds 2 templates: Security Review and QA Validation.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from src.experts.expert import ExpertClass, ExpertCreate, TrustTier
from src.experts.expert_crud import create_expert, get_expert_by_name

SEED_EXPERTS: list[ExpertCreate] = [
    ExpertCreate(
        name="security-review",
        expert_class=ExpertClass.SECURITY,
        capability_tags=["auth", "secrets", "crypto", "injection"],
        scope_description=(
            "Review code changes for security vulnerabilities including "
            "authentication, authorization, secret handling, cryptographic "
            "operations, and injection risks. Produces structured findings "
            "with severity and remediation guidance."
        ),
        tool_policy={
            "allowed_suites": ["repo_read", "analysis"],
            "denied_suites": ["repo_write", "publish"],
            "read_only": True,
        },
        trust_tier=TrustTier.PROBATION,
        definition={
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
            "edge_cases": [
                "Indirect vulnerabilities through dependency chains",
                "Race conditions in auth flows",
                "Timing attacks on crypto operations",
            ],
            "failure_modes": [
                "Missing context on auth model → request missing inputs",
                "Conflicting security requirements → escalate",
            ],
        },
    ),
    ExpertCreate(
        name="qa-validation",
        expert_class=ExpertClass.QA_VALIDATION,
        capability_tags=["intent_validation", "acceptance_criteria", "defect_classification"],
        scope_description=(
            "Validate implementation against Intent Specification acceptance "
            "criteria. Classify defects by category and severity per the QA "
            "defect taxonomy (thestudioarc/14-qa-quality-layer.md)."
        ),
        tool_policy={
            "allowed_suites": ["repo_read", "test_runner", "analysis"],
            "denied_suites": ["repo_write", "publish"],
            "read_only": True,
        },
        trust_tier=TrustTier.PROBATION,
        definition={
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
                "Classify defects using taxonomy: intent_gap, implementation_bug, "
                "regression, security, performance, compliance, partner_mismatch, operability",
                "Assign severity: S0 critical, S1 high, S2 medium, S3 low",
            ],
            "edge_cases": [
                "Ambiguous acceptance criteria → flag as intent_gap",
                "Partial implementation → map which criteria pass and which fail",
            ],
            "failure_modes": [
                "Missing acceptance criteria → request intent refinement",
                "Cannot determine pass/fail → flag as intent_gap",
            ],
        },
    ),
]


async def seed_experts(session: AsyncSession) -> list[str]:
    """Seed expert templates. Returns names of created experts (skips existing)."""
    created: list[str] = []
    for expert_data in SEED_EXPERTS:
        existing = await get_expert_by_name(session, expert_data.name)
        if existing is None:
            await create_expert(session, expert_data)
            created.append(expert_data.name)
    return created
