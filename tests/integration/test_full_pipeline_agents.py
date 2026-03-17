"""Full pipeline integration test — all 8 agents use AgentRunner (Epic 23, Story 3.10).

Validates:
- All 8 agents share AgentRunner infrastructure
- All 8 agents have AgentConfig with correct pipeline_step
- All 8 agents have output schemas
- All 8 agents have fallback functions
- Feature flags control LLM enablement per agent
- All configs route through Model Gateway (pipeline_step maps to routing rule)
- All agents produce valid output via fallback (no LLM needed)
"""

import json

import pytest

from src.agent.framework import AgentConfig, AgentContext, AgentRunner


class TestAllAgentsShareFramework:
    """AC 31: All 8 agents use the same AgentRunner."""

    @pytest.fixture
    def all_configs(self) -> list[AgentConfig]:
        """Load all 8 agent configs."""
        from src.agent.primary_agent import _make_developer_config
        DEVELOPER_AGENT_CONFIG = _make_developer_config()
        from src.assembler.assembler_config import ASSEMBLER_AGENT_CONFIG
        from src.context.context_config import CONTEXT_AGENT_CONFIG
        from src.intake.intake_config import INTAKE_AGENT_CONFIG
        from src.intent.intent_config import INTENT_AGENT_CONFIG
        from src.qa.qa_config import QA_AGENT_CONFIG
        from src.recruiting.recruiter_config import RECRUITER_AGENT_CONFIG
        from src.routing.router_config import ROUTER_AGENT_CONFIG

        return [
            INTAKE_AGENT_CONFIG,
            CONTEXT_AGENT_CONFIG,
            INTENT_AGENT_CONFIG,
            ROUTER_AGENT_CONFIG,
            RECRUITER_AGENT_CONFIG,
            ASSEMBLER_AGENT_CONFIG,
            DEVELOPER_AGENT_CONFIG,
            QA_AGENT_CONFIG,
        ]

    def test_all_eight_configs_exist(self, all_configs: list[AgentConfig]) -> None:
        assert len(all_configs) == 8

    def test_all_are_agent_config(self, all_configs: list[AgentConfig]) -> None:
        for config in all_configs:
            assert isinstance(config, AgentConfig), f"{config.agent_name} is not AgentConfig"

    def test_all_have_unique_names(self, all_configs: list[AgentConfig]) -> None:
        names = [c.agent_name for c in all_configs]
        assert len(set(names)) == 8, f"Duplicate agent names: {names}"

    def test_all_have_pipeline_step(self, all_configs: list[AgentConfig]) -> None:
        """AC 32: All agents route through Model Gateway via pipeline_step."""
        for config in all_configs:
            assert config.pipeline_step, f"{config.agent_name} has no pipeline_step"

    def test_all_have_output_schema_except_primary(self, all_configs: list[AgentConfig]) -> None:
        """Non-primary agents have output schemas for structured parsing."""
        for config in all_configs:
            if config.pipeline_step == "primary_agent":
                continue  # Primary agent returns free-form text via tool loop
            assert config.output_schema is not None, (
                f"{config.agent_name} missing output_schema"
            )

    def test_all_completion_agents_have_fallback(self, all_configs: list[AgentConfig]) -> None:
        """AC 35: All completion-mode agents have rule-based fallback."""
        for config in all_configs:
            if config.pipeline_step == "primary_agent":
                continue  # Primary agent uses agentic mode, no fallback needed
            assert config.fallback_fn is not None, (
                f"{config.agent_name} missing fallback_fn"
            )

    def test_all_can_create_runner(self, all_configs: list[AgentConfig]) -> None:
        """All configs can instantiate an AgentRunner."""
        for config in all_configs:
            runner = AgentRunner(config)
            assert runner.config.agent_name == config.agent_name


