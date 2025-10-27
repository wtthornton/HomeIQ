#!/usr/bin/env python3
"""
Recreate Device Intelligence Service Database Tables

This script drops all existing tables and recreates them with the latest schema.
WARNING: This will delete all existing data in the database.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Settings
from src.core.database import initialize_database, recreate_tables

logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp":"%(asctime)s","level":"%(levelname)s","message":"%(message)s","service":"device-intelligence-recreate-db"}'
)
logger = logging.getLogger(__name__)


async def main():
    """Main function to recreate database tables."""
    logger.info("=" * 80)
    logger.info("DATABASE TABLE RECREATION SCRIPT")
    logger.info("WARNING: This will DELETE ALL existing data!")
    logger.info("=" * 80)
    
    # Load settings
    settings = Settings()
    
    # Initialize database connection
    logger.info("🔌 Connecting to database...")
    await initialize_database(settings)
    logger.info("✅ Database connected")
    
    # Recreate tables
    logger.info("")
    logger.info("🔄 Recreating database tables...")
    logger.info("⚠️  This will drop all existing tables and recreate them with the new schema")
    logger.info("")
    
    try:
        await recreate_tables()
        logger.info("")
        logger.info("=" * 80)
        logger.info("✅ DATABASE TABLES RECREATED SUCCESSFULLY")
        logger.info("=" * 80)
        logger.info("")
        logger.info("The following fields have been added to the devices table:")
        logger.info("  - device_class (device type)")
        logger.info("  - config_entry_id (HA config entry ID)")
        logger.info("  - connections_json (physical connections)")
        logger.info("  - identifiers_json (device identifiers)")
        logger.info("  - zigbee_ieee (IEEE address)")
        logger.info("  - is_battery_powered (power source indicator)")
        logger.info("")
        logger.info("Area name will now be stored for all devices.")
        logger.info("Integration field logic has been fixed.")
        logger.info("")
        logger.info("Next step: Run the discovery service to populate devices with the new fields.")
        logger.info("")
        
    except Exception as e:
        logger.error(f"")
        logger.error(f"=" * 80)
        logger.error(f"❌ FAILED TO RECREATE DATABASE TABLES")
        logger.error(f"=" * 80)
        logger.error(f"Error: {e}")
        logger.error(f"")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

