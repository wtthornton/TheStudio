"""CLI-shaped Ralph status parsing, including TESTS_STATUS: DEFERRED (Epic 51)."""

from __future__ import annotations

import json

from ralph_sdk.parsing import parse_ralph_status
from ralph_sdk.status import RalphLoopStatus


def test_text_fallback_tests_status_deferred() -> None:
    text = """
Some narrative from the model.

WORK_TYPE: IMPLEMENTATION
PROGRESS_SUMMARY: deferred tests per epic policy
TESTS_STATUS: DEFERRED
EXIT_SIGNAL: false
"""
    st = parse_ralph_status(text)
    assert st.tests_status == "DEFERRED"
    assert st.exit_signal is False


def test_text_fallback_tests_status_deferred_case_insensitive() -> None:
    text = "TESTS_STATUS: deferred\nEXIT_SIGNAL: false\n"
    st = parse_ralph_status(text)
    assert st.tests_status == "DEFERRED"


def test_json_block_tests_status_deferred() -> None:
    text = """```json
{
  "work_type": "IMPLEMENTATION",
  "progress_summary": "loop",
  "exit_signal": false,
  "tests_status": "DEFERRED"
}
```"""
    st = parse_ralph_status(text)
    assert st.tests_status == "DEFERRED"


def test_jsonl_wraps_result_with_deferred_text() -> None:
    inner = "TESTS_STATUS: DEFERRED\nEXIT_SIGNAL: false\n"
    line = '{"type": "result", "result": ' + json.dumps(inner) + "}"
    st = parse_ralph_status(line)
    assert st.tests_status == "DEFERRED"


def test_deferred_does_not_force_completed_loop_status_in_json() -> None:
    text = """```json
{"work_type": "IMPLEMENTATION", "exit_signal": false, "tests_status": "DEFERRED"}
```"""
    st = parse_ralph_status(text)
    assert st.status != RalphLoopStatus.COMPLETED
