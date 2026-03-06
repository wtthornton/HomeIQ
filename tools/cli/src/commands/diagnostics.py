"""System diagnostics CLI commands."""

import asyncio
import socket
import time
from typing import Any, Dict

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from ..utils.api_client import APIClient
from ..utils.config import load_config
from ..utils.output import OutputFormatter

app = typer.Typer(name="diagnostics", help="System diagnostics commands")
console = Console()

@app.command("check")
def run_diagnostics(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output")
):
    """Run comprehensive system diagnostics."""
    try:
        config = load_config()
        config.verbose = verbose
        
        formatter = OutputFormatter(console)
        formatter.print_header("System Diagnostics", "Comprehensive health and connectivity check")
        
        async def _run_diagnostics():
            # Test API connection
            formatter.print_info("Testing API connection...")
            client = APIClient(config)
            
            try:
                # Test basic connectivity
                connectivity_ok = await client.test_connection()
                
                if connectivity_ok:
                    formatter.print_success("API connection successful")
                    
                    # Get detailed health information
                    with formatter.print_progress("Fetching detailed health information..."):
                        health_data = await client.get_health()
                        stats_data = await client.get_statistics()
                    
                    # Analyze health data
                    _analyze_health_data(formatter, health_data, stats_data)
                    
                else:
                    formatter.print_error("API connection failed")
                    _diagnose_connection_issues(formatter, config)
                
            finally:
                await client.close()
        
        asyncio.run(_run_diagnostics())
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

@app.command("connectivity")
def test_connectivity(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output")
):
    """Test network connectivity to all services."""
    try:
        config = load_config()
        config.verbose = verbose
        
        formatter = OutputFormatter(console)
        formatter.print_header("Connectivity Test", "Testing network connectivity to all services")
        
        # Test Admin API
        formatter.print_info("Testing Admin API connectivity...")
        admin_api_ok = _test_tcp_connectivity(config.api_url.replace("http://", "").replace("https://", ""), 8000)
        
        if admin_api_ok:
            formatter.print_success("Admin API: ✓ Connected")
        else:
            formatter.print_error("Admin API: ✗ Connection failed")
        
        # Test WebSocket Ingestion Service
        formatter.print_info("Testing WebSocket Ingestion Service...")
        ws_service_ok = _test_tcp_connectivity("localhost", 8080)
        
        if ws_service_ok:
            formatter.print_success("WebSocket Ingestion: ✓ Connected")
        else:
            formatter.print_warning("WebSocket Ingestion: ⚠ Not accessible (may be internal)")
        
        # Test InfluxDB
        formatter.print_info("Testing InfluxDB connectivity...")
        influxdb_ok = _test_tcp_connectivity("localhost", 8086)
        
        if influxdb_ok:
            formatter.print_success("InfluxDB: ✓ Connected")
        else:
            formatter.print_warning("InfluxDB: ⚠ Not accessible (may be internal)")
        
        # Test Health Dashboard
        formatter.print_info("Testing Health Dashboard...")
        dashboard_ok = _test_tcp_connectivity("localhost", 3000)
        
        if dashboard_ok:
            formatter.print_success("Health Dashboard: ✓ Connected")
        else:
            formatter.print_warning("Health Dashboard: ⚠ Not accessible")
        
        # Summary
        services_status = {
            "Admin API": admin_api_ok,
            "WebSocket Ingestion": ws_service_ok,
            "InfluxDB": influxdb_ok,
            "Health Dashboard": dashboard_ok
        }
        
        connected_count = sum(services_status.values())
        total_count = len(services_status)
        
        if connected_count == total_count:
            formatter.print_success(f"All {total_count} services are accessible")
        elif connected_count > 0:
            formatter.print_warning(f"{connected_count}/{total_count} services are accessible")
        else:
            formatter.print_error("No services are accessible")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

