#!/usr/bin/env python3
"""
Zigbee2MQTT Integration Setup Script

This script helps set up the Zigbee2MQTT integration properly in Home Assistant.
"""

import asyncio
import os

import aiohttp

# Configuration
HA_URL = os.getenv("HA_HTTP_URL", "http://192.168.1.86:8123")
HA_TOKEN = os.getenv("HA_TOKEN", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJmYzAxMTBmZGRiNzc0ZDNjYTJhNjg2Mjk5M2U3ZGE4MiIsImlhdCI6MTc2MDM5NjUwNSwiZXhwIjoyMDc1NzU2NTA1fQ.dngeB--Ov3TgE1iJR3VyL9tX-a99jTiiUxlrz467j1Q")

async def setup_zigbee2mqtt_integration():
    """Set up Zigbee2MQTT integration via Home Assistant API"""

    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    }

    connector = aiohttp.TCPConnector(ssl=False)
    timeout = aiohttp.ClientTimeout(total=60)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        print("=" * 80)
        print("🔧 ZIGBEE2MQTT INTEGRATION SETUP")
        print("=" * 80)

        # Step 1: Check if Zigbee2MQTT addon is running
        print("📱 Checking Zigbee2MQTT addon status...")
        try:
            async with session.get(f"{HA_URL}/api/hassio/addons", headers=headers) as response:
                if response.status == 200:
                    addons = await response.json()
                    zigbee_addon = None
                    for addon in addons.get("data", {}).get("addons", []):
                        if addon.get("slug") == "zigbee2mqtt":
                            zigbee_addon = addon
                            break

                    if zigbee_addon:
                        print(f"✅ Zigbee2MQTT addon found: {zigbee_addon.get('name')}")
                        print(f"   Status: {zigbee_addon.get('state')}")
                        print(f"   Installed: {zigbee_addon.get('installed')}")
                        print(f"   Started: {zigbee_addon.get('started')}")

                        if not zigbee_addon.get("started"):
                            print("⚠️  Zigbee2MQTT addon is not started!")
                            print("   Please start it from Settings → Add-ons → Zigbee2MQTT")
                            return False
                    else:
                        print("❌ Zigbee2MQTT addon not found!")
                        return False
                else:
                    print(f"❌ Failed to get addon status: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ Error checking addon status: {e}")
            return False

        # Step 2: Try to create Zigbee2MQTT integration
        print("\n🔗 Attempting to create Zigbee2MQTT integration...")

        # Try different integration setup methods
        integration_configs = [
            {
                "domain": "zigbee2mqtt",
                "data": {
                    "host": "localhost",
                    "port": 8485,
                    "username": "",
                    "password": "",
                },
            },
            {
                "domain": "mqtt",
                "data": {
                    "broker": "localhost",
                    "port": 1883,
                    "username": "",
                    "password": "",
                },
            },
        ]

        for config in integration_configs:
            try:
                async with session.post(
                    f"{HA_URL}/api/config/config_entries/flow",
                    json={
                        "handler": config["domain"],
                        "show_advanced_options": True,
                        "data": config["data"],
                    },
                    headers=headers,
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        print(f"✅ Successfully created {config['domain']} integration flow")
                        print(f"   Flow ID: {result.get('flow_id')}")

                        # Complete the flow
                        try:
                            async with session.post(
                                f"{HA_URL}/api/config/config_entries/flow/{result.get('flow_id')}",
                                json={"result": config["data"]},
                                headers=headers,
                            ) as complete_response:
                                if complete_response.status == 200:
                                    print(f"✅ Successfully completed {config['domain']} integration")
                                    return True
                                print(f"❌ Failed to complete {config['domain']} integration: {complete_response.status}")
                        except Exception as e:
                            print(f"❌ Error completing {config['domain']} integration: {e}")
                    else:
                        print(f"❌ Failed to create {config['domain']} integration flow: {response.status}")
            except Exception as e:
                print(f"❌ Error creating {config['domain']} integration: {e}")

        # Step 3: Manual setup instructions
        print("\n📋 MANUAL SETUP REQUIRED")
        print("=" * 50)
        print("Since automatic integration creation failed, please follow these steps:")
        print()
        print("1. Go to Home Assistant: Settings → Devices & Services")
        print("2. Click 'Add Integration'")
        print("3. Search for 'Zigbee2MQTT'")
        print("4. If not found, search for 'MQTT'")
        print("5. Configure with these settings:")
        print("   - Host: localhost")
        print("   - Port: 8485 (for Zigbee2MQTT) or 1883 (for MQTT)")
        print("   - Username: (leave empty)")
        print("   - Password: (leave empty)")
        print()
        print("6. After integration is created:")
        print("   - Check Settings → Devices & Services → MQTT")
        print("   - Look for Zigbee2MQTT devices")
        print("   - Restart HA Ingestor: docker restart homeiq-websocket")

        return False

async def main():
    """Main setup process"""
    success = await setup_zigbee2mqtt_integration()

    if success:
        print("\n🎉 Zigbee2MQTT integration setup completed!")
        print("Next steps:")
        print("1. Wait 2-3 minutes for device discovery")
        print("2. Check Settings → Devices & Services → MQTT")
        print("3. Restart HA Ingestor: docker restart homeiq-websocket")
        print("4. Check your dashboard: http://localhost:3000/devices")
    else:
        print("\n⚠️  Manual setup required - see instructions above")

    print("=" * 80)
    print("✅ ZIGBEE2MQTT INTEGRATION SETUP COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
