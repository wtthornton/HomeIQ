"""Configuration management CLI commands."""

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from ..utils.api_client import APIClient
from ..utils.config import get_default_config_path, load_config, save_config
from ..utils.output import OutputFormatter

app = typer.Typer(name="config", help="Configuration management commands")
console = Console()

@app.command("show")
def show_config(
    format: str = typer.Option("table", "--format", "-f", help="Output format (table, json, yaml)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output")
):
    """Show current configuration."""
    try:
        config = load_config()
        config.verbose = verbose
        
        formatter = OutputFormatter(console)
        
        # Convert config to dict for display
        config_dict = config.dict()
        
        if format == "json":
            formatter.print_json(config_dict, "Current Configuration")
        elif format == "yaml":
            formatter.print_yaml(config_dict, "Current Configuration")
        else:
            formatter.print_header("Current Configuration")
            formatter.print_table([config_dict])
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

@app.command("get")
def get_config_value(
    key: str = typer.Argument(..., help="Configuration key to get"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output")
):
    """Get a specific configuration value."""
    try:
        config = load_config()
        config.verbose = verbose
        
        formatter = OutputFormatter(console)
        
        # Get value from config
        config_dict = config.dict()
        if key in config_dict:
            value = config_dict[key]
            formatter.print_info(f"{key}: {value}")
        else:
            formatter.print_error(f"Configuration key '{key}' not found")
            raise typer.Exit(1)
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

@app.command("set")
def set_config_value(
    key: str = typer.Argument(..., help="Configuration key to set"),
    value: str = typer.Argument(..., help="Value to set"),
    config_file: Optional[str] = typer.Option(None, "--config-file", "-c", help="Configuration file path"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output")
):
    """Set a configuration value."""
    try:
        config = load_config(config_file)
        config.verbose = verbose
        
        formatter = OutputFormatter(console)
        
        # Validate key
        valid_keys = ["api_url", "api_token", "timeout", "retries", "output_format", "verbose"]
        if key not in valid_keys:
            formatter.print_error(f"Invalid configuration key '{key}'. Valid keys: {', '.join(valid_keys)}")
            raise typer.Exit(1)
        
        # Convert value to appropriate type
        if key in ["timeout", "retries"]:
            try:
                value = int(value)
            except ValueError:
                formatter.print_error(f"Value for '{key}' must be an integer")
                raise typer.Exit(1)
        elif key == "verbose":
            value = value.lower() in ["true", "1", "yes", "on"]
        
        # Set value
        setattr(config, key, value)
        
        # Save to file
        if config_file:
            save_config(config, config_file)
        else:
            default_path = get_default_config_path()
            save_config(config, str(default_path))
        
        formatter.print_success(f"Set {key} = {value}")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

@app.command("init")
def init_config(
    config_file: Optional[str] = typer.Option(None, "--config-file", "-c", help="Configuration file path"),
    api_url: str = typer.Option("http://localhost:8000", "--api-url", help="Admin API URL"),
    api_token: Optional[str] = typer.Option(None, "--api-token", help="API authentication token"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output")
):
    """Initialize configuration file."""
    try:
        formatter = OutputFormatter(console)
        
        # Create default config
        from ..utils.config import CLIConfig
        config = CLIConfig(
            api_url=api_url,
            api_token=api_token,
            verbose=verbose
        )
        
        # Save to file
        if config_file:
            save_path = Path(config_file)
        else:
            save_path = get_default_config_path()
        
        save_config(config, str(save_path))
        
        formatter.print_success(f"Configuration initialized at {save_path}")
        formatter.print_info("You can now use 'homeiq-cli config show' to view the configuration")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

@app.command("remote")
def get_remote_config(
    format: str = typer.Option("table", "--format", "-f", help="Output format (table, json, yaml)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output")
):
    """Get remote system configuration."""
    try:
        config = load_config()
        config.verbose = verbose
        
        formatter = OutputFormatter(console)
        
        async def _get_remote_config():
            client = APIClient(config)
            
            try:
                # Test connection first
                if not await client.test_connection():
                    formatter.print_error("Cannot connect to Admin API")
                    return
                
                # Get remote configuration
                remote_config = await client.get_configuration()
                
                if format == "json":
                    formatter.print_json(remote_config, "Remote System Configuration")
                elif format == "yaml":
                    formatter.print_yaml(remote_config, "Remote System Configuration")
                else:
                    formatter.print_header("Remote System Configuration")
                    formatter.print_tree(remote_config)
                
            finally:
                await client.close()
        
        import asyncio
        asyncio.run(_get_remote_config())
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

@app.command("update")
def update_remote_config(
    config_file: str = typer.Argument(..., help="Configuration file to upload"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output")
):
    """Update remote system configuration."""
    try:
        config = load_config()
        config.verbose = verbose
        
        formatter = OutputFormatter(console)
        
        # Load configuration file
        config_path = Path(config_file)
        if not config_path.exists():
            formatter.print_error(f"Configuration file '{config_file}' not found")
            raise typer.Exit(1)
        
        with open(config_path, 'r') as f:
            config_data = json.load(f)
        
        async def _update_remote_config():
            client = APIClient(config)
            
            try:
                # Test connection first
                if not await client.test_connection():
                    formatter.print_error("Cannot connect to Admin API")
                    return
                
                # Update remote configuration
                with formatter.print_progress("Updating remote configuration..."):
                    result = await client.update_configuration(config_data)
                
                formatter.print_success("Remote configuration updated successfully")
                
                if verbose:
                    formatter.print_json(result, "Update Result")
                
            finally:
                await client.close()
        
        import asyncio
        asyncio.run(_update_remote_config())
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
