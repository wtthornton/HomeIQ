#!/usr/bin/env python3
"""
HA Ingestor Device Comparison Test

This script compares devices from Home Assistant with devices stored in the HA Ingestor database.
It helps identify missing devices and synchronization issues.
"""

import asyncio
import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import aiohttp

# Configuration
HA_URL = os.getenv("HA_HTTP_URL", "http://192.168.1.86:8123")
HA_TOKEN = os.getenv("HA_TOKEN", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJmYzAxMTBmZGRiNzc0ZDNjYTJhNjg2Mjk5M2U3ZGE4MiIsImlhdCI6MTc2MDM5NjUwNSwiZXhwIjoyMDc1NzU2NTA1fQ.dngeB--Ov3TgE1iJR3VyL9tX-a99jTiiUxlrz467j1Q")
DATA_API_URL = os.getenv("DATA_API_URL", "http://localhost:8006")

@dataclass
class DeviceInfo:
    """Device information structure"""
    device_id: str
    name: str
    manufacturer: str = None
    model: str = None
    area_id: str = None
    entity_count: int = 0
    last_seen: str = None
    source: str = None  # 'ha' or 'db'

async def get_ha_devices(session: aiohttp.ClientSession) -> list[DeviceInfo]:
    """Get all devices from Home Assistant via REST API"""
    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    }

    devices = []

    try:
        # Get all states from Home Assistant
        async with session.get(f"{HA_URL}/api/states", headers=headers) as response:
            if response.status == 200:
                states = await response.json()

                # Group entities by device
                device_map = {}
                for state in states:
                    entity_id = state.get("entity_id", "")
                    attributes = state.get("attributes", {})

                    # Extract device information
                    device_id = attributes.get("device_id")
                    if not device_id:
                        continue

                    if device_id not in device_map:
                        device_map[device_id] = {
                            "device_id": device_id,
                            "name": attributes.get("friendly_name", "Unknown"),
                            "manufacturer": attributes.get("device_info", {}).get("manufacturer"),
                            "model": attributes.get("device_info", {}).get("model"),
                            "area_id": attributes.get("area_id"),
                            "entities": set(),
                        }

                    device_map[device_id]["entities"].add(entity_id)

                # Convert to DeviceInfo objects
                for device_data in device_map.values():
                    device = DeviceInfo(
                        device_id=device_data["device_id"],
                        name=device_data["name"],
                        manufacturer=device_data["manufacturer"],
                        model=device_data["model"],
                        area_id=device_data["area_id"],
                        entity_count=len(device_data["entities"]),
                        source="ha",
                    )
                    devices.append(device)

                print(f"✅ Retrieved {len(devices)} devices from Home Assistant")

            else:
                print(f"❌ Failed to get HA states: {response.status}")

    except Exception as e:
        print(f"❌ Error getting HA devices: {e}")

    return devices

async def get_db_devices(session: aiohttp.ClientSession) -> list[DeviceInfo]:
    """Get all devices from HA Ingestor database"""
    devices = []

    try:
        async with session.get(f"{DATA_API_URL}/api/devices") as response:
            if response.status == 200:
                data = await response.json()
                db_devices = data.get("devices", [])

                for device_data in db_devices:
                    device = DeviceInfo(
                        device_id=device_data.get("device_id", ""),
                        name=device_data.get("name", "Unknown"),
                        manufacturer=device_data.get("manufacturer"),
                        model=device_data.get("model"),
                        area_id=device_data.get("area_id"),
                        entity_count=device_data.get("entity_count", 0),
                        last_seen=device_data.get("timestamp"),
                        source="db",
                    )
                    devices.append(device)

                print(f"✅ Retrieved {len(devices)} devices from HA Ingestor database")

            else:
                print(f"❌ Failed to get DB devices: {response.status}")

    except Exception as e:
        print(f"❌ Error getting DB devices: {e}")

    return devices

def compare_devices(ha_devices: list[DeviceInfo], db_devices: list[DeviceInfo]) -> dict[str, Any]:
    """Compare devices between Home Assistant and database"""

    # Create sets for comparison
    ha_device_ids = {device.device_id for device in ha_devices}
    db_device_ids = {device.device_id for device in db_devices}

    # Find differences
    missing_in_db = ha_device_ids - db_device_ids
    extra_in_db = db_device_ids - ha_device_ids
    common_devices = ha_device_ids & db_device_ids

    # Create device maps for detailed comparison
    ha_device_map = {device.device_id: device for device in ha_devices}
    db_device_map = {device.device_id: device for device in db_devices}

    # Find devices with different information
    different_info = []
    for device_id in common_devices:
        ha_device = ha_device_map[device_id]
        db_device = db_device_map[device_id]

        differences = []
        if ha_device.name != db_device.name:
            differences.append(f"name: '{ha_device.name}' vs '{db_device.name}'")
        if ha_device.manufacturer != db_device.manufacturer:
            differences.append(f"manufacturer: '{ha_device.manufacturer}' vs '{db_device.manufacturer}'")
        if ha_device.model != db_device.model:
            differences.append(f"model: '{ha_device.model}' vs '{db_device.model}'")
        if ha_device.entity_count != db_device.entity_count:
            differences.append(f"entity_count: {ha_device.entity_count} vs {db_device.entity_count}")

        if differences:
            different_info.append({
                "device_id": device_id,
                "name": ha_device.name,
                "differences": differences,
            })

    return {
        "ha_count": len(ha_devices),
        "db_count": len(db_devices),
        "common_count": len(common_devices),
        "missing_in_db": list(missing_in_db),
        "extra_in_db": list(extra_in_db),
        "different_info": different_info,
        "ha_devices": ha_devices,
        "db_devices": db_devices,
    }

