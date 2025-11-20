"""Script to find devices with real manufacturer data."""
import asyncio

from sqlalchemy import text
from src.config import Settings
from src.core.database import get_db_session, initialize_database


async def find_real_devices():
    settings = Settings()
    await initialize_database(settings)

    async for session in get_db_session():
        # Find devices with connections or identifiers (real hardware devices)
        result = await session.execute(text('''
            SELECT id, name, manufacturer, model, integration, area_name, 
                   config_entry_id, connections_json, identifiers_json
            FROM devices 
            WHERE connections_json IS NOT NULL OR identifiers_json IS NOT NULL
            LIMIT 10
        '''))

        devices = result.fetchall()

        print(f"Found {len(devices)} devices with connections/identifiers:\n")

        for device in devices:
            print(f"Name: {device[1]}")
            print(f"  Manufacturer: {device[2]}")
            print(f"  Model: {device[3]}")
            print(f"  Integration: {device[4]}")
            print(f"  Area: {device[5]}")
            print(f"  Config Entry: {device[6]}")
            print(f"  Connections: {device[7]}")
            print(f"  Identifiers: {device[8]}")
            print()

if __name__ == "__main__":
    asyncio.run(find_real_devices())

