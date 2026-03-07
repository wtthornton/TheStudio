"""Tests for Story 4.6 & 4.7: Workflow Console API.

4.6: List, Detail, Timeline
4.7: Safe Rerun — rerun-verification, send-to-agent, escalate
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import status

from src.admin.audit import set_audit_service

from src.admin.workflow_console import (
    EscalateResult,
    EscalationInfo,
    RerunResult,
    RetryInfo,
    SendToAgentResult,
    StepStatus,
    TimelineEntry,
    UnsafeRerunError,
    WorkflowConsoleService,
    WorkflowDetail,
    WorkflowListItem,
    WorkflowListResponse,
    WorkflowNotFoundError,
    WorkflowStatus,
    WorkflowStep,
)


class TestWorkflowStatus:
    """Tests for WorkflowStatus enum."""

    def test_status_values(self) -> None:
        """WorkflowStatus has expected values."""
        assert WorkflowStatus.RUNNING.value == "running"
        assert WorkflowStatus.STUCK.value == "stuck"
        assert WorkflowStatus.COMPLETED.value == "completed"
        assert WorkflowStatus.FAILED.value == "failed"
        assert WorkflowStatus.CANCELED.value == "canceled"


class TestTimelineEntry:
    """Tests for TimelineEntry dataclass."""

    def test_to_dict_minimal(self) -> None:
        """to_dict returns minimal dict for basic entry."""
        entry = TimelineEntry(
            step=WorkflowStep.CONTEXT.value,
            status=StepStatus.OK,
        )
        result = entry.to_dict()

        assert result["step"] == "context"
        assert result["status"] == "ok"
        assert result["attempt_count"] == 1

    def test_to_dict_full(self) -> None:
        """to_dict includes all fields when present."""
        now = datetime.now(UTC)
        entry = TimelineEntry(
            step=WorkflowStep.VERIFY.value,
            status=StepStatus.FAILED,
            started_at=now,
            completed_at=now + timedelta(seconds=30),
            duration_ms=30000,
            failure_reason="Lint errors found",
            evidence=["ruff: F401 unused import"],
            attempt_count=2,
        )
        result = entry.to_dict()

        assert result["step"] == "verify"
        assert result["status"] == "failed"
        assert result["failure_reason"] == "Lint errors found"
        assert result["evidence"] == ["ruff: F401 unused import"]
        assert result["attempt_count"] == 2
        assert result["duration_ms"] == 30000


class TestWorkflowListItem:
    """Tests for WorkflowListItem dataclass."""

    def test_to_dict(self) -> None:
        """to_dict converts to API format."""
        repo_id = uuid4()
        now = datetime.now(UTC)
        item = WorkflowListItem(
            workflow_id="homeiq-platform-issue-123",
            repo_id=repo_id,
            repo_name="homeiq/platform",
            status=WorkflowStatus.RUNNING,
            current_step="verify",
            issue_ref="#123",
            started_at=now,
            attempt_count=2,
            complexity="high",
        )
        result = item.to_dict()

        assert result["workflow_id"] == "homeiq-platform-issue-123"
        assert result["repo_id"] == str(repo_id)
        assert result["status"] == "running"
        assert result["current_step"] == "verify"
        assert result["issue_ref"] == "#123"
        assert result["complexity"] == "high"


class TestWorkflowDetail:
    """Tests for WorkflowDetail dataclass."""

    def test_to_dict(self) -> None:
        """to_dict converts full detail to API format."""
        now = datetime.now(UTC)
        detail = WorkflowDetail(
            workflow_id="homeiq-platform-issue-123",
            task_packet_id="tp-123",
            repo_id=None,
            repo_name="homeiq/platform",
            issue_ref="#123",
            status=WorkflowStatus.RUNNING,
            current_step="verify",
            attempt_count=5,
            complexity="high",
            started_at=now,
            completed_at=None,
            timeline=[
                TimelineEntry(step="context", status=StepStatus.OK),
                TimelineEntry(step="verify", status=StepStatus.RUNNING),
            ],
            retry_info=RetryInfo(attempt_count_for_step=2),
            escalation_info=EscalationInfo(human_wait_state=False),
        )
        result = detail.to_dict()

        assert result["workflow_id"] == "homeiq-platform-issue-123"
        assert result["task_packet_id"] == "tp-123"
        assert result["status"] == "running"
        assert len(result["timeline"]) == 2
        assert result["retry_info"]["attempt_count_for_step"] == 2


class TestWorkflowConsoleService:
    """Tests for WorkflowConsoleService."""

    @pytest.fixture
    def service(self) -> WorkflowConsoleService:
        """Create a WorkflowConsoleService for testing."""
        return WorkflowConsoleService(
            temporal_host="localhost:7233",
            namespace="default",
        )

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create mock database session."""
        return AsyncMock()

    def test_extract_repo_name(self, service: WorkflowConsoleService) -> None:
        """_extract_repo_name parses workflow ID correctly."""
        result = service._extract_repo_name("homeiq-platform-issue-123")
        assert result == "homeiq/platform"

    def test_extract_repo_name_unknown(self, service: WorkflowConsoleService) -> None:
        """_extract_repo_name returns unknown for invalid ID."""
        result = service._extract_repo_name("invalid")
        assert result == "unknown/unknown"

    def test_extract_issue_ref(self, service: WorkflowConsoleService) -> None:
        """_extract_issue_ref extracts issue number from ID."""
        result = service._extract_issue_ref("homeiq-platform-issue-123")
        assert result == "#123"

    def test_extract_issue_ref_none(self, service: WorkflowConsoleService) -> None:
        """_extract_issue_ref returns None when no issue in ID."""
        result = service._extract_issue_ref("homeiq-platform-pr-456")
        assert result is None

    def test_determine_status_completed(self, service: WorkflowConsoleService) -> None:
        """_determine_status returns COMPLETED for completed workflows."""
        from temporalio.client import WorkflowExecutionStatus

        mock_wf = AsyncMock()
        mock_wf.status = WorkflowExecutionStatus.COMPLETED

        result = service._determine_status(
            mock_wf,
            datetime.now(UTC),
            timedelta(hours=2),
        )

        assert result == WorkflowStatus.COMPLETED

    def test_determine_status_stuck(self, service: WorkflowConsoleService) -> None:
        """_determine_status returns STUCK for old running workflows."""
        from temporalio.client import WorkflowExecutionStatus

        mock_wf = AsyncMock()
        mock_wf.status = WorkflowExecutionStatus.RUNNING
        mock_wf.start_time = datetime.now(UTC) - timedelta(hours=5)

        result = service._determine_status(
            mock_wf,
            datetime.now(UTC),
            timedelta(hours=2),
        )

        assert result == WorkflowStatus.STUCK

    def test_determine_status_running(self, service: WorkflowConsoleService) -> None:
        """_determine_status returns RUNNING for recent workflows."""
        from temporalio.client import WorkflowExecutionStatus

        mock_wf = AsyncMock()
        mock_wf.status = WorkflowExecutionStatus.RUNNING
        mock_wf.start_time = datetime.now(UTC) - timedelta(minutes=30)

        result = service._determine_status(
            mock_wf,
            datetime.now(UTC),
            timedelta(hours=2),
        )

        assert result == WorkflowStatus.RUNNING

    def test_map_status_filter_none(self, service: WorkflowConsoleService) -> None:
        """_map_status_filter returns all statuses when filter is None."""
        result = service._map_status_filter(None)
        assert len(result) == 5

    def test_map_status_filter_completed(self, service: WorkflowConsoleService) -> None:
        """_map_status_filter maps COMPLETED correctly."""
        from temporalio.client import WorkflowExecutionStatus

        result = service._map_status_filter(WorkflowStatus.COMPLETED)
        assert WorkflowExecutionStatus.COMPLETED in result


