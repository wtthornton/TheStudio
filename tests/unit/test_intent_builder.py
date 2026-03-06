"""Unit tests for Intent Builder (Story 0.4).

Tests goal extraction, constraint derivation, acceptance criteria parsing,
non-goals extraction, and versioning logic.
"""


from src.intent.intent_builder import (
    derive_constraints,
    extract_acceptance_criteria,
    extract_goal,
    extract_non_goals,
)
from src.intent.intent_spec import IntentSpecCreate

# --- Goal Extraction Tests ---


class TestGoalExtraction:
    def test_clear_title_with_body(self) -> None:
        """Test case 1: Clear issue with title + body."""
        goal = extract_goal(
            "Add user email verification",
            "Users should receive a verification email after registration.\n\n"
            "## Requirements\n- Send email within 5 minutes",
        )
        assert "Add user email verification" in goal
        assert "verification email" in goal

    def test_vague_title(self) -> None:
        """Test case 2: Vague issue."""
        goal = extract_goal(
            "Improve performance",
            "The app is slow. We need to optimize database queries and caching.\n\n"
            "Some more details here.",
        )
        assert "Improve performance" in goal
        assert len(goal) > len("Improve performance")

    def test_title_only(self) -> None:
        goal = extract_goal("Fix login bug", "")
        assert goal == "Fix login bug"

    def test_body_with_heading_skipped(self) -> None:
        goal = extract_goal(
            "Update API",
            "## Background\n\nThe API endpoint needs updating for new requirements.",
        )
        assert "Update API" in goal
        # Should include the paragraph, not the heading
        assert "endpoint needs updating" in goal

    def test_body_with_code_block_skipped(self) -> None:
        goal = extract_goal(
            "Fix bug",
            "```python\nprint('hello')\n```\n\nThe actual description is here.",
        )
        assert "Fix bug" in goal
        assert "actual description" in goal


# --- Constraint Derivation Tests ---


class TestConstraintDerivation:
    def test_no_risk_flags(self) -> None:
        """Test case 5: No risks -> default constraint only."""
        constraints = derive_constraints({
            "risk_security": False,
            "risk_breaking": False,
            "risk_cross_team": False,
            "risk_data": False,
        })
        assert len(constraints) == 1
        assert "tests" in constraints[0].lower()

    def test_security_risk(self) -> None:
        """Test case 3: Security risk -> credential constraint."""
        constraints = derive_constraints({
            "risk_security": True,
            "risk_breaking": False,
            "risk_cross_team": False,
            "risk_data": False,
        })
        assert len(constraints) > 1
        assert any("credential" in c.lower() for c in constraints)

    def test_multiple_risks(self) -> None:
        """Test case 4: Multiple risks -> multiple constraints."""
        constraints = derive_constraints({
            "risk_security": True,
            "risk_breaking": True,
            "risk_cross_team": False,
            "risk_data": False,
        })
        assert len(constraints) >= 3  # default + security(2) + breaking(2)

    def test_all_risks(self) -> None:
        constraints = derive_constraints({
            "risk_security": True,
            "risk_breaking": True,
            "risk_cross_team": True,
            "risk_data": True,
        })
        assert len(constraints) >= 5

    def test_none_risk_flags(self) -> None:
        constraints = derive_constraints(None)
        assert len(constraints) == 1


# --- Acceptance Criteria Tests ---


class TestAcceptanceCriteria:
    def test_checkbox_extraction(self) -> None:
        """Test case 1: Issue with checkboxes."""
        body = (
            "## Acceptance Criteria\n"
            "- [ ] Users can register with email\n"
            "- [ ] Verification email sent within 5 minutes\n"
            "- [x] Already done: basic form exists\n"
        )
        criteria = extract_acceptance_criteria(body)
        assert len(criteria) == 3

    def test_bullet_list_under_heading(self) -> None:
        body = (
            "## Background\nSome context.\n\n"
            "## Acceptance Criteria\n"
            "- Must handle 100 concurrent users\n"
            "- Response time under 200ms\n\n"
            "## Notes\nExtra info."
        )
        criteria = extract_acceptance_criteria(body)
        assert len(criteria) >= 2

    def test_no_criteria_found(self) -> None:
        criteria = extract_acceptance_criteria("Just a plain description with no structure.")
        assert isinstance(criteria, list)

    def test_fallback_to_bullets(self) -> None:
        body = (
            "Please fix these:\n"
            "- Fix the login flow\n"
            "- Update the dashboard\n"
            "- Add error handling\n"
        )
        criteria = extract_acceptance_criteria(body)
        assert len(criteria) >= 2


# --- Non-Goals Extraction Tests ---


class TestNonGoals:
    def test_out_of_scope_section(self) -> None:
        """Test case 8: Non-goals extraction."""
        body = (
            "## Description\nUpdate the checkout flow.\n\n"
            "Out of scope: mobile app changes\n\n"
            "## Notes\nMore info."
        )
        non_goals = extract_non_goals(body)
        assert len(non_goals) >= 1
        assert any("mobile" in ng.lower() for ng in non_goals)

    def test_wont_fix_pattern(self) -> None:
        body = "Won't implement: dark mode support"
        non_goals = extract_non_goals(body)
        assert len(non_goals) >= 1

    def test_no_non_goals(self) -> None:
        non_goals = extract_non_goals("Just a normal issue description.")
        assert non_goals == []

    def test_non_goals_with_bullets(self) -> None:
        body = (
            "Non-goals:\n"
            "- Mobile support\n"
            "- Internationalization\n"
        )
        non_goals = extract_non_goals(body)
        assert len(non_goals) >= 1


# --- IntentSpec Model Tests ---


class TestIntentSpecModel:
    def test_create_model(self) -> None:
        from uuid import uuid4

        data = IntentSpecCreate(
            taskpacket_id=uuid4(),
            version=1,
            goal="Implement feature X",
            constraints=["Must include tests"],
            acceptance_criteria=["Feature X works"],
            non_goals=["No mobile support"],
        )
        assert data.goal == "Implement feature X"
        assert len(data.constraints) == 1

    def test_default_version(self) -> None:
        from uuid import uuid4

        data = IntentSpecCreate(
            taskpacket_id=uuid4(),
            goal="Fix bug",
        )
        assert data.version == 1
        assert data.constraints == []
        assert data.acceptance_criteria == []
        assert data.non_goals == []
