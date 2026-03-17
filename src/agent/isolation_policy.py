"""Container isolation policy enforcement (Epic 25 blocker fix).

Determines whether a task must run in a container, can fall back to
in-process, or must fail when container mode is unavailable.

The key security invariant: Execute tier tasks MUST NOT silently fall back
to in-process execution. A missing Docker runtime on Execute tier is a
hard failure, not a graceful degradation.
"""

import enum
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class IsolationMode(enum.StrEnum):
    """How the agent code should execute."""

    PROCESS = "process"
    CONTAINER = "container"


class FallbackPolicy(enum.StrEnum):
    """What to do when container mode is requested but unavailable."""

    ALLOW = "allow"  # Fall back to in-process (Observe/Suggest only)
    DENY = "deny"  # Fail the task (Execute tier)


@dataclass(frozen=True)
class IsolationDecision:
    """Result of resolving isolation policy for a task."""

    mode: IsolationMode
    fell_back: bool  # True if container was requested but unavailable
    tier: str
    cpu_limit: float
    memory_mb: int
    timeout_seconds: int


class ContainerUnavailableError(Exception):
    """Raised when container mode is required but Docker is not available."""

    def __init__(self, tier: str) -> None:
        super().__init__(
            f"Container isolation required for {tier} tier but Docker is unavailable. "
            f"Fallback policy is 'deny' — task cannot proceed without isolation."
        )
        self.tier = tier


def resolve_isolation(
    repo_tier: str,
    container_available: bool,
) -> IsolationDecision:
    """Resolve the isolation mode for a task based on tier and availability.

    Args:
        repo_tier: Trust tier of the repository (observe, suggest, execute).
        container_available: Whether the Docker runtime is reachable.

    Returns:
        IsolationDecision with the resolved mode and resource limits.

    Raises:
        ContainerUnavailableError: When container is required but unavailable.
    """
    from src.settings import settings

    global_mode = IsolationMode(settings.agent_isolation)
    fallback = FallbackPolicy(
        settings.agent_isolation_fallback.get(repo_tier, "allow")
    )
    cpu = settings.agent_container_cpu_limit.get(repo_tier, 1.0)
    mem = settings.agent_container_memory_mb.get(repo_tier, 512)
    timeout = settings.agent_container_timeout_seconds.get(repo_tier, 300)

    # If global mode is process, always run in-process (no container needed)
    if global_mode == IsolationMode.PROCESS:
        return IsolationDecision(
            mode=IsolationMode.PROCESS,
            fell_back=False,
            tier=repo_tier,
            cpu_limit=cpu,
            memory_mb=mem,
            timeout_seconds=timeout,
        )

    # Container mode requested
    if container_available:
        return IsolationDecision(
            mode=IsolationMode.CONTAINER,
            fell_back=False,
            tier=repo_tier,
            cpu_limit=cpu,
            memory_mb=mem,
            timeout_seconds=timeout,
        )

    # Container unavailable — check fallback policy
    if fallback == FallbackPolicy.DENY:
        logger.error(
            "isolation.container_unavailable",
            extra={"tier": repo_tier, "fallback": "deny"},
        )
        raise ContainerUnavailableError(repo_tier)

    # Fallback allowed (Observe/Suggest)
    logger.warning(
        "isolation.fallback_to_process",
        extra={"tier": repo_tier, "fallback": "allow"},
    )
    return IsolationDecision(
        mode=IsolationMode.PROCESS,
        fell_back=True,
        tier=repo_tier,
        cpu_limit=cpu,
        memory_mb=mem,
        timeout_seconds=timeout,
    )
