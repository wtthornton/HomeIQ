"""
Unified Entity Validator

Consolidates entity validation from multiple sources:
- EntityValidator (primary)
- EnsembleEntityValidator (if available)
- EntityIDValidator (fallback)

Created: Phase 2 - Core Service Refactoring
"""

import logging
from typing import Any

from ...clients.data_api_client import DataAPIClient
from ...clients.ha_client import HomeAssistantClient
from ...services.entity_validator import EntityValidator as LegacyEntityValidator

logger = logging.getLogger(__name__)


class EntityValidator:
    """
    Unified entity validator that consolidates all validation methods.
    
    Validates that entities exist in Home Assistant and provides
    suggestions for similar entities if not found.
    """

    def __init__(
        self,
        ha_client: HomeAssistantClient | None = None,
        data_api_client: DataAPIClient | None = None,
        enable_ensemble: bool = True
    ):
        """
        Initialize unified entity validator.
        
        Args:
            ha_client: Home Assistant client for entity validation
            data_api_client: Data API client for entity lookups
            enable_ensemble: Whether to use ensemble validation (if available)
        """
        self.ha_client = ha_client
        self.data_api_client = data_api_client or DataAPIClient()
        self.enable_ensemble = enable_ensemble

        # Initialize legacy validator (will be refactored later)
        self._legacy_validator: LegacyEntityValidator | None = None

        logger.info("EntityValidator initialized")

    def _get_validator(self) -> LegacyEntityValidator:
        """Get or create legacy validator instance"""
        if self._legacy_validator is None:
            self._legacy_validator = LegacyEntityValidator(
                data_api_client=self.data_api_client,
                ha_client=self.ha_client,
                enable_full_chain=True
            )
        return self._legacy_validator

    async def validate_entities(
        self,
        entity_ids: list[str],
        query_context: str | None = None,
        available_entities: list[dict[str, Any]] | None = None
    ) -> dict[str, bool]:
        """
        Validate that entities exist in Home Assistant.
        
        Args:
            entity_ids: List of entity IDs to validate
            query_context: Optional query context for better matching
            available_entities: Optional pre-fetched entity list
        
        Returns:
            Dictionary mapping entity_id to validation result (True/False)
        """
        if not entity_ids:
            return {}

        try:
            validator = self._get_validator()

            # Use legacy validator's verify method
            results = await validator.verify_entities_exist_in_ha(
                entity_ids=entity_ids,
                ha_client=self.ha_client,
                use_ensemble=self.enable_ensemble,
                query_context=query_context,
                available_entities=available_entities
            )

            valid_count = sum(1 for v in results.values() if v)
            logger.info(f"✅ Validated {valid_count}/{len(entity_ids)} entities")

            return results

        except Exception as e:
            logger.error(f"❌ Entity validation failed: {e}", exc_info=True)
            # Return all False on error
            return dict.fromkeys(entity_ids, False)

    async def suggest_alternatives(
        self,
        entity_id: str,
        query_context: str | None = None
    ) -> list[str]:
        """
        Suggest alternative entities if the given entity doesn't exist.
        
        Args:
            entity_id: Entity ID that wasn't found
            query_context: Optional query context for better suggestions
        
        Returns:
            List of suggested alternative entity IDs
        """
        try:
            validator = self._get_validator()

            # Use legacy validator's suggestion logic
            # This will be enhanced in future iterations
            return []

        except Exception as e:
            logger.error(f"❌ Failed to suggest alternatives: {e}", exc_info=True)
            return []

