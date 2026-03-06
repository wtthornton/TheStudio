"""Tests for Story 4.1: Repo Registry Database Persistence.

Tests the RepoRepository class for database-backed repo management.
These tests use mock sessions to avoid requiring a real database.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.repo.repo_profile import (
    RepoProfileCreate,
    RepoProfileRow,
    RepoStatus,
    RepoTier,
)
from src.repo.repository import (
    RepoDuplicateError,
    RepoNotFoundError,
    RepoRepository,
    to_dict,
)


def make_repo_row(
    owner: str = "test-org",
    repo_name: str = "test-repo",
    tier: RepoTier = RepoTier.OBSERVE,
    status: RepoStatus = RepoStatus.ACTIVE,
) -> RepoProfileRow:
    """Create a mock RepoProfileRow for testing."""
    row = MagicMock(spec=RepoProfileRow)
    row.id = uuid4()
    row.owner = owner
    row.repo_name = repo_name
    row.installation_id = 12345
    row.default_branch = "main"
    row.tier = tier
    row.required_checks = ["ruff", "pytest"]
    row.tool_allowlist = []
    row.webhook_secret_encrypted = "secret"
    row.status = status
    row.writes_enabled = True
    row.created_at = datetime.now(UTC)
    row.updated_at = datetime.now(UTC)
    row.deleted_at = None
    row.full_name = f"{owner}/{repo_name}"
    row.is_deleted = False
    return row


class TestRepoRepository:
    """Tests for RepoRepository CRUD operations."""

    @pytest.fixture
    def repository(self) -> RepoRepository:
        """Create a RepoRepository instance."""
        return RepoRepository()

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock AsyncSession."""
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.commit = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_create_new_repo(
        self, repository: RepoRepository, mock_session: AsyncMock
    ) -> None:
        """Can create a new repository."""
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )

        create_data = RepoProfileCreate(
            owner="test-org",
            repo_name="test-repo",
            installation_id=12345,
            webhook_secret="secret123",
        )

        with patch.object(repository, "get_by_full_name", return_value=None):
            row = await repository.create(mock_session, create_data)

        assert row.owner == "test-org"
        assert row.repo_name == "test-repo"
        assert row.tier == RepoTier.OBSERVE
        assert row.status == RepoStatus.ACTIVE
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_duplicate_raises_error(
        self, repository: RepoRepository, mock_session: AsyncMock
    ) -> None:
        """Creating a duplicate repo raises RepoDuplicateError."""
        existing = make_repo_row()

        with patch.object(repository, "get_by_full_name", return_value=existing):
            with pytest.raises(RepoDuplicateError) as exc_info:
                create_data = RepoProfileCreate(
                    owner="test-org",
                    repo_name="test-repo",
                    installation_id=12345,
                    webhook_secret="secret123",
                )
                await repository.create(mock_session, create_data)

        assert "test-org/test-repo" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_existing_repo(
        self, repository: RepoRepository, mock_session: AsyncMock
    ) -> None:
        """Can retrieve an existing repository."""
        existing = make_repo_row()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get(mock_session, existing.id)

        assert result is not None
        assert result.owner == "test-org"

    @pytest.mark.asyncio
    async def test_get_nonexistent_repo_returns_none(
        self, repository: RepoRepository, mock_session: AsyncMock
    ) -> None:
        """Getting a nonexistent repo returns None."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get(mock_session, uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_update_tier(
        self, repository: RepoRepository, mock_session: AsyncMock
    ) -> None:
        """Can update repository tier."""
        existing = make_repo_row(tier=RepoTier.OBSERVE)

        with patch.object(repository, "get", return_value=existing):
            result = await repository.update_tier(
                mock_session, existing.id, RepoTier.SUGGEST
            )

        assert result.tier == RepoTier.SUGGEST
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_tier_nonexistent_raises_error(
        self, repository: RepoRepository, mock_session: AsyncMock
    ) -> None:
        """Updating tier on nonexistent repo raises RepoNotFoundError."""
        with patch.object(repository, "get", return_value=None):
            with pytest.raises(RepoNotFoundError):
                await repository.update_tier(mock_session, uuid4(), RepoTier.SUGGEST)

    @pytest.mark.asyncio
    async def test_update_status(
        self, repository: RepoRepository, mock_session: AsyncMock
    ) -> None:
        """Can update repository status (pause/resume)."""
        existing = make_repo_row(status=RepoStatus.ACTIVE)

        with patch.object(repository, "get", return_value=existing):
            result = await repository.update_status(
                mock_session, existing.id, RepoStatus.PAUSED
            )

        assert result.status == RepoStatus.PAUSED

    @pytest.mark.asyncio
    async def test_set_writes_enabled(
        self, repository: RepoRepository, mock_session: AsyncMock
    ) -> None:
        """Can enable/disable writes (Publisher freeze)."""
        existing = make_repo_row()
        existing.writes_enabled = True

        with patch.object(repository, "get", return_value=existing):
            result = await repository.set_writes_enabled(
                mock_session, existing.id, enabled=False
            )

        assert result.writes_enabled is False

    @pytest.mark.asyncio
    async def test_soft_delete(
        self, repository: RepoRepository, mock_session: AsyncMock
    ) -> None:
        """Can soft-delete a repository."""
        existing = make_repo_row()
        existing.deleted_at = None

        with patch.object(repository, "get", return_value=existing):
            result = await repository.soft_delete(mock_session, existing.id)

        assert result.deleted_at is not None
        assert result.status == RepoStatus.DISABLED

    @pytest.mark.asyncio
    async def test_list_all(
        self, repository: RepoRepository, mock_session: AsyncMock
    ) -> None:
        """Can list all repositories."""
        repos = [
            make_repo_row("org1", "repo1"),
            make_repo_row("org2", "repo2"),
        ]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = repos
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repository.list_all(mock_session)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_count_by_tier(
        self, repository: RepoRepository, mock_session: AsyncMock
    ) -> None:
        """Can count repositories by tier."""
        repos = [
            make_repo_row("org1", "repo1", tier=RepoTier.OBSERVE),
            make_repo_row("org2", "repo2", tier=RepoTier.OBSERVE),
            make_repo_row("org3", "repo3", tier=RepoTier.EXECUTE),
        ]

        with patch.object(repository, "list_all", return_value=repos):
            result = await repository.count_by_tier(mock_session)

        assert result["observe"] == 2
        assert result["execute"] == 1


class TestToDictHelper:
    """Tests for the to_dict helper function."""

    def test_to_dict_converts_row(self) -> None:
        """to_dict converts RepoProfileRow to dict format."""
        row = make_repo_row()

        result = to_dict(row)

        assert result["id"] == row.id
        assert result["owner"] == "test-org"
        assert result["repo"] == "test-repo"
        assert result["repo_name"] == "test-repo"
        assert result["full_name"] == "test-org/test-repo"
        assert result["tier"] == RepoTier.OBSERVE
        assert result["status"] == RepoStatus.ACTIVE
        assert result["writes_enabled"] is True


class TestRepoProfileRowModel:
    """Tests for RepoProfileRow model properties."""

    def test_full_name_property(self) -> None:
        """full_name returns owner/repo_name format."""
        row = make_repo_row("my-org", "my-repo")
        assert row.full_name == "my-org/my-repo"

    def test_is_deleted_false_when_no_deleted_at(self) -> None:
        """is_deleted is False when deleted_at is None."""
        row = make_repo_row()
        row.deleted_at = None
        row.is_deleted = False
        assert row.is_deleted is False

    def test_is_deleted_true_when_deleted_at_set(self) -> None:
        """is_deleted is True when deleted_at is set."""
        row = make_repo_row()
        row.deleted_at = datetime.now(UTC)
        row.is_deleted = True
        assert row.is_deleted is True
