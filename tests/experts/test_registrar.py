"""Tests for expert registrar (Story 26.3)."""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.experts.expert import (
    ExpertClass,
    ExpertRead,
    ExpertVersionRead,
    LifecycleState,
    TrustTier,
)
from src.experts.manifest import ExpertManifest
from src.experts.registrar import SyncResult, _get_stored_hash, sync_experts
from src.experts.scanner import ScannedExpert

# --- Helpers ---

_NOW = datetime(2026, 3, 13, tzinfo=UTC)


def _make_expert_read(
    name: str,
    version: int = 1,
    expert_class: ExpertClass = ExpertClass.TECHNICAL,
) -> ExpertRead:
    return ExpertRead(
        id=uuid4(),
        name=name,
        expert_class=expert_class,
        capability_tags=["tag"],
        scope_description=f"Expert {name}",
        tool_policy={},
        trust_tier=TrustTier.SHADOW,
        lifecycle_state=LifecycleState.ACTIVE,
        current_version=version,
        created_at=_NOW,
        updated_at=_NOW,
    )


def _make_version_read(
    expert_id, version: int = 1, version_hash: str | None = "abc123"
) -> ExpertVersionRead:
    definition: dict = {"scope_boundaries": [], "system_prompt_template": "prompt"}
    if version_hash is not None:
        definition["_version_hash"] = version_hash
    return ExpertVersionRead(
        id=uuid4(),
        expert_id=expert_id,
        version=version,
        definition=definition,
        created_at=_NOW,
    )


def _make_scanned(
    name: str,
    version_hash: str = "newhash",
    expert_class: ExpertClass = ExpertClass.TECHNICAL,
) -> ScannedExpert:
    manifest = ExpertManifest(
        name=name,
        expert_class=expert_class,
        capability_tags=["tag"],
        description=f"Expert {name}",
        trust_tier=TrustTier.SHADOW,
        system_prompt_template="You are an expert.",
        version_hash=version_hash,
        source_path=Path(f"/experts/{name}/EXPERT.md"),
    )
    return ScannedExpert(manifest=manifest, directory=Path(f"/experts/{name}"))


_CRUD = "src.experts.registrar"


class TestNewExpert:
    """Test 1: new expert is created when name not in DB."""

    @pytest.mark.asyncio
    async def test_new_expert_created(self) -> None:
        session = AsyncMock()
        scanned = [_make_scanned("new-expert")]

        with (
            patch(f"{_CRUD}.search_experts", return_value=[]) as mock_search,
            patch(f"{_CRUD}.get_expert_versions", return_value=[]),
            patch(
                f"{_CRUD}.create_expert",
                return_value=_make_expert_read("new-expert"),
            ) as mock_create,
        ):
            result = await sync_experts(session, scanned)

        assert result.created == ["new-expert"]
        assert result.updated == []
        assert result.unchanged == []
        mock_create.assert_called_once()
        mock_search.assert_called_once()


class TestChangedExpert:
    """Test 2: changed expert triggers version bump."""

    @pytest.mark.asyncio
    async def test_changed_hash_triggers_update(self) -> None:
        session = AsyncMock()
        existing = _make_expert_read("my-expert")
        version = _make_version_read(existing.id, version_hash="oldhash")
        scanned = [_make_scanned("my-expert", version_hash="newhash")]

        # session.get returns an ExpertRow mock for field updates
        mock_row = MagicMock()
        session.get.return_value = mock_row

        with (
            patch(f"{_CRUD}.search_experts", return_value=[existing]),
            patch(f"{_CRUD}.get_expert_versions", return_value=[version]),
            patch(f"{_CRUD}.update_expert_version", return_value=existing) as mock_update,
        ):
            result = await sync_experts(session, scanned)

        assert result.updated == ["my-expert"]
        assert result.unchanged == []
        mock_update.assert_called_once()


class TestUnchangedExpert:
    """Test 3: unchanged expert is skipped."""

    @pytest.mark.asyncio
    async def test_matching_hash_skipped(self) -> None:
        session = AsyncMock()
        existing = _make_expert_read("same-expert")
        # The stored hash in version definition uses _version_hash key
        # but manifest_to_expert_create puts it under "version_hash" in definition
        # _get_stored_hash reads _version_hash, the comparison is against definition["version_hash"]
        # Let's trace: stored uses _version_hash, ExpertCreate.definition uses "version_hash"
        # The comparison is: stored_hash == expert_create.definition.get("version_hash")
        version = _make_version_read(existing.id, version_hash="samehash")
        scanned = [_make_scanned("same-expert", version_hash="samehash")]

        with (
            patch(f"{_CRUD}.search_experts", return_value=[existing]),
            patch(f"{_CRUD}.get_expert_versions", return_value=[version]),
            patch(f"{_CRUD}.create_expert") as mock_create,
            patch(f"{_CRUD}.update_expert_version") as mock_update,
        ):
            result = await sync_experts(session, scanned)

        assert result.unchanged == ["same-expert"]
        assert result.created == []
        assert result.updated == []
        mock_create.assert_not_called()
        mock_update.assert_not_called()


