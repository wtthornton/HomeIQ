#!/usr/bin/env python3
"""
Home Assistant API Zigbee2MQTT Device Discovery Fix

This script uses the Home Assistant API to diagnose and fix Zigbee2MQTT device discovery issues.
It can trigger device discovery, check MQTT integration, and force device updates.
"""

import asyncio
import os
from datetime import datetime
from typing import Any

import aiohttp

# Configuration
HA_URL = os.getenv("HA_HTTP_URL", "http://192.168.1.86:8123")
HA_TOKEN = os.getenv("HA_TOKEN", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJmYzAxMTBmZGRiNzc0ZDNjYTJhNjg2Mjk5M2U3ZGE4MiIsImlhdCI6MTc2MDM5NjUwNSwiZXhwIjoyMDc1NzU2NTA1fQ.dngeB--Ov3TgE1iJR3VyL9tX-a99jTiiUxlrz467j1Q")

class HADeviceDiscoveryFixer:
    """Home Assistant API device discovery fixer"""

    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        self.headers = {
            "Authorization": f"Bearer {HA_TOKEN}",
            "Content-Type": "application/json",
        }

    async def check_ha_health(self) -> bool:
        """Check if Home Assistant is accessible"""
        try:
            async with self.session.get(f"{HA_URL}/api/", headers=self.headers) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Home Assistant is accessible: {data.get('message', 'OK')}")
                    return True
                print(f"❌ Home Assistant health check failed: {response.status}")
                return False
        except Exception as e:
            print(f"❌ Error checking HA health: {e}")
            return False

    async def get_integrations(self) -> list[dict[str, Any]]:
        """Get all Home Assistant integrations"""
        try:
            async with self.session.get(f"{HA_URL}/api/config/config_entries/entry", headers=self.headers) as response:
                if response.status == 200:
                    integrations = await response.json()
                    print(f"✅ Found {len(integrations)} integrations")
                    return integrations
                print(f"❌ Failed to get integrations: {response.status}")
                return []
        except Exception as e:
            print(f"❌ Error getting integrations: {e}")
            return []

    async def find_mqtt_integration(self) -> dict[str, Any] | None:
        """Find the MQTT integration"""
        integrations = await self.get_integrations()
        for integration in integrations:
            if integration.get("domain") == "mqtt":
                print(f"✅ Found MQTT integration: {integration.get('title', 'Unknown')}")
                return integration
        print("❌ MQTT integration not found")
        return None

    async def find_zigbee2mqtt_integration(self) -> dict[str, Any] | None:
        """Find the Zigbee2MQTT integration"""
        integrations = await self.get_integrations()
        for integration in integrations:
            if integration.get("domain") == "zigbee2mqtt":
                print(f"✅ Found Zigbee2MQTT integration: {integration.get('title', 'Unknown')}")
                return integration
        print("❌ Zigbee2MQTT integration not found")
        return None

    async def trigger_mqtt_discovery(self) -> bool:
        """Trigger MQTT device discovery"""
        try:
            # Try different MQTT discovery services
            services_to_try = [
                "mqtt/discover",
                "mqtt/scan",
                "mqtt/reload",
                "homeassistant/reload_config_entry",
            ]

            for service in services_to_try:
                try:
                    async with self.session.post(
                        f"{HA_URL}/api/services/{service}",
                        json={},
                        headers=self.headers,
                    ) as response:
                        if response.status in [200, 202]:
                            print(f"✅ Successfully triggered {service}")
                            return True
                        print(f"❌ Failed to trigger {service}: {response.status}")
                except Exception as e:
                    print(f"❌ Error triggering {service}: {e}")

            return False
        except Exception as e:
            print(f"❌ Error triggering MQTT discovery: {e}")
            return False

    async def reload_mqtt_integration(self) -> bool:
        """Reload the MQTT integration"""
        mqtt_integration = await self.find_mqtt_integration()
        if not mqtt_integration:
            return False

        try:
            entry_id = mqtt_integration.get("entry_id")
            async with self.session.post(
                f"{HA_URL}/api/config/config_entries/entry/{entry_id}/reload",
                headers=self.headers,
            ) as response:
                if response.status == 200:
                    print("✅ Successfully reloaded MQTT integration")
                    return True
                print(f"❌ Failed to reload MQTT integration: {response.status}")
                return False
        except Exception as e:
            print(f"❌ Error reloading MQTT integration: {e}")
            return False

    async def get_mqtt_devices(self) -> list[dict[str, Any]]:
        """Get devices from MQTT integration"""
        try:
            async with self.session.get(f"{HA_URL}/api/devices", headers=self.headers) as response:
                if response.status == 200:
                    devices = await response.json()
                    mqtt_devices = [d for d in devices if "mqtt" in d.get("identifiers", [[]])[0][0].lower()]
                    print(f"✅ Found {len(mqtt_devices)} MQTT devices")
                    return mqtt_devices
                print(f"❌ Failed to get devices: {response.status}")
                return []
        except Exception as e:
            print(f"❌ Error getting MQTT devices: {e}")
            return []

    async def get_zigbee2mqtt_devices(self) -> list[dict[str, Any]]:
        """Get devices specifically from Zigbee2MQTT"""
        mqtt_devices = await self.get_mqtt_devices()
        zigbee_devices = []

        for device in mqtt_devices:
            identifiers = device.get("identifiers", [])
            for identifier in identifiers:
                if len(identifier) >= 2 and "zigbee2mqtt" in identifier[1].lower():
                    zigbee_devices.append(device)
                    break

        print(f"✅ Found {len(zigbee_devices)} Zigbee2MQTT devices")
        return zigbee_devices

    async def check_mqtt_topics(self) -> list[str]:
        """Check MQTT topics for Zigbee2MQTT discovery messages"""
        try:
            # This would require MQTT broker access, which we don't have directly
            # Instead, we'll check if there are any MQTT entities
            async with self.session.get(f"{HA_URL}/api/states", headers=self.headers) as response:
                if response.status == 200:
                    states = await response.json()
                    mqtt_entities = [s for s in states if s.get("entity_id", "").startswith("mqtt.")]
                    zigbee_entities = [s for s in mqtt_entities if "zigbee2mqtt" in s.get("attributes", {}).get("friendly_name", "").lower()]

                    print(f"✅ Found {len(mqtt_entities)} MQTT entities")
                    print(f"✅ Found {len(zigbee_entities)} Zigbee2MQTT entities")

                    if zigbee_entities:
                        print("🎉 Zigbee2MQTT entities found:")
                        for entity in zigbee_entities[:10]:  # Show first 10
                            print(f"  • {entity.get('entity_id')} - {entity.get('attributes', {}).get('friendly_name', 'Unknown')}")

                    return [entity.get("entity_id") for entity in zigbee_entities]
                print(f"❌ Failed to get states: {response.status}")
                return []
        except Exception as e:
            print(f"❌ Error checking MQTT topics: {e}")
            return []

    async def trigger_zigbee2mqtt_discovery(self) -> bool:
        """Trigger Zigbee2MQTT specific discovery"""
        try:
            # Try Zigbee2MQTT specific services
            services_to_try = [
                "zigbee2mqtt/discover",
                "zigbee2mqtt/scan",
                "zigbee2mqtt/reload",
                "zigbee2mqtt/permit_join",
            ]

            for service in services_to_try:
                try:
                    async with self.session.post(
                        f"{HA_URL}/api/services/{service}",
                        json={},
                        headers=self.headers,
                    ) as response:
                        if response.status in [200, 202]:
                            print(f"✅ Successfully triggered {service}")
                            return True
                        print(f"❌ Failed to trigger {service}: {response.status}")
                except Exception as e:
                    print(f"❌ Error triggering {service}: {e}")

            return False
        except Exception as e:
            print(f"❌ Error triggering Zigbee2MQTT discovery: {e}")
            return False

    async def restart_zigbee2mqtt_addon(self) -> bool:
        """Restart the Zigbee2MQTT addon"""
        try:
            # This requires supervisor API access
            async with self.session.post(
                f"{HA_URL}/api/hassio/addon/zigbee2mqtt/restart",
                headers=self.headers,
            ) as response:
                if response.status == 200:
                    print("✅ Successfully restarted Zigbee2MQTT addon")
                    return True
                print(f"❌ Failed to restart Zigbee2MQTT addon: {response.status}")
                return False
        except Exception as e:
            print(f"❌ Error restarting Zigbee2MQTT addon: {e}")
            return False

    async def comprehensive_fix(self) -> bool:
        """Run a comprehensive fix sequence"""
        print("🔧 Running comprehensive Zigbee2MQTT discovery fix...")

        success_count = 0
        total_attempts = 0

        # Step 1: Check HA health
        total_attempts += 1
        if await self.check_ha_health():
            success_count += 1

        # Step 2: Find integrations
        total_attempts += 1
        mqtt_integration = await self.find_mqtt_integration()
        if mqtt_integration:
            success_count += 1

        total_attempts += 1
        zigbee_integration = await self.find_zigbee2mqtt_integration()
        if zigbee_integration:
            success_count += 1

        # Step 3: Check current devices
        total_attempts += 1
        zigbee_devices = await self.get_zigbee2mqtt_devices()
        if zigbee_devices:
            success_count += 1

        # Step 4: Check MQTT entities
        total_attempts += 1
        zigbee_entities = await self.check_mqtt_topics()
        if zigbee_entities:
            success_count += 1

        # Step 5: Trigger discovery
        total_attempts += 1
        if await self.trigger_mqtt_discovery():
            success_count += 1

        total_attempts += 1
        if await self.trigger_zigbee2mqtt_discovery():
            success_count += 1

        # Step 6: Reload MQTT integration
        total_attempts += 1
        if await self.reload_mqtt_integration():
            success_count += 1

        # Step 7: Wait and check again
        print("⏳ Waiting for discovery to complete...")
        await asyncio.sleep(10)

        total_attempts += 1
        zigbee_devices_after = await self.get_zigbee2mqtt_devices()
        if len(zigbee_devices_after) > len(zigbee_devices):
            success_count += 1
            print(f"🎉 Discovery successful! Found {len(zigbee_devices_after)} devices (was {len(zigbee_devices)})")

        total_attempts += 1
        zigbee_entities_after = await self.check_mqtt_topics()
        if len(zigbee_entities_after) > len(zigbee_entities):
            success_count += 1
            print(f"🎉 Entity discovery successful! Found {len(zigbee_entities_after)} entities (was {len(zigbee_entities)})")

        success_rate = (success_count / total_attempts) * 100
        print(f"\n📊 Fix Results: {success_count}/{total_attempts} successful ({success_rate:.1f}%)")

        return success_rate > 50

async def main():
    """Main fix process"""
    print("=" * 80)
    print("🔧 HOME ASSISTANT API ZIGBEE2MQTT DISCOVERY FIX")
    print("=" * 80)
    print(f"Home Assistant URL: {HA_URL}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 80)

    # Create HTTP session
    connector = aiohttp.TCPConnector(ssl=False)
    timeout = aiohttp.ClientTimeout(total=120)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        fixer = HADeviceDiscoveryFixer(session)

        # Run comprehensive fix
        success = await fixer.comprehensive_fix()

        if success:
            print("\n🎉 Zigbee2MQTT discovery fix completed successfully!")
            print("Next steps:")
            print("1. Check Home Assistant: Settings → Devices & Services")
            print("2. Look for MQTT integration and Zigbee2MQTT devices")
            print("3. Restart HA Ingestor: docker restart homeiq-websocket")
            print("4. Check your dashboard: http://localhost:3000/devices")
        else:
            print("\n⚠️  Zigbee2MQTT discovery fix had limited success")
            print("Manual steps required:")
            print("1. Check Zigbee2MQTT addon logs for errors")
            print("2. Verify Zigbee2MQTT configuration file")
            print("3. Ensure Inovelli switches are enabled in Zigbee2MQTT")
            print("4. Check MQTT broker connectivity")

    print("=" * 80)
    print("✅ HOME ASSISTANT API FIX COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
