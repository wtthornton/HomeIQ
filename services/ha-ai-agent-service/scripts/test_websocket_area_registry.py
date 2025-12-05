#!/usr/bin/env python3
"""Test WebSocket area registry directly"""

import asyncio
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from clients.ha_client import HomeAssistantClient
from config import Settings


async def test_websocket():
    """Test WebSocket area registry directly"""
    print("=" * 60)
    print("Testing WebSocket Area Registry API")
    print("=" * 60)
    
    settings = Settings()
    print(f"HA URL: {settings.ha_url}")
    print(f"Token: {settings.ha_token[:20]}...")
    print()
    
    client = HomeAssistantClient(
        ha_url=settings.ha_url,
        access_token=settings.ha_token
    )
    
    try:
        print("1. Testing WebSocket API directly...")
        areas = await client._get_area_registry_websocket()
        print(f"   ✅ WebSocket API returned {len(areas)} areas")
        if areas:
            for area in areas[:3]:
                print(f"      - {area.get('name')} (area_id: {area.get('area_id')})")
        return areas
    except Exception as e:
        print(f"   ❌ WebSocket API failed: {e}")
        print()
        print("2. Testing REST API fallback...")
        try:
            areas = await client.get_area_registry()
            print(f"   ✅ REST API returned {len(areas)} areas")
            return areas
        except Exception as e2:
            print(f"   ❌ REST API also failed: {e2}")
            return []
    finally:
        await client.close()


if __name__ == "__main__":
    result = asyncio.run(test_websocket())
    print()
    print("=" * 60)
    if result:
        print(f"✅ SUCCESS: Found {len(result)} areas")
    else:
        print("❌ FAILED: No areas found")
    print("=" * 60)

