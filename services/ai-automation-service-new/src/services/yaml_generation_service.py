"""
YAML Generation Service

Epic 39, Story 39.10: Automation Service Foundation
Core service for generating Home Assistant automation YAML from suggestions.
"""

import logging
import re
from typing import Any

import yaml

from ..clients.data_api_client import DataAPIClient
from ..clients.openai_client import OpenAIClient
from ..database.models import Suggestion

logger = logging.getLogger(__name__)


class YAMLGenerationError(Exception):
    """Base exception for YAML generation errors."""
    pass


class InvalidSuggestionError(YAMLGenerationError):
    """Raised when suggestion data is invalid."""
    pass


class YAMLGenerationService:
    """
    Service for generating Home Assistant automation YAML from suggestions.
    
    Features:
    - Generate YAML from suggestion descriptions
    - Validate YAML syntax
    - Clean and format YAML
    - Entity validation
    """

    def __init__(
        self,
        openai_client: OpenAIClient,
        data_api_client: DataAPIClient
    ):
        """
        Initialize YAML generation service.
        
        Args:
            openai_client: Client for generating YAML via OpenAI
            data_api_client: Client for validating entities
        """
        self.openai_client = openai_client
        self.data_api_client = data_api_client

    async def generate_automation_yaml(
        self,
        suggestion: dict[str, Any] | Suggestion
    ) -> str:
        """
        Generate Home Assistant automation YAML from a suggestion.
        
        Args:
            suggestion: Suggestion dictionary or Suggestion model instance
        
        Returns:
            Generated YAML string
        
        Raises:
            InvalidSuggestionError: If suggestion is invalid
            YAMLGenerationError: If YAML generation fails
        """
        try:
            # Extract suggestion data
            if isinstance(suggestion, Suggestion):
                description = suggestion.description or ""
                title = suggestion.title or "Automation"
            else:
                description = suggestion.get("description", "")
                title = suggestion.get("title", "Automation")
            
            if not description:
                raise InvalidSuggestionError("Suggestion description is required")
            
            # Build prompt for YAML generation
            prompt = f"""Generate a Home Assistant automation YAML for the following automation:

Title: {title}
Description: {description}

Requirements:
- Use valid Home Assistant automation YAML format
- Include id, alias, description, trigger, and action sections
- Use proper entity IDs
- Include error handling
- Return ONLY the YAML, no explanations or markdown code blocks
"""
            
            # Generate YAML using OpenAI
            yaml_content = await self.openai_client.generate_yaml(
                prompt=prompt,
                temperature=0.1,  # Low temperature for deterministic YAML
                max_tokens=2000
            )
            
            # Clean YAML (remove markdown code blocks if present)
            yaml_content = self._clean_yaml_content(yaml_content)
            
            # Validate YAML syntax
            try:
                yaml.safe_load(yaml_content)
            except yaml.YAMLError as e:
                logger.error(f"Generated YAML is invalid: {e}")
                raise YAMLGenerationError(f"Invalid YAML syntax: {e}")
            
            logger.info(f"Generated YAML for suggestion: {title}")
            return yaml_content
            
        except InvalidSuggestionError:
            raise
        except YAMLGenerationError:
            raise
        except Exception as e:
            logger.error(f"Failed to generate YAML: {e}")
            raise YAMLGenerationError(f"YAML generation failed: {e}")

    def _clean_yaml_content(self, yaml_content: str) -> str:
        """
        Clean YAML content by removing markdown code blocks.
        
        Args:
            yaml_content: Raw YAML string
        
        Returns:
            Cleaned YAML string
        """
        # Remove markdown code blocks
        if yaml_content.startswith("```"):
            lines = yaml_content.split("\n")
            # Remove first line (```yaml or ```)
            if lines[0].startswith("```"):
                lines = lines[1:]
            # Remove last line (```)
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            yaml_content = "\n".join(lines)
        
        # Remove document separators (---)
        yaml_content = re.sub(r'^---\s*$', '', yaml_content, flags=re.MULTILINE)
        
        return yaml_content.strip()

    async def validate_yaml(self, yaml_content: str) -> tuple[bool, str | None]:
        """
        Validate YAML syntax and structure.
        
        Args:
            yaml_content: YAML string to validate
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Parse YAML
            data = yaml.safe_load(yaml_content)
            
            if not data:
                return (False, "YAML is empty")
            
            # Check for required automation fields
            if not isinstance(data, dict):
                return (False, "YAML root must be a dictionary")
            
            # Check for id or alias (at least one required)
            if "id" not in data and "alias" not in data:
                return (False, "YAML must contain 'id' or 'alias' field")
            
            # Check for trigger
            if "trigger" not in data:
                return (False, "YAML must contain 'trigger' field")
            
            # Check for action
            if "action" not in data:
                return (False, "YAML must contain 'action' field")
            
            return (True, None)
            
        except yaml.YAMLError as e:
            return (False, f"YAML syntax error: {e}")
        except Exception as e:
            return (False, f"Validation error: {e}")

    async def validate_entities(
        self,
        yaml_content: str
    ) -> tuple[bool, list[str]]:
        """
        Validate that all entity IDs in YAML exist.
        
        Args:
            yaml_content: YAML string to validate
        
        Returns:
            Tuple of (all_valid, list_of_invalid_entities)
        """
        try:
            # Parse YAML
            data = yaml.safe_load(yaml_content)
            
            if not data:
                return (True, [])
            
            # Extract entity IDs from YAML
            entity_ids = self._extract_entity_ids(data)
            
            if not entity_ids:
                return (True, [])
            
            # Fetch all entities from Data API
            entities = await self.data_api_client.fetch_entities()
            valid_entity_ids = {e.get("entity_id") for e in entities if e.get("entity_id")}
            
            # Check which entities are invalid
            invalid_entities = [eid for eid in entity_ids if eid not in valid_entity_ids]
            
            return (len(invalid_entities) == 0, invalid_entities)
            
        except Exception as e:
            logger.error(f"Failed to validate entities: {e}")
            return (False, [])

    def _extract_entity_ids(self, data: Any, entity_ids: list[str] | None = None) -> list[str]:
        """
        Recursively extract entity IDs from YAML data.
        
        Args:
            data: YAML data structure
            entity_ids: Accumulator for entity IDs
        
        Returns:
            List of entity IDs found
        """
        if entity_ids is None:
            entity_ids = []
        
        if isinstance(data, dict):
            # Check for entity_id field
            if "entity_id" in data:
                entity_id = data["entity_id"]
                if isinstance(entity_id, str) and "." in entity_id:
                    entity_ids.append(entity_id)
            
            # Recursively check all values
            for value in data.values():
                self._extract_entity_ids(value, entity_ids)
        
        elif isinstance(data, list):
            # Recursively check all items
            for item in data:
                self._extract_entity_ids(item, entity_ids)
        
        elif isinstance(data, str):
            # Check if string looks like an entity ID (domain.entity_name)
            if "." in data and len(data.split(".")) == 2:
                parts = data.split(".")
                if len(parts[0]) > 0 and len(parts[1]) > 0:
                    entity_ids.append(data)
        
        return entity_ids

