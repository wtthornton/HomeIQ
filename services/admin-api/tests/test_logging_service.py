"""Tests for logging service."""

import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from src.logging_service import LogAggregator, LogEntry, LoggingService, StructuredLogger


class TestLogEntry:
    """Test LogEntry class."""

    def test_log_entry_creation(self):
        """Test log entry creation."""
        entry = LogEntry(
            timestamp="2024-01-01T00:00:00Z",
            level="INFO",
            service="test-service",
            component="test-component",
            message="Test message",
        )

        assert entry.timestamp == "2024-01-01T00:00:00Z"
        assert entry.level == "INFO"
        assert entry.service == "test-service"
        assert entry.component == "test-component"
        assert entry.message == "Test message"

    def test_log_entry_to_dict(self):
        """Test log entry to dictionary conversion."""
        entry = LogEntry(
            timestamp="2024-01-01T00:00:00Z",
            level="INFO",
            service="test-service",
            component="test-component",
            message="Test message",
            event_id="test-event-123",
            metadata={"key": "value"},
        )

        data = entry.to_dict()

        assert data["timestamp"] == "2024-01-01T00:00:00Z"
        assert data["level"] == "INFO"
        assert data["service"] == "test-service"
        assert data["component"] == "test-component"
        assert data["message"] == "Test message"
        assert data["event_id"] == "test-event-123"
        assert data["metadata"] == {"key": "value"}

    def test_log_entry_to_json(self):
        """Test log entry to JSON conversion."""
        entry = LogEntry(
            timestamp="2024-01-01T00:00:00Z",
            level="INFO",
            service="test-service",
            component="test-component",
            message="Test message",
        )

        json_str = entry.to_json()
        data = json.loads(json_str)

        assert data["timestamp"] == "2024-01-01T00:00:00Z"
        assert data["level"] == "INFO"
        assert data["service"] == "test-service"
        assert data["component"] == "test-component"
        assert data["message"] == "Test message"


class TestStructuredLogger:
    """Test StructuredLogger class."""

    def test_structured_logger_creation(self):
        """Test structured logger creation."""
        logger = StructuredLogger("test-service", "test-component")

        assert logger.service_name == "test-service"
        assert logger.component == "test-component"
        assert logger.correlation_id is None
        assert logger.session_id is None
        assert logger.user_id is None

    def test_set_context(self):
        """Test setting logging context."""
        logger = StructuredLogger("test-service", "test-component")

        logger.set_context(
            correlation_id="corr-123",
            session_id="session-456",
            user_id="user-789",
        )

        assert logger.correlation_id == "corr-123"
        assert logger.session_id == "session-456"
        assert logger.user_id == "user-789"

    @patch("src.logging_service.logging.getLogger")
    def test_log_methods(self, mock_get_logger):
        """Test logging methods."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        logger = StructuredLogger("test-service", "test-component")

        # Test debug
        logger.debug("Debug message", event_id="debug-123")
        mock_logger.debug.assert_called_once()

        # Test info
        logger.info("Info message", event_id="info-123")
        mock_logger.info.assert_called_once()

        # Test warning
        logger.warning("Warning message", event_id="warn-123")
        mock_logger.warning.assert_called_once()

        # Test error
        logger.error("Error message", event_id="error-123")
        mock_logger.error.assert_called_once()

        # Test critical
        logger.critical("Critical message", event_id="critical-123")
        mock_logger.critical.assert_called_once()


class TestLogAggregator:
    """Test LogAggregator class."""

    @pytest.fixture
    def temp_log_dir(self):
        """Create temporary log directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    def test_log_aggregator_creation(self, temp_log_dir):
        """Test log aggregator creation."""
        aggregator = LogAggregator(temp_log_dir)

        assert aggregator.log_dir == Path(temp_log_dir)
        assert aggregator.log_dir.exists()
        assert len(aggregator.log_entries) == 0
        assert aggregator.max_memory_entries == 10000

    def test_add_log_entry(self, temp_log_dir):
        """Test adding log entry."""
        aggregator = LogAggregator(temp_log_dir)

        entry = LogEntry(
            timestamp="2024-01-01T00:00:00Z",
            level="INFO",
            service="test-service",
            component="test-component",
            message="Test message",
        )

        aggregator.add_log_entry(entry)

        assert len(aggregator.log_entries) == 1
        assert aggregator.log_entries[0] == entry

    def test_get_recent_logs(self, temp_log_dir):
        """Test getting recent logs."""
        aggregator = LogAggregator(temp_log_dir)

        # Add multiple log entries
        for i in range(5):
            entry = LogEntry(
                timestamp=f"2024-01-01T0{i}:00:00Z",
                level="INFO",
                service="test-service",
                component="test-component",
                message=f"Test message {i}",
            )
            aggregator.add_log_entry(entry)

        # Get recent logs
        recent_logs = aggregator.get_recent_logs(limit=3)

        assert len(recent_logs) == 3
        # Should be sorted by timestamp (newest first)
        assert recent_logs[0]["message"] == "Test message 4"
        assert recent_logs[1]["message"] == "Test message 3"
        assert recent_logs[2]["message"] == "Test message 2"

    def test_get_recent_logs_with_filters(self, temp_log_dir):
        """Test getting recent logs with filters."""
        aggregator = LogAggregator(temp_log_dir)

        # Add log entries with different levels and services
        entries = [
            LogEntry("2024-01-01T00:00:00Z", "INFO", "service1", "comp1", "Message 1"),
            LogEntry("2024-01-01T01:00:00Z", "ERROR", "service1", "comp1", "Message 2"),
            LogEntry("2024-01-01T02:00:00Z", "INFO", "service2", "comp1", "Message 3"),
            LogEntry("2024-01-01T03:00:00Z", "WARNING", "service1", "comp2", "Message 4"),
        ]

        for entry in entries:
            aggregator.add_log_entry(entry)

        # Filter by level
        error_logs = aggregator.get_recent_logs(level="ERROR")
        assert len(error_logs) == 1
        assert error_logs[0]["message"] == "Message 2"

        # Filter by service
        service1_logs = aggregator.get_recent_logs(service="service1")
        assert len(service1_logs) == 3

        # Filter by component
        comp1_logs = aggregator.get_recent_logs(component="comp1")
        assert len(comp1_logs) == 3

    def test_get_log_statistics(self, temp_log_dir):
        """Test getting log statistics."""
        aggregator = LogAggregator(temp_log_dir)

        # Add log entries
        entries = [
            LogEntry("2024-01-01T00:00:00Z", "INFO", "service1", "comp1", "Message 1"),
            LogEntry("2024-01-01T01:00:00Z", "ERROR", "service1", "comp1", "Message 2"),
            LogEntry("2024-01-01T02:00:00Z", "INFO", "service2", "comp1", "Message 3"),
            LogEntry("2024-01-01T03:00:00Z", "WARNING", "service1", "comp2", "Message 4"),
        ]

        for entry in entries:
            aggregator.add_log_entry(entry)

        stats = aggregator.get_log_statistics()

        assert stats["total_entries"] == 4
        assert stats["level_counts"]["INFO"] == 2
        assert stats["level_counts"]["ERROR"] == 1
        assert stats["level_counts"]["WARNING"] == 1
        assert stats["service_counts"]["service1"] == 3
        assert stats["service_counts"]["service2"] == 1
        assert stats["component_counts"]["comp1"] == 3
        assert stats["component_counts"]["comp2"] == 1

    @pytest.mark.asyncio
    async def test_start_stop(self, temp_log_dir):
        """Test starting and stopping aggregator."""
        aggregator = LogAggregator(temp_log_dir)

        # Start aggregator
        await aggregator.start()
        assert aggregator.is_processing

        # Stop aggregator
        await aggregator.stop()
        assert not aggregator.is_processing


