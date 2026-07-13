from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "dev"

    # SQLite por padrão (dev sem dependências); Postgres via env no docker-compose.
    database_url: str = "sqlite:///./data/spec_monitor.db"

    secret_key: str = "dev-only-change-me"

    # Super admin — criado (ou promovido) no startup.
    admin_email: str = "admin@example.com"
    admin_password: str = "troque-me"

    sync_interval_minutes: int = 10

    # Vazio = endpoint de webhook desativado (polling continua funcionando).
    github_webhook_secret: str = ""

    session_cookie_name: str = "spec_monitor_session"
    session_max_age_seconds: int = 8 * 60 * 60


@lru_cache
def get_settings() -> Settings:
    return Settings()
