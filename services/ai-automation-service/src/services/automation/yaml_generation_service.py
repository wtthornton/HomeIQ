"""
YAML Generation Service

Extracted from ask_ai_router.py for better maintainability.
Handles all YAML generation logic for Home Assistant automations.

Optimized for GPT-5.1 (2025):
- Uses reasoning_effort='medium' for balanced quality/latency
- Uses verbosity='low' for concise YAML-only output
- Optimized temperature (0.1) for deterministic YAML generation
- Supports longer outputs (5000 tokens) for complex automations

Functions:
- generate_automation_yaml() - Main YAML generation function
- pre_validate_suggestion_for_yaml() - Pre-validation helper
- build_suggestion_specific_entity_mapping() - Prompt building helper
- Helper functions: _get_temperature_for_model, _get_gpt51_parameters, _is_entity_id, extract_device_mentions_from_text

Created: Refactoring from ask_ai_router.py
Updated: 2025 - Enhanced with type hints, better error handling, GPT-5.1 optimizations
"""

import logging
import re
from typing import Any, TypedDict

import yaml as yaml_lib
from sqlalchemy.ext.asyncio import AsyncSession

from ...clients.ha_client import HomeAssistantClient
from ...config import settings
from ...llm.openai_client import OpenAIClient
from ...contracts.models import AutomationPlan
from pydantic import ValidationError as PydanticValidationError
from .yaml_validator import AutomationYAMLValidator

logger = logging.getLogger(__name__)


class SuggestionDict(TypedDict, total=False):
    """Type definition for suggestion dictionary structure."""
    description: str
    trigger_summary: str
    action_summary: str
    devices_involved: list[str]
    validated_entities: dict[str, str]
    enriched_entity_context: str
    suggestion_id: str
    test_mode: str
    debug: dict[str, Any]


class YAMLGenerationError(Exception):
    """Base exception for YAML generation errors."""
    pass


class InvalidSuggestionError(YAMLGenerationError):
    """Raised when suggestion data is invalid or missing required fields."""
    pass


class EntityValidationError(YAMLGenerationError):
    """Raised when entity validation fails."""
    pass


def _get_temperature_for_model(model: str, desired_temperature: float = 0.1) -> float:
    """
    Get the appropriate temperature value for a given model.
    
    GPT-5.1: Lower temperature (0.1) recommended for deterministic YAML generation.
    GPT-4o: Supports full temperature range.
    
    Args:
        model: The model name (e.g., 'gpt-5.1', 'gpt-4o-mini', 'gpt-4o')
        desired_temperature: The desired temperature value (default: 0.1 for precise YAML)
    
    Returns:
        The temperature value to use
    
    Raises:
        ValueError: If model or temperature value is invalid
    """
    if not model or not isinstance(model, str):
        raise ValueError("Model name must be a non-empty string")
    if not 0.0 <= desired_temperature <= 2.0:
        raise ValueError(f"Temperature must be between 0.0 and 2.0, got {desired_temperature}")
    
    # GPT-5.1: Optimized for low temperature (0.1) for deterministic YAML generation
    # GPT-5.1 has better reasoning capabilities, so lower temperature works better
    if model.startswith('gpt-5'):
        logger.debug(f"Using temperature={desired_temperature} for {model} (GPT-5.1 optimized for precise YAML)")
        return desired_temperature
    
    # Legacy models with fixed temperature requirements
    models_with_fixed_temperature: list[str] = []
    if model in models_with_fixed_temperature:
        logger.debug(f"Using temperature=1.0 for {model} (model only supports default temperature)")
        return 1.0
    
    return desired_temperature


def _get_gpt51_parameters(model: str) -> dict[str, Any]:
    """
    Get GPT-5.1 specific parameters for optimal YAML generation.
    
    GPT-5.1 features:
    - reasoning_effort: Control thinking time ('low', 'medium', 'high', 'none')
    - verbosity: Control response length ('low', 'medium', 'high')
    
    Args:
        model: The model name (e.g., 'gpt-5.1')
    
    Returns:
        Dictionary of GPT-5.1 specific parameters
    """
    if not model or not model.startswith('gpt-5'):
        return {}
    
    # GPT-5.1 optimizations for YAML generation:
    # - reasoning_effort='medium': Balance between quality and latency for YAML
    # - verbosity='low': Keep responses concise (just YAML, no explanations)
    return {
        'reasoning_effort': 'medium',  # Medium reasoning for accurate YAML structure
        'verbosity': 'low'  # Low verbosity - just return YAML, no explanations
    }


def _is_entity_id(mention: str) -> bool:
    """
    Check if a string is an entity ID format (domain.entity_name).
    
    Entity IDs follow the pattern: domain.entity_name
    Examples: light.kitchen, binary_sensor.front_door, sensor.temperature
    
    Args:
        mention: String to check
        
    Returns:
        True if the string looks like an entity ID, False otherwise
    """
    if not mention or not isinstance(mention, str):
        return False
    # Entity IDs follow pattern: domain.entity_name
    # Must contain a dot and have at least domain and entity parts
    parts = mention.split('.')
    return len(parts) == 2 and len(parts[0]) > 0 and len(parts[1]) > 0


def _clean_yaml_content(yaml_content: str) -> str:
    """
    Clean YAML content by removing markdown code blocks and document separators.
    
    Args:
        yaml_content: Raw YAML string from LLM
        
    Returns:
        Cleaned YAML string
    """
    # Remove markdown code blocks if present
    yaml_content = yaml_content.strip()
    if yaml_content.startswith('```yaml'):
        yaml_content = yaml_content[7:]  # Remove ```yaml
    elif yaml_content.startswith('```'):
        yaml_content = yaml_content[3:]  # Remove ```

    if yaml_content.endswith('```'):
        yaml_content = yaml_content[:-3]  # Remove closing ```

    yaml_content = yaml_content.strip()
    
    # Remove YAML document separators (---) - we only want a single document
    if '---' in yaml_content:
        # Split by --- and take the first non-empty document
        parts = yaml_content.split('---')
        yaml_content = parts[0].strip()
        if not yaml_content and len(parts) > 1:
            yaml_content = parts[1].strip()
        logger.info(f"🧹 Removed YAML document separators (---), using first document ({len(yaml_content)} chars)")

    return yaml_content


