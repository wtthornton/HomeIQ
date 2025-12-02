"""
Tests for voice command hint generator

Story AI10.3: Voice Command Hints in Descriptions
Epic AI-10: Home Assistant 2025 YAML Target Optimization
"""

import pytest

from src.services.automation.voice_hint_generator import (
    generate_voice_hints,
    get_entity_aliases,
    suggest_entity_aliases,
    _generate_voice_hint_for_action,
    _generate_generic_voice_hint,
    _get_service_verb,
    _humanize_name,
    _add_voice_hints_to_description
)


class TestVoiceHintGeneration:
    """Tests for voice hint generation"""

    def test_generate_voice_hints_area_based(self):
        """Test voice hints for area-based automation"""
        yaml_data = {
            "alias": "Living Room - Evening Lights",
            "description": "Turn on living room lights at sunset",
            "action": [
                {
                    "service": "light.turn_on",
                    "target": {
                        "area_id": "living_room"
                    }
                }
            ]
        }
        
        enhanced = generate_voice_hints(yaml_data)
        
        # Should add voice hint
        description = enhanced.get("description", "")
        assert "(voice:" in description.lower()
        assert "living room" in description.lower()
    
    def test_generate_voice_hints_label_based(self):
        """Test voice hints for label-based automation"""
        yaml_data = {
            "alias": "Holiday Lights Auto On",
            "description": "Turn on all holiday lights at sunset",
            "action": [
                {
                    "service": "light.turn_on",
                    "target": {
                        "label_id": "holiday-lights"
                    }
                }
            ]
        }
        
        enhanced = generate_voice_hints(yaml_data)
        
        # Should add voice hint
        description = enhanced.get("description", "")
        assert "(voice:" in description.lower()
        assert "holiday" in description.lower()
    
    def test_generate_voice_hints_single_entity(self):
        """Test voice hints for single entity automation"""
        yaml_data = {
            "alias": "Bedroom Lamp Auto Off",
            "description": "Turn off bedroom lamp at midnight",
            "action": [
                {
                    "service": "light.turn_off",
                    "target": {
                        "entity_id": ["light.bedroom_lamp"]
                    }
                }
            ]
        }
        
        entities_metadata = {
            "light.bedroom_lamp": {
                "entity_id": "light.bedroom_lamp",
                "friendly_name": "Bedroom Lamp",
                "name_by_user": "Bedside Lamp",
                "aliases": ["bedside light", "reading lamp"]
            }
        }
        
        enhanced = generate_voice_hints(yaml_data, entities_metadata)
        
        # Should add voice hint
        description = enhanced.get("description", "")
        assert "(voice:" in description.lower()
        # Should use name_by_user (highest priority)
        assert "bedside lamp" in description.lower()
    
    def test_generate_voice_hints_multiple_entities_same_area(self):
        """Test voice hints when multiple entities in same area"""
        yaml_data = {
            "alias": "Kitchen Lights Auto On",
            "description": "Turn on kitchen lights at sunset",
            "action": [
                {
                    "service": "light.turn_on",
                    "target": {
                        "entity_id": ["light.kitchen_ceiling", "light.kitchen_counter"]
                    }
                }
            ]
        }
        
        entities_metadata = {
            "light.kitchen_ceiling": {
                "entity_id": "light.kitchen_ceiling",
                "area_id": "kitchen"
            },
            "light.kitchen_counter": {
                "entity_id": "light.kitchen_counter",
                "area_id": "kitchen"
            }
        }
        
        enhanced = generate_voice_hints(yaml_data, entities_metadata)
        
        # Should add voice hint with common area
        description = enhanced.get("description", "")
        assert "(voice:" in description.lower()
        assert "kitchen" in description.lower()
    
    def test_generate_voice_hints_no_duplicate(self):
        """Test that voice hints are not duplicated if already exist"""
        yaml_data = {
            "alias": "Living Room Lights",
            "description": "Turn on lights (voice: 'turn on living room')",
            "action": [
                {
                    "service": "light.turn_on",
                    "target": {
                        "area_id": "living_room"
                    }
                }
            ]
        }
        
        enhanced = generate_voice_hints(yaml_data)
        
        # Should NOT add duplicate voice hints
        description = enhanced.get("description", "")
        assert description.count("(voice:") == 1
    
    def test_generate_voice_hints_multiple_actions(self):
        """Test voice hints with multiple actions"""
        yaml_data = {
            "alias": "Movie Time Scene",
            "description": "Set up movie watching scene",
            "action": [
                {
                    "service": "light.turn_off",
                    "target": {
                        "area_id": "living_room"
                    }
                },
                {
                    "service": "media_player.turn_on",
                    "target": {
                        "entity_id": ["media_player.tv"]
                    }
                }
            ]
        }
        
        entities_metadata = {
            "media_player.tv": {
                "entity_id": "media_player.tv",
                "friendly_name": "Living Room TV"
            }
        }
        
        enhanced = generate_voice_hints(yaml_data, entities_metadata)
        
        # Should add voice hints for both actions
        description = enhanced.get("description", "")
        assert "(voice:" in description.lower()


