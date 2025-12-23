"""
Training Data Augmenter

Create variations of homes for training data augmentation.
"""

import copy
import logging
import random
from typing import Any

logger = logging.getLogger(__name__)


class TrainingDataAugmenter:
    """
    Create variations of homes for training data augmentation.
    
    Variations (3-5 per home):
    1. Device count variations (±20%)
    2. Event frequency variations (±30%)
    3. Device type distribution variations
    4. Spatial layout variations
    """
    
    def __init__(self, augmentation_factor: int = 4):
        """
        Initialize data augmenter.
        
        Args:
            augmentation_factor: Number of variations to create per home (default: 4)
        """
        self.augmentation_factor = augmentation_factor
        logger.info(f"TrainingDataAugmenter initialized (factor: {augmentation_factor})")
    
    def create_variations(
        self,
        base_profile: dict[str, Any],
        count: int | None = None
    ) -> list[dict[str, Any]]:
        """
        Create augmented training samples.
        
        Args:
            base_profile: Base home profile
            count: Number of variations to create (default: augmentation_factor)
        
        Returns:
            List of augmented profile dictionaries
        """
        if count is None:
            count = self.augmentation_factor
        
        variations = []
        
        for i in range(count):
            variation = self._create_single_variation(base_profile, i)
            variations.append(variation)
        
        logger.debug(f"Created {len(variations)} variations from base profile")
        return variations
    
    def _create_single_variation(
        self,
        base_profile: dict[str, Any],
        variation_index: int
    ) -> dict[str, Any]:
        """
        Create a single variation of the base profile.
        
        Args:
            base_profile: Base home profile
            variation_index: Index of variation (0-based)
        
        Returns:
            Augmented profile dictionary
        """
        # Deep copy to avoid modifying original
        variation = copy.deepcopy(base_profile)
        
        # Apply different augmentation strategies based on index
        strategy = variation_index % 4
        
        if strategy == 0:
            # Device count variation (±20%)
            self._vary_device_counts(variation, factor=0.2)
        elif strategy == 1:
            # Event frequency variation (±30%)
            self._vary_event_frequencies(variation, factor=0.3)
        elif strategy == 2:
            # Device type distribution variation
            self._vary_device_distribution(variation)
        else:
            # Spatial layout variation
            self._vary_spatial_layout(variation)
        
        # Mark as variation
        variation['is_augmented'] = True
        variation['variation_index'] = variation_index
        variation['base_home_id'] = base_profile.get('home_id', 'unknown')
        
        return variation
    
    def _vary_device_counts(
        self,
        profile: dict[str, Any],
        factor: float = 0.2
    ):
        """
        Vary device counts by ±factor.
        
        Args:
            profile: Profile to modify
            factor: Variation factor (default: 0.2 = ±20%)
        """
        device_comp = profile.get('device_composition', {})
        total = device_comp.get('total_devices', 0)
        
        # Apply random variation
        variation = random.uniform(-factor, factor)
        new_total = max(1, int(total * (1 + variation)))
        
        device_comp['total_devices'] = new_total
        
        # Adjust ratios slightly to maintain consistency
        ratios = device_comp.get('ratios', {})
        for key in ratios:
            # Small random variation to ratios
            ratios[key] = max(0.0, min(1.0, ratios[key] + random.uniform(-0.05, 0.05)))
    
    def _vary_event_frequencies(
        self,
        profile: dict[str, Any],
        factor: float = 0.3
    ):
        """
        Vary event frequencies by ±factor.
        
        Args:
            profile: Profile to modify
            factor: Variation factor (default: 0.3 = ±30%)
        """
        event_patterns = profile.get('event_patterns', {})
        total_events = event_patterns.get('total_events', 0)
        events_per_day = event_patterns.get('events_per_day', 0.0)
        
        # Apply random variation
        variation = random.uniform(-factor, factor)
        new_total = max(0, int(total_events * (1 + variation)))
        new_per_day = max(0.0, events_per_day * (1 + variation))
        
        event_patterns['total_events'] = new_total
        event_patterns['events_per_day'] = new_per_day
    
    def _vary_device_distribution(self, profile: dict[str, Any]):
        """
        Vary device type distribution.
        
        Args:
            profile: Profile to modify
        """
        device_comp = profile.get('device_composition', {})
        ratios = device_comp.get('ratios', {})
        
        # Redistribute ratios slightly
        total_ratio = sum(ratios.values())
        if total_ratio > 0:
            # Add small random variations
            for key in ratios:
                ratios[key] = max(0.0, min(1.0, ratios[key] + random.uniform(-0.1, 0.1)))
            
            # Renormalize
            new_total = sum(ratios.values())
            if new_total > 0:
                for key in ratios:
                    ratios[key] = ratios[key] / new_total * total_ratio
    
    def _vary_spatial_layout(self, profile: dict[str, Any]):
        """
        Vary spatial layout metrics.
        
        Args:
            profile: Profile to modify
        """
        spatial = profile.get('spatial_layout', {})
        area_count = spatial.get('area_count', 0)
        devices_per_area = spatial.get('devices_per_area', 0.0)
        
        # Vary area count slightly
        if area_count > 0:
            variation = random.uniform(-0.15, 0.15)
            new_area_count = max(1, int(area_count * (1 + variation)))
            spatial['area_count'] = new_area_count
            
            # Adjust devices_per_area accordingly
            total_devices = profile.get('device_composition', {}).get('total_devices', 0)
            if new_area_count > 0:
                spatial['devices_per_area'] = total_devices / new_area_count

