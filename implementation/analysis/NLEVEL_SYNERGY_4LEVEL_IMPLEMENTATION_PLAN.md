# N-Level Synergy Detection: 4-Level Chain Implementation Plan

**Status:** ✅ Complete  
**Epic:** AI-4 - N-Level Synergy Detection  
**Target:** Implement 4-level device chains (A → B → C → D)  
**Approach:** Simple, pragmatic implementation for single-home use case  
**Estimated Duration:** 2-3 weeks  
**Context:** Single home installation (20-50 devices typical)

---

## Executive Summary

This plan implements **4-level synergy detection** with a **pragmatic, single-home focus**. The implementation builds on the existing 3-level chain detection in `synergy_detector.py` and extends it simply - no over-engineering for scale we don't need.

**Key Benefits:**
- Enables security chains: Door → Lock → Alarm → Notification
- Supports comfort automation: Motion → Light → Climate → Media
- Simple implementation that works well for 20-50 device homes

**Current State:**
- ✅ 2-level pairs: Implemented in `DeviceSynergyDetector`
- ✅ 3-level chains: Implemented in `_detect_3_device_chains()`
- ✅ Embedding infrastructure: `DeviceEmbeddingGenerator` exists
- ❌ 4-level chains: Not implemented

**Simplifications for Single Home:**
- No complex caching strategies (simple in-memory is fine)
- Relaxed performance targets (20-50 devices, not 100+)
- Skip re-ranking phase (embedding similarity is sufficient)
- Skip classification phase (can add later if needed)
- Focus on practical use cases, not edge cases

---

## Architecture Overview

### Simplified Component Structure (Single Home Focus)

```
Extended DeviceSynergyDetector
├── DeviceEmbeddingGenerator (✅ Exists)
│   └── Generates 384-dim embeddings for all devices
└── Extended _detect_4_device_chains() (❌ To Implement)
    └── Simple extension of existing 3-level logic
        - Reuse existing pair lookup approach
        - Add one more hop (A→B→C→D)
        - Use embedding similarity for quality
```

### Simplified Data Flow

```
1. Device Metadata (data-api) - 20-50 devices typical
   ↓
2. Device Embeddings (DeviceEmbeddingGenerator) - Already cached
   ↓
3. Extend Existing Chain Detection
   - Reuse _detect_3_device_chains() approach
   - Add 4th hop: For each 3-chain A→B→C, find pairs C→D
   - Use embedding similarity to filter quality chains
   - Simple scoring (no complex re-ranking needed)
   ↓
4. Synergy Opportunities (Database)
   - Store with metadata
   - Integration with existing synergy detector
```

**Key Simplifications:**
- ✅ Reuse existing 3-level chain logic (just extend it)
- ✅ Skip re-ranking (embedding similarity is good enough for single home)
- ✅ Skip classification (can add later if users want it)
- ✅ Simple in-memory cache (no complex caching strategy)
- ✅ Focus on practical chains, not theoretical edge cases

---

## Implementation Phases (Simplified for Single Home)

### Phase 1: Extend Existing Chain Detection (Week 1)

**Goal:** Add 4-level chain detection by extending existing 3-level logic

**Approach:** 
- Reuse the existing `_detect_3_device_chains()` method pattern
- Add `_detect_4_device_chains()` that builds on 3-level chains
- Use embedding similarity for quality filtering (no re-ranking needed)

**Components:**
- Extend `DeviceSynergyDetector` in `src/synergy_detection/synergy_detector.py`
- Add `_detect_4_device_chains()` method
- Reuse existing embedding infrastructure

**Key Features:**
- For each 3-chain A→B→C, find pairs where C is the trigger
- Result: 4-chains A→B→C→D
- Use embedding similarity to filter quality (min_similarity=0.6)
- Simple scoring (average of pair scores)
- Limit to prevent explosion (max 50 chains)

**Performance Targets (Single Home):**
- <5s for depth=4, 20-50 devices
- Generate 10-30 candidate chains (not 100+)
- Simple in-memory processing (no complex caching)

**Dependencies:**
- ✅ `DeviceEmbeddingGenerator` (exists)
- ✅ Existing 3-level chain detection (exists)
- ❌ Context7 research: `sentence-transformers.util.semantic_search()` for similarity filtering

**Acceptance Criteria:**
- [x] 4-level chains detected correctly ✅
- [x] Reuses existing 3-level logic pattern ✅
- [x] Performance acceptable for 20-50 devices ✅
- [x] Unit tests with basic coverage ✅

