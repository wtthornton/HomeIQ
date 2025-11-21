#!/usr/bin/env python3
"""
Test HTTP API discovery to verify it works correctly.
This script tests the discovery functionality directly without requiring the service to be running.
"""
import asyncio
import os
import sys

import aiohttp
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

load_dotenv()

HA_URL = os.getenv("HA_HTTP_URL") or os.getenv("HOME_ASSISTANT_URL", "http://192.168.1.86:8123")
HA_TOKEN = os.getenv("HA_TOKEN") or os.getenv("HOME_ASSISTANT_TOKEN")
DATA_API_URL = os.getenv("DATA_API_URL", "http://localhost:8006")
DATA_API_KEY = os.getenv("DATA_API_API_KEY") or os.getenv("DATA_API_KEY") or os.getenv("API_KEY")

async def test_http_discovery():
    """Test HTTP API discovery for devices and entities"""

    # Normalize URL
    ha_url = HA_URL.replace("ws://", "http://").replace("wss://", "https://").rstrip("/")

    if not HA_TOKEN:
        print("ERROR: No HA token available")
        return False

    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    }

    print("=" * 80)
    print("TESTING HTTP API DISCOVERY")
    print("=" * 80)
    print(f"HA URL: {ha_url}")
    print(f"Data API URL: {DATA_API_URL}")
    print()

    async with aiohttp.ClientSession() as session:
        # Test device discovery
        print("1. Testing Device Discovery...")
        try:
            async with session.get(
                f"{ha_url}/api/config/device_registry/list",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status == 200:
                    devices = await response.json()
                    if isinstance(devices, dict):
                        devices = devices.get("devices", devices.get("result", []))
                    print(f"   [OK] SUCCESS: Retrieved {len(devices)} devices")
                    if devices:
                        sample = devices[0]
                        print(f"   Sample device: {sample.get('name', 'Unknown')} (ID: {sample.get('id', 'Unknown')})")
                else:
                    error_text = await response.text()
                    print(f"   [FAIL] FAILED: HTTP {response.status} - {error_text}")
                    return False
        except Exception as e:
            print(f"   [ERROR] ERROR: {e}")
            return False

        print()

        # Test entity discovery
        print("2. Testing Entity Discovery...")
        try:
            async with session.get(
                f"{ha_url}/api/config/entity_registry/list",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status == 200:
                    entities = await response.json()
                    if isinstance(entities, dict):
                        entities = entities.get("entities", entities.get("result", []))
                    print(f"   [OK] SUCCESS: Retrieved {len(entities)} entities")

                    # Check for name fields
                    if entities:
                        sample = entities[0]
                        print(f"   Sample entity: {sample.get('entity_id', 'Unknown')}")
                        print(f"   name: {sample.get('name')}")
                        print(f"   name_by_user: {sample.get('name_by_user')}")
                        print(f"   original_name: {sample.get('original_name')}")

                        # Count entities with name fields
                        with_names = sum(1 for e in entities if e.get("name") or e.get("name_by_user") or e.get("original_name"))
                        print(f"   Entities with name fields: {with_names}/{len(entities)}")

                        # Check Hue entities
                        hue_entities = [e for e in entities if "hue" in e.get("entity_id", "").lower()]
                        print(f"   Hue entities found: {len(hue_entities)}")
                        if hue_entities:
                            print("   Sample Hue entities:")
                            for entity in hue_entities[:5]:
                                eid = entity.get("entity_id", "Unknown")
                                name = entity.get("name", "")
                                name_by_user = entity.get("name_by_user", "")
                                print(f"      {eid}: name={name}, name_by_user={name_by_user}")
                else:
                    error_text = await response.text()
                    print(f"   [FAIL] FAILED: HTTP {response.status} - {error_text}")
                    return False
        except Exception as e:
            print(f"   [ERROR] ERROR: {e}")
            return False

        print()

        # Test storing entities via data-api
        print("3. Testing Entity Storage via data-api...")
        if entities:
            try:
                api_headers = {"Content-Type": "application/json"}
                if DATA_API_KEY:
                    api_headers["Authorization"] = f"Bearer {DATA_API_KEY}"

                async with session.post(
                    f"{DATA_API_URL}/internal/entities/bulk_upsert",
                    json=entities,
                    headers=api_headers,
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as api_response:
                    if api_response.status == 200:
                        result = await api_response.json()
                        upserted = result.get("upserted", 0)
                        print(f"   [OK] SUCCESS: Stored {upserted} entities to database")
                        return True
                    error_text = await api_response.text()
                    print(f"   [FAIL] FAILED: HTTP {api_response.status} - {error_text}")
                    return False
            except Exception as e:
                print(f"   [ERROR] ERROR: {e}")
                import traceback
                print(traceback.format_exc())
                return False
        else:
            print("   [SKIP] SKIPPED: No entities to store")
            return False

    print()
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    return True

if __name__ == "__main__":
    success = asyncio.run(test_http_discovery())
    sys.exit(0 if success else 1)

