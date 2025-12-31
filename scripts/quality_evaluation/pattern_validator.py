"""
Pattern Validator for Quality Evaluation

Validates patterns against actual events.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

# Add services path for pattern detectors
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "services" / "ai-pattern-service" / "src"))

try:
    from pattern_analyzer.co_occurrence import CoOccurrencePatternDetector
    from pattern_analyzer.time_of_day import TimeOfDayPatternDetector
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("Could not import pattern detectors - pattern validation will be limited")
    CoOccurrencePatternDetector = None
    TimeOfDayPatternDetector = None

logger = logging.getLogger(__name__)


class PatternValidator:
    """Validates patterns against actual events."""
    
    def __init__(self):
        """Initialize pattern detectors."""
        self.tod_detector = None
        self.co_detector = None
        
        if TimeOfDayPatternDetector:
            self.tod_detector = TimeOfDayPatternDetector(min_occurrences=3, min_confidence=0.6)
        if CoOccurrencePatternDetector:
            self.co_detector = CoOccurrencePatternDetector(
                min_support=0.1, min_confidence=0.5, window_minutes=5
            )
    
    async def validate_patterns(
        self,
        stored_patterns: List[Dict[str, Any]],
        events_df: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Validate stored patterns against events.
        
        Args:
            stored_patterns: List of stored pattern dictionaries
            events_df: DataFrame containing events
            
        Returns:
            Validation results dictionary
        """
        if events_df.empty:
            return {
                'status': 'skipped',
                'reason': 'No events available'
            }
        
        logger.info(f"Validating {len(stored_patterns)} patterns against events...")
        
        # Re-detect patterns from events
        redetected_patterns = await self.redetect_patterns(events_df)
        
        # Create lookup for redetected patterns
        redetected_lookup = {}
        for pattern in redetected_patterns:
            key = (pattern['pattern_type'], pattern['device_id'])
            redetected_lookup[key] = pattern
        
        # Validate stored patterns
        validated_count = 0
        false_positives = []
        confidence_errors = []
        
        for stored in stored_patterns:
            key = (stored['pattern_type'], stored['device_id'])
            
            if key in redetected_lookup:
                validated_count += 1
                redetected = redetected_lookup[key]
                
                # Check confidence accuracy
                confidence_diff = abs(stored['confidence'] - redetected['confidence'])
                if confidence_diff > 0.2:  # 20% threshold
                    confidence_errors.append({
                        'pattern_type': stored['pattern_type'],
                        'device_id': stored['device_id'],
                        'stored_confidence': stored['confidence'],
                        'actual_confidence': redetected['confidence'],
                        'difference': confidence_diff
                    })
            else:
                false_positives.append({
                    'pattern_type': stored['pattern_type'],
                    'device_id': stored['device_id'],
                    'confidence': stored['confidence'],
                    'occurrences': stored.get('occurrences', 0)
                })
        
        # Calculate metrics
        total_stored = len(stored_patterns)
        total_redetected = len(redetected_patterns)
        
        precision = validated_count / total_stored if total_stored > 0 else 0.0
        recall = validated_count / total_redetected if total_redetected > 0 else 0.0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        logger.info(f"Pattern validation: {validated_count}/{total_stored} validated, "
                   f"precision={precision:.2%}, recall={recall:.2%}, F1={f1_score:.2%}")
        
        return {
            'total_patterns': total_stored,
            'validated_patterns': validated_count,
            'false_positives': false_positives,
            'precision': precision,
            'recall': recall,
            'f1_score': f1_score,
            'confidence_errors': confidence_errors,
            'redetected_count': total_redetected
        }
    
    async def redetect_patterns(
        self,
        events_df: pd.DataFrame
    ) -> List[Dict[str, Any]]:
        """
        Re-detect patterns from events using same algorithms.
        
        Args:
            events_df: DataFrame containing events
            
        Returns:
            List of detected patterns
        """
        all_patterns = []
        
        # Time-of-day patterns
        if self.tod_detector:
            try:
                tod_patterns = await asyncio.to_thread(
                    self.tod_detector.detect_patterns,
                    events_df
                )
                all_patterns.extend(tod_patterns)
                logger.debug(f"Re-detected {len(tod_patterns)} time-of-day patterns")
            except Exception as e:
                logger.warning(f"Time-of-day detection failed: {e}")
        
        # Co-occurrence patterns
        if self.co_detector:
            try:
                co_patterns = await asyncio.to_thread(
                    self.co_detector.detect_patterns,
                    events_df
                )
                all_patterns.extend(co_patterns)
                logger.debug(f"Re-detected {len(co_patterns)} co-occurrence patterns")
            except Exception as e:
                logger.warning(f"Co-occurrence detection failed: {e}")
        
        return all_patterns
