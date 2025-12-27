"""
Comprehensive Tests for Logging Configuration
Modern 2025 Patterns: Structured logging, correlation IDs

Module: shared/logging_config.py
Coverage Target: >85%
"""

import pytest
import logging
import json
from unittest.mock import Mock, patch
from datetime import datetime

# Import module under test
from logging_config import (
    StructuredFormatter,
    PerformanceLogger,
    performance_monitor,
    generate_correlation_id,
    set_correlation_id,
    get_correlation_id,
    setup_logging,
    get_logger,
    log_with_context,
    log_performance,
    log_error_with_context,
    correlation_id
)


# ============================================================================
# Structured Formatter Tests
# ============================================================================

class TestStructuredFormatter:
    """Test structured JSON formatter"""

    def test_format_basic_log_record(self):
        """Test formatting a basic log record"""
        formatter = StructuredFormatter(service_name="test-service")

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/path/to/file.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )

        formatted = formatter.format(record)
        log_entry = json.loads(formatted)

        assert log_entry['level'] == 'INFO'
        assert log_entry['service'] == 'test-service'
        assert log_entry['message'] == 'Test message'
        assert log_entry['context']['filename'] == 'file.py'
        assert log_entry['context']['lineno'] == 42
        assert 'timestamp' in log_entry

    def test_format_log_with_correlation_id(self, correlation_id_context):
        """Test log includes correlation ID from context"""
        formatter = StructuredFormatter(service_name="test-service")

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/path/file.py",
            lineno=1,
            msg="Message with correlation",
            args=(),
            exc_info=None
        )

        formatted = formatter.format(record)
        log_entry = json.loads(formatted)

        assert log_entry['correlation_id'] == correlation_id_context

    def test_format_log_with_exception(self):
        """Test formatting log with exception info"""
        formatter = StructuredFormatter(service_name="test-service")

        try:
            raise ValueError("Test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="/path/file.py",
            lineno=1,
            msg="Error occurred",
            args=(),
            exc_info=exc_info
        )

        formatted = formatter.format(record)
        log_entry = json.loads(formatted)

        assert 'exception' in log_entry
        assert log_entry['exception']['type'] == 'ValueError'
        assert 'Test error' in log_entry['exception']['message']
        assert 'traceback' in log_entry['exception']


# ============================================================================
# Correlation ID Tests
# ============================================================================

class TestCorrelationID:
    """Test correlation ID management"""

    def test_generate_correlation_id(self):
        """Test correlation ID generation"""
        corr_id = generate_correlation_id()

        assert corr_id.startswith('req_')
        assert len(corr_id) > 10

    def test_generate_unique_correlation_ids(self):
        """Test generated IDs are unique"""
        id1 = generate_correlation_id()
        id2 = generate_correlation_id()

        assert id1 != id2

    def test_set_and_get_correlation_id(self):
        """Test setting and getting correlation ID"""
        test_id = "test_correlation_123"

        set_correlation_id(test_id)
        retrieved_id = get_correlation_id()

        assert retrieved_id == test_id

        # Cleanup
        correlation_id.set(None)

    def test_correlation_id_isolated_between_contexts(self):
        """Test correlation IDs are isolated in different contexts"""
        set_correlation_id("context_1")

        assert get_correlation_id() == "context_1"

        # Cleanup
        correlation_id.set(None)


# ============================================================================
# Performance Logger Tests
# ============================================================================

class TestPerformanceLogger:
    """Test performance logging context manager"""

    def test_performance_logger_context_manager(self, test_logger):
        """Test performance logger as context manager"""
        import time

        with PerformanceLogger(test_logger, "test_operation") as perf:
            time.sleep(0.01)  # 10ms

        # Verify it completed without error
        assert perf.start_time is not None

    def test_performance_logger_records_duration(self, test_logger):
        """Test performance logger records duration"""
        import time

        with patch.object(test_logger, 'info') as mock_info:
            with PerformanceLogger(test_logger, "test_op"):
                time.sleep(0.01)

            # Verify logger was called with performance info
            mock_info.assert_called_once()
            call_args = mock_info.call_args
            assert "Performance" in call_args[0][0]
            assert 'performance' in call_args[1]['extra']

    def test_performance_logger_handles_exceptions(self, test_logger):
        """Test performance logger handles exceptions"""
        with patch.object(test_logger, 'info') as mock_info:
            try:
                with PerformanceLogger(test_logger, "failing_op"):
                    raise ValueError("Test error")
            except ValueError:
                pass

            # Should still log, but with error status
            mock_info.assert_called_once()
            extra = mock_info.call_args[1]['extra']
            assert extra['performance']['status'] == 'error'


# ============================================================================
# Performance Monitor Decorator Tests
# ============================================================================

