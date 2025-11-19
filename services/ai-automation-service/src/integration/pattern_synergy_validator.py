"""
Pattern-Synergy Validator

Phase 2: Cross-validation of synergies against detected patterns.

Provides functionality to:
- Validate synergies against patterns
- Calculate pattern support scores
- Identify supporting and conflicting patterns
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timezone
import logging
import json

from ..database.models import Pattern, SynergyOpportunity

logger = logging.getLogger(__name__)


class PatternSynergyValidator:
    """
    Validates synergy opportunities against detected patterns.
    
    Phase 2: Cross-validation between patterns and synergies.
    
    Logic:
    - High-confidence pattern for synergy device pair → boost synergy score
    - Conflicting pattern → reduce synergy score
    - No pattern → neutral score
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize pattern-synergy validator.
        
        Args:
            db: Database session
        """
        self.db = db
    
    async def validate_synergy_with_patterns(
        self,
        synergy: Dict,
        min_pattern_confidence: float = 0.7
    ) -> Dict[str, any]:
        """
        Validate synergy against detected patterns.
        
        Args:
            synergy: Synergy opportunity dictionary
            min_pattern_confidence: Minimum pattern confidence to consider (default: 0.7)
            
        Returns:
            Dictionary with validation results:
            {
                'pattern_support_score': float (0.0-1.0),
                'validated_by_patterns': bool,
                'supporting_patterns': List[Dict],
                'conflicting_patterns': List[Dict],
                'recommended_confidence_adjustment': float,
                'validation_status': 'valid' | 'warning' | 'invalid'
            }
        """
        try:
            # Extract device IDs from synergy
            device_ids = synergy.get('devices', [])
            if isinstance(device_ids, str):
                try:
                    device_ids = json.loads(device_ids)
                except:
                    device_ids = [device_ids]
            
            if not device_ids:
                logger.warning(f"Synergy {synergy.get('synergy_id')} has no device IDs")
                return {
                    'pattern_support_score': 0.0,
                    'validated_by_patterns': False,
                    'supporting_patterns': [],
                    'conflicting_patterns': [],
                    'recommended_confidence_adjustment': 0.0,
                    'validation_status': 'invalid'
                }
            
            # Find patterns involving these devices
            patterns = await self._find_patterns_for_devices(device_ids, min_pattern_confidence)
            
            # Calculate support score
            support_score, supporting_patterns, conflicting_patterns = self._calculate_support_score(
                synergy, patterns, device_ids
            )
            
            # Determine validation status
            validation_status = self._determine_validation_status(
                support_score, len(supporting_patterns), len(conflicting_patterns)
            )
            
            # Calculate confidence adjustment recommendation
            confidence_adjustment = self._calculate_confidence_adjustment(support_score)
            
            result = {
                'pattern_support_score': support_score,
                'validated_by_patterns': support_score >= 0.5,
                'supporting_patterns': supporting_patterns,
                'conflicting_patterns': conflicting_patterns,
                'recommended_confidence_adjustment': confidence_adjustment,
                'validation_status': validation_status
            }
            
            logger.debug(
                f"Synergy {synergy.get('synergy_id')} validation: "
                f"support={support_score:.2f}, status={validation_status}, "
                f"supporting={len(supporting_patterns)}, conflicting={len(conflicting_patterns)}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to validate synergy with patterns: {e}", exc_info=True)
            return {
                'pattern_support_score': 0.0,
                'validated_by_patterns': False,
                'supporting_patterns': [],
                'conflicting_patterns': [],
                'recommended_confidence_adjustment': 0.0,
                'validation_status': 'error',
                'error': str(e)
            }
    
    async def _find_patterns_for_devices(
        self,
        device_ids: List[str],
        min_confidence: float
    ) -> List[Pattern]:
        """
        Find patterns that involve any of the given devices.
        
        Args:
            device_ids: List of device IDs
            min_confidence: Minimum pattern confidence
            
        Returns:
            List of Pattern instances
        """
        try:
            # Build query to find patterns matching any device
            conditions = []
            for device_id in device_ids:
                # Pattern device_id can be a single device or a combination (e.g., "device1+device2")
                conditions.append(Pattern.device_id.like(f"%{device_id}%"))
            
            if not conditions:
                return []
            
            # Use OR to match any condition
            from sqlalchemy import or_
            # Check if session is in a good state before querying
            from sqlalchemy.exc import PendingRollbackError
            try:
                # Try a simple query to check session health
                if hasattr(self.db, 'in_transaction') and self.db.in_transaction():
                    test_query = select(1)
                    await self.db.execute(test_query)
            except (PendingRollbackError, Exception) as e:
                logger.warning(f"Database session in bad state, cannot query patterns: {e}")
                return []
            
            query = select(Pattern).where(
                or_(*conditions),
                Pattern.confidence >= min_confidence
            )
            
            try:
                result = await self.db.execute(query)
                patterns = result.scalars().all()
            except (PendingRollbackError, Exception) as e:
                logger.warning(f"Error querying patterns: {e}")
                return []
            
            # Filter to only patterns that actually involve these devices
            matching_patterns = []
            for pattern in patterns:
                pattern_devices = self._extract_devices_from_pattern(pattern)
                if any(dev in pattern_devices for dev in device_ids):
                    matching_patterns.append(pattern)
            
            return matching_patterns
            
        except Exception as e:
            logger.error(f"Failed to find patterns for devices: {e}", exc_info=True)
            return []
    
    def _extract_devices_from_pattern(self, pattern: Pattern) -> List[str]:
        """
        Extract device IDs from a pattern.
        
        Handles both single device and combined device patterns.
        """
        device_id = pattern.device_id
        
        # Check if it's a combined pattern (e.g., "device1+device2")
        if '+' in device_id:
            return device_id.split('+')
        else:
            return [device_id]
    
    def _calculate_support_score(
        self,
        synergy: Dict,
        patterns: List[Pattern],
        device_ids: List[str]
    ) -> Tuple[float, List[Dict], List[Dict]]:
        """
        Calculate pattern support score for a synergy using multi-criteria approach.
        
        Quality Improvement: Priority 2.2 - Enhanced validation with multiple criteria:
        - Direct co-occurrence pattern (0.5 weight)
        - Sequence pattern where trigger → action (0.3 weight)
        - Temporal alignment (time-of-day overlap, 0.2 weight)
        - Context alignment (both respond to context, 0.2 weight)
        
        Args:
            synergy: Synergy opportunity dictionary
            patterns: List of relevant patterns
            device_ids: Device IDs in the synergy
            
        Returns:
            Tuple of (support_score, supporting_patterns, conflicting_patterns)
        """
        supporting_patterns = []
        conflicting_patterns = []
        
        # Extract trigger and action entities from synergy
        trigger_entity = synergy.get('opportunity_metadata', {}).get('trigger_entity_id') or synergy.get('trigger_entity')
        action_entity = synergy.get('opportunity_metadata', {}).get('action_entity_id') or synergy.get('action_entity')
        
        if not trigger_entity or not action_entity:
            # Fallback to device_ids if metadata not available
            if len(device_ids) >= 2:
                trigger_entity = device_ids[0]
                action_entity = device_ids[1]
            else:
                trigger_entity = device_ids[0] if device_ids else None
                action_entity = None
        
        support_score = 0.0
        supporting_pattern_ids = []
        
        # Criterion 1: Direct co-occurrence pattern (0.5 weight)
        for pattern in patterns:
            if pattern.pattern_type == 'co_occurrence':
                pattern_devices = self._extract_devices_from_pattern(pattern)
                if trigger_entity and action_entity:
                    if ((trigger_entity in pattern_devices and action_entity in pattern_devices) or
                        (action_entity in pattern_devices and trigger_entity in pattern_devices)):
                        # Direct match - strong support
                        contribution = pattern.confidence * 0.5
                        support_score += contribution
                        supporting_pattern_ids.append(pattern.id)
                        supporting_patterns.append({
                            'pattern_id': pattern.id,
                            'pattern_type': pattern.pattern_type,
                            'device_id': pattern.device_id,
                            'confidence': pattern.confidence,
                            'criterion': 'direct_co_occurrence',
                            'weight': 0.5,
                            'score_contribution': contribution
                        })
        
        # Criterion 2: Sequence pattern where trigger → action (0.3 weight)
        for pattern in patterns:
            if pattern.pattern_type == 'sequence':
                pattern_metadata = pattern.pattern_metadata or {}
                sequence_devices = pattern_metadata.get('sequence_devices', [])
                
                if trigger_entity and action_entity and sequence_devices:
                    # Check if trigger → action appears in sequence
                    if trigger_entity in sequence_devices and action_entity in sequence_devices:
                        trigger_idx = sequence_devices.index(trigger_entity)
                        action_idx = sequence_devices.index(action_entity)
                        
                        if action_idx > trigger_idx:  # Action comes after trigger
                            contribution = pattern.confidence * 0.3
                            support_score += contribution
                            if pattern.id not in supporting_pattern_ids:
                                supporting_pattern_ids.append(pattern.id)
                                supporting_patterns.append({
                                    'pattern_id': pattern.id,
                                    'pattern_type': pattern.pattern_type,
                                    'device_id': pattern.device_id,
                                    'confidence': pattern.confidence,
                                    'criterion': 'sequence_pattern',
                                    'weight': 0.3,
                                    'score_contribution': contribution
                                })
        
        # Criterion 3: Temporal alignment (time-of-day overlap, 0.2 weight)
        trigger_time_patterns = [p for p in patterns 
                                if p.pattern_type == 'time_of_day' and 
                                (trigger_entity in self._extract_devices_from_pattern(p) if trigger_entity else False)]
        action_time_patterns = [p for p in patterns 
                               if p.pattern_type == 'time_of_day' and 
                               (action_entity in self._extract_devices_from_pattern(p) if action_entity else False)]
        
        for t_pattern in trigger_time_patterns:
            for a_pattern in action_time_patterns:
                t_metadata = t_pattern.pattern_metadata or {}
                a_metadata = a_pattern.pattern_metadata or {}
                t_hour = t_metadata.get('hour') or t_pattern.device_id  # Fallback
                t_minute = t_metadata.get('minute', 0)
                a_hour = a_metadata.get('hour') or a_pattern.device_id  # Fallback
                a_minute = a_metadata.get('minute', 0)
                
                # Check if times are within 30 minutes
                if isinstance(t_hour, int) and isinstance(a_hour, int):
                    diff_minutes = abs((t_hour * 60 + t_minute) - (a_hour * 60 + a_minute))
                    if diff_minutes <= 30:
                        contribution = min(t_pattern.confidence, a_pattern.confidence) * 0.2
                        support_score += contribution
                        # Note: Don't add to supporting_patterns (indirect support)
        
        # Criterion 4: Context alignment (both respond to context, 0.2 weight)
        trigger_context_patterns = [p for p in patterns 
                                   if p.pattern_type == 'contextual' and 
                                   (trigger_entity in self._extract_devices_from_pattern(p) if trigger_entity else False)]
        action_context_patterns = [p for p in patterns 
                                  if p.pattern_type == 'contextual' and 
                                  (action_entity in self._extract_devices_from_pattern(p) if action_entity else False)]
        
        if trigger_context_patterns and action_context_patterns:
            # Both respond to context - likely related
            avg_confidence = (sum(p.confidence for p in trigger_context_patterns) / len(trigger_context_patterns) +
                            sum(p.confidence for p in action_context_patterns) / len(action_context_patterns)) / 2
            contribution = avg_confidence * 0.2
            support_score += contribution
        
        # Normalize score to [0, 1]
        support_score = min(1.0, support_score)
        
        return support_score, supporting_patterns, conflicting_patterns
    
    def _calculate_pattern_relevance(
        self,
        pattern: Pattern,
        synergy_type: str,
        device_ids: List[str]
    ) -> float:
        """
        Calculate how relevant a pattern is to a synergy.
        
        Returns:
            Relevance score: positive for supporting, negative for conflicting, 0 for neutral
        """
        pattern_devices = self._extract_devices_from_pattern(pattern)
        
        # Check device overlap
        overlap = set(pattern_devices) & set(device_ids)
        if not overlap:
            return 0.0  # No overlap, neutral
        
        # Calculate relevance based on pattern type and synergy type
        relevance = 0.5  # Base relevance for device overlap
        
        # Pattern type adjustments
        if pattern.pattern_type == 'co_occurrence' and synergy_type == 'device_pair':
            # Co-occurrence patterns strongly support device_pair synergies
            relevance = 1.0
        elif pattern.pattern_type == 'time_of_day' and synergy_type == 'device_pair':
            # Time-of-day patterns are less relevant for device_pair synergies
            relevance = 0.3
        elif pattern.pattern_type == 'sequence' and synergy_type == 'device_pair':
            # Sequence patterns are very relevant
            relevance = 1.0
        
        # Weight by device overlap percentage
        overlap_ratio = len(overlap) / max(len(pattern_devices), len(device_ids))
        relevance *= overlap_ratio
        
        return relevance
    
    def _determine_validation_status(
        self,
        support_score: float,
        num_supporting: int,
        num_conflicting: int
    ) -> str:
        """
        Determine validation status based on support score and pattern counts.
        
        Returns:
            'valid' | 'warning' | 'invalid'
        """
        if support_score >= 0.7 and num_supporting > 0 and num_conflicting == 0:
            return 'valid'
        elif support_score >= 0.4 or num_supporting > 0:
            return 'warning'
        else:
            return 'invalid'
    
    def _calculate_confidence_adjustment(self, support_score: float) -> float:
        """
        Calculate recommended confidence adjustment based on support score.
        
        Returns:
            Adjustment value (-0.2 to +0.2)
        """
        if support_score >= 0.7:
            return 0.15  # Strong boost
        elif support_score >= 0.5:
            return 0.05  # Moderate boost
        elif support_score >= 0.3:
            return 0.0   # Neutral
        else:
            return -0.1  # Reduction