class TestLoggingService:
    """Test LoggingService class."""

    @pytest.fixture
    def temp_log_dir(self):
        """Create temporary log directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    def test_logging_service_creation(self):
        """Test logging service creation."""
        service = LoggingService()

        assert isinstance(service.aggregator, LogAggregator)
        assert len(service.loggers) == 0
        assert not service.is_running

    def test_get_logger(self):
        """Test getting logger."""
        service = LoggingService()

        logger1 = service.get_logger("test-service", "comp1")
        logger2 = service.get_logger("test-service", "comp1")
        logger3 = service.get_logger("test-service", "comp2")

        # Should return same logger for same service/component
        assert logger1 is logger2
        # Should return different logger for different component
        assert logger1 is not logger3

        assert len(service.loggers) == 2

    def test_get_recent_logs(self, temp_log_dir):
        """Test getting recent logs."""
        service = LoggingService()
        service.aggregator = LogAggregator(temp_log_dir)

        # Add log entry
        entry = LogEntry(
            timestamp="2024-01-01T00:00:00Z",
            level="INFO",
            service="test-service",
            component="test-component",
            message="Test message",
        )
        service.aggregator.add_log_entry(entry)

        logs = service.get_recent_logs(limit=10)

        assert len(logs) == 1
        assert logs[0]["message"] == "Test message"

    def test_get_log_statistics(self, temp_log_dir):
        """Test getting log statistics."""
        service = LoggingService()
        service.aggregator = LogAggregator(temp_log_dir)

        stats = service.get_log_statistics()

        assert stats["total_entries"] == 0
        assert stats["level_counts"] == {}
        assert stats["service_counts"] == {}
        assert stats["component_counts"] == {}

    @pytest.mark.asyncio
    async def test_start_stop(self, temp_log_dir):
        """Test starting and stopping service."""
        service = LoggingService()
        service.aggregator = LogAggregator(temp_log_dir)

        # Start service
        await service.start()
        assert service.is_running

        # Stop service
        await service.stop()
        assert not service.is_running
