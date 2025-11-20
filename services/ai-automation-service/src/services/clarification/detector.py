"""
Clarification Detector - Detects ambiguities in automation requests
"""

import logging
import re
from typing import Any

from .models import Ambiguity, AmbiguitySeverity, AmbiguityType

logger = logging.getLogger(__name__)


class ClarificationDetector:
    """Detects ambiguities in automation requests"""

    def __init__(self, rag_client=None):
        """
        Initialize clarification detector.
        
        Args:
            rag_client: Optional RAG client for semantic similarity lookup.
                       If provided, will use semantic search to reduce false positives.
        """
        self.rag_client = rag_client
        if rag_client:
            logger.info("ClarificationDetector initialized with RAG client (semantic understanding enabled)")
        else:
            logger.info("ClarificationDetector initialized without RAG client (using hardcoded rules only)")

    async def detect_ambiguities(
        self,
        query: str,
        extracted_entities: list[dict[str, Any]],
        available_devices: dict[str, Any],
        automation_context: dict[str, Any] | None = None
    ) -> list[Ambiguity]:
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
        extracted_entities: list[dict[str, Any]],
        available_devices: dict[str, Any],
        start_id: int
    ) -> list[Ambiguity]:
        """Detect device-related ambiguities"""
        ambiguities = []
        id_counter = start_id

        # Extract device mentions from query (case-insensitive)
        query_lower = query.lower()

        # Extract location mentions from query (e.g., "in my office", "in the kitchen")
        location_patterns = [
            # Pattern 1: "in my office", "at the kitchen", "of the bedroom"
            r'\b(in|at|of)\s+(?:my|the|a|an)?\s*(\w+(?:\s+\w+)?)',
            # Pattern 2: Direct location mentions (office, kitchen, etc.)
            r'\b(office|desk|kitchen|bedroom|living\s+room|bathroom|garage|outdoor|outside|hallway|basement|attic)\b',
        ]

        mentioned_locations = []
        for pattern in location_patterns:
            matches = re.finditer(pattern, query_lower)
            for match in matches:
                # Extract location from match (group 2 if exists, otherwise group 0)
                if match.lastindex and match.lastindex >= 2:
                    location = match.group(2)
                else:
                    location = match.group(0)

                # Clean up location (remove "in", "at", "of", "my", "the", etc.)
                location = re.sub(r'^(in|at|of|my|the|a|an)\s+', '', location, flags=re.IGNORECASE).strip()
                # Remove trailing "room", "area", "space" if present
                location = re.sub(r'\s+(room|area|space)$', '', location, flags=re.IGNORECASE).strip()

                if location and len(location) > 1 and location not in mentioned_locations:
                    mentioned_locations.append(location.lower())

        # Extract area entities from extracted entities
        area_entities = [e for e in extracted_entities if e.get('type') == 'area']
        mentioned_areas = [e.get('name', '').lower() for e in area_entities if e.get('name')]
        mentioned_areas.extend(mentioned_locations)
        mentioned_areas = list(set(mentioned_areas))  # Deduplicate

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
                # Build device lookup map for enriching entities with device names
                devices_list = available_devices.get('devices', [])
                device_map = {}
                if isinstance(devices_list, list):
                    for device_info in devices_list:
                        if isinstance(device_info, dict):
                            device_id = device_info.get('device_id', device_info.get('id', ''))
                            device_name = device_info.get('name', device_info.get('friendly_name', ''))
                            if device_id and device_name:
                                device_map[device_id] = device_name

                # Check entities list (from DataFrame.to_dict('records'))
                entities_list = available_devices.get('entities', [])
                if isinstance(entities_list, list):
                    for entity_info in entities_list:
                        if isinstance(entity_info, dict):
                            entity_id = entity_info.get('entity_id', '')
                            entity_name = entity_info.get('friendly_name', entity_info.get('name', '') or '')

                            # If entity name is empty, try to get device name
                            if not entity_name:
                                device_id = entity_info.get('device_id', '')
                                if device_id and device_id in device_map:
                                    entity_name = device_map[device_id]

                            entity_name_lower = entity_name.lower()
                            entity_id_lower = entity_id.lower()
                            # Check both name and entity_id (fallback to entity_id if name is empty)
                            if entity_id and (mention_lower in entity_name_lower or mention_lower in entity_id_lower):
                                # Use device name if available, otherwise fallback to entity_id
                                display_name = entity_name if entity_name else entity_id
                                # Create entity-like dict with area info
                                entity_dict = {
                                    'entity_id': entity_id,
                                    'name': display_name,
                                    'domain': entity_id.split('.')[0] if '.' in entity_id else 'unknown',
                                    'area_id': entity_info.get('area_id', entity_info.get('area', '')),
                                    'device_area_id': entity_info.get('device_area_id', '')
                                }
                                # Avoid duplicates
                                if not any(e.get('entity_id') == entity_id for e in matching_entities):
                                    matching_entities.append(entity_dict)

                # Also check entities_by_domain (has area info)
                entities_by_domain = available_devices.get('entities_by_domain', {})
                if isinstance(entities_by_domain, dict):
                    for domain, domain_entities in entities_by_domain.items():
                        if isinstance(domain_entities, list):
                            for entity_info in domain_entities:
                                if isinstance(entity_info, dict):
                                    entity_id = entity_info.get('entity_id', '')
                                    entity_name = entity_info.get('friendly_name', entity_info.get('name', '') or '')

                                    # If entity name is empty, try to get device name
                                    if not entity_name:
                                        device_id = entity_info.get('device_id', '')
                                        if device_id and device_id in device_map:
                                            entity_name = device_map[device_id]

                                    entity_name_lower = entity_name.lower()
                                    entity_id_lower = entity_id.lower()
                                    # Check both name and entity_id (fallback to entity_id if name is empty)
                                    if entity_id and (mention_lower in entity_name_lower or mention_lower in entity_id_lower):
                                        # Use device name if available, otherwise fallback to entity_id
                                        display_name = entity_name if entity_name else entity_id
                                        # Create entity-like dict with area info
                                        entity_dict = {
                                            'entity_id': entity_id,
                                            'name': display_name,
                                            'domain': domain,
                                            'area_id': entity_info.get('area', entity_info.get('area_id', '')),
                                            'device_area_id': entity_info.get('device_area_id', '')
                                        }
                                        # Avoid duplicates
                                        if not any(e.get('entity_id') == entity_id for e in matching_entities):
                                            matching_entities.append(entity_dict)

                # Check devices list (from DataFrame.to_dict('records'))
                devices_list = available_devices.get('devices', [])
                if isinstance(devices_list, list):
                    for device_info in devices_list:
                        if isinstance(device_info, dict):
                            device_id = device_info.get('device_id', device_info.get('id', ''))
                            device_name = device_info.get('friendly_name', device_info.get('name', '')).lower()
                            if mention_lower in device_name and device_id:
                                # Create entity-like dict
                                entity_dict = {
                                    'entity_id': device_id,
                                    'name': device_info.get('friendly_name', device_id),
                                    'domain': 'device',
                                    'area_id': device_info.get('area_id', ''),
                                    'device_area_id': device_info.get('area_id', '')
                                }
                                # Avoid duplicates
                                if not any(e.get('entity_id') == device_id for e in matching_entities):
                                    matching_entities.append(entity_dict)

            # NEW: Check for location mismatches
            if mentioned_areas and matching_entities:
                location_mismatches = []
                for entity in matching_entities:
                    # Get entity area (try multiple fields)
                    entity_area = (
                        entity.get('area_id', '') or
                        entity.get('device_area_id', '') or
                        entity.get('area_name', '') or
                        entity.get('area', '')
                    ).lower()

                    # Check if entity area matches any mentioned location
                    area_matches = False
                    for mentioned_area in mentioned_areas:
                        # Normalize area names (remove common words, handle partial matches)
                        normalized_mentioned = re.sub(r'\b(room|area|space)\b', '', mentioned_area).strip()
                        normalized_entity = re.sub(r'\b(room|area|space)\b', '', entity_area).strip()

                        if (mentioned_area in entity_area or
                            entity_area in mentioned_area or
                            normalized_mentioned in normalized_entity or
                            normalized_entity in normalized_mentioned):
                            area_matches = True
                            break

                    # If entity has an area but doesn't match mentioned location, flag it
                    if entity_area and not area_matches:
                        location_mismatches.append({
                            'entity': entity,
                            'entity_area': entity_area,
                            'mentioned_areas': mentioned_areas
                        })

                # If we have location mismatches, create ambiguity
                if location_mismatches:
                    mismatched_entities = [m['entity'] for m in location_mismatches]
                    ambiguities.append(Ambiguity(
                        id=f"amb-{id_counter}",
                        type=AmbiguityType.DEVICE,
                        severity=AmbiguitySeverity.CRITICAL,
                        description=f"Device '{mention}' matches devices in wrong location. You mentioned: {', '.join(mentioned_areas)}",
                        context={
                            'mention': mention,
                            'mentioned_locations': mentioned_areas,
                            'mismatches': [
                                {
                                    'entity_id': e.get('entity_id'),
                                    'name': e.get('name', e.get('friendly_name')),
                                    'actual_area': m['entity_area'],
                                    'expected_areas': m['mentioned_areas']
                                }
                                for e, m in zip(mismatched_entities, location_mismatches)
                            ]
                        },
                        related_entities=[e.get('entity_id') for e in mismatched_entities if e.get('entity_id')],
                        detected_text=mention
                    ))
                    id_counter += 1
                    continue  # Skip multiple match check if we already flagged location mismatch

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
                                'name': e.get('name', e.get('friendly_name')),
                                'area': e.get('area_id') or e.get('device_area_id') or 'unknown'
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
        extracted_entities: list[dict[str, Any]],
        automation_context: dict[str, Any] | None,
        start_id: int
    ) -> list[Ambiguity]:
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
        extracted_entities: list[dict[str, Any]],
        automation_context: dict[str, Any] | None,
        start_id: int
    ) -> list[Ambiguity]:
        """Detect action-related ambiguities"""
        ambiguities = []
        id_counter = start_id

        query_lower = query.lower()

        # NEW: If RAG client is available, check semantic similarity first
        # This reduces false positives by learning from successful queries
        # Use hybrid retrieval (2025 best practice: dense + sparse + reranking)
        if self.rag_client:
            try:
                # Check if similar successful queries exist
                similar_queries = await self.rag_client.retrieve_hybrid(
                    query=query,
                    knowledge_type='query',
                    top_k=1,
                    min_similarity=0.85,  # High threshold for "clear query"
                    use_query_expansion=True,
                    use_reranking=True
                )

                # If we find a highly similar successful query, the query is likely clear
                # Hybrid retrieval returns 'final_score' or 'hybrid_score', fallback to 'similarity'
                top_result = similar_queries[0] if similar_queries else None
                if top_result:
                    similarity = top_result.get('final_score') or top_result.get('hybrid_score') or top_result.get('similarity', 0.0)
                    if similarity > 0.85:
                        logger.debug(
                            f"Found similar successful query (similarity={similarity:.2f}) - "
                            f"skipping action ambiguity check for: {query[:50]}..."
                        )
                        return []  # No ambiguity - query is clear based on semantic similarity

            except Exception as e:
                # If RAG lookup fails, fall back to hardcoded rules
                logger.warning(f"RAG lookup failed, falling back to hardcoded rules: {e}")

        # Fallback: Check for vague action terms (hardcoded rules)
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
    ) -> list[Ambiguity]:
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

