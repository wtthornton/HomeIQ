"""
WebSocket Ingestion Service Main Entry Point
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import aiohttp
from dotenv import load_dotenv

# Add shared directory to path for imports
shared_path_override = os.getenv('HOMEIQ_SHARED_PATH')

# Resolve a robust default shared path. In containers, code lives under /app/src and shared under /app/shared.
# Use parents[1] (the /app directory) rather than a deep index that can fail based on layout.
try:
    app_root = Path(__file__).resolve().parents[1]  # typically /app
except Exception:
    app_root = Path("/app")

candidate_paths = []
if shared_path_override:
    candidate_paths.append(Path(shared_path_override).expanduser())
candidate_paths.extend([
    app_root / "shared",
    Path("/app/shared"),
    Path.cwd() / "shared",
])

shared_path: Path | None = None
for p in candidate_paths:
    if p.exists():
        shared_path = p.resolve()
        break

if shared_path and str(shared_path) not in sys.path:
    sys.path.append(str(shared_path))
elif not shared_path:
    logging.warning("[websocket-ingestion] Warning: could not locate 'shared' directory in expected locations")

from shared.correlation_middleware import create_correlation_middleware
from shared.enhanced_ha_connection_manager import ha_connection_manager
from shared.logging_config import (
    generate_correlation_id,
    get_correlation_id,
    log_error_with_context,
    log_with_context,
    performance_monitor,
    set_correlation_id,
    setup_logging,
)

from .async_event_processor import AsyncEventProcessor
from .batch_processor import BatchProcessor
from .connection_manager import ConnectionManager
from .entity_filter import EntityFilter  # Epic 45.2
from .event_queue import EventQueue
from .health_check import HealthCheckHandler
from .historical_event_counter import HistoricalEventCounter
from .http_client import SimpleHTTPClient
from .influxdb_wrapper import InfluxDBConnectionManager
from .memory_manager import MemoryManager

# Load environment variables
load_dotenv()

# Configure enhanced logging
logger = setup_logging('websocket-ingestion')


class WebSocketIngestionService:
    """Main service class for WebSocket ingestion"""

    def __init__(self):
        self.start_time = datetime.now()
        self.connection_manager: ConnectionManager | None = None
        self.health_handler = HealthCheckHandler()
        # Pass self reference to health handler for weather statistics
        self.health_handler.websocket_service = self

        # High-volume processing components
        self.async_event_processor: AsyncEventProcessor | None = None
        self.event_queue: EventQueue | None = None
        self.batch_processor: BatchProcessor | None = None
        self.memory_manager: MemoryManager | None = None

        # HTTP client for enrichment service
        self.http_client: SimpleHTTPClient | None = None

        # InfluxDB connection for device/entity registry storage
        self.influxdb_manager: InfluxDBConnectionManager | None = None

        # Get configuration from environment
        # Support both new (HA_HTTP_URL/HA_WS_URL/HA_TOKEN) and old (HOME_ASSISTANT_URL/HOME_ASSISTANT_TOKEN) variable names
        self.home_assistant_url = os.getenv('HA_HTTP_URL') or os.getenv('HOME_ASSISTANT_URL')
        # Prioritize HA_WS_URL, then fall back to HA_URL (for backward compatibility with .env.websocket)
        self.home_assistant_ws_url = os.getenv('HA_WS_URL') or os.getenv('HA_URL')
        self.home_assistant_token = os.getenv('HA_TOKEN') or os.getenv('HOME_ASSISTANT_TOKEN')

        # Nabu Casa fallback configuration
        self.nabu_casa_url = os.getenv('NABU_CASA_URL')
        self.nabu_casa_token = os.getenv('NABU_CASA_TOKEN')

        self.home_assistant_enabled = os.getenv('ENABLE_HOME_ASSISTANT', 'true').lower() == 'true'

        # High-volume processing configuration
        self.max_workers = int(os.getenv('MAX_WORKERS', '10'))
        self.processing_rate_limit = int(os.getenv('PROCESSING_RATE_LIMIT', '1000'))
        self.batch_size = int(os.getenv('BATCH_SIZE', '100'))
        self.batch_timeout = float(os.getenv('BATCH_TIMEOUT', '5.0'))
        self.max_memory_mb = int(os.getenv('MAX_MEMORY_MB', '1024'))

        # InfluxDB configuration for device/entity registry storage
        self.influxdb_url = os.getenv('INFLUXDB_URL', 'http://influxdb:8086')
        self.influxdb_token = os.getenv('INFLUXDB_TOKEN')
        self.influxdb_org = os.getenv('INFLUXDB_ORG', 'homeassistant')
        self.influxdb_bucket = os.getenv('INFLUXDB_BUCKET', 'home_assistant_events')
        self.influxdb_max_pending_points = int(os.getenv('INFLUXDB_MAX_PENDING_POINTS', '20000'))
        self.influxdb_overflow_strategy = os.getenv('INFLUXDB_OVERFLOW_STRATEGY', 'drop_oldest').lower()

        # Historical event counter for persistent totals
        self.historical_counter = None

        # Epic 45.2: Entity filter for event capture
        self.entity_filter: EntityFilter | None = None
        self._init_entity_filter()

        # Note: HA connection validation is now handled by ha_connection_manager
        # The service will check for available connections during startup
        # Note: Weather enrichment is handled by standalone weather-api service (Epic 31)

    def _init_entity_filter(self):
        """Initialize entity filter from environment or config file (Epic 45.2)"""
        try:
            # Load filter config from environment variable (JSON string)
            filter_config_json = os.getenv('ENTITY_FILTER_CONFIG')
            if filter_config_json:
                filter_config = json.loads(filter_config_json)
                self.entity_filter = EntityFilter(filter_config)
                logger.info("Entity filter initialized from ENTITY_FILTER_CONFIG environment variable")
                return
            
            # Try loading from config file
            config_file = os.getenv('ENTITY_FILTER_CONFIG_FILE', 'config/entity_filter.json')
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    filter_config = json.load(f)
                    self.entity_filter = EntityFilter(filter_config)
                    logger.info(f"Entity filter initialized from {config_file}")
                    return
            
            # Default: No filtering (include all entities)
            logger.info("Entity filter not configured - all entities will be included")
            self.entity_filter = None
        except Exception as e:
            logger.warning(f"Failed to initialize entity filter: {e}. Continuing without filtering.")
            self.entity_filter = None

    @performance_monitor("service_startup")
    async def start(self):
        """Start the service"""
        corr_id = generate_correlation_id()
        set_correlation_id(corr_id)

        log_with_context(
            logger, "INFO", "Starting WebSocket Ingestion Service",
            operation="service_startup",
            correlation_id=corr_id,
            service="websocket-ingestion"
        )

        try:
            # Initialize high-volume processing components
            self.memory_manager = MemoryManager(max_memory_mb=self.max_memory_mb)
            self.event_queue = EventQueue(maxsize=10000)
            self.batch_processor = BatchProcessor(
                batch_size=self.batch_size,
                batch_timeout=self.batch_timeout
            )
            self.async_event_processor = AsyncEventProcessor(
                max_workers=self.max_workers,
                processing_rate_limit=self.processing_rate_limit
            )

            # Start high-volume processing components
            await self.memory_manager.start()
            await self.batch_processor.start()
            await self.async_event_processor.start()

            log_with_context(
                logger, "INFO", "High-volume processing components started",
                operation="component_startup",
                correlation_id=corr_id,
                components=["memory_manager", "event_queue", "batch_processor", "async_event_processor"]
            )

            # Register InfluxDB write handler (will be registered after InfluxDB batch writer is initialized)
            # This will be done later in the start() method after InfluxDB components are ready

            # Note: Weather enrichment is now handled by the standalone weather-api service (Epic 31)
            # This service only handles WebSocket ingestion and direct InfluxDB writes

            # Set up batch processor handler
            self.batch_processor.add_batch_handler(self._process_batch)

            # Initialize InfluxDB manager for device/entity registry storage
            self.influxdb_manager = InfluxDBConnectionManager(
                url=self.influxdb_url,
                token=self.influxdb_token,
                org=self.influxdb_org,
                bucket=self.influxdb_bucket
            )
            await self.influxdb_manager.start()
            log_with_context(
                logger, "INFO", "InfluxDB manager started",
                operation="influxdb_connection",
                correlation_id=corr_id
            )

            # Initialize historical event counter for persistent totals
            self.historical_counter = HistoricalEventCounter(self.influxdb_manager)
            historical_totals = await self.historical_counter.initialize_historical_totals()
            log_with_context(
                logger, "INFO", "Historical event totals initialized",
                operation="historical_counter_init",
                correlation_id=corr_id,
                total_events=historical_totals.get('total_events_received', 0)
            )

            # Initialize InfluxDB batch writer for event storage
            from .influxdb_batch_writer import InfluxDBBatchWriter
            self.influxdb_batch_writer = InfluxDBBatchWriter(
                connection_manager=self.influxdb_manager,
                batch_size=1000,
                batch_timeout=5.0,
                max_pending_points=self.influxdb_max_pending_points,
                overflow_strategy=self.influxdb_overflow_strategy
            )
            await self.influxdb_batch_writer.start()
            log_with_context(
                logger, "INFO", "InfluxDB batch writer started",
                operation="influxdb_batch_writer_startup",
                correlation_id=corr_id
            )

            # Register InfluxDB write handler with async event processor
            self.async_event_processor.add_event_handler(self._write_event_to_influxdb)
            log_with_context(
                logger, "INFO", "Registered InfluxDB write handler",
                operation="handler_registration",
                correlation_id=corr_id
            )

            # Initialize connection manager (only if Home Assistant is enabled)
            if self.home_assistant_enabled:
                # Use the enhanced HA connection manager with circuit breaker protection
                connection_config = await ha_connection_manager.get_connection_with_circuit_breaker()

                if not connection_config:
                    raise ValueError("No Home Assistant connections available. Configure HA_HTTP_URL/HA_WS_URL + HA_TOKEN or NABU_CASA_URL + NABU_CASA_TOKEN")

                logger.info(f"Using HA connection: {connection_config.name} ({connection_config.url})", extra={'correlation_id': corr_id})

                self.connection_manager = ConnectionManager(
                    connection_config.url,
                    connection_config.token,
                    influxdb_manager=self.influxdb_manager
                )

                # Set up event handlers - don't override connection manager's callbacks
                # The connection manager handles subscription, we'll add discovery in a separate callback
                self.connection_manager.on_connect = self._on_connect  # FIX: Wire up discovery trigger
                self.connection_manager.on_disconnect = self._on_disconnect
                self.connection_manager.on_message = self._on_message
                self.connection_manager.on_error = self._on_error
                self.connection_manager.on_event = self._on_event

                # Start connection manager
                await self.connection_manager.start()

                # Wait a moment for connection attempt
                await asyncio.sleep(2)

                # Check if connection is actually established
                connected = await self._check_connection_status()

                if not connected:
                    logger.error("Failed to establish Home Assistant connection", extra={'correlation_id': corr_id})
                    raise ConnectionError("Could not connect to Home Assistant")

                log_with_context(
                    logger, "INFO", "Home Assistant connection manager started",
                    operation="ha_connection_startup",
                    correlation_id=corr_id,
                    connection_name=connection_config.name,
                    url=connection_config.url
                )
            else:
                log_with_context(
                    logger, "INFO", "Home Assistant connection disabled - running in standalone mode",
                    operation="ha_connection_startup",
                    correlation_id=corr_id,
                    mode="standalone"
                )

            # Update health handler with connection manager and historical counter
            self.health_handler.set_connection_manager(self.connection_manager)
            self.health_handler.set_historical_counter(self.historical_counter)

            log_with_context(
                logger, "INFO", "WebSocket Ingestion Service started successfully",
                operation="service_startup_complete",
                correlation_id=corr_id,
                status="success"
            )

        except Exception as e:
            log_error_with_context(
                logger, "Failed to start WebSocket Ingestion Service", e,
                operation="service_startup",
                correlation_id=corr_id,
                error_type="startup_failure"
            )
            raise

    async def stop(self):
        """Stop the service"""
        logger.info("Stopping WebSocket Ingestion Service...")

        # Stop high-volume processing components
        if self.async_event_processor:
            await self.async_event_processor.stop()
        if self.batch_processor:
            await self.batch_processor.stop()
        if self.memory_manager:
            await self.memory_manager.stop()

        # Stop InfluxDB batch writer
        if hasattr(self, 'influxdb_batch_writer') and self.influxdb_batch_writer:
            await self.influxdb_batch_writer.stop()
        # Stop InfluxDB manager
        if self.influxdb_manager:
            await self.influxdb_manager.stop()

        # HTTP client cleanup is handled by context manager in main()

        if self.connection_manager:
            await self.connection_manager.stop()

        logger.info("WebSocket Ingestion Service stopped")

    async def _check_connection_status(self) -> bool:
        """Check if WebSocket connection is actually established"""
        if not self.connection_manager or not self.connection_manager.client:
            return False

        # Check if websocket exists and is connected
        if hasattr(self.connection_manager.client, 'websocket') and self.connection_manager.client.websocket:
            return not self.connection_manager.client.websocket.closed

        return False

    async def _on_connect(self):
        """Handle successful connection and trigger discovery"""
        corr_id = get_correlation_id() or generate_correlation_id()
        log_with_context(
            logger, "INFO", "Successfully connected to Home Assistant",
            operation="ha_connection",
            correlation_id=corr_id,
            status="connected",
            url=self.home_assistant_url
        )

        # Call the connection manager's subscription logic
        if self.connection_manager:
            try:
                log_with_context(
                    logger, "INFO", "Calling connection manager subscription method",
                    operation="subscription_trigger",
                    correlation_id=corr_id
                )
                await self.connection_manager._subscribe_to_events()
                log_with_context(
                    logger, "INFO", "Subscription method completed",
                    operation="subscription_complete",
                    correlation_id=corr_id
                )
            except Exception as e:
                log_with_context(
                    logger, "ERROR", f"Failed to subscribe to events: {e}",
                    operation="subscription_error",
                    correlation_id=corr_id,
                    error=str(e)
                )

        # Trigger device and entity discovery
        # Entity discovery uses HTTP API (no WebSocket needed)
        # Device discovery requires WebSocket (HA doesn't have HTTP API for device registry)
        if self.connection_manager:
            log_with_context(
                logger, "INFO", "Starting device and entity discovery...",
                operation="discovery_trigger",
                correlation_id=corr_id
            )
            try:
                # Ensure WebSocket is available for device discovery
                websocket = None
                if (self.connection_manager.client and
                    hasattr(self.connection_manager.client, 'websocket') and
                    self.connection_manager.client.is_connected and
                    self.connection_manager.client.is_authenticated):
                    websocket = self.connection_manager.client.websocket
                    log_with_context(
                        logger, "INFO", "WebSocket available for device discovery",
                        operation="discovery_websocket_check",
                        correlation_id=corr_id
                    )
                else:
                    log_with_context(
                        logger, "WARNING", "WebSocket not ready - device discovery will be skipped (entities will still be discovered)",
                        operation="discovery_websocket_check",
                        correlation_id=corr_id
                    )

                # Discovery: entities use HTTP API, devices use WebSocket if available
                await self.connection_manager.discovery_service.discover_all(websocket=websocket, store=True)
            except Exception as e:
                log_error_with_context(
                    logger, "Discovery failed (non-fatal)", e,
                    operation="discovery_error",
                    correlation_id=corr_id
                )

    async def _on_disconnect(self):
        """Handle disconnection"""
        corr_id = get_correlation_id() or generate_correlation_id()
        log_with_context(
            logger, "WARNING", "Disconnected from Home Assistant",
            operation="ha_disconnection",
            correlation_id=corr_id,
            status="disconnected",
            url=self.home_assistant_url
        )

    async def _on_message(self, message):
        """Handle incoming message"""
        corr_id = get_correlation_id() or generate_correlation_id()
        log_with_context(
            logger, "DEBUG", "Received message from Home Assistant",
            operation="message_received",
            correlation_id=corr_id,
            message_type=type(message).__name__,
            message_size=len(str(message)) if message else 0
        )
        # Message handling is now done in connection_manager

    @performance_monitor("event_processing")
    async def _on_event(self, processed_event):
        """Handle processed event"""
        corr_id = get_correlation_id() or generate_correlation_id()

        event_type = processed_event.get('event_type', 'unknown')
        entity_id = processed_event.get('entity_id', 'N/A')

        log_with_context(
            logger, "DEBUG", "Processing Home Assistant event",
            operation="event_processing",
            correlation_id=corr_id,
            event_type=event_type,
            entity_id=entity_id,
            domain=processed_event.get('domain', 'unknown')
        )

        try:
            # Epic 45.2: Apply entity filter before adding to batch
            if self.entity_filter and not self.entity_filter.should_include(processed_event):
                log_with_context(
                    logger, "DEBUG", "Event filtered by entity filter",
                    operation="entity_filtering",
                    correlation_id=corr_id,
                    event_type=event_type,
                    entity_id=entity_id
                )
                return  # Skip filtered events
            
            # Add to batch processor for high-volume processing
            if self.batch_processor:
                await self.batch_processor.add_event(processed_event)
                log_with_context(
                    logger, "DEBUG", "Event added to batch processor",
                    operation="batch_processing",
                    correlation_id=corr_id,
                    event_type=event_type,
                    entity_id=entity_id
                )

        except Exception as e:
            log_error_with_context(
                logger, "Error processing Home Assistant event", e,
                operation="event_processing",
                correlation_id=corr_id,
                event_type=event_type,
                entity_id=entity_id
            )

    async def _write_event_to_influxdb(self, event_data: dict[str, Any]):
        """Write event to InfluxDB"""
        try:
            if self.influxdb_batch_writer:
                # Write event using the batch writer
                success = await self.influxdb_batch_writer.write_event(event_data)
                if not success:
                    logger.warning(f"Failed to write event to InfluxDB: {event_data.get('event_type')}")
        except Exception as e:
            logger.error(f"Error writing event to InfluxDB: {e}")

    @performance_monitor("batch_processing")
    async def _process_batch(self, batch):
        """Process a batch of events"""
        corr_id = get_correlation_id() or generate_correlation_id()
        batch_size = len(batch)

        log_with_context(
            logger, "DEBUG", "Processing batch of events",
            operation="batch_processing",
            correlation_id=corr_id,
            batch_size=batch_size
        )

        try:
            # Add batch to async event processor
            if self.async_event_processor:
                for event in batch:
                    await self.async_event_processor.process_event(event)

                log_with_context(
                    logger, "DEBUG", "Batch processed by async event processor",
                    operation="async_processing",
                    correlation_id=corr_id,
                    batch_size=batch_size
                )

            log_with_context(
                logger, "DEBUG", "Batch processed - events stored in InfluxDB",
                operation="influxdb_storage",
                correlation_id=corr_id,
                batch_size=batch_size
            )

        except Exception as e:
            log_error_with_context(
                logger, "Error processing batch", e,
                operation="batch_processing",
                correlation_id=corr_id,
                batch_size=batch_size
            )

    async def _on_error(self, error):
        """Handle error"""
        corr_id = get_correlation_id() or generate_correlation_id()
        log_error_with_context(
            logger, "Service error occurred", error,
            operation="service_error",
            correlation_id=corr_id,
            error_type="service_error"
        )

# Import FastAPI app from api module
from .api.app import app


def main():
    """Main entry point - uses uvicorn to run FastAPI app"""
    import uvicorn
    
    port = int(os.getenv('WEBSOCKET_INGESTION_PORT', '8000'))
    host = os.getenv('WEBSOCKET_INGESTION_HOST', '0.0.0.0')
    
    logger.info(f"Starting WebSocket Ingestion Service on {host}:{port}...")
    
    # Run with uvicorn
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )


if __name__ == "__main__":
    main()
