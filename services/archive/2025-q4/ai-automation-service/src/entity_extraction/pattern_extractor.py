"""
Pattern-based Entity Extraction

Safe entity extraction using regex patterns without triggering Home Assistant actions.
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

def extract_entities_from_query(query: str) -> list[dict[str, Any]]:
    """
    Extract entities from query using regex patterns (PRIMARY method).
    
    This is the safe way to extract entities without triggering any actions in Home Assistant.
    Uses pattern matching to identify devices, rooms, and entity types from natural language.
    This function is a fallback/primary method for entity extraction that doesn't require
    Home Assistant API access or external services.
    
    The function uses multiple regex patterns to identify:
    - Room/area names (office, living room, bedroom, kitchen, garage, front, back)
    - Device types (lights, sensors, switches, doors, windows)
    - Common device patterns in natural language queries
    
    Algorithm/Process:
    1. Convert query to lowercase for case-insensitive matching
    2. Apply device patterns to extract room + device combinations
    3. Handle regex match groups (tuples) and single matches
    4. Filter out single-letter matches (avoid false positives)
    5. If no entities found, apply generic fallback patterns:
       - Check for common room keywords (office, garage, front)
       - Check for device type keywords (light, door)
       - Create generic entity entries with appropriate domains
    
    Args:
        query (str): Natural language query string from user (e.g., "turn on office lights")
    
    Returns:
        List[dict[str, Any]]: List of extracted entities, each containing:
            - name (str): Extracted entity name (e.g., "office", "lights", "front door")
            - domain (str): Entity domain (e.g., "light", "binary_sensor", "room", "unknown")
            - state (str): Always "unknown" (pattern matching doesn't provide state)
            - extraction_method (str): Always "pattern_matching"
        Empty list if no entities can be extracted.
    
    Examples:
        >>> # Extract room and device
        >>> extract_entities_from_query("turn on office lights")
        [{'name': 'office', 'domain': 'room', ...}, {'name': 'lights', 'domain': 'light', ...}]
        
        >>> # Extract door entity
        >>> extract_entities_from_query("check front door")
        [{'name': 'front door', 'domain': 'binary_sensor', ...}]
        
        >>> # Generic fallback
        >>> extract_entities_from_query("control lights")
        [{'name': 'lights', 'domain': 'light', ...}]
        
        >>> # No entities found
        >>> extract_entities_from_query("what's the weather")
        []
    
    Complexity: C (17) - Multiple regex patterns, nested loops, fallback logic
    Note: This is a pattern-based fallback. For more accurate extraction, use
          multi-model entity extraction (EntityExtractor) which combines NER models
          and OpenAI for complex queries. Consider refactoring to extract pattern
          definitions to a separate configuration if patterns need frequent updates.
    """
    entities = []
    query_lower = query.lower()

    # Extract common device patterns from the query - be more selective
    device_patterns = [
        r'(office|living room|bedroom|kitchen|garage|front|back)\s+(?:light|lights|sensor|sensors|switch|switches|door|doors|window|windows)',
        r'(?:turn on|turn off|flash|dim|control)\s+(office|living room|bedroom|kitchen|garage|front|back)\s+(?:light|lights)',
        r'(front|back|garage|office)\s+(?:door|doors)',
        r'(?:light|lights)\s+(?:in|of)\s+(office|living room|bedroom|kitchen|garage)'
    ]

    for pattern in device_patterns:
        matches = re.findall(pattern, query, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):
                # Handle multiple groups
                for group in match:
                    if group and len(group) > 1:  # Avoid single letters
                        entities.append({
                            'name': group,
                            'domain': 'unknown',
                            'state': 'unknown',
                            'extraction_method': 'pattern_matching'
                        })
            elif match and len(match) > 1:  # Avoid single letters
                entities.append({
                    'name': match,
                    'domain': 'unknown',
                    'state': 'unknown',
                    'extraction_method': 'pattern_matching'
                })

    # If still no entities, add some generic ones based on common terms
    if not entities:
        if 'office' in query_lower:
            entities.append({'name': 'office', 'domain': 'room', 'state': 'unknown', 'extraction_method': 'pattern_matching'})
        if 'light' in query_lower or 'lights' in query_lower:
            entities.append({'name': 'lights', 'domain': 'light', 'state': 'unknown', 'extraction_method': 'pattern_matching'})
        if 'door' in query_lower or 'doors' in query_lower:
            entities.append({'name': 'door', 'domain': 'binary_sensor', 'state': 'unknown', 'extraction_method': 'pattern_matching'})
        if 'front' in query_lower:
            entities.append({'name': 'front door', 'domain': 'binary_sensor', 'state': 'unknown', 'extraction_method': 'pattern_matching'})
        if 'garage' in query_lower:
            entities.append({'name': 'garage door', 'domain': 'binary_sensor', 'state': 'unknown', 'extraction_method': 'pattern_matching'})

    logger.info(f"Extracted {len(entities)} entities from query using pattern matching")
    return entities
