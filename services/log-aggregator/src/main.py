"""Log Aggregation Service for Centralized Log Collection"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import aiohttp_cors
import docker
from aiohttp import web

# Add shared directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))

from shared.logging_config import setup_logging

# Configure logging
logger = setup_logging("log-aggregator")

class LogAggregator:
    """Simple log aggregation service for collecting logs from all services"""

    def __init__(self):
        # Use app directory for local log storage
        self.log_directory = Path("/app/logs")
        self.log_directory.mkdir(exist_ok=True)
        self.aggregated_logs = []
        self.max_logs = 10000  # Keep last 10k log entries in memory

        # Initialize Docker client (Context7 recommended pattern for 2025)
        try:
            self.docker_client = docker.from_env()
            self.docker_client.ping()
            logger.info("✅ Docker client initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Docker client: {e}")
            logger.debug("Check that /var/run/docker.sock is mounted and accessible")
            self.docker_client = None

    async def collect_logs(self) -> list[dict]:
        """Collect logs from Docker containers using Docker API"""
        logs = []

        if not self.docker_client:
            logger.warning("Docker client not available, skipping log collection")
            return []

        try:
            # Get all containers
            containers = self.docker_client.containers.list(all=False)

            for container in containers:
                try:
                    # Get container logs (last 100 lines)
                    container_logs = container.logs(
                        tail=100,
                        timestamps=True,
                        stream=False
                    ).decode('utf-8', errors='ignore')

                    # Parse log lines
                    for line in container_logs.split('\n'):
                        if not line.strip():
                            continue

                        try:
                            # Try to parse as JSON log
                            log_entry = json.loads(line.strip())
                            log_entry['container_name'] = container.name
                            log_entry['container_id'] = container.short_id
                            logs.append(log_entry)
                        except json.JSONDecodeError:
                            # Handle non-JSON logs
                            # Docker logs format: "timestamp log_message"
                            parts = line.strip().split(' ', 1)
                            if len(parts) == 2:
                                log_entry = {
                                    'timestamp': parts[0],
                                    'message': parts[1],
                                    'container_name': container.name,
                                    'container_id': container.short_id,
                                    'level': 'INFO'
                                }
                                logs.append(log_entry)

                except Exception as e:
                    logger.debug(f"Error reading logs from container {container.name}: {e}")
                    continue

            # Store in aggregated logs
            self.aggregated_logs.extend(logs)

            # Keep only recent logs
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
        """Get recent logs with optional filtering"""
        logs = self.aggregated_logs.copy()

        # Filter by service
        if service:
            logs = [log for log in logs if log.get('service') == service]

        # Filter by level
        if level:
            logs = [log for log in logs if log.get('level') == level.upper()]

        # Sort by timestamp (most recent first)
        logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        # Return limited results
        return logs[:limit]

    async def search_logs(self, query: str, limit: int = 100) -> list[dict]:
        """Search logs by message content"""
        logs = []

        for log in self.aggregated_logs:
            if query.lower() in log.get('message', '').lower():
                logs.append(log)

        # Sort by timestamp (most recent first)
        logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        return logs[:limit]

# Global log aggregator instance
log_aggregator = LogAggregator()

async def health_check(request: web.Request) -> web.Response:
    """Health check endpoint"""
    return web.json_response({
        "status": "healthy",
        "service": "log-aggregator",
        "timestamp": datetime.utcnow().isoformat(),
        "logs_collected": len(log_aggregator.aggregated_logs)
    })

async def get_logs(request: web.Request) -> web.Response:
    """Get recent logs with optional filtering"""
    service = request.query.get('service')
    level = request.query.get('level')
    limit = int(request.query.get('limit', 100))

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
    """Search logs by query"""
    query = request.query.get('q', '')
    limit = int(request.query.get('limit', 100))

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

async def collect_logs(request: web.Request) -> web.Response:
    """Manually trigger log collection"""
    logs = await log_aggregator.collect_logs()

    return web.json_response({
        "message": f"Collected {len(logs)} log entries",
        "logs_collected": len(logs),
        "total_logs": len(log_aggregator.aggregated_logs)
    })

async def get_log_stats(request: web.Request) -> web.Response:
    """Get log statistics"""
    stats = {
        "total_logs": len(log_aggregator.aggregated_logs),
        "services": {},
        "levels": {},
        "recent_logs": len([log for log in log_aggregator.aggregated_logs
                           if (datetime.utcnow() - datetime.fromisoformat(log.get('timestamp', '1970-01-01T00:00:00Z').replace('Z', '+00:00'))).total_seconds() < 3600])
    }

    # Count by service and level
    for log in log_aggregator.aggregated_logs:
        service = log.get('service', 'unknown')
        level = log.get('level', 'unknown')

        stats['services'][service] = stats['services'].get(service, 0) + 1
        stats['levels'][level] = stats['levels'].get(level, 0) + 1

    return web.json_response(stats)

async def background_log_collection():
    """Background task to collect logs periodically"""
    while True:
        try:
            await log_aggregator.collect_logs()
            await asyncio.sleep(30)  # Collect logs every 30 seconds
        except Exception as e:
            logger.error(f"Error in background log collection: {e}")
            await asyncio.sleep(60)  # Wait longer on error

async def main():
    """Main application entry point"""
    logger.info("Starting log aggregation service...")

    # Create web application
    app = web.Application()

    # Configure CORS for browser requests
    cors = aiohttp_cors.setup(app, defaults={
        "http://localhost:3000": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods=["GET", "POST", "OPTIONS", "PUT", "DELETE"]
        ),
        "http://localhost:3001": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods=["GET", "POST", "OPTIONS", "PUT", "DELETE"]
        ),
    })

    # Add routes
    app.router.add_get('/health', health_check)
    app.router.add_get('/api/v1/logs', get_logs)
    app.router.add_get('/api/v1/logs/search', search_logs)
    app.router.add_post('/api/v1/logs/collect', collect_logs)
    app.router.add_get('/api/v1/logs/stats', get_log_stats)

    # Configure CORS for all routes
    for route in list(app.router.routes()):
        cors.add(route)

    # Start background log collection
    asyncio.create_task(background_log_collection())

    # Start web server
    port = int(os.getenv('PORT', '8015'))
    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

    logger.info(f"Log aggregation service started on port {port}")

    # Keep service running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
