"""Configuration for the FastAPI backend.

Values come from the environment (see .env.example). Nothing here has a secret
as its default — the only defaults are safe local-development ones.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    # ── Database ────────────────────────────────────────────────────────────
    postgres_user: str = "mos"
    postgres_password: str = "mos_dev_password"
    postgres_db: str = "marketing_os"
    postgres_host: str = "localhost"
    postgres_port: int = 5434

    # ── API ─────────────────────────────────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    public_api_url: str = "http://localhost:8000"
    cors_origins: str = "http://localhost:3000,http://localhost:3001"

    # ── Email delivery (Phase 3) ────────────────────────────────────────────
    # An empty smtp_host means DRY-RUN: messages are rendered and recorded but
    # never actually sent. That is the safe default.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_from_name: str = "Marketing OS"
    smtp_use_tls: bool = True

    # Managed Postgres providers (Neon, Supabase, Railway) refuse plain
    # connections — set POSTGRES_SSLMODE=require for them. Empty means the
    # local Docker database, which speaks no TLS at all.
    postgres_sslmode: str = ""

    # Shared secret for POST /campaigns/scheduler/run — the endpoint a cron
    # job calls in production. Empty (local dev) leaves it open.
    scheduler_token: str = ""

    @property
    def database_url(self) -> str:
        url = (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
        if self.postgres_sslmode:
            url += f"?sslmode={self.postgres_sslmode}"
        return url

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def email_enabled(self) -> bool:
        """True only when SMTP is fully configured; otherwise we dry-run."""
        return bool(self.smtp_host and self.smtp_from_email)


@lru_cache
def get_settings() -> Settings:
    return Settings()
