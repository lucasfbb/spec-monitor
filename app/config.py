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

    # Origens permitidas para o frontend (SPA) chamar a API com credenciais.
    # Lista separada por vírgula. Em dev, o proxy do Vite deixa tudo same-origin,
    # mas manter localhost aqui cobre quem chamar a API direto.
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    # Cookie de sessão cross-site (frontend e API em hosts diferentes em prod)
    # exige SameSite=None + Secure. Em dev (same-origin via proxy) "lax" basta.
    session_cookie_samesite: str = "lax"
    session_cookie_secure: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
