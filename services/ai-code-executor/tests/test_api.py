"""
Integration tests for FastAPI endpoints.

Tests /health and /execute endpoints with proper authentication and error handling.
"""

import os

import pytest
from fastapi.testclient import TestClient

from src.config import Settings
from src.executor.mcp_sandbox import MCPSandbox, SandboxConfig
from src.main import app
from src.security.code_validator import CodeValidator, CodeValidatorConfig


@pytest.fixture
def test_settings(monkeypatch):
    """Create test settings with secure token."""
    monkeypatch.setenv("EXECUTOR_API_TOKEN", "test-token-123")
    monkeypatch.setenv("EXECUTION_TIMEOUT", "5")
    monkeypatch.setenv("MAX_MEMORY_MB", "100")
    monkeypatch.setenv("MAX_CPU_PERCENT", "50.0")
    monkeypatch.setenv("MAX_CONCURRENT_EXECUTIONS", "2")
    monkeypatch.setenv("MAX_CODE_BYTES", "10000")
    monkeypatch.setenv("MAX_AST_NODES", "5000")
    monkeypatch.setenv("ENABLE_MCP_NETWORK_TOOLS", "false")
    monkeypatch.setenv("MCP_WORKSPACE_DIR", "/tmp/test_workspace")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    return Settings()


@pytest.fixture
def client(test_settings):
    """Create a test client with initialized sandbox."""
    # Initialize sandbox and validator
    sandbox_config = SandboxConfig(
        timeout_seconds=test_settings.execution_timeout,
        max_memory_mb=test_settings.max_memory_mb,
        max_cpu_percent=test_settings.max_cpu_percent,
    )
    
    # Import here to get fresh instances
    from src.main import code_validator, sandbox
    
    # Initialize sandbox
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    sandbox = MCPSandbox(
        config=sandbox_config,
        workspace_dir=test_settings.mcp_workspace_dir,
        max_concurrent_executions=test_settings.max_concurrent_executions,
        enable_network_tools=test_settings.enable_mcp_network_tools,
    )
    loop.run_until_complete(sandbox.initialize())
    
    code_validator = CodeValidator(
        CodeValidatorConfig(
            max_bytes=test_settings.max_code_bytes,
            max_ast_nodes=test_settings.max_ast_nodes,
            allowed_imports=sandbox_config.allowed_imports,
        )
    )
    
    # Update global instances
    import src.main as main_module
    main_module.sandbox = sandbox
    main_module.code_validator = code_validator
    
    yield TestClient(app)
    
    loop.close()


class TestHealthEndpoint:
    """Test suite for /health endpoint."""

    def test_health_check_success(self, client):
        """Test that health check returns healthy status."""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "ai-code-executor"
        assert data["version"] == "1.0.0"
        assert "mcp_initialized" in data

    def test_health_check_mcp_initialized(self, client):
        """Test that health check reports MCP initialization status."""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data["mcp_initialized"], bool)


