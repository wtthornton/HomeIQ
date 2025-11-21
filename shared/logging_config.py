"""
Enhanced Shared Logging Configuration with Structured JSON Logging and Correlation IDs
"""

import json
import logging
import logging.handlers
import os
import sys
import time
import uuid
from contextvars import ContextVar
from datetime import datetime
from functools import wraps

# Context variable for correlation ID
correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging"""

    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON"""
        # Get correlation ID from context
        corr_id = correlation_id.get()

        # Build structured log entry
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "service": self.service_name,
            "message": record.getMessage(),
            "correlation_id": corr_id,
            "context": {
                "filename": record.filename,
                "lineno": record.lineno,
                "function": record.funcName,
                "module": record.module,
                "pathname": record.pathname,
            },
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info),
            }

        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in ["name", "msg", "args", "levelname", "levelno", "pathname",
                          "filename", "module", "lineno", "funcName", "created",
                          "msecs", "relativeCreated", "thread", "threadName",
                          "processName", "process", "getMessage", "exc_info",
                          "exc_text", "stack_info"] and key not in log_entry:
                log_entry[key] = value

        return json.dumps(log_entry, default=str)


class PerformanceLogger:
    """Performance monitoring decorator and context manager"""

    def __init__(self, logger: logging.Logger, operation: str):
        self.logger = logger
        self.operation = operation
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (time.time() - self.start_time) * 1000  # Convert to milliseconds

        # Log performance metrics
        self.logger.info(
            f"Performance: {self.operation}",
            extra={
                "performance": {
                    "operation": self.operation,
                    "duration_ms": round(duration, 2),
                    "status": "error" if exc_type else "success",
                },
            },
        )


def performance_monitor(operation: str | None = None):
    """Decorator for automatic performance monitoring"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get logger from the module or create one
            logger = logging.getLogger(func.__module__)
            op_name = operation or f"{func.__module__}.{func.__name__}"

            with PerformanceLogger(logger, op_name):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def generate_correlation_id() -> str:
    """Generate a new correlation ID"""
    return f"req_{int(time.time())}_{uuid.uuid4().hex[:8]}"


def set_correlation_id(corr_id: str):
    """Set correlation ID in context"""
    correlation_id.set(corr_id)


def get_correlation_id() -> str | None:
    """Get current correlation ID from context"""
    return correlation_id.get()


def setup_logging(service_name: str, log_level: str | None = None, log_format: str | None = None):
    """
    Set up enhanced logging configuration for a service

    Args:
        service_name: Name of the service
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Log format ('json' or 'text')
    """
    # Get configuration from environment
    level = log_level or os.getenv("LOG_LEVEL", "INFO")
    format_type = log_format or os.getenv("LOG_FORMAT", "json")
    output = os.getenv("LOG_OUTPUT", "stdout")

    # Create logger
    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, level.upper()))

    # Clear existing handlers
    logger.handlers.clear()

    # Create formatter based on format type
    if format_type.lower() == "json":
        formatter = StructuredFormatter(service_name)
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    # Create handlers based on output configuration
    if output in ["stdout", "both"]:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    if output in ["file", "both"]:
        log_file_path = os.getenv("LOG_FILE_PATH", "/var/log/homeiq/")
        os.makedirs(log_file_path, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            filename=os.path.join(log_file_path, f"{service_name}.log"),
            maxBytes=int(os.getenv("LOG_MAX_SIZE", "104857600")),  # 100MB default
            backupCount=int(os.getenv("LOG_BACKUP_COUNT", "5")),
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Prevent duplicate logs
    logger.propagate = False

    return logger


def get_logger(service_name: str) -> logging.Logger:
    """
    Get a logger for a specific service

    Args:
        service_name: Name of the service

    Returns:
        Logger instance
    """
    return logging.getLogger(service_name)


def log_with_context(logger: logging.Logger, level: str, message: str, **context):
    """
    Log a message with additional context information

    Args:
        logger: Logger instance
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        message: Log message
        **context: Additional context information
    """
    getattr(logger, level.lower())(
        message,
        extra={"context": context},
    )


def log_performance(logger: logging.Logger, operation: str, duration_ms: float,
                   status: str = "success", **metrics):
    """
    Log performance metrics

    Args:
        logger: Logger instance
        operation: Operation name
        duration_ms: Duration in milliseconds
        status: Operation status (success, error, timeout)
        **metrics: Additional performance metrics
    """
    logger.info(
        f"Performance: {operation}",
        extra={
            "performance": {
                "operation": operation,
                "duration_ms": round(duration_ms, 2),
                "status": status,
                **metrics,
            },
        },
    )


def log_error_with_context(logger: logging.Logger, message: str, error: Exception,
                          **context):
    """
    Log an error with full context and stack trace

    Args:
        logger: Logger instance
        message: Error message
        error: Exception instance
        **context: Additional context information
    """
    logger.error(
        message,
        extra={
            "context": context,
            "error": {
                "type": type(error).__name__,
                "message": str(error),
                "code": getattr(error, "code", None),
            },
        },
        exc_info=True,
    )
