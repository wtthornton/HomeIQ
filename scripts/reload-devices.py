#!/usr/bin/env python3
"""
Script to delete all devices/entities from database and trigger re-discovery
"""

import asyncio
import os
import sys

import aiohttp

# Fix Windows console encoding
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

# Configuration
DATA_API_URL = os.getenv("DATA_API_URL", "http://localhost:8006")
WEBSOCKET_INGESTION_URL = os.getenv("WEBSOCKET_INGESTION_URL", "http://localhost:8001")

async def clear_devices(session: aiohttp.ClientSession) -> bool:
    """Delete all devices and entities from database"""
    try:
        print("🗑️  Deleting all devices and entities from database...")
        async with session.delete(f"{DATA_API_URL}/internal/devices/clear") as response:
            if response.status == 200:
                result = await response.json()
                print(f"✅ Cleared {result.get('devices_deleted', 0)} devices and {result.get('entities_deleted', 0)} entities")
                return True
            error_text = await response.text()
            print(f"❌ Failed to clear devices: {response.status} - {error_text}")
            return False
    except Exception as e:
        print(f"❌ Error clearing devices: {e}")
        return False

async def trigger_discovery(session: aiohttp.ClientSession) -> bool:
    """Trigger device discovery"""
    try:
        print("\n🔍 Triggering device discovery...")
        async with session.post(f"{WEBSOCKET_INGESTION_URL}/api/v1/discovery/trigger") as response:
            if response.status == 200:
                result = await response.json()
                if result.get("success"):
                    print("✅ Discovery triggered successfully")
                    print(f"   Devices discovered: {result.get('devices_discovered', 0)}")
                    print(f"   Entities discovered: {result.get('entities_discovered', 0)}")
                    return True
                print(f"❌ Discovery failed: {result.get('error', 'Unknown error')}")
                return False
            error_text = await response.text()
            print(f"❌ Failed to trigger discovery: {response.status} - {error_text}")
            return False
    except Exception as e:
        print(f"❌ Error triggering discovery: {e}")
        return False

async def main():
    """Main function"""
    print("=" * 80)
    print("🔄 Device Reload Script")
    print("=" * 80)
    print(f"Data API URL: {DATA_API_URL}")
    print(f"WebSocket Ingestion URL: {WEBSOCKET_INGESTION_URL}")
    print("=" * 80)

    connector = aiohttp.TCPConnector(ssl=False)
    timeout = aiohttp.ClientTimeout(total=60)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        # Step 1: Clear all devices
        if not await clear_devices(session):
            print("\n❌ Failed to clear devices. Aborting.")
            sys.exit(1)

        # Step 2: Wait a moment
        print("\n⏳ Waiting 2 seconds...")
        await asyncio.sleep(2)

        # Step 3: Trigger discovery
        if not await trigger_discovery(session):
            print("\n❌ Failed to trigger discovery.")
            sys.exit(1)

        print("\n" + "=" * 80)
        print("✅ Device reload complete!")
        print("=" * 80)
        print("\n💡 Tip: Check the dashboard at http://localhost:3000 to see the updated device count.")

if __name__ == "__main__":
    asyncio.run(main())

