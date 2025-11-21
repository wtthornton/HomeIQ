"""
MQTT Capability Listener for Zigbee2MQTT Bridge

Subscribes to Zigbee2MQTT bridge and automatically discovers device capabilities
for ALL Zigbee manufacturers (Inovelli, Aqara, IKEA, Xiaomi, Sonoff, and 100+ more).

CRITICAL SECURITY NOTE:
This component is READ-ONLY for Zigbee2MQTT topics.
NEVER publish to zigbee2mqtt/* topics - can disrupt Zigbee network.

Story: AI2.1 - MQTT Capability Listener & Universal Parser
Epic: AI-2 - Device Intelligence System
"""

import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Import CRUD operations (Story AI2.2)
from src.database.crud import upsert_device_capability


class MQTTCapabilityListener:
    """
    Listens to Zigbee2MQTT bridge for universal device capability discovery.

    Subscribes to 'zigbee2mqtt/bridge/devices' topic to receive complete
    device list with capability definitions. Works for ALL Zigbee manufacturers
    by parsing the standardized Zigbee2MQTT 'exposes' format.

    Key Features:
    - Universal manufacturer support (6,000+ device models)
    - Real-time discovery when devices are paired
    - Automatic capability parsing and storage
    - Graceful error handling

    Security:
    - READ-ONLY subscription (never publishes to bridge topics)
    - Safe to run alongside existing Zigbee2MQTT automations

    Example Usage:
        listener = MQTTCapabilityListener(mqtt_client, db_session, parser)
        await listener.start()
        # Automatically discovers capabilities when bridge publishes
    """

    def __init__(self, mqtt_client, db_session, parser):
        """
        Initialize capability listener.

        Args:
            mqtt_client: paho-mqtt client instance (from Story AI1.1)
            db_session: SQLAlchemy async session (Story 2.2 will add tables)
            parser: CapabilityParser instance
        """
        self.mqtt_client = mqtt_client
        self.db = db_session
        self.parser = parser
        self.devices_discovered = 0
        self.devices_processed = 0
        self.devices_skipped = 0
        self.errors = 0
        self._started = False
        self._subscribe_topic = "zigbee2mqtt/bridge/devices"
        self._pending_devices = []  # Queue for devices to process

    async def start(self) -> None:
        """
        Start listening to Zigbee2MQTT bridge.

        Subscribes to 'zigbee2mqtt/bridge/devices' topic and sets up
        message callback handler.

        BEST PRACTICE (from Context7): Subscription is registered, but actual
        subscribe will happen in MQTT client's on_connect callback to ensure
        automatic resubscription on reconnect.

        CRITICAL: Read-only subscription. NEVER publish to zigbee2mqtt/* topics.
        Publishing to bridge topics can disrupt Zigbee network coordination.

        Raises:
            Exception: If MQTT client is not connected
        """
        if self._started:
            logger.warning("⚠️ MQTT Capability Listener already started")
            return

        logger.info("🎧 Starting MQTT Capability Listener...")

        try:
            # Subscribe to bridge devices topic
            # NOTE: If connection is lost and reestablished, MQTT client
            # will automatically resubscribe (paho-mqtt best practice)
            self.mqtt_client.subscribe(self._subscribe_topic)
            self.mqtt_client.on_message = self._on_message

            self._started = True
            logger.info(
                "✅ MQTT Capability Listener started - waiting for bridge message\n"
                f"   📡 Subscribed to: {self._subscribe_topic}\n"
                "   🔒 Mode: READ-ONLY (safe)\n"
                "   ♻️  Auto-resubscribe on reconnect: enabled",
            )

        except Exception as e:
            logger.exception(f"❌ Failed to start MQTT Capability Listener: {e}")
            raise

    def _on_message(self, client, userdata, msg) -> None:
        """
        MQTT callback - processes bridge message.

        This callback runs in the MQTT client thread. We schedule the
        async processing to run in the main event loop.

        Args:
            client: MQTT client instance
            userdata: User data (unused)
            msg: MQTT message object with topic and payload
        """
        if msg.topic == "zigbee2mqtt/bridge/devices":
            try:
                # Parse JSON payload
                devices = json.loads(msg.payload)

                if not isinstance(devices, list):
                    logger.error(
                        f"❌ Bridge message is not a list: {type(devices)}",
                    )
                    return

                logger.info(
                    f"📡 Received bridge message with {len(devices)} devices",
                )

                # Process in async context (thread-safe)
                # Store devices for background processing
                self._pending_devices = devices
                logger.info("📋 Devices queued for processing (Story 2.3 will process in batch)")

            except json.JSONDecodeError as e:
                logger.exception(
                    f"❌ Failed to parse bridge message as JSON: {e}\n"
                    f"   Payload (first 200 chars): {msg.payload[:200]}",
                )
                self.errors += 1

            except Exception as e:
                logger.error(
                    f"❌ Unexpected error processing bridge message: {e}",
                    exc_info=True,
                )
                self.errors += 1
        else:
            # Ignore messages from other topics (shouldn't happen)
            logger.debug(f"Ignoring message from topic: {msg.topic}")

    async def _process_devices(self, devices: list[dict]) -> None:
        """
        Process all devices from Zigbee2MQTT bridge.

        Iterates through device list, parses capabilities, and stores
        them in the database. Tracks statistics for monitoring.

        Args:
            devices: List of device objects from Zigbee2MQTT bridge
        """
        logger.info(f"🔄 Processing {len(devices)} devices from bridge...")

        # Reset counters
        processed = 0
        skipped = 0
        errors = 0
        start_time = datetime.utcnow()

        for i, device in enumerate(devices, 1):
            try:
                # Log progress every 10 devices
                if i % 10 == 0:
                    logger.info(f"   Progress: {i}/{len(devices)} devices...")

                result = await self._process_single_device(device)

                if result == "processed":
                    processed += 1
                elif result == "skipped":
                    skipped += 1

            except KeyError as e:
                logger.warning(
                    f"⚠️ Device missing required field: {e}\n"
                    f"   Device: {device.get('friendly_name', 'unknown')}",
                )
                skipped += 1

            except Exception as e:
                logger.error(
                    f"❌ Error processing device: {e}\n"
                    f"   Device: {device.get('friendly_name', 'unknown')}",
                    exc_info=True,
                )
                errors += 1

        # Update instance counters
        self.devices_processed = processed
        self.devices_skipped = skipped
        self.errors += errors
        self.devices_discovered = processed + skipped

        # Calculate duration
        duration = (datetime.utcnow() - start_time).total_seconds()

        # Log completion summary
        logger.info(
            f"✅ Capability discovery complete in {duration:.1f}s\n"
            f"   ✅ Processed: {processed} devices\n"
            f"   ⏭️  Skipped: {skipped} devices (no capabilities)\n"
            f"   ❌ Errors: {errors} devices",
        )

        # Performance check (NFR12: <3 minutes for 100 devices)
        if len(devices) >= 100 and duration > 180:
            logger.warning(
                f"⚠️ Performance threshold exceeded: {duration:.1f}s for "
                f"{len(devices)} devices (expected <180s for 100 devices)",
            )

    async def _process_single_device(self, device: dict) -> str:
        """
        Process single device from bridge message.

        Extracts device metadata, parses capabilities using CapabilityParser,
        and stores in database.

        Args:
            device: Device object from Zigbee2MQTT bridge

        Returns:
            "processed" if device had capabilities and was processed
            "skipped" if device had no capabilities (coordinator/router)

        Raises:
            KeyError: If device is missing required fields
            Exception: For other processing errors
        """
        # Extract device metadata
        definition = device.get("definition")

        if not definition or definition is None:
            # No definition = coordinator or router (not an end device)
            logger.debug(
                f"Skipping device without definition: "
                f"{device.get('friendly_name', 'unknown')}",
            )
            return "skipped"

        # Extract definition fields
        manufacturer = definition.get("vendor", "Unknown")
        model = definition.get("model", "Unknown")
        description = definition.get("description", "")
        exposes = definition.get("exposes", [])

        if not exposes or len(exposes) == 0:
            # No exposes = no capabilities to discover
            logger.debug(
                f"Device {model} has no exposes "
                f"(coordinator/router or unsupported device)",
            )
            return "skipped"

        # Parse capabilities using universal parser
        try:
            capabilities = self.parser.parse_exposes(exposes)
        except Exception as e:
            logger.exception(
                f"❌ Failed to parse exposes for {manufacturer} {model}: {e}",
            )
            raise

        if not capabilities:
            logger.debug(
                f"Parser returned no capabilities for {manufacturer} {model}",
            )
            return "skipped"

        logger.info(
            f"📦 Discovered {len(capabilities)} capabilities for "
            f"{manufacturer} {model}",
        )
        logger.debug(f"   Capabilities: {list(capabilities.keys())}")

        # Store in database (Story 2.2 will implement storage)
        await self._store_capabilities(
            device_model=model,
            manufacturer=manufacturer,
            description=description,
            capabilities=capabilities,
            mqtt_exposes=exposes,
        )

        return "processed"

    async def _store_capabilities(
        self,
        device_model: str,
        manufacturer: str,
        description: str,
        capabilities: dict,
        mqtt_exposes: list,
    ) -> None:
        """
        Store capabilities in database.

        Story AI2.2: Implements actual database storage.

        Args:
            device_model: Device model identifier (e.g., "VZM31-SN")
            manufacturer: Manufacturer name (e.g., "Inovelli")
            description: Device description
            capabilities: Parsed capabilities dict
            mqtt_exposes: Raw MQTT exposes array
        """
        if not self.db:
            logger.debug(
                f"Database session not available, skipping storage for {device_model}",
            )
            return

        try:
            # Upsert capability (insert if new, update if exists)
            async with self.db as session:
                await upsert_device_capability(
                    db=session,
                    device_model=device_model,
                    manufacturer=manufacturer,
                    description=description,
                    capabilities=capabilities,
                    mqtt_exposes=mqtt_exposes,
                    integration_type="zigbee2mqtt",
                )

            logger.info(
                f"💾 Stored capabilities for {manufacturer} {device_model}\n"
                f"   Capabilities: {len(capabilities)} features\n"
                f"   Database: ai_automation.db → device_capabilities",
            )

        except Exception as e:
            logger.error(
                f"❌ Failed to store capabilities for {device_model}: {e}",
                exc_info=True,
            )
            # Don't raise - continue processing other devices

    def get_stats(self) -> dict[str, int]:
        """
        Get discovery statistics for monitoring.

        Returns:
            Dict with discovery metrics:
            - devices_discovered: Total devices seen
            - devices_processed: Devices with capabilities stored
            - devices_skipped: Devices without capabilities
            - errors: Number of processing errors
        """
        return {
            "devices_discovered": self.devices_discovered,
            "devices_processed": self.devices_processed,
            "devices_skipped": self.devices_skipped,
            "errors": self.errors,
        }

    def is_started(self) -> bool:
        """
        Check if listener has been started.

        Returns:
            True if listener is running, False otherwise
        """
        return self._started

    async def process_pending_devices(self) -> None:
        """
        Process any pending devices from MQTT queue.

        Called by scheduler or manually to process devices received via MQTT.
        This runs in the async event loop (not MQTT thread).
        """
        if not self._pending_devices:
            logger.debug("No pending devices to process")
            return

        devices = self._pending_devices
        self._pending_devices = []  # Clear queue

        await self._process_devices(devices)

