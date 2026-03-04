"""Log Aggregation Service for Centralized Log Collection.

Collects logs from Docker containers via the Docker API, stores them in memory,
and exposes REST endpoints for querying and searching logs. Provides background
periodic collection, manual trigger with rate limiting, and log statistics including
per-service and per-level breakdowns.
"""

import asyncio
import contextlib
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path

import aiohttp_cors
import docker
from aiohttp import web
from homeiq_observability.logging_config import setup_logging

# Configure logging
logger = setup_logging("log-aggregator")

class LogAggregator:
    """Centralized log aggregation service that collects logs from Docker containers.

    Uses the Docker API to stream container logs, parse them into structured entries,
    and store them in memory for REST API querying and searching.
    """

    def __init__(self) -> None:
        """Initialize the log aggregator with Docker client and in-memory log storage."""
        # Use app directory for local log storage
        self.log_directory = Path(os.getenv("LOG_DIRECTORY", "/app/logs"))
        self.log_directory.mkdir(exist_ok=True)
        self.aggregated_logs = []
        self.max_logs = int(os.getenv("MAX_LOGS_MEMORY", "10000"))
        self.collection_interval = int(os.getenv("COLLECTION_INTERVAL", "30"))
        self._last_seen: dict[str, datetime] = {}
        self._last_manual_collect: float = 0.0
        self._api_key: str | None = os.getenv("LOG_AGGREGATOR_API_KEY")

        # Initialize Docker client
        try:
            self.docker_client = docker.from_env()
            self.docker_client.ping()
            logger.info("Docker client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            logger.debug("Check that /var/run/docker.sock is mounted and accessible")
            self.docker_client = None

    # Safety limits to prevent memory exhaustion from oversized log entries
    _MAX_LINE_LENGTH = 64 * 1024  # Truncate individual log lines beyond 64KB
    _MAX_MESSAGE_LENGTH = 8192  # Truncate parsed message field beyond 8KB

    def _parse_log_line(self, line: str, container_name: str, container_id: str) -> dict | None:
        """Parse a single log line into a log entry."""
        stripped = line.strip()
        if not stripped:
            return None

        if len(stripped) > self._MAX_LINE_LENGTH:
            stripped = stripped[:self._MAX_LINE_LENGTH]

        try:
            parsed = json.loads(stripped)
            message = str(parsed.get('message', ''))[:self._MAX_MESSAGE_LENGTH]
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
                    'message': parts[1][:self._MAX_MESSAGE_LENGTH],
                    'service': container_name,
                    'container_name': container_name,
                    'container_id': container_id,
                    'level': 'INFO'
                }
        return None

    def _process_container_logs(self, container) -> list[dict]:
        """Process logs from a single container."""
        logs = []
        try:
            last_seen = self._last_seen.get(container.short_id)
            if last_seen:
                container_logs = container.logs(
                    since=last_seen,
                    timestamps=True,
                    stream=False
                ).decode('utf-8', errors='ignore')
            else:
                container_logs = container.logs(
                    tail=100,
                    timestamps=True,
                    stream=False
                ).decode('utf-8', errors='ignore')

            self._last_seen[container.short_id] = datetime.now(UTC)

            for line in container_logs.split('\n'):
                log_entry = self._parse_log_line(line, container.name, container.short_id)
                if log_entry:
                    logs.append(log_entry)

        except Exception as e:
            logger.warning(f"Error reading logs from container {container.name}: {e}")
        return logs

    async def collect_logs(self) -> list[dict]:
        """Collect logs from all running Docker containers via the Docker API.

        Returns:
            List of parsed log entry dictionaries from all containers.
        """
        if not self.docker_client:
            logger.warning("Docker client not available, skipping log collection")
            return []

        try:
            loop = asyncio.get_event_loop()
            containers = await loop.run_in_executor(
                None, lambda: self.docker_client.containers.list(all=False)
            )
            logs = []

            for container in containers:
                container_logs = await loop.run_in_executor(
                    None, self._process_container_logs, container
                )
                logs.extend(container_logs)

            self.aggregated_logs.extend(logs)

            if len(self.aggregated_logs) > self.max_logs:
                self.aggregated_logs = self.aggregated_logs[-self.max_logs:]

            logger.info(f"Collected {len(logs)} log entries from {len(containers)} containers")
            return logs

        except Exception as e:
            logger.error(f"Error collecting logs: {e}")
            return []

    async def get_recent_logs(self, service: str | None = None,
                            level: str | None = None,
                            limit: int = 100) -> list[dict]:
        """Get recent logs filtered by service name and/or log level.

        Args:
            service: Optional service name to filter by.
            level: Optional log level to filter by (e.g. INFO, ERROR).
            limit: Maximum number of log entries to return.

        Returns:
            List of matching log entries, sorted by timestamp descending.
        """
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
        """Search logs by case-insensitive substring match on message content.

        Args:
            query: Search string to match against log messages.
            limit: Maximum number of results to return.

        Returns:
            List of matching log entries, sorted by timestamp descending.
        """
        query_lower = query.lower()
        logs = []

        for log in self.aggregated_logs:
            if query_lower in log.get('message', '').lower():
                logs.append(log)

        logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        return logs[:limit]

