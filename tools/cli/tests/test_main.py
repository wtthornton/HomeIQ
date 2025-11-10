"""Tests for the main CLI application."""

import pytest
import typer
from typer.testing import CliRunner
from unittest.mock import patch, AsyncMock

from src.main import app

runner = CliRunner()

class TestMainCLI:
    """Test the main CLI application."""
    
    def test_version_command(self):
        """Test version command."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "HA Ingestor CLI" in result.output
        assert "1.0.0" in result.output
    
    def test_help_command(self):
        """Test help command."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Home Assistant Ingestor CLI Tools" in result.output
    
    def test_verbose_option(self):
        """Test verbose option."""
        result = runner.invoke(app, ["--verbose", "--help"])
        assert result.exit_code == 0
    
    def test_config_option(self):
        """Test config file option."""
        result = runner.invoke(app, ["--config", "test.yaml", "--help"])
        assert result.exit_code == 0
    
    @patch('src.main.load_config')
    @patch('src.main.APIClient')
    def test_info_command(self, mock_api_client, mock_load_config):
        """Test info command."""
        # Mock configuration
        mock_config = mock_load_config.return_value
        
        # Mock API client
        mock_client_instance = mock_api_client.return_value
        mock_health = mock_client_instance.get_health.return_value
        
        # Mock health data structure
        mock_health.overall_status = "healthy"
        mock_health.admin_api_status = "running"
        mock_health.ingestion_service.websocket_connection.is_connected = True
        mock_health.ingestion_service.event_processing.events_per_minute = 50.0
        mock_health.ingestion_service.event_processing.error_rate = 0.01
        mock_health.ingestion_service.weather_enrichment.enabled = True
        mock_health.ingestion_service.influxdb_storage.is_connected = True
        
        result = runner.invoke(app, ["info"])
        assert result.exit_code == 0
        assert "System Status" in result.output
        assert "healthy" in result.output
    
    @patch('src.main.load_config')
    @patch('src.main.APIClient')
    def test_status_command(self, mock_api_client, mock_load_config):
        """Test status command."""
        # Mock configuration
        mock_config = mock_load_config.return_value
        
        # Mock API client
        mock_client_instance = mock_api_client.return_value
        mock_health = mock_client_instance.get_health.return_value
        
        # Mock health data structure
        mock_health.overall_status = "healthy"
        mock_health.timestamp = "2024-01-01T12:00:00Z"
        mock_health.ingestion_service.websocket_connection.is_connected = True
        mock_health.ingestion_service.websocket_connection.connection_attempts = 5
        mock_health.ingestion_service.event_processing.events_per_minute = 50.0
        mock_health.ingestion_service.weather_enrichment.enabled = True
        mock_health.ingestion_service.weather_enrichment.cache_hits = 100
        mock_health.ingestion_service.influxdb_storage.is_connected = True
        mock_health.ingestion_service.influxdb_storage.write_errors = 0
        
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "System Status Overview" in result.output
        assert "Connected" in result.output
    
    def test_version_command_direct(self):
        """Test version command directly."""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "HA Ingestor CLI" in result.output
        assert "1.0.0" in result.output
