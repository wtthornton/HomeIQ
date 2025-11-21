"""
Shared utilities for AI Automation Service
"""

from .area_detection import (
    COMMON_AREAS,
    add_custom_area,
    extract_area_from_request,
    format_area_display,
    get_area_list,
    is_valid_area,
)
from .fuzzy import (
    RAPIDFUZZ_AVAILABLE,
    fuzzy_match_best,
    fuzzy_match_with_context,
    fuzzy_score,
)

__all__ = [
    'extract_area_from_request',
    'get_area_list',
    'format_area_display',
    'is_valid_area',
    'add_custom_area',
    'COMMON_AREAS',
    'fuzzy_score',
    'fuzzy_match_best',
    'fuzzy_match_with_context',
    'RAPIDFUZZ_AVAILABLE',
]

