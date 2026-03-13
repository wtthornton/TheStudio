"""Mock activity implementations for integration tests.

Provides realistic mock activities for all 9 pipeline stages. Real
activities are used for intake and router (pure functions, no I/O).
Mock activities return properly typed dataclass instances with
non-empty, realistic data.

Note: Temporal may deserialize dataclass params as dicts, so mock
activities use _get() to handle both dataclass and dict access.

Usage:
    from tests.integration.mock_providers import ALL_MOCK_ACTIVITIES
    # Use ALL_MOCK_ACTIVITIES with a Temporal Worker
"""

from __future__ import annotations

from temporalio import activity

from src.workflow.activities import (
    AssemblerOutput,
    ContextOutput,
    ImplementOutput,
    IntentOutput,
    PublishOutput,
    QAOutput,
    VerifyOutput,
    intake_activity,
    router_activity,
)

# --- Real activities (pure functions, no external deps) ---
# intake_activity: calls evaluate_eligibility() — pure
# router_activity: calls route() — pure


def _get(params, key: str, default=""):
    """Get a field from params whether it's a dataclass or dict."""
    if isinstance(params, dict):
        return params.get(key, default)
    return getattr(params, key, default)


# --- Mock activities (replace I/O-dependent activities) ---


@activity.defn(name="context_activity")
async def mock_context_activity(params) -> ContextOutput:
    """Mock context enrichment — returns realistic scope and risk flags."""
    return ContextOutput(
        scope={"type": "bug_fix", "components": "auth,sso"},
        risk_flags={"security": True, "data_loss": False},
        complexity_index="medium",
        context_packs=[
            {"name": "auth-context", "version": "1.2.0"},
            {"name": "sso-integration", "version": "3.0.1"},
        ],
    )


@activity.defn(name="intent_activity")
async def mock_intent_activity(params) -> IntentOutput:
    """Mock intent builder — returns realistic intent spec."""
    return IntentOutput(
        intent_spec_id="int-test-001",
        version=1,
        goal="Fix SSO login timeout by reducing connection pool wait",
        acceptance_criteria=[
            "SSO login completes within 5 seconds",
            "Error message shown on timeout",
            "Retry button available after failure",
        ],
    )


@activity.defn(name="assembler_activity")
async def mock_assembler_activity(params) -> AssemblerOutput:
    """Mock assembler — returns realistic plan with provenance."""
    tp_id = _get(params, "taskpacket_id")
    return AssemblerOutput(
        plan_steps=[
            "reduce_connection_pool_timeout",
            "add_retry_logic",
            "update_error_messages",
            "add_integration_tests",
        ],
        qa_handoff=[
            {"check": "sso_timeout_test", "priority": "high"},
            {"check": "error_message_display", "priority": "medium"},
        ],
        provenance={"taskpacket_id": tp_id},
    )


@activity.defn(name="implement_activity")
async def mock_implement_activity(params) -> ImplementOutput:
    """Mock primary agent — returns realistic implementation output."""
    tp_id = _get(params, "taskpacket_id")
    return ImplementOutput(
        taskpacket_id=tp_id,
        intent_version=1,
        files_changed=[
            "src/auth/sso_client.py",
            "src/auth/connection_pool.py",
            "tests/test_sso_client.py",
        ],
        agent_summary=(
            "Reduced SSO connection pool timeout from 30s to 5s. "
            "Added retry logic with exponential backoff. "
            "Updated error messages to show user-friendly "
            "timeout notice."
        ),
    )


@activity.defn(name="verify_activity")
async def mock_verify_activity(params) -> VerifyOutput:
    """Mock verification — passes all checks."""
    return VerifyOutput(passed=True, checks=[])


@activity.defn(name="qa_activity")
async def mock_qa_activity(params) -> QAOutput:
    """Mock QA agent — passes validation."""
    return QAOutput(passed=True)


@activity.defn(name="publish_activity")
async def mock_publish_activity(params) -> PublishOutput:
    """Mock publisher — returns realistic PR output."""
    return PublishOutput(
        pr_number=42,
        pr_url="https://github.com/test-org/test-repo/pull/42",
        created=True,
        marked_ready=False,
    )


# --- Loopback variants ---


def make_verify_with_loopback(fail_count: int = 1):
    """Create a verify activity that fails N times then passes."""
    call_count = 0

    @activity.defn(name="verify_activity")
    async def verify_with_loopback(params) -> VerifyOutput:
        nonlocal call_count
        call_count += 1
        if call_count <= fail_count:
            return VerifyOutput(
                passed=False,
                loopback_triggered=True,
            )
        return VerifyOutput(passed=True, checks=[])

    return verify_with_loopback


def make_qa_with_loopback(fail_count: int = 1):
    """Create a QA activity that fails N times then passes."""
    call_count = 0

    @activity.defn(name="qa_activity")
    async def qa_with_loopback(params) -> QAOutput:
        nonlocal call_count
        call_count += 1
        if call_count <= fail_count:
            return QAOutput(
                passed=False,
                needs_loopback=True,
                defect_count=2,
            )
        return QAOutput(passed=True)

    return qa_with_loopback


def make_verify_always_fail():
    """Create a verify activity that always fails."""

    @activity.defn(name="verify_activity")
    async def verify_always_fail(params) -> VerifyOutput:
        return VerifyOutput(passed=False, loopback_triggered=True)

    return verify_always_fail


def make_qa_always_fail():
    """Create a QA activity that always fails."""

    @activity.defn(name="qa_activity")
    async def qa_always_fail(params) -> QAOutput:
        return QAOutput(
            passed=False, needs_loopback=True, defect_count=1,
        )

    return qa_always_fail


# --- Activity lists ---

ALL_MOCK_ACTIVITIES = [
    intake_activity,  # Real — pure function
    mock_context_activity,
    mock_intent_activity,
    router_activity,  # Real — pure function
    mock_assembler_activity,
    mock_implement_activity,
    mock_verify_activity,
    mock_qa_activity,
    mock_publish_activity,
]


def activities_with_verify_loopback(fail_count: int = 1) -> list:
    """Activity list where verify fails N times then passes."""
    activities = list(ALL_MOCK_ACTIVITIES)
    activities[6] = make_verify_with_loopback(fail_count)
    return activities


def activities_with_qa_loopback(fail_count: int = 1) -> list:
    """Activity list where QA fails N times then passes."""
    activities = list(ALL_MOCK_ACTIVITIES)
    activities[7] = make_qa_with_loopback(fail_count)
    return activities


def activities_with_verify_exhaustion() -> list:
    """Activity list where verify always fails."""
    activities = list(ALL_MOCK_ACTIVITIES)
    activities[6] = make_verify_always_fail()
    return activities


def activities_with_qa_exhaustion() -> list:
    """Activity list where QA always fails."""
    activities = list(ALL_MOCK_ACTIVITIES)
    activities[7] = make_qa_always_fail()
    return activities
