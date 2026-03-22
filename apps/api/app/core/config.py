from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "PodiumForge"
    environment: str = "development"
    database_url: str = (
        "postgresql+psycopg://podiumforge:podiumforge@db:5432/podiumforge"
    )
    jwt_secret_key: str = "change-me-local-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 720
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])
    seeded_admin_email: str = "admin@podiumforge.local"
    seeded_admin_password: str = "admin1234"
    seeded_admin_username: str = "admin"
    smtp_host: str = "mailpit"
    smtp_port: int = 1025
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str = "no-reply@podiumforge.local"
    smtp_from_name: str = "PodiumForge"
    smtp_starttls: bool = False
    smtp_ssl: bool = False
    password_reset_url_base: str = "http://localhost:8080/reset-password"
    password_reset_expire_minutes: int = 60

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
