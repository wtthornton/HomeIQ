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
        self._devices_summary_service = None
        self._areas_service = None
        self._services_summary_service = None
        self._capability_patterns_service = None
        self._helpers_scenes_service = None
        self._entity_attributes_service = None
        self._device_state_context_service = None
        self._automation_patterns_service = None
        self._automation_rag_service = None
        # Reusable Pattern Framework: RAG Context Registry for multi-domain context assembly
        self._rag_registry = None
        # Phase 3: Context prioritization and filtering services
        self._context_prioritization_service = None
        self._context_filtering_service = None
        # Enhanced context builder for area-focused entity context
        self._enhanced_context_builder = None
        # Epic Activity Recognition: Activity context for Tier 1
        self._activity_context_service = None

    async def initialize(self) -> None:
        """Initialize context builder and all services"""
        # Lazy imports to avoid circular dependencies
        from .areas_service import AreasService
        from .automation_patterns_service import AutomationPatternsService
        from .capability_patterns_service import CapabilityPatternsService
        from .context_filtering_service import ContextFilteringService
        from .context_prioritization_service import ContextPrioritizationService
        from .device_state_context_service import DeviceStateContextService
        from .devices_summary_service import DevicesSummaryService
        from .entity_attributes_service import EntityAttributesService
        from .entity_inventory_service import EntityInventoryService
        from .helpers_scenes_service import HelpersScenesService
        from .services_summary_service import ServicesSummaryService

        self._entity_inventory_service = EntityInventoryService(
            settings=self.settings,
            context_builder=self
        )
        self._devices_summary_service = DevicesSummaryService(
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
        self._device_state_context_service = DeviceStateContextService(
            settings=self.settings,
            context_builder=self
        )
        self._automation_patterns_service = AutomationPatternsService(
            settings=self.settings,
            context_builder=self
        )
        from homeiq_patterns import RAGContextRegistry

        from .automation_rag_service import AutomationRAGService
        from .blueprint_rag_service import BlueprintRAGService
        from .comfort_rag_service import ComfortRAGService
        from .device_capability_rag_service import DeviceCapabilityRAGService
        from .device_setup_rag_service import DeviceSetupRAGService
        from .energy_rag_service import EnergyRAGService
        from .scene_script_rag_service import SceneScriptRAGService
        from .security_rag_service import SecurityRAGService
        self._automation_rag_service = AutomationRAGService()
        # Reusable Pattern Framework: Initialize RAG registry and register services
        self._rag_registry = RAGContextRegistry()
        self._rag_registry.register(self._automation_rag_service)
        # Epic: High-Value Domain Extensions — register new RAG services
        self._rag_registry.register(EnergyRAGService())
        self._rag_registry.register(BlueprintRAGService())
        self._rag_registry.register(DeviceSetupRAGService())
        # Epic: Platform-Wide Pattern Rollout — register Phase 4 RAG services
        self._rag_registry.register(SecurityRAGService())
        self._rag_registry.register(ComfortRAGService())
        self._rag_registry.register(SceneScriptRAGService())
        self._rag_registry.register(DeviceCapabilityRAGService())
        # Phase 3: Initialize prioritization and filtering services
        self._context_prioritization_service = ContextPrioritizationService()
        self._context_filtering_service = ContextFilteringService()
        # Enhanced context builder for area-focused entity context
        from .enhanced_context_builder import EnhancedContextBuilder
        self._enhanced_context_builder = EnhancedContextBuilder(settings=self.settings)
        # Epic Activity Recognition: Activity context (Story 2.1)
        from .activity_context_service import ActivityContextService
        self._activity_context_service = ActivityContextService(
            settings=self.settings,
            context_builder=self,
        )
        self._initialized = True
        logger.info("✅ Context builder initialized with all services")

    async def close(self) -> None:
        """Cleanup resources"""
        if self._entity_inventory_service:
            await self._entity_inventory_service.close()
        if self._devices_summary_service:
            await self._devices_summary_service.close()
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
        if self._device_state_context_service:
            await self._device_state_context_service.close()
        if self._automation_patterns_service:
            await self._automation_patterns_service.close()
        if hasattr(self, '_enhanced_context_builder') and self._enhanced_context_builder:
            await self._enhanced_context_builder.close()
        self._initialized = False
        logger.info("✅ Context builder closed")

    async def build_context(self, skip_truncation: bool = False) -> str:
        """
        Build complete Tier 1 context for OpenAI agent.

        Args:
            skip_truncation: If True, skip truncation in all services (for debug display)

        Returns:
            Formatted context string ready for OpenAI system/user prompts
        """
        if not self._initialized:
            logger.error(
                "❌ CRITICAL: Context builder not initialized! "
                "Call context_builder.initialize() first."
            )
            raise RuntimeError("Context builder not initialized")

        logger.debug(f"Building Tier 1 context (devices, areas, services, etc.) - skip_truncation={skip_truncation}")
        context_parts = ["HOME ASSISTANT CONTEXT:\n"]

        # Epic Activity Recognition (Story 2.1): Current household activity
        try:
            if self._activity_context_service:
                activity_line = await self._activity_context_service.get_activity_context_line()
                if activity_line:
                    context_parts.append(f"{activity_line}\n")
        except Exception as e:
            logger.debug("Activity context unavailable: %s", e)

        # Devices Summary - Device details with manufacturer, model, and area
        try:
            logger.debug(f"🔍 Checking devices summary service: {self._devices_summary_service is not None}")
            if self._devices_summary_service is None:
                logger.error("❌ CRITICAL: _devices_summary_service is None! Service not initialized.")
                context_parts.append("DEVICES: (unavailable - service not initialized)\n")
            else:
                logger.info("📱 Fetching devices summary for context injection...")
                logger.debug(f"📱 DevicesSummaryService type: {type(self._devices_summary_service).__name__}")
                devices_summary = await self._devices_summary_service.get_summary(skip_truncation=skip_truncation)
                logger.debug(f"📱 Devices summary received: {len(devices_summary) if devices_summary else 0} chars")
                if devices_summary and len(devices_summary.strip()) > 0:
                    context_parts.append(f"DEVICES:\n{devices_summary}\n")
                    logger.info(f"✅ Devices summary added to context ({len(devices_summary)} chars)")
                else:
                    logger.warning("⚠️ Devices summary is empty - will show 'unavailable' in context")
                    context_parts.append("DEVICES: (unavailable)\n")
        except Exception as e:
            logger.error(f"❌ Failed to get devices summary: {e}", exc_info=True)
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            context_parts.append("DEVICES: (unavailable)\n")

        # Story AI19.3 - Areas/Rooms List
        try:
            areas_list = await self._areas_service.get_areas_list()
            context_parts.append(f"AREAS:\n{areas_list}\n")
        except Exception as e:
            logger.warning(f"⚠️ Failed to get areas: {e}")
            context_parts.append("AREAS: (unavailable)\n")

        # Story AI19.4 - Available Services Summary
        try:
            services_summary = await self._services_summary_service.get_summary(skip_truncation=skip_truncation)
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
            helpers_scenes_summary = await self._helpers_scenes_service.get_summary(skip_truncation=skip_truncation)
            context_parts.append(f"HELPERS & SCENES:\n{helpers_scenes_summary}\n")
        except Exception as e:
            logger.warning(f"⚠️ Failed to get helpers/scenes: {e}")
            context_parts.append("HELPERS & SCENES: (unavailable)\n")

        # Entity Attributes (OPTIONAL - now merged into Entity Inventory for token efficiency)
        # Skip entity attributes in default context to avoid duplication
        # Entity attributes are already included in Entity Inventory examples
        logger.debug("⏭️ Skipping entity attributes (merged into entity inventory for token efficiency)")

        # Phase 2.3: Recent Automation Patterns (OPTIONAL - added dynamically per message if relevant)
        # Automation patterns are added per-message based on user prompt, not in static context
        # This keeps context size manageable while providing relevant patterns when needed
        logger.debug("⏭️ Skipping automation patterns in static context (added dynamically per-message)")

        # Enhanced Context: Entity inventory by area (CRITICAL for automation creation)
        # Provides entity_ids (light.office_go, switch.kitchen, etc.) that the LLM needs for YAML generation.
        # Without this, the LLM has device names but no entity_ids to reference in automation YAML.
        try:
            if hasattr(self, '_enhanced_context_builder') and self._enhanced_context_builder:
                entity_inventory = await self._enhanced_context_builder.build_area_entity_context()
                if entity_inventory and "Unavailable" not in entity_inventory:
                    # Truncate to keep within token budget (already limited to 10 entities/domain/area)
                    max_entity_chars = 6000 if not skip_truncation else 999999
                    if len(entity_inventory) > max_entity_chars:
                        entity_inventory = entity_inventory[:max_entity_chars] + "\n... (truncated for token efficiency)"
                    context_parts.append(f"\n{entity_inventory}")
                    logger.info(f"✅ Added entity inventory context ({len(entity_inventory)} chars)")
                else:
                    logger.warning("⚠️ Entity inventory unavailable")
        except Exception as e:
            logger.warning(f"⚠️ Failed to add entity inventory context: {e}")

        # Enhanced Context: Binary sensors and trigger platforms reference
        # Critical for automation creation - provides entity IDs for motion/presence triggers
        try:
            if hasattr(self, '_enhanced_context_builder') and self._enhanced_context_builder:
                # Add binary sensor context (motion/presence sensors)
                binary_sensor_context = await self._enhanced_context_builder.build_binary_sensor_context()
                if binary_sensor_context and "Unavailable" not in binary_sensor_context:
                    context_parts.append(f"\n{binary_sensor_context}")
                    logger.info("✅ Added binary sensor context for motion/presence detection")

                # Add existing automations (for duplicate detection)
                automations_context = await self._enhanced_context_builder.build_existing_automations_context()
                if automations_context and "Unavailable" not in automations_context:
                    context_parts.append(f"\n{automations_context}")
                    logger.info("✅ Added existing automations context for duplicate detection")

                # Add trigger platforms reference
                trigger_ref = self._enhanced_context_builder.build_trigger_platforms_reference()
                context_parts.append(f"\n{trigger_ref}")
                logger.info("✅ Added trigger platforms reference")
        except Exception as e:
            logger.warning(f"⚠️ Failed to add enhanced context: {e}")

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

    async def get_device_state_context(
        self,
        entity_ids: list[str] | None = None,
        user_prompt: str | None = None,
        skip_truncation: bool = False,
    ) -> str:
        """
        Get device state context for specified entities.

        This is a helper method to access the DeviceStateContextService.
        Device state context is dynamic and should be included per-message,
        not cached with the general context.

        Args:
            entity_ids: Optional list of entity IDs to fetch states for
            user_prompt: Optional user prompt (not used, entity extraction should happen in caller)
            skip_truncation: If True, skip truncation (for debug display)

        Returns:
            Formatted state context string, or empty string if no entities or unavailable
        """
        if not self._device_state_context_service:
            logger.warning("DeviceStateContextService not initialized")
            return ""

        return await self._device_state_context_service.get_state_context(
            entity_ids=entity_ids,
            user_prompt=user_prompt,
            skip_truncation=skip_truncation,
        )

    async def build_filtered_context(
        self,
        user_prompt: str | None = None,
        skip_truncation: bool = False
    ) -> str:
        """
        Build context with Phase 3 filtering and prioritization.

        Args:
            user_prompt: Optional user prompt for intent extraction and prioritization
            skip_truncation: If True, skip truncation in all services

        Returns:
            Filtered and prioritized context string
        """
        if not user_prompt:
            # No user prompt - return standard context
            return await self.build_context(skip_truncation=skip_truncation)

        # Phase 3.2: Extract intent from user prompt
        intent = self._context_filtering_service.extract_intent(user_prompt)
        logger.info(f"🔍 Extracted intent: areas={intent.get('areas')}, domains={intent.get('domains')}, services={intent.get('services')}")

        # Build standard context first
        return await self.build_context(skip_truncation=skip_truncation)

        # Phase 3.1 & 3.2: Apply filtering and prioritization to entity inventory
        # Note: Other context sections (devices, areas, services) are already filtered
        # by the individual services, but we can add prioritization here if needed

        # For now, filtering is handled at the service level (entity_inventory_service)
        # and prioritization can be applied when building entity examples


    async def build_complete_system_prompt(self, skip_truncation: bool = False) -> str:
        """
        Build complete system prompt with context injection.

        This combines the base system prompt with the Tier 1 context,
        ready to be used as the system message in OpenAI API calls.

        Args:
            skip_truncation: If True, skip truncation in all services (for debug display)

        Returns:
            Complete system prompt with context injected
        """
        logger.debug(f"Building complete system prompt with context injection - skip_truncation={skip_truncation}")

        base_prompt = self.get_system_prompt()
        base_length = len(base_prompt)
        logger.debug(f"Base system prompt length: {base_length} chars")

        context = await self.build_context(skip_truncation=skip_truncation)
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
                return result.scalar_one_or_none()
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

