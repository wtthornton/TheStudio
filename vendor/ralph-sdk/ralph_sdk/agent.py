"""Ralph SDK Agent — Agent SDK proof of concept replicating ralph_loop.sh core loop.

Dual-mode: standalone CLI + TheStudio embedded.
All agent methods are async. Use run_sync() for CLI synchronous execution.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel, Field, field_validator

from ralph_sdk.circuit_breaker import CircuitBreaker, StallDetector
from ralph_sdk.config import RalphConfig
from ralph_sdk.context_management import build_progressive_context
from ralph_sdk.cost_tracking import CostTracker
from ralph_sdk.decomposition import (
    DecompositionContext,
    DecompositionHint,
    detect_decomposition_needed,
)
from ralph_sdk.parsing import parse_ralph_status
from ralph_sdk.state import FileStateBackend, RalphStateBackend
from ralph_sdk.status import CircuitBreakerState, RalphLoopStatus, RalphStatus, WorkType
from ralph_sdk.tools import (
    RALPH_TOOLS,
    ralph_circuit_state_tool,
    ralph_rate_check_tool,
    ralph_status_tool,
    ralph_task_update_tool,
)

logger = logging.getLogger("ralph.sdk")


class CancelResult(BaseModel, frozen=True):
    """Outcome of :meth:`RalphAgent.cancel` (Temporal / activity cancellation).

    ``cancel`` is synchronous and safe from another thread while the event loop
    is driving ``run()`` / ``run_iteration()``. It sets the loop stop flag and
    sends **SIGTERM** to the active Claude CLI child process when one exists
    (``terminate()`` on :class:`asyncio.subprocess.Process`; on Windows this
    ends the child process similarly).

    ``partial_output`` contains the decoded stdout from the most recently
    completed (or just-terminated) subprocess invocation.  It is populated from
    ``RalphAgent._output_buffer``, which is updated at the end of every
    ``_run_iteration`` call.  When ``cancel()`` races with an in-flight
    ``communicate()`` the buffer reflects the *previous* iteration; once the
    process exits the activity's grace-wait loop can read the final value via
    ``agent._output_buffer``.

    **Grace wait contract (caller responsibility):**
    After ``cancel()`` returns, the activity wrapper should ``await
    asyncio.sleep(grace_seconds)`` (default 10 s) before hard-cancelling the
    asyncio task so the subprocess can flush and ``communicate()`` can resolve.
    """

    requested: bool = True
    subprocess_terminated: bool = False
    message: str = ""
    partial_output: str = ""


def _status_is_timeout(status: RalphStatus) -> bool:
    s = status.status
    if isinstance(s, RalphLoopStatus):
        return s == RalphLoopStatus.TIMEOUT
    return str(s).upper() == "TIMEOUT"


def _status_is_error(status: RalphStatus) -> bool:
    s = status.status
    if isinstance(s, RalphLoopStatus):
        return s == RalphLoopStatus.ERROR
    return str(s).upper() == "ERROR"


# =============================================================================
# Abstract Interface (SDK-3: Hybrid Architecture)
# =============================================================================


class RalphAgentInterface(Protocol):
    """Abstract interface for Ralph agent implementations (CLI and SDK)."""

    async def run_iteration(self, prompt: str, context: dict[str, Any]) -> RalphStatus:
        """Execute a single loop iteration."""
        ...

    async def should_exit(self, status: RalphStatus, loop_count: int) -> bool:
        """Evaluate exit conditions (dual-condition gate)."""
        ...

    async def check_rate_limit(self) -> bool:
        """Check if within rate limits. Returns True if OK to proceed."""
        ...

    async def check_circuit_breaker(self) -> bool:
        """Check circuit breaker state. Returns True if OK to proceed."""
        ...


# =============================================================================
# Task Input/Output (SDK-3: TheStudio compatibility)
# =============================================================================


class TaskInput(BaseModel, frozen=True):
    """Union type for task input — handles fix_plan.md and TheStudio TaskPackets.

    In standalone mode: reads from fix_plan.md + PROMPT.md
    In TheStudio mode: receives TaskPacket with structured fields
    """

    prompt: str = ""
    fix_plan: str = ""
    agent_instructions: str = ""
    # TheStudio fields (populated when embedded)
    task_packet_id: str = ""
    task_packet_type: str = ""
    task_packet_payload: dict[str, Any] = Field(default_factory=dict)
    complexity_band: str = "unknown"

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        """Prompt must be non-empty when provided for execution (validated at use site)."""
        return v

    @field_validator("task_packet_payload")
    @classmethod
    def validate_payload(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Payload must be a dict."""
        return v

    @classmethod
    def from_ralph_dir(cls, ralph_dir: str | Path = ".ralph") -> TaskInput:
        """Load task input from .ralph/ directory (standalone mode)."""
        ralph_path = Path(ralph_dir)
        prompt = ""
        fix_plan = ""
        agent_instructions = ""

        prompt_file = ralph_path / "PROMPT.md"
        if prompt_file.exists():
            prompt = prompt_file.read_text(encoding="utf-8")

        fix_plan_file = ralph_path / "fix_plan.md"
        if fix_plan_file.exists():
            fix_plan = fix_plan_file.read_text(encoding="utf-8")

        agent_file = ralph_path / "AGENT.md"
        if agent_file.exists():
            agent_instructions = agent_file.read_text(encoding="utf-8")

        return cls(
            prompt=prompt,
            fix_plan=fix_plan,
            agent_instructions=agent_instructions,
        )

    @classmethod
    def from_task_packet(cls, packet: dict[str, Any]) -> TaskInput:
        """Load task input from TheStudio TaskPacket."""
        return cls(
            prompt=packet.get("prompt", ""),
            fix_plan=packet.get("fix_plan", ""),
            agent_instructions=packet.get("agent_instructions", ""),
            task_packet_id=packet.get("id", ""),
            task_packet_type=packet.get("type", ""),
            task_packet_payload=packet,
            complexity_band=str(packet.get("complexity_band", "unknown") or "unknown"),
        )


