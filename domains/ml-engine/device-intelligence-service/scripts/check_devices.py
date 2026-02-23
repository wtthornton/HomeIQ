"""Script to check device count in database."""
import asyncio

from sqlalchemy import text
from src.config import Settings
from src.core.database import get_db_session


async def check_devices():
    settings = Settings()

    # Import and initialize database
    from src.core.database import initialize_database
    await initialize_database(settings)

    # Now check count
    async for session in get_db_session():
        result = await session.execute(text('SELECT COUNT(*) FROM devices'))
        count = result.scalar()
        print(f'Devices in database: {count}')
        break

if __name__ == "__main__":
    asyncio.run(check_devices())

