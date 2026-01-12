"""
Tests for Home Assistant 2026.1 Purpose-Specific Triggers

Tests new trigger types and enhanced targeting support.
"""

import pytest

from shared.homeiq_automation.converter import HomeIQToAutomationSpecConverter
from shared.homeiq_automation.schema import (
    HomeIQAutomation,
    HomeIQMetadata,
    HomeIQTrigger,
    HomeIQAction,
    HomeIQCondition,
    DeviceContext,
    TriggerConfig,
    Target,
)
from shared.yaml_validation_service.version_aware_renderer import VersionAwareRenderer


class TestNewTriggerTypes:
    """Test all new purpose-specific trigger types from HA 2026.1."""
    
    def test_button_trigger(self):
        """Test button trigger."""
        automation = HomeIQAutomation(
            alias="Button Test",
            homeiq_metadata=HomeIQMetadata(use_case="comfort", complexity="low"),
            device_context=DeviceContext(entity_ids=["button.living_room_button"]),
            triggers=[
                HomeIQTrigger(
                    platform="button",
                    config=TriggerConfig(
                        entity_id="button.living_room_button",
                        parameters={"action": "press"}
                    )
                )
            ],
            actions=[
                HomeIQAction(service="light.turn_on")
            ]
        )
        
        converter = HomeIQToAutomationSpecConverter()
        spec = converter.convert(automation)
        
        assert len(spec.trigger) == 1
        trigger = spec.trigger[0]
        assert trigger.platform == "button"
        assert trigger.extra["entity_id"] == "button.living_room_button"
        assert trigger.extra["action"] == "press"
    
    def test_climate_trigger_mode_change(self):
        """Test climate trigger for HVAC mode changes."""
        automation = HomeIQAutomation(
            alias="Climate Mode Test",
            homeiq_metadata=HomeIQMetadata(use_case="comfort", complexity="low"),
            device_context=DeviceContext(entity_ids=["climate.living_room"]),
            triggers=[
                HomeIQTrigger(
                    platform="climate",
                    config=TriggerConfig(
                        entity_id="climate.living_room",
                        parameters={"mode": "heating"}
                    )
                )
            ],
            actions=[HomeIQAction(service="climate.set_temperature")]
        )
        
        converter = HomeIQToAutomationSpecConverter()
        spec = converter.convert(automation)
        
        assert spec.trigger[0].platform == "climate"
        assert spec.trigger[0].extra["entity_id"] == "climate.living_room"
        assert spec.trigger[0].extra["mode"] == "heating"
    
    def test_climate_trigger_temperature_threshold(self):
        """Test climate trigger for temperature threshold."""
        automation = HomeIQAutomation(
            alias="Climate Temperature Test",
            homeiq_metadata=HomeIQMetadata(use_case="comfort", complexity="low"),
            device_context=DeviceContext(entity_ids=["climate.living_room"]),
            triggers=[
                HomeIQTrigger(
                    platform="climate",
                    config=TriggerConfig(
                        entity_id="climate.living_room",
                        parameters={"temperature_threshold": 20.0}
                    )
                )
            ],
            actions=[HomeIQAction(service="climate.set_temperature")]
        )
        
        converter = HomeIQToAutomationSpecConverter()
        spec = converter.convert(automation)
        
        assert spec.trigger[0].extra["temperature_threshold"] == 20.0
    
    def test_device_tracker_trigger(self):
        """Test device tracker trigger for arrival/departure."""
        automation = HomeIQAutomation(
            alias="Device Tracker Test",
            homeiq_metadata=HomeIQMetadata(use_case="security", complexity="low"),
            device_context=DeviceContext(entity_ids=["device_tracker.phone"]),
            triggers=[
                HomeIQTrigger(
                    platform="device_tracker",
                    config=TriggerConfig(
                        entity_id="device_tracker.phone",
                        parameters={"event": "entered_home"}
                    )
                )
            ],
            actions=[HomeIQAction(service="light.turn_on")]
        )
        
        converter = HomeIQToAutomationSpecConverter()
        spec = converter.convert(automation)
        
        assert spec.trigger[0].platform == "device_tracker"
        assert spec.trigger[0].extra["event"] == "entered_home"
    
    def test_humidifier_trigger(self):
        """Test humidifier trigger."""
        automation = HomeIQAutomation(
            alias="Humidifier Test",
            homeiq_metadata=HomeIQMetadata(use_case="comfort", complexity="low"),
            device_context=DeviceContext(entity_ids=["humidifier.living_room"]),
            triggers=[
                HomeIQTrigger(
                    platform="humidifier",
                    config=TriggerConfig(
                        entity_id="humidifier.living_room",
                        parameters={"state": "on"}
                    )
                )
            ],
            actions=[HomeIQAction(service="humidifier.turn_on")]
        )
        
        converter = HomeIQToAutomationSpecConverter()
        spec = converter.convert(automation)
        
        assert spec.trigger[0].platform == "humidifier"
        assert spec.trigger[0].extra["state"] == "on"
    
    def test_light_trigger_brightness_threshold(self):
        """Test light trigger for brightness threshold."""
        automation = HomeIQAutomation(
            alias="Light Brightness Test",
            homeiq_metadata=HomeIQMetadata(use_case="comfort", complexity="low"),
            device_context=DeviceContext(entity_ids=["light.living_room"]),
            triggers=[
                HomeIQTrigger(
                    platform="light",
                    config=TriggerConfig(
                        entity_id="light.living_room",
                        parameters={"brightness_threshold": 128}
                    )
                )
            ],
            actions=[HomeIQAction(service="light.turn_on")]
        )
        
        converter = HomeIQToAutomationSpecConverter()
        spec = converter.convert(automation)
        
        assert spec.trigger[0].platform == "light"
        assert spec.trigger[0].extra["brightness_threshold"] == 128
    
    def test_lock_trigger(self):
        """Test lock trigger for lock/unlock events."""
        automation = HomeIQAutomation(
            alias="Lock Test",
            homeiq_metadata=HomeIQMetadata(use_case="security", complexity="low"),
            device_context=DeviceContext(entity_ids=["lock.front_door"]),
            triggers=[
                HomeIQTrigger(
                    platform="lock",
                    config=TriggerConfig(
                        entity_id="lock.front_door",
                        parameters={"event": "unlocked"}
                    )
                )
            ],
            actions=[HomeIQAction(service="lock.lock")]
        )
        
        converter = HomeIQToAutomationSpecConverter()
        spec = converter.convert(automation)
        
        assert spec.trigger[0].platform == "lock"
        assert spec.trigger[0].extra["event"] == "unlocked"
    
    def test_scene_trigger(self):
        """Test scene trigger."""
        automation = HomeIQAutomation(
            alias="Scene Test",
            homeiq_metadata=HomeIQMetadata(use_case="comfort", complexity="low"),
            device_context=DeviceContext(entity_ids=["scene.movie_mode"]),
            triggers=[
                HomeIQTrigger(
                    platform="scene",
                    config=TriggerConfig(
                        entity_id="scene.movie_mode"
                    )
                )
            ],
            actions=[HomeIQAction(scene="scene.movie_mode")]
        )
        
        converter = HomeIQToAutomationSpecConverter()
        spec = converter.convert(automation)
        
        assert spec.trigger[0].platform == "scene"
        assert spec.trigger[0].extra["entity_id"] == "scene.movie_mode"
    
    def test_siren_trigger(self):
        """Test siren trigger."""
        automation = HomeIQAutomation(
            alias="Siren Test",
            homeiq_metadata=HomeIQMetadata(use_case="security", complexity="low"),
            device_context=DeviceContext(entity_ids=["siren.alarm"]),
            triggers=[
                HomeIQTrigger(
                    platform="siren",
                    config=TriggerConfig(
                        entity_id="siren.alarm",
                        parameters={"state": "on"}
                    )
                )
            ],
            actions=[HomeIQAction(service="siren.turn_on")]
        )
        
        converter = HomeIQToAutomationSpecConverter()
        spec = converter.convert(automation)
        
        assert spec.trigger[0].platform == "siren"
        assert spec.trigger[0].extra["state"] == "on"
    
    def test_update_trigger(self):
        """Test update trigger."""
        automation = HomeIQAutomation(
            alias="Update Test",
            homeiq_metadata=HomeIQMetadata(use_case="convenience", complexity="low"),
            device_context=DeviceContext(entity_ids=["update.home_assistant"]),
            triggers=[
                HomeIQTrigger(
                    platform="update",
                    config=TriggerConfig(
                        entity_id="update.home_assistant"
                    )
                )
            ],
            actions=[HomeIQAction(service="update.install")]
        )
        
        converter = HomeIQToAutomationSpecConverter()
        spec = converter.convert(automation)
        
        assert spec.trigger[0].platform == "update"
        assert spec.trigger[0].extra["entity_id"] == "update.home_assistant"


