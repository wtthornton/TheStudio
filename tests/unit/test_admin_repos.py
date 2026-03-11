"""Tests for Story 4.4: Repo Management API — List, Register, Update.

Tests the admin repo endpoints for listing, registering, and updating repos.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import status

from src.admin.audit import set_audit_service
from src.admin.router import (
    RepoListItem,
    RepoListResponse,
    RepoProfileResponse,
    RepoProfileUpdateRequest,
    RepoProfileUpdateResponse,
    RepoRegisterRequest,
    RepoRegisterResponse,
    set_repo_repository,
)
from src.repo.repo_profile import RepoStatus, RepoTier
from src.repo.repository import RepoDuplicateError, RepoNotFoundError, RepoRepository


def _make_mock_http_request(user_id: str = "admin@example.com") -> MagicMock:
    """Create a mock HTTP request with X-User-ID header."""
    mock_request = MagicMock()
    mock_request.headers.get.return_value = user_id
    return mock_request


class TestRepoListItem:
    """Tests for RepoListItem model."""

    def test_create_list_item(self) -> None:
        """RepoListItem can be created with required fields."""
        item = RepoListItem(
            id=uuid4(),
            owner="homeiq",
            repo="platform",
            tier=RepoTier.EXECUTE,
            status=RepoStatus.ACTIVE,
            installation_id=12345,
            health="ok",
        )

        assert item.owner == "homeiq"
        assert item.repo == "platform"
        assert item.tier == RepoTier.EXECUTE
        assert item.health == "ok"

    def test_default_health(self) -> None:
        """RepoListItem defaults health to unknown."""
        item = RepoListItem(
            id=uuid4(),
            owner="test",
            repo="repo",
            tier=RepoTier.OBSERVE,
            status=RepoStatus.ACTIVE,
            installation_id=1,
        )

        assert item.health == "unknown"


class TestRepoRegisterRequest:
    """Tests for RepoRegisterRequest model."""

    def test_valid_request(self) -> None:
        """RepoRegisterRequest accepts valid data."""
        request = RepoRegisterRequest(
            owner="homeiq",
            repo="platform",
            installation_id=12345,
            default_branch="main",
        )

        assert request.owner == "homeiq"
        assert request.repo == "platform"
        assert request.installation_id == 12345

    def test_default_branch(self) -> None:
        """RepoRegisterRequest defaults branch to main."""
        request = RepoRegisterRequest(
            owner="test",
            repo="repo",
            installation_id=1,
        )

        assert request.default_branch == "main"


class MockRepoProfileRow:
    """Mock RepoProfileRow for testing."""

    def __init__(
        self,
        repo_id: UUID | None = None,
        owner: str = "test",
        repo_name: str = "repo",
        tier: RepoTier = RepoTier.OBSERVE,
        status_val: RepoStatus = RepoStatus.ACTIVE,
        installation_id: int = 12345,
    ) -> None:
        self.id = repo_id or uuid4()
        self.owner = owner
        self.repo_name = repo_name
        self.tier = tier
        self.status = status_val
        self.installation_id = installation_id
        self.default_branch = "main"
        self.required_checks = ["ruff", "pytest"]
        self.tool_allowlist: list[str] = []
        self.writes_enabled = True
        self.poll_enabled = False
        self.poll_interval_minutes = 15
        self.created_at = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.repo_name}"


class TestListRepos:
    """Tests for GET /admin/repos endpoint."""

    @pytest.fixture
    def mock_repo_repository(self) -> AsyncMock:
        """Create mock repo repository."""
        return AsyncMock(spec=RepoRepository)

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create mock database session."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_list_repos_empty(
        self, mock_repo_repository: AsyncMock, mock_session: AsyncMock
    ) -> None:
        """list_repos returns empty list when no repos."""
        mock_repo_repository.list_all.return_value = []

        from src.admin.router import list_repos

        set_repo_repository(mock_repo_repository)
        try:
            result = await list_repos(mock_session)

            assert isinstance(result, RepoListResponse)
            assert result.repos == []
            assert result.total == 0
        finally:
            set_repo_repository(None)

    @pytest.mark.asyncio
    async def test_list_repos_with_data(
        self, mock_repo_repository: AsyncMock, mock_session: AsyncMock
    ) -> None:
        """list_repos returns repos with correct data."""
        repo1 = MockRepoProfileRow(owner="homeiq", repo_name="platform")
        repo2 = MockRepoProfileRow(
            owner="tango",
            repo_name="core",
            tier=RepoTier.SUGGEST,
            status_val=RepoStatus.PAUSED,
        )
        mock_repo_repository.list_all.return_value = [repo1, repo2]

        from src.admin.router import list_repos

        set_repo_repository(mock_repo_repository)
        try:
            result = await list_repos(mock_session)

            assert result.total == 2
            assert result.repos[0].owner == "homeiq"
            assert result.repos[0].repo == "platform"
            assert result.repos[0].health == "ok"
            assert result.repos[1].owner == "tango"
            assert result.repos[1].health == "degraded"
        finally:
            set_repo_repository(None)


class TestRegisterRepo:
    """Tests for POST /admin/repos endpoint."""

    @pytest.fixture
    def mock_repo_repository(self) -> AsyncMock:
        """Create mock repo repository."""
        return AsyncMock(spec=RepoRepository)

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def mock_audit_service(self) -> AsyncMock:
        """Create mock audit service."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_register_repo_success(
        self,
        mock_repo_repository: AsyncMock,
        mock_session: AsyncMock,
        mock_audit_service: AsyncMock,
    ) -> None:
        """register_repo creates new repo at Observe tier."""
        created_repo = MockRepoProfileRow(owner="homeiq", repo_name="platform")
        mock_repo_repository.create.return_value = created_repo

        from src.admin.router import register_repo

        request = RepoRegisterRequest(
            owner="homeiq",
            repo="platform",
            installation_id=12345,
        )
        http_request = _make_mock_http_request()

        set_repo_repository(mock_repo_repository)
        set_audit_service(mock_audit_service)
        try:
            result = await register_repo(request, http_request, mock_session)

            assert isinstance(result, RepoRegisterResponse)
            assert result.owner == "homeiq"
            assert result.repo == "platform"
            assert result.tier == RepoTier.OBSERVE
            mock_session.commit.assert_called_once()
        finally:
            set_repo_repository(None)
            set_audit_service(None)

    @pytest.mark.asyncio
    async def test_register_repo_duplicate_409(
        self, mock_repo_repository: AsyncMock, mock_session: AsyncMock
    ) -> None:
        """register_repo returns 409 for duplicate repo."""
        mock_repo_repository.create.side_effect = RepoDuplicateError("homeiq/platform")

        from fastapi import HTTPException

        from src.admin.router import register_repo

        request = RepoRegisterRequest(
            owner="homeiq",
            repo="platform",
            installation_id=12345,
        )
        http_request = _make_mock_http_request()

        set_repo_repository(mock_repo_repository)
        try:
            with pytest.raises(HTTPException) as exc_info:
                await register_repo(request, http_request, mock_session)

            assert exc_info.value.status_code == status.HTTP_409_CONFLICT
            assert "already registered" in exc_info.value.detail
        finally:
            set_repo_repository(None)

    @pytest.mark.asyncio
    async def test_register_repo_emits_audit_event(
        self,
        mock_repo_repository: AsyncMock,
        mock_session: AsyncMock,
        mock_audit_service: AsyncMock,
    ) -> None:
        """register_repo emits repo_registered audit event."""
        created_repo = MockRepoProfileRow(owner="homeiq", repo_name="platform")
        mock_repo_repository.create.return_value = created_repo

        from src.admin.router import register_repo

        request = RepoRegisterRequest(
            owner="homeiq",
            repo="platform",
            installation_id=12345,
        )
        http_request = _make_mock_http_request()

        set_repo_repository(mock_repo_repository)
        set_audit_service(mock_audit_service)
        try:
            await register_repo(request, http_request, mock_session)

            mock_audit_service.log_repo_event.assert_called_once()
        finally:
            set_repo_repository(None)
            set_audit_service(None)


