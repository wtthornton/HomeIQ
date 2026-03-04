"""Configuration management for CLI tools."""

import os
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field


class CLIConfig(BaseModel):
    """CLI configuration model."""
    
    api_url: str = Field(default="http://localhost:8000", description="Admin API URL")
    api_token: Optional[str] = Field(default=None, description="API authentication token")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    retries: int = Field(default=3, description="Number of retry attempts")
    output_format: str = Field(default="table", description="Default output format")
    verbose: bool = Field(default=False, description="Enable verbose output")
    
    class Config:
        env_prefix = "HA_INGESTOR_"

def load_config(config_file: Optional[str] = None) -> CLIConfig:
    """
    Load configuration from file and environment variables.
    
    Args:
        config_file: Path to configuration file
        
    Returns:
        CLIConfig: Loaded configuration
    """
    # Load environment variables
    load_dotenv()
    
    # Default configuration
    config_data = {
        "api_url": os.getenv("HA_INGESTOR_API_URL", "http://localhost:8000"),
        "api_token": os.getenv("HA_INGESTOR_API_TOKEN"),
        "timeout": int(os.getenv("HA_INGESTOR_TIMEOUT", "30")),
        "retries": int(os.getenv("HA_INGESTOR_RETRIES", "3")),
        "output_format": os.getenv("HA_INGESTOR_OUTPUT_FORMAT", "table"),
        "verbose": os.getenv("HA_INGESTOR_VERBOSE", "false").lower() == "true",
    }
    
    # Load from config file if provided
    if config_file:
        config_path = Path(config_file)
        if config_path.exists():
            with open(config_path, 'r') as f:
                file_config = yaml.safe_load(f) or {}
                config_data.update(file_config)
    
    # Try to load from default config file
    elif os.getenv("HA_INGESTOR_CONFIG"):
        config_path = Path(os.getenv("HA_INGESTOR_CONFIG"))
        if config_path.exists():
            with open(config_path, 'r') as f:
                file_config = yaml.safe_load(f) or {}
                config_data.update(file_config)
    
    # Try to load from default locations
    else:
        default_paths = [
            Path.home() / ".homeiq" / "config.yaml",
            Path.cwd() / "homeiq.yaml",
            Path.cwd() / ".homeiq.yaml",
        ]
        
        for config_path in default_paths:
            if config_path.exists():
                with open(config_path, 'r') as f:
                    file_config = yaml.safe_load(f) or {}
                    config_data.update(file_config)
                break
    
    return CLIConfig(**config_data)

def save_config(config: CLIConfig, config_file: str) -> None:
    """
    Save configuration to file.
    
    Args:
        config: Configuration to save
        config_file: Path to save configuration file
    """
    config_path = Path(config_file)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_path, 'w') as f:
        yaml.dump(config.dict(), f, default_flow_style=False, indent=2)

def get_default_config_path() -> Path:
    """Get the default configuration file path."""
    return Path.home() / ".homeiq" / "config.yaml"
