#!/usr/bin/env python3
"""
Test script for Ask AI area filtering fix

Tests the area extraction and filtering functionality added to nl_automation_generator.py
"""

import re
from typing import Optional

def extract_area_from_request(request_text: str) -> Optional[str]:
    """
    Extract area/location from the user request (copied from nl_automation_generator.py)
    """
    if not request_text:
        return None
    
    text_lower = request_text.lower()
    
    # Common area/room names
    common_areas = [
        'office', 'kitchen', 'bedroom', 'living room', 'living_room', 
        'bathroom', 'garage', 'basement', 'attic', 'hallway',
        'dining room', 'dining_room', 'master bedroom', 'master_bedroom',
        'guest room', 'guest_room', 'laundry room', 'laundry_room',
        'den', 'study', 'library', 'gym', 'playroom', 'nursery',
        'porch', 'patio', 'deck', 'yard', 'garden', 'driveway',
        'foyer', 'entryway', 'closet', 'pantry'
    ]
    
    # Pattern 1: "in the X" or "in X"
    in_pattern = r'(?:in\s+(?:the\s+)?)([\w\s]+?)(?:\s+|,|$)'
    matches = re.finditer(in_pattern, text_lower)
    for match in matches:
        potential_area = match.group(1).strip()
        # Check if it matches a common area
        for area in common_areas:
            if potential_area == area or potential_area.replace(' ', '_') == area:
                return area.replace(' ', '_')  # Normalize to snake_case
    
    # Pattern 2: "at the X" or "at X"
    at_pattern = r'(?:at\s+(?:the\s+)?)([\w\s]+?)(?:\s+|,|$)'
    matches = re.finditer(at_pattern, text_lower)
    for match in matches:
        potential_area = match.group(1).strip()
        for area in common_areas:
            if potential_area == area or potential_area.replace(' ', '_') == area:
                return area.replace(' ', '_')
    
    # Pattern 3: Area name at start of sentence
    for area in common_areas:
        if text_lower.startswith(area + ' ') or text_lower.startswith('the ' + area + ' '):
            return area.replace(' ', '_')
    
    return None


def test_area_extraction():
    """Test the area extraction from various user prompts"""
    
    # Test cases
    test_cases = [
        # Original issue
        ("In the office, flash all the Hue lights for 45 secs", "office"),
        
        # Various patterns
        ("Turn on kitchen lights at 7 AM", "kitchen"),
        ("Flash lights in the living room", "living_room"),
        ("Turn off bedroom lights at night", "bedroom"),
        ("In the garage, turn on the light", "garage"),
        ("At the front door, turn on the camera", None),  # "door" not in common areas
        
        # Pattern variations
        ("in office flash lights", "office"),
        ("in the office flash lights", "office"),
        ("at the kitchen turn on lights", "kitchen"),
        ("at kitchen turn on lights", "kitchen"),
        
        # Area at start
        ("office lights on", "office"),
        ("kitchen switch turn on", "kitchen"),
        
        # No area specified
        ("Turn on all lights", None),
        ("Flash the lights", None),
        
        # Multi-word areas
        ("In the living room, turn on lights", "living_room"),
        ("In the master bedroom, turn off lights", "master_bedroom"),
        ("Turn on dining room lights", "dining_room"),
    ]
    
    print("Testing area extraction:")
    print("=" * 70)
    
    passed = 0
    failed = 0
    
    for prompt, expected_area in test_cases:
        extracted_area = extract_area_from_request(prompt)
        status = "✅" if extracted_area == expected_area else "❌"
        
        if extracted_area == expected_area:
            passed += 1
        else:
            failed += 1
        
        print(f"{status} Prompt: {prompt[:50]:<50}")
        print(f"   Expected: {expected_area}")
        print(f"   Extracted: {extracted_area}")
        print()
    
    print("=" * 70)
    print(f"Results: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    
    return failed == 0


def test_integration_scenario():
    """Test the original user scenario"""
    
    original_prompt = """In the office, flash all the Hue lights for 45 secs using the Hue Flash action. 
Do this at the top of every hour. Kick up the brightness to 100% when flashing. 
When 45 secs is over, return all lights back to their original state."""
    
    print("\nTesting original user scenario:")
    print("=" * 70)
    print(f"Prompt: {original_prompt}")
    print()
    
    extracted_area = extract_area_from_request(original_prompt)
    
    if extracted_area == "office":
        print("✅ Area extraction: SUCCESS")
        print(f"   Extracted area: '{extracted_area}'")
        print()
        print("Expected behavior:")
        print("  1. System will log: 📍 Detected area filter: 'office'")
        print("  2. System will fetch only office entities from data-api")
        print("  3. OpenAI prompt will include area restriction notice")
        print("  4. Generated automation will use only office devices")
        return True
    else:
        print("❌ Area extraction: FAILED")
        print(f"   Expected: 'office'")
        print(f"   Got: '{extracted_area}'")
        return False


if __name__ == "__main__":
    print("Ask AI Area Filtering Fix - Test Suite")
    print("=" * 70)
    print()
    
    # Run tests
    test1_passed = test_area_extraction()
    test2_passed = test_integration_scenario()
    
    print()
    print("=" * 70)
    print("Overall Test Results:")
    
    if test1_passed and test2_passed:
        print("✅ All tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed")
        sys.exit(1)

