"""Tests for Story 4.8: RBAC — Role Definitions, API Enforcement.

Tests the RBAC module including:
- Role and Permission definitions
- RBACService methods
- FastAPI dependencies for role enforcement
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException, status

from src.admin.rbac import (
    Permission,
    PermissionDeniedError,
    RBACService,
    Role,
    ROLE_PERMISSIONS,
    UserRoleCreate,
    UserRoleDuplicateError,
    UserRoleNotFoundError,
    UserRoleRow,
    UserRoleUpdate,
    _get_minimum_role_for_permission,
    get_current_user_id,
    get_rbac_service,
    require_permission,
    set_rbac_service,
)


class TestRoleEnum:
    """Tests for Role enum."""

    def test_role_values(self) -> None:
        """Role enum has expected values."""
        assert Role.ADMIN.value == "admin"
        assert Role.OPERATOR.value == "operator"
        assert Role.VIEWER.value == "viewer"

    def test_role_count(self) -> None:
        """Three roles are defined."""
        assert len(Role) == 3


class TestPermissionEnum:
    """Tests for Permission enum."""

    def test_viewer_permissions_exist(self) -> None:
        """Viewer permissions are defined."""
        assert Permission.VIEW_HEALTH.value == "view_health"
        assert Permission.VIEW_REPOS.value == "view_repos"
        assert Permission.VIEW_WORKFLOWS.value == "view_workflows"
        assert Permission.VIEW_METRICS.value == "view_metrics"

    def test_operator_permissions_exist(self) -> None:
        """Operator permissions are defined."""
        assert Permission.PAUSE_REPO.value == "pause_repo"
        assert Permission.RESUME_REPO.value == "resume_repo"
        assert Permission.RERUN_VERIFICATION.value == "rerun_verification"
        assert Permission.SEND_TO_AGENT.value == "send_to_agent"
        assert Permission.ESCALATE_WORKFLOW.value == "escalate_workflow"

    def test_admin_permissions_exist(self) -> None:
        """Admin permissions are defined."""
        assert Permission.REGISTER_REPO.value == "register_repo"
        assert Permission.UPDATE_REPO_PROFILE.value == "update_repo_profile"
        assert Permission.CHANGE_REPO_TIER.value == "change_repo_tier"
        assert Permission.TOGGLE_WRITES.value == "toggle_writes"
        assert Permission.MANAGE_USERS.value == "manage_users"


class TestRolePermissions:
    """Tests for ROLE_PERMISSIONS mapping."""

    def test_viewer_has_view_permissions(self) -> None:
        """Viewer role has view permissions."""
        viewer_perms = ROLE_PERMISSIONS[Role.VIEWER]
        assert Permission.VIEW_HEALTH in viewer_perms
        assert Permission.VIEW_REPOS in viewer_perms
        assert Permission.VIEW_WORKFLOWS in viewer_perms
        assert Permission.VIEW_METRICS in viewer_perms

    def test_viewer_lacks_operator_permissions(self) -> None:
        """Viewer role lacks operator permissions."""
        viewer_perms = ROLE_PERMISSIONS[Role.VIEWER]
        assert Permission.PAUSE_REPO not in viewer_perms
        assert Permission.RERUN_VERIFICATION not in viewer_perms

    def test_operator_inherits_viewer_permissions(self) -> None:
        """Operator role has all viewer permissions."""
        operator_perms = ROLE_PERMISSIONS[Role.OPERATOR]
        viewer_perms = ROLE_PERMISSIONS[Role.VIEWER]
        for perm in viewer_perms:
            assert perm in operator_perms

    def test_operator_has_operational_permissions(self) -> None:
        """Operator role has operational permissions."""
        operator_perms = ROLE_PERMISSIONS[Role.OPERATOR]
        assert Permission.PAUSE_REPO in operator_perms
        assert Permission.RESUME_REPO in operator_perms
        assert Permission.RERUN_VERIFICATION in operator_perms
        assert Permission.SEND_TO_AGENT in operator_perms
        assert Permission.ESCALATE_WORKFLOW in operator_perms

    def test_operator_lacks_admin_permissions(self) -> None:
        """Operator role lacks admin permissions."""
        operator_perms = ROLE_PERMISSIONS[Role.OPERATOR]
        assert Permission.REGISTER_REPO not in operator_perms
        assert Permission.CHANGE_REPO_TIER not in operator_perms
        assert Permission.MANAGE_USERS not in operator_perms

    def test_admin_has_all_permissions(self) -> None:
        """Admin role has all permissions."""
        admin_perms = ROLE_PERMISSIONS[Role.ADMIN]
        for perm in Permission:
            assert perm in admin_perms, f"Admin missing {perm.value}"


class TestUserRoleModels:
    """Tests for UserRole Pydantic models."""

    def test_user_role_create_defaults(self) -> None:
        """UserRoleCreate has default role."""
        create = UserRoleCreate(user_id="test@example.com")
        assert create.role == Role.VIEWER

    def test_user_role_create_with_role(self) -> None:
        """UserRoleCreate accepts explicit role."""
        create = UserRoleCreate(user_id="admin@example.com", role=Role.ADMIN)
        assert create.role == Role.ADMIN

    def test_user_role_update(self) -> None:
        """UserRoleUpdate stores role."""
        update = UserRoleUpdate(role=Role.OPERATOR)
        assert update.role == Role.OPERATOR


class TestUserRoleExceptions:
    """Tests for RBAC exception classes."""

    def test_user_role_not_found_error(self) -> None:
        """UserRoleNotFoundError contains user_id."""
        error = UserRoleNotFoundError("missing@example.com")
        assert error.user_id == "missing@example.com"
        assert "missing@example.com" in str(error)

    def test_user_role_duplicate_error(self) -> None:
        """UserRoleDuplicateError contains user_id."""
        error = UserRoleDuplicateError("existing@example.com")
        assert error.user_id == "existing@example.com"
        assert "existing@example.com" in str(error)

    def test_permission_denied_error(self) -> None:
        """PermissionDeniedError contains user_id and permission."""
        error = PermissionDeniedError("user@example.com", Permission.REGISTER_REPO)
        assert error.user_id == "user@example.com"
        assert error.permission == Permission.REGISTER_REPO
        assert "register_repo" in str(error)


class TestRBACService:
    """Tests for RBACService."""

    @pytest.fixture
    def service(self) -> RBACService:
        """Create an RBACService instance."""
        return RBACService()

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create mock database session."""
        return AsyncMock()

    def test_has_permission_admin(self, service: RBACService) -> None:
        """Admin role has all permissions."""
        for perm in Permission:
            assert service.has_permission(Role.ADMIN, perm) is True

    def test_has_permission_operator(self, service: RBACService) -> None:
        """Operator role has correct permissions."""
        assert service.has_permission(Role.OPERATOR, Permission.VIEW_HEALTH) is True
        assert service.has_permission(Role.OPERATOR, Permission.PAUSE_REPO) is True
        assert service.has_permission(Role.OPERATOR, Permission.REGISTER_REPO) is False

    def test_has_permission_viewer(self, service: RBACService) -> None:
        """Viewer role has only view permissions."""
        assert service.has_permission(Role.VIEWER, Permission.VIEW_HEALTH) is True
        assert service.has_permission(Role.VIEWER, Permission.PAUSE_REPO) is False
        assert service.has_permission(Role.VIEWER, Permission.REGISTER_REPO) is False

    def test_has_permission_none_role(self, service: RBACService) -> None:
        """None role has no permissions."""
        assert service.has_permission(None, Permission.VIEW_HEALTH) is False
        assert service.has_permission(None, Permission.REGISTER_REPO) is False

    def test_check_permission_passes(self, service: RBACService) -> None:
        """check_permission passes for valid permission."""
        service.check_permission(Role.ADMIN, Permission.REGISTER_REPO, "admin@example.com")

    def test_check_permission_raises(self, service: RBACService) -> None:
        """check_permission raises for invalid permission."""
        with pytest.raises(PermissionDeniedError) as exc_info:
            service.check_permission(
                Role.VIEWER, Permission.REGISTER_REPO, "viewer@example.com"
            )

        assert exc_info.value.user_id == "viewer@example.com"
        assert exc_info.value.permission == Permission.REGISTER_REPO

    @pytest.mark.asyncio
    async def test_get_user_role_found(
        self, service: RBACService, mock_session: AsyncMock
    ) -> None:
        """get_user_role returns role when found."""
        mock_row = MagicMock(spec=UserRoleRow)
        mock_row.role = Role.OPERATOR

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_row
        mock_session.execute.return_value = mock_result

        role = await service.get_user_role(mock_session, "operator@example.com")

        assert role == Role.OPERATOR

    @pytest.mark.asyncio
    async def test_get_user_role_not_found(
        self, service: RBACService, mock_session: AsyncMock
    ) -> None:
        """get_user_role returns None when not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        role = await service.get_user_role(mock_session, "unknown@example.com")

        assert role is None

    @pytest.mark.asyncio
    async def test_create_user_role_success(
        self, service: RBACService, mock_session: AsyncMock
    ) -> None:
        """create_user_role creates new role assignment."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        data = UserRoleCreate(user_id="new@example.com", role=Role.OPERATOR)
        await service.create_user_role(mock_session, data, "admin@example.com")

        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_user_role_duplicate(
        self, service: RBACService, mock_session: AsyncMock
    ) -> None:
        """create_user_role raises for duplicate user."""
        mock_row = MagicMock(spec=UserRoleRow)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_row
        mock_session.execute.return_value = mock_result

        data = UserRoleCreate(user_id="existing@example.com", role=Role.VIEWER)

        with pytest.raises(UserRoleDuplicateError):
            await service.create_user_role(mock_session, data)

    @pytest.mark.asyncio
    async def test_update_user_role_success(
        self, service: RBACService, mock_session: AsyncMock
    ) -> None:
        """update_user_role updates role assignment."""
        mock_row = MagicMock(spec=UserRoleRow)
        mock_row.role = Role.VIEWER
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_row
        mock_session.execute.return_value = mock_result

        data = UserRoleUpdate(role=Role.OPERATOR)
        await service.update_user_role(mock_session, "user@example.com", data)

        assert mock_row.role == Role.OPERATOR
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_user_role_not_found(
        self, service: RBACService, mock_session: AsyncMock
    ) -> None:
        """update_user_role raises for unknown user."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        data = UserRoleUpdate(role=Role.ADMIN)

        with pytest.raises(UserRoleNotFoundError):
            await service.update_user_role(mock_session, "unknown@example.com", data)

    @pytest.mark.asyncio
    async def test_delete_user_role_success(
        self, service: RBACService, mock_session: AsyncMock
    ) -> None:
        """delete_user_role deletes role assignment."""
        mock_row = MagicMock(spec=UserRoleRow)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_row
        mock_session.execute.return_value = mock_result

        await service.delete_user_role(mock_session, "user@example.com")

        mock_session.delete.assert_called_once_with(mock_row)
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_user_role_not_found(
        self, service: RBACService, mock_session: AsyncMock
    ) -> None:
        """delete_user_role raises for unknown user."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with pytest.raises(UserRoleNotFoundError):
            await service.delete_user_role(mock_session, "unknown@example.com")