class TestListWorkflowsEndpoint:
    """Tests for GET /admin/workflows endpoint."""

    @pytest.fixture
    def mock_console_service(self) -> AsyncMock:
        """Create mock workflow console service."""
        return AsyncMock(spec=WorkflowConsoleService)

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create mock database session."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_list_workflows_empty(
        self, mock_console_service: AsyncMock, mock_session: AsyncMock
    ) -> None:
        """list_workflows returns empty list when no workflows."""
        mock_console_service.list_workflows.return_value = WorkflowListResponse(
            workflows=[],
            total=0,
            filtered_by={},
        )

        from src.admin.router import list_workflows, set_workflow_console_service

        set_workflow_console_service(mock_console_service)
        try:
            result = await list_workflows(mock_session)

            assert result.total == 0
            assert result.workflows == []
        finally:
            set_workflow_console_service(None)

    @pytest.mark.asyncio
    async def test_list_workflows_with_data(
        self, mock_console_service: AsyncMock, mock_session: AsyncMock
    ) -> None:
        """list_workflows returns workflows with correct data."""
        now = datetime.now(UTC)
        mock_console_service.list_workflows.return_value = WorkflowListResponse(
            workflows=[
                WorkflowListItem(
                    workflow_id="wf-1",
                    repo_id=None,
                    repo_name="homeiq/platform",
                    status=WorkflowStatus.RUNNING,
                    current_step="verify",
                    issue_ref="#123",
                    started_at=now,
                ),
            ],
            total=1,
            filtered_by={"status": "running"},
        )

        from src.admin.router import list_workflows, set_workflow_console_service

        set_workflow_console_service(mock_console_service)
        try:
            result = await list_workflows(mock_session)

            assert result.total == 1
            assert result.workflows[0].workflow_id == "wf-1"
            assert result.workflows[0].status == "running"
        finally:
            set_workflow_console_service(None)

    @pytest.mark.asyncio
    async def test_list_workflows_with_filters(
        self, mock_console_service: AsyncMock, mock_session: AsyncMock
    ) -> None:
        """list_workflows passes filters to service."""
        mock_console_service.list_workflows.return_value = WorkflowListResponse(
            workflows=[],
            total=0,
            filtered_by={},
        )

        from src.admin.router import list_workflows, set_workflow_console_service

        repo_id = uuid4()
        set_workflow_console_service(mock_console_service)
        try:
            await list_workflows(
                mock_session,
                repo_id=repo_id,
                status_filter=WorkflowStatus.STUCK,
                age_hours=4,
            )

            mock_console_service.list_workflows.assert_called_once_with(
                mock_session,
                repo_id=repo_id,
                status_filter=WorkflowStatus.STUCK,
                age_hours=4,
            )
        finally:
            set_workflow_console_service(None)


