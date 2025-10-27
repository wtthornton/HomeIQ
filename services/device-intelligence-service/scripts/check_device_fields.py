"""Script to check device fields in database."""
import asyncio
from sqlalchemy import text
from src.core.database import get_db_session, initialize_database
from src.config import Settings

async def check_device_fields():
    settings = Settings()
    await initialize_database(settings)
    
    async for session in get_db_session():
        # Get sample devices with all fields
        result = await session.execute(text('''
            SELECT id, name, manufacturer, model, integration, area_name, 
                   device_class, sw_version, hw_version, power_source,
                   config_entry_id, zigbee_ieee, is_battery_powered
            FROM devices 
            LIMIT 5
        '''))
        
        devices = result.fetchall()
        
        if not devices:
            print("No devices found")
            return
        
        print(f"Sample devices ({len(devices)} shown):\n")
        for device in devices:
            print(f"ID: {device[0]}")
            print(f"  Name: {device[1]}")
            print(f"  Manufacturer: {device[2]}")
            print(f"  Model: {device[3]}")
            print(f"  Integration: {device[4]}")
            print(f"  Area: {device[5]}")
            print(f"  Device Class: {device[6]}")
            print(f"  SW Version: {device[7]}")
            print(f"  HW Version: {device[8]}")
            print(f"  Power Source: {device[9]}")
            print(f"  Config Entry ID: {device[10]}")
            print(f"  Zigbee IEEE: {device[11]}")
            print(f"  Is Battery Powered: {device[12]}")
            print()

if __name__ == "__main__":
    asyncio.run(check_device_fields())

