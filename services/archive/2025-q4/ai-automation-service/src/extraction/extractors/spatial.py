"""
Spatial Extractor (2025)

Responsible for extracting area and location context from user queries.
Filters the search space for subsequent extractors.
"""

import re
import logging
from typing import List, Dict, Any, Optional
from ..models import AutomationContext, SpatialContext
from .base_extractor import BaseExtractor

logger = logging.getLogger(__name__)

class SpatialExtractor(BaseExtractor):
    """
    Extracts spatial information (areas, floors, locations) from queries.
    Uses a combination of regex patterns and fuzzy matching against HA Area Registry.
    """
    
    # Common location patterns that imply specific areas
    LOCATION_PATTERNS = [
        (r'\b(living room|livingroom)\b', 'living_room'),
        (r'\b(bedroom|bed room)\b', 'bedroom'),
        (r'\b(kitchen)\b', 'kitchen'),
        (r'\b(bathroom|bath room)\b', 'bathroom'),
        (r'\b(office)\b', 'office'),
        (r'\b(garage)\b', 'garage'),
        (r'\b(entry|entryway|entry way|foyer)\b', 'entry'),
        (r'\b(dining room|diningroom)\b', 'dining_room'),
        (r'\b(family room|familyroom)\b', 'family_room'),
        (r'\b(basement)\b', 'basement'),
        (r'\b(attic)\b', 'attic'),
        (r'\b(patio|deck|porch|garden|backyard)\b', 'outdoor'),
        (r'\b(hallway|hall|corridor)\b', 'hallway'),
        (r'\b(master|main) (bedroom|bath)\b', 'master_bedroom'),
        (r'\b(guest) (bedroom|bath|room)\b', 'guest_room'),
        (r'\b(upstairs|upper floor)\b', 'upstairs'),
        (r'\b(downstairs|lower floor)\b', 'downstairs'),
    ]

    def __init__(self, ha_client: Any = None):
        super().__init__()
        self.ha_client = ha_client
        self._area_registry_cache: Dict[str, str] = {} # name -> area_id

    async def _refresh_area_registry(self):
        """Fetch valid areas from Home Assistant if client available."""
        if not self.ha_client:
            return

        try:
            # This assumes ha_client has get_area_registry method
            # In a real implementation, we'd want to check capability or use a protocol
            if hasattr(self.ha_client, 'get_area_registry'):
                registry = await self.ha_client.get_area_registry()
                if registry:
                    self._area_registry_cache = {
                        area.get('name', '').lower(): area_id 
                        for area_id, area in registry.items()
                    }
                    logger.debug(f"Cached {len(self._area_registry_cache)} areas from HA")
        except Exception as e:
            logger.warning(f"Failed to refresh area registry: {e}")

    def _extract_locations_regex(self, query: str) -> List[str]:
        """Extract potential locations using regex patterns."""
        locations = set()
        query_lower = query.lower()
        
        for pattern, normalized_name in self.LOCATION_PATTERNS:
            if re.search(pattern, query_lower):
                locations.add(normalized_name)
                
        return list(locations)

    def _match_registry_areas(self, candidates: List[str]) -> List[str]:
        """Match extracted candidates against real HA areas."""
        if not self._area_registry_cache:
            # If no registry, trust the candidates (fallback mode)
            return candidates
            
        valid_areas = []
        for candidate in candidates:
            # 1. Direct match
            if candidate in self._area_registry_cache:
                valid_areas.append(candidate)
                continue
                
            # 2. Fuzzy/Partial match (simplified)
            # e.g., 'master bedroom' matches 'master_bedroom' or 'Bedroom Master'
            candidate_clean = candidate.replace('_', ' ')
            for area_name in self._area_registry_cache:
                if candidate_clean in area_name or area_name in candidate_clean:
                    valid_areas.append(area_name.replace(' ', '_'))
                    
        return list(set(valid_areas))

    async def extract(self, query: str, context: AutomationContext) -> AutomationContext:
        """
        Process query for spatial context.
        
        1. Regex extraction of potential locations
        2. Validation against HA Area Registry (if available)
        3. Update AutomationContext
        """
        # Refresh cache if empty (lazy load)
        if not self._area_registry_cache and self.ha_client:
            await self._refresh_area_registry()
            
        # 1. Extract candidates
        candidates = self._extract_locations_regex(query)
        
        # 2. Validate/Resolve against Registry
        # If we have a registry, we filter candidates to only real areas.
        # If not, we accept the candidates as 'inferred' areas.
        final_areas = self._match_registry_areas(candidates)
        
        # 3. Update Context
        context.spatial.areas = final_areas
        context.spatial.locations = candidates # Keep raw candidates as specific locations
        
        # Determine if we successfully matched against real data
        context.spatial.area_matched = bool(self._area_registry_cache and final_areas)
        
        logger.info(f"Spatial extraction: found {len(final_areas)} areas: {final_areas}")
        return context