class TestGetWorkflowDetailEndpoint:
    """Tests for GET /admin/workflows/{id} endpoint."""

    @pytest.fixture
    def mock_console_service(self) -> AsyncMock:
        """Create mock workflow console service."""
        return AsyncMock(spec=WorkflowConsoleService)

    @pytest.mark.asyncio
    async def test_get_workflow_detail_success(
        self, mock_console_service: AsyncMock
    ) -> None:
        """get_workflow_detail returns full detail."""
        now = datetime.now(UTC)
        mock_console_service.get_workflow_detail.return_value = WorkflowDetail(
            workflow_id="wf-123",
            task_packet_id="tp-123",
            repo_id=None,
            repo_name="homeiq/platform",
            issue_ref="#123",
            status=WorkflowStatus.RUNNING,
            current_step="verify",
            attempt_count=2,
            complexity="high",
            started_at=now,
            completed_at=None,
            timeline=[
                TimelineEntry(step="context", status=StepStatus.OK),
            ],
            retry_info=RetryInfo(),
            escalation_info=EscalationInfo(),
        )

        from src.admin.router import get_workflow_detail, set_workflow_console_service

        set_workflow_console_service(mock_console_service)
        try:
            result = await get_workflow_detail("wf-123")

            assert result.workflow_id == "wf-123"
            assert result.task_packet_id == "tp-123"
            assert result.status == "running"
            assert len(result.timeline) == 1
        finally:
            set_workflow_console_service(None)

    @pytest.mark.asyncio
    async def test_get_workflow_detail_not_found_404(
        self, mock_console_service: AsyncMock
    ) -> None:
        """get_workflow_detail returns 404 for unknown workflow."""
        mock_console_service.get_workflow_detail.return_value = None

        from fastapi import HTTPException

        from src.admin.router import get_workflow_detail, set_workflow_console_service

        set_workflow_console_service(mock_console_service)
        try:
            with pytest.raises(HTTPException) as exc_info:
                await get_workflow_detail("unknown-wf")

            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        finally:
            set_workflow_console_service(None)

    @pytest.mark.asyncio
    async def test_get_workflow_detail_with_timeline(
        self, mock_console_service: AsyncMock
    ) -> None:
        """get_workflow_detail includes full timeline."""
        now = datetime.now(UTC)
        mock_console_service.get_workflow_detail.return_value = WorkflowDetail(
            workflow_id="wf-123",
            task_packet_id="tp-123",
            repo_id=None,
            repo_name="homeiq/platform",
            issue_ref="#123",
            status=WorkflowStatus.FAILED,
            current_step="verify",
            attempt_count=5,
            complexity="high",
            started_at=now,
            completed_at=None,
            timeline=[
                TimelineEntry(step="context", status=StepStatus.OK),
                TimelineEntry(step="intent", status=StepStatus.OK),
                TimelineEntry(step="experts", status=StepStatus.OK),
                TimelineEntry(step="plan", status=StepStatus.OK),
                TimelineEntry(step="implement", status=StepStatus.OK),
                TimelineEntry(
                    step="verify",
                    status=StepStatus.FAILED,
                    failure_reason="Lint errors",
                    evidence=["ruff: F401"],
                    attempt_count=2,
                ),
            ],
            retry_info=RetryInfo(attempt_count_for_step=2),
            escalation_info=EscalationInfo(),
        )

        from src.admin.router import get_workflow_detail, set_workflow_console_service

        set_workflow_console_service(mock_console_service)
        try:
            result = await get_workflow_detail("wf-123")

            assert len(result.timeline) == 6
            assert result.timeline[5].status == "failed"
            assert result.timeline[5].failure_reason == "Lint errors"
            assert result.retry_info.attempt_count_for_step == 2
        finally:
            set_workflow_console_service(None)


