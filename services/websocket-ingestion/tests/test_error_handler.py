"""
Tests for Error Handler
"""

import pytest
from datetime import datetime, timedelta
from src.error_handler import ErrorHandler, ErrorCategory, ErrorSeverity


class TestErrorHandler:
    """Test cases for ErrorHandler class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.error_handler = ErrorHandler()
    
    def test_initialization(self):
        """Test error handler initialization"""
        assert self.error_handler.error_counts[ErrorCategory.NETWORK] == 0
        assert self.error_handler.error_counts[ErrorCategory.AUTHENTICATION] == 0
        assert self.error_handler.error_counts[ErrorCategory.SUBSCRIPTION] == 0
        assert self.error_handler.error_counts[ErrorCategory.WEBSOCKET] == 0
        assert self.error_handler.error_counts[ErrorCategory.TIMEOUT] == 0
        assert self.error_handler.error_counts[ErrorCategory.UNKNOWN] == 0
        assert self.error_handler.error_history == []
        assert self.error_handler.last_error_time is None
    
    def test_categorize_network_error(self):
        """Test categorization of network errors"""
        error = ConnectionError("Connection refused")
        category, severity = self.error_handler.categorize_error(error)
        
        assert category == ErrorCategory.NETWORK
        assert severity == ErrorSeverity.HIGH
    
    def test_categorize_timeout_error(self):
        """Test categorization of timeout errors"""
        error = TimeoutError("Connection timeout")
        category, severity = self.error_handler.categorize_error(error)
        
        assert category == ErrorCategory.TIMEOUT
        assert severity == ErrorSeverity.MEDIUM
    
    def test_categorize_authentication_error(self):
        """Test categorization of authentication errors"""
        error = ValueError("Invalid token")
        category, severity = self.error_handler.categorize_error(error)
        
        assert category == ErrorCategory.AUTHENTICATION
        assert severity == ErrorSeverity.CRITICAL
    
    def test_categorize_websocket_error(self):
        """Test categorization of WebSocket errors"""
        error = Exception("WebSocket handshake failed")
        category, severity = self.error_handler.categorize_error(error)
        
        assert category == ErrorCategory.WEBSOCKET
        assert severity == ErrorSeverity.HIGH
    
    def test_categorize_subscription_error(self):
        """Test categorization of subscription errors"""
        error = Exception("Subscription failed")
        category, severity = self.error_handler.categorize_error(error)
        
        assert category == ErrorCategory.SUBSCRIPTION
        assert severity == ErrorSeverity.MEDIUM
    
    def test_categorize_unknown_error(self):
        """Test categorization of unknown errors"""
        error = Exception("Some random error")
        category, severity = self.error_handler.categorize_error(error)
        
        assert category == ErrorCategory.UNKNOWN
        assert severity == ErrorSeverity.LOW
    
    def test_log_error(self):
        """Test error logging"""
        error = ConnectionError("Connection failed")
        context = {"url": "ws://test", "attempt": 1}
        
        error_record = self.error_handler.log_error(error, context)
        
        assert error_record["category"] == ErrorCategory.NETWORK.value
        assert error_record["severity"] == ErrorSeverity.HIGH.value
        assert error_record["error_type"] == "ConnectionError"
        assert error_record["error_message"] == "Connection failed"
        assert error_record["context"] == context
        assert "timestamp" in error_record
        
        # Check error counts
        assert self.error_handler.error_counts[ErrorCategory.NETWORK] == 1
        assert self.error_handler.last_error_time is not None
        assert len(self.error_handler.error_history) == 1
    
    def test_log_multiple_errors(self):
        """Test logging multiple errors"""
        # Log network error
        self.error_handler.log_error(ConnectionError("Connection failed"))
        
        # Log authentication error
        self.error_handler.log_error(ValueError("Invalid token"))
        
        # Log subscription error
        self.error_handler.log_error(Exception("Subscription failed"))
        
        # Check counts
        assert self.error_handler.error_counts[ErrorCategory.NETWORK] == 1
        assert self.error_handler.error_counts[ErrorCategory.AUTHENTICATION] == 1
        assert self.error_handler.error_counts[ErrorCategory.SUBSCRIPTION] == 1
        assert self.error_handler.error_counts[ErrorCategory.WEBSOCKET] == 0
        assert self.error_handler.error_counts[ErrorCategory.TIMEOUT] == 0
        assert self.error_handler.error_counts[ErrorCategory.UNKNOWN] == 0
        
        assert len(self.error_handler.error_history) == 3
    
    def test_error_history_limit(self):
        """Test error history size limit"""
        # Set a small limit for testing
        self.error_handler.max_history_size = 3
        
        # Log more errors than the limit
        for i in range(5):
            self.error_handler.log_error(Exception(f"Error {i}"))
        
        # Should only keep the last 3 errors
        assert len(self.error_handler.error_history) == 3
        
        # Check that the oldest errors were removed
        assert self.error_handler.error_history[0]["error_message"] == "Error 2"
        assert self.error_handler.error_history[1]["error_message"] == "Error 3"
        assert self.error_handler.error_history[2]["error_message"] == "Error 4"
    
    def test_get_error_rate(self):
        """Test error rate calculation"""
        # Log some errors
        self.error_handler.log_error(ConnectionError("Error 1"))
        self.error_handler.log_error(ConnectionError("Error 2"))
        
        # Error rate should be calculated based on recent errors
        rate = self.error_handler.get_error_rate()
        assert rate >= 0  # Should be non-negative
    
    def test_get_error_statistics(self):
        """Test getting error statistics"""
        # Log some errors
        self.error_handler.log_error(ConnectionError("Network error"))
        self.error_handler.log_error(ValueError("Auth error"))
        self.error_handler.log_error(Exception("Unknown error"))
        
        stats = self.error_handler.get_error_statistics()
        
        assert stats["total_errors"] == 3
        assert stats["error_counts_by_category"]["network"] == 1
        assert stats["error_counts_by_category"]["authentication"] == 1
        assert stats["error_counts_by_category"]["unknown"] == 1
        assert stats["error_counts_by_category"]["websocket"] == 0
        assert stats["error_counts_by_category"]["subscription"] == 0
        assert stats["error_counts_by_category"]["timeout"] == 0
        assert stats["last_error_time"] is not None
        assert stats["error_history_size"] == 3
        assert "most_common_category" in stats
    
    def test_get_recent_errors(self):
        """Test getting recent errors"""
        # Log some errors
        self.error_handler.log_error(ConnectionError("Error 1"))
        self.error_handler.log_error(ConnectionError("Error 2"))
        self.error_handler.log_error(ConnectionError("Error 3"))
        
        # Get recent errors
        recent = self.error_handler.get_recent_errors(limit=2)
        
        assert len(recent) == 2
        assert recent[0]["error_message"] == "Error 2"
        assert recent[1]["error_message"] == "Error 3"
    
    def test_reset_statistics(self):
        """Test resetting error statistics"""
        # Log some errors
        self.error_handler.log_error(ConnectionError("Error 1"))
        self.error_handler.log_error(ValueError("Error 2"))
        
        # Reset statistics
        self.error_handler.reset_statistics()
        
        # Check that everything is reset
        assert self.error_handler.error_counts[ErrorCategory.NETWORK] == 0
        assert self.error_handler.error_counts[ErrorCategory.AUTHENTICATION] == 0
        assert self.error_handler.error_history == []
        assert self.error_handler.recent_errors == []
        assert self.error_handler.last_error_time is None
    
    def test_should_alert(self):
        """Test alert threshold checking"""
        # With no errors, should not alert
        assert not self.error_handler.should_alert(threshold_rate=1.0)
        
        # Log some errors
        for i in range(10):
            self.error_handler.log_error(ConnectionError(f"Error {i}"))
        
        # Should alert if threshold is low enough
        assert self.error_handler.should_alert(threshold_rate=1.0)
    
    def test_clean_old_errors(self):
        """Test cleaning old errors from rate calculation"""
        # Log an error
        self.error_handler.log_error(ConnectionError("Error"))
        
        # Manually add old timestamps to recent_errors
        old_time = datetime.now() - timedelta(minutes=10)
        self.error_handler.recent_errors.append(old_time)
        
        # Clean old errors
        self.error_handler._clean_old_errors()
        
        # Should only have the recent error
        assert len(self.error_handler.recent_errors) == 1
    
    def test_log_error_without_context(self):
        """Test logging error without context"""
        error = ConnectionError("Connection failed")
        
        error_record = self.error_handler.log_error(error)
        
        assert error_record["context"] == {}
        assert self.error_handler.error_counts[ErrorCategory.NETWORK] == 1
