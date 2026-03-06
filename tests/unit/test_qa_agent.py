"""Unit tests for QA Agent (Story 1.6).

Architecture reference: thestudioarc/14-qa-quality-layer.md
"""

from uuid import uuid4

from src.assembler.assembler import QAHandoffMapping
from src.qa.defect import DefectCategory, QADefect, Severity
from src.qa.qa_agent import validate
from src.qa.signals import _build_qa_payload


class TestQAValidationPass:
    """QA passes when all criteria are satisfied with evidence."""

    def test_all_criteria_pass_with_evidence(self) -> None:
        criteria = ["Authentication must pass all tests"]
        handoff = [
            QAHandoffMapping(
                criterion="Authentication must pass all tests",
                validation_steps=["Verify authentication works"],
                source_experts=["sec"],
            ),
        ]
        evidence: dict[str, object] = {
            "test_results": "authentication tests passed",
            "verification": "Verify authentication works - passed",
        }
        result = validate(criteria, handoff, evidence)
        assert result.passed is True
        assert len(result.defects) == 0
        assert result.loopback is None

    def test_empty_evidence_fails(self) -> None:
        criteria = ["Authentication must pass all tests"]
        result = validate(criteria, [], {})
        assert result.passed is False
        assert len(result.defects) > 0


class TestQADefectTaxonomy:
    """Defects classified by 8-category taxonomy."""

    def test_all_categories_exist(self) -> None:
        assert len(DefectCategory) == 8
        assert DefectCategory.INTENT_GAP.value == "intent_gap"
        assert DefectCategory.IMPLEMENTATION_BUG.value == "implementation_bug"
        assert DefectCategory.REGRESSION.value == "regression"
        assert DefectCategory.SECURITY.value == "security"
        assert DefectCategory.PERFORMANCE.value == "performance"
        assert DefectCategory.COMPLIANCE.value == "compliance"
        assert DefectCategory.PARTNER_MISMATCH.value == "partner_mismatch"
        assert DefectCategory.OPERABILITY.value == "operability"

    def test_all_severities_exist(self) -> None:
        assert len(Severity) == 4
        assert Severity.S0_CRITICAL.value == "S0"
        assert Severity.S1_HIGH.value == "S1"
        assert Severity.S2_MEDIUM.value == "S2"
        assert Severity.S3_LOW.value == "S3"

    def test_security_criterion_classified_as_security(self) -> None:
        criteria = ["Security authentication must be enforced"]
        result = validate(criteria, [], {})
        assert len(result.defects) > 0
        assert result.defects[0].category == DefectCategory.SECURITY

    def test_performance_criterion_classified(self) -> None:
        criteria = ["Performance latency must be under 100ms"]
        result = validate(criteria, [], {})
        assert len(result.defects) > 0
        assert result.defects[0].category == DefectCategory.PERFORMANCE


class TestIntentGapBlocking:
    """intent_gap blocks qa_passed — no exception."""

    def test_intent_gap_blocks_pass(self) -> None:
        # Vague criterion triggers intent_gap
        criteria = ["Do stuff"]  # Too short (<10 chars)
        result = validate(criteria, [], {})
        assert result.passed is False
        assert result.has_intent_gap is True
        intent_gaps = [d for d in result.defects if d.category == DefectCategory.INTENT_GAP]
        assert len(intent_gaps) > 0

    def test_no_criteria_triggers_intent_gap(self) -> None:
        result = validate([], [], {})
        assert result.passed is False
        assert result.has_intent_gap is True
        assert result.intent_refinement is not None

    def test_intent_gap_with_other_passing_criteria(self) -> None:
        """Even if other criteria pass, intent_gap blocks overall pass."""
        criteria = [
            "Authentication must pass all tests",
            "X",  # Too short — intent_gap
        ]
        evidence: dict[str, object] = {
            "test_results": "authentication tests passed",
        }
        result = validate(criteria, [], evidence)
        assert result.passed is False
        assert result.has_intent_gap is True


class TestQALoopback:
    """QA failure triggers loopback to Primary Agent."""

    def test_failure_produces_loopback_request(self) -> None:
        criteria = ["Authentication must pass all tests"]
        result = validate(criteria, [], {})
        assert result.passed is False
        assert result.loopback is not None
        assert len(result.loopback.defects) > 0
        assert len(result.loopback.intent_mapping) > 0

    def test_loopback_maps_defects_to_criteria(self) -> None:
        criteria = ["Authentication must pass all tests"]
        result = validate(criteria, [], {})
        assert result.loopback is not None
        # Each defect maps to its acceptance criterion
        for _criterion, descriptions in result.loopback.intent_mapping.items():
            assert len(descriptions) > 0


class TestQAIntentRefinement:
    """QA requests intent refinement for ambiguous criteria."""

    def test_ambiguous_criterion_triggers_refinement(self) -> None:
        criteria = ["Fix it"]  # Vague
        result = validate(criteria, [], {})
        assert result.intent_refinement is not None
        assert len(result.intent_refinement.questions) > 0
        assert result.intent_refinement.source == "qa_agent"

    def test_missing_criteria_triggers_refinement(self) -> None:
        result = validate([], [], {})
        assert result.intent_refinement is not None
        assert "No acceptance criteria" in result.intent_refinement.questions[0]


class TestQASignalPayload:
    """QA signal emission structure."""

    def test_qa_passed_payload(self) -> None:
        tp_id = uuid4()
        corr_id = uuid4()
        payload = _build_qa_payload("qa_passed", tp_id, corr_id)
        import json
        data = json.loads(payload)
        assert data["event"] == "qa_passed"
        assert data["taskpacket_id"] == str(tp_id)
        assert data["correlation_id"] == str(corr_id)
        assert "timestamp" in data

    def test_qa_defect_payload_includes_defects(self) -> None:
        tp_id = uuid4()
        corr_id = uuid4()
        defects = [
            QADefect(
                category=DefectCategory.SECURITY,
                severity=Severity.S0_CRITICAL,
                description="Auth bypass found",
                acceptance_criterion="Auth must be enforced",
            ),
        ]
        payload = _build_qa_payload("qa_defect", tp_id, corr_id, defects)
        import json
        data = json.loads(payload)
        assert data["event"] == "qa_defect"
        assert len(data["defects"]) == 1
        assert data["defects"][0]["category"] == "security"
        assert data["defects"][0]["severity"] == "S0"

    def test_defect_requires_category_and_severity(self) -> None:
        """QA defect must include category + severity — schema enforcement."""
        defect = QADefect(
            category=DefectCategory.IMPLEMENTATION_BUG,
            severity=Severity.S2_MEDIUM,
            description="Test failure",
            acceptance_criterion="Tests must pass",
        )
        assert defect.category == DefectCategory.IMPLEMENTATION_BUG
        assert defect.severity == Severity.S2_MEDIUM