class TestDeactivateRemoved:
    """Tests 4-5: deactivate_removed behavior."""

    @pytest.mark.asyncio
    async def test_deactivate_removed_true(self) -> None:
        session = AsyncMock()
        existing = _make_expert_read("old-expert")
        version = _make_version_read(existing.id, version_hash="hash")

        with (
            patch(f"{_CRUD}.search_experts", return_value=[existing]),
            patch(f"{_CRUD}.get_expert_versions", return_value=[version]),
            patch(f"{_CRUD}.deprecate_expert", return_value=existing) as mock_deprecate,
        ):
            result = await sync_experts(session, [], deactivate_removed=True)

        assert result.deactivated == ["old-expert"]
        mock_deprecate.assert_called_once_with(session, existing.id)

    @pytest.mark.asyncio
    async def test_deactivate_removed_false(self) -> None:
        session = AsyncMock()
        existing = _make_expert_read("old-expert")
        version = _make_version_read(existing.id, version_hash="hash")

        with (
            patch(f"{_CRUD}.search_experts", return_value=[existing]),
            patch(f"{_CRUD}.get_expert_versions", return_value=[version]),
            patch(f"{_CRUD}.deprecate_expert") as mock_deprecate,
        ):
            result = await sync_experts(session, [], deactivate_removed=False)

        assert result.deactivated == []
        mock_deprecate.assert_not_called()


class TestMixedSync:
    """Test 6: multiple experts sync correctly."""

    @pytest.mark.asyncio
    async def test_mixed_create_update_unchanged(self) -> None:
        session = AsyncMock()
        mock_row = MagicMock()
        session.get.return_value = mock_row

        existing_unchanged = _make_expert_read("unchanged")
        existing_changed = _make_expert_read("changed")
        ver_unchanged = _make_version_read(existing_unchanged.id, version_hash="samehash")
        ver_changed = _make_version_read(existing_changed.id, version_hash="oldhash")

        scanned = [
            _make_scanned("new-one", version_hash="hash1"),
            _make_scanned("unchanged", version_hash="samehash"),
            _make_scanned("changed", version_hash="newhash"),
        ]

        async def mock_get_versions(sess, expert_id):
            if expert_id == existing_unchanged.id:
                return [ver_unchanged]
            if expert_id == existing_changed.id:
                return [ver_changed]
            return []

        with (
            patch(f"{_CRUD}.search_experts", return_value=[existing_unchanged, existing_changed]),
            patch(f"{_CRUD}.get_expert_versions", side_effect=mock_get_versions),
            patch(f"{_CRUD}.create_expert", return_value=_make_expert_read("new-one")),
            patch(f"{_CRUD}.update_expert_version", return_value=existing_changed),
        ):
            result = await sync_experts(session, scanned)

        assert result.created == ["new-one"]
        assert result.unchanged == ["unchanged"]
        assert result.updated == ["changed"]
        assert result.errors == []


class TestLegacyExpert:
    """Test 7: legacy expert without _version_hash treated as changed."""

    @pytest.mark.asyncio
    async def test_legacy_no_hash_triggers_update(self) -> None:
        session = AsyncMock()
        mock_row = MagicMock()
        session.get.return_value = mock_row

        existing = _make_expert_read("legacy")
        # No _version_hash in definition
        version = _make_version_read(existing.id, version_hash=None)
        scanned = [_make_scanned("legacy", version_hash="newhash")]

        with (
            patch(f"{_CRUD}.search_experts", return_value=[existing]),
            patch(f"{_CRUD}.get_expert_versions", return_value=[version]),
            patch(f"{_CRUD}.update_expert_version", return_value=existing) as mock_update,
        ):
            result = await sync_experts(session, scanned)

        assert result.updated == ["legacy"]
        mock_update.assert_called_once()


class TestSourcePathStored:
    """Test 8: _source_path is stored in definition."""

    @pytest.mark.asyncio
    async def test_source_path_in_definition(self) -> None:
        session = AsyncMock()
        scanned = [_make_scanned("path-test")]

        with (
            patch(f"{_CRUD}.search_experts", return_value=[]),
            patch(f"{_CRUD}.get_expert_versions", return_value=[]),
            patch(
                f"{_CRUD}.create_expert",
                return_value=_make_expert_read("path-test"),
            ) as mock_create,
        ):
            await sync_experts(session, scanned)

        # Check the ExpertCreate passed to create_expert
        call_args = mock_create.call_args
        expert_create = call_args[0][1]  # second positional arg (session, data)
        assert "_source_path" in expert_create.definition
        source = expert_create.definition["_source_path"]
        assert "path-test" in source
        assert "EXPERT.md" in source


class TestSyncResultCounts:
    """Test 9: SyncResult counts are correct."""

    def test_sync_result_defaults(self) -> None:
        result = SyncResult()
        assert result.created == []
        assert result.updated == []
        assert result.unchanged == []
        assert result.deactivated == []
        assert result.errors == []


class TestGetStoredHash:
    """Unit tests for _get_stored_hash helper."""

    def test_returns_hash_from_latest_version(self) -> None:
        expert = _make_expert_read("test")
        v1 = _make_version_read(expert.id, version=1, version_hash="v1hash")
        v2 = _make_version_read(expert.id, version=2, version_hash="v2hash")
        versions_by_id = {expert.id: [v1, v2]}

        assert _get_stored_hash(versions_by_id, expert) == "v2hash"

    def test_returns_none_for_no_versions(self) -> None:
        expert = _make_expert_read("test")
        versions_by_id: dict = {}

        assert _get_stored_hash(versions_by_id, expert) is None

    def test_returns_none_for_legacy_no_hash(self) -> None:
        expert = _make_expert_read("test")
        version = _make_version_read(expert.id, version_hash=None)
        versions_by_id = {expert.id: [version]}

        assert _get_stored_hash(versions_by_id, expert) is None
