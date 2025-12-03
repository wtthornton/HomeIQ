"""
Training Data Exporters

Export training data in different formats for model training.
"""

import csv
import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    logging.warning("pandas not available, Parquet export disabled")

logger = logging.getLogger(__name__)


class TrainingDataExporter:
    """
    Training data exporter for different model training formats.
    
    Supports:
    - GNN synergy data (JSON, Parquet)
    - Soft Prompt data (JSON, SQLite)
    - Pattern detection data (JSON, Parquet)
    - YAML generation data (JSON)
    - Device intelligence data (JSON, CSV)
    """

    def __init__(self, output_directory: Path):
        """
        Initialize training data exporter.
        
        Args:
            output_directory: Output directory for exported data
        """
        self.output_directory = Path(output_directory)
        self.output_directory.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"TrainingDataExporter initialized: {output_directory}")

    def export_gnn_synergy_data(
        self,
        synergy_data: list[dict[str, Any]],
        format: str = "json"
    ) -> Path:
        """
        Export GNN synergy data.
        
        Args:
            synergy_data: List of synergy data entries
            format: Export format ("json" or "parquet")
            
        Returns:
            Path to exported file
        """
        logger.info(f"Exporting {len(synergy_data)} GNN synergy entries ({format})")
        
        # Transform data for GNN format
        gnn_data = []
        for entry in synergy_data:
            synergy = entry.get("synergy", {})
            gnn_data.append({
                "entity_1": synergy.get("entity_1"),
                "entity_2": synergy.get("entity_2"),
                "synergy_type": synergy.get("synergy_type", "co_activation"),
                "confidence": synergy.get("confidence", 0.0),
                "relationship": entry.get("relationship", {}),
                "prediction": entry.get("prediction", {})
            })
        
        if format == "json":
            output_path = self.output_directory / "gnn_synergy_data.json"
            try:
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(gnn_data, f, indent=2)
            except (OSError, TypeError) as e:
                logger.error(f"Failed to export GNN synergy data to {output_path}: {e}")
                raise
        elif format == "parquet" and PANDAS_AVAILABLE:
            output_path = self.output_directory / "gnn_synergy_data.parquet"
            df = pd.DataFrame(gnn_data)
            df.to_parquet(output_path, index=False)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        logger.info(f"Exported GNN synergy data: {output_path}")
        return output_path

    def export_soft_prompt_data(
        self,
        prompt_data: list[dict[str, Any]],
        format: str = "json"
    ) -> Path:
        """
        Export Soft Prompt data.
        
        Args:
            prompt_data: List of prompt data entries
            format: Export format ("json" or "sqlite")
            
        Returns:
            Path to exported file
        """
        logger.info(f"Exporting {len(prompt_data)} Soft Prompt entries ({format})")
        
        # Transform data for Soft Prompt format
        soft_prompt_data = []
        for entry in prompt_data:
            suggestion = entry.get("suggestion", {})
            prompt = entry.get("prompt", {})
            soft_prompt_data.append({
                "query": prompt.get("user_prompt", ""),
                "suggestion": suggestion.get("description", ""),
                "automation_type": suggestion.get("automation_type", ""),
                "quality_score": suggestion.get("quality_score", 0.0),
                "response": entry.get("response", {})
            })
        
        if format == "json":
            output_path = self.output_directory / "soft_prompt_data.json"
            try:
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(soft_prompt_data, f, indent=2)
            except (OSError, TypeError) as e:
                logger.error(f"Failed to export Soft Prompt data to {output_path}: {e}")
                raise
        elif format == "sqlite":
            output_path = self.output_directory / "soft_prompt_data.db"
            try:
                conn = sqlite3.connect(output_path, timeout=30.0)
                try:
                    cursor = conn.cursor()
                    
                    # Create table
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS ask_ai_queries (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            query TEXT NOT NULL,
                            suggestion TEXT,
                            automation_type TEXT,
                            quality_score REAL,
                            response TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    
                    # Insert data
                    for entry in soft_prompt_data:
                        cursor.execute("""
                            INSERT INTO ask_ai_queries 
                            (query, suggestion, automation_type, quality_score, response)
                            VALUES (?, ?, ?, ?, ?)
                        """, (
                            entry["query"],
                            entry["suggestion"],
                            entry["automation_type"],
                            entry["quality_score"],
                            json.dumps(entry["response"])
                        ))
                    
                    conn.commit()
                finally:
                    conn.close()
            except (sqlite3.Error, json.JSONEncodeError) as e:
                logger.error(f"Failed to export Soft Prompt data to SQLite {output_path}: {e}")
                raise
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        logger.info(f"Exported Soft Prompt data: {output_path}")
        return output_path

    def export_pattern_detection_data(
        self,
        pattern_data: list[dict[str, Any]],
        format: str = "json"
    ) -> Path:
        """
        Export pattern detection data.
        
        Args:
            pattern_data: List of pattern data entries
            format: Export format ("json" or "parquet")
            
        Returns:
            Path to exported file
        """
        logger.info(f"Exporting {len(pattern_data)} pattern detection entries ({format})")
        
        # Transform data
        patterns = []
        for entry in pattern_data:
            pattern = entry.get("pattern", {})
            patterns.append({
                "entity_id": pattern.get("entity_id"),
                "pattern_type": pattern.get("pattern_type"),
                "confidence": pattern.get("confidence", 0.0),
                "occurrences": pattern.get("occurrences", 0),
                "ground_truth": entry.get("ground_truth", {}),
                "metrics": entry.get("metrics", {})
            })
        
        if format == "json":
            output_path = self.output_directory / "pattern_detection_data.json"
            try:
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(patterns, f, indent=2)
            except (OSError, TypeError) as e:
                logger.error(f"Failed to export pattern detection data to {output_path}: {e}")
                raise
        elif format == "parquet" and PANDAS_AVAILABLE:
            output_path = self.output_directory / "pattern_detection_data.parquet"
            df = pd.DataFrame(patterns)
            df.to_parquet(output_path, index=False)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        logger.info(f"Exported pattern detection data: {output_path}")
        return output_path

    def export_yaml_generation_data(
        self,
        yaml_data: list[dict[str, Any]]
    ) -> Path:
        """
        Export YAML generation data.
        
        Args:
            yaml_data: List of YAML data entries
            
        Returns:
            Path to exported file
        """
        logger.info(f"Exporting {len(yaml_data)} YAML generation entries")
        
        # Transform data
        yaml_pairs = []
        for entry in yaml_data:
            yaml_pair = entry.get("yaml_pair", {})
            yaml_pairs.append({
                "input": yaml_pair.get("input", ""),
                "output": yaml_pair.get("output", ""),
                "validation_result": entry.get("validation_result", {}),
                "ground_truth": entry.get("ground_truth", {})
            })
        
        output_path = self.output_directory / "yaml_generation_data.json"
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(yaml_pairs, f, indent=2)
        except (OSError, TypeError) as e:
            logger.error(f"Failed to export YAML generation data to {output_path}: {e}")
            raise
        
        logger.info(f"Exported YAML generation data: {output_path}")
        return output_path

    def export_device_intelligence_data(
        self,
        device_data: list[dict[str, Any]],
        format: str = "json"
    ) -> Path:
        """
        Export device intelligence data.
        
        Args:
            device_data: List of device data entries
            format: Export format ("json" or "csv")
            
        Returns:
            Path to exported file
        """
        logger.info(f"Exporting {len(device_data)} device intelligence entries ({format})")
        
        # Transform data
        devices = []
        for entry in device_data:
            devices.append({
                "device_id": entry.get("device_id", ""),
                "entity_id": entry.get("entity_id", ""),
                "device_type": entry.get("device_type", ""),
                "capabilities": entry.get("capabilities", []),
                "metadata": entry.get("metadata", {})
            })
        
        if format == "json":
            output_path = self.output_directory / "device_intelligence_data.json"
            try:
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(devices, f, indent=2)
            except (OSError, TypeError) as e:
                logger.error(f"Failed to export device intelligence data to {output_path}: {e}")
                raise
        elif format == "csv":
            output_path = self.output_directory / "device_intelligence_data.csv"
            try:
                with open(output_path, "w", newline="", encoding="utf-8") as f:
                    if devices:
                        writer = csv.DictWriter(f, fieldnames=devices[0].keys())
                        writer.writeheader()
                        writer.writerows(devices)
            except (OSError, KeyError) as e:
                logger.error(f"Failed to export device intelligence data to {output_path}: {e}")
                raise
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        logger.info(f"Exported device intelligence data: {output_path}")
        return output_path

