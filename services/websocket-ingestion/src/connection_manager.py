"""
Connection Manager for Home Assistant WebSocket with Retry Logic
"""

import asyncio
import logging
import os
import random
from collections.abc import Callable
from datetime import datetime
from typing import Any

from .discovery_service import DiscoveryService
from .error_handler import ErrorHandler
from .event_processor import EventProcessor
from .event_rate_monitor import EventRateMonitor
from .event_subscription import EventSubscriptionManager
from .state_machine import ConnectionState, ConnectionStateMachine, InvalidStateTransition
from .websocket_client import HomeAssistantWebSocketClient

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connection with automatic retry and reconnection"""

    def __init__(self, base_url: str, token: str, influxdb_manager=None):
        self.base_url = base_url
        self.token = token
        self.client: HomeAssistantWebSocketClient | None = None
        # State machine for connection state management
        self.state_machine = ConnectionStateMachine()
        self.reconnect_task: asyncio.Task | None = None
        self.listen_task: asyncio.Task | None = None
        self.periodic_discovery_task: asyncio.Task | None = None

        # Event management components
        self.event_subscription = EventSubscriptionManager()
        self.event_rate_monitor = EventRateMonitor()
        self.error_handler = ErrorHandler()
        self.discovery_service = DiscoveryService(influxdb_manager=influxdb_manager)
        # Epic 23.2: Pass discovery_service to event_processor for device/area enrichment
        self.event_processor = EventProcessor(discovery_service=self.discovery_service)

        # Periodic discovery refresh interval (default: 30 minutes to match cache TTL)
        self.discovery_refresh_interval = int(os.getenv('DISCOVERY_REFRESH_INTERVAL', '1800'))  # 30 minutes

        # Retry configuration (configurable via environment)
        # -1 = infinite retries (recommended for production)
        self.max_retries = int(os.getenv('WEBSOCKET_MAX_RETRIES', '-1'))
        self.base_delay = 1  # seconds
        self.max_delay = int(os.getenv('WEBSOCKET_MAX_RETRY_DELAY', '300'))  # 5 minutes default
        self.backoff_multiplier = 2
        self.jitter_range = 0.1  # 10% jitter
        self.current_retry_count = 0

        # Connection statistics
        self.connection_attempts = 0
        self.successful_connections = 0
        self.failed_connections = 0
        self.last_connection_time: datetime | None = None
        self.last_error: str | None = None

        # Event handlers
        self.on_connect: Callable | None = None
        self.on_disconnect: Callable | None = None
        self.on_message: Callable | None = None
        self.on_error: Callable | None = None
        self.on_event: Callable | None = None

    async def start(self) -> bool:
        """
        Start the connection manager
        
        Returns:
            True if started successfully, False otherwise
        """
        current_state = self.state_machine.get_state()
        if current_state == ConnectionState.CONNECTED:
            logger.warning("Connection manager is already connected")
            return True
        if current_state in [ConnectionState.CONNECTING, ConnectionState.RECONNECTING]:
            logger.warning(f"Connection manager is already in state {current_state.value}")
            return True

        logger.info("Starting connection manager")
        try:
            # Transition to connecting state
            self.state_machine.transition(ConnectionState.CONNECTING)
        except InvalidStateTransition as e:
            logger.error(f"Cannot start from state {current_state.value}: {e}")
            return False

        # Set up event handlers
        self._setup_event_handlers()

        # Start connection
        success = await self._connect()

        if success:
            # Transition to connected state
            try:
                self.state_machine.transition(ConnectionState.CONNECTED)
            except InvalidStateTransition as e:
                logger.error(f"State transition error after successful connection: {e}")
                # Force transition if we're actually connected
                self.state_machine.transition(ConnectionState.CONNECTED, force=True)

            # Start listening task
            self.listen_task = asyncio.create_task(self._listen_loop())
            logger.info("Connection manager started successfully")
            return True
        else:
            # Transition to failed state
            try:
                self.state_machine.transition(ConnectionState.FAILED)
            except InvalidStateTransition:
                pass  # Already in failed state

            # Start reconnection task
            self.reconnect_task = asyncio.create_task(self._reconnect_loop())
            logger.info("Connection manager started with reconnection task")
            return True

    async def stop(self):
        """Stop the connection manager"""
        current_state = self.state_machine.get_state()
        if current_state == ConnectionState.DISCONNECTED:
            return

        logger.info("Stopping connection manager")

        # Transition to disconnected state
        try:
            self.state_machine.transition(ConnectionState.DISCONNECTED, force=True)
        except InvalidStateTransition:
            # Force reset if needed
            self.state_machine.reset(ConnectionState.DISCONNECTED)

        # Cancel tasks
        if self.reconnect_task:
            self.reconnect_task.cancel()
            try:
                await self.reconnect_task
            except asyncio.CancelledError:
                pass

        if self.listen_task:
            self.listen_task.cancel()
            try:
                await self.listen_task
            except asyncio.CancelledError:
                pass

        # Disconnect client
        if self.client:
            await self.client.disconnect()

        logger.info("Connection manager stopped")

    def _setup_event_handlers(self):
        """Set up event handlers for the WebSocket client"""
        self.client = HomeAssistantWebSocketClient(self.base_url, self.token)

        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.client.on_error = self._on_error

    async def _connect(self) -> bool:
        """Attempt to connect to Home Assistant"""
        if not self.client:
            self._setup_event_handlers()

        current_state = self.state_machine.get_state()
        if current_state == ConnectionState.DISCONNECTED:
            try:
                self.state_machine.transition(ConnectionState.CONNECTING)
            except InvalidStateTransition as e:
                logger.error(f"Cannot transition to CONNECTING: {e}")
                return False

        self.connection_attempts += 1
        logger.info(f"Connection attempt {self.connection_attempts}")

        try:
            # Transition to authenticating state if connecting
            if current_state == ConnectionState.CONNECTING:
                try:
                    self.state_machine.transition(ConnectionState.AUTHENTICATING)
                except InvalidStateTransition:
                    pass  # Already transitioning

            success = await self.client.connect()
            if success:
                self.successful_connections += 1
                self.last_connection_time = datetime.now()
                self.last_error = None
                logger.info("Connection successful")
                # Transition to connected will happen in start() method
            else:
                self.failed_connections += 1
                logger.warning("Connection failed")
                try:
                    self.state_machine.transition(ConnectionState.FAILED)
                except InvalidStateTransition:
                    pass  # May already be in failed state

            return success

        except Exception as e:
            self.failed_connections += 1
            self.last_error = str(e)

            # Log error with categorization
            context = {
                "base_url": self.base_url,
                "connection_attempt": self.connection_attempts + 1,
                "retry_count": self.current_retry_count
            }
            self.error_handler.log_error(e, context)

            return False

    async def _reconnect_loop(self):
        """Loop for automatic reconnection with exponential backoff and jitter"""
        # Transition to reconnecting state
        try:
            self.state_machine.transition(ConnectionState.RECONNECTING)
        except InvalidStateTransition:
            pass  # May already be reconnecting

        current_state = self.state_machine.get_state()
        # Support infinite retries when max_retries = -1
        while current_state in [ConnectionState.RECONNECTING, ConnectionState.FAILED] and (self.max_retries == -1 or self.current_retry_count < self.max_retries):
            try:
                self._increment_retry_count()
                self.connection_attempts += 1
                delay = self._calculate_delay()

                # Format retry message (show "∞" for infinite retries)
                retry_display = "∞" if self.max_retries == -1 else str(self.max_retries)
                logger.info(f"Reconnection attempt {self.current_retry_count}/{retry_display} in {delay:.1f}s")
                await asyncio.sleep(delay)

                # Check if we should continue (update current_state will be done at end of loop)
                current_state_check = self.state_machine.get_state()
                if current_state_check not in [ConnectionState.RECONNECTING, ConnectionState.FAILED]:
                    break

                # Transition to connecting from reconnecting
                try:
                    self.state_machine.transition(ConnectionState.CONNECTING)
                except InvalidStateTransition:
                    pass  # May already be connecting

                success = await self._connect()

                if success:
                    # Transition to connected
                    try:
                        self.state_machine.transition(ConnectionState.CONNECTED)
                    except InvalidStateTransition:
                        self.state_machine.transition(ConnectionState.CONNECTED, force=True)

                    # Reset retry count on successful connection
                    self._reset_retry_count()

                    # Subscribe to events
                    await self._subscribe_to_events()

                    # Start listening task
                    self.listen_task = asyncio.create_task(self._listen_loop())
                    logger.info("Reconnection successful")
                    break
                else:
                    logger.warning(f"Reconnection attempt {self.current_retry_count} failed")
                    try:
                        self.state_machine.transition(ConnectionState.FAILED)
                    except InvalidStateTransition:
                        pass

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.last_error = str(e)

                # Transition to failed on exception
                try:
                    self.state_machine.transition(ConnectionState.FAILED)
                except InvalidStateTransition:
                    pass

                # Log reconnection error with categorization
                context = {
                    "reconnection_attempt": self.current_retry_count,
                    "total_attempts": self.connection_attempts,
                    "base_url": self.base_url
                }
                self.error_handler.log_error(e, context)

            # Update current state for loop condition
            current_state = self.state_machine.get_state()

        # Only stop if we have a retry limit (not infinite)
        if self.max_retries != -1 and self.current_retry_count >= self.max_retries:
            logger.error(f"Maximum reconnection attempts ({self.max_retries}) reached")
            try:
                self.state_machine.transition(ConnectionState.FAILED)
            except InvalidStateTransition:
                pass

    async def _listen_loop(self):
        """Loop for listening to WebSocket messages"""
        current_state = self.state_machine.get_state()
        while current_state == ConnectionState.CONNECTED and self.client and self.client.is_connected:
            try:
                await self.client.listen()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Listen loop error: {e}")
                if self.on_error:
                    await self.on_error(f"Listen error: {e}")

                # If we lose connection, transition to reconnecting
                try:
                    self.state_machine.transition(ConnectionState.RECONNECTING)
                except InvalidStateTransition:
                    try:
                        self.state_machine.transition(ConnectionState.FAILED)
                    except InvalidStateTransition:
                        pass

                # Start reconnection if not already reconnecting
                current_state = self.state_machine.get_state()
                if current_state in [ConnectionState.RECONNECTING, ConnectionState.FAILED]:
                    self.reconnect_task = asyncio.create_task(self._reconnect_loop())
                break

    def _calculate_delay(self) -> float:
        """Calculate delay for next reconnection attempt with exponential backoff and jitter"""
        # Exponential backoff calculation
        delay = self.base_delay * (self.backoff_multiplier ** (self.current_retry_count - 1))
        delay = min(delay, self.max_delay)

        # Add jitter to prevent thundering herd
        jitter = delay * self.jitter_range * (2 * random.random() - 1)  # ±10% jitter
        final_delay = delay + jitter

        # Ensure minimum delay
        return max(final_delay, 0.1)

    def _reset_retry_count(self):
        """Reset retry count after successful connection"""
        self.current_retry_count = 0

    def _increment_retry_count(self):
        """Increment retry count"""
        self.current_retry_count += 1

    async def _subscribe_to_events(self):
        """Subscribe to Home Assistant events"""
        try:
            logger.info("=" * 80)
            logger.info("🔍 CHECKING SUBSCRIPTION PREREQUISITES")
            logger.info("=" * 80)
            logger.info(f"🔌 Client exists: {self.client is not None}")
            logger.info(f"🔗 Client connected: {self.client and self.client.is_connected}")
            logger.info(f"🔐 Client authenticated: {self.client and self.client.is_authenticated}")

            if not self.client:
                logger.error("❌ Cannot subscribe: No WebSocket client available")
                return

            if not self.client.is_connected:
                logger.error("❌ Cannot subscribe: WebSocket client not connected")
                return

            if not self.client.is_authenticated:
                logger.error("❌ Cannot subscribe: WebSocket client not authenticated")
                return

            logger.info("✅ All prerequisites met, waiting 1 second before subscribing...")
            await asyncio.sleep(1)  # Give authentication time to fully complete

            # Subscribe to state_changed events by default
            logger.info("📡 Initiating subscription to state_changed events")
            success = await self.event_subscription.subscribe_to_events(
                self.client,
                ['state_changed']
            )

            if success:
                logger.info("=" * 80)
                logger.info("🎉 EVENT SUBSCRIPTION PROCESS COMPLETED SUCCESSFULLY")
                logger.info("=" * 80)
            else:
                logger.error("=" * 80)
                logger.error("❌ EVENT SUBSCRIPTION PROCESS FAILED")
                logger.error("=" * 80)

        except Exception as e:
            logger.error("=" * 80)
            logger.error(f"❌ ERROR SUBSCRIBING TO EVENTS: {e}")
            logger.error("=" * 80)
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

    async def _periodic_discovery_refresh(self):
        """
        Periodically refresh the discovery cache to keep device/area mappings up-to-date.
        
        Runs every DISCOVERY_REFRESH_INTERVAL seconds (default: 30 minutes).
        Automatically retries if discovery fails.
        """
        logger.info(f"🔄 Periodic discovery refresh task started (interval: {self.discovery_refresh_interval/60:.1f} minutes)")

        while True:
            try:
                # Wait for the refresh interval
                await asyncio.sleep(self.discovery_refresh_interval)

                # Check if we're still connected
                current_state = self.state_machine.get_state()
                if current_state != ConnectionState.CONNECTED:
                    logger.warning(f"⚠️  Skipping periodic discovery refresh - not connected (state: {current_state.value})")
                    continue

                # Check if client and websocket are available
                if not self.client or not self.client.websocket:
                    logger.warning("⚠️  Skipping periodic discovery refresh - WebSocket not available")
                    continue

                # Run discovery refresh
                # 2025 Best Practice: Use HTTP API for discovery to avoid concurrent receive() errors
                # Don't pass websocket - discovery will use HTTP API instead
                logger.info("=" * 80)
                logger.info("🔄 PERIODIC DISCOVERY REFRESH")
                logger.info("=" * 80)

                try:
                    # 2025 Best Practice: Pass None for websocket to force HTTP API usage
                    # This avoids "Concurrent call to receive() is not allowed" errors
                    await self.discovery_service.discover_all(websocket=None, store=True)
                    logger.info("✅ Periodic discovery refresh completed successfully")
                except Exception as discovery_error:
                    logger.error(f"❌ Periodic discovery refresh failed: {discovery_error}")
                    # Log but continue - will try again next interval
                    import traceback
                    logger.error(traceback.format_exc())

                logger.info("=" * 80)

            except asyncio.CancelledError:
                logger.info("🛑 Periodic discovery refresh task cancelled")
                break
            except Exception as e:
                logger.error(f"❌ Error in periodic discovery refresh task: {e}")
                # Log but continue - will try again next interval
                import traceback
                logger.error(traceback.format_exc())
                # Short sleep to avoid rapid retries on persistent errors
                await asyncio.sleep(60)

    async def _on_connect(self):
        """Handle successful connection"""
        logger.info("=" * 80)
        logger.info("🎉 CONNECTED TO HOME ASSISTANT")
        logger.info("=" * 80)

        # Subscribe to events after connection is established
        logger.info("⏳ Preparing to subscribe to events...")
        await self._subscribe_to_events()

        # Discover devices and entities
        # 2025 Best Practice: Use HTTP API for discovery to avoid concurrent receive() errors
        # Discovery can run independently of WebSocket connection
        logger.info("🔍 Starting device and entity discovery...")
        try:
            # 2025 Best Practice: Pass None for websocket to force HTTP API usage
            # This avoids "Concurrent call to receive() is not allowed" errors
            # Discovery will use HTTP API endpoints instead of WebSocket
            await self.discovery_service.discover_all(websocket=None)

            # Subscribe to registry update events (still requires WebSocket for real-time updates)
            if self.client and self.client.websocket:
                logger.info("📡 Subscribing to registry update events...")
                await self.discovery_service.subscribe_to_device_registry_events(self.client.websocket)
                await self.discovery_service.subscribe_to_entity_registry_events(self.client.websocket)
            else:
                logger.warning("⚠️  WebSocket not available - skipping registry event subscriptions")

            # Start periodic discovery refresh task
            if not self.periodic_discovery_task or self.periodic_discovery_task.done():
                logger.info(f"🔄 Starting periodic discovery refresh (every {self.discovery_refresh_interval/60:.1f} minutes)...")
                self.periodic_discovery_task = asyncio.create_task(self._periodic_discovery_refresh())
        except Exception as e:
            logger.error(f"❌ Discovery failed (non-fatal): {e}")
            import traceback
            logger.error(traceback.format_exc())

        if self.on_connect:
            logger.info("📞 Calling external on_connect callback")
            await self.on_connect()
        else:
            logger.info("ℹ️  No external on_connect callback registered")

    async def _on_disconnect(self):
        """Handle disconnection"""
        logger.info("Disconnected from Home Assistant")

        # Cancel periodic discovery task if running
        if self.periodic_discovery_task and not self.periodic_discovery_task.done():
            logger.info("🛑 Cancelling periodic discovery refresh task...")
            self.periodic_discovery_task.cancel()
            try:
                await self.periodic_discovery_task
            except asyncio.CancelledError:
                pass

        # Transition to reconnecting or disconnected based on current state
        current_state = self.state_machine.get_state()
        if current_state == ConnectionState.CONNECTED:
            try:
                self.state_machine.transition(ConnectionState.RECONNECTING)
            except InvalidStateTransition:
                pass

        if self.on_disconnect:
            await self.on_disconnect()

        # If still in a reconnectable state, start reconnection
        current_state = self.state_machine.get_state()
        if current_state in [ConnectionState.RECONNECTING, ConnectionState.FAILED] and not self.reconnect_task:
            self.reconnect_task = asyncio.create_task(self._reconnect_loop())

    async def _on_message(self, message: dict[str, Any]):
        """Handle incoming message"""
        try:
            # Handle subscription results
            await self.event_subscription.handle_subscription_result(message)

            # Handle event messages
            if message.get("type") == "event":
                await self.event_subscription.handle_event_message(message)

                # Get event data
                event_data = message.get("event", {})
                event_type = event_data.get("event_type", "")

                # Handle registry update events
                if event_type == "device_registry_updated":
                    await self.discovery_service.handle_device_registry_event(event_data)
                elif event_type == "entity_registry_updated":
                    await self.discovery_service.handle_entity_registry_event(event_data)
                else:
                    # Process regular events (state_changed, etc)
                    processed_event = self.event_processor.process_event(event_data)

                    if processed_event:
                        # Record for rate monitoring
                        self.event_rate_monitor.record_event(processed_event)

                        # Call event handler
                        if self.on_event:
                            await self.on_event(processed_event)

            # Call general message handler
            if self.on_message:
                await self.on_message(message)

        except Exception as e:
            logger.error(f"Error handling message: {e}")
            if self.on_error:
                await self.on_error(f"Message handling error: {e}")

    async def _on_error(self, error: str):
        """Handle error"""
        self.last_error = error
        logger.error(f"WebSocket error: {error}")
        if self.on_error:
            await self.on_error(error)

    async def send_message(self, message: dict[str, Any]) -> bool:
        """
        Send message to Home Assistant
        
        Args:
            message: Message to send
            
        Returns:
            True if message sent successfully, False otherwise
        """
        if not self.client:
            logger.warning("No client available")
            return False

        return await self.client.send_message(message)

    def configure_retry_parameters(self, max_retries: int = None, base_delay: float = None,
                                   max_delay: float = None, backoff_multiplier: float = None,
                                   jitter_range: float = None):
        """
        Configure retry parameters
        
        Args:
            max_retries: Maximum number of reconnection attempts
            base_delay: Base delay in seconds for first retry
            max_delay: Maximum delay in seconds
            backoff_multiplier: Multiplier for exponential backoff
            jitter_range: Jitter range (0.0 to 1.0)
        """
        if max_retries is not None:
            self.max_retries = max_retries
        if base_delay is not None:
            self.base_delay = base_delay
        if max_delay is not None:
            self.max_delay = max_delay
        if backoff_multiplier is not None:
            self.backoff_multiplier = backoff_multiplier
        if jitter_range is not None:
            self.jitter_range = min(max(jitter_range, 0.0), 1.0)  # Clamp between 0 and 1

        logger.info(f"Retry parameters configured: max_retries={self.max_retries}, "
                   f"base_delay={self.base_delay}, max_delay={self.max_delay}, "
                   f"backoff_multiplier={self.backoff_multiplier}, jitter_range={self.jitter_range}")

    @property
    def is_running(self) -> bool:
        """
        Check if connection manager is running
        
        Returns:
            True if connected, connecting, or reconnecting
        """
        return self.state_machine.get_state() in [ConnectionState.CONNECTED, ConnectionState.CONNECTING, ConnectionState.RECONNECTING]

    def get_status(self) -> dict[str, Any]:
        """
        Get connection manager status
        
        Returns:
            Dictionary with status information
        """
        client_status = self.client.get_connection_status() if self.client else {}

        return {
            "state": self.state_machine.get_state().value,
            "is_running": self.is_running,  # Use property instead of inline computation
            "connection_attempts": self.connection_attempts,
            "successful_connections": self.successful_connections,
            "failed_connections": self.failed_connections,
            "last_connection_time": self.last_connection_time.isoformat() if self.last_connection_time else None,
            "last_error": self.last_error,
            "retry_config": {
                "max_retries": self.max_retries,
                "base_delay": self.base_delay,
                "max_delay": self.max_delay,
                "backoff_multiplier": self.backoff_multiplier,
                "jitter_range": self.jitter_range,
                "current_retry_count": self.current_retry_count
            },
            "base_url": self.base_url,
            "client_status": client_status,
            "event_subscription": self.event_subscription.get_subscription_status(),
            "event_processing": self.event_processor.get_processing_statistics(),
            "event_rates": self.event_rate_monitor.get_rate_statistics(),
            "error_statistics": self.error_handler.get_error_statistics(),
            "timestamp": datetime.now().isoformat()
        }
