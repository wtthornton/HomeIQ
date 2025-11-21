#!/usr/bin/env python3
"""
Force Zigbee2MQTT Device Discovery Script

This script forces Zigbee2MQTT to rediscover and enable devices
that are currently disabled.
"""

import asyncio
import os
from datetime import datetime
from typing import Any

import aiohttp

# Configuration
HA_URL = os.getenv("HA_HTTP_URL", "http://192.168.1.86:8123")
HA_TOKEN = os.getenv("HA_TOKEN", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJmYzAxMTBmZGRiNzc0ZDNjYTJhNjg2Mjk5M2U3ZGE4MiIsImlhdCI6MTc2MDM5NjUwNSwiZXhwIjoyMDc1NzU2NTA1fQ.dngeB--Ov3TgE1iJR3VyL9tX-a99jTiiUxlrz467j1Q")

async def force_zigbee_discovery(session: aiohttp.ClientSession) -> bool:
    """Force Zigbee2MQTT to rediscover all devices"""
    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    }

    # Try multiple service calls to force discovery
    services_to_try = [
        "zigbee2mqtt/discover",
        "mqtt/discover",
        "homeassistant/restart",
    ]

    for service in services_to_try:
        try:
            service_data = {}
            async with session.post(
                f"{HA_URL}/api/services/{service}",
                json=service_data,
                headers=headers,
            ) as response:
                if response.status in [200, 202]:
                    print(f"✅ Successfully called {service}")
                    return True
                print(f"❌ Failed to call {service}: {response.status}")
        except Exception as e:
            print(f"❌ Error calling {service}: {e}")

    return False

async def check_mqtt_devices(session: aiohttp.ClientSession) -> list[dict[str, Any]]:
    """Check for MQTT devices in Home Assistant"""
    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        async with session.get(f"{HA_URL}/api/states", headers=headers) as response:
            if response.status == 200:
                states = await response.json()
                mqtt_devices = []

                for state in states:
                    entity_id = state.get("entity_id", "")
                    friendly_name = state.get("attributes", {}).get("friendly_name", "")

                    # Look for MQTT entities (Zigbee2MQTT devices appear as MQTT entities)
                    if ("mqtt" in entity_id or
                        "Bar Light" in friendly_name or
                        "Office Fan" in friendly_name or
                        "Office Light" in friendly_name):
                        mqtt_devices.append({
                            "entity_id": entity_id,
                            "friendly_name": friendly_name,
                            "state": state.get("state"),
                            "attributes": state.get("attributes", {}),
                        })

                print(f"✅ Found {len(mqtt_devices)} MQTT entities")
                return mqtt_devices
            print(f"❌ Failed to get states: {response.status}")
            return []
    except Exception as e:
        print(f"❌ Error getting states: {e}")
        return []

async def main():
    """Main discovery process"""
    print("=" * 80)
    print("🔍 FORCE ZIGBEE2MQTT DEVICE DISCOVERY")
    print("=" * 80)
    print(f"Home Assistant URL: {HA_URL}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 80)

    # Create HTTP session
    connector = aiohttp.TCPConnector(ssl=False)
    timeout = aiohttp.ClientTimeout(total=60)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        # Check current MQTT devices
        print("📱 Checking current MQTT devices...")
        mqtt_devices = await check_mqtt_devices(session)

        if mqtt_devices:
            print("🎉 FOUND MQTT DEVICES:")
            for device in mqtt_devices:
                print(f"   - {device['friendly_name']} ({device['entity_id']})")
        else:
            print("⚠️  No MQTT devices found")

        # Force discovery
        print("🔄 Forcing Zigbee2MQTT discovery...")
        await force_zigbee_discovery(session)

        # Wait and check again
        print("⏳ Waiting for discovery to complete...")
        await asyncio.sleep(15)

        # Check again
        print("📱 Checking MQTT devices after forced discovery...")
        mqtt_devices = await check_mqtt_devices(session)

        if mqtt_devices:
            print("🎉 FOUND MQTT DEVICES AFTER DISCOVERY:")
            for device in mqtt_devices:
                print(f"   - {device['friendly_name']} ({device['entity_id']})")
        else:
            print("⚠️  Still no MQTT devices found")

    print("=" * 80)
    print("✅ FORCED DISCOVERY COMPLETE")
    print("=" * 80)
    print("Next steps:")
    print("1. Check Home Assistant: Settings → Devices & Services")
    print("2. Look for MQTT integration")
    print("3. Restart HA Ingestor: docker restart homeiq-websocket")

if __name__ == "__main__":
    asyncio.run(main())
