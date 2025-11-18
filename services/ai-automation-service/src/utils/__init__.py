"""
Shared utilities for AI Automation Service
"""

from .area_detection import (
    extract_area_from_request,
    get_area_list,
    format_area_display,
    is_valid_area,
    add_custom_area,
    COMMON_AREAS
)

__all__ = [
    'extract_area_from_request',
    'get_area_list',
    'format_area_display',
    'is_valid_area',
    'add_custom_area',
    'COMMON_AREAS'
]

