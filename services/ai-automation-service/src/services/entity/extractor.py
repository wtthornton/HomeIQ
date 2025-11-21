"""
Unified Entity Extractor

Consolidates entity extraction from multiple sources:
- MultiModelEntityExtractor (primary)
- EnhancedEntityExtractor (fallback)
- Pattern-based extraction (emergency)

Created: Phase 2 - Core Service Refactoring
"""

import logging
from typing import Any

from ...clients.device_intelligence_client import DeviceIntelligenceClient
from ...entity_extraction.enhanced_extractor import EnhancedEntityExtractor
from ...entity_extraction.multi_model_extractor import MultiModelEntityExtractor
from ..config import settings

logger = logging.getLogger(__name__)


class EntityExtractor:
    """
    Unified entity extractor that consolidates all extraction methods.

    Uses multi-model approach with fallbacks:
    1. MultiModelEntityExtractor (primary - NER + OpenAI)
    2. EnhancedEntityExtractor (fallback)
    3. Pattern-based extraction (emergency)
    """

    def __init__(
        self,
        device_intelligence_client: DeviceIntelligenceClient | None = None,
        openai_api_key: str | None = None,
        ner_model: str | None = None,
        openai_model: str | None = None,
    ):
        """
        Initialize unified entity extractor.

        Args:
            device_intelligence_client: Optional device intelligence client
            openai_api_key: OpenAI API key (defaults to settings)
            ner_model: NER model name (defaults to settings)
            openai_model: OpenAI model name (defaults to settings)
        """
        self.device_intelligence_client = device_intelligence_client

        # Use provided values or fall back to settings
        self.openai_api_key = openai_api_key or settings.openai_api_key
        self.ner_model = ner_model or settings.ner_model
        self.openai_model = openai_model or settings.openai_model

        # Initialize primary extractor
        self._multi_model_extractor: MultiModelEntityExtractor | None = None
        self._enhanced_extractor: EnhancedEntityExtractor | None = None

        logger.info("EntityExtractor initialized")

    def _get_multi_model_extractor(self) -> MultiModelEntityExtractor:
        """Get or create multi-model extractor"""
        if self._multi_model_extractor is None:
            self._multi_model_extractor = MultiModelEntityExtractor(
                openai_api_key=self.openai_api_key,
                device_intelligence_client=self.device_intelligence_client,
                ner_model=self.ner_model,
                openai_model=self.openai_model,
            )
        return self._multi_model_extractor

    def _get_enhanced_extractor(self) -> EnhancedEntityExtractor | None:
        """Get or create enhanced extractor (fallback)"""
        if self._enhanced_extractor is None and self.device_intelligence_client:
            try:
                self._enhanced_extractor = EnhancedEntityExtractor(
                    self.device_intelligence_client,
                )
            except Exception as e:
                logger.warning(f"Failed to initialize EnhancedEntityExtractor: {e}")
        return self._enhanced_extractor

    async def extract(
        self,
        query: str,
        context: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Extract entities from natural language query.

        Args:
            query: Natural language query string
            context: Optional context (conversation history, etc.)

        Returns:
            List of extracted entities with metadata
        """
        try:
            # Primary: Use multi-model extractor
            extractor = self._get_multi_model_extractor()
            entities = await extractor.extract_entities(query)

            if entities:
                logger.info(f"✅ Extracted {len(entities)} entities using MultiModelEntityExtractor")
                return entities

            # Fallback: Use enhanced extractor
            enhanced_extractor = self._get_enhanced_extractor()
            if enhanced_extractor:
                entities = await enhanced_extractor.extract_entities(query)
                if entities:
                    logger.info(f"✅ Extracted {len(entities)} entities using EnhancedEntityExtractor")
                    return entities

            # Emergency: Pattern-based extraction
            from ...entity_extraction.pattern_extractor import extract_entities_from_query
            entities = extract_entities_from_query(query)
            if entities:
                logger.info(f"✅ Extracted {len(entities)} entities using pattern extraction")
                return entities

            logger.warning(f"⚠️ No entities extracted from query: {query[:50]}...")
            return []

        except Exception as e:
            logger.error(f"❌ Entity extraction failed: {e}", exc_info=True)
            # Return empty list on error
            return []

