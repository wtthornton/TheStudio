"""Tests for Model Gateway — routing, fallbacks, budgets, audit (Stories 7.4-7.5)."""

import pytest

from src.admin.model_gateway import (
    BudgetEnforcer,
    BudgetExceededError,
    BudgetSpec,
    ModelAuditStore,
    ModelCallAudit,
    ModelClass,
    ModelRouter,
    NoProviderAvailableError,
    ProviderConfig,
    RoutingRule,
)


@pytest.fixture
def router():
    return ModelRouter()


@pytest.fixture
def enforcer():
    return BudgetEnforcer()


@pytest.fixture
def audit_store():
    return ModelAuditStore()


class TestModelClass:
    def test_enum_values(self):
        assert ModelClass.FAST == "fast"
        assert ModelClass.BALANCED == "balanced"
        assert ModelClass.STRONG == "strong"


class TestProviderConfig:
    def test_to_dict(self):
        p = ProviderConfig("id-1", "anthropic", "claude-haiku", ModelClass.FAST, 0.001)
        d = p.to_dict()
        assert d["provider_id"] == "id-1"
        assert d["model_class"] == "fast"
        assert d["enabled"] is True


class TestRoutingRule:
    def test_to_dict(self):
        r = RoutingRule("intake", ModelClass.FAST, overlay_overrides={"security": ModelClass.STRONG})
        d = r.to_dict()
        assert d["step"] == "intake"
        assert d["overlay_overrides"]["security"] == "strong"


class TestModelRouter:
    def test_default_routing_intake_is_fast(self, router):
        cls = router.resolve_class("intake")
        assert cls == ModelClass.FAST

    def test_default_routing_context_is_fast(self, router):
        cls = router.resolve_class("context")
        assert cls == ModelClass.FAST

    def test_default_routing_intent_is_balanced(self, router):
        cls = router.resolve_class("intent")
        assert cls == ModelClass.BALANCED

    def test_default_routing_primary_agent_is_balanced(self, router):
        cls = router.resolve_class("primary_agent")
        assert cls == ModelClass.BALANCED

    def test_overlay_escalates_to_strong(self, router):
        cls = router.resolve_class("intent", overlays=["security"])
        assert cls == ModelClass.STRONG

    def test_tier_override_escalates(self, router):
        cls = router.resolve_class("primary_agent", repo_tier="execute")
        assert cls == ModelClass.STRONG

    def test_unknown_step_returns_balanced(self, router):
        cls = router.resolve_class("unknown_step")
        assert cls == ModelClass.BALANCED

    def test_select_model_returns_provider(self, router):
        provider = router.select_model("intake")
        assert provider.model_class == ModelClass.FAST
        assert provider.enabled is True

    def test_select_model_high_complexity_escalates(self, router):
        provider = router.select_model("intake", complexity="high")
        assert provider.model_class == ModelClass.STRONG

    def test_select_with_fallback_no_failure(self, router):
        provider, chain = router.select_with_fallback("intake")
        assert provider.model_class == ModelClass.FAST
        assert chain == []

    def test_select_with_fallback_escalates(self, router):
        # Disable the fast provider
        router.set_provider_enabled("fast-default", False)
        provider, chain = router.select_with_fallback("intake")
        assert provider.model_class == ModelClass.BALANCED
        assert any("escalated" in c for c in chain)

    def test_select_with_fallback_all_exhausted(self):
        providers = [
            ProviderConfig("p1", "x", "m1", ModelClass.FAST, 0.001, enabled=False),
            ProviderConfig("p2", "x", "m2", ModelClass.BALANCED, 0.003, enabled=False),
            ProviderConfig("p3", "x", "m3", ModelClass.STRONG, 0.015, enabled=False),
        ]
        r = ModelRouter(providers=providers)
        with pytest.raises(NoProviderAvailableError):
            r.select_with_fallback("intake")

    def test_select_with_failed_providers(self, router):
        provider, chain = router.select_with_fallback("intake", failed_providers=["fast-default"])
        # Should escalate since fast is "failed"
        assert provider.model_class == ModelClass.BALANCED

    def test_providers_list(self, router):
        assert len(router.providers) == 3

    def test_rules_list(self, router):
        assert len(router.rules) == 7

    def test_set_provider_enabled(self, router):
        p = router.set_provider_enabled("fast-default", False)
        assert p.enabled is False
        p = router.set_provider_enabled("fast-default", True)
        assert p.enabled is True

    def test_set_provider_not_found(self, router):
        with pytest.raises(KeyError):
            router.set_provider_enabled("nonexistent", False)

    def test_get_provider(self, router):
        p = router.get_provider("fast-default")
        assert p is not None
        assert p.provider_id == "fast-default"

    def test_get_provider_not_found(self, router):
        assert router.get_provider("nonexistent") is None

    def test_multiple_overlays_takes_highest(self, router):
        # intent with security overlay -> STRONG
        cls = router.resolve_class("intent", overlays=["security", "compliance"])
        assert cls == ModelClass.STRONG


