"""Verify all 9 pipeline stages emit enter/exit events via events_publisher.

B-0.4b acceptance: full pipeline run emits 9/9 stage enter/exit events.
"""

import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest

ALL_STAGES = [
    "intake",
    "context",
    "intent",
    "router",
    "assembler",
    "implement",
    "verify",
    "qa",
    "publish",
]

TASK_ID = str(uuid.uuid4())


def _collect_events(mock_js: AsyncMock) -> list[dict]:
    """Extract published events from mock JetStream."""
    events = []
    for call in mock_js.publish.call_args_list:
        _subject, payload_bytes = call.args
        events.append(json.loads(payload_bytes))
    return events


def _mock_js():
    js = AsyncMock()
    js.find_stream_name_by_subject = AsyncMock(
        return_value="THESTUDIO_PIPELINE",
    )
    js.publish = AsyncMock()
    return js


class _StubAgentResult:
    def __init__(self):
        self.parsed_output = None
        self.raw_output = "{}"


class _StubAgentRunner:
    def __init__(self, config):
        pass

    async def run(self, context):
        return _StubAgentResult()


@pytest.mark.asyncio
async def test_all_9_stages_emit_enter_exit():
    """Each stage activity should emit exactly one enter and one exit event."""
    from src.workflow.activities import (
        AssemblerInput,
        ContextInput,
        ImplementInput,
        ImplementOutput,
        IntakeInput,
        IntentInput,
        PublishInput,
        QAInput,
        RouterInput,
        VerifyInput,
        assembler_activity,
        context_activity,
        implement_activity,
        intake_activity,
        intent_activity,
        publish_activity,
        qa_activity,
        router_activity,
        verify_activity,
    )

    mock_js = _mock_js()
    tid = TASK_ID

    with (
        patch(
            "src.dashboard.events_publisher.get_pipeline_jetstream",
            return_value=mock_js,
        ),
        patch(
            "src.agent.framework.AgentRunner",
            _StubAgentRunner,
        ),
        patch(
            "src.workflow.activities._implement_in_process",
            new_callable=AsyncMock,
            return_value=ImplementOutput(
                taskpacket_id=tid,
                files_changed=["src/foo.py"],
                agent_summary="Fixed it",
            ),
        ),
        patch("src.settings.settings") as mock_settings,
    ):
        mock_settings.agent_isolation = "process"
        mock_settings.github_provider = "stub"
        mock_settings.nats_url = "nats://localhost:4222"

        # Stage 1: Intake
        await intake_activity(IntakeInput(
            repo="owner/repo",
            issue_title="Test",
            issue_body="body",
            labels=[],
            repo_registered=True,
            repo_paused=False,
            has_active_workflow=False,
            event_id=tid,
        ))

        # Stage 2: Context
        await context_activity(ContextInput(
            taskpacket_id=tid,
            repo="owner/repo",
            issue_title="Test",
            issue_body="body",
            labels=[],
        ))

        # Stage 3: Intent
        await intent_activity(IntentInput(
            taskpacket_id=tid,
            issue_title="Test",
            issue_body="body",
            risk_flags={},
        ))

        # Stage 4: Router
        await router_activity(RouterInput(
            base_role="Developer",
            overlays=[],
            risk_flags={},
            taskpacket_id=tid,
        ))

        # Stage 5: Assembler
        await assembler_activity(AssemblerInput(
            taskpacket_id=tid,
            intent_goal="Fix bug",
            intent_constraints=[],
            acceptance_criteria="Tests pass",
        ))

        # Stage 6: Implement
        await implement_activity(ImplementInput(
            taskpacket_id=tid,
            repo_path="/tmp/repo",
            loopback_attempt=0,
        ))

        # Stage 7: Verify
        await verify_activity(VerifyInput(
            taskpacket_id=tid,
            changed_files=["src/foo.py"],
            repo_path="/tmp/repo",
        ))

        # Stage 8: QA
        await qa_activity(QAInput(
            taskpacket_id=tid,
            acceptance_criteria="Tests pass",
            qa_handoff="",
            evidence={"test_results": "all passed"},
        ))

        # Stage 9: Publish
        await publish_activity(PublishInput(
            taskpacket_id=tid,
            repo_tier="observe",
            qa_passed=True,
            files_changed=["src/foo.py"],
            agent_summary="Fixed bug",
        ))

    events = _collect_events(mock_js)
    enter_stages = [
        e["data"]["stage"]
        for e in events
        if e["type"] == "pipeline.stage.enter"
    ]
    exit_stages = [
        e["data"]["stage"]
        for e in events
        if e["type"] == "pipeline.stage.exit"
    ]

    assert sorted(enter_stages) == sorted(ALL_STAGES), (
        f"Missing enter events: {set(ALL_STAGES) - set(enter_stages)}"
    )
    assert sorted(exit_stages) == sorted(ALL_STAGES), (
        f"Missing exit events: {set(ALL_STAGES) - set(exit_stages)}"
    )
    # Verify all exits were successful
    for e in events:
        if e["type"] == "pipeline.stage.exit":
            assert e["data"]["success"] is True, (
                f"Stage {e['data']['stage']} exited with success=False"
            )
