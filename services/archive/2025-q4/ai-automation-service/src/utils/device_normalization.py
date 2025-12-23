"""
Device Normalization Utilities

2025 Home Assistant API Best Practices:
- Normalizes device queries and entity names for fuzzy matching
- Handles Entity Registry priority order (name > original_name > friendly_name)
- Tokenizes compound names for better matching accuracy
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Common stop words to remove from device queries
STOP_WORDS = {
    'the', 'a', 'an', 'device', 'devices', 'light', 'lights', 'switch', 'switches',
    'sensor', 'sensors', 'of', 'in', 'on', 'at', 'to', 'for', 'with', 'by'
}

# Common words to remove from area names
AREA_STOP_WORDS = {'room', 'area', 'space', 'the'}


def normalize_device_query(query: str) -> list[str]:
    """
    Normalize and tokenize device query for matching.
    
    Handles:
    - Lowercase conversion
    - Stop word removal
    - Compound name tokenization ("Office WLED" -> ["office", "wled"])
    - Abbreviation handling (LED -> WLED substring matching)
    
    Args:
        query: Device query string (e.g., "Office WLED device")
        
    Returns:
        List of normalized tokens (e.g., ["office", "wled"])
        
    Examples:
        >>> normalize_device_query("Office WLED device")
        ['office', 'wled']
        >>> normalize_device_query("the kitchen light")
        ['kitchen']
        >>> normalize_device_query("LED")
        ['led']
    """
    if not query:
        return []
    
    # Lowercase conversion
    normalized = query.lower().strip()
    
    # Remove punctuation but keep spaces
    normalized = re.sub(r'[^\w\s]', ' ', normalized)
    
    # Tokenize by whitespace
    tokens = normalized.split()
    
    # Remove stop words
    filtered_tokens = [token for token in tokens if token not in STOP_WORDS]
    
    # Handle abbreviations (e.g., LED -> WLED substring matching)
    # Keep abbreviations as-is for substring matching later
    return filtered_tokens


def normalize_entity_name(entity: dict) -> list[str]:
    """
    Normalize entity names using 2025 Entity Registry best practices.
    
    Priority order for Entity Registry entries:
    1. name_by_user - User-customized name (highest priority, what user sees)
    2. name - Entity Registry name (source of truth, what shows in HA UI)
    3. original_name - Entity Registry original name
    4. friendly_name - States API friendly_name (fallback only)
    
    For States API entities (when Entity Registry unavailable):
    1. friendly_name - States API friendly_name
    2. entity_id - Use entity_id as last resort
    
    Phase 1 Enhancement: Also checks aliases for matching (handled separately in matching logic)
    
    Args:
        entity: Entity dictionary (from Entity Registry or States API)
        
    Returns:
        List of normalized tokens from the entity name
        
    Examples:
        >>> entity = {"name": "Office Back Left", "original_name": "Hue Color Downlight 1 7"}
        >>> normalize_entity_name(entity)
        ['office', 'back', 'left']
    """
    # Priority 1: User-customized name (Entity Registry) - highest priority
    name_by_user = entity.get('name_by_user')
    if name_by_user and isinstance(name_by_user, str):
        return normalize_device_query(name_by_user)
    
    # Priority 2: Entity Registry name (source of truth)
    name = entity.get('name')
    if name and isinstance(name, str):
        return normalize_device_query(name)
    
    # Priority 3: Entity Registry original_name
    original_name = entity.get('original_name')
    if original_name and isinstance(original_name, str):
        return normalize_device_query(original_name)
    
    # Priority 4: States API friendly_name (fallback)
    friendly_name = entity.get('friendly_name')
    if friendly_name and isinstance(friendly_name, str):
        return normalize_device_query(friendly_name)
    
    # Last resort: entity_id
    entity_id = entity.get('entity_id', '')
    if entity_id:
        # Extract entity name part (after domain prefix)
        if '.' in entity_id:
            entity_name_part = entity_id.split('.', 1)[1]
            return normalize_device_query(entity_name_part)
    
    return []


def normalize_entity_aliases(entity: dict) -> list[list[str]]:
    """
    Normalize entity aliases for matching.
    
    Phase 1 Enhancement: Extracts and normalizes all aliases from entity.
    Returns list of token lists (one per alias) for comprehensive matching.
    
    Args:
        entity: Entity dictionary (from Entity Registry)
        
    Returns:
        List of normalized token lists, one per alias
        
    Examples:
        >>> entity = {"aliases": ["desk light", "work light", "office desk"]}
        >>> normalize_entity_aliases(entity)
        [['desk'], ['work'], ['office', 'desk']]
    """
    aliases = entity.get('aliases') or []
    if not isinstance(aliases, list):
        return []
    
    normalized_aliases = []
    for alias in aliases:
        if isinstance(alias, str) and alias.strip():
            tokens = normalize_device_query(alias)
            if tokens:
                normalized_aliases.append(tokens)
    
    return normalized_aliases


def normalize_area_name(area: str) -> str:
    """
    Normalize area names for matching.
    
    Handles:
    - Lowercase conversion
    - Article removal ("the office" -> "office")
    - Variation handling ("living room" vs "livingroom" vs "living-room")
    - Common word removal ("room", "area", "space")
    
    Args:
        area: Area name string (e.g., "the office", "Living Room")
        
    Returns:
        Normalized area name (e.g., "office", "living")
        
    Examples:
        >>> normalize_area_name("the office")
        'office'
        >>> normalize_area_name("Living Room")
        'living'
        >>> normalize_area_name("living-room")
        'living'
    """
    if not area:
        return ""
    
    # Lowercase conversion
    normalized = area.lower().strip()
    
    # Remove hyphens and underscores, replace with spaces
    normalized = re.sub(r'[-_]', ' ', normalized)
    
    # Remove punctuation
    normalized = re.sub(r'[^\w\s]', ' ', normalized)
    
    # Tokenize
    tokens = normalized.split()
    
    # Remove stop words
    filtered_tokens = [token for token in tokens if token not in AREA_STOP_WORDS]
    
    # Join back (prefer first significant token, but handle multi-word areas)
    if filtered_tokens:
        # For compound areas like "living room", keep first significant word
        # This helps match "living room" to "living"
        return filtered_tokens[0] if len(filtered_tokens) == 1 else ' '.join(filtered_tokens)
    
    return normalized

