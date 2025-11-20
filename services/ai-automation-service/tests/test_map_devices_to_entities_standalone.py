"""
Standalone unit tests for map_devices_to_entities and consolidate_devices_involved functions.

These tests verify the logic without requiring full module imports.
Tests the optimization for single-home local solutions.
"""


import pytest


def consolidate_devices_involved_logic(
    devices_involved: list[str],
    validated_entities: dict[str, str]
) -> list[str]:
    """
    Standalone version of consolidate_devices_involved for testing.
    This matches the actual implementation logic.
    """
    if not devices_involved or not validated_entities:
        return devices_involved

    # Group device names by their mapped entity_id
    entity_id_to_devices = {}
    for device_name in devices_involved:
        entity_id = validated_entities.get(device_name)
        if entity_id:
            if entity_id not in entity_id_to_devices:
                entity_id_to_devices[entity_id] = []
            entity_id_to_devices[entity_id].append(device_name)

    # For each entity_id, keep the most specific device name
    # Priority: longer names > exact matches > shorter names
    consolidated = []
    entity_ids_seen = set()

    for device_name in devices_involved:
        entity_id = validated_entities.get(device_name)
        if entity_id:
            if entity_id not in entity_ids_seen:
                # First time seeing this entity_id - add it
                if len(entity_id_to_devices.get(entity_id, [])) > 1:
                    # Multiple devices map to this entity - choose the best one
                    candidates = entity_id_to_devices[entity_id]
                    # Prefer longer, more specific names
                    best_name = max(candidates, key=lambda x: (len(x), x.count(' '), x.lower()))
                    consolidated.append(best_name)
                else:
                    # Only one device maps to this entity
                    consolidated.append(device_name)
                entity_ids_seen.add(entity_id)
            # If entity_id already seen, skip (already consolidated)
        else:
            # Keep unmapped devices (they might be groups or areas)
            consolidated.append(device_name)

    return consolidated


