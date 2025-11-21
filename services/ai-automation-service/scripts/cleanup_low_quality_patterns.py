"""
Cleanup Low-Quality Patterns

Removes patterns that don't meet quality requirements:
- Non-actionable devices (sensors, events, images)
- Low occurrence counts (< 10)
- Low confidence (< 0.7)
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Import settings
from src.config import settings

# Import filters
from src.pattern_detection.pattern_filters import (
    MIN_CONFIDENCE,
    MIN_OCCURRENCES,
    is_actionable_device,
)


async def cleanup_patterns():
    """Clean up low-quality patterns from database"""

    # Create database connection
    database_url = getattr(settings, "database_url", "sqlite+aiosqlite:///./ai_automation.db")
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        try:
            # Get initial counts
            result = await db.execute(text("SELECT COUNT(*) FROM patterns"))
            initial_count = result.scalar()

            result = await db.execute(text("SELECT COUNT(DISTINCT device_id) FROM patterns"))
            initial_devices = result.scalar()

            print("Initial state:")
            print(f"  Total patterns: {initial_count}")
            print(f"  Unique devices: {initial_devices}")
            print()

            # Cleanup 1: Remove non-actionable devices
            print("Step 1: Removing non-actionable devices...")
            result = await db.execute(text("""
                SELECT device_id, COUNT(*) as count
                FROM patterns
                GROUP BY device_id
            """))
            all_devices = result.fetchall()

            removed_devices = 0
            for device_id, count in all_devices:
                if not is_actionable_device(device_id):
                    await db.execute(
                        text("DELETE FROM patterns WHERE device_id = :device_id"),
                        {"device_id": device_id},
                    )
                    removed_devices += count
                    print(f"  Removed {count} patterns for {device_id}")

            print(f"  Removed {removed_devices} patterns from non-actionable devices")
            print()

            # Cleanup 2: Remove low occurrences
            print("Step 2: Removing patterns with low occurrences...")
            result = await db.execute(
                text("DELETE FROM patterns WHERE occurrences < :min_occurrences"),
                {"min_occurrences": MIN_OCCURRENCES},
            )
            removed_low_occurrences = result.rowcount
            print(f"  Removed {removed_low_occurrences} patterns with < {MIN_OCCURRENCES} occurrences")
            print()

            # Cleanup 3: Remove low confidence
            print("Step 3: Removing patterns with low confidence...")
            result = await db.execute(
                text("DELETE FROM patterns WHERE confidence < :min_confidence"),
                {"min_confidence": MIN_CONFIDENCE},
            )
            removed_low_confidence = result.rowcount
            print(f"  Removed {removed_low_confidence} patterns with < {MIN_CONFIDENCE} confidence")
            print()

            # Commit all changes
            await db.commit()

            # Get final counts
            result = await db.execute(text("SELECT COUNT(*) FROM patterns"))
            final_count = result.scalar()

            result = await db.execute(text("SELECT COUNT(DISTINCT device_id) FROM patterns"))
            final_devices = result.scalar()

            result = await db.execute(text("""
                SELECT pattern_type, COUNT(*) as count
                FROM patterns
                GROUP BY pattern_type
                ORDER BY count DESC
            """))
            pattern_types = result.fetchall()

            print("Final state:")
            print(f"  Total patterns: {final_count} (removed {initial_count - final_count})")
            print(f"  Unique devices: {final_devices} (removed {initial_devices - final_devices})")
            print()
            print("Pattern types:")
            for pattern_type, count in pattern_types:
                print(f"  {pattern_type}: {count}")

            print()
            print("✅ Cleanup complete!")

        except Exception as e:
            await db.rollback()
            print(f"❌ Error during cleanup: {e}")
            raise
        finally:
            await engine.dispose()

if __name__ == "__main__":
    asyncio.run(cleanup_patterns())

