"""Structured logging service for comprehensive logging and monitoring."""

import logging
import json
import os
import sys
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import threading
from queue import Queue, Empty
import gzip
import shutil
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler


class LogLevel(Enum):
    """Log level enumeration."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class LogEntry:
    """Structured log entry."""
    timestamp: str
    level: str
    service: str
    component: str
    message: str
    event_id: Optional[str] = None
    entity_id: Optional[str] = None
    processing_time_ms: Optional[float] = None
    correlation_id: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert log entry to dictionary."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert log entry to JSON string."""
        return json.dumps(self.to_dict(), default=str)


class StructuredLogger:
    """Structured logger for JSON-formatted logs."""
    
    def __init__(self, service_name: str, component: str = "main"):
        """
        Initialize structured logger.
        
        Args:
            service_name: Name of the service
            component: Component name within the service
        """
        self.service_name = service_name
        self.component = component
        self.correlation_id = None
        self.session_id = None
        self.user_id = None
    
    def set_context(self, correlation_id: Optional[str] = None, 
                   session_id: Optional[str] = None, 
                   user_id: Optional[str] = None):
        """Set logging context."""
        self.correlation_id = correlation_id
        self.session_id = session_id
        self.user_id = user_id
    
    def _create_log_entry(self, level: str, message: str, 
                         event_id: Optional[str] = None,
                         entity_id: Optional[str] = None,
                         processing_time_ms: Optional[float] = None,
                         metadata: Optional[Dict[str, Any]] = None) -> LogEntry:
        """Create a structured log entry."""
        return LogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            level=level,
            service=self.service_name,
            component=self.component,
            message=message,
            event_id=event_id,
            entity_id=entity_id,
            processing_time_ms=processing_time_ms,
            correlation_id=self.correlation_id,
            user_id=self.user_id,
            session_id=self.session_id,
            metadata=metadata
        )
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        entry = self._create_log_entry(LogLevel.DEBUG.value, message, **kwargs)
        logging.getLogger(self.service_name).debug(entry.to_json())
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        entry = self._create_log_entry(LogLevel.INFO.value, message, **kwargs)
        logging.getLogger(self.service_name).info(entry.to_json())
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        entry = self._create_log_entry(LogLevel.WARNING.value, message, **kwargs)
        logging.getLogger(self.service_name).warning(entry.to_json())
    
    def error(self, message: str, **kwargs):
        """Log error message."""
        entry = self._create_log_entry(LogLevel.ERROR.value, message, **kwargs)
        logging.getLogger(self.service_name).error(entry.to_json())
    
    def critical(self, message: str, **kwargs):
        """Log critical message."""
        entry = self._create_log_entry(LogLevel.CRITICAL.value, message, **kwargs)
        logging.getLogger(self.service_name).critical(entry.to_json())


