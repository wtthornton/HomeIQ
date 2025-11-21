# YAML Generation Service Enhancement Plan

**Date:** January 2025  
**Based on:** [Official Home Assistant Automation YAML Documentation](https://www.home-assistant.io/docs/automation/yaml/)  
**Status:** 📋 Plan for Review

---

## 🚨 Critical Format Discrepancy Identified

The current implementation uses a **different format** than the official Home Assistant documentation:

### Current Implementation Format
```yaml
trigger:           # ❌ SINGULAR
  - platform: time # ❌ Uses "platform:" field
action:            # ❌ SINGULAR
  - service: light.turn_on # ❌ Uses "service:" field
```

### Official Home Assistant Format (from docs)
```yaml
triggers:          # ✅ PLURAL
  - trigger: sun   # ✅ Uses "trigger:" field
  - trigger: state
actions:           # ✅ PLURAL
  - action: homeassistant.turn_on # ✅ Uses "action:" field
  - action: light.turn_off
```

**Source:** [Home Assistant Automation YAML Docs](https://www.home-assistant.io/docs/automation/yaml/)

---

## 📋 Enhancement Plan

### Phase 1: Format Alignment (CRITICAL - High Priority)

#### 1.1 Update Top-Level Keys
**Current:** `trigger:` (singular), `action:` (singular)  
**Target:** `triggers:` (plural), `actions:` (plural)

**Files to update:**
- `services/ai-automation-service/src/services/automation/yaml_generation_service.py`
  - Line 663: Change `trigger:` → `triggers:`
  - Line 667: Change `action:` → `actions:`
  - Update all examples (lines 559, 563, 577, 581, 606, 619, etc.)
  - Update checklist (lines 749-751)
  - Update system prompts (lines 824, 944)

**Impact:** Major - affects all generated automations

#### 1.2 Update Trigger Item Field Names
**Current:** `platform: time`, `platform: state`  
**Target:** `trigger: time`, `trigger: state` (based on official docs)

**Note:** Need to verify if both formats are accepted. The docs show `trigger: sun`, `trigger: state`, but many examples use `platform:`. May need to test which format Home Assistant API accepts.

**Files to update:**
- All trigger examples in the prompt
- Validator may need updates if it expects `platform:` format

**Impact:** Medium - needs verification with actual HA API

#### 1.3 Update Action Item Field Names
**Current:** `service: light.turn_on`  
**Target:** `action: light.turn_on` (based on official docs)

**Note:** Same verification needed - docs show `action:`, but `service:` is commonly used. May be format variation.

**Files to update:**
- All action examples in the prompt
- Validator may need updates

**Impact:** Medium - needs verification with actual HA API

#### 1.4 Update Validation Checklist
Update checklist to reflect correct format:
- Change "trigger:" (singular) → "triggers:" (plural)
- Change "action:" (singular) → "actions:" (plural)
- Update field name expectations

---

### Phase 2: Additional Features from Official Docs

#### 2.1 Support Labeled Automation Blocks
The docs show support for labeled automation blocks in `configuration.yaml`:
```yaml
automation kitchen:
  - triggers:
      - trigger: ...
```

**Current:** Only generates single automation format  
**Enhancement:** Support labeled blocks for batch automation generation

**Priority:** Low - nice to have

#### 2.2 Support Advanced Options
From official docs, add support for:

**Variables:**
```yaml
variables:
  PARAMETER_NAME: value
trigger_variables:
  PARAMETER_NAME: value
```

**Priority:** Medium - useful for complex automations

**Trace Configuration:**
```yaml
trace:
  stored_traces: 10
```

**Priority:** Low - debugging feature

**Initial State:**
```yaml
initial_state: false
```

**Priority:** Medium - useful for controlling startup behavior

**Max Configuration:**
```yaml
max: 5
max_exceeded: warning  # or silent
```

**Priority:** Medium - useful for parallel mode control

---

### Phase 3: Example Alignment

#### 3.1 Update Examples to Match Official Docs
Replace current examples with examples that match the official documentation format.

**Examples from docs to include:**
1. Sun-based trigger with conditions
2. State-based trigger
3. Zone-based trigger with conditions
4. Event-based trigger (custom events like Xiaomi cube)

**Files to update:**
- `yaml_generation_service.py` examples section
- Keep examples realistic and relevant to common use cases

---

### Phase 4: Format Verification & Testing

#### 4.1 Verify Format Compatibility
**Critical:** Test which format Home Assistant API actually accepts:
- Test `triggers:` vs `trigger:`
- Test `trigger:` field vs `platform:` field in triggers
- Test `action:` field vs `service:` field in actions

**Approach:**
- Create test automations using both formats
- Check which ones are accepted by HA API
- Document the correct format based on API response

#### 4.2 Update Validator
If format changes, update `YAMLStructureValidator` to:
- Validate correct format (plural keys)
- Auto-fix incorrect format if possible
- Provide clear error messages

---

### Phase 5: Documentation Improvements

#### 5.1 Add Format Reference
Add a section in the prompt that clearly shows the format difference:
- When to use labeled blocks vs list format
- Format variations (if both are accepted)
- Link to official documentation

#### 5.2 Improve Error Messages
If format is wrong, provide clearer error messages pointing to:
- Official documentation
- Correct format example
- Common mistakes

---

## 🔍 Research Needed

### Critical Questions:
1. **Does Home Assistant accept both formats?**
   - `trigger:` vs `triggers:`?
   - `platform:` vs `trigger:` field?
   - `service:` vs `action:` field?

2. **Is the format context-dependent?**
   - Different for `automations.yaml` vs `configuration.yaml`?
   - Different for labeled blocks vs list format?

3. **What does the HA API actually accept?**
   - Need to test with actual API calls
   - Check validator responses

---

## 📊 Implementation Priority

### 🔴 Critical (Must Fix)
1. **Format Verification** - Test what HA API actually accepts
2. **Top-Level Keys** - Update `trigger:` → `triggers:`, `action:` → `actions:` (if verified)
3. **Update Examples** - Align with verified format

### 🟡 High Priority (Should Fix)
1. **Update Checklist** - Reflect correct format
2. **Update System Prompts** - Use correct format instructions
3. **Update Validator** - Validate correct format

### 🟢 Medium Priority (Nice to Have)
1. **Support Variables** - Add variable support
2. **Support Initial State** - Add initial_state option
3. **Support Max Config** - Add max/max_exceeded options

### ⚪ Low Priority (Future)
1. **Labeled Blocks** - Support labeled automation blocks
2. **Trace Config** - Add trace configuration
3. **Advanced Documentation** - More detailed format docs

---

## 🧪 Testing Plan

### Phase 1 Testing:
1. Generate test automation with current format
2. Generate test automation with official doc format
3. Submit both to HA API
4. Document which format(s) are accepted

### Phase 2 Testing:
1. Generate automations with new features (variables, initial_state, etc.)
2. Verify HA API accepts them
3. Test edge cases

---

## 📝 Notes

- The official documentation may show one format, but the API might accept variations
- Need to test actual HA API behavior, not just rely on documentation
- Consider backward compatibility if format changes
- May need to support multiple formats if both are valid

---

## 🔗 References

- [Official Home Assistant Automation YAML Documentation](https://www.home-assistant.io/docs/automation/yaml/)
- Current implementation: `services/ai-automation-service/src/services/automation/yaml_generation_service.py`
- Validator: `services/ai-automation-service/src/services/yaml_structure_validator.py`