# --- Story 4.7: Workflow Safe Rerun Tests ---


class TestRerunResult:
    """Tests for RerunResult dataclass."""

    def test_rerun_result_creation(self) -> None:
        """RerunResult stores all fields correctly."""
        result = RerunResult(
            workflow_id="wf-123",
            task_packet_id="tp-123",
            previous_step="verify",
            rerun_from_step="verify",
            idempotency_preserved=True,
            signal_sent=True,
        )

        assert result.workflow_id == "wf-123"
        assert result.task_packet_id == "tp-123"
        assert result.idempotency_preserved is True
        assert result.signal_sent is True


class TestSendToAgentResult:
    """Tests for SendToAgentResult dataclass."""

    def test_send_to_agent_result_creation(self) -> None:
        """SendToAgentResult stores all fields correctly."""
        result = SendToAgentResult(
            workflow_id="wf-123",
            task_packet_id="tp-123",
            sent_to_step="implement",
            workspace_reset=True,
            idempotency_preserved=True,
            signal_sent=False,
        )

        assert result.sent_to_step == "implement"
        assert result.workspace_reset is True


class TestEscalateResult:
    """Tests for EscalateResult dataclass."""

    def test_escalate_result_creation(self) -> None:
        """EscalateResult stores all fields correctly."""
        now = datetime.now(UTC)
        result = EscalateResult(
            workflow_id="wf-123",
            task_packet_id="tp-123",
            escalated_at=now,
            trigger="Stuck in verification for 4 hours",
            owner="oncall@example.com",
            signal_sent=True,
        )

        assert result.escalated_at == now
        assert result.owner == "oncall@example.com"


