"""Tests for ReviewContext model and system prompt generation (Epic 24 Story 24.1)."""

from uuid import uuid4

from src.approval.review_context import (
    EvidenceHighlights,
    IntentSummary,
    QASummary,
    ReviewContext,
    TaskPacketSummary,
    VerificationCheckResult,
    VerificationSummary,
)


def _make_context(**overrides) -> ReviewContext:
    defaults = {
        "taskpacket": TaskPacketSummary(
            taskpacket_id=uuid4(),
            repo="test-org/test-repo",
            status="awaiting_approval",
            repo_tier="suggest",
            issue_title="Fix login timeout",
            issue_number=42,
        ),
        "intent": IntentSummary(
            goal="Fix SSO login timeout",
            acceptance_criteria=[
                "Login completes in 5s",
                "Error shown on timeout",
            ],
            version=1,
        ),
        "verification": VerificationSummary(
            passed=True,
            checks=[
                VerificationCheckResult(name="ruff", passed=True),
                VerificationCheckResult(name="pytest", passed=True),
            ],
        ),
        "qa": QASummary(passed=True, defect_count=0),
        "evidence": EvidenceHighlights(
            files_changed=["src/auth/sso.py", "tests/test_sso.py"],
            agent_summary="Reduced pool timeout to 5s",
        ),
        "pr_url": "https://github.com/test-org/test-repo/pull/42",
    }
    defaults.update(overrides)
    return ReviewContext(**defaults)


class TestReviewContext:
    def test_model_creation(self):
        ctx = _make_context()
        assert ctx.taskpacket.repo == "test-org/test-repo"
        assert len(ctx.intent.acceptance_criteria) == 2
        assert ctx.verification.passed is True
        assert ctx.qa.passed is True

    def test_default_values(self):
        ctx = ReviewContext(
            taskpacket=TaskPacketSummary(taskpacket_id=uuid4()),
        )
        assert ctx.intent.goal == ""
        assert ctx.verification.passed is False
        assert ctx.qa.defect_count == 0
        assert ctx.evidence.files_changed == []

    def test_to_system_prompt_contains_key_info(self):
        ctx = _make_context()
        prompt = ctx.to_system_prompt()

        assert "Fix SSO login timeout" in prompt
        assert "test-org/test-repo" in prompt
        assert "suggest" in prompt
        assert "Login completes in 5s" in prompt
        assert "src/auth/sso.py" in prompt
        assert "ruff" in prompt
        assert "Passed: True" in prompt

    def test_to_system_prompt_empty_criteria(self):
        ctx = _make_context(
            intent=IntentSummary(goal="test", acceptance_criteria=[]),
        )
        prompt = ctx.to_system_prompt()
        assert "(none specified)" in prompt

    def test_to_system_prompt_no_files(self):
        ctx = _make_context(
            evidence=EvidenceHighlights(files_changed=[]),
        )
        prompt = ctx.to_system_prompt()
        assert "(no files changed)" in prompt

    def test_serialization_roundtrip(self):
        ctx = _make_context()
        data = ctx.model_dump(mode="json")
        restored = ReviewContext.model_validate(data)

        assert restored.taskpacket.repo == ctx.taskpacket.repo
        assert restored.intent.goal == ctx.intent.goal
        assert len(restored.verification.checks) == 2

    def test_verification_checks_detail(self):
        ctx = _make_context(
            verification=VerificationSummary(
                passed=False,
                checks=[
                    VerificationCheckResult(
                        name="security", passed=False, detail="CVE-2026-001",
                    ),
                ],
            ),
        )
        prompt = ctx.to_system_prompt()
        assert "security" in prompt
        assert "FAIL" in prompt
        assert "CVE-2026-001" in prompt
