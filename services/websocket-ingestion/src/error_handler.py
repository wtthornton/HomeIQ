"""
Error Handler for WebSocket Connection Management
"""

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Categories of errors that can occur"""
    NETWORK = "network"
    AUTHENTICATION = "authentication"
    SUBSCRIPTION = "subscription"
    WEBSOCKET = "websocket"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


class ErrorSeverity(Enum):
    """Severity levels for errors"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorHandler:
    """Handles error categorization, logging, and tracking"""

    def __init__(self):
        self.error_counts: dict[ErrorCategory, int] = dict.fromkeys(ErrorCategory, 0)
        self.error_history: list = []
        self.max_history_size = 100
        self.last_error_time: datetime | None = None

        # Error rate tracking
        self.error_rate_window_minutes = 5
        self.recent_errors: list = []

    def categorize_error(self, error: Exception) -> tuple[ErrorCategory, ErrorSeverity]:
        """
        Categorize an error and determine its severity
        
        Args:
            error: The exception to categorize
            
        Returns:
            Tuple of (category, severity)
        """
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()

        # Network errors
        if any(keyword in error_str for keyword in ['connection', 'network', 'unreachable', 'timeout', 'refused']):
            if 'timeout' in error_str:
                return ErrorCategory.TIMEOUT, ErrorSeverity.MEDIUM
            return ErrorCategory.NETWORK, ErrorSeverity.HIGH

        # Authentication errors
        if any(keyword in error_str for keyword in ['auth', 'token', 'unauthorized', 'forbidden', 'invalid']):
            return ErrorCategory.AUTHENTICATION, ErrorSeverity.CRITICAL

        # WebSocket specific errors
        if any(keyword in error_str for keyword in ['websocket', 'ws', 'protocol', 'handshake']):
            return ErrorCategory.WEBSOCKET, ErrorSeverity.HIGH

        # Subscription errors
        if any(keyword in error_str for keyword in ['subscription', 'subscribe', 'event']):
            return ErrorCategory.SUBSCRIPTION, ErrorSeverity.MEDIUM

        # Default categorization
        return ErrorCategory.UNKNOWN, ErrorSeverity.LOW

    def log_error(self, error: Exception, context: dict[str, Any] = None) -> dict[str, Any]:
        """
        Log an error with categorization and context
        
        Args:
            error: The exception to log
            context: Additional context information
            
        Returns:
            Dictionary with error information
        """
        category, severity = self.categorize_error(error)
        timestamp = datetime.now(timezone.utc)

        # Create error record
        error_record = {
            "timestamp": timestamp.isoformat(),
            "category": category.value,
            "severity": severity.value,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context or {}
        }

        # Update error counts
        self.error_counts[category] += 1
        self.last_error_time = timestamp

        # Add to history
        self.error_history.append(error_record)
        if len(self.error_history) > self.max_history_size:
            self.error_history.pop(0)

        # Add to recent errors for rate calculation
        self.recent_errors.append(timestamp)
        self._clean_old_errors()

        # Log based on severity
        log_message = f"[{category.value.upper()}] {type(error).__name__}: {str(error)}"
        if context:
            log_message += f" | Context: {context}"

        if severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message)
        elif severity == ErrorSeverity.HIGH:
            logger.error(log_message)
        elif severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message)
        else:
            logger.info(log_message)

        return error_record

    def _clean_old_errors(self):
        """Remove errors older than the rate window"""
        cutoff_time = datetime.now(timezone.utc).timestamp() - (self.error_rate_window_minutes * 60)
        self.recent_errors = [ts for ts in self.recent_errors if ts.timestamp() > cutoff_time]

    def get_error_rate(self) -> float:
        """
        Get current error rate (errors per minute)
        
        Returns:
            Error rate in errors per minute
        """
        self._clean_old_errors()
        return len(self.recent_errors) / self.error_rate_window_minutes

    def get_error_statistics(self) -> dict[str, Any]:
        """
        Get comprehensive error statistics
        
        Returns:
            Dictionary with error statistics
        """
        self._clean_old_errors()

        total_errors = sum(self.error_counts.values())

        return {
            "total_errors": total_errors,
            "error_counts_by_category": {category.value: count for category, count in self.error_counts.items()},
            "error_rate_per_minute": self.get_error_rate(),
            "last_error_time": self.last_error_time.isoformat() if self.last_error_time else None,
            "recent_errors_count": len(self.recent_errors),
            "error_history_size": len(self.error_history),
            "most_common_category": max(self.error_counts.items(), key=lambda x: x[1])[0].value if total_errors > 0 else None
        }

    def get_recent_errors(self, limit: int = 10) -> list:
        """
        Get recent error records
        
        Args:
            limit: Maximum number of errors to return
            
        Returns:
            List of recent error records
        """
        return self.error_history[-limit:] if self.error_history else []

    def reset_statistics(self):
        """Reset error statistics"""
        self.error_counts = dict.fromkeys(ErrorCategory, 0)
        self.error_history.clear()
        self.recent_errors.clear()
        self.last_error_time = None
        logger.info("Error statistics reset")

    def should_alert(self, threshold_rate: float = 5.0) -> bool:
        """
        Check if error rate exceeds alert threshold
        
        Args:
            threshold_rate: Error rate threshold (errors per minute)
            
        Returns:
            True if alert should be triggered
        """
        return self.get_error_rate() > threshold_rate
