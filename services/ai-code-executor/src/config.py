"""
Configuration for AI Code Executor Service.
Simplified - optimized for single-home NUC deployment with strict security controls.
"""


from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Service configuration - MCP Code Execution always enabled"""

    # Service basics
    service_name: str = "ai-code-executor"
    service_port: int = 8030

    # Sandbox limits (NUC-optimized)
    execution_timeout: int = Field(
        default=30,
        env="EXECUTION_TIMEOUT",
        description="Maximum code execution time in seconds",
    )

    max_memory_mb: int = Field(
        default=128,
        env="MAX_MEMORY_MB",
        description="Maximum memory per execution (MB)",
    )

    max_cpu_percent: float = Field(
        default=50.0,
        env="MAX_CPU_PERCENT",
        description="Maximum CPU usage percentage",
    )

    max_concurrent_executions: int = Field(
        default=2,
        env="MAX_CONCURRENT_EXECUTIONS",
        description="Maximum concurrent code executions",
    )

    max_code_bytes: int = Field(
        default=10_000,
        env="MAX_CODE_BYTES",
        description="Maximum size of submitted code payload (bytes)",
    )

    max_ast_nodes: int = Field(
        default=5_000,
        env="MAX_AST_NODES",
        description="Maximum number of AST nodes allowed in submitted code",
    )

    enable_mcp_network_tools: bool = Field(
        default=False,
        env="ENABLE_MCP_NETWORK_TOOLS",
        description="Allow sandboxed code to access HomeIQ services via MCP tools",
    )

    # MCP workspace
    mcp_workspace_dir: str = Field(
        default="/tmp/mcp_workspace",
        env="MCP_WORKSPACE_DIR",
        description="Directory for MCP tool filesystem",
    )

    # API surface security
    allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:8030"],
        env="ALLOWED_ORIGINS",
        description="Comma-separated list of allowed origins for CORS",
    )

    api_token: str = Field(
        default="local-dev-token",
        env="EXECUTOR_API_TOKEN",
        description="Shared secret required via X-Executor-Token header",
    )

    # Logging
    log_level: str = Field(
        default="INFO",
        env="LOG_LEVEL",
    )

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, value):
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
