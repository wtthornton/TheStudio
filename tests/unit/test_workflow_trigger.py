"""Unit tests for workflow_trigger module (Temporal client singleton + start_workflow)."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


class TestGetTemporalClient:
    """Tests for get_temporal_client singleton."""

    async def test_creates_client_on_first_call(self) -> None:
        import src.ingress.workflow_trigger as mod

        mod._client = None
        mock_client = AsyncMock()

        with patch.object(mod, "_client", None), patch(
            "src.ingress.workflow_trigger.Client"
        ) as mock_cls:
            mock_cls.connect = AsyncMock(return_value=mock_client)
            result = await mod.get_temporal_client()

        assert result is mock_client
        mock_cls.connect.assert_awaited_once()

    async def test_returns_cached_client_on_second_call(self) -> None:
        import src.ingress.workflow_trigger as mod

        cached = AsyncMock()
        original = mod._client
        try:
            mod._client = cached
            result = await mod.get_temporal_client()
            assert result is cached
        finally:
            mod._client = original

    async def test_connect_uses_settings(self) -> None:
        import src.ingress.workflow_trigger as mod

        original = mod._client
        try:
            mod._client = None
            mock_client = AsyncMock()

            with patch(
                "src.ingress.workflow_trigger.Client"
            ) as mock_cls, patch(
                "src.ingress.workflow_trigger.settings"
            ) as mock_settings:
                mock_settings.temporal_host = "temporal.example.com:7233"
                mock_settings.temporal_namespace = "prod-ns"
                mock_cls.connect = AsyncMock(return_value=mock_client)

                await mod.get_temporal_client()

                mock_cls.connect.assert_awaited_once_with(
                    "temporal.example.com:7233",
                    namespace="prod-ns",
                )
        finally:
            mod._client = original


class TestStartWorkflow:
    """Tests for start_workflow function."""

    async def test_start_workflow_returns_run_id(self) -> None:
        from src.ingress.workflow_trigger import start_workflow

        tp_id = uuid4()
        corr_id = uuid4()

        mock_handle = MagicMock()
        mock_handle.result_run_id = "run-abc-123"

        mock_client = AsyncMock()
        mock_client.start_workflow = AsyncMock(return_value=mock_handle)

        with patch(
            "src.ingress.workflow_trigger.get_temporal_client",
            new_callable=AsyncMock,
            return_value=mock_client,
        ):
            result = await start_workflow(tp_id, corr_id)

        assert result == "run-abc-123"

    async def test_start_workflow_passes_correct_args(self) -> None:
        from src.ingress.workflow_trigger import start_workflow

        tp_id = uuid4()
        corr_id = uuid4()

        mock_handle = MagicMock()
        mock_handle.result_run_id = "run-xyz"

        mock_client = AsyncMock()
        mock_client.start_workflow = AsyncMock(return_value=mock_handle)

        with patch(
            "src.ingress.workflow_trigger.get_temporal_client",
            new_callable=AsyncMock,
            return_value=mock_client,
        ), patch(
            "src.ingress.workflow_trigger.settings"
        ) as mock_settings:
            mock_settings.temporal_task_queue = "my-queue"
            await start_workflow(tp_id, corr_id)

        mock_client.start_workflow.assert_awaited_once_with(
            "TheStudioPipelineWorkflow",
            arg={
                "taskpacket_id": str(tp_id),
                "correlation_id": str(corr_id),
            },
            id=str(tp_id),
            task_queue="my-queue",
        )

    async def test_start_workflow_uses_taskpacket_id_as_workflow_id(self) -> None:
        """Temporal idempotency: workflow ID == taskpacket_id."""
        from src.ingress.workflow_trigger import start_workflow

        tp_id = uuid4()
        corr_id = uuid4()

        mock_handle = MagicMock()
        mock_handle.result_run_id = "r1"

        mock_client = AsyncMock()
        mock_client.start_workflow = AsyncMock(return_value=mock_handle)

        with patch(
            "src.ingress.workflow_trigger.get_temporal_client",
            new_callable=AsyncMock,
            return_value=mock_client,
        ):
            await start_workflow(tp_id, corr_id)

        call_kwargs = mock_client.start_workflow.call_args
        assert call_kwargs.kwargs["id"] == str(tp_id)

    async def test_start_workflow_returns_empty_string_when_no_run_id(self) -> None:
        """When result_run_id is None, return empty string."""
        from src.ingress.workflow_trigger import start_workflow

        mock_handle = MagicMock()
        mock_handle.result_run_id = None

        mock_client = AsyncMock()
        mock_client.start_workflow = AsyncMock(return_value=mock_handle)

        with patch(
            "src.ingress.workflow_trigger.get_temporal_client",
            new_callable=AsyncMock,
            return_value=mock_client,
        ):
            result = await start_workflow(uuid4(), uuid4())

        assert result == ""

    async def test_start_workflow_propagates_temporal_error(self) -> None:
        """If Temporal raises, the exception should propagate."""
        from src.ingress.workflow_trigger import start_workflow

        mock_client = AsyncMock()
        mock_client.start_workflow = AsyncMock(
            side_effect=RuntimeError("Temporal unavailable")
        )

        with patch(
            "src.ingress.workflow_trigger.get_temporal_client",
            new_callable=AsyncMock,
            return_value=mock_client,
        ), pytest.raises(RuntimeError, match="Temporal unavailable"):
            await start_workflow(uuid4(), uuid4())
