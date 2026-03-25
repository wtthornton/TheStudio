"""CLI-shaped Ralph status parsing tests (Epic 51, updated for SDK v2.0.3).

tests_status field was removed from RalphStatus in v2.0.3. These tests verify
the 3-strategy parse chain (JSON block, JSONL, text fallback) still works for
standard fields.
"""

from __future__ import annotations

import json

from ralph_sdk.parsing import parse_ralph_status
from ralph_sdk.status import RalphLoopStatus, WorkType


def test_text_fallback_parses_work_type_and_exit_signal() -> None:
    text = """
Some narrative from the model.

WORK_TYPE: IMPLEMENTATION
PROGRESS_SUMMARY: deferred tests per epic policy
EXIT_SIGNAL: false
"""
    st = parse_ralph_status(text)
    assert st.work_type == WorkType.IMPLEMENTATION
    assert st.exit_signal is False
    assert st.progress_summary == "deferred tests per epic policy"


def test_text_fallback_exit_signal_true() -> None:
    text = "WORK_TYPE: BUG_FIX\nEXIT_SIGNAL: true\n"
    st = parse_ralph_status(text)
    assert st.exit_signal is True


def test_json_block_parses_correctly() -> None:
    text = """```json
{
  "work_type": "IMPLEMENTATION",
  "progress_summary": "loop iteration",
  "exit_signal": false
}
```"""
    st = parse_ralph_status(text)
    assert st.work_type == WorkType.IMPLEMENTATION
    assert st.progress_summary == "loop iteration"
    assert st.exit_signal is False


def test_jsonl_wraps_result_parsed() -> None:
    inner = "WORK_TYPE: REFACTORING\nEXIT_SIGNAL: false\n"
    line = '{"type": "result", "result": ' + json.dumps(inner) + "}"
    st = parse_ralph_status(line)
    assert st.exit_signal is False


def test_json_block_without_exit_signal_not_completed() -> None:
    text = """```json
{"work_type": "IMPLEMENTATION", "exit_signal": false}
```"""
    st = parse_ralph_status(text)
    assert st.status != RalphLoopStatus.COMPLETED
