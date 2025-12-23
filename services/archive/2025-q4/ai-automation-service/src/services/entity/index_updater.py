"""
Index Updater for Personalized Entity Index

Epic AI-12, Story AI12.5: Index Update from User Feedback
Updates personalized index based on user feedback without full rebuild.
"""

import logging
from typing import Any, Optional
from collections import defaultdict

from .personalized_index import PersonalizedEntityIndex, EntityIndexEntry, EntityVariant
from ..learning.feedback_tracker import FeedbackTracker, FeedbackType, EntityResolutionFeedback

logger = logging.getLogger(__name__)


class IndexUpdater:
    """
    Updates personalized entity index based on user feedback.
    
    Features:
    - Incremental index updates (no full rebuild)
    - Update entity name mappings based on corrections
    - Boost confidence for frequently selected entities
    - Learn user's preferred naming conventions
    - Add custom mappings from user feedback
    """
    
    def __init__(
        self,
        personalized_index: PersonalizedEntityIndex,
        feedback_tracker: FeedbackTracker
    ):
        """
        Initialize index updater.
        
        Args:
            personalized_index: PersonalizedEntityIndex to update
            feedback_tracker: FeedbackTracker for accessing feedback
        """
        self.index = personalized_index
        self.feedback_tracker = feedback_tracker
        
        # Track variant confidence scores (entity_id -> variant_name -> confidence)
        self._variant_confidence: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        
        # Track variant selection counts (entity_id -> variant_name -> count)
        self._variant_selections: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        
        logger.info("IndexUpdater initialized")
    
    async def update_from_feedback(
        self,
        device_name: str,
        entity_id: str,
        feedback_type: FeedbackType,
        area_id: Optional[str] = None
    ) -> bool:
        """
        Update index based on feedback.
        
        Args:
            device_name: Device name from query
            entity_id: Entity ID (suggested or actual)
            feedback_type: Type of feedback
            area_id: Optional area ID
        
        Returns:
            True if update was successful
        """
        try:
            if feedback_type == FeedbackType.APPROVE:
                # Boost confidence for this mapping
                await self._boost_variant_confidence(device_name, entity_id)
            
            elif feedback_type == FeedbackType.REJECT:
                # Reduce confidence for this mapping
                await self._reduce_variant_confidence(device_name, entity_id)
            
            elif feedback_type == FeedbackType.CORRECT:
                # Add/update custom mapping
                await self._add_custom_variant(device_name, entity_id, area_id)
            
            elif feedback_type == FeedbackType.CUSTOM_MAPPING:
                # Add custom mapping
                await self._add_custom_variant(device_name, entity_id, area_id)
            
            logger.info(f"Updated index from feedback: {feedback_type.value} for '{device_name}' -> {entity_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update index from feedback: {e}", exc_info=True)
            return False
    
    async def _boost_variant_confidence(
        self,
        device_name: str,
        entity_id: str
    ) -> None:
        """Boost confidence for a variant mapping"""
        try:
            entry = self.index.get_entity(entity_id)
            if not entry:
                logger.warning(f"Entity {entity_id} not found in index for boosting")
                return
            
            # Find or create variant
            variant = self._find_or_create_variant(entry, device_name, "user_feedback")
            
            # Boost confidence (increase by 0.1, max 1.0)
            current_confidence = self._variant_confidence[entity_id].get(device_name.lower(), 0.5)
            new_confidence = min(1.0, current_confidence + 0.1)
            self._variant_confidence[entity_id][device_name.lower()] = new_confidence
            
            # Increment selection count
            self._variant_selections[entity_id][device_name.lower()] += 1
            
            logger.debug(f"Boosted confidence for '{device_name}' -> {entity_id}: {current_confidence:.2f} -> {new_confidence:.2f}")
            
        except Exception as e:
            logger.error(f"Failed to boost variant confidence: {e}", exc_info=True)
    
    async def _reduce_variant_confidence(
        self,
        device_name: str,
        entity_id: str
    ) -> None:
        """Reduce confidence for a variant mapping"""
        try:
            entry = self.index.get_entity(entity_id)
            if not entry:
                logger.warning(f"Entity {entity_id} not found in index for reducing")
                return
            
            # Reduce confidence (decrease by 0.1, min 0.0)
            current_confidence = self._variant_confidence[entity_id].get(device_name.lower(), 0.5)
            new_confidence = max(0.0, current_confidence - 0.1)
            self._variant_confidence[entity_id][device_name.lower()] = new_confidence
            
            logger.debug(f"Reduced confidence for '{device_name}' -> {entity_id}: {current_confidence:.2f} -> {new_confidence:.2f}")
            
        except Exception as e:
            logger.error(f"Failed to reduce variant confidence: {e}", exc_info=True)
    
    async def _add_custom_variant(
        self,
        device_name: str,
        entity_id: str,
        area_id: Optional[str] = None
    ) -> None:
        """Add custom variant mapping to index"""
        try:
            entry = self.index.get_entity(entity_id)
            if not entry:
                logger.warning(f"Entity {entity_id} not found in index for custom variant")
                return
            
            # Check if variant already exists
            existing_variant = self._find_variant(entry, device_name)
            
            if existing_variant:
                # Update existing variant
                existing_variant.variant_type = "user_feedback"  # Mark as user feedback
                logger.debug(f"Updated existing variant: '{device_name}' -> {entity_id}")
            else:
                # Create new variant
                variant = self._find_or_create_variant(entry, device_name, "user_feedback", area_id)
                
                # Set high confidence for user-provided mappings
                self._variant_confidence[entity_id][device_name.lower()] = 0.9
                self._variant_selections[entity_id][device_name.lower()] = 1
                
                logger.debug(f"Added custom variant: '{device_name}' -> {entity_id}")
            
            # Update entry timestamp
            from datetime import datetime
            entry.last_updated = datetime.now()
            
        except Exception as e:
            logger.error(f"Failed to add custom variant: {e}", exc_info=True)
    
    def _find_variant(
        self,
        entry: EntityIndexEntry,
        variant_name: str
    ) -> Optional[EntityVariant]:
        """Find variant by name (case-insensitive)"""
        variant_name_lower = variant_name.lower()
        for variant in entry.variants:
            if variant.variant_name.lower() == variant_name_lower:
                return variant
        return None
    
    def _find_or_create_variant(
        self,
        entry: EntityIndexEntry,
        variant_name: str,
        variant_type: str,
        area_id: Optional[str] = None
    ) -> EntityVariant:
        """Find or create variant"""
        # Try to find existing
        existing = self._find_variant(entry, variant_name)
        if existing:
            return existing
        
        # Create new variant
        embedding = self.index._generate_embedding(variant_name)
        
        variant = EntityVariant(
            entity_id=entry.entity_id,
            variant_name=variant_name.strip(),
            variant_type=variant_type,
            embedding=embedding,
            area_id=area_id or entry.area_id,
            area_name=entry.area_name
        )
        
        entry.variants.append(variant)
        
        # Add to reverse index
        self.index._variant_index[variant_name.strip().lower()].append(entry.entity_id)
        
        return variant
    
    async def process_feedback_batch(
        self,
        device_name: Optional[str] = None,
        limit: int = 100
    ) -> dict[str, Any]:
        """
        Process a batch of feedback and update index.
        
        Args:
            device_name: Optional device name filter
            limit: Maximum number of feedback records to process
        
        Returns:
            Dictionary with update statistics
        """
        try:
            # Get feedback
            if device_name:
                feedbacks = await self.feedback_tracker.get_feedback_for_device(device_name, limit)
            else:
                # Get all feedback (would need to implement in FeedbackTracker)
                feedbacks = await self.feedback_tracker.get_feedback_for_device("", limit)
            
            stats = {
                "processed": 0,
                "updated": 0,
                "errors": 0,
                "by_type": defaultdict(int)
            }
            
            for feedback in feedbacks:
                try:
                    entity_id = feedback.actual_entity_id or feedback.suggested_entity_id
                    if not entity_id:
                        continue
                    
                    success = await self.update_from_feedback(
                        device_name=feedback.device_name,
                        entity_id=entity_id,
                        feedback_type=feedback.feedback_type,
                        area_id=feedback.area_id
                    )
                    
                    if success:
                        stats["updated"] += 1
                        stats["by_type"][feedback.feedback_type.value] += 1
                    
                    stats["processed"] += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to process feedback: {e}")
                    stats["errors"] += 1
            
            logger.info(
                f"Processed feedback batch: {stats['processed']} processed, "
                f"{stats['updated']} updated, {stats['errors']} errors"
            )
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to process feedback batch: {e}", exc_info=True)
            return {
                "processed": 0,
                "updated": 0,
                "errors": 1,
                "by_type": {}
            }
    
    def get_variant_confidence(
        self,
        entity_id: str,
        variant_name: str
    ) -> float:
        """
        Get confidence score for a variant mapping.
        
        Args:
            entity_id: Entity ID
            variant_name: Variant name
        
        Returns:
            Confidence score (0.0-1.0)
        """
        return self._variant_confidence[entity_id].get(variant_name.lower(), 0.5)
    
    def get_variant_selection_count(
        self,
        entity_id: str,
        variant_name: str
    ) -> int:
        """
        Get selection count for a variant mapping.
        
        Args:
            entity_id: Entity ID
            variant_name: Variant name
        
        Returns:
            Selection count
        """
        return self._variant_selections[entity_id].get(variant_name.lower(), 0)
    
    def get_update_stats(self) -> dict[str, Any]:
        """Get statistics about index updates"""
        total_variants = sum(len(confidences) for confidences in self._variant_confidence.values())
        total_selections = sum(
            sum(counts.values()) for counts in self._variant_selections.values()
        )
        
        return {
            "total_variants_with_confidence": total_variants,
            "total_selections": total_selections,
            "entities_with_feedback": len(self._variant_confidence)
        }

