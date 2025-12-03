"""
Data Lineage Tracker

Track data lineage for collected training data.
"""

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class LineageTracker:
    """
    Data lineage tracker for training data.
    
    Tracks:
    - Data source (cycle, home, test)
    - Data transformations (filters, validations)
    - Data relationships (linked patterns, synergies, suggestions)
    - Lineage metadata
    """

    def __init__(self, lineage_db_path: Path | None = None):
        """
        Initialize lineage tracker.
        
        Args:
            lineage_db_path: Path to lineage database (default: in-memory)
        """
        if lineage_db_path:
            self.db_path = Path(lineage_db_path)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            self.db_path = None
        
        self._init_database()
        logger.info(f"LineageTracker initialized: {self.db_path or 'in-memory'}")

    def _init_database(self) -> None:
        """Initialize lineage database."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS data_lineage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_id TEXT NOT NULL,
                data_type TEXT NOT NULL,
                source_cycle TEXT,
                source_home_id TEXT,
                source_test_id TEXT,
                transformations TEXT,
                relationships TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS data_relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_data_id TEXT NOT NULL,
                target_data_id TEXT NOT NULL,
                relationship_type TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()

    def _get_connection(self) -> sqlite3.Connection:
        """
        Get database connection.
        
        Note: sqlite3 is blocking, but for simulation framework this is acceptable.
        For production use, consider aiosqlite for async operations.
        """
        if self.db_path:
            return sqlite3.connect(self.db_path, timeout=30.0)
        else:
            return sqlite3.connect(":memory:", timeout=30.0)

    def track_data(
        self,
        data_id: str,
        data_type: str,
        source_cycle: str | None = None,
        source_home_id: str | None = None,
        source_test_id: str | None = None,
        transformations: list[str] | None = None,
        relationships: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None
    ) -> None:
        """
        Track data lineage entry.
        
        Args:
            data_id: Unique data identifier
            data_type: Data type (pattern_detection, synergy_detection, etc.)
            source_cycle: Source simulation cycle
            source_home_id: Source home ID
            source_test_id: Source test ID
            transformations: List of transformations applied
            relationships: List of related data entries
            metadata: Additional metadata
        """
        try:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO data_lineage 
                    (data_id, data_type, source_cycle, source_home_id, source_test_id, 
                     transformations, relationships, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    data_id,
                    data_type,
                    source_cycle,
                    source_home_id,
                    source_test_id,
                    json.dumps(transformations) if transformations else None,
                    json.dumps(relationships) if relationships else None,
                    json.dumps(metadata) if metadata else None
                ))
                
                conn.commit()
                logger.debug(f"Tracked data lineage: {data_id} ({data_type})")
            finally:
                conn.close()
        except (sqlite3.Error, json.JSONEncodeError) as e:
            logger.error(f"Failed to track data lineage for {data_id}: {e}")
            raise

    def track_relationship(
        self,
        source_data_id: str,
        target_data_id: str,
        relationship_type: str
    ) -> None:
        """
        Track data relationship.
        
        Args:
            source_data_id: Source data ID
            target_data_id: Target data ID
            relationship_type: Relationship type (linked, derived, etc.)
        """
        try:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO data_relationships 
                    (source_data_id, target_data_id, relationship_type)
                    VALUES (?, ?, ?)
                """, (source_data_id, target_data_id, relationship_type))
                
                conn.commit()
                logger.debug(f"Tracked relationship: {source_data_id} -> {target_data_id} ({relationship_type})")
            finally:
                conn.close()
        except sqlite3.Error as e:
            logger.error(f"Failed to track relationship {source_data_id} -> {target_data_id}: {e}")
            raise

    def query_by_cycle(self, cycle: str) -> list[dict[str, Any]]:
        """
        Query all data from a specific cycle.
        
        Args:
            cycle: Cycle identifier
            
        Returns:
            List of lineage entries
        """
        try:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM data_lineage
                    WHERE source_cycle = ?
                """, (cycle,))
                
                rows = cursor.fetchall()
                
                # Convert to dictionaries
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
            finally:
                conn.close()
        except sqlite3.Error as e:
            logger.error(f"Failed to query lineage by cycle {cycle}: {e}")
            return []

    def query_by_model(self, model_type: str) -> list[dict[str, Any]]:
        """
        Query all data for a specific model type.
        
        Args:
            model_type: Model type (gnn_synergy, soft_prompt, etc.)
            
        Returns:
            List of lineage entries
        """
        try:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                
                # Map model types to data types
                model_to_data_type = {
                    "gnn_synergy": "synergy_detection",
                    "soft_prompt": "suggestion_generation",
                    "pattern_detection": "pattern_detection",
                    "yaml_generation": "yaml_generation"
                }
                
                data_type = model_to_data_type.get(model_type, model_type)
                
                cursor.execute("""
                    SELECT * FROM data_lineage
                    WHERE data_type = ?
                """, (data_type,))
                
                rows = cursor.fetchall()
                
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
            finally:
                conn.close()
        except sqlite3.Error as e:
            logger.error(f"Failed to query lineage by model {model_type}: {e}")
            return []

    def get_relationships(self, data_id: str) -> list[dict[str, Any]]:
        """
        Get all relationships for a data entry.
        
        Args:
            data_id: Data identifier
            
        Returns:
            List of relationship entries
        """
        try:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM data_relationships
                    WHERE source_data_id = ? OR target_data_id = ?
                """, (data_id, data_id))
                
                rows = cursor.fetchall()
                
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
            finally:
                conn.close()
        except sqlite3.Error as e:
            logger.error(f"Failed to get relationships for {data_id}: {e}")
            return []

    def export_lineage(self, output_path: Path) -> None:
        """
        Export lineage data for audit and debugging.
        
        Args:
            output_path: Output file path
        """
        try:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                
                # Export lineage entries
                cursor.execute("SELECT * FROM data_lineage")
                lineage_rows = cursor.fetchall()
                lineage_columns = [desc[0] for desc in cursor.description]
                lineage_data = [dict(zip(lineage_columns, row)) for row in lineage_rows]
                
                # Export relationships
                cursor.execute("SELECT * FROM data_relationships")
                relationship_rows = cursor.fetchall()
                relationship_columns = [desc[0] for desc in cursor.description]
                relationship_data = [dict(zip(relationship_columns, row)) for row in relationship_rows]
            finally:
                conn.close()
            
            # Write to JSON
            export_data = {
                "lineage": lineage_data,
                "relationships": relationship_data,
                "exported_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Ensure directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2)
            
            logger.info(f"Exported lineage data: {output_path}")
        except (sqlite3.Error, OSError, json.JSONEncodeError) as e:
            logger.error(f"Failed to export lineage data to {output_path}: {e}")
            raise

