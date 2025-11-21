"""Check patterns and synergies in database"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from src.config import settings


async def check():
    database_url = getattr(settings, "database_url", "sqlite+aiosqlite:///./ai_automation.db")
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # Pattern types
        result = await db.execute(text("SELECT pattern_type, COUNT(*) as count FROM patterns GROUP BY pattern_type ORDER BY count DESC"))
        print("\n=== Pattern Types ===")
        for row in result.all():
            print(f"  {row[0]}: {row[1]}")

        # Total patterns
        result = await db.execute(text("SELECT COUNT(*) FROM patterns"))
        total = result.scalar_one()
        print(f"\nTotal patterns: {total}")

        # Synergies
        result = await db.execute(text("SELECT COUNT(*) FROM synergy_opportunities"))
        synergies = result.scalar_one()
        print(f"\nTotal synergies: {synergies}")

        # Sample patterns
        result = await db.execute(text("SELECT pattern_type, device_id, occurrences, confidence FROM patterns LIMIT 20"))
        print("\n=== Sample Patterns (first 20) ===")
        for row in result.all():
            print(f"  {row[0]}: {row[1]} (occ={row[2]}, conf={row[3]:.2f})")

        # Patterns by device domain
        result = await db.execute(text("""
            SELECT
                SUBSTR(device_id, 1, INSTR(device_id || '.', '.') - 1) as domain,
                COUNT(*) as count
            FROM patterns
            GROUP BY domain
            ORDER BY count DESC
            LIMIT 20
        """))
        print("\n=== Patterns by Device Domain (top 20) ===")
        for row in result.all():
            print(f"  {row[0]}: {row[1]}")

if __name__ == "__main__":
    asyncio.run(check())

