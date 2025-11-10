"""Tests for configuration management commands."""

import pytest
import typer
from typer.testing import CliRunner
from unittest.mock import patch, AsyncMock
from pathlib import Path
import tempfile
import os

from src.commands.config import app

runner = CliRunner()

class TestConfigCommands:
    """Test configuration management commands."""
    
    @patch('src.commands.config.load_config')
    def test_show_config(self, mock_load_config):
        """Test show config command."""
        # Mock configuration
        mock_config = mock_load_config.return_value
        mock_config.dict.return_value = {
            "api_url": "http://localhost:8000",
            "api_token": "test-token",
            "timeout": 30,
            "retries": 3,
            "output_format": "table",
            "verbose": False
        }
        
        result = runner.invoke(app, ["show"])
        assert result.exit_code == 0
        assert "Current Configuration" in result.output
    
    @patch('src.commands.config.load_config')
    def test_show_config_json_format(self, mock_load_config):
        """Test show config command with JSON format."""
        # Mock configuration
        mock_config = mock_load_config.return_value
        mock_config.dict.return_value = {
            "api_url": "http://localhost:8000",
            "api_token": "test-token",
            "timeout": 30,
            "retries": 3,
            "output_format": "table",
            "verbose": False
        }
        
        result = runner.invoke(app, ["show", "--format", "json"])
        assert result.exit_code == 0
        assert "api_url" in result.output
        assert "http://localhost:8000" in result.output
    
    @patch('src.commands.config.load_config')
    def test_get_config_value(self, mock_load_config):
        """Test get config value command."""
        # Mock configuration
        mock_config = mock_load_config.return_value
        mock_config.dict.return_value = {
            "api_url": "http://localhost:8000",
            "api_token": "test-token",
            "timeout": 30,
            "retries": 3,
            "output_format": "table",
            "verbose": False
        }
        
        result = runner.invoke(app, ["get", "api_url"])
        assert result.exit_code == 0
        assert "api_url: http://localhost:8000" in result.output
    
    @patch('src.commands.config.load_config')
    def test_get_config_value_not_found(self, mock_load_config):
        """Test get config value command with invalid key."""
        # Mock configuration
        mock_config = mock_load_config.return_value
        mock_config.dict.return_value = {
            "api_url": "http://localhost:8000",
            "api_token": "test-token",
            "timeout": 30,
            "retries": 3,
            "output_format": "table",
            "verbose": False
        }
        
        result = runner.invoke(app, ["get", "invalid_key"])
        assert result.exit_code == 1
        assert "Configuration key 'invalid_key' not found" in result.output
    
    @patch('src.commands.config.load_config')
    @patch('src.commands.config.save_config')
    def test_set_config_value(self, mock_save_config, mock_load_config):
        """Test set config value command."""
        # Mock configuration
        mock_config = mock_load_config.return_value
        
        result = runner.invoke(app, ["set", "api_url", "http://new-url:8000"])
        assert result.exit_code == 0
        assert "Set api_url = http://new-url:8000" in result.output
        mock_save_config.assert_called_once()
    
    @patch('src.commands.config.load_config')
    @patch('src.commands.config.save_config')
    def test_set_config_value_invalid_key(self, mock_save_config, mock_load_config):
        """Test set config value command with invalid key."""
        # Mock configuration
        mock_config = mock_load_config.return_value
        
        result = runner.invoke(app, ["set", "invalid_key", "value"])
        assert result.exit_code == 1
        assert "Invalid configuration key" in result.output
    
    @patch('src.commands.config.load_config')
    @patch('src.commands.config.save_config')
    def test_set_config_value_invalid_int(self, mock_save_config, mock_load_config):
        """Test set config value command with invalid integer."""
        # Mock configuration
        mock_config = mock_load_config.return_value
        
        result = runner.invoke(app, ["set", "timeout", "invalid"])
        assert result.exit_code == 1
        assert "Value for 'timeout' must be an integer" in result.output
    
    @patch('src.commands.config.save_config')
    @patch('src.commands.config.get_default_config_path')
    def test_init_config(self, mock_get_default_path, mock_save_config):
        """Test init config command."""
        # Mock default path
        mock_path = Path("/tmp/test-config.yaml")
        mock_get_default_path.return_value = mock_path
        
        result = runner.invoke(app, ["init", "--api-url", "http://test:8000"])
        assert result.exit_code == 0
        assert "Configuration initialized" in result.output
        mock_save_config.assert_called_once()
    
    @patch('src.commands.config.load_config')
    @patch('src.commands.config.APIClient')
    def test_get_remote_config(self, mock_api_client, mock_load_config):
        """Test get remote config command."""
        # Mock configuration
        mock_config = mock_load_config.return_value
        mock_config.verbose = False
        
        # Mock API client
        mock_client_instance = mock_api_client.return_value
        mock_client_instance.test_connection = AsyncMock(return_value=True)
        mock_client_instance.get_configuration = AsyncMock(return_value={
            "websocket_ingestion": {
                "home_assistant_url": "http://localhost:8123",
                "home_assistant_token": "***"
            },
            "weather_enrichment": {
                "api_key": "***",
                "enabled": True
            }
        })
        mock_client_instance.close = AsyncMock()
        
        result = runner.invoke(app, ["remote"])
        assert result.exit_code == 0
        assert "Remote System Configuration" in result.output
    
    @patch('src.commands.config.load_config')
    @patch('src.commands.config.APIClient')
    def test_update_remote_config(self, mock_api_client, mock_load_config):
        """Test update remote config command."""
        # Mock configuration
        mock_config = mock_load_config.return_value
        mock_config.verbose = False
        
        # Mock API client
        mock_client_instance = mock_api_client.return_value
        mock_client_instance.test_connection = AsyncMock(return_value=True)
        mock_client_instance.update_configuration = AsyncMock(return_value={
            "status": "success",
            "message": "Configuration updated"
        })
        mock_client_instance.close = AsyncMock()
        
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"test": "value"}')
            temp_file = f.name
        
        try:
            result = runner.invoke(app, ["update", temp_file])
            assert result.exit_code == 0
            assert "Remote configuration updated successfully" in result.output
        finally:
            os.unlink(temp_file)
    
    @patch('src.commands.config.load_config')
    def test_update_remote_config_file_not_found(self, mock_load_config):
        """Test update remote config command with non-existent file."""
        # Mock configuration
        mock_config = mock_load_config.return_value
        
        result = runner.invoke(app, ["update", "nonexistent.json"])
        assert result.exit_code == 1
        assert "Configuration file 'nonexistent.json' not found" in result.output
