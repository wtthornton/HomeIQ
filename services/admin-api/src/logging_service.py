"""
Structured logging utilities for admin-api tests.

The module provides lightweight implementations with in-memory storage to
simulate logging aggregation workflows during unit testing.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class LogEntry:
    timestamp: str
    level: str
    service: str
    component: str
    message: str
    event_id: Optional[str] = None
    metadata: Dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        return {
            "timestamp": self.timestamp,
            "level": self.level,
            "service": self.service,
            "component": self.component,
            "message": self.message,
            "event_id": self.event_id,
            "metadata": dict(self.metadata),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class StructuredLogger:
    def __init__(self, service_name: str, component: str) -> None:
        self.service_name = service_name
        self.component = component
        self.correlation_id: Optional[str] = None
        self.session_id: Optional[str] = None
        self.user_id: Optional[str] = None

    def set_context(
        self,
        *,
        correlation_id: Optional[str] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> None:
        self.correlation_id = correlation_id
        self.session_id = session_id
        self.user_id = user_id

    def _log(self, level: str, message: str, *, event_id: Optional[str] = None, **metadata) -> None:
        logger = logging.getLogger(f"{self.service_name}.{self.component}")
        entry = {
            "service": self.service_name,
            "component": self.component,
            "message": message,
            "event_id": event_id,
            "correlation_id": self.correlation_id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            **metadata,
        }
        if level == LogLevel.DEBUG.value:
            logger.debug(entry)
        elif level == LogLevel.INFO.value:
            logger.info(entry)
        elif level == LogLevel.WARNING.value:
            logger.warning(entry)
        elif level == LogLevel.ERROR.value:
            logger.error(entry)
        else:
            logger.critical(entry)

    def debug(self, message: str, **kwargs) -> None:
        self._log(LogLevel.DEBUG.value, message, **kwargs)

    def info(self, message: str, **kwargs) -> None:
        self._log(LogLevel.INFO.value, message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        self._log(LogLevel.WARNING.value, message, **kwargs)

    def error(self, message: str, **kwargs) -> None:
        self._log(LogLevel.ERROR.value, message, **kwargs)

    def critical(self, message: str, **kwargs) -> None:
        self._log(LogLevel.CRITICAL.value, message, **kwargs)


class LogAggregator:
    def __init__(self, log_dir: str | Path, *, max_memory_entries: int = 10000) -> None:
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_entries: List[LogEntry] = []
        self.max_memory_entries = max_memory_entries
        self.is_processing = False

    def add_log_entry(self, entry: LogEntry) -> None:
        self.log_entries.append(entry)
        if len(self.log_entries) > self.max_memory_entries:
            self.log_entries = self.log_entries[-self.max_memory_entries :]

    def get_recent_logs(
        self,
        *,
        limit: int = 50,
        level: Optional[str] = None,
        service: Optional[str] = None,
        component: Optional[str] = None,
    ) -> List[Dict[str, object]]:
        entries = self.log_entries
        if level:
            entries = [entry for entry in entries if entry.level == level]
        if service:
            entries = [entry for entry in entries if entry.service == service]
        if component:
            entries = [entry for entry in entries if entry.component == component]

        # Sort by timestamp descending when possible
        def sort_key(entry: LogEntry):
            try:
                return datetime.fromisoformat(entry.timestamp.replace("Z", "+00:00"))
            except ValueError:
                return datetime.min

        entries = sorted(entries, key=sort_key, reverse=True)
        return [entry.to_dict() for entry in entries[:limit]]

    def get_log_statistics(self) -> Dict[str, Dict[str, int] | int]:
        level_counts: Dict[str, int] = {}
        service_counts: Dict[str, int] = {}
        component_counts: Dict[str, int] = {}

        for entry in self.log_entries:
            level_counts[entry.level] = level_counts.get(entry.level, 0) + 1
            service_counts[entry.service] = service_counts.get(entry.service, 0) + 1
            component_counts[entry.component] = component_counts.get(entry.component, 0) + 1

        return {
            "total_entries": len(self.log_entries),
            "level_counts": level_counts,
            "service_counts": service_counts,
            "component_counts": component_counts,
        }

    async def start(self) -> None:
        self.is_processing = True

    async def stop(self) -> None:
        self.is_processing = False


class LoggingService:
    def __init__(self, log_dir: Optional[str | Path] = None) -> None:
        directory = log_dir or (Path.cwd() / "logs")
        self.aggregator = LogAggregator(directory)
        self.loggers: Dict[str, StructuredLogger] = {}
        self.is_running = False

    def get_logger(self, service_name: str, component: str) -> StructuredLogger:
        key = f"{service_name}:{component}"
        if key not in self.loggers:
            self.loggers[key] = StructuredLogger(service_name, component)
        return self.loggers[key]

    def get_recent_logs(self, **kwargs) -> List[Dict[str, object]]:
        return self.aggregator.get_recent_logs(**kwargs)

    def get_log_statistics(self) -> Dict[str, Dict[str, int] | int]:
        return self.aggregator.get_log_statistics()

    def compress_old_logs(self) -> int:
        """Compress logs (no-op for in-memory implementation)."""
        return 0

    def cleanup_old_compressed_logs(self, days_to_keep: int) -> int:
        """Cleanup compressed logs older than specified days (no-op)."""
        return 0

    async def start(self) -> None:
        await self.aggregator.start()
        self.is_running = True

    async def stop(self) -> None:
        await self.aggregator.stop()
        self.is_running = False


# Module-level singleton used by other services/tests
logging_service = LoggingService()

