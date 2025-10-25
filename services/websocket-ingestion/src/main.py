"""
WebSocket Ingestion Service Main Entry Point
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Optional, Dict, Any
from aiohttp import web
import aiohttp
from dotenv import load_dotenv

# Add shared directory to path for imports
sys.path.append('/app/shared')

from shared.logging_config import (
    setup_logging, get_logger, log_with_context, log_performance, 
    log_error_with_context, performance_monitor, generate_correlation_id,
    set_correlation_id, get_correlation_id
)
from shared.correlation_middleware import create_correlation_middleware
from shared.ha_connection_manager import ha_connection_manager

from health_check import HealthCheckHandler
from connection_manager import ConnectionManager
from async_event_processor import AsyncEventProcessor
from event_queue import EventQueue
from batch_processor import BatchProcessor
from memory_manager import MemoryManager
# DEPRECATED (Epic 31, Story 31.4): Weather enrichment removed
# Weather data now available via weather-api service (Port 8009)
# from weather_enrichment import WeatherEnrichmentService
from http_client import SimpleHTTPClient
from influxdb_wrapper import InfluxDBConnectionManager
from historical_event_counter import HistoricalEventCounter

# Load environment variables
load_dotenv()

# Configure enhanced logging
logger = setup_logging('websocket-ingestion')


class WebSocketIngestionService:
    """Main service class for WebSocket ingestion"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.connection_manager: Optional[ConnectionManager] = None
        self.health_handler = HealthCheckHandler()
        # Pass self reference to health handler for weather statistics
        self.health_handler.websocket_service = self
        
        # High-volume processing components
        self.async_event_processor: Optional[AsyncEventProcessor] = None
        self.event_queue: Optional[EventQueue] = None
        self.batch_processor: Optional[BatchProcessor] = None
        self.memory_manager: Optional[MemoryManager] = None
        
        # DEPRECATED (Epic 31, Story 31.4): Weather enrichment removed
        # Use weather-api service on Port 8009 for weather data
        self.weather_enrichment: Optional = None  # Set to None to prevent AttributeError
        
        # HTTP client for enrichment service
        self.http_client: Optional[SimpleHTTPClient] = None
        
        # InfluxDB connection for device/entity registry storage
        self.influxdb_manager: Optional[InfluxDBConnectionManager] = None
        
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
        
        # Weather enrichment configuration
        self.weather_api_key = os.getenv('WEATHER_API_KEY')
        self.weather_default_location = os.getenv('WEATHER_DEFAULT_LOCATION', 'London,UK')
        # DEPRECATED (Epic 31): Weather enrichment disabled
        self.weather_enrichment_enabled = False  # Force disabled - use weather-api service
        
        # DEPRECATED (Epic 31): Enrichment service removed
        # Events now go directly to InfluxDB, external services consume from there
        self.enrichment_service_url = None
        
        # InfluxDB configuration for device/entity registry storage
        self.influxdb_url = os.getenv('INFLUXDB_URL', 'http://influxdb:8086')
        self.influxdb_token = os.getenv('INFLUXDB_TOKEN')
        self.influxdb_org = os.getenv('INFLUXDB_ORG', 'homeassistant')
        self.influxdb_bucket = os.getenv('INFLUXDB_BUCKET', 'home_assistant_events')
        
        # Historical event counter for persistent totals
        self.historical_counter = None
        
        if self.home_assistant_enabled and (not self.home_assistant_url or not self.home_assistant_token):
            raise ValueError("HA_HTTP_URL/HA_WS_URL and HA_TOKEN must be set when ENABLE_HOME_ASSISTANT=true")
    
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
            
            # Initialize weather enrichment service
            if self.weather_api_key and self.weather_enrichment_enabled:
                self.weather_enrichment = WeatherEnrichmentService(
                    api_key=self.weather_api_key,
                    default_location=self.weather_default_location
                )
                await self.weather_enrichment.start()
                log_with_context(
                    logger, "INFO", "Weather enrichment service initialized",
                    operation="weather_service_startup",
                    correlation_id=corr_id,
                    location=self.weather_default_location
                )
            else:
                log_with_context(
                    logger, "INFO", "Weather enrichment service disabled",
                    operation="weather_service_startup",
                    correlation_id=corr_id,
                    reason="no_api_key_or_disabled"
                )
            
            # HTTP client is initialized in main() function
            log_with_context(
                logger, "INFO", "HTTP client will be initialized in main()",
                operation="http_client_startup",
                correlation_id=corr_id,
                enrichment_url=self.enrichment_service_url
            )
            
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
            from influxdb_batch_writer import InfluxDBBatchWriter
            self.influxdb_batch_writer = InfluxDBBatchWriter(
                connection_manager=self.influxdb_manager,
                batch_size=1000,
                batch_timeout=5.0
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
                # Use the new HA connection manager with automatic fallback
                connection_config = await ha_connection_manager.get_connection()
                
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
        
        # Stop weather enrichment service
        # DEPRECATED (Epic 31, Story 31.4): Weather enrichment removed
        # if self.weather_enrichment:
        #     await self.weather_enrichment.stop()
        
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
        if self.connection_manager and self.connection_manager.client:
            log_with_context(
                logger, "INFO", "Starting device and entity discovery...",
                operation="discovery_trigger",
                correlation_id=corr_id
            )
            try:
                if self.connection_manager.client.websocket:
                    await self.connection_manager.discovery_service.discover_all(
                        self.connection_manager.client.websocket
                    )
                else:
                    logger.error("Cannot run discovery: WebSocket not available")
            except Exception as e:
                logger.error(f"Discovery failed (non-fatal): {e}")
    
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
            # DEPRECATED (Epic 31): Weather enrichment removed
            # Weather data now available via weather-api service (Port 8009)
            # Enrichment happens downstream if needed
            # Original code removed to prevent AttributeError
            
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
    
    async def _write_event_to_influxdb(self, event_data: Dict[str, Any]):
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
            
            # DEPRECATED (Epic 31): Enrichment service removed
            # Events are now stored directly in InfluxDB
            # External services (weather-api, etc.) consume from InfluxDB
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
    
    async def get_event_rate(self, request):
        """Get standardized event rate metrics"""
        try:
            # Get processing statistics from async event processor
            processing_stats = {}
            if self.async_event_processor:
                processing_stats = self.async_event_processor.get_processing_statistics()
            
            # Get connection statistics
            connection_stats = {}
            if self.connection_manager and hasattr(self.connection_manager, 'event_subscription'):
                event_subscription = self.connection_manager.event_subscription
                if event_subscription:
                    sub_status = event_subscription.get_subscription_status()
                    connection_stats = {
                        "is_connected": getattr(self.connection_manager, 'is_running', False),
                        "is_subscribed": sub_status.get("is_subscribed", False),
                        "total_events_received": sub_status.get("total_events_received", 0),
                        "events_by_type": sub_status.get("events_by_type", {}),
                        "last_event_time": sub_status.get("last_event_time")
                    }
            
            # Calculate event rate per second
            events_per_second = processing_stats.get("processing_rate_per_second", 0)
            
            # Calculate events per hour
            events_per_hour = events_per_second * 3600
            
            # Get uptime
            uptime_seconds = (datetime.now() - self.start_time).total_seconds()
            
            # Build response
            response_data = {
                "service": "websocket-ingestion",
                "events_per_second": round(events_per_second, 2),
                "events_per_hour": round(events_per_hour, 2),
                "total_events_processed": processing_stats.get("processed_events", 0),
                "uptime_seconds": round(uptime_seconds, 2),
                "processing_stats": processing_stats,
                "connection_stats": connection_stats,
                "timestamp": datetime.now().isoformat()
            }
            
            return web.json_response(response_data, status=200)
            
        except Exception as e:
            logger.error(f"Error getting event rate: {e}")
            return web.json_response(
                {
                    "service": "websocket-ingestion",
                    "error": str(e),
                    "events_per_second": 0,
                    "events_per_hour": 0,
                    "timestamp": datetime.now().isoformat()
                },
                status=500
            )


async def websocket_handler(request):
    """WebSocket handler for real-time data streaming"""
    # Generate correlation ID for this WebSocket connection
    corr_id = generate_correlation_id()
    set_correlation_id(corr_id)
    
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    
    log_with_context(
        logger, "INFO", "WebSocket client connected",
        operation="websocket_connection",
        correlation_id=corr_id,
        client_ip=request.remote,
        user_agent=request.headers.get('User-Agent', 'unknown')
    )
    
    try:
        # Send initial connection message
        await ws.send_json({
            "type": "connection",
            "status": "connected",
            "message": "Connected to HA Ingestor WebSocket",
            "correlation_id": corr_id
        })
        
        # Keep connection alive and handle messages
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    log_with_context(
                        logger, "DEBUG", "Received WebSocket message",
                        operation="websocket_message",
                        correlation_id=corr_id,
                        message_type=data.get("type", "unknown"),
                        message_size=len(msg.data)
                    )
                    
                    # Handle different message types
                    if data.get("type") == "ping":
                        await ws.send_json({
                            "type": "pong", 
                            "timestamp": datetime.now().isoformat(),
                            "correlation_id": corr_id
                        })
                    elif data.get("type") == "subscribe":
                        # Handle subscription requests
                        channels = data.get("channels", [])
                        await ws.send_json({
                            "type": "subscription",
                            "status": "subscribed",
                            "channels": channels,
                            "correlation_id": corr_id
                        })
                        log_with_context(
                            logger, "INFO", "WebSocket client subscribed to channels",
                            operation="websocket_subscription",
                            correlation_id=corr_id,
                            channels=channels
                        )
                    else:
                        # Echo back unknown messages
                        await ws.send_json({
                            "type": "echo",
                            "original": data,
                            "correlation_id": corr_id
                        })
                        
                except json.JSONDecodeError as e:
                    log_error_with_context(
                        logger, "Invalid JSON in WebSocket message", e,
                        operation="websocket_message_parse",
                        correlation_id=corr_id,
                        message_data=msg.data[:100]  # First 100 chars for debugging
                    )
                    await ws.send_json({
                        "type": "error",
                        "message": "Invalid JSON format",
                        "correlation_id": corr_id
                    })
            elif msg.type == aiohttp.WSMsgType.ERROR:
                log_error_with_context(
                    logger, "WebSocket error occurred", ws.exception(),
                    operation="websocket_error",
                    correlation_id=corr_id
                )
                break
                
    except Exception as e:
        log_error_with_context(
            logger, "WebSocket handler error", e,
            operation="websocket_handler",
            correlation_id=corr_id
        )
    finally:
        log_with_context(
            logger, "INFO", "WebSocket client disconnected",
            operation="websocket_disconnection",
            correlation_id=corr_id
        )
    
    return ws


async def create_app():
    """Create the web application"""
    # Create web application with proper middleware factory
    correlation_middleware = create_correlation_middleware()
    app = web.Application(middlewares=[correlation_middleware])
    
    # Create service instance
    service = WebSocketIngestionService()
    
    # Add health check endpoint
    app.router.add_get('/health', service.health_handler.handle)
    
    # Add standardized event rate endpoint
    app.router.add_get('/api/v1/event-rate', service.get_event_rate)
    
    # Add WebSocket endpoint
    app.router.add_get('/ws', websocket_handler)
    
    # Store service instance in app
    app['service'] = service
    
    return app


async def main():
    """Main entry point"""
    logger.info("Starting WebSocket Ingestion Service...")
    
    # DEPRECATED (Epic 31): Enrichment service removed
    # Events go directly to InfluxDB, no HTTP client needed
    http_client = None
    
    # Create web application
    app = await create_app()
    service = app['service']
    
    # DEPRECATED (Epic 31): No HTTP client needed
    service.http_client = None
    
    # Start web server
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.getenv('WEBSOCKET_INGESTION_PORT', '8000'))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    logger.info(f"WebSocket Ingestion Service started on port {port}")
    
    # Start the service
    await service.start()
    
    # Keep the service running
    try:
        await asyncio.Future()  # Run forever
    except KeyboardInterrupt:
        logger.info("Shutting down WebSocket Ingestion Service...")
    finally:
        await service.stop()
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