def print_comparison_report(comparison: dict[str, Any]):
    """Print a detailed comparison report"""

    print("=" * 80)
    print("📊 DEVICE COMPARISON REPORT")
    print("=" * 80)
    print(f"Home Assistant Devices: {comparison['ha_count']}")
    print(f"HA Ingestor DB Devices: {comparison['db_count']}")
    print(f"Common Devices: {comparison['common_count']}")
    print(f"Missing in DB: {len(comparison['missing_in_db'])}")
    print(f"Extra in DB: {len(comparison['extra_in_db'])}")
    print(f"Different Info: {len(comparison['different_info'])}")
    print("=" * 80)

    # Missing devices
    if comparison["missing_in_db"]:
        print("\n❌ DEVICES MISSING IN HA INGESTOR DATABASE:")
        print("-" * 50)
        ha_device_map = {device.device_id: device for device in comparison["ha_devices"]}
        for device_id in comparison["missing_in_db"]:
            device = ha_device_map[device_id]
            print(f"  • {device.name} ({device.device_id})")
            print(f"    Manufacturer: {device.manufacturer}")
            print(f"    Model: {device.model}")
            print(f"    Entities: {device.entity_count}")
            print()

    # Extra devices
    if comparison["extra_in_db"]:
        print("\n➕ DEVICES EXTRA IN HA INGESTOR DATABASE:")
        print("-" * 50)
        db_device_map = {device.device_id: device for device in comparison["db_devices"]}
        for device_id in comparison["extra_in_db"]:
            device = db_device_map[device_id]
            print(f"  • {device.name} ({device.device_id})")
            print(f"    Manufacturer: {device.manufacturer}")
            print(f"    Model: {device.model}")
            print(f"    Last Seen: {device.last_seen}")
            print()

    # Different information
    if comparison["different_info"]:
        print("\n🔄 DEVICES WITH DIFFERENT INFORMATION:")
        print("-" * 50)
        for device_info in comparison["different_info"]:
            print(f"  • {device_info['name']} ({device_info['device_id']})")
            for diff in device_info["differences"]:
                print(f"    - {diff}")
            print()

    # Inovelli devices check
    print("\n🔍 INOVELLI DEVICES CHECK:")
    print("-" * 50)

    inovelli_ha = [d for d in comparison["ha_devices"] if d.manufacturer and "inovelli" in d.manufacturer.lower()]
    inovelli_db = [d for d in comparison["db_devices"] if d.manufacturer and "inovelli" in d.manufacturer.lower()]

    print(f"Inovelli devices in HA: {len(inovelli_ha)}")
    for device in inovelli_ha:
        print(f"  • {device.name} ({device.device_id})")

    print(f"Inovelli devices in DB: {len(inovelli_db)}")
    for device in inovelli_db:
        print(f"  • {device.name} ({device.device_id})")

    if len(inovelli_ha) > len(inovelli_db):
        print(f"\n⚠️  {len(inovelli_ha) - len(inovelli_db)} Inovelli devices missing from HA Ingestor database!")

async def main():
    """Main comparison process"""
    print("=" * 80)
    print("🔍 HA INGESTOR DEVICE COMPARISON TEST")
    print("=" * 80)
    print(f"Home Assistant URL: {HA_URL}")
    print(f"Data API URL: {DATA_API_URL}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 80)

    # Create HTTP session
    connector = aiohttp.TCPConnector(ssl=False)
    timeout = aiohttp.ClientTimeout(total=60)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        # Get devices from both sources
        print("📱 Fetching devices from Home Assistant...")
        ha_devices = await get_ha_devices(session)

        print("💾 Fetching devices from HA Ingestor database...")
        db_devices = await get_db_devices(session)

        # Compare devices
        print("🔄 Comparing devices...")
        comparison = compare_devices(ha_devices, db_devices)

        # Print report
        print_comparison_report(comparison)

        # Save detailed report to file
        report_file = f"device_comparison_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, "w") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "ha_url": HA_URL,
                "data_api_url": DATA_API_URL,
                "comparison": {
                    "ha_count": comparison["ha_count"],
                    "db_count": comparison["db_count"],
                    "common_count": comparison["common_count"],
                    "missing_in_db": comparison["missing_in_db"],
                    "extra_in_db": comparison["extra_in_db"],
                    "different_info": comparison["different_info"],
                },
                "ha_devices": [
                    {
                        "device_id": d.device_id,
                        "name": d.name,
                        "manufacturer": d.manufacturer,
                        "model": d.model,
                        "area_id": d.area_id,
                        "entity_count": d.entity_count,
                    } for d in comparison["ha_devices"]
                ],
                "db_devices": [
                    {
                        "device_id": d.device_id,
                        "name": d.name,
                        "manufacturer": d.manufacturer,
                        "model": d.model,
                        "area_id": d.area_id,
                        "entity_count": d.entity_count,
                        "last_seen": d.last_seen,
                    } for d in comparison["db_devices"]
                ],
            }, f, indent=2)

        print(f"\n💾 Detailed report saved to: {report_file}")

    print("=" * 80)
    print("✅ DEVICE COMPARISON COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
