"""Settings for the homeiq MCP server.

Fail-fast: `load_settings()` raises `ConfigError` naming every missing or
malformed variable so the container refuses to start with a partial config
(TAP-5293 acceptance) instead of serving 500s later.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, SecretStr, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


def _split_csv(value: str | list[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [v for v in value if v]
    return [part.strip() for part in value.split(",") if part.strip()]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="HOMEIQ_MCP_", extra="ignore", populate_by_name=True
    )

    transport: Literal["http", "stdio"] = "http"
    host: str = "0.0.0.0"  # container-internal bind; DNS rebinding is guarded by allowed_hosts
    port: int = Field(default=8050, ge=1, le=65535)
    public_hostname: str = "homeiq-mcp"
    allowed_hosts: str = ""
    """Extra Host header values (comma-separated) accepted besides the public hostname and localhost."""

    read_tokens: str = ""
    write_tokens: str = ""
    allow_writes: str = ""
    """Per-tool mutation grant (design rule 1): comma-separated tool names. v1 has no mutating tools."""

    data_api_url: str = Field(default="", validation_alias="DATA_API_URL")
    data_api_key: SecretStr = Field(default=SecretStr(""), validation_alias="API_KEY")
    pattern_service_url: str = Field(default="", validation_alias="PATTERN_SERVICE_URL")
    device_intelligence_url: str = Field(default="", validation_alias="DEVICE_INTELLIGENCE_URL")
    backing_timeout_seconds: float = Field(default=10.0, gt=0, le=120)
    catalogue_path: str = ""
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    @field_validator("data_api_url", "pattern_service_url", "device_intelligence_url")
    @classmethod
    def _strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")

    @property
    def read_token_list(self) -> list[str]:
        return _split_csv(self.read_tokens)

    @property
    def write_token_list(self) -> list[str]:
        return _split_csv(self.write_tokens)

    @property
    def allowed_write_tools(self) -> frozenset[str]:
        return frozenset(_split_csv(self.allow_writes))

    @property
    def allowed_host_patterns(self) -> list[str]:
        hosts = [f"{self.public_hostname}:*", "localhost:*", "127.0.0.1:*", "[::1]:*"]
        hosts.extend(f"{h}:*" if ":" not in h else h for h in _split_csv(self.allowed_hosts))
        return hosts


_REQUIRED_HTTP = {
    "read_tokens": "HOMEIQ_MCP_READ_TOKENS",
    "data_api_url": "DATA_API_URL",
    "data_api_key": "API_KEY",
}
_REQUIRED_ANY = {
    "data_api_url": "DATA_API_URL",
    "data_api_key": "API_KEY",
}


def load_settings(**overrides: object) -> Settings:
    """Build settings from the environment (plus overrides) and fail fast on gaps."""
    try:
        settings = Settings(**overrides)  # type: ignore[arg-type]
    except ValidationError as exc:
        problems = "; ".join(
            f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()
        )
        raise ConfigError(f"invalid configuration: {problems}") from exc

    required = _REQUIRED_HTTP if settings.transport == "http" else _REQUIRED_ANY
    missing = []
    for attr, env_name in required.items():
        value = getattr(settings, attr)
        if isinstance(value, SecretStr):
            value = value.get_secret_value()
        if not value:
            missing.append(env_name)
    if missing:
        raise ConfigError(
            "refusing to start: missing required configuration " + ", ".join(sorted(missing))
        )
    overlap = set(settings.read_token_list) & set(settings.write_token_list)
    if overlap:
        raise ConfigError(
            "refusing to start: a token appears in both HOMEIQ_MCP_READ_TOKENS and HOMEIQ_MCP_WRITE_TOKENS"
        )
    return settings
