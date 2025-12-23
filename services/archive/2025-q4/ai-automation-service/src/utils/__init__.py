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
from .gpt51_params import (
    can_use_temperature,
    get_gpt51_params_for_use_case,
    is_gpt51_model,
    merge_gpt51_params,
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
    'is_gpt51_model',
    'get_gpt51_params_for_use_case',
    'merge_gpt51_params',
    'can_use_temperature',
]

