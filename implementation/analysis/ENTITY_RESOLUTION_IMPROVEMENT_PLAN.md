# Entity Resolution Improvement Plan

**Date:** October 30, 2025  
**Problem:** Only 3 of 4 devices mapped - "Office light 4" cannot be resolved  
**Root Cause:** Numbered device matching too restrictive, doesn't handle complex entity ID patterns

## Current Issues Identified

### Issue 1: Numbered Pattern Matching is Too Restrictive
**Problem:**
- Query: "Office light 1" → Looks for patterns like `office_1`, `office_light_1`
- Reality: Entity ID is `light.hue_color_downlight_2_2` (complex manufacturer-specific naming)
- Pattern matching fails because it doesn't account for:
  - Multi-number sequences (`2_2`, `1_6`)
  - Manufacturer prefixes (`hue_color_`)
  - Non-standard numbering schemes

**Location:** `entity_validator.py:801-831` - `_build_numbered_entity_patterns()`

### Issue 2: Number Extraction Only Gets Last Number
**Problem:**
- Query: "Office light 4" → Extracts number `"4"`
- Entity: `light.hue_color_downlight_2_2` → Contains `"2_2"`, not `"4"`
- Algorithm can't match multi-number patterns

**Location:** `entity_validator.py:778-799` - `_extract_number_from_query()`

### Issue 3: Missing Fallback Strategy for Non-Existent Devices
**Problem:**
- When "Office light 4" doesn't exist, system silently fails
- No strategy to:
  - Find closest match (e.g., if only 3 lights exist)
  - Use semantic similarity for partial matches
  - Suggest alternatives to user

**Location:** `entity_validator.py:1529-1536` - Device mapping loop

### Issue 4: Friendly Name Matching Not Fully Utilized
**Problem:**
- Entity has `friendly_name: "Office Front Right"`
- Query says "Office light 1" but no matching number in friendly name
- System should use fuzzy matching on friendly names for numbered devices

**Current Implementation:** Friendly name matching exists but requires exact number match first

### Issue 5: No Multi-Number Pattern Recognition
**Problem:**
- Entity IDs like `hue_color_downlight_2_2` have two numbers
- Algorithm doesn't understand that `"2_2"` could represent positions (2nd device, 2nd position)
- No heuristics to map query number to multi-number patterns

## Proposed Improvements

### Improvement 1: Enhanced Number Pattern Matching

**Strategy:** Extract ALL numbers from query and entity IDs, then match using multiple strategies

```python
def _extract_all_numbers(self, text: str) -> List[str]:
    """
    Extract all numbers from text, including multi-number sequences.
    
    Examples:
        "Office light 4" -> ["4"]
        "light.hue_color_downlight_2_2" -> ["2", "2", "2_2"]
        "light.hue_go_1" -> ["1"]
    """
    import re
    numbers = []
    
    # Extract individual numbers
    individual = re.findall(r'\d+', text)
    numbers.extend(individual)
    
    # Extract multi-number sequences (e.g., "2_2", "1_6")
    sequences = re.findall(r'\d+[._]\d+', text)
    numbers.extend(sequences)
    
    return numbers

def _number_pattern_matches(self, query_numbers: List[str], entity_id: str, friendly_name: str = "") -> float:
    """
    Calculate match score for numbered devices using multiple strategies.
    
    Strategies:
    1. Direct number match (query "4" matches entity containing "4")
    2. Sequential match (query "4" matches "2_2" if 4th in sequence)
    3. Position-based match (query "4" matches entity at 4th position in area)
    4. Fuzzy number match (query "4" matches "3" if no "4" exists)
    
    Returns:
        Match score 0.0-1.0
    """
    entity_numbers = self._extract_all_numbers(entity_id + " " + friendly_name)
    
    # Strategy 1: Direct match
    for q_num in query_numbers:
        if q_num in entity_numbers:
            return 1.0  # Perfect match
    
    # Strategy 2: Sequential match (if query asks for 4th device, check if entity is 4th in sequence)
    # This requires area context - implement if available
    
    # Strategy 3: Position-based (check if entity is at position in sorted list)
    # Requires area filtering and sorting
    
    # Strategy 4: Fuzzy match (find closest number)
    if entity_numbers and query_numbers:
        q_num = int(query_numbers[0])
        entity_ints = [int(n.split('_')[0]) for n in entity_numbers if n.split('_')[0].isdigit()]
        if entity_ints:
            closest = min(entity_ints, key=lambda x: abs(x - q_num))
            similarity = 1.0 - (abs(closest - q_num) / max(q_num, 1))
            return max(0.0, similarity)  # Minimum 0, penalize distance
    
    return 0.0
```

