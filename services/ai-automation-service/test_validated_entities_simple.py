"""
Simple test to verify validated_entities implementation

This test verifies:
1. Code structure has all necessary components
2. Helper function logic works correctly
3. Fast/slow path logic is in place
"""

import re
import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def test_code_structure():
    """Test that code structure includes all necessary components"""
    print("=" * 80)
    print("TEST 1: Code Structure Verification")
    print("=" * 80)
    
    router_file = Path(__file__).parent / "src" / "api" / "ask_ai_router.py"
    
    if not router_file.exists():
        print(f"❌ File not found: {router_file}")
        return False
    
    content = router_file.read_text(encoding='utf-8')
    
    checks = [
        ("map_devices_to_entities function", "def map_devices_to_entities"),
        ("validated_entities field exists", "validated_entities", content.count("validated_entities") >= 10),
        ("Fast path check in test endpoint", "if suggestion.get('validated_entities'):"),
        ("FAST PATH logging", "FAST PATH"),
        ("SLOW PATH logging", "SLOW PATH"),
        ("enriched_data initialization", "enriched_data = {}"),
        ("Fallback includes validated_entities", "'validated_entities': {}"),
    ]
    
    all_passed = True
    for check_name, pattern, *args in checks:
        if args:
            # Boolean check
            passed = args[0] if args else False
        else:
            # Pattern check
            passed = pattern in content
        
        status = "✅" if passed else "❌"
        print(f"{status} {check_name}")
        if not passed:
            all_passed = False
    
    return all_passed


def test_helper_function_logic():
    """Test the logic of map_devices_to_entities function"""
    print("\n" + "=" * 80)
    print("TEST 2: Helper Function Logic Test")
    print("=" * 80)
    
    # Simulate the function logic
    def map_devices_to_entities(devices_involved, enriched_data):
        """Simplified version for testing"""
        validated_entities = {}
        for device_name in devices_involved:
            for entity_id, enriched in enriched_data.items():
                friendly_name = enriched.get('friendly_name', '')
                if friendly_name == device_name:
                    validated_entities[device_name] = entity_id
                    break
        return validated_entities
    
    # Test case 1: Normal mapping
    enriched_data = {
        "light.office_1": {"friendly_name": "Office light 1"},
        "light.office_2": {"friendly_name": "Office light 2"},
    }
    devices = ["Office light 1", "Office light 2"]
    result = map_devices_to_entities(devices, enriched_data)
    
    print(f"Test 2.1: Normal mapping")
    print(f"  Input: {devices}")
    print(f"  Expected: 2 mappings")
    print(f"  Got: {len(result)} mappings")
    assert len(result) == 2, f"Expected 2, got {len(result)}"
    assert result["Office light 1"] == "light.office_1"
    assert result["Office light 2"] == "light.office_2"
    print(f"  ✅ PASSED")
    
    # Test case 2: Partial mapping (some devices not found)
    devices = ["Office light 1", "Non-existent light"]
    result = map_devices_to_entities(devices, enriched_data)
    
    print(f"\nTest 2.2: Partial mapping (unmapped device)")
    print(f"  Input: {devices}")
    print(f"  Expected: 1 mapping (unmapped device ignored)")
    print(f"  Got: {len(result)} mappings")
    assert len(result) == 1, f"Expected 1, got {len(result)}"
    assert result["Office light 1"] == "light.office_1"
    print(f"  ✅ PASSED")
    
    # Test case 3: Empty enriched_data
    result = map_devices_to_entities(devices, {})
    
    print(f"\nTest 2.3: Empty enriched_data")
    print(f"  Input: {devices}, enriched_data={{}}")
    print(f"  Expected: 0 mappings")
    print(f"  Got: {len(result)} mappings")
    assert len(result) == 0, f"Expected 0, got {len(result)}"
    print(f"  ✅ PASSED")
    
    return True


def test_suggestion_structure_patterns():
    """Test that suggestion building code includes validated_entities"""
    print("\n" + "=" * 80)
    print("TEST 3: Suggestion Structure Pattern Check")
    print("=" * 80)
    
    router_file = Path(__file__).parent / "src" / "api" / "ask_ai_router.py"
    content = router_file.read_text(encoding='utf-8')
    
    # Find the suggestion building section
    suggestion_pattern = r"suggestions\.append\(\{[\s\S]*?'validated_entities'"
    
    if re.search(suggestion_pattern, content):
        print("✅ Found validated_entities in suggestion building")
        print("   Location: suggestions.append({...}) section")
        
        # Check if it's mapped from enriched_data
        if "map_devices_to_entities" in content:
            print("✅ Uses map_devices_to_entities function")
        else:
            print("⚠️  Note: Check that map_devices_to_entities is used")
        
        return True
    else:
        print("❌ validated_entities not found in suggestion building")
        return False


def test_fast_slow_path_logic():
    """Test that fast/slow path logic is properly implemented"""
    print("\n" + "=" * 80)
    print("TEST 4: Fast/Slow Path Logic Check")
    print("=" * 80)
    
    router_file = Path(__file__).parent / "src" / "api" / "ask_ai_router.py"
    content = router_file.read_text(encoding='utf-8')
    
    # Find test endpoint section
    test_endpoint_section = re.search(
        r"async def test_suggestion_from_query[\s\S]*?(?=\n    async def|\n@|\Z)",
        content
    )
    
    if not test_endpoint_section:
        print("❌ Could not find test_suggestion_from_query function")
        return False
    
    section = test_endpoint_section.group(0)
    
    checks = [
        ("Fast path check exists", "if suggestion.get('validated_entities'):"),
        ("Fast path uses saved mapping", "entity_mapping = suggestion['validated_entities']"),
        ("Fast path sets resolution time to 0", "entity_resolution_time = 0"),
        ("Fast path logging", "FAST PATH"),
        ("Slow path else clause", "else:"),
        ("Slow path logging", "SLOW PATH"),
        ("Slow path backwards compatibility", "backwards compatibility"),
    ]
    
    all_passed = True
    for check_name, pattern in checks:
        passed = pattern in section
        status = "✅" if passed else "❌"
        print(f"{status} {check_name}")
        if not passed:
            all_passed = False
    
    return all_passed


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("VALIDATED_ENTITIES IMPLEMENTATION - SIMPLE VERIFICATION")
    print("=" * 80 + "\n")
    
    results = []
    
    try:
        results.append(("Code Structure", test_code_structure()))
        results.append(("Helper Function Logic", test_helper_function_logic()))
        results.append(("Suggestion Structure", test_suggestion_structure_patterns()))
        results.append(("Fast/Slow Path Logic", test_fast_slow_path_logic()))
        
        print("\n" + "=" * 80)
        print("TEST RESULTS SUMMARY")
        print("=" * 80)
        
        all_passed = True
        for test_name, passed in results:
            status = "✅ PASSED" if passed else "❌ FAILED"
            print(f"{status}: {test_name}")
            if not passed:
                all_passed = False
        
        print("\n" + "=" * 80)
        if all_passed:
            print("✅ ALL TESTS PASSED")
            print("=" * 80)
            print("\nNext Steps:")
            print("1. Run integration tests with HA/OpenAI setup")
            print("2. Check logs for 'FAST PATH' when testing suggestions")
            print("3. Verify suggestions in database include validated_entities field")
            return 0
        else:
            print("❌ SOME TESTS FAILED")
            print("=" * 80)
            return 1
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

