# Entity Resolution Enhancement Plan

**Date:** October 29, 2025  
**Priority:** High  
**Status:** Planning  

---

## Executive Summary

Based on test results and logs, we've identified 7 enhancement opportunities. This plan prioritizes quick wins with immediate impact, followed by performance optimizations that require more investigation.

**Total Work:** ~3-4 days of focused development  
**Impact:** 30-50% performance improvement, better UX, cleaner logs  

---

## Enhancement Priority Matrix

| Enhancement | Priority | Effort | Impact | Risk |
|------------|----------|--------|--------|------|
| 1. Reduce Logging Noise | 🔴 HIGH | Low (1-2 hours) | High | None |
| 2. Fix Entity Duplication | 🔴 HIGH | Low (2-3 hours) | High | Low |
| 3. Add Performance Metrics | 🟡 MEDIUM | Medium (3-4 hours) | Medium | None |
| 4. Improve Entity Resolution Performance | 🟡 MEDIUM | High (1-2 days) | High | Medium |
| 5. Optimize YAML Generation | 🟡 MEDIUM | High (1-2 days) | High | Medium |
| 6. Add Missing Device Detection | 🟢 LOW | Medium (4-6 hours) | Low | Low |
| 7. Add User Feedback Loop | 🟢 LOW | High (2-3 days) | Low | Low |

---

## Phase 1: Quick Wins (Day 1-2)

### Task 1.1: Reduce Logging Noise ⚡

**Files to modify:**
- `services/ai-automation-service/src/services/entity_validator.py`

**Changes:**
1. Add logging level configuration
2. Summarize location penalties instead of logging each one
3. Log only top 3 candidates per entity
4. Add summary statistics at end

**Implementation:**
```python
# Before: Log every penalty
logger.warning(f"Location MISMATCH PENALTY '{location_context}' not found...")

# After: Aggregate penalties
location_mismatches = []
for entity in entities:
    if not location_match:
        location_mismatches.append(entity['entity_id'])
if location_mismatches:
    logger.debug(f"Location mismatch: {len(location_mismatches)} entities penalized (areas: {unique_areas})")

# Log only top 3 final candidates
top_candidates = sorted(candidates, key=lambda x: x['score'], reverse=True)[:3]
for i, candidate in enumerate(top_candidates):
    logger.debug(f"Candidate #{i+1}: {candidate['entity_id']} (score: {candidate['score']:.3f})")
```

**Expected Outcome:**
- Log output reduced from 100+ lines to ~10-15 lines per query
- Easier to debug actual issues
- Performance unchanged

**Testing:**
- Run test 5 again
- Verify log output is readable
- Ensure no important information lost

**Effort:** 1-2 hours  
**Risk:** None (logging changes only)

---

### Task 1.2: Fix Entity Duplication ⚡

**Files to modify:**
- `services/ai-automation-service/src/api/ask_ai_router.py`

**Problem:**
Multiple device names map to same entity_id, causing YAML duplication:
```yaml
entity_id:
  - light.hue_color_downlight_2_2
  - light.hue_color_downlight_2_2  # Duplicate!
  - light.hue_color_downlight_2_2  # Duplicate!
```

**Implementation:**
```python
# In test_suggestion_from_query() or generate_automation_yaml()
def deduplicate_entities(entity_mapping: Dict[str, str]) -> Dict[str, str]:
    """
    Deduplicate entities - if multiple device names map to same entity_id,
    keep only the first one.
    """
    seen_entities = set()
    deduplicated = {}
    
    for device_name, entity_id in entity_mapping.items():
        if entity_id not in seen_entities:
            deduplicated[device_name] = entity_id
            seen_entities.add(entity_id)
        else:
            logger.debug(f"Skipping duplicate entity mapping: '{device_name}' → {entity_id}")
    
    return deduplicated

# Use it before passing to YAML generation
entity_mapping = deduplicate_entities(entity_mapping)
```

