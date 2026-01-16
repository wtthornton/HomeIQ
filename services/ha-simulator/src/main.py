#!/usr/bin/env python3
"""
Home Assistant Simulator Main Entry Point

Starts the HA Simulator WebSocket server for development and testing.
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent))

from config_manager import ConfigManager
from data_patterns import HADataPatternAnalyzer
from event_generator import EventGenerator
from websocket_server import HASimulatorWebSocketServer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class HASimulatorService:
    """Main HA Simulator service"""

    def __init__(self) -> None:
        self.config_manager = ConfigManager()
        self.websocket_server = None
        self.event_generator = None
        self.running = False

    async def _load_configuration(self) -> dict:
        """Load and return service configuration."""
        config = self.config_manager.config
        logger.info(f"📋 Configuration loaded: {config['simulator']['name']}")
        return config

    async def _analyze_data_patterns(self, log_file: str) -> dict:
        """Analyze Home Assistant data patterns from log file."""
        pattern_analyzer = HADataPatternAnalyzer(log_file)
        patterns = pattern_analyzer.analyze_log_file()
        logger.info(f"📊 Analyzed {len(patterns['entities'])} entity patterns")
        return patterns

    async def _start_websocket_server(self, config: dict) -> None:
        """Start the WebSocket server."""
        self.websocket_server = HASimulatorWebSocketServer(config)
        await self.websocket_server.start_server()

    async def _start_event_generator(self, config: dict, patterns: dict) -> None:
        """Start the event generator."""
        self.event_generator = EventGenerator(config, patterns)
        if self.websocket_server:
            await self.event_generator.start_generation(self.websocket_server.clients)

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    async def start(self) -> None:
        """Start the HA Simulator service"""
        try:
            logger.info("🚀 Starting HA Simulator Service")

            # Load configuration
            config = await self._load_configuration()

            # Analyze data patterns
            patterns = await self._analyze_data_patterns("data/ha_events.log")

            # Start WebSocket server
            await self._start_websocket_server(config)

            # Start event generator
            await self._start_event_generator(config, patterns)

            self.running = True
            logger.info("✅ HA Simulator Service started successfully")

            # Setup signal handlers
            self._setup_signal_handlers()

            # Keep service running
            while self.running:
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"❌ Failed to start HA Simulator Service: {e}")
            raise

    async def stop(self) -> None:
        """Stop the HA Simulator service"""
        logger.info("🛑 Stopping HA Simulator Service")
        self.running = False

        if self.event_generator:
            await self.event_generator.stop_generation()

        if self.websocket_server:
            await self.websocket_server.stop_server()

        logger.info("✅ HA Simulator Service stopped")

    def _signal_handler(self, signum: int, frame: object) -> None:
        """Handle shutdown signals"""
        logger.info(f"📡 Received signal {signum}")
        asyncio.create_task(self.stop())

async def main() -> None:
    """Main function"""
    service = HASimulatorService()

    try:
        await service.start()
    except KeyboardInterrupt:
        logger.info("🛑 Interrupted by user")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        sys.exit(1)
    finally:
        await service.stop()

if __name__ == "__main__":
    asyncio.run(main())

