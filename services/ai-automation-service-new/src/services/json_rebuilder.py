"""
LLM JSON Rebuilder Service

Uses LLM to rebuild HomeIQ JSON from YAML or natural language description.
"""

import logging
from typing import Any

from shared.homeiq_automation.schema import HomeIQAutomation

from ..clients.openai_client import OpenAIClient

logger = logging.getLogger(__name__)


class JSONRebuilder:
    """
    Service for rebuilding HomeIQ JSON using LLM.
    
    Use Cases:
    - Rebuild JSON from legacy YAML
    - Rebuild JSON from natural language description
    - Fix invalid JSON
    """
    
    def __init__(self, openai_client: OpenAIClient):
        """
        Initialize JSON rebuilder.
        
        Args:
            openai_client: OpenAI client for LLM operations
        """
        self.openai_client = openai_client
    
    async def rebuild_from_yaml(
        self,
        yaml_content: str,
        suggestion_id: int | None = None,
        pattern_id: int | None = None
    ) -> dict[str, Any]:
        """
        Rebuild HomeIQ JSON from YAML using LLM.
        
        Args:
            yaml_content: Home Assistant automation YAML
            suggestion_id: Optional suggestion ID for metadata
            pattern_id: Optional pattern ID for metadata
        
        Returns:
            HomeIQ JSON Automation dictionary
        
        Raises:
            ValueError: If rebuild fails
        """
        prompt = f"""Convert this Home Assistant automation YAML to HomeIQ JSON Automation format.

YAML:
```yaml
{yaml_content}
```

Requirements:
- Generate comprehensive HomeIQ JSON Automation format
- Include all HomeIQ metadata fields (created_by, use_case, complexity, etc.)
- Extract device context (entity_ids, device_ids, device_types, area_ids)
- Extract pattern context if applicable
- Include safety checks if automation uses critical devices
- Calculate energy impact if automation involves power-consuming devices
- Set suggestion_id to {suggestion_id} if provided
- Set pattern_id to {pattern_id} if provided
- Use version "1.0.0" for JSON schema version

Return ONLY valid JSON matching the HomeIQ Automation schema, no explanations or markdown code blocks.
"""
        
        try:
            automation_json = await self.openai_client.generate_homeiq_automation_json(
                prompt=prompt,
                homeiq_context=None,
                temperature=0.1,
                max_tokens=3000
            )
            
            # Validate the rebuilt JSON
            try:
                HomeIQAutomation(**automation_json)
            except Exception as e:
                logger.warning(f"Rebuilt JSON validation warning: {e}")
                # Continue anyway - LLM may have generated valid structure
            
            logger.info(f"Rebuilt HomeIQ JSON from YAML: {automation_json.get('alias', 'unknown')}")
            return automation_json
        
        except Exception as e:
            logger.error(f"Failed to rebuild JSON from YAML: {e}")
            raise ValueError(f"JSON rebuild failed: {e}")
    
    async def rebuild_from_description(
        self,
        description: str,
        title: str | None = None,
        suggestion_id: int | None = None,
        pattern_id: int | None = None,
        homeiq_context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Rebuild HomeIQ JSON from natural language description using LLM.
        
        Args:
            description: Natural language description of automation
            title: Optional title for automation
            suggestion_id: Optional suggestion ID for metadata
            pattern_id: Optional pattern ID for metadata
            homeiq_context: Optional HomeIQ context (patterns, devices, areas)
        
        Returns:
            HomeIQ JSON Automation dictionary
        
        Raises:
            ValueError: If rebuild fails
        """
        prompt = f"""Create a HomeIQ JSON Automation from this description:

Title: {title or "Automation"}
Description: {description}

Requirements:
- Generate comprehensive HomeIQ JSON Automation format
- Include all HomeIQ metadata fields
- Extract or infer device context from description
- Set suggestion_id to {suggestion_id} if provided
- Set pattern_id to {pattern_id} if provided
- Use version "1.0.0" for JSON schema version
- Infer use_case (energy, comfort, security, convenience) from description
- Infer complexity (low, medium, high) from automation structure
- Include safety checks if description mentions critical devices (locks, security)
- Calculate energy impact if description mentions power-consuming devices

Return ONLY valid JSON matching the HomeIQ Automation schema, no explanations or markdown code blocks.
"""
        
        try:
            automation_json = await self.openai_client.generate_homeiq_automation_json(
                prompt=prompt,
                homeiq_context=homeiq_context,
                temperature=0.1,
                max_tokens=3000
            )
            
            # Validate the rebuilt JSON
            try:
                HomeIQAutomation(**automation_json)
            except Exception as e:
                logger.warning(f"Rebuilt JSON validation warning: {e}")
            
            logger.info(f"Rebuilt HomeIQ JSON from description: {automation_json.get('alias', 'unknown')}")
            return automation_json
        
        except Exception as e:
            logger.error(f"Failed to rebuild JSON from description: {e}")
            raise ValueError(f"JSON rebuild failed: {e}")
    
    async def fix_invalid_json(
        self,
        invalid_json: dict[str, Any],
        errors: list[str] | None = None
    ) -> dict[str, Any]:
        """
        Fix invalid HomeIQ JSON using LLM.
        
        Args:
            invalid_json: Invalid JSON dictionary
            errors: Optional list of validation errors
        
        Returns:
            Fixed HomeIQ JSON Automation dictionary
        
        Raises:
            ValueError: If fix fails
        """
        errors_text = "\n".join(errors) if errors else "Unknown validation errors"
        
        prompt = f"""Fix this invalid HomeIQ JSON Automation. It has the following errors:

Errors:
{errors_text}

Invalid JSON:
```json
{invalid_json}
```

Requirements:
- Fix all validation errors
- Maintain the original automation logic
- Ensure all required fields are present
- Return ONLY valid JSON matching the HomeIQ Automation schema, no explanations or markdown code blocks.
"""
        
        try:
            fixed_json = await self.openai_client.generate_homeiq_automation_json(
                prompt=prompt,
                homeiq_context=None,
                temperature=0.1,
                max_tokens=3000
            )
            
            # Validate the fixed JSON
            try:
                HomeIQAutomation(**fixed_json)
                logger.info(f"Fixed invalid JSON: {fixed_json.get('alias', 'unknown')}")
            except Exception as e:
                logger.error(f"Fixed JSON still has validation errors: {e}")
                raise ValueError(f"Failed to fix JSON: {e}")
            
            return fixed_json
        
        except Exception as e:
            logger.error(f"Failed to fix invalid JSON: {e}")
            raise ValueError(f"JSON fix failed: {e}")

