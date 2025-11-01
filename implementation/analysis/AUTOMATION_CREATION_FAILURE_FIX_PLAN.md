# Automation Creation Failure Fix Plan

**Date:** November 1, 2025  
**Last Updated:** November 1, 2025  
**Status:** Analysis Complete - Ready for Implementation  
**Priority:** CRITICAL

---

## Problem Analysis

### Error from Logs

```
❌ Failed to create automation (400): {
  "message":"Message malformed: not a valid value for dictionary value @ 
  data['actions'][0]['sequence'][1]['target']['entity_id']"
}
```

**And:**

```
❌ Failed to create automation (400): {
  "message":"Message malformed: not a valid value for dictionary value @ 
  data['actions'][0]['sequence'][1]['repeat']['sequence'][0]['target']['entity_id']"
}
```

### Root Cause

Home Assistant is rejecting the automation because `entity_id` values in nested sequences are:
1. **None/null** - Entity ID is missing
2. **Empty string** - Entity ID is empty
3. **Wrong type** - Entity ID is not a string (could be list/dict)
4. **Invalid format** - Entity ID doesn't match expected pattern

The error occurs specifically at:
- `data['actions'][0]['sequence'][1]['target']['entity_id']` - Second item in sequence
- Nested sequences: `data['actions'][0]['sequence'][1]['repeat']['sequence'][0]['target']['entity_id']`

### Why This Happens

1. **YAML Generation Issues:**
   - LLM might generate entity_id as `None` or empty
   - Entity might not be validated/resolved properly
   - Nested structures (sequences, repeats) might lose entity_id context

2. **Entity Validation Gaps:**
   - Safety validator checks if entity exists, but doesn't validate the YAML structure
   - YAML structure validator fixes field names but doesn't validate entity_id values
   - No pre-flight validation of entity_id format/types in nested structures

3. **Error Handling:**
   - HA API returns 400 error, but we're not parsing it properly
   - Error message doesn't get passed back to frontend clearly
   - No retry with fixed YAML

---

## Solution Strategy

### Phase 1: Entity ID Validation (IMMEDIATE)

**Goal:** Validate all entity_id values before sending to Home Assistant

#### 1.1 Create Entity ID Validator

