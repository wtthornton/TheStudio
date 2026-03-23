from pydantic import model_validator
from pydantic_settings import BaseSettings

_PLACEHOLDER_KEY = "generate-a-real-fernet-key-for-production"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = {"env_prefix": "THESTUDIO_"}

    database_url: str = "postgresql+asyncpg://thestudio:thestudio_dev@localhost:5434/thestudio"
    temporal_host: str = "localhost:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "thestudio-main"
    nats_url: str = "nats://localhost:4222"
    encryption_key: str = _PLACEHOLDER_KEY

    otel_service_name: str = "thestudio"
    otel_exporter: str = "console"  # "console" or "otlp"
    otel_otlp_endpoint: str = "http://localhost:4317"

    # Primary Agent (Story 0.5)
    anthropic_api_key: str = ""
    anthropic_auth_mode: str = "auto"  # "auto", "api_key", "oauth" (Epic 31)
    anthropic_refresh_token: str = ""  # OAuth refresh token (sk-ant-ort01-...)
    anthropic_oauth_client_id: str = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"  # Anthropic default
    agent_model: str = "claude-sonnet-4-5"
    agent_max_turns: int = 30
    agent_max_budget_usd: float = 5.0
    agent_max_loopbacks: int = 2

    # Publisher (Story 0.7)
    github_app_id: str = ""
    github_private_key_path: str = ""

    # Webhook (Admin)
    webhook_secret: str = ""

    # Poll intake (Epic 17 — Poll for Issues as Backup to Webhooks)
    intake_poll_enabled: bool = False
    intake_poll_interval_minutes: int = 10
    intake_poll_token: str = ""  # PAT or installation token for GitHub API

    # Agent LLM feature flags (Epic 23 — per-agent toggle)
    # When False, agent uses rule-based fallback instead of LLM
    # Note: "developer" is the runtime agent_name for PrimaryAgentRunner
    # (distinct from the settings key "primary_agent" for documentation).
    agent_llm_enabled: dict[str, bool] = {
        "primary_agent": False,
        "developer": False,
        "intake_agent": False,
        "context_agent": False,
        "intent_agent": False,
        "router_agent": False,
        "recruiter_agent": False,
        "assembler_agent": False,
        "qa_agent": False,
        "preflight_agent": False,
    }

    # Preflight plan review gate (Epic 28)
    preflight_enabled: bool = False  # Feature flag — off by default
    preflight_tiers: list[str] = ["execute"]  # Only run for these trust tiers

    # GitHub Projects v2 integration (Epic 29)
    projects_v2_enabled: bool = False  # Feature flag — off by default (AC 7)
    projects_v2_owner: str = ""  # GitHub org or user that owns the project
    projects_v2_number: int = 0  # Project number (visible in URL)
    projects_v2_token: str = ""  # Installation token (falls back to github_app_id)

    # GitHub Projects v2 sync behaviors (Epic 38.16 — configurable via dashboard)
    projects_sync_auto_add: bool = True  # Auto-add new TaskPackets to the project board
    projects_sync_auto_close: bool = False  # Close GitHub issues when pipeline completes
    projects_sync_respect_manual_overrides: bool = True  # Skip pipeline sync if user manually set a field

    # Meridian portfolio review (Epic 29 Sprint 2)
    meridian_portfolio_enabled: bool = False  # Feature flag — off by default (AC 18)
    meridian_portfolio_github_issue: bool = False  # Post review to pinned issue (AC 17)
    meridian_portfolio_repo: str = ""  # Repo for health report issue
    meridian_thresholds: dict[str, float] = {
        "blocked_ratio": 0.20,
        "high_risk_concurrent": 3,
        "review_stale_hours": 48,
        "repo_concentration": 0.50,
        "failure_rate": 0.30,
        "queued_stale_days": 7,
    }

    # Feature flags (Epic 8 Sprint 2)
    llm_provider: str = "mock"  # "mock" or "anthropic"
    github_provider: str = "mock"  # "mock" or "real"
    store_backend: str = "memory"  # "memory" or "postgres"

    # Cost optimization (Epic 32)
    cost_optimization_routing_enabled: bool = False  # Route cheap agents to FAST
    cost_optimization_caching_enabled: bool = False  # Prompt caching headers
    cost_optimization_batch_enabled: bool = False  # Batch API for async agents
    cost_optimization_budget_tiers: dict[str, float] = {
        "observe": 2.00,
        "suggest": 5.00,
        "execute": 8.00,
    }

    # Approval auto-bypass (Story 30.14)
    approval_auto_bypass: bool = False  # Skip approval gate for ALL tiers when True

    # Triage mode (Epic 36 — Planning Experience)
    triage_mode_enabled: bool = False  # When True, webhooks create TRIAGE instead of RECEIVED
    intent_review_enabled: bool = False  # When True, workflow pauses after Intent stage
    routing_review_enabled: bool = False  # When True, workflow pauses after Router stage
    max_intent_versions: int = 10  # Cap on intent spec versions per workflow (was 2)

    # Pipeline Comments (Epic 38 Slice 4, Story 38.23)
    # Posts a live status comment on the GitHub issue at each stage transition.
    pipeline_comments_enabled: bool = False  # Feature flag — off by default
    pipeline_webhook_bridge_enabled: bool = False  # Publish PR/issue events to NATS (38.24)

    # Dashboard SSE auth (Epic 34 — B-0.7)
    dashboard_token: str = ""  # Token for SSE endpoint; empty = dev mode (no auth)

    # Approval notification channels (Epic 24)
    slack_approval_webhook_url: str = ""  # Slack incoming webhook for approvals

    # Primary Agent mode (Epic 43 — Ralph SDK Integration)
    # Controls which implementation engine powers the Primary Agent:
    #   "legacy"    — current PrimaryAgentRunner (Claude Agent SDK, single-call)
    #   "ralph"     — RalphAgent from ralph_sdk (loop, session continuity, circuit breaking)
    #   "container" — Docker-isolated agent (Epic 25)
    # Default is "legacy" for safe rollout. Switch to "ralph" after validation.
    # Requires THESTUDIO_AGENT_LLM_ENABLED__DEVELOPER=true to take effect.
    agent_mode: str = "legacy"  # "legacy" | "ralph" | "container"

    # Ralph state backend (Epic 43 Story 43.8 — State persistence)
    # Controls which state backend is used when agent_mode="ralph":
    #   "null"     — NullStateBackend: no persistence (Slice 1 default)
    #   "postgres" — PostgresStateBackend: persists state in ralph_agent_state table
    # Session IDs older than ralph_session_ttl_seconds are discarded on resume.
    ralph_state_backend: str = "null"  # "null" | "postgres"
    ralph_session_ttl_seconds: int = 7200  # 2 hours; discard stale session IDs
    # Maximum wall-clock minutes the RalphAgent loop is allowed to run.
    # The Temporal activity is scheduled with start_to_close_timeout =
    # (ralph_timeout_minutes + 5) minutes to add a buffer for pre/post-run work.
    ralph_timeout_minutes: int = 30  # env: THESTUDIO_RALPH_TIMEOUT_MINUTES

    # Container isolation (Epic 25)
    # Global mode: "process" (in-process, default) or "container" (Docker isolation)
    agent_isolation: str = "process"  # "process" or "container"
    # Per-tier fallback policy: what happens when container mode is requested
    # but Docker is unavailable. "allow" = fall back to in-process,
    # "deny" = fail the task. Execute tier MUST be "deny" to prevent
    # untrusted code running without isolation.
    agent_isolation_fallback: dict[str, str] = {
        "observe": "allow",
        "suggest": "allow",
        "execute": "deny",
    }
    # Container resource limits per tier
    agent_container_cpu_limit: dict[str, float] = {
        "observe": 1.0,
        "suggest": 2.0,
        "execute": 4.0,
    }
    agent_container_memory_mb: dict[str, int] = {
        "observe": 512,
        "suggest": 1024,
        "execute": 2048,
    }
    agent_container_timeout_seconds: dict[str, int] = {
        "observe": 300,
        "suggest": 600,
        "execute": 1200,
    }

    @model_validator(mode="after")
    def _reject_approval_bypass_in_production(self) -> "Settings":
        if (
            self.approval_auto_bypass
            and self.github_provider == "real"
            and self.llm_provider == "anthropic"
        ):
            raise ValueError(
                "THESTUDIO_APPROVAL_AUTO_BYPASS cannot be true when "
                "github_provider=real and llm_provider=anthropic. "
                "The approval gate is a safety-critical control for real PR publication. "
                "Set approval_auto_bypass=false or use mock providers for testing."
            )
        return self

    @model_validator(mode="after")
    def _reject_placeholder_encryption_key(self) -> "Settings":
        if self.store_backend == "postgres" and self.encryption_key == _PLACEHOLDER_KEY:
            raise ValueError(
                "THESTUDIO_ENCRYPTION_KEY must be set to a real Fernet key "
                "when store_backend=postgres. Generate one with: "
                "python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )
        return self

    @model_validator(mode="after")
    def _validate_execute_tier_isolation(self) -> "Settings":
        if (
            self.agent_isolation == "container"
            and self.agent_isolation_fallback.get("execute") != "deny"
        ):
            raise ValueError(
                "Execute tier MUST have agent_isolation_fallback='deny'. "
                "Silent fallback to in-process on Execute tier is a security hole."
            )
        return self


settings = Settings()
