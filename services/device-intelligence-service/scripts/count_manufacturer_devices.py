"""Script to count devices with manufacturer info."""
import asyncio
from sqlalchemy import text
from src.core.database import get_db_session, initialize_database
from src.config import Settings

async def count_manufacturer_devices():
    settings = Settings()
    await initialize_database(settings)
    
    async for session in get_db_session():
        # Count devices with known manufacturer
        result = await session.execute(text('''
            SELECT COUNT(*) FROM devices WHERE manufacturer != "Unknown" AND manufacturer IS NOT NULL
        '''))
        count_with_manufacturer = result.scalar()
        
        # Count devices with known model
        result = await session.execute(text('''
            SELECT COUNT(*) FROM devices WHERE model != "Unknown" AND model IS NOT NULL
        '''))
        count_with_model = result.scalar()
        
        # Count devices with known integration
        result = await session.execute(text('''
            SELECT COUNT(*) FROM devices WHERE integration != "unknown" AND integration IS NOT NULL
        '''))
        count_with_integration = result.scalar()
        
        # Total count
        result = await session.execute(text('SELECT COUNT(*) FROM devices'))
        total_count = result.scalar()
        
        print(f"Total devices: {total_count}")
        print(f"Devices with manufacturer: {count_with_manufacturer}")
        print(f"Devices with model: {count_with_model}")
        print(f"Devices with integration: {count_with_integration}")

if __name__ == "__main__":
    asyncio.run(count_manufacturer_devices())