class TestEnhancedTargeting:
    """Test enhanced targeting (areas, floors, labels) in triggers, conditions, and actions."""
    
    def test_trigger_with_area_targeting(self):
        """Test trigger with area targeting."""
        automation = HomeIQAutomation(
            alias="Area Targeting Test",
            homeiq_metadata=HomeIQMetadata(use_case="comfort", complexity="low"),
            device_context=DeviceContext(entity_ids=["light.living_room"]),
            triggers=[
                HomeIQTrigger(
                    platform="state",
                    config=TriggerConfig(
                        parameters={"to": "on"}
                    ),
                    target=Target(area_id="living_room")
                )
            ],
            actions=[HomeIQAction(service="light.turn_on")]
        )
        
        converter = HomeIQToAutomationSpecConverter()
        spec = converter.convert(automation)
        
        assert "target" in spec.trigger[0].extra
        assert spec.trigger[0].extra["target"]["area_id"] == "living_room"
    
    def test_trigger_with_labels_targeting(self):
        """Test trigger with labels targeting."""
        automation = HomeIQAutomation(
            alias="Labels Targeting Test",
            homeiq_metadata=HomeIQMetadata(use_case="security", complexity="low"),
            device_context=DeviceContext(entity_ids=["sensor.motion"]),
            triggers=[
                HomeIQTrigger(
                    platform="state",
                    config=TriggerConfig(
                        parameters={"to": "on"}
                    ),
                    target=Target(labels=["outdoor", "security"])
                )
            ],
            actions=[HomeIQAction(service="light.turn_on")]
        )
        
        converter = HomeIQToAutomationSpecConverter()
        spec = converter.convert(automation)
        
        assert "target" in spec.trigger[0].extra
        assert spec.trigger[0].extra["target"]["labels"] == ["outdoor", "security"]
    
    def test_trigger_with_floor_targeting(self):
        """Test trigger with floor targeting."""
        automation = HomeIQAutomation(
            alias="Floor Targeting Test",
            homeiq_metadata=HomeIQMetadata(use_case="comfort", complexity="low"),
            device_context=DeviceContext(entity_ids=["light.bedroom"]),
            triggers=[
                HomeIQTrigger(
                    platform="state",
                    config=TriggerConfig(
                        parameters={"to": "on"}
                    ),
                    target=Target(floor_id="second_floor")
                )
            ],
            actions=[HomeIQAction(service="light.turn_on")]
        )
        
        converter = HomeIQToAutomationSpecConverter()
        spec = converter.convert(automation)
        
        assert "target" in spec.trigger[0].extra
        assert spec.trigger[0].extra["target"]["floor_id"] == "second_floor"
    
    def test_trigger_with_multiple_targeting(self):
        """Test trigger with multiple targeting options."""
        automation = HomeIQAutomation(
            alias="Multiple Targeting Test",
            homeiq_metadata=HomeIQMetadata(use_case="comfort", complexity="medium"),
            device_context=DeviceContext(entity_ids=["light.living_room"]),
            triggers=[
                HomeIQTrigger(
                    platform="state",
                    config=TriggerConfig(
                        parameters={"to": "on"}
                    ),
                    target=Target(
                        area_id="living_room",
                        floor_id="first_floor",
                        labels=["indoor", "lighting"]
                    )
                )
            ],
            actions=[HomeIQAction(service="light.turn_on")]
        )
        
        converter = HomeIQToAutomationSpecConverter()
        spec = converter.convert(automation)
        
        target = spec.trigger[0].extra["target"]
        assert target["area_id"] == "living_room"
        assert target["floor_id"] == "first_floor"
        assert target["labels"] == ["indoor", "lighting"]
    
    def test_condition_with_targeting(self):
        """Test condition with enhanced targeting."""
        automation = HomeIQAutomation(
            alias="Condition Targeting Test",
            homeiq_metadata=HomeIQMetadata(use_case="comfort", complexity="low"),
            device_context=DeviceContext(entity_ids=["light.living_room"]),
            triggers=[
                HomeIQTrigger(
                    platform="state",
                    config=TriggerConfig(
                        parameters={"to": "on"}
                    )
                )
            ],
            conditions=[
                HomeIQCondition(
                    condition="state",
                    entity_id="light.living_room",
                    state="off",
                    target=Target(area_id="living_room")
                )
            ],
            actions=[HomeIQAction(service="light.turn_on")]
        )
        
        converter = HomeIQToAutomationSpecConverter()
        spec = converter.convert(automation)
        
        assert len(spec.condition) == 1
        assert "target" in spec.condition[0].extra
        assert spec.condition[0].extra["target"]["area_id"] == "living_room"
    
    def test_action_with_targeting(self):
        """Test action with enhanced targeting."""
        automation = HomeIQAutomation(
            alias="Action Targeting Test",
            homeiq_metadata=HomeIQMetadata(use_case="comfort", complexity="low"),
            device_context=DeviceContext(entity_ids=["light.living_room"]),
            triggers=[
                HomeIQTrigger(
                    platform="state",
                    config=TriggerConfig(
                        parameters={"to": "on"}
                    )
                )
            ],
            actions=[
                HomeIQAction(
                    service="light.turn_on",
                    target=Target(area_id="living_room", labels=["lighting"])
                )
            ]
        )
        
        converter = HomeIQToAutomationSpecConverter()
        spec = converter.convert(automation)
        
        assert len(spec.action) == 1
        action = spec.action[0]
        assert action.target is not None
        assert action.target["area_id"] == "living_room"
        assert action.target["labels"] == ["lighting"]


