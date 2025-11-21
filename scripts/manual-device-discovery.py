#!/usr/bin/env python3
"""
Manual Device Discovery Script for HA Ingestor

This script manually queries Home Assistant's device and entity registries
and stores the results in the HA Ingestor SQLite database.

Use this when the automatic discovery process hangs or fails.
"""

import asyncio
import os
import sys
from datetime import datetime
from typing import Any

import aiohttp

# Configuration
HA_URL = os.getenv("HA_HTTP_URL", "http://192.168.1.86:8123")
HA_TOKEN = os.getenv("HA_TOKEN", "your_token_here")
DATA_API_URL = os.getenv("DATA_API_URL", "http://localhost:8006")

async def get_ha_devices(session: aiohttp.ClientSession) -> list[dict[str, Any]]:
    """Get all devices from Home Assistant device registry"""
    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    }

    url = f"{HA_URL}/api/config/device_registry/list"

    try:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                devices = await response.json()
                print(f"✅ Retrieved {len(devices)} devices from Home Assistant")
                return devices
            print(f"❌ Failed to get devices: {response.status}")
            return []
    except Exception as e:
        print(f"❌ Error getting devices: {e}")
        return []

async def get_ha_entities(session: aiohttp.ClientSession) -> list[dict[str, Any]]:
    """Get all entities from Home Assistant entity registry"""
    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    }

    url = f"{HA_URL}/api/config/entity_registry/list"

    try:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                entities = await response.json()
                print(f"✅ Retrieved {len(entities)} entities from Home Assistant")
                return entities
            print(f"❌ Failed to get entities: {response.status}")
            return []
    except Exception as e:
        print(f"❌ Error getting entities: {e}")
        return []

async def store_devices_to_ingestor(session: aiohttp.ClientSession, devices: list[dict[str, Any]]) -> bool:
    """Store devices to HA Ingestor SQLite database"""
    if not devices:
        return True

    try:
        async with session.post(
            f"{DATA_API_URL}/internal/devices/bulk_upsert",
            json=devices,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            if response.status == 200:
                result = await response.json()
                print(f"✅ Stored {result.get('upserted', 0)} devices to HA Ingestor")
                return True
            error_text = await response.text()
            print(f"❌ Failed to store devices: {response.status} - {error_text}")
            return False
    except Exception as e:
        print(f"❌ Error storing devices: {e}")
        return False

async def store_entities_to_ingestor(session: aiohttp.ClientSession, entities: list[dict[str, Any]]) -> bool:
    """Store entities to HA Ingestor SQLite database"""
    if not entities:
        return True

    try:
        async with session.post(
            f"{DATA_API_URL}/internal/entities/bulk_upsert",
            json=entities,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            if response.status == 200:
                result = await response.json()
                print(f"✅ Stored {result.get('upserted', 0)} entities to HA Ingestor")
                return True
            error_text = await response.text()
            print(f"❌ Failed to store entities: {response.status} - {error_text}")
            return False
    except Exception as e:
        print(f"❌ Error storing entities: {e}")
        return False

async def main():
    """Main discovery process"""
    print("=" * 80)
    print("🔍 MANUAL DEVICE DISCOVERY FOR HA INGESTOR")
    print("=" * 80)
    print(f"Home Assistant URL: {HA_URL}")
    print(f"Data API URL: {DATA_API_URL}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 80)

    # Create HTTP session
    connector = aiohttp.TCPConnector(ssl=False)
    timeout = aiohttp.ClientTimeout(total=60)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        # Get devices from Home Assistant
        print("📱 Fetching devices from Home Assistant...")
        devices = await get_ha_devices(session)

        # Get entities from Home Assistant
        print("🔌 Fetching entities from Home Assistant...")
        entities = await get_ha_entities(session)

        # Store devices to HA Ingestor
        if devices:
            print("💾 Storing devices to HA Ingestor...")
            await store_devices_to_ingestor(session, devices)

        # Store entities to HA Ingestor
        if entities:
            print("💾 Storing entities to HA Ingestor...")
            await store_entities_to_ingestor(session, entities)

        # Check for Inovelli devices
        inovelli_devices = [d for d in devices if "inovelli" in d.get("manufacturer", "").lower() or "inovelli" in d.get("name", "").lower()]
        if inovelli_devices:
            print("🎉 FOUND INOVELLI DEVICES:")
            for device in inovelli_devices:
                print(f"   - {device.get('name', 'Unknown')} ({device.get('manufacturer', 'Unknown')})")
        else:
            print("⚠️  No Inovelli devices found in Home Assistant device registry")

    print("=" * 80)
    print("✅ MANUAL DISCOVERY COMPLETE")
    print("=" * 80)
    print("Check your dashboard at http://localhost:3000/devices")

if __name__ == "__main__":
    # Check environment variables
    if HA_TOKEN == "your_token_here":
        print("❌ Please set HA_TOKEN environment variable")
        print("   Example: $env:HA_TOKEN='your_home_assistant_token'")
        sys.exit(1)

    asyncio.run(main())