class TestRBACServiceSingleton:
    """Tests for RBAC service singleton."""

    def test_get_rbac_service_returns_service(self) -> None:
        """get_rbac_service returns RBACService."""
        set_rbac_service(None)
        try:
            service = get_rbac_service()
            assert isinstance(service, RBACService)
        finally:
            set_rbac_service(None)

    def test_get_rbac_service_returns_same_instance(self) -> None:
        """get_rbac_service returns same instance."""
        set_rbac_service(None)
        try:
            service1 = get_rbac_service()
            service2 = get_rbac_service()
            assert service1 is service2
        finally:
            set_rbac_service(None)

    def test_set_rbac_service_overrides(self) -> None:
        """set_rbac_service overrides singleton."""
        mock_service = MagicMock(spec=RBACService)
        set_rbac_service(mock_service)
        try:
            service = get_rbac_service()
            assert service is mock_service
        finally:
            set_rbac_service(None)


class TestGetCurrentUserId:
    """Tests for get_current_user_id dependency."""

    def test_extracts_user_id_from_header(self) -> None:
        """get_current_user_id extracts X-User-ID header."""
        mock_request = MagicMock()
        mock_request.headers.get.return_value = "user@example.com"

        user_id = get_current_user_id(mock_request)

        assert user_id == "user@example.com"
        mock_request.headers.get.assert_called_once_with("X-User-ID")

    def test_raises_401_when_no_header(self) -> None:
        """get_current_user_id raises 401 when header missing."""
        mock_request = MagicMock()
        mock_request.headers.get.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            get_current_user_id(mock_request)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


