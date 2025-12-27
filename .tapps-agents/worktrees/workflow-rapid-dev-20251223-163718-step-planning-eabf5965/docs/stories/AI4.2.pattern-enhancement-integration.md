# Story AI4.2: Pattern Enhancement Integration

**Epic:** AI-4 (Community Knowledge Augmentation)  
**Status:** InProgress  
**Created:** October 18, 2025  
**Estimated Effort:** 2-3 days  
**Dependencies:** Story AI4.1 (Community Corpus Foundation) ✅ Complete

---

## Story

**As a** Home Assistant user,  
**I want** my detected patterns enhanced with community best practices,  
**so that** I receive smarter suggestions that incorporate proven automation techniques.

---

## Acceptance Criteria

### Functional Requirements

1. **Query Miner During Pattern Detection** (Phase 3 Integration)
   - During `detect_patterns()` in Phase 3, query Automation Miner for similar automations
   - Match detected patterns against corpus using:
     - Device types involved
     - Time-of-day patterns (morning/afternoon/evening/night)
     - Co-occurrence patterns (device A + device B)
   - Retrieve top 5 community automations (sorted by quality_score desc)

2. **Extract Pattern Enhancements**
   - Analyze community automations for common enhancements:
     - **Additional conditions**: Weather, occupancy, time constraints
     - **Timing improvements**: Offsets (e.g., "30 min before sunset")
     - **Action variations**: Brightness levels, color temperature, scenes
   - Create structured enhancement suggestions (not raw YAML)

3. **Augment OpenAI Prompts** (Phase 5 Integration)
   - Inject community insights into suggestion generation prompts
   - Format: "Similar community automations use these enhancements: [list]"
   - Keep personal patterns as primary (80% weight), community as secondary (20% weight)
   - Track which enhancements appear in final suggestions

### Integration Requirements

4. **Graceful Degradation**
   - If Miner query fails/times out (>100ms), continue with Phase 1 patterns only
   - Log failures but don't block suggestion generation
   - Feature flag: `ENABLE_PATTERN_ENHANCEMENT` (default: false)

5. **Performance**
   - Miner queries add <5% overhead to daily analysis job
   - Query timeout: 100ms (fail fast)
   - Cache Miner results for 7 days (patterns don't change frequently)

### Quality Requirements

6. **Enhancement Quality**
   - Only suggest enhancements from automations with quality_score ≥ 0.8
   - Enhancements must be applicable to user's devices (no suggesting sensors they don't have)
   - Track enhancement acceptance rate (user enables suggested condition/action)

7. **Logging & Observability**
   - Log Miner query results with correlation ID
   - Track metrics:
     - Miner queries per analysis run
     - Enhancements injected per suggestion
     - Enhancement acceptance rate
   - Alert if Miner query failure rate >20%

---

## Tasks / Subtasks

### Task 1: Extend Pattern Detection (AC: 1, 4)
- [ ] Modify `services/ai-automation-service/src/pattern_detector.py`
  - [ ] Add `MinerClient` dependency injection
  - [ ] In `detect_patterns()`, after detecting personal patterns:
    ```python
    async def detect_patterns(
        self,
        events: List[Event],
        devices: List[Device],
        miner_client: Optional[MinerClient] = None  # NEW
    ) -> PatternAnalysis:
        # ... existing pattern detection ...
        
        # NEW: Augment with community wisdom
        if miner_client and ENABLE_PATTERN_ENHANCEMENT:
            community_insights = await self._fetch_community_insights(
                detected_patterns,
                devices,
                miner_client
            )
            analysis.community_enhancements = community_insights
        
        return analysis
    ```
- [ ] Implement `_fetch_community_insights()` method
  - [ ] Extract device types from detected patterns
  - [ ] Query Miner: `/api/automation-miner/corpus/search?device=...&min_quality=0.8&limit=5`
  - [ ] Timeout: 100ms (httpx timeout)
  - [ ] Error handling: Return empty list on failure, log warning
- [ ] Add `community_enhancements` field to `PatternAnalysis` Pydantic model

