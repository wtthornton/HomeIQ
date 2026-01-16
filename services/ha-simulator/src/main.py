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

    async def start(self) -> None:
        """Start the HA Simulator service"""
        try:
            logger.info("🚀 Starting HA Simulator Service")

            # Load configuration
            config = self.config_manager.config
            logger.info(f"📋 Configuration loaded: {config['simulator']['name']}")

            # Analyze data patterns
            pattern_analyzer = HADataPatternAnalyzer("data/ha_events.log")
            patterns = pattern_analyzer.analyze_log_file()
            logger.info(f"📊 Analyzed {len(patterns['entities'])} entity patterns")

            # Start WebSocket server
            self.websocket_server = HASimulatorWebSocketServer(config)
            await self.websocket_server.start_server()

            # Start event generator
            self.event_generator = EventGenerator(config, patterns)
            await self.event_generator.start_generation(self.websocket_server.clients)

            self.running = True
            logger.info("✅ HA Simulator Service started successfully")

            # Setup signal handlers
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)

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