class TestWorkflowConsoleServiceSafeRerun:
    """Tests for WorkflowConsoleService safe rerun methods."""

    @pytest.fixture
    def service(self) -> WorkflowConsoleService:
        """Create a WorkflowConsoleService for testing."""
        return WorkflowConsoleService(
            temporal_host="localhost:7233",
            namespace="default",
        )

    def test_is_safe_rerun_step_verify(self, service: WorkflowConsoleService) -> None:
        """_is_safe_rerun_step returns True for verify."""
        assert service._is_safe_rerun_step("verify") is True

    def test_is_safe_rerun_step_publish_unsafe(
        self, service: WorkflowConsoleService
    ) -> None:
        """_is_safe_rerun_step returns False for publish."""
        assert service._is_safe_rerun_step("publish") is False

    def test_is_safe_rerun_step_unknown(self, service: WorkflowConsoleService) -> None:
        """_is_safe_rerun_step returns False for unknown steps."""
        assert service._is_safe_rerun_step("unknown_step") is False

    def test_validate_rerun_safety_safe_step(
        self, service: WorkflowConsoleService
    ) -> None:
        """_validate_rerun_safety passes for safe steps."""
        service._validate_rerun_safety("verify", "verify")

    def test_validate_rerun_safety_publish_raises(
        self, service: WorkflowConsoleService
    ) -> None:
        """_validate_rerun_safety raises for publish step."""
        with pytest.raises(UnsafeRerunError) as exc_info:
            service._validate_rerun_safety("verify", "publish")

        assert "publish" in exc_info.value.step
        assert "idempotency" in exc_info.value.reason.lower()

    def test_validate_rerun_safety_unknown_step_raises(
        self, service: WorkflowConsoleService
    ) -> None:
        """_validate_rerun_safety raises for unknown target step."""
        with pytest.raises(UnsafeRerunError) as exc_info:
            service._validate_rerun_safety("verify", "unknown_step")

        assert "unknown_step" in exc_info.value.step


