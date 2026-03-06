from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = {"env_prefix": "THESTUDIO_"}

    database_url: str = "postgresql+asyncpg://thestudio:thestudio_dev@localhost:5432/thestudio"
    temporal_host: str = "localhost:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "thestudio-main"
    nats_url: str = "nats://localhost:4222"
    encryption_key: str = "generate-a-real-fernet-key-for-production"

    otel_service_name: str = "thestudio"
    otel_exporter: str = "console"  # "console" or "otlp"
    otel_otlp_endpoint: str = "http://localhost:4317"


settings = Settings()