**Alternative approach:**
Instead of deduplicating the mapping, deduplicate in the YAML generation prompt:
```python
# In OpenAI prompt
unique_entity_ids = list(set(entity_mapping.values()))
prompt += f"\nUnique entities to use: {unique_entity_ids}\n"
prompt += f"CRITICAL: Use each entity ID only ONCE in the YAML.\n"
```

**Expected Outcome:**
- No duplicate entity_ids in generated YAML
- Cleaner automation YAML
- Better performance (fewer redundant HA calls)

**Testing:**
- Create test case with duplicate mappings
- Verify YAML has no duplicates
- Test automation still works correctly

**Effort:** 2-3 hours  
**Risk:** Low (deduplication is safe)

---

### Task 1.3: Add Performance Metrics 📊

**Files to modify:**
- `services/ai-automation-service/src/api/ask_ai_router.py`
- `services/ai-automation-service/src/services/entity_validator.py`

**Implementation:**
Add structured metrics collection:

```python
@dataclass
class PerformanceMetrics:
    """Detailed performance metrics for entity resolution"""
    entity_count: int = 0
    domain_filter_ms: float = 0.0
    location_filter_ms: float = 0.0
    enrichment_ms: float = 0.0
    matching_ms: float = 0.0
    total_resolution_ms: float = 0.0
    candidates_evaluated: int = 0
    matches_found: int = 0

def log_performance_summary(metrics: PerformanceMetrics):
    """Log performance summary in readable format"""
    logger.info("=" * 60)
    logger.info("ENTITY RESOLUTION PERFORMANCE")
    logger.info("=" * 60)
    logger.info(f"Entities requested: {metrics.entity_count}")
    logger.info(f"Candidates evaluated: {metrics.candidates_evaluated}")
    logger.info(f"Matches found: {metrics.matches_found}")
    logger.info(f"")
    logger.info("Timing Breakdown:")
    logger.info(f"  Domain filter:     {metrics.domain_filter_ms:>6.1f}ms")
    logger.info(f"  Location filter:   {metrics.location_filter_ms:>6.1f}ms")
    logger.info(f"  Enrichment:        {metrics.enrichment_ms:>6.1f}ms")
    logger.info(f"  Matching:          {metrics.matching_ms:>6.1f}ms")
    logger.info(f"  TOTAL RESOLUTION:  {metrics.total_resolution_ms:>6.1f}ms")
    logger.info("=" * 60)
```

**Expected Outcome:**
- Clear performance breakdown
- Easy to identify bottlenecks
- Production monitoring ready

**Testing:**
- Run test 5
- Verify metrics logged correctly
- Check timings add up

**Effort:** 3-4 hours  
**Risk:** None (additive logging)

---

## Phase 2: Performance Optimization (Day 3-4)

### Task 2.1: Improve Entity Resolution Performance 🚀

**Objective:** Reduce entity resolution time from 5.3s to ~3s

**Approach 1: Early Location Filtering** (Recommended first)

**Implementation:**
```python
async def _get_available_entities(
    self,
    domain: Optional[str] = None,
    area_id: Optional[str] = None,  # Add this parameter
    integration: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get available entities with early location filtering.
    
    This reduces candidates before expensive enrichment step.
    """
    if area_id:
        # Fetch with location filter at API level
        entities = await self.data_api_client.fetch_entities(
            domain=domain,
            area_id=area_id,  # Filter at database level
            platform=integration
        )
        logger.info(f"📍 Early location filter: {len(entities)} entities in area '{area_id}'")
    else:
        entities = await self.data_api_client.fetch_entities(
            domain=domain,
            platform=integration
        )
    
    return entities
```

**Expected Impact:**
- Reduces candidates from ~50 to ~10-15
- Skips enrichment for non-office entities
- Expected time reduction: 5.3s → ~3s

**Effort:** 3-4 hours  
**Risk:** Medium (need to verify data-api supports area_id filtering)

---

**Approach 2: Batch Entity Enrichment**

