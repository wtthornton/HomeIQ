"""
Batch Device Capability Update

Replaces real-time MQTT listener with daily batch query.
Story AI2.5 - Unified Daily Batch Job

Instead of subscribing to MQTT 24/7, this module queries the Zigbee2MQTT
bridge once per day during the scheduled analysis run.
"""

import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


async def update_device_capabilities_batch(
    mqtt_client,
    data_api_client,
    db_session_factory,
) -> dict[str, int]:
    """
    Query Zigbee2MQTT bridge for device capabilities (batch).

    This replaces the real-time MQTT listener from Story 2.1.
    Called daily at 3 AM by the unified batch job.

    Args:
        mqtt_client: MQTT client instance
        data_api_client: Data API client for fetching HA devices
        db_session_factory: Database session factory

    Returns:
        Dictionary with update statistics:
        {
            "devices_checked": int,
            "capabilities_updated": int,
            "new_devices": int,
            "errors": int
        }

    Story AI2.5: Unified Daily Batch Job
    """
    stats = {
        "devices_checked": 0,
        "capabilities_updated": 0,
        "new_devices": 0,
        "errors": 0,
    }

    try:
        logger.info("📡 Starting batch device capability update...")

        # =====================================================================
        # Step 1: Get all HA devices
        # =====================================================================
        logger.info("   → Step 1: Fetching devices from Home Assistant...")

        try:
            devices = await data_api_client.get_all_devices()
            stats["devices_checked"] = len(devices)
            logger.info(f"   ✅ Found {len(devices)} devices in HA")
        except Exception as e:
            logger.exception(f"   ❌ Failed to fetch HA devices: {e}")
            stats["errors"] += 1
            return stats

        if not devices:
            logger.info("   ℹ️  No devices found in HA, skipping capability update")
            return stats

        # =====================================================================
        # Step 2: Query Zigbee2MQTT bridge (one-time batch query)
        # =====================================================================
        logger.info("   → Step 2: Querying Zigbee2MQTT bridge...")

        try:
            # Query bridge/devices topic for all device definitions
            bridge_data = await _query_zigbee2mqtt_bridge(mqtt_client)

            if not bridge_data:
                logger.warning("   ⚠️  No data from Zigbee2MQTT bridge, skipping")
                return stats

            logger.info(f"   ✅ Retrieved data for {len(bridge_data)} Zigbee devices")
        except Exception as e:
            logger.exception(f"   ❌ Failed to query Zigbee2MQTT bridge: {e}")
            stats["errors"] += 1
            return stats

        # =====================================================================
        # Step 3: Parse and store capabilities for new/updated devices
        # =====================================================================
        logger.info("   → Step 3: Parsing and storing capabilities...")

        from src.database.crud import get_device_capability, upsert_device_capability

        from .capability_parser import CapabilityParser

        parser = CapabilityParser()

        # Create index of bridge data by model for faster lookup
        bridge_index = {device.get("model"): device for device in bridge_data if device.get("model")}

        for device in devices:
            device_model = device.get("model")
            manufacturer = device.get("manufacturer", "Unknown")

            if not device_model:
                continue  # Skip devices without model info

            try:
                # Check if we have bridge data for this model
                bridge_device = bridge_index.get(device_model)
                if not bridge_device:
                    continue  # Not a Zigbee device or not in bridge

                # Check if capability already exists and is fresh
                async with db_session_factory() as db:
                    existing = await get_device_capability(db, device_model)

                    if existing and not _is_stale(existing):
                        continue  # Skip if capability is fresh (<30 days old)

                    # Parse capabilities from bridge data
                    exposes = bridge_device.get("exposes", [])
                    if not exposes:
                        continue  # No capability data available

                    parsed_capabilities = parser.parse_exposes(exposes)

                    if not parsed_capabilities:
                        continue  # Parsing failed

                    # Prepare capability record
                    capability_data = {
                        "device_model": device_model,
                        "manufacturer": manufacturer,
                        "integration_type": "zigbee",
                        "description": bridge_device.get("description", ""),
                        "capabilities": parsed_capabilities,
                        "mqtt_exposes": exposes,  # Store raw data
                        "source": "zigbee2mqtt_bridge",
                        "last_updated": datetime.utcnow(),
                    }

                    # Upsert capability
                    await upsert_device_capability(db, capability_data)

                    stats["capabilities_updated"] += 1
                    if not existing:
                        stats["new_devices"] += 1
                        logger.info(f"      🆕 New device: {device_model} ({manufacturer})")
                    else:
                        logger.debug(f"      🔄 Updated: {device_model}")

            except Exception as e:
                logger.exception(f"      ❌ Failed to process {device_model}: {e}")
                stats["errors"] += 1

        # =====================================================================
        # Summary
        # =====================================================================
        logger.info("   ✅ Batch capability update complete:")
        logger.info(f"      - Devices checked: {stats['devices_checked']}")
        logger.info(f"      - Capabilities updated: {stats['capabilities_updated']}")
        logger.info(f"      - New devices: {stats['new_devices']}")
        logger.info(f"      - Errors: {stats['errors']}")

        return stats

    except Exception as e:
        logger.error(f"❌ Batch capability update failed: {e}", exc_info=True)
        stats["errors"] += 1
        return stats


async def _query_zigbee2mqtt_bridge(mqtt_client) -> list[dict] | None:
    """
    Query Zigbee2MQTT bridge for device list (one-time query).

    Args:
        mqtt_client: MQTT client instance

    Returns:
        List of device dictionaries from bridge, or None if query fails
    """
    try:
        # In production, this would be a request-response MQTT pattern
        # or reading from bridge/devices topic

        # For now, we'll use a simplified approach:
        # Subscribe temporarily, wait for message, unsubscribe

        import asyncio
        import json

        received_data = []
        event = asyncio.Event()

        def on_message(client, userdata, msg):
            """Callback for MQTT message"""
            try:
                if msg.topic == "zigbee2mqtt/bridge/devices":
                    data = json.loads(msg.payload)
                    if isinstance(data, list):
                        received_data.extend(data)
                    event.set()
            except Exception as e:
                logger.exception(f"Failed to parse bridge message: {e}")
                event.set()

        # Subscribe to bridge/devices
        mqtt_client.client.subscribe("zigbee2mqtt/bridge/devices")
        mqtt_client.client.on_message = on_message

        # Request bridge info (some bridges send data on request)
        mqtt_client.client.publish("zigbee2mqtt/bridge/request/devices", "")

        # Wait for response (with timeout)
        try:
            await asyncio.wait_for(event.wait(), timeout=10.0)
        except asyncio.TimeoutError:
            logger.warning("Timeout waiting for Zigbee2MQTT bridge response")

        # Unsubscribe
        mqtt_client.client.unsubscribe("zigbee2mqtt/bridge/devices")

        return received_data if received_data else None

    except Exception as e:
        logger.exception(f"Failed to query Zigbee2MQTT bridge: {e}")
        return None


def _is_stale(capability_record, max_age_days: int = 30) -> bool:
    """
    Check if capability record is stale and needs refresh.

    Args:
        capability_record: DeviceCapability SQLAlchemy model instance
        max_age_days: Maximum age in days before considered stale

    Returns:
        True if stale (older than max_age_days), False otherwise
    """
    if not capability_record:
        return True

    if not hasattr(capability_record, "last_updated") or not capability_record.last_updated:
        return True  # No timestamp = stale

    age = datetime.utcnow() - capability_record.last_updated
    return age > timedelta(days=max_age_days)

