# Scoring System Review - Ask AI Continuous Improvement

**Date:** January 2025  
**Script:** `tools/ask-ai-continuous-improvement.py`  
**Status:** 🔍 Analysis Complete - Issues Identified

---

## Executive Summary

The scoring system has **several critical flaws** that prevent accurate assessment of automation quality:

1. **Entity Detection Bug** - Filters out valid entity IDs
2. **Score Overflow** - Can exceed 100 points
3. **Insufficient Validation** - Doesn't verify Home Assistant format compliance
4. **Weak Conditional Logic Checks** - Only checks existence, not correctness
5. **YAML Validity Too Lenient** - Doesn't validate actual HA structure requirements

---

## Detailed Analysis

### 1. Automation Correctness Scoring (`_score_generic_prompt`)

#### Current Implementation
```python
# Check 1: Valid trigger (25 points) + bonus (5 points)
# Check 2: Valid actions (25 points) + bonus (5 points)  
# Check 3: Time-based requirements (20 points)
# Check 4: Device/entity usage (20 points)
# Check 5: Conditional logic (20 points)
# Total: 95-100+ points (can exceed 100!)
```

#### Issues Identified

**🔴 CRITICAL BUG: Entity Detection Logic (Line 372)**
```python
valid_entities = [e for e in entities_found if not e.startswith(('scene.', 'light.', 'service:'))]
```
**Problem:** This filters out ALL `light.*` entity IDs, which are VALID! Entity IDs ARE in the format `light.wled_office`, `light.lr_ceiling`, etc.

**Impact:** Prompts requiring lights will never get full points for entity usage, even when correct.

**Fix Required:**
```python
# Should check for actual entity patterns, not filter out valid ones
# Valid: light.wled_office, switch.kitchen, sensor.temperature
# Invalid: scene.create, light.turn_on (service calls)
valid_entities = [
    e for e in entities_found 
    if re.match(r'^(light|switch|sensor|binary_sensor|climate|media_player|cover|fan|lock|vacuum|camera|device_tracker|person|zone|input_|automation|script|scene)\.\w+$', e)
    and not e.startswith('service:')
]
```

**🔴 Score Overflow Issue (Lines 325-395)**
- Base score: 25 + 25 + 20 + 20 + 20 = 110 points
- With bonuses: 110 + 5 + 5 = 120 points
- Code uses `min(score, max_score)` but this masks the real issue

**Impact:** Scoring is inconsistent - some automations can score above 100, others capped at 100.

**Fix Required:** Redistribute points so base score = 100, bonuses are extra credit OR reduce base points.

**🟡 Weak Time-Based Detection (Lines 349-363)**
```python
if any(keyword in prompt_lower for keyword in time_keywords):
    # Only checks if time trigger exists, not if it's CORRECT
```
**Problem:** 
- Doesn't verify the time matches the prompt (e.g., prompt says "7:00 AM" but automation uses "8:00 AM")
- Doesn't check if time pattern is correct (e.g., "every 15 mins" should use `time_pattern` with `minutes: '/15'`)

**Impact:** Automations with wrong times still get points.

**🟡 Conditional Logic Check Too Simple (Lines 384-394)**
```python
if 'if' in prompt_lower or 'when' in prompt_lower or 'between' in prompt_lower:
    has_condition = (
        Scorer._find_in_actions(action, lambda a: 'condition' in a) or
        any('condition' in str(t) for t in trigger)
    )
```
**Problem:**
- Only checks if condition exists, not if it's correct
- Doesn't verify the condition matches the prompt requirement
- Example: Prompt says "if between 6 PM and 11 PM" but automation has condition for "if after 9 PM" - still gets points

**Impact:** Incorrect conditional logic still scores well.

---

### 2. YAML Validity Scoring (`score_yaml_validity`)

