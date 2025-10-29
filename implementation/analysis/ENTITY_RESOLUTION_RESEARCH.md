# Entity Resolution Research & Improvement Discussion

**Date:** October 29, 2025  
**Purpose:** Investigate numbered device mapping and research how to better leverage HA device data and models for entity resolution  
**Status:** 🔍 Research & Discussion Phase

---

## Executive Summary

This document analyzes the current entity resolution implementation, identifies gaps in leveraging Home Assistant device data, and proposes improvements using model chaining and better data utilization.

---

## Current Implementation Analysis

### 1. Current Entity Resolution Approach

**Location:** `services/ai-automation-service/src/services/entity_validator.py`

**Current Method:** `_find_best_match()` - Simple word-based matching

**How It Works:**
1. Extracts number from query (e.g., "Office light 1" → number="1")
2. Builds numbered patterns (e.g., "office_light_1", "office_lamp_1")
3. Searches entity_ids for substring matches
4. Calculates word overlap score (Jaccard-like)
5. Boosts scores for location matches
6. Returns best match if score >= 0.25

**Limitations Identified:**
- ❌ **Not using `friendly_name`** - Entities have friendly names we're ignoring
- ❌ **Not using device metadata** - Device name, manufacturer, model not used
- ❌ **No semantic similarity** - Word matching doesn't understand "lamp" = "light"
- ❌ **No embedding-based matching** - No use of sentence-transformers we already have
- ❌ **Limited numbered matching** - Only checks entity_id patterns, not friendly_name patterns
- ❌ **No model chaining** - Simple regex/word matching only

### 2. Available Data (Not Currently Used)

#### Entity Data Available:
```python
{
    "entity_id": "light.hue_go_1",  # ✅ Used
    "device_id": "1c0de85ffbffe283370a4b3617b99a76",  # ❌ Not used
    "domain": "light",  # ✅ Used (for filtering)
    "area_id": None,  # ✅ Used (but often None)
    "friendly_name": null,  # ❌ NOT USED - Critical gap!
    "platform": "hue",  # ❌ Not used
}
```

#### Device Data Available (via device_id):
```python
{
    "device_id": "1c0de85ffbffe283370a4b3617b99a76",
    "name": "Office Light 1",  # ❌ NOT USED - This could solve numbered matching!
    "manufacturer": "Philips",  # ❌ Not used
    "model": "Hue Go",  # ❌ Not used
    "area_id": "office",  # Could augment entity area_id
    "integration": "hue",  # ❌ Not used
}
```

#### Attributes Available (via API):
```python
{
    "friendly_name": "Office Light 1",  # ❌ NOT USED
    "supported_features": 191,  # ✅ Used (for capabilities)
    "attributes": {
        "brightness": 255,
        "color_mode": "rgb",
        # ... more attributes
    }
}
```

### 3. Why Numbered Devices Map to Same Entity

**Issue:** All "Office light 1", "Office light 2", etc. map to `light.office`

**Root Cause Analysis:**
1. Query: "Office light 1"
2. Numbered extraction finds base="office light", number="1"
3. Builds patterns: `["office_light_1", "office_lamp_1", ...]`
4. Searches entity_ids: `light.office`, `light.hue_go_1`, `light.garage_2`
5. **Problem:** Pattern `office_light_1` doesn't match `light.hue_go_1` well
6. Falls back to word overlap: "office" + "light" matches `light.office` perfectly
7. Result: All numbered devices map to `light.office`

**Missing:** 
- Device name matching ("Office Light 1" from device registry)
- Friendly name matching (if available)
- Better semantic understanding of numbered patterns

---

## Existing Infrastructure (Already Built!)

### 1. Multi-Model Entity Extractor
**Location:** `services/ai-automation-service/src/entity_extraction/multi_model_extractor.py`

**Current Use:** Entity **extraction** (identifying what entities are mentioned in text)

**Models Available:**
- ✅ HuggingFace NER: `dslim/bert-base-NER` (already loaded)
- ✅ OpenAI GPT-4o-mini: For complex queries
- ✅ spaCy: For preprocessing

