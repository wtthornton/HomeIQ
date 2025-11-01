# Binary Sensor Entity Validation Issue - Analysis & Fix Plan

**Date:** November 1, 2025  
**Status:** Analysis Complete - Ready for Implementation

---

## Problem Statement

Automation creation is failing due to binary sensor entities (e.g., presence sensors) not being found during safety validation. The safety validator's `_check_entity_availability` method is correctly identifying missing entities, but the root cause is that invalid entity IDs are making it into the generated YAML.

---

## Root Cause Analysis

### Issue Flow:
1. **User Query:** "Presence detected at the office desk. → Transition the Office lights to Natural Light..."
2. **Entity Mapping:** The system tries to map "office desk" to an entity but may not find an exact match
3. **YAML Generation:** LLM generates YAML with entity IDs that may not exist (e.g., `binary_sensor.office_desk_presence`)
4. **Safety Validation:** `_check_entity_availability` checks each entity via `get_entity_state()`
5. **Failure:** Entity not found → Critical issue → Automation blocked

### Specific Problems:

1. **Entity Validation Gap:**
   - Entity validation happens BEFORE YAML generation
   - But LLM might still create entity IDs that weren't validated
   - LLM might pluralize, add suffixes, or modify entity IDs

2. **Binary Sensor Naming:**
   - Presence sensors often have names like:
     - `binary_sensor.office_desk_presence`
     - `binary_sensor.presence_office_desk`
     - `binary_sensor.office_desk_occupancy`
   - These variations may not match what's in HA

3. **Safety Validator Strictness:**
   - Currently treats ANY missing entity as critical
   - Blocks automation creation completely
   - Doesn't distinguish between validated and unvalidated entities

---

## Solution Plan

### Phase 1: Improve Entity Validation Before YAML Generation

**Goal:** Ensure only validated entity IDs make it into the YAML prompt

1. **Enhanced Entity Validation:**
   - Add fuzzy matching for binary sensors (presence, motion, door sensors)
   - Check multiple naming patterns:
     - `binary_sensor.{location}_{type}`
     - `binary_sensor.{type}_{location}`
     - `binary_sensor.{location}_{device}_{type}`
   - Return best match with confidence score

2. **Entity ID Constraints in Prompt:**
   - Make the prompt MORE strict about using ONLY validated entities
   - Add examples showing what happens if you create invalid IDs
   - Add a validation checklist for the LLM to follow

### Phase 2: Improve Safety Validator Entity Checking

**Goal:** Make safety validator smarter about missing entities

1. **Distinguish Entity Sources:**
   - Track which entities were validated vs. created by LLM
   - If entity was validated but not found → Critical (block)
   - If entity was NOT validated → Warning (suggest fix, but allow with override)

2. **Entity Name Suggestions:**
   - When entity not found, suggest similar entities from HA
   - Use fuzzy matching to find closest matches
   - Provide recommendations in the error message

3. **Partial Entity Matching:**
   - For binary sensors, check if similar entities exist
   - Example: `binary_sensor.office_desk_presence` not found
   - Check for: `binary_sensor.office_desk`, `binary_sensor.office_presence`, etc.
   - Suggest alternatives in warnings

### Phase 3: Better Error Messages & Recovery

**Goal:** Help users fix entity issues

1. **Detailed Error Messages:**
   - Show which specific entity is missing
   - List similar entities that DO exist
   - Provide exact entity ID format needed

2. **Entity Discovery:**
   - Add endpoint to search entities by partial name
   - Return suggestions when entity not found
   - Help users discover correct entity IDs

---

## Implementation Steps

### Step 1: Enhance Entity Validation (High Priority)

**File:** `services/ai-automation-service/src/services/entity_validator.py`

**Changes:**
1. Add fuzzy matching for binary sensors
2. Check multiple naming patterns for presence/motion sensors
3. Return confidence scores and alternatives

**Example Logic:**
```python
def _find_binary_sensor_fuzzy(self, query_term: str, available_entities: List[str]) -> Optional[str]:
    """
    Find binary sensor with fuzzy matching for common patterns.
    
    Patterns checked:
    - {location}_{type} (e.g., office_desk_presence)
    - {type}_{location} (e.g., presence_office_desk)
    - {location}_{device}_{type} (e.g., office_desk_occupancy)
    """
    query_lower = query_term.lower()
    candidates = []
    
    for entity_id in available_entities:
        if not entity_id.startswith('binary_sensor.'):
            continue
            
        entity_name = entity_id.replace('binary_sensor.', '').lower()
        
        # Exact match
        if query_lower in entity_name or entity_name in query_lower:
            return entity_id
        
        # Fuzzy match scoring
        score = self._calculate_similarity(query_lower, entity_name)
        if score > 0.7:
            candidates.append((entity_id, score))
    
    # Return best match
    if candidates:
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]
    
    return None
```

### Step 2: Strengthen YAML Generation Prompt

**File:** `services/ai-automation-service/src/api/ask_ai_router.py`

**Changes:**
1. Add stronger warnings about using ONLY validated entities
2. Add example of what happens if invalid entity is used
3. Add validation checklist in prompt

**Example Addition:**
```python
CRITICAL VALIDATION REQUIREMENT:
Before using ANY entity ID in your YAML, verify it is in the validated entities list above.
If the entity is NOT in the list, DO NOT create it. Instead:
1. Use a placeholder with a clear comment
2. OR use the closest matching entity from the validated list

Example of what NOT to do:
❌ BAD: entity_id: binary_sensor.office_desk_presence  # Not validated!
✅ GOOD: entity_id: binary_sensor.office_motion  # From validated list
✅ GOOD: entity_id: binary_sensor.office_motion  # Closest match to "desk presence"
```

