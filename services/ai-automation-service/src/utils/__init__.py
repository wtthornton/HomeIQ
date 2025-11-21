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

__all__ = [
    "COMMON_AREAS",
    "add_custom_area",
    "extract_area_from_request",
    "format_area_display",
    "get_area_list",
    "is_valid_area",
]

