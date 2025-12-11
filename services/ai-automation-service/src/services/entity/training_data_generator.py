"""
Training Data Generator for Entity Resolution

Epic AI-12, Story AI12.6: Training Data Generation from User Devices
Generates training data from user's actual devices for simulation framework.
"""

import json
import logging
from typing import Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import csv

from .personalized_index import PersonalizedEntityIndex, EntityIndexEntry
from .personalized_resolver import PersonalizedEntityResolver, ResolutionResult
from ..learning.feedback_tracker import FeedbackTracker, EntityResolutionFeedback

logger = logging.getLogger(__name__)


@dataclass
class QueryEntityPair:
    """Represents a query-entity pair for training"""
    query: str
    entity_id: str
    device_name: str
    domain: str
    area_id: Optional[str] = None
    area_name: Optional[str] = None
    confidence: float = 1.0
    source: str = "synthetic"  # 'synthetic', 'user_feedback', 'interaction'
    created_at: Optional[str] = None


class TrainingDataGenerator:
    """
    Generates training data from user's actual devices.
    
    Features:
    - Extract query-entity pairs from user interactions
    - Generate synthetic queries from user's device names
    - Create personalized test dataset
    - Export in standard formats (JSON, CSV)
    - Support simulation framework integration
    """
    
    def __init__(
        self,
        personalized_index: PersonalizedEntityIndex,
        personalized_resolver: Optional[PersonalizedEntityResolver] = None,
        feedback_tracker: Optional[FeedbackTracker] = None
    ):
        """
        Initialize training data generator.
        
        Args:
            personalized_index: PersonalizedEntityIndex
            personalized_resolver: Optional PersonalizedEntityResolver
            feedback_tracker: Optional FeedbackTracker for extracting user interactions
        """
        self.index = personalized_index
        self.resolver = personalized_resolver
        self.feedback_tracker = feedback_tracker
        
        logger.info("TrainingDataGenerator initialized")
    
    def generate_synthetic_queries(
        self,
        entity_id: Optional[str] = None,
        limit: int = 100
    ) -> list[QueryEntityPair]:
        """
        Generate synthetic queries from user's device names.
        
        Args:
            entity_id: Optional entity ID filter
            limit: Maximum number of queries to generate
        
        Returns:
            List of QueryEntityPair objects
        """
        pairs = []
        
        try:
            # Get entities from index
            entities = list(self.index._index.values())
            
            if entity_id:
                entities = [e for e in entities if e.entity_id == entity_id]
            
            # Generate queries for each entity
            for entry in entities[:limit]:
                # Generate queries from all variants
                for variant in entry.variants:
                    # Base query
                    base_query = f"turn on {variant.variant_name}"
                    pairs.append(QueryEntityPair(
                        query=base_query,
                        entity_id=entry.entity_id,
                        device_name=variant.variant_name,
                        domain=entry.domain,
                        area_id=entry.area_id,
                        area_name=entry.area_name,
                        confidence=1.0,
                        source="synthetic",
                        created_at=datetime.utcnow().isoformat()
                    ))
                    
                    # Generate variations
                    variations = self._generate_query_variations(variant.variant_name, entry.domain)
                    for var_query in variations:
                        pairs.append(QueryEntityPair(
                            query=var_query,
                            entity_id=entry.entity_id,
                            device_name=variant.variant_name,
                            domain=entry.domain,
                            area_id=entry.area_id,
                            area_name=entry.area_name,
                            confidence=0.9,  # Slightly lower for variations
                            source="synthetic",
                            created_at=datetime.utcnow().isoformat()
                        ))
            
            logger.info(f"Generated {len(pairs)} synthetic queries")
            return pairs
            
        except Exception as e:
            logger.error(f"Failed to generate synthetic queries: {e}", exc_info=True)
            return []
    
    def _generate_query_variations(
        self,
        device_name: str,
        domain: str
    ) -> list[str]:
        """Generate query variations for a device name"""
        variations = []
        
        # Common action verbs
        actions = {
            "light": ["turn on", "turn off", "toggle", "dim", "brighten", "set"],
            "switch": ["turn on", "turn off", "toggle"],
            "sensor": ["check", "read", "get status of"],
            "climate": ["set temperature", "turn on", "turn off", "adjust"],
            "cover": ["open", "close", "stop"],
            "fan": ["turn on", "turn off", "set speed"],
            "lock": ["lock", "unlock"],
            "media_player": ["play", "pause", "stop", "volume up", "volume down"]
        }
        
        # Get actions for domain
        domain_actions = actions.get(domain, ["turn on", "turn off"])
        
        # Generate variations
        for action in domain_actions:
            variations.append(f"{action} {device_name}")
            variations.append(f"{action} the {device_name}")
        
        # Add area context if available
        # (Would need area information from index)
        
        return variations[:5]  # Limit to 5 variations
    
    async def extract_from_user_feedback(
        self,
        device_name: Optional[str] = None,
        limit: int = 100
    ) -> list[QueryEntityPair]:
        """
        Extract query-entity pairs from user feedback.
        
        Args:
            device_name: Optional device name filter
            limit: Maximum number of pairs to extract
        
        Returns:
            List of QueryEntityPair objects
        """
        pairs = []
        
        if not self.feedback_tracker:
            logger.warning("FeedbackTracker not available, skipping user feedback extraction")
            return pairs
        
        try:
            # Get feedback
            if device_name:
                feedbacks = await self.feedback_tracker.get_feedback_for_device(device_name, limit)
            else:
                # Get all feedback (would need to implement in FeedbackTracker)
                feedbacks = []
            
            for feedback in feedbacks:
                # Use actual entity ID if available, otherwise suggested
                entity_id = feedback.actual_entity_id or feedback.suggested_entity_id
                if not entity_id:
                    continue
                
                # Get entity info from index
                entry = self.index.get_entity(entity_id)
                if not entry:
                    continue
                
                pairs.append(QueryEntityPair(
                    query=feedback.query,
                    entity_id=entity_id,
                    device_name=feedback.device_name,
                    domain=entry.domain,
                    area_id=feedback.area_id,
                    area_name=entry.area_name if entry else None,
                    confidence=feedback.confidence_score or 1.0,
                    source="user_feedback",
                    created_at=feedback.created_at.isoformat() if feedback.created_at else None
                ))
            
            logger.info(f"Extracted {len(pairs)} query-entity pairs from user feedback")
            return pairs
            
        except Exception as e:
            logger.error(f"Failed to extract from user feedback: {e}", exc_info=True)
            return []
    
    async def generate_personalized_dataset(
        self,
        include_synthetic: bool = True,
        include_feedback: bool = True,
        limit: int = 1000
    ) -> list[QueryEntityPair]:
        """
        Generate personalized test dataset.
        
        Args:
            include_synthetic: Include synthetic queries
            include_feedback: Include queries from user feedback
            limit: Maximum number of pairs to generate
        
        Returns:
            List of QueryEntityPair objects
        """
        pairs = []
        
        try:
            # Generate synthetic queries
            if include_synthetic:
                synthetic = self.generate_synthetic_queries(limit=limit // 2)
                pairs.extend(synthetic)
            
            # Extract from user feedback
            if include_feedback:
                feedback_pairs = await self.extract_from_user_feedback(limit=limit // 2)
                pairs.extend(feedback_pairs)
            
            # Remove duplicates (same query + entity_id)
            seen = set()
            unique_pairs = []
            for pair in pairs:
                key = (pair.query.lower(), pair.entity_id)
                if key not in seen:
                    seen.add(key)
                    unique_pairs.append(pair)
            
            logger.info(f"Generated personalized dataset: {len(unique_pairs)} unique pairs")
            return unique_pairs[:limit]
            
        except Exception as e:
            logger.error(f"Failed to generate personalized dataset: {e}", exc_info=True)
            return []
    
    def export_to_json(
        self,
        pairs: list[QueryEntityPair],
        output_path: str | Path
    ) -> bool:
        """
        Export training data to JSON format.
        
        Args:
            pairs: List of QueryEntityPair objects
            output_path: Path to output file
        
        Returns:
            True if export was successful
        """
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert to dict
            data = {
                "metadata": {
                    "generated_at": datetime.utcnow().isoformat(),
                    "total_pairs": len(pairs),
                    "sources": list(set(p.source for p in pairs))
                },
                "pairs": [asdict(pair) for pair in pairs]
            }
            
            # Write to file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Exported {len(pairs)} pairs to JSON: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export to JSON: {e}", exc_info=True)
            return False
    
    def export_to_csv(
        self,
        pairs: list[QueryEntityPair],
        output_path: str | Path
    ) -> bool:
        """
        Export training data to CSV format.
        
        Args:
            pairs: List of QueryEntityPair objects
            output_path: Path to output file
        
        Returns:
            True if export was successful
        """
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write CSV
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    'query', 'entity_id', 'device_name', 'domain',
                    'area_id', 'area_name', 'confidence', 'source', 'created_at'
                ])
                writer.writeheader()
                
                for pair in pairs:
                    writer.writerow(asdict(pair))
            
            logger.info(f"Exported {len(pairs)} pairs to CSV: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export to CSV: {e}", exc_info=True)
            return False
    
    def export_for_simulation(
        self,
        pairs: list[QueryEntityPair],
        output_path: str | Path,
        format: str = "json"
    ) -> bool:
        """
        Export training data in format suitable for simulation framework.
        
        Args:
            pairs: List of QueryEntityPair objects
            output_path: Path to output file
            format: Export format ('json' or 'csv')
        
        Returns:
            True if export was successful
        """
        try:
            if format.lower() == "json":
                return self.export_to_json(pairs, output_path)
            elif format.lower() == "csv":
                return self.export_to_csv(pairs, output_path)
            else:
                logger.error(f"Unsupported format: {format}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to export for simulation: {e}", exc_info=True)
            return False
    
    def get_dataset_stats(
        self,
        pairs: list[QueryEntityPair]
    ) -> dict[str, Any]:
        """
        Get statistics about the dataset.
        
        Args:
            pairs: List of QueryEntityPair objects
        
        Returns:
            Dictionary with statistics
        """
        if not pairs:
            return {
                "total_pairs": 0,
                "by_source": {},
                "by_domain": {},
                "by_area": {},
                "avg_confidence": 0.0
            }
        
        stats = {
            "total_pairs": len(pairs),
            "by_source": {},
            "by_domain": {},
            "by_area": {},
            "avg_confidence": 0.0
        }
        
        total_confidence = 0.0
        confidence_count = 0
        
        for pair in pairs:
            # Count by source
            stats["by_source"][pair.source] = stats["by_source"].get(pair.source, 0) + 1
            
            # Count by domain
            stats["by_domain"][pair.domain] = stats["by_domain"].get(pair.domain, 0) + 1
            
            # Count by area
            area = pair.area_name or pair.area_id or "unknown"
            stats["by_area"][area] = stats["by_area"].get(area, 0) + 1
            
            # Track confidence
            if pair.confidence is not None:
                total_confidence += pair.confidence
                confidence_count += 1
        
        # Calculate average confidence
        if confidence_count > 0:
            stats["avg_confidence"] = total_confidence / confidence_count
        
        return stats