def _validate_with_pydantic_schema(yaml_content: str) -> tuple[bool, str | None]:
    """
    Validate YAML against Pydantic AutomationPlan schema.
    
    Args:
        yaml_content: YAML string to validate
        
    Returns:
        Tuple of (is_valid, error_message) where error_message is None if valid
    """
    try:
        data = yaml_lib.safe_load(yaml_content)
        
        if not isinstance(data, dict):
            return (False, "YAML must be a dictionary")
        
        # Convert HA singular format (trigger:, action:) to Pydantic plural format (triggers:, actions:)
        # Only convert if present to avoid KeyError
        if 'trigger' in data:
            data['triggers'] = data.pop('trigger')
        if 'action' in data:
            data['actions'] = data.pop('action')
        
        # Convert 'alias' to 'name' for Pydantic model
        if 'alias' in data:
            data['name'] = data.pop('alias')
        
        # Validate against Pydantic schema
        automation_plan = AutomationPlan.model_validate(data)
        
        logger.debug("[OK] Pydantic schema validation passed")
        return (True, None)
        
    except yaml_lib.YAMLError as e:
        # YAML parsing error - should not happen as syntax validation already passed
        logger.warning(f"[WARNING] YAML parsing error in schema validation (unexpected): {e}")
        return (False, f"YAML parsing error: {e}")
    except PydanticValidationError as e:
        error_messages = [f"{'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}" for err in e.errors()]
        error_msg = "; ".join(error_messages[:3])  # First 3 errors
        logger.debug(f"[WARNING] Pydantic schema validation issues: {error_msg}")
        return (False, error_msg)
    except Exception as e:
        logger.debug(f"[WARNING] Pydantic schema validation error (non-fatal): {e}")
        return (False, str(e))


def extract_device_mentions_from_text(
    text: str,
    validated_entities: dict[str, str],
    enriched_data: dict[str, dict[str, Any]] | None = None
) -> dict[str, str]:
    """
    Extract device mentions from text and map them to entity IDs.
    
    Filters out entity IDs from being used as mention keys to prevent
    entity IDs from appearing as friendly names in the UI.
    
    Args:
        text: Text to scan (description, trigger_summary, action_summary)
        validated_entities: Dictionary mapping friendly_name → entity_id
        enriched_data: Optional enriched entity data for fuzzy matching
        
    Returns:
        Dictionary mapping mention → entity_id (no entity IDs as keys)
    """
    if not text:
        return {}

    mentions = {}
    text_lower = text.lower()

    # Extract mentions from validated_entities
    for friendly_name, entity_id in validated_entities.items():
        # Skip if friendly_name is actually an entity ID (prevents entity IDs as keys)
        if _is_entity_id(friendly_name):
            logger.debug(f"[SKIP] Skipping entity ID '{friendly_name}' from validated_entities (not a friendly name)")
            continue

        friendly_name_lower = friendly_name.lower()
        # Check if friendly name appears in text (word boundary matching)
        pattern = r'\b' + re.escape(friendly_name_lower) + r'\b'
        if re.search(pattern, text_lower):
            mentions[friendly_name] = entity_id
            logger.debug(f"[FOUND] Found mention '{friendly_name}' in text → {entity_id}")

        # Also check for partial matches (e.g., "wled" matches "WLED" or "wled strip")
        if friendly_name_lower in text_lower or text_lower in friendly_name_lower:
            if friendly_name not in mentions:
                mentions[friendly_name] = entity_id
                logger.debug(f"🔍 Found partial mention '{friendly_name}' in text → {entity_id}")

    # If enriched_data available, also check entity names and domains
    if enriched_data:
        for entity_id, enriched in enriched_data.items():
            friendly_name = enriched.get('friendly_name', '')
            if not friendly_name:
                continue
            friendly_name = friendly_name.lower()
            domain = entity_id.split('.')[0].lower() if '.' in entity_id else ''
            entity_name = entity_id.split('.')[-1].lower() if '.' in entity_id else ''

            # Check domain matches (e.g., "wled" text matches light entities with "wled" in the name)
            # Skip if domain looks like an entity ID (shouldn't happen, but defensive)
            if domain and domain in text_lower and len(domain) >= 3:
                if domain not in [m.lower() for m in mentions] and not _is_entity_id(domain):
                    mentions[domain] = entity_id
                    logger.debug(f"🔍 Found domain mention '{domain}' in text → {entity_id}")

            # Check entity name matches
            # Skip if entity_name looks like an entity ID (defensive check)
            if entity_name and entity_name in text_lower:
                if entity_name not in [m.lower() for m in mentions] and not _is_entity_id(entity_name):
                    mentions[entity_name] = entity_id
                    logger.debug(f"🔍 Found entity name mention '{entity_name}' in text → {entity_id}")

    return mentions


async def pre_validate_suggestion_for_yaml(
    suggestion: dict[str, Any],
    validated_entities: dict[str, str],
    ha_client: HomeAssistantClient | None = None
) -> dict[str, str]:
    """
    Pre-validate and enhance suggestion before YAML generation.
    
    Extracts all device mentions from description/trigger/action summaries,
    maps them to entity IDs, and queries HA for domain entities if device name is incomplete.
    
    Args:
        suggestion: Suggestion dictionary
        validated_entities: Mapping friendly_name → entity_id
        ha_client: Optional HA client for querying entities
        
    Returns:
        Enhanced validated_entities dictionary with all mentions mapped
    """
    # Import verify_entities_exist_in_ha from router (used elsewhere too, so kept there)
    from ...api.ask_ai_router import verify_entities_exist_in_ha
    
    enhanced_validated_entities = validated_entities.copy()

    # Extract device mentions from all text fields
    text_fields = {
        'description': suggestion.get('description', ''),
        'trigger_summary': suggestion.get('trigger_summary', ''),
        'action_summary': suggestion.get('action_summary', '')
    }

    all_mentions = {}
    for field, text in text_fields.items():
        mentions = extract_device_mentions_from_text(text, validated_entities, None)
        all_mentions.update(mentions)

    # Add mentions to enhanced_validated_entities, but collect for verification first
    # Filter out entity IDs from being used as keys (prevents entity IDs as friendly names)
    new_mentions = {}
    for mention, entity_id in all_mentions.items():
        # Skip if mention is an entity ID (prevents entity IDs as keys in validated_entities)
        if _is_entity_id(mention):
            logger.debug(f"[SKIP] Skipping entity ID mention '{mention}' (not a friendly name)")
            continue
        if mention not in enhanced_validated_entities:
            new_mentions[mention] = entity_id
            logger.debug(f"🔍 Found mention '{mention}' → {entity_id}")

    # Check for incomplete entity IDs (domain-only mentions like "wled", "office")
    if ha_client and new_mentions:
        incomplete_mentions = {}
        complete_mentions = {}
        for mention, entity_id in new_mentions.items():
            if '.' not in entity_id or entity_id.startswith('.') or entity_id.endswith('.'):  # Incomplete entity ID
                incomplete_mentions[mention] = entity_id
            else:
                complete_mentions[mention] = entity_id

        # Query HA for domain entities if we found incomplete mentions
        if incomplete_mentions:
            domains_to_query = set()
            for mention, entity_id in incomplete_mentions.items():
                domains_to_query.add(entity_id.lower().strip('.'))

            logger.info(f"[QUERY] Found {len(incomplete_mentions)} incomplete mentions, querying HA for domains: {list(domains_to_query)}")
            for domain in domains_to_query:
                try:
                    domain_entities = await ha_client.get_entities_by_domain(domain)
                    if domain_entities:
                        # Verify the first entity exists before using it
                        first_entity = domain_entities[0]
                        state = await ha_client.get_entity_state(first_entity)
                        if state:
                            # Use first entity from domain if it exists
                            for mention in incomplete_mentions:
                                if incomplete_mentions[mention].lower().strip('.') == domain:
                                    complete_mentions[mention] = first_entity
                                    logger.info(f"[OK] Queried HA for '{domain}', verified and using: {first_entity}")
                        else:
                            logger.warning(f"[WARNING] Entity {first_entity} from domain '{domain}' query does not exist in HA")
                except Exception as e:
                    logger.warning(f"[WARNING] Failed to query HA for domain '{domain}': {e}")

        # CRITICAL: Verify ALL complete mentions exist in HA before adding
        if complete_mentions and ha_client:
            logger.info(f"[VERIFY] Verifying {len(complete_mentions)} extracted mentions exist in HA...")
            entity_ids_to_verify = list(complete_mentions.values())
            verification_results = await verify_entities_exist_in_ha(entity_ids_to_verify, ha_client)

            # Only add verified entities
            for mention, entity_id in complete_mentions.items():
                if verification_results.get(entity_id, False):
                    enhanced_validated_entities[mention] = entity_id
                    logger.debug(f"[OK] Added verified mention '{mention}' → {entity_id} to validated entities")
                else:
                    logger.warning(f"[ERROR] Mention '{mention}' → {entity_id} does NOT exist in HA - skipped")

    return enhanced_validated_entities


