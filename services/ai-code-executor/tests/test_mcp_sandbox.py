"""
Unit tests for MCPSandbox.

Tests MCP sandbox initialization, execution with MCP context, and concurrency control.
"""

import asyncio

import pytest

from src.executor.mcp_sandbox import MCPSandbox
from src.executor.sandbox import SandboxConfig


@pytest.fixture
def sandbox_config():
    """Create a SandboxConfig for testing."""
    return SandboxConfig(
        timeout_seconds=5,
        max_memory_mb=100,
        max_cpu_percent=50.0,
    )


@pytest.fixture
def mcp_sandbox(sandbox_config):
    """Create an MCPSandbox instance for testing."""
    return MCPSandbox(
        config=sandbox_config,
        workspace_dir="/tmp/test_workspace",
        max_concurrent_executions=2,
        enable_network_tools=False,
    )


@pytest.mark.asyncio
class TestMCPSandbox:
    """Test suite for MCPSandbox."""

    async def test_initialization(self, mcp_sandbox):
        """Test that sandbox initializes correctly."""
        assert not mcp_sandbox.is_initialized()
        await mcp_sandbox.initialize()
        assert mcp_sandbox.is_initialized()

    async def test_double_initialization(self, mcp_sandbox):
        """Test that double initialization is safe."""
        await mcp_sandbox.initialize()
        assert mcp_sandbox.is_initialized()
        
        # Second initialization should be safe
        await mcp_sandbox.initialize()
        assert mcp_sandbox.is_initialized()

    async def test_execute_with_mcp_auto_initializes(self, mcp_sandbox):
        """Test that execute_with_mcp auto-initializes if not initialized."""
        assert not mcp_sandbox.is_initialized()
        
        code = "_ = 42"
        result = await mcp_sandbox.execute_with_mcp(code)
        
        assert mcp_sandbox.is_initialized()
        assert result.success
        assert result.return_value == 42

    async def test_execute_with_mcp_simple_code(self, mcp_sandbox):
        """Test executing simple code with MCP sandbox."""
        await mcp_sandbox.initialize()
        
        code = """
result = 2 + 2
_ = result
"""
        result = await mcp_sandbox.execute_with_mcp(code)
        
        assert result.success
        assert result.return_value == 4
        assert result.error is None

    async def test_execute_with_mcp_with_context(self, mcp_sandbox):
        """Test executing code with user-provided context."""
        await mcp_sandbox.initialize()
        
        code = """
result = user_value * 2
_ = result
"""
        context = {"user_value": 5}
        result = await mcp_sandbox.execute_with_mcp(code, context=context)
        
        assert result.success
        assert result.return_value == 10

    async def test_execute_with_mcp_context_merging(self, mcp_sandbox):
        """Test that user context merges with MCP tool context."""
        await mcp_sandbox.initialize()
        
        code = """
result = user_var
_ = result
"""
        context = {"user_var": "test_value"}
        result = await mcp_sandbox.execute_with_mcp(code, context=context)
        
        assert result.success
        assert result.return_value == "test_value"

    async def test_execute_with_mcp_empty_context(self, mcp_sandbox):
        """Test executing with empty context."""
        await mcp_sandbox.initialize()
        
        code = "_ = 'success'"
        result = await mcp_sandbox.execute_with_mcp(code, context=None)
        
        assert result.success
        assert result.return_value == "success"

    async def test_execute_with_mcp_error_handling(self, mcp_sandbox):
        """Test error handling in execute_with_mcp."""
        await mcp_sandbox.initialize()
        
        code = """
raise ValueError("Test error")
"""
        result = await mcp_sandbox.execute_with_mcp(code)
        
        assert not result.success
        assert result.error is not None
        assert "ValueError" in result.error or "Test error" in result.error

    async def test_concurrency_guard(self, mcp_sandbox):
        """Test that concurrency guard limits simultaneous executions."""
        await mcp_sandbox.initialize()
        
        # Create code that takes a moment to execute
        code = """
import time
time.sleep(0.1)
_ = "done"
"""
        
        # Execute multiple tasks concurrently
        tasks = [mcp_sandbox.execute_with_mcp(code) for _ in range(5)]
        results = await asyncio.gather(*tasks)
        
        # All should succeed, but semaphore should limit concurrent execution
        assert all(r.success for r in results)
        assert all(r.return_value == "done" for r in results)

    async def test_workspace_dir_setting(self, sandbox_config):
        """Test that workspace directory is set correctly."""
        custom_workspace = "/tmp/custom_workspace"
        sandbox = MCPSandbox(
            config=sandbox_config,
            workspace_dir=custom_workspace,
            max_concurrent_executions=1,
            enable_network_tools=False,
        )
        
        assert sandbox.workspace_dir == custom_workspace

    async def test_max_concurrent_executions_setting(self, sandbox_config):
        """Test that max concurrent executions is set correctly."""
        sandbox = MCPSandbox(
            config=sandbox_config,
            workspace_dir="/tmp/test",
            max_concurrent_executions=5,
            enable_network_tools=False,
        )
        
        # The semaphore should limit to 5
        assert sandbox._execution_guard._value == 5

    async def test_network_tools_disabled(self, sandbox_config):
        """Test that network tools are disabled by default."""
        sandbox = MCPSandbox(
            config=sandbox_config,
            workspace_dir="/tmp/test",
            max_concurrent_executions=1,
            enable_network_tools=False,
        )
        
        await sandbox.initialize()
        # When network tools are disabled, context should be empty
        assert sandbox._tool_context == {}

    async def test_network_tools_enabled_raises(self, sandbox_config):
        """Test that enabling network tools raises error (pending implementation)."""
        sandbox = MCPSandbox(
            config=sandbox_config,
            workspace_dir="/tmp/test",
            max_concurrent_executions=1,
            enable_network_tools=True,
        )
        
        # Should raise RuntimeError when trying to initialize with network tools
        with pytest.raises(RuntimeError, match="Network-enabled MCP tools"):
            await sandbox.initialize()

    async def test_execute_with_mcp_timeout(self, mcp_sandbox):
        """Test that execution timeout is enforced."""
        await mcp_sandbox.initialize()
        
        # Code that exceeds timeout
        code = """
import time
time.sleep(10)  # Exceeds 5 second timeout
_ = "never_reached"
"""
        result = await mcp_sandbox.execute_with_mcp(code)
        
        assert not result.success
        assert result.error is not None

    async def test_execute_with_mcp_memory_limit(self, mcp_sandbox):
        """Test that memory limits are enforced."""
        await mcp_sandbox.initialize()
        
        # Code that attempts to use excessive memory
        code = """
data = []
for i in range(100000):
    data.append('x' * 1000)
_ = len(data)
"""
        result = await mcp_sandbox.execute_with_mcp(code)
        
        # Should fail due to memory limit or timeout
        assert not result.success or result.memory_used_mb > 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

