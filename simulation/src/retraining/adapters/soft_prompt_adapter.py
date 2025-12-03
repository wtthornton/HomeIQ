"""
Soft Prompt Data Adapter

Converts simulation JSON data to format expected by Soft Prompt training script.
"""

import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class SoftPromptDataAdapter:
    """
    Adapter to prepare Soft Prompt training database from simulation JSON data.
    
    Converts JSON soft prompt data to ask_ai_queries database table.
    """
    
    def __init__(self, db_path: Path):
        """
        Initialize Soft Prompt data adapter.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"SoftPromptDataAdapter initialized: db_path={db_path}")
    
    def prepare_training_database(self, json_path: Path) -> Path:
        """
        Prepare training database from JSON data.
        
        Args:
            json_path: Path to soft_prompt_data.json
            
        Returns:
            Path to database
        """
        logger.info(f"Preparing Soft Prompt training database from {json_path}")
        
        # Load JSON data
        if not json_path.exists():
            raise FileNotFoundError(f"Soft prompt data not found: {json_path}")
        
        with open(json_path, "r", encoding="utf-8") as f:
            soft_prompt_data = json.load(f)
        
        logger.info(f"Loaded {len(soft_prompt_data)} soft prompt entries from JSON")
        
        # Create database and table
        self._create_table()
        
        # Populate database
        self._populate_database(soft_prompt_data)
        
        logger.info(f"✅ Soft Prompt training database prepared: {len(soft_prompt_data)} queries")
        
        return self.db_path
    
    def _create_table(self) -> None:
        """Create ask_ai_queries table if it doesn't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ask_ai_queries (
                    query_id TEXT PRIMARY KEY,
                    original_query TEXT NOT NULL,
                    user_id TEXT NOT NULL DEFAULT 'anonymous',
                    parsed_intent TEXT,
                    extracted_entities TEXT,
                    suggestions TEXT,
                    confidence REAL,
                    processing_time_ms INTEGER,
                    failure_reason TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create index on created_at for ordering
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS ix_ask_ai_queries_created_at 
                ON ask_ai_queries(created_at DESC)
            """)
            
            conn.commit()
            logger.info("✅ Created ask_ai_queries table")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to create table: {e}", exc_info=True)
            raise
        finally:
            conn.close()
    
    def _populate_database(self, soft_prompt_data: list[dict[str, Any]]) -> None:
        """
        Populate ask_ai_queries table from JSON data.
        
        Args:
            soft_prompt_data: List of soft prompt data entries
        """
        logger.info(f"Populating database with {len(soft_prompt_data)} queries...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Clear existing data (for fresh training)
            cursor.execute("DELETE FROM ask_ai_queries")
            
            # Insert queries
            inserted = 0
            for entry in soft_prompt_data:
                # Extract data (support multiple formats)
                query = entry.get("query") or entry.get("instruction") or ""
                
                # Handle suggestion format - check multiple locations
                suggestion_text = ""
                suggestion = entry.get("suggestion", {})
                response = entry.get("response", {})
                
                # Try to extract suggestion text from various locations
                if isinstance(suggestion, str) and suggestion.strip():
                    suggestion_text = suggestion
                elif isinstance(suggestion, dict):
                    suggestion_text = suggestion.get("description") or suggestion.get("text") or ""
                
                # If still empty, try response.text.description (from simulation format)
                if not suggestion_text and isinstance(response, dict):
                    text_data = response.get("text", {})
                    if isinstance(text_data, dict):
                        suggestion_text = text_data.get("description") or text_data.get("text") or ""
                    elif isinstance(text_data, str):
                        suggestion_text = text_data
                
                # If still empty, try response.description directly
                if not suggestion_text and isinstance(response, dict):
                    suggestion_text = response.get("description") or ""
                
                if not query or not suggestion_text:
                    logger.warning(f"Skipping entry with missing query or suggestion: query={bool(query)}, suggestion={bool(suggestion_text)}")
                    continue
                
                # Create suggestions array (training script expects JSON array)
                suggestions_array = [{
                    "description": suggestion_text,
                    "confidence": entry.get("quality_score", 0.8),
                    "automation_type": entry.get("automation_type", "automation")
                }]
                
                query_id = f"query-{uuid.uuid4().hex[:8]}"
                
                cursor.execute("""
                    INSERT INTO ask_ai_queries (
                        query_id, original_query, user_id, suggestions, confidence, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    query_id,
                    query,
                    "simulation",
                    json.dumps(suggestions_array),
                    entry.get("quality_score", 0.8),
                    datetime.now(timezone.utc).isoformat()
                ))
                
                inserted += 1
            
            conn.commit()
            logger.info(f"✅ Inserted {inserted} queries into database")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to populate database: {e}", exc_info=True)
            raise
        finally:
            conn.close()

