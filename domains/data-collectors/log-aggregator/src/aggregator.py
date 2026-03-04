"""Log Aggregator core logic.

Collects logs from Docker containers via the Docker API, stores them in memory,
and provides methods for querying and searching logs.
"""

import asyncio
import json
from datetime import UTC, datetime
from typing import Any

import docker
from config import settings
from homeiq_observability.logging_config import setup_logging

logger = setup_logging("log-aggregator")


class LogAggregator:
    """Centralized log aggregation service that collects logs from Docker containers."""

    # Safety limits to prevent memory exhaustion from oversized log entries
    _MAX_LINE_LENGTH = 64 * 1024  # Truncate individual log lines beyond 64KB
    _MAX_MESSAGE_LENGTH = 8192  # Truncate parsed message field beyond 8KB

    def __init__(self) -> None:
        """Initialize the log aggregator with Docker client and in-memory log storage."""
        self.log_directory = settings.log_directory_path
        self.log_directory.mkdir(exist_ok=True)
        self.aggregated_logs: list[dict[str, Any]] = []
        self.max_logs = settings.max_logs_memory
        self.collection_interval = settings.collection_interval
        self._last_seen: dict[str, datetime] = {}
        self._last_manual_collect: float = 0.0
        self._api_key: str | None = settings.log_aggregator_api_key

        # Initialize Docker client
        try:
            self.docker_client = docker.from_env()
            self.docker_client.ping()
            logger.info("Docker client initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize Docker client: %s", e)
            logger.debug("Check that /var/run/docker.sock is mounted and accessible")
            self.docker_client = None

    def _parse_log_line(self, line: str, container_name: str, container_id: str) -> dict | None:
        """Parse a single log line into a log entry."""
        stripped = line.strip()
        if not stripped:
            return None

        if len(stripped) > self._MAX_LINE_LENGTH:
            stripped = stripped[: self._MAX_LINE_LENGTH]

        try:
            parsed = json.loads(stripped)
            message = str(parsed.get('message', ''))[: self._MAX_MESSAGE_LENGTH]
            return {
                'timestamp': parsed.get('timestamp', ''),
                'message': message,
                'level': str(parsed.get('level', 'INFO')),
                'service': container_name,
                'container_name': container_name,
                'container_id': container_id,
            }
        except json.JSONDecodeError:
            parts = stripped.split(' ', 1)
            if len(parts) == 2:
                return {
                    'timestamp': parts[0],
                    'message': parts[1][: self._MAX_MESSAGE_LENGTH],
                    'service': container_name,
                    'container_name': container_name,
                    'container_id': container_id,
                    'level': 'INFO',
                }
        return None

    def _process_container_logs(self, container: Any) -> list[dict]:
        """Process logs from a single container."""
        logs: list[dict] = []
        try:
            last_seen = self._last_seen.get(container.short_id)
            if last_seen:
                container_logs = container.logs(
                    since=last_seen,
                    timestamps=True,
                    stream=False,
                ).decode('utf-8', errors='ignore')
            else:
                container_logs = container.logs(
                    tail=100,
                    timestamps=True,
                    stream=False,
                ).decode('utf-8', errors='ignore')

            self._last_seen[container.short_id] = datetime.now(UTC)

            for line in container_logs.split('\n'):
                log_entry = self._parse_log_line(line, container.name, container.short_id)
                if log_entry:
                    logs.append(log_entry)

        except Exception as e:
            logger.warning("Error reading logs from container %s: %s", container.name, e)
        return logs

    async def collect_logs(self) -> list[dict]:
        """Collect logs from all running Docker containers via the Docker API."""
        if not self.docker_client:
            logger.warning("Docker client not available, skipping log collection")
            return []

        try:
            loop = asyncio.get_event_loop()
            containers = await loop.run_in_executor(
                None, lambda: self.docker_client.containers.list(all=False),
            )
            logs: list[dict] = []

            for container in containers:
                container_logs = await loop.run_in_executor(
                    None, self._process_container_logs, container,
                )
                logs.extend(container_logs)

            self.aggregated_logs.extend(logs)

            if len(self.aggregated_logs) > self.max_logs:
                self.aggregated_logs = self.aggregated_logs[-self.max_logs :]

            logger.info("Collected %d log entries from %d containers", len(logs), len(containers))
            return logs

        except Exception as e:
            logger.error("Error collecting logs: %s", e)
            return []

    async def get_recent_logs(
        self,
        service: str | None = None,
        level: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """Get recent logs filtered by service name and/or log level."""
        level_upper = level.upper() if level else None

        filtered = []
        for log in self.aggregated_logs:
            if service and log.get('service') != service:
                continue
            if level_upper and log.get('level') != level_upper:
                continue
            filtered.append(log)

        filtered.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return filtered[:limit]

    async def search_logs(self, query: str, limit: int = 100) -> list[dict]:
        """Search logs by case-insensitive substring match on message content."""
        query_lower = query.lower()
        logs = []

        for log in self.aggregated_logs:
            if query_lower in log.get('message', '').lower():
                logs.append(log)

        logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return logs[:limit]
