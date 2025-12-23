"""
Database Migration: Add 2025 Enhancement Fields to Synergy Opportunities

Phase 3.3: Update database schema
- Add explanation JSON field to synergy_opportunities
- Add context_breakdown JSON field to synergy_opportunities
- Create synergy_feedback table for RL feedback loop

Epic 39: Pattern Improvements Implementation
"""

import asyncio
import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)


async def add_2025_synergy_fields(db_path: str) -> None:
    """
    Add 2025 enhancement fields to synergy_opportunities table.
    
    Args:
        db_path: Path to SQLite database file
    """
    logger.info(f"Adding 2025 enhancement fields to database: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if explanation column exists
        cursor.execute("""
            SELECT COUNT(*) FROM pragma_table_info('synergy_opportunities') 
            WHERE name = 'explanation'
        """)
        has_explanation = cursor.fetchone()[0] > 0
        
        # Check if context_breakdown column exists
        cursor.execute("""
            SELECT COUNT(*) FROM pragma_table_info('synergy_opportunities') 
            WHERE name = 'context_breakdown'
        """)
        has_context_breakdown = cursor.fetchone()[0] > 0
        
        # Add explanation column if missing
        if not has_explanation:
            logger.info("Adding 'explanation' column to synergy_opportunities")
            cursor.execute("""
                ALTER TABLE synergy_opportunities 
                ADD COLUMN explanation TEXT
            """)
            logger.info("✅ Added 'explanation' column")
        else:
            logger.info("✅ 'explanation' column already exists")
        
        # Add context_breakdown column if missing
        if not has_context_breakdown:
            logger.info("Adding 'context_breakdown' column to synergy_opportunities")
            cursor.execute("""
                ALTER TABLE synergy_opportunities 
                ADD COLUMN context_breakdown TEXT
            """)
            logger.info("✅ Added 'context_breakdown' column")
        else:
            logger.info("✅ 'context_breakdown' column already exists")
        
        # Check if synergy_feedback table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='synergy_feedback'
        """)
        has_feedback_table = cursor.fetchone() is not None
        
        # Create synergy_feedback table if missing
        if not has_feedback_table:
            logger.info("Creating 'synergy_feedback' table")
            cursor.execute("""
                CREATE TABLE synergy_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    synergy_id VARCHAR(36) NOT NULL,
                    feedback_type VARCHAR(20) NOT NULL,
                    feedback_data TEXT NOT NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (synergy_id) REFERENCES synergy_opportunities(synergy_id)
                )
            """)
            
            # Create indexes
            cursor.execute("""
                CREATE INDEX idx_synergy_feedback_synergy_id 
                ON synergy_feedback(synergy_id)
            """)
            cursor.execute("""
                CREATE INDEX idx_synergy_feedback_type 
                ON synergy_feedback(feedback_type)
            """)
            cursor.execute("""
                CREATE INDEX idx_synergy_feedback_created_at 
                ON synergy_feedback(created_at)
            """)
            
            logger.info("✅ Created 'synergy_feedback' table with indexes")
        else:
            logger.info("✅ 'synergy_feedback' table already exists")
        
        conn.commit()
        logger.info("✅ Database migration completed successfully")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Database migration failed: {e}", exc_info=True)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    import sys
    
    # Get database path from command line or use default
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        # Default: look for database in common locations
        possible_paths = [
            "data/homeiq.db",
            "../ai-automation-service/data/homeiq.db",
            "../../ai-automation-service/data/homeiq.db"
        ]
        
        db_path = None
        for path in possible_paths:
            if Path(path).exists():
                db_path = path
                break
        
        if not db_path:
            logger.error("Database not found. Please provide path as argument.")
            sys.exit(1)
    
    logging.basicConfig(level=logging.INFO)
    asyncio.run(add_2025_synergy_fields(db_path))