class TestModelClassAssignments:
    """AC 32: Model class assignments match doc 26."""

    def test_intake_uses_fast(self) -> None:
        from src.intake.intake_config import INTAKE_AGENT_CONFIG
        assert INTAKE_AGENT_CONFIG.model_class == "fast"

    def test_context_uses_fast(self) -> None:
        from src.context.context_config import CONTEXT_AGENT_CONFIG
        assert CONTEXT_AGENT_CONFIG.model_class == "fast"

    def test_intent_uses_balanced(self) -> None:
        from src.intent.intent_config import INTENT_AGENT_CONFIG
        assert INTENT_AGENT_CONFIG.model_class == "balanced"

    def test_router_uses_balanced(self) -> None:
        from src.routing.router_config import ROUTER_AGENT_CONFIG
        assert ROUTER_AGENT_CONFIG.model_class == "balanced"

    def test_recruiter_uses_balanced(self) -> None:
        from src.recruiting.recruiter_config import RECRUITER_AGENT_CONFIG
        assert RECRUITER_AGENT_CONFIG.model_class == "balanced"

    def test_assembler_uses_balanced(self) -> None:
        from src.assembler.assembler_config import ASSEMBLER_AGENT_CONFIG
        assert ASSEMBLER_AGENT_CONFIG.model_class == "balanced"

    def test_qa_uses_balanced(self) -> None:
        from src.qa.qa_config import QA_AGENT_CONFIG
        assert QA_AGENT_CONFIG.model_class == "balanced"


class TestBudgetDefaults:
    """Budget defaults match Appendix C."""

    def test_intake_budget(self) -> None:
        from src.intake.intake_config import INTAKE_AGENT_CONFIG
        assert INTAKE_AGENT_CONFIG.max_budget_usd == 0.10

    def test_context_budget(self) -> None:
        from src.context.context_config import CONTEXT_AGENT_CONFIG
        assert CONTEXT_AGENT_CONFIG.max_budget_usd == 0.20

    def test_intent_budget(self) -> None:
        from src.intent.intent_config import INTENT_AGENT_CONFIG
        assert INTENT_AGENT_CONFIG.max_budget_usd == 0.50

    def test_router_budget(self) -> None:
        from src.routing.router_config import ROUTER_AGENT_CONFIG
        assert ROUTER_AGENT_CONFIG.max_budget_usd == 0.30

    def test_recruiter_budget(self) -> None:
        from src.recruiting.recruiter_config import RECRUITER_AGENT_CONFIG
        assert RECRUITER_AGENT_CONFIG.max_budget_usd == 0.30

    def test_assembler_budget(self) -> None:
        from src.assembler.assembler_config import ASSEMBLER_AGENT_CONFIG
        assert ASSEMBLER_AGENT_CONFIG.max_budget_usd == 0.50

    def test_qa_budget(self) -> None:
        from src.qa.qa_config import QA_AGENT_CONFIG
        assert QA_AGENT_CONFIG.max_budget_usd == 0.50


class TestCompletionVsAgenticMode:
    """AC 6: Two execution modes. Only Primary Agent uses agentic mode."""

    def test_intake_completion_mode(self) -> None:
        from src.intake.intake_config import INTAKE_AGENT_CONFIG
        assert INTAKE_AGENT_CONFIG.tool_allowlist == []

    def test_context_completion_mode(self) -> None:
        from src.context.context_config import CONTEXT_AGENT_CONFIG
        assert CONTEXT_AGENT_CONFIG.tool_allowlist == []

    def test_intent_completion_mode(self) -> None:
        from src.intent.intent_config import INTENT_AGENT_CONFIG
        assert INTENT_AGENT_CONFIG.tool_allowlist == []

    def test_router_completion_mode(self) -> None:
        from src.routing.router_config import ROUTER_AGENT_CONFIG
        assert ROUTER_AGENT_CONFIG.tool_allowlist == []

    def test_recruiter_completion_mode(self) -> None:
        from src.recruiting.recruiter_config import RECRUITER_AGENT_CONFIG
        assert RECRUITER_AGENT_CONFIG.tool_allowlist == []

    def test_assembler_completion_mode(self) -> None:
        from src.assembler.assembler_config import ASSEMBLER_AGENT_CONFIG
        assert ASSEMBLER_AGENT_CONFIG.tool_allowlist == []

    def test_qa_completion_mode(self) -> None:
        from src.qa.qa_config import QA_AGENT_CONFIG
        assert QA_AGENT_CONFIG.tool_allowlist == []

    def test_primary_agent_agentic_mode(self) -> None:
        from src.agent.primary_agent import _make_developer_config
        DEVELOPER_AGENT_CONFIG = _make_developer_config()
        assert len(DEVELOPER_AGENT_CONFIG.tool_allowlist) > 0