**Implementation:**
```python
async def _enrich_entities_batch(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Enrich multiple entities in parallel with caching"""
    
    # Build list of unique device_ids (no duplicates)
    device_ids = list(set(
        entity.get('device_id') 
        for entity in entities 
        if entity.get('device_id') and entity.get('device_id') not in self._device_metadata_cache
    ))
    
    # Batch fetch metadata (if data_api supports batch endpoint)
    if device_ids and hasattr(self.data_api_client, 'get_devices_metadata_batch'):
        try:
            batch_metadata = await self.data_api_client.get_devices_metadata_batch(device_ids)
            self._device_metadata_cache.update(batch_metadata)
        except:
            # Fallback to individual fetches
            pass
    
    # Enrich entities (now with cached metadata)
    tasks = [self._enrich_entity_with_metadata(entity) for entity in entities]
    enriched = await asyncio.gather(*tasks, return_exceptions=True)
    
    return enriched
```

**Expected Impact:**
- Parallel fetching instead of sequential
- Expected time reduction: ~1-2s

**Effort:** 2-3 hours  
**Risk:** Low (with fallback)

---

### Task 2.2: Optimize YAML Generation 🚀

**Objective:** Reduce YAML generation from 14.3s to ~5-8s

**Approach 1: Template-Based Generation** (Quick win)

**Implementation:**
```python
SIMPLE_AUTOMATION_PATTERNS = {
    'turn_on': {
        'trigger_template': 'platform: event\nevent_type: test_trigger',
        'action_template': 'service: light.turn_on\ntarget:\n  entity_id: {entity_ids}'
    },
    'flash': {
        'trigger_template': 'platform: event\nevent_type: test_trigger',
        'action_template': '''sequence:
  - service: light.turn_on
    target:
      entity_id: {entity_ids}
    data:
      brightness_pct: 100
  - delay: "00:00:01"
  - service: light.turn_off
    target:
      entity_id: {entity_ids}'''
    }
}

def detect_automation_pattern(suggestion: Dict[str, Any]) -> Optional[str]:
    """Detect if suggestion matches a simple pattern"""
    description_lower = suggestion.get('description', '').lower()
    
    if 'turn on' in description_lower or 'flash' in description_lower:
        # Check if it's a simple on/off or flash pattern
        if 'sequence' not in description_lower and 'repeat' not in description_lower:
            return 'turn_on'
        elif 'flash' in description_lower:
            return 'flash'
    
    return None

async def generate_automation_yaml(suggestion, original_query, entities, db_session):
    """Generate YAML with template fallback"""
    
    # Try pattern detection first
    pattern = detect_automation_pattern(suggestion)
    if pattern:
        entity_ids = list(suggestion.get('validated_entities', {}).values())
        if entity_ids:
            yaml = SIMPLE_AUTOMATION_PATTERNS[pattern]['action_template'].format(
                entity_ids='\n      - '.join(entity_ids)
            )
            logger.info(f"✅ Used template for pattern '{pattern}' (fast path)")
            return yaml
    
    # Fall back to OpenAI generation
    return await generate_yaml_with_openai(suggestion, original_query, entities)
```

**Expected Impact:**
- Simple automations: 14s → <1s
- Complex automations: Still 14s (fallback to OpenAI)
- Expected average: ~5-8s

**Effort:** 4-6 hours  
**Risk:** Medium (need to test patterns thoroughly)

---

**Approach 2: OpenAI Response Caching**

**Implementation:**
```python
from functools import lru_cache
import hashlib

def hash_query_and_suggestion(query: str, suggestion: Dict) -> str:
    """Create hash for caching"""
    key = f"{query}_{suggestion.get('description', '')}"
    return hashlib.md5(key.encode()).hexdigest()

@lru_cache(maxsize=100)
async def cached_generate_yaml(query_hash: str):
    """Cache OpenAI responses (requires serialization)"""
    pass  # Complex due to async + OpenAI client

# OR: Redis/Memcached for distributed caching
```

**Expected Impact:**
- Cache hit: 14s → <100ms
- Cache miss: Still 14s
- Expected improvement: 20-30% if cache hit rate good

