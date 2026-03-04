"""
Configuration for AI Code Executor Service.
Simplified - optimized for single-home NUC deployment with strict security controls.
"""

from __future__ import annotations

import os
import warnings

from pydantic import Field, field_validator

from homeiq_data import BaseServiceSettings


class Settings(BaseServiceSettings):
    """Service configuration - MCP Code Execution always enabled.

    Inherits common fields (service_name, service_port, log_level,
    database_url, cors_origins, etc.) from BaseServiceSettings.
    """

    # Override base defaults
    service_name: str = "ai-code-executor"
    service_port: int = 8030

    # Sandbox limits (NUC-optimized)
    execution_timeout: int = Field(
        default=30,
        description="Maximum code execution time in seconds",
    )

    max_memory_mb: int = Field(
        default=128,
        description="Maximum memory per execution (MB)",
    )

    max_cpu_percent: float = Field(
        default=50.0,
        description="Maximum CPU usage percentage",
    )

    max_concurrent_executions: int = Field(
        default=2,
        description="Maximum concurrent code executions",
    )

    max_code_bytes: int = Field(
        default=10_000,
        description="Maximum size of submitted code payload (bytes)",
    )

    max_ast_nodes: int = Field(
        default=5_000,
        description="Maximum number of AST nodes allowed in submitted code",
    )

    enable_mcp_network_tools: bool = Field(
        default=False,
        description="Allow sandboxed code to access HomeIQ services via MCP tools",
    )

    # MCP workspace
    mcp_workspace_dir: str = Field(
        default="/tmp/mcp_workspace",  # noqa: S108
        description="Directory for MCP tool filesystem",
    )

    # API surface security
    api_token: str = Field(
        default="",
        alias="EXECUTOR_API_TOKEN",
        description="Shared secret required via X-Executor-Token header",
    )

    @field_validator("api_token")
    @classmethod
    def validate_api_token(cls, value: str) -> str:
        """Validate that API token is set and not a default value."""
        weak_tokens = ("", "local-dev-token", "change-me", "test-token")
        if os.getenv("ENVIRONMENT", "").lower() in ("production", "prod"):
            if not value or value in weak_tokens:
                msg = (
                    "EXECUTOR_API_TOKEN must be set to a secure value in production. "
                    "Set EXECUTOR_API_TOKEN environment variable."
                )
                raise ValueError(msg)
        elif value in weak_tokens:
            warnings.warn(
                "Using default or weak API token. "
                "Set EXECUTOR_API_TOKEN environment variable for security.",
                UserWarning,
                stacklevel=2,
            )
        return value


settings = Settings()
