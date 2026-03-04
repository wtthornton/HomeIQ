"""
AI Code Executor Service - FastAPI application.

Secure Python code execution for MCP (Model Context Protocol) pattern.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

from fastapi import Depends, Header, HTTPException, status
from homeiq_resilience import ServiceLifespan, StandardHealthCheck, create_app
from pydantic import BaseModel, Field

from .config import settings
from .executor.mcp_sandbox import MCPSandbox, SandboxConfig
from .middleware import get_metrics, record_execution, record_request
from .security.code_validator import (
    CodeValidationError,
    CodeValidator,
    CodeValidatorConfig,
)


def _configure_logging() -> None:
    """Configure logging for the service."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


_configure_logging()
logger = logging.getLogger(__name__)

# Global sandbox + validator instances
sandbox: MCPSandbox | None = None
code_validator: CodeValidator | None = None


# ---------------------------------------------------------------------------
# Lifespan hooks
# ---------------------------------------------------------------------------


async def _startup_sandbox() -> None:
    """Initialize MCP sandbox and code validator on startup."""
    global sandbox, code_validator  # noqa: PLW0603

    logger.info("Execution timeout: %ss", settings.execution_timeout)
    logger.info("Max memory: %sMB", settings.max_memory_mb)
    logger.info("Max CPU: %s%%", settings.max_cpu_percent)
    logger.info("MCP workspace: %s", settings.mcp_workspace_dir)

    sandbox_config = SandboxConfig(
        timeout_seconds=settings.execution_timeout,
        max_memory_mb=settings.max_memory_mb,
        max_cpu_percent=settings.max_cpu_percent,
    )
    sandbox = MCPSandbox(
        config=sandbox_config,
        workspace_dir=settings.mcp_workspace_dir,
        max_concurrent_executions=settings.max_concurrent_executions,
        enable_network_tools=settings.enable_mcp_network_tools,
    )
    await sandbox.initialize()
    logger.info("MCP sandbox initialized successfully")

    code_validator = CodeValidator(
        CodeValidatorConfig(
            max_bytes=settings.max_code_bytes,
            max_ast_nodes=settings.max_ast_nodes,
            allowed_imports=sandbox_config.allowed_imports,
        )
    )
    logger.info(
        "Code validator ready (max_bytes=%s, max_ast_nodes=%s)",
        settings.max_code_bytes,
        settings.max_ast_nodes,
    )


lifespan = ServiceLifespan(settings.service_name, graceful=False)
lifespan.on_startup(_startup_sandbox, name="sandbox")


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

health = StandardHealthCheck(
    service_name=settings.service_name,
    version="1.0.0",
)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = create_app(
    title="AI Code Executor Service",
    version="1.0.0",
    description="Secure Python code execution for MCP code execution pattern",
    lifespan=lifespan.handler,
    health_check=health,
    cors_origins=settings.get_cors_origins_list(),
)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class ExecuteRequest(BaseModel):
    """Request to execute code."""

    code: str = Field(..., description="Python code to execute")
    context: dict[str, Any] | None = Field(
        default=None,
        description="Context variables available to code",
    )


class ExecuteResponse(BaseModel):
    """Response from code execution."""

    success: bool
    stdout: str
    stderr: str
    return_value: Any
    execution_time: float
    memory_used_mb: float
    error: str | None = None


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def verify_api_token(
    x_executor_token: str | None = Header(default=None, alias="X-Executor-Token"),
) -> None:
    """Simple header-based authentication for execute endpoint."""
    if not settings.api_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API token not configured",
        )

    if not x_executor_token or x_executor_token != settings.api_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing executor token",
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/metrics")
async def metrics() -> dict[str, float | int]:
    """Metrics endpoint for monitoring."""
    record_request()
    return get_metrics()


@app.post(
    "/execute",
    response_model=ExecuteResponse,
    dependencies=[Depends(verify_api_token)],
)
async def execute_code(request: ExecuteRequest) -> ExecuteResponse:
    """Execute Python code in secure sandbox with MCP tool access."""
    if sandbox is None or code_validator is None:
        raise HTTPException(status_code=503, detail="Sandbox not initialized")

    try:
        code_validator.validate(request.code)
    except CodeValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        record_request()
        logger.info("Executing code (%s chars)", len(request.code))

        result = await sandbox.execute_with_mcp(request.code, request.context)

        record_execution(
            success=result.success,
            execution_time=result.execution_time,
            memory_used_mb=result.memory_used_mb,
        )

        logger.info(
            "Execution complete: success=%s, time=%.3fs, memory=%.2fMB",
            result.success,
            result.execution_time,
            result.memory_used_mb,
        )

        if not result.success:
            logger.warning("Execution failed: %s", result.error)

        return ExecuteResponse(
            success=result.success,
            stdout=result.stdout,
            stderr=result.stderr,
            return_value=result.return_value,
            execution_time=result.execution_time,
            memory_used_mb=result.memory_used_mb,
            error=result.error,
        )

    except Exception as e:
        logger.error("Execution failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",  # noqa: S104
        port=settings.service_port,
        log_level=settings.log_level.lower(),
    )