**Effort:** 1-2 days (requires caching infrastructure)  
**Risk:** Medium

---

## Phase 3: Edge Cases (Day 5+)

### Task 3.1: Add Missing Device Detection 🔍

**Implementation:**
```python
def detect_missing_devices(original_query: str, mapped_entities: Dict[str, str]) -> List[str]:
    """
    Detect devices mentioned in query but not mapped.
    
    Example: "include the Wled lights" → if no wled entities mapped, flag it
    """
    query_lower = original_query.lower()
    missing = []
    
    # Check for WLED mentions
    if 'wled' in query_lower and not any('wled' in entity_id.lower() for entity_id in mapped_entities.values()):
        missing.append("WLED lights mentioned but not found")
    
    return missing

# Add to response
test_data['warnings'] = detect_missing_devices(query.original_query, entity_mapping)
```

**Expected Outcome:**
- User notified if requested devices not found
- Better UX for device discovery

**Effort:** 4-6 hours  
**Risk:** Low

---

### Task 3.2: User Feedback Loop 💬

**This is a larger UX enhancement - defer to future sprint**

**Concept:**
- After automation created, show user what was created
- Allow user to correct device mappings
- Use corrections to improve future suggestions

**Effort:** 2-3 days  
**Risk:** Medium (UX design needed)

---

## Execution Schedule

### Week 1: Quick Wins

**Day 1 (4-6 hours):**
- ✅ Task 1.1: Reduce logging noise
- Test and verify logs are clean

**Day 2 (4-6 hours):**
- ✅ Task 1.2: Fix entity duplication
- ✅ Task 1.3: Add performance metrics
- Test all Phase 1 changes

### Week 2: Performance

**Day 3-4 (8-10 hours):**
- ✅ Task 2.1: Entity resolution performance
  - Early location filtering
  - Batch entity enrichment
- Measure improvements

**Day 5 (4-6 hours):**
- ✅ Task 2.2: YAML generation optimization
  - Template-based generation
- Test and measure

### Week 3: Edge Cases (Optional)

**Day 6-7:**
- Task 3.1: Missing device detection
- Task 3.2: User feedback loop (if prioritized)

---

## Success Metrics

### Before Enhancements:
- Entity Resolution: 5.3s
- YAML Generation: 14.3s
- Total Time: ~48s
- Log Output: 100+ lines
- Entity Duplication: Yes

### Target (After Phase 1 + Phase 2):
- Entity Resolution: **3s** (40% improvement)
- YAML Generation: **8s avg** (44% improvement for simple cases)
- Total Time: **~30s** (38% improvement)
- Log Output: **~15 lines** (85% reduction)
- Entity Duplication: **No**

### Monitor:
- Test 5 execution time
- Log file sizes
- User feedback on UX improvements

---

## Risk Mitigation

1. **Data-API Changes Required**
   - Risk: Early location filtering needs area_id support
   - Mitigation: Check data-api capabilities first, fallback to current approach

2. **YAML Pattern Detection**
   - Risk: Templates might not match all cases
   - Mitigation: Conservative pattern matching, always fallback to OpenAI

3. **Performance Regression**
   - Risk: Changes might slow things down
   - Mitigation: Measure before/after, revert if regression

---

## Next Steps

1. **Review this plan** with team
2. **Prioritize** which enhancements to implement
3. **Start with Phase 1** (quick wins - can be done today)
4. **Set up monitoring** for Phase 2 performance metrics
5. **Schedule Phase 2** for next sprint

---

## Appendix: Code Locations

### Files to Modify:

**High Priority:**
1. `services/ai-automation-service/src/services/entity_validator.py` (logging, early filtering)
2. `services/ai-automation-service/src/api/ask_ai_router.py` (deduplication, metrics)

**Medium Priority:**
3. `services/ai-automation-service/src/clients/data_api_client.py` (batch queries if needed)

**Low Priority:**
4. `services/data-api/` (area_id filtering support if needed)

---

**Ready to execute Phase 1 (Quick Wins)?** 🚀

