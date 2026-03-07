"""Unit tests for Publisher (Story 0.7).

Tests evidence comment formatting, idempotency guard, lifecycle labels,
and publish orchestration with mocked GitHub API.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.agent.evidence import EvidenceBundle
from src.intent.intent_spec import IntentSpecRead
from src.models.taskpacket import TaskPacketRead, TaskPacketStatus
from src.publisher.evidence_comment import (
    EVIDENCE_COMMENT_MARKER,
    format_evidence_comment,
)
from src.publisher.publisher import (
    LABEL_DONE,
    LABEL_IN_PROGRESS,
    _branch_name,
    _pr_title,
)
from src.verification.gate import VerificationResult
from src.verification.runners.base import CheckResult

# --- Fixtures ---


def _make_taskpacket(**overrides: object) -> TaskPacketRead:
    defaults = {
        "id": uuid4(),
        "repo": "acme/widgets",
        "issue_id": 42,
        "delivery_id": "abc123",
        "correlation_id": uuid4(),
        "status": TaskPacketStatus.VERIFICATION_PASSED,
        "scope": {"type": "feature"},
        "risk_flags": {},
        "complexity_index": {"score": 0.2, "band": "low", "dimensions": {"scope_breadth": 1, "risk_flag_count": 0, "dependency_count": 1, "lines_estimate": 50, "expert_coverage": 0}},
        "context_packs": [],
        "intent_spec_id": uuid4(),
        "intent_version": 1,
        "loopback_count": 0,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return TaskPacketRead(**defaults)  # type: ignore[arg-type]


def _make_intent(**overrides: object) -> IntentSpecRead:
    defaults = {
        "id": uuid4(),
        "taskpacket_id": uuid4(),
        "version": 1,
        "goal": "Add health endpoint returning 200",
        "constraints": ["No new deps"],
        "acceptance_criteria": ["GET /health returns 200"],
        "non_goals": ["Auth on health endpoint"],
        "created_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return IntentSpecRead(**defaults)  # type: ignore[arg-type]


def _make_evidence(tp_id: object = None) -> EvidenceBundle:
    return EvidenceBundle(
        taskpacket_id=tp_id or uuid4(),
        intent_version=1,
        files_changed=["src/health.py", "tests/test_health.py"],
        agent_summary="Added health endpoint",
    )


def _make_verification(passed: bool = True) -> VerificationResult:
    return VerificationResult(
        passed=passed,
        checks=[
            CheckResult(name="ruff", passed=True, details="clean"),
            CheckResult(name="pytest", passed=passed, details="5 passed" if passed else "1 failed"),
        ],
    )


# --- Branch Name Tests ---


class TestBranchName:
    def test_deterministic(self) -> None:
        tp_id = uuid4()
        assert _branch_name(tp_id, 1) == _branch_name(tp_id, 1)

    def test_includes_version(self) -> None:
        tp_id = uuid4()
        assert "/v1" in _branch_name(tp_id, 1)
        assert "/v2" in _branch_name(tp_id, 2)

    def test_different_ids_different_branches(self) -> None:
        assert _branch_name(uuid4(), 1) != _branch_name(uuid4(), 1)


# --- PR Title Tests ---


class TestPrTitle:
    def test_short_goal(self) -> None:
        title = _pr_title("Fix login bug")
        assert title == "[TheStudio] Fix login bug"

    def test_truncates_long_goal(self) -> None:
        long_goal = "A" * 100
        title = _pr_title(long_goal)
        assert len(title) <= 72

    def test_includes_prefix(self) -> None:
        assert _pr_title("anything").startswith("[TheStudio] ")


# --- Evidence Comment Tests ---


class TestEvidenceComment:
    def test_contains_marker(self) -> None:
        comment = format_evidence_comment(
            _make_evidence(), _make_intent(), _make_verification()
        )
        assert EVIDENCE_COMMENT_MARKER in comment

    def test_contains_taskpacket_id(self) -> None:
        tp_id = uuid4()
        evidence = _make_evidence(tp_id=tp_id)
        comment = format_evidence_comment(evidence, _make_intent(), _make_verification())
        assert str(tp_id) in comment

    def test_contains_intent_goal(self) -> None:
        intent = _make_intent(goal="Implement caching layer")
        comment = format_evidence_comment(_make_evidence(), intent, _make_verification())
        assert "Implement caching layer" in comment

    def test_contains_verification_status_passed(self) -> None:
        comment = format_evidence_comment(
            _make_evidence(), _make_intent(), _make_verification(passed=True)
        )
        assert "PASSED" in comment

    def test_contains_verification_status_failed(self) -> None:
        comment = format_evidence_comment(
            _make_evidence(), _make_intent(), _make_verification(passed=False)
        )
        assert "FAILED" in comment

    def test_contains_files_changed(self) -> None:
        comment = format_evidence_comment(
            _make_evidence(), _make_intent(), _make_verification()
        )
        assert "src/health.py" in comment
        assert "tests/test_health.py" in comment

    def test_contains_acceptance_criteria(self) -> None:
        intent = _make_intent(acceptance_criteria=["GET /health returns 200", "JSON body"])
        comment = format_evidence_comment(_make_evidence(), intent, _make_verification())
        assert "GET /health returns 200" in comment
        assert "JSON body" in comment

    def test_contains_check_results(self) -> None:
        comment = format_evidence_comment(
            _make_evidence(), _make_intent(), _make_verification()
        )
        assert "ruff" in comment
        assert "pytest" in comment


# --- Publisher Orchestration Tests ---


class TestPublish:
    @pytest.mark.asyncio
    async def test_creates_new_pr(self) -> None:
        """Happy path: no existing PR, creates draft PR with evidence."""
        tp_id = uuid4()
        tp = _make_taskpacket(id=tp_id)
        intent = _make_intent(taskpacket_id=tp_id)
        evidence = _make_evidence(tp_id=tp_id)
        verification = _make_verification(passed=True)

        mock_github = AsyncMock()
        mock_github.find_pr_by_head.return_value = None
        mock_github.get_default_branch.return_value = "main"
        mock_github.get_branch_sha.return_value = "abc123sha"
        mock_github.create_pull_request.return_value = {
            "number": 99,
            "html_url": "https://github.com/acme/widgets/pull/99",
        }
        mock_github.add_comment.return_value = {"id": 555}
        mock_github.add_labels.return_value = []
        mock_github.remove_label.return_value = None

        with (
            patch("src.publisher.publisher.get_by_id", return_value=tp),
            patch("src.publisher.publisher.get_latest_for_taskpacket", return_value=intent),
            patch("src.publisher.publisher.update_status", return_value=tp),
        ):
            from src.publisher.publisher import publish

            result = await publish(AsyncMock(), tp_id, evidence, verification, mock_github)

        assert result.created is True
        assert result.pr_number == 99
        assert "pull/99" in result.pr_url
        mock_github.create_branch.assert_called_once()
        mock_github.create_pull_request.assert_called_once()
        mock_github.add_comment.assert_called_once()

    @pytest.mark.asyncio
    async def test_idempotency_updates_existing_pr(self) -> None:
        """Idempotency: if PR exists for same branch, update comment instead."""
        tp_id = uuid4()
        tp = _make_taskpacket(id=tp_id)
        intent = _make_intent(taskpacket_id=tp_id)
        evidence = _make_evidence(tp_id=tp_id)
        verification = _make_verification(passed=True)

        existing_pr = {
            "number": 42,
            "html_url": "https://github.com/acme/widgets/pull/42",
        }
        mock_github = AsyncMock()
        mock_github.find_pr_by_head.return_value = existing_pr

        # Mock the _client for comment search (httpx response has sync .json())
        mock_resp = MagicMock()
        mock_resp.json.return_value = [
            {"id": 100, "body": f"old comment {EVIDENCE_COMMENT_MARKER}"}
        ]
        mock_resp.raise_for_status = MagicMock()
        # _client.get is async, but returns a sync-like response
        mock_github._client = AsyncMock()
        mock_github._client.get.return_value = mock_resp
        mock_github.update_comment.return_value = {"id": 100}

        with (
            patch("src.publisher.publisher.get_by_id", return_value=tp),
            patch("src.publisher.publisher.get_latest_for_taskpacket", return_value=intent),
            patch("src.publisher.publisher.update_status", return_value=tp),
        ):
            from src.publisher.publisher import publish

            result = await publish(AsyncMock(), tp_id, evidence, verification, mock_github)

        assert result.created is False
        assert result.pr_number == 42
        mock_github.create_pull_request.assert_not_called()
        mock_github.update_comment.assert_called_once()

    @pytest.mark.asyncio
    async def test_rejects_failed_verification(self) -> None:
        """Cannot publish when verification has not passed."""
        tp_id = uuid4()
        tp = _make_taskpacket(id=tp_id)
        verification = _make_verification(passed=False)

        with patch("src.publisher.publisher.get_by_id", return_value=tp):
            from src.publisher.publisher import publish

            with pytest.raises(ValueError, match="verification has not passed"):
                await publish(
                    AsyncMock(), tp_id, _make_evidence(tp_id=tp_id), verification, AsyncMock()
                )

    @pytest.mark.asyncio
    async def test_no_taskpacket_raises(self) -> None:
        with patch("src.publisher.publisher.get_by_id", return_value=None):
            from src.publisher.publisher import publish

            with pytest.raises(ValueError, match="not found"):
                await publish(
                    AsyncMock(),
                    uuid4(),
                    _make_evidence(),
                    _make_verification(),
                    AsyncMock(),
                )

    @pytest.mark.asyncio
    async def test_lifecycle_labels(self) -> None:
        """Verifies lifecycle label transitions: in-progress -> done."""
        tp_id = uuid4()
        tp = _make_taskpacket(id=tp_id)
        intent = _make_intent(taskpacket_id=tp_id)

        mock_github = AsyncMock()
        mock_github.find_pr_by_head.return_value = None
        mock_github.get_default_branch.return_value = "main"
        mock_github.get_branch_sha.return_value = "sha"
        mock_github.create_pull_request.return_value = {
            "number": 1,
            "html_url": "https://github.com/acme/widgets/pull/1",
        }
        mock_github.add_comment.return_value = {"id": 1}
        mock_github.add_labels.return_value = []
        mock_github.remove_label.return_value = None

        with (
            patch("src.publisher.publisher.get_by_id", return_value=tp),
            patch("src.publisher.publisher.get_latest_for_taskpacket", return_value=intent),
            patch("src.publisher.publisher.update_status", return_value=tp),
        ):
            from src.publisher.publisher import publish

            await publish(
                AsyncMock(), tp_id, _make_evidence(tp_id=tp_id), _make_verification(), mock_github
            )

        # Should add in-progress, then remove it, then add done, then reconcile tier labels
        label_calls = mock_github.add_labels.call_args_list
        assert any(LABEL_IN_PROGRESS in str(call) for call in label_calls)
        assert any(LABEL_DONE in str(call) for call in label_calls)
        # remove_label called for agent:in-progress and for tier reconciliation
        assert mock_github.remove_label.call_count >= 1