@app.command("performance")
def test_performance(
    duration: int = typer.Option(60, "--duration", "-d", help="Test duration in seconds"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output")
):
    """Test system performance and response times."""
    try:
        config = load_config()
        config.verbose = verbose
        
        formatter = OutputFormatter(console)
        formatter.print_header("Performance Test", f"Testing system performance for {duration} seconds")
        
        async def _test_performance():
            client = APIClient(config)
            
            try:
                # Test connection first
                if not await client.test_connection():
                    formatter.print_error("Cannot connect to Admin API")
                    return
                
                start_time = time.time()
                end_time = start_time + duration
                
                response_times = []
                success_count = 0
                error_count = 0
                
                formatter.print_info(f"Running performance test for {duration} seconds...")
                
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                    transient=True
                ) as progress:
                    task = progress.add_task("Testing performance...", total=duration)
                    
                    while time.time() < end_time:
                        try:
                            # Test health endpoint
                            request_start = time.time()
                            await client.get_health()
                            request_end = time.time()
                            
                            response_time = (request_end - request_start) * 1000  # Convert to ms
                            response_times.append(response_time)
                            success_count += 1
                            
                            if verbose:
                                formatter.print_info(f"Response time: {response_time:.2f}ms")
                            
                        except Exception as e:
                            error_count += 1
                            if verbose:
                                formatter.print_error(f"Request failed: {e}")
                        
                        # Update progress
                        elapsed = time.time() - start_time
                        progress.update(task, completed=elapsed)
                        
                        # Wait before next request
                        await asyncio.sleep(1)
                
                # Calculate statistics
                if response_times:
                    avg_response_time = sum(response_times) / len(response_times)
                    min_response_time = min(response_times)
                    max_response_time = max(response_times)
                    
                    # Performance summary
                    perf_table = Table(show_header=True, header_style="bold blue")
                    perf_table.add_column("Metric", style="cyan")
                    perf_table.add_column("Value", style="green")
                    
                    perf_table.add_row("Test Duration", f"{duration} seconds")
                    perf_table.add_row("Total Requests", str(success_count + error_count))
                    perf_table.add_row("Successful Requests", str(success_count))
                    perf_table.add_row("Failed Requests", str(error_count))
                    perf_table.add_row("Success Rate", f"{(success_count / (success_count + error_count) * 100):.1f}%")
                    perf_table.add_row("Average Response Time", f"{avg_response_time:.2f}ms")
                    perf_table.add_row("Min Response Time", f"{min_response_time:.2f}ms")
                    perf_table.add_row("Max Response Time", f"{max_response_time:.2f}ms")
                    
                    formatter.print_header("Performance Test Results")
                    console.print(perf_table)
                    
                    # Performance assessment
                    if avg_response_time < 100:
                        formatter.print_success("Performance: Excellent (< 100ms average)")
                    elif avg_response_time < 500:
                        formatter.print_info("Performance: Good (< 500ms average)")
                    elif avg_response_time < 1000:
                        formatter.print_warning("Performance: Acceptable (< 1s average)")
                    else:
                        formatter.print_error("Performance: Poor (> 1s average)")
                
                else:
                    formatter.print_error("No successful requests during test period")
                
            finally:
                await client.close()
        
        asyncio.run(_test_performance())
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

def _test_tcp_connectivity(host: str, port: int, timeout: int = 5) -> bool:
    """Test TCP connectivity to a host and port."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            return result == 0
    except Exception:
        return False

def _analyze_health_data(formatter: OutputFormatter, health_data: Dict[str, Any], stats_data: Dict[str, Any]) -> None:
    """Analyze health data and provide insights."""
    formatter.print_header("Health Analysis")
    
    # Overall status
    overall_status = health_data.get("overall_status", "unknown")
    status_color = "green" if overall_status == "healthy" else "yellow" if overall_status == "degraded" else "red"
    formatter.print_info(f"Overall Status: [{status_color}]{overall_status.upper()}[/{status_color}]")
    
    # Ingestion service analysis
    ingestion_service = health_data.get("ingestion_service", {})
    if ingestion_service:
        ws_connection = ingestion_service.get("websocket_connection", {})
        event_processing = ingestion_service.get("event_processing", {})
        
        # WebSocket connection analysis
        if ws_connection.get("is_connected"):
            formatter.print_success("WebSocket Connection: Active")
        else:
            formatter.print_error("WebSocket Connection: Disconnected")
        
        # Event processing analysis
        if event_processing:
            total_events = event_processing.get("total_events", 0)
            events_per_minute = event_processing.get("events_per_minute", 0)
            error_rate = event_processing.get("error_rate", 0)
            
            formatter.print_info(f"Total Events Processed: {total_events}")
            formatter.print_info(f"Events per Minute: {events_per_minute}")
            
            if error_rate < 0.01:
                formatter.print_success(f"Error Rate: {error_rate:.3f} (Excellent)")
            elif error_rate < 0.05:
                formatter.print_info(f"Error Rate: {error_rate:.3f} (Good)")
            else:
                formatter.print_warning(f"Error Rate: {error_rate:.3f} (High)")
    
    # Statistics analysis
    if stats_data:
        total_events = stats_data.get("total_events", 0)
        events_today = stats_data.get("events_today", 0)
        active_entities = stats_data.get("active_entities", 0)
        
        formatter.print_info(f"Total Events: {total_events}")
        formatter.print_info(f"Events Today: {events_today}")
        formatter.print_info(f"Active Entities: {active_entities}")

def _diagnose_connection_issues(formatter: OutputFormatter, config) -> None:
    """Diagnose connection issues."""
    formatter.print_header("Connection Diagnostics")
    
    # Check configuration
    formatter.print_info(f"API URL: {config.api_url}")
    formatter.print_info(f"API Token: {'Set' if config.api_token else 'Not set'}")
    formatter.print_info(f"Timeout: {config.timeout}s")
    
    # Test basic connectivity
    host = config.api_url.replace("http://", "").replace("https://", "").split(":")[0]
    port = 8000
    
    stripped_url = config.api_url.replace("http://", "").replace("https://", "")
    if ":" in stripped_url:
        port_str = stripped_url.split(":")[-1].split("/")[0]
        try:
            port = int(port_str)
        except ValueError:
            port = 8000
    
    formatter.print_info(f"Testing connectivity to {host}:{port}...")
    
    if _test_tcp_connectivity(host, port):
        formatter.print_success("TCP connection successful")
        formatter.print_warning("API may be running but not responding to HTTP requests")
    else:
        formatter.print_error("TCP connection failed")
        formatter.print_info("Possible issues:")
        formatter.print_info("  - Service is not running")
        formatter.print_info("  - Wrong host/port configuration")
        formatter.print_info("  - Firewall blocking connection")
        formatter.print_info("  - Network connectivity issues")
