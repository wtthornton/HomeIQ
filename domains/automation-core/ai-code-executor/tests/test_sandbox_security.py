"""
Security tests for AI Code Executor sandbox.

Tests filesystem isolation, network isolation, resource limits, and import restrictions.
"""

import asyncio
import os
import tempfile
from pathlib import Path

import pytest

from src.executor.sandbox import PythonSandbox, SandboxConfig, ExecutionResult


@pytest.fixture
def sandbox():
    """Create a sandbox instance for testing."""
    config = SandboxConfig(
        timeout_seconds=5,
        max_memory_mb=100,
        max_cpu_percent=50,
    )
    return PythonSandbox(config=config)


@pytest.mark.asyncio
async def test_filesystem_isolation(sandbox):
    """Test that sandbox cannot access host filesystem."""
    # Attempt to read sensitive files
    malicious_code = """
import os
try:
    with open('/etc/passwd', 'r') as f:
        content = f.read()
    result = "SUCCESS: Read /etc/passwd"
except Exception as e:
    result = f"FAILED: {str(e)}"
result
"""
    result = await sandbox.execute(malicious_code)
    
    assert not result.success or "FAILED" in str(result.return_value) or result.error is not None
    assert "/etc/passwd" not in result.stdout
    assert "/etc/passwd" not in str(result.return_value)


@pytest.mark.asyncio
async def test_filesystem_write_isolation(sandbox):
    """Test that sandbox cannot write to host filesystem."""
    # Attempt to write to sensitive locations
    malicious_code = """
import os
try:
    with open('/tmp/sandbox_escape_test', 'w') as f:
        f.write('ESCAPED')
    result = "SUCCESS: Wrote to /tmp"
except Exception as e:
    result = f"FAILED: {str(e)}"
result
"""
    result = await sandbox.execute(malicious_code)
    
    # Verify file was not created
    assert not Path("/tmp/sandbox_escape_test").exists()
    assert not result.success or "FAILED" in str(result.return_value) or result.error is not None


@pytest.mark.asyncio
async def test_network_isolation(sandbox):
    """Test that sandbox cannot access network."""
    # Attempt to make network requests
    malicious_code = """
import socket
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('8.8.8.8', 53))
    result = "SUCCESS: Network access"
except Exception as e:
    result = f"FAILED: {str(e)}"
result
"""
    result = await sandbox.execute(malicious_code)
    
    assert not result.success or "FAILED" in str(result.return_value) or result.error is not None
    assert "SUCCESS: Network access" not in str(result.return_value)


@pytest.mark.asyncio
async def test_import_restrictions(sandbox):
    """Test that dangerous imports are blocked."""
    # Attempt to import dangerous modules
    dangerous_imports = [
        "import subprocess",
        "import os.system",
        "import sys.exit",
        "import shutil.rmtree",
    ]
    
    for import_stmt in dangerous_imports:
        code = f"""
{import_stmt}
result = "SUCCESS"
result
"""
        result = await sandbox.execute(code)
        
        # Should fail or be blocked
        assert not result.success or result.error is not None or "ImportError" in str(result.error)


@pytest.mark.asyncio
async def test_resource_limits_memory(sandbox):
    """Test that memory limits are enforced."""
    # Code that attempts to allocate excessive memory
    malicious_code = """
data = []
for i in range(1000000):
    data.append('x' * 1000)
result = len(data)
result
"""
    result = await sandbox.execute(malicious_code)
    
    # Should fail due to memory limit or timeout
    assert not result.success or result.error is not None or result.memory_used_mb > 100


@pytest.mark.asyncio
async def test_resource_limits_timeout(sandbox):
    """Test that execution timeout is enforced."""
    # Code that runs indefinitely
    malicious_code = """
import time
while True:
    time.sleep(0.1)
result = "NEVER_REACHED"
result
"""
    result = await sandbox.execute(malicious_code)
    
    # Should timeout
    assert not result.success
    assert result.error is not None or result.execution_time >= 5


@pytest.mark.asyncio
async def test_code_execution_boundaries(sandbox):
    """Test that code execution is properly isolated."""
    # Attempt to escape sandbox using various techniques
    escape_attempts = [
        # Try to access __builtins__
        "__builtins__['__import__']('os').system('ls')",
        # Try to use eval
        "eval('__import__(\"os\").system(\"ls\")')",
        # Try to use exec
        "exec('import os; os.system(\"ls\")')",
    ]
    
    for attempt in escape_attempts:
        code = f"""
result = {attempt}
result
"""
        result = await sandbox.execute(code)
        
        # Should fail or be blocked
        assert not result.success or result.error is not None


@pytest.mark.asyncio
async def test_safe_code_execution(sandbox):
    """Test that safe code executes successfully."""
    # Safe code that should work
    safe_code = """
result = 2 + 2
result
"""
    result = await sandbox.execute(safe_code)
    
    assert result.success
    assert result.return_value == 4
    assert result.error is None


@pytest.mark.asyncio
async def test_context_sanitization(sandbox):
    """Test that context variables are properly sanitized."""
    # Attempt to inject malicious code via context
    malicious_context = {
        "malicious": "__import__('os').system('ls')",
        "safe_value": "test"
    }
    
    code = """
result = malicious
result
"""
    result = await sandbox.execute(code, context=malicious_context)
    
    # Should fail or sanitize the malicious context
    assert not result.success or result.error is not None or "os.system" not in str(result.return_value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