### Improvement 2: Position-Based Matching for Numbered Devices

**Strategy:** When exact number match fails, use position in filtered list

```python
async def _find_by_position(
    self,
    query_number: int,
    available_entities: List[Dict[str, Any]],
    location_context: str
) -> Optional[Dict[str, Any]]:
    """
    Find entity by position in filtered list when exact number match fails.
    
    Example:
        Query: "Office light 4"
        Available: ["light.hue_go_1", "light.downlight_2_2", "light.downlight_1_6"]
        Strategy: Sort by entity_id, return 4th entity (index 3)
    """
    if not available_entities:
        return None
    
    # Sort entities by entity_id for consistent ordering
    sorted_entities = sorted(available_entities, key=lambda e: e.get('entity_id', ''))
    
    # Adjust for 0-based indexing (query "4" = index 3)
    index = query_number - 1
    
    if 0 <= index < len(sorted_entities):
        return sorted_entities[index]
    
    # If query number exceeds available entities, return last one with warning
    if query_number > len(sorted_entities):
        logger.warning(
            f"Query requests device #{query_number} but only {len(sorted_entities)} available. "
            f"Returning last device: {sorted_entities[-1].get('entity_id')}"
        )
        return sorted_entities[-1]
    
    return None
```

### Improvement 3: Semantic Similarity Fallback

**Strategy:** Use embeddings for numbered devices when exact match fails

```python
async def _find_semantic_numbered_match(
    self,
    query_term: str,  # e.g., "Office light 4"
    base_term: str,   # e.g., "office light"
    number: str,      # e.g., "4"
    available_entities: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """
    Find best match using semantic similarity when exact number match fails.
    
    Process:
    1. Remove number from query: "Office light 4" -> "Office light"
    2. Find entities matching base term semantically
    3. If multiple matches, use position-based selection (4th match)
    4. Return best candidate with confidence score
    """
    # Build semantic search query without number
    semantic_query = base_term
    
    # Use existing embedding matching to find candidates
    # Then select by position if multiple matches
    # This handles cases where numbering doesn't match exactly
```

### Improvement 4: Enhanced Friendly Name Fuzzy Matching for Numbered Devices

**Strategy:** Match on friendly name even if numbers don't match exactly

```python
def _match_numbered_device_by_friendly_name(
    self,
    query_term: str,  # "Office light 4"
    friendly_name: str,  # "Office Front Right"
    entity_id: str,
    number: str
) -> float:
    """
    Match numbered device using friendly name when exact number match fails.
    
    Strategy:
    1. Check if friendly name contains base term ("office", "light")
    2. Extract position indicators from friendly name ("Front", "Right", "Back", "Left")
    3. Map position words to numbers:
       - "Front" + "Right" = position 1
       - "Front" + "Left" = position 2
       - "Back" + "Right" = position 3
       - "Back" + "Left" = position 4
    4. Compare with query number
    
    Returns:
        Match score 0.0-1.0
    """
    position_words = {
        'front': 1, 'back': 2, 'rear': 2,
        'right': 1, 'left': 2,
        'north': 1, 'south': 2, 'east': 1, 'west': 2
    }
    
    friendly_lower = friendly_name.lower()
    detected_positions = []
    
    for word, pos in position_words.items():
        if word in friendly_lower:
            detected_positions.append(pos)
    
    # Simple heuristic: sum positions to estimate device number
    # "Front Right" = 1+1 = 2, but might be device 1
    # Better: use combination logic
    
    # For now, use fuzzy matching on base term
    base_term = query_term.rsplit(' ', 1)[0]  # Remove number
    fuzzy_score = self._fuzzy_match_score(base_term, friendly_name)
    
    return fuzzy_score * 0.7  # Weight down since number doesn't match
```

### Improvement 5: Multi-Strategy Fallback Chain

**Strategy:** Try multiple matching strategies in order of preference

