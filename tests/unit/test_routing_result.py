"""Unit tests for routing result Pydantic schemas (Story 36.14d).

Tests ExpertSelectionRead and RoutingResultRead round-trip serialization.
"""

from uuid import uuid4

import pytest

from src.experts.expert import ExpertClass
from src.routing.routing_result import ExpertSelectionRead, RoutingResultRead


def _make_expert_selection(
    *,
    expert_id=None,
    expert_class=ExpertClass.TECHNICAL,
    pattern="parallel",
    reputation_weight=0.8,
    reputation_confidence=0.9,
    selection_score=1.2,
    selection_reason="High trust tier with strong track record",
) -> dict:
    return {
        "expert_id": expert_id or uuid4(),
        "expert_class": expert_class,
        "pattern": pattern,
        "reputation_weight": reputation_weight,
        "reputation_confidence": reputation_confidence,
        "selection_score": selection_score,
        "selection_reason": selection_reason,
    }


class TestExpertSelectionRead:
    """Round-trip tests for ExpertSelectionRead schema."""

    def test_round_trip_all_fields(self) -> None:
        data = _make_expert_selection()
        obj = ExpertSelectionRead(**data)
        assert obj.expert_id == data["expert_id"]
        assert obj.expert_class == ExpertClass.TECHNICAL
        assert obj.pattern == "parallel"
        assert obj.reputation_weight == 0.8
        assert obj.reputation_confidence == 0.9
        assert obj.selection_score == 1.2
        assert obj.selection_reason == "High trust tier with strong track record"

    def test_all_expert_classes(self) -> None:
        for cls in ExpertClass:
            data = _make_expert_selection(expert_class=cls)
            obj = ExpertSelectionRead(**data)
            assert obj.expert_class == cls

    def test_staged_pattern(self) -> None:
        data = _make_expert_selection(pattern="staged")
        obj = ExpertSelectionRead(**data)
        assert obj.pattern == "staged"

    def test_serializes_to_dict(self) -> None:
        data = _make_expert_selection()
        obj = ExpertSelectionRead(**data)
        d = obj.model_dump()
        assert d["expert_class"] == data["expert_class"]
        assert d["reputation_weight"] == 0.8
        assert "expert_id" in d

    def test_zero_scores(self) -> None:
        data = _make_expert_selection(
            reputation_weight=0.0,
            reputation_confidence=0.0,
            selection_score=0.0,
        )
        obj = ExpertSelectionRead(**data)
        assert obj.reputation_weight == 0.0
        assert obj.selection_score == 0.0

    def test_max_scores(self) -> None:
        data = _make_expert_selection(
            reputation_weight=1.0,
            reputation_confidence=1.0,
            selection_score=2.0,
        )
        obj = ExpertSelectionRead(**data)
        assert obj.reputation_weight == 1.0
        assert obj.selection_score == 2.0


class TestRoutingResultRead:
    """Round-trip tests for RoutingResultRead schema."""

    def test_round_trip_with_selections(self) -> None:
        task_id = uuid4()
        sel = ExpertSelectionRead(**_make_expert_selection())
        obj = RoutingResultRead(
            taskpacket_id=task_id,
            selections=[sel],
            rationale="Best coverage for this issue type",
            budget_remaining=1000,
        )
        assert obj.taskpacket_id == task_id
        assert len(obj.selections) == 1
        assert obj.rationale == "Best coverage for this issue type"
        assert obj.budget_remaining == 1000

    def test_empty_selections(self) -> None:
        obj = RoutingResultRead(
            taskpacket_id=uuid4(),
            selections=[],
            rationale="No experts required",
            budget_remaining=0,
        )
        assert obj.selections == []
        assert obj.budget_remaining == 0

    def test_multiple_selections(self) -> None:
        sels = [
            ExpertSelectionRead(**_make_expert_selection(expert_class=ExpertClass.TECHNICAL)),
            ExpertSelectionRead(**_make_expert_selection(expert_class=ExpertClass.SECURITY)),
            ExpertSelectionRead(**_make_expert_selection(expert_class=ExpertClass.QA_VALIDATION)),
        ]
        obj = RoutingResultRead(
            taskpacket_id=uuid4(),
            selections=sels,
            rationale="Multi-expert coverage",
            budget_remaining=500,
        )
        assert len(obj.selections) == 3
        classes = {s.expert_class for s in obj.selections}
        assert ExpertClass.TECHNICAL in classes
        assert ExpertClass.SECURITY in classes

    def test_serializes_to_dict(self) -> None:
        task_id = uuid4()
        sel = ExpertSelectionRead(**_make_expert_selection())
        obj = RoutingResultRead(
            taskpacket_id=task_id,
            selections=[sel],
            rationale="Test",
            budget_remaining=200,
        )
        d = obj.model_dump()
        assert d["taskpacket_id"] == task_id
        assert len(d["selections"]) == 1
        assert d["rationale"] == "Test"
        assert d["budget_remaining"] == 200
