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
            query = select(Pattern).where(
                or_(*conditions),
                Pattern.confidence >= min_confidence
            )
            
            result = await self.db.execute(query)
            patterns = result.scalars().all()
            
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
        Calculate pattern support score for a synergy.
        
        Args:
            synergy: Synergy opportunity dictionary
            patterns: List of relevant patterns
            device_ids: Device IDs in the synergy
            
        Returns:
            Tuple of (support_score, supporting_patterns, conflicting_patterns)
        """
        supporting_patterns = []
        conflicting_patterns = []
        total_score = 0.0
        max_score = 0.0
        
        synergy_type = synergy.get('synergy_type', 'device_pair')
        
        for pattern in patterns:
            pattern_info = {
                'pattern_id': pattern.id,
                'pattern_type': pattern.pattern_type,
                'device_id': pattern.device_id,
                'confidence': pattern.confidence,
                'trend_direction': pattern.trend_direction,
                'trend_strength': pattern.trend_strength
            }
            
            # Calculate pattern relevance score
            relevance = self._calculate_pattern_relevance(pattern, synergy_type, device_ids)
            
            if relevance > 0:
                # Supporting pattern
                # Weight by pattern confidence and type relevance
                pattern_score = pattern.confidence * relevance
                
                # Boost if pattern is increasing in confidence
                if pattern.trend_direction == 'increasing':
                    pattern_score *= 1.2
                
                # Boost co-occurrence patterns for device_pair synergies
                if synergy_type == 'device_pair' and pattern.pattern_type == 'co_occurrence':
                    pattern_score *= 1.2
                # Less weight for time-of-day patterns in device_pair synergies
                elif synergy_type == 'device_pair' and pattern.pattern_type == 'time_of_day':
                    pattern_score *= 0.8
                
                supporting_patterns.append({
                    **pattern_info,
                    'relevance': relevance,
                    'score_contribution': pattern_score
                })
                total_score += pattern_score
                
            elif relevance < 0:
                # Conflicting pattern
                conflicting_patterns.append({
                    **pattern_info,
                    'relevance': relevance,
                    'conflict_strength': abs(relevance)
                })
                # Reduce score for conflicts
                total_score -= abs(relevance) * pattern.confidence * 0.5
            
            max_score += pattern.confidence
        
        # Normalize score to 0-1 range
        if max_score > 0:
            support_score = max(0.0, min(1.0, total_score / max_score))
        else:
            support_score = 0.0
        
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

