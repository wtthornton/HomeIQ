"""
Clarification Detector - Detects ambiguities in automation requests
"""

import re
import logging
from typing import List, Dict, Any, Optional
from .models import Ambiguity, AmbiguityType, AmbiguitySeverity

logger = logging.getLogger(__name__)


class ClarificationDetector:
    """Detects ambiguities in automation requests"""
    
    def __init__(self):
        """Initialize clarification detector"""
        pass
    
    async def detect_ambiguities(
        self,
        query: str,
        extracted_entities: List[Dict[str, Any]],
        available_devices: Dict[str, Any],
        automation_context: Optional[Dict[str, Any]] = None
    ) -> List[Ambiguity]:
        """
        Detect ambiguities in query.
        
        Args:
            query: User's natural language query
            extracted_entities: Entities extracted from query
            available_devices: Available devices/entities in system
            automation_context: Additional context (areas, capabilities, etc.)
            
        Returns:
            List of Ambiguity objects with type, severity, and context
        """
        ambiguities = []
        ambiguity_id_counter = 1
        
        # 1. Check device references
        device_ambiguities = await self._detect_device_ambiguities(
            query, extracted_entities, available_devices, ambiguity_id_counter
        )
        ambiguities.extend(device_ambiguities)
        ambiguity_id_counter += len(device_ambiguities)
        
        # 2. Check trigger references
        trigger_ambiguities = await self._detect_trigger_ambiguities(
            query, extracted_entities, automation_context, ambiguity_id_counter
        )
        ambiguities.extend(trigger_ambiguities)
        ambiguity_id_counter += len(trigger_ambiguities)
        
        # 3. Check action clarity
        action_ambiguities = await self._detect_action_ambiguities(
            query, extracted_entities, automation_context, ambiguity_id_counter
        )
        ambiguities.extend(action_ambiguities)
        ambiguity_id_counter += len(action_ambiguities)
        
        # 4. Check timing clarity
        timing_ambiguities = self._detect_timing_ambiguities(
            query, ambiguity_id_counter
        )
        ambiguities.extend(timing_ambiguities)
        ambiguity_id_counter += len(timing_ambiguities)
        
        logger.info(f"🔍 Detected {len(ambiguities)} ambiguities in query")
        return ambiguities
    
    async def _detect_device_ambiguities(
        self,
        query: str,
        extracted_entities: List[Dict[str, Any]],
        available_devices: Dict[str, Any],
        start_id: int
    ) -> List[Ambiguity]:
        """Detect device-related ambiguities"""
        ambiguities = []
        id_counter = start_id
        
        # Extract device mentions from query (case-insensitive)
        query_lower = query.lower()
        
        # Look for device patterns
        device_patterns = [
            r'\b(light|lights|sensor|sensors|switch|switches|device|devices)\b',
            r'\b(office|desk|kitchen|bedroom|living|room)\s+(light|sensor|switch|device)',
        ]
        
        device_mentions = []
        for pattern in device_patterns:
            matches = re.finditer(pattern, query_lower)
            for match in matches:
                device_mentions.append(match.group(0))
        
        # Check for multiple devices matching same mention
        for mention in set(device_mentions):
            # Try to find matching entities
            matching_entities = []
            mention_lower = mention.lower()
            
            # Look for entities that match this mention
            for entity in extracted_entities:
                entity_name = entity.get('name', entity.get('friendly_name', '')).lower()
                entity_id = entity.get('entity_id', '').lower()
                
                if mention_lower in entity_name or mention_lower in entity_id:
                    matching_entities.append(entity)
            
            # Check in available devices
            if isinstance(available_devices, dict):
                for device_id, device_info in available_devices.items():
                    if isinstance(device_info, dict):
                        device_name = device_info.get('friendly_name', device_info.get('name', '')).lower()
                        if mention_lower in device_name:
                            # Create entity-like dict
                            entity_dict = {
                                'entity_id': device_id,
                                'name': device_info.get('friendly_name', device_id),
                                'domain': device_id.split('.')[0] if '.' in device_id else 'unknown'
                            }
                            # Avoid duplicates
                            if not any(e.get('entity_id') == device_id for e in matching_entities):
                                matching_entities.append(entity_dict)
            
            # If multiple matches, create ambiguity
            if len(matching_entities) > 1:
                ambiguities.append(Ambiguity(
                    id=f"amb-{id_counter}",
                    type=AmbiguityType.DEVICE,
                    severity=AmbiguitySeverity.CRITICAL,
                    description=f"Multiple devices match '{mention}' ({len(matching_entities)} found)",
                    context={
                        'mention': mention,
                        'matches': [
                            {
                                'entity_id': e.get('entity_id'),
                                'name': e.get('name', e.get('friendly_name'))
                            }
                            for e in matching_entities
                        ]
                    },
                    related_entities=[e.get('entity_id') for e in matching_entities if e.get('entity_id')],
                    detected_text=mention
                ))
                id_counter += 1
            
            # Check for typos (e.g., "presents" vs "presence")
            if 'present' in mention_lower or 'presence' in mention_lower:
                # Check if any entity actually contains "presence"
                has_presence = any(
                    'presence' in (e.get('entity_id', '') + ' ' + e.get('name', '')).lower()
                    for e in matching_entities
                )
                if not has_presence and 'presents' in mention_lower:
                    ambiguities.append(Ambiguity(
                        id=f"amb-{id_counter}",
                        type=AmbiguityType.DEVICE,
                        severity=AmbiguitySeverity.CRITICAL,
                        description=f"Could not find device matching '{mention}' - did you mean 'presence sensor'?",
                        context={
                            'mention': mention,
                            'suggestion': 'presence sensor',
                            'typo_detected': True
                        },
                        detected_text=mention
                    ))
                    id_counter += 1
        
        # Check for generic device references (e.g., "the light", "the sensor")
        generic_patterns = [
            r'\b(the|a|an)\s+(light|sensor|switch|device)\b',
        ]
        for pattern in generic_patterns:
            if re.search(pattern, query_lower):
                # Check if we have multiple entities of that type
                device_type = re.search(pattern, query_lower).group(2)
                matching_by_type = [
                    e for e in extracted_entities
                    if device_type in e.get('entity_id', '').lower() or
                       device_type in e.get('name', '').lower()
                ]
                
                if len(matching_by_type) > 1:
                    ambiguities.append(Ambiguity(
                        id=f"amb-{id_counter}",
                        type=AmbiguityType.DEVICE,
                        severity=AmbiguitySeverity.IMPORTANT,
                        description=f"Generic reference to '{device_type}' - which one?",
                        context={
                            'device_type': device_type,
                            'matches': [e.get('entity_id') for e in matching_by_type]
                        },
                        related_entities=[e.get('entity_id') for e in matching_by_type if e.get('entity_id')],
                        detected_text=f"the {device_type}"
                    ))
                    id_counter += 1
        
        return ambiguities
    
    async def _detect_trigger_ambiguities(
        self,
        query: str,
        extracted_entities: List[Dict[str, Any]],
        automation_context: Optional[Dict[str, Any]],
        start_id: int
    ) -> List[Ambiguity]:
        """Detect trigger-related ambiguities"""
        ambiguities = []
        id_counter = start_id
        
        query_lower = query.lower()
        
        # Look for trigger patterns
        trigger_keywords = ['when', 'if', 'trigger', 'detect', 'sensor']
        has_trigger = any(keyword in query_lower for keyword in trigger_keywords)
        
        if has_trigger:
            # Check for sensor mentions
            sensor_patterns = [
                r'\b(sensor|motion|presence|door|window|temperature|humidity)\b',
            ]
            
            sensor_mentions = []
            for pattern in sensor_patterns:
                matches = re.finditer(pattern, query_lower)
                for sensor_match in matches:
                    sensor_mentions.append(sensor_match.group(0))
            
            # Check if sensor entities exist
            sensor_entities = [
                e for e in extracted_entities
                if 'sensor' in e.get('entity_id', '').lower() or
                   'binary_sensor' in e.get('entity_id', '').lower()
            ]
            
            if sensor_mentions and not sensor_entities:
                # Sensor mentioned but not found
                ambiguities.append(Ambiguity(
                    id=f"amb-{id_counter}",
                    type=AmbiguityType.TRIGGER,
                    severity=AmbiguitySeverity.CRITICAL,
                    description=f"Sensor mentioned but not found: {', '.join(sensor_mentions)}",
                    context={
                        'mentioned_sensors': sensor_mentions,
                        'suggestion': 'Check sensor names or entity IDs'
                    },
                    detected_text=', '.join(sensor_mentions)
                ))
                id_counter += 1
        
        return ambiguities
    
    async def _detect_action_ambiguities(
        self,
        query: str,
        extracted_entities: List[Dict[str, Any]],
        automation_context: Optional[Dict[str, Any]],
        start_id: int
    ) -> List[Ambiguity]:
        """Detect action-related ambiguities"""
        ambiguities = []
        id_counter = start_id
        
        query_lower = query.lower()
        
        # Check for vague action terms
        vague_actions = {
            'flash': ['fast', 'slow', 'pattern', 'color', 'duration'],
            'show': ['effect', 'pattern', 'animation'],
            'turn': ['on', 'off', 'dim', 'brighten']
        }
        
        for action, required_details in vague_actions.items():
            if action in query_lower:
                # Check if required details are present
                missing_details = [
                    detail for detail in required_details
                    if detail not in query_lower
                ]
                
                if missing_details:
                    ambiguities.append(Ambiguity(
                        id=f"amb-{id_counter}",
                        type=AmbiguityType.ACTION,
                        severity=AmbiguitySeverity.IMPORTANT,
                        description=f"Action '{action}' is vague - missing details: {', '.join(missing_details)}",
                        context={
                            'action': action,
                            'missing_details': missing_details
                        },
                        detected_text=action
                    ))
                    id_counter += 1
        
        return ambiguities
    
    def _detect_timing_ambiguities(
        self,
        query: str,
        start_id: int
    ) -> List[Ambiguity]:
        """Detect timing-related ambiguities"""
        ambiguities = []
        id_counter = start_id
        
        query_lower = query.lower()
        
        # Check for relative timing (e.g., "then", "also", "at the same time")
        relative_timing_keywords = ['then', 'also', 'and', 'after', 'before']
        has_relative_timing = any(keyword in query_lower for keyword in relative_timing_keywords)
        
        if has_relative_timing:
            # Check if timing is explicit
            explicit_timing_patterns = [
                r'\d+\s*(second|minute|hour|sec|min|hr)',
                r'\d+:\d+',  # Time format
                r'at\s+the\s+same\s+time',
                r'simultaneous',
            ]
            
            has_explicit_timing = any(
                re.search(pattern, query_lower) for pattern in explicit_timing_patterns
            )
            
            if not has_explicit_timing:
                ambiguities.append(Ambiguity(
                    id=f"amb-{id_counter}",
                    type=AmbiguityType.TIMING,
                    severity=AmbiguitySeverity.OPTIONAL,
                    description="Timing sequence is unclear - should actions happen simultaneously or sequentially?",
                    context={
                        'relative_timing_detected': True
                    }
                ))
                id_counter += 1
        
        return ambiguities

