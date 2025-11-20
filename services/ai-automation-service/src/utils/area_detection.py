"""
Area Detection Utility

Shared utility for extracting area/location information from natural language text.
Used by both the clarification system and automation generation.

Example usage:
    >>> from utils.area_detection import extract_area_from_request
    >>> area = extract_area_from_request("Turn on lights in the office")
    >>> print(area)  # "office"
    >>> 
    >>> areas = extract_area_from_request("Turn on lights in the office and kitchen")
    >>> print(areas)  # "office,kitchen"
"""

import re

# Common area/room names recognized by the system
COMMON_AREAS = [
    'office', 'kitchen', 'bedroom', 'living room', 'living_room',
    'bathroom', 'garage', 'basement', 'attic', 'hallway',
    'dining room', 'dining_room', 'master bedroom', 'master_bedroom',
    'guest room', 'guest_room', 'laundry room', 'laundry_room',
    'den', 'study', 'library', 'gym', 'playroom', 'nursery',
    'porch', 'patio', 'deck', 'yard', 'garden', 'driveway',
    'foyer', 'entryway', 'closet', 'pantry'
]


def extract_area_from_request(request_text: str) -> str | None:
    """
    Extract area(s)/location(s) from natural language text.
    
    Looks for common patterns like:
    - Single area: "in the office", "at the kitchen"
    - Multiple areas: "in the office and kitchen", "bedroom and living room"
    
    Args:
        request_text: Natural language text (e.g., user prompt)
    
    Returns:
        Comma-separated area names if found (e.g., "office,kitchen"), None otherwise
        
    Examples:
        >>> extract_area_from_request("In the office, turn on lights")
        'office'
        >>> extract_area_from_request("Turn on lights in the office and kitchen")
        'office,kitchen'
        >>> extract_area_from_request("Turn on all lights")
        None
    """
    if not request_text:
        return None

    text_lower = request_text.lower()
    found_areas = []

    # Pattern 1: "in the X and Y" or "in X and Y" (multiple areas)
    multi_in_pattern = r'(?:in\s+(?:the\s+)?)([\w\s]+?)(?:\s+and\s+(?:the\s+)?)([\w\s]+?)(?:\s+|,|$)'
    matches = re.finditer(multi_in_pattern, text_lower)
    for match in matches:
        area1 = match.group(1).strip()
        area2 = match.group(2).strip()
        for potential in [area1, area2]:
            for area in COMMON_AREAS:
                if potential == area or potential.replace(' ', '_') == area:
                    normalized = area.replace(' ', '_')
                    if normalized not in found_areas:
                        found_areas.append(normalized)

    if found_areas:
        return ','.join(found_areas)

    # Pattern 2: "X and Y" (e.g., "bedroom and living room lights")
    area_and_pattern = r'([\w\s]+?)\s+and\s+(?:the\s+)?([\w\s]+?)(?:\s+|,|$)'
    matches = re.finditer(area_and_pattern, text_lower)
    for match in matches:
        area1 = match.group(1).strip()
        area2 = match.group(2).strip()
        for potential in [area1, area2]:
            for area in COMMON_AREAS:
                if potential == area or potential.replace(' ', '_') == area:
                    normalized = area.replace(' ', '_')
                    if normalized not in found_areas:
                        found_areas.append(normalized)

    if found_areas:
        return ','.join(found_areas)

    # Pattern 3: "in the X" or "in X" (single area)
    in_pattern = r'(?:in\s+(?:the\s+)?)([\w\s]+?)(?:\s+|,|$)'
    matches = re.finditer(in_pattern, text_lower)
    for match in matches:
        potential_area = match.group(1).strip()
        for area in COMMON_AREAS:
            if potential_area == area or potential_area.replace(' ', '_') == area:
                return area.replace(' ', '_')

    # Pattern 4: "at the X" or "at X" (single area)
    at_pattern = r'(?:at\s+(?:the\s+)?)([\w\s]+?)(?:\s+|,|$)'
    matches = re.finditer(at_pattern, text_lower)
    for match in matches:
        potential_area = match.group(1).strip()
        for area in COMMON_AREAS:
            if potential_area == area or potential_area.replace(' ', '_') == area:
                return area.replace(' ', '_')

    # Pattern 5: Area name at start of sentence
    for area in COMMON_AREAS:
        if text_lower.startswith(area + ' ') or text_lower.startswith('the ' + area + ' '):
            return area.replace(' ', '_')

    return None


def get_area_list(area_filter: str | None) -> list[str]:
    """
    Convert comma-separated area string to list.
    
    Args:
        area_filter: Comma-separated areas (e.g., "office,kitchen") or single area
        
    Returns:
        List of area names
        
    Examples:
        >>> get_area_list("office")
        ['office']
        >>> get_area_list("office,kitchen")
        ['office', 'kitchen']
        >>> get_area_list(None)
        []
    """
    if not area_filter:
        return []
    return [a.strip() for a in area_filter.split(',')]


def format_area_display(area_filter: str | None) -> str:
    """
    Format area filter for display to users.
    
    Args:
        area_filter: Comma-separated areas or single area
        
    Returns:
        Formatted string for display
        
    Examples:
        >>> format_area_display("office")
        'Office'
        >>> format_area_display("office,kitchen")
        'Office and Kitchen'
        >>> format_area_display("office,kitchen,bedroom")
        'Office, Kitchen and Bedroom'
    """
    if not area_filter:
        return ""

    areas = [a.replace('_', ' ').title() for a in get_area_list(area_filter)]

    if len(areas) == 1:
        return areas[0]
    elif len(areas) == 2:
        return f"{areas[0]} and {areas[1]}"
    else:
        return ', '.join(areas[:-1]) + ' and ' + areas[-1]


def is_valid_area(area_name: str) -> bool:
    """
    Check if an area name is in the list of recognized areas.
    
    Args:
        area_name: Area name to check
        
    Returns:
        True if area is recognized, False otherwise
    """
    if not area_name:
        return False

    normalized = area_name.lower().replace(' ', '_')
    return normalized in [a.replace(' ', '_') for a in COMMON_AREAS]


def add_custom_area(area_name: str) -> None:
    """
    Add a custom area to the recognized areas list.
    
    Useful for adding user-specific or house-specific areas.
    
    Args:
        area_name: Area name to add (will be normalized)
    """
    if area_name and area_name.lower() not in [a.lower() for a in COMMON_AREAS]:
        COMMON_AREAS.append(area_name.lower())

