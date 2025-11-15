"""
Configuration for AI Code Executor Service.
Simplified - no feature flags, optimized for single-home NUC deployment.
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Service configuration - MCP Code Execution always enabled"""

    # Service basics
    service_name: str = "ai-code-executor"
    service_port: int = 8030

    # Sandbox limits (NUC-optimized)
    execution_timeout: int = Field(
        default=30,
        env="EXECUTION_TIMEOUT",
        description="Maximum code execution time in seconds"
    )

    max_memory_mb: int = Field(
        default=128,
        env="MAX_MEMORY_MB",
        description="Maximum memory per execution (MB)"
    )

    max_cpu_percent: float = Field(
        default=50.0,
        env="MAX_CPU_PERCENT",
        description="Maximum CPU usage percentage"
    )

    # Connection pooling
    max_concurrent_executions: int = Field(
        default=2,
        env="MAX_CONCURRENT_EXECUTIONS",
        description="Maximum concurrent code executions"
    )

    http_pool_size: int = Field(
        default=5,
        env="HTTP_POOL_SIZE",
        description="HTTP connection pool size for MCP tool calls"
    )

    # Caching
    code_cache_size: int = Field(
        default=100,
        env="CODE_CACHE_SIZE",
        description="Number of compiled code blocks to cache"
    )

    mcp_tool_cache_ttl: int = Field(
        default=300,
        env="MCP_TOOL_CACHE_TTL",
        description="MCP tool definition cache TTL (seconds)"
    )

    # MCP workspace
    mcp_workspace_dir: str = Field(
        default="/tmp/mcp_workspace",
        env="MCP_WORKSPACE_DIR",
        description="Directory for MCP tool filesystem"
    )

    # Logging
    log_level: str = Field(
        default="INFO",
        env="LOG_LEVEL"
    )

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
