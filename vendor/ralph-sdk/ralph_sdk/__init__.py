"""Ralph SDK — Agent SDK integration for Ralph autonomous development loop.

Provides dual-mode operation: standalone CLI + TheStudio embedded.
"""

__version__ = "2.0.2"

from ralph_sdk.agent import CancelResult, RalphAgent, TaskInput, TaskResult
from ralph_sdk.config import RalphConfig
from ralph_sdk.converters import (
    ComplexityBand,
    IntentSpecInput,
    RiskFlag,
    TaskPacketInput,
    TrustTier,
)
from ralph_sdk.cost_tracking import BudgetCheckResult, BudgetLevel, CostTracker
from ralph_sdk.decomposition import (
    DecompositionContext,
    DecompositionHint,
    detect_decomposition_needed,
)
from ralph_sdk.state import FileStateBackend, NullStateBackend, RalphStateBackend
from ralph_sdk.status import (
    CircuitBreakerState,
    CircuitBreakerStateEnum,
    RalphLoopStatus,
    RalphStatus,
    WorkType,
)
from ralph_sdk.tools import (
    ralph_circuit_state_tool,
    ralph_rate_check_tool,
    ralph_status_tool,
    ralph_task_update_tool,
)

__all__ = [
    "BudgetCheckResult",
    "BudgetLevel",
    "CancelResult",
    "CircuitBreakerState",
    "CircuitBreakerStateEnum",
    "ComplexityBand",
    "CostTracker",
    "DecompositionContext",
    "DecompositionHint",
    "FileStateBackend",
    "IntentSpecInput",
    "NullStateBackend",
    "RalphAgent",
    "RalphConfig",
    "RalphLoopStatus",
    "RalphStateBackend",
    "RalphStatus",
    "RiskFlag",
    "TaskInput",
    "TaskPacketInput",
    "TaskResult",
    "TrustTier",
    "WorkType",
    "detect_decomposition_needed",
    "ralph_circuit_state_tool",
    "ralph_rate_check_tool",
    "ralph_status_tool",
    "ralph_task_update_tool",
]