class TestRequirePermission:
    """Tests for require_permission dependency factory."""

    @pytest.mark.asyncio
    async def test_passes_with_permission(self) -> None:
        """require_permission passes when user has permission."""
        mock_service = MagicMock(spec=RBACService)
        mock_service.has_permission.return_value = True

        set_rbac_service(mock_service)
        try:
            checker = require_permission(Permission.VIEW_HEALTH)
            await checker(user_id="user@example.com", role=Role.VIEWER)
        finally:
            set_rbac_service(None)

    @pytest.mark.asyncio
    async def test_raises_403_without_permission(self) -> None:
        """require_permission raises 403 when user lacks permission."""
        mock_service = MagicMock(spec=RBACService)
        mock_service.has_permission.return_value = False

        set_rbac_service(mock_service)
        try:
            checker = require_permission(Permission.REGISTER_REPO)

            with pytest.raises(HTTPException) as exc_info:
                await checker(user_id="viewer@example.com", role=Role.VIEWER)

            assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
            assert "Permission denied" in exc_info.value.detail
        finally:
            set_rbac_service(None)


class TestGetMinimumRoleForPermission:
    """Tests for _get_minimum_role_for_permission helper."""

    def test_viewer_permission_returns_viewer(self) -> None:
        """View permissions return VIEWER role."""
        assert _get_minimum_role_for_permission(Permission.VIEW_HEALTH) == Role.VIEWER
        assert _get_minimum_role_for_permission(Permission.VIEW_REPOS) == Role.VIEWER

    def test_operator_permission_returns_operator(self) -> None:
        """Operator permissions return OPERATOR role."""
        assert _get_minimum_role_for_permission(Permission.PAUSE_REPO) == Role.OPERATOR
        assert (
            _get_minimum_role_for_permission(Permission.RERUN_VERIFICATION)
            == Role.OPERATOR
        )

    def test_admin_permission_returns_admin(self) -> None:
        """Admin-only permissions return ADMIN role."""
        assert _get_minimum_role_for_permission(Permission.REGISTER_REPO) == Role.ADMIN
        assert _get_minimum_role_for_permission(Permission.MANAGE_USERS) == Role.ADMIN
