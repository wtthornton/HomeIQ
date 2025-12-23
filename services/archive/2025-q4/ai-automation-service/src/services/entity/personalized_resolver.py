"""
Personalized Entity Resolver

Epic AI-12, Story AI12.2: Natural Language Entity Resolver Enhancement
Enhances entity resolution to use personalized index for natural language queries.
Provides multi-variant matching, area-aware resolution, and context-aware resolution
with confidence scoring based on user's naming patterns.
"""

import logging
from typing import Any, Optional
from dataclasses import dataclass

from ...clients.data_api_client import DataAPIClient
from ...clients.ha_client import HomeAssistantClient
from .resolver import EntityResolver
from .personalized_index import PersonalizedEntityIndex
from .index_builder import PersonalizedIndexBuilder
from .area_resolver import AreaResolver

logger = logging.getLogger(__name__)


@dataclass
class ResolutionResult:
    """Result of entity resolution with confidence score"""
    entity_id: str
    confidence: float
    matched_variant: Optional[str] = None
    matched_type: Optional[str] = None  # 'name', 'name_by_user', 'alias', etc.
    area_id: Optional[str] = None
    area_name: Optional[str] = None


class PersonalizedEntityResolver:
    """
    Personalized entity resolver that uses personalized index for natural language queries.
    
    Features:
    - Semantic search using personalized index
    - Multi-variant matching (all name variations per device)
    - Area-aware resolution
    - Context-aware resolution (query context improves matching)
    - Confidence scoring based on user's naming patterns
    - Backward compatibility with existing EntityResolver
    """
    
    def __init__(
        self,
        personalized_index: PersonalizedEntityIndex,
        ha_client: Optional[HomeAssistantClient] = None,
        data_api_client: Optional[DataAPIClient] = None,
        fallback_resolver: Optional[EntityResolver] = None,
        area_resolver: Optional[AreaResolver] = None
    ):
        """
        Initialize personalized entity resolver.
        
        Args:
            personalized_index: PersonalizedEntityIndex instance
            ha_client: Optional Home Assistant client
            data_api_client: Optional Data API client
            fallback_resolver: Optional fallback resolver for backward compatibility
            area_resolver: Optional AreaResolver for area name resolution
        """
        self.personalized_index = personalized_index
        self.ha_client = ha_client
        self.data_api_client = data_api_client or DataAPIClient()
        self.fallback_resolver = fallback_resolver
        self.area_resolver = area_resolver
        
        logger.info("PersonalizedEntityResolver initialized")
    
    async def resolve_device_names(
        self,
        device_names: list[str],
        query: Optional[str] = None,
        area_id: Optional[str] = None,
        domain: Optional[str] = None,
        use_fallback: bool = True
    ) -> dict[str, str]:
        """
        Resolve device names to entity IDs using personalized index.
        
        Args:
            device_names: List of device names to resolve
            query: Optional query context for better matching
            area_id: Optional area filter
            domain: Optional domain filter
            use_fallback: If True, use fallback resolver for unresolved names
        
        Returns:
            Dictionary mapping device_name to entity_id
        """
        if not device_names:
            return {}
        
        results: dict[str, str] = {}
        unresolved: list[str] = []
        
        # Try personalized index resolution for each device name
        for device_name in device_names:
            resolution = await self.resolve_single_device(
                device_name=device_name,
                query=query,
                area_id=area_id,
                domain=domain
            )
            
            if resolution and resolution.confidence > 0.5:  # Confidence threshold
                results[device_name] = resolution.entity_id
                logger.debug(
                    f"Resolved '{device_name}' → {resolution.entity_id} "
                    f"(confidence: {resolution.confidence:.2f}, variant: {resolution.matched_variant})"
                )
            else:
                unresolved.append(device_name)
        
        # Use fallback resolver for unresolved names
        if unresolved and use_fallback and self.fallback_resolver:
            logger.debug(f"Using fallback resolver for {len(unresolved)} unresolved names")
            fallback_results = await self.fallback_resolver.resolve_device_names(
                device_names=unresolved,
                query=query,
                area_id=area_id
            )
            results.update(fallback_results)
        
        logger.info(f"Resolved {len(results)}/{len(device_names)} device names using personalized index")
        return results
    
    async def resolve_single_device(
        self,
        device_name: str,
        query: Optional[str] = None,
        area_id: Optional[str] = None,
        domain: Optional[str] = None
    ) -> Optional[ResolutionResult]:
        """
        Resolve single device name to entity ID with confidence score.
        
        Args:
            device_name: Device name to resolve
            query: Optional query context
            area_id: Optional area filter
            domain: Optional domain filter
        
        Returns:
            ResolutionResult with entity_id and confidence, or None if not found
        """
        if not device_name or not device_name.strip():
            return None
        
        # Use query context if available, otherwise use device name
        search_query = query or device_name
        
        # Search personalized index
        search_results = self.personalized_index.search_by_name(
            query=search_query,
            domain=domain,
            area_id=area_id,
            limit=5  # Get top 5 matches
        )
        
        if not search_results:
            return None
        
        # Get best match
        best_entity_id, best_score = search_results[0]
        entry = self.personalized_index.get_entity(best_entity_id)
        
        if not entry:
            return None
        
        # Find which variant matched best
        matched_variant = None
        matched_type = None
        
        # Check if device_name matches any variant exactly (higher confidence)
        device_name_lower = device_name.strip().lower()
        for variant in entry.variants:
            if variant.variant_name.lower() == device_name_lower:
                matched_variant = variant.variant_name
                matched_type = variant.variant_type
                # Boost confidence for exact match
                best_score = min(1.0, best_score + 0.2)
                break
        
        # If no exact match, use the variant with highest similarity
        if not matched_variant and entry.variants:
            matched_variant = entry.variants[0].variant_name
            matched_type = entry.variants[0].variant_type
        
        # Adjust confidence based on variant type (user-defined names are more reliable)
        confidence = best_score
        if matched_type == "name_by_user":
            confidence = min(1.0, confidence + 0.1)
        elif matched_type == "alias":
            confidence = min(1.0, confidence + 0.05)
        
        return ResolutionResult(
            entity_id=best_entity_id,
            confidence=confidence,
            matched_variant=matched_variant,
            matched_type=matched_type,
            area_id=entry.area_id,
            area_name=entry.area_name
        )
    
    async def resolve_with_context(
        self,
        device_names: list[str],
        query: str,
        area_hint: Optional[str] = None,
        domain_hint: Optional[str] = None
    ) -> dict[str, ResolutionResult]:
        """
        Resolve device names with full context awareness.
        
        Args:
            device_names: List of device names to resolve
            query: Full query context
            area_hint: Optional area hint from query
            domain_hint: Optional domain hint from query
        
        Returns:
            Dictionary mapping device_name to ResolutionResult
        """
        results: dict[str, ResolutionResult] = {}
        
        # Extract area from query if not provided
        area_id = area_hint
        if not area_id and area_hint:
            # Try to resolve area name to area_id
            area_id = await self._resolve_area_name(area_hint)
        
        for device_name in device_names:
            resolution = await self.resolve_single_device(
                device_name=device_name,
                query=query,  # Use full query for better context
                area_id=area_id,
                domain=domain_hint
            )
            
            if resolution:
                results[device_name] = resolution
        
        return results
    
    async def _resolve_area_name(self, area_name: str) -> Optional[str]:
        """Resolve area name to area_id"""
        if not area_name:
            return None
        
        # Use AreaResolver if available
        if self.area_resolver:
            area_id = self.area_resolver.resolve_area_name(area_name)
            if area_id:
                return area_id
        
        # Fallback: search via Data API
        try:
            areas = await self.data_api_client.fetch_areas()
            if not areas:
                return None
            
            area_name_lower = area_name.strip().lower()
            for area in areas:
                if area.get("name", "").lower() == area_name_lower:
                    return area.get("area_id")
            
            return None
        except Exception as e:
            logger.warning(f"Failed to resolve area name '{area_name}': {e}")
            return None
    
    def extract_area_from_query(self, query: str) -> Optional[str]:
        """
        Extract area name from natural language query.
        
        Args:
            query: Natural language query
        
        Returns:
            Area name if found, None otherwise
        """
        if not self.area_resolver:
            return None
        
        return self.area_resolver.extract_area_from_query(query)
    
    async def get_resolution_confidence(
        self,
        device_name: str,
        entity_id: str
    ) -> float:
        """
        Get confidence score for a specific device_name → entity_id mapping.
        
        Args:
            device_name: Device name
            entity_id: Entity ID
        
        Returns:
            Confidence score (0.0 to 1.0)
        """
        entry = self.personalized_index.get_entity(entity_id)
        if not entry:
            return 0.0
        
        device_name_lower = device_name.strip().lower()
        
        # Check for exact match
        for variant in entry.variants:
            if variant.variant_name.lower() == device_name_lower:
                # Exact match - high confidence
                confidence = 0.95
                if variant.variant_type == "name_by_user":
                    confidence = 1.0  # User-defined names are most reliable
                return confidence
        
        # Check for partial match
        for variant in entry.variants:
            if device_name_lower in variant.variant_name.lower() or \
               variant.variant_name.lower() in device_name_lower:
                return 0.7  # Partial match - medium confidence
        
        return 0.0  # No match
    
    def get_index_stats(self) -> dict[str, Any]:
        """Get personalized index statistics"""
        return self.personalized_index.get_stats()

