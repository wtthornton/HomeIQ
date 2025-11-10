"""Tests for output formatting utilities."""

import pytest
from unittest.mock import MagicMock
from datetime import datetime
from rich.console import Console

from src.utils.output import OutputFormatter

class TestOutputFormatter:
    """Test OutputFormatter class."""
    
    def test_init(self):
        """Test OutputFormatter initialization."""
        console = Console()
        formatter = OutputFormatter(console)
        
        assert formatter.console == console
    
    def test_print_success(self):
        """Test printing success message."""
        console = Console()
        formatter = OutputFormatter(console)
        
        with pytest.capture_output() as captured:
            formatter.print_success("Test success message")
        
        assert "✓ Test success message" in captured.out
    
    def test_print_error(self):
        """Test printing error message."""
        console = Console()
        formatter = OutputFormatter(console)
        
        with pytest.capture_output() as captured:
            formatter.print_error("Test error message")
        
        assert "✗ Test error message" in captured.out
    
    def test_print_warning(self):
        """Test printing warning message."""
        console = Console()
        formatter = OutputFormatter(console)
        
        with pytest.capture_output() as captured:
            formatter.print_warning("Test warning message")
        
        assert "⚠ Test warning message" in captured.out
    
    def test_print_info(self):
        """Test printing info message."""
        console = Console()
        formatter = OutputFormatter(console)
        
        with pytest.capture_output() as captured:
            formatter.print_info("Test info message")
        
        assert "ℹ Test info message" in captured.out
    
    def test_print_header(self):
        """Test printing header."""
        console = Console()
        formatter = OutputFormatter(console)
        
        with pytest.capture_output() as captured:
            formatter.print_header("Test Title", "Test Subtitle")
        
        assert "Test Title" in captured.out
        assert "Test Subtitle" in captured.out
    
    def test_print_json(self):
        """Test printing JSON data."""
        console = Console()
        formatter = OutputFormatter(console)
        
        data = {"key": "value", "number": 123}
        
        with pytest.capture_output() as captured:
            formatter.print_json(data, "Test JSON")
        
        assert "Test JSON" in captured.out
        assert "key" in captured.out
        assert "value" in captured.out
    
    def test_print_yaml(self):
        """Test printing YAML data."""
        console = Console()
        formatter = OutputFormatter(console)
        
        data = {"key": "value", "number": 123}
        
        with pytest.capture_output() as captured:
            formatter.print_yaml(data, "Test YAML")
        
        assert "Test YAML" in captured.out
        assert "key" in captured.out
        assert "value" in captured.out
    
    def test_print_table_empty_data(self):
        """Test printing table with empty data."""
        console = Console()
        formatter = OutputFormatter(console)
        
        with pytest.capture_output() as captured:
            formatter.print_table([], "Empty Table")
        
        assert "No data to display" in captured.out
    
    def test_print_table_with_data(self):
        """Test printing table with data."""
        console = Console()
        formatter = OutputFormatter(console)
        
        data = [
            {"name": "Item 1", "value": 100},
            {"name": "Item 2", "value": 200}
        ]
        
        with pytest.capture_output() as captured:
            formatter.print_table(data, "Test Table")
        
        assert "Test Table" in captured.out
        assert "Item 1" in captured.out
        assert "Item 2" in captured.out
    
    def test_print_table_with_columns(self):
        """Test printing table with specific columns."""
        console = Console()
        formatter = OutputFormatter(console)
        
        data = [
            {"name": "Item 1", "value": 100, "extra": "ignored"},
            {"name": "Item 2", "value": 200, "extra": "ignored"}
        ]
        
        with pytest.capture_output() as captured:
            formatter.print_table(data, "Test Table", columns=["name", "value"])
        
        assert "Test Table" in captured.out
        assert "Item 1" in captured.out
        assert "Item 2" in captured.out
        assert "ignored" not in captured.out
    
    def test_print_health_status(self):
        """Test printing health status."""
        console = Console()
        formatter = OutputFormatter(console)
        
        health_data = {
            "overall_status": "healthy",
            "admin_api_status": "running",
            "ingestion_service": {
                "status": "healthy",
                "websocket_connection": {
                    "is_connected": True,
                    "last_connection_time": "2024-01-01T12:00:00Z",
                    "connection_attempts": 5,
                    "last_error": None
                },
                "event_processing": {
                    "total_events": 1000,
                    "events_per_minute": 50,
                    "error_rate": 0.01
                }
            }
        }
        
        with pytest.capture_output() as captured:
            formatter.print_health_status(health_data)
        
        assert "System Health Status" in captured.out
        assert "HEALTHY" in captured.out
        assert "Admin API" in captured.out
        assert "WebSocket Ingestion" in captured.out
    
    def test_print_statistics(self):
        """Test printing statistics."""
        console = Console()
        formatter = OutputFormatter(console)
        
        stats_data = {
            "total_events": 10000,
            "events_today": 500,
            "active_entities": 25,
            "uptime": "2 days, 5 hours",
            "event_processing": {
                "success_rate": 0.99,
                "avg_processing_time": 0.05
            },
            "weather_enrichment": {
                "cache_hits": 1000,
                "api_calls": 100
            },
            "influxdb_storage": {
                "write_success_rate": 0.98,
                "avg_write_time": 0.1
            }
        }
        
        with pytest.capture_output() as captured:
            formatter.print_statistics(stats_data)
        
        assert "System Statistics" in captured.out
        assert "10000" in captured.out
        assert "500" in captured.out
        assert "25" in captured.out
    
    def test_print_events(self):
        """Test printing events."""
        console = Console()
        formatter = OutputFormatter(console)
        
        events_data = {
            "events": [
                {
                    "timestamp": "2024-01-01T12:00:00Z",
                    "entity_id": "sensor.temperature",
                    "event_type": "state_changed",
                    "state": "20.5",
                    "attributes": {"unit": "°C"}
                },
                {
                    "timestamp": "2024-01-01T12:01:00Z",
                    "entity_id": "sensor.humidity",
                    "event_type": "state_changed",
                    "state": "65",
                    "attributes": {"unit": "%"}
                }
            ]
        }
        
        with pytest.capture_output() as captured:
            formatter.print_events(events_data, limit=2)
        
        assert "Recent Events" in captured.out
        assert "sensor.temperature" in captured.out
        assert "sensor.humidity" in captured.out
    
    def test_print_events_empty(self):
        """Test printing events with empty data."""
        console = Console()
        formatter = OutputFormatter(console)
        
        events_data = {"events": []}
        
        with pytest.capture_output() as captured:
            formatter.print_events(events_data)
        
        assert "No events found" in captured.out
    
    def test_print_progress(self):
        """Test printing progress indicator."""
        console = Console()
        formatter = OutputFormatter(console)
        
        status = formatter.print_progress("Test progress")
        
        assert status is not None
        # Status should be a Rich Status object
        assert hasattr(status, 'start')
        assert hasattr(status, 'stop')
    
    def test_print_tree(self):
        """Test printing tree structure."""
        console = Console()
        formatter = OutputFormatter(console)
        
        data = {
            "level1": {
                "level2": {
                    "value": "test"
                },
                "list": [1, 2, 3]
            }
        }
        
        with pytest.capture_output() as captured:
            formatter.print_tree(data, "Test Tree")
        
        assert "Test Tree" in captured.out
        assert "level1" in captured.out
        assert "level2" in captured.out
        assert "test" in captured.out
    
    def test_print_tree_no_title(self):
        """Test printing tree structure without title."""
        console = Console()
        formatter = OutputFormatter(console)
        
        data = {"key": "value"}
        
        with pytest.capture_output() as captured:
            formatter.print_tree(data)
        
        assert "key" in captured.out
        assert "value" in captured.out
