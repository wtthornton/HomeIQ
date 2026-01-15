"""
Update Zigbee2MQTT device integration field based on device names found in Zigbee2MQTT UI.

This script matches devices from the Zigbee2MQTT interface (found via Playwright)
with devices in the database and updates their integration field to "zigbee2mqtt".
"""

import asyncio
import aiohttp
import os
from typing import Dict, List, Optional

# Zigbee devices found in Zigbee2MQTT UI (from Playwright inspection)
ZIGBEE_DEVICES = [
    {"name": "Bar Light Switch", "ieee": "0x9035eafffec911ef", "model": "2-in-1 switch + dimmer"},
    {"name": "Office 4 Button Switch", "ieee": "0x90395efffe357b59", "model": "Wireless switch with 4 buttons"},
    {"name": "Office FP300 Sensor", "ieee": "0x54ef44100146c0f4", "model": "Presence sensor FP300"},
    {"name": "Bar PF300 Sensor", "ieee": "0x54ef44100146c22c", "model": "Presence sensor FP300"},
    {"name": "Office Fan Switch", "ieee": "0x048727fffe196715", "model": "Fan controller"},
    {"name": "Office Light Switch", "ieee": "0x9035eafffec90e8f", "model": "2-in-1 switch + dimmer"},
]

# Data API configuration
DATA_API_URL = os.getenv('DATA_API_URL', 'http://localhost:8006')
API_KEY = os.getenv('DATA_API_API_KEY') or os.getenv('DATA_API_KEY') or os.getenv('API_KEY')


async def update_device_integration(
    session: aiohttp.ClientSession,
    device_id: str,
    integration: str
) -> bool:
    """Update device integration field via data-api"""
    try:
        headers = {"Content-Type": "application/json"}
        if API_KEY:
            headers["Authorization"] = f"Bearer {API_KEY}"
        
        # Use internal bulk upsert endpoint with updated integration
        device_update = {
            "device_id": device_id,
            "integration": integration
        }
        
        # Note: bulk_upsert expects full device data, but we can use PATCH if available
        # For now, we'll get the device first, then update it
        async with session.patch(
            f"{DATA_API_URL}/api/devices/{device_id}",
            json={"integration": integration},
            headers=headers
        ) as response:
            if response.status in [200, 204]:
                return True
            elif response.status == 404:
                # PATCH endpoint might not exist, try alternative
                return False
            else:
                error_text = await response.text()
                print(f"  [WARN] Failed to update {device_id}: {response.status} - {error_text[:100]}")
                return False
    except Exception as e:
        print(f"  [FAIL] Error updating {device_id}: {e}")
        return False


def match_device_name(
    db_device_name: str, 
    zigbee_device_name: str, 
    db_model: str = None, 
    zigbee_model: str = None,
    db_manufacturer: str = None
) -> bool:
    """Check if device names match (case-insensitive, handles variations)"""
    db_name_lower = db_device_name.lower()
    zigbee_name_lower = zigbee_device_name.lower()
    db_model_lower = (db_model or "").lower()
    zigbee_model_lower = (zigbee_model or "").lower()
    
    # Exact match
    if db_name_lower == zigbee_name_lower:
        return True
    
    # Check if Zigbee name is contained in DB name (handles prefixes like "[TV]")
    if zigbee_name_lower in db_name_lower:
        return True
    
    # Check if DB name is contained in Zigbee name
    if db_name_lower in zigbee_name_lower:
        return True
    
    # Reject obvious mismatches (Hue Rooms, WLED, etc.)
    if "room" in db_model_lower or "wled" in db_manufacturer.lower() if db_manufacturer else False:
        return False
    
    # Check model match (more reliable than name)
    if db_model_lower and zigbee_model_lower:
        # FP300 Sensor matching - must have "presence" or "fp" in name AND "fp" in model
        if "fp300" in zigbee_model_lower or "presence sensor fp300" in zigbee_model_lower:
            if ("presence" in db_name_lower or "fp" in db_name_lower) and \
               ("fp" in db_model_lower or "presence" in db_model_lower):
                # Also match location if present
                if "office" in zigbee_name_lower and "office" not in db_name_lower:
                    return False
                if "bar" in zigbee_name_lower and "bar" not in db_name_lower:
                    return False
                return True
        
        # Switch matching - must have "switch" in both name and model
        if "switch" in zigbee_name_lower and "switch" in zigbee_model_lower:
            if "switch" not in db_name_lower and "switch" not in db_model_lower:
                return False
            # Check location match
            if "office" in zigbee_name_lower and "office" not in db_name_lower:
                return False
            if "bar" in zigbee_name_lower and "bar" not in db_name_lower:
                return False
            # Check switch type
            if "button" in zigbee_name_lower or "button" in zigbee_model_lower:
                if "button" not in db_name_lower and "button" not in db_model_lower:
                    return False
            if "light" in zigbee_name_lower and "light" not in db_name_lower:
                return False
            if "fan" in zigbee_name_lower and "fan" not in db_name_lower:
                return False
            if "dimmer" in zigbee_model_lower and "dimmer" not in db_model_lower:
                return False
            return True
        
        if "fan" in zigbee_model_lower:
            if "fan" not in db_name_lower and "fan" not in db_model_lower:
                return False
            if "office" in zigbee_name_lower and "office" not in db_name_lower:
                return False
            return True
    
    # Check if key words match (e.g., "Office", "Bar", "Switch", "Sensor", "FP", "Fan")
    db_words = set(db_name_lower.split())
    zigbee_words = set(zigbee_name_lower.split())
    
    # If at least 2 key words match, consider it a match
    common_words = db_words.intersection(zigbee_words)
    # Filter out common words like "the", "a", "and", etc.
    significant_words = {w for w in common_words if len(w) > 2}
    
    # Special handling for FP sensors
    if "fp" in db_name_lower and "fp" in zigbee_name_lower:
        if len(significant_words) >= 1:  # Lower threshold for FP sensors
            return True
    
    if len(significant_words) >= 2:
        return True
    
    return False


