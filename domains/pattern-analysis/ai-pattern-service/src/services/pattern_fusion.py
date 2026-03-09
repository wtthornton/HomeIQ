"""Cross-detector pattern fusion. Story 40.8."""
import logging
import uuid
from typing import Any

logger = logging.getLogger(__name__)

# Minimum entity overlap to consider patterns related
OVERLAP_THRESHOLD = 0.85


class PatternFusionEngine:
    """Combines outputs from multiple detectors to identify compound patterns."""

    def fuse_patterns(self, all_patterns: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Post-detection fusion step to find compound patterns."""
        if len(all_patterns) < 2:
            return all_patterns

        compound_patterns = []
        used_indices: set[int] = set()

        # Group patterns by device overlap
        for i in range(len(all_patterns)):
            if i in used_indices:
                continue
            pattern_a = all_patterns[i]
            entities_a = self._extract_entities(pattern_a)
            if not entities_a:
                continue

            related = [(i, pattern_a)]
            for j in range(i + 1, len(all_patterns)):
                if j in used_indices:
                    continue
                pattern_b = all_patterns[j]
                entities_b = self._extract_entities(pattern_b)
                if not entities_b:
                    continue

                # Check entity overlap
                overlap = len(entities_a & entities_b) / max(len(entities_a | entities_b), 1)
                if overlap >= OVERLAP_THRESHOLD:
                    related.append((j, pattern_b))

            # If multiple detectors found overlapping patterns, create compound
            if len(related) >= 2:
                types = {p['pattern_type'] for _, p in related}
                if len(types) >= 2:  # Different detector types
                    compound = self._create_compound(related)
                    compound_patterns.append(compound)
                    for idx, _ in related:
                        used_indices.add(idx)

        if compound_patterns:
            logger.info(f"Pattern fusion: {len(compound_patterns)} compound patterns from {len(used_indices)} source patterns")

        # Return: original patterns (minus consumed) + compound patterns
        remaining = [p for i, p in enumerate(all_patterns) if i not in used_indices]
        return remaining + compound_patterns

    def deduplicate(self, patterns: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Remove patterns with >85% entity overlap within same type."""
        if len(patterns) < 2:
            return patterns

        unique = []
        for pattern in patterns:
            entities = self._extract_entities(pattern)
            is_duplicate = False
            for existing in unique:
                if existing['pattern_type'] != pattern['pattern_type']:
                    continue
                existing_entities = self._extract_entities(existing)
                if not entities or not existing_entities:
                    continue
                overlap = len(entities & existing_entities) / max(len(entities | existing_entities), 1)
                if overlap > OVERLAP_THRESHOLD:
                    # Keep higher confidence
                    if pattern.get('confidence', 0) > existing.get('confidence', 0):
                        unique.remove(existing)
                        unique.append(pattern)
                    is_duplicate = True
                    break
            if not is_duplicate:
                unique.append(pattern)

        if len(unique) < len(patterns):
            logger.info(f"Deduplication: {len(patterns)} -> {len(unique)} patterns")
        return unique

    def _create_compound(self, related: list[tuple[int, dict]]) -> dict[str, Any]:
        """Create a compound pattern from related source patterns."""
        types = sorted({p['pattern_type'] for _, p in related})
        all_entities: set[str] = set()
        confidences = []
        source_ids = []

        for _, pattern in related:
            all_entities |= self._extract_entities(pattern)
            confidences.append(pattern.get('confidence', 0.0))
            source_ids.append(pattern.get('pattern_id', str(uuid.uuid4())[:8]))

        # Weighted average confidence
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        return {
            'pattern_type': 'compound',
            'device_id': sorted(all_entities)[0] if all_entities else 'unknown',
            'confidence': float(avg_confidence),
            'metadata': {
                'source_types': types,
                'source_count': len(related),
                'source_pattern_ids': source_ids,
                'all_entities': sorted(all_entities),
                'compound_description': f"{'+ '.join(types)} compound pattern",
            },
        }

    @staticmethod
    def _extract_entities(pattern: dict[str, Any]) -> set[str]:
        """Extract entity IDs from a pattern dict."""
        entities: set[str] = set()
        if 'device_id' in pattern and pattern['device_id']:
            # Handle combined IDs like "light.a+light.b"
            device_id = pattern['device_id']
            if '+' in device_id:
                entities.update(device_id.split('+'))
            else:
                entities.add(device_id)
        if 'device1' in pattern:
            entities.add(pattern['device1'])
        if 'device2' in pattern:
            entities.add(pattern['device2'])
        if 'sequence' in pattern:
            entities.update(pattern['sequence'])
        return entities