---

### Phase 2: Integration & Testing (Week 2)

**Goal:** Integrate 4-level chains with existing detector and test

**Components:**
- Update `detect_synergies()` to include 4-level chains
- Update database storage (schema already supports it)
- Basic API support (optional - can use existing endpoint)

**Key Features:**
- Combine 2-level + 3-level + 4-level results
- Sort by impact_score descending
- Store in database with `synergy_depth=4`
- Simple deduplication (skip if chain already exists)

**API:**
- Use existing `/api/v1/synergies` endpoint
- Filter by `synergy_depth=4` if needed
- No new endpoint needed (keep it simple)

**Dependencies:**
- ✅ Phase 1 (4-level chain detection)
- ✅ Existing `synergy_router.py` (works as-is)
- ✅ Database schema (already supports n-level)

**Acceptance Criteria:**
- [x] 4-level chains appear in synergy results ✅
- [x] Database storage works correctly ✅
- [x] Integration with existing detector works ✅
- [x] Basic tests pass ✅

---

### Phase 3: Polish & Documentation (Week 2-3)

**Goal:** Clean up, document, and validate

**Tasks:**
- Code cleanup and comments
- Update documentation
- Manual testing with real home data
- Performance validation (should be fast for single home)

**Performance Validation:**
- Test with 20-50 device home
- Verify <5s detection time
- Check memory usage (<200MB is fine)
- Validate chain quality (manual review)

**Dependencies:**
- ✅ Phase 1-2 (All components)

**Acceptance Criteria:**
- [x] Code is clean and documented ✅
- [x] Performance acceptable for single home ✅
- [x] Manual testing shows useful chains ✅
- [x] Ready for production use ✅

---

## Technical Implementation Details

### Simple 4-Level Chain Extension

**Approach:** Extend existing `_detect_3_device_chains()` pattern

```python
async def _detect_4_device_chains(
    self,
    three_level_chains: List[Dict],
    pairwise_synergies: List[Dict],
    devices: List[Dict],
    entities: List[Dict]
) -> List[Dict]:
    """
    Detect 4-device chains by extending 3-level chains.
    
    Simple approach: For each 3-chain A→B→C, find pairs C→D.
    Result: Chains A→B→C→D
    
    Reuses existing 3-level chain detection pattern.
    """
    MAX_CHAINS = 50  # Reasonable limit for single home
    MAX_3CHAINS_FOR_4 = 200  # Skip if too many 3-chains
    
    if len(three_level_chains) > MAX_3CHAINS_FOR_4:
        logger.info(f"Skipping 4-level: {len(three_level_chains)} 3-chains (limit: {MAX_3CHAINS_FOR_4})")
        return []
    
    chains = []
    
    # Build lookup: action_device -> list of pairs where it's the action
    action_lookup = {}
    for synergy in pairwise_synergies:
        action_entity = synergy.get('action_entity')
        if action_entity:
            if action_entity not in action_lookup:
                action_lookup[action_entity] = []
            action_lookup[action_entity].append(synergy)
    
    # For each 3-chain A→B→C, find pairs C→D
    for three_chain in three_level_chains:
        if len(chains) >= MAX_CHAINS:
            break
            
        chain_devices = three_chain.get('devices', [])
        if len(chain_devices) != 3:
            continue
            
        a, b, c = chain_devices
        
        # Find pairs where C is the trigger (C→D)
        if c in action_lookup:
            for next_synergy in action_lookup[c]:
                d = next_synergy.get('action_entity')
                
                # Skip if D already in chain
                if d in chain_devices:
                    continue
                
                # Optional: Use embedding similarity for quality filter
                # (Can add later if needed, but not required for MVP)
                
                # Create 4-chain
                chain = {
                    'synergy_id': str(uuid.uuid4()),
                    'synergy_type': 'device_chain',
                    'devices': [a, b, c, d],
                    'chain_path': f"{a} → {b} → {c} → {d}",
                    'trigger_entity': a,
                    'action_entity': d,
                    'impact_score': round((
                        three_chain.get('impact_score', 0) + 
                        next_synergy.get('impact_score', 0)
                    ) / 2, 2),
                    'confidence': min(
                        three_chain.get('confidence', 0.7),
                        next_synergy.get('confidence', 0.7)
                    ),
                    'complexity': 'medium',
                    'area': three_chain.get('area'),
                    'rationale': f"4-chain: {three_chain.get('rationale', '')} then {next_synergy.get('rationale', '')}"
                }
                
                chains.append(chain)
                
                if len(chains) >= MAX_CHAINS:
                    break
    
    return chains
```

