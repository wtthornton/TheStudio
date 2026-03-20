"""Unit tests for QA signal emission (src/qa/signals.py).

Covers: get_jetstream, _build_qa_payload, emit_qa_passed, emit_qa_defect, emit_qa_rework.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from src.qa.defect import DefectCategory, QADefect, Severity
from src.qa.signals import (
    STREAM_NAME,
    SUBJECT_PREFIX,
    _build_qa_payload,
    emit_qa_defect,
    emit_qa_passed,
    emit_qa_rework,
    get_jetstream,
)

TP_ID = UUID("aaaaaaaa-1111-2222-3333-444444444444")
CORR_ID = UUID("bbbbbbbb-5555-6666-7777-888888888888")


def _make_defect(**overrides):
    defaults = {
        "category": DefectCategory.IMPLEMENTATION_BUG,
        "severity": Severity.S2_MEDIUM,
        "description": "Widget fails on edge case",
        "acceptance_criterion": "Widget must handle edge cases",
    }
    defaults.update(overrides)
    return QADefect(**defaults)


# ---------------------------------------------------------------------------
# _build_qa_payload
# ---------------------------------------------------------------------------


class TestBuildQAPayload:
    """Tests for the _build_qa_payload helper."""

    def test_basic_payload_structure(self):
        raw = _build_qa_payload("qa_passed", TP_ID, CORR_ID)
        payload = json.loads(raw)

        assert payload["event"] == "qa_passed"
        assert payload["taskpacket_id"] == str(TP_ID)
        assert payload["correlation_id"] == str(CORR_ID)
        assert "timestamp" in payload
        assert "defects" not in payload

    def test_payload_is_bytes(self):
        raw = _build_qa_payload("qa_passed", TP_ID, CORR_ID)
        assert isinstance(raw, bytes)

    def test_payload_with_defects(self):
        defects = [
            _make_defect(),
            _make_defect(
                category=DefectCategory.SECURITY,
                severity=Severity.S0_CRITICAL,
                description="SQL injection",
                acceptance_criterion="No SQL injection",
            ),
        ]
        raw = _build_qa_payload("qa_defect", TP_ID, CORR_ID, defects=defects)
        payload = json.loads(raw)

        assert payload["event"] == "qa_defect"
        assert len(payload["defects"]) == 2
        assert payload["defects"][0]["category"] == "implementation_bug"
        assert payload["defects"][0]["severity"] == "S2"
        assert payload["defects"][0]["description"] == "Widget fails on edge case"
        assert payload["defects"][1]["category"] == "security"
        assert payload["defects"][1]["severity"] == "S0"

    def test_payload_with_empty_defects_list(self):
        """An empty list is falsy, so defects key should be absent."""
        raw = _build_qa_payload("qa_passed", TP_ID, CORR_ID, defects=[])
        payload = json.loads(raw)
        assert "defects" not in payload

    def test_payload_with_none_defects(self):
        raw = _build_qa_payload("qa_passed", TP_ID, CORR_ID, defects=None)
        payload = json.loads(raw)
        assert "defects" not in payload

    def test_defect_acceptance_criterion_preserved(self):
        defect = _make_defect(acceptance_criterion="Must do X")
        raw = _build_qa_payload("qa_defect", TP_ID, CORR_ID, defects=[defect])
        payload = json.loads(raw)
        assert payload["defects"][0]["acceptance_criterion"] == "Must do X"

    def test_timestamp_is_iso_format(self):
        raw = _build_qa_payload("qa_passed", TP_ID, CORR_ID)
        payload = json.loads(raw)
        # ISO format contains 'T' separator
        assert "T" in payload["timestamp"]


# ---------------------------------------------------------------------------
# get_jetstream
# ---------------------------------------------------------------------------


class TestGetJetstream:
    """Tests for get_jetstream() with mocked NATS."""

    async def test_creates_jetstream_context(self):
        import src.qa.signals as mod

        original_js = mod._js
        mod._js = None
        try:
            mock_js = AsyncMock()
            mock_js.find_stream_name_by_subject = AsyncMock(return_value=STREAM_NAME)
            mock_nc = AsyncMock()
            mock_nc.jetstream = MagicMock(return_value=mock_js)

            with patch("src.qa.signals.nats.connect", AsyncMock(return_value=mock_nc)):
                js = await get_jetstream()

            assert js is mock_js
            mock_nc.jetstream.assert_called_once()
            mock_js.find_stream_name_by_subject.assert_awaited_once_with(
                f"{SUBJECT_PREFIX}.*"
            )
        finally:
            mod._js = original_js

    async def test_creates_stream_when_not_found(self):
        import src.qa.signals as mod

        original_js = mod._js
        mod._js = None
        try:
            mock_js = AsyncMock()
            mock_js.find_stream_name_by_subject = AsyncMock(
                side_effect=Exception("stream not found")
            )
            mock_js.add_stream = AsyncMock()
            mock_nc = AsyncMock()
            mock_nc.jetstream = MagicMock(return_value=mock_js)

            with patch("src.qa.signals.nats.connect", AsyncMock(return_value=mock_nc)):
                js = await get_jetstream()

            assert js is mock_js
            mock_js.add_stream.assert_awaited_once_with(
                name=STREAM_NAME,
                subjects=[f"{SUBJECT_PREFIX}.*"],
            )
        finally:
            mod._js = original_js

    async def test_reuses_existing_context(self):
        import src.qa.signals as mod

        original_js = mod._js
        mock_js = AsyncMock()
        mod._js = mock_js
        try:
            with patch("src.qa.signals.nats.connect", AsyncMock()) as mock_connect:
                js = await get_jetstream()

            assert js is mock_js
            mock_connect.assert_not_awaited()
        finally:
            mod._js = original_js


# ---------------------------------------------------------------------------
# emit_qa_passed / emit_qa_defect / emit_qa_rework
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _mock_pipeline_gate():
    """Prevent pipeline gate calls from interfering with QA signal tests."""
    with patch("src.qa.signals.get_pipeline_jetstream", AsyncMock(return_value=AsyncMock())):
        yield


class TestEmitQAPassed:
    """Tests for emit_qa_passed."""

    async def test_publishes_to_correct_subject(self):
        mock_js = AsyncMock()
        with patch("src.qa.signals.get_jetstream", AsyncMock(return_value=mock_js)):
            await emit_qa_passed(TP_ID, CORR_ID)

        mock_js.publish.assert_awaited_once()
        call_args = mock_js.publish.call_args
        subject = call_args[0][0]
        assert subject == f"{SUBJECT_PREFIX}.{TP_ID}"

    async def test_payload_contains_qa_passed_event(self):
        mock_js = AsyncMock()
        with patch("src.qa.signals.get_jetstream", AsyncMock(return_value=mock_js)):
            await emit_qa_passed(TP_ID, CORR_ID)

        raw = mock_js.publish.call_args[0][1]
        payload = json.loads(raw)
        assert payload["event"] == "qa_passed"
        assert payload["taskpacket_id"] == str(TP_ID)
        assert payload["correlation_id"] == str(CORR_ID)
        assert "defects" not in payload


class TestEmitQADefect:
    """Tests for emit_qa_defect."""

    async def test_publishes_with_defects(self):
        mock_js = AsyncMock()
        defects = [_make_defect(), _make_defect(severity=Severity.S1_HIGH)]

        with patch("src.qa.signals.get_jetstream", AsyncMock(return_value=mock_js)):
            await emit_qa_defect(TP_ID, CORR_ID, defects)

        mock_js.publish.assert_awaited_once()
        raw = mock_js.publish.call_args[0][1]
        payload = json.loads(raw)
        assert payload["event"] == "qa_defect"
        assert len(payload["defects"]) == 2

    async def test_correct_subject(self):
        mock_js = AsyncMock()
        with patch("src.qa.signals.get_jetstream", AsyncMock(return_value=mock_js)):
            await emit_qa_defect(TP_ID, CORR_ID, [_make_defect()])

        subject = mock_js.publish.call_args[0][0]
        assert subject == f"{SUBJECT_PREFIX}.{TP_ID}"


class TestEmitQARework:
    """Tests for emit_qa_rework."""

    async def test_publishes_with_rework_event(self):
        mock_js = AsyncMock()
        defects = [_make_defect()]

        with patch("src.qa.signals.get_jetstream", AsyncMock(return_value=mock_js)):
            await emit_qa_rework(TP_ID, CORR_ID, defects)

        mock_js.publish.assert_awaited_once()
        raw = mock_js.publish.call_args[0][1]
        payload = json.loads(raw)
        assert payload["event"] == "qa_rework"
        assert len(payload["defects"]) == 1

    async def test_correct_subject(self):
        mock_js = AsyncMock()
        with patch("src.qa.signals.get_jetstream", AsyncMock(return_value=mock_js)):
            await emit_qa_rework(TP_ID, CORR_ID, [_make_defect()])

        subject = mock_js.publish.call_args[0][0]
        assert subject == f"{SUBJECT_PREFIX}.{TP_ID}"

    async def test_logs_defect_count(self):
        mock_js = AsyncMock()
        defects = [_make_defect(), _make_defect(), _make_defect()]

        with (
            patch("src.qa.signals.get_jetstream", AsyncMock(return_value=mock_js)),
            patch("src.qa.signals.logger") as mock_logger,
        ):
            await emit_qa_rework(TP_ID, CORR_ID, defects)

        mock_logger.info.assert_called_once()
        log_msg = mock_logger.info.call_args[0][0]
        assert "qa_rework" in log_msg


# ---------------------------------------------------------------------------
# Pipeline gate event tests
# ---------------------------------------------------------------------------


class TestQAPipelineGateEvents:
    """Verify that QA emit_* functions also publish pipeline.gate.pass/fail."""

    async def test_passed_emits_gate_pass(self) -> None:
        mock_js = AsyncMock()
        pipeline_js = AsyncMock()

        with (
            patch("src.qa.signals.get_jetstream", AsyncMock(return_value=mock_js)),
            patch("src.qa.signals.get_pipeline_jetstream", AsyncMock(return_value=pipeline_js)),
        ):
            await emit_qa_passed(TP_ID, CORR_ID)

        pipeline_js.publish.assert_awaited_once()
        subject = pipeline_js.publish.call_args[0][0]
        assert subject == "pipeline.gate.pass"
        payload = json.loads(pipeline_js.publish.call_args[0][1])
        assert payload["type"] == "pipeline.gate.pass"
        assert payload["data"]["stage"] == "qa"

    async def test_defect_emits_gate_fail(self) -> None:
        mock_js = AsyncMock()
        pipeline_js = AsyncMock()

        with (
            patch("src.qa.signals.get_jetstream", AsyncMock(return_value=mock_js)),
            patch("src.qa.signals.get_pipeline_jetstream", AsyncMock(return_value=pipeline_js)),
        ):
            await emit_qa_defect(TP_ID, CORR_ID, [_make_defect()])

        subject = pipeline_js.publish.call_args[0][0]
        assert subject == "pipeline.gate.fail"

    async def test_rework_emits_gate_fail(self) -> None:
        mock_js = AsyncMock()
        pipeline_js = AsyncMock()

        with (
            patch("src.qa.signals.get_jetstream", AsyncMock(return_value=mock_js)),
            patch("src.qa.signals.get_pipeline_jetstream", AsyncMock(return_value=pipeline_js)),
        ):
            await emit_qa_rework(TP_ID, CORR_ID, [_make_defect()])

        subject = pipeline_js.publish.call_args[0][0]
        assert subject == "pipeline.gate.fail"

    async def test_gate_failure_does_not_break_emit(self) -> None:
        """Pipeline gate publish failure must not affect QA signal."""
        mock_js = AsyncMock()
        pipeline_js = AsyncMock()
        pipeline_js.publish.side_effect = Exception("NATS down")

        with (
            patch("src.qa.signals.get_jetstream", AsyncMock(return_value=mock_js)),
            patch("src.qa.signals.get_pipeline_jetstream", AsyncMock(return_value=pipeline_js)),
        ):
            await emit_qa_passed(TP_ID, CORR_ID)

        # Original QA signal still published
        mock_js.publish.assert_awaited_once()