```python
async def _find_best_match_with_fallbacks(
    self,
    query_term: str,
    available_entities: List[Dict[str, Any]],
    location_context: Optional[str] = None
) -> Tuple[Optional[Dict[str, Any]], float, str]:
    """
    Find best match using multiple fallback strategies.
    
    Strategy Order:
    1. Exact number + name match (highest pact)
    2. Number pattern match (direct number in entity_id)
    3. Position-based match (query number = position in filtered list)
    4. Semantic similarity match (base term without number)
    5. Friendly name fuzzy match (ignore number, match on name)
    6. Fuzzy number match (find closest number)
    
    Returns:
        Tuple of (best_match, confidence_score, strategy_used)
    """
    numbered_info = self._extract_number_from_query(query_term)
    
    if not numbered_info:
        # Use existing non-numbered matching
        return await self._find_best_match_full_chain(...)
    
    base_term,词汇 number = numbered_info
    
    # Strategy TRIES in order:
    strategies = [
        ("exact_number", self._try_exact_number_match),
        ("number_pattern", self._try_number_pattern_match),
        ("position_based", self._try_position_based_match),
        ("semantic_fallback", self._try_semantic_fallback),
        ("friendly_name_fuzzy", self._try_friendly_name_fuzzy),
        ("fuzzy_number", self._try_fuzzy_number_match),
    ]
    
    for strategy_name, strategy_func in strategies:
        match, score = await strategy_func(query_term, available_entities, base_term, number)
        if match and score >= 0.5:  # Minimum confidence threshold
            logger.info(f"✅ Matched using strategy: {strategy_name} (score: {score:.2f})")
            return match, score, strategy_name
    
    # No match found with any strategy
    return None, 0.0, "none"
```

### Improvement 6: Device Count Awareness

**Strategy:** Check how many devices exist before generating numbered names

```python
async def _get_device_count_in_area(
    self,
    domain: str,
    area_id: str
) -> int:
    """
    Get count of devices of specific domain in area.
    
    This helps validate if query number is reasonable.
    Example: If only 3 office lights exist, "Office light 4" is invalid.
    """
    entities = await self._get_available_entities(domain=domain, area_id=area_id)
    return len(entities)

async def _validate_query_number(
    self,
    query_number: int,
    domain: str,
    area_id: str,
    devices_involved: List[str]
) -> Tuple[bool, Optional[str]]:
    """
    Validate if requested device number is reasonable.
    
    Returns:
        (is_valid, warning_message)
    """
    device_count = await self._get_device_count_in_area(domain, area_id)
    
    if query_number > device_count:
        warning = (
            f"Query requests device #{query_number} but only {device_count} {domain} devices "
            f"exist in {area_id}. Will attempt to find closest match."
        )
        return False, warning
    
    return True, None
```

## Implementation Priority

### Phase 1: Quick Wins (Immediate)
1. ✅ **Enhance number pattern matching** - Extract all numbers, not just last one
2. ✅ **Position-based fallback** - Use position in filtered list when exact match fails
3. ✅ **Better logging** - Log why devices aren't matching for debugging

### Phase 2: Enhanced Matching (Next Sprint)
4. ✅ **Friendly name fuzzy matching** - Match on friendly names even without exact number
5. ✅ **Device count validation** - Warn when query number exceeds available devices
6. ✅ **Multi-strategy fallback chain** - Try multiple strategies in order

### Phase 3: Advanced Features (Future)
7. ✅ **Position word mapping** - Map "Front Right" to device numbers
8. ✅ **Semantic similarity for numbered devices** - Use embeddings for better matching
9. ✅ **User feedback** - Suggest alternatives when device not found

## Testing Strategy

### Test Cases
1. **Exact Match:** "Office light 1" → `light.hue_go_1` ✅
2. **Complex Numbering:** "Office light 2" → `light.hue_color_downlight_2_2` ❌ (needs improvement)
3. **Position Fallback:** "Office light 4" (only 3 exist) → `light.hue_color_downlight_1_6` (3rd device)
4. **Friendly Name Match:** "Office light 1" → matches "Office Front Right" by position
5. **Missing Device:** "Office light 5" → returns closest match with warning

## Expected Outcomes

**Before Improvements:**
- "Office light 4" → ❌ No match (silently dropped)

**After Improvements:**
- "Office light 4" → ✅ Matches 4th device OR closest match with warning
- Better logging explains why matches succeed/fail
- User gets feedback when device count mismatch occurs

## Research-Backed Techniques

1. **Fuzzy String Matching** (rapidfuzz) - Already implemented, enhance usage
2. **Semantic Embeddings** (sentence-transformers) - Already implemented, apply to numbered devices
3. **Position-Based Matching** - Standard technique in entity resolution
4. **Multi-Strategy Fallback** - Common pattern in NLP entity linking systems
5. **Number Normalization** - Extract and compare numbers across different formats

## Code Locations to Modify

1. `entity_validator.py:778-799` - Enhance `_extract_number_from_query()`
2. `entity_validator.py:801-831` - Enhance `_build_numbered_entity_patterns()`
3. `entity_validator.py:1181-1229` - Improve numbered device matching logic
4. `entity_validator.py:1367-1393` - Enhance `_number_matches_exactly()`
5. `ask_ai_router.py:1529-1536` - Add fallback strategies and validation

