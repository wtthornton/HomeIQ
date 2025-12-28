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
from ..clients.yaml_validation_client import YAMLValidationClient
from ..database.models import Suggestion
from ..services.plan_parser import PlanParser
from shared.homeiq_automation.converter import HomeIQToAutomationSpecConverter
from shared.homeiq_automation.schema import HomeIQAutomation
from shared.homeiq_automation.validator import HomeIQAutomationValidator
from shared.yaml_validation_service.renderer import AutomationRenderer

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
        data_api_client: DataAPIClient,
        yaml_validation_client: YAMLValidationClient | None = None
    ):
        """
        Initialize YAML generation service.
        
        Args:
            openai_client: Client for generating YAML via OpenAI
            data_api_client: Client for validating entities
            yaml_validation_client: Client for comprehensive YAML validation (Epic 51, optional)
        """
        self.openai_client = openai_client
        self.data_api_client = data_api_client
        self.yaml_validation_client = yaml_validation_client
        self.plan_parser = PlanParser()
        self.renderer = AutomationRenderer()
        self.json_validator = HomeIQAutomationValidator(data_api_client=data_api_client)
        self.json_converter = HomeIQToAutomationSpecConverter()

    async def generate_homeiq_json(
        self,
        suggestion: dict[str, Any] | Suggestion,
        homeiq_context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Generate HomeIQ JSON Automation format from a suggestion.
        
        This is the new primary method that generates comprehensive HomeIQ JSON
        including metadata, device context, patterns, and safety checks.
        
        Args:
            suggestion: Suggestion dictionary or Suggestion model instance
            homeiq_context: Optional HomeIQ context (patterns, devices, areas)
        
        Returns:
            HomeIQ JSON Automation dictionary
        
        Raises:
            InvalidSuggestionError: If suggestion is invalid
            YAMLGenerationError: If JSON generation fails
        """
        try:
            # Extract suggestion data
            if isinstance(suggestion, Suggestion):
                description = suggestion.description or ""
                title = suggestion.title or "Automation"
                pattern_id = suggestion.pattern_id
            else:
                description = suggestion.get("description", "")
                title = suggestion.get("title", "Automation")
                pattern_id = suggestion.get("pattern_id")
            
            if not description:
                raise InvalidSuggestionError("Suggestion description is required")
            
            # Build prompt
            prompt = f"""Create a HomeIQ automation with the following requirements:

Title: {title}
Description: {description}
"""
            
            # Generate HomeIQ JSON using OpenAI
            automation_json = await self.openai_client.generate_homeiq_automation_json(
                prompt=prompt,
                homeiq_context=homeiq_context,
                temperature=0.1,
                max_tokens=3000
            )
            
            # Validate JSON
            validation_result = await self.json_validator.validate(
                automation_json,
                validate_entities=True,
                validate_devices=True,
                validate_safety=True
            )
            
            if not validation_result.valid:
                errors = "; ".join(validation_result.errors)
                logger.warning(f"HomeIQ JSON validation found issues: {errors}")
                # Continue anyway - warnings are logged but don't block generation
            
            logger.info(f"Generated HomeIQ JSON automation: {automation_json.get('alias', 'unknown')}")
            return automation_json
            
        except InvalidSuggestionError:
            raise
        except Exception as e:
            logger.error(f"Failed to generate HomeIQ JSON: {e}")
            raise YAMLGenerationError(f"HomeIQ JSON generation failed: {e}")

    async def generate_automation_yaml(
        self,
        suggestion: dict[str, Any] | Suggestion,
        use_homeiq_json: bool = True,
        use_structured_plan: bool = True
    ) -> str:
        """
        Generate Home Assistant automation YAML from a suggestion.
        
        New flow (use_homeiq_json=True, default):
        - LLM generates HomeIQ JSON Automation
        - JSON is validated
        - JSON is converted to AutomationSpec
        - AutomationSpec is rendered to YAML
        
        Legacy flow (use_homeiq_json=False):
        - Epic 51, Story 51.8: Uses structured plan generation
        - LLM generates structured JSON plan
        - Plan is parsed into AutomationSpec
        - AutomationSpec is rendered to YAML
        
        Args:
            suggestion: Suggestion dictionary or Suggestion model instance
            use_homeiq_json: Whether to use HomeIQ JSON format (default: True)
            use_structured_plan: Whether to use structured plan generation (legacy, default: True)
        
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
            
            if use_homeiq_json:
                # New flow: HomeIQ JSON → AutomationSpec → YAML
                return await self._generate_yaml_from_homeiq_json(suggestion)
            elif use_structured_plan:
                # Legacy: Epic 51, Story 51.8: Structured Plan Generation
                return await self._generate_yaml_from_structured_plan(title, description)
            else:
                # Legacy: Direct YAML generation (backward compatibility)
                return await self._generate_yaml_direct(title, description)
            
        except InvalidSuggestionError:
            raise
        except YAMLGenerationError:
            raise
        except Exception as e:
            logger.error(f"Failed to generate YAML: {e}")
            raise YAMLGenerationError(f"YAML generation failed: {e}")

    async def _generate_yaml_from_homeiq_json(
        self,
        suggestion: dict[str, Any] | Suggestion
    ) -> str:
        """
        Generate YAML from HomeIQ JSON Automation.
        
        Flow:
        1. Generate HomeIQ JSON from suggestion
        2. Validate JSON
        3. Convert JSON to AutomationSpec
        4. Render AutomationSpec to YAML
        5. Validate and return YAML
        """
        try:
            # Build HomeIQ context if available
            homeiq_context: dict[str, Any] | None = None
            if isinstance(suggestion, Suggestion) and suggestion.pattern_id:
                # Could fetch pattern data here if needed
                homeiq_context = {}
            elif isinstance(suggestion, dict):
                # Extract context from suggestion dict if available
                homeiq_context = suggestion.get("homeiq_context")
            
            # Step 1: Generate HomeIQ JSON
            automation_json = await self.generate_homeiq_json(
                suggestion=suggestion,
                homeiq_context=homeiq_context
            )
            
            # Step 2: Convert JSON to HomeIQAutomation model
            homeiq_automation = HomeIQAutomation(**automation_json)
            
            # Step 3: Convert HomeIQ JSON to AutomationSpec
            automation_spec = self.json_converter.convert(homeiq_automation)
            
            # Step 4: Render AutomationSpec to YAML
            yaml_content = self.renderer.render(automation_spec)
            
            # Step 5: Validate YAML (optional, but recommended)
            if self.yaml_validation_client:
                try:
                    validation_result = await self.yaml_validation_client.validate_yaml(
                        yaml_content=yaml_content,
                        normalize=True,
                        validate_entities=True
                    )
                    if not validation_result.get("valid", False):
                        errors = validation_result.get("errors", [])
                        logger.warning(f"YAML validation found issues: {errors}")
                        # Use fixed YAML if available
                        if validation_result.get("fixed_yaml"):
                            yaml_content = validation_result["fixed_yaml"]
                            logger.info("Using normalized YAML from validation service")
                except Exception as e:
                    logger.warning(f"YAML validation failed (non-critical): {e}")
            
            logger.info(f"Generated YAML from HomeIQ JSON: {homeiq_automation.alias}")
            return yaml_content
            
        except Exception as e:
            logger.error(f"Failed to generate YAML from HomeIQ JSON: {e}")
            raise YAMLGenerationError(f"HomeIQ JSON to YAML conversion failed: {e}")

    async def _generate_yaml_from_structured_plan(self, title: str, description: str) -> str:
        """
        Generate YAML from structured plan (Epic 51, Story 51.8).
        
        Flow:
        1. LLM generates structured JSON plan
        2. Parse plan into AutomationSpec
        3. Render AutomationSpec to YAML
        4. Validate and return YAML
        """
        # Build prompt for structured plan generation
        prompt = f"""Create a Home Assistant automation with the following requirements:

Title: {title}
Description: {description}

Requirements:
- Use valid entity IDs and service names
- Include appropriate triggers and actions
- Add error handling where appropriate
- Use proper mode (single, restart, queued, or parallel)
"""
        
        try:
            # Step 1: Generate structured plan from LLM
            plan_dict = await self.openai_client.generate_structured_plan(
                prompt=prompt,
                temperature=0.1,  # Low temperature for deterministic output
                max_tokens=2000
            )
            
            logger.debug(f"Generated structured plan: {plan_dict.get('alias', 'unknown')}")
            
            # Step 2: Parse plan into AutomationSpec
            automation_spec = self.plan_parser.parse_plan(plan_dict)
            
            # Step 3: Render AutomationSpec to YAML
            yaml_content = self.renderer.render(automation_spec)
            
            # Step 4: Validate YAML (optional, but recommended)
            if self.yaml_validation_client:
                try:
                    validation_result = await self.yaml_validation_client.validate_yaml(
                        yaml_content=yaml_content,
                        normalize=True,
                        validate_entities=True
                    )
                    if not validation_result.get("valid", False):
                        errors = validation_result.get("errors", [])
                        logger.warning(f"YAML validation found issues: {errors}")
                        # Use fixed YAML if available
                        if validation_result.get("fixed_yaml"):
                            yaml_content = validation_result["fixed_yaml"]
                            logger.info("Using normalized YAML from validation service")
                except Exception as e:
                    logger.warning(f"YAML validation failed (non-critical): {e}")
            
            logger.info(f"Generated YAML from structured plan: {title}")
            return yaml_content
            
        except ValueError as e:
            logger.error(f"Failed to parse structured plan: {e}")
            raise YAMLGenerationError(f"Plan parsing failed: {e}")
        except Exception as e:
            logger.error(f"Failed to generate YAML from structured plan: {e}")
            raise YAMLGenerationError(f"Structured plan generation failed: {e}")

    async def _generate_yaml_direct(self, title: str, description: str) -> str:
        """
        Generate YAML directly (legacy method, backward compatibility).
        """
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
        
        logger.info(f"Generated YAML (legacy method) for suggestion: {title}")
        return yaml_content

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
        Validate YAML syntax and structure (Epic 51: uses YAML Validation Service if available).
        
        Args:
            yaml_content: YAML string to validate
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Use YAML Validation Service if available (Epic 51, Story 51.6)
        if self.yaml_validation_client:
            try:
                logger.debug("Using YAML Validation Service for comprehensive validation")
                result = await self.yaml_validation_client.validate_yaml(
                    yaml_content=yaml_content,
                    normalize=True,
                    validate_entities=True,
                    validate_services=False
                )
                
                if result.get("valid", False):
                    return (True, None)
                else:
                    errors = result.get("errors", [])
                    error_message = "; ".join(errors) if errors else "Validation failed"
                    return (False, error_message)
                    
            except Exception as e:
                logger.warning(f"YAML Validation Service failed, falling back to basic validation: {e}")
                # Fall through to basic validation
        
        # Fallback to basic validation
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

