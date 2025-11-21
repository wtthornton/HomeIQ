"""
Entity ID Validator for YAML Validation

Validates that all entity_id values in YAML are valid before sending to Home Assistant.
Catches None, empty strings, wrong types, and invalid formats in nested structures.
"""

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of entity ID validation"""
    is_valid: bool
    errors: list[str]
    warnings: list[str]


class EntityIDValidator:
    """
    Validates entity_id values in YAML structure.
    
    Recursively checks all entity_id values to ensure they are:
    - Not None
    - Not empty strings
    - String type
    - Valid format (domain.entity)
    
    Can also auto-fix incomplete entity IDs using validated entities.
    """

    def validate_entity_ids(
        self,
        yaml_data: dict,
        validated_entities: list[str] | None = None,
        auto_fix: bool = True
    ) -> ValidationResult:
        """
        Recursively validate all entity_id values in YAML.
        
        Args:
            yaml_data: Parsed YAML dictionary
            validated_entities: List of validated entity IDs for auto-fixing
            auto_fix: Whether to attempt auto-fixing incomplete entity IDs
            
        Returns:
            ValidationResult with validation status and errors
        """
        errors = []
        warnings = []
        fixes_applied = []

        # Extract all entity IDs from YAML
        entity_ids = self._extract_all_entity_ids(yaml_data)

        logger.debug(f"🔍 Found {len(entity_ids)} entity_id values to validate")

        # Build domain-to-entity and name-to-entity mappings for auto-fixing
        domain_map = {}
        name_map = {}  # entity_name -> [entity_ids]
        entity_name_parts_map = {}  # partial_name -> [entity_ids] for fuzzy matching

        if validated_entities and auto_fix:
            logger.debug(f"🔍 Building maps from {len(validated_entities)} validated entities: {validated_entities[:5]}")
            for entity_id in validated_entities:
                if isinstance(entity_id, str) and '.' in entity_id:
                    domain, name = entity_id.split('.', 1)

                    # Domain map: domain -> [entity_ids]
                    if domain not in domain_map:
                        domain_map[domain] = []
                    domain_map[domain].append(entity_id)

                    # Name map: full name -> [entity_ids] (for exact matches)
                    if name not in name_map:
                        name_map[name] = []
                    name_map[name].append(entity_id)

                    # Entity name parts map: partial matches
                    # Add each word in the name (split by underscore)
                    name_parts = name.split('_')
                    for part in name_parts:
                        if part:
                            if part not in entity_name_parts_map:
                                entity_name_parts_map[part] = []
                            if entity_id not in entity_name_parts_map[part]:
                                entity_name_parts_map[part].append(entity_id)

                    # Also add the full name as a partial (for substring matching)
                    if name not in entity_name_parts_map:
                        entity_name_parts_map[name] = []
                    if entity_id not in entity_name_parts_map[name]:
                        entity_name_parts_map[name].append(entity_id)

            logger.debug(f"🔍 Maps built - domains: {list(domain_map.keys())}, names: {len(name_map)}, name_parts: {len(entity_name_parts_map)}")

        for entity_id, location in entity_ids:
            # Check if None
            if entity_id is None:
                errors.append(f"❌ {location}: entity_id is None")
                continue

            # Check if empty
            if isinstance(entity_id, str) and not entity_id.strip():
                errors.append(f"❌ {location}: entity_id is empty string")
                continue

            # Check if string type
            if not isinstance(entity_id, str):
                errors.append(
                    f"❌ {location}: entity_id is {type(entity_id).__name__}, "
                    f"expected string, got: {entity_id}"
                )
                continue

            # Check format (domain.entity)
            if '.' not in entity_id:
                # AUTO-FIX: Try to complete incomplete entity IDs using validated entities
                # entity_id might be just a domain (e.g., 'wled') or entity name
                if auto_fix and validated_entities:
                    candidates = []
                    logger.debug(f"🔍 Attempting auto-fix for incomplete entity_id '{entity_id}' at {location}")

                    # Strategy 1: Exact domain match (highest priority)
                    entity_id_lower = entity_id.lower()
                    if entity_id_lower in domain_map:
                        candidates = domain_map[entity_id_lower]
                        logger.debug(f"🔍 Strategy 1 (domain exact): Found {len(candidates)} candidates: {candidates}")

                    # Strategy 2: Exact entity name match (high priority)
                    if not candidates and entity_id_lower in name_map:
                        candidates = name_map[entity_id_lower]
                        logger.debug(f"🔍 Strategy 2 (name exact): Found {len(candidates)} candidates: {candidates}")

                    # Strategy 3: Entity name parts match (partial match)
                    if not candidates:
                        # Check if entity_id matches any name part
                        if entity_id_lower in entity_name_parts_map:
                            candidates = entity_name_parts_map[entity_id_lower]
                            logger.debug(f"🔍 Strategy 3 (name part): Found {len(candidates)} candidates: {candidates}")

                    # Strategy 4: Substring matching - check if entity_id is contained in domain or entity name
                    if not candidates:
                        for valid_id in validated_entities:
                            if isinstance(valid_id, str) and '.' in valid_id:
                                domain, name = valid_id.split('.', 1)
                                domain_lower = domain.lower()
                                name_lower = name.lower()

                                # Check if entity_id is contained in domain or name
                                if entity_id_lower in domain_lower or entity_id_lower in name_lower or domain_lower.startswith(entity_id_lower) or name_lower.startswith(entity_id_lower):
                                    candidates.append(valid_id)

                        if candidates:
                            logger.debug(f"🔍 Strategy 4 (substring): Found {len(candidates)} candidates: {candidates}")

                    # Strategy 5: Fuzzy matching with rapidfuzz
                    if not candidates:
                        # Use rapidfuzz for better typo and abbreviation handling
                        for valid_id in validated_entities:
                            if isinstance(valid_id, str) and '.' in valid_id:
                                domain, name = valid_id.split('.', 1)
                                # Check if entity_id is similar to domain or name (at least 70% match)
                                domain_score = self._fuzzy_match(entity_id_lower, domain.lower(), threshold=0.7)
                                name_score = self._fuzzy_match(entity_id_lower, name.lower(), threshold=0.7)
                                if domain_score > 0.0 or name_score > 0.0:
                                    candidates.append(valid_id)

                        if candidates:
                            logger.debug(f"🔍 Strategy 5 (fuzzy): Found {len(candidates)} candidates: {candidates}")

                    if len(candidates) == 1:
                        # Unique match - auto-fix it
                        fixed_id = candidates[0]
                        if self._apply_fix_to_yaml(yaml_data, location, entity_id, fixed_id):
                            fixes_applied.append(f"{location}: '{entity_id}' → '{fixed_id}'")
                            logger.info(f"🔧 Auto-fixed {location}: '{entity_id}' → '{fixed_id}'")
                            # Re-extract entity IDs after fix to update the loop
                            entity_ids = self._extract_all_entity_ids(yaml_data)
                            continue
                        else:
                            logger.warning(f"⚠️ Could not apply fix to {location}")
                    elif len(candidates) > 1:
                        # Multiple matches - use the first one but warn
                        fixed_id = candidates[0]
                        if self._apply_fix_to_yaml(yaml_data, location, entity_id, fixed_id):
                            fixes_applied.append(f"{location}: '{entity_id}' → '{fixed_id}' (selected from {len(candidates)} matches)")
                            warnings.append(
                                f"⚠️ {location}: entity_id '{entity_id}' matched {len(candidates)} entities. "
                                f"Using: {fixed_id}. Other candidates: {', '.join(candidates[1:3])}"
                            )
                            logger.info(f"🔧 Auto-fixed {location}: '{entity_id}' → '{fixed_id}' (from {len(candidates)} candidates)")
                            # Re-extract entity IDs after fix to update the loop
                            entity_ids = self._extract_all_entity_ids(yaml_data)
                            continue
                        else:
                            logger.warning(f"⚠️ Could not apply fix to {location}")
                    else:
                        logger.warning(f"⚠️ No candidates found for incomplete entity_id '{entity_id}' in validated entities: {validated_entities[:10]}")

                errors.append(
                    f"❌ {location}: entity_id '{entity_id}' doesn't contain '.' "
                    f"(required format: domain.entity)"
                )
                continue

            if entity_id.count('.') != 1:
                errors.append(
                    f"❌ {location}: entity_id '{entity_id}' has {entity_id.count('.')} dots, "
                    f"expected exactly 1 (format: domain.entity)"
                )
                continue

            # Check domain is valid (not empty, doesn't start with digit)
            domain, entity_name = entity_id.split('.', 1)
            if not domain or not domain.strip():
                errors.append(
                    f"❌ {location}: Invalid domain in entity_id '{entity_id}' (domain is empty)"
                )
            elif domain[0].isdigit():
                errors.append(
                    f"❌ {location}: Invalid domain in entity_id '{entity_id}' (domain starts with digit)"
                )
            elif not all(c.islower() or c.isdigit() or c == '_' for c in domain):
                errors.append(
                    f"❌ {location}: Invalid domain in entity_id '{entity_id}' "
                    f"(domain must be lowercase letters, numbers, and underscores only)"
                )

            if not entity_name or not entity_name.strip():
                errors.append(
                    f"❌ {location}: Invalid entity name in entity_id '{entity_id}' (name is empty)"
                )
            else:
                # Check entity name follows HA naming conventions
                entity_name_stripped = entity_name.strip()
                if entity_name_stripped.startswith('_') or entity_name_stripped.endswith('_'):
                    errors.append(
                        f"❌ {location}: Invalid entity name in entity_id '{entity_id}' "
                        f"(name cannot start or end with underscore per HA requirements)"
                    )
                elif not all(c.islower() or c.isdigit() or c == '_' for c in entity_name_stripped):
                    errors.append(
                        f"❌ {location}: Invalid entity name in entity_id '{entity_id}' "
                        f"(name must be lowercase letters, numbers, and underscores only per HA requirements)"
                    )

        if fixes_applied:
            logger.info(f"✅ Applied {len(fixes_applied)} auto-fixes: {fixes_applied}")
            warnings.append(f"Auto-fixed {len(fixes_applied)} incomplete entity IDs")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def _extract_all_entity_ids(self, yaml_data: dict) -> list[tuple[str, str]]:
        """
        Recursively extract all entity_id values with their locations.
        
        Returns:
            List of tuples: (entity_id, location_path)
        """
        entity_ids = []

        def _clean_entity_id(eid: Any) -> str | None:
            """Clean entity ID by removing trailing commas and whitespace"""
            if not isinstance(eid, str):
                return str(eid) if eid is not None else None
            # Remove trailing commas and whitespace
            cleaned = eid.rstrip(', ').strip()
            # Filter out Jinja2 template variables ({{ ... }}, {% ... %})
            if cleaned and ('{{' in cleaned or '{%' in cleaned):
                return None  # Skip Jinja2 template variables - they're not entity IDs
            return cleaned if cleaned else None

        # Check triggers
        triggers = yaml_data.get('trigger', yaml_data.get('triggers', []))
        if isinstance(triggers, list):
            for i, trigger in enumerate(triggers):
                if isinstance(trigger, dict):
                    entity_id = trigger.get('entity_id')
                    if entity_id is not None:
                        if isinstance(entity_id, list):
                            for j, eid in enumerate(entity_id):
                                cleaned_eid = _clean_entity_id(eid)
                                if cleaned_eid:
                                    entity_ids.append((cleaned_eid, f"trigger[{i}].entity_id[{j}]"))
                        else:
                            cleaned_eid = _clean_entity_id(entity_id)
                            if cleaned_eid:
                                entity_ids.append((cleaned_eid, f"trigger[{i}].entity_id"))

        # Check actions (recursive)
        actions = yaml_data.get('action', yaml_data.get('actions', []))
        if actions:
            entity_ids.extend(self._extract_from_actions(actions, "action"))

        # Check conditions
        conditions = yaml_data.get('condition', yaml_data.get('conditions', []))
        if isinstance(conditions, list):
            for i, condition in enumerate(conditions):
                if isinstance(condition, dict):
                    entity_id = condition.get('entity_id')
                    if entity_id is not None:
                        if isinstance(entity_id, list):
                            for j, eid in enumerate(entity_id):
                                cleaned_eid = _clean_entity_id(eid)
                                if cleaned_eid:
                                    entity_ids.append((cleaned_eid, f"condition[{i}].entity_id[{j}]"))
                        else:
                            cleaned_eid = _clean_entity_id(entity_id)
                            if cleaned_eid:
                                entity_ids.append((cleaned_eid, f"condition[{i}].entity_id"))

        return entity_ids

    def extract_scenes_created(self, yaml_data: dict) -> set[str]:
        """
        Extract scene entity IDs that are created by scene.create service calls.
        
        Home Assistant 2025 format:
        - action: (top level, singular)
        - service: scene.create (inside action items)
        - data.scene_id: The scene ID (becomes scene.{scene_id} entity)
        
        Args:
            yaml_data: Parsed YAML dictionary
            
        Returns:
            Set of scene entity IDs that are created dynamically
        """
        created_scenes = set()
        actions = yaml_data.get('action', yaml_data.get('actions', []))
        if actions:
            self._extract_scenes_created(actions, created_scenes)
        
        # Also extract all scene entities from the YAML to help with matching
        # This helps us identify if a scene entity is referenced but not created
        all_scene_entities = set()
        entity_id_tuples = self._extract_all_entity_ids(yaml_data)
        for entity_id, _ in entity_id_tuples:
            if entity_id and entity_id.startswith('scene.'):
                all_scene_entities.add(entity_id)
        
        # If we found scene entities but didn't find them in created_scenes,
        # try to match them by checking if the scene_id (without scene. prefix) matches
        if all_scene_entities and created_scenes:
            # Check for potential matches (scene.entity_name might be created as scene_id: entity_name)
            for scene_entity in all_scene_entities:
                if scene_entity not in created_scenes:
                    # Try to find a match by removing the scene. prefix
                    scene_name = scene_entity.replace('scene.', '', 1)
                    # Check if any created scene matches (with or without scene. prefix)
                    for created in created_scenes:
                        created_name = created.replace('scene.', '', 1)
                        if scene_name == created_name:
                            logger.info(f"🔍 Matched scene entity {scene_entity} to created scene {created}")
                            created_scenes.add(scene_entity)
                            break
        
        return created_scenes

    def _extract_scenes_created(self, actions: Any, created_scenes: set[str]) -> None:
        """
        Recursively extract scene IDs created by scene.create service calls.
        
        Home Assistant 2025 format:
        - action: (top level, singular)
        - service: scene.create (inside action items)
        - data.scene_id: The scene ID (becomes scene.{scene_id} entity)
        
        Args:
            actions: Action structure (list or dict)
            created_scenes: Set to populate with created scene entity IDs
        """
        if isinstance(actions, list):
            for i, action in enumerate(actions):
                if isinstance(action, dict):
                    # Check for scene.create service (2025 format: service: field)
                    service = action.get('service')
                    if service == 'scene.create':
                        data = action.get('data', {})
                        scene_id = data.get('scene_id')
                        
                        if scene_id:
                            # Handle template variables - if scene_id contains {{ }}, skip it
                            # (can't validate template variables at validation time)
                            if isinstance(scene_id, str) and '{{' in scene_id:
                                logger.warning(f"⚠️ Scene ID contains template variable, skipping: {scene_id}")
                                continue
                            
                            # Convert scene_id to entity_id format (Home Assistant 2025 pattern)
                            if not scene_id.startswith('scene.'):
                                scene_entity_id = f"scene.{scene_id}"
                            else:
                                scene_entity_id = scene_id
                            
                            created_scenes.add(scene_entity_id)
                            logger.info(f"🔍 Found dynamically created scene: {scene_entity_id} (from scene_id: {scene_id})")
                        else:
                            logger.warning(f"⚠️ scene.create service found but no scene_id in data: {action}")
                    
                    # Recursively check nested structures (sequence, repeat.sequence, choose)
                    if 'sequence' in action:
                        sequence = action['sequence']
                        if sequence:
                            self._extract_scenes_created(sequence, created_scenes)
                    if 'repeat' in action and isinstance(action['repeat'], dict):
                        if 'sequence' in action['repeat']:
                            sequence = action['repeat']['sequence']
                            if sequence:
                                self._extract_scenes_created(sequence, created_scenes)
                    if 'choose' in action:
                        choose = action['choose']
                        if isinstance(choose, list):
                            for branch in choose:
                                if isinstance(branch, dict) and 'sequence' in branch:
                                    sequence = branch['sequence']
                                    if sequence:
                                        self._extract_scenes_created(sequence, created_scenes)
        elif isinstance(actions, dict):
            # Handle single action dict
            service = actions.get('service')
            if service == 'scene.create':
                data = actions.get('data', {})
                scene_id = data.get('scene_id')
                
                if scene_id:
                    # Handle template variables
                    if isinstance(scene_id, str) and '{{' in scene_id:
                        logger.warning(f"⚠️ Scene ID contains template variable, skipping: {scene_id}")
                        return
                    
                    # Convert scene_id to entity_id format
                    if not scene_id.startswith('scene.'):
                        scene_entity_id = f"scene.{scene_id}"
                    else:
                        scene_entity_id = scene_id
                    
                    created_scenes.add(scene_entity_id)
                    logger.info(f"🔍 Found dynamically created scene: {scene_entity_id} (from scene_id: {scene_id})")
                else:
                    logger.warning(f"⚠️ scene.create service found but no scene_id in data: {actions}")

    def _extract_from_actions(self, actions: Any, base_path: str) -> list[tuple[str, str]]:
        """Recursively extract entity_ids from action structures"""
        entity_ids = []

        if isinstance(actions, list):
            for i, action in enumerate(actions):
                path = f"{base_path}[{i}]"
                entity_ids.extend(self._extract_from_action(action, path))
        elif isinstance(actions, dict):
            entity_ids.extend(self._extract_from_action(actions, base_path))

        return entity_ids

    def _extract_from_action(self, action: Any, path: str) -> list[tuple[str, str]]:
        """Extract entity_id from a single action, handling nested structures"""
        entity_ids = []

        if not isinstance(action, dict):
            return entity_ids

        def _clean_entity_id(eid: Any) -> str | None:
            """Clean entity ID by removing trailing commas and whitespace"""
            if not isinstance(eid, str):
                return str(eid) if eid is not None else None
            # Remove trailing commas and whitespace
            cleaned = eid.rstrip(', ').strip()
            return cleaned if cleaned else None

        # Check target.entity_id (single or list)
        target = action.get('target', {})
        if isinstance(target, dict):
            entity_id = target.get('entity_id')
            if entity_id is not None:
                if isinstance(entity_id, str):
                    cleaned_eid = _clean_entity_id(entity_id)
                    if cleaned_eid:
                        entity_ids.append((cleaned_eid, f"{path}.target.entity_id"))
                elif isinstance(entity_id, list):
                    for j, eid in enumerate(entity_id):
                        cleaned_eid = _clean_entity_id(eid)
                        if cleaned_eid:
                            entity_ids.append((cleaned_eid, f"{path}.target.entity_id[{j}]"))

        # Check direct entity_id
        entity_id = action.get('entity_id')
        if entity_id is not None:
            if isinstance(entity_id, str):
                cleaned_eid = _clean_entity_id(entity_id)
                if cleaned_eid:
                    entity_ids.append((cleaned_eid, f"{path}.entity_id"))
            elif isinstance(entity_id, list):
                for j, eid in enumerate(entity_id):
                    cleaned_eid = _clean_entity_id(eid)
                    if cleaned_eid:
                        entity_ids.append((cleaned_eid, f"{path}.entity_id[{j}]"))

        # Check sequence (nested)
        if 'sequence' in action:
            sequence = action['sequence']
            if sequence:  # Only if sequence exists and is not empty
                entity_ids.extend(self._extract_from_actions(sequence, f"{path}.sequence"))

        # Check repeat.sequence (nested)
        if 'repeat' in action:
            repeat = action['repeat']
            if isinstance(repeat, dict) and 'sequence' in repeat:
                sequence = repeat['sequence']
                if sequence:
                    entity_ids.extend(self._extract_from_actions(sequence, f"{path}.repeat.sequence"))

        # Check choose branches
        if 'choose' in action:
            choose = action['choose']
            if isinstance(choose, list):
                for i, branch in enumerate(choose):
                    if isinstance(branch, dict) and 'sequence' in branch:
                        sequence = branch['sequence']
                        if sequence:
                            entity_ids.extend(
                                self._extract_from_actions(sequence, f"{path}.choose[{i}].sequence")
                            )

        return entity_ids

    def _fuzzy_match(self, str1: str, str2: str, threshold: float = 0.7) -> float:
        """
        Calculate fuzzy similarity score using rapidfuzz.
        
        Uses fuzzy_score() utility for typo handling, abbreviation matching,
        and word order independence. Returns confidence score instead of boolean.
        
        Args:
            str1: First string to compare
            str2: Second string to compare
            threshold: Minimum similarity ratio (0.0 to 1.0) - used for filtering
            
        Returns:
            Similarity score 0.0-1.0 (0.0 if below threshold)
        """
        from ..utils.fuzzy import fuzzy_score
        
        if not str1 or not str2:
            return 0.0

        # Use rapidfuzz-based fuzzy_score for better accuracy
        return fuzzy_score(str1, str2, threshold=threshold)

    def _apply_fix_to_yaml(self, yaml_data: dict, location: str, old_id: str, new_id: str) -> bool:
        """Apply a fix to the YAML data structure by updating entity_id at the given location
        
        Handles complex nested paths like: action[0].sequence[1].repeat.sequence[0].target.entity_id
        
        Returns:
            True if fix was applied successfully, False otherwise
        """
        try:
            # Parse location into path segments
            # Example: "action[0].sequence[1].repeat.sequence[0].target.entity_id"
            # Becomes: [('action', 0), ('sequence', 1), ('repeat', None), ('sequence', 0), ('target', None), ('entity_id', None)]

            segments = []
            for segment in location.split('.'):
                if '[' in segment:
                    # Array access: action[0] or sequence[1]
                    key, index_str = segment.split('[', 1)
                    index = int(index_str.rstrip(']'))
                    segments.append((key, index))
                else:
                    # Dictionary access: target, entity_id
                    segments.append((segment, None))

            # Navigate to the parent of the target
            current = yaml_data
            for i, (key, index) in enumerate(segments[:-1]):
                # Navigate to the key
                if not isinstance(current, dict) or key not in current:
                    logger.warning(f"Path {location}: '{key}' not found in dict at segment {i}")
                    return False

                current = current[key]

                # If this segment has an index, navigate into the array
                if index is not None:
                    if not isinstance(current, list):
                        logger.warning(f"Path {location}: '{key}' is not a list at segment {i}")
                        return False
                    if index >= len(current):
                        logger.warning(f"Path {location}: Index {index} out of bounds for '{key}' at segment {i} (length: {len(current)})")
                        return False
                    current = current[index]

            # Fix the target (last segment)
            target_key, target_index = segments[-1]

            if target_index is not None:
                # Target is an array element: entity_id[0]
                if not isinstance(current, dict) or target_key not in current:
                    # Create the array if it doesn't exist
                    if target_key not in current:
                        current[target_key] = []
                    elif not isinstance(current[target_key], list):
                        current[target_key] = [current[target_key]]

                # Extend array if needed
                while len(current[target_key]) <= target_index:
                    current[target_key].append(None)

                current[target_key][target_index] = new_id
                logger.debug(f"✅ Fixed {location}: '{old_id}' → '{new_id}'")
                return True
            else:
                # Target is a direct dictionary key: entity_id
                if not isinstance(current, dict):
                    logger.warning(f"Path {location}: Parent is not a dict for '{target_key}'")
                    return False

                current[target_key] = new_id
                logger.debug(f"✅ Fixed {location}: '{old_id}' → '{new_id}'")
                return True

        except (KeyError, IndexError, ValueError, AttributeError, TypeError) as e:
            logger.warning(f"Could not apply fix to {location}: {e}", exc_info=True)
            return False

