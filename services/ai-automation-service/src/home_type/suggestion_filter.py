"""
Suggestion Enhancement with Home Type

Filter and prioritize suggestions based on home type.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class HomeTypeSuggestionFilter:
    """
    Filter and prioritize suggestions based on home type.
    
    Integration Point: Filter suggestions by home type
    """
    
    # Home type preferences for suggestion categories
    HOME_TYPE_PREFERENCES = {
        'security_focused': {
            'preferred_categories': ['security'],
            'boost_confidence': 0.1
        },
        'climate_controlled': {
            'preferred_categories': ['comfort', 'energy'],
            'boost_confidence': 0.1
        },
        'smart_home': {
            'preferred_categories': ['convenience', 'energy'],
            'boost_confidence': 0.05
        },
        'apartment': {
            'preferred_categories': ['convenience', 'energy'],
            'boost_confidence': 0.05
        },
        'standard_home': {
            'preferred_categories': ['convenience', 'comfort'],
            'boost_confidence': 0.0
        }
    }
    
    def __init__(self):
        """Initialize suggestion filter."""
        logger.info("HomeTypeSuggestionFilter initialized")
    
    def filter_by_home_type(
        self,
        suggestions: list[dict[str, Any]],
        home_type: str
    ) -> list[dict[str, Any]]:
        """
        Filter suggestions by home type.
        
        Args:
            suggestions: List of suggestion dictionaries
            home_type: Home type string
        
        Returns:
            Filtered suggestions list
        """
        if not suggestions:
            return []
        
        preferences = self.HOME_TYPE_PREFERENCES.get(
            home_type,
            self.HOME_TYPE_PREFERENCES['standard_home']
        )
        preferred_categories = preferences.get('preferred_categories', [])
        
        # Filter: Keep all suggestions but prioritize preferred categories
        filtered = []
        for suggestion in suggestions:
            category = suggestion.get('category', 'convenience')
            
            # Boost confidence for preferred categories
            if category in preferred_categories:
                boost = preferences.get('boost_confidence', 0.0)
                suggestion['confidence'] = min(1.0, suggestion.get('confidence', 0.0) + boost)
            
            filtered.append(suggestion)
        
        logger.debug(f"Filtered {len(suggestions)} suggestions for home type: {home_type}")
        return filtered
    
    def prioritize_by_home_type(
        self,
        suggestions: list[dict[str, Any]],
        home_type: str
    ) -> list[dict[str, Any]]:
        """
        Prioritize suggestions by home type.
        
        Args:
            suggestions: List of suggestion dictionaries
            home_type: Home type string
        
        Returns:
            Prioritized suggestions list (sorted by relevance)
        """
        filtered = self.filter_by_home_type(suggestions, home_type)
        
        # Sort by confidence (descending)
        prioritized = sorted(
            filtered,
            key=lambda s: s.get('confidence', 0.0),
            reverse=True
        )
        
        return prioritized