class TestFeatureFlags:
    """AC 37: Feature flags control LLM enablement per agent."""

    def test_settings_has_agent_llm_enabled(self) -> None:
        from src.settings import settings
        assert hasattr(settings, "agent_llm_enabled")

    def test_all_agents_in_flag_dict(self) -> None:
        from src.settings import settings
        # Feature flags keyed by descriptive name; primary_agent maps to
        # the developer agent (agent_name="developer", step="primary_agent")
        expected_flags = {
            "primary_agent", "intake_agent", "context_agent", "intent_agent",
            "router_agent", "recruiter_agent", "assembler_agent", "qa_agent",
        }
        actual_flags = set(settings.agent_llm_enabled.keys())
        assert expected_flags <= actual_flags, (
            f"Missing flags: {expected_flags - actual_flags}"
        )

    def test_all_disabled_by_default(self) -> None:
        """Default: all LLM disabled (safe fallback mode)."""
        from src.settings import settings
        for agent, enabled in settings.agent_llm_enabled.items():
            assert enabled is False, f"{agent} LLM should be disabled by default"


class TestFallbackProducesValidOutput:
    """AC 35: All fallback functions produce valid output."""

    def test_intake_fallback(self) -> None:
        from src.intake.intake_config import _intake_fallback
        ctx = AgentContext(
            issue_title="Test issue",
            issue_body="Test body",
            labels=["agent:run", "type:bug"],
            extra={"repo_registered": True, "repo_paused": False,
                   "has_active_workflow": False, "event_id": "test"},
        )
        result = _intake_fallback(ctx)
        data = json.loads(result)
        assert "accepted" in data

    def test_context_fallback(self) -> None:
        from src.context.context_config import _context_fallback
        ctx = AgentContext(issue_title="Test", issue_body="Test body")
        result = _context_fallback(ctx)
        data = json.loads(result)
        assert "scope_summary" in data

    def test_intent_fallback(self) -> None:
        from src.intent.intent_config import _intent_fallback
        ctx = AgentContext(issue_title="Add feature", issue_body="- [ ] Criterion 1")
        result = _intent_fallback(ctx)
        data = json.loads(result)
        assert "goal" in data
        assert "constraints" in data

    def test_router_fallback(self) -> None:
        from src.routing.router_config import _router_fallback
        ctx = AgentContext(
            risk_flags={},
            overlays=[],
            extra={"base_role": "developer"},
        )
        result = _router_fallback(ctx)
        data = json.loads(result)
        assert "selections" in data

    def test_recruiter_fallback(self) -> None:
        from src.recruiting.recruiter_config import _recruiter_fallback
        ctx = AgentContext(
            extra={"expert_class": "security", "capability_tags": ["auth"]},
        )
        result = _recruiter_fallback(ctx)
        data = json.loads(result)
        assert "expert_name" in data

    def test_assembler_fallback(self) -> None:
        from uuid import uuid4

        from src.assembler.assembler_config import _assembler_fallback
        ctx = AgentContext(
            taskpacket_id=uuid4(),
            correlation_id=uuid4(),
            expert_outputs=[],
            extra={"intent_constraints": [], "acceptance_criteria": [], "intent_version": 1},
        )
        result = _assembler_fallback(ctx)
        data = json.loads(result)
        assert "plan_steps" in data

    def test_qa_fallback(self) -> None:
        from src.qa.qa_config import _qa_fallback
        ctx = AgentContext(
            evidence={"test": "passed"},
            extra={"acceptance_criteria": ["Tests pass"], "qa_handoff": []},
        )
        result = _qa_fallback(ctx)
        data = json.loads(result)
        assert "criteria_results" in data
