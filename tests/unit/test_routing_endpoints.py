"""Unit tests for routing review API endpoints (Story 36.14d).

Tests GET /tasks/{id}/routing, POST .../approve, POST .../override.
Follows the pattern established in tests/unit/test_planning.py.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.models.taskpacket import TaskPacketRead, TaskPacketStatus


@pytest.fixture
def client() -> TestClient:
    from src.app import app

    return TestClient(app)


def _make_task(
    task_id=None,
    status=TaskPacketStatus.INTENT_BUILT,
    routing_result=None,
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
        routing_result=routing_result,
    )


def _make_routing_result(task_id=None) -> dict:
    """Build a minimal routing_result JSON payload."""
    return {
        "selections": [
            {
                "expert_id": str(uuid4()),
                "expert_class": "technical",
                "pattern": "parallel",
                "reputation_weight": 0.8,
                "reputation_confidence": 0.9,
                "selection_score": 1.2,
                "selection_reason": "Strong track record",
            }
        ],
        "rationale": "Best expert for this issue",
        "budget_remaining": 1000,
    }


# ---------------------------------------------------------------------------
# GET /tasks/{task_id}/routing
# ---------------------------------------------------------------------------


class TestGetRoutingEndpoint:
    """GET /tasks/{task_id}/routing."""

    @patch("src.dashboard.planning.get_by_id", new_callable=AsyncMock)
    def test_get_routing_200_with_result(
        self,
        mock_get: AsyncMock,
        client: TestClient,
    ) -> None:
        task_id = uuid4()
        routing = _make_routing_result(task_id)
        mock_get.return_value = _make_task(
            task_id=task_id,
            status=TaskPacketStatus.INTENT_BUILT,
            routing_result=routing,
        )

        response = client.get(f"/api/v1/dashboard/tasks/{task_id}/routing")
        assert response.status_code == 200
        data = response.json()
        assert str(data["taskpacket_id"]) == str(task_id)
        assert len(data["selections"]) == 1
        assert data["selections"][0]["expert_class"] == "technical"
        assert data["rationale"] == "Best expert for this issue"
        assert data["budget_remaining"] == 1000

    @patch("src.dashboard.planning.get_by_id", new_callable=AsyncMock)
    def test_get_routing_404_no_routing_result(
        self,
        mock_get: AsyncMock,
        client: TestClient,
    ) -> None:
        task_id = uuid4()
        mock_get.return_value = _make_task(
            task_id=task_id,
            status=TaskPacketStatus.INTENT_BUILT,
            routing_result=None,
        )

        response = client.get(f"/api/v1/dashboard/tasks/{task_id}/routing")
        assert response.status_code == 404
        assert "routing result" in response.json()["detail"].lower()

    @patch("src.dashboard.planning.get_by_id", new_callable=AsyncMock)
    def test_get_routing_404_task_not_found(
        self,
        mock_get: AsyncMock,
        client: TestClient,
    ) -> None:
        mock_get.return_value = None

        response = client.get(f"/api/v1/dashboard/tasks/{uuid4()}/routing")
        assert response.status_code == 404

    @patch("src.dashboard.planning.get_by_id", new_callable=AsyncMock)
    def test_get_routing_returns_all_selection_fields(
        self,
        mock_get: AsyncMock,
        client: TestClient,
    ) -> None:
        task_id = uuid4()
        expert_id = str(uuid4())
        routing = {
            "selections": [
                {
                    "expert_id": expert_id,
                    "expert_class": "security",
                    "pattern": "staged",
                    "reputation_weight": 0.6,
                    "reputation_confidence": 0.7,
                    "selection_score": 0.9,
                    "selection_reason": "Security specialist required",
                }
            ],
            "rationale": "Security review needed",
            "budget_remaining": 500,
        }
        mock_get.return_value = _make_task(
            task_id=task_id,
            routing_result=routing,
        )

        response = client.get(f"/api/v1/dashboard/tasks/{task_id}/routing")
        assert response.status_code == 200
        sel = response.json()["selections"][0]
        assert sel["expert_id"] == expert_id
        assert sel["expert_class"] == "security"
        assert sel["pattern"] == "staged"
        assert sel["reputation_weight"] == 0.6
        assert sel["selection_reason"] == "Security specialist required"

    @patch("src.dashboard.planning.get_by_id", new_callable=AsyncMock)
    def test_get_routing_empty_selections(
        self,
        mock_get: AsyncMock,
        client: TestClient,
    ) -> None:
        task_id = uuid4()
        routing = {"selections": [], "rationale": "No experts needed", "budget_remaining": 0}
        mock_get.return_value = _make_task(task_id=task_id, routing_result=routing)

        response = client.get(f"/api/v1/dashboard/tasks/{task_id}/routing")
        assert response.status_code == 200
        assert response.json()["selections"] == []


# ---------------------------------------------------------------------------
# POST /tasks/{task_id}/routing/approve
# ---------------------------------------------------------------------------


class TestApproveRoutingEndpoint:
    """POST /tasks/{task_id}/routing/approve."""

    @patch("src.ingress.workflow_trigger.get_temporal_client", new_callable=AsyncMock)
    @patch("src.dashboard.planning.get_by_id", new_callable=AsyncMock)
    def test_approve_sends_signal_and_returns_approved(
        self,
        mock_get: AsyncMock,
        mock_temporal: AsyncMock,
        client: TestClient,
    ) -> None:
        task_id = uuid4()
        mock_get.return_value = _make_task(task_id=task_id)
        mock_handle = AsyncMock()
        mock_client = MagicMock()
        mock_client.get_workflow_handle.return_value = mock_handle
        mock_temporal.return_value = mock_client

        response = client.post(f"/api/v1/dashboard/tasks/{task_id}/routing/approve")
        assert response.status_code == 200
        assert response.json()["status"] == "approved"
        mock_handle.signal.assert_called_once()

    @patch("src.ingress.workflow_trigger.get_temporal_client", new_callable=AsyncMock)
    @patch("src.dashboard.planning.get_by_id", new_callable=AsyncMock)
    def test_approve_signals_with_correct_args(
        self,
        mock_get: AsyncMock,
        mock_temporal: AsyncMock,
        client: TestClient,
    ) -> None:
        task_id = uuid4()
        mock_get.return_value = _make_task(task_id=task_id)
        mock_handle = AsyncMock()
        mock_client = MagicMock()
        mock_client.get_workflow_handle.return_value = mock_handle
        mock_temporal.return_value = mock_client

        client.post(f"/api/v1/dashboard/tasks/{task_id}/routing/approve")
        mock_handle.signal.assert_called_once_with("approve_routing", args=["dashboard_user"])

    @patch("src.dashboard.planning.get_by_id", new_callable=AsyncMock)
    def test_approve_409_wrong_status(
        self,
        mock_get: AsyncMock,
        client: TestClient,
    ) -> None:
        task_id = uuid4()
        mock_get.return_value = _make_task(
            task_id=task_id,
            status=TaskPacketStatus.RECEIVED,
        )

        response = client.post(f"/api/v1/dashboard/tasks/{task_id}/routing/approve")
        assert response.status_code == 409

    @patch("src.dashboard.planning.get_by_id", new_callable=AsyncMock)
    def test_approve_404_task_not_found(
        self,
        mock_get: AsyncMock,
        client: TestClient,
    ) -> None:
        mock_get.return_value = None

        response = client.post(f"/api/v1/dashboard/tasks/{uuid4()}/routing/approve")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /tasks/{task_id}/routing/override
# ---------------------------------------------------------------------------


class TestOverrideRoutingEndpoint:
    """POST /tasks/{task_id}/routing/override."""

    @patch("src.ingress.workflow_trigger.get_temporal_client", new_callable=AsyncMock)
    @patch("src.dashboard.planning.get_by_id", new_callable=AsyncMock)
    def test_override_sends_signal_and_returns_overridden(
        self,
        mock_get: AsyncMock,
        mock_temporal: AsyncMock,
        client: TestClient,
    ) -> None:
        task_id = uuid4()
        mock_get.return_value = _make_task(task_id=task_id)
        mock_handle = AsyncMock()
        mock_client = MagicMock()
        mock_client.get_workflow_handle.return_value = mock_handle
        mock_temporal.return_value = mock_client

        response = client.post(
            f"/api/v1/dashboard/tasks/{task_id}/routing/override",
            json={"reason": "Replace security expert with compliance expert"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "overridden"
        mock_handle.signal.assert_called_once()

    @patch("src.ingress.workflow_trigger.get_temporal_client", new_callable=AsyncMock)
    @patch("src.dashboard.planning.get_by_id", new_callable=AsyncMock)
    def test_override_signals_with_reason(
        self,
        mock_get: AsyncMock,
        mock_temporal: AsyncMock,
        client: TestClient,
    ) -> None:
        task_id = uuid4()
        mock_get.return_value = _make_task(task_id=task_id)
        mock_handle = AsyncMock()
        mock_client = MagicMock()
        mock_client.get_workflow_handle.return_value = mock_handle
        mock_temporal.return_value = mock_client

        reason = "Need compliance coverage instead"
        client.post(
            f"/api/v1/dashboard/tasks/{task_id}/routing/override",
            json={"reason": reason},
        )
        mock_handle.signal.assert_called_once_with(
            "override_routing", args=["dashboard_user", reason]
        )

    @patch("src.dashboard.planning.get_by_id", new_callable=AsyncMock)
    def test_override_409_wrong_status(
        self,
        mock_get: AsyncMock,
        client: TestClient,
    ) -> None:
        task_id = uuid4()
        mock_get.return_value = _make_task(
            task_id=task_id,
            status=TaskPacketStatus.TRIAGE,
        )

        response = client.post(
            f"/api/v1/dashboard/tasks/{task_id}/routing/override",
            json={"reason": "Override reason"},
        )
        assert response.status_code == 409

    @patch("src.dashboard.planning.get_by_id", new_callable=AsyncMock)
    def test_override_404_task_not_found(
        self,
        mock_get: AsyncMock,
        client: TestClient,
    ) -> None:
        mock_get.return_value = None

        response = client.post(
            f"/api/v1/dashboard/tasks/{uuid4()}/routing/override",
            json={"reason": "Override reason"},
        )
        assert response.status_code == 404

    @patch("src.dashboard.planning.get_by_id", new_callable=AsyncMock)
    def test_override_requires_reason(
        self,
        mock_get: AsyncMock,
        client: TestClient,
    ) -> None:
        task_id = uuid4()
        mock_get.return_value = _make_task(task_id=task_id)

        response = client.post(
            f"/api/v1/dashboard/tasks/{task_id}/routing/override",
            json={},
        )
        assert response.status_code == 422
