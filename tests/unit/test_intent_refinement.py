"""Unit tests for Intent Refinement Loop (Story 1.7).

Architecture reference: thestudioarc/11-intent-layer.md — Refinement Loop
"""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from src.intent.intent_spec import IntentSpecRead
from src.intent.refinement import (
    MAX_INTENT_VERSIONS,
    RefinementCapExceededError,
    RefinementTrigger,
    refine_intent,
)
from src.models.taskpacket import TaskPacketRead, TaskPacketStatus


def _make_taskpacket(
    taskpacket_id=None, correlation_id=None, intent_version=1,
) -> TaskPacketRead:
    from datetime import UTC, datetime
    return TaskPacketRead(
        id=taskpacket_id or uuid4(),
        repo="owner/repo",
        issue_id=1,
        delivery_id="d-1",
        correlation_id=correlation_id or uuid4(),
        status=TaskPacketStatus.INTENT_BUILT,
        intent_spec_id=uuid4(),
        intent_version=intent_version,
        loopback_count=0,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def _make_intent(taskpacket_id=None, version=1, source="auto") -> IntentSpecRead:
    from datetime import UTC, datetime
    return IntentSpecRead(
        id=uuid4(),
        taskpacket_id=taskpacket_id or uuid4(),
        version=version,
        goal="Fix the authentication bug",
        constraints=["Must include tests"],
        acceptance_criteria=["Auth works after fix"],
        non_goals=["No UI changes"],
        source=source,
        created_at=datetime.now(UTC),
    )


class TestRefineFromQATrigger:
    """Refinement from QA Agent trigger."""

    @pytest.mark.asyncio
    async def test_refine_from_qa_produces_new_version(self) -> None:
        tp_id = uuid4()
        tp = _make_taskpacket(taskpacket_id=tp_id, intent_version=1)
        current_intent = _make_intent(taskpacket_id=tp_id, version=1)
        new_intent = _make_intent(taskpacket_id=tp_id, version=2)

        trigger = RefinementTrigger(
            source="qa_agent",
            questions=["Clarify acceptance criterion: Auth works after fix"],
        )

        session = AsyncMock()
        with (
            patch("src.intent.refinement.get_by_id", return_value=tp),
            patch("src.intent.refinement.get_latest_for_taskpacket", return_value=current_intent),
            patch("src.intent.refinement.create_intent", return_value=new_intent) as mock_create,
            patch("src.intent.refinement.update_intent_version", return_value=tp),
        ):
            result = await refine_intent(session, tp_id, trigger)

        assert result.version == 2
        # Verify the create call used version 2
        call_args = mock_create.call_args[0]
        assert call_args[1].version == 2
        assert any("Refinement v2" in c for c in call_args[1].constraints)


class TestRefineFromAssemblerTrigger:
    """Refinement from Assembler trigger."""

    @pytest.mark.asyncio
    async def test_refine_from_assembler_produces_new_version(self) -> None:
        tp_id = uuid4()
        tp = _make_taskpacket(taskpacket_id=tp_id, intent_version=1)
        current_intent = _make_intent(taskpacket_id=tp_id, version=1)
        new_intent = _make_intent(taskpacket_id=tp_id, version=2)

        trigger = RefinementTrigger(
            source="assembler",
            questions=["Conflict between experts: security vs performance"],
            triggering_conflict="security vs performance tradeoff",
        )

        session = AsyncMock()
        with (
            patch("src.intent.refinement.get_by_id", return_value=tp),
            patch("src.intent.refinement.get_latest_for_taskpacket", return_value=current_intent),
            patch("src.intent.refinement.create_intent", return_value=new_intent) as mock_create,
            patch("src.intent.refinement.update_intent_version", return_value=tp),
        ):
            result = await refine_intent(session, tp_id, trigger)

        assert result.version == 2
        call_args = mock_create.call_args[0]
        assert call_args[1].version == 2


class TestPriorVersionPreserved:
    """Prior intent versions are preserved after refinement."""

    @pytest.mark.asyncio
    async def test_original_version_not_modified(self) -> None:
        tp_id = uuid4()
        tp = _make_taskpacket(taskpacket_id=tp_id, intent_version=1)
        current_intent = _make_intent(taskpacket_id=tp_id, version=1)
        new_intent = _make_intent(taskpacket_id=tp_id, version=2)

        trigger = RefinementTrigger(
            source="qa_agent",
            questions=["Clarify criterion"],
        )

        session = AsyncMock()
        with (
            patch("src.intent.refinement.get_by_id", return_value=tp),
            patch("src.intent.refinement.get_latest_for_taskpacket", return_value=current_intent),
            patch("src.intent.refinement.create_intent", return_value=new_intent) as mock_create,
            patch("src.intent.refinement.update_intent_version", return_value=tp),
        ):
            result = await refine_intent(session, tp_id, trigger)

        # create_intent is called (new row), not update — prior version untouched
        mock_create.assert_called_once()
        assert result.version == 2
        # The original intent (version 1) was read but never modified


class TestRefinementCap:
    """Version cap at 10 per workflow (configurable via settings)."""

    @pytest.mark.asyncio
    async def test_cap_exceeded_raises(self) -> None:
        tp_id = uuid4()
        tp = _make_taskpacket(taskpacket_id=tp_id, intent_version=10)
        current_intent = _make_intent(taskpacket_id=tp_id, version=10)

        trigger = RefinementTrigger(
            source="qa_agent",
            questions=["Another question"],
        )

        session = AsyncMock()
        with (
            patch("src.intent.refinement.get_by_id", return_value=tp),
            patch("src.intent.refinement.get_latest_for_taskpacket", return_value=current_intent),
        ):
            with pytest.raises(RefinementCapExceededError) as exc_info:
                await refine_intent(session, tp_id, trigger)

        assert exc_info.value.current_version == 10
        assert exc_info.value.taskpacket_id == tp_id

    def test_max_versions_constant(self) -> None:
        assert MAX_INTENT_VERSIONS == 10

    @pytest.mark.asyncio
    async def test_five_versions_no_error(self) -> None:
        """Developer editing creates 5+ versions without hitting cap."""
        tp_id = uuid4()
        tp = _make_taskpacket(taskpacket_id=tp_id, intent_version=5)
        current_intent = _make_intent(taskpacket_id=tp_id, version=5)
        new_intent = _make_intent(taskpacket_id=tp_id, version=6)

        trigger = RefinementTrigger(
            source="developer",
            questions=["Clarify scope"],
        )

        session = AsyncMock()
        with (
            patch("src.intent.refinement.get_by_id", return_value=tp),
            patch("src.intent.refinement.get_latest_for_taskpacket", return_value=current_intent),
            patch("src.intent.refinement.create_intent", return_value=new_intent),
            patch("src.intent.refinement.update_intent_version", return_value=tp),
        ):
            result = await refine_intent(session, tp_id, trigger)

        assert result.version == 6


class TestRefinementProvenance:
    """Refinement source tracked in provenance."""

    @pytest.mark.asyncio
    async def test_refinement_constraints_include_source(self) -> None:
        tp_id = uuid4()
        tp = _make_taskpacket(taskpacket_id=tp_id, intent_version=1)
        current_intent = _make_intent(taskpacket_id=tp_id, version=1)
        new_intent = _make_intent(taskpacket_id=tp_id, version=2)

        trigger = RefinementTrigger(
            source="qa_agent",
            questions=["What does 'works' mean for auth?"],
            triggering_defects=["Intent gap: vague criterion"],
        )

        session = AsyncMock()
        with (
            patch("src.intent.refinement.get_by_id", return_value=tp),
            patch("src.intent.refinement.get_latest_for_taskpacket", return_value=current_intent),
            patch("src.intent.refinement.create_intent", return_value=new_intent) as mock_create,
            patch("src.intent.refinement.update_intent_version", return_value=tp),
        ):
            await refine_intent(session, tp_id, trigger)

        # The new intent's constraints include the refinement question
        created_data = mock_create.call_args[0][1]
        refinement_constraints = [
            c for c in created_data.constraints if "[Refinement v2]" in c
        ]
        assert len(refinement_constraints) == 1
        assert "What does 'works' mean for auth?" in refinement_constraints[0]


class TestTaskPacketUpdated:
    """TaskPacket intent_version updated after refinement."""

    @pytest.mark.asyncio
    async def test_taskpacket_version_updated(self) -> None:
        tp_id = uuid4()
        tp = _make_taskpacket(taskpacket_id=tp_id, intent_version=1)
        current_intent = _make_intent(taskpacket_id=tp_id, version=1)
        new_intent = _make_intent(taskpacket_id=tp_id, version=2)

        trigger = RefinementTrigger(
            source="assembler",
            questions=["Resolve conflict"],
        )

        session = AsyncMock()
        with (
            patch("src.intent.refinement.get_by_id", return_value=tp),
            patch("src.intent.refinement.get_latest_for_taskpacket", return_value=current_intent),
            patch("src.intent.refinement.create_intent", return_value=new_intent),
            patch("src.intent.refinement.update_intent_version", return_value=tp) as mock_update,
        ):
            await refine_intent(session, tp_id, trigger)

        mock_update.assert_called_once_with(
            session, tp_id, new_intent.id, new_intent.version,
        )
