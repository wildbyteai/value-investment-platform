from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VIP_", env_file=Path(__file__).resolve().parents[1] / ".env", extra="ignore")

    db_url: str = "postgresql+psycopg2://vip_app@127.0.0.1:5432/vip_v0001_local"
    # Clock can be injected; default to wall clock.
    demo_mode: bool = False
    eodhd_api_token: SecretStr = Field(default=SecretStr(''), validation_alias='EODHD_API_TOKEN')
    # Alert e-mail (R6). Unset host = e-mail deliveries are marked skipped, in-app still works.
    smtp_host: str = ''
    smtp_port: int = 465
    smtp_user: str = ''
    smtp_password: SecretStr = Field(default=SecretStr(''))
    smtp_starttls: bool = False  # False = implicit TLS (465); True = STARTTLS (587)
    alert_sender: str = ''       # overrides config/alerts-v1.json sender.address
    # Security (deployment). Fail closed: real login unless a developer explicitly opts into the
    # header-based mock identities for local work and tests.
    auth_mode: str = 'session'           # session | dev
    cookie_secure: bool = True           # session cookie only over HTTPS; set false only for plain-http local runs
    session_idle_minutes: int = 720      # sign out after 12 h without activity
    session_max_hours: int = 168         # and at most 7 days after signing in
    allowed_hosts: str = '*'             # comma list for TrustedHostMiddleware, e.g. research.example.com
    docs_enabled: bool = False           # FastAPI /docs, /redoc, /openapi.json


@lru_cache
def get_settings() -> Settings:
    return Settings()
