"""Events management CLI commands."""

from datetime import datetime, timedelta
from typing import Optional

import typer
from rich.console import Console

from ..utils.api_client import APIClient
from ..utils.config import load_config
from ..utils.output import OutputFormatter

app = typer.Typer(name="events", help="Events management commands")
console = Console()

@app.command("list")
def list_events(
    limit: int = typer.Option(100, "--limit", "-l", help="Maximum number of events to return"),
    entity_id: Optional[str] = typer.Option(None, "--entity-id", "-e", help="Filter by entity ID"),
    event_type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by event type"),
    hours: int = typer.Option(24, "--hours", "-h", help="Show events from last N hours"),
    format: str = typer.Option("table", "--format", "-f", help="Output format (table, json, yaml)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output")
):
    """List recent events."""
    try:
        config = load_config()
        config.verbose = verbose
        
        formatter = OutputFormatter(console)
        
        async def _list_events():
            client = APIClient(config)
            
            try:
                # Test connection first
                if not await client.test_connection():
                    formatter.print_error("Cannot connect to Admin API")
                    return
                
                # Calculate time range
                end_time = datetime.now()
                start_time = end_time - timedelta(hours=hours)
                
                # Get events data
                events_data = await client.get_recent_events(
                    limit=limit,
                    entity_id=entity_id,
                    event_type=event_type,
                    start_time=start_time,
                    end_time=end_time
                )
                
                if format == "json":
                    formatter.print_json(events_data, "Recent Events")
                elif format == "yaml":
                    formatter.print_yaml(events_data, "Recent Events")
                else:
                    formatter.print_events(events_data, limit)
                
            finally:
                await client.close()
        
        import asyncio
        asyncio.run(_list_events())
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

@app.command("export")
def export_events(
    output_file: str = typer.Option("events.json", "--output", "-o", help="Output file path"),
    format: str = typer.Option("json", "--format", "-f", help="Export format (json, csv)"),
    entity_id: Optional[str] = typer.Option(None, "--entity-id", "-e", help="Filter by entity ID"),
    event_type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by event type"),
    hours: int = typer.Option(24, "--hours", "-h", help="Export events from last N hours"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output")
):
    """Export events to file."""
    try:
        config = load_config()
        config.verbose = verbose
        
        formatter = OutputFormatter(console)
        
        async def _export_events():
            client = APIClient(config)
            
            try:
                # Test connection first
                if not await client.test_connection():
                    formatter.print_error("Cannot connect to Admin API")
                    return
                
                # Calculate time range
                end_time = datetime.now()
                start_time = end_time - timedelta(hours=hours)
                
                # Export events
                with formatter.print_progress(f"Exporting events to {output_file}..."):
                    data = await client.export_events(
                        format=format,
                        entity_id=entity_id,
                        event_type=event_type,
                        start_time=start_time,
                        end_time=end_time
                    )
                
                # Write to file
                with open(output_file, 'wb') as f:
                    f.write(data)
                
                formatter.print_success(f"Events exported to {output_file}")
                
            finally:
                await client.close()
        
        import asyncio
        asyncio.run(_export_events())
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

@app.command("search")
def search_events(
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(50, "--limit", "-l", help="Maximum number of events to return"),
    hours: int = typer.Option(24, "--hours", "-h", help="Search events from last N hours"),
    format: str = typer.Option("table", "--format", "-f", help="Output format (table, json, yaml)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output")
):
    """Search events by query."""
    try:
        config = load_config()
        config.verbose = verbose
        
        formatter = OutputFormatter(console)
        
        async def _search_events():
            client = APIClient(config)
            
            try:
                # Test connection first
                if not await client.test_connection():
                    formatter.print_error("Cannot connect to Admin API")
                    return
                
                # Calculate time range
                end_time = datetime.now()
                start_time = end_time - timedelta(hours=hours)
                
                # Search events (using entity_id filter as a simple search)
                events_data = await client.get_recent_events(
                    limit=limit,
                    entity_id=query if query else None,
                    start_time=start_time,
                    end_time=end_time
                )
                
                if format == "json":
                    formatter.print_json(events_data, f"Search Results for '{query}'")
                elif format == "yaml":
                    formatter.print_yaml(events_data, f"Search Results for '{query}'")
                else:
                    formatter.print_header(f"Search Results for '{query}'")
                    formatter.print_events(events_data, limit)
                
            finally:
                await client.close()
        
        import asyncio
        asyncio.run(_search_events())
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

@app.command("monitor")
def monitor_events(
    interval: int = typer.Option(5, "--interval", "-i", help="Update interval in seconds"),
    limit: int = typer.Option(10, "--limit", "-l", help="Number of events to show"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output")
):
    """Monitor events in real-time."""
    try:
        config = load_config()
        config.verbose = verbose
        
        formatter = OutputFormatter(console)
        
        async def _monitor_events():
            client = APIClient(config)
            
            try:
                # Test connection first
                if not await client.test_connection():
                    formatter.print_error("Cannot connect to Admin API")
                    return
                
                formatter.print_info(f"Monitoring events (updating every {interval} seconds). Press Ctrl+C to stop.")
                
                import asyncio

                from rich.layout import Layout
                from rich.live import Live
                
                layout = Layout()
                layout.split_column(
                    Layout(name="header", size=3),
                    Layout(name="events")
                )
                
                with Live(layout, refresh_per_second=1) as live:
                    while True:
                        try:
                            # Get recent events
                            events_data = await client.get_recent_events(limit=limit)
                            
                            # Update header
                            header_text = f"Event Monitor - Last {limit} events (updating every {interval}s)"
                            layout["header"].update(Panel(header_text, border_style="blue"))
                            
                            # Update events
                            events_table = formatter._create_events_table(events_data.get("events", []), limit)
                            layout["events"].update(events_table)
                            
                            await asyncio.sleep(interval)
                            
                        except KeyboardInterrupt:
                            break
                        except Exception as e:
                            layout["events"].update(Panel(f"Error: {e}", border_style="red"))
                            await asyncio.sleep(interval)
                
            finally:
                await client.close()
        
        import asyncio
        asyncio.run(_monitor_events())
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
