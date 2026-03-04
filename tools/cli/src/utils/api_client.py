"""API client for CLI tools."""

import json
from datetime import datetime
from typing import Any, Dict, Optional

import httpx
from rich.console import Console
from rich.json import JSON
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from .config import CLIConfig


class APIClient:
    """API client for communicating with the Admin REST API."""
    
    def __init__(self, config: CLIConfig):
        """
        Initialize API client.
        
        Args:
            config: CLI configuration
        """
        self.config = config
        self.console = Console()
        self.client = httpx.AsyncClient(
            base_url=config.api_url,
            timeout=config.timeout,
            headers=self._get_headers()
        )
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for API requests."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "homeiq-cli/1.0.0"
        }
        
        if self.config.api_token:
            headers["Authorization"] = f"Bearer {self.config.api_token}"
        
        return headers
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        show_progress: bool = True
    ) -> Dict[str, Any]:
        """
        Make HTTP request to API.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            params: Query parameters
            data: Request body data
            show_progress: Whether to show progress indicator
            
        Returns:
            Dict: Response data
            
        Raises:
            httpx.HTTPError: If request fails
        """
        url = f"/api/v1{endpoint}"
        
        if show_progress and not self.config.verbose:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console,
                transient=True
            ) as progress:
                task = progress.add_task(f"{method.upper()} {url}", total=None)
                
                try:
                    response = await self.client.request(
                        method=method,
                        url=url,
                        params=params,
                        json=data
                    )
                    progress.update(task, description="✓ Request completed")
                except Exception as e:
                    progress.update(task, description=f"✗ Request failed: {e}")
                    raise
        else:
            response = await self.client.request(
                method=method,
                url=url,
                params=params,
                json=data
            )
        
        response.raise_for_status()
        return response.json()
    
    async def get_health(self) -> Dict[str, Any]:
        """Get system health status."""
        return await self._make_request("GET", "/health")
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get system statistics."""
        return await self._make_request("GET", "/stats")
    
    async def get_configuration(self) -> Dict[str, Any]:
        """Get system configuration."""
        return await self._make_request("GET", "/config")
    
    async def update_configuration(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update system configuration."""
        return await self._make_request("PUT", "/config", data=config_data)
    
    async def get_recent_events(
        self,
        limit: int = 100,
        entity_id: Optional[str] = None,
        event_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get recent events.
        
        Args:
            limit: Maximum number of events to return
            entity_id: Filter by entity ID
            event_type: Filter by event type
            start_time: Filter events after this time
            end_time: Filter events before this time
            
        Returns:
            Dict: Events data
        """
        params = {"limit": limit}
        
        if entity_id:
            params["entity_id"] = entity_id
        if event_type:
            params["event_type"] = event_type
        if start_time:
            params["start_time"] = start_time.isoformat()
        if end_time:
            params["end_time"] = end_time.isoformat()
        
        return await self._make_request("GET", "/events", params=params)
    
    async def export_events(
        self,
        format: str = "json",
        entity_id: Optional[str] = None,
        event_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> bytes:
        """
        Export events in specified format.
        
        Args:
            format: Export format (json, csv)
            entity_id: Filter by entity ID
            event_type: Filter by event type
            start_time: Filter events after this time
            end_time: Filter events before this time
            
        Returns:
            bytes: Exported data
        """
        params = {"format": format}
        
        if entity_id:
            params["entity_id"] = entity_id
        if event_type:
            params["event_type"] = event_type
        if start_time:
            params["start_time"] = start_time.isoformat()
        if end_time:
            params["end_time"] = end_time.isoformat()
        
        response = await self.client.get("/api/v1/events/export", params=params)
        response.raise_for_status()
        return response.content
    
    async def test_connection(self) -> bool:
        """
        Test API connection.
        
        Returns:
            bool: True if connection successful
        """
        try:
            await self._make_request("GET", "/health", show_progress=False)
            return True
        except Exception:
            return False
    
    def format_output(self, data: Any, format: str = "table") -> None:
        """
        Format and display output data.
        
        Args:
            data: Data to display
            format: Output format (table, json, yaml)
        """
        if format == "json":
            self.console.print(JSON(json.dumps(data, indent=2, default=str)))
        elif format == "yaml":
            import yaml
            self.console.print(Panel(yaml.dump(data, default_flow_style=False)))
        elif format == "table" and isinstance(data, dict):
            self._format_table(data)
        else:
            self.console.print(data)
    
    def _format_table(self, data: Dict[str, Any]) -> None:
        """Format data as a table."""
        table = Table(show_header=True, header_style="bold blue")
        
        if "events" in data:
            # Format events table
            table.add_column("Time", style="dim")
            table.add_column("Entity ID", style="cyan")
            table.add_column("Event Type", style="green")
            table.add_column("State", style="yellow")
            
            for event in data["events"]:
                table.add_row(
                    event.get("timestamp", "N/A"),
                    event.get("entity_id", "N/A"),
                    event.get("event_type", "N/A"),
                    str(event.get("state", "N/A"))
                )
        else:
            # Format key-value table
            table.add_column("Key", style="bold")
            table.add_column("Value", style="")
            
            for key, value in data.items():
                if isinstance(value, dict):
                    value = json.dumps(value, indent=2)
                elif isinstance(value, list):
                    value = f"[{len(value)} items]"
                else:
                    value = str(value)
                
                table.add_row(key, value)
        
        self.console.print(table)
    
    async def close(self) -> None:
        """Close the API client."""
        await self.client.aclose()