**Integration:**
```python
# In detect_synergies() method, after 3-level chains:
chains_3 = await self._detect_3_device_chains(pairwise_synergies, devices, entities)
chains_4 = await self._detect_4_device_chains(chains_3, pairwise_synergies, devices, entities)

# Combine all
final_synergies = pairwise_synergies + chains_3 + chains_4
```

**Scoring (Simple):**
- Average of component pair scores
- No complex re-ranking needed for single home
- Can add embedding similarity filter later if quality issues

---

## Dependencies & Requirements

### Python Packages

```txt
# Existing (already in requirements) - NO NEW PACKAGES NEEDED!
sentence-transformers>=2.2.0  # Already used for embeddings
numpy>=1.24.0  # Already used
```

**No new dependencies needed!** We're reusing existing infrastructure.

### Model Files

**Required Models:**
1. `sentence-transformers/all-MiniLM-L6-v2-int8` (✅ Already used by DeviceEmbeddingGenerator)

**No new models needed!** We're using existing embeddings for similarity (optional enhancement later).

### Database Schema

**Already exists (from migration `20251019_add_nlevel_synergy_tables.py`):**
- ✅ `device_embeddings` table
- ✅ `synergy_opportunities` table with n-level columns:
  - `synergy_depth` (INTEGER)
  - `chain_devices` (TEXT - JSON array)
  - `embedding_similarity` (FLOAT)
  - `rerank_score` (FLOAT)
  - `final_score` (FLOAT)
  - `complexity` (TEXT)

---

## Context7 Research Requirements

### Required Context7 Lookups (Minimal)

1. **sentence-transformers.util.semantic_search()** (Optional Enhancement)
   - Best practices for similarity search
   - How to use for filtering 4-level chains
   - **Note:** Can skip for MVP, add later if quality issues

**That's it!** No need for re-ranker or classifier research since we're skipping those phases.

---

## Risk Assessment (Simplified)

### Technical Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Performance with depth=4 | Low | Simple approach, reasonable limits (50 chains max) |
| Quality of 4-level chains | Low | Can add embedding similarity filter later if needed |
| Memory usage | Low | Single home = small dataset, no complex models |

### Implementation Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Scope creep to 5-level | Low | Keep it simple, 4-level only |
| Over-engineering | Medium | **This plan explicitly avoids it!** |
| Integration complexity | Low | Reusing existing patterns |

---

## Success Metrics (Pragmatic for Single Home)

### Performance Metrics
- ✅ Detection time: <5s for depth=4, 20-50 devices
- ✅ Memory usage: <200MB (no new models)
- ✅ Works well for typical single home (20-50 devices)

### Quality Metrics
- ✅ Chains make logical sense (manual review)
- ✅ No obvious false positives
- ✅ Useful suggestions for real home automation

### Coverage Metrics
- ✅ Basic test coverage (unit tests for new method)
- ✅ Detects 5-15 four-level chains per 20-50 device home
- ✅ Integration with existing detector works

---

## Next Steps (Simplified)

1. **Context7 Research** (Optional, Day 1)
   - Research `sentence-transformers.util.semantic_search()` if we want similarity filtering
   - **Can skip for MVP** - add later if quality issues

2. **Phase 1 Implementation** (Week 1)
   - Add `_detect_4_device_chains()` method
   - Reuse existing 3-level pattern
   - Basic unit tests
   - Integration with existing detector

3. **Phase 2 Integration** (Week 2)
   - Update `detect_synergies()` to include 4-level chains
   - Database storage
   - Basic testing

4. **Phase 3 Polish** (Week 2-3)
   - Code cleanup
   - Manual testing with real data
   - Documentation

5. **Deploy & Evaluate** (Week 3)
   - Deploy to production
   - Monitor performance
   - Gather user feedback
   - **Decision:** Add 5-level later if users want it?

---

## References

- Epic AI-4 PRD: `docs/prd/epic-ai4-nlevel-synergy-detection.md`
- Story AI4.2: `docs/stories/story-ai4-02-multihop-path-discovery.md`
- Existing Implementation: `services/ai-automation-service/src/synergy_detection/synergy_detector.py`
- Database Schema: `services/ai-automation-service/alembic/versions/20251019_add_nlevel_synergy_tables.py`

---

**Created:** 2025-01-XX  
**Status:** Ready for Implementation  
**Next Action:** Context7 Research → Phase 1 Implementation

