"""
Context Builder Service
Orchestrates all Tier 1 context components for OpenAI agent
"""

import logging
from datetime import datetime, timedelta

from sqlalchemy import select

from ..config import Settings
from ..database import ContextCache, get_session
from ..prompts.system_prompt import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class ContextBuilder:
    """
    Orchestrates all Tier 1 context components and formats context for OpenAI.

    Epic AI-19: Tier 1 context injection system
    """

    def __init__(self, settings: Settings):
        """
        Initialize context builder.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self._initialized = False
        self._entity_inventory_service = None
        self._areas_service = None
        self._services_summary_service = None
        self._capability_patterns_service = None
        self._helpers_scenes_service = None
        self._entity_attributes_service = None

    async def initialize(self) -> None:
        """Initialize context builder and all services"""
        # Lazy imports to avoid circular dependencies
        from .areas_service import AreasService
        from .capability_patterns_service import CapabilityPatternsService
        from .entity_attributes_service import EntityAttributesService
        from .entity_inventory_service import EntityInventoryService
        from .helpers_scenes_service import HelpersScenesService
        from .services_summary_service import ServicesSummaryService

        self._entity_inventory_service = EntityInventoryService(
            settings=self.settings,
            context_builder=self
        )
        self._areas_service = AreasService(
            settings=self.settings,
            context_builder=self
        )
        self._services_summary_service = ServicesSummaryService(
            settings=self.settings,
            context_builder=self
        )
        self._capability_patterns_service = CapabilityPatternsService(
            settings=self.settings,
            context_builder=self
        )
        self._helpers_scenes_service = HelpersScenesService(
            settings=self.settings,
            context_builder=self
        )
        self._entity_attributes_service = EntityAttributesService(
            settings=self.settings,
            context_builder=self
        )
        self._initialized = True
        logger.info("✅ Context builder initialized with all services")

    async def close(self) -> None:
        """Cleanup resources"""
        if self._entity_inventory_service:
            await self._entity_inventory_service.close()
        if self._areas_service:
            await self._areas_service.close()
        if self._services_summary_service:
            await self._services_summary_service.close()
        if self._capability_patterns_service:
            await self._capability_patterns_service.close()
        if self._helpers_scenes_service:
            await self._helpers_scenes_service.close()
        if self._entity_attributes_service:
            await self._entity_attributes_service.close()
        self._initialized = False
        logger.info("✅ Context builder closed")

    async def build_context(self) -> str:
        """
        Build complete Tier 1 context for OpenAI agent.

        Returns:
            Formatted context string ready for OpenAI system/user prompts
        """
        if not self._initialized:
            logger.error(
                "❌ CRITICAL: Context builder not initialized! "
                "Call context_builder.initialize() first."
            )
            raise RuntimeError("Context builder not initialized")

        logger.debug("Building Tier 1 context (entity inventory, areas, services, etc.)")
        context_parts = ["HOME ASSISTANT CONTEXT:\n"]

        # Story AI19.2 - Entity Inventory Summary
        try:
            logger.debug("Fetching entity inventory summary...")
            entity_summary = await self._entity_inventory_service.get_summary()
            if entity_summary and len(entity_summary.strip()) > 0:
                context_parts.append(f"ENTITY INVENTORY:\n{entity_summary}\n")
                logger.debug(f"✅ Entity inventory added ({len(entity_summary)} chars)")
            else:
                logger.warning("⚠️ Entity inventory summary is empty")
                context_parts.append("ENTITY INVENTORY: (unavailable)\n")
        except Exception as e:
            logger.error(f"❌ Failed to get entity inventory: {e}", exc_info=True)
            context_parts.append("ENTITY INVENTORY: (unavailable)\n")

        # Story AI19.3 - Areas/Rooms List
        try:
            areas_list = await self._areas_service.get_areas_list()
            context_parts.append(f"AREAS:\n{areas_list}\n")
        except Exception as e:
            logger.warning(f"⚠️ Failed to get areas: {e}")
            context_parts.append("AREAS: (unavailable)\n")

        # Story AI19.4 - Available Services Summary
        try:
            services_summary = await self._services_summary_service.get_summary()
            context_parts.append(f"AVAILABLE SERVICES:\n{services_summary}\n")
        except Exception as e:
            logger.warning(f"⚠️ Failed to get services summary: {e}")
            context_parts.append("AVAILABLE SERVICES: (unavailable)\n")

        # Story AI19.5 - Device Capability Patterns (OPTIONAL - consolidated into Entity Inventory)
        # Skip capability patterns in default context to avoid duplication
        # Capability patterns are already shown in Entity Inventory examples (effect_list, color_modes, etc.)
        logger.debug("⏭️ Skipping capability patterns (consolidated into entity inventory for token efficiency)")

        # Story AI19.6 - Helpers & Scenes Summary
        try:
            helpers_scenes_summary = await self._helpers_scenes_service.get_summary()
            context_parts.append(f"HELPERS & SCENES:\n{helpers_scenes_summary}\n")
        except Exception as e:
            logger.warning(f"⚠️ Failed to get helpers/scenes: {e}")
            context_parts.append("HELPERS & SCENES: (unavailable)\n")

        # Entity Attributes (OPTIONAL - now merged into Entity Inventory for token efficiency)
        # Skip entity attributes in default context to avoid duplication
        # Entity attributes are already included in Entity Inventory examples
        logger.debug("⏭️ Skipping entity attributes (merged into entity inventory for token efficiency)")

        context = "\n".join(context_parts)
        
        # Log context building result
        context_length = len(context)
        unavailable_count = context.count("(unavailable)")
        
        if unavailable_count > 0:
            logger.warning(
                f"⚠️ Context built with {unavailable_count} unavailable section(s). "
                f"Total length: {context_length} chars"
            )
        else:
            logger.info(
                f"✅ Context built successfully. Total length: {context_length} chars"
            )
        
        return context

    def get_system_prompt(self) -> str:
        """
        Get the base system prompt for the OpenAI agent.

        Returns:
            System prompt string defining agent role and behavior
        """
        return SYSTEM_PROMPT

    async def build_complete_system_prompt(self) -> str:
        """
        Build complete system prompt with context injection.

        This combines the base system prompt with the Tier 1 context,
        ready to be used as the system message in OpenAI API calls.

        Returns:
            Complete system prompt with context injected
        """
        logger.debug("Building complete system prompt with context injection...")
        
        base_prompt = self.get_system_prompt()
        base_length = len(base_prompt)
        logger.debug(f"Base system prompt length: {base_length} chars")
        
        context = await self.build_context()
        context_length = len(context)
        logger.debug(f"Context length: {context_length} chars")

        # Inject context into the system prompt
        # The system prompt mentions context will be provided, so we append it
        complete_prompt = f"""{base_prompt}

