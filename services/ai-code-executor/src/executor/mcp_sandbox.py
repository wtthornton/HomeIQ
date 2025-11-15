"""
Enhanced sandbox with MCP tool support.
"""

from .sandbox import PythonSandbox, SandboxConfig, ExecutionResult
from ..mcp.filesystem_generator import MCPFilesystemGenerator
from ..mcp.homeiq_tools import HomeIQMCPTools
import sys
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class MCPSandbox(PythonSandbox):
    """Sandbox with MCP tool filesystem support"""

    def __init__(self, config: SandboxConfig = None, workspace_dir: str = "/tmp/mcp_workspace"):
        super().__init__(config)
        self.mcp_generator = MCPFilesystemGenerator(workspace_dir)
        self._initialized = False

    async def initialize(self):
        """Initialize MCP workspace and register HomeIQ servers"""
        if self._initialized:
            logger.info("MCP workspace already initialized")
            return

        await self.mcp_generator.initialize_workspace()

        # Register all HomeIQ MCP servers
        await self._register_homeiq_servers()

        self._initialized = True
        logger.info("MCP sandbox initialized successfully")

    async def _register_homeiq_servers(self):
        """Register HomeIQ MCP servers"""
        all_tools = HomeIQMCPTools.get_all_tools()

        for server_name, tools in all_tools.items():
            await self.mcp_generator.register_server(server_name, tools)
            logger.info(f"Registered {len(tools)} tools for '{server_name}' server")

    async def execute_with_mcp(
        self,
        code: str,
        context: Dict[str, Any] = None
    ) -> ExecutionResult:
        """
        Execute code with MCP tool access.

        The code can import MCP tools like:
        ```python
        import data
        devices = await data.get_devices()
        ```
        """
        # Ensure initialized
        if not self._initialized:
            await self.initialize()

        # Add MCP workspace to Python path
        workspace_path = self.mcp_generator.get_workspace_path()

        # Build context with sys.path modification
        mcp_context = context or {}

        # Prepend code to add workspace to sys.path
        setup_code = f"""
import sys
if '{workspace_path}/servers' not in sys.path:
    sys.path.insert(0, '{workspace_path}/servers')
"""

        full_code = setup_code + "\n" + code

        return await self.execute(full_code, mcp_context)