class TestRerunVerificationEndpoint:
    """Tests for POST /admin/workflows/{id}/rerun-verification endpoint."""

    @pytest.fixture
    def mock_console_service(self) -> AsyncMock:
        """Create mock workflow console service."""
        return AsyncMock(spec=WorkflowConsoleService)

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def mock_audit_service(self) -> AsyncMock:
        """Create mock audit service."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_rerun_verification_success(
        self,
        mock_console_service: AsyncMock,
        mock_session: AsyncMock,
        mock_audit_service: AsyncMock,
    ) -> None:
        """rerun_verification returns success response."""
        mock_console_service.rerun_verification.return_value = RerunResult(
            workflow_id="wf-123",
            task_packet_id="tp-123",
            previous_step="verify",
            rerun_from_step="verify",
            idempotency_preserved=True,
            signal_sent=True,
        )

        from src.admin.router import (
            RerunVerificationRequest,
            rerun_verification,
            set_workflow_console_service,
        )

        set_workflow_console_service(mock_console_service)
        set_audit_service(mock_audit_service)
        try:
            request = RerunVerificationRequest(
                reason="Lint errors fixed externally",
                actor="admin@example.com",
            )
            result = await rerun_verification("wf-123", request, mock_session)

            assert result.workflow_id == "wf-123"
            assert result.idempotency_preserved is True
            assert "rerun initiated" in result.message.lower()

            mock_console_service.rerun_verification.assert_called_once_with(
                workflow_id="wf-123",
                reason="Lint errors fixed externally",
                actor="admin@example.com",
            )
        finally:
            set_workflow_console_service(None)
            set_audit_service(None)

    @pytest.mark.asyncio
    async def test_rerun_verification_not_found_404(
        self, mock_console_service: AsyncMock, mock_session: AsyncMock
    ) -> None:
        """rerun_verification returns 404 for unknown workflow."""
        mock_console_service.rerun_verification.side_effect = WorkflowNotFoundError(
            "unknown-wf"
        )

        from fastapi import HTTPException

        from src.admin.router import (
            RerunVerificationRequest,
            rerun_verification,
            set_workflow_console_service,
        )

        set_workflow_console_service(mock_console_service)
        try:
            request = RerunVerificationRequest(
                reason="Test rerun",
                actor="admin@example.com",
            )
            with pytest.raises(HTTPException) as exc_info:
                await rerun_verification("unknown-wf", request, mock_session)

            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        finally:
            set_workflow_console_service(None)

    @pytest.mark.asyncio
    async def test_rerun_verification_unsafe_400(
        self, mock_console_service: AsyncMock, mock_session: AsyncMock
    ) -> None:
        """rerun_verification returns 400 for unsafe rerun."""
        mock_console_service.rerun_verification.side_effect = UnsafeRerunError(
            "publish", "Requires idempotency key"
        )

        from fastapi import HTTPException

        from src.admin.router import (
            RerunVerificationRequest,
            rerun_verification,
            set_workflow_console_service,
        )

        set_workflow_console_service(mock_console_service)
        try:
            request = RerunVerificationRequest(
                reason="Test rerun",
                actor="admin@example.com",
            )
            with pytest.raises(HTTPException) as exc_info:
                await rerun_verification("wf-123", request, mock_session)

            assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
            assert "unsafe" in exc_info.value.detail.lower()
        finally:
            set_workflow_console_service(None)


class TestSendToAgentEndpoint:
    """Tests for POST /admin/workflows/{id}/send-to-agent endpoint."""

    @pytest.fixture
    def mock_console_service(self) -> AsyncMock:
        """Create mock workflow console service."""
        return AsyncMock(spec=WorkflowConsoleService)

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def mock_audit_service(self) -> AsyncMock:
        """Create mock audit service."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_send_to_agent_success(
        self,
        mock_console_service: AsyncMock,
        mock_session: AsyncMock,
        mock_audit_service: AsyncMock,
    ) -> None:
        """send_to_agent returns success response."""
        mock_console_service.send_to_agent.return_value = SendToAgentResult(
            workflow_id="wf-123",
            task_packet_id="tp-123",
            sent_to_step="implement",
            workspace_reset=False,
            idempotency_preserved=True,
            signal_sent=True,
        )

        from src.admin.router import (
            SendToAgentRequest,
            send_to_agent,
            set_workflow_console_service,
        )

        set_workflow_console_service(mock_console_service)
        set_audit_service(mock_audit_service)
        try:
            request = SendToAgentRequest(
                reason="Agent needs to fix implementation",
                actor="admin@example.com",
                reset_workspace=False,
            )
            result = await send_to_agent("wf-123", request, mock_session)

            assert result.workflow_id == "wf-123"
            assert result.sent_to_step == "implement"
            assert result.workspace_reset is False

            mock_console_service.send_to_agent.assert_called_once_with(
                workflow_id="wf-123",
                reason="Agent needs to fix implementation",
                actor="admin@example.com",
                reset_workspace=False,
            )
        finally:
            set_workflow_console_service(None)
            set_audit_service(None)

    @pytest.mark.asyncio
    async def test_send_to_agent_with_workspace_reset(
        self,
        mock_console_service: AsyncMock,
        mock_session: AsyncMock,
        mock_audit_service: AsyncMock,
    ) -> None:
        """send_to_agent passes reset_workspace flag."""
        mock_console_service.send_to_agent.return_value = SendToAgentResult(
            workflow_id="wf-123",
            task_packet_id="tp-123",
            sent_to_step="implement",
            workspace_reset=True,
            idempotency_preserved=True,
            signal_sent=True,
        )

        from src.admin.router import (
            SendToAgentRequest,
            send_to_agent,
            set_workflow_console_service,
        )

        set_workflow_console_service(mock_console_service)
        set_audit_service(mock_audit_service)
        try:
            request = SendToAgentRequest(
                reason="Need clean slate",
                actor="admin@example.com",
                reset_workspace=True,
            )
            result = await send_to_agent("wf-123", request, mock_session)

            assert result.workspace_reset is True
        finally:
            set_workflow_console_service(None)
            set_audit_service(None)

    @pytest.mark.asyncio
    async def test_send_to_agent_not_found_404(
        self, mock_console_service: AsyncMock, mock_session: AsyncMock
    ) -> None:
        """send_to_agent returns 404 for unknown workflow."""
        mock_console_service.send_to_agent.side_effect = WorkflowNotFoundError(
            "unknown-wf"
        )

        from fastapi import HTTPException

        from src.admin.router import (
            SendToAgentRequest,
            send_to_agent,
            set_workflow_console_service,
        )

        set_workflow_console_service(mock_console_service)
        try:
            request = SendToAgentRequest(
                reason="Test",
                actor="admin@example.com",
            )
            with pytest.raises(HTTPException) as exc_info:
                await send_to_agent("unknown-wf", request, mock_session)

            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        finally:
            set_workflow_console_service(None)


