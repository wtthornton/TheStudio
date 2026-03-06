"""Verification Gate — deterministic quality check orchestrator.

Runs repo-profile checks against code changes, emits pass/fail signals
to JetStream, and triggers loopback on failure (max 2 for Phase 0).

Gates fail closed: runner errors = verification failure.

Architecture reference: thestudioarc/13-verification-gate.md
"""

import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.taskpacket import TaskPacketStatus
from src.models.taskpacket_crud import (
    get_by_id,
    increment_loopback,
    update_status,
)
from src.observability.conventions import (
    ATTR_CORRELATION_ID,
    ATTR_TASKPACKET_ID,
    SPAN_VERIFICATION_CHECK,
    SPAN_VERIFICATION_RUN,
)
from src.observability.tracing import get_tracer
from src.repo.repo_profile_crud import get_by_repo
from src.verification.runners.base import CheckResult
from src.verification.runners.pytest_runner import run_pytest
from src.verification.runners.ruff_runner import run_ruff
from src.verification.signals import (
    emit_verification_exhausted,
    emit_verification_failed,
    emit_verification_passed,
)

logger = logging.getLogger(__name__)
tracer = get_tracer("thestudio.verification")

MAX_LOOPBACKS = 2

# Map check names to runner functions
_RUNNERS: dict[str, str] = {
    "ruff": "ruff",
    "pytest": "pytest",
}


@dataclass
class VerificationResult:
    """Result of a full verification cycle."""

    passed: bool
    checks: list[CheckResult]
    loopback_triggered: bool = False
    exhausted: bool = False


async def _run_check(
    check_name: str,
    changed_files: list[str],
    repo_path: str,
) -> CheckResult:
    """Run a single check by name."""
    with tracer.start_as_current_span(SPAN_VERIFICATION_CHECK) as span:
        span.set_attribute("thestudio.check_name", check_name)

        if check_name == "ruff":
            result = await run_ruff(changed_files, repo_path)
        elif check_name == "pytest":
            result = await run_pytest(repo_path)
        else:
            result = CheckResult(
                name=check_name, passed=False, details=f"Unknown check: {check_name}"
            )

        span.set_attribute("thestudio.check_result", "passed" if result.passed else "failed")
        return result


async def verify(
    session: AsyncSession,
    taskpacket_id: UUID,
    changed_files: list[str],
    repo_path: str,
) -> VerificationResult:
    """Run verification checks for a TaskPacket.

    Loads required checks from Repo Profile, runs each, emits signals,
    and triggers loopback on failure (up to MAX_LOOPBACKS).

    Args:
        session: Database session.
        taskpacket_id: TaskPacket being verified.
        changed_files: List of changed file paths.
        repo_path: Root path of the repository.

    Returns:
        VerificationResult with pass/fail, check details, and loopback status.
    """
    with tracer.start_as_current_span(SPAN_VERIFICATION_RUN) as span:
        # Load TaskPacket
        tp = await get_by_id(session, taskpacket_id)
        if tp is None:
            raise ValueError(f"TaskPacket {taskpacket_id} not found")

        span.set_attribute(ATTR_TASKPACKET_ID, str(taskpacket_id))
        span.set_attribute(ATTR_CORRELATION_ID, str(tp.correlation_id))
        span.set_attribute("thestudio.loopback_count", tp.loopback_count)

        # Load Repo Profile for required checks
        owner, repo_name = tp.repo.split("/", 1)
        profile = await get_by_repo(session, owner, repo_name)
        required_checks = profile.required_checks if profile else ["ruff", "pytest"]

        # Run all checks
        results: list[CheckResult] = []
        for check_name in required_checks:
            result = await _run_check(check_name, changed_files, repo_path)
            results.append(result)

        all_passed = all(r.passed for r in results)

        if all_passed:
            # Verification passed
            await update_status(session, taskpacket_id, TaskPacketStatus.VERIFICATION_PASSED)
            await emit_verification_passed(
                taskpacket_id, tp.correlation_id, tp.loopback_count, results
            )
            span.set_attribute("thestudio.verification_outcome", "passed")
            return VerificationResult(passed=True, checks=results)

        # Verification failed — check loopback budget
        current_count = await increment_loopback(session, taskpacket_id)

        if current_count > MAX_LOOPBACKS:
            # Exhausted — mark as failed
            await update_status(session, taskpacket_id, TaskPacketStatus.FAILED)
            await emit_verification_exhausted(
                taskpacket_id, tp.correlation_id, current_count, results
            )
            span.set_attribute("thestudio.verification_outcome", "exhausted")
            return VerificationResult(
                passed=False, checks=results, exhausted=True
            )

        # Loopback — mark as verification_failed for retry
        await update_status(
            session, taskpacket_id, TaskPacketStatus.VERIFICATION_FAILED
        )
        await emit_verification_failed(
            taskpacket_id, tp.correlation_id, current_count, results
        )
        span.set_attribute("thestudio.verification_outcome", "failed_loopback")
        return VerificationResult(
            passed=False, checks=results, loopback_triggered=True
        )
