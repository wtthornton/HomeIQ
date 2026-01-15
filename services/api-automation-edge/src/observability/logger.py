"""
Structured Logging

Epic F1: Structured logs with correlation IDs and secret redaction
"""

import json
import logging
import uuid
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class StructuredLogger:
    """
    Structured logger with correlation IDs.
    
    Features:
    - Correlation IDs across trigger/plan/execute/confirm
    - Structured log format (JSON)
    - Secret redaction
    """
    
    def __init__(self, logger_instance: Optional[logging.Logger] = None):
        """
        Initialize structured logger.
        
        Args:
            logger_instance: Optional logger instance
        """
        self.logger = logger_instance or logger
        self._correlation_id: Optional[str] = None
    
    def set_correlation_id(self, correlation_id: Optional[str] = None):
        """Set correlation ID for current context"""
        self._correlation_id = correlation_id or str(uuid.uuid4())
        return self._correlation_id
    
    def get_correlation_id(self) -> Optional[str]:
        """Get current correlation ID"""
        return self._correlation_id
    
    def _redact_secrets(self, data: Any) -> Any:
        """Recursively redact secrets from data structures"""
        if isinstance(data, dict):
            redacted = {}
            for key, value in data.items():
                if any(secret_key in key.lower() for secret_key in ['token', 'password', 'secret', 'key', 'auth']):
                    redacted[key] = "[REDACTED]"
                else:
                    redacted[key] = self._redact_secrets(value)
            return redacted
        elif isinstance(data, list):
            return [self._redact_secrets(item) for item in data]
        elif isinstance(data, str):
            # Redact if looks like a token (long alphanumeric string)
            if len(data) > 20 and all(c.isalnum() or c in '-_' for c in data):
                return "[REDACTED]"
        return data
    
    def _create_log_entry(
        self,
        level: str,
        message: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Create structured log entry"""
        entry = {
            "timestamp": logging.Formatter().formatTime(
                logging.LogRecord(
                    "", 0, "", 0, message, (), None
                ),
                datefmt="%Y-%m-%d %H:%M:%S"
            ),
            "level": level,
            "message": message,
            "correlation_id": self._correlation_id,
            **kwargs
        }
        return self._redact_secrets(entry)
    
    def log(
        self,
        level: str,
        message: str,
        **kwargs
    ):
        """Log structured message"""
        entry = self._create_log_entry(level, message, **kwargs)
        log_message = json.dumps(entry)
        
        if level == "DEBUG":
            self.logger.debug(log_message)
        elif level == "INFO":
            self.logger.info(log_message)
        elif level == "WARNING":
            self.logger.warning(log_message)
        elif level == "ERROR":
            self.logger.error(log_message)
        else:
            self.logger.info(log_message)
    
    def log_trigger(
        self,
        trigger_type: str,
        trigger_data: Dict[str, Any],
        spec_id: str
    ):
        """Log trigger event"""
        self.log(
            "INFO",
            f"Trigger received: {trigger_type}",
            event_type="trigger",
            trigger_type=trigger_type,
            trigger_data=trigger_data,
            spec_id=spec_id
        )
    
    def log_validation(
        self,
        spec_id: str,
        is_valid: bool,
        errors: list[str],
        execution_plan: Optional[Dict[str, Any]] = None
    ):
        """Log validation result"""
        self.log(
            "INFO" if is_valid else "WARNING",
            f"Validation {'passed' if is_valid else 'failed'} for spec {spec_id}",
            event_type="validation",
            spec_id=spec_id,
            is_valid=is_valid,
            errors=errors,
            execution_plan=execution_plan
        )
    
    def log_execution(
        self,
        spec_id: str,
        execution_result: Dict[str, Any]
    ):
        """Log execution result"""
        self.log(
            "INFO" if execution_result.get("success") else "ERROR",
            f"Execution {'succeeded' if execution_result.get('success') else 'failed'} for spec {spec_id}",
            event_type="execution",
            spec_id=spec_id,
            execution_result=execution_result
        )
    
    def log_confirmation(
        self,
        entity_id: str,
        confirmed: bool,
        error: Optional[str] = None
    ):
        """Log confirmation result"""
        self.log(
            "INFO" if confirmed else "WARNING",
            f"Confirmation {'received' if confirmed else 'failed'} for {entity_id}",
            event_type="confirmation",
            entity_id=entity_id,
            confirmed=confirmed,
            error=error
        )
