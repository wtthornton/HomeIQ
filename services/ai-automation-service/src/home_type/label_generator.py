"""
Home Type Label Generator

Generate home type labels from synthetic home metadata or profile features.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class HomeTypeLabelGenerator:
    """
    Generate home type labels from synthetic home metadata.
    
    Strategy:
    1. Use home metadata (type field) when available
    2. Use heuristics from profile features (fallback)
    3. Map to standard home types:
       - security_focused
       - climate_controlled
       - high_activity
       - smart_home
       - standard_home
       - apartment
       - etc.
    """
    
    # Home type mappings
    TYPE_MAPPINGS = {
        'single_family_house': 'standard_home',
        'apartment': 'apartment',
        'condo': 'apartment',
        'townhouse': 'standard_home',
        'cottage': 'standard_home',
        'studio': 'apartment',
        'multi_story': 'standard_home',
        'ranch_house': 'standard_home'
    }
    
    def __init__(self):
        """Initialize label generator."""
        logger.info("HomeTypeLabelGenerator initialized")
    
    def label_home_type(
        self,
        home_metadata: dict[str, Any],
        profile: dict[str, Any] | None = None
    ) -> str:
        """
        Generate home type label.
        
        Args:
            home_metadata: Home metadata from synthetic generation
            profile: Optional home profile for heuristic labeling
        
        Returns:
            Home type label string
        """
        # Try to get type from metadata
        home_type = home_metadata.get('home_type')
        if not home_type:
            # Try from nested metadata
            nested_home = home_metadata.get('metadata', {}).get('home', {})
            home_type = nested_home.get('type')
        
        if home_type:
            # Map to standard label
            label = self.TYPE_MAPPINGS.get(home_type, 'standard_home')
            logger.debug(f"Labeled as {label} from metadata type: {home_type}")
            return label
        
        # Fallback: Use heuristics from profile
        if profile:
            label = self._label_from_profile(profile)
            logger.debug(f"Labeled as {label} from profile heuristics")
            return label
        
        # Default
        logger.warning("No home type found, defaulting to 'standard_home'")
        return 'standard_home'
    
    def _label_from_profile(self, profile: dict[str, Any]) -> str:
        """
        Label home type from profile features using heuristics.
        
        Args:
            profile: Home profile
        
        Returns:
            Home type label
        """
        device_comp = profile.get('device_composition', {})
        ratios = device_comp.get('ratios', {})
        
        security_ratio = ratios.get('security_ratio', 0.0)
        climate_ratio = ratios.get('climate_ratio', 0.0)
        total_devices = device_comp.get('total_devices', 0)
        
        # Heuristic rules
        if security_ratio > 0.2:
            return 'security_focused'
        elif climate_ratio > 0.15:
            return 'climate_controlled'
        elif total_devices > 50:
            return 'smart_home'
        else:
            return 'standard_home'

