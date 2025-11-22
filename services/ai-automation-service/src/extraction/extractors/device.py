"""
Device Extractor (2025)

Responsible for identifying specific devices and entities from user queries.
Uses Semantic Embeddings (Vector Search) and Fuzzy Matching.
"""

import logging
import re
from typing import List, Dict, Any, Set, Tuple
from ..models import AutomationContext, DeviceContext
from ..utils.embeddings import EmbeddingService
from .base_extractor import BaseExtractor

# Optional import for rapidfuzz
try:
    from rapidfuzz import fuzz, process
    _RAPIDFUZZ_AVAILABLE = True
except ImportError:
    _RAPIDFUZZ_AVAILABLE = False

logger = logging.getLogger(__name__)

class DeviceExtractor(BaseExtractor):
    """
    Extracts device entities using a hybrid approach:
    1. Semantic Search (Embeddings): Matches "reading light" to "light.study_desk"
    2. Fuzzy Matching: Matches "kitchen lght" to "light.kitchen_main"
    3. Scoping: Filters by Spatial Context (Area) if available
    """

    def __init__(self, ha_client: Any = None, device_client: Any = None):
        super().__init__()
        self.ha_client = ha_client
        self.device_client = device_client
        self._entity_cache: List[Dict[str, Any]] = []
        self._entity_embeddings = None
        self._entity_ids = []

    async def _refresh_entity_cache(self):
        """Fetch all entities and generate/cache embeddings."""
        if not self.ha_client:
            return

        try:
            # Fetch all entities (simplified)
            # In production, this would use data_api_client or ha_client.get_all_entities()
            if hasattr(self.ha_client, 'get_all_entities'):
                self._entity_cache = await self.ha_client.get_all_entities()
            elif hasattr(self.ha_client, 'get_states'):
                 states = await self.ha_client.get_states()
                 self._entity_cache = [
                     {
                         'entity_id': s.entity_id,
                         'friendly_name': s.attributes.get('friendly_name', s.entity_id),
                         'domain': s.domain,
                         'area_id': getattr(s, 'area_id', None) # Requires enriched data
                     }
                     for s in states
                 ]
            
            # Generate embeddings for names
            # We embed: friendly_name + " " + entity_id
            if EmbeddingService.get_model() and self._entity_cache:
                texts = [
                    f"{e.get('friendly_name', '')} {e['entity_id']}" 
                    for e in self._entity_cache
                ]
                self._entity_embeddings = EmbeddingService.encode(texts)
                self._entity_ids = [e['entity_id'] for e in self._entity_cache]
                logger.debug(f"Generated embeddings for {len(self._entity_ids)} entities")
                
        except Exception as e:
            logger.warning(f"Failed to refresh entity cache: {e}")

    def _filter_by_area(self, entities: List[Dict[str, Any]], areas: List[str]) -> List[Dict[str, Any]]:
        """Filter entities based on identified areas."""
        if not areas:
            return entities
            
        filtered = []
        normalized_areas = [a.replace('_', ' ').lower() for a in areas]
        
        for entity in entities:
            # Check explicit area_id
            area_id = entity.get('area_id')
            if area_id and area_id in areas:
                filtered.append(entity)
                continue
                
            # Check name overlap (fallback)
            name = entity.get('friendly_name', '').lower()
            entity_id = entity['entity_id'].lower()
            
            if any(area in name or area in entity_id for area in normalized_areas):
                filtered.append(entity)
                
        return filtered

    async def extract(self, query: str, context: AutomationContext) -> AutomationContext:
        """
        Identify action and trigger devices.
        """
        # Lazy load cache
        if not self._entity_cache and self.ha_client:
            await self._refresh_entity_cache()
            
        if not self._entity_cache:
            logger.warning("No entity cache available for DeviceExtractor")
            return context

        # 1. Scope the search space (Spatial Filtering)
        # If areas were found, we prioritize devices in those areas
        search_space = self._entity_cache
        if context.spatial.areas:
            scoped_entities = self._filter_by_area(self._entity_cache, context.spatial.areas)
            # If scoping leaves us with nothing, fallback to global search (user might have mentioned area implicitly)
            if scoped_entities:
                search_space = scoped_entities
                logger.debug(f"Scoped search to {len(scoped_entities)} devices in areas: {context.spatial.areas}")

        # 2. Hybrid Matching (Semantic + Fuzzy)
        # We look for noun phrases in the query that might be devices
        # Simplified: We treat the whole query as the search term for embeddings
        # In a full implementation, we'd use Noun Chunking here.
        
        found_entities = set()
        
        # Strategy A: Semantic Search (if available)
        if self._entity_embeddings is not None:
            # We query against the FULL query to find most relevant devices
            query_embedding = EmbeddingService.encode(query)
            if query_embedding is not None:
                # Note: This requires _entity_embeddings to be sliced if we scoped the search space.
                # For MVP simplicity, we'll search global embeddings and filter results.
                scores = EmbeddingService.cosine_similarity(query_embedding, self._entity_embeddings)
                
                # Top K
                top_indices = scores.argsort()[::-1][:10] 
                for idx in top_indices:
                    if scores[idx] > 0.4: # Threshold
                        entity = self._entity_cache[idx]
                        # Apply area filter post-search if needed
                        if context.spatial.areas:
                             # Check if this entity matches the spatial scope
                             if entity in search_space:
                                 found_entities.add(entity['entity_id'])
                        else:
                            found_entities.add(entity['entity_id'])

        # Strategy B: Fuzzy / Keyword Match
        # Good for explicit names "turn on wled"
        if _RAPIDFUZZ_AVAILABLE:
            choices = {e['entity_id']: f"{e.get('friendly_name','')} {e['entity_id']}" for e in search_space}
            # Extract potential device names (simple heuristic: words not in common stop words)
            # Better: Use the Intent Extractor to pull out "device names" strings first.
            # For now, we match the whole query against friendly names
            
            results = process.extract(query, choices, limit=5, scorer=fuzz.token_set_ratio)
            for entity_id, score, _ in results:
                if score > 70: # Threshold
                    found_entities.add(entity_id)

        # 3. Classify into Action vs Trigger
        # This is heuristic-based. Real classification happens in IntentExtractor (LLM).
        # Here we just populate the candidate lists. The IntentExtractor will refine this.
        # For now, we put everything in action_entities as candidates.
        
        context.devices.action_entities = list(found_entities)
        
        # Populate Names for context
        names = []
        for eid in found_entities:
            entity = next((e for e in self._entity_cache if e['entity_id'] == eid), None)
            if entity:
                names.append(entity.get('friendly_name', eid))
        context.devices.action_device_names = names
        
        # Identify Domains
        domains = set(e.split('.')[0] for e in found_entities)
        context.devices.domains = list(domains)

        logger.info(f"Device extraction: found {len(found_entities)} entities")
        return context
