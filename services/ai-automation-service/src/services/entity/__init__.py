"""
Unified Entity Services Module

Consolidates all entity-related functionality:
- Extraction: Extract entities from natural language queries
- Validation: Validate entities exist in Home Assistant
- Enrichment: Enrich entities with comprehensive data
- Resolution: Resolve device names to entity IDs

Created: Phase 2 - Core Service Refactoring
"""

from .enricher import EntityEnricher
from .extractor import EntityExtractor
from .resolver import EntityResolver
from .validator import EntityValidator

__all__ = [
    "EntityEnricher",
    "EntityExtractor",
    "EntityResolver",
    "EntityValidator",
]

