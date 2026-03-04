"""Output formatting utilities for CLI tools."""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import yaml
from rich import box
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.status import Status
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich.tree import Tree


class OutputFormatter:
    """Output formatter for CLI tools."""
    
    def __init__(self, console: Console):
        """
        Initialize output formatter.
        
        Args:
            console: Rich console instance
        """
        self.console = console
    
    def print_success(self, message: str) -> None:
        """Print success message."""
        self.console.print(f"[green]✓[/green] {message}")
    
    def print_error(self, message: str) -> None:
        """Print error message."""
        self.console.print(f"[red]✗[/red] {message}")
    
    def print_warning(self, message: str) -> None:
        """Print warning message."""
        self.console.print(f"[yellow]⚠[/yellow] {message}")
    
    def print_info(self, message: str) -> None:
        """Print info message."""
        self.console.print(f"[blue]ℹ[/blue] {message}")
    
    def print_header(self, title: str, subtitle: Optional[str] = None) -> None:
        """Print formatted header."""
        header_text = Text(title, style="bold blue")
        if subtitle:
            header_text.append(f"\n{subtitle}", style="dim")
        
        self.console.print(Panel(header_text, box=box.DOUBLE))
    
    def print_json(self, data: Any, title: Optional[str] = None) -> None:
        """Print JSON data."""
        json_str = json.dumps(data, indent=2, default=str)
        syntax = Syntax(json_str, "json", theme="monokai")
        
        if title:
            self.console.print(Panel(syntax, title=title, title_align="left"))
        else:
            self.console.print(syntax)
    
    def print_yaml(self, data: Any, title: Optional[str] = None) -> None:
        """Print YAML data."""
        yaml_str = yaml.dump(data, default_flow_style=False, indent=2)
        syntax = Syntax(yaml_str, "yaml", theme="monokai")
        
        if title:
            self.console.print(Panel(syntax, title=title, title_align="left"))
        else:
            self.console.print(syntax)
    
    def print_table(
        self,
        data: List[Dict[str, Any]],
        title: Optional[str] = None,
        columns: Optional[List[str]] = None
    ) -> None:
        """
        Print data as a table.
        
        Args:
            data: List of dictionaries to display
            title: Table title
            columns: List of column names to display
        """
        if not data:
            self.console.print("[dim]No data to display[/dim]")
            return
        
        table = Table(show_header=True, header_style="bold blue", box=box.ROUNDED)
        
        if columns:
            for col in columns:
                table.add_column(col, style="cyan")
        else:
            # Auto-detect columns from first item
            first_item = data[0]
            for key in first_item.keys():
                table.add_column(key.replace("_", " ").title(), style="cyan")
        
        for item in data:
            row = []
            keys = columns if columns else list(first_item.keys())
            
            for key in keys:
                value = item.get(key, "N/A")
                if isinstance(value, (dict, list)):
                    value = json.dumps(value, default=str)
                elif isinstance(value, datetime):
                    value = value.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    value = str(value)
                
                row.append(value)
            
            table.add_row(*row)
        
        if title:
            self.console.print(Panel(table, title=title, title_align="left"))
        else:
            self.console.print(table)
    
    def print_health_status(self, health_data: Dict[str, Any]) -> None:
        """Print health status in a formatted way."""
        overall_status = health_data.get("overall_status", "unknown")
        
        # Status color
        status_color = "green" if overall_status == "healthy" else "yellow" if overall_status == "degraded" else "red"
        
        # Header
        self.print_header("System Health Status", f"Overall Status: [{status_color}]{overall_status.upper()}[/{status_color}]")
        
        # Services status
        services_table = Table(show_header=True, header_style="bold blue")
        services_table.add_column("Service", style="cyan")
        services_table.add_column("Status", style="green")
        services_table.add_column("Details", style="dim")
        
        # Admin API status
        services_table.add_row(
            "Admin API",
            "[green]Running[/green]",
            "REST API operational"
        )
        
        # Ingestion service status
        ingestion_service = health_data.get("ingestion_service", {})
        ingestion_status = ingestion_service.get("status", "unknown")
        ingestion_color = "green" if ingestion_status == "healthy" else "yellow" if ingestion_status == "degraded" else "red"
        
        services_table.add_row(
            "WebSocket Ingestion",
            f"[{ingestion_color}]{ingestion_status.title()}[/{ingestion_color}]",
            f"Connection: {ingestion_service.get('websocket_connection', {}).get('is_connected', 'Unknown')}"
        )
        
        self.console.print(services_table)
        
        # Detailed information
        if self.console.is_terminal:
            self.console.print("\n[bold]Detailed Information:[/bold]")
            
            # WebSocket connection details
            ws_connection = ingestion_service.get("websocket_connection", {})
            if ws_connection:
                self.console.print(f"  WebSocket Connection: {ws_connection.get('is_connected', 'Unknown')}")
                self.console.print(f"  Last Connection: {ws_connection.get('last_connection_time', 'N/A')}")
                self.console.print(f"  Connection Attempts: {ws_connection.get('connection_attempts', 'N/A')}")
            
            # Event processing details
            event_processing = ingestion_service.get("event_processing", {})
            if event_processing:
                self.console.print(f"  Total Events: {event_processing.get('total_events', 'N/A')}")
                self.console.print(f"  Events/Minute: {event_processing.get('events_per_minute', 'N/A')}")
                self.console.print(f"  Error Rate: {event_processing.get('error_rate', 'N/A')}")
    
    def print_statistics(self, stats_data: Dict[str, Any]) -> None:
        """Print statistics in a formatted way."""
        self.print_header("System Statistics")
        
        # Create columns layout
        layout = Layout()
        layout.split_column(
            Layout(name="overview", size=3),
            Layout(name="details")
        )
        
        # Overview section
        overview_table = Table(show_header=False, box=box.MINIMAL)
        overview_table.add_column("Metric", style="bold cyan")
        overview_table.add_column("Value", style="green")
        
        overview_table.add_row("Total Events", str(stats_data.get("total_events", "N/A")))
        overview_table.add_row("Events Today", str(stats_data.get("events_today", "N/A")))
        overview_table.add_row("Active Entities", str(stats_data.get("active_entities", "N/A")))
        overview_table.add_row("Uptime", str(stats_data.get("uptime", "N/A")))
        
        layout["overview"].update(Panel(overview_table, title="Overview", border_style="blue"))
        
        # Details section
        details_data = {
            "Event Processing": stats_data.get("event_processing", {}),
            "Weather Enrichment": stats_data.get("weather_enrichment", {}),
            "InfluxDB Storage": stats_data.get("influxdb_storage", {}),
        }
        
        details_text = ""
        for section, data in details_data.items():
            if data:
                details_text += f"\n[bold]{section}:[/bold]\n"
                for key, value in data.items():
                    details_text += f"  {key.replace('_', ' ').title()}: {value}\n"
        
        layout["details"].update(Panel(details_text.strip(), title="Details", border_style="green"))
        
        self.console.print(layout)
    
    def print_events(self, events_data: Dict[str, Any], limit: int = 10) -> None:
        """Print recent events."""
        events = events_data.get("events", [])
        
        if not events:
            self.console.print("[dim]No events found[/dim]")
            return
        
        self.print_header(f"Recent Events (showing {min(limit, len(events))} of {len(events)})")
        
        events_table = Table(show_header=True, header_style="bold blue")
        events_table.add_column("Time", style="dim", width=20)
        events_table.add_column("Entity ID", style="cyan", width=25)
        events_table.add_column("Event Type", style="green", width=15)
        events_table.add_column("State", style="yellow", width=15)
        events_table.add_column("Attributes", style="dim", width=30)
        
        for event in events[:limit]:
            timestamp = event.get("timestamp", "N/A")
            if timestamp != "N/A":
                try:
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    pass
            
            attributes = event.get("attributes", {})
            attributes_str = json.dumps(attributes, default=str)[:30] + "..." if len(str(attributes)) > 30 else json.dumps(attributes, default=str)
            
            events_table.add_row(
                timestamp,
                event.get("entity_id", "N/A"),
                event.get("event_type", "N/A"),
                str(event.get("state", "N/A")),
                attributes_str
            )
        
        self.console.print(events_table)
    
    def print_progress(self, message: str) -> Status:
        """Print progress indicator."""
        return self.console.status(message)
    
    def print_tree(self, data: Dict[str, Any], title: Optional[str] = None) -> None:
        """Print data as a tree structure."""
        tree = Tree("System", style="bold blue")
        
        def add_to_tree(node: Tree, data: Any, key: str = ""):
            if isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, (dict, list)):
                        branch = node.add(f"[cyan]{k}[/cyan]")
                        add_to_tree(branch, v, k)
                    else:
                        node.add(f"[cyan]{k}[/cyan]: [green]{v}[/green]")
            elif isinstance(data, list):
                for i, item in enumerate(data):
                    if isinstance(item, (dict, list)):
                        branch = node.add(f"[cyan]Item {i+1}[/cyan]")
                        add_to_tree(branch, item, f"item_{i}")
                    else:
                        node.add(f"[green]{item}[/green]")
            else:
                node.add(f"[green]{data}[/green]")
        
        add_to_tree(tree, data)
        
        if title:
            self.console.print(Panel(tree, title=title, title_align="left"))
        else:
            self.console.print(tree)
