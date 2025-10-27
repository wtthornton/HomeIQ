"""
Entity Validation Service for AI Automation

Validates that entities exist in Home Assistant before generating automations.
This prevents "Entity not found" errors by ensuring only real entities are used.
"""

import logging
from typing import Dict, List, Optional, Any
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class EntityValidationResult:
    """Result of entity validation"""
    entity_id: str
    exists: bool
    suggested_alternatives: List[str]
    confidence_score: float


class EntityValidator:
    """
    Validates entities against real Home Assistant entities.
    
    This service ensures that automations use actual entities that exist
    in the Home Assistant instance, preventing "Entity not found" errors.
    """
    
    def __init__(self, data_api_client=None):
        self.data_api_client = data_api_client
        self.entity_cache = {}
        
    async def validate_entities(self, entity_ids: List[str]) -> Dict[str, EntityValidationResult]:
        """
        Validate a list of entity IDs against real Home Assistant entities.
        
        Args:
            entity_ids: List of entity IDs to validate
            
        Returns:
            Dictionary mapping entity_id to validation result
        """
        results = {}
        
        # Get all available entities from data-api
        available_entities = await self._get_available_entities()
        
        for entity_id in entity_ids:
            result = await self._validate_single_entity(entity_id, available_entities)
            results[entity_id] = result
            
        return results
    
    async def _get_available_entities(self) -> List[Dict[str, Any]]:
        """Get all available entities from data-api"""
        try:
            if self.data_api_client:
                logger.info("🔍 Fetching entities from data-api...")
                entities = await self.data_api_client.fetch_entities()
                logger.info(f"✅ Fetched {len(entities)} entities from data-api")
                if len(entities) > 0:
                    logger.info(f"First 3 entities: {[e.get('entity_id') for e in entities[:3]]}")
                return entities
            else:
                logger.warning("Data API client not available, using empty entity list")
                return []
        except Exception as e:
            logger.error(f"Error fetching entities from data-api: {e}", exc_info=True)
            return []
    
    async def _validate_single_entity(self, entity_id: str, available_entities: List[Dict[str, Any]]) -> EntityValidationResult:
        """
        Validate a single entity ID.
        
        Args:
            entity_id: Entity ID to validate
            available_entities: List of available entities
            
        Returns:
            EntityValidationResult with validation details
        """
        # Check if entity exists exactly
        exact_match = self._find_exact_match(entity_id, available_entities)
        if exact_match:
            return EntityValidationResult(
                entity_id=entity_id,
                exists=True,
                suggested_alternatives=[],
                confidence_score=1.0
            )
        
        # Find alternatives
        alternatives = self._find_alternatives(entity_id, available_entities)
        
        return EntityValidationResult(
            entity_id=entity_id,
            exists=False,
            suggested_alternatives=alternatives,
            confidence_score=0.0
        )
    
    def _find_exact_match(self, entity_id: str, available_entities: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Find exact match for entity ID"""
        for entity in available_entities:
            if entity.get('entity_id') == entity_id:
                return entity
        return None
    
    def _find_alternatives(self, entity_id: str, available_entities: List[Dict[str, Any]]) -> List[str]:
        """
        Find alternative entity IDs based on similarity.
        
        Args:
            entity_id: Entity ID to find alternatives for
            available_entities: List of available entities
            
        Returns:
            List of alternative entity IDs
        """
        alternatives = []
        
        # Extract domain and name parts
        if '.' in entity_id:
            domain, name = entity_id.split('.', 1)
        else:
            domain = 'unknown'
            name = entity_id
        
        # Find entities with same domain
        same_domain = [
            entity for entity in available_entities
            if entity.get('domain') == domain
        ]
        
        # Find entities with similar names
        name_words = set(re.findall(r'\w+', name.lower()))
        
        for entity in same_domain:
            entity_name = entity.get('entity_id', '').split('.', 1)[1] if '.' in entity.get('entity_id', '') else ''
            entity_words = set(re.findall(r'\w+', entity_name.lower()))
            
            # Calculate similarity
            common_words = name_words.intersection(entity_words)
            if common_words:
                similarity = len(common_words) / len(name_words.union(entity_words))
                if similarity > 0.3:  # 30% similarity threshold
                    alternatives.append(entity.get('entity_id'))
        
        # Limit to top 5 alternatives
        return alternatives[:5]
    
    async def map_query_to_entities(self, query: str, entities: List[str]) -> Dict[str, str]:
        """
        Map query terms to actual entity IDs.
        
        Args:
            query: Original user query
            entities: List of entities mentioned in query
            
        Returns:
            Dictionary mapping query terms to actual entity IDs
        """
        print(f"🔍 map_query_to_entities CALLED with query='{query}', entities={entities}")
        logger.info(f"🔍 map_query_to_entities CALLED with query='{query}', entities={entities}")
        mapping = {}
        
        # Get available entities
        available_entities = await self._get_available_entities()
        print(f"🔍 Available entities count: {len(available_entities)}")
        logger.info(f"🔍 Available entities count: {len(available_entities)}")
        
        # If entities list is empty, try to extract from query directly
        if not entities:
            print(f"🔍 No entities provided, extracting from query directly: {query}")
            logger.info("No entities provided, extracting from query directly")
            # Extract potential entities from query
            query_lower = query.lower()
            print(f"🔍 Query lower: {query_lower}")
            
            # Look for living room-related entities
            if 'living room' in query_lower or 'livingroom' in query_lower:
                print(f"🔍 Found 'living room' in query, looking for living room entities...")
                living_room_entities = [e for e in available_entities if 'living' in e.get('entity_id', '').lower() and 'room' in e.get('entity_id', '').lower()]
                print(f"🔍 Living room entities found: {[e.get('entity_id') for e in living_room_entities[:5]]}")
                if living_room_entities:
                    # Prefer lights for living room
                    living_room_lights = [e for e in living_room_entities if e.get('domain') == 'light']
                    print(f"🔍 Living room lights found: {[e.get('entity_id') for e in living_room_lights[:3]]}")
                    if living_room_lights:
                        mapping['living room'] = living_room_lights[0]['entity_id']
                        mapping['lights'] = living_room_lights[0]['entity_id']
                        print(f"🔍 Mapped 'living room' to {living_room_lights[0]['entity_id']}")
                        logger.info(f"Mapped 'living room' to {living_room_lights[0]['entity_id']}")
            
            # Look for office-related entities
            if 'office' in query_lower:
                print(f"🔍 Found 'office' in query, looking for office entities...")
                office_entities = [e for e in available_entities if 'office' in e.get('entity_id', '').lower()]
                print(f"🔍 Office entities found: {[e.get('entity_id') for e in office_entities[:5]]}")
                if office_entities:
                    # Prefer lights for office
                    office_lights = [e for e in office_entities if e.get('domain') == 'light']
                    print(f"🔍 Office lights found: {[e.get('entity_id') for e in office_lights[:3]]}")
                    if office_lights:
                        mapping['office'] = office_lights[0]['entity_id']
                        print(f"🔍 Mapped 'office' to {office_lights[0]['entity_id']}")
                        logger.info(f"Mapped 'office' to {office_lights[0]['entity_id']}")
            
            # Look for door-related entities
            if 'door' in query_lower or 'front' in query_lower:
                door_entities = [e for e in available_entities if 'door' in e.get('entity_id', '').lower()]
                if door_entities:
                    # Prefer binary sensors for doors
                    door_sensors = [e for e in door_entities if e.get('domain') == 'binary_sensor']
                    if door_sensors:
                        mapping['door'] = door_sensors[0]['entity_id']
                        logger.info(f"Mapped 'door' to {door_sensors[0]['entity_id']}")
                    else:
                        # Fallback to any door entity
                        mapping['door'] = door_entities[0]['entity_id']
                        logger.info(f"Mapped 'door' to {door_entities[0]['entity_id']}")
            
            # Look for light-related entities
            if 'light' in query_lower or 'flash' in query_lower:
                light_entities = [e for e in available_entities if e.get('domain') == 'light']
                if light_entities:
                    # Prefer living room lights if query mentions living room
                    living_room_lights = [e for e in light_entities if 'living' in e.get('entity_id', '').lower() and 'room' in e.get('entity_id', '').lower()]
                    if living_room_lights:
                        mapping['lights'] = living_room_lights[0]['entity_id']
                        logger.info(f"Mapped 'lights' to living room light: {living_room_lights[0]['entity_id']}")
                    else:
                        # Prefer office lights if available
                        office_lights = [e for e in light_entities if 'office' in e.get('entity_id', '').lower()]
                        if office_lights:
                            mapping['lights'] = office_lights[0]['entity_id']
                            logger.info(f"Mapped 'lights' to {office_lights[0]['entity_id']}")
                        else:
                            # Use any light
                            mapping['lights'] = light_entities[0]['entity_id']
                            logger.info(f"Mapped 'lights' to {light_entities[0]['entity_id']}")
        else:
            # Use the provided entities list
            print(f"🔍 Using provided entities list: {entities}")
            logger.info(f"Using provided entities list: {entities}")
            for entity in entities:
                # Try to find best match
                print(f"🔍 Looking for best match for '{entity}'...")
                logger.info(f"Looking for best match for '{entity}'...")
                
                # If query mentions "light", prefer light entities
                entity_lower = entity.lower()
                filtered_entities = available_entities
                if 'light' in entity_lower or 'flash' in entity_lower:
                    # Try to find lights first
                    light_entities = [e for e in available_entities if e.get('domain') == 'light']
                    if light_entities:
                        print(f"🔍 Filtering to light entities only ({len(light_entities)} found)")
                        filtered_entities = light_entities
                
                best_match = self._find_best_match(entity, filtered_entities)
                if best_match:
                    mapping[entity] = best_match['entity_id']
                    print(f"✅ Mapped '{entity}' to {best_match['entity_id']}")
                    logger.info(f"Mapped '{entity}' to {best_match['entity_id']}")
                else:
                    print(f"⚠️ No match found for '{entity}'")
                    logger.warning(f"No match found for '{entity}'")
        
        logger.info(f"Final entity mapping: {mapping}")
        return mapping
    
    def _find_best_match(self, query_term: str, available_entities: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Find the best matching entity for a query term.
        
        Args:
            query_term: Term from user query (e.g., "office light")
            available_entities: List of available entities
            
        Returns:
            Best matching entity or None
        """
        query_words = set(re.findall(r'\w+', query_term.lower()))
        print(f"🔍 _find_best_match for '{query_term}' with {len(query_words)} words: {query_words}")
        
        best_match = None
        best_score = 0
        
        # Debug: Check if we find light.living_room
        living_room_lights = [e for e in available_entities if 'living_room' in e.get('entity_id', '')]
        if living_room_lights:
            print(f"🔍 DEBUG: Found {len(living_room_lights)} living_room entities: {[e.get('entity_id') for e in living_room_lights[:3]]}")
        
        for entity in available_entities:
            entity_id = entity.get('entity_id', '')
            entity_name = entity_id.split('.', 1)[1] if '.' in entity_id else entity_id
            
            # Split on underscores and hyphens to handle "living_room" -> ["living", "room"]
            entity_words = set()
            for word in re.findall(r'\w+', entity_name.lower()):
                # Also split underscores and hyphens
                entity_words.update(word.split('_'))
                entity_words.update(word.split('-'))
            
            # Calculate word overlap score
            common_words = query_words.intersection(entity_words)
            
            # Debug specific entity
            if entity_id == 'light.living_room':
                print(f"🔍 DEBUG light.living_room: query_words={query_words}, entity_words={entity_words}, common={common_words}")
            
            if common_words:
                score = len(common_words) / len(query_words.union(entity_words))
                if score > best_score:
                    best_score = score
                    best_match = entity
                    print(f"  💡 Better match: {entity_id} (score: {score:.2f}, common: {common_words})")
        
        # Lower threshold to 25% to catch "Living Room Light" -> "light.living_room"
        print(f"🔍 Best match: {best_match.get('entity_id') if best_match else 'NONE'} (score: {best_score:.2f})")
        return best_match if best_score >= 0.25 else None
    
    async def validate_automation_yaml(self, yaml_content: str) -> Dict[str, Any]:
        """
        Validate all entities in an automation YAML.
        
        Args:
            yaml_content: Automation YAML content
            
        Returns:
            Validation result with entity status
        """
        import yaml
        
        try:
            automation_data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            return {
                "valid": False,
                "error": f"Invalid YAML: {e}",
                "entity_results": {}
            }
        
        # Extract entity IDs from YAML
        entity_ids = self._extract_entity_ids_from_yaml(automation_data)
        
        # Validate entities
        validation_results = await self.validate_entities(entity_ids)
        
        # Check if all entities are valid
        all_valid = all(result.exists for result in validation_results.values())
        
        return {
            "valid": all_valid,
            "entity_results": validation_results,
            "invalid_entities": [
                entity_id for entity_id, result in validation_results.items()
                if not result.exists
            ]
        }
    
    def _extract_entity_ids_from_yaml(self, automation_data: Dict[str, Any]) -> List[str]:
        """Extract all entity IDs from automation YAML data"""
        entity_ids = set()
        
        def extract_from_dict(data):
            if isinstance(data, dict):
                if 'entity_id' in data:
                    entity_id = data['entity_id']
                    if isinstance(entity_id, str):
                        entity_ids.add(entity_id)
                    elif isinstance(entity_id, list):
                        entity_ids.update(entity_id)
                
                for value in data.values():
                    extract_from_dict(value)
            elif isinstance(data, list):
                for item in data:
                    extract_from_dict(item)
        
        extract_from_dict(automation_data)
        return list(entity_ids)