### Task 2: Implement Enhancement Extraction (AC: 2)
- [ ] Create `EnhancementExtractor` class in `services/ai-automation-service/src/miner/enhancement_extractor.py`
  ```python
  from pydantic import BaseModel
  from typing import List, Dict, Any
  
  class Enhancement(BaseModel):
      type: Literal['condition', 'timing', 'action']
      category: str  # 'weather', 'occupancy', 'offset', 'brightness', etc.
      description: str
      example: str  # Natural language example
      applicable_devices: List[str]  # Device types this applies to
      frequency: int  # How many community automations use this
      quality_score: float  # Average quality of automations using this
  
  class EnhancementExtractor:
      def extract_enhancements(
          self,
          community_automations: List[Dict[str, Any]],
          user_devices: List[str]
      ) -> List[Enhancement]:
          """Extract applicable enhancements from community automations"""
          
          enhancements = []
          
          for automation in community_automations:
              # Extract condition enhancements
              for condition in automation.get('conditions', []):
                  if self._is_applicable(condition, user_devices):
                      enhancements.append(self._create_enhancement(
                          type='condition',
                          condition_data=condition,
                          quality=automation['quality_score']
                      ))
              
              # Extract timing enhancements
              for trigger in automation.get('triggers', []):
                  if trigger.get('type') == 'time' and 'offset' in trigger:
                      enhancements.append(Enhancement(
                          type='timing',
                          category='offset',
                          description=f"Offset: {trigger['offset']}",
                          example=f"Trigger {trigger['offset']} instead of exactly at {trigger['time']}",
                          applicable_devices=automation['devices'],
                          frequency=1,
                          quality_score=automation['quality_score']
                      ))
              
              # Extract action enhancements
              for action in automation.get('actions', []):
                  if 'brightness' in action or 'color_temp' in action:
                      enhancements.append(self._create_action_enhancement(action))
          
          # Deduplicate and rank by frequency + quality
          return self._rank_enhancements(enhancements)
  ```
- [ ] Implement `_is_applicable()` - Check if user has required devices
- [ ] Implement `_rank_enhancements()` - Sort by frequency × quality_score
- [ ] Add unit tests for various automation structures

### Task 3: Augment OpenAI Prompts (AC: 3, 6)
- [ ] Modify `services/ai-automation-service/src/suggestion_generator.py`
  - [ ] In `generate_suggestions()`, check if `pattern_analysis.community_enhancements` exists
  - [ ] Build enhancement context string:
    ```python
    def _build_community_context(
        enhancements: List[Enhancement]
    ) -> str:
        """Format enhancements for OpenAI prompt"""
        
        if not enhancements:
            return ""
        
        # Group by type
        by_type = {
            'condition': [],
            'timing': [],
            'action': []
        }
        for enh in enhancements[:10]:  # Top 10 only
            by_type[enh.type].append(enh)
        
        context = "\n\n**Community Best Practices:**\n"
        
        if by_type['condition']:
            context += "\n**Conditions** (used in high-quality automations):\n"
            for enh in by_type['condition'][:3]:
                context += f"- {enh.description} (used by {enh.frequency} automations)\n"
        
        if by_type['timing']:
            context += "\n**Timing Improvements:**\n"
            for enh in by_type['timing'][:3]:
                context += f"- {enh.example}\n"
        
        if by_type['action']:
            context += "\n**Action Variations:**\n"
            for enh in by_type['action'][:3]:
                context += f"- {enh.description}\n"
        
        context += "\n**Note:** These are optional enhancements. Prioritize user's existing patterns.\n"
        
        return context
    ```
  - [ ] Inject into prompt after pattern description, before "Generate suggestions" instruction
  - [ ] Add comment in prompt: "User patterns = 80% weight, Community insights = 20% weight"
- [ ] Track which enhancements appear in generated suggestions
  - [ ] Parse OpenAI response for enhancement keywords
  - [ ] Store in `automation_suggestions.metadata` JSON field:
    ```json
    {
      "community_enhancements_used": [
        {"type": "condition", "category": "weather", "accepted": false},
        {"type": "timing", "category": "offset", "accepted": false}
      ]
    }
    ```
  - [ ] Update `accepted` when user enables suggestion

### Task 4: Implement Miner Client (AC: 1, 4, 5)
- [ ] Create `services/ai-automation-service/src/miner/miner_client.py`
  ```python
  import httpx
  from typing import List, Dict, Any, Optional
  from pydantic import BaseModel
  
  class MinerClient:
      def __init__(
          self,
          base_url: str = "http://localhost:8019",
          timeout: float = 0.1,  # 100ms
          cache_ttl: int = 604800  # 7 days in seconds
      ):
          self.base_url = base_url
          self.timeout = httpx.Timeout(timeout)
          self._cache: Dict[str, Any] = {}  # Simple in-memory cache
      
      async def search_corpus(
          self,
          device: Optional[str] = None,
          integration: Optional[str] = None,
          use_case: Optional[str] = None,
          min_quality: float = 0.8,
          limit: int = 5
      ) -> List[Dict[str, Any]]:
          """Search community automation corpus"""
          
          # Check cache
          cache_key = f"{device}:{integration}:{use_case}:{min_quality}"
          if cache_key in self._cache:
              return self._cache[cache_key]
          
          try:
              async with httpx.AsyncClient(timeout=self.timeout) as client:
                  response = await client.get(
                      f"{self.base_url}/api/automation-miner/corpus/search",
                      params={
                          "device": device,
                          "integration": integration,
                          "use_case": use_case,
                          "min_quality": min_quality,
                          "limit": limit
                      }
                  )
                  response.raise_for_status()
                  data = response.json()
                  
                  # Cache result
                  self._cache[cache_key] = data['automations']
                  return data['automations']
                  
          except (httpx.TimeoutException, httpx.HTTPError) as e:
              logger.warning(f"Miner query failed: {e}")
              return []  # Graceful degradation
  ```
