# YAML Accuracy Fix Plan - 100% Accuracy Strategy

**Date:** November 1, 2025  
**Status:** Analysis Complete - Ready for Implementation  
**Priority:** CRITICAL

---

## Problem Analysis

### Issues Found in Generated YAML

```yaml
# ❌ CURRENT (BROKEN) YAML:
triggers:                    # Wrong key name
  - entity_id: binary_sensor.office_motion
    to: "on"
    trigger: state           # Wrong: should be "platform: state"

actions:                     # Wrong: should be "action:"
  - sequence:
      - target:
          entity_id: light.office
        data:
          transition: 5
          color_name: natural_light
        action: light.turn_on  # ❌ WRONG: should be "service: light.turn_on"
```

### Root Causes Identified

1. **Trigger Structure Error:**
   - Generated: `trigger: state`
   - Required: `platform: state`
   - Issue: LLM is using wrong key name

2. **Action Field Error:**
   - Generated: `action: light.turn_on` inside sequence items
   - Required: `service: light.turn_on`
   - Issue: LLM confusing `action:` (top-level) with `service:` (inside actions)

3. **Key Name Errors:**
   - Generated: `triggers:` (plural) and `actions:` (plural)
   - Required: `trigger:` (singular) and `action:` (singular)
   - Issue: LLM using plural forms

4. **Structure Issues:**
   - Generated: `actions:` with `sequence:` inside
   - Required: `action:` with list of actions or `sequence:` directly
   - Issue: Incorrect nesting structure

---

## Root Cause: LLM Prompt Issues

### Current Prompt Problems

1. **Insufficient Examples:**
   - Examples show correct structure but LLM still makes mistakes
   - Need MORE examples showing sequence structure specifically

2. **Missing Explicit Warnings:**
   - Prompt doesn't explicitly warn against common mistakes
   - No examples of WRONG structure to avoid

3. **Service vs Action Confusion:**
   - Prompt doesn't clearly distinguish `action:` (top-level) vs `service:` (inside actions)

4. **No Post-Generation Validation:**
   - No YAML structure validation after generation
   - No parsing check to catch structural errors

---

## Solution Strategy: 100% Accuracy

### Phase 1: Enhanced Prompt Engineering (High Priority)

**Goal:** Make the prompt bulletproof so LLM generates correct YAML 99%+ of the time

#### 1.1 Add Explicit Error Examples

```python
COMMON MISTAKES - DO NOT DO THIS:
❌ WRONG: trigger: state
✅ CORRECT: platform: state

❌ WRONG: triggers: (plural)
✅ CORRECT: trigger: (singular)

❌ WRONG: actions: (plural)
✅ CORRECT: action: (singular)

❌ WRONG (inside sequence):
  - action: light.turn_on
✅ CORRECT (inside sequence):
  - service: light.turn_on

❌ WRONG: 
action:
  - sequence:
      - action: light.turn_on
✅ CORRECT:
action:
  - service: light.turn_on
  # OR with sequence:
action:
  - sequence:
      - service: light.turn_on
```

#### 1.2 Add Sequence-Specific Examples

Add detailed examples showing:
- Simple action list (no sequence)
- Sequence with multiple services
- Sequence with delay
- Sequence with repeat
- Nested sequences

#### 1.3 Strengthen System Prompt

```python
system_prompt = """You are a Home Assistant YAML expert. You MUST:

1. ALWAYS use 'platform:' not 'trigger:' in triggers
2. ALWAYS use 'service:' not 'action:' inside action lists
3. ALWAYS use singular: 'trigger:' and 'action:' (not plural)
4. ALWAYS validate structure matches Home Assistant requirements
5. Return ONLY valid YAML, no explanations"""
```

### Phase 2: Post-Generation YAML Validation

**Goal:** Catch structural errors immediately after generation

#### 2.1 YAML Structure Validator

Create `YAMLStructureValidator` class:

