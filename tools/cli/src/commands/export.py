"""Data export CLI commands."""

import csv
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from ..utils.api_client import APIClient
from ..utils.config import load_config
from ..utils.output import OutputFormatter

app = typer.Typer(name="export", help="Data export commands")
console = Console()

@app.command("events")
def export_events(
    output_file: str = typer.Option("events.json", "--output", "-o", help="Output file path"),
    format: str = typer.Option("json", "--format", "-f", help="Export format (json, csv, yaml)"),
    entity_id: Optional[str] = typer.Option(None, "--entity-id", "-e", help="Filter by entity ID"),
    event_type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by event type"),
    hours: int = typer.Option(24, "--hours", "-h", help="Export events from last N hours"),
    days: int = typer.Option(0, "--days", "-d", help="Export events from last N days"),
    limit: int = typer.Option(1000, "--limit", "-l", help="Maximum number of events to export"),
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
                if days > 0:
                    start_time = end_time - timedelta(days=days)
                else:
                    start_time = end_time - timedelta(hours=hours)
                
                # Get events data
                with formatter.print_progress(f"Fetching events from {start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%Y-%m-%d %H:%M')}..."):
                    events_data = await client.get_recent_events(
                        limit=limit,
                        entity_id=entity_id,
                        event_type=event_type,
                        start_time=start_time,
                        end_time=end_time
                    )
                
                events = events_data.get("events", [])
                
                if not events:
                    formatter.print_warning("No events found for the specified criteria")
                    return
                
                # Export to file
                output_path = Path(output_file)
                
                with formatter.print_progress(f"Writing {len(events)} events to {output_file}..."):
                    if format == "json":
                        with open(output_path, 'w') as f:
                            json.dump(events_data, f, indent=2, default=str)
                    
                    elif format == "csv":
                        with open(output_path, 'w', newline='') as f:
                            if events:
                                writer = csv.DictWriter(f, fieldnames=events[0].keys())
                                writer.writeheader()
                                writer.writerows(events)
                    
                    elif format == "yaml":
                        import yaml
                        with open(output_path, 'w') as f:
                            yaml.dump(events_data, f, default_flow_style=False, indent=2)
                    
                    else:
                        formatter.print_error(f"Unsupported format: {format}")
                        raise typer.Exit(1)
                
                formatter.print_success(f"Exported {len(events)} events to {output_file}")
                
                if verbose:
                    formatter.print_info(f"Time range: {start_time.strftime('%Y-%m-%d %H:%M:%S')} to {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    formatter.print_info(f"File size: {output_path.stat().st_size} bytes")
                
            finally:
                await client.close()
        
        import asyncio
        asyncio.run(_export_events())
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

@app.command("stats")
def export_statistics(
    output_file: str = typer.Option("statistics.json", "--output", "-o", help="Output file path"),
    format: str = typer.Option("json", "--format", "-f", help="Export format (json, yaml)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output")
):
    """Export system statistics to file."""
    try:
        config = load_config()
        config.verbose = verbose
        
        formatter = OutputFormatter(console)
        
        async def _export_stats():
            client = APIClient(config)
            
            try:
                # Test connection first
                if not await client.test_connection():
                    formatter.print_error("Cannot connect to Admin API")
                    return
                
                # Get statistics data
                with formatter.print_progress("Fetching system statistics..."):
                    stats_data = await client.get_statistics()
                
                # Export to file
                output_path = Path(output_file)
                
                with formatter.print_progress(f"Writing statistics to {output_file}..."):
                    if format == "json":
                        with open(output_path, 'w') as f:
                            json.dump(stats_data, f, indent=2, default=str)
                    
                    elif format == "yaml":
                        import yaml
                        with open(output_path, 'w') as f:
                            yaml.dump(stats_data, f, default_flow_style=False, indent=2)
                    
                    else:
                        formatter.print_error(f"Unsupported format: {format}")
                        raise typer.Exit(1)
                
                formatter.print_success(f"Exported statistics to {output_file}")
                
                if verbose:
                    formatter.print_info(f"File size: {output_path.stat().st_size} bytes")
                
            finally:
                await client.close()
        
        import asyncio
        asyncio.run(_export_stats())
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

@app.command("health")
def export_health(
    output_file: str = typer.Option("health.json", "--output", "-o", help="Output file path"),
    format: str = typer.Option("json", "--format", "-f", help="Export format (json, yaml)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output")
):
    """Export system health status to file."""
    try:
        config = load_config()
        config.verbose = verbose
        
        formatter = OutputFormatter(console)
        
        async def _export_health():
            client = APIClient(config)
            
            try:
                # Test connection first
                if not await client.test_connection():
                    formatter.print_error("Cannot connect to Admin API")
                    return
                
                # Get health data
                with formatter.print_progress("Fetching system health status..."):
                    health_data = await client.get_health()
                
                # Export to file
                output_path = Path(output_file)
                
                with formatter.print_progress(f"Writing health status to {output_file}..."):
                    if format == "json":
                        with open(output_path, 'w') as f:
                            json.dump(health_data, f, indent=2, default=str)
                    
                    elif format == "yaml":
                        import yaml
                        with open(output_path, 'w') as f:
                            yaml.dump(health_data, f, default_flow_style=False, indent=2)
                    
                    else:
                        formatter.print_error(f"Unsupported format: {format}")
                        raise typer.Exit(1)
                
                formatter.print_success(f"Exported health status to {output_file}")
                
                if verbose:
                    formatter.print_info(f"File size: {output_path.stat().st_size} bytes")
                
            finally:
                await client.close()
        
        import asyncio
        asyncio.run(_export_health())
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

@app.command("all")
def export_all(
    output_dir: str = typer.Option("export", "--output-dir", "-o", help="Output directory"),
    format: str = typer.Option("json", "--format", "-f", help="Export format (json, yaml)"),
    hours: int = typer.Option(24, "--hours", "-h", help="Export events from last N hours"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output")
):
    """Export all data (events, statistics, health) to files."""
    try:
        config = load_config()
        config.verbose = verbose
        
        formatter = OutputFormatter(console)
        
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        async def _export_all():
            client = APIClient(config)
            
            try:
                # Test connection first
                if not await client.test_connection():
                    formatter.print_error("Cannot connect to Admin API")
                    return
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # Export health
                with formatter.print_progress("Exporting health status..."):
                    health_data = await client.get_health()
                    health_file = output_path / f"health_{timestamp}.{format}"
                    
                    if format == "json":
                        with open(health_file, 'w') as f:
                            json.dump(health_data, f, indent=2, default=str)
                    elif format == "yaml":
                        import yaml
                        with open(health_file, 'w') as f:
                            yaml.dump(health_data, f, default_flow_style=False, indent=2)
                
                # Export statistics
                with formatter.print_progress("Exporting statistics..."):
                    stats_data = await client.get_statistics()
                    stats_file = output_path / f"statistics_{timestamp}.{format}"
                    
                    if format == "json":
                        with open(stats_file, 'w') as f:
                            json.dump(stats_data, f, indent=2, default=str)
                    elif format == "yaml":
                        import yaml
                        with open(stats_file, 'w') as f:
                            yaml.dump(stats_data, f, default_flow_style=False, indent=2)
                
                # Export events
                with formatter.print_progress("Exporting events..."):
                    end_time = datetime.now()
                    start_time = end_time - timedelta(hours=hours)
                    
                    events_data = await client.get_recent_events(
                        limit=10000,  # Large limit for export
                        start_time=start_time,
                        end_time=end_time
                    )
                    
                    events_file = output_path / f"events_{timestamp}.{format}"
                    
                    if format == "json":
                        with open(events_file, 'w') as f:
                            json.dump(events_data, f, indent=2, default=str)
                    elif format == "yaml":
                        import yaml
                        with open(events_file, 'w') as f:
                            yaml.dump(events_data, f, default_flow_style=False, indent=2)
                
                formatter.print_success(f"Exported all data to {output_dir}")
                formatter.print_info(f"Files created:")
                formatter.print_info(f"  - {health_file.name}")
                formatter.print_info(f"  - {stats_file.name}")
                formatter.print_info(f"  - {events_file.name}")
                
            finally:
                await client.close()
        
        import asyncio
        asyncio.run(_export_all())
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