- [ ] Add dependency injection in `ai_automation_job.py`
  - [ ] Initialize `MinerClient` if feature flag enabled
  - [ ] Pass to `detect_patterns()` and `generate_suggestions()`
- [ ] Add metrics tracking:
  - [ ] Miner query count
  - [ ] Miner query latency (p50, p95, p99)
  - [ ] Miner failure rate

### Task 5: Feature Flag & Configuration (AC: 4, 7)
- [ ] Add environment variable to `infrastructure/env.ai-automation`
  ```bash
  # Automation Miner Integration
  ENABLE_PATTERN_ENHANCEMENT=false  # Set to true after Story AI4.1 deployed
  MINER_BASE_URL=http://localhost:8019
  MINER_QUERY_TIMEOUT_MS=100
  MINER_CACHE_TTL_DAYS=7
  ```
- [ ] Update `services/ai-automation-service/src/config.py`
  ```python
  from pydantic_settings import BaseSettings
  
  class Settings(BaseSettings):
      # ... existing settings ...
      
      # Automation Miner (Story AI4.2)
      enable_pattern_enhancement: bool = False
      miner_base_url: str = "http://localhost:8019"
      miner_query_timeout_ms: int = 100
      miner_cache_ttl_days: int = 7
  ```
- [ ] Add health check for Miner integration
  ```python
  async def check_miner_health() -> dict:
      if not settings.enable_pattern_enhancement:
          return {"status": "disabled"}
      
      try:
          async with httpx.AsyncClient(timeout=1.0) as client:
              response = await client.get(f"{settings.miner_base_url}/health")
              response.raise_for_status()
              return {"status": "healthy", "data": response.json()}
      except Exception as e:
          return {"status": "unhealthy", "error": str(e)}
  ```

### Task 6: Testing & Documentation (AC: All)
- [ ] Unit tests:
  - [ ] `EnhancementExtractor.extract_enhancements()` with various automations
  - [ ] `_build_community_context()` formatting
  - [ ] `MinerClient` with mocked responses
- [ ] Integration tests:
  - [ ] Full flow: Pattern detection → Miner query → Enhancement extraction → Prompt augmentation
  - [ ] Test graceful degradation (Miner unavailable)
  - [ ] Test cache hit/miss
- [ ] Performance tests:
  - [ ] Measure overhead added to daily analysis job (<5%)
  - [ ] Verify Miner query timeout works (100ms)
- [ ] Update call tree documentation:
  - [ ] Add Phase 3b: Community Enhancement Query
  - [ ] Add Phase 5c: Enhancement Injection
- [ ] Update `README.md` with feature flag configuration

---

## Dev Notes

### Integration Points

**Phase 3: Pattern Detection** (`services/ai-automation-service/src/pattern_detector.py`)
- **Current behavior**: Detects time-of-day and co-occurrence patterns from user's event history
- **New behavior**: After pattern detection, queries Miner for similar community automations
- **Key change**: Add `miner_client` parameter, call `_fetch_community_insights()`

**Phase 5: Suggestion Generation** (`services/ai-automation-service/src/suggestion_generator.py`)
- **Current behavior**: Generates suggestions using OpenAI with patterns + features
- **New behavior**: Includes community enhancements in prompt if available
- **Key change**: Call `_build_community_context()`, inject into prompt

### Prompt Template Example

**Before** (Phase 1):
```
You are an expert Home Assistant automation advisor.

User's devices: [list]
Detected patterns: [time-of-day, co-occurrence]
Underutilized features: [list]

Generate 10 automation suggestions...
```

