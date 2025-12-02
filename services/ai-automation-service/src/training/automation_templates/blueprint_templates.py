"""
Blueprint Automation Templates

Templates for generating realistic Home Assistant automation patterns in synthetic homes.
"""

from typing import Any
from dataclasses import dataclass


@dataclass
class BlueprintTemplate:
    """Blueprint automation template definition."""
    template_id: str
    name: str
    description: str
    trigger_type: str
    condition_type: str | None
    action_type: str
    required_device_types: list[str]
    optional_device_types: list[str]
    metadata: dict[str, Any]


# Blueprint automation templates (Epic AI-11)
BLUEPRINT_TEMPLATES: dict[str, BlueprintTemplate] = {
    'motion_activated_light': BlueprintTemplate(
        template_id='motion_activated_light',
        name='Motion-Activated Light',
        description='Turn on lights when motion is detected, turn off after delay',
        trigger_type='state',
        condition_type='time',  # Only during certain hours
        action_type='light_control',
        required_device_types=['binary_sensor.motion', 'light'],
        optional_device_types=['sensor.brightness'],
        metadata={
            'common_pattern': True,
            'energy_efficient': True,
            'use_case': 'convenience',
            'typical_delay_minutes': 5
        }
    ),
    
    'climate_comfort': BlueprintTemplate(
        template_id='climate_comfort',
        name='Climate Comfort Automation',
        description='Adjust climate based on temperature and time of day',
        trigger_type='state',
        condition_type='time_and_temperature',
        action_type='climate_control',
        required_device_types=['sensor.temperature', 'climate'],
        optional_device_types=['sensor.humidity', 'binary_sensor.presence'],
        metadata={
            'common_pattern': True,
            'energy_efficient': True,
            'use_case': 'comfort',
            'typical_temperature_range': (65, 75)
        }
    ),
    
    'security_alert': BlueprintTemplate(
        template_id='security_alert',
        name='Security Alert Automation',
        description='Trigger alerts when security sensors detect activity',
        trigger_type='state',
        condition_type='presence',  # Only when away
        action_type='notification',
        required_device_types=['binary_sensor.door', 'binary_sensor.window', 'alarm_control_panel'],
        optional_device_types=['camera', 'light', 'siren'],
        metadata={
            'common_pattern': True,
            'energy_efficient': False,
            'use_case': 'security',
            'alert_types': ['notification', 'light_flash', 'siren']
        }
    ),
    
    'energy_optimization': BlueprintTemplate(
        template_id='energy_optimization',
        name='Energy Optimization Automation',
        description='Optimize energy usage based on time, presence, and carbon intensity',
        trigger_type='time',
        condition_type='energy_aware',
        action_type='energy_control',
        required_device_types=['sensor.energy', 'switch'],
        optional_device_types=['sensor.carbon_intensity', 'binary_sensor.presence'],
        metadata={
            'common_pattern': True,
            'energy_efficient': True,
            'use_case': 'energy_saving',
            'optimization_factors': ['time', 'carbon_intensity', 'presence']
        }
    ),
    
    'voice_routine': BlueprintTemplate(
        template_id='voice_routine',
        name='Voice Routine Automation',
        description='Execute multiple actions triggered by voice command',
        trigger_type='voice',
        condition_type=None,
        action_type='multi_action',
        required_device_types=['light', 'switch'],
        optional_device_types=['scene', 'climate', 'media_player'],
        metadata={
            'common_pattern': True,
            'energy_efficient': False,
            'use_case': 'convenience',
            'voice_platforms': ['alexa', 'google_assistant', 'assist'],
            'typical_actions': ['lights', 'climate', 'scenes']
        }
    )
}

