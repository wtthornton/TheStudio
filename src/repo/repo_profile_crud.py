"""CRUD operations for Repo Profile."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.repo.defaults import DEFAULT_REQUIRED_CHECKS, DEFAULT_TOOL_ALLOWLIST
from src.repo.repo_profile import (
    RepoProfileCreate,
    RepoProfileRead,
    RepoProfileRow,
    RepoStatus,
    RepoTier,
)
from src.repo.secrets import decrypt_secret, encrypt_secret


async def register(session: AsyncSession, data: RepoProfileCreate) -> RepoProfileRead:
    """Register a new repo. Applies defaults for checks/tools if not provided."""
    checks = data.required_checks if data.required_checks else DEFAULT_REQUIRED_CHECKS
    tools = data.tool_allowlist if data.tool_allowlist else DEFAULT_TOOL_ALLOWLIST

    row = RepoProfileRow(
        owner=data.owner,
        repo_name=data.repo_name,
        installation_id=data.installation_id,
        tier=data.tier,
        required_checks=checks,
        tool_allowlist=tools,
        webhook_secret_encrypted=encrypt_secret(data.webhook_secret),
        status=RepoStatus.ACTIVE,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return RepoProfileRead.model_validate(row)


async def get_by_repo(
    session: AsyncSession, owner: str, repo_name: str
) -> RepoProfileRead | None:
    """Get a repo profile by owner/repo_name."""
    stmt = select(RepoProfileRow).where(
        RepoProfileRow.owner == owner,
        RepoProfileRow.repo_name == repo_name,
    )
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        return None
    return RepoProfileRead.model_validate(row)


async def get_webhook_secret(session: AsyncSession, owner: str, repo_name: str) -> str | None:
    """Get the decrypted webhook secret for signature validation."""
    stmt = select(RepoProfileRow.webhook_secret_encrypted).where(
        RepoProfileRow.owner == owner,
        RepoProfileRow.repo_name == repo_name,
    )
    result = await session.execute(stmt)
    encrypted = result.scalar_one_or_none()
    if encrypted is None:
        return None
    return decrypt_secret(encrypted)


async def get_active_repos(session: AsyncSession) -> list[RepoProfileRead]:
    """Get all active repo profiles."""
    stmt = select(RepoProfileRow).where(RepoProfileRow.status == RepoStatus.ACTIVE)
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [RepoProfileRead.model_validate(r) for r in rows]


async def update_tier(
    session: AsyncSession, profile_id: UUID, new_tier: RepoTier
) -> RepoProfileRead:
    """Update the tier of a repo profile."""
    row = await session.get(RepoProfileRow, profile_id)
    if row is None:
        raise ValueError(f"RepoProfile {profile_id} not found")
    row.tier = new_tier
    await session.commit()
    await session.refresh(row)
    return RepoProfileRead.model_validate(row)


async def update_status(
    session: AsyncSession, profile_id: UUID, new_status: RepoStatus
) -> RepoProfileRead:
    """Update the status of a repo profile."""
    row = await session.get(RepoProfileRow, profile_id)
    if row is None:
        raise ValueError(f"RepoProfile {profile_id} not found")
    row.status = new_status
    await session.commit()
    await session.refresh(row)
    return RepoProfileRead.model_validate(row)