```python
class EntityIDValidator:
    """Validates entity_id values in YAML structure"""
    
    def validate_entity_ids(self, yaml_data: Dict) -> ValidationResult:
        """
        Recursively validate all entity_id values in YAML.
        
        Checks:
        - Not None
        - Not empty string
        - Is a string type
        - Matches domain.entity format
        - Exists in validated entities list (optional)
        """
        errors = []
        warnings = []
        
        # Extract all entity IDs from YAML
        entity_ids = self._extract_all_entity_ids(yaml_data)
        
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
            if '.' not in entity_id or entity_id.count('.') != 1:
                errors.append(
                    f"❌ {location}: entity_id '{entity_id}' doesn't match format 'domain.entity'"
                )
                continue
            
            # Check domain is valid
            domain = entity_id.split('.')[0]
            if not domain or domain[0].isdigit():
                errors.append(
                    f"❌ {location}: Invalid domain in entity_id '{entity_id}'"
                )
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def _extract_all_entity_ids(self, yaml_data: Dict, path: str = "") -> List[Tuple[str, str]]:
        """Recursively extract all entity_id values with their locations"""
        entity_ids = []
        
        # Check triggers
        triggers = yaml_data.get('trigger', [])
        for i, trigger in enumerate(triggers):
            if isinstance(trigger, dict):
                entity_id = trigger.get('entity_id')
                if entity_id:
                    entity_ids.append((entity_id, f"trigger[{i}].entity_id"))
        
        # Check actions (recursive)
        actions = yaml_data.get('action', [])
        entity_ids.extend(self._extract_from_actions(actions, "action"))
        
        # Check conditions
        conditions = yaml_data.get('condition', [])
        for i, condition in enumerate(conditions):
            if isinstance(condition, dict):
                entity_id = condition.get('entity_id')
                if entity_id:
                    entity_ids.append((entity_id, f"condition[{i}].entity_id"))
        
        return entity_ids
    
    def _extract_from_actions(self, actions: Any, base_path: str) -> List[Tuple[str, str]]:
        """Recursively extract entity_ids from action structures"""
        entity_ids = []
        
        if isinstance(actions, list):
            for i, action in enumerate(actions):
                path = f"{base_path}[{i}]"
                entity_ids.extend(self._extract_from_action(action, path))
        elif isinstance(actions, dict):
            entity_ids.extend(self._extract_from_action(actions, base_path))
        
        return entity_ids
    
    def _extract_from_action(self, action: Any, path: str) -> List[Tuple[str, str]]:
        """Extract entity_id from a single action, handling nested structures"""
        entity_ids = []
        
        if not isinstance(action, dict):
            return entity_ids
        
        # Check target.entity_id (single)
        target = action.get('target', {})
        if isinstance(target, dict):
            entity_id = target.get('entity_id')
            if entity_id:
                if isinstance(entity_id, str):
                    entity_ids.append((entity_id, f"{path}.target.entity_id"))
                elif isinstance(entity_id, list):
                    for j, eid in enumerate(entity_id):
                        entity_ids.append((eid, f"{path}.target.entity_id[{j}]"))
        
        # Check direct entity_id
        entity_id = action.get('entity_id')
        if entity_id:
            if isinstance(entity_id, str):
                entity_ids.append((entity_id, f"{path}.entity_id"))
            elif isinstance(entity_id, list):
                for j, eid in enumerate(entity_id):
                    entity_ids.append((eid, f"{path}.entity_id[{j}]"))
        
        # Check sequence (nested)
        if 'sequence' in action:
            sequence = action['sequence']
            entity_ids.extend(self._extract_from_actions(sequence, f"{path}.sequence"))
        
        # Check repeat.sequence (nested)
        if 'repeat' in action:
            repeat = action['repeat']
            if isinstance(repeat, dict) and 'sequence' in repeat:
                sequence = repeat['sequence']
                entity_ids.extend(self._extract_from_actions(sequence, f"{path}.repeat.sequence"))
        
        # Check choose branches
        if 'choose' in action:
            choose = action['choose']
            if isinstance(choose, list):
                for i, branch in enumerate(choose):
                    if isinstance(branch, dict) and 'sequence' in branch:
                        sequence = branch['sequence']
                        entity_ids.extend(
                            self._extract_from_actions(sequence, f"{path}.choose[{i}].sequence")
                        )
        
        return entity_ids
```

#### 1.2 Integrate into YAML Generation

```python
# After YAML structure validation
from ..services.entity_id_validator import EntityIDValidator

entity_validator = EntityIDValidator()
entity_validation = entity_validator.validate_entity_ids(yaml.safe_load(yaml_content))

if not entity_validation.is_valid:
    logger.error("❌ Entity ID validation failed:")
    for error in entity_validation.errors:
        logger.error(f"  {error}")
    
    # Don't proceed if entity IDs are invalid
    raise ValueError(f"Invalid entity IDs in YAML: {entity_validation.errors}")
```

### Phase 2: Enhanced Error Handling

**Goal:** Better error messages and handling of HA API errors

#### 2.1 Parse HA API Errors

```python
async def create_automation(self, automation_yaml: str) -> Dict[str, Any]:
    try:
        # ... existing code ...
    except aiohttp.ClientResponseError as e:
        if e.status == 400:
            # Try to parse error message
            error_data = {}
            try:
                error_data = await e.response.json()
            except:
                error_data = {"message": str(e)}
            
            error_message = error_data.get('message', str(e))
            
            # Extract path from error message if available
            # e.g., "data['actions'][0]['sequence'][1]['target']['entity_id']"
            logger.error(f"❌ HA API validation error: {error_message}")
            
            raise AutomationValidationError(
                status_code=400,
                message=error_message,
                path=self._extract_path_from_error(error_message),
                yaml_section=self._extract_yaml_section(automation_yaml, error_message)
            )
        else:
            raise
```

#### 2.2 Return Better Error Messages