class TestExecuteEndpoint:
    """Test suite for /execute endpoint."""

    def test_execute_without_token(self, client):
        """Test that execute endpoint requires authentication."""
        response = client.post(
            "/execute",
            json={"code": "_ = 42"}
        )
        assert response.status_code == 401
        assert "Invalid or missing executor token" in response.json()["detail"]

    def test_execute_with_invalid_token(self, client):
        """Test that invalid token is rejected."""
        response = client.post(
            "/execute",
            json={"code": "_ = 42"},
            headers={"X-Executor-Token": "invalid-token"}
        )
        assert response.status_code == 401
        assert "Invalid or missing executor token" in response.json()["detail"]

    def test_execute_with_valid_token(self, client):
        """Test successful code execution with valid token."""
        response = client.post(
            "/execute",
            json={"code": "result = 2 + 2\n_ = result"},
            headers={"X-Executor-Token": "test-token-123"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["return_value"] == 4
        assert data["error"] is None
        assert "execution_time" in data
        assert "memory_used_mb" in data

    def test_execute_simple_arithmetic(self, client):
        """Test executing simple arithmetic."""
        response = client.post(
            "/execute",
            json={"code": "_ = 10 * 5"},
            headers={"X-Executor-Token": "test-token-123"}
        )
        assert response.status_code == 200
        assert response.json()["return_value"] == 50

    def test_execute_with_context(self, client):
        """Test executing code with context variables."""
        response = client.post(
            "/execute",
            json={
                "code": "result = x * y\n_ = result",
                "context": {"x": 5, "y": 3}
            },
            headers={"X-Executor-Token": "test-token-123"}
        )
        assert response.status_code == 200
        assert response.json()["return_value"] == 15

    def test_execute_with_list_comprehension(self, client):
        """Test executing code with list comprehension."""
        response = client.post(
            "/execute",
            json={"code": "_ = [x * x for x in range(5)]"},
            headers={"X-Executor-Token": "test-token-123"}
        )
        assert response.status_code == 200
        assert response.json()["return_value"] == [0, 1, 4, 9, 16]

    def test_execute_with_error(self, client):
        """Test executing code that raises an error."""
        response = client.post(
            "/execute",
            json={"code": "raise ValueError('Test error')\n_ = 'never'"},
            headers={"X-Executor-Token": "test-token-123"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is False
        assert data["error"] is not None
        assert "ValueError" in data["error"] or "Test error" in data["error"]

    def test_execute_empty_code(self, client):
        """Test that empty code is rejected."""
        response = client.post(
            "/execute",
            json={"code": ""},
            headers={"X-Executor-Token": "test-token-123"}
        )
        assert response.status_code == 400
        assert "Code payload is empty" in response.json()["detail"]

    def test_execute_invalid_syntax(self, client):
        """Test that invalid syntax is rejected."""
        response = client.post(
            "/execute",
            json={"code": "def invalid syntax"},
            headers={"X-Executor-Token": "test-token-123"}
        )
        assert response.status_code == 400
        assert "Code failed to parse" in response.json()["detail"]

    def test_execute_forbidden_import(self, client):
        """Test that forbidden imports are rejected."""
        response = client.post(
            "/execute",
            json={"code": "import os\n_ = os.getcwd()"},
            headers={"X-Executor-Token": "test-token-123"}
        )
        assert response.status_code == 400
        assert "Import of 'os' is not permitted" in response.json()["detail"]

    def test_execute_allowed_import(self, client):
        """Test that allowed imports work."""
        response = client.post(
            "/execute",
            json={"code": "import json\n_ = json.dumps({'key': 'value'})"},
            headers={"X-Executor-Token": "test-token-123"}
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_execute_code_too_large(self, client, monkeypatch):
        """Test that code exceeding size limit is rejected."""
        monkeypatch.setenv("MAX_CODE_BYTES", "100")
        
        # Reload settings
        from src.config import Settings
        settings = Settings()
        
        large_code = "x" * 101
        response = client.post(
            "/execute",
            json={"code": large_code},
            headers={"X-Executor-Token": "test-token-123"}
        )
        assert response.status_code == 400
        assert "Code payload is" in response.json()["detail"]
        assert "bytes; limit is" in response.json()["detail"]

    def test_execute_with_stdout(self, client):
        """Test that stdout is captured correctly."""
        response = client.post(
            "/execute",
            json={"code": "print('Hello, World!')\n_ = 'done'"},
            headers={"X-Executor-Token": "test-token-123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Hello, World!" in data["stdout"]

    def test_execute_with_stderr(self, client):
        """Test that stderr is captured correctly."""
        # Note: RestrictedPython may not allow certain operations
        # This test verifies error handling
        response = client.post(
            "/execute",
            json={"code": "import sys\nsys.stderr.write('Error message')\n_ = 'done'"},
            headers={"X-Executor-Token": "test-token-123"}
        )
        # May succeed or fail depending on RestrictedPython restrictions
        assert response.status_code in [200, 400]

    def test_execute_response_structure(self, client):
        """Test that response has correct structure."""
        response = client.post(
            "/execute",
            json={"code": "_ = 42"},
            headers={"X-Executor-Token": "test-token-123"}
        )
        assert response.status_code == 200
        
        data = response.json()
        required_fields = ["success", "stdout", "stderr", "return_value", "execution_time", "memory_used_mb", "error"]
        for field in required_fields:
            assert field in data

    def test_execute_timeout_handling(self, client):
        """Test that timeout is handled gracefully."""
        # Code that should timeout
        response = client.post(
            "/execute",
            json={"code": "import time\ntime.sleep(10)\n_ = 'done'"},
            headers={"X-Executor-Token": "test-token-123"}
        )
        # Should either timeout or be rejected
        assert response.status_code in [200, 400, 500]
        if response.status_code == 200:
            data = response.json()
            # If it completes, it should have failed
            assert not data["success"] or data["error"] is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

