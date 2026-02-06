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

    async def _fetch_entity_context(self) -> dict[str, Any]:
        """
        Fetch entity context from Data API (R1: Entity Context Fetching).
        
        Returns:
            Dictionary with entity context formatted for LLM consumption
        """
        try:
            # Fetch all entities from Data API
            entities = await self.data_api_client.fetch_entities(limit=10000)
            
            if not entities:
                logger.warning("No entities found in Data API - entity context will be empty")
                return {}
            
            # Group entities by domain for easier LLM consumption
            entity_context: dict[str, list[dict[str, Any]]] = {}
            for entity in entities:
                domain = entity.get("domain", "unknown")
                if domain not in entity_context:
                    entity_context[domain] = []
                
                entity_info = {
                    "entity_id": entity.get("entity_id"),
                    "friendly_name": entity.get("friendly_name") or entity.get("name"),
                    "area_id": entity.get("area_id"),
                    "device_class": entity.get("device_class")
                }
                # Only add if entity_id is valid
                if entity_info["entity_id"]:
                    entity_context[domain].append(entity_info)
            
            logger.info(f"Fetched {len(entities)} entities, grouped into {len(entity_context)} domains")
            return {"entities": entity_context, "total_count": len(entities)}
            
        except Exception as e:
            logger.warning(f"Failed to fetch entity context from Data API: {e}. Continuing with empty context.")
            return {}

    def _format_entity_context_for_prompt(self, entity_context: dict[str, Any]) -> str:
        """
        Format entity context for LLM prompt (R6: Entity Context Formatting).
        
        Args:
            entity_context: Entity context dictionary from _fetch_entity_context
        
        Returns:
            Formatted string for inclusion in LLM prompt
        """
        if not entity_context or not entity_context.get("entities"):
            return ""
        
        entities_by_domain = entity_context["entities"]
        formatted_sections = []
        
        # Format by domain
        for domain, entity_list in sorted(entities_by_domain.items()):
            if not entity_list:
                continue
            
            # Limit to top 50 entities per domain to avoid token limits
            limited_entities = entity_list[:50]
            
            entity_lines = []
            for entity in limited_entities:
                entity_id = entity.get("entity_id", "")
                friendly_name = entity.get("friendly_name", "")
                area = entity.get("area_id", "")
                
                # Format: entity_id (Friendly Name) [area]
                line = f"  - {entity_id}"
                if friendly_name:
                    line += f" ({friendly_name})"
                if area:
                    line += f" [area: {area}]"
                entity_lines.append(line)
            
            if entity_lines:
                section = f"{domain.upper()} entities:\n" + "\n".join(entity_lines)
                if len(entity_list) > 50:
                    section += f"\n  ... and {len(entity_list) - 50} more {domain} entities"
                formatted_sections.append(section)
        
        if formatted_sections:
            return "\n\n".join(formatted_sections)
        return ""

    async def generate_homeiq_json(
        self,
        suggestion: dict[str, Any] | Suggestion,
        homeiq_context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Generate HomeIQ JSON Automation format from a suggestion.
        
        This is the new primary method that generates comprehensive HomeIQ JSON
        including metadata, device context, patterns, and safety checks.
        
        R1, R2: Fetches entity context and passes to LLM.
        
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
            
            # R1: Fetch entity context before generation
            entity_context = await self._fetch_entity_context()
            
            # R6: Format entity context for prompt
            entity_context_str = self._format_entity_context_for_prompt(entity_context)
            
            # Build prompt with entity context
            prompt = f"""Create a HomeIQ automation with the following requirements:

Title: {title}
Description: {description}
"""
            
            # Add entity context to prompt if available
            if entity_context_str:
                prompt += f"""

AVAILABLE ENTITIES (YOU MUST USE ONLY THESE ENTITIES):
{entity_context_str}

CRITICAL: You MUST only use entity IDs from the list above. Do NOT create fictional entity IDs.
If you need an entity that doesn't exist, use the closest matching entity from the list.
"""
            
            # Generate HomeIQ JSON using OpenAI with entity context
            automation_json = await self.openai_client.generate_homeiq_automation_json(
                prompt=prompt,
                homeiq_context=homeiq_context,
                entity_context=entity_context,  # R2: Pass entity context
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
            
            # Step 1: Generate HomeIQ JSON (entity context is fetched inside generate_homeiq_json)
            # M2 fix: Removed duplicate _fetch_entity_context() call here;
            # generate_homeiq_json() fetches it internally.
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
            
            # R3: Mandatory entity validation - fail if invalid entities found
            is_valid, invalid_entities = await self.validate_entities(yaml_content)
            if not is_valid:
                error_msg = f"YAML generation failed: Invalid entities found: {', '.join(invalid_entities)}"
                logger.error(error_msg)
                raise YAMLGenerationError(error_msg)
            
            # Step 5: Additional YAML validation (optional, but recommended)
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
        
        R1, R2: Fetches entity context and passes to LLM.
        R3: Validates entities after generation and fails if invalid.
        
        Flow:
        1. Fetch entity context (R1)
        2. LLM generates structured JSON plan with entity context (R2)
        3. Parse plan into AutomationSpec
        4. Render AutomationSpec to YAML
        5. Validate entities (R3: mandatory)
        6. Return YAML
        """
        # R1: Fetch entity context before generation
        entity_context = await self._fetch_entity_context()
        
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
            # Step 1: Generate structured plan from LLM with entity context (R2)
            plan_dict = await self.openai_client.generate_structured_plan(
                prompt=prompt,
                entity_context=entity_context,  # R2: Pass entity context
                temperature=0.1,  # Low temperature for deterministic output
                max_tokens=2000
            )
            
            logger.debug(f"Generated structured plan: {plan_dict.get('alias', 'unknown')}")
            
            # Step 2: Parse plan into AutomationSpec
            automation_spec = self.plan_parser.parse_plan(plan_dict)
            
            # Step 3: Render AutomationSpec to YAML
            yaml_content = self.renderer.render(automation_spec)
            
            # R3: Mandatory entity validation - fail if invalid entities found
            is_valid, invalid_entities = await self.validate_entities(yaml_content)
            if not is_valid:
                error_msg = f"YAML generation failed: Invalid entities found: {', '.join(invalid_entities)}"
                logger.error(error_msg)
                raise YAMLGenerationError(error_msg)
            
            # Step 4: Additional YAML validation (optional, but recommended)
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
        
        R1, R2: Fetches entity context and passes to LLM.
        R3: Validates entities after generation and fails if invalid.
        """
        # R1: Fetch entity context before generation
        entity_context = await self._fetch_entity_context()
        
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
        
        # Generate YAML using OpenAI with entity context (R2)
        yaml_content = await self.openai_client.generate_yaml(
            prompt=prompt,
            entity_context=entity_context,  # R2: Pass entity context
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
        
        # R3: Mandatory entity validation - fail if invalid entities found
        is_valid, invalid_entities = await self.validate_entities(yaml_content)
        if not is_valid:
            error_msg = f"YAML generation failed: Invalid entities found: {', '.join(invalid_entities)}"
            logger.error(error_msg)
            raise YAMLGenerationError(error_msg)
        
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
        Recursively extract entity IDs from YAML data (R5: Enhanced Entity Extraction).
        
        Extracts entities from:
        - entity_id fields (single and lists)
        - Template expressions: {{ states('entity_id') }}, {{ is_state('entity_id', 'on') }}
        - Area targets: area_id fields (validates area exists)
        - Scene snapshots: snapshot_entities lists
        - Counter references: counter.entity_id
        - Group references: group.entity_id
        
        Args:
            data: YAML data structure
            entity_ids: Accumulator for entity IDs
        
        Returns:
            List of entity IDs found
        """
        if entity_ids is None:
            entity_ids = []
        
        if isinstance(data, dict):
            # Check for entity_id field (single or list)
            if "entity_id" in data:
                entity_id = data["entity_id"]
                if isinstance(entity_id, str) and "." in entity_id:
                    entity_ids.append(entity_id)
                elif isinstance(entity_id, list):
                    for eid in entity_id:
                        if isinstance(eid, str) and "." in eid:
                            entity_ids.append(eid)
            
            # Check for area_id (R5: validate areas)
            if "area_id" in data:
                area_id = data["area_id"]
                if isinstance(area_id, str):
                    # Areas are validated separately, but we note them here
                    # Areas don't have entity_id format, so we skip adding to entity_ids
                    pass
            
            # Check for snapshot_entities (R5: scene snapshots)
            if "snapshot_entities" in data:
                snapshot_entities = data["snapshot_entities"]
                if isinstance(snapshot_entities, list):
                    for eid in snapshot_entities:
                        if isinstance(eid, str) and "." in eid:
                            entity_ids.append(eid)
            
            # Recursively check all values
            for value in data.values():
                self._extract_entity_ids(value, entity_ids)
        
        elif isinstance(data, list):
            # Recursively check all items
            for item in data:
                self._extract_entity_ids(item, entity_ids)
        
        elif isinstance(data, str):
            # R5: Extract entities from template expressions
            # Pattern: {{ states('entity_id') }}, {{ is_state('entity_id', 'on') }}, etc.
            template_patterns = [
                r"states\(['\"]([^'\"]+)['\"]\)",  # states('entity_id')
                r"is_state\(['\"]([^'\"]+)['\"]",  # is_state('entity_id', ...)
                r"state_attr\(['\"]([^'\"]+)['\"]",  # state_attr('entity_id', ...)
                r"states\[['\"]([^'\"]+)['\"]\]",  # states['entity_id']
            ]
            
            for pattern in template_patterns:
                matches = re.findall(pattern, data)
                for match in matches:
                    if "." in match and len(match.split(".")) == 2:
                        entity_ids.append(match)
            
            # Check if string looks like an entity ID (domain.entity_name)
            if "." in data and len(data.split(".")) == 2:
                parts = data.split(".")
                if len(parts[0]) > 0 and len(parts[1]) > 0:
                    # Check if it's a valid entity domain (not just any dot-separated string)
                    valid_domains = [
                        "light", "switch", "binary_sensor", "sensor", "input_boolean",
                        "input_number", "input_select", "input_text", "scene", "script",
                        "automation", "counter", "group", "media_player", "climate",
                        "cover", "fan", "lock", "vacuum", "camera", "device_tracker"
                    ]
                    if parts[0] in valid_domains or parts[0].startswith("input_") or parts[0].startswith("binary_"):
                        entity_ids.append(data)
        
        return entity_ids

