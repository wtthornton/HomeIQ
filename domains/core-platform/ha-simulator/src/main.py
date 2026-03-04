#!/usr/bin/env python3
"""
Home Assistant Simulator Main Entry Point

Starts the HA Simulator WebSocket server for development and testing.
Uses BaseServiceSettings from homeiq-data for configuration management.
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent))

from config import settings
from data_patterns import HADataPatternAnalyzer
from event_generator import EventGenerator
from websocket_server import HASimulatorWebSocketServer

# Configure logging from settings
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _build_legacy_config() -> dict:
    """Build the legacy config dict expected by subsystems.

    The WebSocket server, authentication manager, and event generator
    currently consume a nested dict.  This bridges the new Settings
    object to the existing internal API without rewriting every module.
    """
    return {
        "simulator": {
            "name": settings.simulator_name,
            "version": settings.ha_version,
            "port": settings.service_port,
        },
        "authentication": {
            "enabled": settings.auth_enabled,
            "token": settings.auth_token,
        },
        "logging": {
            "level": settings.log_level,
        },
    }


class HASimulatorService:
    """Main HA Simulator service."""

    def __init__(self) -> None:
        self.config = _build_legacy_config()
        self.websocket_server: HASimulatorWebSocketServer | None = None
        self.event_generator: EventGenerator | None = None
        self.running = False

    async def _analyze_data_patterns(self, log_file: str) -> dict:
        """Analyze Home Assistant data patterns from log file."""
        pattern_analyzer = HADataPatternAnalyzer(log_file)
        patterns = pattern_analyzer.analyze_log_file()
        logger.info("Analyzed %d entity patterns", len(patterns["entities"]))
        return patterns

    async def _start_websocket_server(self) -> None:
        """Start the WebSocket server."""
        self.websocket_server = HASimulatorWebSocketServer(self.config)
        await self.websocket_server.start_server()

    async def _start_event_generator(self, patterns: dict) -> None:
        """Start the event generator."""
        self.event_generator = EventGenerator(self.config, patterns)
        if self.websocket_server:
            await self.event_generator.start_generation(self.websocket_server.clients)

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    async def start(self) -> None:
        """Start the HA Simulator service."""
        try:
            logger.info(
                "Starting %s on port %d",
                settings.service_name,
                settings.service_port,
            )

            # Analyze data patterns
            patterns = await self._analyze_data_patterns(settings.log_file_path)

            # Start WebSocket server
            await self._start_websocket_server()

            # Start event generator
            await self._start_event_generator(patterns)

            self.running = True
            logger.info("%s started successfully", settings.service_name)

            # Setup signal handlers
            self._setup_signal_handlers()

            # Keep service running
            while self.running:
                await asyncio.sleep(1)

        except Exception:
            logger.exception("Failed to start %s", settings.service_name)
            raise

    async def stop(self) -> None:
        """Stop the HA Simulator service."""
        logger.info("Stopping %s", settings.service_name)
        self.running = False

        if self.event_generator:
            await self.event_generator.stop_generation()

        if self.websocket_server:
            await self.websocket_server.stop_server()

        logger.info("%s stopped", settings.service_name)

    def _signal_handler(self, signum: int, _frame: object) -> None:
        """Handle shutdown signals."""
        logger.info("Received signal %d", signum)
        asyncio.create_task(self.stop())


async def main() -> None:
    """Main function."""
    service = HASimulatorService()

    try:
        await service.start()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception:
        logger.exception("Unexpected error")
        sys.exit(1)
    finally:
        await service.stop()


if __name__ == "__main__":
    asyncio.run(main())
