"""
Common Automation Patterns Library

Pre-built templates for instant, high-quality automation generation.
"""

from .common_patterns import (
    PatternDefinition,
    PatternVariable,
    PATTERNS,
    get_pattern,
    get_all_patterns,
    get_patterns_by_category,
    generate_automation_id
)

from .pattern_matcher import (
    PatternMatch,
    PatternMatcher,
    get_pattern_matcher
)

from .pattern_composer import (
    ComposedAutomation,
    PatternComposer,
    get_pattern_composer
)

__all__ = [
    # Pattern definitions
    'PatternDefinition',
    'PatternVariable',
    'PATTERNS',
    'get_pattern',
    'get_all_patterns',
    'get_patterns_by_category',
    'generate_automation_id',

    # Pattern matching
    'PatternMatch',
    'PatternMatcher',
    'get_pattern_matcher',

    # Pattern composition
    'ComposedAutomation',
    'PatternComposer',
    'get_pattern_composer',
]
