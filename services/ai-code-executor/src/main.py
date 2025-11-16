"""
AI Code Executor Service - FastAPI application
Secure Python code execution for MCP (Model Context Protocol) pattern.
"""

from fastapi import FastAPI, HTTPException, Depends, Header, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager
import logging

from .executor.mcp_sandbox import MCPSandbox, SandboxConfig
from .config import settings
from .security.code_validator import (
    CodeValidator,
    CodeValidatorConfig,
    CodeValidationError,
)

# Setup logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global sandbox + validator instances
sandbox: Optional[MCPSandbox] = None
code_validator: Optional[CodeValidator] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize sandbox on startup"""
    global sandbox, code_validator

    logger.info("=" * 60)
    logger.info("AI Code Executor Service Starting Up")
    logger.info("=" * 60)
    logger.info(f"Service: {settings.service_name}")
    logger.info(f"Port: {settings.service_port}")
    logger.info(f"Execution timeout: {settings.execution_timeout}s")
    logger.info(f"Max memory: {settings.max_memory_mb}MB")
    logger.info(f"Max CPU: {settings.max_cpu_percent}%")
    logger.info(f"MCP workspace: {settings.mcp_workspace_dir}")
    logger.info("=" * 60)

    try:
        # Initialize MCP sandbox
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
        logger.info("✅ MCP sandbox initialized successfully")

        code_validator = CodeValidator(
            CodeValidatorConfig(
                max_bytes=settings.max_code_bytes,
                max_ast_nodes=settings.max_ast_nodes,
                allowed_imports=sandbox_config.allowed_imports,
            )
        )
        logger.info(
            "✅ Code validator ready (max_bytes=%s, max_ast_nodes=%s)",
            settings.max_code_bytes,
            settings.max_ast_nodes,
        )
    except Exception as e:
        logger.error(f"❌ Failed to initialize sandbox: {e}")
        raise

    yield

    # Cleanup on shutdown
    logger.info("🛑 AI Code Executor Service shutting down")


# Create FastAPI app
app = FastAPI(
    title="AI Code Executor Service",
    description="Secure Python code execution for MCP code execution pattern",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware with explicit allow-list
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["POST", "OPTIONS", "GET"],
    allow_headers=["Authorization", "Content-Type", "X-Executor-Token"],
)


def verify_api_token(x_executor_token: Optional[str] = Header(default=None, alias="X-Executor-Token")):
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


class ExecuteRequest(BaseModel):
    """Request to execute code"""
    code: str = Field(..., description="Python code to execute")
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Context variables available to code"
    )


class ExecuteResponse(BaseModel):
    """Response from code execution"""
    success: bool
    stdout: str
    stderr: str
    return_value: Any
    execution_time: float
    memory_used_mb: float
    error: Optional[str] = None


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": settings.service_name,
        "version": "1.0.0",
        "mcp_initialized": sandbox is not None and sandbox._initialized
    }


@app.post(
    "/execute",
    response_model=ExecuteResponse,
    dependencies=[Depends(verify_api_token)],
)
async def execute_code(request: ExecuteRequest):
    """
    Execute Python code in secure sandbox with MCP tool access.

    Example:
    ```python
    {
        "code": "import data\\ndevices = await data.get_devices()\\nprint(devices['count'])\\ndevices"
    }
    ```
    """
    if sandbox is None or code_validator is None:
        raise HTTPException(status_code=503, detail="Sandbox not initialized")

    try:
        code_validator.validate(request.code)
    except CodeValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        logger.info(f"Executing code ({len(request.code)} chars)")

        result = await sandbox.execute_with_mcp(request.code, request.context)

        logger.info(
            f"Execution complete: success={result.success}, "
            f"time={result.execution_time:.3f}s, "
            f"memory={result.memory_used_mb:.2f}MB"
        )

        if not result.success:
            logger.warning(f"Execution failed: {result.error}")

        return ExecuteResponse(
            success=result.success,
            stdout=result.stdout,
            stderr=result.stderr,
            return_value=result.return_value,
            execution_time=result.execution_time,
            memory_used_mb=result.memory_used_mb,
            error=result.error
        )

    except Exception as e:
        logger.error(f"Execution failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=settings.service_port,
        log_level=settings.log_level.lower()
    )