class TestStateTriggers:
    """Test state triggers with new schema format."""
    
    def test_state_trigger_with_to_from(self):
        """Test state trigger with to/from parameters."""
        automation = HomeIQAutomation(
            alias="State Trigger Test",
            homeiq_metadata=HomeIQMetadata(use_case="comfort", complexity="low"),
            device_context=DeviceContext(entity_ids=["light.living_room"]),
            triggers=[
                HomeIQTrigger(
                    platform="state",
                    config=TriggerConfig(
                        entity_id="light.living_room",
                        parameters={
                            "to": "on",
                            "from": "off"
                        }
                    )
                )
            ],
            actions=[HomeIQAction(service="light.turn_on")]
        )
        
        converter = HomeIQToAutomationSpecConverter()
        spec = converter.convert(automation)
        
        assert spec.trigger[0].platform == "state"
        assert spec.trigger[0].extra["entity_id"] == "light.living_room"
        assert spec.trigger[0].extra["to"] == "on"
        assert spec.trigger[0].extra["from"] == "off"
    
    def test_time_trigger(self):
        """Test time trigger with at parameter."""
        automation = HomeIQAutomation(
            alias="Time Trigger Test",
            homeiq_metadata=HomeIQMetadata(use_case="comfort", complexity="low"),
            device_context=DeviceContext(entity_ids=["light.living_room"]),
            triggers=[
                HomeIQTrigger(
                    platform="time",
                    config=TriggerConfig(
                        parameters={"at": "08:00:00"}
                    )
                )
            ],
            actions=[HomeIQAction(service="light.turn_on")]
        )
        
        converter = HomeIQToAutomationSpecConverter()
        spec = converter.convert(automation)
        
        assert spec.trigger[0].platform == "time"
        assert spec.trigger[0].extra["at"] == "08:00:00"