# Global log aggregator instance
log_aggregator = LogAggregator()

async def health_check(_request: web.Request) -> web.Response:
    """Health check endpoint returning Docker client connectivity status."""
    is_healthy = log_aggregator.docker_client is not None
    status = "healthy" if is_healthy else "degraded"
    status_code = 200 if is_healthy else 503
    return web.json_response({
        "status": status,
        "service": "log-aggregator",
        "timestamp": datetime.now(UTC).isoformat(),
        "logs_collected": len(log_aggregator.aggregated_logs)
    }, status=status_code)

async def get_logs(request: web.Request) -> web.Response:
    """REST endpoint to get recent logs with optional service/level/limit filters."""
    service = request.query.get('service')
    level = request.query.get('level')
    try:
        limit = int(request.query.get('limit', 100))
        if limit < 1 or limit > 10000:
            return web.json_response({"error": "limit must be between 1 and 10000"}, status=400)
    except (ValueError, TypeError):
        return web.json_response({"error": "limit must be a valid integer"}, status=400)

    logs = await log_aggregator.get_recent_logs(service, level, limit)

    return web.json_response({
        "logs": logs,
        "count": len(logs),
        "filters": {
            "service": service,
            "level": level,
            "limit": limit
        }
    })

async def search_logs(request: web.Request) -> web.Response:
    """REST endpoint to search logs by query string parameter 'q'."""
    query = request.query.get('q', '')
    try:
        limit = int(request.query.get('limit', 100))
        if limit < 1 or limit > 10000:
            return web.json_response({"error": "limit must be between 1 and 10000"}, status=400)
    except (ValueError, TypeError):
        return web.json_response({"error": "limit must be a valid integer"}, status=400)

    if not query:
        return web.json_response({
            "error": "Query parameter 'q' is required"
        }, status=400)

    logs = await log_aggregator.search_logs(query, limit)

    return web.json_response({
        "logs": logs,
        "count": len(logs),
        "query": query,
        "limit": limit
    })

async def collect_logs_endpoint(request: web.Request) -> web.Response:
    """REST endpoint to manually trigger log collection with rate limiting."""
    if log_aggregator._api_key:
        provided_key = request.headers.get('X-API-Key', '')
        if provided_key != log_aggregator._api_key:
            return web.json_response({"error": "Invalid or missing API key"}, status=403)

    now = time.monotonic()
    elapsed = now - log_aggregator._last_manual_collect
    if elapsed < 10.0:
        return web.json_response({
            "error": f"Rate limited. Try again in {10.0 - elapsed:.1f}s"
        }, status=429)

    log_aggregator._last_manual_collect = now
    logs = await log_aggregator.collect_logs()

    return web.json_response({
        "message": f"Collected {len(logs)} log entries",
        "logs_collected": len(logs),
        "total_logs": len(log_aggregator.aggregated_logs)
    })

