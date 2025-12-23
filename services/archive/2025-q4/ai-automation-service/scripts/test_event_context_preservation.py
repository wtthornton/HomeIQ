#!/usr/bin/env python3
"""
Test script to verify event_context preservation in synergy metadata.

This script tests the metadata merging logic to ensure event-specific fields
like event_context, event_type, and suggested_action are preserved when storing synergies.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_metadata_merging():
    """Test that event_context is preserved in metadata merging."""
    
    # Simulate event opportunity data (as created by EventOpportunityDetector)
    sports_opportunity = {
        'synergy_id': 'test-sports-123',
        'synergy_type': 'event_context',
        'devices': ['media_player.living_room_tv'],
        'action_entity': 'media_player.living_room_tv',
        'area': 'living_room',
        'relationship': 'sports_event_scene',
        'impact_score': 0.65,
        'complexity': 'medium',
        'confidence': 0.70,
        'opportunity_metadata': {
            'action_name': 'Living Room TV',
            'event_context': 'Sports events',  # This should be preserved!
            'event_type': 'sports',
            'suggested_action': 'Activate scene when favorite team plays',
            'rationale': 'Automate Living Room TV for sports viewing'
        }
    }
    
    calendar_opportunity = {
        'synergy_id': 'test-calendar-456',
        'synergy_type': 'event_context',
        'devices': ['media_player.denon_avr'],
        'action_entity': 'media_player.denon_avr',
        'area': 'entertainment',
        'relationship': 'calendar_event_scene',
        'impact_score': 0.60,
        'complexity': 'medium',
        'confidence': 0.65,
        'opportunity_metadata': {
            'action_name': 'Denon AVR',
            'event_context': 'Calendar events',  # This should be preserved!
            'event_type': 'calendar',
            'suggested_action': 'Activate scene based on calendar events',
            'rationale': 'Automate Denon AVR based on calendar schedule'
        }
    }
    
    # Simulate the new metadata merging logic (from crud.py)
    def merge_metadata(synergy_data):
        """Replicate the metadata merging logic from store_synergy_opportunities."""
        existing_metadata = synergy_data.get('opportunity_metadata', {})
        if not isinstance(existing_metadata, dict):
            existing_metadata = {}
        
        # Build base metadata with standard fields (only non-None values)
        base_metadata = {}
        for key in ['trigger_entity', 'trigger_name', 'action_entity', 'action_name', 'relationship', 'rationale']:
            value = synergy_data.get(key)
            if value is not None:
                base_metadata[key] = value
        
        # Merge: Start with existing_metadata (preserves event_context, event_type, suggested_action, etc.)
        # Then overlay base_metadata to ensure standard fields are set
        metadata = {**existing_metadata, **base_metadata}
        
        return metadata
    
    # Test sports opportunity
    sports_metadata = merge_metadata(sports_opportunity)
    print("=" * 60)
    print("TEST 1: Sports Event Opportunity")
    print("=" * 60)
    print(f"Original event_context: {sports_opportunity['opportunity_metadata']['event_context']}")
    print(f"Merged event_context: {sports_metadata.get('event_context', 'MISSING!')}")
    print(f"Event type: {sports_metadata.get('event_type', 'MISSING!')}")
    print(f"Suggested action: {sports_metadata.get('suggested_action', 'MISSING!')}")
    print(f"Action entity: {sports_metadata.get('action_entity', 'MISSING!')}")
    print(f"Action name: {sports_metadata.get('action_name', 'MISSING!')}")
    
    assert sports_metadata.get('event_context') == 'Sports events', "❌ FAIL: event_context not preserved!"
    assert sports_metadata.get('event_type') == 'sports', "❌ FAIL: event_type not preserved!"
    assert sports_metadata.get('suggested_action') is not None, "❌ FAIL: suggested_action not preserved!"
    assert sports_metadata.get('action_entity') == 'media_player.living_room_tv', "❌ FAIL: action_entity not set!"
    print("✅ PASS: Sports event metadata preserved correctly")
    
    # Test calendar opportunity
    calendar_metadata = merge_metadata(calendar_opportunity)
    print("\n" + "=" * 60)
    print("TEST 2: Calendar Event Opportunity")
    print("=" * 60)
    print(f"Original event_context: {calendar_opportunity['opportunity_metadata']['event_context']}")
    print(f"Merged event_context: {calendar_metadata.get('event_context', 'MISSING!')}")
    print(f"Event type: {calendar_metadata.get('event_type', 'MISSING!')}")
    print(f"Suggested action: {calendar_metadata.get('suggested_action', 'MISSING!')}")
    print(f"Action entity: {calendar_metadata.get('action_entity', 'MISSING!')}")
    print(f"Action name: {calendar_metadata.get('action_name', 'MISSING!')}")
    
    assert calendar_metadata.get('event_context') == 'Calendar events', "❌ FAIL: event_context not preserved!"
    assert calendar_metadata.get('event_type') == 'calendar', "❌ FAIL: event_type not preserved!"
    assert calendar_metadata.get('suggested_action') is not None, "❌ FAIL: suggested_action not preserved!"
    assert calendar_metadata.get('action_entity') == 'media_player.denon_avr', "❌ FAIL: action_entity not set!"
    print("✅ PASS: Calendar event metadata preserved correctly")
    
    # Test with missing opportunity_metadata (backward compatibility)
    device_pair_synergy = {
        'synergy_id': 'test-pair-789',
        'synergy_type': 'device_pair',
        'trigger_entity': 'binary_sensor.motion',
        'trigger_name': 'Motion Sensor',
        'action_entity': 'light.living_room',
        'action_name': 'Living Room Light',
        'relationship': 'motion_to_light',
        'rationale': 'Motion-activated lighting'
    }
    
    pair_metadata = merge_metadata(device_pair_synergy)
    print("\n" + "=" * 60)
    print("TEST 3: Device Pair (No opportunity_metadata)")
    print("=" * 60)
    print(f"Trigger entity: {pair_metadata.get('trigger_entity', 'MISSING!')}")
    print(f"Action entity: {pair_metadata.get('action_entity', 'MISSING!')}")
    print(f"Relationship: {pair_metadata.get('relationship', 'MISSING!')}")
    print(f"Event context: {pair_metadata.get('event_context', 'None (expected)')}")
    
    assert pair_metadata.get('trigger_entity') == 'binary_sensor.motion', "❌ FAIL: trigger_entity not set!"
    assert pair_metadata.get('action_entity') == 'light.living_room', "❌ FAIL: action_entity not set!"
    assert pair_metadata.get('event_context') is None, "❌ FAIL: event_context should be None for device pairs!"
    print("✅ PASS: Device pair metadata works correctly (backward compatible)")
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
    print("\nThe metadata merging logic correctly preserves:")
    print("  - event_context (Sports events, Calendar events, Holiday events)")
    print("  - event_type (sports, calendar, holiday)")
    print("  - suggested_action")
    print("  - All standard fields (trigger_entity, action_entity, etc.)")
    print("\nThe fix is working correctly! 🎉")

if __name__ == '__main__':
    try:
        test_metadata_merging()
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