class TestCostOptimizationRouting:
    """Epic 32: Cost optimization routing feature flag tests."""

    def test_routing_flag_off_by_default(self):
        """When cost_routing_enabled=False, routing stays BALANCED."""
        router = ModelRouter(cost_routing_enabled=False)
        cls = router.resolve_class("routing")
        assert cls == ModelClass.BALANCED

    def test_routing_flag_on_downgrades_routing(self):
        """When cost_routing_enabled=True, routing drops to FAST."""
        router = ModelRouter(cost_routing_enabled=True)
        cls = router.resolve_class("routing")
        assert cls == ModelClass.FAST

    def test_routing_flag_on_downgrades_assembler(self):
        """When cost_routing_enabled=True, assembler drops to FAST."""
        router = ModelRouter(cost_routing_enabled=True)
        cls = router.resolve_class("assembler")
        assert cls == ModelClass.FAST

    def test_routing_flag_preserves_security_overlay(self):
        """Security overlay still escalates to STRONG even with cost routing on."""
        router = ModelRouter(cost_routing_enabled=True)
        cls = router.resolve_class("assembler", overlays=["security"])
        assert cls == ModelClass.STRONG

    def test_routing_flag_does_not_affect_intent(self):
        """Intent is not in the cost-optimized list — stays BALANCED."""
        router = ModelRouter(cost_routing_enabled=True)
        cls = router.resolve_class("intent")
        assert cls == ModelClass.BALANCED

    def test_routing_flag_does_not_affect_primary_agent(self):
        """Primary agent is not in the cost-optimized list."""
        router = ModelRouter(cost_routing_enabled=True)
        cls = router.resolve_class("primary_agent")
        assert cls == ModelClass.BALANCED

    def test_routing_flag_does_not_affect_qa(self):
        """QA eval is not in the cost-optimized list."""
        router = ModelRouter(cost_routing_enabled=True)
        cls = router.resolve_class("qa_eval")
        assert cls == ModelClass.BALANCED

    def test_intake_and_context_already_fast(self):
        """Intake and context are already FAST — flag makes no difference."""
        router_off = ModelRouter(cost_routing_enabled=False)
        router_on = ModelRouter(cost_routing_enabled=True)
        for step in ("intake", "context"):
            assert router_off.resolve_class(step) == ModelClass.FAST
            assert router_on.resolve_class(step) == ModelClass.FAST

    def test_select_model_with_cost_routing(self):
        """select_model returns FAST provider when cost routing is on."""
        router = ModelRouter(cost_routing_enabled=True)
        provider = router.select_model("routing")
        assert provider.model_class == ModelClass.FAST

    def test_tier_override_still_escalates_with_cost_routing(self):
        """Tier overrides still escalate even when cost routing is on."""
        router = ModelRouter(cost_routing_enabled=True)
        cls = router.resolve_class("primary_agent", repo_tier="execute")
        assert cls == ModelClass.STRONG


