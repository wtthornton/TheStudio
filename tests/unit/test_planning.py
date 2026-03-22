"""Unit tests for planning endpoints (Epic 36, Stories 36.3, 36.9, 36.10)."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.intent.intent_spec import IntentSpecRead
from src.models.taskpacket import TaskPacketRead, TaskPacketStatus


@pytest.fixture
def client() -> TestClient:
    from src.app import app

    return TestClient(app)


def _make_task(
    task_id=None,
    status=TaskPacketStatus.TRIAGE,
    **kwargs,
) -> TaskPacketRead:
    return TaskPacketRead(
        id=task_id or uuid4(),
        repo="owner/repo",
        issue_id=42,
        delivery_id="test-delivery",
        correlation_id=uuid4(),
        status=status,
        issue_title=kwargs.get("issue_title", "Test issue"),
        issue_body=kwargs.get("issue_body", "Fix this bug"),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


class TestAcceptEndpoint:
    @patch("src.dashboard.events_publisher.emit_triage_accepted", new_callable=AsyncMock)
    @patch("src.ingress.workflow_trigger.start_workflow", new_callable=AsyncMock)
    @patch("src.dashboard.planning.update_status", new_callable=AsyncMock)
    @patch("src.dashboard.planning.get_by_id", new_callable=AsyncMock)
    def test_accept_transitions_to_received(
        self,
        mock_get: AsyncMock,
        mock_update: AsyncMock,
        mock_workflow: AsyncMock,
        mock_emit: AsyncMock,
        client: TestClient,
    ) -> None:
        task_id = uuid4()
        mock_get.return_value = _make_task(task_id=task_id)
        mock_update.return_value = _make_task(
            task_id=task_id, status=TaskPacketStatus.RECEIVED,
        )
        mock_workflow.return_value = "run-id"

        response = client.post(f"/api/v1/dashboard/tasks/{task_id}/accept")
        assert response.status_code == 200
        data = response.json()
        assert data["task"]["status"] == "received"
        assert data["workflow_started"] is True

    @patch("src.dashboard.planning.get_by_id", new_callable=AsyncMock)
    def test_accept_409_on_non_triage_status(
        self, mock_get: AsyncMock, client: TestClient,
    ) -> None:
        task_id = uuid4()
        mock_get.return_value = _make_task(
            task_id=task_id, status=TaskPacketStatus.RECEIVED,
        )

        response = client.post(f"/api/v1/dashboard/tasks/{task_id}/accept")
        assert response.status_code == 409

    @patch("src.dashboard.planning.get_by_id", new_callable=AsyncMock)
    def test_accept_404_on_missing_task(
        self, mock_get: AsyncMock, client: TestClient,
    ) -> None:
        mock_get.return_value = None

        response = client.post(f"/api/v1/dashboard/tasks/{uuid4()}/accept")
        assert response.status_code == 404


class TestRejectEndpoint:
    @patch("src.dashboard.planning.get_by_id", new_callable=AsyncMock)
    def test_reject_requires_reason(
        self, mock_get: AsyncMock, client: TestClient,
    ) -> None:
        task_id = uuid4()
        mock_get.return_value = _make_task(task_id=task_id)

        response = client.post(
            f"/api/v1/dashboard/tasks/{task_id}/reject",
            json={},
        )
        assert response.status_code == 422

    @patch("src.dashboard.planning.get_by_id", new_callable=AsyncMock)
    def test_reject_invalid_reason(
        self, mock_get: AsyncMock, client: TestClient,
    ) -> None:
        task_id = uuid4()
        mock_get.return_value = _make_task(task_id=task_id)

        response = client.post(
            f"/api/v1/dashboard/tasks/{task_id}/reject",
            json={"reason": "invalid_reason"},
        )
        assert response.status_code == 422

    @patch("src.dashboard.planning.get_by_id", new_callable=AsyncMock)
    def test_reject_409_on_non_triage_status(
        self, mock_get: AsyncMock, client: TestClient,
    ) -> None:
        task_id = uuid4()
        mock_get.return_value = _make_task(
            task_id=task_id, status=TaskPacketStatus.IN_PROGRESS,
        )

        response = client.post(
            f"/api/v1/dashboard/tasks/{task_id}/reject",
            json={"reason": "duplicate"},
        )
        assert response.status_code == 409


class TestEditEndpoint:
    @patch("src.dashboard.planning.get_by_id", new_callable=AsyncMock)
    def test_edit_409_on_non_triage_status(
        self, mock_get: AsyncMock, client: TestClient,
    ) -> None:
        task_id = uuid4()
        mock_get.return_value = _make_task(
            task_id=task_id, status=TaskPacketStatus.RECEIVED,
        )

        response = client.patch(
            f"/api/v1/dashboard/tasks/{task_id}",
            json={"issue_title": "New title"},
        )
        assert response.status_code == 409

    @patch("src.dashboard.planning.get_by_id", new_callable=AsyncMock)
    def test_edit_404_on_missing_task(
        self, mock_get: AsyncMock, client: TestClient,
    ) -> None:
        mock_get.return_value = None

        response = client.patch(
            f"/api/v1/dashboard/tasks/{uuid4()}",
            json={"issue_title": "New title"},
        )
        assert response.status_code == 404


class TestRejectionReasons:
    """Verify rejection reason validation via Pydantic model."""

    @pytest.mark.parametrize(
        "reason",
        ["duplicate", "out_of_scope", "needs_info", "wont_fix"],
    )
    def test_valid_reason_accepted(self, reason: str) -> None:
        from src.dashboard.planning import RejectRequest

        req = RejectRequest(reason=reason)
        assert req.reason.value == reason

    def test_invalid_reason_rejected(self) -> None:
        from src.dashboard.planning import RejectRequest

        with pytest.raises(Exception):
            RejectRequest(reason="invalid_reason")


# ---------------------------------------------------------------------------
# Intent review helpers
# ---------------------------------------------------------------------------


def _make_intent(
    taskpacket_id=None,
    version=1,
    source="auto",
) -> IntentSpecRead:
    return IntentSpecRead(
        id=uuid4(),
        taskpacket_id=taskpacket_id or uuid4(),
        version=version,
        goal="Fix the authentication bug",
        constraints=["Must include tests"],
        acceptance_criteria=["Auth works after fix"],
        non_goals=["No UI changes"],
        source=source,
        created_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# Intent review endpoint tests (Story 36.9)
# ---------------------------------------------------------------------------


class TestGetIntentEndpoint:
    """GET /tasks/{task_id}/intent."""

    @patch("src.dashboard.planning.get_all_versions")
    @patch("src.dashboard.planning.get_latest_for_taskpacket")
    @patch("src.dashboard.planning.get_by_id", new_callable=AsyncMock)
    def test_get_intent_returns_current_and_versions(
        self,
        mock_get: AsyncMock,
        mock_latest: AsyncMock,
        mock_all: AsyncMock,
        client: TestClient,
    ) -> None:
        task_id = uuid4()
        mock_get.return_value = _make_task(
            task_id=task_id, status=TaskPacketStatus.INTENT_BUILT,
        )
        intent_v1 = _make_intent(taskpacket_id=task_id, version=1, source="auto")
        intent_v2 = _make_intent(taskpacket_id=task_id, version=2, source="developer")
        mock_latest.return_value = intent_v2
        mock_all.return_value = [intent_v1, intent_v2]

        response = client.get(f"/api/v1/dashboard/tasks/{task_id}/intent")
        assert response.status_code == 200
        data = response.json()
        assert data["current"]["version"] == 2
        assert data["current"]["source"] == "developer"
        assert len(data["versions"]) == 2
        assert data["versions"][0]["source"] == "auto"

    @patch("src.dashboard.planning.get_latest_for_taskpacket")
    @patch("src.dashboard.planning.get_by_id", new_callable=AsyncMock)
    def test_get_intent_404_no_spec(
        self,
        mock_get: AsyncMock,
        mock_latest: AsyncMock,
        client: TestClient,
    ) -> None:
        task_id = uuid4()
        mock_get.return_value = _make_task(
            task_id=task_id, status=TaskPacketStatus.INTENT_BUILT,
        )
        mock_latest.return_value = None

        response = client.get(f"/api/v1/dashboard/tasks/{task_id}/intent")
        assert response.status_code == 404

    @patch("src.dashboard.planning.get_by_id", new_callable=AsyncMock)
    def test_get_intent_404_no_task(
        self,
        mock_get: AsyncMock,
        client: TestClient,
    ) -> None:
        mock_get.return_value = None
        response = client.get(f"/api/v1/dashboard/tasks/{uuid4()}/intent")
        assert response.status_code == 404


class TestApproveIntentEndpoint:
    """POST /tasks/{task_id}/intent/approve."""

    @patch("src.ingress.workflow_trigger.get_temporal_client", new_callable=AsyncMock)
    @patch("src.dashboard.planning.get_by_id", new_callable=AsyncMock)
    def test_approve_sends_signal(
        self,
        mock_get: AsyncMock,
        mock_temporal: AsyncMock,
        client: TestClient,
    ) -> None:
        task_id = uuid4()
        mock_get.return_value = _make_task(
            task_id=task_id, status=TaskPacketStatus.INTENT_BUILT,
        )
        mock_handle = AsyncMock()
        # get_workflow_handle is sync, so use MagicMock for the client
        mock_client = MagicMock()
        mock_client.get_workflow_handle.return_value = mock_handle
        mock_temporal.return_value = mock_client

        response = client.post(f"/api/v1/dashboard/tasks/{task_id}/intent/approve")
        assert response.status_code == 200
        assert response.json()["status"] == "approved"
        mock_handle.signal.assert_called_once()

    @patch("src.dashboard.planning.get_by_id", new_callable=AsyncMock)
    def test_approve_409_wrong_status(
        self,
        mock_get: AsyncMock,
        client: TestClient,
    ) -> None:
        task_id = uuid4()
        mock_get.return_value = _make_task(
            task_id=task_id, status=TaskPacketStatus.RECEIVED,
        )
        response = client.post(f"/api/v1/dashboard/tasks/{task_id}/intent/approve")
        assert response.status_code == 409


class TestRejectIntentEndpoint:
    """POST /tasks/{task_id}/intent/reject."""

    @patch("src.ingress.workflow_trigger.get_temporal_client", new_callable=AsyncMock)
    @patch("src.dashboard.planning.get_by_id", new_callable=AsyncMock)
    def test_reject_sends_signal_with_reason(
        self,
        mock_get: AsyncMock,
        mock_temporal: AsyncMock,
        client: TestClient,
    ) -> None:
        task_id = uuid4()
        mock_get.return_value = _make_task(
            task_id=task_id, status=TaskPacketStatus.INTENT_BUILT,
        )
        mock_handle = AsyncMock()
        mock_client = MagicMock()
        mock_client.get_workflow_handle.return_value = mock_handle
        mock_temporal.return_value = mock_client

        response = client.post(
            f"/api/v1/dashboard/tasks/{task_id}/intent/reject",
            json={"reason": "Goal is too vague"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "rejected"
        mock_handle.signal.assert_called_once()

    @patch("src.dashboard.planning.get_by_id", new_callable=AsyncMock)
    def test_reject_409_wrong_status(
        self,
        mock_get: AsyncMock,
        client: TestClient,
    ) -> None:
        task_id = uuid4()
        mock_get.return_value = _make_task(
            task_id=task_id, status=TaskPacketStatus.RECEIVED,
        )
        response = client.post(
            f"/api/v1/dashboard/tasks/{task_id}/intent/reject",
            json={"reason": "Too vague"},
        )
        assert response.status_code == 409

    @patch("src.dashboard.planning.get_by_id", new_callable=AsyncMock)
    def test_reject_requires_reason(
        self,
        mock_get: AsyncMock,
        client: TestClient,
    ) -> None:
        task_id = uuid4()
        mock_get.return_value = _make_task(
            task_id=task_id, status=TaskPacketStatus.INTENT_BUILT,
        )
        response = client.post(
            f"/api/v1/dashboard/tasks/{task_id}/intent/reject",
            json={},
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Intent edit + refinement endpoint tests (Story 36.10)
# ---------------------------------------------------------------------------


class TestEditIntentEndpoint:
    """PUT /tasks/{task_id}/intent."""

    @patch("src.dashboard.planning.update_intent_version", new_callable=AsyncMock)
    @patch("src.dashboard.planning.create_intent", new_callable=AsyncMock)
    @patch("src.dashboard.planning.get_latest_for_taskpacket", new_callable=AsyncMock)
    @patch("src.dashboard.planning.get_by_id", new_callable=AsyncMock)
    def test_edit_creates_new_version_with_developer_source(
        self,
        mock_get: AsyncMock,
        mock_latest: AsyncMock,
        mock_create: AsyncMock,
        mock_update: AsyncMock,
        client: TestClient,
    ) -> None:
        task_id = uuid4()
        mock_get.return_value = _make_task(
            task_id=task_id, status=TaskPacketStatus.INTENT_BUILT,
        )
        current = _make_intent(taskpacket_id=task_id, version=1)
        mock_latest.return_value = current
        new_intent = _make_intent(taskpacket_id=task_id, version=2, source="developer")
        mock_create.return_value = new_intent
        mock_update.return_value = _make_task(task_id=task_id, status=TaskPacketStatus.INTENT_BUILT)

        response = client.put(
            f"/api/v1/dashboard/tasks/{task_id}/intent",
            json={
                "goal": "Updated goal",
                "constraints": ["New constraint"],
                "acceptance_criteria": ["New AC"],
                "non_goals": [],
            },
        )
        assert response.status_code == 200
        # Verify create_intent was called with source="developer"
        call_args = mock_create.call_args[0]
        assert call_args[1].source == "developer"
        assert call_args[1].version == 2

    @patch("src.dashboard.planning.get_by_id", new_callable=AsyncMock)
    def test_edit_409_wrong_status(
        self,
        mock_get: AsyncMock,
        client: TestClient,
    ) -> None:
        task_id = uuid4()
        mock_get.return_value = _make_task(
            task_id=task_id, status=TaskPacketStatus.RECEIVED,
        )
        response = client.put(
            f"/api/v1/dashboard/tasks/{task_id}/intent",
            json={
                "goal": "Updated goal",
                "constraints": [],
                "acceptance_criteria": [],
                "non_goals": [],
            },
        )
        assert response.status_code == 409

    @patch("src.dashboard.planning.get_latest_for_taskpacket", new_callable=AsyncMock)
    @patch("src.dashboard.planning.get_by_id", new_callable=AsyncMock)
    def test_edit_404_no_intent(
        self,
        mock_get: AsyncMock,
        mock_latest: AsyncMock,
        client: TestClient,
    ) -> None:
        task_id = uuid4()
        mock_get.return_value = _make_task(
            task_id=task_id, status=TaskPacketStatus.INTENT_BUILT,
        )
        mock_latest.return_value = None
        response = client.put(
            f"/api/v1/dashboard/tasks/{task_id}/intent",
            json={
                "goal": "Updated goal",
                "constraints": [],
                "acceptance_criteria": [],
                "non_goals": [],
            },
        )
        assert response.status_code == 404


class TestRefineIntentEndpoint:
    """POST /tasks/{task_id}/intent/refine."""

    @patch("src.intent.refinement.update_intent_version", new_callable=AsyncMock)
    @patch("src.intent.refinement.create_intent", new_callable=AsyncMock)
    @patch("src.intent.refinement.get_latest_for_taskpacket", new_callable=AsyncMock)
    @patch("src.intent.refinement.get_by_id", new_callable=AsyncMock)
    @patch("src.dashboard.planning.get_by_id", new_callable=AsyncMock)
    def test_refine_creates_refinement_version(
        self,
        mock_planning_get: AsyncMock,
        mock_refine_get: AsyncMock,
        mock_latest: AsyncMock,
        mock_create: AsyncMock,
        mock_update: AsyncMock,
        client: TestClient,
    ) -> None:
        task_id = uuid4()
        task = _make_task(task_id=task_id, status=TaskPacketStatus.INTENT_BUILT)
        mock_planning_get.return_value = task

        tp_read = TaskPacketRead(
            id=task_id,
            repo="owner/repo",
            issue_id=42,
            delivery_id="test-delivery",
            correlation_id=uuid4(),
            status=TaskPacketStatus.INTENT_BUILT,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        mock_refine_get.return_value = tp_read

        current = _make_intent(taskpacket_id=task_id, version=1)
        mock_latest.return_value = current
        new_intent = _make_intent(taskpacket_id=task_id, version=2, source="refinement")
        mock_create.return_value = new_intent
        mock_update.return_value = tp_read

        response = client.post(
            f"/api/v1/dashboard/tasks/{task_id}/intent/refine",
            json={"feedback": "Make the goal more specific"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == 2

    @patch("src.dashboard.planning.get_by_id", new_callable=AsyncMock)
    def test_refine_409_wrong_status(
        self,
        mock_get: AsyncMock,
        client: TestClient,
    ) -> None:
        task_id = uuid4()
        mock_get.return_value = _make_task(
            task_id=task_id, status=TaskPacketStatus.RECEIVED,
        )
        response = client.post(
            f"/api/v1/dashboard/tasks/{task_id}/intent/refine",
            json={"feedback": "Improve this"},
        )
        assert response.status_code == 409

    @patch("src.dashboard.planning.get_by_id", new_callable=AsyncMock)
    def test_refine_requires_feedback(
        self,
        mock_get: AsyncMock,
        client: TestClient,
    ) -> None:
        task_id = uuid4()
        mock_get.return_value = _make_task(
            task_id=task_id, status=TaskPacketStatus.INTENT_BUILT,
        )
        response = client.post(
            f"/api/v1/dashboard/tasks/{task_id}/intent/refine",
            json={},
        )
        assert response.status_code == 422
