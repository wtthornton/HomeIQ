# Ask AI Suggestion Generation - Call Tree & Analysis

**Date**: 2025-11-04  
**Query Analyzed**: "When you sit at your desk, turn on the WLED with fireworks effect and fade ceiling lights to 100%"

## Call Tree

```
POST /api/v1/ask-ai/query
  └─> process_natural_language_query() [ask_ai_router.py:2590]
      ├─> extract_entities_with_ha(query) [line 2607]
      │   └─> multi_model_extractor.extract_entities()
      │       ├─> NER extraction (BERT)
      │       ├─> OpenAI extraction (fallback)
      │       └─> Pattern matching (fallback)
      │
      └─> generate_suggestions_from_query(query, entities, user_id) [line 2610]
          ├─> Resolve and enrich entities [lines 2336-2446]
          │   ├─> Extract location & domain from query [line 2356-2357]
          │   ├─> _get_available_entities(domain, area_id) [line 2362]
          │   ├─> expand_group_entities_to_members() [line 2374]
          │   └─> enrich_entities_comprehensively() [line 2413]
          │       ├─> Fetch HA entity states
          │       ├─> Fetch device intelligence data
          │       └─> Build comprehensive enriched_data dict
          │
          ├─> Build unified prompt [line 2451]
          │   └─> UnifiedPromptBuilder.build_query_prompt()
          │       └─> Includes entity context JSON + device intelligence
          │
          ├─> Call OpenAI [line 2464]
          │   └─> OpenAI returns list of suggestions with:
          │       - description
          │       - trigger_summary
          │       - action_summary
          │       - devices_involved: ['light', 'wled', 'WLED Office', 'LR Front Left Ceiling', ...]
          │       - capabilities_used
          │       - confidence
          │
          └─> Process each suggestion [lines 2489-2561]
              ├─> _pre_consolidate_device_names() [line 2498] ✅ NEW FIX
              │   └─> Remove generic terms: 'light', 'wled', domains, short terms
              │
              ├─> map_devices_to_entities() [line 2515]
              │   ├─> Match device names to entity IDs from enriched_data
              │   │   ├─> Strategy 1: Exact match by friendly_name [line 661]
              │   │   ├─> Strategy 2: Fuzzy matching (substring) [line 670]
              │   │   └─> Strategy 3: Domain name match [line 699]
              │   │
              │   └─> verify_entities_exist_in_ha() [line 737]
              │       └─> Check if each entity_id exists in HA
              │           └─> Remove non-existent entities
              │
              ├─> consolidate_devices_involved() [line 2525]
              │   └─> Remove redundant device names that map to same entity_id
              │
              └─> enhance_suggestion_with_entity_ids() [line 2552]
                  └─> Add entity IDs and metadata to suggestion
```

## Current Flow Analysis

### What's Working ✅

1. **Entity Extraction**: Multi-model extractor successfully extracts entities from the query
2. **Entity Resolution**: System successfully resolves entities by location + domain
3. **Entity Enrichment**: Comprehensive enrichment fetches data from HA + Device Intelligence
4. **OpenAI Generation**: OpenAI successfully generates 5 suggestions
5. **Pre-Consolidation**: Generic terms like 'light', 'wled' are now being removed (latest fix)

### What's Failing ❌

