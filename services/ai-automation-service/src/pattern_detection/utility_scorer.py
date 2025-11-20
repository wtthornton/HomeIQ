"""
High Utility Pattern Mining

Scores patterns by utility (energy savings, time saved, user satisfaction)
rather than just frequency. Prioritizes high-utility patterns for automation suggestions.
"""

import logging

logger = logging.getLogger(__name__)


class PatternUtilityScorer:
    """
    Scores patterns by utility metrics:
    - Energy impact (potential energy savings)
    - Time savings (automation reduces manual actions)
    - User satisfaction (pattern reliability)
    - Frequency (occurrence rate)
    """

    # Energy-intensive device patterns have higher utility
    ENERGY_INTENSIVE_DEVICES = {
        'climate', 'heater', 'air_conditioner', 'ac', 'hvac', 'thermostat',
        'light', 'lamp', 'lighting', 'bulb', 'switch',
        'washer', 'dryer', 'dishwasher', 'oven', 'stove', 'fridge', 'refrigerator'
    }

    # Time-saving patterns (frequent manual actions)
    TIME_SAVING_PATTERNS = {
        'sequence',  # Multi-step sequences save time
        'session',   # Routine patterns save time
        'co_occurrence'  # Devices used together = automation opportunity
    }

    def __init__(
        self,
        energy_weight: float = 0.4,
        time_weight: float = 0.3,
        satisfaction_weight: float = 0.2,
        frequency_weight: float = 0.1
    ):
        """
        Initialize utility scorer.
        
        Args:
            energy_weight: Weight for energy savings utility (0-1)
            time_weight: Weight for time savings utility (0-1)
            satisfaction_weight: Weight for user satisfaction (0-1)
            frequency_weight: Weight for frequency/occurrence rate (0-1)
        """
        self.energy_weight = energy_weight
        self.time_weight = time_weight
        self.satisfaction_weight = satisfaction_weight
        self.frequency_weight = frequency_weight

        # Normalize weights to sum to 1.0
        total_weight = energy_weight + time_weight + satisfaction_weight + frequency_weight
        if total_weight > 0:
            self.energy_weight /= total_weight
            self.time_weight /= total_weight
            self.satisfaction_weight /= total_weight
            self.frequency_weight /= total_weight

        logger.info(f"PatternUtilityScorer initialized: energy={self.energy_weight:.2f}, time={self.time_weight:.2f}, satisfaction={self.satisfaction_weight:.2f}, frequency={self.frequency_weight:.2f}")

    def score_pattern(self, pattern: dict) -> dict[str, float]:
        """
        Calculate utility scores for a pattern.
        
        Args:
            pattern: Pattern dictionary
            
        Returns:
            Dictionary with utility scores:
            - energy_utility: Energy savings potential (0-1)
            - time_utility: Time savings potential (0-1)
            - satisfaction_utility: User satisfaction estimate (0-1)
            - frequency_utility: Occurrence frequency utility (0-1)
            - total_utility: Weighted total utility score (0-1)
        """
        energy_utility = self._calculate_energy_utility(pattern)
        time_utility = self._calculate_time_utility(pattern)
        satisfaction_utility = self._calculate_satisfaction_utility(pattern)
        frequency_utility = self._calculate_frequency_utility(pattern)

        # Weighted total utility
        total_utility = (
            self.energy_weight * energy_utility +
            self.time_weight * time_utility +
            self.satisfaction_weight * satisfaction_utility +
            self.frequency_weight * frequency_utility
        )

        return {
            'energy_utility': energy_utility,
            'time_utility': time_utility,
            'satisfaction_utility': satisfaction_utility,
            'frequency_utility': frequency_utility,
            'total_utility': total_utility
        }

    def _calculate_energy_utility(self, pattern: dict) -> float:
        """
        Calculate energy savings utility.
        
        Patterns involving energy-intensive devices or time-of-day
        optimizations have higher utility.
        """
        devices = pattern.get('devices', [])
        if isinstance(devices, str):
            devices = [devices]

        device_id = pattern.get('device_id', '')
        pattern_type = pattern.get('pattern_type', '')

        # Check if pattern involves energy-intensive devices
        device_names = ' '.join(devices).lower() + ' ' + device_id.lower()
        energy_intensive = any(
            device_keyword in device_names
            for device_keyword in self.ENERGY_INTENSIVE_DEVICES
        )

        if not energy_intensive:
            return 0.2  # Low utility for non-energy devices

        # Time-of-day patterns can optimize energy usage
        if pattern_type == 'time_of_day':
            metadata = pattern.get('metadata', {})
            hour = metadata.get('hour', metadata.get('typical_hour', 12))

            # Patterns during peak hours (morning/evening) have higher utility
            if 6 <= hour <= 9 or 17 <= hour <= 22:
                return 0.9
            elif 10 <= hour <= 16:
                return 0.7
            else:
                return 0.5

        # Co-occurrence patterns with energy devices
        if pattern_type == 'co_occurrence' and len(devices) >= 2:
            return 0.8

        # Session patterns with energy devices
        if pattern_type == 'session':
            return 0.7

        # Default for energy-intensive devices
        return 0.6

    def _calculate_time_utility(self, pattern: dict) -> float:
        """
        Calculate time savings utility.
        
        Patterns that automate frequent manual actions have higher utility.
        """
        pattern_type = pattern.get('pattern_type', '')
        occurrences = pattern.get('occurrences', 0)

        # Sequence patterns save the most time (multiple steps automated)
        if pattern_type == 'sequence':
            sequence_length = len(pattern.get('metadata', {}).get('sequence', []))
            # Longer sequences = more time saved
            base_utility = min(0.5 + (sequence_length - 2) * 0.15, 1.0)
            return base_utility

        # Session/routine patterns save time
        if pattern_type in ['session', 'routine']:
            return 0.7

        # Co-occurrence patterns (automate device pairs)
        if pattern_type == 'co_occurrence':
            return 0.6

        # Frequent patterns save more time
        if occurrences >= 20:
            return 0.8
        elif occurrences >= 10:
            return 0.6
        elif occurrences >= 5:
            return 0.4

        return 0.3

    def _calculate_satisfaction_utility(self, pattern: dict) -> float:
        """
        Calculate user satisfaction utility.
        
        Higher confidence and consistency = higher satisfaction.
        """
        confidence = pattern.get('confidence', 0.5)
        occurrences = pattern.get('occurrences', 0)

        # High confidence patterns are more reliable
        satisfaction = confidence

        # More occurrences = more reliable (user keeps doing it)
        occurrence_boost = min(occurrences / 30.0, 0.2)
        satisfaction = min(satisfaction + occurrence_boost, 1.0)

        # Time consistency boost
        time_consistency = pattern.get('time_consistency', 0.0)
        if time_consistency > 0:
            satisfaction = (satisfaction + time_consistency) / 2

        return satisfaction

    def _calculate_frequency_utility(self, pattern: dict) -> float:
        """
        Calculate frequency-based utility.
        
        More frequent patterns have higher utility (but less important than other factors).
        """
        occurrences = pattern.get('occurrences', 0)

        # Normalize to 0-1 (max at 30 occurrences)
        return min(occurrences / 30.0, 1.0)

    def add_utility_scores(self, patterns: list[dict]) -> list[dict]:
        """
        Add utility scores to list of patterns.
        
        Args:
            patterns: List of pattern dictionaries
            
        Returns:
            Patterns with utility scores added to metadata
        """
        for pattern in patterns:
            utility_scores = self.score_pattern(pattern)

            # Add utility scores to metadata
            if 'metadata' not in pattern:
                pattern['metadata'] = {}

            pattern['metadata']['utility'] = utility_scores
            pattern['utility_score'] = utility_scores['total_utility']

        # Sort by utility score (highest first)
        patterns.sort(key=lambda p: p.get('utility_score', 0), reverse=True)

        return patterns

    def get_high_utility_patterns(
        self,
        patterns: list[dict],
        min_utility: float = 0.6,
        max_results: int | None = None
    ) -> list[dict]:
        """
        Filter and return high-utility patterns.
        
        Args:
            patterns: List of patterns
            min_utility: Minimum utility score threshold
            max_results: Maximum number of patterns to return
            
        Returns:
            Filtered list of high-utility patterns
        """
        # Add utility scores if not already present
        patterns_with_utility = self.add_utility_scores(patterns)

        # Filter by minimum utility
        high_utility = [
            p for p in patterns_with_utility
            if p.get('utility_score', 0) >= min_utility
        ]

        # Limit results
        if max_results:
            high_utility = high_utility[:max_results]

        return high_utility

    def prioritize_for_suggestions(
        self,
        patterns: list[dict],
        max_suggestions: int = 10
    ) -> list[dict]:
        """
        Prioritize patterns for automation suggestions based on utility.
        
        Args:
            patterns: List of patterns
            max_suggestions: Maximum number of patterns to return
            
        Returns:
            Prioritized list of patterns sorted by utility
        """
        # Add utility scores
        patterns_with_utility = self.add_utility_scores(patterns)

        # Filter by minimum confidence (patterns should still be reliable)
        reliable_patterns = [
            p for p in patterns_with_utility
            if p.get('confidence', 0) >= 0.6  # Minimum confidence threshold
        ]

        # Sort by utility score (descending)
        prioritized = sorted(
            reliable_patterns,
            key=lambda p: p.get('utility_score', 0),
            reverse=True
        )

        return prioritized[:max_suggestions]

