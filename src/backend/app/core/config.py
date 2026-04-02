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

    # API Configuration
    API_V1_STR: str = "/api/v1"
    VERSION: str = "local"

    # Workspace Configuration
    WORKSPACE_BASE_PATH: str = "/var/tmp/workspace"

    # Documentation Configuration
    DISABLE_DOCS: bool = False

    # Session Configuration
    PERMISSION_QUEUE_SIZE: int = 100
    POLLING_INTERVAL: float = 0.05  # seconds

    @property
    def fastapi_properties(self) -> dict:
        return {
            "title": "Claude Agent API Server",
            "version": self.VERSION,
            "description": (
                "API server for Claude Agent. Provides endpoints for managing "
                "agent session, interacting with agent, and integrating with external services."
            ),
            "openapi_url": f"{self.API_V1_STR}/openapi.json",
            "docs_url": "/docs",
            "redoc_url": "/redoc",
        }

    @property
    def fastapi_kwargs(self) -> dict:
        """Creates dictionary of values to pass to FastAPI app
        as **kwargs.

        Returns:
            dict: This can be unpacked as **kwargs to pass to FastAPI app.
        """
        fastapi_kwargs = self.fastapi_properties
        if self.DISABLE_DOCS:
            fastapi_kwargs.update(
                {
                    "openapi_url": None,
                    "openapi_prefix": None,
                    "docs_url": None,
                    "redoc_url": None,
                }
            )
        return fastapi_kwargs


@lru_cache
def get_settings():
    """Use lru_cache to avoid re-reading the .env file on every call."""
    return Settings()