#### Current Implementation
```python
# Check 1: Valid YAML syntax (40 points)
# Check 2: Required fields: id, alias, trigger, action (30 points - 7.5 each)
# Check 3: Valid HA structure: trigger is list, action is list (20 points - 10 each)
# Check 4: Valid entity ID format (10 points)
# Total: 100 points
```

#### Issues Identified

**🔴 Entity ID Format Check Too Narrow (Line 648)**
```python
if re.search(r'light\.\w+|entity_id:\s*light\.\w+', yaml_str):
```
**Problem:**
- Only checks for `light.*` entities
- Ignores all other domains (switch, sensor, climate, etc.)
- Doesn't validate actual entity existence

**Impact:** Valid automations using non-light entities get penalized.

**Fix Required:**
```python
# Check for any valid entity domain
entity_pattern = r'\b(light|switch|sensor|binary_sensor|climate|media_player|cover|fan|lock|vacuum|camera|device_tracker|person|zone|input_|automation|script|scene)\.\w+\b'
if re.search(entity_pattern, yaml_str):
    score += 10.0
```

**🟡 Missing Home Assistant Format Validation**
**Problem:** Doesn't check for:
- `platform:` field in triggers (required by HA)
- `service:` field in actions (required by HA)
- Proper `target.entity_id` structure
- Valid trigger platforms (time, time_pattern, state, sun, etc.)

**Impact:** Invalid HA format automations can still score 100 on YAML validity.

**Fix Required:** Add checks for:
```python
# Check trigger format
for trigger in triggers:
    if 'platform' not in trigger:
        # Deduct points - platform is required
        score -= 5.0

# Check action format  
for action in actions:
    if 'service' not in action:
        # Deduct points - service is required
        score -= 5.0
```

**🟡 Required Fields Check Incomplete**
**Problem:** Only checks for `id, alias, trigger, action` but Home Assistant also requires:
- `trigger` must be a list (checked)
- `action` must be a list (checked)
- But doesn't verify `trigger` items have `platform:` field
- Doesn't verify `action` items have `service:` field

---

### 3. Prompt-Specific Scoring

#### WLED Prompt (`_score_wled_prompt`) - Lines 400-494

**Issues:**
1. **Line 416:** Checks for `/15` in minutes string - too fragile
   - Should check: `minutes: '/15'` or `minutes: '*/15'` or pattern matching
2. **Line 445:** Checks for `'15' in delay` - matches "15 minutes" incorrectly
   - Should check for exactly 15 seconds: `delay: '00:00:15'` or `delay: 15` (seconds)
3. **Line 457:** Checks `brightness_pct == '100'` - should handle both string and int
4. **Line 484:** Entity check uses string matching - fragile

#### Complex Logic Prompt (`_score_complex_logic_prompt`) - Lines 496-587

**Issues:**
1. **Line 512:** WiFi trigger detection too broad - `'wifi' in str(t).lower()` matches comments
2. **Line 532:** Hardcoded time check - only works for specific prompt
3. **Line 557:** Action counting doesn't verify correctness, just existence

---

### 4. Clarification Scoring

#### Current Implementation
```python
clarification_penalty = 5.0  # Reduced from 10.0
clarification_score = max(0.0, 100.0 - (clarification_count * clarification_penalty))
```

**Analysis:**
- ✅ Reasonable penalty (5 points per round)
- ✅ Allows up to 20 rounds before hitting 0
- ⚠️ Doesn't weight by question complexity
- ⚠️ Doesn't consider if questions were necessary vs. avoidable

**Recommendation:** Keep as-is, but consider:
- Weight by question type (entity selection = more penalty than confirmation)
- Consider if questions could have been avoided with better entity extraction

---

### 5. Total Score Calculation

#### Current Weights
```python
AUTOMATION_SCORE_WEIGHT = 0.5  # 50%
YAML_SCORE_WEIGHT = 0.3        # 30%
CLARIFICATION_SCORE_WEIGHT = 0.2  # 20%
```

