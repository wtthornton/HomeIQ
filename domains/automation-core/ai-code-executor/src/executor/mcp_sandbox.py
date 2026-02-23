"""
Enhanced sandbox with MCP tool support.
"""

import asyncio
import logging
from typing import Any

from ..mcp.homeiq_tools import HomeIQMCPTools
from .sandbox import ExecutionResult, PythonSandbox, SandboxConfig

logger = logging.getLogger(__name__)


class MCPSandbox(PythonSandbox):
    """Sandbox wrapper that optionally injects MCP tool context."""

    def __init__(
        self,
        config: SandboxConfig = None,
        workspace_dir: str = "/tmp/mcp_workspace",
        max_concurrent_executions: int = 2,
        enable_network_tools: bool = False,
    ):
        super().__init__(config)
        self.workspace_dir = workspace_dir
        self._initialized = False
        self._tool_context: dict[str, Any] = {}
        self._execution_guard = asyncio.Semaphore(max_concurrent_executions)
        self._tool_registry = HomeIQMCPTools(enable_network_tools=enable_network_tools)

    async def initialize(self):
        """Prepare tool context. Network access is disabled by default."""
        if self._initialized:
            return

        self._tool_context = await self._tool_registry.build_context()
        self._initialized = True
        logger.info(
            "MCP sandbox initialized (network_tools_enabled=%s)",
            self._tool_registry.network_enabled,
        )

    def is_initialized(self) -> bool:
        """Check if sandbox has been initialized."""
        return self._initialized

    async def execute_with_mcp(
        self,
        code: str,
        context: dict[str, Any] = None,
    ) -> ExecutionResult:
        """Execute code with optional MCP context within concurrency guard."""
        if not self._initialized:
            await self.initialize()

        merged_context: dict[str, Any] = {}
        if self._tool_context:
            merged_context.update(self._tool_context)
        if context:
            merged_context.update(context)

        async with self._execution_guard:
            return await self.execute(code, merged_context)