**Gap:** Used for extraction, NOT for resolution (mapping to entity IDs)

### 2. Embedding Models (Already Deployed!)
**Location:** `services/ai-automation-service/src/nlevel_synergy/embedding_model.py`

**Model:** `sentence-transformers/all-MiniLM-L6-v2` (384-dim embeddings)

**Current Use:** Pattern similarity search in RAG queries

**Potential Use:** Semantic similarity for entity matching!
- Query: "Office light 1" → embedding
- Candidates: All entity friendly_names → embeddings
- Match: Cosine similarity to find best match

### 3. Device Intelligence Client
**Location:** `services/ai-automation-service/src/clients/data_api_client.py`

**Capabilities:**
- ✅ `fetch_entities()` - Get all entities with metadata
- ✅ `fetch_devices()` - Get device registry
- ✅ `get_device_metadata(device_id)` - Get full device info including name
- ✅ `get_entity_metadata(entity_id)` - Get entity with friendly_name

**Current Usage:** ✅ Used for fetching entities  
**Missing Usage:** ❌ Not enriching entities with device names/friendly_names

---

## Research: How We SHOULD Be Using HA Data

### 1. Home Assistant Data Architecture

**Three Layers:**
1. **Entity Registry** - Individual entities (light.hue_go_1)
   - tempo: Primary entity_sort_order
   - Has friendly_name (user-assigned or auto-generated)
   - Linked to device via device_id

2. **Device Registry** - Physical devices
   - Has name (user-assigned, often "Office Light 1")
   - Has manufacturer, model
   - Has area_id (often more reliable than entity area_id)
   - Contains multiple entities (one device → many entities)

3. **State/Attributes** - Current values
   - friendly_name in attributes (often different from registry)
   - Supported features
   - Current state values

### 2. Best Practices for Entity Resolution

**Standard Approach (used by HA itself):**
1. **Primary:** Match against `friendly_name` (user-facing name)
2. **Secondary:** Match against device `name` (device registry)
3. **Tertiary:** Match against `entity_id` (technical ID)
4. **Fallback:** Semantic similarity using embeddings

**Why This Matters:**
- User says "Office Light 1" → matches device.name "Office Light 1"
- User says "Hue Go in office" → matches friendly_name + area_id
- User says "the lamp" → semantic similarity finds closest match

### 3. Model Chaining Strategy (Research Proposal)

**Suggested Pipeline:**

```
User Query: "Turn on Office Light 1"
    ↓
Step 1: NER Extraction (HuggingFace)
    → Extracts: ["Office Light 1"]
    ↓
Step 2: Entity Candidate Generation
    → Fetch all entities with:
      - friendly_name (if available)
      - device.name (via device_id lookup)
      - entity_id
      - Filter by domain (if mentioned: "light")
      - Filter by area (if mentioned: "office")
    ↓
Step 3: Embedding-Based Matching (sentence-transformers)
    → Query embedding: "Office Light 1"
    → Candidate embeddings: [friendly_names + device_names]
    → Rank by cosine similarity
    ↓
Step 4: Numbered Device Detection
    → If number detected (e.g., "1")
    → Boost candidates with matching number in name/entity_id
    ↓
Step 5: Final Ranking
    → Combine:
      - Embedding similarity (0.0-1.0)
      - Number match bonus (+0.3)
      - Location match bonus (+0.5)
      - Exact name match (highest priority)
    → Return top match
```

---

## Proposed Improvements

### Option 1: Enhance Current Approach (Quick Win)

**Changes:**
1. ✅ Fetch `friendly_name` from entity metadata
2. ✅ Fetch device `name` via device_id lookup
3. ✅ Match against friendly_name and device.name in addition to entity_id
4. ✅ Better numbered pattern matching using device names

**Pros:**
- Low risk, leverages existing code
- Can implement quickly
- Uses data we already fetch

**Cons:**
- Still word-based matching
- Doesn't solve semantic similarity ("lamp" vs "light")

### Option 2: Add Embedding-Based Matching (Medium Effort)