---

{context}"""

        total_length = len(complete_prompt)
        logger.info(
            f"✅ Complete system prompt built: {total_length} chars "
            f"(base: {base_length}, context: {context_length}). "
            f"Contains 'CRITICAL': {'CRITICAL' in complete_prompt}, "
            f"Contains 'HOME ASSISTANT CONTEXT': {'HOME ASSISTANT CONTEXT' in complete_prompt}"
        )

        return complete_prompt

    async def _get_cached_value(self, cache_key: str) -> str | None:
        """
        Get cached value if not expired.

        Args:
            cache_key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        try:
            async for session in get_session():
                now = datetime.now()
                stmt = select(ContextCache.cache_value).where(
                    ContextCache.cache_key == cache_key,
                    ContextCache.expires_at > now
                )
                result = await session.execute(stmt)
                row = result.scalar_one_or_none()
                return row
        except Exception as e:
            logger.warning(f"⚠️ Error reading cache for {cache_key}: {e}")
        return None

    async def _set_cached_value(
        self,
        cache_key: str,
        cache_value: str,
        ttl_seconds: int
    ) -> None:
        """
        Set cached value with TTL.

        Args:
            cache_key: Cache key
            cache_value: Value to cache
            ttl_seconds: Time to live in seconds
        """
        try:
            expires_at = datetime.now() + timedelta(seconds=ttl_seconds)
            async for session in get_session():
                # Check if entry exists
                stmt = select(ContextCache).where(ContextCache.cache_key == cache_key)
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()

                if existing:
                    # Update existing entry
                    existing.cache_value = cache_value
                    existing.expires_at = expires_at
                    existing.updated_at = datetime.now()
                else:
                    # Create new entry
                    cache_entry = ContextCache(
                        cache_key=cache_key,
                        cache_value=cache_value,
                        expires_at=expires_at
                    )
                    session.add(cache_entry)

                await session.commit()
        except Exception as e:
            logger.warning(f"⚠️ Error writing cache for {cache_key}: {e}")

