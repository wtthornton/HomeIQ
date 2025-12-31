"""
Database Accessor for Quality Evaluation

Handles database connections and queries for patterns and synergies.
"""

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DatabaseAccessor:
    """Handles database access for patterns and synergies."""
    
    def __init__(self, db_path: str):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {db_path}")
        
        self.conn: Optional[sqlite3.Connection] = None
        logger.info(f"Initialized database accessor for {db_path}")
    
    def _table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the database."""
        if self.conn is None:
            self.conn = sqlite3.connect(str(self.db_path))
            self.conn.row_factory = sqlite3.Row
        
        try:
            cursor = self.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,)
            )
            return cursor.fetchone() is not None
        except sqlite3.Error:
            return False
    
    async def get_all_patterns(
        self,
        pattern_type: Optional[str] = None,
        device_id: Optional[str] = None,
        min_confidence: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all patterns with optional filters.
        
        Args:
            pattern_type: Filter by pattern type
            device_id: Filter by device ID
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of pattern dictionaries
        """
        if self.conn is None:
            self.conn = sqlite3.connect(str(self.db_path))
            self.conn.row_factory = sqlite3.Row
        
        # Check if table exists
        if not self._table_exists('patterns'):
            logger.warning("Table 'patterns' does not exist in database")
            return []
        
        query = "SELECT * FROM patterns WHERE 1=1"
        params = []
        
        if pattern_type:
            query += " AND pattern_type = ?"
            params.append(pattern_type)
        
        if device_id:
            query += " AND device_id = ?"
            params.append(device_id)
        
        if min_confidence is not None:
            query += " AND confidence >= ?"
            params.append(min_confidence)
        
        query += " ORDER BY confidence DESC"
        
        try:
            cursor = self.conn.execute(query, params)
            rows = cursor.fetchall()
            
            patterns = []
            for row in rows:
                pattern = dict(row)
                # Parse JSON fields
                if 'pattern_metadata' in pattern and pattern['pattern_metadata']:
                    try:
                        pattern['pattern_metadata'] = json.loads(pattern['pattern_metadata'])
                    except (json.JSONDecodeError, TypeError):
                        pattern['pattern_metadata'] = {}
                
                patterns.append(pattern)
            
            logger.info(f"Retrieved {len(patterns)} patterns from database")
            return patterns
            
        except sqlite3.Error as e:
            logger.error(f"Database query error: {e}", exc_info=True)
            raise
    
    async def get_all_synergies(
        self,
        synergy_type: Optional[str] = None,
        min_confidence: Optional[float] = None,
        synergy_depth: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all synergies with optional filters.
        
        Args:
            synergy_type: Filter by synergy type
            min_confidence: Minimum confidence threshold
            synergy_depth: Filter by synergy depth (2, 3, 4)
            
        Returns:
            List of synergy dictionaries
        """
        if self.conn is None:
            self.conn = sqlite3.connect(str(self.db_path))
            self.conn.row_factory = sqlite3.Row
        
        # Check if table exists
        if not self._table_exists('synergy_opportunities'):
            logger.warning("Table 'synergy_opportunities' does not exist in database")
            return []
        
        query = "SELECT * FROM synergy_opportunities WHERE 1=1"
        params = []
        
        if synergy_type:
            query += " AND synergy_type = ?"
            params.append(synergy_type)
        
        if min_confidence is not None:
            query += " AND confidence >= ?"
            params.append(min_confidence)
        
        if synergy_depth is not None:
            query += " AND synergy_depth = ?"
            params.append(synergy_depth)
        
        query += " ORDER BY impact_score DESC"
        
        try:
            cursor = self.conn.execute(query, params)
            rows = cursor.fetchall()
            
            synergies = []
            for row in rows:
                synergy = dict(row)
                # Parse JSON fields
                for field in ['device_ids', 'opportunity_metadata', 'supporting_pattern_ids', 
                             'chain_devices', 'explanation', 'context_breakdown']:
                    if field in synergy and synergy[field]:
                        try:
                            synergy[field] = json.loads(synergy[field])
                        except (json.JSONDecodeError, TypeError):
                            synergy[field] = None if field in ['device_ids', 'chain_devices'] else {}
                
                synergies.append(synergy)
            
            logger.info(f"Retrieved {len(synergies)} synergies from database")
            return synergies
            
        except sqlite3.Error as e:
            logger.error(f"Database query error: {e}", exc_info=True)
            raise
    
    async def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            logger.debug("Database connection closed")