**Changes:**
1. Use existing `sentence-transformers/all-MiniLM-L6-v2` model
2. Generate embeddings for:
   - Query terms
   - Entity friendly_names
   - Device names
3. Rank candidates by cosine similarity
4. Combine with current word-based matching

**Pros:**
- Solves semantic similarity issues
- Uses infrastructure we already have
- Better accuracy for numbered devices

**Cons:**
- Requires embedding inference (20-50ms per query)
- Need to cache entity embeddings (or compute on-the-fly)

### Option 3: Full Model Chain (High Effort, Best Results)

**Changes:**
1. Implement full pipeline from research above
2. NER → Embedding → Filter → Rank → Match
3. Leverage all HA data layers
4. Add confidence scoring

**Pros:**
- Best accuracy
- Handles edge cases well
- Future-proof architecture

**Cons:**
- Most complex
- Requires testing
- May need fine-tuning

---

## Questions for Discussion

### 1. Data Utilization
- **Q:** Should we prioritize `friendly_name` from entity attributes vs entity registry?
- **Q:** Do we want to fetch device metadata for every entity resolution, or batch it?
- **Q:** Should we cache device metadata (TTL-based) to reduce API calls?

### 2. Model Selection
- **Q:** Is `sentence-transformers/all-MiniLM-L6-v2` good enough for entity matching, or should we use a domain-specific model?
- **Q:** Should we chain NER → Embeddings, or is NER unnecessary for resolution?
- **Q:** Do we want to use OpenAI for complex resolution cases (fallback), or keep it local?

### 3. Performance vs Accuracy
- **Q:** What's acceptable latency? Current: ~50ms, with embeddings: ~100-200ms
- **Q:** Should we pre-compute embeddings for all entities (storage vs computation)?
- **Q:** Do we need real-time resolution, or can we cache results?

### 4. Numbered Device Priority
- **Q:** How important is perfect numbered device matching? (Is it worth the complexity?)
- **Q:** Should we prefer exact name matches over semantic similarity when both available?
- **Q:** What's the fallback if numbered match fails? (Ask user vs use best guess)

### 5. Integration Points
- **Q:** Should we enhance `EntityValidator.map_query_to_entities()` or create a new service?
- **Q:** Do we integrate with existing `MultiModelEntityExtractor` rescopers it?
- **Q:** Should we create a new `EntityResolutionService` that uses all these techniques?

---

## Recommendations (For Discussion)

### Short Term (This Week)
1. ✅ **Enhance current approach** - Add friendly_name and device.name matching
2. ✅ **Fix numbered device patterns** - Check device names in addition to entity_ids
3. ✅ **Add device metadata lookup** - Enrich entity resolution with device info

### Medium Term (Next Sprint)
1. ⚠️ **Add embedding-based matching** - Use sentence-transformers for semantic similarity
2. ⚠️ **Implement hybrid scoring** - Combine word matching + embeddings
3. ⚠️ **Cache device metadata** - Reduce API calls

### Long Term (Future Epic)
1. 🔮 **Full model chain** - NER → Embeddings → Filter → Rank
2. 🔮 **Confidence scoring** - Return match confidence for UX decisions
3. 🔮 **Fine-tuned model** - Train on actual HA device names for better accuracy

---

## Next Steps

1. **Review this document** - Discuss recommendations and priorities
2. **Clarify requirements** - Answer discussion questions above
3. **Choose approach** - Option 1, 2, or 3 (or hybrid)
4. **Create implementation plan** - Break down into tasks
5. **Implement and test** - Verify numbered device matching works

---

## References

- Current Implementation: `services/ai-automation-service/src/services/entity_validator.py`
- Multi-Model Extractor: `services/ai-automation-service/src/entity_extraction/multi_model_extractor.py`
- Data API Client: `services/ai-automation-service/src/clients/data_api_client.py`
- Embedding Model: `services/ai-automation-service/src/nlevel_synergy/embedding_model.py`
- HA Device Research: `docs/research/home-assistant-device-discovery-research.md`
- Device Data Fields: `implementation/DEVICE_DATA_FIELD_REVIEW.md`

