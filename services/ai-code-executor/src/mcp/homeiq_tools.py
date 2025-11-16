"""
HomeIQ-specific MCP tool definitions.

Network connectivity is disabled by default to avoid lateral movement risks.
"""

from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class HomeIQMCPTools:
    """Registry of MCP helper context (network-less by default)."""

    def __init__(self, enable_network_tools: bool = False):
        self.network_enabled = enable_network_tools

    async def build_context(self) -> Dict[str, Any]:
        """
        Return a context dictionary injected into the sandbox.

        When network tools are disabled (default), this returns an empty dict to
        prevent sandboxed code from pivoting into other HomeIQ services.
        """
        if not self.network_enabled:
            logger.info("MCP network tools disabled; no remote services exposed to sandboxed code")
            return {}

        raise RuntimeError(
            "Network-enabled MCP tools are temporarily disabled pending new security controls"
        )
