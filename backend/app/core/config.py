from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "HRMS Lite"
    app_env: str = "development"
    app_debug: bool = True
    api_v1_prefix: str = "/api"

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/hrms_lite"
    superadmin_key: str = "change-me-superadmin-key"

    cors_allowed_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    rabbitmq_exchange: str = "hrms.events"
    rabbitmq_listener_queue: str = "hrms.activity.listener"
    rabbitmq_internal_topic: str = "internal.#"
    rabbitmq_activity_topic: str = "activity.#"
    rabbitmq_reconnect_seconds: int = 3
    event_publish_enabled: bool = True
    event_listener_enabled: bool = True
    event_source: str = "hrms.backend"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