```python
class YAMLStructureValidator:
    """Validates YAML structure against Home Assistant requirements"""
    
    def validate(self, yaml_str: str) -> ValidationResult:
        """
        Validate YAML structure.
        
        Returns:
            ValidationResult with:
            - is_valid: bool
            - errors: List[str]
            - warnings: List[str]
            - fixed_yaml: Optional[str] (auto-fixed version)
        """
        errors = []
        warnings = []
        
        # Parse YAML
        try:
            data = yaml.safe_load(yaml_str)
        except yaml.YAMLError as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"YAML parse error: {e}"],
                warnings=[],
                fixed_yaml=None
            )
        
        # Check top-level keys
        if 'triggers' in data:
            errors.append("❌ Found 'triggers:' (plural) - should be 'trigger:' (singular)")
        
        if 'actions' in data:
            errors.append("❌ Found 'actions:' (plural) - should be 'action:' (singular)")
        
        # Check trigger structure
        triggers = data.get('trigger', [])
        for i, trigger in enumerate(triggers):
            if 'trigger' in trigger:
                errors.append(f"❌ Trigger {i}: Found 'trigger: state' - should be 'platform: state'")
        
        # Check action structure
        actions = data.get('action', [])
        for i, action in enumerate(actions):
            # Check if action has wrong 'action:' field
            if isinstance(action, dict) and 'action' in action:
                errors.append(f"❌ Action {i}: Found 'action:' inside action - should be 'service:'")
            
            # Check sequence structure
            if isinstance(action, dict) and 'sequence' in action:
                sequence = action['sequence']
                for j, seq_item in enumerate(sequence):
                    if isinstance(seq_item, dict) and 'action' in seq_item:
                        errors.append(
                            f"❌ Action {i}, sequence item {j}: Found 'action:' - should be 'service:'"
                        )
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            fixed_yaml=self._auto_fix(yaml_str, errors) if errors else None
        )
    
    def _auto_fix(self, yaml_str: str, errors: List[str]) -> str:
        """
        Attempt to auto-fix common YAML structure errors.
        
        Returns:
            Fixed YAML string
        """
        fixed = yaml_str
        
        # Fix plural keys
        fixed = re.sub(r'^triggers:', 'trigger:', fixed, flags=re.MULTILINE)
        fixed = re.sub(r'^actions:', 'action:', fixed, flags=re.MULTILINE)
        
        # Fix trigger: state → platform: state
        fixed = re.sub(r'(\s+)trigger:\s*state', r'\1platform: state', fixed)
        
        # Fix action: inside sequence → service:
        # This is more complex, need to be careful with indentation
        # For now, return original if too complex
        # TODO: Implement proper sequence action fixing
        
        return fixed
```

#### 2.2 Integration into YAML Generation

```python
async def generate_automation_yaml(...) -> str:
    # ... existing generation logic ...
    
    yaml_content = response.choices[0].message.content
    
    # Validate structure
    validator = YAMLStructureValidator()
    validation = validator.validate(yaml_content)
    
    if not validation.is_valid:
        logger.error(f"❌ YAML structure validation failed: {validation.errors}")
        
        # Try auto-fix
        if validation.fixed_yaml:
            logger.info("🔧 Attempting to auto-fix YAML structure...")
            fixed_validation = validator.validate(validation.fixed_yaml)
            if fixed_validation.is_valid:
                logger.info("✅ Auto-fix successful!")
                return validation.fixed_yaml
            else:
                logger.warning(f"⚠️ Auto-fix incomplete: {fixed_validation.errors}")
        
        # If auto-fix fails, regenerate with stricter prompt
        logger.info("🔄 Regenerating YAML with stricter validation prompt...")
        yaml_content = await _regenerate_with_strict_validation(...)
    
    return yaml_content
```

### Phase 3: Regeneration with Error Feedback

**Goal:** If validation fails, regenerate with explicit error feedback

```python
async def _regenerate_with_strict_validation(
    original_prompt: str,
    validation_errors: List[str],
    openai_client
) -> str:
    """
    Regenerate YAML with explicit error feedback.
    
    This gives the LLM a second chance to fix structural errors.
    """
    error_feedback = "\n".join([f"- {error}" for error in validation_errors])
    
    strict_prompt = f"""
{original_prompt}

⚠️ PREVIOUS GENERATION HAD ERRORS - PLEASE FIX:

{error_feedback}

CRITICAL: The YAML you generate MUST:
1. Use 'platform:' not 'trigger:' in triggers
2. Use 'service:' not 'action:' inside action lists  
3. Use singular keys: 'trigger:' and 'action:'
4. Follow the structure examples EXACTLY

Generate the corrected YAML now:
"""
    
    response = await openai_client.client.chat.completions.create(...)
    return response.choices[0].message.content
```