**Analysis:**
- ✅ Reasonable distribution
- ⚠️ YAML validity should be a hard requirement (if invalid, automation won't work)
- ⚠️ Should YAML validity be pass/fail rather than weighted?

**Recommendation:**
- Consider making YAML validity a multiplier: `total = automation_score * yaml_multiplier * clarification_score`
- Where `yaml_multiplier = 1.0 if yaml_score >= 80 else 0.5` (partial credit for fixable issues)

---

## Recommended Fixes

### Priority 1: Critical Bugs

1. **Fix Entity Detection (Line 372)**
   ```python
   # Current (WRONG):
   valid_entities = [e for e in entities_found if not e.startswith(('scene.', 'light.', 'service:'))]
   
   # Fixed:
   valid_entity_pattern = r'^(light|switch|sensor|binary_sensor|climate|media_player|cover|fan|lock|vacuum|camera|device_tracker|person|zone|input_|automation|script|scene)\.\w+$'
   valid_entities = [
       e for e in entities_found 
       if re.match(valid_entity_pattern, e) and not e.startswith('service:')
   ]
   ```

2. **Fix Score Overflow (Lines 325-395)**
   ```python
   # Redistribute points:
   # Check 1: Valid trigger (20 points) + bonus (5 points)
   # Check 2: Valid actions (20 points) + bonus (5 points)
   # Check 3: Time-based requirements (20 points)
   # Check 4: Device/entity usage (20 points)
   # Check 5: Conditional logic (20 points)
   # Total: 100 base + 10 bonus = 110 max (cap at 100)
   ```

3. **Fix YAML Entity Check (Line 648)**
   ```python
   # Current (TOO NARROW):
   if re.search(r'light\.\w+|entity_id:\s*light\.\w+', yaml_str):
   
   # Fixed:
   entity_pattern = r'\b(light|switch|sensor|binary_sensor|climate|media_player|cover|fan|lock|vacuum|camera|device_tracker|person|zone|input_|automation|script|scene)\.\w+\b'
   if re.search(entity_pattern, yaml_str):
   ```

### Priority 2: Enhancements

4. **Add Home Assistant Format Validation**
   - Check for `platform:` in triggers
   - Check for `service:` in actions
   - Verify `target.entity_id` structure

5. **Improve Time-Based Validation**
   - Extract time from prompt
   - Verify automation time matches prompt time
   - Check time pattern format (e.g., `/15` for "every 15 minutes")

6. **Enhance Conditional Logic Checks**
   - Parse conditions from prompt
   - Verify automation conditions match prompt requirements
   - Check for correct condition types (time, state, numeric_state, etc.)

### Priority 3: Improvements

7. **Add Prompt-Specific Validators**
   - Create validators for each prompt complexity level
   - Check specific requirements (e.g., "weekdays only" = condition: time with weekday filter)

8. **Improve WLED Prompt Scoring**
   - Better time pattern detection
   - More robust delay parsing
   - Handle both string and int brightness values

---

## Testing Recommendations

1. **Create Test Cases:**
   - Valid automation with light entities → should score 100 on entity check
   - Invalid automation with wrong time → should NOT score on time check
   - YAML with non-light entities → should pass entity format check

2. **Add Unit Tests:**
   - Test entity detection with various entity types
   - Test score calculation with edge cases
   - Test YAML validation with invalid formats

3. **Validate Against Real Automations:**
   - Run scoring on known-good automations
   - Verify scores match expected quality
   - Identify false positives/negatives

---

## Conclusion

The scoring system has **5 critical bugs** and **several enhancement opportunities**. The most critical issues are:

1. Entity detection filtering out valid entities
2. Score overflow allowing >100 points
3. Insufficient Home Assistant format validation
4. Weak conditional logic verification

**Recommendation:** Fix Priority 1 issues immediately, then implement Priority 2 enhancements for more accurate scoring.

