"""Unit tests for preflight_activity (Epic 28 Story 28.2).

Tests:
- Activity wiring with AgentRunner (AC 5)
- Input/output dataclass fields
- Parsed output mapping
- Raw JSON fallback mapping
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.workflow.activities import (
    PreflightActivityOutput,
    PreflightInput,
    preflight_activity,
)


class TestPreflightInputOutput:
    """AC 5: PreflightInput and PreflightActivityOutput dataclass fields."""

    def test_input_defaults(self) -> None:
        inp = PreflightInput(taskpacket_id="tp-001")
        assert inp.plan_steps == []
        assert inp.acceptance_criteria == []
        assert inp.constraints == []

    def test_input_with_data(self) -> None:
        inp = PreflightInput(
            taskpacket_id="tp-001",
            plan_steps=["Step 1", "Step 2"],
            acceptance_criteria=["AC 1"],
            constraints=["No global state"],
        )
        assert len(inp.plan_steps) == 2
        assert len(inp.constraints) == 1

    def test_output_defaults(self) -> None:
        out = PreflightActivityOutput()
        assert out.approved is True
        assert out.uncovered_criteria == []
        assert out.constraint_violations == []
        assert out.vague_steps == []
        assert out.summary == ""


class TestPreflightActivityIntegration:
    """AC 5: preflight_activity uses AgentRunner."""

    @pytest.mark.asyncio
    async def test_parsed_output_mapping(self) -> None:
        """When AgentRunner returns parsed_output, map it to PreflightActivityOutput."""
        mock_parsed = MagicMock()
        mock_parsed.approved = True
        mock_parsed.uncovered_criteria = []
        mock_parsed.constraint_violations = []
        mock_parsed.vague_steps = []
        mock_parsed.summary = "All clear"

        mock_result = MagicMock()
        mock_result.parsed_output = mock_parsed

        mock_runner_instance = MagicMock()
        mock_runner_instance.run = AsyncMock(return_value=mock_result)

        with patch(
            "src.agent.framework.AgentRunner",
            return_value=mock_runner_instance,
        ):
            result = await preflight_activity(
                PreflightInput(
                    taskpacket_id="00000000-0000-0000-0000-000000000001",
                    plan_steps=["Do the thing"],
                    acceptance_criteria=["Thing is done"],
                )
            )

        assert result.approved is True
        assert result.summary == "All clear"

    @pytest.mark.asyncio
    async def test_raw_json_fallback(self) -> None:
        """When parsed_output is None, parse raw JSON."""
        raw_data = {
            "approved": False,
            "uncovered_criteria": ["Missing AC"],
            "constraint_violations": [],
            "vague_steps": ["Figure out stuff"],
            "summary": "Issues found",
        }

        mock_result = MagicMock()
        mock_result.parsed_output = None
        mock_result.raw_output = json.dumps(raw_data)

        mock_runner_instance = MagicMock()
        mock_runner_instance.run = AsyncMock(return_value=mock_result)

        with patch(
            "src.agent.framework.AgentRunner",
            return_value=mock_runner_instance,
        ):
            result = await preflight_activity(
                PreflightInput(
                    taskpacket_id="00000000-0000-0000-0000-000000000001",
                    plan_steps=["Figure out stuff"],
                    acceptance_criteria=["Missing AC"],
                )
            )

        assert result.approved is False
        assert result.uncovered_criteria == ["Missing AC"]
        assert result.vague_steps == ["Figure out stuff"]

    @pytest.mark.asyncio
    async def test_empty_raw_output_defaults_to_approved(self) -> None:
        """When raw_output is empty, default to approved=True."""
        mock_result = MagicMock()
        mock_result.parsed_output = None
        mock_result.raw_output = None

        mock_runner_instance = MagicMock()
        mock_runner_instance.run = AsyncMock(return_value=mock_result)

        with patch(
            "src.agent.framework.AgentRunner",
            return_value=mock_runner_instance,
        ):
            result = await preflight_activity(
                PreflightInput(
                    taskpacket_id="00000000-0000-0000-0000-000000000001",
                )
            )

        assert result.approved is True
