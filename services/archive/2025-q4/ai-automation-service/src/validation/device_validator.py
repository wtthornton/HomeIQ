"""
Device Validation Service

Validates that automation suggestions only use devices, entities, and sensors
that actually exist in the Home Assistant system.

This prevents suggestions like "when office window is open" when no window
sensor exists, or "control non-existent light" scenarios.
"""

import logging
from dataclasses import dataclass
from typing import Any

from ..clients.data_api_client import DataAPIClient

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of device/entity validation"""
    is_valid: bool
    missing_devices: list[str]
    missing_entities: list[str]
    missing_sensors: list[str]
    available_alternatives: dict[str, list[str]]
    error_message: str | None = None


class DeviceValidator:
    """
    Validates automation suggestions against actual Home Assistant devices and entities.
    
    This service ensures that:
    1. All referenced devices actually exist
    2. All referenced entities are available
    3. Required sensors exist for trigger conditions
    4. Alternative devices are suggested when possible
    """

    def __init__(self, data_api_client: DataAPIClient):
        self.data_api_client = data_api_client
        self._device_cache: dict[str, Any] | None = None
        self._entity_cache: dict[str, Any] | None = None
        self._sensor_cache: dict[str, Any] | None = None

    async def validate_automation_suggestion(
        self,
        suggestion_text: str,
        suggested_entities: list[str],
        trigger_conditions: list[str]
    ) -> ValidationResult:
        """
        Validate an automation suggestion against actual available devices.
        
        Args:
            suggestion_text: The full text of the automation suggestion
            suggested_entities: List of entity IDs mentioned in the suggestion
            trigger_conditions: List of trigger conditions (e.g., "window open", "presence detected")
        
        Returns:
            ValidationResult with validation status and alternatives
        """
        try:
            # Ensure we have fresh device/entity data
            await self._refresh_caches()

            missing_devices = []
            missing_entities = []
            missing_sensors = []
            available_alternatives = {}

            # Validate each suggested entity
            for entity_id in suggested_entities:
                if not await self._entity_exists(entity_id):
                    missing_entities.append(entity_id)
                    # Find alternatives
                    alternatives = await self._find_entity_alternatives(entity_id)
                    if alternatives:
                        available_alternatives[entity_id] = alternatives

            # Validate trigger conditions against available sensors
            for condition in trigger_conditions:
                required_sensors = self._extract_required_sensors(condition)
                for sensor_type in required_sensors:
                    if not await self._sensor_type_exists(sensor_type):
                        missing_sensors.append(sensor_type)
                        # Find alternatives
                        alternatives = await self._find_sensor_alternatives(sensor_type)
                        if alternatives:
                            available_alternatives[sensor_type] = alternatives

            # Determine overall validity
            is_valid = len(missing_devices) == 0 and len(missing_entities) == 0 and len(missing_sensors) == 0

            error_message = None
            if not is_valid:
                error_parts = []
                if missing_entities:
                    error_parts.append(f"Missing entities: {', '.join(missing_entities)}")
                if missing_sensors:
                    error_parts.append(f"Missing sensors: {', '.join(missing_sensors)}")
                error_message = "; ".join(error_parts)

            return ValidationResult(
                is_valid=is_valid,
                missing_devices=missing_devices,
                missing_entities=missing_entities,
                missing_sensors=missing_sensors,
                available_alternatives=available_alternatives,
                error_message=error_message
            )

        except Exception as e:
            logger.error(f"Device validation failed: {e}")
            return ValidationResult(
                is_valid=False,
                missing_devices=[],
                missing_entities=[],
                missing_sensors=[],
                available_alternatives={},
                error_message=f"Validation error: {str(e)}"
            )

    async def validate_trigger_condition(self, condition: str) -> ValidationResult:
        """
        Validate a specific trigger condition against available sensors.
        
        Args:
            condition: Trigger condition text (e.g., "window open", "presence detected")
        
        Returns:
            ValidationResult for this specific condition
        """
        try:
            await self._refresh_caches()

            required_sensors = self._extract_required_sensors(condition)
            missing_sensors = []
            available_alternatives = {}

            for sensor_type in required_sensors:
                if not await self._sensor_type_exists(sensor_type):
                    missing_sensors.append(sensor_type)
                    alternatives = await self._find_sensor_alternatives(sensor_type)
                    if alternatives:
                        available_alternatives[sensor_type] = alternatives

            is_valid = len(missing_sensors) == 0

            return ValidationResult(
                is_valid=is_valid,
                missing_devices=[],
                missing_entities=[],
                missing_sensors=missing_sensors,
                available_alternatives=available_alternatives,
                error_message=f"Missing sensors: {', '.join(missing_sensors)}" if missing_sensors else None
            )

        except Exception as e:
            logger.error(f"Trigger condition validation failed: {e}")
            return ValidationResult(
                is_valid=False,
                missing_devices=[],
                missing_entities=[],
                missing_sensors=[],
                available_alternatives={},
                error_message=f"Validation error: {str(e)}"
            )

    async def get_available_sensor_types(self) -> dict[str, list[str]]:
        """
        Get all available sensor types organized by category.
        
        Returns:
            Dict mapping sensor categories to lists of available sensor types
        """
        try:
            await self._refresh_caches()

            sensor_types = {
                'presence': [],
                'contact': [],
                'motion': [],
                'door': [],
                'window': [],
                'temperature': [],
                'humidity': [],
                'light': [],
                'binary': [],
                'other': []
            }

            # Categorize all available entities
            for entity in self._entity_cache.values():
                entity_id = entity.get('entity_id', '')
                domain = entity.get('domain', '')

                if domain == 'binary_sensor':
                    if 'presence' in entity_id or 'occupancy' in entity_id:
                        sensor_types['presence'].append(entity_id)
                    elif 'contact' in entity_id or 'door' in entity_id or 'window' in entity_id:
                        sensor_types['contact'].append(entity_id)
                        if 'door' in entity_id:
                            sensor_types['door'].append(entity_id)
                        if 'window' in entity_id:
                            sensor_types['window'].append(entity_id)
                    elif 'motion' in entity_id:
                        sensor_types['motion'].append(entity_id)
                    else:
                        sensor_types['binary'].append(entity_id)

                elif domain == 'sensor':
                    if 'temperature' in entity_id:
                        sensor_types['temperature'].append(entity_id)
                    elif 'humidity' in entity_id:
                        sensor_types['humidity'].append(entity_id)
                    elif 'light' in entity_id or 'luminance' in entity_id:
                        sensor_types['light'].append(entity_id)
                    else:
                        sensor_types['other'].append(entity_id)

                elif domain == 'light':
                    sensor_types['light'].append(entity_id)

            return sensor_types

        except Exception as e:
            logger.error(f"Failed to get available sensor types: {e}")
            return {}

    # Private helper methods

    async def _refresh_caches(self):
        """Refresh device and entity caches from Home Assistant"""
        try:
            # Fetch all entities
            entities = await self.data_api_client.fetch_entities(limit=1000)
            self._entity_cache = {entity['entity_id']: entity for entity in entities}

            # Fetch all devices
            devices = await self.data_api_client.fetch_devices(limit=1000)
            self._device_cache = {device['device_id']: device for device in devices}

            logger.debug(f"Refreshed caches: {len(self._entity_cache)} entities, {len(self._device_cache)} devices")

        except Exception as e:
            logger.error(f"Failed to refresh caches: {e}")
            self._entity_cache = {}
            self._device_cache = {}

    async def _entity_exists(self, entity_id: str) -> bool:
        """Check if an entity exists"""
        if not self._entity_cache:
            await self._refresh_caches()
        return entity_id in self._entity_cache

    async def _sensor_type_exists(self, sensor_type: str) -> bool:
        """Check if sensors of a given type exist"""
        if not self._entity_cache:
            await self._refresh_caches()

        # Map sensor type names to entity patterns
        sensor_patterns = {
            'window': ['window', 'contact'],
            'door': ['door', 'contact'],
            'presence': ['presence', 'occupancy'],
            'motion': ['motion', 'pir'],
            'temperature': ['temperature', 'temp'],
            'humidity': ['humidity', 'moisture'],
            'light': ['light', 'luminance', 'lux'],
            'contact': ['contact']
        }

        patterns = sensor_patterns.get(sensor_type.lower(), [sensor_type])

        for entity_id, entity_data in self._entity_cache.items():
            entity_domain = entity_data.get('domain', '')
            if entity_domain in ['binary_sensor', 'sensor']:
                for pattern in patterns:
                    if pattern in entity_id.lower():
                        return True

        return False

    def _extract_required_sensors(self, condition: str) -> list[str]:
        """Extract required sensor types from a trigger condition"""
        condition_lower = condition.lower()
        required_sensors = []

        # Window-related conditions
        if any(word in condition_lower for word in ['window', 'open', 'closed']):
            required_sensors.append('window')

        # Door-related conditions
        if any(word in condition_lower for word in ['door', 'opened', 'closed']):
            required_sensors.append('door')

        # Presence-related conditions
        if any(word in condition_lower for word in ['presence', 'occupancy', 'detected', 'someone']):
            required_sensors.append('presence')

        # Motion-related conditions
        if any(word in condition_lower for word in ['motion', 'movement', 'moving']):
            required_sensors.append('motion')

        # Temperature-related conditions
        if any(word in condition_lower for word in ['temperature', 'temp', 'hot', 'cold']):
            required_sensors.append('temperature')

        # Light-related conditions
        if any(word in condition_lower for word in ['light', 'bright', 'dark', 'luminance']):
            required_sensors.append('light')

        return required_sensors

    async def _find_entity_alternatives(self, entity_id: str) -> list[str]:
        """Find alternative entities similar to the requested one"""
        if not self._entity_cache:
            await self._refresh_caches()

        alternatives = []
        entity_domain = entity_id.split('.')[0] if '.' in entity_id else ''
        entity_name = entity_id.split('.')[1] if '.' in entity_id else entity_id

        # Look for entities with similar names or same domain
        for cached_entity_id, entity_data in self._entity_cache.items():
            cached_domain = entity_data.get('domain', '')
            if cached_domain == entity_domain:
                alternatives.append(cached_entity_id)

        return alternatives[:5]  # Limit to 5 alternatives

    async def _find_sensor_alternatives(self, sensor_type: str) -> list[str]:
        """Find alternative sensors of the requested type"""
        if not self._entity_cache:
            await self._refresh_caches()

        alternatives = []
        sensor_patterns = {
            'window': ['window', 'contact'],
            'door': ['door', 'contact'],
            'presence': ['presence', 'occupancy'],
            'motion': ['motion', 'pir'],
            'temperature': ['temperature', 'temp'],
            'humidity': ['humidity', 'moisture'],
            'light': ['light', 'luminance', 'lux'],
            'contact': ['contact']
        }

        patterns = sensor_patterns.get(sensor_type.lower(), [sensor_type])

        for entity_id, entity_data in self._entity_cache.items():
            entity_domain = entity_data.get('domain', '')
            if entity_domain in ['binary_sensor', 'sensor']:
                for pattern in patterns:
                    if pattern in entity_id.lower():
                        alternatives.append(entity_id)

        return alternatives[:5]  # Limit to 5 alternatives
