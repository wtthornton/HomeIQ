"""
Label-Based Filtering Utilities for Suggestions

Filters and groups suggestions based on entity and device labels,
enabling better organization and targeted automation suggestions.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def filter_entities_by_labels(
    entities: list[dict[str, Any]],
    required_labels: list[str] | None = None,
    excluded_labels: list[str] | None = None
) -> list[dict[str, Any]]:
    """
    Filter entities based on labels.
    
    Args:
        entities: List of entity dictionaries with labels
        required_labels: Labels that entities must have (OR logic - any match)
        excluded_labels: Labels that entities must NOT have
        
    Returns:
        Filtered list of entities
    """
    if not required_labels and not excluded_labels:
        return entities
    
    filtered = []
    for entity in entities:
        entity_labels = entity.get("labels", []) or []
        if not isinstance(entity_labels, list):
            entity_labels = []
        
        # Convert to lowercase for case-insensitive matching
        entity_labels_lower = [label.lower() if isinstance(label, str) else str(label).lower() 
                               for label in entity_labels]
        
        # Check excluded labels first (hard filter)
        if excluded_labels:
            excluded_lower = [label.lower() for label in excluded_labels]
            if any(label in entity_labels_lower for label in excluded_lower):
                continue  # Skip this entity
        
        # Check required labels (OR logic - any match)
        if required_labels:
            required_lower = [label.lower() for label in required_labels]
            if not any(label in entity_labels_lower for label in required_lower):
                continue  # Skip this entity
        
        filtered.append(entity)
    
    logger.debug(f"Label filtering: {len(entities)} → {len(filtered)} entities")
    return filtered


def group_entities_by_labels(
    entities: list[dict[str, Any]]
) -> dict[str, list[dict[str, Any]]]:
    """
    Group entities by their labels.
    
    Args:
        entities: List of entity dictionaries with labels
        
    Returns:
        Dictionary mapping label -> list of entities with that label
    """
    groups: dict[str, list[dict[str, Any]]] = {}
    
    for entity in entities:
        entity_labels = entity.get("labels", []) or []
        if not isinstance(entity_labels, list):
            entity_labels = []
        
        # Add entity to each label group
        for label in entity_labels:
            if not isinstance(label, str):
                label = str(label)
            
            label_lower = label.lower()
            if label_lower not in groups:
                groups[label_lower] = []
            groups[label_lower].append(entity)
    
    logger.debug(f"Grouped {len(entities)} entities into {len(groups)} label groups")
    return groups


def extract_labels_from_query(query: str) -> list[str]:
    """
    Extract potential label references from natural language query.
    
    Looks for common label keywords that users might mention:
    - outdoor/indoor
    - security/safety
    - entertainment/media
    - climate/comfort
    - energy/power
    
    Args:
        query: Natural language query
        
    Returns:
        List of detected label keywords
    """
    query_lower = query.lower()
    
    # Common label keywords
    label_keywords = {
        "outdoor": ["outdoor", "outside", "exterior", "garden", "patio", "deck"],
        "indoor": ["indoor", "inside", "interior"],
        "security": ["security", "secure", "alarm", "lock", "camera", "monitor"],
        "safety": ["safety", "safe", "emergency"],
        "entertainment": ["entertainment", "media", "tv", "music", "movie"],
        "climate": ["climate", "temperature", "heating", "cooling", "hvac"],
        "comfort": ["comfort", "cozy", "comfortable"],
        "energy": ["energy", "power", "efficient", "saving"],
        "lighting": ["light", "lights", "lighting", "lamp", "bulb"],
        "presence": ["motion", "presence", "occupancy", "person"],
    }
    
    detected_labels = []
    for label, keywords in label_keywords.items():
        if any(keyword in query_lower for keyword in keywords):
            detected_labels.append(label)
    
    return detected_labels


def enhance_suggestions_with_labels(
    suggestions: list[dict[str, Any]],
    entities: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """
    Enhance suggestions with label information from entities.
    
    Adds label context to suggestions to help with filtering and grouping.
    
    Args:
        suggestions: List of suggestion dictionaries
        entities: List of entity dictionaries with labels
        
    Returns:
        Enhanced suggestions with label information
    """
    # Build entity_id -> labels mapping
    entity_labels_map = {}
    for entity in entities:
        entity_id = entity.get("entity_id")
        labels = entity.get("labels", []) or []
        if entity_id and labels:
            entity_labels_map[entity_id] = labels
    
    # Enhance each suggestion
    enhanced = []
    for suggestion in suggestions:
        suggestion_copy = suggestion.copy()
        
        # Extract entity IDs from suggestion
        validated_entities = suggestion.get("validated_entities", {})
        if isinstance(validated_entities, dict):
            entity_ids = list(validated_entities.values())
        else:
            entity_ids = []
        
        # Collect all labels from entities in this suggestion
        suggestion_labels = set()
        for entity_id in entity_ids:
            if entity_id in entity_labels_map:
                labels = entity_labels_map[entity_id]
                if isinstance(labels, list):
                    suggestion_labels.update(labels)
        
        # Add labels to suggestion
        if suggestion_labels:
            suggestion_copy["detected_labels"] = sorted(list(suggestion_labels))
        
        enhanced.append(suggestion_copy)
    
    return enhanced

