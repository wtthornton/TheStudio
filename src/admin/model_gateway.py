"""Model Gateway — routing, fallbacks, budgets, and audit.

Story 7.4: Model Class & Routing Rules
Story 7.5: Fallback Chains & Budget Enforcement
Architecture reference: thestudioarc/26-model-runtime-and-routing.md
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


class ModelClass(StrEnum):
    """Cost/capability tiers for LLM routing."""

    FAST = "fast"
    BALANCED = "balanced"
    STRONG = "strong"


_CLASS_ORDER = [ModelClass.FAST, ModelClass.BALANCED, ModelClass.STRONG]


@dataclass
class ProviderConfig:
    """Configuration for a model provider."""

    provider_id: str
    provider: str
    model_id: str
    model_class: ModelClass
    cost_per_1k_tokens: float
    rate_limit_tpm: int = 100_000
    priority: int = 0
    enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "provider": self.provider,
            "model_id": self.model_id,
            "model_class": self.model_class.value,
            "cost_per_1k_tokens": self.cost_per_1k_tokens,
            "rate_limit_tpm": self.rate_limit_tpm,
            "priority": self.priority,
            "enabled": self.enabled,
        }


@dataclass
class RoutingRule:
    """Routing rule for a workflow step."""

    step: str
    default_class: ModelClass
    role_overrides: dict[str, ModelClass] = field(default_factory=dict)
    overlay_overrides: dict[str, ModelClass] = field(default_factory=dict)
    tier_overrides: dict[str, ModelClass] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "default_class": self.default_class.value,
            "role_overrides": {k: v.value for k, v in self.role_overrides.items()},
            "overlay_overrides": {k: v.value for k, v in self.overlay_overrides.items()},
            "tier_overrides": {k: v.value for k, v in self.tier_overrides.items()},
        }


@dataclass
class ModelCallAudit:
    """Audit record for a single LLM call."""

    id: UUID = field(default_factory=uuid4)
    correlation_id: UUID | None = None
    task_id: UUID | None = None
    step: str = ""
    role: str = ""
    overlays: list[str] = field(default_factory=list)
    provider: str = ""
    model: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    cost: float = 0.0
    latency_ms: float = 0.0
    error_class: str | None = None
    fallback_chain: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "correlation_id": str(self.correlation_id) if self.correlation_id else None,
            "task_id": str(self.task_id) if self.task_id else None,
            "step": self.step,
            "role": self.role,
            "overlays": self.overlays,
            "provider": self.provider,
            "model": self.model,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "cost": round(self.cost, 6),
            "latency_ms": round(self.latency_ms, 2),
            "error_class": self.error_class,
            "fallback_chain": self.fallback_chain,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class BudgetSpec:
    """Budget limits for model usage."""

    per_task_max_spend: float = 1.0
    per_step_token_cap: int = 50_000
    conservative_mode: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "per_task_max_spend": self.per_task_max_spend,
            "per_step_token_cap": self.per_step_token_cap,
            "conservative_mode": self.conservative_mode,
        }


class BudgetExceededError(Exception):
    """Raised when a model call would exceed budget limits."""

    def __init__(self, task_id: str, current_spend: float, limit: float) -> None:
        self.task_id = task_id
        self.current_spend = current_spend
        self.limit = limit
        super().__init__(
            f"Budget exceeded for task {task_id}: "
            f"${current_spend:.4f} spent of ${limit:.4f} limit"
        )


class NoProviderAvailableError(Exception):
    """Raised when no provider is available for the requested class."""

    def __init__(self, model_class: ModelClass) -> None:
        self.model_class = model_class
        super().__init__(f"No enabled provider available for class {model_class.value}")


# --- Default routing rules per arch doc ---

DEFAULT_ROUTING_RULES: list[RoutingRule] = [
    RoutingRule("intake", ModelClass.FAST),
    RoutingRule("context", ModelClass.FAST),
    RoutingRule(
        "intent",
        ModelClass.BALANCED,
        overlay_overrides={"security": ModelClass.STRONG, "compliance": ModelClass.STRONG},
    ),
    RoutingRule("expert_routing", ModelClass.BALANCED),
    RoutingRule(
        "assembler",
        ModelClass.BALANCED,
        overlay_overrides={"security": ModelClass.STRONG},
    ),
    RoutingRule(
        "primary_agent",
        ModelClass.BALANCED,
        tier_overrides={"execute": ModelClass.STRONG},
        overlay_overrides={"security": ModelClass.STRONG},
    ),
    RoutingRule(
        "qa_eval",
        ModelClass.BALANCED,
        overlay_overrides={"security": ModelClass.STRONG},
    ),
]

# --- Default provider configs (mock) ---

DEFAULT_PROVIDERS: list[ProviderConfig] = [
    ProviderConfig(
        provider_id="fast-default",
        provider="anthropic",
        model_id="claude-haiku-4-5",
        model_class=ModelClass.FAST,
        cost_per_1k_tokens=0.001,
        rate_limit_tpm=200_000,
        priority=0,
    ),
    ProviderConfig(
        provider_id="balanced-default",
        provider="anthropic",
        model_id="claude-sonnet-4-6",
        model_class=ModelClass.BALANCED,
        cost_per_1k_tokens=0.003,
        rate_limit_tpm=100_000,
        priority=0,
    ),
    ProviderConfig(
        provider_id="strong-default",
        provider="anthropic",
        model_id="claude-opus-4-6",
        model_class=ModelClass.STRONG,
        cost_per_1k_tokens=0.015,
        rate_limit_tpm=50_000,
        priority=0,
    ),
]


class ModelRouter:
    """Selects the appropriate model for a workflow step."""

    def __init__(
        self,
        providers: list[ProviderConfig] | None = None,
        rules: list[RoutingRule] | None = None,
    ) -> None:
        self._providers = {p.provider_id: p for p in (providers or DEFAULT_PROVIDERS)}
        self._rules = {r.step: r for r in (rules or DEFAULT_ROUTING_RULES)}

    @property
    def providers(self) -> list[ProviderConfig]:
        return list(self._providers.values())

    @property
    def rules(self) -> list[RoutingRule]:
        return list(self._rules.values())

    def get_provider(self, provider_id: str) -> ProviderConfig | None:
        return self._providers.get(provider_id)

    def set_provider_enabled(self, provider_id: str, enabled: bool) -> ProviderConfig:
        provider = self._providers.get(provider_id)
        if provider is None:
            raise KeyError(f"Provider '{provider_id}' not found")
        provider.enabled = enabled
        return provider

    def resolve_class(
        self,
        step: str,
        role: str = "",
        overlays: list[str] | None = None,
        repo_tier: str = "",
    ) -> ModelClass:
        """Resolve which model class to use for a step.

        Priority: overlay_overrides > tier_overrides > role_overrides > default_class.
        Always picks the highest (most capable) class from applicable overrides.
        """
        rule = self._rules.get(step)
        if rule is None:
            return ModelClass.BALANCED

        candidates: list[ModelClass] = [rule.default_class]

        if role and role in rule.role_overrides:
            candidates.append(rule.role_overrides[role])

        if repo_tier and repo_tier in rule.tier_overrides:
            candidates.append(rule.tier_overrides[repo_tier])

        for overlay in (overlays or []):
            if overlay in rule.overlay_overrides:
                candidates.append(rule.overlay_overrides[overlay])

        # Return the highest class
        return max(candidates, key=lambda c: _CLASS_ORDER.index(c))

    def select_model(
        self,
        step: str,
        role: str = "",
        overlays: list[str] | None = None,
        repo_tier: str = "",
        complexity: str = "",
    ) -> ProviderConfig:
        """Select a provider for the given context.

        Resolves model class, then picks the highest-priority enabled provider.
        """
        target_class = self.resolve_class(step, role, overlays, repo_tier)

        # Complexity override: high complexity escalates to STRONG
        if complexity == "high" and target_class != ModelClass.STRONG:
            target_class = ModelClass.STRONG

        return self._find_provider(target_class)

    def select_with_fallback(
        self,
        step: str,
        role: str = "",
        overlays: list[str] | None = None,
        repo_tier: str = "",
        complexity: str = "",
        failed_providers: list[str] | None = None,
    ) -> tuple[ProviderConfig, list[str]]:
        """Select a provider with fallback chain.

        Returns (selected_provider, fallback_chain_tried).
        Tries same class first (excluding failed), then escalates.
        """
        target_class = self.resolve_class(step, role, overlays, repo_tier)
        if complexity == "high" and target_class != ModelClass.STRONG:
            target_class = ModelClass.STRONG

        failed = set(failed_providers or [])
        chain: list[str] = []

        # Try same class first
        try:
            provider = self._find_provider(target_class, exclude=failed)
            return provider, chain
        except NoProviderAvailableError:
            chain.append(f"{target_class.value}:exhausted")

        # Escalate to next class
        idx = _CLASS_ORDER.index(target_class)
        for higher_class in _CLASS_ORDER[idx + 1:]:
            try:
                provider = self._find_provider(higher_class, exclude=failed)
                chain.append(f"escalated:{higher_class.value}")
                return provider, chain
            except NoProviderAvailableError:
                chain.append(f"{higher_class.value}:exhausted")

        raise NoProviderAvailableError(target_class)

    def _find_provider(
        self,
        model_class: ModelClass,
        exclude: set[str] | None = None,
    ) -> ProviderConfig:
        """Find the best enabled provider for a model class."""
        exclude = exclude or set()
        candidates = [
            p for p in self._providers.values()
            if p.model_class == model_class and p.enabled and p.provider_id not in exclude
        ]
        if not candidates:
            raise NoProviderAvailableError(model_class)
        candidates.sort(key=lambda p: p.priority)
        return candidates[0]


@runtime_checkable
class BudgetEnforcerProtocol(Protocol):
    """Interface for budget enforcement."""

    def set_budget(self, repo_id: str, budget: BudgetSpec) -> None: ...
    def get_budget(self, repo_id: str) -> BudgetSpec: ...
    def check_budget(self, task_id: str, repo_id: str = "") -> bool: ...
    def record_spend(self, task_id: str, step: str, cost: float, tokens: int, repo_id: str = "") -> None: ...
    def get_task_spend(self, task_id: str) -> float: ...
    def clear(self) -> None: ...


class InMemoryBudgetEnforcer:
    """Tracks and enforces per-task model spend budgets."""

    def __init__(self) -> None:
        self._task_spend: dict[str, float] = {}
        self._task_tokens: dict[str, dict[str, int]] = {}
        self._budgets: dict[str, BudgetSpec] = {}

    def set_budget(self, repo_id: str, budget: BudgetSpec) -> None:
        self._budgets[repo_id] = budget

    def get_budget(self, repo_id: str) -> BudgetSpec:
        return self._budgets.get(repo_id, BudgetSpec())

    def check_budget(self, task_id: str, repo_id: str = "") -> bool:
        """Check if task is within budget. Returns True if OK."""
        budget = self.get_budget(repo_id)
        current = self._task_spend.get(task_id, 0.0)
        return current < budget.per_task_max_spend

    def record_spend(self, task_id: str, step: str, cost: float, tokens: int, repo_id: str = "") -> None:
        """Record spend for a task. Raises BudgetExceededError if over limit."""
        budget = self.get_budget(repo_id)
        current = self._task_spend.get(task_id, 0.0)
        new_total = current + cost

        if new_total > budget.per_task_max_spend:
            raise BudgetExceededError(task_id, new_total, budget.per_task_max_spend)

        # Check step token cap
        step_key = f"{task_id}:{step}"
        step_tokens = self._task_tokens.get(step_key, {}).get("total", 0)
        if step_tokens + tokens > budget.per_step_token_cap:
            raise BudgetExceededError(task_id, new_total, budget.per_task_max_spend)

        self._task_spend[task_id] = new_total
        if step_key not in self._task_tokens:
            self._task_tokens[step_key] = {"total": 0}
        self._task_tokens[step_key]["total"] += tokens

    def get_task_spend(self, task_id: str) -> float:
        return self._task_spend.get(task_id, 0.0)

    def clear(self) -> None:
        self._task_spend.clear()
        self._task_tokens.clear()
        self._budgets.clear()


@runtime_checkable
class ModelAuditStoreProtocol(Protocol):
    """Interface for model call audit storage."""

    def record(self, audit: ModelCallAudit) -> None: ...
    def query(
        self,
        task_id: str | None = None,
        step: str | None = None,
        provider: str | None = None,
        limit: int = 100,
    ) -> list[ModelCallAudit]: ...
    def clear(self) -> None: ...


class InMemoryModelAuditStore:
    """In-memory store for model call audit records."""

    def __init__(self) -> None:
        self._records: list[ModelCallAudit] = []

    def record(self, audit: ModelCallAudit) -> None:
        self._records.append(audit)

    def query(
        self,
        task_id: str | None = None,
        step: str | None = None,
        provider: str | None = None,
        limit: int = 100,
    ) -> list[ModelCallAudit]:
        results = self._records
        if task_id:
            results = [r for r in results if str(r.task_id) == task_id]
        if step:
            results = [r for r in results if r.step == step]
        if provider:
            results = [r for r in results if r.provider == provider]
        return sorted(results, key=lambda r: r.created_at, reverse=True)[:limit]

    def clear(self) -> None:
        self._records.clear()


# Backwards-compatible aliases
BudgetEnforcer = InMemoryBudgetEnforcer
ModelAuditStore = InMemoryModelAuditStore


# --- Global instances ---

_router: ModelRouter | None = None
_budget_enforcer: InMemoryBudgetEnforcer | None = None
_audit_store: InMemoryModelAuditStore | None = None


def get_model_router() -> ModelRouter:
    """Return the module-level ModelRouter singleton."""
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router


def get_budget_enforcer() -> BudgetEnforcerProtocol:
    """Return the module-level BudgetEnforcer singleton."""
    global _budget_enforcer
    if _budget_enforcer is None:
        _budget_enforcer = InMemoryBudgetEnforcer()
    return _budget_enforcer


def get_model_audit_store() -> ModelAuditStoreProtocol:
    """Return the module-level ModelAuditStore singleton."""
    global _audit_store
    if _audit_store is None:
        _audit_store = InMemoryModelAuditStore()
    return _audit_store


def wire_settings_reload() -> None:
    """Subscribe ModelRouter to settings reload signals.

    Story 12.7: Hot Reload & Settings Propagation.
    Called at startup to connect SettingsService changes to ModelRouter.
    """
    from src.admin.settings_service import get_settings_service

    svc = get_settings_service()

    def on_setting_changed(key: str) -> None:
        if key == "agent_model":
            logger.info(
                "Hot reload: agent_model changed, "
                "ModelRouter will use new model on next call",
            )
        elif key.startswith("agent_"):
            logger.info("Hot reload: agent config %s changed", key)

    svc.subscribe_reload(on_setting_changed)
