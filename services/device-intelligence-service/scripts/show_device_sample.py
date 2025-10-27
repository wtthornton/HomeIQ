"""Script to show a sample of devices from the database with raw data."""
import asyncio
from sqlalchemy import text
from src.core.database import get_db_session, initialize_database
from src.config import Settings

async def show_device_sample():
    settings = Settings()
    await initialize_database(settings)
    
    async for session in get_db_session():
        # Get ALL device fields
        result = await session.execute(text('''
            SELECT id, name, manufacturer, model, integration, area_id, area_name,
                   device_class, sw_version, hw_version, power_source, via_device_id,
                   config_entry_id, connections_json, identifiers_json, zigbee_ieee, is_battery_powered
            FROM devices 
            LIMIT 10
        '''))
        
        devices = result.fetchall()
        
        if not devices:
            print("No devices found")
            return
        
        print(f"Sample of {len(devices)} devices from database:\n")
        
        for idx, device in enumerate(devices, 1):
            print(f"\n{'='*80}")
            print(f"DEVICE {idx}:")
            print(f"{'='*80}")
            print(f"ID:                 {device[0]}")
            print(f"Name:               {device[1]}")
            print(f"Manufacturer:       {device[2]}")
            print(f"Model:              {device[3]}")
            print(f"Integration:        {device[4]}")
            print(f"Area ID:            {device[5]}")
            print(f"Area Name:          {device[6]}")
            print(f"Device Class:       {device[7]}")
            print(f"SW Version:         {device[8]}")
            print(f"HW Version:         {device[9]}")
            print(f"Power Source:       {device[10]}")
            print(f"Via Device ID:      {device[11]}")
            print(f"Config Entry ID:    {device[12]}")
            print(f"Connections JSON:   {device[13]}")
            print(f"Identifiers JSON:   {device[14]}")
            print(f"Zigbee IEEE:        {device[15]}")
            print(f"Is Battery Powered: {device[16]}")

if __name__ == "__main__":
    asyncio.run(show_device_sample())