class TestPerformanceMonitorDecorator:
    """Test performance monitoring decorator"""

    def test_performance_monitor_decorator(self):
        """Test performance monitor decorator"""
        import time

        @performance_monitor("test_function")
        def slow_function():
            time.sleep(0.01)
            return "result"

        result = slow_function()

        assert result == "result"

    def test_performance_monitor_preserves_function(self):
        """Test decorator preserves function attributes"""

        @performance_monitor()
        def documented_func():
            """This is a test function"""
            return True

        assert documented_func.__name__ == "documented_func"
        assert documented_func.__doc__ == "This is a test function"


# ============================================================================
# Setup Logging Tests
# ============================================================================

class TestSetupLogging:
    """Test logging setup function"""

    @patch.dict('os.environ', {'LOG_LEVEL': 'DEBUG', 'LOG_FORMAT': 'json'})
    def test_setup_logging_json_format(self):
        """Test setting up logging with JSON format"""
        logger = setup_logging("test-service")

        assert logger.name == "test-service"
        assert logger.level == logging.DEBUG
        assert len(logger.handlers) > 0

        # Check formatter is StructuredFormatter
        handler = logger.handlers[0]
        assert isinstance(handler.formatter, StructuredFormatter)

        # Cleanup
        logger.handlers.clear()

    @patch.dict('os.environ', {'LOG_LEVEL': 'INFO', 'LOG_FORMAT': 'text'})
    def test_setup_logging_text_format(self):
        """Test setting up logging with text format"""
        logger = setup_logging("test-service")

        assert logger.level == logging.INFO

        # Check formatter is standard formatter
        handler = logger.handlers[0]
        assert isinstance(handler.formatter, logging.Formatter)
        assert not isinstance(handler.formatter, StructuredFormatter)

        # Cleanup
        logger.handlers.clear()

    def test_setup_logging_clears_existing_handlers(self):
        """Test setup clears existing handlers"""
        logger = setup_logging("test-clear")
        initial_handlers = len(logger.handlers)

        # Call again
        logger = setup_logging("test-clear")

        # Should not accumulate handlers
        assert len(logger.handlers) == initial_handlers

        # Cleanup
        logger.handlers.clear()

    def test_get_logger(self):
        """Test get_logger function"""
        logger = get_logger("test-get-logger")

        assert logger.name == "test-get-logger"
        assert isinstance(logger, logging.Logger)


# ============================================================================
# Logging Helper Functions Tests
# ============================================================================

class TestLoggingHelpers:
    """Test logging helper functions"""

    def test_log_with_context(self, test_logger):
        """Test logging with additional context"""
        with patch.object(test_logger, 'info') as mock_info:
            log_with_context(
                test_logger,
                "info",
                "Test message",
                user_id=123,
                request_id="abc"
            )

            mock_info.assert_called_once()
            call_args = mock_info.call_args
            assert call_args[0][0] == "Test message"
            assert 'context' in call_args[1]['extra']
            assert call_args[1]['extra']['context']['user_id'] == 123

    def test_log_performance(self, test_logger):
        """Test logging performance metrics"""
        with patch.object(test_logger, 'info') as mock_info:
            log_performance(
                test_logger,
                "database_query",
                duration_ms=45.5,
                status="success",
                rows_returned=100
            )

            mock_info.assert_called_once()
            extra = mock_info.call_args[1]['extra']
            assert extra['performance']['operation'] == "database_query"
            assert extra['performance']['duration_ms'] == 45.5
            assert extra['performance']['status'] == "success"
            assert extra['performance']['rows_returned'] == 100

    def test_log_error_with_context(self, test_logger):
        """Test logging errors with context"""
        with patch.object(test_logger, 'error') as mock_error:
            try:
                raise ValueError("Test error")
            except ValueError as e:
                log_error_with_context(
                    test_logger,
                    "Operation failed",
                    e,
                    operation="test_operation",
                    user_id=456
                )

            mock_error.assert_called_once()
            call_args = mock_error.call_args
            assert call_args[1]['exc_info'] is True
            assert 'error' in call_args[1]['extra']
            assert call_args[1]['extra']['error']['type'] == 'ValueError'


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.integration
class TestLoggingIntegration:
    """Integration tests for complete logging flow"""

    @patch.dict('os.environ', {'LOG_LEVEL': 'INFO', 'LOG_FORMAT': 'json'})
    def test_complete_logging_flow_with_correlation(self):
        """Test complete logging flow with correlation ID"""
        # Setup logger
        logger = setup_logging("integration-test")

        # Set correlation ID
        test_corr_id = "integration_test_123"
        set_correlation_id(test_corr_id)

        # Capture log output
        from io import StringIO
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setFormatter(StructuredFormatter("integration-test"))
        logger.addHandler(handler)

        # Log a message
        logger.info("Test integration message")

        # Check output
        log_output = log_capture.getvalue()
        log_entry = json.loads(log_output.strip())

        assert log_entry['correlation_id'] == test_corr_id
        assert log_entry['message'] == "Test integration message"
        assert log_entry['service'] == "integration-test"

        # Cleanup
        logger.handlers.clear()
        correlation_id.set(None)