class TestVoiceHintForAction:
    """Tests for single action voice hint generation"""
    
    def test_area_based_action(self):
        """Test voice hint for area-based action"""
        action = {
            "service": "light.turn_on",
            "target": {
                "area_id": "bedroom"
            }
        }
        
        hint = _generate_voice_hint_for_action(action, None)
        
        assert hint is not None
        assert "bedroom" in hint.lower()
        assert "turn on" in hint.lower()
    
    def test_label_based_action(self):
        """Test voice hint for label-based action"""
        action = {
            "service": "light.turn_off",
            "target": {
                "label_id": "outdoor"
            }
        }
        
        hint = _generate_voice_hint_for_action(action, None)
        
        assert hint is not None
        assert "outdoor" in hint.lower()
        assert "turn off" in hint.lower()
    
    def test_device_based_action_with_area(self):
        """Test voice hint for device-based action with area context"""
        action = {
            "service": "light.toggle",
            "target": {
                "device_id": "abc123"
            }
        }
        
        entities_metadata = {
            "light.patio": {
                "device_id": "abc123",
                "area_id": "patio",
                "friendly_name": "Patio Light"
            }
        }
        
        hint = _generate_voice_hint_for_action(action, entities_metadata)
        
        assert hint is not None
        assert "patio" in hint.lower()


class TestServiceVerb:
    """Tests for service verb mapping"""
    
    def test_turn_on_verb(self):
        """Test turn_on service maps to 'turn on'"""
        assert _get_service_verb("light.turn_on") == "turn on"
    
    def test_turn_off_verb(self):
        """Test turn_off service maps to 'turn off'"""
        assert _get_service_verb("light.turn_off") == "turn off"
    
    def test_toggle_verb(self):
        """Test toggle service"""
        assert _get_service_verb("switch.toggle") == "toggle"
    
    def test_lock_unlock_verbs(self):
        """Test lock/unlock verbs"""
        assert _get_service_verb("lock.lock") == "lock"
        assert _get_service_verb("lock.unlock") == "unlock"
    
    def test_unknown_service(self):
        """Test unknown service returns cleaned name"""
        assert _get_service_verb("custom.my_action") == "my action"
    
    def test_invalid_service(self):
        """Test invalid service format"""
        assert _get_service_verb("invalid") == "control"
        assert _get_service_verb("") == "control"


class TestHumanizeName:
    """Tests for name humanization"""
    
    def test_underscores_to_spaces(self):
        """Test underscores converted to spaces"""
        assert _humanize_name("living_room") == "Living Room"
    
    def test_hyphens_to_spaces(self):
        """Test hyphens converted to spaces"""
        assert _humanize_name("holiday-lights") == "Holiday Lights"
    
    def test_title_case(self):
        """Test title casing"""
        assert _humanize_name("bedroom") == "Bedroom"
        assert _humanize_name("front_porch") == "Front Porch"
    
    def test_empty_string(self):
        """Test empty string"""
        assert _humanize_name("") == ""


class TestGenericVoiceHint:
    """Tests for generic voice hint generation"""
    
    def test_simple_alias(self):
        """Test generic hint from simple alias"""
        hint = _generate_generic_voice_hint("Movie Time")
        
        assert hint is not None
        assert "movie time" in hint.lower()
    
    def test_alias_with_automation_prefix(self):
        """Test alias with 'automation' prefix removed"""
        hint = _generate_generic_voice_hint("Automation - Evening Lights")
        
        assert hint is not None
        assert "automation" not in hint.lower()
        assert "evening lights" in hint.lower()
    
    def test_alias_with_action_verb(self):
        """Test alias with action verb preserved"""
        hint = _generate_generic_voice_hint("Turn on bedtime lights")
        
        assert hint is not None
        assert "turn on" in hint.lower()
    
    def test_empty_alias(self):
        """Test empty alias returns None"""
        assert _generate_generic_voice_hint("") is None
    
    def test_very_short_alias(self):
        """Test very short alias returns None"""
        assert _generate_generic_voice_hint("On") is None


