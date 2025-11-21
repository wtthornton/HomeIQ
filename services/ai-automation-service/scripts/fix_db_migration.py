"""Quick fix for missing database columns"""
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from src.config import settings

async def migrate():
    engine = create_async_engine(settings.database_url, echo=False)
    try:
        async with engine.begin() as conn:
            await conn.execute(text("ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS enable_qa_learning BOOLEAN DEFAULT TRUE"))
            await conn.execute(text("ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS preference_consistency_threshold REAL DEFAULT 0.9"))
            await conn.execute(text("ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS min_questions_for_preference INTEGER DEFAULT 3"))
            await conn.execute(text("ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS learning_retrain_frequency VARCHAR DEFAULT 'weekly'"))
            print("✅ Migration complete - columns added")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(migrate())

