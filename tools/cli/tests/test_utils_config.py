"""Tests for configuration utilities."""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch

from src.utils.config import CLIConfig, load_config, save_config, get_default_config_path

class TestCLIConfig:
    """Test CLIConfig class."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = CLIConfig()
        
        assert config.api_url == "http://localhost:8000"
        assert config.api_token is None
        assert config.timeout == 30
        assert config.retries == 3
        assert config.output_format == "table"
        assert config.verbose is False
    
    def test_config_with_values(self):
        """Test configuration with custom values."""
        config = CLIConfig(
            api_url="http://test:9000",
            api_token="test-token",
            timeout=60,
            retries=5,
            output_format="json",
            verbose=True
        )
        
        assert config.api_url == "http://test:9000"
        assert config.api_token == "test-token"
        assert config.timeout == 60
        assert config.retries == 5
        assert config.output_format == "json"
        assert config.verbose is True
    
    def test_config_dict(self):
        """Test configuration to dict conversion."""
        config = CLIConfig(
            api_url="http://test:9000",
            api_token="test-token",
            timeout=60
        )
        
        config_dict = config.dict()
        
        assert config_dict["api_url"] == "http://test:9000"
        assert config_dict["api_token"] == "test-token"
        assert config_dict["timeout"] == 60
        assert config_dict["retries"] == 3  # default value
        assert config_dict["output_format"] == "table"  # default value
        assert config_dict["verbose"] is False  # default value

class TestLoadConfig:
    """Test load_config function."""
    
    def test_load_config_default(self):
        """Test loading default configuration."""
        config = load_config()
        
        assert config.api_url == "http://localhost:8000"
        assert config.api_token is None
        assert config.timeout == 30
        assert config.retries == 3
        assert config.output_format == "table"
        assert config.verbose is False
    
    @patch.dict(os.environ, {
        "HA_INGESTOR_API_URL": "http://env:8000",
        "HA_INGESTOR_API_TOKEN": "env-token",
        "HA_INGESTOR_TIMEOUT": "60",
        "HA_INGESTOR_RETRIES": "5",
        "HA_INGESTOR_OUTPUT_FORMAT": "json",
        "HA_INGESTOR_VERBOSE": "true"
    })
    def test_load_config_from_env(self):
        """Test loading configuration from environment variables."""
        config = load_config()
        
        assert config.api_url == "http://env:8000"
        assert config.api_token == "env-token"
        assert config.timeout == 60
        assert config.retries == 5
        assert config.output_format == "json"
        assert config.verbose is True
    
    def test_load_config_from_file(self):
        """Test loading configuration from file."""
        import yaml
        
        # Create temporary config file
        config_data = {
            "api_url": "http://file:8000",
            "api_token": "file-token",
            "timeout": 90,
            "retries": 7,
            "output_format": "yaml",
            "verbose": True
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_file = f.name
        
        try:
            config = load_config(temp_file)
            
            assert config.api_url == "http://file:8000"
            assert config.api_token == "file-token"
            assert config.timeout == 90
            assert config.retries == 7
            assert config.output_format == "yaml"
            assert config.verbose is True
        finally:
            os.unlink(temp_file)
    
    def test_load_config_file_not_found(self):
        """Test loading configuration from non-existent file."""
        config = load_config("nonexistent.yaml")
        
        # Should return default config
        assert config.api_url == "http://localhost:8000"
        assert config.api_token is None
    
    @patch.dict(os.environ, {"HA_INGESTOR_CONFIG": ""})
    def test_load_config_env_var_empty(self):
        """Test loading configuration with empty env var."""
        config = load_config()
        
        # Should return default config
        assert config.api_url == "http://localhost:8000"

class TestSaveConfig:
    """Test save_config function."""
    
    def test_save_config(self):
        """Test saving configuration to file."""
        import yaml
        
        config = CLIConfig(
            api_url="http://save:8000",
            api_token="save-token",
            timeout=120
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            temp_file = f.name
        
        try:
            save_config(config, temp_file)
            
            # Verify file was created and contains correct data
            assert os.path.exists(temp_file)
            
            with open(temp_file, 'r') as f:
                saved_data = yaml.safe_load(f)
            
            assert saved_data["api_url"] == "http://save:8000"
            assert saved_data["api_token"] == "save-token"
            assert saved_data["timeout"] == 120
            assert saved_data["retries"] == 3  # default value
        finally:
            os.unlink(temp_file)
    
    def test_save_config_create_directory(self):
        """Test saving configuration creates directory if needed."""
        import yaml
        
        config = CLIConfig(api_url="http://test:8000")
        
        # Use a path that doesn't exist
        temp_dir = tempfile.mkdtemp()
        config_file = os.path.join(temp_dir, "subdir", "config.yaml")
        
        try:
            save_config(config, config_file)
            
            # Verify directory was created and file was saved
            assert os.path.exists(config_file)
            
            with open(config_file, 'r') as f:
                saved_data = yaml.safe_load(f)
            
            assert saved_data["api_url"] == "http://test:8000"
        finally:
            # Clean up
            import shutil
            shutil.rmtree(temp_dir)

class TestGetDefaultConfigPath:
    """Test get_default_config_path function."""
    
    @patch('src.utils.config.Path.home')
    def test_get_default_config_path(self, mock_home):
        """Test getting default configuration path."""
        mock_home.return_value = Path("/home/test")
        
        default_path = get_default_config_path()
        
        expected_path = Path("/home/test/.homeiq/config.yaml")
        assert default_path == expected_path
