"""
MCP (Model Context Protocol) integration.
Filesystem-based tool discovery and execution.
"""

from .filesystem_generator import MCPFilesystemGenerator
from .homeiq_tools import HomeIQMCPTools

__all__ = ['MCPFilesystemGenerator', 'HomeIQMCPTools']