class LogAggregator:
    """Centralized log aggregation service."""
    
    def __init__(self, log_dir: str = "/app/logs"):
        """
        Initialize log aggregator.
        
        Args:
            log_dir: Directory for log files
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Log storage
        self.log_entries: List[LogEntry] = []
        self.log_lock = threading.Lock()
        self.max_memory_entries = int(os.getenv('LOG_MAX_MEMORY_ENTRIES', '10000'))
        
        # Log rotation settings
        self.max_file_size = int(os.getenv('LOG_MAX_FILE_SIZE_MB', '100')) * 1024 * 1024
        self.backup_count = int(os.getenv('LOG_BACKUP_COUNT', '10'))
        self.rotation_interval = os.getenv('LOG_ROTATION_INTERVAL', 'midnight')
        
        # Setup log handlers
        self._setup_log_handlers()
        
        # Background processing
        self.processing_queue = Queue()
        self.is_processing = False
        self.processing_task = None
    
    def _setup_log_handlers(self):
        """Setup log handlers for structured logging."""
        # Create formatter for structured logs
        formatter = logging.Formatter('%(message)s')
        
        # File handler with rotation
        log_file = self.log_dir / "homeiq.log"
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        
        # Time-based rotation handler
        time_handler = TimedRotatingFileHandler(
            self.log_dir / "homeiq-time.log",
            when=self.rotation_interval,
            interval=1,
            backupCount=self.backup_count
        )
        time_handler.setFormatter(formatter)
        time_handler.setLevel(logging.INFO)
        
        # Console handler for development
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(time_handler)
        
        # Add console handler in development
        if os.getenv('ENVIRONMENT', 'production').lower() == 'development':
            root_logger.addHandler(console_handler)
    
    async def start(self):
        """Start log aggregation processing."""
        if self.is_processing:
            return
        
        self.is_processing = True
        self.processing_task = asyncio.create_task(self._process_logs())
    
    async def stop(self):
        """Stop log aggregation processing."""
        if not self.is_processing:
            return
        
        self.is_processing = False
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
    
    async def _process_logs(self):
        """Process log entries in background."""
        while self.is_processing:
            try:
                # Process queued log entries
                while not self.processing_queue.empty():
                    try:
                        log_entry = self.processing_queue.get_nowait()
                        await self._store_log_entry(log_entry)
                    except Empty:
                        break
                
                # Cleanup old entries if needed
                await self._cleanup_old_entries()
                
                # Wait before next processing cycle
                await asyncio.sleep(1)
                
            except Exception as e:
                logging.error(f"Error processing logs: {e}")
                await asyncio.sleep(5)
    
    async def _store_log_entry(self, log_entry: LogEntry):
        """Store log entry."""
        with self.log_lock:
            self.log_entries.append(log_entry)
            
            # Limit memory usage
            if len(self.log_entries) > self.max_memory_entries:
                self.log_entries = self.log_entries[-self.max_memory_entries:]
    
    async def _cleanup_old_entries(self):
        """Cleanup old log entries based on retention policy."""
        retention_hours = int(os.getenv('LOG_RETENTION_HOURS', '168'))  # 7 days default
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=retention_hours)
        
        with self.log_lock:
            self.log_entries = [
                entry for entry in self.log_entries
                if datetime.fromisoformat(entry.timestamp.replace('Z', '+00:00')) > cutoff_time
            ]
    
    def add_log_entry(self, log_entry: LogEntry):
        """Add log entry to processing queue."""
        self.processing_queue.put(log_entry)
    
    def get_recent_logs(self, limit: int = 100, 
                       level: Optional[str] = None,
                       service: Optional[str] = None,
                       component: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recent log entries."""
        with self.log_lock:
            logs = self.log_entries.copy()
        
        # Apply filters
        if level:
            logs = [log for log in logs if log.level == level]
        if service:
            logs = [log for log in logs if log.service == service]
        if component:
            logs = [log for log in logs if log.component == component]
        
        # Sort by timestamp (newest first) and limit
        logs.sort(key=lambda x: x.timestamp, reverse=True)
        return [log.to_dict() for log in logs[:limit]]
    
    def get_log_statistics(self) -> Dict[str, Any]:
        """Get log statistics."""
        with self.log_lock:
            logs = self.log_entries.copy()
        
        if not logs:
            return {
                "total_entries": 0,
                "level_counts": {},
                "service_counts": {},
                "component_counts": {},
                "oldest_entry": None,
                "newest_entry": None
            }
        
        # Count by level
        level_counts = {}
        for log in logs:
            level_counts[log.level] = level_counts.get(log.level, 0) + 1
        
        # Count by service
        service_counts = {}
        for log in logs:
            service_counts[log.service] = service_counts.get(log.service, 0) + 1
        
        # Count by component
        component_counts = {}
        for log in logs:
            component_counts[log.component] = component_counts.get(log.component, 0) + 1
        
        # Find oldest and newest entries
        timestamps = [log.timestamp for log in logs]
        oldest_entry = min(timestamps)
        newest_entry = max(timestamps)
        
        return {
            "total_entries": len(logs),
            "level_counts": level_counts,
            "service_counts": service_counts,
            "component_counts": component_counts,
            "oldest_entry": oldest_entry,
            "newest_entry": newest_entry,
            "memory_usage_mb": len(logs) * 0.001  # Rough estimate
        }
    
    def compress_old_logs(self) -> int:
        """Compress old log files."""
        compressed_count = 0
        
        for log_file in self.log_dir.glob("*.log.*"):
            if not log_file.name.endswith('.gz'):
                try:
                    # Compress the file
                    with open(log_file, 'rb') as f_in:
                        with gzip.open(f"{log_file}.gz", 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    
                    # Remove original file
                    log_file.unlink()
                    compressed_count += 1
                    
                except Exception as e:
                    logging.error(f"Error compressing {log_file}: {e}")
        
        return compressed_count
    
    def cleanup_old_compressed_logs(self, days_to_keep: int = 30) -> int:
        """Cleanup old compressed log files."""
        cutoff_time = datetime.now() - timedelta(days=days_to_keep)
        deleted_count = 0
        
        for log_file in self.log_dir.glob("*.log.*.gz"):
            try:
                if datetime.fromtimestamp(log_file.stat().st_mtime) < cutoff_time:
                    log_file.unlink()
                    deleted_count += 1
            except Exception as e:
                logging.error(f"Error deleting {log_file}: {e}")
        
        return deleted_count


class LoggingService:
    """Main logging service for the application."""
    
    def __init__(self):
        """Initialize logging service."""
        self.aggregator = LogAggregator("/app/logs")
        self.loggers: Dict[str, StructuredLogger] = {}
        self.is_running = False
    
    async def start(self):
        """Start the logging service."""
        if self.is_running:
            return
        
        await self.aggregator.start()
        self.is_running = True
        
        # Log service startup
        logger = self.get_logger("logging-service", "main")
        logger.info("Logging service started", event_id="logging_service_start")
    
    async def stop(self):
        """Stop the logging service."""
        if not self.is_running:
            return
        
        # Log service shutdown
        logger = self.get_logger("logging-service", "main")
        logger.info("Logging service stopping", event_id="logging_service_stop")
        
        await self.aggregator.stop()
        self.is_running = False
    
    def get_logger(self, service_name: str, component: str = "main") -> StructuredLogger:
        """Get or create a structured logger."""
        logger_key = f"{service_name}:{component}"
        
        if logger_key not in self.loggers:
            self.loggers[logger_key] = StructuredLogger(service_name, component)
        
        return self.loggers[logger_key]
    
    def get_recent_logs(self, limit: int = 100, **filters) -> List[Dict[str, Any]]:
        """Get recent log entries."""
        return self.aggregator.get_recent_logs(limit, **filters)
    
    def get_log_statistics(self) -> Dict[str, Any]:
        """Get log statistics."""
        return self.aggregator.get_log_statistics()
    
    def compress_old_logs(self) -> int:
        """Compress old log files."""
        return self.aggregator.compress_old_logs()
    
    def cleanup_old_compressed_logs(self, days_to_keep: int = 30) -> int:
        """Cleanup old compressed log files."""
        return self.aggregator.cleanup_old_compressed_logs(days_to_keep)


# Global logging service instance
logging_service = LoggingService()