class TestGetRepoDetail:
    """Tests for GET /admin/repos/{id} endpoint."""

    @pytest.fixture
    def mock_repo_repository(self) -> AsyncMock:
        """Create mock repo repository."""
        return AsyncMock(spec=RepoRepository)

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create mock database session."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_get_repo_detail_success(
        self, mock_repo_repository: AsyncMock, mock_session: AsyncMock
    ) -> None:
        """get_repo_detail returns full profile."""
        repo_id = uuid4()
        repo = MockRepoProfileRow(repo_id=repo_id, owner="homeiq", repo_name="platform")
        mock_repo_repository.get.return_value = repo

        from src.admin.router import get_repo_detail

        set_repo_repository(mock_repo_repository)
        try:
            result = await get_repo_detail(repo_id, mock_session)

            assert isinstance(result, RepoProfileResponse)
            assert result.id == repo_id
            assert result.owner == "homeiq"
            assert result.repo == "platform"
            assert result.required_checks == ["ruff", "pytest"]
        finally:
            set_repo_repository(None)

    @pytest.mark.asyncio
    async def test_get_repo_detail_not_found_404(
        self, mock_repo_repository: AsyncMock, mock_session: AsyncMock
    ) -> None:
        """get_repo_detail returns 404 for unknown repo."""
        mock_repo_repository.get.return_value = None

        from fastapi import HTTPException

        from src.admin.router import get_repo_detail

        set_repo_repository(mock_repo_repository)
        try:
            with pytest.raises(HTTPException) as exc_info:
                await get_repo_detail(uuid4(), mock_session)

            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        finally:
            set_repo_repository(None)


