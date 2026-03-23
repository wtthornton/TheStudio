"""Tests for evidence comment handling of remote verification checks (Story 40.12).

Verifies that the evidence comment builder correctly renders remote
verification check names (install, remote_ruff, remote_pytest,
container_verify) in both Markdown and JSON formats.
"""

from uuid import UUID, uuid4

import pytest

from src.agent.evidence import EvidenceBundle
from src.intent.intent_spec import IntentSpecRead
from src.publisher.evidence_comment import (
    EVIDENCE_COMMENT_MARKER,
    format_evidence_comment,
    format_evidence_json,
    format_full_evidence_comment,
    QAResultSummary,
)
from src.verification.gate import VerificationResult
from src.verification.runners.base import CheckResult


def _make_evidence(taskpacket_id: UUID | None = None) -> EvidenceBundle:
    """Create a minimal EvidenceBundle for testing."""
    return EvidenceBundle(
        taskpacket_id=taskpacket_id or uuid4(),
        intent_version=1,
        loopback_attempt=0,
        files_changed=["src/main.py", "tests/test_main.py"],
    )


def _make_intent() -> IntentSpecRead:
    """Create a minimal IntentSpecRead for testing."""
    return IntentSpecRead(
        goal="Fix the bug in main module",
        constraints=["No breaking changes"],
        invariants=[],
        acceptance_criteria=["Tests pass", "No lint errors"],
        non_goals=[],
        assumptions=[],
        version=1,
    )


class TestRemoteCheckNames:
    """Verify remote verification check names render correctly."""

    def test_remote_checks_in_markdown(self) -> None:
        """Remote check names appear in the Markdown evidence comment."""
        evidence = _make_evidence()
        intent = _make_intent()
        verification = VerificationResult(
            passed=True,
            checks=[
                CheckResult(name="install", passed=True, details="", duration_ms=1200),
                CheckResult(name="remote_ruff", passed=True, details="", duration_ms=500),
                CheckResult(name="remote_pytest", passed=True, details="", duration_ms=3000),
            ],
        )

        comment = format_evidence_comment(evidence, intent, verification)

        assert EVIDENCE_COMMENT_MARKER in comment
        assert "install" in comment
        assert "remote_ruff" in comment
        assert "remote_pytest" in comment
        assert "PASSED" in comment

    def test_remote_checks_failure_in_markdown(self) -> None:
        """Failed remote checks show FAILED status in Markdown."""
        evidence = _make_evidence()
        intent = _make_intent()
        verification = VerificationResult(
            passed=False,
            checks=[
                CheckResult(name="install", passed=True, details=""),
                CheckResult(name="remote_ruff", passed=False, details="3 lint errors"),
                CheckResult(name="remote_pytest", passed=False, details="2 tests failed"),
            ],
        )

        comment = format_evidence_comment(evidence, intent, verification)

        assert "| remote_ruff | FAILED |" in comment
        assert "| remote_pytest | FAILED |" in comment
        assert "3 lint errors" in comment
        assert "2 tests failed" in comment

    def test_container_verify_check_in_markdown(self) -> None:
        """Container-level error check renders in Markdown."""
        evidence = _make_evidence()
        intent = _make_intent()
        verification = VerificationResult(
            passed=False,
            checks=[
                CheckResult(
                    name="container_verify",
                    passed=False,
                    details="Container timed out after 900s",
                ),
            ],
        )

        comment = format_evidence_comment(evidence, intent, verification)

        assert "container_verify" in comment
        assert "FAILED" in comment
        assert "Container timed out" in comment

    def test_remote_checks_in_full_evidence_comment(self) -> None:
        """Remote checks render in the full evidence comment format."""
        evidence = _make_evidence()
        intent = _make_intent()
        correlation_id = uuid4()
        verification = VerificationResult(
            passed=True,
            checks=[
                CheckResult(name="install", passed=True, details=""),
                CheckResult(name="remote_ruff", passed=True, details=""),
                CheckResult(name="remote_pytest", passed=True, details=""),
            ],
        )

        comment = format_full_evidence_comment(
            evidence, intent, verification, correlation_id,
        )

        assert "install" in comment
        assert "remote_ruff" in comment
        assert "remote_pytest" in comment

    def test_remote_checks_in_evidence_json(self) -> None:
        """Remote check names are preserved in EvidencePayload JSON."""
        evidence = _make_evidence()
        intent = _make_intent()
        verification = VerificationResult(
            passed=True,
            checks=[
                CheckResult(name="install", passed=True, details="", duration_ms=100),
                CheckResult(name="remote_ruff", passed=True, details="", duration_ms=50),
                CheckResult(name="remote_pytest", passed=True, details="", duration_ms=200),
            ],
        )

        payload = format_evidence_json(
            evidence=evidence,
            intent=intent,
            verification=verification,
        )

        assert payload.gate_results is not None
        assert payload.gate_results.verification_passed is True
        check_names = [c.name for c in payload.gate_results.checks]
        assert "install" in check_names
        assert "remote_ruff" in check_names
        assert "remote_pytest" in check_names

    def test_remote_checks_failure_in_evidence_json(self) -> None:
        """Failed remote checks are captured in EvidencePayload."""
        evidence = _make_evidence()
        verification = VerificationResult(
            passed=False,
            checks=[
                CheckResult(name="install", passed=True, details=""),
                CheckResult(name="remote_ruff", passed=True, details=""),
                CheckResult(name="remote_pytest", passed=False, details="FAILED tests/test_main.py"),
            ],
        )

        payload = format_evidence_json(
            evidence=evidence,
            verification=verification,
        )

        assert payload.gate_results is not None
        assert payload.gate_results.verification_passed is False
        failed_checks = [c for c in payload.gate_results.checks if not c.passed]
        assert len(failed_checks) == 1
        assert failed_checks[0].name == "remote_pytest"
        assert "FAILED" in (failed_checks[0].details or "")

    def test_mixed_local_and_remote_checks(self) -> None:
        """Evidence handles a mix of local and remote checks."""
        evidence = _make_evidence()
        intent = _make_intent()
        verification = VerificationResult(
            passed=True,
            checks=[
                CheckResult(name="ruff", passed=True, details=""),
                CheckResult(name="remote_ruff", passed=True, details=""),
                CheckResult(name="pytest", passed=True, details=""),
                CheckResult(name="remote_pytest", passed=True, details=""),
            ],
        )

        comment = format_evidence_comment(evidence, intent, verification)

        assert "| ruff | PASSED |" in comment
        assert "| remote_ruff | PASSED |" in comment
        assert "| pytest | PASSED |" in comment
        assert "| remote_pytest | PASSED |" in comment

    def test_empty_checks_handled(self) -> None:
        """Evidence comment handles empty check list."""
        evidence = _make_evidence()
        intent = _make_intent()
        verification = VerificationResult(passed=True, checks=[])

        comment = format_evidence_comment(evidence, intent, verification)

        assert EVIDENCE_COMMENT_MARKER in comment
        # Empty checks table shows placeholder
        assert "| - | - | - |" in comment
