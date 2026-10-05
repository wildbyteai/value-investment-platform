from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VIP_", env_file=Path(__file__).resolve().parents[1] / ".env", extra="ignore")

    db_url: str = "postgresql+psycopg2://vip_app@127.0.0.1:5432/vip_v0001_local"
    # Clock can be injected; default to wall clock.
    demo_mode: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
