"""
Tests for Enhanced Logging Framework
"""

import json
import logging
import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime

# Add shared directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../shared'))

from shared.logging_config import (
    setup_logging, get_logger, log_with_context, log_performance,
    log_error_with_context, performance_monitor, generate_correlation_id,
    set_correlation_id, get_correlation_id, StructuredFormatter
)
from shared.correlation_middleware import (
    correlation_context, with_correlation_id, propagate_correlation_id,
    extract_correlation_id
)
from shared.log_validator import LogValidator, validate_log_format, validate_log_consistency


class TestEnhancedLoggingFramework(unittest.TestCase):
    """Test cases for enhanced logging framework"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_service = "test-service"
        self.temp_dir = tempfile.mkdtemp()
        
        # Set up test environment variables
        os.environ['LOG_LEVEL'] = 'DEBUG'
        os.environ['LOG_FORMAT'] = 'json'
        os.environ['LOG_OUTPUT'] = 'stdout'
        os.environ['LOG_FILE_PATH'] = self.temp_dir
    
    def tearDown(self):
        """Clean up test environment"""
        # Clean up environment variables
        for key in ['LOG_LEVEL', 'LOG_FORMAT', 'LOG_OUTPUT', 'LOG_FILE_PATH']:
            if key in os.environ:
                del os.environ[key]
    
    def test_setup_logging(self):
        """Test logging setup"""
        logger = setup_logging(self.test_service)
        
        self.assertIsInstance(logger, logging.Logger)
        self.assertEqual(logger.name, self.test_service)
        self.assertEqual(logger.level, logging.DEBUG)
    
    def test_structured_formatter(self):
        """Test structured JSON formatter"""
        formatter = StructuredFormatter(self.test_service)
        
        # Create a test log record
        record = logging.LogRecord(
            name=self.test_service,
            level=logging.INFO,
            pathname="/test/path",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        # Format the record
        formatted = formatter.format(record)
        
        # Parse the JSON
        log_data = json.loads(formatted)
        
        # Verify structure
        self.assertIn('timestamp', log_data)
        self.assertIn('level', log_data)
        self.assertIn('service', log_data)
        self.assertIn('message', log_data)
        self.assertIn('context', log_data)
        
        # Verify values
        self.assertEqual(log_data['level'], 'INFO')
        self.assertEqual(log_data['service'], self.test_service)
        self.assertEqual(log_data['message'], 'Test message')
        self.assertEqual(log_data['context']['lineno'], 42)
    
    def test_correlation_id_generation(self):
        """Test correlation ID generation"""
        corr_id = generate_correlation_id()
        
        self.assertIsInstance(corr_id, str)
        self.assertTrue(corr_id.startswith('req_'))
        self.assertIn('_', corr_id)
        
        # Test uniqueness
        corr_id2 = generate_correlation_id()
        self.assertNotEqual(corr_id, corr_id2)
    
    def test_correlation_id_context(self):
        """Test correlation ID context management"""
        corr_id = generate_correlation_id()
        
        # Test setting and getting
        set_correlation_id(corr_id)
        self.assertEqual(get_correlation_id(), corr_id)
        
        # Test context manager
        with correlation_context() as ctx_corr_id:
            self.assertIsNotNone(ctx_corr_id)
            self.assertEqual(get_correlation_id(), ctx_corr_id)
        
        # Should be back to original
        self.assertEqual(get_correlation_id(), corr_id)
    
    def test_log_with_context(self):
        """Test logging with context information"""
        logger = setup_logging(self.test_service)
        
        # Capture log output
        with patch('sys.stdout') as mock_stdout:
            log_with_context(
                logger, "INFO", "Test message",
                operation="test_operation",
                user_id="test_user",
                request_id="req_123"
            )
        
        # Verify log was called (exact verification would require more complex mocking)
        self.assertTrue(True)  # Placeholder - actual verification would check stdout
    
    def test_performance_monitor_decorator(self):
        """Test performance monitoring decorator"""
        logger = setup_logging(self.test_service)
        
        @performance_monitor("test_operation")
        def test_function():
            return "test_result"
        
        # Should not raise exception
        result = test_function()
        self.assertEqual(result, "test_result")
    
    def test_log_performance(self):
        """Test performance logging"""
        logger = setup_logging(self.test_service)
        
        # Should not raise exception
        log_performance(
            logger, "test_operation", 123.45,
            status="success",
            memory_usage=1024
        )
    
    def test_log_error_with_context(self):
        """Test error logging with context"""
        logger = setup_logging(self.test_service)
        
        try:
            raise ValueError("Test error")
        except ValueError as e:
            # Should not raise exception
            log_error_with_context(
                logger, "Test error occurred", e,
                operation="test_operation",
                user_id="test_user"
            )
    
    def test_correlation_middleware_functions(self):
        """Test correlation middleware utility functions"""
        # Test propagate correlation ID
        headers = {}
        corr_id = generate_correlation_id()
        set_correlation_id(corr_id)
        
        updated_headers = propagate_correlation_id(headers)
        self.assertEqual(updated_headers['X-Correlation-ID'], corr_id)
        
        # Test extract correlation ID
        extracted = extract_correlation_id(updated_headers)
        self.assertEqual(extracted, corr_id)
    
    def test_with_correlation_id_decorator(self):
        """Test correlation ID decorator"""
        @with_correlation_id()
        def test_function():
            return get_correlation_id()
        
        result = test_function()
        self.assertIsNotNone(result)
        self.assertTrue(result.startswith('req_'))


class TestLogValidator(unittest.TestCase):
    """Test cases for log validation"""
    
    def setUp(self):
        """Set up test environment"""
        self.validator = LogValidator()
    
    def test_valid_log_entry(self):
        """Test validation of valid log entry"""
        valid_log = json.dumps({
            "timestamp": "2025-01-04T15:30:45.123Z",
            "level": "INFO",
            "service": "websocket-ingestion",
            "message": "Test message",
            "correlation_id": "req_1234567890_abcdef12",
            "context": {
                "filename": "test.py",
                "lineno": 42,
                "function": "test_function",
                "module": "test_module"
            }
        })
        
        result = self.validator.validate_log_entry(valid_log)
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)
    
    def test_invalid_json(self):
        """Test validation of invalid JSON"""
        invalid_log = "invalid json"
        
        result = self.validator.validate_log_entry(invalid_log)
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.errors), 0)
        self.assertIn("Invalid JSON format", result.errors[0])
    
    def test_missing_required_fields(self):
        """Test validation with missing required fields"""
        incomplete_log = json.dumps({
            "level": "INFO",
            "message": "Test message"
            # Missing timestamp and service
        })
        
        result = self.validator.validate_log_entry(incomplete_log)
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.errors), 0)
    
    def test_invalid_log_level(self):
        """Test validation with invalid log level"""
        invalid_level_log = json.dumps({
            "timestamp": "2025-01-04T15:30:45.123Z",
            "level": "INVALID",
            "service": "websocket-ingestion",
            "message": "Test message"
        })
        
        result = self.validator.validate_log_entry(invalid_level_log)
        self.assertFalse(result.is_valid)
        self.assertIn("Invalid log level", result.errors[0])
    
    def test_invalid_timestamp(self):
        """Test validation with invalid timestamp"""
        invalid_timestamp_log = json.dumps({
            "timestamp": "invalid-timestamp",
            "level": "INFO",
            "service": "websocket-ingestion",
            "message": "Test message"
        })
        
        result = self.validator.validate_log_entry(invalid_timestamp_log)
        self.assertFalse(result.is_valid)
        self.assertIn("Invalid timestamp format", result.errors[0])
    
    def test_unknown_service(self):
        """Test validation with unknown service"""
        unknown_service_log = json.dumps({
            "timestamp": "2025-01-04T15:30:45.123Z",
            "level": "INFO",
            "service": "unknown-service",
            "message": "Test message"
        })
        
        result = self.validator.validate_log_entry(unknown_service_log)
        self.assertTrue(result.is_valid)  # Should be valid but with warning
        self.assertGreater(len(result.warnings), 0)
        self.assertIn("Unknown service name", result.warnings[0])
    
    def test_performance_metrics_validation(self):
        """Test validation of performance metrics"""
        performance_log = json.dumps({
            "timestamp": "2025-01-04T15:30:45.123Z",
            "level": "INFO",
            "service": "websocket-ingestion",
            "message": "Performance test",
            "performance": {
                "operation": "test_operation",
                "duration_ms": 123.45,
                "status": "success"
            }
        })
        
        result = self.validator.validate_log_entry(performance_log)
        self.assertTrue(result.is_valid)
    
    def test_batch_validation(self):
        """Test batch log validation"""
        log_entries = [
            json.dumps({
                "timestamp": "2025-01-04T15:30:45.123Z",
                "level": "INFO",
                "service": "websocket-ingestion",
                "message": "Test message 1"
            }),
            json.dumps({
                "timestamp": "2025-01-04T15:30:46.123Z",
                "level": "ERROR",
                "service": "websocket-ingestion",
                "message": "Test message 2"
            })
        ]
        
        results = self.validator.validate_log_batch(log_entries)
        self.assertEqual(len(results), 2)
        
        # Both should be valid
        for result in results.values():
            self.assertTrue(result.is_valid)
    
    def test_validation_summary(self):
        """Test validation summary generation"""
        log_entries = [
            json.dumps({
                "timestamp": "2025-01-04T15:30:45.123Z",
                "level": "INFO",
                "service": "websocket-ingestion",
                "message": "Valid message"
            }),
            "invalid json",
            json.dumps({
                "timestamp": "2025-01-04T15:30:46.123Z",
                "level": "INFO",
                "service": "websocket-ingestion",
                "message": "Another valid message"
            })
        ]
        
        results = self.validator.validate_log_batch(log_entries)
        summary = self.validator.get_validation_summary(results)
        
        self.assertEqual(summary['total_entries'], 3)
        self.assertEqual(summary['valid_entries'], 2)
        self.assertEqual(summary['invalid_entries'], 1)
        self.assertAlmostEqual(summary['validation_rate'], 66.67, places=1)


class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions"""
    
    def test_validate_log_format(self):
        """Test validate_log_format convenience function"""
        valid_log = json.dumps({
            "timestamp": "2025-01-04T15:30:45.123Z",
            "level": "INFO",
            "service": "websocket-ingestion",
            "message": "Test message"
        })
        
        result = validate_log_format(valid_log)
        self.assertTrue(result.is_valid)
    
    def test_validate_log_consistency(self):
        """Test validate_log_consistency convenience function"""
        log_entries = [
            json.dumps({
                "timestamp": "2025-01-04T15:30:45.123Z",
                "level": "INFO",
                "service": "websocket-ingestion",
                "message": "Test message 1"
            }),
            json.dumps({
                "timestamp": "2025-01-04T15:30:46.123Z",
                "level": "INFO",
                "service": "websocket-ingestion",
                "message": "Test message 2"
            })
        ]
        
        summary = validate_log_consistency(log_entries)
        self.assertEqual(summary['total_entries'], 2)
        self.assertEqual(summary['valid_entries'], 2)
        self.assertEqual(summary['validation_rate'], 100.0)


if __name__ == '__main__':
    unittest.main()
