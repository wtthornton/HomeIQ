"""
Script to identify and update Zigbee2MQTT devices in the database.

This script queries Home Assistant directly to get device identifiers,
then identifies Zigbee devices and updates their integration field.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import aiohttp
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Import data-api models
data_api_src = project_root / "services" / "data-api" / "src"
sys.path.insert(0, str(data_api_src))
sys.path.insert(0, str(data_api_src.parent))

# Set up imports
import importlib.util
spec = importlib.util.spec_from_file_location("database", data_api_src / "database.py")
database_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(database_module)

spec = importlib.util.spec_from_file_location("device_model", data_api_src / "models" / "device.py")
device_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(device_module)

Device = device_module.Device
get_database_url = database_module.get_database_url


async def get_ha_devices(ha_url: str, ha_token: str) -> list[dict]:
    """Get devices from Home Assistant via WebSocket API (using HTTP fallback)"""
    try:
        # Try HTTP API first (may not exist in all HA versions)
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {ha_token}"}
            
            # Try device registry endpoint
            async with session.get(
                f"{ha_url}/api/config/device_registry/list",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("devices", [])
                elif response.status == 404:
                    print("⚠️  Device Registry HTTP API not available (404)")
                    return []
                else:
                    print(f"❌ HTTP API failed: {response.status}")
                    return []
    except Exception as e:
        print(f"❌ Error fetching devices from HA: {e}")
        return []


def is_zigbee_device(device: dict) -> bool:
    """Identify if a device is a Zigbee device based on identifiers"""
    identifiers = device.get("identifiers", [])
    
    for identifier in identifiers:
        identifier_str = str(identifier).lower()
        
        # Check for 'zigbee' or 'ieee' in identifier
        if 'zigbee' in identifier_str or 'ieee' in identifier_str:
            return True
        
        # Check for IEEE address pattern (0x followed by 8+ hex digits)
        if identifier_str.startswith('0x') and len(identifier_str) >= 10:
            try:
                int(identifier_str[2:], 16)
                return True
            except ValueError:
                pass
    
    # Check manufacturer/model for Zigbee patterns
    manufacturer = str(device.get("manufacturer", "")).lower()
    model = str(device.get("model", "")).lower()
    name = str(device.get("name", "")).lower()
    
    if "zigbee2mqtt" in manufacturer or ("bridge" in model and "zigbee" in name):
        return True
    
    return False


async def update_device_integrations():
    """Update device integration fields for Zigbee devices"""
    # Get HA connection info
    ha_url = os.getenv('HA_HTTP_URL') or os.getenv('HOME_ASSISTANT_URL', 'http://192.168.1.86:8123')
    ha_token = os.getenv('HA_TOKEN') or os.getenv('HOME_ASSISTANT_TOKEN')
    
    if not ha_token:
        print("❌ No HA token found. Set HA_TOKEN or HOME_ASSISTANT_TOKEN environment variable.")
        return
    
    # Normalize URL
    ha_url = ha_url.replace('ws://', 'http://').replace('wss://', 'https://').rstrip('/')
    
    print(f"🔍 Fetching devices from Home Assistant: {ha_url}")
    
    # Get devices from HA
    ha_devices = await get_ha_devices(ha_url, ha_token)
    
    if not ha_devices:
        print("⚠️  No devices found from Home Assistant")
        print("💡 Note: HTTP API endpoint may not exist. Try using WebSocket discovery instead.")
        return
    
    print(f"✅ Found {len(ha_devices)} devices from Home Assistant")
    
    # Connect to database
    database_url = get_database_url()
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    zigbee_count = 0
    updated_count = 0
    
    async with async_session() as session:
        # Process each HA device
        for ha_device in ha_devices:
            device_id = ha_device.get('id')
            if not device_id:
                continue
            
            # Check if it's a Zigbee device
            if is_zigbee_device(ha_device):
                zigbee_count += 1
                print(f"🔍 Identified Zigbee device: {ha_device.get('name', 'unknown')}")
                
                # Update database
                result = await session.execute(
                    update(Device)
                    .where(Device.device_id == device_id)
                    .values(integration="zigbee2mqtt")
                )
                
                if result.rowcount > 0:
                    updated_count += 1
                    print(f"  ✅ Updated integration to 'zigbee2mqtt'")
                else:
                    print(f"  ⚠️  Device not found in database: {device_id}")
        
        await session.commit()
    
    await engine.dispose()
    
    print(f"\n✅ Summary:")
    print(f"   Zigbee devices identified: {zigbee_count}")
    print(f"   Devices updated in database: {updated_count}")


if __name__ == "__main__":
    asyncio.run(update_device_integrations())