class TestUpdateRepoProfile:
    """Tests for PATCH /admin/repos/{id}/profile endpoint."""

    @pytest.fixture
    def mock_repo_repository(self) -> AsyncMock:
        """Create mock repo repository."""
        return AsyncMock(spec=RepoRepository)

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def mock_audit_service(self) -> AsyncMock:
        """Create mock audit service."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_update_profile_success(
        self,
        mock_repo_repository: AsyncMock,
        mock_session: AsyncMock,
        mock_audit_service: AsyncMock,
    ) -> None:
        """update_repo_profile updates specified fields."""
        repo_id = uuid4()
        repo = MockRepoProfileRow(repo_id=repo_id, owner="homeiq", repo_name="platform")
        mock_repo_repository.update_profile.return_value = repo

        from src.admin.router import update_repo_profile

        request = RepoProfileUpdateRequest(
            required_checks=["ruff", "pytest", "mypy"],
        )
        http_request = _make_mock_http_request()

        set_repo_repository(mock_repo_repository)
        set_audit_service(mock_audit_service)
        try:
            result = await update_repo_profile(repo_id, request, http_request, mock_session)

            assert isinstance(result, RepoProfileUpdateResponse)
            assert result.id == repo_id
            assert "required_checks" in result.updated_fields
            mock_session.commit.assert_called_once()
        finally:
            set_repo_repository(None)
            set_audit_service(None)

    @pytest.mark.asyncio
    async def test_update_profile_not_found_404(
        self, mock_repo_repository: AsyncMock, mock_session: AsyncMock
    ) -> None:
        """update_repo_profile returns 404 for unknown repo."""
        mock_repo_repository.update_profile.side_effect = RepoNotFoundError(uuid4())

        from fastapi import HTTPException

        from src.admin.router import update_repo_profile

        request = RepoProfileUpdateRequest(default_branch="develop")
        http_request = _make_mock_http_request()

        set_repo_repository(mock_repo_repository)
        try:
            with pytest.raises(HTTPException) as exc_info:
                await update_repo_profile(uuid4(), request, http_request, mock_session)

            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        finally:
            set_repo_repository(None)

    @pytest.mark.asyncio
    async def test_update_profile_emits_audit_event(
        self,
        mock_repo_repository: AsyncMock,
        mock_session: AsyncMock,
        mock_audit_service: AsyncMock,
    ) -> None:
        """update_repo_profile emits repo_profile_updated audit event."""
        repo_id = uuid4()
        repo = MockRepoProfileRow(repo_id=repo_id, owner="homeiq", repo_name="platform")
        mock_repo_repository.update_profile.return_value = repo

        from src.admin.router import update_repo_profile

        request = RepoProfileUpdateRequest(default_branch="develop")
        http_request = _make_mock_http_request()

        set_repo_repository(mock_repo_repository)
        set_audit_service(mock_audit_service)
        try:
            await update_repo_profile(repo_id, request, http_request, mock_session)

            mock_audit_service.log_repo_event.assert_called_once()
        finally:
            set_repo_repository(None)
            set_audit_service(None)

    @pytest.mark.asyncio
    async def test_update_profile_tracks_updated_fields(
        self,
        mock_repo_repository: AsyncMock,
        mock_session: AsyncMock,
        mock_audit_service: AsyncMock,
    ) -> None:
        """update_repo_profile correctly tracks which fields were updated."""
        repo_id = uuid4()
        repo = MockRepoProfileRow(repo_id=repo_id)
        mock_repo_repository.update_profile.return_value = repo

        from src.admin.router import update_repo_profile

        request = RepoProfileUpdateRequest(
            default_branch="develop",
            required_checks=["ruff"],
            tool_allowlist=["edit_file"],
        )
        http_request = _make_mock_http_request()

        set_repo_repository(mock_repo_repository)
        set_audit_service(mock_audit_service)
        try:
            result = await update_repo_profile(repo_id, request, http_request, mock_session)

            assert "default_branch" in result.updated_fields
            assert "required_checks" in result.updated_fields
            assert "tool_allowlist" in result.updated_fields
            assert len(result.updated_fields) == 3
        finally:
            set_repo_repository(None)
            set_audit_service(None)


class TestHealthDerivation:
    """Tests for health field derivation from status."""

    def test_active_status_health_ok(self) -> None:
        """Active repos have health=ok."""
        from src.admin.router import RepoListItem

        item = RepoListItem(
            id=uuid4(),
            owner="test",
            repo="repo",
            tier=RepoTier.OBSERVE,
            status=RepoStatus.ACTIVE,
            installation_id=1,
            health="ok",
        )

        assert item.health == "ok"

    def test_paused_status_health_degraded(self) -> None:
        """Paused repos have health=degraded."""
        from src.admin.router import RepoListItem

        item = RepoListItem(
            id=uuid4(),
            owner="test",
            repo="repo",
            tier=RepoTier.OBSERVE,
            status=RepoStatus.PAUSED,
            installation_id=1,
            health="degraded",
        )

        assert item.health == "degraded"


# --- Story 4.5 Tests: Tier, Pause, Writes ---


class TestChangeTier:
    """Tests for PATCH /admin/repos/{id}/tier endpoint."""

    @pytest.fixture
    def mock_repo_repository(self) -> AsyncMock:
        """Create mock repo repository."""
        return AsyncMock(spec=RepoRepository)

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def mock_audit_service(self) -> AsyncMock:
        """Create mock audit service."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_change_tier_success(
        self,
        mock_repo_repository: AsyncMock,
        mock_session: AsyncMock,
        mock_audit_service: AsyncMock,
    ) -> None:
        """change_repo_tier updates tier and returns old/new values."""
        repo_id = uuid4()
        repo = MockRepoProfileRow(
            repo_id=repo_id, owner="homeiq", repo_name="platform"
        )
        repo.tier = RepoTier.OBSERVE
        mock_repo_repository.get.return_value = repo

        updated_repo = MockRepoProfileRow(
            repo_id=repo_id, owner="homeiq", repo_name="platform"
        )
        updated_repo.tier = RepoTier.SUGGEST
        mock_repo_repository.update_tier.return_value = updated_repo

        from src.admin.router import (
            RepoTierChangeRequest,
            RepoTierChangeResponse,
            change_repo_tier,
        )

        request = RepoTierChangeRequest(tier=RepoTier.SUGGEST)
        http_request = _make_mock_http_request()

        set_repo_repository(mock_repo_repository)
        set_audit_service(mock_audit_service)
        try:
            result = await change_repo_tier(repo_id, request, http_request, mock_session)

            assert isinstance(result, RepoTierChangeResponse)
            assert result.from_tier == RepoTier.OBSERVE
            assert result.to_tier == RepoTier.SUGGEST
            mock_session.commit.assert_called_once()
        finally:
            set_repo_repository(None)
            set_audit_service(None)

    @pytest.mark.asyncio
    async def test_change_tier_not_found_404(
        self, mock_repo_repository: AsyncMock, mock_session: AsyncMock
    ) -> None:
        """change_repo_tier returns 404 for unknown repo."""
        mock_repo_repository.get.return_value = None

        from fastapi import HTTPException

        from src.admin.router import RepoTierChangeRequest, change_repo_tier

        request = RepoTierChangeRequest(tier=RepoTier.EXECUTE)
        http_request = _make_mock_http_request()

        set_repo_repository(mock_repo_repository)
        try:
            with pytest.raises(HTTPException) as exc_info:
                await change_repo_tier(uuid4(), request, http_request, mock_session)

            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        finally:
            set_repo_repository(None)

    @pytest.mark.asyncio
    async def test_change_tier_emits_audit_event(
        self,
        mock_repo_repository: AsyncMock,
        mock_session: AsyncMock,
        mock_audit_service: AsyncMock,
    ) -> None:
        """change_repo_tier emits repo_tier_changed audit event."""
        repo_id = uuid4()
        repo = MockRepoProfileRow(repo_id=repo_id)
        repo.tier = RepoTier.OBSERVE
        mock_repo_repository.get.return_value = repo

        updated_repo = MockRepoProfileRow(repo_id=repo_id)
        updated_repo.tier = RepoTier.EXECUTE
        mock_repo_repository.update_tier.return_value = updated_repo

        from src.admin.router import RepoTierChangeRequest, change_repo_tier

        request = RepoTierChangeRequest(tier=RepoTier.EXECUTE)
        http_request = _make_mock_http_request()

        set_repo_repository(mock_repo_repository)
        set_audit_service(mock_audit_service)
        try:
            await change_repo_tier(repo_id, request, http_request, mock_session)

            mock_audit_service.log_repo_event.assert_called_once()
        finally:
            set_repo_repository(None)
            set_audit_service(None)