class TaskResult(BaseModel):
    """Output compatible with status.json and TheStudio signals."""

    status: RalphStatus = Field(default_factory=RalphStatus)
    exit_code: int = 0
    output: str = ""
    error: str = ""
    loop_count: int = 0
    duration_seconds: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    files_changed: list[str] = Field(default_factory=list)
    decomposition_hint: DecompositionHint | None = None
    session_cost_usd: float = 0.0

    def to_signal(self) -> dict[str, Any]:
        """Convert to TheStudio-compatible signal format."""
        return {
            "type": "ralph_result",
            "task_result": self.status.to_dict(),
            "exit_code": self.exit_code,
            "output": self.output,
            "error": self.error,
            "loop_count": self.loop_count,
            "duration_seconds": self.duration_seconds,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "files_changed": self.files_changed,
            "decomposition_hint": self.decomposition_hint.model_dump()
            if self.decomposition_hint
            else None,
            "session_cost_usd": self.session_cost_usd,
        }


# =============================================================================
# SDK Agent Implementation (SDK-1: Proof of Concept)
# =============================================================================


class RalphAgent:
    """Ralph Agent SDK implementation — replicates ralph_loop.sh core loop in Python.

    Core loop: Read PROMPT.md + fix_plan.md -> invoke Claude -> parse response ->
    check exit conditions -> repeat.

    All loop methods are async. Use run_sync() for synchronous CLI execution.

    Supports three operational modes:
    - Standalone CLI: `ralph` (bash loop, unchanged)
    - Standalone SDK: `ralph --sdk` (this class)
    - TheStudio embedded: RalphAgent used as Primary Agent
    """

    def __init__(
        self,
        config: RalphConfig | None = None,
        project_dir: str | Path = ".",
        state_backend: RalphStateBackend | None = None,
        correlation_id: str | None = None,
        tracer: Any | None = None,
    ) -> None:
        self.config = config or RalphConfig.load(project_dir)
        self.project_dir = Path(project_dir).resolve()
        self.ralph_dir = self.project_dir / self.config.ralph_dir
        self.loop_count = 0
        self.start_time = 0.0
        self.session_id = ""
        self._completion_indicators = 0
        self._running = False
        self._last_tokens_in = 0
        self._last_tokens_out = 0

        # Correlation ID — auto-generated UUID if not provided
        self.correlation_id = correlation_id or str(uuid.uuid4())

        # Optional OpenTelemetry tracer (guarded import)
        self.tracer = tracer

        # State backend — FileStateBackend by default
        self.state_backend: RalphStateBackend = state_backend or FileStateBackend(self.ralph_dir)

        self._circuit_breaker = CircuitBreaker(
            self.state_backend,
            no_progress_threshold=self.config.cb_no_progress_threshold,
            same_error_threshold=self.config.cb_same_error_threshold,
            cooldown_minutes=self.config.cb_cooldown_minutes,
            auto_reset=self.config.cb_auto_reset,
        )
        self._stall_detector = StallDetector(
            self._circuit_breaker,
            fast_trip_max=self.config.stall_fast_trip_max,
            fast_trip_max_seconds=self.config.stall_fast_trip_max_seconds,
            deferred_test_max=self.config.stall_deferred_test_max,
            consecutive_timeout_max=self.config.stall_consecutive_timeout_max,
        )
        self._files_changed_session: set[str] = set()
        self._last_iteration_files_changed: list[str] = []
        self._last_iteration_duration_sec: float = 0.0
        self._prior_iteration_timeout: bool = False
        self._no_file_change_streak: int = 0
        self._cost_tracker = CostTracker(self.config)
        self._current_cli_proc: asyncio.subprocess.Process | None = None
        # Rolling buffer of the most recently captured subprocess stdout.
        # Updated at the end of every _run_iteration so cancel() can surface
        # partial work even when the active communicate() is still in-flight.
        self._output_buffer: str = ""

        # Ensure .ralph directory exists
        self.ralph_dir.mkdir(parents=True, exist_ok=True)
        (self.ralph_dir / "logs").mkdir(exist_ok=True)

    # -------------------------------------------------------------------------
    # Sync wrapper for CLI mode
    # -------------------------------------------------------------------------

    def run_sync(self) -> TaskResult:
        """Synchronous wrapper around async run() for CLI mode.

        Uses asyncio.run() to execute the async loop. This is the entry point
        for `ralph --sdk` and `python -m ralph_sdk`.
        """
        return asyncio.run(self.run())

    def cancel(self) -> CancelResult:
        """Stop the loop and **SIGTERM** the active Claude CLI subprocess if any.

        Intended for Temporal activity cancellation and wall-clock timeouts.
        Returns immediately after signalling.

        **Caller grace-wait pattern** (activities.py)::

            cr = agent.cancel()
            await asyncio.sleep(grace_seconds)  # default 10 s
            impl_task.cancel()
            await asyncio.gather(impl_task, return_exceptions=True)

        After the grace period the activity wrapper may inspect
        ``agent._output_buffer`` for the final captured output if
        ``communicate()`` resolved while the subprocess was exiting.

        :returns: :class:`CancelResult` with ``partial_output`` from the most
            recently completed subprocess invocation (may be from the previous
            iteration if the current one is still in-flight).
        """
        self._running = False
        partial = self._output_buffer
        proc = self._current_cli_proc
        if proc is None or proc.returncode is not None:
            return CancelResult(
                requested=True,
                subprocess_terminated=False,
                message="No active Claude CLI subprocess",
                partial_output=partial,
            )
        try:
            proc.terminate()
            return CancelResult(
                requested=True,
                subprocess_terminated=True,
                message="Sent SIGTERM to Claude CLI subprocess",
                partial_output=partial,
            )
        except OSError as exc:
            return CancelResult(
                requested=True,
                subprocess_terminated=False,
                message=f"terminate() failed: {exc}",
                partial_output=partial,
            )

    # -------------------------------------------------------------------------
    # Core Loop (async, replicates ralph_loop.sh main())
    # -------------------------------------------------------------------------

    async def run(self) -> TaskResult:
        """Execute the autonomous loop until exit conditions are met."""
        self.start_time = time.time()
        self._running = True

        logger.info(
            "Ralph SDK starting (v%s) [%s]",
            self.config.model,
            self.correlation_id,
            extra={"correlation_id": self.correlation_id},
        )
        logger.info(
            "Project: %s (%s)",
            self.config.project_name,
            self.config.project_type,
            extra={"correlation_id": self.correlation_id},
        )

        # Load session
        await self._load_session()

        # Reset circuit breaker counters (matching bash behavior)
        cb_data = await self.state_backend.read_circuit_breaker()
        cb = CircuitBreakerState._from_state_dict(cb_data) if cb_data else CircuitBreakerState()
        cb.no_progress_count = 0
        cb.same_error_count = 0
        await self.state_backend.write_circuit_breaker(cb._to_state_dict())

        self._stall_detector.reset()
        self._files_changed_session.clear()
        self._prior_iteration_timeout = False
        self._no_file_change_streak = 0
        self._cost_tracker.reset()

        result = TaskResult()

        try:
            while self._running:
                self.loop_count += 1
                logger.info("Loop iteration %d", self.loop_count)

                # Rate limit check
                if not await self.check_rate_limit():
                    logger.warning("Rate limit reached, waiting for reset")
                    result.error = "Rate limit reached"
                    break

                # Circuit breaker check
                if not await self.check_circuit_breaker():
                    logger.warning("Circuit breaker OPEN, stopping")
                    result.error = "Circuit breaker open"
                    break

                # Dry run check
                if self.config.dry_run:
                    logger.info("Dry run mode — skipping API call")
                    status = RalphStatus(
                        status=RalphLoopStatus.DRY_RUN,
                        work_type=WorkType.DRY_RUN,
                        loop_count=self.loop_count,
                        correlation_id=self.correlation_id,
                    )
                    await self.state_backend.write_status(status.to_dict())
                    result.status = status
                    break

                # Load task input
                task_input = TaskInput.from_ralph_dir(str(self.ralph_dir))
                if not task_input.prompt and not task_input.fix_plan:
                    logger.error("No PROMPT.md or fix_plan.md found")
                    result.error = "No task input found"
                    break

                # Execute one iteration
                iteration_status = await self.run_iteration(task_input)

                n_changed = len(self._last_iteration_files_changed)
                if _status_is_timeout(iteration_status) or _status_is_error(iteration_status):
                    self._no_file_change_streak = 0
                elif n_changed == 0:
                    self._no_file_change_streak += 1
                else:
                    self._no_file_change_streak = 0

                decomp = detect_decomposition_needed(
                    iteration_status,
                    self.config,
                    DecompositionContext(
                        iteration_files_changed=n_changed,
                        prior_iteration_was_timeout=self._prior_iteration_timeout,
                        complexity_band=task_input.complexity_band,
                        consecutive_no_progress=self._no_file_change_streak,
                    ),
                )
                if decomp.decompose:
                    logger.warning(
                        "Decomposition suggested [%s]: %s",
                        self.correlation_id,
                        decomp.recommendation,
                        extra={"correlation_id": self.correlation_id},
                    )
                    result.decomposition_hint = decomp

                self._prior_iteration_timeout = _status_is_timeout(iteration_status)

                self._cost_tracker.record_iteration_cost(
                    self.config.model,
                    self._last_tokens_in,
                    self._last_tokens_out,
                )

                stall_reason = await self._stall_detector.evaluate_after_iteration(
                    iteration_duration_sec=self._last_iteration_duration_sec,
                    files_changed_count=len(self._last_iteration_files_changed),
                    tests_status=iteration_status.tests_status,
                    timed_out=_status_is_timeout(iteration_status),
                    cli_had_error=_status_is_error(iteration_status),
                )
                if stall_reason:
                    logger.warning("Stall detector tripped: %s", stall_reason)
                    result.error = stall_reason
                    result.status = iteration_status
                    break

                # Check exit conditions (dual-condition gate)
                if await self.should_exit(iteration_status, self.loop_count):
                    logger.info("Exit conditions met after %d loops", self.loop_count)
                    result.status = iteration_status
                    break

                # Brief pause between iterations
                await asyncio.sleep(2)

        except KeyboardInterrupt:
            logger.info("Interrupted by user")
            result.error = "User interrupt"
        except Exception as e:
            logger.exception("Unexpected error in loop")
            result.error = str(e)
        finally:
            self._running = False
            result.loop_count = self.loop_count
            result.duration_seconds = time.time() - self.start_time
            result.tokens_in = self._last_tokens_in
            result.tokens_out = self._last_tokens_out
            result.files_changed = sorted(self._files_changed_session)
            result.session_cost_usd = self._cost_tracker.get_session_cost()

        return result

    async def run_iteration(
        self,
        task_input: TaskInput | None = None,
        system_prompt: str | None = None,
    ) -> RalphStatus:
        """Execute a single loop iteration via Claude Code CLI.

        Uses asyncio.create_subprocess_exec() with asyncio.wait_for() timeout.

        Args:
            task_input: Task input to process. Loads from .ralph/ if None.
            system_prompt: Optional system prompt passed through to Claude CLI
                via --system-prompt flag.
        """
        if task_input is None:
            task_input = TaskInput.from_ralph_dir(str(self.ralph_dir))

        iteration_t0 = time.monotonic()
        self._last_iteration_duration_sec = 0.0
        self._last_iteration_files_changed = []

        # Build the prompt for this iteration
        prompt = self._build_iteration_prompt(task_input)

        # Build Claude CLI command
        cmd = self._build_claude_command(prompt, system_prompt=system_prompt)

        logger.debug("Invoking: %s", " ".join(cmd[:5]) + "...")

        # Execute Claude CLI asynchronously
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.project_dir),
            )
            self._current_cli_proc = proc
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=self.config.timeout_minutes * 60,
                )
            finally:
                self._current_cli_proc = None

            stdout = stdout_bytes.decode("utf-8", errors="replace") if stdout_bytes else ""
            stderr = stderr_bytes.decode("utf-8", errors="replace") if stderr_bytes else ""
            returncode = proc.returncode or 0

            # Persist for cancel() / heartbeat consumers
            self._output_buffer = stdout

            # Increment call count
            await self._increment_call_count()

            # Parse response (also extracts session_id)
            status = self._parse_response(stdout, returncode)
            status.loop_count = self.loop_count
            status.session_id = self.session_id
            status.correlation_id = self.correlation_id
            await self.state_backend.write_status(status.to_dict())

            # Persist extracted session_id for continuity across restarts
            if self.session_id:
                await self._save_session()

            # Log output
            self._log_output(stdout, stderr, self.loop_count)

            self._last_iteration_duration_sec = time.monotonic() - iteration_t0
            changed = await self._git_changed_paths()
            self._last_iteration_files_changed = changed
            self._files_changed_session.update(changed)

            return status

        except TimeoutError:
            logger.warning("Claude CLI timed out after %d minutes", self.config.timeout_minutes)
            self._current_cli_proc = None
            # Kill the orphaned subprocess to prevent resource leaks
            try:
                proc.kill()
                await proc.wait()
            except Exception:
                pass
            status = RalphStatus(
                status=RalphLoopStatus.TIMEOUT,
                work_type="UNKNOWN",
                error=f"Timeout after {self.config.timeout_minutes} minutes",
                loop_count=self.loop_count,
            )
            await self.state_backend.write_status(status.to_dict())
            self._last_iteration_duration_sec = time.monotonic() - iteration_t0
            self._last_iteration_files_changed = []
            return status

        except FileNotFoundError:
            logger.error("Claude CLI not found: %s", self.config.claude_code_cmd)
            self._last_iteration_duration_sec = time.monotonic() - iteration_t0
            self._last_iteration_files_changed = []
            return RalphStatus(
                status=RalphLoopStatus.ERROR,
                error=f"Claude CLI not found: {self.config.claude_code_cmd}",
            )

    async def should_exit(self, status: RalphStatus, loop_count: int) -> bool:
        """Dual-condition exit gate (matching bash implementation).

        Requires BOTH:
        1. completion_indicators >= 2 (NLP heuristics)
        2. EXIT_SIGNAL: true (explicit from Claude)

        When there is productive work (files changed or completed_task set) but
        ``exit_signal`` is false, stale completion heuristics are cleared (CLI
        parity; evaluation §1.6).
        """
        productive = bool(
            len(self._last_iteration_files_changed) > 0 or status.completed_task.strip()
        )
        if not status.exit_signal and productive:
            self._completion_indicators = 0

        if status.exit_signal:
            self._completion_indicators += 1

        # Check for completion phrases in progress summary
        completion_phrases = [
            "all tasks complete",
            "all tasks done",
            "nothing left",
            "no remaining tasks",
            "work is complete",
            "all items checked",
        ]
        summary_lower = status.progress_summary.lower()
        if any(phrase in summary_lower for phrase in completion_phrases):
            self._completion_indicators += 1

        # Dual condition: need both indicators and explicit exit signal
        return self._completion_indicators >= 2 and status.exit_signal

    async def check_rate_limit(self) -> bool:
        """Check if within rate limits via state backend."""
        call_count = await self.state_backend.read_call_count()
        last_reset = await self.state_backend.read_last_reset()
        now = int(time.time())
        elapsed = now - last_reset if last_reset > 0 else 3600
        remaining = max(0, self.config.max_calls_per_hour - call_count)
        # If the hour has elapsed, we're not rate limited
        if elapsed >= 3600:
            return True
        return remaining > 0

    async def check_circuit_breaker(self) -> bool:
        """Check circuit breaker — returns True if OK to proceed."""
        return await self._circuit_breaker.can_proceed()

    # -------------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------------

    def _build_iteration_prompt(self, task_input: TaskInput) -> str:
        """Build the prompt for one iteration (matching bash PROMPT+fix_plan injection)."""
        parts = []
        if task_input.prompt:
            parts.append(task_input.prompt)
        if task_input.fix_plan:
            fix_body = task_input.fix_plan
            if self.config.progressive_context_enabled and fix_body.strip():
                fix_body = build_progressive_context(
                    fix_body, self.config.progressive_context_max_items
                )
            parts.append(f"\n\n## Current Fix Plan\n\n{fix_body}")
        if task_input.agent_instructions:
            parts.append(f"\n\n## Build/Run Instructions\n\n{task_input.agent_instructions}")
        return "\n".join(parts)

    def _build_claude_command(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> list[str]:
        """Build Claude CLI command (matching bash build_claude_command())."""
        cmd = [self.config.claude_code_cmd]

        # Agent mode (v1.0+)
        if self.config.use_agent:
            cmd.extend(["--agent", self.config.agent_name])

        # System prompt (for TheStudio DeveloperRoleConfig injection)
        if system_prompt:
            cmd.extend(["--system-prompt", system_prompt])

        # Prompt
        cmd.extend(["-p", prompt])

        # Output format
        cmd.extend(["--output-format", self.config.output_format])

        # Allowed tools
        if self.config.allowed_tools:
            cmd.extend(["--allowedTools", ",".join(self.config.allowed_tools)])

        # Session continuity
        if self.config.session_continuity and self.session_id:
            cmd.extend(["--continue", self.session_id])

        # Max turns
        cmd.extend(["--max-turns", str(self.config.max_turns)])

        return cmd

    def _parse_response(self, stdout: str, return_code: int) -> RalphStatus:
        """Parse Claude CLI response using 3-strategy chain (JSON block -> JSONL -> text).

        Delegates to ralph_sdk.parsing.parse_ralph_status for the actual parsing,
        with session_id extraction handled here.
        """
        status = RalphStatus()

        if return_code != 0:
            status.status = RalphLoopStatus.ERROR
            status.error = f"Claude CLI exited with code {return_code}"
            return status

        # Extract session_id from JSONL before parsing status
        self._extract_session_id(stdout)

        # Use the 3-strategy parse chain
        return parse_ralph_status(stdout)

    def _extract_session_id(self, stdout: str) -> None:
        """Extract session_id and token counts from JSONL result objects."""
        self._last_tokens_in = 0
        self._last_tokens_out = 0
        for line in reversed(stdout.strip().splitlines()):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if obj.get("type") == "result":
                    if "session_id" in obj:
                        self.session_id = obj["session_id"]
                    # Extract token usage from result message
                    self._last_tokens_in += obj.get("input_tokens", 0)
                    self._last_tokens_out += obj.get("output_tokens", 0)
                    return
            except json.JSONDecodeError:
                continue

    async def _git_changed_paths(self) -> list[str]:
        """List paths changed vs HEAD in project_dir (working tree)."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "git",
                "-C",
                str(self.project_dir),
                "diff",
                "--name-only",
                "HEAD",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30.0)
        except (FileNotFoundError, TimeoutError, OSError):
            return []
        if proc.returncode != 0:
            return []
        text = stdout.decode("utf-8", errors="replace").strip()
        if not text:
            return []
        return [p.strip() for p in text.splitlines() if p.strip()]

    async def _load_session(self) -> None:
        """Load session ID via state backend."""
        self.session_id = await self.state_backend.read_session_id()

    async def _save_session(self) -> None:
        """Save session ID via state backend."""
        await self.state_backend.write_session_id(self.session_id)

    async def _increment_call_count(self) -> None:
        """Increment API call counter via state backend (matching bash rate limiting)."""
        now = int(time.time())
        last_reset = await self.state_backend.read_last_reset()

        if now - last_reset >= 3600:
            # Reset counter
            await self.state_backend.write_call_count(1)
            await self.state_backend.write_last_reset(now)
        else:
            # Increment
            count = await self.state_backend.read_call_count()
            await self.state_backend.write_call_count(count + 1)

    def _log_output(self, stdout: str, stderr: str, loop_count: int) -> None:
        """Log Claude output to .ralph/logs/."""
        log_dir = self.ralph_dir / "logs"
        log_dir.mkdir(exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"claude_output_{loop_count:04d}_{timestamp}.log"
        try:
            with open(log_file, "w", encoding="utf-8") as f:
                f.write(f"=== Loop {loop_count} — {timestamp} ===\n")
                f.write(f"=== STDOUT ===\n{stdout}\n")
                if stderr:
                    f.write(f"=== STDERR ===\n{stderr}\n")
        except OSError:
            pass

    # -------------------------------------------------------------------------
    # TheStudio Adapter (SDK-3)
    # -------------------------------------------------------------------------

    async def process_task_packet(self, packet: dict[str, Any]) -> dict[str, Any]:
        """Process a TheStudio TaskPacket and return a Signal.

        Converts TaskPacket -> TaskInput, runs iteration, returns TaskResult as Signal.
        """
        task_input = TaskInput.from_task_packet(packet)
        status = await self.run_iteration(task_input)
        result = TaskResult(
            status=status,
            loop_count=self.loop_count,
            duration_seconds=time.time() - self.start_time if self.start_time else 0,
            files_changed=list(self._last_iteration_files_changed),
        )
        return result.to_signal()

    # -------------------------------------------------------------------------
    # Tool handlers (for Agent SDK tool registration)
    # -------------------------------------------------------------------------

    async def handle_tool_call(self, tool_name: str, tool_input: dict[str, Any]) -> dict[str, Any]:
        """Dispatch tool calls to appropriate async handlers."""
        if tool_name == "ralph_status":
            return await ralph_status_tool(ralph_dir=str(self.ralph_dir), **tool_input)
        elif tool_name == "ralph_rate_check":
            return await ralph_rate_check_tool(
                ralph_dir=str(self.ralph_dir),
                max_calls_per_hour=self.config.max_calls_per_hour,
            )
        elif tool_name == "ralph_circuit_state":
            return await ralph_circuit_state_tool(
                ralph_dir=str(self.ralph_dir),
            )
        elif tool_name == "ralph_task_update":
            return await ralph_task_update_tool(ralph_dir=str(self.ralph_dir), **tool_input)
        return {"ok": False, "error": f"Unknown tool: {tool_name}"}

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        """Return tool definitions for Agent SDK registration."""
        return [{k: v for k, v in tool.items() if k != "handler"} for tool in RALPH_TOOLS]