def _count_recent_logs(logs: list[dict], hours: int = 1) -> int:
    """Count log entries from the last N hours based on their timestamp.

    Args:
        logs: List of log entry dictionaries with 'timestamp' field.
        hours: Time window in hours to count from (default: 1 hour).

    Returns:
        Number of log entries within the time window.
    """
    cutoff = datetime.now(UTC).timestamp() - (hours * 3600)
    count = 0
    for log in logs:
        try:
            timestamp_str = log.get('timestamp', '1970-01-01T00:00:00Z').replace('Z', '+00:00')
            log_time = datetime.fromisoformat(timestamp_str).timestamp()
            if log_time > cutoff:
                count += 1
        except (ValueError, AttributeError):
            continue
    return count


def _count_by_field(logs: list[dict], field: str) -> dict[str, int]:
    """Count log entries grouped by a specific field value.

    Args:
        logs: List of log entry dictionaries.
        field: Field name to group by (e.g., 'service', 'level').

    Returns:
        Dictionary mapping field values to their occurrence counts.
    """
    counts: dict[str, int] = {}
    for log in logs:
        value = str(log.get(field, 'unknown'))
        counts[value] = counts.get(value, 0) + 1
    return counts


async def get_log_stats(_request: web.Request) -> web.Response:
    """REST endpoint returning log statistics: totals, by-service, by-level, and recent counts."""
    logs = log_aggregator.aggregated_logs
    stats = {
        "total_logs": len(logs),
        "services": _count_by_field(logs, 'service'),
        "levels": _count_by_field(logs, 'level'),
        "recent_logs": _count_recent_logs(logs, hours=1)
    }

    return web.json_response(stats)

async def background_log_collection() -> None:
    """Background task that periodically collects logs from Docker containers."""
    interval = log_aggregator.collection_interval
    while True:
        try:
            await log_aggregator.collect_logs()
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            logger.info("Background log collection cancelled")
            return
        except Exception as e:
            logger.error(f"Error in background log collection: {e}")
            await asyncio.sleep(interval * 2)


def _on_background_task_done(task: asyncio.Task) -> None:
    """Callback for background task completion/failure logging."""
    try:
        exc = task.exception()
        if exc:
            logger.error(f"Background log collection task failed: {exc}")
    except asyncio.CancelledError:
        pass


async def main() -> None:
    """Main entry point: starts the web server and background log collection task."""
    logger.info("Starting log aggregation service...")

    app = web.Application(client_max_size=64 * 1024)

    cors_origins_str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001")
    cors_origins = [o.strip() for o in cors_origins_str.split(",") if o.strip()]
    allowed_methods = ["GET", "POST", "OPTIONS"]

    cors_defaults = {}
    for origin in cors_origins:
        cors_defaults[origin] = aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods=allowed_methods
        )

    cors = aiohttp_cors.setup(app, defaults=cors_defaults)

    # Add routes
    app.router.add_get('/health', health_check)
    app.router.add_get('/api/v1/logs', get_logs)
    app.router.add_get('/api/v1/logs/search', search_logs)
    app.router.add_post('/api/v1/logs/collect', collect_logs_endpoint)
    app.router.add_get('/api/v1/logs/stats', get_log_stats)

    # Configure CORS for all routes
    for route in list(app.router.routes()):
        cors.add(route)

    # Start background log collection
    bg_task = asyncio.create_task(background_log_collection())
    bg_task.add_done_callback(_on_background_task_done)

    # Start web server
    port = int(os.getenv('PORT', '8015'))
    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, '0.0.0.0', port)  # noqa: S104
    await site.start()

    logger.info(f"Log aggregation service started on port {port}")

    # Keep service running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        bg_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await bg_task
        await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