class TestPauseRepo:
    """Tests for POST /admin/repos/{id}/pause endpoint."""

    @pytest.fixture
    def mock_repo_repository(self) -> AsyncMock:
        """Create mock repo repository."""
        return AsyncMock(spec=RepoRepository)

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def mock_audit_service(self) -> AsyncMock:
        """Create mock audit service."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_pause_repo_success(
        self,
        mock_repo_repository: AsyncMock,
        mock_session: AsyncMock,
        mock_audit_service: AsyncMock,
    ) -> None:
        """pause_repo sets status to PAUSED."""
        repo_id = uuid4()
        repo = MockRepoProfileRow(repo_id=repo_id, status_val=RepoStatus.PAUSED)
        mock_repo_repository.update_status.return_value = repo

        from src.admin.router import RepoStatusChangeResponse, pause_repo

        http_request = _make_mock_http_request()

        set_repo_repository(mock_repo_repository)
        set_audit_service(mock_audit_service)
        try:
            result = await pause_repo(repo_id, http_request, mock_session)

            assert isinstance(result, RepoStatusChangeResponse)
            assert result.status == RepoStatus.PAUSED
            mock_repo_repository.update_status.assert_called_once_with(
                mock_session, repo_id, RepoStatus.PAUSED
            )
            mock_session.commit.assert_called_once()
        finally:
            set_repo_repository(None)
            set_audit_service(None)

    @pytest.mark.asyncio
    async def test_pause_repo_not_found_404(
        self, mock_repo_repository: AsyncMock, mock_session: AsyncMock
    ) -> None:
        """pause_repo returns 404 for unknown repo."""
        mock_repo_repository.update_status.side_effect = RepoNotFoundError(uuid4())

        from fastapi import HTTPException

        from src.admin.router import pause_repo

        http_request = _make_mock_http_request()

        set_repo_repository(mock_repo_repository)
        try:
            with pytest.raises(HTTPException) as exc_info:
                await pause_repo(uuid4(), http_request, mock_session)

            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        finally:
            set_repo_repository(None)

    @pytest.mark.asyncio
    async def test_pause_repo_emits_audit_event(
        self,
        mock_repo_repository: AsyncMock,
        mock_session: AsyncMock,
        mock_audit_service: AsyncMock,
    ) -> None:
        """pause_repo emits repo_paused audit event."""
        repo_id = uuid4()
        repo = MockRepoProfileRow(repo_id=repo_id, status_val=RepoStatus.PAUSED)
        mock_repo_repository.update_status.return_value = repo

        from src.admin.router import pause_repo

        http_request = _make_mock_http_request()

        set_repo_repository(mock_repo_repository)
        set_audit_service(mock_audit_service)
        try:
            await pause_repo(repo_id, http_request, mock_session)

            mock_audit_service.log_repo_event.assert_called_once()
        finally:
            set_repo_repository(None)
            set_audit_service(None)


class TestResumeRepo:
    """Tests for POST /admin/repos/{id}/resume endpoint."""

    @pytest.fixture
    def mock_repo_repository(self) -> AsyncMock:
        """Create mock repo repository."""
        return AsyncMock(spec=RepoRepository)

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def mock_audit_service(self) -> AsyncMock:
        """Create mock audit service."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_resume_repo_success(
        self,
        mock_repo_repository: AsyncMock,
        mock_session: AsyncMock,
        mock_audit_service: AsyncMock,
    ) -> None:
        """resume_repo sets status to ACTIVE."""
        repo_id = uuid4()
        repo = MockRepoProfileRow(repo_id=repo_id, status_val=RepoStatus.ACTIVE)
        mock_repo_repository.update_status.return_value = repo

        from src.admin.router import RepoStatusChangeResponse, resume_repo

        http_request = _make_mock_http_request()

        set_repo_repository(mock_repo_repository)
        set_audit_service(mock_audit_service)
        try:
            result = await resume_repo(repo_id, http_request, mock_session)

            assert isinstance(result, RepoStatusChangeResponse)
            assert result.status == RepoStatus.ACTIVE
            mock_repo_repository.update_status.assert_called_once_with(
                mock_session, repo_id, RepoStatus.ACTIVE
            )
            mock_session.commit.assert_called_once()
        finally:
            set_repo_repository(None)
            set_audit_service(None)

    @pytest.mark.asyncio
    async def test_resume_repo_not_found_404(
        self, mock_repo_repository: AsyncMock, mock_session: AsyncMock
    ) -> None:
        """resume_repo returns 404 for unknown repo."""
        mock_repo_repository.update_status.side_effect = RepoNotFoundError(uuid4())

        from fastapi import HTTPException

        from src.admin.router import resume_repo

        http_request = _make_mock_http_request()

        set_repo_repository(mock_repo_repository)
        try:
            with pytest.raises(HTTPException) as exc_info:
                await resume_repo(uuid4(), http_request, mock_session)

            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        finally:
            set_repo_repository(None)

    @pytest.mark.asyncio
    async def test_resume_repo_emits_audit_event(
        self,
        mock_repo_repository: AsyncMock,
        mock_session: AsyncMock,
        mock_audit_service: AsyncMock,
    ) -> None:
        """resume_repo emits repo_resumed audit event."""
        repo_id = uuid4()
        repo = MockRepoProfileRow(repo_id=repo_id, status_val=RepoStatus.ACTIVE)
        mock_repo_repository.update_status.return_value = repo

        from src.admin.router import resume_repo

        http_request = _make_mock_http_request()

        set_repo_repository(mock_repo_repository)
        set_audit_service(mock_audit_service)
        try:
            await resume_repo(repo_id, http_request, mock_session)

            mock_audit_service.log_repo_event.assert_called_once()
        finally:
            set_repo_repository(None)
            set_audit_service(None)


