"""
Unified Entity Services Module

Consolidates all entity-related functionality:
- Extraction: Extract entities from natural language queries
- Validation: Validate entities exist in Home Assistant
- Enrichment: Enrich entities with comprehensive data
- Resolution: Resolve device names to entity IDs
- Personalized Resolution: Personalized entity resolution with semantic search (Epic AI-12)

Created: Phase 2 - Core Service Refactoring
Enhanced: Epic AI-12 - Personalized Entity Resolution
"""

from .enricher import EntityEnricher
from .extractor import EntityExtractor
from .resolver import EntityResolver
from .validator import EntityValidator
from .personalized_resolver import PersonalizedEntityResolver, ResolutionResult
from .personalized_index import PersonalizedEntityIndex, EntityVariant, EntityIndexEntry
from .index_builder import PersonalizedIndexBuilder
from .area_resolver import AreaResolver, AreaInfo
from .index_updater import IndexUpdater
from .training_data_generator import TrainingDataGenerator, QueryEntityPair

__all__ = [
    'EntityExtractor',
    'EntityValidator',
    'EntityEnricher',
    'EntityResolver',
    'PersonalizedEntityResolver',
    'ResolutionResult',
    'PersonalizedEntityIndex',
    'EntityVariant',
    'EntityIndexEntry',
    'PersonalizedIndexBuilder',
    'AreaResolver',
    'AreaInfo',
    'IndexUpdater',
    'TrainingDataGenerator',
    'QueryEntityPair'
]

