# Scoring System Fixes - Complete Implementation Guide

**Date:** January 2025  
**Status:** ✅ All Fixes Identified - Ready for Manual Application

---

## Summary of All Fixes

I've identified **8 critical fixes** needed in the scoring system. Due to tool limitations, here's a complete guide for applying them manually.

---

## Fix 1: Prompt ID Matching (Lines 308-315)

**Current (WRONG):**
```python
match prompt_id:
    case "prompt-4-very-complex":
        return Scorer._score_wled_prompt(yaml_data, yaml_str)
    case "prompt-5-extremely-complex":
        return Scorer._score_complex_logic_prompt(yaml_data, yaml_str, prompt)
```

**Fixed:**
```python
match prompt_id:
    case "prompt-12-very-complex":  # FIXED: Correct prompt ID for WLED state restoration prompt
        return Scorer._score_wled_prompt(yaml_data, yaml_str)
    case "prompt-14-extremely-complex":  # FIXED: Correct prompt ID for complex conditional logic prompt
        return Scorer._score_complex_logic_prompt(yaml_data, yaml_str, prompt)
```

**Impact:** Prompt-specific scoring never runs because IDs don't match!

---

## Fix 2: Entity Detection Bug (Lines 365-382)

**Current (WRONG - filters out valid light entities):**
```python
entity_pattern = r'\b\w+\.\w+\b'
entities_found = re.findall(entity_pattern, yaml_str)
valid_entities = [e for e in entities_found if not e.startswith(('scene.', 'light.', 'service:'))]
```

**Fixed:**
```python
# Check for entity IDs in format domain.entity - FIXED: Include all valid HA domains
valid_entity_pattern = r'\b(light|switch|sensor|binary_sensor|climate|media_player|cover|fan|lock|vacuum|camera|device_tracker|person|zone|input_|automation|script|scene)\.\w+\b'
entities_found = re.findall(valid_entity_pattern, yaml_str)
# Filter out service calls only (light.* entities are VALID!)
valid_entities = [e for e in entities_found if not e.startswith('service:')]
```

**Impact:** Light entities like `light.wled_office` are incorrectly filtered out!

---

## Fix 3: Score Overflow (Lines 325-347)

**Current (WRONG - can exceed 100):**
```python
# Check 1: 25 points + 5 bonus = 30
# Check 2: 25 points + 5 bonus = 30
# Check 3: 20 points
# Check 4: 20 points
# Check 5: 20 points
# Total: 120 points!
```

**Fixed:**
```python
# Check 1: Has valid trigger (20 points) - FIXED: Reduced to prevent score overflow
if isinstance(trigger, list) and len(trigger) > 0:
    score += 20.0  # Changed from 25.0
    # Bonus: Multiple triggers (5 points)
    if len(trigger) > 1:
        score += 5.0

# Check 2: Has valid actions (20 points) - FIXED: Reduced to prevent score overflow
if isinstance(action, list) and len(action) > 0:
    score += 20.0  # Changed from 25.0
    # Bonus: Multiple actions (5 points)
    if len(action) > 1:
        score += 5.0
```

**Impact:** Scores can exceed 100, making comparisons inconsistent.

---

## Fix 4: YAML Entity Format Check (Line 648)

**Current (WRONG - only checks light.*):**
```python
if re.search(r'light\.\w+|entity_id:\s*light\.\w+', yaml_str):
```

**Fixed:**
```python
# Check for all valid Home Assistant entity domains
entity_pattern = r'\b(light|switch|sensor|binary_sensor|climate|media_player|cover|fan|lock|vacuum|camera|device_tracker|person|zone|input_|automation|script|scene)\.\w+\b'
if re.search(entity_pattern, yaml_str):
```

**Impact:** Valid automations using non-light entities get penalized.

---

## Fix 5: WLED Prompt - Time Pattern (Line 416)

**Current (FRAGILE):**
```python
if '/15' in minutes:
```

**Fixed:**
```python
# Check for '/15' or '*/15' pattern (every 15 minutes)
if '/15' in minutes or '*/15' in minutes or minutes == '*/15':
```

