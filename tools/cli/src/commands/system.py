"""System management CLI commands."""


import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from ..utils.api_client import APIClient
from ..utils.config import load_config
from ..utils.output import OutputFormatter

app = typer.Typer(name="system", help="System management commands")
console = Console()

@app.command("health")
def health_check(
    format: str = typer.Option("table", "--format", "-f", help="Output format (table, json, yaml)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output")
):
    """Check system health status."""
    try:
        config = load_config()
        config.verbose = verbose
        
        formatter = OutputFormatter(console)
        
        async def _check_health():
            client = APIClient(config)
            
            try:
                # Test connection first
                if not await client.test_connection():
                    formatter.print_error("Cannot connect to Admin API")
                    return
                
                # Get health data
                health_data = await client.get_health()
                
                if format == "json":
                    formatter.print_json(health_data, "System Health")
                elif format == "yaml":
                    formatter.print_yaml(health_data, "System Health")
                else:
                    formatter.print_health_status(health_data)
                
            finally:
                await client.close()
        
        import asyncio
        asyncio.run(_check_health())
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

@app.command("stats")
def get_statistics(
    format: str = typer.Option("table", "--format", "-f", help="Output format (table, json, yaml)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output")
):
    """Get system statistics."""
    try:
        config = load_config()
        config.verbose = verbose
        
        formatter = OutputFormatter(console)
        
        async def _get_stats():
            client = APIClient(config)
            
            try:
                # Test connection first
                if not await client.test_connection():
                    formatter.print_error("Cannot connect to Admin API")
                    return
                
                # Get statistics data
                stats_data = await client.get_statistics()
                
                if format == "json":
                    formatter.print_json(stats_data, "System Statistics")
                elif format == "yaml":
                    formatter.print_yaml(stats_data, "System Statistics")
                else:
                    formatter.print_statistics(stats_data)
                
            finally:
                await client.close()
        
        import asyncio
        asyncio.run(_get_stats())
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

@app.command("status")
def get_status(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output")
):
    """Get quick system status overview."""
    try:
        config = load_config()
        config.verbose = verbose
        
        formatter = OutputFormatter(console)
        
        async def _get_status():
            client = APIClient(config)
            
            try:
                # Test connection
                if not await client.test_connection():
                    formatter.print_error("Cannot connect to Admin API")
                    return
                
                # Get health and stats
                health_data = await client.get_health()
                stats_data = await client.get_statistics()
                
                # Quick status overview
                overall_status = health_data.get("overall_status", "unknown")
                status_color = "green" if overall_status == "healthy" else "yellow" if overall_status == "degraded" else "red"
                
                status_text = Text()
                status_text.append("System Status: ", style="bold")
                status_text.append(f"[{status_color}]{overall_status.upper()}[/{status_color}]")
                
                if stats_data:
                    status_text.append(f"\nTotal Events: {stats_data.get('total_events', 'N/A')}")
                    status_text.append(f"\nEvents Today: {stats_data.get('events_today', 'N/A')}")
                    status_text.append(f"\nActive Entities: {stats_data.get('active_entities', 'N/A')}")
                
                console.print(Panel(status_text, title="Quick Status", border_style="blue"))
                
            finally:
                await client.close()
        
        import asyncio
        asyncio.run(_get_status())
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

@app.command("ping")
def ping_api(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output")
):
    """Test API connection."""
    try:
        config = load_config()
        config.verbose = verbose
        
        formatter = OutputFormatter(console)
        
        async def _ping():
            client = APIClient(config)
            
            try:
                # Test connection
                if await client.test_connection():
                    formatter.print_success(f"API connection successful ({config.api_url})")
                else:
                    formatter.print_error(f"API connection failed ({config.api_url})")
                
            finally:
                await client.close()
        
        import asyncio
        asyncio.run(_ping())
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
