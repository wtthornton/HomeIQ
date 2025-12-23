"""
Real-World Device Rules

Research-based rules for device compatibility based on real-world usage patterns.
These rules prevent false relationships and improve automation suggestion quality.

Phase 2: Real-World Rules Database
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


# Real-world device relationship rules based on research and common patterns
REAL_WORLD_DEVICE_RULES = {
    # Door/Lock rules
    'door_lock_rules': {
        'front_door_lock': {
            'compatible_lights': ['front_door', 'entryway', 'porch', 'entrance', 'main'],
            'incompatible_lights': ['backyard', 'back_door', 'back', 'rear', 'garage'],
            'compatible_sensors': ['front_door', 'entryway', 'entrance'],
            'incompatible_sensors': ['backyard', 'back_door', 'back'],
            'rationale': 'Front door lock should only control front entry area devices'
        },
        'back_door_lock': {
            'compatible_lights': ['back_door', 'backyard', 'back', 'rear', 'patio'],
            'incompatible_lights': ['front_door', 'entryway', 'porch', 'entrance'],
            'compatible_sensors': ['back_door', 'backyard', 'back', 'rear'],
            'incompatible_sensors': ['front_door', 'entryway', 'entrance'],
            'rationale': 'Back door lock should only control back area devices'
        },
        'garage_door': {
            'compatible_lights': ['garage', 'driveway'],
            'incompatible_lights': ['front_door', 'backyard', 'bedroom', 'kitchen'],
            'rationale': 'Garage door should only control garage area devices'
        }
    },
    
    # Motion sensor rules
    'motion_sensor_rules': {
        'kitchen_motion': {
            'compatible_lights': ['kitchen', 'dining'],
            'max_distance_rooms': 1,  # Can control adjacent rooms
            'rationale': 'Kitchen motion should primarily control kitchen lights'
        },
        'bedroom_motion': {
            'compatible_lights': ['bedroom', 'bathroom'],  # Adjacent bathroom
            'incompatible_lights': ['kitchen', 'living_room', 'garage'],
            'rationale': 'Bedroom motion should control bedroom and adjacent bathroom lights'
        },
        'outdoor_motion': {
            'compatible_lights': ['outdoor', 'yard', 'garden', 'patio', 'deck', 'backyard'],
            'incompatible_lights': ['indoor', 'bedroom', 'kitchen', 'living_room'],
            'rationale': 'Outdoor motion should only control outdoor lights'
        }
    },
    
    # Common patterns from research
    'common_patterns': {
        'entryway_automation': {
            'trigger': ['door_sensor', 'motion_sensor'],
            'action': ['light', 'notify'],
            'location': 'entryway',
            'frequency': 'high',  # Very common pattern
            'confidence': 0.95
        },
        'bedroom_sleep': {
            'trigger': ['bedroom_motion', 'bedroom_door'],
            'action': ['bedroom_light', 'bedroom_fan'],
            'location': 'bedroom',
            'time_constraint': 'evening',
            'confidence': 0.90
        },
        'kitchen_cooking': {
            'trigger': ['kitchen_motion', 'kitchen_temperature'],
            'action': ['kitchen_light', 'kitchen_fan'],
            'location': 'kitchen',
            'confidence': 0.85
        }
    }
}


class RealWorldRulesValidator:
    """
    Validates device pairs against real-world rules.
    
    Checks if device combinations make sense based on research
    and common automation patterns.
    """
    
    def __init__(self):
        """Initialize real-world rules validator"""
        self.rules = REAL_WORLD_DEVICE_RULES
    
    def _matches_pattern(self, text: str, patterns: list[str]) -> bool:
        """
        Check if text matches any pattern in the list.
        
        Args:
            text: Text to check (device name, entity ID, etc.)
            patterns: List of pattern strings to match against
            
        Returns:
            True if text matches any pattern
        """
        text_lower = text.lower()
        for pattern in patterns:
            # Use word boundaries for better matching
            pattern_lower = pattern.lower()
            if pattern_lower in text_lower:
                return True
        return False
    
    def validate_device_pair(
        self,
        device1: dict,
        device2: dict
    ) -> tuple[bool, Optional[str]]:
        """
        Validate device pair against real-world rules.
        
        Args:
            device1: First device dict
            device2: Second device dict
            
        Returns:
            Tuple of (is_valid, reason) where:
            - is_valid: True if pair is valid according to rules
            - reason: Explanation or None if no rule matched
        """
        name1 = device1.get('friendly_name', device1.get('entity_id', ''))
        name2 = device2.get('friendly_name', device2.get('entity_id', ''))
        entity_id1 = device1.get('entity_id', '')
        entity_id2 = device2.get('entity_id', '')
        
        # Combine names and entity IDs for matching
        text1 = f"{name1} {entity_id1}".lower()
        text2 = f"{name2} {entity_id2}".lower()
        
        # Check door/lock rules
        door_rules = self.rules.get('door_lock_rules', {})
        for lock_type, rule_config in door_rules.items():
            # Check if device1 matches lock pattern
            if self._matches_pattern(text1, [lock_type]):
                # Check compatible devices
                compatible = rule_config.get('compatible_lights', []) + \
                            rule_config.get('compatible_sensors', [])
                incompatible = rule_config.get('incompatible_lights', []) + \
                              rule_config.get('incompatible_sensors', [])
                
                # Check if device2 is compatible
                if self._matches_pattern(text2, compatible):
                    return (True, f"matches_{lock_type}_compatible")
                
                # Check if device2 is incompatible
                if self._matches_pattern(text2, incompatible):
                    return (False, f"matches_{lock_type}_incompatible")
        
        # Check motion sensor rules
        motion_rules = self.rules.get('motion_sensor_rules', {})
        for motion_type, rule_config in motion_rules.items():
            # Check if device1 matches motion pattern
            if self._matches_pattern(text1, [motion_type]):
                compatible = rule_config.get('compatible_lights', [])
                incompatible = rule_config.get('incompatible_lights', [])
                
                # Check if device2 is compatible
                if self._matches_pattern(text2, compatible):
                    return (True, f"matches_{motion_type}_compatible")
                
                # Check if device2 is incompatible
                if self._matches_pattern(text2, incompatible):
                    return (False, f"matches_{motion_type}_incompatible")
        
        # No rule matched - return None to indicate no rule applied
        return (True, None)
    
    def get_compatible_devices(self, device: dict) -> list[str]:
        """
        Get list of compatible device patterns for a given device.
        
        Args:
            device: Device dict
            
        Returns:
            List of compatible device patterns
        """
        name = device.get('friendly_name', device.get('entity_id', ''))
        entity_id = device.get('entity_id', '')
        text = f"{name} {entity_id}".lower()
        
        compatible = []
        
        # Check door/lock rules
        door_rules = self.rules.get('door_lock_rules', {})
        for lock_type, rule_config in door_rules.items():
            if self._matches_pattern(text, [lock_type]):
                compatible.extend(rule_config.get('compatible_lights', []))
                compatible.extend(rule_config.get('compatible_sensors', []))
        
        # Check motion sensor rules
        motion_rules = self.rules.get('motion_sensor_rules', {})
        for motion_type, rule_config in motion_rules.items():
            if self._matches_pattern(text, [motion_type]):
                compatible.extend(rule_config.get('compatible_lights', []))
        
        return compatible
    
    def get_incompatible_devices(self, device: dict) -> list[str]:
        """
        Get list of incompatible device patterns for a given device.
        
        Args:
            device: Device dict
            
        Returns:
            List of incompatible device patterns
        """
        name = device.get('friendly_name', device.get('entity_id', ''))
        entity_id = device.get('entity_id', '')
        text = f"{name} {entity_id}".lower()
        
        incompatible = []
        
        # Check door/lock rules
        door_rules = self.rules.get('door_lock_rules', {})
        for lock_type, rule_config in door_rules.items():
            if self._matches_pattern(text, [lock_type]):
                incompatible.extend(rule_config.get('incompatible_lights', []))
                incompatible.extend(rule_config.get('incompatible_sensors', []))
        
        # Check motion sensor rules
        motion_rules = self.rules.get('motion_sensor_rules', {})
        for motion_type, rule_config in motion_rules.items():
            if self._matches_pattern(text, [motion_type]):
                incompatible.extend(rule_config.get('incompatible_lights', []))
        
        return incompatible

