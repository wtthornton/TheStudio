"""Tests for IntentSpec source column and schema changes (Story 36.7)."""

from datetime import UTC, datetime
from uuid import uuid4

from src.intent.intent_spec import IntentSpecCreate, IntentSpecRead, IntentSpecRow


class TestIntentSpecRowSource:
    """IntentSpecRow has a source column with default 'auto'."""

    def test_source_column_exists(self) -> None:
        assert hasattr(IntentSpecRow, "source")

    def test_source_column_has_server_default(self) -> None:
        """Source column has server_default='auto' for backfill compatibility."""
        col = IntentSpecRow.__table__.columns["source"]
        assert col.server_default.arg == "auto"

    def test_source_column_explicit(self) -> None:
        row = IntentSpecRow(
            taskpacket_id=uuid4(),
            version=1,
            goal="Test goal",
            constraints=[],
            acceptance_criteria=[],
            non_goals=[],
            source="developer",
        )
        assert row.source == "developer"


class TestIntentSpecCreate:
    """IntentSpecCreate accepts source field."""

    def test_default_source_is_auto(self) -> None:
        create = IntentSpecCreate(
            taskpacket_id=uuid4(),
            goal="Test goal",
        )
        assert create.source == "auto"

    def test_explicit_source_developer(self) -> None:
        create = IntentSpecCreate(
            taskpacket_id=uuid4(),
            goal="Test goal",
            source="developer",
        )
        assert create.source == "developer"

    def test_explicit_source_refinement(self) -> None:
        create = IntentSpecCreate(
            taskpacket_id=uuid4(),
            goal="Test goal",
            source="refinement",
        )
        assert create.source == "refinement"


class TestIntentSpecRead:
    """IntentSpecRead includes source field."""

    def test_source_in_read_model(self) -> None:
        read = IntentSpecRead(
            id=uuid4(),
            taskpacket_id=uuid4(),
            version=1,
            goal="Test goal",
            constraints=[],
            acceptance_criteria=[],
            non_goals=[],
            source="auto",
            created_at=datetime.now(UTC),
        )
        assert read.source == "auto"

    def test_developer_source_in_read(self) -> None:
        read = IntentSpecRead(
            id=uuid4(),
            taskpacket_id=uuid4(),
            version=2,
            goal="Edited goal",
            constraints=["New constraint"],
            acceptance_criteria=["New AC"],
            non_goals=[],
            source="developer",
            created_at=datetime.now(UTC),
        )
        assert read.source == "developer"
        assert read.version == 2

    def test_from_attributes_includes_source(self) -> None:
        """model_config from_attributes=True should pick up source."""
        row = IntentSpecRow(
            id=uuid4(),
            taskpacket_id=uuid4(),
            version=1,
            goal="Test",
            constraints=[],
            acceptance_criteria=[],
            non_goals=[],
            source="refinement",
            created_at=datetime.now(UTC),
        )
        read = IntentSpecRead.model_validate(row)
        assert read.source == "refinement"
