"""
Synergy Quality Scorer Service

2025 Enhancement: Comprehensive quality scoring for synergies with filtering decisions.

Calculates quality scores based on:
- Impact score (25%)
- Confidence (20%)
- Pattern support score (15%)
- Validation bonuses (25%)
- Complexity adjustment (15%)

Provides filtering decisions based on quality thresholds.
"""

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class SynergyQualityScorer:
    """
    Calculate quality scores for synergies and determine filtering decisions.
    
    2025 Best Practice: Centralized quality scoring with configurable thresholds.
    """
    
    # Quality tier thresholds
    QUALITY_TIER_HIGH = 0.70
    QUALITY_TIER_MEDIUM = 0.50
    QUALITY_TIER_LOW = 0.30
    
    # Default filtering thresholds
    DEFAULT_MIN_QUALITY_SCORE = 0.30
    DEFAULT_MIN_CONFIDENCE = 0.50
    DEFAULT_MIN_IMPACT = 0.30
    DEFAULT_MIN_PATTERN_SUPPORT = 0.30
    
    def calculate_quality_score(
        self,
        synergy: dict[str, Any],
        active_devices: set[str] | None = None,
        blueprint_fit_score: float | None = None
    ) -> dict[str, Any]:
        """
        Calculate comprehensive quality score for a synergy.
        
        Quality Score Formula:
        - Base metrics (60%): impact_score*0.25 + confidence*0.20 + pattern_support_score*0.15
        - Validation bonuses (25%): pattern_validation (0.10) + active_devices (0.10) + blueprint (0.05)
        - Complexity adjustment (15%): low=+0.15, medium=0.0, high=-0.15
        
        Args:
            synergy: Synergy dictionary with required fields:
                - impact_score (float, 0.0-1.0)
                - confidence (float, 0.0-1.0)
                - pattern_support_score (float, 0.0-1.0, optional, defaults to 0.0)
                - validated_by_patterns (bool, optional, defaults to False)
                - complexity (str, 'low'|'medium'|'high', optional, defaults to 'medium')
                - devices (list, optional, for active device check)
            active_devices: Set of active device IDs (optional)
            blueprint_fit_score: Blueprint fit score (optional, 0.0-1.0)
        
        Returns:
            Dictionary with:
            - quality_score: float (0.0-1.0)
            - quality_tier: str ('high'|'medium'|'low'|'poor')
            - score_breakdown: dict with component scores
        """
        # Extract base metrics with defaults
        impact_score = float(synergy.get('impact_score', 0.5))
        confidence = float(synergy.get('confidence', 0.7))
        pattern_support_score = float(synergy.get('pattern_support_score', 0.0))
        validated_by_patterns = bool(synergy.get('validated_by_patterns', False))
        complexity = str(synergy.get('complexity', 'medium')).lower()
        
        # Validate and clamp scores
        impact_score = max(0.0, min(1.0, impact_score))
        confidence = max(0.0, min(1.0, confidence))
        pattern_support_score = max(0.0, min(1.0, pattern_support_score))
        
        # Base metrics (60%)
        base_score = (
            impact_score * 0.25 +
            confidence * 0.20 +
            pattern_support_score * 0.15
        )
        
        # Validation bonuses (25%)
        validation_bonus = 0.0
        
        # Pattern validation bonus
        if validated_by_patterns:
            validation_bonus += 0.10
        
        # Active devices bonus (check if all devices in synergy are active)
        if active_devices is not None:
            device_ids = synergy.get('devices', [])
            if device_ids and all(d in active_devices for d in device_ids):
                validation_bonus += 0.10
        
        # Blueprint fit bonus
        if blueprint_fit_score is not None and blueprint_fit_score > 0.7:
            validation_bonus += 0.05
        
        # Complexity adjustment (15%)
        complexity_adjustment = 0.0
        if complexity == 'low':
            complexity_adjustment = 0.15
        elif complexity == 'high':
            complexity_adjustment = -0.15
        # medium complexity: no adjustment (0.0)
        
        # Calculate final quality score
        quality_score = base_score + validation_bonus + complexity_adjustment
        
        # Clamp to [0.0, 1.0]
        quality_score = max(0.0, min(1.0, quality_score))
        
        # Determine quality tier
        if quality_score >= self.QUALITY_TIER_HIGH:
            quality_tier = 'high'
        elif quality_score >= self.QUALITY_TIER_MEDIUM:
            quality_tier = 'medium'
        elif quality_score >= self.QUALITY_TIER_LOW:
            quality_tier = 'low'
        else:
            quality_tier = 'poor'
        
        return {
            'quality_score': round(quality_score, 4),
            'quality_tier': quality_tier,
            'score_breakdown': {
                'base_score': round(base_score, 4),
                'validation_bonus': round(validation_bonus, 4),
                'complexity_adjustment': round(complexity_adjustment, 4),
                'impact_score': impact_score,
                'confidence': confidence,
                'pattern_support_score': pattern_support_score,
                'validated_by_patterns': validated_by_patterns,
                'complexity': complexity
            }
        }
    
    def should_filter_synergy(
        self,
        synergy: dict[str, Any],
        quality_score: float,
        config: dict[str, Any] | None = None
    ) -> tuple[bool, str | None]:
        """
        Determine if synergy should be filtered (hard filters + quality thresholds).
        
        Hard Filters (always filter):
        - Missing required fields (device_ids, impact_score, confidence)
        - Invalid synergy_type
        - Invalid complexity value
        - External data sources (sports, weather, calendar, energy APIs)
        
        Quality Filters (configurable):
        - Minimum quality score (default: 0.30)
        - Minimum confidence (default: 0.50)
        - Minimum impact score (default: 0.30)
        - Unvalidated high complexity (default: filter)
        
        Args:
            synergy: Synergy dictionary
            quality_score: Calculated quality score (0.0-1.0)
            config: Optional configuration dict with thresholds:
                - min_quality_score (default: 0.30)
                - min_confidence (default: 0.50)
                - min_impact (default: 0.30)
                - filter_unvalidated_high_complexity (default: True)
        
        Returns:
            Tuple of (should_filter: bool, reason: str | None)
        """
        if config is None:
            config = {}
        
        min_quality_score = config.get('min_quality_score', self.DEFAULT_MIN_QUALITY_SCORE)
        min_confidence = config.get('min_confidence', self.DEFAULT_MIN_CONFIDENCE)
        min_impact = config.get('min_impact', self.DEFAULT_MIN_IMPACT)
        filter_unvalidated_high_complexity = config.get('filter_unvalidated_high_complexity', True)
        
        # Hard filters: Missing required fields
        if not synergy.get('device_ids') and not synergy.get('devices'):
            return True, "Missing device_ids"
        
        if 'impact_score' not in synergy:
            return True, "Missing impact_score"
        
        if 'confidence' not in synergy:
            return True, "Missing confidence"
        
        # Hard filters: Invalid values
        synergy_type = synergy.get('synergy_type', '')
        valid_types = {'device_pair', 'device_chain', 'event_context'}
        if synergy_type and synergy_type not in valid_types:
            return True, f"Invalid synergy_type: {synergy_type}"
        
        complexity = str(synergy.get('complexity', 'medium')).lower()
        if complexity not in {'low', 'medium', 'high'}:
            return True, f"Invalid complexity: {complexity}"
        
        # Hard filters: External data sources
        device_ids = synergy.get('devices', synergy.get('device_ids', []))
        if isinstance(device_ids, str):
            # Try to parse JSON if it's a string
            try:
                import json
                device_ids = json.loads(device_ids)
            except (json.JSONDecodeError, TypeError):
                device_ids = []
        
        if device_ids:
            external_patterns = [
                'team_tracker', 'nfl_', 'nhl_', 'mlb_', 'nba_', 'ncaa_',  # Sports
                'weather', 'openweathermap',  # Weather
                'carbon_intensity', 'electricity_pricing', 'national_grid',  # Energy
                'calendar'  # Calendar
            ]
            
            device_ids_str = ' '.join(str(d) for d in device_ids).lower()
            if any(pattern in device_ids_str for pattern in external_patterns):
                return True, "External data source (sports/weather/calendar/energy)"
        
        # Quality filters: Minimum thresholds
        if quality_score < min_quality_score:
            return True, f"Quality score {quality_score:.3f} below threshold {min_quality_score}"
        
        confidence = float(synergy.get('confidence', 0.0))
        if confidence < min_confidence:
            return True, f"Confidence {confidence:.3f} below threshold {min_confidence}"
        
        impact_score = float(synergy.get('impact_score', 0.0))
        if impact_score < min_impact:
            return True, f"Impact score {impact_score:.3f} below threshold {min_impact}"
        
        # Quality filter: Unvalidated high complexity
        if filter_unvalidated_high_complexity:
            validated_by_patterns = bool(synergy.get('validated_by_patterns', False))
            if complexity == 'high' and not validated_by_patterns:
                return True, "High complexity without pattern validation"
        
        # No filtering needed
        return False, None