### Step 3: Improve Safety Validator Entity Checking

**File:** `services/ai-automation-service/src/services/safety_validator.py`

**Changes:**
1. Add entity suggestion logic
2. Check for similar entities when exact match fails
3. Provide helpful error messages

**Implementation:**
```python
async def _check_entity_availability(self, yaml_data: Dict, validated_entities: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Check entity availability with smart suggestions.
    
    Args:
        yaml_data: Parsed YAML
        validated_entities: List of entity IDs that were validated during generation
    """
    issues = []
    validated_set = set(validated_entities) if validated_entities else set()
    
    # ... existing entity extraction ...
    
    for entity_id in all_entities:
        try:
            state = await self.ha_client.get_entity_state(entity_id)
            if not state:
                # Check if this was a validated entity
                was_validated = entity_id in validated_set
                
                # Try to find similar entities
                suggestions = await self._find_similar_entities(entity_id)
                
                issue = {
                    'severity': 'critical' if was_validated else 'warning',
                    'category': 'availability',
                    'message': f'Entity not found: {entity_id}',
                    'details': {
                        'entity_id': entity_id,
                        'was_validated': was_validated,
                        'suggestions': suggestions[:3]  # Top 3 suggestions
                    },
                    'recommendation': f'Verify entity {entity_id} exists. ' + 
                                    (f'Similar entities: {", ".join(suggestions[:2])}' if suggestions else '')
                }
                issues.append(issue)
        except Exception as e:
            logger.warning(f"Error checking entity {entity_id}: {e}")
    
    return issues

async def _find_similar_entities(self, entity_id: str) -> List[str]:
    """Find similar entities in Home Assistant."""
    if not self.ha_client:
        return []
    
    try:
        # Get all entities from HA
        all_states = await self.ha_client.get_states()
        
        domain = entity_id.split('.')[0] if '.' in entity_id else ''
        entity_name = entity_id.split('.', 1)[1] if '.' in entity_id else entity_id
        
        # Find entities in same domain with similar names
        candidates = []
        for state in all_states:
            state_entity_id = state.get('entity_id', '')
            if not state_entity_id.startswith(domain + '.'):
                continue
            
            state_name = state_entity_id.split('.', 1)[1] if '.' in state_entity_id else state_entity_id
            
            # Simple similarity: check for common words
            entity_words = set(entity_name.lower().split('_'))
            state_words = set(state_name.lower().split('_'))
            
            common = entity_words.intersection(state_words)
            if len(common) >= 2:  # At least 2 words in common
                score = len(common) / max(len(entity_words), len(state_words))
                candidates.append((state_entity_id, score))
        
        # Sort by score and return top matches
        candidates.sort(key=lambda x: x[1], reverse=True)
        return [entity_id for entity_id, score in candidates[:5]]
        
    except Exception as e:
        logger.warning(f"Error finding similar entities: {e}")
        return []
```

### Step 4: Pass Validated Entities to Safety Validator

**File:** `services/ai-automation-service/src/api/ask_ai_router.py`

**Changes:**
1. Track which entities were validated during YAML generation
2. Pass this list to safety validator
3. Safety validator uses it to determine severity

**Implementation:**
```python
# In approve_suggestion_from_query:
# Track validated entities
validated_entity_ids = []
if 'validated_entities' in final_suggestion:
    validated_entity_ids = list(final_suggestion['validated_entities'].values())

# Pass to safety validator
safety_report = await safety_validator.validate_automation(
    automation_yaml,
    validated_entities=validated_entity_ids
)
```

---

## Testing Strategy

1. **Test Case 1: Missing Binary Sensor**
   - Query: "Turn on lights when presence detected at office desk"
   - Expected: Entity validation finds closest match OR provides clear error with suggestions

2. **Test Case 2: Validated Entity Not Found**
   - Query with entity that was validated but doesn't exist in HA
   - Expected: Critical error with explanation

3. **Test Case 3: LLM Creates Invalid Entity**
   - Query where LLM might create entity not in validated list
   - Expected: Warning (not critical) with suggestions

4. **Test Case 4: Fuzzy Matching Success**
   - Query: "office desk presence"
   - Entity exists: `binary_sensor.office_desk_occupancy`
   - Expected: Fuzzy match finds it successfully

---

## Priority & Risk Assessment

### Priority: **HIGH**
- Blocks automation creation
- Affects user experience
- Common issue with presence sensors

### Risk: **LOW**
- Changes are additive (improvements, not breaking changes)
- Fallback behavior maintained
- Better error messages help users

---

## Success Criteria

1. ✅ Binary sensor entities are found via fuzzy matching during validation
2. ✅ Safety validator provides helpful suggestions when entities not found
3. ✅ Error messages clearly explain what entity is missing and what alternatives exist
4. ✅ Users can successfully create automations with presence sensors
5. ✅ No increase in false positives (blocking valid automations)

---

## Next Steps

1. Implement Step 1: Enhanced entity validation with fuzzy matching
2. Implement Step 2: Strengthened YAML generation prompt
3. Implement Step 3: Improved safety validator with suggestions
4. Test with real queries containing binary sensors
5. Deploy and monitor

