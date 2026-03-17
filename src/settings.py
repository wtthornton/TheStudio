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
    agent_llm_enabled: dict[str, bool] = {
        "primary_agent": False,
        "intake_agent": False,
        "context_agent": False,
        "intent_agent": False,
        "router_agent": False,
        "recruiter_agent": False,
        "assembler_agent": False,
        "qa_agent": False,
    }

    # Feature flags (Epic 8 Sprint 2)
    llm_provider: str = "mock"  # "mock" or "anthropic"
    github_provider: str = "mock"  # "mock" or "real"
    store_backend: str = "memory"  # "memory" or "postgres"

    # Approval notification channels (Epic 24)
    slack_approval_webhook_url: str = ""  # Slack incoming webhook for approvals

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
