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

    # STATUS defasado: se a spec/checkpoint mais recente está há >= N dias à
    # frente do último commit no STATUS.md, o projeto é sinalizado como defasado
    # (o painel mostra o badge; a notificação de mudança inclui um aviso).
    status_stale_days: int = 14

    # Vazio = endpoint de webhook desativado (polling continua funcionando).
    github_webhook_secret: str = ""

    # Notificações por e-mail (SMTP). Vazio SMTP_HOST = notificações desativadas
    # (o sync segue normal), mesma lógica do webhook sem segredo. Telegram e
    # outros canais ficam para depois (ver STATUS, decisão M1).
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""  # remetente; se vazio, usa smtp_user
    smtp_use_tls: bool = True
    # Base pública para montar links nos e-mails (ex.: https://spec.exemplo.com).
    app_base_url: str = ""

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

    @property
    def notifications_enabled(self) -> bool:
        """SMTP configurado (host presente). Sem isso, notificações são no-op."""
        return bool(self.smtp_host.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
