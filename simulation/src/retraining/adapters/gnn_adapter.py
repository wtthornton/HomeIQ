"""
GNN Synergy Data Adapter

Converts simulation JSON data to format expected by GNN training script.
"""

import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class GNNDataAdapter:
    """
    Adapter to prepare GNN training environment from simulation JSON data.
    
    Converts JSON synergy data to:
    1. Entities list (for Data API mock)
    2. Database synergies (synergy_opportunities table)
    """
    
    def __init__(self, db_path: Path):
        """
        Initialize GNN data adapter.
        
        Args:
            db_path: Path to SQLite database for synergies
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"GNNDataAdapter initialized: db_path={db_path}")
    
    def prepare_training_environment(
        self,
        json_path: Path
    ) -> tuple[list[dict[str, Any]], Path]:
        """
        Prepare training environment from JSON data.
        
        Args:
            json_path: Path to gnn_synergy_data.json
            
        Returns:
            Tuple of (entities_list, db_path)
        """
        logger.info(f"Preparing GNN training environment from {json_path}")
        
        # Load JSON data
        if not json_path.exists():
            raise FileNotFoundError(f"GNN synergy data not found: {json_path}")
        
        with open(json_path, "r", encoding="utf-8") as f:
            synergy_data = json.load(f)
        
        logger.info(f"Loaded {len(synergy_data)} synergy entries from JSON")
        
        # Extract entities and synergies
        entities_set = set()
        synergies = []
        
        for entry in synergy_data:
            # Handle both formats: nested "synergy" key or flat structure
            if "synergy" in entry:
                synergy = entry.get("synergy", {})
                entity_1 = synergy.get("entity_1") or synergy.get("device1")
                entity_2 = synergy.get("entity_2") or synergy.get("device2")
                synergy_score = synergy.get("synergy_score") or synergy.get("confidence", 0.5)
                synergy_type = synergy.get("synergy_type", "co_activation")
                relationship = entry.get("relationship", {})
            else:
                # Flat structure (from exporter)
                entity_1 = entry.get("entity_1") or entry.get("device1")
                entity_2 = entry.get("entity_2") or entry.get("device2")
                synergy_score = entry.get("confidence", 0.5)
                synergy_type = entry.get("synergy_type", "co_activation")
                relationship = entry.get("relationship", {})
            
            if not entity_1 or not entity_2:
                logger.warning(f"Skipping entry with missing entities: {entry}")
                continue
            
            # Add to entities set
            entities_set.add(entity_1)
            entities_set.add(entity_2)
            
            # Create synergy record
            synergies.append({
                "synergy_id": str(uuid.uuid4()),
                "synergy_type": synergy_type,
                "device_ids": json.dumps([entity_1, entity_2]),
                "opportunity_metadata": entry.get("relationship", {}),
                "impact_score": float(synergy_score),
                "complexity": "medium",  # Default complexity
                "confidence": float(synergy_score),
                "area": None,  # Can be extracted from metadata if available
                "pattern_support_score": 0.0,
                "validated_by_patterns": False,
                "synergy_depth": 2
            })
        
        logger.info(f"Extracted {len(entities_set)} unique entities and {len(synergies)} synergies")
        
        # Create entities list (minimal format for training)
        entities = []
        for entity_id in entities_set:
            # Parse entity_id to extract domain
            parts = entity_id.split(".")
            domain = parts[0] if len(parts) > 1 else "unknown"
            
            entities.append({
                "entity_id": entity_id,
                "domain": domain,
                "device_id": entity_id,  # Use entity_id as device_id
                "name": parts[-1] if len(parts) > 1 else entity_id,
                "state": "unknown",
                "attributes": {}
            })
        
        # Populate database
        self._populate_database(synergies)
        
        logger.info(f"✅ GNN training environment prepared: {len(entities)} entities, {len(synergies)} synergies")
        
        return entities, self.db_path
    
    def _populate_database(self, synergies: list[dict[str, Any]]) -> None:
        """
        Populate synergy_opportunities table in database.
        
        Args:
            synergies: List of synergy dictionaries
        """
        logger.info(f"Populating database with {len(synergies)} synergies...")
        
        # Connect to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Create table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS synergy_opportunities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    synergy_id TEXT UNIQUE NOT NULL,
                    synergy_type TEXT NOT NULL,
                    device_ids TEXT NOT NULL,
                    opportunity_metadata TEXT,
                    impact_score REAL NOT NULL,
                    complexity TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    area TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    pattern_support_score REAL DEFAULT 0.0,
                    validated_by_patterns INTEGER DEFAULT 0,
                    supporting_pattern_ids TEXT,
                    synergy_depth INTEGER DEFAULT 2,
                    chain_devices TEXT,
                    embedding_similarity REAL,
                    rerank_score REAL,
                    final_score REAL
                )
            """)
            
            # Create index
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS ix_synergy_opportunities_synergy_id 
                ON synergy_opportunities(synergy_id)
            """)
            
            # Clear existing synergies (for fresh training)
            cursor.execute("DELETE FROM synergy_opportunities")
            
            # Insert synergies
            for synergy in synergies:
                cursor.execute("""
                    INSERT INTO synergy_opportunities (
                        synergy_id, synergy_type, device_ids, opportunity_metadata,
                        impact_score, complexity, confidence, area,
                        pattern_support_score, validated_by_patterns, synergy_depth
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    synergy["synergy_id"],
                    synergy["synergy_type"],
                    synergy["device_ids"],
                    json.dumps(synergy["opportunity_metadata"]),
                    synergy["impact_score"],
                    synergy["complexity"],
                    synergy["confidence"],
                    synergy["area"],
                    synergy["pattern_support_score"],
                    1 if synergy["validated_by_patterns"] else 0,
                    synergy["synergy_depth"]
                ))
            
            conn.commit()
            logger.info(f"✅ Inserted {len(synergies)} synergies into database")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to populate database: {e}", exc_info=True)
            raise
        finally:
            conn.close()
    
    def create_entities_json(self, entities: list[dict[str, Any]], output_path: Path) -> Path:
        """
        Create entities JSON file for mock Data API.
        
        Args:
            entities: List of entity dictionaries
            output_path: Path to save entities JSON
            
        Returns:
            Path to created JSON file
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(entities, f, indent=2)
        
        logger.info(f"Created entities JSON: {output_path}")
        return output_path

