"""Seed the Expert Library with vetted templates.

Seeds 5 expert classes: Security, QA Validation, Technical, Compliance, Process Quality.
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
    ExpertCreate(
        name="technical-review",
        expert_class=ExpertClass.TECHNICAL,
        capability_tags=["architecture", "code_quality", "performance", "design_review"],
        scope_description=(
            "Review code changes for architecture alignment, code quality, "
            "performance implications, and design pattern adherence. Identifies "
            "technical debt, anti-patterns, and scalability concerns."
        ),
        tool_policy={
            "allowed_suites": ["repo_read", "analysis"],
            "denied_suites": ["repo_write", "publish"],
            "read_only": True,
        },
        trust_tier=TrustTier.PROBATION,
        definition={
            "scope_boundaries": [
                "Architecture pattern compliance",
                "Code quality and maintainability",
                "Performance impact analysis",
                "API design review",
            ],
            "expected_outputs": [
                "Architecture alignment assessment",
                "Code quality findings with severity",
                "Performance impact notes",
                "Suggested refactoring or design improvements",
            ],
            "operating_procedure": [
                "Review changed files for architecture pattern violations",
                "Assess code complexity and maintainability metrics",
                "Identify performance-sensitive code paths",
                "Check API contracts for backward compatibility",
                "Produce findings with category and actionable recommendations",
            ],
            "edge_cases": [
                "Trade-offs between performance and readability",
                "Legacy code that cannot follow current patterns",
                "Cross-cutting concerns spanning multiple services",
            ],
            "failure_modes": [
                "Missing architecture context → request system design docs",
                "Cannot assess performance without benchmarks → flag for profiling",
            ],
        },
    ),
    ExpertCreate(
        name="compliance-check",
        expert_class=ExpertClass.COMPLIANCE,
        capability_tags=["regulatory", "data_handling", "audit_trail", "retention"],
        scope_description=(
            "Review changes for compliance with regulatory requirements including "
            "data handling policies, audit trail completeness, retention rules, "
            "and privacy regulations (GDPR, SOC2, PCI)."
        ),
        tool_policy={
            "allowed_suites": ["repo_read", "analysis"],
            "denied_suites": ["repo_write", "publish"],
            "read_only": True,
        },
        trust_tier=TrustTier.PROBATION,
        definition={
            "scope_boundaries": [
                "Data handling and privacy compliance",
                "Audit trail completeness",
                "Retention policy adherence",
                "Regulatory requirement verification",
            ],
            "expected_outputs": [
                "Compliance checklist (pass/fail per regulation)",
                "Data handling findings with regulatory reference",
                "Audit trail gap identification",
                "Retention policy violation alerts",
            ],
            "operating_procedure": [
                "Identify data types being processed (PII, financial, health)",
                "Check data handling against applicable regulations",
                "Verify audit logging for state-changing operations",
                "Validate retention and deletion policies are enforced",
                "Produce compliance findings with regulatory citations",
            ],
            "edge_cases": [
                "Cross-border data transfers with conflicting regulations",
                "Derived data that inherits sensitivity from source",
                "Temporary storage that bypasses retention policies",
            ],
            "failure_modes": [
                "Unknown data classification → request data inventory",
                "Conflicting regulations → escalate to compliance team",
            ],
        },
    ),
    ExpertCreate(
        name="process-quality",
        expert_class=ExpertClass.PROCESS_QUALITY,
        capability_tags=["release_readiness", "operational_hygiene", "runbook", "incident_response"],
        scope_description=(
            "Assess operational readiness of changes including runbook updates, "
            "monitoring coverage, incident response procedures, and release "
            "process compliance."
        ),
        tool_policy={
            "allowed_suites": ["repo_read", "analysis"],
            "denied_suites": ["repo_write", "publish"],
            "read_only": True,
        },
        trust_tier=TrustTier.PROBATION,
        definition={
            "scope_boundaries": [
                "Release readiness verification",
                "Operational runbook completeness",
                "Monitoring and alerting coverage",
                "Incident response procedure updates",
            ],
            "expected_outputs": [
                "Release readiness checklist (pass/fail)",
                "Runbook gap identification",
                "Monitoring coverage assessment",
                "Incident response procedure review",
            ],
            "operating_procedure": [
                "Check for corresponding runbook updates with code changes",
                "Verify monitoring and alerting covers new functionality",
                "Assess rollback procedures for the change",
                "Validate feature flags and gradual rollout configuration",
                "Review incident response procedures for new failure modes",
            ],
            "edge_cases": [
                "Changes that affect multiple services' runbooks",
                "Infrastructure changes without corresponding monitoring",
                "Silent failures that bypass existing alerting",
            ],
            "failure_modes": [
                "No runbook exists for the service → flag for creation",
                "Cannot assess monitoring without access to dashboards → escalate",
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
