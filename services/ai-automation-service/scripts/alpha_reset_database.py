#!/usr/bin/env python3
"""
Alpha Database Reset Script - Story AI1.23
==========================================

Resets the SQLite database for conversational automation system.

⚠️ WARNING: This will DELETE the entire database!
This is acceptable in Alpha but should NOT be used in production.

What this does:
1. Stops ai-automation-service (you must do this manually)
2. Deletes data/ai_automation.db
3. Recreates database with new schema (via SQLAlchemy)
4. Verifies new schema has conversational fields

Usage:
    # 1. Stop service first!
    docker-compose stop ai-automation-service
    
    # 2. Run this script
    python scripts/alpha_reset_database.py
    
    # 3. Restart service
    docker-compose up -d ai-automation-service
    
    # 4. Reprocess patterns
    python scripts/reprocess_patterns.py
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent / "src"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "data" / "ai_automation.db"


def confirm_deletion():
    """Ask user to confirm database deletion"""
    print("="*80)
    print("⚠️  ALPHA DATABASE RESET - Story AI1.23")
    print("="*80)
    print("")
    print(f"This will DELETE: {DB_PATH}")
    print("")
    print("The database will be recreated with new conversational automation schema:")
    print("  ✅ description_only - Human-readable description")
    print("  ✅ conversation_history - Edit history (JSON)")
    print("  ✅ device_capabilities - Cached features (JSON)")
    print("  ✅ refinement_count - Number of edits")
    print("  ✅ status - draft|refining|yaml_generated|deployed|rejected")
    print("  ✅ yaml_generated_at - Timestamp of YAML creation")
    print("")
    print("All existing suggestions will be LOST!")
    print("")

    response = input("Type 'yes' to continue or anything else to cancel: ")
    return response.lower() == 'yes'


async def reset_database():
    """Reset the database"""

    # Check if database exists
    db_exists = DB_PATH.exists()

    if db_exists:
        logger.info(f"📁 Found existing database: {DB_PATH}")
        logger.info(f"📊 Size: {DB_PATH.stat().st_size / 1024:.2f} KB")

        # Delete database file
        logger.info("🗑️  Deleting database...")
        DB_PATH.unlink()
        logger.info("✅ Database deleted")
    else:
        logger.info(f"ℹ️  No existing database found at {DB_PATH}")

    # Ensure data directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Import and initialize database (creates new schema)
    logger.info("🔨 Creating new database with conversational schema...")

    from database.models import Suggestion, init_db

    await init_db()

    logger.info("✅ Database created successfully")

    # Verify schema
    logger.info("🔍 Verifying new schema...")

    # Check that Suggestion model has new fields
    suggestion_fields = [c.name for c in Suggestion.__table__.columns]

    required_fields = [
        'description_only',
        'conversation_history',
        'device_capabilities',
        'refinement_count',
        'yaml_generated_at',
        'approved_at'
    ]

    missing_fields = [f for f in required_fields if f not in suggestion_fields]

    if missing_fields:
        logger.error(f"❌ Schema validation failed! Missing fields: {missing_fields}")
        logger.error("   The model might not be updated correctly.")
        return False

    logger.info("✅ Schema validation passed")
    logger.info(f"   Found {len(suggestion_fields)} columns in suggestions table")
    logger.info(f"   Key fields: {', '.join(required_fields)}")

    return True


async def main():
    """Main execution"""
    logger.info("")
    logger.info("="*80)
    logger.info("🔬 ALPHA DATABASE RESET - Conversational Automation System")
    logger.info("="*80)
    logger.info("")

    # Confirm with user
    if not confirm_deletion():
        logger.info("❌ Reset cancelled by user")
        return

    logger.info("")
    logger.info("🚀 Starting database reset...")
    logger.info("")

    # Reset database
    success = await reset_database()

    if not success:
        logger.error("")
        logger.error("="*80)
        logger.error("❌ Database reset FAILED")
        logger.error("="*80)
        logger.error("")
        sys.exit(1)

    # Success message
    logger.info("")
    logger.info("="*80)
    logger.info("✅ DATABASE RESET COMPLETE")
    logger.info("="*80)
    logger.info("")
    logger.info("Next steps:")
    logger.info("")
    logger.info("  1. Restart ai-automation-service:")
    logger.info("     docker-compose up -d ai-automation-service")
    logger.info("")
    logger.info("  2. Reprocess patterns to generate suggestions:")
    logger.info("     python scripts/reprocess_patterns.py")
    logger.info("")
    logger.info("  3. Verify suggestions created:")
    logger.info("     curl http://localhost:8018/api/v1/suggestions | jq")
    logger.info("")
    logger.info("  4. Open UI to see new conversational interface:")
    logger.info("     http://localhost:3001/suggestions")
    logger.info("")
    logger.info("="*80)
    logger.info("")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
    except Exception as e:
        logger.error(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

