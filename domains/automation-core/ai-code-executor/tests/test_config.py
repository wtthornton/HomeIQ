"""
Unit tests for Settings configuration.

Tests configuration loading, validation, and edge cases.
"""

import os
import warnings

import pytest

from src.config import Settings


class TestSettings:
    """Test suite for Settings configuration."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        settings = Settings()
        assert settings.service_name == "ai-code-executor"
        assert settings.service_port == 8030
        assert settings.execution_timeout == 30
        assert settings.max_memory_mb == 128
        assert settings.max_cpu_percent == 50.0
        assert settings.max_concurrent_executions == 2
        assert settings.max_code_bytes == 10_000
        assert settings.max_ast_nodes == 5_000
        assert settings.enable_mcp_network_tools is False
        assert settings.mcp_workspace_dir == "/tmp/mcp_workspace"
        assert settings.log_level == "INFO"

    def test_allowed_origins_default(self):
        """Test default allowed origins."""
        settings = Settings()
        assert settings.allowed_origins == ["http://localhost:8030"]

    def test_allowed_origins_from_env_string(self, monkeypatch):
        """Test parsing allowed origins from comma-separated string."""
        monkeypatch.setenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8030,https://example.com")
        settings = Settings()
        assert len(settings.allowed_origins) == 3
        assert "http://localhost:3000" in settings.allowed_origins
        assert "http://localhost:8030" in settings.allowed_origins
        assert "https://example.com" in settings.allowed_origins

    def test_allowed_origins_with_spaces(self, monkeypatch):
        """Test parsing allowed origins with spaces."""
        monkeypatch.setenv("ALLOWED_ORIGINS", "http://localhost:3000, http://localhost:8030 , https://example.com")
        settings = Settings()
        assert len(settings.allowed_origins) == 3
        assert all(origin.strip() == origin for origin in settings.allowed_origins)

    def test_allowed_origins_empty_string(self, monkeypatch):
        """Test parsing empty allowed origins string."""
        monkeypatch.setenv("ALLOWED_ORIGINS", "")
        settings = Settings()
        assert settings.allowed_origins == []

    def test_api_token_default_warning(self, monkeypatch):
        """Test that default API token generates warning in development."""
        # Ensure not in production
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        monkeypatch.setenv("EXECUTOR_API_TOKEN", "local-dev-token")
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            settings = Settings()
            assert len(w) == 1
            assert issubclass(w[0].category, UserWarning)
            assert "default or weak API token" in str(w[0].message)

    def test_api_token_empty_warning(self, monkeypatch):
        """Test that empty API token generates warning."""
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        monkeypatch.setenv("EXECUTOR_API_TOKEN", "")
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            settings = Settings()
            assert len(w) == 1

    def test_api_token_production_validation(self, monkeypatch):
        """Test that production requires secure API token."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("EXECUTOR_API_TOKEN", "local-dev-token")
        
        with pytest.raises(ValueError, match="EXECUTOR_API_TOKEN must be set to a secure value"):
            Settings()

    def test_api_token_production_empty(self, monkeypatch):
        """Test that production rejects empty token."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("EXECUTOR_API_TOKEN", "")
        
        with pytest.raises(ValueError, match="EXECUTOR_API_TOKEN must be set to a secure value"):
            Settings()

    def test_api_token_production_secure(self, monkeypatch):
        """Test that production accepts secure token."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("EXECUTOR_API_TOKEN", "secure-random-token-12345")
        
        settings = Settings()
        assert settings.api_token == "secure-random-token-12345"

    def test_api_token_production_test_token(self, monkeypatch):
        """Test that production rejects test token."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("EXECUTOR_API_TOKEN", "test-token")
        
        with pytest.raises(ValueError, match="EXECUTOR_API_TOKEN must be set to a secure value"):
            Settings()

    def test_execution_timeout_from_env(self, monkeypatch):
        """Test loading execution timeout from environment."""
        monkeypatch.setenv("EXECUTION_TIMEOUT", "60")
        settings = Settings()
        assert settings.execution_timeout == 60

    def test_max_memory_mb_from_env(self, monkeypatch):
        """Test loading max memory from environment."""
        monkeypatch.setenv("MAX_MEMORY_MB", "256")
        settings = Settings()
        assert settings.max_memory_mb == 256

    def test_max_cpu_percent_from_env(self, monkeypatch):
        """Test loading max CPU percent from environment."""
        monkeypatch.setenv("MAX_CPU_PERCENT", "75.5")
        settings = Settings()
        assert settings.max_cpu_percent == 75.5

    def test_max_concurrent_executions_from_env(self, monkeypatch):
        """Test loading max concurrent executions from environment."""
        monkeypatch.setenv("MAX_CONCURRENT_EXECUTIONS", "5")
        settings = Settings()
        assert settings.max_concurrent_executions == 5

    def test_max_code_bytes_from_env(self, monkeypatch):
        """Test loading max code bytes from environment."""
        monkeypatch.setenv("MAX_CODE_BYTES", "20000")
        settings = Settings()
        assert settings.max_code_bytes == 20000

    def test_max_ast_nodes_from_env(self, monkeypatch):
        """Test loading max AST nodes from environment."""
        monkeypatch.setenv("MAX_AST_NODES", "10000")
        settings = Settings()
        assert settings.max_ast_nodes == 10000

    def test_enable_mcp_network_tools_from_env(self, monkeypatch):
        """Test loading MCP network tools flag from environment."""
        monkeypatch.setenv("ENABLE_MCP_NETWORK_TOOLS", "true")
        settings = Settings()
        assert settings.enable_mcp_network_tools is True

    def test_mcp_workspace_dir_from_env(self, monkeypatch):
        """Test loading MCP workspace directory from environment."""
        monkeypatch.setenv("MCP_WORKSPACE_DIR", "/custom/workspace")
        settings = Settings()
        assert settings.mcp_workspace_dir == "/custom/workspace"

    def test_log_level_from_env(self, monkeypatch):
        """Test loading log level from environment."""
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        settings = Settings()
        assert settings.log_level == "DEBUG"

    def test_all_settings_from_env(self, monkeypatch):
        """Test loading all settings from environment."""
        monkeypatch.setenv("EXECUTION_TIMEOUT", "45")
        monkeypatch.setenv("MAX_MEMORY_MB", "512")
        monkeypatch.setenv("MAX_CPU_PERCENT", "80.0")
        monkeypatch.setenv("MAX_CONCURRENT_EXECUTIONS", "10")
        monkeypatch.setenv("MAX_CODE_BYTES", "50000")
        monkeypatch.setenv("MAX_AST_NODES", "20000")
        monkeypatch.setenv("ENABLE_MCP_NETWORK_TOOLS", "true")
        monkeypatch.setenv("MCP_WORKSPACE_DIR", "/tmp/custom")
        monkeypatch.setenv("LOG_LEVEL", "WARNING")
        monkeypatch.setenv("EXECUTOR_API_TOKEN", "test-token-123")
        
        settings = Settings()
        assert settings.execution_timeout == 45
        assert settings.max_memory_mb == 512
        assert settings.max_cpu_percent == 80.0
        assert settings.max_concurrent_executions == 10
        assert settings.max_code_bytes == 50000
        assert settings.max_ast_nodes == 20000
        assert settings.enable_mcp_network_tools is True
        assert settings.mcp_workspace_dir == "/tmp/custom"
        assert settings.log_level == "WARNING"
        assert settings.api_token == "test-token-123"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