```python
except Exception as e:
    logger.error(f"❌ Failed to create automation: {e}", exc_info=True)
    
    # Check if it's a validation error
    if isinstance(e, AutomationValidationError):
        return {
            'status': 'blocked',
            'safe': False,
            'message': f'Automation validation failed: {e.message}',
            'error_details': {
                'path': e.path,
                'yaml_section': e.yaml_section,
                'full_error': str(e)
            },
            'warnings': []
        }
    
    # Generic error
    return {
        'status': 'error',
        'safe': False,
        'message': f'Failed to create automation: {str(e)}',
        'warnings': []
    }
```

### Phase 3: Pre-Flight YAML Validation

**Goal:** Validate YAML structure matches HA requirements before sending

#### 3.1 HA-Compatible YAML Validator

```python
def validate_ha_compatibility(self, yaml_data: Dict) -> ValidationResult:
    """
    Validate YAML is compatible with Home Assistant's automation schema.
    
    Specifically checks:
    - entity_id values are valid in all nested structures
    - Required fields are present
    - Field types match expected types
    """
    errors = []
    
    # Use EntityIDValidator to check all entity_ids
    entity_validator = EntityIDValidator()
    entity_result = entity_validator.validate_entity_ids(yaml_data)
    errors.extend(entity_result.errors)
    
    # Check that sequences have valid structure
    actions = yaml_data.get('action', [])
    for i, action in enumerate(actions):
        if isinstance(action, dict) and 'sequence' in action:
            sequence = action['sequence']
            if not isinstance(sequence, list):
                errors.append(f"❌ action[{i}].sequence must be a list")
            elif len(sequence) == 0:
                errors.append(f"❌ action[{i}].sequence cannot be empty")
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=entity_result.warnings
    )
```

---

## Implementation Steps

### Step 1: Create Entity ID Validator (HIGH PRIORITY)

**File:** `services/ai-automation-service/src/services/entity_id_validator.py` (NEW)

**Time:** 1 hour

### Step 2: Integrate Entity ID Validation

**File:** `services/ai-automation-service/src/api/ask_ai_router.py`

**Changes:**
1. Add entity ID validation after YAML structure validation
2. Fail fast if entity IDs are invalid
3. Log specific entity ID errors

**Time:** 30 minutes

### Step 3: Enhance Error Handling

**File:** `services/ai-automation-service/src/api/ask_ai_router.py`

**Changes:**
1. Parse HA API error messages
2. Extract path information from errors
3. Return detailed error messages to frontend

**Time:** 45 minutes

### Step 4: Add Pre-Flight Validation

**File:** `services/ai-automation-service/src/services/yaml_structure_validator.py`

**Changes:**
1. Add HA compatibility validation
2. Check nested structures
3. Validate all entity IDs before sending

**Time:** 30 minutes

---

## Testing Strategy

### Test Cases

1. **None Entity ID:**
   ```yaml
   action:
     - service: light.turn_on
       target:
         entity_id: null  # Should be caught
   ```

2. **Empty Entity ID:**
   ```yaml
   action:
     - service: light.turn_on
       target:
         entity_id: ""  # Should be caught
   ```

3. **Invalid Type:**
   ```yaml
   action:
     - service: light.turn_on
       target:
         entity_id: [light.office]  # Should be caught if wrong context
   ```

4. **Nested Sequence:**
   ```yaml
   action:
     - sequence:
         - service: light.turn_on
           target:
             entity_id: null  # Should be caught
   ```

5. **Repeat Sequence:**
   ```yaml
   action:
     - repeat:
         sequence:
           - service: light.turn_on
             target:
               entity_id: ""  # Should be caught
   ```

---

## Success Criteria

1. ✅ All entity_id values validated before sending to HA
2. ✅ Clear error messages identifying which entity_id is invalid
3. ✅ No 400 errors from HA due to invalid entity_id values
4. ✅ Better error messages returned to frontend
5. ✅ Nested structures (sequences, repeats) validated correctly

---

## Next Steps

1. Implement Entity ID Validator
2. Integrate into YAML generation pipeline
3. Enhance error handling
4. Test with problematic YAML
5. Deploy and monitor

