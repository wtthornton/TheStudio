"""Unit tests for context pre-scan (Epic 36, Story 36.4)."""

from src.context.prescan import prescan_issue


class TestPrescanOutput:
    def test_returns_expected_shape(self) -> None:
        result = prescan_issue("Fix bug", "Simple fix in src/app.py")
        assert "file_count_estimate" in result
        assert "complexity_hint" in result
        assert "cost_estimate_range" in result
        assert isinstance(result["file_count_estimate"], int)
        assert result["complexity_hint"] in ("low", "medium", "high")
        assert "min" in result["cost_estimate_range"]
        assert "max" in result["cost_estimate_range"]

    def test_file_count_from_paths(self) -> None:
        result = prescan_issue(
            "Update multiple files",
            "Need to change src/models/task.py and src/ingress/handler.py and tests/test_task.py",
        )
        assert result["file_count_estimate"] >= 3

    def test_minimum_file_count_is_one(self) -> None:
        result = prescan_issue("Fix typo", "Small change")
        assert result["file_count_estimate"] >= 1


class TestComplexityHints:
    def test_simple_bug_is_low(self) -> None:
        result = prescan_issue(
            "Fix typo in README",
            "Small typo on line 5",
            labels=["bug"],
        )
        assert result["complexity_hint"] == "low"

    def test_migration_is_high(self) -> None:
        result = prescan_issue(
            "Database migration for new schema",
            "Need to add migration for authentication table with security constraints. "
            "This is a breaking change that affects the database schema.",
            labels=["migration", "breaking"],
        )
        assert result["complexity_hint"] == "high"

    def test_api_endpoint_is_at_least_medium(self) -> None:
        result = prescan_issue(
            "Add new API endpoint",
            "Create a new REST endpoint for the dashboard.",
        )
        assert result["complexity_hint"] in ("medium", "high")

    def test_long_body_increases_complexity(self) -> None:
        long_body = "x " * 1500  # >2000 chars
        result = prescan_issue("Task", long_body)
        # Long body alone should bump to at least medium
        assert result["complexity_hint"] in ("medium", "high")

    def test_security_label_increases_complexity(self) -> None:
        result = prescan_issue(
            "Fix issue", "Simple fix",
            labels=["security"],
        )
        assert result["complexity_hint"] in ("medium", "high")


class TestCostEstimates:
    def test_low_complexity_cost_range(self) -> None:
        result = prescan_issue("Fix typo", "Small change", labels=["bug"])
        assert result["cost_estimate_range"]["min"] == 0.05
        assert result["cost_estimate_range"]["max"] == 0.15

    def test_high_complexity_cost_range(self) -> None:
        result = prescan_issue(
            "Database migration",
            "Breaking schema change with security and authentication refactoring",
            labels=["migration", "breaking"],
        )
        assert result["cost_estimate_range"]["min"] == 0.30
        assert result["cost_estimate_range"]["max"] == 1.00

    def test_empty_inputs(self) -> None:
        result = prescan_issue("", "")
        assert result["complexity_hint"] == "low"
        assert result["file_count_estimate"] >= 1