**After** (Phase 2 with Story AI4.2):
```
You are an expert Home Assistant automation advisor.

User's devices: [list]
Detected patterns: [time-of-day, co-occurrence]
Underutilized features: [list]

**Community Best Practices:**

**Conditions** (used in high-quality automations):
- Add weather condition: Only run if temperature > 20°C (used by 150 automations)
- Add occupancy check: Only run if home occupied (used by 200 automations)
- Add time window: Only between 8 AM - 10 PM (used by 180 automations)

**Timing Improvements:**
- Trigger 30 minutes before sunset instead of exactly at sunset
- Add 5 minute delay before action to avoid false triggers

**Action Variations:**
- Use brightness: 50% instead of 100% for energy saving
- Set color temperature: 2700K for warm evening ambiance

**Note:** These are optional enhancements. Prioritize user's existing patterns (80% weight). Community insights should augment, not replace, personal patterns (20% weight).

Generate 10 automation suggestions...
```

### Enhancement Applicability Logic

```python
def _is_applicable(
    enhancement: Enhancement,
    user_devices: List[str]
) -> bool:
    """Check if enhancement is applicable to user's setup"""
    
    # Weather enhancements: Only if user has weather integration
    if enhancement.category == 'weather':
        return 'weather' in user_integrations
    
    # Occupancy enhancements: Only if user has occupancy sensors
    if enhancement.category == 'occupancy':
        return any(d in user_devices for d in ['motion_sensor', 'occupancy_sensor', 'person'])
    
    # Device-specific enhancements
    required_devices = enhancement.applicable_devices
    return any(d in user_devices for d in required_devices)
```

### Caching Strategy

**Why Cache:**
- Community corpus changes weekly (Story AI4.4)
- User's device list rarely changes
- Query results stable for 7 days

**Cache Key:**
```
{device_type}:{integration}:{use_case}:{min_quality}
```

**Cache Invalidation:**
- TTL: 7 days
- Manual: Clear cache after weekly Miner refresh (Story AI4.4)
- Storage: In-memory dict (simple, no Redis needed)

### Performance Budget

**Current Phase 1 Analysis Time:** ~45 seconds  
**Allowed Overhead:** 5% = 2.25 seconds  
**Miner Integration Budget:**
- Pattern detection queries: 3-5 queries × 100ms = 0.3-0.5s
- Enhancement extraction: 0.1s
- Prompt building: 0.05s
- **Total:** ~0.5-0.7s ✅ Well under 2.25s budget

### Metrics to Track

```python
from shared.metrics_collector import MetricsCollector

metrics = MetricsCollector()

# During pattern detection
start = time.time()
community_insights = await miner_client.search_corpus(...)
metrics.record_timing('miner.query.latency', time.time() - start)
metrics.increment('miner.query.count')

if not community_insights:
    metrics.increment('miner.query.failures')

# During suggestion generation
enhancements_used = parse_enhancements_from_suggestion(suggestion)
metrics.increment('enhancements.injected', len(enhancements_used))

# When user accepts suggestion
if user_accepted:
    for enh in enhancements_used:
        if enh['accepted']:
            metrics.increment(f'enhancements.accepted.{enh["category"]}')
```

**Dashboard:**
- Miner query success rate (target: >95%)
- Average enhancement count per suggestion (target: 2-3)
- Enhancement acceptance rate (target: >30%)
- Phase 1 analysis time increase (target: <5%)

### Testing Scenarios

1. **Miner Unavailable:**
   - Mock Miner to return 503 Service Unavailable
   - Verify analysis continues with Phase 1 patterns only
   - Verify no error thrown to user

2. **Miner Timeout:**
   - Mock Miner to delay response 200ms (>100ms timeout)
   - Verify query cancelled, graceful degradation
   - Verify warning logged

3. **No Matching Automations:**
   - User has rare device (e.g., custom DIY sensor)
   - Miner returns empty list
   - Verify no enhancements injected, no errors

4. **High-Quality Enhancements:**
   - Mock Miner to return 5 automations with quality_score > 0.9
   - Verify top 3 conditions/timing/actions extracted
   - Verify applicable_devices filter works

### Security Considerations

- **Input validation**: Sanitize device names before Miner query (prevent injection)
- **Output validation**: Validate Miner response schema (Pydantic model)
- **Timeout enforcement**: Hard 100ms timeout (prevent DoS if Miner slow)
- **Error handling**: Never expose Miner errors to user

---

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-10-18 | 1.0 | Story created with Phase 3/5 integration | BMad Master |

---

## Dev Agent Record

### Agent Model Used
*Populated during implementation*

### Debug Log References
*Populated during implementation*

### Completion Notes List
*Populated during implementation*

### File List
*Populated during implementation*

---

## QA Results
*QA Agent review pending*