async def build_suggestion_specific_entity_mapping(
    suggestion: dict[str, Any],
    validated_entities: dict[str, str]
) -> str:
    """
    Build suggestion-specific entity ID mapping text for LLM prompt.
    
    Creates explicit mapping table for devices mentioned in THIS specific suggestion.
    
    Args:
        suggestion: Suggestion dictionary
        validated_entities: Mapping friendly_name → entity_id
        
    Returns:
        Formatted text for LLM prompt
    """
    if not validated_entities:
        return ""

    # Extract devices mentioned in this suggestion
    description = suggestion.get('description', '').lower()
    trigger = suggestion.get('trigger_summary', '').lower()
    action = suggestion.get('action_summary', '').lower()
    combined_text = f"{description} {trigger} {action}"

    # Build mapping for devices mentioned in this suggestion
    mappings = []
    for friendly_name, entity_id in validated_entities.items():
        friendly_name_lower = friendly_name.lower()
        # Check if this device is mentioned in the suggestion
        if (friendly_name_lower in combined_text or
            friendly_name_lower in description or
            friendly_name_lower in trigger or
            friendly_name_lower in action):
            domain = entity_id.split('.')[0] if '.' in entity_id else ''
            mappings.append(f"  - \"{friendly_name}\" or \"{friendly_name_lower}\" → {entity_id} (domain: {domain})")

    if not mappings:
        # Fallback: include all validated entities
        for friendly_name, entity_id in validated_entities.items():
            domain = entity_id.split('.')[0] if '.' in entity_id else ''
            mappings.append(f"  - \"{friendly_name}\" → {entity_id} (domain: {domain})")

    if mappings:
        return f"""
SUGGESTION-SPECIFIC ENTITY ID MAPPINGS:
For THIS specific automation suggestion, use these exact mappings:

Description: "{suggestion.get('description', '')[:100]}..."
Trigger mentions: "{suggestion.get('trigger_summary', '')[:100]}..."
Action mentions: "{suggestion.get('action_summary', '')[:100]}..."

ENTITY ID MAPPINGS FOR THIS AUTOMATION:
{chr(10).join(mappings[:10])}

CRITICAL: When generating YAML, use the entity IDs above. For example, if you see "wled" in the description, use the full entity ID from above (NOT just "wled").
"""

    return ""


