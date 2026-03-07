"""Tests for context pack signal emission (Story 6.3)."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from src.context.context_manager import (
    ContextPackSignal,
    _emit_pack_signal,
    clear_pack_signals,
    get_pack_signals,
)


class TestContextPackSignal:
    """Tests for ContextPackSignal dataclass."""

    def test_to_dict(self):
        sig = ContextPackSignal(
            signal_type="pack_used_by_task",
            repo="api-gateway",
            taskpacket_id=UUID("aaaaaaaa-0000-0000-0000-000000000001"),
            pack_names=["fastapi-service"],
        )
        d = sig.to_dict()
        assert d["signal_type"] == "pack_used_by_task"
        assert d["repo"] == "api-gateway"
        assert d["pack_names"] == ["fastapi-service"]
        assert "timestamp" in d

    def test_to_dict_missing_signal(self):
        sig = ContextPackSignal(
            signal_type="pack_missing_detected",
            repo="unknown-repo",
            taskpacket_id=UUID("aaaaaaaa-0000-0000-0000-000000000002"),
        )
        d = sig.to_dict()
        assert d["signal_type"] == "pack_missing_detected"
        assert d["pack_names"] == []


class TestEmitPackSignal:
    """Tests for signal emission functions."""

    def setup_method(self):
        clear_pack_signals()

    def teardown_method(self):
        clear_pack_signals()

    def test_emit_pack_used(self):
        tp_id = uuid4()
        sig = _emit_pack_signal(
            signal_type="pack_used_by_task",
            repo="svc-auth",
            taskpacket_id=tp_id,
            pack_names=["fastapi-service"],
        )
        assert sig.signal_type == "pack_used_by_task"
        assert sig.pack_names == ["fastapi-service"]
        assert len(get_pack_signals()) == 1

    def test_emit_pack_missing(self):
        tp_id = uuid4()
        sig = _emit_pack_signal(
            signal_type="pack_missing_detected",
            repo="unknown-repo",
            taskpacket_id=tp_id,
        )
        assert sig.signal_type == "pack_missing_detected"
        assert sig.pack_names == []
        assert len(get_pack_signals()) == 1

    def test_multiple_signals_accumulate(self):
        for i in range(3):
            _emit_pack_signal(
                signal_type="pack_used_by_task",
                repo=f"repo-{i}",
                taskpacket_id=uuid4(),
                pack_names=[f"pack-{i}"],
            )
        assert len(get_pack_signals()) == 3

    def test_clear_signals(self):
        _emit_pack_signal(
            signal_type="pack_used_by_task",
            repo="r",
            taskpacket_id=uuid4(),
            pack_names=["p"],
        )
        clear_pack_signals()
        assert len(get_pack_signals()) == 0


@pytest.mark.asyncio
class TestEnrichTaskpacketSignals:
    """Tests for signal emission during enrich_taskpacket."""

    async def test_emits_pack_used_when_packs_found(self):
        from src.context.service_context_pack import ServiceContextPack

        clear_pack_signals()
        tp_id = uuid4()
        mock_tp = MagicMock()
        mock_tp.repo = "svc-auth"
        mock_tp.correlation_id = uuid4()

        mock_pack = ServiceContextPack(
            name="fastapi-service", version="1.0", repo_patterns=["svc-*"]
        )

        with (
            patch("src.context.context_manager.get_by_id", new_callable=AsyncMock, return_value=mock_tp),
            patch("src.context.context_manager.get_context_packs", return_value=[mock_pack]),
            patch("src.context.context_manager.analyze_scope") as mock_scope,
            patch("src.context.context_manager.flag_risks", return_value={}),
            patch("src.context.context_manager.compute_complexity_index") as mock_ci,
            patch("src.context.context_manager.update_enrichment", new_callable=AsyncMock, return_value=mock_tp),
        ):
            mock_scope.return_value = MagicMock(to_dict=lambda: {})
            mock_ci.return_value = MagicMock(score=5.0, band="medium", to_dict=lambda: {})

            from src.context.context_manager import enrich_taskpacket
            await enrich_taskpacket(AsyncMock(), tp_id, "title", "body")

        signals = get_pack_signals()
        used = [s for s in signals if s.signal_type == "pack_used_by_task"]
        assert len(used) == 1
        assert used[0].pack_names == ["fastapi-service"]
        assert used[0].repo == "svc-auth"
        clear_pack_signals()

    async def test_emits_pack_missing_when_no_packs(self):
        clear_pack_signals()
        tp_id = uuid4()
        mock_tp = MagicMock()
        mock_tp.repo = "unknown-repo"
        mock_tp.correlation_id = uuid4()

        with (
            patch("src.context.context_manager.get_by_id", new_callable=AsyncMock, return_value=mock_tp),
            patch("src.context.context_manager.get_context_packs", return_value=[]),
            patch("src.context.context_manager.analyze_scope") as mock_scope,
            patch("src.context.context_manager.flag_risks", return_value={}),
            patch("src.context.context_manager.compute_complexity_index") as mock_ci,
            patch("src.context.context_manager.update_enrichment", new_callable=AsyncMock, return_value=mock_tp),
        ):
            mock_scope.return_value = MagicMock(to_dict=lambda: {})
            mock_ci.return_value = MagicMock(score=5.0, band="medium", to_dict=lambda: {})

            from src.context.context_manager import enrich_taskpacket
            await enrich_taskpacket(AsyncMock(), tp_id, "title", "body")

        signals = get_pack_signals()
        missing = [s for s in signals if s.signal_type == "pack_missing_detected"]
        assert len(missing) == 1
        assert missing[0].repo == "unknown-repo"
        clear_pack_signals()
