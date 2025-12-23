"""
Voice Command Hint Generator for Automation Descriptions

Generates natural language voice command hints for automations to improve
discoverability and align with Home Assistant 2025.8 AI Suggestions feature.

Story AI10.3: Voice Command Hints in Descriptions
Epic AI-10: Home Assistant 2025 YAML Target Optimization & Voice Enhancement
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def generate_voice_hints(
    yaml_data: dict[str, Any],
    entities_metadata: dict[str, dict[str, Any]] | None = None
) -> dict[str, Any]:
    """
    Add voice command hints to automation descriptions.
    
    Generates natural language voice commands based on:
    - Area names for area-based automations
    - Device names for device-based automations
    - Entity friendly names
    - Entity aliases if available
    - Automation alias/description
    
    Args:
        yaml_data: Parsed automation YAML data
        entities_metadata: Optional entity metadata with aliases and friendly names
        
    Returns:
        YAML data with enhanced description including voice hints
    """
    try:
        # Get automation context
        alias = yaml_data.get("alias", "")
        description = yaml_data.get("description", "")
        actions = yaml_data.get("action", [])
        
        if not isinstance(actions, list) or not actions:
            return yaml_data
        
        # Generate voice hints based on action targets
        voice_hints = []
        for action in actions:
            if not isinstance(action, dict):
                continue
            
            hint = _generate_voice_hint_for_action(action, entities_metadata)
            if hint:
                voice_hints.append(hint)
        
        if not voice_hints:
            # No specific hints - generate generic hint from alias
            if alias:
                generic_hint = _generate_generic_voice_hint(alias)
                if generic_hint:
                    voice_hints.append(generic_hint)
        
        # Add voice hints to description
        if voice_hints:
            enhanced_description = _add_voice_hints_to_description(
                description, voice_hints
            )
            yaml_data["description"] = enhanced_description
            logger.debug(f"Added voice hints: {', '.join(voice_hints)}")
        
        return yaml_data
    
    except Exception as e:
        logger.debug(f"Could not generate voice hints: {e}")
        return yaml_data


def _generate_voice_hint_for_action(
    action: dict[str, Any],
    entities_metadata: dict[str, dict[str, Any]] | None
) -> str | None:
    """
    Generate voice command hint for a single action.
    
    Args:
        action: Action dictionary
        entities_metadata: Entity metadata
        
    Returns:
        Voice hint string or None
    """
    service = action.get("service", "")
    target = action.get("target")
    
    if not target or not isinstance(target, dict):
        return None
    
    # Area-based targeting
    if "area_id" in target:
        area_id = target["area_id"]
        area_name = _humanize_name(area_id)
        verb = _get_service_verb(service)
        return f"'{verb} {area_name}'"
    
    # Device-based targeting
    if "device_id" in target:
        # Device names are usually UUIDs, try to get friendly name from entities
        if entities_metadata:
            # Find first entity with this device_id to get area context
            for entity_id, metadata in entities_metadata.items():
                if metadata.get("device_id") == target["device_id"]:
                    area_id = metadata.get("area_id")
                    if area_id:
                        area_name = _humanize_name(area_id)
                        verb = _get_service_verb(service)
                        return f"'{verb} {area_name}'"
                    # Use entity friendly name as fallback
                    friendly_name = metadata.get("friendly_name") or metadata.get("name_by_user")
                    if friendly_name:
                        verb = _get_service_verb(service)
                        return f"'{verb} {friendly_name}'"
                    break
        return None
    
    # Label-based targeting
    if "label_id" in target:
        label_id = target["label_id"]
        label_name = _humanize_name(label_id)
        verb = _get_service_verb(service)
        return f"'{verb} {label_name}'"
    
    # Entity-based targeting
    if "entity_id" in target:
        entity_ids = target["entity_id"]
        if not isinstance(entity_ids, list):
            entity_ids = [entity_ids]
        
        if len(entity_ids) == 1 and entities_metadata:
            # Single entity - use friendly name or alias
            entity_id = entity_ids[0]
            metadata = entities_metadata.get(entity_id)
            if metadata:
                # Prioritize name_by_user, then friendly_name, then alias
                name = (
                    metadata.get("name_by_user") or
                    metadata.get("friendly_name") or
                    metadata.get("name")
                )
                if name:
                    verb = _get_service_verb(service)
                    return f"'{verb} {name}'"
                
                # Check aliases
                aliases = metadata.get("aliases", [])
                if aliases and isinstance(aliases, list) and aliases:
                    alias = aliases[0]
                    verb = _get_service_verb(service)
                    return f"'{verb} {alias}'"
        
        # Multiple entities - try to find common area
        if entities_metadata and len(entity_ids) > 1:
            areas = set()
            for entity_id in entity_ids:
                metadata = entities_metadata.get(entity_id)
                if metadata and metadata.get("area_id"):
                    areas.add(metadata["area_id"])
            
            if len(areas) == 1:
                area_id = list(areas)[0]
                area_name = _humanize_name(area_id)
                verb = _get_service_verb(service)
                return f"'{verb} {area_name}'"
    
    return None


def _generate_generic_voice_hint(alias: str) -> str | None:
    """
    Generate generic voice hint from automation alias.
    
    Args:
        alias: Automation alias
        
    Returns:
        Generic voice hint or None
    """
    if not alias:
        return None
    
    # Clean alias for voice command
    cleaned = alias.lower().strip()
    
    # Remove common automation prefixes/suffixes
    cleaned = re.sub(r'^(automation|auto)\s*-\s*', '', cleaned)
    cleaned = re.sub(r'\s*-\s*(automation|auto)$', '', cleaned)
    
    # Generate hint based on alias pattern
    if len(cleaned) < 3:
        return None
    
    # Check for action-based aliases
    action_verbs = ['turn on', 'turn off', 'activate', 'deactivate', 'enable', 'disable', 'start', 'stop']
    for verb in action_verbs:
        if verb in cleaned:
            return f"'{cleaned}'"
    
    # Generic hint with "activate" prefix
    return f"'activate {cleaned}'"


def _get_service_verb(service: str) -> str:
    """
    Get voice-friendly verb for a service call.
    
    Args:
        service: Service name (e.g., 'light.turn_on', 'switch.toggle')
        
    Returns:
        Voice-friendly verb
    """
    if not service or '.' not in service:
        return "control"
    
    service_action = service.split('.')[-1]
    
    # Map service actions to voice-friendly verbs
    verb_map = {
        'turn_on': 'turn on',
        'turn_off': 'turn off',
        'toggle': 'toggle',
        'open': 'open',
        'close': 'close',
        'lock': 'lock',
        'unlock': 'unlock',
        'start': 'start',
        'stop': 'stop',
        'play': 'play',
        'pause': 'pause',
        'set_value': 'set',
        'set_temperature': 'set',
        'set_hvac_mode': 'set',
    }
    
    return verb_map.get(service_action, service_action.replace('_', ' '))


def _humanize_name(identifier: str) -> str:
    """
    Convert identifier to human-readable name.
    
    Args:
        identifier: ID or name (e.g., 'living_room', 'outdoor', 'holiday-lights')
        
    Returns:
        Human-readable name
    """
    if not identifier:
        return ""
    
    # Replace underscores and hyphens with spaces
    humanized = identifier.replace('_', ' ').replace('-', ' ')
    
    # Title case
    humanized = humanized.title()
    
    return humanized


def _add_voice_hints_to_description(
    description: str,
    voice_hints: list[str]
) -> str:
    """
    Add voice hints to automation description.
    
    Args:
        description: Original description
        voice_hints: List of voice command hints
        
    Returns:
        Enhanced description with voice hints
    """
    if not voice_hints:
        return description
    
    # Build voice hint suffix
    if len(voice_hints) == 1:
        hint_suffix = f" (voice: {voice_hints[0]})"
    elif len(voice_hints) == 2:
        hint_suffix = f" (voice: {voice_hints[0]} or {voice_hints[1]})"
    else:
        # Multiple hints - show first two with "or more"
        hint_suffix = f" (voice: {voice_hints[0]}, {voice_hints[1]}, or more)"
    
    # Check if voice hints already exist
    if "(voice:" in description.lower():
        logger.debug("Voice hints already exist in description, skipping")
        return description
    
    # Add hint to description
    if description:
        # Remove trailing period if exists
        description = description.rstrip('.')
        enhanced = description + hint_suffix
    else:
        # No description - create minimal one with hint
        enhanced = f"Voice-controlled automation{hint_suffix}"
    
    return enhanced


def get_entity_aliases(
    entity_id: str,
    entities_metadata: dict[str, dict[str, Any]] | None
) -> list[str]:
    """
    Get aliases for an entity.
    
    Args:
        entity_id: Entity ID
        entities_metadata: Entity metadata
        
    Returns:
        List of aliases
    """
    if not entities_metadata or entity_id not in entities_metadata:
        return []
    
    metadata = entities_metadata[entity_id]
    aliases = metadata.get("aliases", [])
    
    if not isinstance(aliases, list):
        return []
    
    return aliases


def suggest_entity_aliases(
    entity_id: str,
    friendly_name: str | None = None
) -> list[str]:
    """
    Suggest potential aliases for an entity based on its ID and friendly name.
    
    Args:
        entity_id: Entity ID
        friendly_name: Optional friendly name
        
    Returns:
        List of suggested aliases
    """
    suggestions = []
    
    # Extract entity name from ID
    if '.' in entity_id:
        domain, name = entity_id.split('.', 1)
        
        # Humanize the name
        humanized = _humanize_name(name)
        if humanized:
            suggestions.append(humanized)
        
        # Add domain-specific aliases
        if domain == 'light':
            if 'bedroom' in name:
                suggestions.append('bedroom light')
            if 'living' in name or 'lounge' in name:
                suggestions.append('living room light')
        elif domain == 'switch':
            suggestions.append(f"{humanized} switch")
    
    # Use friendly name if provided
    if friendly_name:
        # Remove common prefixes/suffixes
        cleaned = re.sub(r'\s+(light|switch|sensor|binary_sensor)$', '', friendly_name.lower())
        if cleaned != friendly_name.lower():
            suggestions.append(cleaned)
    
    # Deduplicate while preserving order
    seen = set()
    unique_suggestions = []
    for suggestion in suggestions:
        if suggestion.lower() not in seen:
            seen.add(suggestion.lower())
            unique_suggestions.append(suggestion)
    
    return unique_suggestions

