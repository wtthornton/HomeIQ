"""
CRUD operations for Pattern Service

Epic 39, Story 39.6: Daily Scheduler Migration
"""

from .patterns import get_patterns, store_patterns
from .synergies import get_synergy_opportunities, store_synergy_opportunities

__all__ = [
    "store_patterns",
    "get_patterns",
    "store_synergy_opportunities",
    "get_synergy_opportunities",
]