async def _validate_generated_yaml(
    yaml_content: str,
    ha_client: HomeAssistantClient | None,
    validated_entities: dict[str, str],
    suggestion: dict[str, Any] | None = None
) -> tuple[str, dict[str, Any]]:
    """
    Unified validation function for generated YAML.
    
    Runs comprehensive multi-stage validation pipeline:
    1. Syntax validation (YAML parsing)
    2. Structure validation (HA format with auto-fixes)
    3. Entity existence validation (if HA client available)
    4. Logic validation (placeholder)
    5. Safety checks (placeholder)
    6. Optional Pydantic schema validation
    
    Args:
        yaml_content: YAML string to validate
        ha_client: Optional Home Assistant client for entity validation
        validated_entities: Dictionary mapping friendly_name → entity_id
        suggestion: Optional suggestion dictionary for storing validation metadata
        
    Returns:
        Tuple of (final_yaml, validation_metadata) where:
        - final_yaml: Validated YAML (auto-fixed if available)
        - validation_metadata: Dictionary with validation results
    """
    logger.info("[VALIDATION] Starting comprehensive YAML validation...")
    
    # Initialize multi-stage validator
    validator = AutomationYAMLValidator(ha_client=ha_client)
    
    # Prepare validation context (for entity validation)
    validation_context = {
        'validated_entities': validated_entities,
        'suggestion_id': suggestion.get('suggestion_id') if suggestion else None
    }
    
    # Run comprehensive validation pipeline
    validation_result = await validator.validate(
        yaml_content=yaml_content,
        context=validation_context
    )
    
    # Check if syntax validation failed (first stage) - this is critical
    # Note: The pipeline already returns early on syntax errors, but we double-check
    if not validation_result.stages or not validation_result.stages[0].valid:
        syntax_errors = validation_result.stages[0].errors if validation_result.stages else []
        error_msg = syntax_errors[0] if syntax_errors else "Invalid YAML syntax"
        logger.error(f"[ERROR] YAML syntax validation failed: {error_msg}")
        raise YAMLGenerationError(f"Generated YAML syntax is invalid: {error_msg}")
    
    # Use fixed YAML if available
    final_yaml = validation_result.fixed_yaml if validation_result.fixed_yaml else yaml_content
    auto_fixed = bool(validation_result.fixed_yaml)
    
    if auto_fixed:
        logger.info("[OK] Using auto-fixed YAML (fixes applied from structure validation)")
    
    # Log validation results for each stage
    all_stages_passed = validation_result.all_checks_passed
    stages_metadata = []
    
    for stage in validation_result.stages:
        if stage.valid:
            logger.info(f"[OK] Validation stage '{stage.name}' passed")
        else:
            logger.warning(f"[WARNING] Validation stage '{stage.name}' found {len(stage.errors)} errors")
            if stage.errors:
                logger.warning(f"  First error: {stage.errors[0]}")
            if stage.warnings:
                logger.info(f"  Warnings: {stage.warnings[:2]}")
        
        stages_metadata.append({
            'name': stage.name,
            'valid': stage.valid,
            'error_count': len(stage.errors),
            'warning_count': len(stage.warnings),
            'errors': stage.errors[:3],  # First 3 errors for debugging
            'warnings': stage.warnings[:3]  # First 3 warnings for debugging
        })
    
    # Optional Pydantic schema validation
    schema_valid, schema_error = _validate_with_pydantic_schema(final_yaml)
    if schema_valid:
        logger.info("[OK] Pydantic schema validation passed")
    else:
        logger.warning(f"[WARNING] Pydantic schema validation issues (non-fatal): {schema_error}")
    
    # Calculate totals once
    total_errors = sum(len(stage['errors']) for stage in stages_metadata)
    total_warnings = sum(len(stage['warnings']) for stage in stages_metadata)
    
    # Build validation metadata
    validation_metadata = {
        'all_stages_passed': all_stages_passed,
        'stages': stages_metadata,
        'schema_valid': schema_valid,
        'schema_error': schema_error if not schema_valid else None,
        'auto_fixed': auto_fixed,
        'fixed_yaml_used': auto_fixed,
        'total_errors': total_errors,
        'total_warnings': total_warnings
    }
    
    if all_stages_passed:
        logger.info("[OK] All validation stages passed")
    else:
        logger.warning(
            f"[WARNING] Validation found {total_errors} errors and {total_warnings} warnings but continuing "
            f"(will be caught by HA when creating automation)"
        )
    
    return (final_yaml, validation_metadata)


