# YAML Generation Invalid Entity IDs - Fix Plan

**Status**: ✅ IMPLEMENTED - Primary fix completed  
**Date**: 2025-11-02  
**Location**: `services/ai-automation-service/src/api/ask_ai_router.py:1209-1221`

## Root Cause Analysis

From the Docker logs and codebase review, I've identified the core issue:

### The Problem
The AI automation service generates YAML with invalid entity IDs that don't exist in Home Assistant, causing deployment failures with errors like:
- `binary_sensor.office_desk_presence` 
- `light.wled_led_strip`
- `light.lr_front_left_ceiling`
- etc.

### The Flow Breakdown

**Current Flow:**
```
User Query → Entity Extraction → Fake Entity IDs Generated → HA Verification Fails → No Validated Entities → LLM Makes Up More Fake IDs → YAML Generation Fails
```

**From the Logs:**
```
❌ Entity light.hue_color_downlight_1 not found in HA (ground truth)
❌ Entity light.hue_lr_back_left_ceiling not found in HA (ground truth)
...
⚠️ Could not map any of 5 devices to verified entities
⚠️ No verified entities found for suggestion
...
❌ POST-GEN VALIDATION FAILED: 7 invalid entities without replacements
ValueError: Generated YAML contains invalid entity IDs that don't exist in Home Assistant
Available validated entities: None
```

### Key Findings

1. **Entity Extraction Creates Fake IDs**: The entity extraction process generates entity IDs like `light.wled`, `light.hue_color_downlight_1_3` that don't exist in Home Assistant.

2. **Verification Removes Invalid IDs**: The `map_devices_to_entities()` function correctly removes invalid entity IDs via HA verification, but this leaves `validated_entities` empty.

3. **Empty Validated Entities**: When `validated_entities` is empty, the code should fail early but instead continues to YAML generation.

4. **LLM Makes Up Entities**: Without validated entities, the prompt includes placeholders that the LLM fills with more fake entity IDs.

5. **Post-Gen Validation Catches It**: The post-generation validation finally catches the invalid IDs and fails, but too late.

### Code Locations

1. **Entity Mapping** (`ask_ai_router.py:501-601`): `map_devices_to_entities()` function
   - Maps device names to entity IDs from enriched data
   - Verifies entities exist in HA
   - Logs: `⚠️ Could not map any of 5 devices to verified entities`

2. **Validation Checks** (`ask_ai_router.py:1160-1173`): When `validated_entities` is empty
   - Current: Sets error text but continues to YAML generation
   - Issue: Should fail early here

3. **YAML Generation** (`ask_ai_router.py:1233-1268`): Prompt building
   - Issue: When `validated_entities` is empty, uses placeholders
   - LLM fills placeholders with fake entity IDs

4. **Post-Gen Validation** (`ask_ai_router.py:1770-1825`): Final check
   - Only validation that actually fails
   - Too late to fix the underlying issue

## The Fix

### Solution 1: Fail Early When No Validated Entities ✅ IMPLEMENTED

**Primary Fix**: Modify `generate_automation_yaml()` to fail immediately when no validated entities are available, instead of continuing to YAML generation.

**Location**: `services/ai-automation-service/src/api/ask_ai_router.py` line 1209-1221

**Implementation**:
```python
# CRITICAL: Fail early if no validated entities available
# This prevents the LLM from generating fake entity IDs
if not validated_entities:
    devices_involved = suggestion.get('devices_involved', [])
    error_msg = (
        f"Cannot generate automation YAML: No validated entities found. "
        f"The system could not map any of {len(devices_involved)} requested devices "
        f"({', '.join(devices_involved[:5])}{'...' if len(devices_involved) > 5 else ''}) "
        f"to actual Home Assistant entities. "
        f"Available validated entities: None"
    )
    logger.error(f"❌ {error_msg}")
    raise ValueError(error_msg)
```

**Result**: Now when no entities can be validated, the function fails immediately with a clear error message before attempting to generate YAML. This prevents the LLM from creating fake entity IDs.

### Solution 2: Improve Entity Mapping Accuracy

**Secondary Fix**: Fix the entity extraction/mapping to produce better matches.

**Issues Found**:
1. Entity extraction generates fake IDs (`light.wled`, `light.hue_color_downlight_1_3`)
2. Mapping relies on enriched data that may not have correct entity IDs
3. Fuzzy matching may be creating wrong mappings

**Investigation Needed**:
- Why is entity extraction creating fake IDs?
- Where does `enriched_data` get populated?
- Are we using the right data source for entity discovery?

**Location**: `services/ai-automation-service/src/api/ask_ai_router.py` around line 1050-1090 where enriched_data is built

### Solution 3: Better Error Handling in Post-Gen Validation

**Tertiary Fix**: If we still generate YAML with invalid entities, provide better error messages and auto-fix capabilities.

**Location**: `services/ai-automation-service/src/api/ask_ai_router.py` around line 1819-1825

**Current**: Simple error message
**Proposed**: 
- Better error message with suggestions
- Attempt to find similar entities
- Return partial success if some entities can be fixed

## Implementation Steps

### Step 1: Immediate Fix (Fail Early)
1. Modify `generate_automation_yaml()` to fail when `validated_entities` is empty
2. Add clear error message to user
3. Test with failing scenario

### Step 2: Debug Entity Mapping
1. Add detailed logging to entity extraction
2. Investigate why enriched_data has wrong entity IDs
3. Check data sources (data-api, HA client, device intelligence)

### Step 3: Investigate Root Cause
1. Review comprehensive entity enrichment code
2. Check entity discovery pipeline
3. Verify Home Assistant integration is working

