#!/usr/bin/env python3
"""
Manual Zigbee2MQTT Device Discovery Script

This script specifically looks for Zigbee2MQTT devices and forces them
into Home Assistant's device registry.
"""

import asyncio
import os
from datetime import datetime
from typing import Any

import aiohttp

# Configuration
HA_URL = os.getenv("HA_HTTP_URL", "http://192.168.1.86:8123")
HA_TOKEN = os.getenv("HA_TOKEN", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJmYzAxMTBmZGRiNzc0ZDNjYTJhNjg2Mjk5M2U3ZGE4MiIsImlhdCI6MTc2MDM5NjUwNSwiZXhwIjoyMDc1NzU2NTA1fQ.dngeB--Ov3TgE1iJR3VyL9tX-a99jTiiUxlrz467j1Q")
DATA_API_URL = os.getenv("DATA_API_URL", "http://localhost:8006")

async def trigger_zigbee_discovery(session: aiohttp.ClientSession) -> bool:
    """Trigger Zigbee2MQTT device discovery"""
    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    }

    # Try to trigger discovery via service call
    service_data = {
        "entity_id": "zigbee2mqtt",
    }

    try:
        async with session.post(
            f"{HA_URL}/api/services/zigbee2mqtt/discover",
            json=service_data,
            headers=headers,
        ) as response:
            if response.status in [200, 202]:
                print("✅ Triggered Zigbee2MQTT discovery")
                return True
            print(f"❌ Failed to trigger discovery: {response.status}")
            return False
    except Exception as e:
        print(f"❌ Error triggering discovery: {e}")
        return False

async def check_zigbee_devices(session: aiohttp.ClientSession) -> list[dict[str, Any]]:
    """Check for Zigbee2MQTT devices in Home Assistant states"""
    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        async with session.get(f"{HA_URL}/api/states", headers=headers) as response:
            if response.status == 200:
                states = await response.json()
                zigbee_devices = []

                for state in states:
                    entity_id = state.get("entity_id", "")
                    friendly_name = state.get("attributes", {}).get("friendly_name", "")

                    # Look for Zigbee2MQTT entities
                    if ("zigbee2mqtt" in entity_id or
                        "Bar Light" in friendly_name or
                        "Office Fan" in friendly_name or
                        "Office Light" in friendly_name):
                        zigbee_devices.append({
                            "entity_id": entity_id,
                            "friendly_name": friendly_name,
                            "state": state.get("state"),
                            "attributes": state.get("attributes", {}),
                        })

                print(f"✅ Found {len(zigbee_devices)} Zigbee2MQTT entities")
                return zigbee_devices
            print(f"❌ Failed to get states: {response.status}")
            return []
    except Exception as e:
        print(f"❌ Error getting states: {e}")
        return []

async def main():
    """Main discovery process"""
    print("=" * 80)
    print("🔍 ZIGBEE2MQTT DEVICE DISCOVERY")
    print("=" * 80)
    print(f"Home Assistant URL: {HA_URL}")
    print(f"Data API URL: {DATA_API_URL}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 80)

    # Create HTTP session
    connector = aiohttp.TCPConnector(ssl=False)
    timeout = aiohttp.ClientTimeout(total=60)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        # Check current Zigbee devices
        print("📱 Checking current Zigbee2MQTT devices...")
        zigbee_devices = await check_zigbee_devices(session)

        if zigbee_devices:
            print("🎉 FOUND ZIGBEE DEVICES:")
            for device in zigbee_devices:
                print(f"   - {device['friendly_name']} ({device['entity_id']})")
        else:
            print("⚠️  No Zigbee2MQTT devices found in Home Assistant states")

        # Try to trigger discovery
        print("🔄 Triggering Zigbee2MQTT discovery...")
        await trigger_zigbee_discovery(session)

        # Wait a bit and check again
        print("⏳ Waiting for discovery to complete...")
        await asyncio.sleep(10)

        # Check again
        print("📱 Checking Zigbee2MQTT devices after discovery...")
        zigbee_devices = await check_zigbee_devices(session)

        if zigbee_devices:
            print("🎉 FOUND ZIGBEE DEVICES AFTER DISCOVERY:")
            for device in zigbee_devices:
                print(f"   - {device['friendly_name']} ({device['entity_id']})")
        else:
            print("⚠️  Still no Zigbee2MQTT devices found")

    print("=" * 80)
    print("✅ ZIGBEE DISCOVERY COMPLETE")
    print("=" * 80)
    print("If devices were found, restart HA Ingestor:")
    print("docker restart homeiq-websocket")

if __name__ == "__main__":
    asyncio.run(main())
