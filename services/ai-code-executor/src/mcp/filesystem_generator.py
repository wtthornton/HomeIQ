"""
Generate filesystem-based MCP tool modules.

Structure:
/workspace/
  servers/
    data/
      query_device_history.py
      get_devices.py
      search_events.py
    automation/
      detect_patterns.py
    device/
      get_device_capabilities.py
"""

import os
import json
from typing import Dict, List, Any
from pathlib import Path
import aiofiles
import logging

logger = logging.getLogger(__name__)


class MCPFilesystemGenerator:
    """Generate filesystem structure for MCP tools"""

    def __init__(self, workspace_dir: str = "/tmp/mcp_workspace"):
        self.workspace_dir = Path(workspace_dir)
        self.servers_dir = self.workspace_dir / "servers"

    async def initialize_workspace(self):
        """Create workspace directory structure"""
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.servers_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initialized MCP workspace at {self.workspace_dir}")

    async def register_server(
        self,
        server_name: str,
        tools: List[Dict[str, Any]]
    ):
        """
        Register MCP server and generate tool modules.

        Args:
            server_name: Name of MCP server (e.g., "data")
            tools: List of tool definitions
        """
        server_dir = self.servers_dir / server_name
        server_dir.mkdir(parents=True, exist_ok=True)

        # Generate __init__.py
        await self._generate_init_file(server_dir, tools)

        # Generate individual tool modules
        for tool in tools:
            await self._generate_tool_module(server_dir, server_name, tool)

        logger.info(f"Registered {len(tools)} tools for server '{server_name}'")

    async def _generate_init_file(self, server_dir: Path, tools: List[Dict]):
        """Generate __init__.py with tool exports"""
        init_path = server_dir / "__init__.py"

        tool_names = [tool['name'] for tool in tools]
        imports = "\n".join(f"from .{name} import {name}" for name in tool_names)
        exports = ", ".join(f'"{name}"' for name in tool_names)

        content = f'''"""
MCP Server Tools - Auto-generated
"""

{imports}

__all__ = [{exports}]
'''

        async with aiofiles.open(init_path, 'w') as f:
            await f.write(content)

    async def _generate_tool_module(
        self,
        server_dir: Path,
        server_name: str,
        tool: Dict[str, Any]
    ):
        """Generate individual tool module with real service URL"""
        tool_name = tool['name']
        tool_description = tool.get('description', '')
        server_url = tool.get('server_url', f'http://{server_name}:8006')
        endpoint = tool.get('endpoint', f'/mcp/tools/{tool_name}')

        content = f'''"""
{tool_description}
"""

import httpx
from typing import Any, Dict, Optional

# MCP Tool Configuration
TOOL_NAME = "{tool_name}"
SERVER_URL = "{server_url}"
ENDPOINT = "{endpoint}"


async def {tool_name}(**kwargs) -> Dict[str, Any]:
    """
    {tool_description}

    This function calls the HomeIQ service via HTTP.
    Auto-generated from MCP tool definition.

    Args:
        **kwargs: Tool parameters (validated by service)

    Returns:
        Service response

    Raises:
        httpx.HTTPStatusError: If service returns error
        httpx.RequestError: If connection fails
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{{SERVER_URL}}{{ENDPOINT}}",
                json=kwargs
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            # Re-raise with context
            raise Exception(
                f"MCP tool '{{TOOL_NAME}}' failed: "
                f"{{e.response.status_code}} - {{e.response.text}}"
            )
        except httpx.RequestError as e:
            raise Exception(
                f"MCP tool '{{TOOL_NAME}}' connection failed: {{e}}"
            )
'''

        async with aiofiles.open(server_dir / f"{tool_name}.py", 'w') as f:
            await f.write(content)

    def get_workspace_path(self) -> str:
        """Get workspace directory path for code execution"""
        return str(self.workspace_dir)