### Step 4: Long-term Solution
1. Fix entity extraction to use real Home Assistant entity IDs
2. Improve entity mapping accuracy
3. Add better fallback suggestions when mappings fail

## Testing Plan

### Test Case 1: No Validated Entities (Should Fail Early)
- **Input**: Query that maps to no real entities
- **Expected**: Error message before YAML generation
- **Current**: Generates YAML, then fails in post-gen validation
- **Status**: Fix in Step 1

### Test Case 2: Valid Query with Real Entities
- **Input**: Query with devices that map to real HA entities
- **Expected**: YAML generated successfully
- **Current**: Should work
- **Status**: Verify after fix

### Test Case 3: Query with Some Invalid Entities
- **Input**: Query with mix of valid and invalid entities
- **Expected**: Use only valid entities, fail if all invalid
- **Current**: Behavior unclear
- **Status**: Test after fix

## Files to Modify

1. **Primary Fix**:
   - `services/ai-automation-service/src/api/ask_ai_router.py` (line ~1194)

2. **Investigation**:
   - `services/ai-automation-service/src/api/ask_ai_router.py` (entity enrichment around line 1050-1090)
   - `services/ai-automation-service/src/services/comprehensive_entity_enrichment.py`
   - `services/ai-automation-service/src/api/ask_ai_router.py` (map_devices_to_entities around line 501)

3. **Documentation**:
   - Update entity validation workflow docs
   - Add troubleshooting guide

## Related Issues

- Entity extraction creating fake IDs
- Enriched data not having correct entity mappings
- Fuzzy matching producing wrong results
- Missing fallback when entities can't be mapped

## Success Criteria

1. ✅ No YAML generated when all entities are invalid
2. ✅ Clear error message to user
3. ✅ Early failure (before YAML generation)
4. ⏳ Better entity mapping accuracy (requires further investigation)
5. ✅ Comprehensive logging for debugging

## Summary

### What Was Fixed
- **Primary Issue**: YAML generation continued even when no validated entities were available, leading the LLM to generate fake entity IDs
- **Solution**: Added early validation check that fails immediately with a clear error message before attempting to generate YAML
- **Impact**: Prevents the "Generated YAML contains invalid entity IDs" error by catching the issue earlier in the pipeline

### Remaining Issues
- **Root Cause**: Entity extraction is still generating fake entity IDs in the first place
- **Next Steps**: Investigate why entity mapping is failing and fix the entity extraction/mapping logic
- **Long-term**: Improve entity discovery and enrichment pipeline to produce accurate mappings

### Testing Required
1. Test with a query that maps to no real entities → Should fail early with clear message
2. Test with a query that has valid entities → Should work as before
3. Test with a query with some invalid entities → Need to verify behavior

## Additional Findings

### Root Cause of Fake Entity IDs

The investigation revealed that fake entity IDs are coming from **external data sources**, not from the AI itself:

1. **Device Intelligence Service**: Provides entity IDs that may not exist in Home Assistant
2. **Data API**: Stores entity metadata that may be outdated or incorrect
3. **Enrichment Pipeline**: Combines data from multiple sources, including invalid entities

**The Logs Show**:
```
Office → light.wled
LR Front Left Ceiling → light.hue_color_downlight_1_3
LR Back Right Ceiling → light.hue_color_downlight_1
```

These mappings are created by `map_devices_to_entities()` using `enriched_data` that comes from:
- Multi-model entity extractor
- Device intelligence service  
- Data API
- Comprehensive entity enrichment

**The Real Issue**: These services are providing entity IDs that don't actually exist in the Home Assistant instance, suggesting:
1. Data synchronization issues between HA and our services
2. Stale data in device intelligence/data-api
3. Entities that were removed/renamed but not updated

### Recommendation

**Short-term**: The early validation fix prevents YAML generation with invalid entities ✅

**Long-term**: Need to investigate and fix the data synchronization between:
- Home Assistant instance
- Device Intelligence service
- Data API
- Entity enrichment pipeline

This is a **data quality issue** that requires fixing at the source rather than patching in the YAML generation layer.

## Detailed Next Steps for Data Quality Investigation

### 1. Verify HA Entity Registry

**Query real Home Assistant entities** to understand what actually exists:

```bash
# Use HA REST API to get all entities
curl -X GET "http://192.168.1.86:8123/api/states" \
  -H "Authorization: Bearer YOUR_TOKEN" | jq '.[] | .entity_id' | grep -E '(wled|hue|office|lr_)'
```

This will show what entities actually exist vs what our services think exist.

### 2. Check Device Intelligence Service

**Investigate** why device intelligence is providing fake entity IDs:

- Logs: `docker logs homeiq-device-intelligence --tail 200`
- Check: Is device intelligence properly synchronized with HA?
- Verify: Entity discovery and registration pipeline

### 3. Verify Data API

**Check** if data-api has stale entity data:

- Logs: `docker logs homeiq-data-api --tail 200`
- Query: Check if entities in data-api match HA
- Verify: How data-api discovers and stores entities

### 4. Test Real Query

**After investigation**, test with a real query that has matching entities in HA to verify the fix works when data is correct.

## Conclusion

**What We Fixed**: 
✅ YAML generation now fails early when no valid entities are found, preventing LLM from creating fake entity IDs

**What Remains**: 
⚠️ Root cause data quality issue in entity discovery/synchronization requires separate investigation

**Current State**: 
System now provides clear error messages to users instead of generating invalid YAML. The underlying data synchronization issue is documented and needs to be addressed at the source.

