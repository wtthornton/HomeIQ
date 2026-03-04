"""Configuration for the Admin API service.

Loads all settings from environment variables with sensible defaults.
Handles API key validation and anonymous-mode fallback.
"""

import os
import secrets
from dataclasses import dataclass, field

from homeiq_observability.logging_config import setup_logging

logger = setup_logging("admin-api.config")


def _bool_env(key: str, default: str = "false") -> bool:
    """Read an env var as a boolean ('true'/'false')."""
    return os.getenv(key, default).lower() == "true"


@dataclass
class AdminAPIConfig:
    """Immutable configuration for the Admin API service.

    All values are resolved from environment variables at instantiation time.
    The ``api_key`` field is validated: if it is unset and anonymous mode
    is disabled, a ``RuntimeError`` is raised.
    """

    api_host: str = field(default_factory=lambda: os.getenv("API_HOST", "0.0.0.0"))  # noqa: S104
    api_port: int = field(default_factory=lambda: int(os.getenv("API_PORT", "8000")))
    api_title: str = field(
        default_factory=lambda: os.getenv(
            "API_TITLE", "Home Assistant Ingestor Admin API"
        )
    )
    api_version: str = field(
        default_factory=lambda: os.getenv("API_VERSION", "1.0.0")
    )
    api_description: str = field(
        default_factory=lambda: os.getenv(
            "API_DESCRIPTION", "Admin API for Home Assistant Ingestor"
        )
    )

    allow_anonymous: bool = field(
        default_factory=lambda: _bool_env("ADMIN_API_ALLOW_ANONYMOUS")
    )
    docs_enabled: bool = field(
        default_factory=lambda: _bool_env("ADMIN_API_ENABLE_DOCS")
    )
    openapi_enabled: bool = field(
        default_factory=lambda: _bool_env("ADMIN_API_ENABLE_OPENAPI")
    )
    rate_limit_per_min: int = field(
        default_factory=lambda: int(os.getenv("ADMIN_API_RATE_LIMIT_PER_MIN", "60"))
    )
    rate_limit_burst: int = field(
        default_factory=lambda: int(os.getenv("ADMIN_API_RATE_LIMIT_BURST", "20"))
    )

    cors_origins: list[str] = field(
        default_factory=lambda: os.getenv(
            "CORS_ORIGINS", "http://localhost:3000"
        ).split(",")
    )
    cors_methods: list[str] = field(
        default_factory=lambda: os.getenv(
            "CORS_METHODS", "GET,POST,PUT,DELETE"
        ).split(",")
    )
    cors_headers: list[str] = field(
        default_factory=lambda: os.getenv("CORS_HEADERS", "*").split(",")
    )

    api_key: str = field(default="")

    def __post_init__(self) -> None:
        """Resolve and validate the API key after dataclass init."""
        raw_key = os.getenv("ADMIN_API_API_KEY") or os.getenv("API_KEY") or ""
        if raw_key:
            self.api_key = raw_key
        elif self.allow_anonymous:
            self.api_key = secrets.token_urlsafe(48)
            logger.warning(
                "Admin API started in anonymous mode for local testing only. "
                "Set ADMIN_API_API_KEY to enforce authentication."
            )
        else:
            raise RuntimeError(
                "API_KEY (or ADMIN_API_API_KEY) must be set "
                "before starting admin-api"
            )
