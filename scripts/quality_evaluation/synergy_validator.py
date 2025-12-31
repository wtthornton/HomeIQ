"""
Synergy Validator for Quality Evaluation

Validates synergies against actual events.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

# Add services path for synergy detector
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "services" / "ai-pattern-service" / "src"))

try:
    from synergy_detection.synergy_detector import DeviceSynergyDetector
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("Could not import synergy detector - synergy validation will be limited")
    DeviceSynergyDetector = None

logger = logging.getLogger(__name__)


class SynergyValidator:
    """Validates synergies against actual events."""
    
    def __init__(self):
        """Initialize synergy detector."""
        self.detector = None
        if DeviceSynergyDetector:
            self.detector = DeviceSynergyDetector()
    
    async def validate_synergies(
        self,
        stored_synergies: List[Dict[str, Any]],
        events_df: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Validate stored synergies against events.
        
        Args:
            stored_synergies: List of stored synergy dictionaries
            events_df: DataFrame containing events
            
        Returns:
            Validation results dictionary
        """
        if events_df.empty:
            return {
                'status': 'skipped',
                'reason': 'No events available'
            }
        
        logger.info(f"Validating {len(stored_synergies)} synergies against events...")
        
        # Re-detect synergies from events (simplified - would need devices/entities)
        # For now, we'll do basic validation without full re-detection
        validated_count = 0
        false_positives = []
        pattern_support_errors = []
        depth_errors = []
        
        # Create device set from events for basic validation
        devices_in_events = set()
        if 'device_id' in events_df.columns:
            devices_in_events = set(events_df['device_id'].dropna().unique())
        
        for stored in stored_synergies:
            device_ids = stored.get('device_ids', [])
            if isinstance(device_ids, str):
                try:
                    import json
                    device_ids = json.loads(device_ids)
                except (json.JSONDecodeError, TypeError):
                    device_ids = []
            
            # Basic validation: check if devices exist in events
            if isinstance(device_ids, list) and all(d in devices_in_events for d in device_ids):
                validated_count += 1
            else:
                false_positives.append({
                    'synergy_id': stored.get('synergy_id', 'unknown'),
                    'synergy_type': stored.get('synergy_type', 'unknown'),
                    'device_ids': device_ids,
                    'confidence': stored.get('confidence', 0.0)
                })
            
            # Check pattern support score
            pattern_support = stored.get('pattern_support_score', 0.0)
            validated_by_patterns = stored.get('validated_by_patterns', False)
            
            if pattern_support > 0.5 and not validated_by_patterns:
                pattern_support_errors.append({
                    'synergy_id': stored.get('synergy_id', 'unknown'),
                    'pattern_support_score': pattern_support,
                    'validated_by_patterns': validated_by_patterns
                })
        
        # Calculate metrics
        total_stored = len(stored_synergies)
        precision = validated_count / total_stored if total_stored > 0 else 0.0
        recall = precision  # Simplified - would need full re-detection for accurate recall
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        logger.info(f"Synergy validation: {validated_count}/{total_stored} validated, "
                   f"precision={precision:.2%}")
        
        return {
            'total_synergies': total_stored,
            'validated_synergies': validated_count,
            'false_positives': false_positives,
            'precision': precision,
            'recall': recall,
            'f1_score': f1_score,
            'pattern_support_errors': pattern_support_errors,
            'depth_errors': depth_errors
        }
    
    async def redetect_synergies(
        self,
        events_df: pd.DataFrame
    ) -> List[Dict[str, Any]]:
        """
        Re-detect synergies from events.
        
        Args:
            events_df: DataFrame containing events
            
        Returns:
            List of detected synergies
        """
        if not self.detector:
            logger.warning("Synergy detector not available - cannot re-detect")
            return []
        
        # Would need devices and entities for full detection
        # For now, return empty list
        logger.warning("Full synergy re-detection requires devices/entities - skipping")
        return []
