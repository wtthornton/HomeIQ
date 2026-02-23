"""
Database Migration Script: Add Zigbee2MQTT Fields

This script adds new Zigbee2MQTT-specific fields to the devices table
and creates the zigbee_device_metadata table.

Usage:
    python scripts/migrate_add_zigbee_fields.py
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path to import from src
script_dir = Path(__file__).parent
service_dir = script_dir.parent
sys.path.insert(0, str(service_dir))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.config import Settings
from src.core.database import get_database_url

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def migrate():
    """Run database migration."""
    settings = Settings()
    database_url = get_database_url(settings)
    
    logger.info(f"📊 Connecting to database: {database_url}")
    engine = create_async_engine(database_url, echo=False)
    
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        try:
            # Add new columns to devices table
            logger.info("🔄 Adding Zigbee2MQTT fields to devices table...")
            
            # Check which columns already exist
            logger.info("🔍 Checking existing columns...")
            check_sql = "PRAGMA table_info(devices);"
            result = await session.execute(text(check_sql))
            existing_columns = {row[1] for row in result.fetchall()}
            
            # Add Zigbee2MQTT fields to devices table (only if they don't exist)
            columns_to_add = [
                ("lqi", "INTEGER"),
                ("lqi_updated_at", "DATETIME"),
                ("availability_status", "TEXT"),
                ("availability_updated_at", "DATETIME"),
                ("battery_level", "INTEGER"),
                ("battery_low", "BOOLEAN"),
                ("battery_updated_at", "DATETIME"),
                ("device_type", "TEXT"),
                ("source", "TEXT"),
            ]
            
            for column_name, column_type in columns_to_add:
                if column_name not in existing_columns:
                    logger.info(f"  Adding column: {column_name}")
                    await session.execute(text(f"ALTER TABLE devices ADD COLUMN {column_name} {column_type};"))
                else:
                    logger.info(f"  Column already exists: {column_name}")
            
            await session.commit()
            
            # Create indexes for new fields (execute one at a time for SQLite)
            logger.info("🔍 Creating indexes...")
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_devices_lqi ON devices(lqi);",
                "CREATE INDEX IF NOT EXISTS idx_devices_availability_status ON devices(availability_status);",
                "CREATE INDEX IF NOT EXISTS idx_devices_battery_low ON devices(battery_low);",
                "CREATE INDEX IF NOT EXISTS idx_devices_source ON devices(source);",
            ]
            
            for index_sql in indexes:
                await session.execute(text(index_sql))
            
            await session.commit()
            logger.info("✅ Added Zigbee2MQTT fields to devices table")
            
            # Create zigbee_device_metadata table
            logger.info("🔄 Creating zigbee_device_metadata table...")
            
            metadata_table_sql = """
            CREATE TABLE IF NOT EXISTS zigbee_device_metadata (
                device_id TEXT PRIMARY KEY,
                ieee_address TEXT UNIQUE NOT NULL,
                model_id TEXT,
                manufacturer_code TEXT,
                date_code TEXT,
                hardware_version TEXT,
                software_build_id TEXT,
                network_address INTEGER,
                supported BOOLEAN DEFAULT 1,
                interview_completed BOOLEAN DEFAULT 0,
                definition_json TEXT,
                settings_json TEXT,
                last_seen_zigbee DATETIME,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
            );
            """
            
            await session.execute(text(metadata_table_sql))
            await session.commit()
            
            # Create index for metadata table (execute separately)
            logger.info("🔍 Creating metadata table index...")
            metadata_index_sql = "CREATE INDEX IF NOT EXISTS idx_zigbee_metadata_ieee_address ON zigbee_device_metadata(ieee_address);"
            await session.execute(text(metadata_index_sql))
            await session.commit()
            logger.info("✅ Created zigbee_device_metadata table")
            
            logger.info("🎉 Migration completed successfully!")
            
        except Exception as e:
            await session.rollback()
            logger.error(f"❌ Migration failed: {e}")
            raise
        finally:
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(migrate())