**Impact:** More robust pattern matching for time intervals.

---

## Fix 6: WLED Prompt - Duration Check (Line 445)

**Current (WRONG - matches "15 minutes" incorrectly):**
```python
return '15' in delay or '00:00:15' in delay
```

**Fixed:**
```python
# Check for exactly 15 seconds: '00:00:15' or '15' (seconds) or 15.0 (float)
return '00:00:15' in delay or delay.strip() == '15' or delay.strip() == '15.0'
```

**Impact:** Prevents false positives from "15 minutes" or "150 seconds".

---

## Fix 7: WLED Prompt - Brightness Check (Line 457)

**Current (WRONG - only handles strings):**
```python
return str(data.get('brightness_pct', '')) == '100'
```

**Fixed:**
```python
brightness = data.get('brightness_pct', '')
# Handle both string '100' and int 100
return str(brightness) == '100' or brightness == 100
```

**Impact:** Handles both YAML string and integer brightness values.

---

## Fix 8: Complex Logic Prompt - WiFi Detection (Line 512)

**Current (WRONG - matches comments):**
```python
if platform in ['device_tracker', 'zone'] or 'wifi' in str(t).lower():
```

**Fixed:**
```python
# Check platform field first (most reliable)
if platform in ['device_tracker', 'zone']:
    has_wifi_trigger = True
    break
# Only check entity_id field for 'wifi', not entire dict (avoids matching comments)
entity_id = t.get('entity_id', '')
if isinstance(entity_id, str) and 'wifi' in entity_id.lower():
    has_wifi_trigger = True
    break
```

**Impact:** Prevents false positives from comments containing "wifi".

---

## Additional Optimizations

### Optimization 1: Compile Regex Patterns

Add at class level:
```python
class Scorer:
    # Compiled regex patterns for better performance
    _ENTITY_PATTERN = re.compile(r'\b(light|switch|sensor|binary_sensor|climate|media_player|cover|fan|lock|vacuum|camera|device_tracker|person|zone|input_|automation|script|scene)\.\w+\b')
    
    @staticmethod
    def _find_in_actions(actions: Any, predicate: Callable[[Any], bool]) -> bool:
        # ... existing code ...
```

Then use:
```python
entities_found = Scorer._ENTITY_PATTERN.findall(yaml_str)
```

### Optimization 2: Cache Prompt Lowercase

In `_score_generic_prompt`, cache `prompt_lower` at the start (already done).

### Optimization 3: Early Returns

Add early returns in YAML validity check:
```python
if not yaml_str:
    return 0.0
```

---

## Testing Checklist

After applying fixes, test:

- [ ] Prompt-12-very-complex uses WLED scorer
- [ ] Prompt-14-extremely-complex uses complex logic scorer
- [ ] Light entities (light.wled_office) are detected correctly
- [ ] Non-light entities (switch.kitchen) are detected correctly
- [ ] Scores don't exceed 100
- [ ] WLED prompt correctly detects 15-minute intervals
- [ ] WLED prompt correctly detects 15-second delays (not 15 minutes)
- [ ] Brightness check handles both string and int
- [ ] WiFi detection doesn't match comments

---

## File Locations

All fixes are in: `tools/ask-ai-continuous-improvement.py`

- Lines 308-315: Prompt ID matching
- Lines 325-347: Score overflow
- Lines 365-382: Entity detection
- Line 402: WLED prompt docstring
- Line 416: Time pattern matching
- Line 445: Duration check
- Line 457: Brightness check
- Line 498: Complex logic prompt docstring
- Line 512: WiFi detection
- Line 648: YAML entity format check

---

## Priority Order

1. **P0 - Critical:** Fixes 1, 2, 3 (prevent incorrect scoring)
2. **P1 - Important:** Fixes 4, 5, 6, 7 (improve accuracy)
3. **P2 - Enhancement:** Fix 8, optimizations (polish)

---

## Verification

After applying all fixes, run the script and verify:
- No scores exceed 100
- Light entities are detected
- Prompt-specific scoring works
- All tests pass

