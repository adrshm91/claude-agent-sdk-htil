from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    ANTHROPIC_MODEL: str | None = None
    ANTHROPIC_SMALL_FAST_MODEL: str | None = None


@lru_cache
def get_settings():
    """Use lru_cache to avoid re-reading the .env file on every call."""
    return Settings()
