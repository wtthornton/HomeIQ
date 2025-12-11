"""
Personalized Entity Index Builder

Epic AI-12, Story AI12.1: Personalized Entity Index Builder
Builds personalized entity index from user's actual Home Assistant devices by reading
Entity Registry, extracting all name variations, and building semantic embeddings.
"""

import logging
import time
from typing import Any, Optional
from datetime import datetime

from ...clients.ha_client import HomeAssistantClient
from ...clients.data_api_client import DataAPIClient
from .personalized_index import PersonalizedEntityIndex, EntityIndexEntry
from .area_resolver import AreaResolver
from .index_cache import IndexCache

logger = logging.getLogger(__name__)


class PersonalizedIndexBuilder:
    """
    Builds personalized entity index from Home Assistant Entity Registry.
    
    Reads all devices from Entity Registry, extracts name variations, and builds
    semantic embeddings for natural language matching.
    """
    
    def __init__(
        self,
        ha_client: HomeAssistantClient,
        data_api_client: Optional[DataAPIClient] = None,
        embedding_model: Optional[str] = None,
        area_resolver: Optional[AreaResolver] = None,
        use_cache: bool = True
    ):
        """
        Initialize index builder.
        
        Args:
            ha_client: Home Assistant client for Entity Registry access
            data_api_client: Optional Data API client for area information
            embedding_model: Optional embedding model name
            area_resolver: Optional AreaResolver for area name resolution
            use_cache: If True, use IndexCache to avoid rebuilding (Epic AI-12 Story AI12.10)
        """
        self.ha_client = ha_client
        self.data_api_client = data_api_client or DataAPIClient()
        self.embedding_model = embedding_model
        self.area_resolver = area_resolver
        self.use_cache = use_cache
        
        # Index cache (Epic AI-12 Story AI12.10)
        self._index_cache = IndexCache.get_instance() if use_cache else None
        
        logger.info(f"PersonalizedIndexBuilder initialized (use_cache={use_cache})")
    
    async def build_index(
        self,
        index: PersonalizedEntityIndex,
        incremental: bool = False,
        force_rebuild: bool = False
    ) -> dict[str, Any]:
        """
        Build personalized entity index from Home Assistant.
        
        Epic AI-12 Story AI12.10: Uses IndexCache to avoid rebuilding on every request.
        
        Args:
            index: PersonalizedEntityIndex instance to populate
            incremental: If True, only update changed entities
            force_rebuild: If True, force rebuild (ignore cache)
        
        Returns:
            Build statistics dictionary
        """
        start_time = time.time()
        logger.info("Starting personalized index build (incremental=%s, force_rebuild=%s)", incremental, force_rebuild)
        
        # Check cache first (Epic AI-12 Story AI12.10)
        if self._index_cache and not force_rebuild and not incremental:
            cached_index = self._index_cache.get(force_rebuild=force_rebuild)
            if cached_index is not None:
                # Copy cached index data to provided index
                index._index = cached_index._index.copy()
                index._variant_index = cached_index._variant_index.copy()
                index._area_index = cached_index._area_index.copy()
                index._embedding_model = cached_index._embedding_model
                index._embedding_cache = cached_index._embedding_cache
                index._query_cache = cached_index._query_cache
                
                build_duration_ms = (time.time() - start_time) * 1000
                stats = index.get_stats()
                stats["build_duration_ms"] = build_duration_ms
                stats["cached"] = True
                
                logger.info(f"✅ Using cached index (build_duration_ms={build_duration_ms:.2f})")
                return stats
        
        if not incremental:
            index.clear()
        
        try:
            # Fetch entities from Entity Registry
            entities = await self._fetch_entities()
            logger.info(f"Fetched {len(entities)} entities from Entity Registry")
            
            # Fetch areas for area name resolution
            areas = await self._fetch_areas()
            area_map = {area["area_id"]: area.get("name") for area in areas if area.get("area_id")}
            logger.info(f"Fetched {len(area_map)} areas")
            
            # Build area index if area_resolver provided
            if self.area_resolver:
                await self._build_area_index(areas)
            
            # Process each entity
            processed = 0
            skipped = 0
            
            for entity_data in entities:
                try:
                    await self._add_entity_to_index(
                        index,
                        entity_data,
                        area_map
                    )
                    processed += 1
                except Exception as e:
                    logger.warning(f"Failed to process entity {entity_data.get('entity_id')}: {e}")
                    skipped += 1
            
            # Update statistics
            build_duration_ms = (time.time() - start_time) * 1000
            stats = index.get_stats()
            stats["last_build_time"] = datetime.now().isoformat()
            stats["build_duration_ms"] = build_duration_ms
            stats["processed"] = processed
            stats["skipped"] = skipped
            stats["cached"] = False
            
            # Cache the index (Epic AI-12 Story AI12.10)
            if self._index_cache:
                self._index_cache.put(index)
                logger.debug("Index cached for future use")
            
            logger.info(
                f"Index build complete: {processed} entities processed, "
                f"{skipped} skipped, {build_duration_ms:.1f}ms"
            )
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to build index: {e}", exc_info=True)
            raise
    
    async def _fetch_entities(self) -> list[dict[str, Any]]:
        """Fetch all entities from Entity Registry"""
        try:
            # Use Entity Registry API
            entities = await self.ha_client.get_entity_registry()
            
            if not entities:
                logger.warning("No entities returned from Entity Registry")
                return []
            
            return entities
            
        except Exception as e:
            logger.error(f"Failed to fetch entities: {e}", exc_info=True)
            # Fallback: try Data API
            try:
                entities = await self.data_api_client.fetch_entities()
                return entities or []
            except Exception as e2:
                logger.error(f"Data API fallback also failed: {e2}", exc_info=True)
                return []
    
    async def _fetch_areas(self) -> list[dict[str, Any]]:
        """Fetch all areas for area name resolution"""
        try:
            # Try Data API first
            areas = await self.data_api_client.fetch_areas()
            if areas:
                return areas
            
            # Fallback: try HA client if available
            if hasattr(self.ha_client, 'get_area_registry'):
                areas = await self.ha_client.get_area_registry()
                return areas or []
            
            return []
        except Exception as e:
            logger.warning(f"Failed to fetch areas: {e}")
            return []
    
    async def _build_area_index(self, areas: list[dict[str, Any]]) -> None:
        """Build area index in AreaResolver"""
        if not self.area_resolver:
            return
        
        for area_data in areas:
            area_id = area_data.get("area_id")
            name = area_data.get("name")
            if not area_id or not name:
                continue
            
            aliases = area_data.get("aliases", [])
            if isinstance(aliases, str):
                aliases = [aliases]
            
            parent_area_id = area_data.get("parent_area_id")
            parent_area_name = area_data.get("parent_area_name")
            
            self.area_resolver.add_area(
                area_id=area_id,
                name=name,
                aliases=aliases,
                parent_area_id=parent_area_id,
                parent_area_name=parent_area_name
            )
        
        logger.info(f"Built area index with {len(areas)} areas")
    
    async def _add_entity_to_index(
        self,
        index: PersonalizedEntityIndex,
        entity_data: dict[str, Any],
        area_map: dict[str, str]
    ) -> None:
        """
        Add entity to index with all name variations.
        
        Args:
            index: PersonalizedEntityIndex to add to
            entity_data: Entity data from Entity Registry
            area_map: Map of area_id -> area_name
        """
        entity_id = entity_data.get("entity_id")
        if not entity_id:
            return
        
        # Extract domain
        domain = entity_id.split(".")[0] if "." in entity_id else "unknown"
        
        # Extract name variations
        name_variants: dict[str, str] = {}
        
        # Standard name
        if "name" in entity_data and entity_data["name"]:
            name_variants["name"] = entity_data["name"]
        
        # User-defined name
        if "name_by_user" in entity_data and entity_data["name_by_user"]:
            name_variants["name_by_user"] = entity_data["name_by_user"]
        
        # Aliases (can be list or string)
        aliases = entity_data.get("aliases", [])
        if aliases:
            if isinstance(aliases, list):
                for i, alias in enumerate(aliases):
                    if alias:
                        name_variants[f"alias_{i}"] = str(alias)
            elif isinstance(aliases, str):
                name_variants["alias_0"] = aliases
        
        # Friendly name (from States API if available)
        # Note: This might need to be fetched separately
        friendly_name = entity_data.get("friendly_name")
        if friendly_name:
            name_variants["friendly_name"] = friendly_name
        
        # If no name variants found, use entity_id as fallback
        if not name_variants:
            # Extract readable name from entity_id
            readable_name = entity_id.split(".")[-1].replace("_", " ").title()
            name_variants["name"] = readable_name
        
        # Extract device and area info
        device_id = entity_data.get("device_id")
        area_id = entity_data.get("area_id")
        area_name = area_map.get(area_id) if area_id else None
        
        # Add to index
        index.add_entity(
            entity_id=entity_id,
            domain=domain,
            name_variants=name_variants,
            device_id=device_id,
            area_id=area_id,
            area_name=area_name
        )
    
    async def update_entity(
        self,
        index: PersonalizedEntityIndex,
        entity_id: str
    ) -> bool:
        """
        Update single entity in index (incremental update).
        
        Args:
            index: PersonalizedEntityIndex to update
            entity_id: Entity ID to update
        
        Returns:
            True if updated, False if not found
        """
        try:
            # Fetch single entity
            entity_data = await self.ha_client.get_entity(entity_id)
            if not entity_data:
                return False
            
            # Fetch areas
            areas = await self._fetch_areas()
            area_map = {area["area_id"]: area.get("name") for area in areas if area.get("area_id")}
            
            # Remove old entry if exists
            if entity_id in index._index:
                entry = index._index[entity_id]
                # Remove from variant index
                for variant in entry.variants:
                    variants = index._variant_index.get(variant.variant_name.lower(), [])
                    if entity_id in variants:
                        variants.remove(entity_id)
                # Remove from area index
                if entry.area_id:
                    area_entities = index._area_index.get(entry.area_id, [])
                    if entity_id in area_entities:
                        area_entities.remove(entity_id)
            
            # Add updated entity
            await self._add_entity_to_index(index, entity_data, area_map)
            
            logger.info(f"Updated entity in index: {entity_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update entity {entity_id}: {e}", exc_info=True)
            return False