async def find_and_update_zigbee_devices():
    """Find Zigbee devices in database and update their integration field"""
    # Set UTF-8 encoding for Windows console (must be before any print with Unicode)
    import sys
    if sys.platform == "win32":
        import io
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
        except AttributeError:
            # Python < 3.7 - use environment variable only
            os.environ["PYTHONIOENCODING"] = "utf-8"
    
    print("[*] Finding and updating Zigbee2MQTT devices...")
    print(f"   Data API URL: {DATA_API_URL}")
    
    async with aiohttp.ClientSession() as session:
        # Get all devices from database
        headers = {}
        if API_KEY:
            headers["Authorization"] = f"Bearer {API_KEY}"
        
        try:
            async with session.get(
                f"{DATA_API_URL}/api/devices?limit=1000",
                headers=headers
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    print(f"[FAIL] Failed to get devices: {response.status} - {error_text[:200]}")
                    return
                
                data = await response.json()
                db_devices = data.get("devices", [])
                print(f"[OK] Found {len(db_devices)} devices in database")
        except Exception as e:
            print(f"[FAIL] Error fetching devices: {e}")
            return
        
        # Match Zigbee devices with database devices
        matched_count = 0
        updated_count = 0
        
        for zigbee_device in ZIGBEE_DEVICES:
            zigbee_name = zigbee_device["name"]
            print(f"\n[*] Looking for: {zigbee_name} (IEEE: {zigbee_device['ieee']})")
            
            # Find matching device in database
            matched_device = None
            for db_device in db_devices:
                db_name = db_device.get("name", "")
                
                # Check name match
                if match_device_name(db_name, zigbee_name):
                    matched_device = db_device
                    print(f"  ✅ Matched: {db_name} (device_id: {db_device.get('device_id')})")
                    break
            
            if matched_device:
                matched_count += 1
                device_id = matched_device.get("device_id")
                current_integration = matched_device.get("integration")
                
                if current_integration == "zigbee2mqtt":
                    print(f"  [INFO] Already marked as zigbee2mqtt, skipping")
                    continue
                
                # Update integration field
                print(f"  🔄 Updating integration from '{current_integration}' to 'zigbee2mqtt'...")
                
                # Use bulk upsert with full device data
                device_update = matched_device.copy()
                device_update["integration"] = "zigbee2mqtt"
                device_update["id"] = device_id  # HA uses 'id', we use 'device_id'
                
                try:
                    bulk_headers = {"Content-Type": "application/json"}
                    if API_KEY:
                        bulk_headers["Authorization"] = f"Bearer {API_KEY}"
                    
                    async with session.post(
                        f"{DATA_API_URL}/internal/devices/bulk_upsert",
                        json=[device_update],
                        headers=bulk_headers
                    ) as update_response:
                        if update_response.status == 200:
                            result = await update_response.json()
                            if result.get("success") or result.get("upserted", 0) > 0:
                                updated_count += 1
                                print(f"  [OK] Successfully updated integration field")
                            else:
                                print(f"  [WARN] Update returned success=False")
                        else:
                            error_text = await update_response.text()
                            print(f"  [FAIL] Failed to update: {update_response.status} - {error_text[:200]}")
                except Exception as e:
                    print(f"  [FAIL] Error updating device: {e}")
            else:
                print(f"  [WARN] No matching device found in database")
        
        print(f"\n[OK] Summary:")
        print(f"   Zigbee devices in UI: {len(ZIGBEE_DEVICES)}")
        print(f"   Devices matched: {matched_count}")
        print(f"   Devices updated: {updated_count}")
        
        if updated_count > 0:
            print(f"\n[*] Verification:")
            print(f"   Check devices: GET {DATA_API_URL}/api/devices?limit=1000")
            print(f"   Filter: devices with integration='zigbee2mqtt'")


if __name__ == "__main__":
    asyncio.run(find_and_update_zigbee_devices())
