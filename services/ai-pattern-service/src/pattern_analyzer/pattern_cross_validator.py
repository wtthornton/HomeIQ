"""
Pattern Cross-Validator

Cross-validates patterns for consistency and quality.
Identifies contradictions, redundancies, and reinforcements.

Quality Improvement: Priority 2.1
Epic 39, Story 39.5: Extracted to ai-pattern-service.
"""

import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class PatternCrossValidator:
    """Cross-validate patterns for consistency and quality"""

    async def cross_validate(self, patterns: list[dict]) -> dict:
        """
        Cross-validate patterns to find:
        1. Contradictions (pattern A says X, pattern B says not X)
        2. Redundancies (patterns that overlap)
        3. Reinforcements (patterns that support each other)
        
        Args:
            patterns: List of pattern dictionaries
            
        Returns:
            Dictionary with validation results and quality score
        """
        validation_results = {
            'contradictions': [],
            'redundancies': [],
            'reinforcements': [],
            'quality_score': 0.0
        }

        if not patterns:
            return validation_results

        # Group patterns by device
        by_device = defaultdict(list)
        for pattern in patterns:
            device_id = pattern.get('device_id') or pattern.get('device1')
            if device_id:
                by_device[device_id].append(pattern)

        # Check each device's patterns
        for device_id, device_patterns in by_device.items():
            # Find time-based patterns
            time_patterns = [p for p in device_patterns
                           if p['pattern_type'] == 'time_of_day']

            # Find co-occurrence patterns
            co_patterns = [p for p in device_patterns
                         if p['pattern_type'] == 'co_occurrence']

            # Check for contradictions
            # Example: Time pattern says "on at 7 AM" but co-occurrence shows
            #          it's always triggered by motion sensor
            if time_patterns and co_patterns:
                for time_p in time_patterns:
                    for co_p in co_patterns:
                        # If co-occurrence has very high confidence,
                        # time pattern might be spurious
                        if co_p['confidence'] > 0.9 and time_p['confidence'] < 0.75:
                            validation_results['contradictions'].append({
                                'device': device_id,
                                'time_pattern': {
                                    'id': time_p.get('id'),
                                    'confidence': time_p['confidence'],
                                    'hour': time_p.get('metadata', {}).get('hour'),
                                    'minute': time_p.get('metadata', {}).get('minute')
                                },
                                'co_pattern': {
                                    'id': co_p.get('id'),
                                    'confidence': co_p['confidence'],
                                    'device1': co_p.get('device1'),
                                    'device2': co_p.get('device2')
                                },
                                'reason': 'Strong co-occurrence suggests time pattern is spurious'
                            })

            # Check for reinforcements
            # Example: Time pattern "on at 7 AM" AND co-occurrence
            #          "motion + light at 7 AM" reinforce each other
            if len(time_patterns) > 1:
                # Multiple time patterns should cluster
                times = []
                for tp in time_patterns:
                    hour = tp.get('metadata', {}).get('hour') or tp.get('hour')
                    minute = tp.get('metadata', {}).get('minute') or tp.get('minute')
                    if hour is not None and minute is not None:
                        times.append((hour, minute))

                # Check if times are clustered (within 30 minutes)
                for i, time1 in enumerate(times):
                    for time2 in times[i+1:]:
                        diff_minutes = abs((time1[0] * 60 + time1[1]) -
                                         (time2[0] * 60 + time2[1]))
                        if diff_minutes <= 30:
                            validation_results['reinforcements'].append({
                                'device': device_id,
                                'pattern1': {
                                    'id': time_patterns[i].get('id'),
                                    'hour': time1[0],
                                    'minute': time1[1],
                                    'confidence': time_patterns[i]['confidence']
                                },
                                'pattern2': {
                                    'id': time_patterns[i+1].get('id'),
                                    'hour': time2[0],
                                    'minute': time2[1],
                                    'confidence': time_patterns[i+1]['confidence']
                                },
                                'reason': 'Consistent time patterns reinforce each other'
                            })

            # Check for redundancies (same pattern type, similar parameters)
            if len(co_patterns) > 1:
                # Group by device pairs
                pair_patterns = defaultdict(list)
                for co_p in co_patterns:
                    device1 = co_p.get('device1')
                    device2 = co_p.get('device2')
                    if device1 and device2:
                        pair = tuple(sorted([device1, device2]))
                        pair_patterns[pair].append(co_p)

                # Find redundant pairs (same devices, similar confidence)
                for pair, pair_list in pair_patterns.items():
                    if len(pair_list) > 1:
                        # Check if patterns are very similar
                        for i, p1 in enumerate(pair_list):
                            for p2 in pair_list[i+1:]:
                                conf_diff = abs(p1['confidence'] - p2['confidence'])
                                if conf_diff < 0.05:  # Very similar confidence
                                    validation_results['redundancies'].append({
                                        'device': device_id,
                                        'pattern1': {
                                            'id': p1.get('id'),
                                            'confidence': p1['confidence'],
                                            'occurrences': p1.get('occurrences', 0)
                                        },
                                        'pattern2': {
                                            'id': p2.get('id'),
                                            'confidence': p2['confidence'],
                                            'occurrences': p2.get('occurrences', 0)
                                        },
                                        'reason': 'Very similar patterns (likely duplicates)'
                                    })

        # Calculate overall quality score
        total_patterns = len(patterns)
        contradictions = len(validation_results['contradictions'])
        reinforcements = len(validation_results['reinforcements'])
        redundancies = len(validation_results['redundancies'])

        # Quality score: more reinforcements = better, contradictions = worse
        # Base score of 0.5, add for reinforcements, subtract for contradictions
        quality_score = 0.5 + (reinforcements * 0.1) - (contradictions * 0.2) - (redundancies * 0.05)
        quality_score = max(0.0, min(1.0, quality_score))  # Clamp to [0, 1]

        validation_results['quality_score'] = quality_score
        validation_results['summary'] = {
            'total_patterns': total_patterns,
            'contradictions': contradictions,
            'redundancies': redundancies,
            'reinforcements': reinforcements,
            'quality_score': quality_score
        }

        return validation_results