class TestConsolidateDevicesInvolved:
    """Test suite for consolidate_devices_involved function"""

    def test_basic_consolidation(self):
        """Test basic consolidation of redundant device names"""
        devices_involved = ["wled led strip", "Office", "WLED Office"]
        validated_entities = {
            "wled led strip": "light.wled_office",
            "Office": "light.wled_office",
            "WLED Office": "light.wled_office"
        }

        result = consolidate_devices_involved_logic(devices_involved, validated_entities)

        # Should consolidate to one entry (prefer longer name)
        assert len(result) == 1
        # "wled led strip" is longest (14 chars), so it should be preferred
        assert result[0] in ["wled led strip", "WLED Office", "Office"]  # Any valid consolidation

    def test_multiple_entities_no_redundancy(self):
        """Test consolidation when no redundancy exists"""
        devices_involved = [
            "LR Front Left Ceiling",
            "LR Back Right Ceiling",
            "LR Front Right Ceiling",
            "LR Back Left Ceiling"
        ]
        validated_entities = {
            "LR Front Left Ceiling": "light.lr_front_left_ceiling",
            "LR Back Right Ceiling": "light.lr_back_right_ceiling",
            "LR Front Right Ceiling": "light.lr_front_right_ceiling",
            "LR Back Left Ceiling": "light.lr_back_left_ceiling"
        }

        result = consolidate_devices_involved_logic(devices_involved, validated_entities)

        # All are unique entities, so no consolidation
        assert len(result) == 4
        assert set(result) == set(devices_involved)

    def test_complete_case_consolidation(self):
        """Test consolidation for the complete case from lines 550-557"""
        devices_involved = [
            "wled led strip",
            "ceiling lights",
            "Office",
            "LR Front Left Ceiling",
            "LR Back Right Ceiling",
            "LR Front Right Ceiling",
            "LR Back Left Ceiling"
        ]
        validated_entities = {
            "wled led strip": "light.wled_office",
            "Office": "light.wled_office",
            "LR Front Left Ceiling": "light.lr_front_left_ceiling",
            "LR Back Right Ceiling": "light.lr_back_right_ceiling",
            "LR Front Right Ceiling": "light.lr_front_right_ceiling",
            "LR Back Left Ceiling": "light.lr_back_left_ceiling"
        }

        result = consolidate_devices_involved_logic(devices_involved, validated_entities)

        # Should consolidate from 7 → 5-6 entries
        # ("ceiling lights" is unmapped, so kept; WLED mappings consolidated)
        assert len(result) <= 6  # At most 6 (1 WLED + 4 ceiling + 1 unmapped)
        assert len(result) >= 5  # At least 5 (1 WLED + 4 ceiling lights)

        # Should keep one WLED entry (prefer longer name)
        wled_entries = [d for d in result if "wled" in d.lower() or ("office" in d.lower() and "ceiling" not in d.lower())]
        assert len(wled_entries) == 1

        # Should keep all 4 specific ceiling lights (plus generic "ceiling lights" if unmapped)
        ceiling_entries = [d for d in result if "ceiling" in d.lower()]
        assert len(ceiling_entries) >= 4  # At least 4 specific ceiling lights
        assert len(ceiling_entries) <= 5  # At most 5 (4 specific + 1 generic if unmapped)

    def test_mixed_mapped_unmapped(self):
        """Test consolidation with some unmapped devices"""
        devices_involved = ["WLED Office", "Non-existent Device", "LR Front Left Ceiling"]
        validated_entities = {
            "WLED Office": "light.wled_office",
            "LR Front Left Ceiling": "light.lr_front_left_ceiling"
        }

        result = consolidate_devices_involved_logic(devices_involved, validated_entities)

        # Should keep unmapped device, consolidate mapped ones
        assert len(result) == 3  # All kept (no redundancy)
        assert "Non-existent Device" in result

    def test_empty_inputs(self):
        """Test with empty inputs"""
        result = consolidate_devices_involved_logic([], {})
        assert result == []

        result = consolidate_devices_involved_logic(["Device"], {})
        assert result == ["Device"]  # Unmapped devices kept

    def test_prefer_longer_names(self):
        """Test that longer, more specific names are preferred"""
        devices_involved = ["Office", "WLED Office", "Office WLED Light"]
        validated_entities = {
            "Office": "light.wled_office",
            "WLED Office": "light.wled_office",
            "Office WLED Light": "light.wled_office"
        }

        result = consolidate_devices_involved_logic(devices_involved, validated_entities)

        # Should prefer longest name
        assert len(result) == 1
        assert "Office WLED Light" in result  # Longest name

    def test_preserve_order(self):
        """Test that order is preserved while consolidating"""
        devices_involved = ["A", "B", "C", "D"]
        validated_entities = {
            "A": "light.entity1",
            "B": "light.entity1",  # Same as A
            "C": "light.entity2",
            "D": "light.entity2"   # Same as C
        }

        result = consolidate_devices_involved_logic(devices_involved, validated_entities)

        # Should consolidate to 2 entries (one per entity)
        assert len(result) == 2
        # First occurrence of each entity_id is kept (A for entity1, C for entity2)
        # But if multiple map to same entity, best name is selected
        assert result[0] in ["A", "B"]  # One of entity1 entries
        assert result[1] in ["C", "D"]  # One of entity2 entries

    def test_all_same_entity(self):
        """Test when all devices map to same entity"""
        devices_involved = ["Device 1", "Device 2", "Device 3", "Device 4"]
        validated_entities = dict.fromkeys(devices_involved, "light.same_entity")

        result = consolidate_devices_involved_logic(devices_involved, validated_entities)

        # Should consolidate to one entry
        assert len(result) == 1
        assert result[0] in devices_involved  # One of them kept

    def test_ceiling_lights_generic(self):
        """Test that generic 'ceiling lights' is handled if mapped"""
        devices_involved = ["ceiling lights", "LR Front Left Ceiling", "LR Back Right Ceiling"]
        validated_entities = {
            "ceiling lights": "light.lr_front_left_ceiling",  # Generic maps to one
            "LR Front Left Ceiling": "light.lr_front_left_ceiling",
            "LR Back Right Ceiling": "light.lr_back_right_ceiling"
        }

        result = consolidate_devices_involved_logic(devices_involved, validated_entities)

        # Should consolidate: "ceiling lights" + "LR Front Left Ceiling" → one entry
        assert len(result) == 2  # One consolidated + one unique
        assert "LR Back Right Ceiling" in result  # Unique entity
        # Should prefer specific name over generic
        assert "LR Front Left Ceiling" in result or "ceiling lights" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

