"""
Unified Entity Extractor (2025)

Uses the UnifiedExtractionPipeline for entity extraction.
Converts AutomationContext to legacy entities format for backward compatibility.

Created: Phase 2 - Core Service Refactoring
Updated: 2025 - Migrated to UnifiedExtractionPipeline
"""

import logging
from typing import Any

from ...clients.device_intelligence_client import DeviceIntelligenceClient
from ...clients.ha_client import HomeAssistantClient
from ...llm.openai_client import OpenAIClient
from ...extraction.pipeline import UnifiedExtractionPipeline
from ...extraction.models import AutomationContext
from ..config import settings

logger = logging.getLogger(__name__)


def _convert_unified_context_to_entities(context: AutomationContext) -> list[dict[str, Any]]:
    """
    Convert AutomationContext to legacy entities list shape.
    
    Produces:
    - Area entities: {'name': <area>, 'type': 'area', ...}
    - Device entities (action/trigger): {'entity_id': <id>, 'name': <id>, 'type': 'device', 'domain': <domain>, ...}
    """
    entities: list[dict[str, Any]] = []

    # Areas
    for area in context.spatial.areas or []:
        entities.append({
            'name': area,
            'type': 'area',
            'domain': 'unknown',
            'confidence': 0.9,
            'extraction_method': 'unified_pipeline'
        })

    # Helper to add device entities
    def _add_device_entity(entity_id: str, role: str):
        domain = entity_id.split('.')[0] if entity_id and '.' in entity_id else 'unknown'
        entities.append({
            'entity_id': entity_id,
            'name': entity_id,  # Back-compat: some code reads 'name'
            'friendly_name': entity_id,
            'type': 'device',
            'domain': domain,
            'role': role,
            'confidence': 0.95,
            'extraction_method': 'unified_pipeline'
        })

    # Action devices
    for eid in context.devices.action_entities or []:
        if isinstance(eid, str) and eid:
            _add_device_entity(eid, role='action')

    # Trigger devices
    for eid in context.devices.trigger_entities or []:
        if isinstance(eid, str) and eid:
            _add_device_entity(eid, role='trigger')

    return entities


class EntityExtractor:
    """
    Unified entity extractor using UnifiedExtractionPipeline (2025).
    
    This is a wrapper that converts the new AutomationContext format
    to the legacy entities list format for backward compatibility.
    """

    def __init__(
        self,
        device_intelligence_client: DeviceIntelligenceClient | None = None,
        ha_client: HomeAssistantClient | None = None,
        openai_client: OpenAIClient | None = None,
        openai_api_key: str | None = None,
        ner_model: str | None = None,
        openai_model: str | None = None
    ):
        """
        Initialize unified entity extractor.
        
        Args:
            device_intelligence_client: Optional device intelligence client
            ha_client: Optional Home Assistant client (required for unified pipeline)
            openai_client: Optional OpenAI client (required for unified pipeline)
            openai_api_key: OpenAI API key (deprecated - use openai_client instead)
            ner_model: NER model name (deprecated - not used by unified pipeline)
            openai_model: OpenAI model name (deprecated - use openai_client instead)
        """
        self.device_intelligence_client = device_intelligence_client
        self.ha_client = ha_client
        self.openai_client = openai_client
        
        # Store deprecated params for backward compatibility but don't use them
        self.openai_api_key = openai_api_key or settings.openai_api_key
        self.ner_model = ner_model or settings.ner_model
        self.openai_model = openai_model or settings.openai_model

        # Pipeline will be initialized lazily when clients are available
        self._pipeline: UnifiedExtractionPipeline | None = None

        logger.info("EntityExtractor initialized (using UnifiedExtractionPipeline)")

    def _get_pipeline(self) -> UnifiedExtractionPipeline | None:
        """Get or create unified extraction pipeline"""
        if self._pipeline is None:
            # Need both HA and OpenAI clients for unified pipeline
            if not self.ha_client or not self.openai_client:
                logger.warning("⚠️ Cannot initialize UnifiedExtractionPipeline - missing HA or OpenAI client")
                return None
            
            self._pipeline = UnifiedExtractionPipeline(
                ha_client=self.ha_client,
                openai_client=self.openai_client,
                device_client=self.device_intelligence_client
            )
            logger.debug("✅ UnifiedExtractionPipeline initialized")
        return self._pipeline

    async def extract(
        self,
        query: str,
        context: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """
        Extract entities from natural language query using UnifiedExtractionPipeline.
        
        Args:
            query: Natural language query string
            context: Optional context (conversation history, etc.) - not used by unified pipeline
        
        Returns:
            List of extracted entities with metadata (legacy format for backward compatibility)
        """
        try:
            pipeline = self._get_pipeline()
            if not pipeline:
                logger.warning(f"⚠️ Unified pipeline not available, returning empty entities for: {query[:50]}...")
                return []

            # Run unified extraction pipeline
            automation_context = await pipeline.process(query)
            
            # Convert to legacy format
            entities = _convert_unified_context_to_entities(automation_context)
            
            if entities:
                logger.info(f"✅ Extracted {len(entities)} entities using UnifiedExtractionPipeline "
                           f"(areas={len(automation_context.spatial.areas)}, "
                           f"action={len(automation_context.devices.action_entities)}, "
                           f"trigger={len(automation_context.devices.trigger_entities)})")
                return entities

            logger.warning(f"⚠️ No entities extracted from query: {query[:50]}...")
            return []

        except Exception as e:
            logger.error(f"❌ Entity extraction failed: {e}", exc_info=True)
            # Return empty list on error
            return []

