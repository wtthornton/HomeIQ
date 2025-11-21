"""
Automation YAML Generator

Wrapper class for YAML generation service.
Generates Home Assistant automation YAML from suggestions.

Created: Phase 2 - Core Service Refactoring
Refactored: Now uses yaml_generation_service module
"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...clients.ha_client import HomeAssistantClient
from ...llm.openai_client import OpenAIClient
from .yaml_generation_service import generate_automation_yaml

logger = logging.getLogger(__name__)


class AutomationYAMLGenerator:
    """
    Unified YAML generator for Home Assistant automations.
    
    Generates valid YAML from natural language suggestions with
    entity validation and capability awareness.
    """

    def __init__(
        self,
        openai_client: OpenAIClient,
        ha_client: HomeAssistantClient | None = None
    ):
        """
        Initialize YAML generator.
        
        Args:
            openai_client: OpenAI client for YAML generation
            ha_client: Optional Home Assistant client for validation
        """
        self.openai_client = openai_client
        self.ha_client = ha_client

        logger.info("AutomationYAMLGenerator initialized")

    async def generate(
        self,
        suggestion: dict[str, Any],
        original_query: str,
        entities: list[dict[str, Any]] | None = None,
        validated_entities: dict[str, str] | None = None,
        db_session: AsyncSession | None = None
    ) -> str:
        """
        Generate automation YAML from suggestion.
        
        Args:
            suggestion: Suggestion dictionary with description, devices, etc.
            original_query: Original user query for context
            entities: Optional list of entities
            validated_entities: Dictionary mapping device names to entity IDs
            db_session: Optional database session
        
        Returns:
            YAML string for the automation
        """
        try:
            yaml_content = await generate_automation_yaml(
                suggestion=suggestion,
                original_query=original_query,
                openai_client=self.openai_client,
                entities=entities,
                db_session=db_session,
                ha_client=self.ha_client
            )

            logger.info("✅ Generated automation YAML")
            return yaml_content

        except Exception as e:
            logger.error(f"❌ YAML generation failed: {e}", exc_info=True)
            raise

