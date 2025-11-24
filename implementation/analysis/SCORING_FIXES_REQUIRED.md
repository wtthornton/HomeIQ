# Scoring System Fixes Required

**Date:** January 2025  
**Script:** `tools/ask-ai-continuous-improvement.py`  
**Status:** 🔧 Fixes Identified - Ready for Implementation

---

## Critical Fixes Summary

### 1. Prompt ID Mismatch (Line 309-312)

**Current:**
```python
case "prompt-4-very-complex":  # WRONG - actual ID is "prompt-12-very-complex"
    return Scorer._score_wled_prompt(yaml_data, yaml_str)
case "prompt-5-extremely-complex":  # WRONG - actual ID is "prompt-14-extremely-complex"
    return Scorer._score_complex_logic_prompt(yaml_data, yaml_str, prompt)
```

**Fix:**
```python
case "prompt-12-very-complex":  # FIXED
    return Scorer._score_wled_prompt(yaml_data, yaml_str)
case "prompt-14-extremely-complex":  # FIXED
    return Scorer._score_complex_logic_prompt(yaml_data, yaml_str, prompt)
```

**Impact:** Prompt-specific scoring never runs for these prompts!

---

### 2. Entity Detection Bug (Line 372)

**Current (WRONG):**
```python
valid_entities = [e for e in entities_found if not e.startswith(('scene.', 'light.', 'service:'))]
```

**Problem:** Filters out ALL `light.*` entities, which are VALID! Entity IDs ARE `light.wled_office`, `light.lr_ceiling`, etc.

**Fix:**
```python
# Check for actual entity patterns, not filter out valid ones
valid_entity_pattern = r'\b(light|switch|sensor|binary_sensor|climate|media_player|cover|fan|lock|vacuum|camera|device_tracker|person|zone|input_|automation|script|scene)\.\w+\b'
entities_found = re.findall(valid_entity_pattern, yaml_str)
valid_entities = [e for e in entities_found if not e.startswith('service:')]
```

**Impact:** Prompts requiring lights will never get full points for entity usage.

---

### 3. Score Overflow (Lines 325-340)

**Current:**
```python
# Check 1: 25 points + 5 bonus = 30
# Check 2: 25 points + 5 bonus = 30
# Check 3: 20 points
# Check 4: 20 points
# Check 5: 20 points
# Total: 120 points (exceeds 100!)
```

**Fix:**
```python
# Check 1: 20 points + 5 bonus = 25
# Check 2: 20 points + 5 bonus = 25
# Check 3: 20 points
# Check 4: 20 points
# Check 5: 20 points
# Total: 100 base + 10 bonus = 110 max (capped at 100)
```

**Impact:** Scoring is inconsistent - some automations can score above 100.

---

### 4. YAML Entity Format Check Too Narrow (Line 648)

**Current:**
```python
if re.search(r'light\.\w+|entity_id:\s*light\.\w+', yaml_str):
```

**Problem:** Only checks for `light.*` entities, ignores all other domains.

**Fix:**
```python
entity_pattern = r'\b(light|switch|sensor|binary_sensor|climate|media_player|cover|fan|lock|vacuum|camera|device_tracker|person|zone|input_|automation|script|scene)\.\w+\b'
if re.search(entity_pattern, yaml_str):
```

**Impact:** Valid automations using non-light entities get penalized.

---

### 5. WLED Prompt Scoring Improvements

**Line 416 - Time Pattern:**
```python
# Current: if '/15' in minutes:
# Better: Check for '/15' or '*/15' pattern
if '/15' in minutes or '*/15' in minutes or minutes == '*/15':
```

**Line 445 - Duration Check:**
```python
# Current: return '15' in delay or '00:00:15' in delay
# Better: More precise matching
return '00:00:15' in delay or delay.strip() == '15' or delay.strip() == '15.0'
```

**Line 457 - Brightness Check:**
```python
# Current: return str(data.get('brightness_pct', '')) == '100'
# Better: Handle both string and int
brightness = data.get('brightness_pct', '')
return str(brightness) == '100' or brightness == 100
```

---

### 6. Complex Logic Prompt - WiFi Detection (Line 512)

**Current:**
```python
if platform in ['device_tracker', 'zone'] or 'wifi' in str(t).lower():
```

**Problem:** `'wifi' in str(t).lower()` matches comments and other text, not just entity IDs.

**Fix:**
```python
if platform in ['device_tracker', 'zone']:
    has_wifi_trigger = True
    break
# Only check entity_id field, not entire dict
entity_id = t.get('entity_id', '')
if isinstance(entity_id, str) and 'wifi' in entity_id.lower():
    has_wifi_trigger = True
    break
```

---

## Implementation Priority

1. **P0 - Critical Bugs (Fix Immediately):**
   - Prompt ID mismatch (prevents prompt-specific scoring)
   - Entity detection bug (filters out valid entities)
   - Score overflow (inconsistent scoring)

2. **P1 - Important Fixes:**
   - YAML entity format check (too narrow)
   - WLED prompt improvements (more robust matching)

3. **P2 - Enhancements:**
   - WiFi detection improvement
   - Add Home Assistant format validation (platform:, service: fields)
   - Improve time-based validation (verify times match prompt)

---

## Testing After Fixes

1. Run script with test automations
2. Verify prompt-12-very-complex uses WLED scorer
3. Verify prompt-14-extremely-complex uses complex logic scorer
4. Verify light entities are detected correctly
5. Verify scores don't exceed 100
6. Verify non-light entities pass YAML format check

---

## Files to Modify

- `tools/ask-ai-continuous-improvement.py`
  - Line 309-312: Fix prompt ID matching
  - Line 325-340: Fix score distribution
  - Line 372: Fix entity detection
  - Line 416: Improve time pattern matching
  - Line 445: Improve duration matching
  - Line 457: Handle int/string brightness
  - Line 512: Improve WiFi detection
  - Line 648: Fix entity format check

