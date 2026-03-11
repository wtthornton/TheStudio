"""Repository module for repo_profile database operations.

Replaces in-memory registry with database-backed CRUD operations.
Story 4.1: Repo Registry Database Persistence.

Architecture reference: thestudioarc/23-admin-control-ui.md
"""

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.repo.repo_profile import (
    RepoProfileCreate,
    RepoProfileRow,
    RepoProfileUpdate,
    RepoStatus,
    RepoTier,
)
from src.repo.secrets import encrypt_secret

logger = logging.getLogger(__name__)


class RepoNotFoundError(Exception):
    """Raised when a repo is not found."""

    def __init__(self, repo_id: UUID) -> None:
        self.repo_id = repo_id
        super().__init__(f"Repository {repo_id} not found")


class RepoDuplicateError(Exception):
    """Raised when a repo already exists."""

    def __init__(self, full_name: str) -> None:
        self.full_name = full_name
        super().__init__(f"Repository {full_name} is already registered")


class RepoRepository:
    """Database repository for repo_profile operations.

    All methods require an AsyncSession. The caller is responsible for
    committing the transaction.
    """

    async def create(
        self,
        session: AsyncSession,
        data: RepoProfileCreate,
    ) -> RepoProfileRow:
        """Register a new repository.

        Args:
            session: Database session.
            data: Repository creation data.

        Returns:
            Created RepoProfileRow.

        Raises:
            RepoDuplicateError: If repo with same owner/repo_name exists.
        """
        full_name = f"{data.owner}/{data.repo_name}"

        existing = await self.get_by_full_name(session, full_name)
        if existing is not None:
            raise RepoDuplicateError(full_name)

        row = RepoProfileRow(
            id=uuid4(),
            owner=data.owner,
            repo_name=data.repo_name,
            installation_id=data.installation_id,
            default_branch=data.default_branch,
            tier=data.tier,
            required_checks=data.required_checks,
            tool_allowlist=data.tool_allowlist,
            webhook_secret_encrypted=encrypt_secret(data.webhook_secret),
            status=RepoStatus.ACTIVE,
            writes_enabled=True,
        )

        session.add(row)
        await session.flush()

        logger.info(
            "Registered repo %s with ID %s at tier %s",
            full_name,
            row.id,
            row.tier.value,
        )

        return row

    async def get(
        self,
        session: AsyncSession,
        repo_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> RepoProfileRow | None:
        """Get a repository by ID.

        Args:
            session: Database session.
            repo_id: Repository UUID.
            include_deleted: If True, include soft-deleted repos.

        Returns:
            RepoProfileRow or None if not found.
        """
        stmt = select(RepoProfileRow).where(RepoProfileRow.id == repo_id)

        if not include_deleted:
            stmt = stmt.where(RepoProfileRow.deleted_at.is_(None))

        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_full_name(
        self,
        session: AsyncSession,
        full_name: str,
        *,
        include_deleted: bool = False,
    ) -> RepoProfileRow | None:
        """Get a repository by full name (owner/repo).

        Args:
            session: Database session.
            full_name: Repository full name in owner/repo format.
            include_deleted: If True, include soft-deleted repos.

        Returns:
            RepoProfileRow or None if not found.
        """
        parts = full_name.split("/", 1)
        if len(parts) != 2:
            return None

        owner, repo_name = parts

        stmt = select(RepoProfileRow).where(
            RepoProfileRow.owner == owner,
            RepoProfileRow.repo_name == repo_name,
        )

        if not include_deleted:
            stmt = stmt.where(RepoProfileRow.deleted_at.is_(None))

        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(
        self,
        session: AsyncSession,
        *,
        include_deleted: bool = False,
        tier: RepoTier | None = None,
        status: RepoStatus | None = None,
    ) -> list[RepoProfileRow]:
        """List all repositories with optional filters.

        Args:
            session: Database session.
            include_deleted: If True, include soft-deleted repos.
            tier: Filter by tier.
            status: Filter by status.

        Returns:
            List of RepoProfileRow.
        """
        stmt = select(RepoProfileRow)

        if not include_deleted:
            stmt = stmt.where(RepoProfileRow.deleted_at.is_(None))

        if tier is not None:
            stmt = stmt.where(RepoProfileRow.tier == tier)

        if status is not None:
            stmt = stmt.where(RepoProfileRow.status == status)

        stmt = stmt.order_by(RepoProfileRow.created_at.desc())

        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_tier(
        self,
        session: AsyncSession,
        *,
        include_deleted: bool = False,
    ) -> dict[str, int]:
        """Count repositories by tier.

        Args:
            session: Database session.
            include_deleted: If True, include soft-deleted repos.

        Returns:
            Dict mapping tier value to count.
        """
        repos = await self.list_all(session, include_deleted=include_deleted)
        counts: dict[str, int] = {}
        for repo in repos:
            tier_value = repo.tier.value
            counts[tier_value] = counts.get(tier_value, 0) + 1
        return counts

    async def update_profile(
        self,
        session: AsyncSession,
        repo_id: UUID,
        data: RepoProfileUpdate,
    ) -> RepoProfileRow:
        """Update repository profile fields.

        Args:
            session: Database session.
            repo_id: Repository UUID.
            data: Fields to update.

        Returns:
            Updated RepoProfileRow.

        Raises:
            RepoNotFoundError: If repo not found.
        """
        repo = await self.get(session, repo_id)
        if repo is None:
            raise RepoNotFoundError(repo_id)

        if data.default_branch is not None:
            repo.default_branch = data.default_branch
        if data.required_checks is not None:
            repo.required_checks = data.required_checks
        if data.tool_allowlist is not None:
            repo.tool_allowlist = data.tool_allowlist
        if data.poll_enabled is not None:
            repo.poll_enabled = data.poll_enabled
        if data.poll_interval_minutes is not None:
            repo.poll_interval_minutes = data.poll_interval_minutes

        await session.flush()

        logger.info("Updated profile for repo %s", repo.full_name)

        return repo

    async def update_tier(
        self,
        session: AsyncSession,
        repo_id: UUID,
        tier: RepoTier,
    ) -> RepoProfileRow:
        """Update repository tier.

        Args:
            session: Database session.
            repo_id: Repository UUID.
            tier: New tier.

        Returns:
            Updated RepoProfileRow.

        Raises:
            RepoNotFoundError: If repo not found.
        """
        repo = await self.get(session, repo_id)
        if repo is None:
            raise RepoNotFoundError(repo_id)

        old_tier = repo.tier
        repo.tier = tier

        await session.flush()

        logger.info(
            "Updated tier for repo %s: %s -> %s",
            repo.full_name,
            old_tier.value,
            tier.value,
        )

        return repo

    async def update_status(
        self,
        session: AsyncSession,
        repo_id: UUID,
        status: RepoStatus,
    ) -> RepoProfileRow:
        """Update repository status (active/paused/disabled).

        Args:
            session: Database session.
            repo_id: Repository UUID.
            status: New status.

        Returns:
            Updated RepoProfileRow.

        Raises:
            RepoNotFoundError: If repo not found.
        """
        repo = await self.get(session, repo_id)
        if repo is None:
            raise RepoNotFoundError(repo_id)

        old_status = repo.status
        repo.status = status

        await session.flush()

        logger.info(
            "Updated status for repo %s: %s -> %s",
            repo.full_name,
            old_status.value,
            status.value,
        )

        return repo

    async def set_writes_enabled(
        self,
        session: AsyncSession,
        repo_id: UUID,
        *,
        enabled: bool,
    ) -> RepoProfileRow:
        """Enable or disable writes (Publisher freeze).

        Args:
            session: Database session.
            repo_id: Repository UUID.
            enabled: True to enable writes, False to freeze.

        Returns:
            Updated RepoProfileRow.

        Raises:
            RepoNotFoundError: If repo not found.
        """
        repo = await self.get(session, repo_id)
        if repo is None:
            raise RepoNotFoundError(repo_id)

        repo.writes_enabled = enabled

        await session.flush()

        action = "enabled" if enabled else "disabled"
        logger.info("Writes %s for repo %s", action, repo.full_name)

        return repo

    async def soft_delete(
        self,
        session: AsyncSession,
        repo_id: UUID,
    ) -> RepoProfileRow:
        """Soft delete a repository.

        Args:
            session: Database session.
            repo_id: Repository UUID.

        Returns:
            Soft-deleted RepoProfileRow.

        Raises:
            RepoNotFoundError: If repo not found.
        """
        repo = await self.get(session, repo_id)
        if repo is None:
            raise RepoNotFoundError(repo_id)

        repo.deleted_at = datetime.now(UTC)
        repo.status = RepoStatus.DISABLED

        await session.flush()

        logger.info("Soft-deleted repo %s", repo.full_name)

        return repo

    async def restore(
        self,
        session: AsyncSession,
        repo_id: UUID,
    ) -> RepoProfileRow:
        """Restore a soft-deleted repository.

        Args:
            session: Database session.
            repo_id: Repository UUID.

        Returns:
            Restored RepoProfileRow.

        Raises:
            RepoNotFoundError: If repo not found (including deleted).
        """
        repo = await self.get(session, repo_id, include_deleted=True)
        if repo is None:
            raise RepoNotFoundError(repo_id)

        repo.deleted_at = None
        repo.status = RepoStatus.ACTIVE

        await session.flush()

        logger.info("Restored repo %s", repo.full_name)

        return repo


def to_dict(row: RepoProfileRow) -> dict[str, Any]:
    """Convert RepoProfileRow to dict for API responses.

    This helper maintains compatibility with existing code that expects
    dict format from the in-memory registry.
    """
    return {
        "id": row.id,
        "owner": row.owner,
        "repo": row.repo_name,
        "repo_name": row.repo_name,
        "full_name": row.full_name,
        "tier": row.tier,
        "status": row.status,
        "installation_id": row.installation_id,
        "default_branch": row.default_branch,
        "required_checks": row.required_checks,
        "tool_allowlist": row.tool_allowlist,
        "writes_enabled": row.writes_enabled,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "deleted_at": row.deleted_at,
    }
