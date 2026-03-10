"""Unit tests for verification signal emission (signals.py).

Covers get_jetstream, _build_payload, and the three emit_* functions.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from src.verification.runners.base import CheckResult
from src.verification import signals
from src.verification.signals import (
    STREAM_NAME,
    SUBJECT_PREFIX,
    _build_payload,
    emit_verification_exhausted,
    emit_verification_failed,
    emit_verification_passed,
    get_jetstream,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TASK_ID = UUID("12345678-1234-5678-1234-567812345678")
CORR_ID = UUID("abcdefab-abcd-abcd-abcd-abcdefabcdef")


def _make_checks() -> list[CheckResult]:
    return [
        CheckResult(name="ruff", passed=True, details="", duration_ms=50),
        CheckResult(name="pytest", passed=False, details="1 failed", duration_ms=300),
    ]


@pytest.fixture(autouse=True)
def _reset_js_singleton():
    """Reset the module-level _js singleton before each test."""
    signals._js = None
    yield
    signals._js = None


# ---------------------------------------------------------------------------
# _build_payload tests
# ---------------------------------------------------------------------------


class TestBuildPayload:
    def test_basic_structure(self) -> None:
        checks = _make_checks()
        raw = _build_payload("verification_passed", TASK_ID, CORR_ID, 0, checks)
        data = json.loads(raw)

        assert data["event"] == "verification_passed"
        assert data["taskpacket_id"] == str(TASK_ID)
        assert data["correlation_id"] == str(CORR_ID)
        assert data["loopback_count"] == 0
        assert "timestamp" in data

    def test_checks_serialised(self) -> None:
        checks = _make_checks()
        data = json.loads(_build_payload("verification_failed", TASK_ID, CORR_ID, 2, checks))

        assert len(data["checks"]) == 2
        assert data["checks"][0]["name"] == "ruff"
        assert data["checks"][0]["result"] == "passed"
        assert data["checks"][0]["duration_ms"] == 50
        assert data["checks"][1]["name"] == "pytest"
        assert data["checks"][1]["result"] == "failed"
        assert data["checks"][1]["details"] == "1 failed"

    def test_empty_checks(self) -> None:
        data = json.loads(_build_payload("verification_passed", TASK_ID, CORR_ID, 0, []))
        assert data["checks"] == []

    def test_returns_bytes(self) -> None:
        raw = _build_payload("verification_passed", TASK_ID, CORR_ID, 0, [])
        assert isinstance(raw, bytes)

    def test_loopback_count_preserved(self) -> None:
        data = json.loads(_build_payload("verification_exhausted", TASK_ID, CORR_ID, 5, []))
        assert data["loopback_count"] == 5


# ---------------------------------------------------------------------------
# get_jetstream tests
# ---------------------------------------------------------------------------


def _mock_nc_with_js(mock_js):
    """Create a MagicMock nc whose .jetstream() returns mock_js (sync call)."""
    mock_nc = MagicMock()
    mock_nc.jetstream.return_value = mock_js
    return mock_nc


class TestGetJetstream:
    async def test_creates_singleton(self) -> None:
        mock_js = AsyncMock()
        mock_js.find_stream_name_by_subject = AsyncMock(return_value="found")
        mock_nc = _mock_nc_with_js(mock_js)

        with patch("src.verification.signals.nats.connect", AsyncMock(return_value=mock_nc)):
            js = await get_jetstream()
            assert js is mock_js
            mock_nc.jetstream.assert_called_once()

    async def test_returns_cached_on_second_call(self) -> None:
        mock_js = AsyncMock()
        mock_js.find_stream_name_by_subject = AsyncMock(return_value="found")
        mock_nc = _mock_nc_with_js(mock_js)

        mock_connect = AsyncMock(return_value=mock_nc)
        with patch("src.verification.signals.nats.connect", mock_connect):
            js1 = await get_jetstream()
            js2 = await get_jetstream()
            assert js1 is js2
            mock_connect.assert_called_once()

    async def test_creates_stream_when_not_found(self) -> None:
        mock_js = AsyncMock()
        mock_js.find_stream_name_by_subject = AsyncMock(side_effect=Exception("not found"))
        mock_js.add_stream = AsyncMock()
        mock_nc = _mock_nc_with_js(mock_js)

        with patch("src.verification.signals.nats.connect", AsyncMock(return_value=mock_nc)):
            await get_jetstream()
            mock_js.add_stream.assert_called_once_with(
                name=STREAM_NAME,
                subjects=[f"{SUBJECT_PREFIX}.*"],
            )

    async def test_skips_create_when_stream_exists(self) -> None:
        mock_js = AsyncMock()
        mock_js.find_stream_name_by_subject = AsyncMock(return_value=STREAM_NAME)
        mock_js.add_stream = AsyncMock()
        mock_nc = _mock_nc_with_js(mock_js)

        with patch("src.verification.signals.nats.connect", AsyncMock(return_value=mock_nc)):
            await get_jetstream()
            mock_js.add_stream.assert_not_called()


# ---------------------------------------------------------------------------
# emit_* function tests
# ---------------------------------------------------------------------------


class TestEmitVerificationPassed:
    async def test_publishes_correct_subject(self) -> None:
        mock_js = AsyncMock()
        checks = _make_checks()

        with patch("src.verification.signals.get_jetstream", return_value=mock_js):
            await emit_verification_passed(TASK_ID, CORR_ID, 0, checks)

        expected_subject = f"{SUBJECT_PREFIX}.{TASK_ID}"
        mock_js.publish.assert_awaited_once()
        call_args = mock_js.publish.await_args
        assert call_args[0][0] == expected_subject

    async def test_payload_contains_event(self) -> None:
        mock_js = AsyncMock()
        checks = _make_checks()

        with patch("src.verification.signals.get_jetstream", return_value=mock_js):
            await emit_verification_passed(TASK_ID, CORR_ID, 1, checks)

        payload = json.loads(mock_js.publish.await_args[0][1])
        assert payload["event"] == "verification_passed"
        assert payload["loopback_count"] == 1


class TestEmitVerificationFailed:
    async def test_publishes_correct_subject(self) -> None:
        mock_js = AsyncMock()
        checks = _make_checks()

        with patch("src.verification.signals.get_jetstream", return_value=mock_js):
            await emit_verification_failed(TASK_ID, CORR_ID, 2, checks)

        expected_subject = f"{SUBJECT_PREFIX}.{TASK_ID}"
        mock_js.publish.assert_awaited_once()
        call_args = mock_js.publish.await_args
        assert call_args[0][0] == expected_subject

    async def test_payload_contains_event(self) -> None:
        mock_js = AsyncMock()

        with patch("src.verification.signals.get_jetstream", return_value=mock_js):
            await emit_verification_failed(TASK_ID, CORR_ID, 3, [])

        payload = json.loads(mock_js.publish.await_args[0][1])
        assert payload["event"] == "verification_failed"
        assert payload["loopback_count"] == 3


class TestEmitVerificationExhausted:
    async def test_publishes_correct_subject(self) -> None:
        mock_js = AsyncMock()
        checks = _make_checks()

        with patch("src.verification.signals.get_jetstream", return_value=mock_js):
            await emit_verification_exhausted(TASK_ID, CORR_ID, 5, checks)

        expected_subject = f"{SUBJECT_PREFIX}.{TASK_ID}"
        mock_js.publish.assert_awaited_once()
        assert mock_js.publish.await_args[0][0] == expected_subject

    async def test_payload_contains_event(self) -> None:
        mock_js = AsyncMock()

        with patch("src.verification.signals.get_jetstream", return_value=mock_js):
            await emit_verification_exhausted(TASK_ID, CORR_ID, 10, [])

        payload = json.loads(mock_js.publish.await_args[0][1])
        assert payload["event"] == "verification_exhausted"
        assert payload["loopback_count"] == 10

    async def test_logs_info(self, caplog) -> None:
        mock_js = AsyncMock()

        with (
            patch("src.verification.signals.get_jetstream", return_value=mock_js),
            caplog.at_level("INFO", logger="src.verification.signals"),
        ):
            await emit_verification_exhausted(TASK_ID, CORR_ID, 0, [])

        assert "verification_exhausted" in caplog.text
