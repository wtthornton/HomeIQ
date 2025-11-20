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
    
    Args:
        query: Natural language query string
        
    Returns:
        List of extracted entities with basic information
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