### Phase 4: Home Assistant API Validation

**Goal:** Use Home Assistant's own validation to ensure YAML is 100% correct

```python
async def validate_with_home_assistant(
    yaml_content: str,
    ha_client: HomeAssistantClient
) -> Dict[str, Any]:
    """
    Validate YAML by attempting to parse it with Home Assistant's config validator.
    
    This is the ultimate validation - if HA can parse it, it's correct.
    """
    try:
        # Use HA's config validation endpoint if available
        # Or create a test automation and validate
        validation_result = await ha_client.validate_automation_yaml(yaml_content)
        return {
            'is_valid': True,
            'errors': [],
            'warnings': validation_result.get('warnings', [])
        }
    except Exception as e:
        return {
            'is_valid': False,
            'errors': [str(e)],
            'warnings': []
        }
```

---

## Implementation Plan

### Step 1: Enhanced Prompt (IMMEDIATE)

**File:** `services/ai-automation-service/src/api/ask_ai_router.py`

**Changes:**
1. Add explicit error examples section
2. Add sequence-specific examples
3. Strengthen system prompt
4. Add explicit field name requirements

**Time Estimate:** 30 minutes

### Step 2: YAML Structure Validator

**File:** `services/ai-automation-service/src/services/yaml_structure_validator.py` (NEW)

**Changes:**
1. Create `YAMLStructureValidator` class
2. Implement validation logic
3. Implement auto-fix logic (basic cases)
4. Add unit tests

**Time Estimate:** 2 hours

### Step 3: Integration

**File:** `services/ai-automation-service/src/api/ask_ai_router.py`

**Changes:**
1. Integrate validator into `generate_automation_yaml`
2. Add regeneration logic with error feedback
3. Add logging for validation failures

**Time Estimate:** 1 hour

### Step 4: HA API Validation (Optional Enhancement)

**File:** `services/ai-automation-service/src/clients/ha_client.py`

**Changes:**
1. Add `validate_automation_yaml` method
2. Use HA's config validation if available

**Time Estimate:** 1 hour (if HA supports it)

---

## Testing Strategy

### Test Cases

1. **Trigger Structure:**
   - ✅ Test: `platform: state` (correct)
   - ❌ Test: `trigger: state` (should be caught and fixed)

2. **Action Structure:**
   - ✅ Test: `service: light.turn_on` in action list
   - ❌ Test: `action: light.turn_on` (should be caught and fixed)

3. **Plural Keys:**
   - ✅ Test: `trigger:` and `action:` (singular)
   - ❌ Test: `triggers:` and `actions:` (should be caught and fixed)

4. **Sequence Structure:**
   - ✅ Test: Sequence with `service:` inside
   - ❌ Test: Sequence with `action:` inside (should be caught and fixed)

5. **Complex Automation:**
   - ✅ Test: Multi-step automation with sequences, delays, repeats
   - Verify all structure is correct

---

## Success Criteria

1. ✅ **Prompt Accuracy:** 99%+ of first-generation YAML is structurally correct
2. ✅ **Validation Coverage:** 100% of generated YAML is validated
3. ✅ **Auto-Fix Rate:** 90%+ of structural errors are auto-fixable
4. ✅ **User Experience:** Zero manual YAML editing required
5. ✅ **Error Detection:** All structural errors caught before deployment

---

## Rollout Plan

1. **Phase 1 (Today):** Enhanced prompt - deploy immediately
2. **Phase 2 (Today):** Basic validator - deploy after testing
3. **Phase 3 (Today):** Full integration - deploy after validation
4. **Phase 4 (Future):** HA API validation - if needed

---

## Monitoring

Track:
- YAML validation failure rate
- Auto-fix success rate
- Regeneration rate
- User-reported YAML errors
- HA automation creation success rate

---

## Next Steps

1. ✅ Create enhanced prompt with explicit error examples
2. ✅ Implement YAML structure validator
3. ✅ Integrate validation into generation pipeline
4. ✅ Test with real queries
5. ✅ Monitor validation metrics

