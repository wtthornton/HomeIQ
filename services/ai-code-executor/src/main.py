"""
AI Code Executor Service - FastAPI application
Secure Python code execution for MCP (Model Context Protocol) pattern.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager
import logging

from .executor.mcp_sandbox import MCPSandbox, SandboxConfig
from .config import settings

# Setup logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global sandbox instance
sandbox: Optional[MCPSandbox] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize sandbox on startup"""
    global sandbox

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
        sandbox = MCPSandbox(
            config=SandboxConfig(
                timeout_seconds=settings.execution_timeout,
                max_memory_mb=settings.max_memory_mb,
                max_cpu_percent=settings.max_cpu_percent
            ),
            workspace_dir=settings.mcp_workspace_dir
        )
        await sandbox.initialize()
        logger.info("✅ MCP sandbox initialized successfully")
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

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


@app.post("/execute", response_model=ExecuteResponse)
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
    if sandbox is None:
        raise HTTPException(status_code=503, detail="Sandbox not initialized")

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
