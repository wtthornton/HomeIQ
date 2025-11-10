"""Tests for system management commands."""

import pytest
import typer
from typer.testing import CliRunner
from unittest.mock import patch, AsyncMock

from src.commands.system import app

runner = CliRunner()

class TestSystemCommands:
    """Test system management commands."""
    
    @patch('src.commands.system.load_config')
    @patch('src.commands.system.APIClient')
    def test_health_check(self, mock_api_client, mock_load_config):
        """Test health check command."""
        # Mock configuration
        mock_config = mock_load_config.return_value
        mock_config.verbose = False
        
        # Mock API client
        mock_client_instance = mock_api_client.return_value
        mock_client_instance.test_connection = AsyncMock(return_value=True)
        mock_client_instance.get_health = AsyncMock(return_value={
            "overall_status": "healthy",
            "admin_api_status": "running",
            "ingestion_service": {
                "status": "healthy",
                "websocket_connection": {
                    "is_connected": True,
                    "last_connection_time": "2024-01-01T12:00:00Z",
                    "connection_attempts": 5,
                    "last_error": None
                },
                "event_processing": {
                    "total_events": 1000,
                    "events_per_minute": 50,
                    "error_rate": 0.01
                }
            }
        })
        mock_client_instance.close = AsyncMock()
        
        result = runner.invoke(app, ["health"])
        assert result.exit_code == 0
        assert "System Health Status" in result.output
    
    @patch('src.commands.system.load_config')
    @patch('src.commands.system.APIClient')
    def test_health_check_json_format(self, mock_api_client, mock_load_config):
        """Test health check command with JSON format."""
        # Mock configuration
        mock_config = mock_load_config.return_value
        mock_config.verbose = False
        
        # Mock API client
        mock_client_instance = mock_api_client.return_value
        mock_client_instance.test_connection = AsyncMock(return_value=True)
        mock_client_instance.get_health = AsyncMock(return_value={
            "overall_status": "healthy",
            "admin_api_status": "running"
        })
        mock_client_instance.close = AsyncMock()
        
        result = runner.invoke(app, ["health", "--format", "json"])
        assert result.exit_code == 0
        assert "overall_status" in result.output
        assert "healthy" in result.output
    
    @patch('src.commands.system.load_config')
    @patch('src.commands.system.APIClient')
    def test_health_check_connection_failed(self, mock_api_client, mock_load_config):
        """Test health check command when connection fails."""
        # Mock configuration
        mock_config = mock_load_config.return_value
        mock_config.verbose = False
        
        # Mock API client
        mock_client_instance = mock_api_client.return_value
        mock_client_instance.test_connection = AsyncMock(return_value=False)
        mock_client_instance.close = AsyncMock()
        
        result = runner.invoke(app, ["health"])
        assert result.exit_code == 0
        assert "Cannot connect to Admin API" in result.output
    
    @patch('src.commands.system.load_config')
    @patch('src.commands.system.APIClient')
    def test_get_statistics(self, mock_api_client, mock_load_config):
        """Test get statistics command."""
        # Mock configuration
        mock_config = mock_load_config.return_value
        mock_config.verbose = False
        
        # Mock API client
        mock_client_instance = mock_api_client.return_value
        mock_client_instance.test_connection = AsyncMock(return_value=True)
        mock_client_instance.get_statistics = AsyncMock(return_value={
            "total_events": 10000,
            "events_today": 500,
            "active_entities": 25,
            "uptime": "2 days, 5 hours"
        })
        mock_client_instance.close = AsyncMock()
        
        result = runner.invoke(app, ["stats"])
        assert result.exit_code == 0
        assert "System Statistics" in result.output
    
    @patch('src.commands.system.load_config')
    @patch('src.commands.system.APIClient')
    def test_get_status(self, mock_api_client, mock_load_config):
        """Test get status command."""
        # Mock configuration
        mock_config = mock_load_config.return_value
        mock_config.verbose = False
        
        # Mock API client
        mock_client_instance = mock_api_client.return_value
        mock_client_instance.test_connection = AsyncMock(return_value=True)
        mock_client_instance.get_health = AsyncMock(return_value={
            "overall_status": "healthy"
        })
        mock_client_instance.get_statistics = AsyncMock(return_value={
            "total_events": 10000,
            "events_today": 500,
            "active_entities": 25
        })
        mock_client_instance.close = AsyncMock()
        
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "System Status" in result.output
        assert "HEALTHY" in result.output
    
    @patch('src.commands.system.load_config')
    @patch('src.commands.system.APIClient')
    def test_ping_api(self, mock_api_client, mock_load_config):
        """Test ping API command."""
        # Mock configuration
        mock_config = mock_load_config.return_value
        mock_config.verbose = False
        mock_config.api_url = "http://localhost:8000"
        
        # Mock API client
        mock_client_instance = mock_api_client.return_value
        mock_client_instance.test_connection = AsyncMock(return_value=True)
        mock_client_instance.close = AsyncMock()
        
        result = runner.invoke(app, ["ping"])
        assert result.exit_code == 0
        assert "API connection successful" in result.output
    
    @patch('src.commands.system.load_config')
    @patch('src.commands.system.APIClient')
    def test_ping_api_failed(self, mock_api_client, mock_load_config):
        """Test ping API command when connection fails."""
        # Mock configuration
        mock_config = mock_load_config.return_value
        mock_config.verbose = False
        mock_config.api_url = "http://localhost:8000"
        
        # Mock API client
        mock_client_instance = mock_api_client.return_value
        mock_client_instance.test_connection = AsyncMock(return_value=False)
        mock_client_instance.close = AsyncMock()
        
        result = runner.invoke(app, ["ping"])
        assert result.exit_code == 0
        assert "API connection failed" in result.output