async def generate_automation_yaml(
    suggestion: SuggestionDict | dict[str, Any],
    original_query: str,
    openai_client: OpenAIClient,
    entities: list[dict[str, Any]] | None = None,
    db_session: AsyncSession | None = None,
    ha_client: HomeAssistantClient | None = None
) -> str:
    """
    Generate Home Assistant automation YAML from a suggestion.
    
    Uses OpenAI to convert the natural language suggestion into valid HA YAML.
    Now includes entity validation to prevent "Entity not found" errors.
    Includes capability details for more precise YAML generation.
    
    Args:
        suggestion: Suggestion dictionary with description, trigger_summary, action_summary, devices_involved
        original_query: Original user query for context
        openai_client: OpenAI client for YAML generation
        entities: Optional list of entities with capabilities for enhanced context
        db_session: Optional database session for alias support
        ha_client: Optional Home Assistant client for validation
    
    Returns:
        YAML string for the automation
    
    Raises:
        ValueError: If required inputs are missing or invalid
        InvalidSuggestionError: If suggestion data is invalid
        EntityValidationError: If entity validation fails
        YAMLGenerationError: If YAML generation fails
    
    Example:
        >>> yaml_str = await generate_automation_yaml(
        ...     suggestion={
        ...         'description': 'Turn on lights at 7 AM',
        ...         'trigger_summary': 'Time at 07:00:00',
        ...         'action_summary': 'Turn on kitchen light',
        ...         'validated_entities': {'Kitchen Light': 'light.kitchen'}
        ...     },
        ...     original_query='Turn on kitchen lights at 7 AM',
        ...     openai_client=openai_client
        ... )
    """
    logger.info(f"[START] GENERATE_YAML CALLED - Query: {original_query[:50]}...")
    
    # Validate inputs
    if not openai_client:
        raise ValueError("OpenAI client not initialized - cannot generate YAML")
    
    if not suggestion or not isinstance(suggestion, dict):
        raise InvalidSuggestionError("Suggestion must be a non-empty dictionary")
    
    if not original_query or not isinstance(original_query, str):
        raise ValueError("Original query must be a non-empty string")

    # Get validated_entities from suggestion (already set during suggestion creation)
    validated_entities = suggestion.get('validated_entities', {})
    if not validated_entities or not isinstance(validated_entities, dict):
        devices_involved = suggestion.get('devices_involved', [])
        error_msg = (
            f"Cannot generate automation YAML: No validated entities found. "
            f"The system could not map any of {len(devices_involved)} requested devices "
            f"({', '.join(devices_involved[:5])}{'...' if len(devices_involved) > 5 else ''}) "
            f"to actual Home Assistant entities."
        )
        logger.error(f"[ERROR] {error_msg}")
        raise EntityValidationError(error_msg)

    # Use enriched_entity_context from suggestion (already computed during creation)
    entity_context_json = suggestion.get('enriched_entity_context', '')
    if entity_context_json:
        logger.info("[OK] Using cached enriched entity context from suggestion")
    else:
        logger.warning("[WARNING] No enriched_entity_context in suggestion (should be set during creation)")

    # Build validated entities text for prompt
    if validated_entities:
        # Build explicit mapping examples GENERICALLY (not hardcoded for specific terms)
        mapping_examples = []
        entity_id_list = []

        for term, entity_id in validated_entities.items():
            entity_id_list.append(f"- {term}: {entity_id}")
            # Build generic mapping instructions
            domain = entity_id.split('.')[0] if '.' in entity_id else 'unknown'
            term_variations = [term, term.lower(), term.upper(), term.title()]
            mapping_examples.append(
                f"  - If you see any variation of '{term}' (or domain '{domain}') in the description → use EXACTLY: {entity_id}"
            )

        mapping_text = ""
        if mapping_examples:
            mapping_text = f"""
EXPLICIT ENTITY ID MAPPINGS (use these EXACT mappings - ALL have been verified to exist in Home Assistant):
{chr(10).join(mapping_examples[:15])}

"""

        # Build dynamic example entity IDs for the prompt
        example_light = next((eid for eid in validated_entities.values() if eid.startswith('light.')), None)
        example_entity = list(validated_entities.values())[0] if validated_entities else '{EXAMPLE_ENTITY_ID}'

        validated_entities_text = f"""
VALIDATED ENTITIES (ALL verified to exist in Home Assistant - use these EXACT entity IDs):
{chr(10).join(entity_id_list)}
{mapping_text}

CRITICAL RULES:
1. Use ONLY the entity IDs listed above - DO NOT modify, shorten, or create new ones
2. Entity IDs are case-sensitive and format-sensitive
3. If device is "Office" and mapping shows "Office": "light.wled_office", 
   use EXACTLY "light.wled_office" - NOT "light.wled" or "light.office"
4. State Restoration with scene.create (REQUIRED for "return to previous state"):
   - Generic Home Assistant pattern - works with ANY entity type (lights, climate, covers, etc.)
   - MUST use scene.create to save state BEFORE changing it
   - MUST use scene.turn_on to restore state AFTER changes
   - Scene ID format: scene_id in scene.create (without "scene." prefix) must match scene entity ID
   - Example pattern (works for lights, climate, covers, and all entity types):
     ```yaml
     actions:
       # Step 1: Save current state (captures ALL attributes: brightness, color, effect, etc.)
       - service: scene.create
         data:
           scene_id: office_light_before_show  # NO "scene." prefix here
           snapshot_entities:
             - light.office_main  # Can be any entity: light, climate, cover, etc.
       # Step 2: Make changes
       - service: light.turn_on
         target:
           entity_id: light.office_main
         data:
           effect: random
           brightness_pct: 100
       - delay: '00:00:15'
       # Step 3: Restore previous state (restores ALL original attributes)
       - service: scene.turn_on
         target:
           entity_id: scene.office_light_before_show  # WITH "scene." prefix here
     ```
   - CRITICAL: scene_id in scene.create (e.g., "office_light_before_show") must match the scene entity ID (e.g., "scene.office_light_before_show")
   - If you reference scene.office_light_before_show, you MUST have a scene.create call with scene_id: office_light_before_show
   - Works for ANY entity: lights, climate, covers, media players, etc. - not specific to any device type

COMMON MISTAKES TO AVOID:
❌ WRONG: entity_id: wled (missing domain prefix)
❌ WRONG: entity_id: light.wled (shortened - not in validated list)
❌ WRONG: entity_id: light.office (generic - not in validated list)
✅ CORRECT: entity_id: {example_entity} (EXACT match from validated list above)

ENTITY ID EXAMPLES FROM VALIDATED LIST:
{chr(10).join([f"  - Device '{name}' → Use EXACTLY: {eid}" for name, eid in list(validated_entities.items())[:5]])}
"""

        # Add entity context JSON if available
        if entity_context_json:
            # Escape any curly braces in JSON to prevent f-string formatting errors
            escaped_json = entity_context_json.replace('{', '{{').replace('}', '}}')

            # Query database for available services for each entity
            available_services_info = []
            if db_session:
                try:
                    from ..service_validator import ServiceValidator
                    service_validator = ServiceValidator(db_session=db_session)

                    for entity_id in validated_entities.values():
                        available_services = await service_validator.get_available_services(entity_id, db_session)
                        if available_services:
                            available_services_info.append(f"  - {entity_id}: {', '.join(available_services)}")
                except Exception as e:
                    logger.debug(f"Could not fetch available services: {e}")

            available_services_text = ""
            if available_services_info:
                available_services_text = f"""

AVAILABLE SERVICES (use ONLY these services for each entity):
{chr(10).join(available_services_info)}

CRITICAL: Only use services listed above. Do NOT use services that are not available for an entity.
"""

            validated_entities_text += f"""

ENTITY CONTEXT (Complete Information):
{escaped_json}
{available_services_text}
Use this entity information to:
1. Choose the right entity type (group vs individual)
2. Understand device capabilities
3. Generate appropriate actions using ONLY available services
4. Respect device limitations (e.g., brightness range, color modes)
"""
    else:
        # This should not happen - validated_entities check above should catch this
        raise ValueError("No validated entities available - cannot generate YAML")

    # Check if test mode
    is_test = 'TEST_MODE' in suggestion.get('description', '') or suggestion.get('trigger_summary', '') == 'Manual trigger (test mode)'

    # TASK 2.4: Check if sequence test mode (shortened delays instead of stripping)
    is_sequence_test = suggestion.get('test_mode') == 'sequence'

    # Build dynamic example entity IDs for prompt examples (use validated entities, or generic placeholders)
    if validated_entities:
        example_light = next((eid for eid in validated_entities.values() if eid.startswith('light.')), None)
        example_sensor = next((eid for eid in validated_entities.values() if eid.startswith('binary_sensor.')), None)
        example_door_sensor = next((eid for eid in validated_entities.values() if 'door' in eid.lower() and eid.startswith('binary_sensor.')), example_sensor)
        example_motion_sensor = next((eid for eid in validated_entities.values() if 'motion' in eid.lower() and eid.startswith('binary_sensor.')), example_sensor)
        example_wled = next((eid for eid in validated_entities.values() if 'wled' in eid.lower()), example_light)
        example_entity_1 = example_light or example_entity
        example_entity_2 = next((eid for eid in list(validated_entities.values())[1:2] if eid.startswith('light.')), example_light) or example_entity_1
    else:
        example_light = '{LIGHT_ENTITY}'
        example_sensor = '{SENSOR_ENTITY}'
        example_door_sensor = '{DOOR_SENSOR_ENTITY}'
        example_motion_sensor = '{MOTION_SENSOR_ENTITY}'
        example_wled = '{WLED_ENTITY}'
        example_entity_1 = '{ENTITY_1}'
        example_entity_2 = '{ENTITY_2}'

    prompt = f"""
TASK: Generate Home Assistant 2025 automation YAML from this request.

USER REQUEST: "{original_query}"

AUTOMATION SPECIFICATION:
- Description: {suggestion.get('description', '')}
- Trigger: {suggestion.get('trigger_summary', '')}
- Action: {suggestion.get('action_summary', '')}
- Devices: {', '.join(suggestion.get('devices_involved', []))}

{validated_entities_text}

{"🔴 TEST MODE (SEQUENCES) - Shortened delays (10x faster) and reduced repeat counts for quick testing" if is_sequence_test else ("🔴 TEST MODE - Use event trigger (event_type: test_trigger) for immediate manual execution" if is_test else "")}

═══════════════════════════════════════════════════════════════════════════════
2025 HOME ASSISTANT YAML EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Example 1 - Simple Time-Based Automation (Specific Time):
```yaml
id: '1234567890'
alias: Morning Light
description: "Turn on light at 7 AM"
mode: single
trigger:
  - platform: time
    at: '07:00:00'
conditions: []
action:
  - service: light.turn_on
    target:
      entity_id: {example_light if example_light else 'REPLACE_WITH_VALIDATED_ENTITY'}
    data:
      brightness_pct: 100
```

Example 1b - Recurring Time-Based Automation (Every X Minutes/Hours):
```yaml
id: '1234567891'
alias: Periodic Light Effect
description: "Change light effect every 10 minutes"
mode: single
trigger:
  - platform: time_pattern
    minutes: '/10'
conditions: []
action:
  - service: light.turn_on
    target:
      entity_id: {example_light if example_light else 'REPLACE_WITH_VALIDATED_ENTITY'}
    data:
      effect: random
```

CRITICAL TIME TRIGGER RULES:
- Use "platform: time" with "at:" field ONLY for SPECIFIC times (e.g., "at 7 AM", "at 14:30:00")
  ✅ CORRECT: platform: time → at: '07:00:00'
  ❌ WRONG: platform: time → at: '/10 * * * *' (cron expressions NOT supported in 'at:' field)
  
- Use "platform: time_pattern" with "minutes:", "hours:", or "seconds:" for RECURRING intervals
  ✅ CORRECT: platform: time_pattern → minutes: '/10' (every 10 minutes)
  ✅ CORRECT: platform: time_pattern → hours: '/2' (every 2 hours)
  ✅ CORRECT: platform: time_pattern → seconds: '/30' (every 30 seconds)
  ❌ WRONG: platform: time → at: '/10 * * * *' (cron syntax not supported)

Example 2 - Advanced Automation with Sequences and Conditions:
```yaml
id: '1234567893'
alias: Smart Door Alert
description: "Color-coded notifications for different doors"
mode: single
trigger:
  - platform: state
    entity_id: {example_door_sensor if example_door_sensor else 'REPLACE_WITH_VALIDATED_SENSOR'}
    to: 'on'
    id: front_door
  - platform: state
    entity_id: {example_sensor if example_sensor else 'REPLACE_WITH_VALIDATED_SENSOR'}
    to: 'on'
    id: back_door
conditions:
  - condition: time
    after: "18:00:00"
    before: "06:00:00"
action:
  - choose:
      - conditions:
          - condition: trigger
            id: front_door
        sequence:
          - service: light.turn_on
            target:
              entity_id: {example_light if example_light else 'REPLACE_WITH_VALIDATED_ENTITY'}
            data:
              brightness_pct: 100
              color_name: red
          - delay: '00:00:02'
          - service: light.turn_off
            target:
              entity_id: {example_light if example_light else 'REPLACE_WITH_VALIDATED_ENTITY'}
      - conditions:
          - condition: trigger
            id: back_door
        sequence:
          - repeat:
              count: 3
              sequence:
                - service: light.turn_on
                  target:
                    entity_id: {example_light if example_light else 'REPLACE_WITH_VALIDATED_ENTITY'}
                  data:
                    brightness_pct: 50
                - delay: '00:00:01'
                - service: light.turn_off
                  target:
                    entity_id: {example_light if example_light else 'REPLACE_WITH_VALIDATED_ENTITY'}
```

═══════════════════════════════════════════════════════════════════════════════
HOME ASSISTANT YAML FORMAT (CURRENT STANDARD)
═══════════════════════════════════════════════════════════════════════════════

REQUIRED STRUCTURE:
```yaml
id: '<base_id>'              # Base ID (will be made unique automatically with timestamp/UUID suffix)
alias: <descriptive_name>
description: "<quoted_if_contains_colons>"
mode: single|restart|queued|parallel
trigger:                     # ✅ SINGULAR "trigger:" (Home Assistant standard)
  - platform: state|time|time_pattern|...  # ✅ "platform:" field (REQUIRED)
    <trigger_fields>
conditions: []               # Optional
action:                      # ✅ SINGULAR "action:" (Home Assistant standard)
  - service: domain.service  # ✅ "service:" field (REQUIRED)
    target:
      entity_id: <validated_entity>
    data:
      <parameters>
```

NOTE: The 'id' field will automatically be made unique (timestamp + UUID suffix appended) to ensure each approval creates a NEW automation, not an update to an existing one.

🔴 CRITICAL RULES (Automation will FAIL if violated):
1. Entity IDs: MUST use EXACT IDs from VALIDATED ENTITIES list above
   - Format: domain.entity (e.g., light.office_ceiling)
   - NEVER invent IDs (causes "Entity not found" error)
   - NEVER use incomplete IDs like "wled", "office" (missing domain)
   
2. Home Assistant Format: MUST use correct structure
   - Top-level: "trigger:" and "action:" (SINGULAR, not plural)
   - Inside trigger items: "platform:" field (REQUIRED - platform: state, platform: time, etc.)
   - Inside action items: "service:" field (REQUIRED - service: light.turn_on, etc.)
   - ❌ WRONG: "triggers:", "actions:", "trigger: state", "action: light.turn_on" (these formats don't exist)
   
3. Time Triggers: MUST use correct platform type for time-based automations
   - SPECIFIC times (e.g., "at 7 AM"): Use "platform: time" with "at: 'HH:MM:SS'"
   - RECURRING intervals (e.g., "every 10 minutes"): Use "platform: time_pattern" with "minutes: '/10'"
   - ❌ NEVER use cron expressions in "at:" field (e.g., '/10 * * * *' - NOT supported)
   - ❌ NEVER use "platform: time" for recurring intervals
   
4. Target Structure: MUST use target.entity_id
   - ✅ CORRECT: service: light.turn_on → target: → entity_id: light.example
   - ❌ WRONG: service: light.turn_on with entity_id directly in action

5. WLED Entities: Use light.turn_on (NOT wled.turn_on - doesn't exist)

6. Special Characters: Quote descriptions containing colons
   - ✅ "TEST MODE: Alert" or "TEST MODE - Alert"
   - ❌ TEST MODE: Alert (breaks YAML)

7. Jinja2 Templates: MUST be quoted in YAML strings
   - ✅ data: "{{{{ states(\\'sensor.temperature\\') }}}}"
   - ✅ data: '{{% if old_effect is not none %}}{{{{ old_effect }}}}{{% endif %}}'
   - ❌ data: {{% if old_effect is not none %}} (breaks YAML - unquoted Jinja2)
   - ❌ data: {{{{ states(\\'sensor.temperature\\') }}}} (breaks YAML - unquoted template)
   - Rule: ALL Jinja2 syntax (double braces and percent braces) MUST be inside quoted strings

ADVANCED FEATURES (Use for creative implementations):
- sequence: Multi-step actions
- choose: Conditional branching
- repeat: Loops (count, while, until)
- parallel: Simultaneous actions
- condition: Complex logic (time, state, template)
- delay: Timing between actions
- template: Dynamic values
"""

    # Build test mode adjustments (avoid backslashes in f-strings)
    test_mode_text = ""
    if is_test and not is_sequence_test:
        test_mode_text = """
TEST MODE ADJUSTMENTS:
- Use trigger: event with event_type: test_trigger
- NO delays or timing components
- NO repeat loops (execute once)
- Simplify to core action only
"""
    elif is_sequence_test:
        test_mode_text = """
TEST MODE ADJUSTMENTS:
- SHORTEN delays by 10x (5 sec → 0.5 sec)
- REDUCE repeat counts (10 → 3, 5 → 2)
- Keep structure but execute faster
"""

    prompt += test_mode_text + """
═══════════════════════════════════════════════════════════════════════════════
PRE-GENERATION VALIDATION CHECKLIST
═══════════════════════════════════════════════════════════════════════════════

Before generating YAML, verify ALL requirements:

□ Every entity_id uses EXACT ID from VALIDATED ENTITIES list (not example IDs)
□ All entity_ids are domain.entity format (e.g., light.office, binary_sensor.door)
□ Top-level uses "trigger:" (singular) and "action:" (singular) - NOT plural
□ Each trigger item uses "platform:" field (platform: state, platform: time, etc.) - NOT "trigger:"
□ Each action item uses "service:" field (service: light.turn_on, etc.) - NOT "action:"
□ Service calls use target.entity_id structure
□ Description quoted if contains colons, or uses dashes instead
□ ALL Jinja2 templates ({{ }}, {% %}) are properly quoted in YAML strings
□ If using scene entities (scene.xxx), MUST have scene.create service call BEFORE referencing the scene
□ Scene ID in scene.create (e.g., "office_light_before_show") must match scene entity ID (e.g., "scene.office_light_before_show")
□ State restoration pattern (scene.create + scene.turn_on) works for ANY entity type - not device-specific
□ Includes required fields: id, alias, mode, trigger, action
□ YAML syntax valid (2-space indentation, proper quoting)
□ WLED entities use light domain (not wled domain)

If missing entities needed for automation:
□ Use time-based trigger instead of missing sensors
□ Simplify to use only available validated entities
□ Return error explaining missing entities

═══════════════════════════════════════════════════════════════════════════════
OUTPUT INSTRUCTIONS
═══════════════════════════════════════════════════════════════════════════════

Generate ONLY the YAML content:
- NO markdown code blocks (no ```yaml or ```)
- NO explanations or comments outside YAML
- NO YAML document separators (no ---)
- SINGLE YAML document only (not multiple documents)
- USE ONLY validated entity IDs from the list above
- FOLLOW Home Assistant format: trigger:/action: (singular), platform:/service: (in items)
- START with "id:" (first line of YAML)
"""

    try:
        # Check if parallel testing enabled
        from ...database.crud import get_system_settings
        system_settings = await get_system_settings(db_session) if db_session else None
        enable_parallel = (
            system_settings is not None and
            getattr(system_settings, 'enable_parallel_model_testing', False)
        )

        if enable_parallel:
            # Parallel model testing mode
            from ..parallel_model_tester import ParallelModelTester
            tester = ParallelModelTester(openai_client.api_key)

            # Get models from settings
            parallel_models = getattr(system_settings, 'parallel_testing_models', {}) if system_settings else {}
            models = parallel_models.get('yaml', ['gpt-5.1'])

            # Get suggestion_id if available
            suggestion_id = suggestion.get('suggestion_id') if suggestion else None

            # Build prompt_dict for parallel tester
            prompt_dict = {
                "system_prompt": (
                    "You are a Home Assistant 2025 YAML automation expert. "
                    "Your output is production-ready YAML that passes Home Assistant validation. "
                    "You NEVER invent entity IDs - you ONLY use entity IDs from the validated list. "
                    "You ALWAYS use Home Assistant format: trigger: (singular) with platform: fields, action: (singular) with service: fields. "
                    "You ALWAYS quote Jinja2 templates ({{ }}, {% %}) in YAML strings - unquoted templates break YAML syntax. "
                    "Return ONLY a SINGLE YAML document starting with 'id:' - NO markdown, NO explanations, NO document separators (---)."
                ),
                "user_prompt": prompt
            }

            # Determine temperature based on model capabilities
            yaml_temperature = _get_temperature_for_model(models[0], desired_temperature=0.1)
            
            # Get GPT-5.1 specific parameters if using GPT-5.1
            gpt51_params = _get_gpt51_parameters(models[0])

            result = await tester.generate_yaml_parallel(
                suggestion=suggestion,
                prompt_dict=prompt_dict,
                models=models,
                db_session=db_session,
                suggestion_id=suggestion_id,
                temperature=yaml_temperature,
                max_tokens=5000,  # GPT-5.1 optimized: supports longer outputs for complex automations
                **gpt51_params  # Add GPT-5.1 specific parameters (reasoning_effort, verbosity)
            )

            yaml_content = result['primary_result']  # Use first model's result
            comparison_metrics = result['comparison']  # Store for metrics

            # Log parallel testing info (safely handle case where only one model is provided)
            if len(models) >= 2:
                logger.info(f"Parallel YAML testing: {models[0]} vs {models[1]} - using {models[0]} result")
            else:
                logger.info(f"Parallel YAML testing: {models[0]} - using result")

            # Store model info in suggestion for later metrics update
            if suggestion and comparison_metrics and comparison_metrics.get('model_results'):
                primary_result = comparison_metrics['model_results'][0]
                if 'debug' not in suggestion:
                    suggestion['debug'] = {}
                suggestion['debug']['yaml_model_used'] = primary_result.get('model', models[0])
                suggestion['debug']['yaml_parallel_testing'] = True

            # Extract YAML from result - handle AutomationSuggestion object or dict/string
            if hasattr(yaml_content, 'automation_yaml'):
                # It's an AutomationSuggestion Pydantic model - extract the YAML string
                yaml_content = yaml_content.automation_yaml
            elif isinstance(yaml_content, dict):
                # If result is a dict, try to extract YAML
                yaml_content = yaml_content.get('automation_yaml', yaml_content.get('yaml', yaml_content.get('content', str(yaml_content))))
            elif not isinstance(yaml_content, str):
                # Convert to string if it's something else
                yaml_content = str(yaml_content)

            # Clean YAML content (remove markdown, document separators)
            yaml_content = _clean_yaml_content(yaml_content)

            logger.info(f"📥 [YAML_RAW] OpenAI returned {len(yaml_content)} chars (parallel mode)")

            # Comprehensive multi-stage validation (same as single model path)
            validated_entities = suggestion.get('validated_entities', {}) if suggestion else {}
            final_yaml, validation_metadata = await _validate_generated_yaml(
                yaml_content=yaml_content,
                ha_client=ha_client,
                validated_entities=validated_entities,
                suggestion=suggestion
            )
            
            # Store validation metadata in suggestion debug info
            if suggestion:
                if 'debug' not in suggestion:
                    suggestion['debug'] = {}
                suggestion['debug']['validation_result'] = validation_metadata

            return final_yaml
        else:
            # Single model mode (existing behavior)
            yaml_model = getattr(settings, 'yaml_generation_model', 'gpt-5.1')

            # Create temporary client with YAML model if different from default
            if yaml_model != openai_client.model:
                yaml_client = OpenAIClient(
                    api_key=openai_client.api_key,
                    model=yaml_model,
                    enable_token_counting=getattr(settings, 'enable_token_counting', True)
                )
            else:
                yaml_client = openai_client

            # Determine temperature based on model capabilities
            yaml_temperature = _get_temperature_for_model(yaml_model, desired_temperature=0.1)
            
            # Get GPT-5.1 specific parameters if using GPT-5.1
            gpt51_params = _get_gpt51_parameters(yaml_model)

            # Store model info in suggestion for later metrics update (single model mode)
            if suggestion:
                if 'debug' not in suggestion:
                    suggestion['debug'] = {}
                suggestion['debug']['yaml_model_used'] = yaml_model
                suggestion['debug']['yaml_parallel_testing'] = False
                # Store GPT-5.1 specific settings for debugging
                if gpt51_params:
                    suggestion['debug']['gpt51_params'] = gpt51_params

            # Build API call parameters with GPT-5.1 optimizations
            api_params = {
                "model": yaml_client.model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                    "You are a Home Assistant 2025 YAML automation expert. "
                    "Your output is production-ready YAML that passes Home Assistant validation. "
                    "You NEVER invent entity IDs - you ONLY use entity IDs from the validated list. "
                    "You ALWAYS use Home Assistant format: trigger: (singular) with platform: fields, action: (singular) with service: fields. "
                    "You ALWAYS quote Jinja2 templates ({{ }}, {% %}) in YAML strings - unquoted templates break YAML syntax. "
                    "Return ONLY a SINGLE YAML document starting with 'id:' - NO markdown, NO explanations, NO document separators (---)."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": yaml_temperature,
                "max_completion_tokens": 5000  # GPT-5.1 optimized: supports longer outputs for complex automations
            }
            
            # Add GPT-5.1 specific parameters if using GPT-5.1
            if gpt51_params:
                api_params.update(gpt51_params)
                logger.debug(f"Using GPT-5.1 optimizations: {gpt51_params}")

            # Call OpenAI to generate YAML using configured model
            response = await yaml_client.client.chat.completions.create(**api_params)

            # Phase 5: Track endpoint-level stats for YAML generation
            if hasattr(response, 'usage') and response.usage:
                usage = response.usage
                endpoint = "yaml_generation"
                if not hasattr(yaml_client, 'endpoint_stats'):
                    yaml_client.endpoint_stats = {}
                if endpoint not in yaml_client.endpoint_stats:
                    yaml_client.endpoint_stats[endpoint] = {
                        'calls': 0,
                        'input_tokens': 0,
                        'output_tokens': 0,
                        'total_tokens': 0,
                        'cost_usd': 0.0
                    }
                from ...llm.cost_tracker import CostTracker
                request_cost = CostTracker.calculate_cost(
                    usage.prompt_tokens,
                    usage.completion_tokens,
                    model=yaml_client.model
                )
                yaml_client.endpoint_stats[endpoint]['calls'] += 1
                yaml_client.endpoint_stats[endpoint]['input_tokens'] += usage.prompt_tokens
                yaml_client.endpoint_stats[endpoint]['output_tokens'] += usage.completion_tokens
                yaml_client.endpoint_stats[endpoint]['total_tokens'] += usage.total_tokens
                yaml_client.endpoint_stats[endpoint]['cost_usd'] += request_cost

            yaml_content = response.choices[0].message.content.strip()

            logger.info(f"📥 [YAML_RAW] OpenAI returned {len(yaml_content)} chars")
            logger.info(f"📄 [YAML_RAW] First 300 chars: {yaml_content[:300]}")

            # Clean YAML content (remove markdown, document separators)
            yaml_content = _clean_yaml_content(yaml_content)

            logger.info(f"🧹 [YAML_CLEANED] After cleanup: {len(yaml_content)} chars")

            # Comprehensive multi-stage validation
            validated_entities = suggestion.get('validated_entities', {})
            final_yaml, validation_metadata = await _validate_generated_yaml(
                yaml_content=yaml_content,
                ha_client=ha_client,
                validated_entities=validated_entities,
                suggestion=suggestion
            )
            
            # Store validation metadata in suggestion debug info
            if suggestion:
                if 'debug' not in suggestion:
                    suggestion['debug'] = {}
                suggestion['debug']['validation_result'] = validation_metadata

            # Validate with Home Assistant API if available (2025 standards compliance)
            # Note: Entity validation is already done in the pipeline, but HA API provides additional checks
            if ha_client:
                try:
                    logger.info("[VALIDATION] Validating YAML with Home Assistant API...")
                    ha_validation = await ha_client.validate_automation(final_yaml)

                    if not ha_validation.get('valid', False):
                        error_msg = ha_validation.get('error', 'Unknown validation error')
                        warnings = ha_validation.get('warnings', [])

                        logger.warning(f"[WARNING] HA API validation issues: {error_msg}")
                        if warnings:
                            logger.warning(f"[WARNING] HA API validation warnings: {', '.join(warnings[:3])}")

                        # Don't fail here - let the create_automation endpoint handle it
                        # This gives better error messages to the user
                    else:
                        logger.info(f"[OK] HA API validation passed ({ha_validation.get('entity_count', 0)} entities validated)")
                except Exception as e:
                    logger.warning(f"[WARNING] Could not validate with HA API (non-fatal): {e}")
                    # Continue - HA API validation is best-effort, not required

            # Debug: Print the final YAML content
            logger.info("=" * 80)
            logger.info("[YAML] FINAL HA AUTOMATION YAML")
            logger.info("=" * 80)
            logger.info(final_yaml)
            logger.info("=" * 80)

            return final_yaml

    except (YAMLGenerationError, InvalidSuggestionError, EntityValidationError):
        # Re-raise our custom exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Failed to generate automation YAML: {e}", exc_info=True)
        raise YAMLGenerationError(f"Unexpected error during YAML generation: {e}") from e