class TestToggleWrites:
    """Tests for POST /admin/repos/{id}/writes endpoint."""

    @pytest.fixture
    def mock_repo_repository(self) -> AsyncMock:
        """Create mock repo repository."""
        return AsyncMock(spec=RepoRepository)

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def mock_audit_service(self) -> AsyncMock:
        """Create mock audit service."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_disable_writes_success(
        self,
        mock_repo_repository: AsyncMock,
        mock_session: AsyncMock,
        mock_audit_service: AsyncMock,
    ) -> None:
        """toggle_repo_writes can disable writes."""
        repo_id = uuid4()
        repo = MockRepoProfileRow(repo_id=repo_id)
        repo.writes_enabled = False
        mock_repo_repository.set_writes_enabled.return_value = repo

        from src.admin.router import (
            RepoWritesChangeRequest,
            RepoWritesChangeResponse,
            toggle_repo_writes,
        )

        request = RepoWritesChangeRequest(enabled=False)
        http_request = _make_mock_http_request()

        set_repo_repository(mock_repo_repository)
        set_audit_service(mock_audit_service)
        try:
            result = await toggle_repo_writes(repo_id, request, http_request, mock_session)

            assert isinstance(result, RepoWritesChangeResponse)
            assert result.writes_enabled is False
            mock_repo_repository.set_writes_enabled.assert_called_once_with(
                mock_session, repo_id, enabled=False
            )
            mock_session.commit.assert_called_once()
        finally:
            set_repo_repository(None)
            set_audit_service(None)

    @pytest.mark.asyncio
    async def test_enable_writes_success(
        self,
        mock_repo_repository: AsyncMock,
        mock_session: AsyncMock,
        mock_audit_service: AsyncMock,
    ) -> None:
        """toggle_repo_writes can enable writes."""
        repo_id = uuid4()
        repo = MockRepoProfileRow(repo_id=repo_id)
        repo.writes_enabled = True
        mock_repo_repository.set_writes_enabled.return_value = repo

        from src.admin.router import (
            RepoWritesChangeRequest,
            RepoWritesChangeResponse,
            toggle_repo_writes,
        )

        request = RepoWritesChangeRequest(enabled=True)
        http_request = _make_mock_http_request()

        set_repo_repository(mock_repo_repository)
        set_audit_service(mock_audit_service)
        try:
            result = await toggle_repo_writes(repo_id, request, http_request, mock_session)

            assert isinstance(result, RepoWritesChangeResponse)
            assert result.writes_enabled is True
        finally:
            set_repo_repository(None)
            set_audit_service(None)

    @pytest.mark.asyncio
    async def test_toggle_writes_not_found_404(
        self, mock_repo_repository: AsyncMock, mock_session: AsyncMock
    ) -> None:
        """toggle_repo_writes returns 404 for unknown repo."""
        mock_repo_repository.set_writes_enabled.side_effect = RepoNotFoundError(uuid4())

        from fastapi import HTTPException

        from src.admin.router import RepoWritesChangeRequest, toggle_repo_writes

        request = RepoWritesChangeRequest(enabled=False)
        http_request = _make_mock_http_request()

        set_repo_repository(mock_repo_repository)
        try:
            with pytest.raises(HTTPException) as exc_info:
                await toggle_repo_writes(uuid4(), request, http_request, mock_session)

            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        finally:
            set_repo_repository(None)

    @pytest.mark.asyncio
    async def test_toggle_writes_emits_audit_event(
        self,
        mock_repo_repository: AsyncMock,
        mock_session: AsyncMock,
        mock_audit_service: AsyncMock,
    ) -> None:
        """toggle_repo_writes emits repo_writes_toggled audit event."""
        repo_id = uuid4()
        repo = MockRepoProfileRow(repo_id=repo_id)
        repo.writes_enabled = False
        mock_repo_repository.set_writes_enabled.return_value = repo

        from src.admin.router import RepoWritesChangeRequest, toggle_repo_writes

        request = RepoWritesChangeRequest(enabled=False)
        http_request = _make_mock_http_request()

        set_repo_repository(mock_repo_repository)
        set_audit_service(mock_audit_service)
        try:
            await toggle_repo_writes(repo_id, request, http_request, mock_session)

            mock_audit_service.log_repo_event.assert_called_once()
        finally:
            set_repo_repository(None)
            set_audit_service(None)
