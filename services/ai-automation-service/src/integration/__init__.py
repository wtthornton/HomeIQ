"""
Integration module for cross-feature validation and enhancement.

Phase 1: Pattern history tracking and trend analysis
Phase 2: Pattern-synergy cross-validation
"""

from .pattern_history_validator import PatternHistoryValidator
from .pattern_synergy_validator import PatternSynergyValidator

__all__ = ["PatternHistoryValidator", "PatternSynergyValidator"]