class TestAddVoiceHintsToDescription:
    """Tests for adding voice hints to descriptions"""
    
    def test_add_single_hint(self):
        """Test adding single voice hint"""
        description = "Turn on living room lights at sunset"
        hints = ["'turn on living room'"]
        
        enhanced = _add_voice_hints_to_description(description, hints)
        
        assert "(voice: 'turn on living room')" in enhanced
        assert description in enhanced
    
    def test_add_two_hints(self):
        """Test adding two voice hints"""
        description = "Movie time scene"
        hints = ["'movie time'", "'activate movie mode'"]
        
        enhanced = _add_voice_hints_to_description(description, hints)
        
        assert "(voice:" in enhanced
        assert "or" in enhanced
        assert "'movie time'" in enhanced
        assert "'activate movie mode'" in enhanced
    
    def test_add_multiple_hints(self):
        """Test adding multiple hints (shows first two)"""
        description = "Evening routine"
        hints = ["'evening routine'", "'good night'", "'bedtime'", "'sleep mode'"]
        
        enhanced = _add_voice_hints_to_description(description, hints)
        
        assert "(voice:" in enhanced
        assert "or more" in enhanced
        # Should show first two hints
        assert "'evening routine'" in enhanced
        assert "'good night'" in enhanced
    
    def test_empty_description(self):
        """Test with empty description"""
        hints = ["'turn on lights'"]
        
        enhanced = _add_voice_hints_to_description("", hints)
        
        assert "voice-controlled automation" in enhanced.lower()
        assert "'turn on lights'" in enhanced
    
    def test_no_hints(self):
        """Test with no hints"""
        description = "Turn on lights"
        
        enhanced = _add_voice_hints_to_description(description, [])
        
        assert enhanced == description


class TestEntityAliases:
    """Tests for entity alias functions"""
    
    def test_get_entity_aliases(self):
        """Test getting entity aliases from metadata"""
        entities_metadata = {
            "light.bedroom": {
                "entity_id": "light.bedroom",
                "aliases": ["bedside light", "reading lamp"]
            }
        }
        
        aliases = get_entity_aliases("light.bedroom", entities_metadata)
        
        assert aliases == ["bedside light", "reading lamp"]
    
    def test_get_entity_aliases_no_aliases(self):
        """Test getting aliases when none exist"""
        entities_metadata = {
            "light.bedroom": {
                "entity_id": "light.bedroom"
            }
        }
        
        aliases = get_entity_aliases("light.bedroom", entities_metadata)
        
        assert aliases == []
    
    def test_get_entity_aliases_no_metadata(self):
        """Test getting aliases when metadata missing"""
        aliases = get_entity_aliases("light.bedroom", None)
        
        assert aliases == []
    
    def test_suggest_entity_aliases(self):
        """Test suggesting aliases for an entity"""
        suggestions = suggest_entity_aliases(
            "light.bedroom_lamp",
            "Bedroom Lamp"
        )
        
        assert len(suggestions) > 0
        assert any("bedroom" in s.lower() for s in suggestions)
    
    def test_suggest_entity_aliases_light_domain(self):
        """Test suggesting aliases for light entity"""
        suggestions = suggest_entity_aliases(
            "light.bedroom_ceiling",
            None
        )
        
        assert len(suggestions) > 0
        # Should suggest domain-specific alias for bedroom light
        assert any("bedroom" in s.lower() for s in suggestions)
    
    def test_suggest_entity_aliases_removes_duplicates(self):
        """Test alias suggestions remove duplicates"""
        suggestions = suggest_entity_aliases(
            "switch.bedroom_fan",
            "Bedroom Fan Switch"
        )
        
        # Should not have duplicate "bedroom fan" entries
        lowercase_suggestions = [s.lower() for s in suggestions]
        assert len(lowercase_suggestions) == len(set(lowercase_suggestions))

