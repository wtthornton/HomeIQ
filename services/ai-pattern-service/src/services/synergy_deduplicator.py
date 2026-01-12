"""
Synergy Deduplicator Service

2025 Enhancement: Detect and remove duplicate synergies.

Prevents duplicate storage and improves quality by keeping only
the highest quality synergy from each group of duplicates.
"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class SynergyDeduplicator:
    """
    Detect and remove duplicate synergies.
    
    2025 Best Practice: Prevent duplicate storage and improve quality.
    """
    
    def find_duplicates(
        self,
        synergies: list[dict[str, Any]]
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Find duplicate synergies based on canonical device pairs.
        
        Duplicates are identified by:
        - Same canonical device pair (sorted device IDs)
        - Same relationship type (from opportunity_metadata)
        - Same area (if area-based)
        
        Args:
            synergies: List of synergy dictionaries
        
        Returns:
            Dictionary mapping canonical_pair keys to lists of duplicate synergies:
            {
                'canonical_pair_1': [synergy1, synergy2, ...],
                'canonical_pair_2': [synergy3, ...],
                ...
            }
        """
        duplicates: dict[str, list[dict[str, Any]]] = {}
        
        for synergy in synergies:
            # Extract device IDs
            device_ids = synergy.get('devices', synergy.get('device_ids', []))
            
            # Handle JSON string format
            if isinstance(device_ids, str):
                try:
                    device_ids = json.loads(device_ids)
                except (json.JSONDecodeError, TypeError):
                    logger.warning(f"Failed to parse device_ids for synergy {synergy.get('synergy_id')}")
                    continue
            
            if not device_ids or len(device_ids) < 2:
                # Skip synergies without valid device pairs
                continue
            
            # Create canonical pair key (sorted device IDs for consistency)
            canonical_pair = tuple(sorted([str(d) for d in device_ids[:2]]))  # Use first 2 devices for pairs
            
            # Include relationship type in key (if available)
            metadata = synergy.get('opportunity_metadata', {})
            relationship = metadata.get('relationship', '') if isinstance(metadata, dict) else ''
            
            # Include area in key (if area-based matching desired)
            area = synergy.get('area', '')
            
            # Create composite key
            key = f"{canonical_pair}|{relationship}|{area}"
            
            if key not in duplicates:
                duplicates[key] = []
            duplicates[key].append(synergy)
        
        # Filter to only return keys with duplicates (2+ synergies)
        return {k: v for k, v in duplicates.items() if len(v) > 1}
    
    def deduplicate(
        self,
        synergies: list[dict[str, Any]],
        keep_highest_quality: bool = True
    ) -> list[dict[str, Any]]:
        """
        Remove duplicates, keeping highest quality synergy from each group.
        
        Args:
            synergies: List of synergy dictionaries
            keep_highest_quality: If True, keep synergy with highest quality_score
                                 If False, keep first occurrence
        
        Returns:
            Deduplicated list of synergies
        """
        duplicates = self.find_duplicates(synergies)
        
        if not duplicates:
            # No duplicates found, return all synergies
            logger.debug(f"No duplicates found in {len(synergies)} synergies")
            return synergies
        
        # Create set of all duplicate synergies (to exclude from result)
        duplicate_synergies = set()
        for group in duplicates.values():
            for synergy in group:
                synergy_id = synergy.get('synergy_id')
                if synergy_id:
                    duplicate_synergies.add(synergy_id)
        
        # Start with non-duplicate synergies
        deduplicated = [
            s for s in synergies
            if s.get('synergy_id') not in duplicate_synergies
        ]
        
        # For each duplicate group, keep the best one
        kept_count = 0
        removed_count = 0
        
        for canonical_pair, group in duplicates.items():
            if keep_highest_quality:
                # Keep synergy with highest quality_score
                best_synergy = max(
                    group,
                    key=lambda s: (
                        float(s.get('quality_score', 0.0)),
                        float(s.get('confidence', 0.0)),
                        float(s.get('impact_score', 0.0))
                    )
                )
            else:
                # Keep first occurrence (by synergy_id or index)
                best_synergy = group[0]
            
            deduplicated.append(best_synergy)
            kept_count += 1
            removed_count += len(group) - 1
            
            logger.debug(
                f"Duplicate group {canonical_pair}: kept 1, removed {len(group) - 1} "
                f"(quality_score: {best_synergy.get('quality_score', 'N/A')})"
            )
        
        logger.info(
            f"Deduplication complete: {len(synergies)} → {len(deduplicated)} "
            f"({kept_count} groups, {removed_count} duplicates removed)"
        )
        
        return deduplicated
