#!/usr/bin/env python3
"""Check HA API directly for device names"""
import asyncio
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()

HA_URL = os.getenv('HA_URL', 'http://192.168.1.86:8123')
HA_TOKEN = os.getenv('HA_TOKEN', '')

async def check_ha_api():
    headers = {"Authorization": f"Bearer {HA_TOKEN}", "Content-Type": "application/json"}
    
    async with aiohttp.ClientSession() as session:
        # Check device registry via WebSocket API (simulated via HTTP)
        print("=" * 120)
        print("CHECKING HA DEVICE REGISTRY")
        print("=" * 120)
        
        # Try to get devices via REST API (if available)
        try:
            async with session.get(
                f"{HA_URL}/api/config/device_registry/list",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    devices = await response.json()
                    print(f"✅ Got {len(devices)} devices via HTTP API")
                    # Filter Hue devices
                    hue_devices = [d for d in devices if 'hue' in str(d.get('manufacturer', '')).lower() or 'hue' in str(d.get('name', '')).lower()]
                    print(f"\nFound {len(hue_devices)} Hue devices:")
                    for device in hue_devices[:10]:
                        device_id = device.get('id', '')
                        name = device.get('name', '')
                        name_by_user = device.get('name_by_user', '')
                        area_id = device.get('area_id', '')
                        print(f"  {device_id}: name='{name}', name_by_user='{name_by_user}', area_id='{area_id}'")
                else:
                    print(f"[FAIL] HTTP API returned {response.status}")
        except Exception as e:
            print(f"[ERROR] HTTP API error: {e}")
        
        print("\n" + "=" * 120)
        print("CHECKING HA ENTITY REGISTRY")
        print("=" * 120)
        
        # Check entity registry
        try:
            async with session.get(
                f"{HA_URL}/api/config/entity_registry/list",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    entities = await response.json()
                    print(f"[OK] Got {len(entities)} entities via HTTP API")
                    # Filter Hue entities
                    hue_entities = [e for e in entities if 'hue' in str(e.get('entity_id', '')).lower()]
                    print(f"\nFound {len(hue_entities)} Hue entities:")
                    for entity in hue_entities[:10]:
                        entity_id = entity.get('entity_id', '')
                        name = entity.get('name', '')
                        name_by_user = entity.get('name_by_user', '')
                        device_id = entity.get('device_id', '')
                        print(f"  {entity_id}: name='{name}', name_by_user='{name_by_user}', device_id='{device_id}'")
                else:
                    print(f"[FAIL] HTTP API returned {response.status}")
        except Exception as e:
            print(f"[ERROR] HTTP API error: {e}")
        
        print("\n" + "=" * 120)
        print("CHECKING DATA-API DEVICES ENDPOINT")
        print("=" * 120)
        
        # Check what data-api returns
        try:
            async with session.get(
                "http://localhost:8006/api/devices",
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    devices = await response.json()
                    if isinstance(devices, dict):
                        devices = devices.get('devices', devices.get('data', []))
                    print(f"✅ Data-API returned {len(devices)} devices")
                    hue_devices = [d for d in devices if 'hue' in str(d.get('manufacturer', '')).lower() or 'hue' in str(d.get('name', '')).lower() or 'hue' in str(d.get('device_id', '')).lower()]
                    print(f"\nFound {len(hue_devices)} Hue devices in data-api:")
                    for device in hue_devices[:10]:
                        device_id = device.get('device_id', device.get('id', ''))
                        name = device.get('name', '')
                        name_by_user = device.get('name_by_user', '')
                        print(f"  {device_id}: name='{name}', name_by_user='{name_by_user}'")
                else:
                    print(f"[FAIL] Data-API returned {response.status}")
        except Exception as e:
            print(f"[ERROR] Data-API error: {e}")

if __name__ == "__main__":
    asyncio.run(check_ha_api())

