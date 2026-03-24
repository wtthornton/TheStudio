"""Tests for Admin UI router — Stories 4.10-4.16.

Tests render all UI pages and partials, verifying:
- Page routes return 200 with correct content
- HTMX attributes are present on interactive elements
- RBAC controls visibility of action buttons
- Partials render correctly with mock data
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from src.admin.rbac import Role

# --- Mock data factories ---


def _mock_health_response():
    """Create mock SystemHealthResponse."""

    @dataclass
    class MockServiceHealth:
        name: str
        status: Any
        latency_ms: float | None = None
        error: str | None = None
        details: dict = field(default_factory=dict)

    class MockStatus:
        def __init__(self, val: str):
            self.value = val

    @dataclass
    class MockSystemHealth:
        temporal: MockServiceHealth
        jetstream: MockServiceHealth
        postgres: MockServiceHealth
        router: MockServiceHealth
        checked_at: datetime
        overall_status: Any

    return MockSystemHealth(
        temporal=MockServiceHealth("temporal", MockStatus("OK"), 5.2),
        jetstream=MockServiceHealth("jetstream", MockStatus("OK"), 3.1),
        postgres=MockServiceHealth("postgres", MockStatus("OK"), 1.8),
        router=MockServiceHealth("router", MockStatus("OK")),
        checked_at=datetime.now(UTC),
        overall_status=MockStatus("OK"),
    )


def _mock_metrics_response():
    """Create mock WorkflowMetricsResponse."""

    @dataclass
    class MockCounts:
        running: int = 5
        stuck: int = 1
        failed: int = 0
        completed: int = 42

    @dataclass
    class MockRepoMetrics:
        repo_id: UUID
        repo_name: str
        tier: str
        counts: MockCounts = field(default_factory=MockCounts)
        queue_depth: int = 10
        pass_rate_24h: float = 0.78
        has_elevated_failure_rate: bool = False
        stuck_workflow_ids: list = field(default_factory=list)

    @dataclass
    class MockAlert:
        alert_type: str
        severity: str
        repo_name: str
        message: str
        workflow_ids: list = field(default_factory=list)
        details: dict = field(default_factory=dict)

    @dataclass
    class MockMetrics:
        aggregate: MockCounts
        queue_depth: int
        pass_rate_24h: float
        repos: list
        alerts: list
        checked_at: datetime
        stuck_threshold_hours: int

    return MockMetrics(
        aggregate=MockCounts(),
        queue_depth=10,
        pass_rate_24h=0.75,
        repos=[
            MockRepoMetrics(
                repo_id=uuid4(),
                repo_name="test/repo",
                tier="observe",
            ),
        ],
        alerts=[
            MockAlert(
                alert_type="elevated_failure_rate",
                severity="warning",
                repo_name="test/repo",
                message="Verification failures spiking",
            ),
        ],
        checked_at=datetime.now(UTC),
        stuck_threshold_hours=2,
    )


def _mock_repo_row(
    repo_id: UUID | None = None,
    owner: str = "test",
    repo: str = "repo",
    tier_val: str = "observe",
    status_val: str = "active",
):
    """Create a mock repo row."""

    class MockEnum:
        def __init__(self, val: str):
            self.value = val

    row = MagicMock()
    row.id = repo_id or uuid4()
    row.owner = owner
    row.repo = repo
    row.tier = MockEnum(tier_val)
    row.status = MockEnum(status_val)
    row.installation_id = 12345
    row.default_branch = "main"
    row.created_at = datetime.now(UTC)
    row.language = "python"
    row.build_commands = "pytest"
    row.required_checks = ["test", "lint"]
    row.risk_paths = ["/auth/**"]
    return row


def _mock_workflow_list_response():
    """Create mock WorkflowListResponse."""
    from src.admin.workflow_console import WorkflowListItem, WorkflowListResponse, WorkflowStatus

    return WorkflowListResponse(
        workflows=[
            WorkflowListItem(
                workflow_id="wf-abc-123",
                repo_id=uuid4(),
                repo_name="test/repo",
                status=WorkflowStatus.RUNNING,
                current_step="verify",
                issue_ref="#42",
                started_at=datetime.now(UTC),
                attempt_count=2,
                complexity="high",
            ),
        ],
        total=1,
        filtered_by={},
    )


def _mock_workflow_detail():
    """Create mock WorkflowDetail."""
    from src.admin.workflow_console import (
        EscalationInfo,
        RetryInfo,
        StepStatus,
        TimelineEntry,
        WorkflowDetail,
        WorkflowStatus,
    )

    return WorkflowDetail(
        workflow_id="wf-abc-123",
        task_packet_id="tp-001",
        repo_id=uuid4(),
        repo_name="test/repo",
        issue_ref="#42",
        status=WorkflowStatus.RUNNING,
        current_step="verify",
        attempt_count=2,
        complexity="high",
        started_at=datetime.now(UTC),
        completed_at=None,
        timeline=[
            TimelineEntry(
                step="context",
                status=StepStatus.OK,
                started_at=datetime.now(UTC),
            ),
            TimelineEntry(
                step="intent",
                status=StepStatus.OK,
                started_at=datetime.now(UTC),
            ),
            TimelineEntry(
                step="verify",
                status=StepStatus.FAILED,
                started_at=datetime.now(UTC),
                failure_reason="ruff: F401 unused import",
                evidence=["ruff: F401 unused import in src/foo.py"],
            ),
        ],
        retry_info=RetryInfo(
            next_retry_time=None,
            time_in_current_step_ms=5000,
            attempt_count_for_step=2,
        ),
        escalation_info=EscalationInfo(),
    )


def _mock_audit_result():
    """Create mock AuditLogListResult."""
    from src.admin.audit import AuditEventType

    @dataclass
    class MockAuditEntry:
        id: UUID
        timestamp: datetime
        actor: str
        event_type: AuditEventType
        target_id: UUID | None
        details: dict | None

    @dataclass
    class MockAuditResult:
        entries: list
        total: int
        filtered_by: dict

    return MockAuditResult(
        entries=[
            MockAuditEntry(
                id=uuid4(),
                timestamp=datetime.now(UTC),
                actor="admin@studio",
                event_type=AuditEventType.REPO_REGISTERED,
                target_id=uuid4(),
                details={"owner": "test", "repo": "repo"},
            ),
        ],
        total=1,
        filtered_by={},
    )


# --- Fixtures ---


@pytest.fixture
def _mock_services():
    """Patch all services used by UI router."""
    health_svc = MagicMock()
    health_svc.check_all = AsyncMock(return_value=_mock_health_response())

    metrics_svc = MagicMock()
    metrics_svc.get_metrics = AsyncMock(return_value=_mock_metrics_response())

    repo_repo = MagicMock()
    repo_repo.list_all = AsyncMock(return_value=[_mock_repo_row()])
    repo_repo.get = AsyncMock(return_value=_mock_repo_row())

    console_svc = MagicMock()
    console_svc.list_workflows = AsyncMock(return_value=_mock_workflow_list_response())
    console_svc.get_workflow_detail = AsyncMock(return_value=_mock_workflow_detail())

    audit_svc = MagicMock()
    audit_svc.query = AsyncMock(return_value=_mock_audit_result())

    rbac_svc = MagicMock()
    rbac_svc.get_user_role = AsyncMock(return_value=Role.ADMIN)

    with (
        patch("src.admin.ui_router.get_health_service", return_value=health_svc),
        patch("src.admin.ui_router.get_workflow_metrics_service", return_value=metrics_svc),
        patch("src.admin.ui_router.get_repo_repository", return_value=repo_repo),
        patch("src.admin.ui_router.get_workflow_console_service", return_value=console_svc),
        patch("src.admin.ui_router.get_audit_service", return_value=audit_svc),
        patch("src.admin.ui_router.get_rbac_service", return_value=rbac_svc),
        patch("src.admin.ui_router.get_async_session"),
    ):
        # Make get_async_session return an async context manager
        from src.admin import ui_router as ui_mod

        mock_session = AsyncMock()
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        ui_mod.get_async_session = MagicMock(return_value=mock_cm)

        yield {
            "health": health_svc,
            "metrics": metrics_svc,
            "repo_repo": repo_repo,
            "console": console_svc,
            "audit": audit_svc,
            "rbac": rbac_svc,
        }


@pytest.fixture
def client(_mock_services):
    """Create test client with mocked services."""
    from fastapi import FastAPI

    from src.admin.ui_router import ui_router

    app = FastAPI()
    app.include_router(ui_router)
    return TestClient(app)


ADMIN_HEADERS = {"X-User-ID": "admin@studio"}
VIEWER_HEADERS = {"X-User-ID": "viewer@studio"}


# --- Story 4.10: UI Foundation Tests ---


class TestUIFoundation:
    """Story 4.10: Layout, navigation, redirects."""

    def test_root_redirects_to_dashboard(self, client):
        resp = client.get("/admin/ui/", headers=ADMIN_HEADERS, follow_redirects=False)
        assert resp.status_code == 302
        assert resp.headers["location"] == "/admin/ui/dashboard"

    def test_root_requires_auth(self, client):
        with patch("src.settings.settings") as mock_settings:
            mock_settings.llm_provider = "anthropic"
            resp = client.get("/admin/ui/", follow_redirects=False)
        assert resp.status_code == 401

    def test_dashboard_page_renders(self, client):
        resp = client.get("/admin/ui/dashboard", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        assert "TheStudio" in resp.text
        assert "Admin Console" in resp.text
        assert "Fleet Dashboard" in resp.text

    def test_navigation_links_present(self, client):
        resp = client.get("/admin/ui/dashboard", headers=ADMIN_HEADERS)
        assert "/admin/ui/dashboard" in resp.text
        assert "/admin/ui/repos" in resp.text
        assert "/admin/ui/workflows" in resp.text
        assert "/admin/ui/audit" in resp.text

    def test_repos_page_renders(self, client):
        resp = client.get("/admin/ui/repos", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        assert "Repo Management" in resp.text

    def test_workflows_page_renders(self, client):
        resp = client.get("/admin/ui/workflows", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        assert "Workflow Console" in resp.text

    def test_audit_page_renders(self, client):
        resp = client.get("/admin/ui/audit", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        assert "Audit Log" in resp.text

    def test_repo_detail_page_renders(self, client):
        repo_id = str(uuid4())
        resp = client.get(f"/admin/ui/repos/{repo_id}", headers=ADMIN_HEADERS)
        assert resp.status_code == 200

    def test_workflow_detail_page_renders(self, client):
        resp = client.get("/admin/ui/workflows/wf-abc-123", headers=ADMIN_HEADERS)
        assert resp.status_code == 200


# --- Story 4.11: Fleet Dashboard Tests ---


class TestDashboardPartial:
    """Story 4.11: Dashboard partial with health and metrics."""

    def test_dashboard_partial_renders(self, client):
        resp = client.get("/admin/ui/partials/dashboard", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        assert "System Health" in resp.text

    def test_dashboard_shows_service_health(self, client):
        resp = client.get("/admin/ui/partials/dashboard", headers=ADMIN_HEADERS)
        assert "Temporal" in resp.text
        assert "Jetstream" in resp.text
        assert "Postgres" in resp.text
        assert "Router" in resp.text
        assert "OK" in resp.text

    def test_dashboard_shows_workflow_counts(self, client):
        resp = client.get("/admin/ui/partials/dashboard", headers=ADMIN_HEADERS)
        assert "Running" in resp.text
        assert "Stuck" in resp.text
        assert "Failed" in resp.text
        assert "Queue Depth" in resp.text

    def test_dashboard_shows_repos_table(self, client):
        resp = client.get("/admin/ui/partials/dashboard", headers=ADMIN_HEADERS)
        assert "test/repo" in resp.text
        assert "24h Pass" in resp.text

    def test_dashboard_shows_hot_alerts(self, client):
        resp = client.get("/admin/ui/partials/dashboard", headers=ADMIN_HEADERS)
        assert "Hot Alerts" in resp.text
        assert "Verification failures spiking" in resp.text

    def test_dashboard_has_htmx_polling(self, client):
        resp = client.get("/admin/ui/dashboard", headers=ADMIN_HEADERS)
        assert "hx-trigger" in resp.text
        assert "every 5s" in resp.text


# --- Story 4.12: Repo Management Tests ---


class TestRepoPartials:
    """Story 4.12: Repo list and detail partials."""

    def test_repos_list_partial_renders(self, client):
        resp = client.get("/admin/ui/partials/repos", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        assert "test" in resp.text  # owner
        assert "repo" in resp.text  # repo name

    def test_repo_detail_partial_renders(self, client):
        repo_id = str(uuid4())
        resp = client.get(f"/admin/ui/partials/repo/{repo_id}", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        assert "test" in resp.text
        assert "repo" in resp.text

    def test_repo_detail_shows_profile(self, client):
        repo_id = str(uuid4())
        resp = client.get(f"/admin/ui/partials/repo/{repo_id}", headers=ADMIN_HEADERS)
        assert "Repo Profile" in resp.text
        assert "Language" in resp.text

    def test_repo_detail_shows_actions_for_admin(self, client):
        repo_id = str(uuid4())
        resp = client.get(f"/admin/ui/partials/repo/{repo_id}", headers=ADMIN_HEADERS)
        assert "Change Tier" in resp.text
        assert "Pause" in resp.text
        assert "Delete" in resp.text

    def test_register_form_visible_for_admin(self, client):
        resp = client.get("/admin/ui/repos", headers=ADMIN_HEADERS)
        assert "Register Repo" in resp.text


# --- Story 4.13: Workflow Console Tests ---


class TestWorkflowPartials:
    """Story 4.13: Workflow list and detail partials."""

    def test_workflows_list_partial_renders(self, client):
        resp = client.get("/admin/ui/partials/workflows", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        assert "wf-abc-123" in resp.text

    def test_workflows_list_shows_status(self, client):
        resp = client.get("/admin/ui/partials/workflows", headers=ADMIN_HEADERS)
        assert "RUNNING" in resp.text

    def test_workflow_detail_partial_renders(self, client):
        resp = client.get(
            "/admin/ui/partials/workflow/wf-abc-123", headers=ADMIN_HEADERS
        )
        assert resp.status_code == 200
        assert "wf-abc-123" in resp.text

    def test_workflow_detail_shows_timeline(self, client):
        resp = client.get(
            "/admin/ui/partials/workflow/wf-abc-123", headers=ADMIN_HEADERS
        )
        assert "Timeline" in resp.text
        assert "context" in resp.text
        assert "intent" in resp.text
        assert "verify" in resp.text

    def test_workflow_detail_shows_failure_evidence(self, client):
        resp = client.get(
            "/admin/ui/partials/workflow/wf-abc-123", headers=ADMIN_HEADERS
        )
        assert "F401" in resp.text

    def test_workflow_detail_shows_controls(self, client):
        resp = client.get(
            "/admin/ui/partials/workflow/wf-abc-123", headers=ADMIN_HEADERS
        )
        assert "Rerun Verification" in resp.text
        assert "Send to Agent" in resp.text
        assert "Escalate" in resp.text

    def test_workflow_detail_has_hx_confirm(self, client):
        resp = client.get(
            "/admin/ui/partials/workflow/wf-abc-123", headers=ADMIN_HEADERS
        )
        assert "hx-confirm" in resp.text

    def test_workflow_filters_present(self, client):
        resp = client.get("/admin/ui/workflows", headers=ADMIN_HEADERS)
        assert "Status" in resp.text
        assert "Repo ID" in resp.text


# --- Story 4.14: Audit Log Tests ---


class TestAuditPartial:
    """Story 4.14: Audit log partial with filters."""

    def test_audit_partial_renders(self, client):
        resp = client.get("/admin/ui/partials/audit", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        assert "admin@studio" in resp.text

    def test_audit_shows_event_type(self, client):
        resp = client.get("/admin/ui/partials/audit", headers=ADMIN_HEADERS)
        assert "Repo Registered" in resp.text

    def test_audit_page_has_filters(self, client):
        resp = client.get("/admin/ui/audit", headers=ADMIN_HEADERS)
        assert "Event Type" in resp.text
        assert "Actor" in resp.text
        assert "Target ID" in resp.text
        assert "Time Range" in resp.text


# --- Story 4.15: RBAC-Aware UI Tests ---


class TestRBACAwareUI:
    """Story 4.15: Role-based visibility of UI controls."""

    def test_admin_sees_audit_nav_link(self, client):
        resp = client.get("/admin/ui/dashboard", headers=ADMIN_HEADERS)
        assert "/admin/ui/audit" in resp.text

    def test_admin_role_badge_shown(self, client):
        resp = client.get("/admin/ui/dashboard", headers=ADMIN_HEADERS)
        assert "ADMIN" in resp.text

    def test_viewer_cannot_see_register_button(self, client, _mock_services):
        """Viewer role should not see register repo button."""
        _mock_services["rbac"].get_user_role = AsyncMock(return_value=Role.VIEWER)
        resp = client.get("/admin/ui/repos", headers=VIEWER_HEADERS)
        assert "Register Repo" not in resp.text

    def test_viewer_cannot_see_action_buttons_on_repo(self, client, _mock_services):
        """Viewer role should not see tier/pause/delete buttons."""
        _mock_services["rbac"].get_user_role = AsyncMock(return_value=Role.VIEWER)
        repo_id = str(uuid4())
        resp = client.get(f"/admin/ui/partials/repo/{repo_id}", headers=VIEWER_HEADERS)
        assert "Change Tier" not in resp.text
        assert "Delete" not in resp.text

    def test_viewer_cannot_see_workflow_controls(self, client, _mock_services):
        """Viewer role should not see rerun/escalate controls."""
        _mock_services["rbac"].get_user_role = AsyncMock(return_value=Role.VIEWER)
        resp = client.get(
            "/admin/ui/partials/workflow/wf-abc-123", headers=VIEWER_HEADERS
        )
        assert "Rerun Verification" not in resp.text
        assert "Send to Agent" not in resp.text
        assert "Escalate" not in resp.text

    def test_viewer_cannot_see_audit_nav(self, client, _mock_services):
        """Viewer role should not see audit log in nav."""
        _mock_services["rbac"].get_user_role = AsyncMock(return_value=Role.VIEWER)
        resp = client.get("/admin/ui/dashboard", headers=VIEWER_HEADERS)
        # Audit nav link should be hidden for non-admin
        body = resp.text
        # Check that audit link is not in nav (it's conditionally rendered)
        assert body.count("/admin/ui/audit") == 0

    def test_operator_sees_rerun_but_not_register(self, client, _mock_services):
        """Operator can rerun but not register repos."""
        _mock_services["rbac"].get_user_role = AsyncMock(return_value=Role.OPERATOR)
        resp = client.get(
            "/admin/ui/partials/workflow/wf-abc-123", headers=VIEWER_HEADERS
        )
        assert "Rerun Verification" in resp.text
        assert "Send to Agent" in resp.text

        resp2 = client.get("/admin/ui/repos", headers=VIEWER_HEADERS)
        assert "Register Repo" not in resp2.text


class TestStory531AdminShellNavConformance:
    """Story 53.1: Admin shell and navigation conformance — SG §2.1–2.2 + §6."""

    def test_skip_nav_link_present(self, client):
        """Skip-nav link must be present for keyboard baseline (SG §6)."""
        resp = client.get("/admin/ui/dashboard", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        assert 'href="#main-content"' in resp.text
        assert "Skip to main content" in resp.text

    def test_main_content_anchor_present(self, client):
        """#main-content anchor must exist as skip-link target (SG §6)."""
        resp = client.get("/admin/ui/dashboard", headers=ADMIN_HEADERS)
        assert 'id="main-content"' in resp.text

    def test_nav_has_aria_label(self, client):
        """Nav element must have aria-label for landmark accessibility (SG §6)."""
        resp = client.get("/admin/ui/dashboard", headers=ADMIN_HEADERS)
        assert 'aria-label="Admin navigation"' in resp.text

    def test_active_nav_item_has_aria_current(self, client):
        """Active nav link must carry aria-current='page' (SG §6)."""
        resp = client.get("/admin/ui/dashboard", headers=ADMIN_HEADERS)
        assert 'aria-current="page"' in resp.text

    def test_active_nav_item_uses_correct_classes(self, client):
        """Active nav item must use bg-gray-800 text-white font-medium (SG §2.2)."""
        resp = client.get("/admin/ui/dashboard", headers=ADMIN_HEADERS)
        body = resp.text
        # The active Dashboard link must carry the active state class
        assert "bg-gray-800 text-white font-medium" in body

    def test_nav_icon_spans_are_aria_hidden(self, client):
        """Decorative icon spans must be aria-hidden so SR skips them (SG §6)."""
        resp = client.get("/admin/ui/dashboard", headers=ADMIN_HEADERS)
        assert 'aria-hidden="true"' in resp.text

    def test_cross_app_link_indigo_emphasis(self, client):
        """Pipeline Dashboard cross-app link must use indigo emphasis (SG §2.2)."""
        resp = client.get("/admin/ui/dashboard", headers=ADMIN_HEADERS)
        assert "bg-indigo-800" in resp.text
        assert "Pipeline Dashboard" in resp.text

    def test_shell_layout_classes_present(self, client):
        """Shell layout must use flex min-h-screen canvas (SG §2.1)."""
        resp = client.get("/admin/ui/dashboard", headers=ADMIN_HEADERS)
        body = resp.text
        assert "flex min-h-screen" in body
        assert "bg-gray-50" in body
        assert "bg-gray-900" in body  # dark sidebar

    def test_repos_page_active_nav(self, client):
        """Repos page must mark repos nav item as aria-current='page'."""
        resp = client.get("/admin/ui/repos", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        assert 'aria-current="page"' in resp.text
