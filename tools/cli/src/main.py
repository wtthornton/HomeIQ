#!/usr/bin/env python3
"""
HA Ingestor CLI - Main entry point

Command-line interface for managing and monitoring the Home Assistant Ingestor system.
"""

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from typing import Optional
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.commands.system import app as system_app
from src.commands.events import app as events_app
from src.commands.config import app as config_app
from src.commands.export import app as export_app
from src.commands.diagnostics import app as diagnostics_app
from src.utils.config import load_config
from src.utils.api_client import APIClient

# Initialize Typer app
app = typer.Typer(
    name="homeiq",
    help="Home Assistant Ingestor CLI Tools",
    add_completion=False,
    rich_markup_mode="rich",
)

# Initialize console
console = Console()

# Add subcommands
app.add_typer(system_app, name="system", help="System management commands")
app.add_typer(events_app, name="events", help="Events management commands")
app.add_typer(config_app, name="config", help="Configuration management commands")
app.add_typer(export_app, name="export", help="Data export commands")
app.add_typer(diagnostics_app, name="diagnostics", help="System diagnostics commands")

@app.callback()
def main(
    version: bool = typer.Option(False, "--version", "-v", help="Show version information"),
    verbose: bool = typer.Option(False, "--verbose", help="Enable verbose output"),
    config_file: Optional[str] = typer.Option(None, "--config", "-c", help="Configuration file path"),
):
    """
    Home Assistant Ingestor CLI Tools
    
    Manage and monitor your Home Assistant data ingestion system.
    """
    if version:
        console.print(f"[bold blue]HA Ingestor CLI[/bold blue] version [bold green]1.0.0[/bold green]")
        raise typer.Exit()
    
    # Set global verbose flag
    if verbose:
        os.environ["HA_INGESTOR_VERBOSE"] = "true"
    
    # Load configuration
    if config_file:
        os.environ["HA_INGESTOR_CONFIG"] = config_file

@app.command()
def info():
    """Show system information and status."""
    try:
        config = load_config()
        api_client = APIClient(config.api_url, config.api_token)
        
        # Get system health
        health = api_client.get_health()
        
        # Create info panel
        info_text = f"""
[bold blue]System Status:[/bold blue] {health.overall_status}
[bold blue]Admin API:[/bold blue] {health.admin_api_status}
[bold blue]WebSocket Connection:[/bold blue] {'Connected' if health.ingestion_service.websocket_connection.is_connected else 'Disconnected'}
[bold blue]Event Processing:[/bold blue] {health.ingestion_service.event_processing.events_per_minute:.1f} events/min
[bold blue]Error Rate:[/bold blue] {health.ingestion_service.event_processing.error_rate * 100:.2f}%
[bold blue]Weather Enrichment:[/bold blue] {'Enabled' if health.ingestion_service.weather_enrichment.enabled else 'Disabled'}
[bold blue]InfluxDB Storage:[/bold blue] {'Connected' if health.ingestion_service.influxdb_storage.is_connected else 'Disconnected'}
        """
        
        console.print(Panel(
            info_text.strip(),
            title="[bold green]HA Ingestor System Information[/bold green]",
            border_style="green"
        ))
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)

@app.command()
def status():
    """Show quick status overview."""
    try:
        config = load_config()
        api_client = APIClient(config.api_url, config.api_token)
        
        # Get system health
        health = api_client.get_health()
        
        # Create status table
        table = Table(title="System Status Overview")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details", style="white")
        
        table.add_row(
            "Overall System",
            health.overall_status.title(),
            f"Last updated: {health.timestamp}"
        )
        
        table.add_row(
            "WebSocket Connection",
            "✅ Connected" if health.ingestion_service.websocket_connection.is_connected else "❌ Disconnected",
            f"Attempts: {health.ingestion_service.websocket_connection.connection_attempts}"
        )
        
        table.add_row(
            "Event Processing",
            "✅ Active",
            f"{health.ingestion_service.event_processing.events_per_minute:.1f} events/min"
        )
        
        table.add_row(
            "Weather Enrichment",
            "✅ Enabled" if health.ingestion_service.weather_enrichment.enabled else "❌ Disabled",
            f"Cache hits: {health.ingestion_service.weather_enrichment.cache_hits}"
        )
        
        table.add_row(
            "InfluxDB Storage",
            "✅ Connected" if health.ingestion_service.influxdb_storage.is_connected else "❌ Disconnected",
            f"Write errors: {health.ingestion_service.influxdb_storage.write_errors}"
        )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)

@app.command()
def version():
    """Show version information."""
    version_info = """
[bold blue]HA Ingestor CLI[/bold blue] version [bold green]1.0.0[/bold green]

[bold cyan]Components:[/bold cyan]
• CLI Tools: 1.0.0
• Admin API: 1.0.0
• WebSocket Ingestion: 1.0.0
• Enrichment Pipeline: 1.0.0
• Health Dashboard: 1.0.0

[bold cyan]Python:[/bold cyan] {python_version}
[bold cyan]Platform:[/bold cyan] {platform}
    """.format(
        python_version=sys.version.split()[0],
        platform=f"{sys.platform} {os.name}"
    )
    
    console.print(Panel(
        version_info.strip(),
        title="[bold green]Version Information[/bold green]",
        border_style="blue"
    ))

if __name__ == "__main__":
    app()