class TestYAMLOutputValidation:
    """Test YAML output format matches HA 2026.1 requirements."""
    
    def test_button_trigger_yaml_output(self):
        """Test button trigger YAML output format."""
        automation = HomeIQAutomation(
            alias="Button YAML Test",
            homeiq_metadata=HomeIQMetadata(use_case="comfort", complexity="low"),
            device_context=DeviceContext(entity_ids=["button.living_room_button"]),
            triggers=[
                HomeIQTrigger(
                    platform="button",
                    config=TriggerConfig(
                        entity_id="button.living_room_button",
                        parameters={"action": "press"}
                    )
                )
            ],
            actions=[HomeIQAction(service="light.turn_on")]
        )
        
        converter = HomeIQToAutomationSpecConverter()
        spec = converter.convert(automation)
        
        renderer = VersionAwareRenderer(ha_version="2026.1.0")
        yaml_content = renderer.render(spec)
        
        assert "platform: button" in yaml_content
        assert "entity_id: button.living_room_button" in yaml_content
        assert "action: press" in yaml_content
    
    def test_enhanced_targeting_yaml_output(self):
        """Test enhanced targeting YAML output format."""
        automation = HomeIQAutomation(
            alias="Enhanced Targeting YAML Test",
            homeiq_metadata=HomeIQMetadata(use_case="comfort", complexity="low"),
            device_context=DeviceContext(entity_ids=["light.living_room"]),
            triggers=[
                HomeIQTrigger(
                    platform="state",
                    config=TriggerConfig(
                        parameters={"to": "on"}
                    ),
                    target=Target(
                        area_id="living_room",
                        labels=["outdoor", "security"]
                    )
                )
            ],
            actions=[HomeIQAction(service="light.turn_on")]
        )
        
        converter = HomeIQToAutomationSpecConverter()
        spec = converter.convert(automation)
        
        renderer = VersionAwareRenderer(ha_version="2026.1.0")
        yaml_content = renderer.render(spec)
        
        assert "target:" in yaml_content
        assert "area_id: living_room" in yaml_content
        assert "labels:" in yaml_content or "- outdoor" in yaml_content
    
    def test_climate_trigger_yaml_output(self):
        """Test climate trigger YAML output format."""
        automation = HomeIQAutomation(
            alias="Climate YAML Test",
            homeiq_metadata=HomeIQMetadata(use_case="comfort", complexity="low"),
            device_context=DeviceContext(entity_ids=["climate.living_room"]),
            triggers=[
                HomeIQTrigger(
                    platform="climate",
                    config=TriggerConfig(
                        entity_id="climate.living_room",
                        parameters={"mode": "heating"}
                    )
                )
            ],
            actions=[HomeIQAction(service="climate.set_temperature")]
        )
        
        converter = HomeIQToAutomationSpecConverter()
        spec = converter.convert(automation)
        
        renderer = VersionAwareRenderer(ha_version="2026.1.0")
        yaml_content = renderer.render(spec)
        
        assert "platform: climate" in yaml_content
        assert "entity_id: climate.living_room" in yaml_content
        assert "mode: heating" in yaml_content
