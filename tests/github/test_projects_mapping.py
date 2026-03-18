"""Tests for GitHub Projects v2 field mapping (Epic 29 AC 2-4)."""


from src.github.projects_mapping import (
    REQUIRED_FIELDS,
    STATUS_MAPPING,
    map_risk,
    map_status,
    map_tier,
)


class TestStatusMapping:
    """AC 2: TaskPacket status → Projects v2 Status field."""

    def test_received_maps_to_queued(self) -> None:
        assert map_status("RECEIVED") == "Queued"

    def test_enriched_maps_to_queued(self) -> None:
        assert map_status("ENRICHED") == "Queued"

    def test_intent_built_maps_to_in_progress(self) -> None:
        assert map_status("INTENT_BUILT") == "In Progress"

    def test_in_progress_maps_to_in_progress(self) -> None:
        assert map_status("IN_PROGRESS") == "In Progress"

    def test_verification_passed_maps_to_in_progress(self) -> None:
        assert map_status("VERIFICATION_PASSED") == "In Progress"

    def test_awaiting_approval_maps_to_in_review(self) -> None:
        assert map_status("AWAITING_APPROVAL") == "In Review"

    def test_clarification_requested_maps_to_blocked(self) -> None:
        assert map_status("CLARIFICATION_REQUESTED") == "Blocked"

    def test_human_review_required_maps_to_blocked(self) -> None:
        assert map_status("HUMAN_REVIEW_REQUIRED") == "Blocked"

    def test_published_maps_to_done(self) -> None:
        assert map_status("PUBLISHED") == "Done"

    def test_failed_maps_to_done(self) -> None:
        assert map_status("FAILED") == "Done"

    def test_rejected_maps_to_done(self) -> None:
        assert map_status("REJECTED") == "Done"

    def test_unknown_status_returns_none(self) -> None:
        assert map_status("NONEXISTENT") is None

    def test_all_statuses_have_mapping(self) -> None:
        """Every mapped status produces a valid Projects v2 value."""
        valid_values = {"Queued", "In Progress", "In Review", "Blocked", "Done"}
        for status, value in STATUS_MAPPING.items():
            assert value in valid_values, f"{status} maps to unknown value {value}"


class TestTierMapping:
    """AC 3: Trust tier → Automation Tier field."""

    def test_observe(self) -> None:
        assert map_tier("observe") == "Observe"

    def test_suggest(self) -> None:
        assert map_tier("suggest") == "Suggest"

    def test_execute(self) -> None:
        assert map_tier("execute") == "Execute"

    def test_case_insensitive(self) -> None:
        assert map_tier("EXECUTE") == "Execute"
        assert map_tier("Suggest") == "Suggest"

    def test_unknown_tier(self) -> None:
        assert map_tier("unknown") is None


class TestRiskTierMapping:
    """AC 4: Complexity index → Risk Tier field."""

    def test_low(self) -> None:
        assert map_risk("low") == "Low"

    def test_medium(self) -> None:
        assert map_risk("medium") == "Medium"

    def test_high(self) -> None:
        assert map_risk("high") == "High"

    def test_case_insensitive(self) -> None:
        assert map_risk("HIGH") == "High"

    def test_unknown_risk(self) -> None:
        assert map_risk("critical") is None


class TestRequiredFields:
    """AC 8: Required fields for compliance."""

    def test_required_fields_count(self) -> None:
        assert len(REQUIRED_FIELDS) == 6

    def test_status_required(self) -> None:
        assert "Status" in REQUIRED_FIELDS

    def test_automation_tier_required(self) -> None:
        assert "Automation Tier" in REQUIRED_FIELDS

    def test_risk_tier_required(self) -> None:
        assert "Risk Tier" in REQUIRED_FIELDS

    def test_priority_required(self) -> None:
        assert "Priority" in REQUIRED_FIELDS

    def test_owner_required(self) -> None:
        assert "Owner" in REQUIRED_FIELDS

    def test_repo_required(self) -> None:
        assert "Repo" in REQUIRED_FIELDS
