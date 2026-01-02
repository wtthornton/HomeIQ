"""
Tests for basic_validation_strategy.py
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.services.validation.basic_validation_strategy import BasicValidationStrategy


@pytest.fixture
def mock_tool_handler():
    """Mock HAToolHandler for testing."""
    handler = MagicMock()
    handler.data_api_client = MagicMock()
    handler.data_api_client.fetch_entities = AsyncMock(return_value=[
        {"entity_id": "light.office_led", "friendly_name": "Office LED"},
        {"entity_id": "light.office_go", "friendly_name": "Office Go"},
        {"entity_id": "switch.office_fan", "friendly_name": "Office Fan"},
    ])
    handler._extract_entities_from_yaml = MagicMock(return_value=["light.office_led"])
    handler._is_group_entity = MagicMock(return_value=False)
    return handler


class TestBasicValidationStrategy:
    """Test BasicValidationStrategy class."""

    def test___init__(self, mock_tool_handler):
        """Test __init__ method."""
        strategy = BasicValidationStrategy(mock_tool_handler)
        assert strategy.tool_handler == mock_tool_handler

    def test_name(self, mock_tool_handler):
        """Test name property."""
        strategy = BasicValidationStrategy(mock_tool_handler)
        assert strategy.name == "Basic Validation"

    def test__build_entity_error_message(self, mock_tool_handler):
        """Test _build_entity_error_message method."""
        strategy = BasicValidationStrategy(mock_tool_handler)
        valid_entities = {"light.office_go", "switch.office_fan"}
        
        # Test with similar entities (suggestions)
        error_msg = strategy._build_entity_error_message("light.office_led", valid_entities)
        assert "Invalid entity ID" in error_msg
        assert "light.office_led" in error_msg
        
        # Test without similar entities
        error_msg_no_match = strategy._build_entity_error_message("sensor.unknown", valid_entities)
        assert "Invalid entity ID" in error_msg_no_match
        assert "sensor.unknown" in error_msg_no_match

    @pytest.mark.asyncio
    async def test__validate_entities_with_invalid_entities(self, mock_tool_handler):
        """Test _validate_entities with invalid entities."""
        strategy = BasicValidationStrategy(mock_tool_handler)
        mock_tool_handler._extract_entities_from_yaml.return_value = ["light.invalid_entity"]
        
        errors, warnings = await strategy._validate_entities(["light.invalid_entity"])
        assert len(errors) > 0
        assert any("Invalid entity ID" in err for err in errors)

    @pytest.mark.asyncio
    async def test__validate_entities_with_valid_entities(self, mock_tool_handler):
        """Test _validate_entities with valid entities."""
        strategy = BasicValidationStrategy(mock_tool_handler)
        
        errors, warnings = await strategy._validate_entities(["light.office_led"])
        assert len(errors) == 0

    @pytest.mark.asyncio
    async def test__validate_entities_no_data_api_client(self):
        """Test _validate_entities when Data API client is not available."""
        handler = MagicMock()
        handler.data_api_client = None
        strategy = BasicValidationStrategy(handler)
        
        errors, warnings = await strategy._validate_entities(["light.office_led"])
        assert len(errors) == 0
        assert len(warnings) == 0

    def test__detect_dimming_pattern_issues_non_dimming(self, mock_tool_handler):
        """Test _detect_dimming_pattern_issues with non-dimming automation."""
        strategy = BasicValidationStrategy(mock_tool_handler)
        automation_dict = {
            "alias": "Turn on lights",
            "description": "Turn on office lights at 7 AM",
            "action": [
                {
                    "service": "light.turn_on",
                    "target": {"area_id": "office"},
                    "data": {"brightness": 255}
                }
            ]
        }
        
        warnings = strategy._detect_dimming_pattern_issues(automation_dict)
        assert len(warnings) == 0

    def test__detect_dimming_pattern_issues_correct_pattern(self, mock_tool_handler):
        """Test _detect_dimming_pattern_issues with correct dimming pattern."""
        strategy = BasicValidationStrategy(mock_tool_handler)
        automation_dict = {
            "alias": "Office motion-based dimming lights",
            "description": "Use all office motion sensors to turn office lights on with motion and gradually dim them to off after 1 minute of no motion.",
            "trigger": [
                {
                    "platform": "state",
                    "entity_id": ["binary_sensor.office_motion_1"],
                    "to": "on"
                },
                {
                    "platform": "state",
                    "entity_id": ["binary_sensor.office_motion_1"],
                    "to": "off",
                    "for": "00:01:00"
                }
            ],
            "action": [
                {
                    "choose": [
                        {
                            "conditions": [
                                {
                                    "condition": "or",
                                    "conditions": [
                                        {
                                            "condition": "state",
                                            "entity_id": "binary_sensor.office_motion_1",
                                            "state": "on"
                                        }
                                    ]
                                }
                            ],
                            "sequence": [
                                {
                                    "service": "light.turn_on",
                                    "target": {"area_id": "office"},
                                    "data": {"brightness": 255}
                                }
                            ]
                        },
                        {
                            "conditions": [
                                {
                                    "condition": "and",
                                    "conditions": [
                                        {
                                            "condition": "state",
                                            "entity_id": "binary_sensor.office_motion_1",
                                            "state": "off"
                                        }
                                    ]
                                }
                            ],
                            "sequence": [
                                {
                                    "repeat": {
                                        "count": 7,
                                        "sequence": [
                                            {
                                                "service": "light.turn_on",
                                                "target": {"area_id": "office"},
                                                "data": {"brightness_step": -40, "transition": 2}
                                            },
                                            {"delay": "00:00:03"}
                                        ]
                                    }
                                },
                                {
                                    "service": "light.turn_off",
                                    "target": {"area_id": "office"}
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        
        warnings = strategy._detect_dimming_pattern_issues(automation_dict)
        assert len(warnings) == 0

    def test__detect_dimming_pattern_issues_until_instead_of_count(self, mock_tool_handler):
        """Test _detect_dimming_pattern_issues detects 'until' instead of 'count'."""
        strategy = BasicValidationStrategy(mock_tool_handler)
        automation_dict = {
            "alias": "Office motion dimming",
            "description": "Dim office lights after no motion",
            "action": [
                {
                    "choose": [
                        {
                            "sequence": [
                                {
                                    "repeat": {
                                        "until": [
                                            {
                                                "condition": "state",
                                                "entity_id": "light.office",
                                                "state": "off"
                                            }
                                        ],
                                        "sequence": [
                                            {
                                                "service": "light.turn_on",
                                                "target": {"area_id": "office"},
                                                "data": {"brightness_step": -40}
                                            }
                                        ]
                                    }
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        
        warnings = strategy._detect_dimming_pattern_issues(automation_dict)
        assert len(warnings) > 0
        assert any("until" in w.lower() and "count" in w.lower() for w in warnings)

    def test__detect_dimming_pattern_issues_missing_turn_off(self, mock_tool_handler):
        """Test _detect_dimming_pattern_issues detects missing light.turn_off."""
        strategy = BasicValidationStrategy(mock_tool_handler)
        automation_dict = {
            "alias": "Office motion dimming",
            "description": "Dim office lights after no motion",
            "action": [
                {
                    "choose": [
                        {
                            "sequence": [
                                {
                                    "repeat": {
                                        "count": 7,
                                        "sequence": [
                                            {
                                                "service": "light.turn_on",
                                                "target": {"area_id": "office"},
                                                "data": {"brightness_step": -40}
                                            }
                                        ]
                                    }
                                }
                                # Missing light.turn_off here
                            ]
                        }
                    ]
                }
            ]
        }
        
        warnings = strategy._detect_dimming_pattern_issues(automation_dict)
        assert len(warnings) > 0
        assert any("turn_off" in w.lower() or "turn off" in w.lower() for w in warnings)

    def test__detect_dimming_pattern_issues_single_trigger_both_states(self, mock_tool_handler):
        """Test _detect_dimming_pattern_issues detects single trigger with both states."""
        strategy = BasicValidationStrategy(mock_tool_handler)
        automation_dict = {
            "alias": "Office motion dimming",
            "description": "Dim office lights after no motion",
            "trigger": [
                {
                    "platform": "state",
                    "entity_id": ["binary_sensor.office_motion_1"],
                    "to": ["on", "off"]  # Both states in single trigger
                }
            ],
            "action": [
                {
                    "service": "light.turn_on",
                    "target": {"area_id": "office"}
                }
            ]
        }
        
        warnings = strategy._detect_dimming_pattern_issues(automation_dict)
        assert len(warnings) > 0
        assert any("separate triggers" in w.lower() or "separate trigger" in w.lower() for w in warnings)

    def test__detect_dimming_pattern_issues_individual_for_in_conditions(self, mock_tool_handler):
        """Test _detect_dimming_pattern_issues detects individual 'for:' in conditions."""
        strategy = BasicValidationStrategy(mock_tool_handler)
        automation_dict = {
            "alias": "Office motion dimming",
            "description": "Dim office lights after no motion",
            "action": [
                {
                    "choose": [
                        {
                            "conditions": [
                                {
                                    "condition": "and",
                                    "conditions": [
                                        {
                                            "condition": "state",
                                            "entity_id": "binary_sensor.office_motion_1",
                                            "state": "off",
                                            "for": "00:01:00"  # Individual for: in condition
                                        },
                                        {
                                            "condition": "state",
                                            "entity_id": "binary_sensor.office_motion_2",
                                            "state": "off",
                                            "for": "00:01:00"  # Individual for: in condition
                                        }
                                    ]
                                }
                            ],
                            "sequence": [
                                {
                                    "service": "light.turn_on",
                                    "target": {"area_id": "office"}
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        
        warnings = strategy._detect_dimming_pattern_issues(automation_dict)
        assert len(warnings) > 0
        assert any("for:" in w or "independently" in w.lower() for w in warnings)