class TestBudgetEnforcer:
    def test_default_budget(self, enforcer):
        budget = enforcer.get_budget("any-repo")
        assert budget.per_task_max_spend == 1.0
        assert budget.per_step_token_cap == 50_000

    def test_set_and_get_budget(self, enforcer):
        enforcer.set_budget("repo-1", BudgetSpec(per_task_max_spend=5.0))
        budget = enforcer.get_budget("repo-1")
        assert budget.per_task_max_spend == 5.0

    def test_check_budget_ok(self, enforcer):
        assert enforcer.check_budget("task-1") is True

    def test_record_spend(self, enforcer):
        enforcer.record_spend("task-1", "intent", 0.5, 1000)
        assert enforcer.get_task_spend("task-1") == 0.5

    def test_record_spend_exceeds_budget(self, enforcer):
        enforcer.set_budget("repo-1", BudgetSpec(per_task_max_spend=0.10))
        enforcer.record_spend("task-1", "intent", 0.05, 500, repo_id="repo-1")
        with pytest.raises(BudgetExceededError) as exc_info:
            enforcer.record_spend("task-1", "intent", 0.10, 500, repo_id="repo-1")
        assert exc_info.value.task_id == "task-1"

    def test_record_spend_exceeds_token_cap(self, enforcer):
        enforcer.set_budget("repo-1", BudgetSpec(per_step_token_cap=100))
        with pytest.raises(BudgetExceededError):
            enforcer.record_spend("task-1", "intent", 0.01, 200, repo_id="repo-1")

    def test_conservative_mode(self, enforcer):
        budget = BudgetSpec(conservative_mode=True)
        enforcer.set_budget("repo-1", budget)
        assert enforcer.get_budget("repo-1").conservative_mode is True

    def test_clear(self, enforcer):
        enforcer.record_spend("task-1", "intent", 0.5, 1000)
        enforcer.clear()
        assert enforcer.get_task_spend("task-1") == 0.0

    def test_budget_spec_to_dict(self):
        b = BudgetSpec(per_task_max_spend=2.0, conservative_mode=True)
        d = b.to_dict()
        assert d["per_task_max_spend"] == 2.0
        assert d["conservative_mode"] is True


class TestModelAuditStore:
    def test_record_and_query(self, audit_store):
        audit = ModelCallAudit(step="intake", provider="anthropic", model="haiku")
        audit_store.record(audit)
        results = audit_store.query()
        assert len(results) == 1
        assert results[0].step == "intake"

    def test_query_by_step(self, audit_store):
        audit_store.record(ModelCallAudit(step="intake", provider="a"))
        audit_store.record(ModelCallAudit(step="intent", provider="b"))
        results = audit_store.query(step="intent")
        assert len(results) == 1
        assert results[0].step == "intent"

    def test_query_by_provider(self, audit_store):
        audit_store.record(ModelCallAudit(step="intake", provider="a"))
        audit_store.record(ModelCallAudit(step="intake", provider="b"))
        results = audit_store.query(provider="b")
        assert len(results) == 1

    def test_query_limit(self, audit_store):
        for i in range(20):
            audit_store.record(ModelCallAudit(step=f"step-{i}"))
        results = audit_store.query(limit=5)
        assert len(results) == 5

    def test_audit_to_dict(self):
        a = ModelCallAudit(step="intake", cost=0.001234, latency_ms=150.5)
        d = a.to_dict()
        assert d["step"] == "intake"
        assert d["cost"] == 0.001234
        assert d["latency_ms"] == 150.5

    def test_audit_cache_fields_default_zero(self):
        a = ModelCallAudit(step="intent")
        assert a.cache_creation_tokens == 0
        assert a.cache_read_tokens == 0

    def test_audit_cache_fields_in_dict(self):
        a = ModelCallAudit(
            step="intent",
            cache_creation_tokens=1500,
            cache_read_tokens=1200,
        )
        d = a.to_dict()
        assert d["cache_creation_tokens"] == 1500
        assert d["cache_read_tokens"] == 1200

    def test_audit_batch_field_default_false(self):
        a = ModelCallAudit(step="context")
        assert a.batch is False

    def test_audit_batch_field_in_dict(self):
        a = ModelCallAudit(step="context", batch=True)
        d = a.to_dict()
        assert d["batch"] is True

    def test_audit_repo_field_in_dict(self):
        a = ModelCallAudit(step="context", repo="org/repo")
        d = a.to_dict()
        assert d["repo"] == "org/repo"

    def test_clear(self, audit_store):
        audit_store.record(ModelCallAudit(step="x"))
        audit_store.clear()
        assert len(audit_store.query()) == 0
