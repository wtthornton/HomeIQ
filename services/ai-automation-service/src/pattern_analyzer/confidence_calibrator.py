"""
Confidence Calibrator

Calibrates pattern confidence scores based on historical user feedback.
Makes confidence scores predictive of user acceptance.

Quality Improvement: Priority 1.3
"""

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class ConfidenceCalibrator:
    """
    Calibrate confidence scores using historical user feedback.
    
    Concept: Track which patterns → suggestions → deployments
    Learn what confidence scores actually mean in terms of user acceptance.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.calibration_data = {}  # Cache calibration curves

    async def calibrate_pattern_confidence(self, pattern: dict) -> float:
        """
        Adjust pattern confidence based on historical acceptance.
        
        Formula:
        calibrated_confidence = raw_confidence × acceptance_rate_factor
        
        Where acceptance_rate_factor is learned from historical data.
        
        Args:
            pattern: Pattern dictionary with 'pattern_type' and 'confidence'
            
        Returns:
            Calibrated confidence score (0.0-1.0)
        """
        pattern_type = pattern.get('pattern_type', 'unknown')
        raw_confidence = pattern.get('confidence', 0.5)

        # Get historical acceptance rate for similar patterns
        acceptance_data = await self._get_acceptance_data(
            pattern_type=pattern_type,
            confidence_range=(max(0.0, raw_confidence - 0.1), min(1.0, raw_confidence + 0.1)),
            min_samples=10  # Need at least 10 samples
        )

        if not acceptance_data or acceptance_data['sample_count'] < 10:
            # Not enough data, use conservative adjustment
            return raw_confidence * 0.95  # Slight downward bias until proven

        # Calculate calibration factor
        acceptance_rate = acceptance_data['accepted'] / acceptance_data['total']

        # Calibration logic:
        # - If acceptance > 80%: Boost confidence (pattern type is reliable)
        # - If acceptance 50-80%: Keep as-is
        # - If acceptance < 50%: Reduce confidence (pattern type has issues)

        if acceptance_rate >= 0.8:
            calibration_factor = 1.0 + (acceptance_rate - 0.8) * 0.5  # Max 1.1x boost
        elif acceptance_rate >= 0.5:
            calibration_factor = 1.0  # No change
        else:
            calibration_factor = 0.7 + acceptance_rate * 0.6  # Down to 0.7x

        calibrated = raw_confidence * calibration_factor
        calibrated = max(0.0, min(1.0, calibrated))  # Clamp to [0, 1]

        logger.debug(
            f"Calibrated {pattern_type} confidence: "
            f"{raw_confidence:.3f} → {calibrated:.3f} "
            f"(acceptance: {acceptance_rate:.1%})"
        )

        return calibrated

    async def _get_acceptance_data(
        self,
        pattern_type: str,
        confidence_range: tuple[float, float],
        min_samples: int
    ) -> dict | None:
        """
        Query historical acceptance rates for patterns in confidence range.
        
        Args:
            pattern_type: Type of pattern (e.g., 'co_occurrence', 'time_of_day')
            confidence_range: (min_confidence, max_confidence) tuple
            min_samples: Minimum number of samples required
            
        Returns:
            Dictionary with 'total', 'accepted', 'sample_count', or None if insufficient data
        """
        try:
            # Query suggestions derived from patterns in this confidence range
            query = text("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN s.status IN ('deployed', 'yaml_generated', 'approved') THEN 1 ELSE 0 END) as accepted
                FROM suggestions s
                JOIN patterns p ON s.pattern_id = p.id
                WHERE 
                    p.pattern_type = :pattern_type
                    AND p.confidence BETWEEN :min_conf AND :max_conf
            """)

            result = await self.db.execute(
                query,
                {
                    'pattern_type': pattern_type,
                    'min_conf': confidence_range[0],
                    'max_conf': confidence_range[1]
                }
            )

            row = result.fetchone()

            if not row or row.total < min_samples:
                return None

            return {
                'total': row.total,
                'accepted': row.accepted or 0,
                'sample_count': row.total
            }

        except Exception as e:
            logger.warning(f"Failed to get acceptance data for {pattern_type}: {e}")
            return None

    async def generate_calibration_report(self) -> dict:
        """
        Generate report on pattern type reliability.
        
        Returns:
            Dictionary mapping pattern_type to reliability metrics
        """
        report = {}

        pattern_types = [
            'time_of_day', 'co_occurrence', 'sequence',
            'contextual', 'multi_factor', 'room_based',
            'session', 'duration', 'anomaly'
        ]

        for pattern_type in pattern_types:
            # Get acceptance rate for this pattern type
            acceptance_data = await self._get_acceptance_data(
                pattern_type=pattern_type,
                confidence_range=(0.0, 1.0),  # All confidence levels
                min_samples=5
            )

            if acceptance_data:
                acceptance_rate = acceptance_data['accepted'] / acceptance_data['total']
                report[pattern_type] = {
                    'acceptance_rate': acceptance_rate,
                    'sample_count': acceptance_data['total'],
                    'reliability': (
                        'high' if acceptance_rate >= 0.7 else
                        'medium' if acceptance_rate >= 0.5 else 'low'
                    )
                }
            else:
                report[pattern_type] = {
                    'acceptance_rate': None,
                    'sample_count': 0,
                    'reliability': 'unknown'
                }

        return report

    async def calibrate_patterns_batch(self, patterns: list[dict]) -> list[dict]:
        """
        Calibrate confidence for a batch of patterns.
        
        Args:
            patterns: List of pattern dictionaries
            
        Returns:
            List of patterns with calibrated confidence scores
        """
        calibrated_patterns = []

        for pattern in patterns:
            # Store raw confidence
            pattern['raw_confidence'] = pattern.get('confidence', 0.5)

            # Calibrate
            calibrated_confidence = await self.calibrate_pattern_confidence(pattern)
            pattern['confidence'] = calibrated_confidence
            pattern['calibrated'] = True

            calibrated_patterns.append(pattern)

        logger.info(
            f"✅ Calibrated {len(calibrated_patterns)} pattern confidences "
            f"(raw avg: {sum(p.get('raw_confidence', 0) for p in patterns) / len(patterns):.3f}, "
            f"calibrated avg: {sum(p.get('confidence', 0) for p in calibrated_patterns) / len(calibrated_patterns):.3f})"
        )

        return calibrated_patterns

