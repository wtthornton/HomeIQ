"""
Unified Entity Resolver

Resolves device names, aliases, and generic references to specific entity IDs.
Handles:
- Device name to entity_id mapping
- Group entity expansion
- Alias resolution
- Fuzzy matching
- RAG-enhanced semantic disambiguation

Created: Phase 2 - Core Service Refactoring
Enhanced: RAG integration for semantic entity disambiguation
"""

import logging
from typing import Dict, List, Optional, Any
from ...clients.ha_client import HomeAssistantClient
from ...services.entity_validator import EntityValidator as LegacyEntityValidator
from ...clients.data_api_client import DataAPIClient

logger = logging.getLogger(__name__)

# Optional RAG client import
try:
    from ...services.rag.client import RAGClient
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    RAGClient = None


class EntityResolver:
    """
    Unified entity resolver for mapping device names to entity IDs.
    
    Resolves:
    - Generic device names ("office lights") to specific entity IDs
    - Group entities to individual members
    - User-defined aliases
    - Fuzzy matching for typos
    - RAG-enhanced semantic disambiguation when exact matches are ambiguous
    """
    
    def __init__(
        self,
        ha_client: Optional[HomeAssistantClient] = None,
        data_api_client: Optional[DataAPIClient] = None,
        rag_client: Optional[Any] = None  # RAGClient type, but optional
    ):
        """
        Initialize unified entity resolver.
        
        Args:
            ha_client: Home Assistant client
            data_api_client: Data API client
            rag_client: Optional RAG client for semantic entity disambiguation
        """
        self.ha_client = ha_client
        self.data_api_client = data_api_client or DataAPIClient()
        self.rag_client = rag_client
        
        # Initialize validator for resolution
        self._validator: Optional[LegacyEntityValidator] = None
        
        if rag_client:
            logger.info("EntityResolver initialized with RAG client for semantic disambiguation")
        else:
            logger.info("EntityResolver initialized (RAG client not available)")
    
    def _get_validator(self) -> LegacyEntityValidator:
        """Get or create validator instance"""
        if self._validator is None:
            self._validator = LegacyEntityValidator(
                data_api_client=self.data_api_client,
                ha_client=self.ha_client
            )
        return self._validator
    
    async def resolve_device_names(
        self,
        device_names: List[str],
        query: Optional[str] = None,
        area_id: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Resolve device names to entity IDs.
        
        Uses RAG for semantic disambiguation when exact matches are ambiguous.
        
        Args:
            device_names: List of device names to resolve
            query: Optional query context for better matching
            area_id: Optional area filter
        
        Returns:
            Dictionary mapping device_name to entity_id
        """
        if not device_names:
            return {}
        
        try:
            validator = self._get_validator()
            
            # Step 1: Try exact matching first
            mapping = await validator.map_query_to_entities(
                query=query or " ".join(device_names),
                device_names=device_names
            )
            
            # Step 2: Use RAG for unresolved or ambiguous matches
            unresolved_names = [name for name in device_names if name not in mapping]
            
            if unresolved_names and self.rag_client:
                try:
                    # Use RAG to find similar entities
                    rag_query = query or " ".join(unresolved_names)
                    
                    # Search for entity-related knowledge
                    rag_results = await self.rag_client.retrieve_hybrid(
                        query=rag_query,
                        knowledge_type="entity",  # Filter for entity knowledge
                        top_k=10,
                        min_similarity=0.6,  # Lower threshold for entity matching
                        filter_metadata={"area_id": area_id} if area_id else None
                    )
                    
                    # Merge RAG results with exact matches
                    for result in rag_results:
                        # Extract entity_id from metadata if available
                        metadata = result.get("metadata", {})
                        entity_id = metadata.get("entity_id")
                        entity_name = metadata.get("name") or metadata.get("friendly_name")
                        
                        if entity_id and entity_name:
                            # Match unresolved names to RAG results
                            for unresolved_name in unresolved_names:
                                if unresolved_name.lower() in entity_name.lower() or \
                                   entity_name.lower() in unresolved_name.lower():
                                    mapping[unresolved_name] = entity_id
                                    logger.debug(
                                        f"RAG match: '{unresolved_name}' → {entity_id} "
                                        f"(similarity: {result.get('similarity', 0):.2f})"
                                    )
                                    break
                    
                    if len(mapping) > len([name for name in device_names if name in mapping]):
                        logger.info(
                            f"✅ RAG enhanced resolution: {len(mapping)}/{len(device_names)} device names resolved"
                        )
                
                except Exception as e:
                    logger.warning(f"RAG disambiguation failed (falling back to exact matching): {e}")
                    # Continue with exact matches only
            
            logger.info(f"✅ Resolved {len(mapping)}/{len(device_names)} device names")
            return mapping
            
        except Exception as e:
            logger.error(f"❌ Device name resolution failed: {e}", exc_info=True)
            return {}
    
    async def expand_group_entities(
        self,
        entity_ids: List[str]
    ) -> List[str]:
        """
        Expand group entities to their individual member entities.
        
        Args:
            entity_ids: List of entity IDs (may include groups)
        
        Returns:
            Expanded list of entity IDs (groups replaced with members)
        """
        if not entity_ids or not self.ha_client:
            return entity_ids
        
        try:
            expanded = []
            
            for entity_id in entity_ids:
                # Check if it's a group entity
                if entity_id.startswith("group."):
                    # Get group members
                    try:
                        state = await self.ha_client.get_entity_state(entity_id)
                        if state and "entity_id" in state.get("attributes", {}):
                            members = state["attributes"]["entity_id"]
                            if isinstance(members, list):
                                expanded.extend(members)
                                logger.debug(f"Expanded group {entity_id} to {len(members)} members")
                            else:
                                expanded.append(entity_id)
                        else:
                            expanded.append(entity_id)
                    except Exception as e:
                        logger.warning(f"Failed to expand group {entity_id}: {e}")
                        expanded.append(entity_id)
                else:
                    expanded.append(entity_id)
            
            if len(expanded) > len(entity_ids):
                logger.info(f"✅ Expanded {len(entity_ids)} entities to {len(expanded)} members")
            
            return expanded
            
        except Exception as e:
            logger.error(f"❌ Group expansion failed: {e}", exc_info=True)
            return entity_ids
    
    async def resolve_aliases(
        self,
        aliases: List[str],
        user_id: str = "anonymous"
    ) -> Dict[str, str]:
        """
        Resolve user-defined aliases to entity IDs.
        
        Args:
            aliases: List of aliases to resolve
            user_id: User ID for alias lookup
        
        Returns:
            Dictionary mapping alias to entity_id
        """
        if not aliases:
            return {}
        
        try:
            # Query database for aliases
            from ...database import get_db
            from ...database.models import EntityAlias
            from sqlalchemy import select
            
            # This will need async session - simplified for now
            # Full implementation will be in Phase 2 completion
            logger.warning("Alias resolution not fully implemented yet")
            return {}
            
        except Exception as e:
            logger.error(f"❌ Alias resolution failed: {e}", exc_info=True)
            return {}

