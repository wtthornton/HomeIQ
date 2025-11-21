"""
Common Automation Patterns Library

Pre-built templates for instant, high-quality automation generation.
"""

from .common_patterns import (
    PATTERNS,
    PatternDefinition,
    PatternVariable,
    generate_automation_id,
    get_all_patterns,
    get_pattern,
    get_patterns_by_category,
)
from .pattern_composer import ComposedAutomation, PatternComposer, get_pattern_composer
from .pattern_matcher import PatternMatch, PatternMatcher, get_pattern_matcher

__all__ = [
    "PATTERNS",
    # Pattern composition
    "ComposedAutomation",
    "PatternComposer",
    # Pattern definitions
    "PatternDefinition",
    # Pattern matching
    "PatternMatch",
    "PatternMatcher",
    "PatternVariable",
    "generate_automation_id",
    "get_all_patterns",
    "get_pattern",
    "get_pattern_composer",
    "get_pattern_matcher",
    "get_patterns_by_category",
]