1. **Entity Mapping**: The `map_devices_to_entities` function generates **wrong entity IDs**:
   - 'WLED Office' → `light.wled` ❌ (doesn't exist)
   - 'LR Front Left Ceiling' → `light.hue_color_downlight_1_3` ❌ (doesn't exist)
   - 'LR Back Right Ceiling' → `light.hue_color_downlight_1` ❌ (doesn't exist)
   - 'LR Front Right Ceiling' → `light.hue_color_downlight_1_4` ❌ (doesn't exist)
   - 'LR Back Left Ceiling' → `light.hue_lr_back_left_ceiling` ❌ (doesn't exist)

2. **Entity Verification**: All mapped entities fail HA verification (don't exist)
3. **Result**: Zero validated entities, cannot create automation

## Root Cause Analysis

### Why Are Entity IDs Wrong?

The `map_devices_to_entities` function uses the **enriched_data** dictionary to map device names to entity IDs. The enriched_data is built from:

1. **`_get_available_entities(domain, area_id)`** - Fetches entities by location + domain
2. **`enrich_entities_comprehensively(entity_ids, ha_client, device_intelligence_client)`** - Enriches with HA states + device metadata

**The problem**: Either the enriched_data contains:
- Wrong entity IDs from the start (incorrect fetch from HA)
- Correct entity IDs but the mapping logic is flawed
- Or the actual HA entity IDs are named differently than expected

### What OpenAI Returns (Devices Involved)

From the logs, OpenAI returns these devices in `devices_involved`:
```json
[
  "light",           // ❌ Generic domain (removed by pre-consolidation)
  "wled",            // ❌ Generic type (removed by pre-consolidation)
  "WLED Office",     // ✅ Specific device name
  "LR Front Left Ceiling",   // ✅ Specific device name
  "LR Back Right Ceiling",   // ✅ Specific device name
  "LR Front Right Ceiling",  // ✅ Specific device name
  "LR Back Left Ceiling"     // ✅ Specific device name
]
```

After pre-consolidation (my fix), only these remain:
```json
[
  "WLED Office",
  "LR Front Left Ceiling",
  "LR Back Right Ceiling",
  "LR Front Right Ceiling",
  "LR Back Left Ceiling"
]
```

### What's Displayed in UI

The UI shows:
- ✅ light (blue checkbox)
- ⚙️ wled (icon)
- ✅ WLED Office
- ✅ LR Front Left Ceiling
- ✅ LR Back Right Ceiling
- ✅ LR Front Right Ceiling
- ✅ LR Back Left Ceiling

**Note**: The UI is showing an **older suggestion** created before the pre-consolidation fix. The latest logs show that 'light' and 'wled' are now being removed.

## Key Questions to Answer

### 1. **What are the ACTUAL entity IDs in Home Assistant?**

To fix the entity mapping, I need to know the correct entity IDs:
- What is the entity ID for "WLED Office"?
  - Expected format: `light.wled_office`?
  - Or something else?
- What are the entity IDs for the ceiling lights?
  - Expected format: `light.lr_front_left_ceiling`?
  - Or Hue IDs like `light.hue_color_downlight_1`?

### 2. **Are there Hue Groups involved?**

The logs mention checking for `is_hue_group` attribute. Are some of these lights:
- Individual Hue lights (e.g., `light.hue_color_downlight_1`)?
- Hue room groups (e.g., `light.office` as a group)?

### 3. **What's in enriched_data?**

The enriched_data dictionary should contain ALL available entities with their metadata. To debug, I need to see:
- What entity IDs are in enriched_data?
- What friendly names are associated with each entity_id?
- Are the Office/LR entities even in enriched_data?

## Recommended Fix Strategy

### Option 1: Debug Entity Fetch (Recommended)

1. **Add detailed logging** to see what's in enriched_data:
   ```python
   logger.info(f"🔍 enriched_data contains {len(enriched_data)} entities")
   logger.info(f"🔍 Entity IDs: {list(enriched_data.keys())[:20]}")
   logger.info(f"🔍 Friendly names: {[e.get('friendly_name') for e in list(enriched_data.values())[:20]]}")
   ```

2. **Check if the correct entities are being fetched** by `_get_available_entities`:
   - Is it finding the WLED Office entity?
   - Is it finding the LR ceiling lights?

3. **Verify HA entity naming**:
   - Go to HA Developer Tools > States
   - Search for "Office", "WLED", "LR", "Ceiling"
   - Get the actual entity IDs

### Option 2: Improve Fuzzy Matching

If enriched_data has correct entities but matching fails:
1. Improve the fuzzy matching algorithm
2. Add better name normalization (e.g., "LR" → "Living Room")
3. Add synonym mapping

### Option 3: Query HA Directly

Skip enriched_data and query HA directly for entity IDs:
1. Use HA's search API to find entities by name
2. Use HA's area/device APIs to find entities by location

## Next Steps

**Before clicking "Approve & Create"**, please provide:

1. **Actual entity IDs** from HA (http://192.168.1.86:8123/developer-tools/states):
   - Search for "WLED" - what's the entity ID?
   - Search for "Office" - what entities are in the Office?
   - Search for "LR" or "Ceiling" - what are the ceiling light entity IDs?

2. **Are these Hue lights?**
   - Are they individual lights or Hue room groups?
   - Do you see entities like `light.office_lights` (group)?

3. **Run this command** to see detailed enriched_data debugging:
   ```powershell
   docker logs ai-automation-service --tail=500 | Select-String -Pattern "enriched_data contains|Entity IDs:|Friendly names:|Mapped device" -Context 2
   ```

Once I have this information, I can fix the entity mapping logic to generate the correct entity IDs.

## Summary

### ✅ What's Fixed
- Pre-consolidation removes generic terms ('light', 'wled')
- Type validation prevents crashes on non-dict device_details
- **Effect list extraction** - WLED effect_list now prominently extracted for OpenAI

### ✅ What User Discovered
- **Entity ID `light.wled` DOES EXIST** in Home Assistant!
- It has 200+ effects in `effect_list` attribute
- State attributes include everything OpenAI needs

### 🔧 What Was Improved
- Effect list (`effect_list`) now explicitly extracted and shown to OpenAI
- Current effect (`current_effect`) prominently displayed
- Supported color modes (`supported_color_modes`) included in context
- OpenAI can now see exact effect names like "Fireworks", "Rainbow", "Plasma Ball"

### ⚠️ Remaining Issue
- Entity verification may be using ensemble validation with low consensus
- Some entities might fail verification even though they exist in HA
- Need to test with new suggestions to see if verification is working correctly

