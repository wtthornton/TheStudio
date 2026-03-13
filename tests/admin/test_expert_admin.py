"""Tests for expert admin endpoints (Story 26.5)."""

from pathlib import Path

from src.admin.platform_router import (
    ExpertReloadResponse,
    ExpertSummary,
)
from src.experts.config import get_experts_base_path
from src.experts.registrar import SyncResult
from src.experts.scanner import ScanError


class TestGetExpertsBasePath:
    """Tests for the config utility."""

    def test_default_path(self) -> None:
        path = get_experts_base_path()
        assert path.name == "experts"
        assert path.is_absolute()

    def test_env_override(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setenv("EXPERTS_BASE_PATH", str(tmp_path))
        path = get_experts_base_path()
        assert path == tmp_path.resolve()


class TestExpertReloadResponseModel:
    """Test response model structure."""

    def test_reload_response_fields(self) -> None:
        resp = ExpertReloadResponse(
            created=["a"],
            updated=["b"],
            unchanged=["c"],
            deactivated=[],
            errors=[],
            scan_errors=[{"directory": "/x", "error": "bad"}],
        )
        assert resp.created == ["a"]
        assert resp.scan_errors[0]["error"] == "bad"


class TestExpertSummaryModel:
    """Test summary model structure."""

    def test_summary_with_metadata(self) -> None:
        s = ExpertSummary(
            id="uuid",
            name="test",
            expert_class="technical",
            capability_tags=["tag"],
            trust_tier="shadow",
            lifecycle_state="active",
            current_version=1,
            source_path="/experts/test/EXPERT.md",
            version_hash="abc123",
            updated_at="2026-03-13T00:00:00+00:00",
        )
        assert s.source_path == "/experts/test/EXPERT.md"
        assert s.version_hash == "abc123"

    def test_summary_without_metadata(self) -> None:
        s = ExpertSummary(
            id="uuid",
            name="legacy",
            expert_class="technical",
            capability_tags=["tag"],
            trust_tier="shadow",
            lifecycle_state="active",
            current_version=1,
            updated_at="2026-03-13T00:00:00+00:00",
        )
        assert s.source_path is None
        assert s.version_hash is None


class TestSyncResultToResponse:
    """Test SyncResult maps to ExpertReloadResponse."""

    def test_sync_result_maps(self) -> None:
        sync = SyncResult(
            created=["new"],
            updated=["changed"],
            unchanged=["same"],
            deactivated=["old"],
            errors=["failed: reason"],
        )
        resp = ExpertReloadResponse(
            created=sync.created,
            updated=sync.updated,
            unchanged=sync.unchanged,
            deactivated=sync.deactivated,
            errors=sync.errors,
            scan_errors=[],
        )
        assert resp.created == ["new"]
        assert resp.updated == ["changed"]
        assert resp.unchanged == ["same"]
        assert resp.deactivated == ["old"]
        assert resp.errors == ["failed: reason"]


class TestScanErrorInResponse:
    """Test scan errors are included in reload response."""

    def test_scan_errors_serialized(self) -> None:
        scan_errors = [
            ScanError(directory=Path("/experts/bad"), error="invalid YAML"),
        ]
        serialized = [
            {"directory": str(e.directory), "error": e.error}
            for e in scan_errors
        ]
        resp = ExpertReloadResponse(
            created=[],
            updated=[],
            unchanged=[],
            deactivated=[],
            errors=[],
            scan_errors=serialized,
        )
        assert len(resp.scan_errors) == 1
        assert "invalid YAML" in resp.scan_errors[0]["error"]
