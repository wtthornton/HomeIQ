"""
Home Type Integration Helpers

Utility functions for home type-aware processing.
"""

from typing import Any


def get_home_type_preferred_categories(home_type: str) -> list[str]:
    """
    Get preferred suggestion categories for home type.
    
    Args:
        home_type: Home type classification
    
    Returns:
        List of preferred categories (ordered by preference)
    """
    preferences = {
        'security_focused': ['security', 'monitoring', 'lighting'],
        'climate_controlled': ['climate', 'energy', 'monitoring'],
        'high_activity': ['lighting', 'appliance', 'convenience'],
        'smart_home': ['automation', 'integration', 'convenience'],
        'standard_home': ['lighting', 'climate', 'security'],
        'apartment': ['lighting', 'climate', 'space_optimization'],
    }
    return preferences.get(home_type, ['general', 'lighting', 'climate'])


def calculate_home_type_boost(
    suggestion_category: str,
    home_type: str,
    base_boost: float = 0.10
) -> float:
    """
    Calculate home type boost for suggestion ranking.
    
    Args:
        suggestion_category: Suggestion category
        home_type: Home type classification
        base_boost: Base boost value (default: 0.10 = 10%)
    
    Returns:
        Boost value (0.0 to base_boost)
    """
    preferred = get_home_type_preferred_categories(home_type)
    
    if suggestion_category in preferred:
        # Higher boost for more preferred categories
        index = preferred.index(suggestion_category)
        multiplier = 1.0 - (index * 0.2)  # 1.0, 0.8, 0.6, ...
        return base_boost * multiplier
    
    return 0.0


def adjust_pattern_thresholds(
    home_type: str,
    base_min_confidence: float = 0.7,
    base_min_occurrences: int = 10
) -> tuple[float, int]:
    """
    Adjust pattern detection thresholds based on home type.
    
    Args:
        home_type: Home type classification
        base_min_confidence: Base minimum confidence
        base_min_occurrences: Base minimum occurrences
    
    Returns:
        Tuple of (adjusted_confidence, adjusted_occurrences)
    """
    adjustments = {
        'security_focused': {
            'confidence_multiplier': 0.93,  # Lower threshold for security patterns
            'occurrences_multiplier': 0.9
        },
        'climate_controlled': {
            'confidence_multiplier': 0.95,
            'occurrences_multiplier': 0.85
        },
        'high_activity': {
            'confidence_multiplier': 0.90,  # More lenient for active homes
            'occurrences_multiplier': 0.8
        },
        'apartment': {
            'confidence_multiplier': 0.95,
            'occurrences_multiplier': 1.0  # No adjustment
        },
    }
    
    adjustment = adjustments.get(home_type, {})
    conf_mult = adjustment.get('confidence_multiplier', 1.0)
    occ_mult = adjustment.get('occurrences_multiplier', 1.0)
    
    return (
        base_min_confidence * conf_mult,
        int(base_min_occurrences * occ_mult)
    )

