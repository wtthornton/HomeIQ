"""
Synthetic Automation Generator

Generate automations for synthetic homes using blueprint templates.
"""

import logging
import random
from typing import Any
from .automation_templates import BLUEPRINT_TEMPLATES, BlueprintTemplate

logger = logging.getLogger(__name__)


class SyntheticAutomationGenerator:
    """
    Generate automations for synthetic homes using blueprint templates.
    
    Creates realistic automation patterns that match common Home Assistant use cases.
    """
    
    def __init__(self):
        """Initialize automation generator."""
        logger.info("SyntheticAutomationGenerator initialized")
    
    def generate_automations(
        self,
        devices: list[dict[str, Any]],
        areas: list[dict[str, Any]] | None = None
    ) -> list[dict[str, Any]]:
        """
        Generate automations for a synthetic home based on available devices.
        
        Args:
            devices: List of device dictionaries
            areas: Optional list of area dictionaries
        
        Returns:
            List of automation dictionaries
        """
        automations = []
        
        # Group devices by type for template matching
        devices_by_type = self._group_devices_by_type(devices)
        
        # Try to generate automations for each template
        for template_id, template in BLUEPRINT_TEMPLATES.items():
            # Check if we have required devices for this template
            if self._can_generate_template(template, devices_by_type):
                # Generate automation(s) for this template
                template_automations = self._generate_from_template(
                    template=template,
                    devices=devices,
                    devices_by_type=devices_by_type,
                    areas=areas
                )
                automations.extend(template_automations)
        
        logger.info(f"✅ Generated {len(automations)} automations from {len(BLUEPRINT_TEMPLATES)} templates")
        return automations
    
    def _group_devices_by_type(
        self,
        devices: list[dict[str, Any]]
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Group devices by device type.
        
        Args:
            devices: List of device dictionaries
        
        Returns:
            Dictionary mapping device types to device lists
        """
        grouped: dict[str, list[dict[str, Any]]] = {}
        
        for device in devices:
            device_type = device.get('device_type', 'unknown')
            device_class = device.get('device_class')
            
            # Create composite key for sensors
            if device_type in ['sensor', 'binary_sensor'] and device_class:
                key = f"{device_type}.{device_class}"
            else:
                key = device_type
            
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(device)
        
        return grouped
    
    def _can_generate_template(
        self,
        template: BlueprintTemplate,
        devices_by_type: dict[str, list[dict[str, Any]]]
    ) -> bool:
        """
        Check if we can generate an automation from this template.
        
        Args:
            template: Blueprint template
            devices_by_type: Devices grouped by type
        
        Returns:
            True if template can be generated
        """
        # Check if all required device types are present
        for required_type in template.required_device_types:
            if required_type not in devices_by_type or len(devices_by_type[required_type]) == 0:
                return False
        
        return True
    
    def _generate_from_template(
        self,
        template: BlueprintTemplate,
        devices: list[dict[str, Any]],
        devices_by_type: dict[str, list[dict[str, Any]]],
        areas: list[dict[str, Any]] | None = None
    ) -> list[dict[str, Any]]:
        """
        Generate automation(s) from a template.
        
        Args:
            template: Blueprint template
            devices: All devices
            devices_by_type: Devices grouped by type
            areas: Optional areas
        
        Returns:
            List of automation dictionaries
        """
        automations = []
        
        # Get required devices
        required_devices = {}
        for device_type in template.required_device_types:
            available = devices_by_type.get(device_type, [])
            if available:
                required_devices[device_type] = random.choice(available)
        
        # Generate automation based on template type
        if template.template_id == 'motion_activated_light':
            automation = self._generate_motion_light_automation(
                template, required_devices, areas
            )
            if automation:
                automations.append(automation)
        
        elif template.template_id == 'climate_comfort':
            automation = self._generate_climate_automation(
                template, required_devices, areas
            )
            if automation:
                automations.append(automation)
        
        elif template.template_id == 'security_alert':
            automation = self._generate_security_automation(
                template, required_devices, areas
            )
            if automation:
                automations.append(automation)
        
        elif template.template_id == 'energy_optimization':
            automation = self._generate_energy_automation(
                template, required_devices, areas
            )
            if automation:
                automations.append(automation)
        
        elif template.template_id == 'voice_routine':
            automation = self._generate_voice_routine_automation(
                template, required_devices, areas
            )
            if automation:
                automations.append(automation)
        
        return automations
    
    def _generate_motion_light_automation(
        self,
        template: BlueprintTemplate,
        required_devices: dict[str, dict[str, Any]],
        areas: list[dict[str, Any]] | None
    ) -> dict[str, Any] | None:
        """Generate motion-activated light automation."""
        motion_sensor = required_devices.get('binary_sensor.motion')
        light = required_devices.get('light')
        
        if not motion_sensor or not light:
            return None
        
        automation_id = f"automation.{motion_sensor.get('area', 'unknown').lower().replace(' ', '_')}_motion_light"
        
        return {
            'automation_id': automation_id,
            'template_id': template.template_id,
            'name': f"{motion_sensor.get('area', 'Unknown')} Motion Light",
            'description': template.description,
            'trigger': {
                'platform': 'state',
                'entity_id': motion_sensor.get('entity_id'),
                'to': 'on'
            },
            'condition': {
                'condition': 'time',
                'after': 'sunset',
                'before': 'sunrise'
            },
            'action': {
                'service': 'light.turn_on',
                'entity_id': light.get('entity_id'),
                'data': {
                    'brightness_pct': 50
                }
            },
            'delay': {
                'minutes': template.metadata.get('typical_delay_minutes', 5)
            },
            'turn_off_action': {
                'service': 'light.turn_off',
                'entity_id': light.get('entity_id')
            },
            'area': motion_sensor.get('area'),
            'devices_involved': [
                motion_sensor.get('entity_id'),
                light.get('entity_id')
            ]
        }
    
    def _generate_climate_automation(
        self,
        template: BlueprintTemplate,
        required_devices: dict[str, dict[str, Any]],
        areas: list[dict[str, Any]] | None
    ) -> dict[str, Any] | None:
        """Generate climate comfort automation."""
        temp_sensor = required_devices.get('sensor.temperature')
        climate = required_devices.get('climate')
        
        if not temp_sensor or not climate:
            return None
        
        automation_id = f"automation.{temp_sensor.get('area', 'unknown').lower().replace(' ', '_')}_climate"
        temp_range = template.metadata.get('typical_temperature_range', (65, 75))
        
        return {
            'automation_id': automation_id,
            'template_id': template.template_id,
            'name': f"{temp_sensor.get('area', 'Unknown')} Climate Control",
            'description': template.description,
            'trigger': {
                'platform': 'state',
                'entity_id': temp_sensor.get('entity_id'),
                'for': {'minutes': 5}
            },
            'condition': {
                'condition': 'numeric_state',
                'entity_id': temp_sensor.get('entity_id'),
                'below': temp_range[1],
                'above': temp_range[0]
            },
            'action': {
                'service': 'climate.set_temperature',
                'entity_id': climate.get('entity_id'),
                'data': {
                    'temperature': (temp_range[0] + temp_range[1]) / 2
                }
            },
            'area': temp_sensor.get('area'),
            'devices_involved': [
                temp_sensor.get('entity_id'),
                climate.get('entity_id')
            ]
        }
    
    def _generate_security_automation(
        self,
        template: BlueprintTemplate,
        required_devices: dict[str, dict[str, Any]],
        areas: list[dict[str, Any]] | None
    ) -> dict[str, Any] | None:
        """Generate security alert automation."""
        door_sensor = required_devices.get('binary_sensor.door')
        window_sensor = required_devices.get('binary_sensor.window')
        alarm = required_devices.get('alarm_control_panel')
        
        # Need at least one sensor and alarm
        sensor = door_sensor or window_sensor
        if not sensor or not alarm:
            return None
        
        automation_id = f"automation.{sensor.get('area', 'unknown').lower().replace(' ', '_')}_security"
        
        return {
            'automation_id': automation_id,
            'template_id': template.template_id,
            'name': f"{sensor.get('area', 'Unknown')} Security Alert",
            'description': template.description,
            'trigger': {
                'platform': 'state',
                'entity_id': sensor.get('entity_id'),
                'to': 'on'
            },
            'condition': {
                'condition': 'state',
                'entity_id': alarm.get('entity_id'),
                'state': 'armed_away'
            },
            'action': {
                'service': 'notify.mobile_app',
                'data': {
                    'message': f"Security alert: {sensor.get('friendly_name', 'Sensor')} triggered",
                    'title': 'Security Alert'
                }
            },
            'area': sensor.get('area'),
            'devices_involved': [
                sensor.get('entity_id'),
                alarm.get('entity_id')
            ]
        }
    
    def _generate_energy_automation(
        self,
        template: BlueprintTemplate,
        required_devices: dict[str, dict[str, Any]],
        areas: list[dict[str, Any]] | None
    ) -> dict[str, Any] | None:
        """Generate energy optimization automation."""
        energy_sensor = required_devices.get('sensor.energy')
        switch = required_devices.get('switch')
        
        if not energy_sensor or not switch:
            return None
        
        automation_id = f"automation.{energy_sensor.get('area', 'unknown').lower().replace(' ', '_')}_energy"
        
        return {
            'automation_id': automation_id,
            'template_id': template.template_id,
            'name': f"{energy_sensor.get('area', 'Unknown')} Energy Optimization",
            'description': template.description,
            'trigger': {
                'platform': 'time',
                'at': '22:00:00'  # 10 PM
            },
            'condition': {
                'condition': 'time',
                'after': '22:00:00',
                'before': '06:00:00'
            },
            'action': {
                'service': 'switch.turn_off',
                'entity_id': switch.get('entity_id')
            },
            'area': energy_sensor.get('area'),
            'devices_involved': [
                energy_sensor.get('entity_id'),
                switch.get('entity_id')
            ]
        }
    
    def _generate_voice_routine_automation(
        self,
        template: BlueprintTemplate,
        required_devices: dict[str, dict[str, Any]],
        areas: list[dict[str, Any]] | None
    ) -> dict[str, Any] | None:
        """Generate voice routine automation."""
        light = required_devices.get('light')
        switch = required_devices.get('switch')
        
        # Need at least one device
        device = light or switch
        if not device:
            return None
        
        automation_id = f"automation.{device.get('area', 'unknown').lower().replace(' ', '_')}_voice_routine"
        platform = random.choice(template.metadata.get('voice_platforms', ['alexa']))
        
        return {
            'automation_id': automation_id,
            'template_id': template.template_id,
            'name': f"{device.get('area', 'Unknown')} Voice Routine",
            'description': template.description,
            'trigger': {
                'platform': 'event',
                'event_type': 'voice_command',
                'event_data': {
                    'platform': platform,
                    'command': 'turn on lights'
                }
            },
            'condition': None,
            'action': {
                'service': 'light.turn_on' if light else 'switch.turn_on',
                'entity_id': device.get('entity_id')
            },
            'area': device.get('area'),
            'devices_involved': [device.get('entity_id')],
            'voice_platform': platform
        }

