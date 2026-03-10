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

    # Feature flags (Epic 8 Sprint 2)
    llm_provider: str = "mock"  # "mock" or "anthropic"
    github_provider: str = "mock"  # "mock" or "real"
    store_backend: str = "memory"  # "memory" or "postgres"

    @model_validator(mode="after")
    def _reject_placeholder_encryption_key(self) -> "Settings":
        if self.store_backend == "postgres" and self.encryption_key == _PLACEHOLDER_KEY:
            raise ValueError(
                "THESTUDIO_ENCRYPTION_KEY must be set to a real Fernet key "
                "when store_backend=postgres. Generate one with: "
                "python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )
        return self


settings = Settings()
