"""Expert registrar — syncs scanned manifests to the database.

Compares manifest version hashes against stored records, creates new experts,
updates changed ones, and optionally deactivates removed experts.

Architecture reference: docs/epics/stories/story-26.3-expert-registration-versioning.md
"""

import logging
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from src.experts.expert import ExpertRead, ExpertRow
from src.experts.expert_crud import (
    create_expert,
    deprecate_expert,
    get_expert_versions,
    search_experts,
    update_expert_version,
)
from src.experts.manifest import manifest_to_expert_create
from src.experts.scanner import ScannedExpert

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """Result of syncing scanned experts against the database."""

    created: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    deactivated: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _get_stored_hash(versions_by_id: dict, expert: ExpertRead) -> str | None:
    """Extract _version_hash from the expert's latest version definition.

    Returns None if no versions exist or the definition lacks _version_hash
    (legacy expert without hash tracking).
    """
    versions = versions_by_id.get(expert.id, [])
    if not versions:
        return None
    latest = max(versions, key=lambda v: v.version)
    return latest.definition.get("_version_hash")


async def sync_experts(
    session: AsyncSession,
    scanned: list[ScannedExpert],
    deactivate_removed: bool = False,
) -> SyncResult:
    """Sync scanned expert manifests against the database.

    For each scanned expert:
    - New name: create via create_expert()
    - Existing name, different hash: update version and top-level fields
    - Existing name, same hash: skip (no DB write)

    If deactivate_removed=True, experts in DB but not in scanned list
    are deprecated.

    Args:
        session: Async database session.
        scanned: List of ScannedExpert from the directory scanner.
        deactivate_removed: Whether to deprecate experts not in scanned list.

    Returns:
        SyncResult with counts per category.
    """
    result = SyncResult()

    # Fetch existing experts and their versions
    existing_experts = await search_experts(session)
    existing_by_name: dict[str, ExpertRead] = {e.name: e for e in existing_experts}

    # Fetch versions for all existing experts to get stored hashes
    versions_by_id = {}
    for expert in existing_experts:
        versions = await get_expert_versions(session, expert.id)
        versions_by_id[expert.id] = versions

    scanned_by_name = {s.manifest.name: s for s in scanned}

    logger.info(
        "Syncing expert manifests",
        extra={
            "scanned_count": len(scanned),
            "existing_count": len(existing_experts),
        },
    )

    for scanned_expert in scanned:
        name = scanned_expert.manifest.name
        expert_create = manifest_to_expert_create(scanned_expert.manifest)

        # Populate context_files contents from supporting files
        if scanned_expert.manifest.context_files:
            context_contents = {}
            for ctx_path in scanned_expert.manifest.context_files:
                for sf in scanned_expert.supporting_files:
                    if sf.relative_path == ctx_path:
                        context_contents[ctx_path] = sf.content
                        break
            expert_create.definition["context_files"] = context_contents

        try:
            if name not in existing_by_name:
                # New expert — create
                await create_expert(session, expert_create)
                result.created.append(name)
                logger.info("Created expert", extra={"expert_name": name})
            else:
                existing = existing_by_name[name]
                stored_hash = _get_stored_hash(versions_by_id, existing)

                if stored_hash == expert_create.definition.get("_version_hash"):
                    # Hash matches — skip
                    result.unchanged.append(name)
                    logger.info("Expert unchanged", extra={"expert_name": name})
                else:
                    # Hash differs or legacy (no hash) — update
                    await update_expert_version(
                        session, existing.id, expert_create.definition
                    )
                    # Update top-level fields on ExpertRow
                    row = await session.get(ExpertRow, existing.id)
                    if row is not None:
                        row.capability_tags = expert_create.capability_tags
                        row.scope_description = expert_create.scope_description
                        row.trust_tier = expert_create.trust_tier
                        row.tool_policy = expert_create.tool_policy
                        await session.flush()

                    result.updated.append(name)
                    logger.info("Updated expert", extra={"expert_name": name})
        except Exception as e:
            result.errors.append(f"{name}: {e}")
            logger.error(
                "Failed to sync expert",
                extra={"expert_name": name, "error": str(e)},
            )

    # Deactivate removed experts
    if deactivate_removed:
        for name, existing in existing_by_name.items():
            if name not in scanned_by_name:
                try:
                    await deprecate_expert(session, existing.id)
                    result.deactivated.append(name)
                    logger.warning(
                        "Deactivating removed expert", extra={"expert_name": name}
                    )
                except Exception as e:
                    result.errors.append(f"{name} (deactivate): {e}")

    return result
