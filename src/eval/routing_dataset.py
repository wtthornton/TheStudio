"""Labeled dataset for intake, context, router, and assembler agent evals.

Epic 32, Story 32.2: 8 synthetic GitHub issues covering the range of
classifications each agent must handle. Reused across all 4 eval suites
with agent-specific context builders and score functions.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.eval.models import EvalCase


@dataclass(frozen=True)
class RoutingEvalCase(EvalCase):
    """Extended EvalCase with expected outputs for all 4 target agents."""

    # Intake expected outputs
    expected_accepted: bool = True
    expected_base_role: str = "developer"
    expected_overlays: list[str] = field(default_factory=list)
    expected_risk_keys: list[str] = field(default_factory=list)

    # Context expected outputs
    expected_scope_keywords: list[str] = field(default_factory=list)
    expected_impacted_count_min: int = 1

    # Router expected outputs
    expected_expert_classes: list[str] = field(default_factory=list)
    expected_min_experts: int = 1

    # Assembler expected outputs
    expected_min_plan_steps: int = 1
    expected_has_qa_handoff: bool = True


ROUTING_DATASET: list[RoutingEvalCase] = [
    # 1. Simple bug fix — developer role, no overlays
    RoutingEvalCase(
        case_id="route_bug_fix_01",
        category="bug_fix",
        issue_title="Fix pagination off-by-one error in tasks API",
        issue_body=(
            "The `/api/v1/tasks` endpoint returns 11 items when `per_page=10`. "
            "The offset calculation uses `page * per_page` instead of "
            "`(page - 1) * per_page`. Affects all paginated endpoints."
        ),
        labels=["agent:run", "bug", "api"],
        complexity="low",
        expected_accepted=True,
        expected_base_role="developer",
        expected_overlays=[],
        expected_risk_keys=[],
        expected_scope_keywords=["api", "pagination", "tasks"],
        expected_impacted_count_min=1,
        expected_expert_classes=["technical"],
        expected_min_experts=1,
        expected_min_plan_steps=2,
        expected_goal_keywords=["pagination", "off-by-one", "fix"],
    ),
    # 2. Security vulnerability — security overlay required
    RoutingEvalCase(
        case_id="route_security_02",
        category="security",
        issue_title="SQL injection in user search endpoint",
        issue_body=(
            "The `/api/v1/users/search` endpoint passes the `q` query "
            "parameter directly into a raw SQL query without parameterization. "
            "An attacker can extract database contents via UNION-based injection. "
            "Requires immediate fix with parameterized queries and input validation."
        ),
        labels=["agent:run", "security", "critical"],
        risk_flags={"risk_security": True},
        complexity="medium",
        expected_accepted=True,
        expected_base_role="developer",
        expected_overlays=["security"],
        expected_risk_keys=["risk_security"],
        expected_scope_keywords=["sql", "injection", "search", "security"],
        expected_impacted_count_min=1,
        expected_expert_classes=["security", "technical"],
        expected_min_experts=2,
        expected_min_plan_steps=3,
        expected_goal_keywords=["sql injection", "parameterized", "security"],
    ),
    # 3. Database migration — migration overlay
    RoutingEvalCase(
        case_id="route_migration_03",
        category="migration",
        issue_title="Add user preferences table and migrate existing settings",
        issue_body=(
            "We need a new `user_preferences` table to replace the JSON blob "
            "in `user_profile.settings`. Create an Alembic migration that:\n"
            "1. Creates the new table with proper columns\n"
            "2. Migrates existing JSON data row-by-row\n"
            "3. Adds a foreign key from user_profile to user_preferences\n"
            "4. Keeps the old column for rollback safety"
        ),
        labels=["agent:run", "database", "migration"],
        risk_flags={"risk_breaking": True},
        complexity="high",
        expected_accepted=True,
        expected_base_role="developer",
        expected_overlays=["migration"],
        expected_risk_keys=["risk_breaking"],
        expected_scope_keywords=["database", "migration", "table", "preferences"],
        expected_impacted_count_min=2,
        expected_expert_classes=["technical"],
        expected_min_experts=1,
        expected_min_plan_steps=4,
        expected_goal_keywords=["migration", "preferences", "table"],
    ),
    # 4. Architecture refactor — architect role
    RoutingEvalCase(
        case_id="route_architect_04",
        category="refactor",
        issue_title="Extract notification subsystem into event-driven architecture",
        issue_body=(
            "Our notification code is scattered across 5 modules with "
            "duplicated email/Slack/webhook logic. Refactor into an "
            "event-driven notification subsystem:\n"
            "- Define notification events (TaskCompleted, ReviewRequested, etc.)\n"
            "- Create NotificationService that subscribes to events\n"
            "- Channel adapters (email, Slack, webhook) as strategy pattern\n"
            "- Ensure backward compatibility with existing callers"
        ),
        labels=["agent:run", "refactor", "architecture"],
        complexity="high",
        expected_accepted=True,
        expected_base_role="architect",
        expected_overlays=[],
        expected_risk_keys=[],
        expected_scope_keywords=["notification", "event", "refactor"],
        expected_impacted_count_min=3,
        expected_expert_classes=["technical"],
        expected_min_experts=1,
        expected_min_plan_steps=4,
        expected_goal_keywords=["notification", "event-driven", "refactor"],
    ),
    # 5. Feature with compliance — billing overlay
    RoutingEvalCase(
        case_id="route_billing_05",
        category="feature",
        issue_title="Add usage-based billing for API calls",
        issue_body=(
            "Implement per-API-call metering and billing:\n"
            "- Track API calls per user/org with request counting middleware\n"
            "- Bill at $0.01 per 1000 API calls above the free tier (10k/month)\n"
            "- Generate monthly invoices with line items\n"
            "- Integrate with Stripe for payment processing\n"
            "- Ensure PCI compliance for payment data handling"
        ),
        labels=["agent:run", "feature", "billing"],
        risk_flags={"risk_security": True},
        complexity="high",
        expected_accepted=True,
        expected_base_role="developer",
        expected_overlays=["billing"],
        expected_risk_keys=["risk_security"],
        expected_scope_keywords=["billing", "api", "metering", "stripe"],
        expected_impacted_count_min=2,
        expected_expert_classes=["technical"],
        expected_min_experts=1,
        expected_min_plan_steps=4,
        expected_goal_keywords=["billing", "api", "metering"],
    ),
    # 6. Simple docs update — should be accepted, low complexity
    RoutingEvalCase(
        case_id="route_docs_06",
        category="docs",
        issue_title="Update README with new API endpoint documentation",
        issue_body=(
            "The README is missing documentation for the new `/api/v2/export` "
            "endpoint added in PR #142. Add:\n"
            "- Endpoint description and authentication requirements\n"
            "- Request/response examples with curl\n"
            "- Rate limiting details"
        ),
        labels=["agent:run", "documentation"],
        complexity="low",
        expected_accepted=True,
        expected_base_role="developer",
        expected_overlays=[],
        expected_risk_keys=[],
        expected_scope_keywords=["readme", "documentation", "api"],
        expected_impacted_count_min=1,
        expected_expert_classes=["technical"],
        expected_min_experts=1,
        expected_min_plan_steps=1,
        expected_goal_keywords=["readme", "documentation", "endpoint"],
    ),
    # 7. Rejected issue — missing agent:run label
    RoutingEvalCase(
        case_id="route_rejected_07",
        category="rejected",
        issue_title="Add dark mode to the admin dashboard",
        issue_body="It would be nice to have dark mode in the admin UI.",
        labels=["enhancement"],  # No agent:run label
        complexity="low",
        expected_accepted=False,
        expected_base_role="developer",
        expected_overlays=[],
        expected_risk_keys=[],
        expected_scope_keywords=[],
        expected_impacted_count_min=0,
        expected_expert_classes=[],
        expected_min_experts=0,
        expected_min_plan_steps=0,
        expected_has_qa_handoff=False,
    ),
    # 8. Cross-team infra change — multiple overlays
    RoutingEvalCase(
        case_id="route_infra_08",
        category="infra",
        issue_title="Migrate CI/CD from GitHub Actions to self-hosted runners",
        issue_body=(
            "Move our CI/CD pipeline to self-hosted runners for cost savings:\n"
            "- Set up 3 self-hosted runners on EC2 (t3.xlarge)\n"
            "- Configure Docker-in-Docker for container builds\n"
            "- Migrate all workflow files to use self-hosted runner labels\n"
            "- Set up monitoring and auto-scaling\n"
            "- Ensure secrets are properly configured on new runners\n"
            "- Cross-team coordination needed: DevOps and all service teams"
        ),
        labels=["agent:run", "infrastructure", "ci-cd"],
        risk_flags={"risk_security": True, "risk_cross_team": True},
        complexity="high",
        expected_accepted=True,
        expected_base_role="developer",
        expected_overlays=["infra"],
        expected_risk_keys=["risk_security", "risk_cross_team"],
        expected_scope_keywords=["ci/cd", "runners", "infrastructure"],
        expected_impacted_count_min=2,
        expected_expert_classes=["technical"],
        expected_min_experts=1,
        expected_min_plan_steps=4,
        expected_goal_keywords=["ci/cd", "self-hosted", "runners"],
    ),
]


def load_routing_dataset() -> list[RoutingEvalCase]:
    """Return the labeled routing evaluation dataset."""
    return list(ROUTING_DATASET)
