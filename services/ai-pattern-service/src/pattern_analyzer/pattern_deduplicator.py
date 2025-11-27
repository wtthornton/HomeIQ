"""
Pattern Deduplicator

Removes duplicate and near-duplicate patterns.
Consolidates similar patterns into single high-quality patterns.

Quality Improvement: Priority 3.1
Epic 39, Story 39.5: Extracted to ai-pattern-service.
"""

import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class PatternDeduplicator:
    """Remove duplicate and near-duplicate patterns"""

    def deduplicate_patterns(self, patterns: list[dict]) -> list[dict]:
        """
        Remove duplicates and consolidate near-duplicates.
        
        Duplicates:
        - Exact same device, type, and metadata
        
        Near-duplicates (consolidate):
        - Same device, same type, similar time (within 15 min)
        - Same devices, same type, slight variation
        
        Args:
            patterns: List of pattern dictionaries
            
        Returns:
            Deduplicated list of patterns
        """
        if not patterns:
            return []

        deduplicated = []
        seen_signatures = set()

        # Group by device and type
        grouped = defaultdict(list)
        for pattern in patterns:
            pattern_type = pattern.get('pattern_type', 'unknown')
            device_id = pattern.get('device_id') or pattern.get('device1')
            key = (pattern_type, device_id)
            grouped[key].append(pattern)

        for (pattern_type, device_id), group in grouped.items():
            if pattern_type == 'time_of_day':
                # Consolidate time patterns within 15 minutes
                consolidated = self._consolidate_time_patterns(group)
                deduplicated.extend(consolidated)

            elif pattern_type == 'co_occurrence':
                # Remove exact duplicates
                unique = self._remove_exact_duplicates(group)
                deduplicated.extend(unique)

            else:
                # For other types, remove exact duplicates only
                unique = self._remove_exact_duplicates(group)
                deduplicated.extend(unique)

        removed_count = len(patterns) - len(deduplicated)
        logger.info(
            f"🧹 Deduplicated: {len(patterns)} → {len(deduplicated)} patterns "
            f"({removed_count} removed)"
        )

        return deduplicated

    def _consolidate_time_patterns(self, patterns: list[dict]) -> list[dict]:
        """Consolidate time patterns within 15-minute window"""

        if not patterns:
            return []

        # Sort by time
        def get_time_key(pattern):
            metadata = pattern.get('pattern_metadata', {})
            hour = metadata.get('hour') or pattern.get('hour', 0)
            minute = metadata.get('minute') or pattern.get('minute', 0)
            return (hour, minute)

        sorted_patterns = sorted(patterns, key=get_time_key)

        consolidated = []
        current_cluster = [sorted_patterns[0]]

        for pattern in sorted_patterns[1:]:
            # Check if within 15 minutes of cluster average
            cluster_avg_time = self._average_time(current_cluster)
            pattern_time = get_time_key(pattern)

            diff_minutes = self._time_diff_minutes(cluster_avg_time, pattern_time)

            if diff_minutes <= 15:
                # Add to cluster
                current_cluster.append(pattern)
            else:
                # Close current cluster, start new one
                consolidated_pattern = self._merge_cluster(current_cluster)
                consolidated.append(consolidated_pattern)
                current_cluster = [pattern]

        # Add final cluster
        if current_cluster:
            consolidated_pattern = self._merge_cluster(current_cluster)
            consolidated.append(consolidated_pattern)

        return consolidated

    def _average_time(self, patterns: list[dict]) -> tuple[int, int]:
        """Calculate average time from a list of time patterns"""
        total_minutes = 0
        count = 0

        for pattern in patterns:
            metadata = pattern.get('pattern_metadata', {})
            hour = metadata.get('hour') or pattern.get('hour', 0)
            minute = metadata.get('minute') or pattern.get('minute', 0)
            total_minutes += hour * 60 + minute
            count += 1

        if count == 0:
            return (0, 0)

        avg_minutes = total_minutes // count
        return (avg_minutes // 60, avg_minutes % 60)

    def _time_diff_minutes(self, time1: tuple[int, int], time2: tuple[int, int]) -> int:
        """Calculate time difference in minutes"""
        minutes1 = time1[0] * 60 + time1[1]
        minutes2 = time2[0] * 60 + time2[1]
        return abs(minutes1 - minutes2)

    def _merge_cluster(self, cluster: list[dict]) -> dict:
        """Merge cluster of similar patterns into one"""

        if len(cluster) == 1:
            return cluster[0]

        # Use highest confidence pattern as base
        base = max(cluster, key=lambda p: p.get('confidence', 0))

        # Average the times
        avg_time = self._average_time(cluster)
        metadata = base.get('pattern_metadata', {})
        metadata['hour'] = avg_time[0]
        metadata['minute'] = avg_time[1]
        base['pattern_metadata'] = metadata

        # Sum occurrences
        base['occurrences'] = sum(p.get('occurrences', 0) for p in cluster)

        # Boost confidence (multiple similar patterns = more confident)
        base['confidence'] = min(1.0, base.get('confidence', 0.5) * 1.1)

        # Note consolidation in metadata
        if 'consolidated_from' not in metadata:
            metadata['consolidated_from'] = len(cluster)
        base['pattern_metadata'] = metadata

        return base

    def _remove_exact_duplicates(self, patterns: list[dict]) -> list[dict]:
        """Remove exact duplicate patterns"""

        seen = set()
        unique = []

        for pattern in patterns:
            # Create signature from key fields
            signature = self._create_pattern_signature(pattern)

            if signature not in seen:
                seen.add(signature)
                unique.append(pattern)

        return unique

    def _create_pattern_signature(self, pattern: dict) -> str:
        """Create a unique signature for a pattern to detect duplicates"""

        pattern_type = pattern.get('pattern_type', '')
        device_id = pattern.get('device_id', '')
        device1 = pattern.get('device1', '')
        device2 = pattern.get('device2', '')
        metadata = pattern.get('pattern_metadata', {})

        # For time patterns, include hour and minute
        if pattern_type == 'time_of_day':
            hour = metadata.get('hour') or pattern.get('hour', 0)
            minute = metadata.get('minute') or pattern.get('minute', 0)
            return f"{pattern_type}:{device_id}:{hour}:{minute}"

        # For co-occurrence, include both devices
        elif pattern_type == 'co_occurrence':
            devices = tuple(sorted([device1, device2])) if device1 and device2 else (device_id,)
            return f"{pattern_type}:{devices}"

        # For other types, use device_id
        else:
            return f"{pattern_type}:{device_id}"

