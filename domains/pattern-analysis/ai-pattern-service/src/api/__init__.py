"""
API routers for Pattern Service

Epic 39, Story 39.5: Pattern Service Foundation
"""

from . import community_pattern_router, health_router, pattern_router, synergy_router

__all__ = ["health_router", "pattern_router", "synergy_router", "community_pattern_router"]