class TestEscalateEndpoint:
    """Tests for POST /admin/workflows/{id}/escalate endpoint."""

    @pytest.fixture
    def mock_console_service(self) -> AsyncMock:
        """Create mock workflow console service."""
        return AsyncMock(spec=WorkflowConsoleService)

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def mock_audit_service(self) -> AsyncMock:
        """Create mock audit service."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_escalate_success(
        self,
        mock_console_service: AsyncMock,
        mock_session: AsyncMock,
        mock_audit_service: AsyncMock,
    ) -> None:
        """escalate_workflow returns success response."""
        now = datetime.now(UTC)
        mock_console_service.escalate.return_value = EscalateResult(
            workflow_id="wf-123",
            task_packet_id="tp-123",
            escalated_at=now,
            trigger="Stuck for 4 hours",
            owner="oncall@example.com",
            signal_sent=True,
        )

        from src.admin.router import (
            EscalateRequest,
            escalate_workflow,
            set_workflow_console_service,
        )

        set_workflow_console_service(mock_console_service)
        set_audit_service(mock_audit_service)
        try:
            request = EscalateRequest(
                reason="Stuck for 4 hours",
                actor="admin@example.com",
                owner="oncall@example.com",
            )
            result = await escalate_workflow("wf-123", request, mock_session)

            assert result.workflow_id == "wf-123"
            assert result.owner == "oncall@example.com"
            assert "escalated" in result.message.lower()

            mock_console_service.escalate.assert_called_once_with(
                workflow_id="wf-123",
                reason="Stuck for 4 hours",
                actor="admin@example.com",
                owner="oncall@example.com",
            )
        finally:
            set_workflow_console_service(None)
            set_audit_service(None)

    @pytest.mark.asyncio
    async def test_escalate_without_owner(
        self,
        mock_console_service: AsyncMock,
        mock_session: AsyncMock,
        mock_audit_service: AsyncMock,
    ) -> None:
        """escalate_workflow works without explicit owner."""
        now = datetime.now(UTC)
        mock_console_service.escalate.return_value = EscalateResult(
            workflow_id="wf-123",
            task_packet_id="tp-123",
            escalated_at=now,
            trigger="Needs review",
            owner=None,
            signal_sent=True,
        )

        from src.admin.router import (
            EscalateRequest,
            escalate_workflow,
            set_workflow_console_service,
        )

        set_workflow_console_service(mock_console_service)
        set_audit_service(mock_audit_service)
        try:
            request = EscalateRequest(
                reason="Needs review",
                actor="admin@example.com",
            )
            result = await escalate_workflow("wf-123", request, mock_session)

            assert result.owner is None
        finally:
            set_workflow_console_service(None)
            set_audit_service(None)

    @pytest.mark.asyncio
    async def test_escalate_not_found_404(
        self, mock_console_service: AsyncMock, mock_session: AsyncMock
    ) -> None:
        """escalate_workflow returns 404 for unknown workflow."""
        mock_console_service.escalate.side_effect = WorkflowNotFoundError("unknown-wf")

        from fastapi import HTTPException

        from src.admin.router import (
            EscalateRequest,
            escalate_workflow,
            set_workflow_console_service,
        )

        set_workflow_console_service(mock_console_service)
        try:
            request = EscalateRequest(
                reason="Test",
                actor="admin@example.com",
            )
            with pytest.raises(HTTPException) as exc_info:
                await escalate_workflow("unknown-wf", request, mock_session)

            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        finally:
            set_workflow_console_service(None)
