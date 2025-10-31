# Suggestion Entity Caching Analysis

**Issue:** Entity validation is re-performed every time the test button is clicked, causing:
- Extra API calls
- Slower execution (200-500ms per test)
- Potential failures if entity names change

**Question:** Should we save `validated_entities` mapping with suggestions for faster test execution?

## Current Flow

### Suggestion Creation (`generate_suggestions_from_query`)
1. ✅ Resolves entities by location/domain
2. ✅ Enriches entities with full attributes
3. ✅ Builds entity context JSON for LLM
4. ✅ LLM generates suggestions with `devices_involved` (friendly names)
5. ❌ **Does NOT save validated_entities mapping**

### Test Execution (`test_suggestion_from_query`)
1. ❌ Re-fetches query and suggestion from DB
2. ❌ Gets `devices_involved` from suggestion
3. ❌ **Re-maps device names → entity IDs** (slow!)
4. ❌ Builds `validated_entities` mapping
5. ✅ Uses mapping for YAML generation

## What's Currently Saved

```python
{
    'suggestion_id': 'ask-ai-{uuid}',
    'description': str,
    'trigger_summary': str,
    'action_summary': str,
    'devices_involved': List[str],  # Friendly names only
    'capabilities_used': List[str],
    'confidence': float,
    'status': 'draft',
    'created_at': str
}
```

## What Should Be Saved

```python
{
    'suggestion_id': 'ask-ai-{uuid}',
    'description': str,
    'trigger_summary': str,
    'action_summary': str,
    'devices_involved': List[str],  # Friendly names
    'validated_entities': Dict[str, str],  # NEW: device_name → entity_id mapping
    'capabilities_used': List[str],
    'confidence': float,
    'status': target='draft',
    'created_at': str
}
```

## Implementation Strategy

### Option 1: Map After LLM Generation (Recommended)
After LLM generates suggestions with `devices_involved`, map those friendly names back to entity IDs using the already-resolved entities.

**Pros:**
- Uses already-resolved entities (no extra API calls)
- Fast (just dictionary lookup)
- Accurate (uses same resolution logic as enrichment)

**Cons:**
- Need to handle case where LLM invents device names not in context

### Option 2: Save Full Entity Context
Save the entire enriched entity context JSON with each suggestion.

**Pros:**
- Complete information available
- No re-fetching needed

**Cons:**
- Larger storage footprint
- May become stale if entities change

### Option 3: Hybrid Approach
Save `validated_entities` mapping + timestamp, with fallback to re-resolution if stale.

**Pros:**
- Best of both worlds
- Handles entity changes gracefully

**Cons:**
- More complex logic

## Recommended Solution: Option 1

Map `devices_involved` to entity IDs after LLM generation using already-resolved entities. This is fast and accurate.

### Implementation Steps

1. After LLM generates suggestions, for each suggestion:
   - Extract `devices_involved` (friendly names)
   - Look up each name in the enriched entity data
   - Build `validated_entities` mapping
   - Add to suggestion dict

2. Save `validated_entities` with suggestion in database

3. Update test endpoint to use saved `validated_entities`:
   - Check if `validated_entities` exists in suggestion
   - If yes, use it directly (no re-resolution)
   - If no, fall back to current re-resolution logic

### Code Changes Needed

**In `generate_suggestions_from_query()`:**
```python
# After LLM generates suggestions (line ~1000)
for suggestion in parsed:
    # Map devices_involved to entity IDs using enriched_data
    validated_entities = {}
    for device_name in suggestion.get('devices_involved', []):
        # Find matching entity by friendly_name in enriched_data
        for entity_id, enriched in enriched_data.items():
            if enriched.get('friendly_name') == device_name:
                validated_entities[device вполне] = entity_id
                break
    
    suggestions.append({
        # ... existing fields ...
        'validated_entities': validated_entities  # NEW
    })
```

**In `test_suggestion_from_query()`:**
```python
# Check if validated_entities already exists (line ~1725)
if 'validated_entities' in suggestion and suggestion['validated_entities']:
    # Use saved mapping (FAST PATH)
    entity_mapping = suggestion['validated_entities']
    logger.info(f"Using saved validated_entities mapping")
else:
    # Fall back to re-resolution (SLOW PATH)
    logger.info(f"Re-resolving entities (validated_entities not saved)")
    # ... current re-resolution logic ...
```

## Performance Impact

### Current (Re-resolution on test)
- Entity resolution: ~200-500ms
- Total test time: ~1-2 seconds

### Optimized (Use saved mapping)
- Entity lookup: ~1-5ms (dictionary lookup)
- Total test time: ~500ms-1 second

**Improvement: ~50-75% faster test execution**

## Edge Cases to Handle

1. **LLM invents device names:** 
   - Fall back to re-resolution if name not found in enriched_data

2. **Entities changed/deleted:**
   - Validate entity IDs still exist before using saved mapping
   - Fall back to re-resolution if validation fails

3. **Group entities:**
   - Save expanded individual entity IDs (already handled in current code)

## Conclusion

**Yes, we should save `validated_entities` with suggestions** for:
- Faster test execution (50-75% improvement)
- Reduced API load
- Better user experience

Implementation is straightforward: map `devices_involved` to entity IDs after LLM generation using already-resolved entities, then use saved mapping in test endpoint.

