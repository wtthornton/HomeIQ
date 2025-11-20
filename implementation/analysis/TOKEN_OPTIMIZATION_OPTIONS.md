# Token Optimization Options for Ask AI Clarification Flow (REVIEWED & UPDATED)

**Date:** November 20, 2025  
**Last Review:** November 20, 2025  
**Issue:** Prompt using 25,557 tokens (86.5% of 30,000 budget), leaving insufficient room for response  
**Current State:** Response hits token limit (`finish_reason: "length"`), causing timeout

---

## 🎯 Executive Summary

**Code Review Findings:**
- ✅ **80% Code Reuse:** Options 1-3 leverage existing infrastructure (EntityValidator, compressor, RAG)
- ✅ **Epic 31 Compliant:** All options follow direct patterns (no intermediate services)
- ✅ **2025 Patterns:** Uses hybrid retrieval, semantic scoring, structured data
- ✅ **Low Risk:** Enhancing existing code vs. building new systems

**Updated Recommendations:**
1. **Option 3 (95/100):** Enhanced relevance filtering using EntityValidator scoring → **4k-6k token savings**
2. **Option 1 (85/100):** Aggressive compression with prioritization → **3k-5k token savings**
3. **Combined Impact:** 7k-11k tokens saved (from 25,557 to ~14,557 tokens)

**Implementation Effort:** 2-3 hours (80% code reuse, 20% enhancement)

---

## Code Review Summary

**Existing Code to Leverage:**
- ✅ **Entity Filtering Logic** (`ask_ai_router.py:3700-3817`) - Already filters by location/name/domain
- ✅ **Entity Compression** (`entity_context_compressor.py`) - Already compresses entities
- ✅ **Hybrid Entity Scoring** (`entity_validator.py:_find_best_match_full_chain`) - Embedding + fuzzy + exact matching
- ✅ **RAG System** (`rag/client.py`) - Semantic similarity with cosine similarity
- ✅ **Token Budget System** (`token_budget.py`) - Already enforces token limits per component
- ✅ **Epic 31 Architecture** - Direct InfluxDB writes, no intermediate services

**2025 Architecture Patterns Found:**
- ✅ Hybrid retrieval (dense + sparse) with cross-encoder reranking
- ✅ RAG semantic search with embeddings
- ✅ Multi-model entity extraction (NER → OpenAI → Pattern)
- ✅ Token budget enforcement per component

**Gaps Identified:**
- ⚠️ Entity filtering doesn't use semantic relevance scoring (only location/name matching)
- ⚠️ Compression doesn't prioritize entities by relevance before truncating
- ⚠️ Clarification context formatting is verbose (can be summarized)
- ⚠️ Token budget set to 10k but can be optimized further

---

## Current Token Breakdown

Based on logs from the clarification submission:
- **Entity Context JSON:** ~9,158 tokens (33 entities, compressed from 45)
- **Clarification Context:** ~1,500-2,000 tokens (Q&A pairs with verbose formatting)
- **System Prompt:** ~800-1,200 tokens
- **User Prompt Instructions:** ~2,500-3,500 tokens
- **Enriched Query:** ~200-500 tokens
- **Pattern Guidance:** ~1,000-1,500 tokens
- **Total:** 25,557 tokens (prompt) + 1,200 tokens (response) = 26,757 tokens
- **Available for Response:** Only ~4,443 tokens remaining

---

## Option Comparison Table

| Option | Token Savings | Implementation Complexity | Response Quality Impact | Risk Level | Priority Score |
|--------|--------------|---------------------------|------------------------|------------|----------------|
| **1. Aggressive Entity Compression** | ~3,000-5,000 tokens | Low | Low-Medium | Low | **85/100** |
| **2. Summarize Clarification Context** | ~1,000-1,500 tokens | Medium | Low | Low | **75/100** |
| **3. Smart Entity Filtering** | ~4,000-6,000 tokens | Medium | Very Low | Low | **90/100** |
| **4. Compact Prompt Template** | ~1,500-2,500 tokens | Low | Low | Very Low | **70/100** |
| **5. Two-Stage Processing** | ~5,000-7,000 tokens | High | Very Low | Medium | **80/100** |

---

## Detailed Option Analysis

### Option 1: Aggressive Entity Context Compression ⭐ RECOMMENDED

**Description:**
Reduce entity context from 10,000 tokens to 7,000 tokens and enhance existing compression with smarter strategies.

**Existing Code to Leverage:**
- `compress_entity_context()` in `entity_context_compressor.py` (already compresses)
- `filter_entity_attributes()` helper function (already filters attributes)
- `summarize_entity_capabilities()` helper function (already summarizes)

**Changes:**
1. **Config Update:** Lower `max_entity_context_tokens` from 10,000 to 7,000
2. **Enhance Compression:**
   - Summarize `effect_list` arrays (e.g., "12 effects: rainbow, theater_chase..." instead of full list)
   - Remove verbose device intelligence (manufacturer, model) unless explicitly mentioned in query
   - Aggregate similar entities (e.g., group by area/domain before compressing)
3. **Prioritize Before Compression:** Use relevance scoring to keep most important entities first

**Token Savings:** 3,000-5,000 tokens  
**Implementation:** 
- Update `config.py`: `max_entity_context_tokens = 7_000`
- Enhance `compress_entity_context()` in `entity_context_compressor.py`:
  - Add `effect_list` summarization (already has capability summarization logic)
  - Add entity grouping/aggregation before compression
  - Remove device_intelligence details (already filtered, but can be more aggressive)
- **NEW:** Sort entities by relevance before compression (most relevant first)

**Pros:**
- ✅ Quick to implement (leverages existing compression infrastructure)
- ✅ Low risk (compression already working, just enhancing it)
- ✅ Significant token savings (3k-5k tokens)
- ✅ Response quality maintained (keeps most relevant entities)
- ✅ Uses existing `filter_entity_attributes()` and `summarize_entity_capabilities()` helpers

**Cons:**
- ⚠️ May lose some device-specific details for less relevant entities
- ⚠️ Effect lists won't be fully enumerated (only summary)

**Code Changes Required:**
```python
# services/ai-automation-service/src/config.py (Line 134)
max_entity_context_tokens: int = 7_000  # Reduced from 10_000

# services/ai-automation-service/src/utils/entity_context_compressor.py
# Enhance compress_entity_context():
def compress_entity_context(
    entities: dict[str, dict[str, Any]],
    max_tokens: int = 7_000,  # Updated default
    model: str = "gpt-4o",
    relevance_scores: dict[str, float] | None = None  # NEW: Sort by relevance
) -> dict[str, dict[str, Any]]:
    # NEW: Sort by relevance before compression (if scores provided)
    if relevance_scores:
        entities = {k: v for k, v in sorted(
            entities.items(),
            key=lambda x: relevance_scores.get(x[0], 0.0),
            reverse=True
        )}
    
    # Enhance: Summarize effect_list arrays
    # Enhance: Remove device_intelligence unless critical
    # Use existing filter_entity_attributes() and summarize_entity_capabilities()
```

**Affected Files:**
- `services/ai-automation-service/src/config.py` (1 line)
- `services/ai-automation-service/src/utils/entity_context_compressor.py` (~50 lines enhancement)
- `services/ai-automation-service/src/api/ask_ai_router.py` (pass relevance_scores to compressor)

**Priority Score: 85/100** - Best balance of effort vs. impact, leverages existing code

---

### Option 2: Summarize Clarification Context

**Description:**
Replace verbose Q&A formatting with concise summary format using structured extraction.

**Existing Code to Leverage:**
- `unified_prompt_builder.py` (Line 240-275) - Already formats clarification context
- Can leverage entity extraction from clarification answers (already parsed)

**Current Format (verbose):**
```
═══════════════════════════════════════════════════════════════════════════════
CLARIFICATION CONTEXT (CRITICAL - USER PROVIDED ANSWERS):
═══════════════════════════════════════════════════════════════════════════════
The user was asked clarifying questions and provided these specific answers. 
YOU MUST USE THESE ANSWERS when generating suggestions. DO NOT IGNORE THEM.

1. Q: When you say "return back to its current state," do you want...
   A: the office LED light that is powered by WLED
   Selected entities: light.office_wled

CRITICAL REQUIREMENTS (MUST FOLLOW):
[Long list of instructions...]
═══════════════════════════════════════════════════════════════════════════════
```

**Optimized Format (Structured Summary):**
```
CLARIFICATION ANSWERS:
- Location: office
- Device: office LED (WLED)
- Action: turn brightness up (dial)
- Entities: light.office_wled

REQUIREMENTS: Use ONLY specified devices/locations, respect user choices.
```

**Token Savings:** 1,000-1,500 tokens  
**Implementation:**
- Update `unified_prompt_builder.py` clarification section (Line 240-275)
- Extract structured data from Q&A:
  - Extract locations (from answers mentioning "office", "bedroom", etc.)
  - Extract device names/entities (from `selected_entities` or answer text)
  - Extract actions/requirements (summarize from answers)
- Use compact bullet format instead of verbose text

**Pros:**
- ✅ Moderate token savings (1k-1.5k tokens)
- ✅ **Leverages existing entity extraction** (entities already parsed)
- ✅ Improves prompt readability (structured format)
- ✅ Preserves critical information (locations, entities, requirements)
- ✅ Easy to implement (formatting change only)
- ✅ **Follows 2025 pattern** (structured data > verbose text)

**Cons:**
- ⚠️ May lose nuance in complex user answers (mitigated by keeping requirements)
- ⚠️ Requires careful extraction logic (but entities already extracted)

**Code Changes Required:**
```python
# services/ai-automation-service/src/prompt_building/unified_prompt_builder.py
# Enhance clarification_section formatting (around Line 240):

def _format_clarification_context_compact(
    clarification_context: dict[str, Any]
) -> str:
    """Format clarification context in compact, structured format."""
    if not clarification_context or not clarification_context.get('questions_and_answers'):
        return ""
    
    qa_list = clarification_context['questions_and_answers']
    
    # Extract structured information
    locations = set()
    devices = set()
    entities = set()
    actions = []
    
    for qa in qa_list:
        answer = qa.get('answer', '').lower()
        
        # Extract location mentions
        location_keywords = ['office', 'bedroom', 'living room', 'kitchen', 'garage']
        for loc in location_keywords:
            if loc in answer:
                locations.add(loc)
        
        # Extract entities
        if qa.get('selected_entities'):
            entities.update(qa['selected_entities'])
        
        # Extract device mentions
        if 'wled' in answer or 'led' in answer:
            devices.add('LED/WLED')
        if any(domain in answer for domain in ['light', 'switch', 'sensor']):
            devices.add(answer.split()[0])  # First device mention
    
    # Build compact format
    parts = []
    if locations:
        parts.append(f"- Location: {', '.join(sorted(locations))}")
    if devices:
        parts.append(f"- Devices: {', '.join(sorted(devices))}")
    if entities:
        parts.append(f"- Entities: {', '.join(sorted(list(entities)[:5]))}")  # Limit to 5
    if actions:
        parts.append(f"- Actions: {', '.join(actions[:3])}")  # Limit to 3
    
    if not parts:
        return ""  # Fallback to verbose if extraction fails
    
    return f"""CLARIFICATION ANSWERS:
{chr(10).join(parts)}

REQUIREMENTS: Use ONLY specified devices/locations, respect user choices."""
```

**Affected Files:**
- `services/ai-automation-service/src/prompt_building/unified_prompt_builder.py` (~50 lines, replaces verbose formatting)

**Priority Score: 75/100** - Good improvement with minimal risk, leverages existing entity extraction

---

### Option 3: Enhanced Relevance-Based Entity Filtering ⭐ HIGHEST IMPACT

**Description:**
Enhance existing entity filtering with semantic relevance scoring using existing RAG/EntityValidator infrastructure.

**Existing Code to Leverage:**
- ✅ **Location/Name Filtering** (`ask_ai_router.py:3700-3817`) - Already filters by location/name/domain
- ✅ **EntityValidator Hybrid Scoring** (`entity_validator.py:_find_best_match_full_chain`) - Embedding (35%) + exact (30%) + fuzzy (15%) + numbered (15%) + location (5%)
- ✅ **RAG Client** (`rag/client.py`) - Semantic similarity with cosine similarity
- ✅ **Multi-Model Entity Extraction** - Already extracts entities from query

**Current State:**
- Filters by location (office → office entities)
- Filters by device name (matches extracted names)
- Filters by domain (light → light.* entities)
- **GAP:** No semantic relevance scoring, no prioritization before compression

**Enhancement:**
1. **Use Existing EntityValidator Scoring:**
   - Leverage `_find_best_match_full_chain()` hybrid scoring
   - Score each entity against enriched query + clarification answers
   - Use existing embedding similarity (35% weight) + exact match (30%) + fuzzy (15%)
2. **Prioritize Before Filtering:**
   - Score all entities first (even those outside location/name filters)
   - Keep top N most relevant (20-25 entities)
   - Entities mentioned in clarification answers get 2x relevance boost
3. **Then Apply Existing Filters:**
   - Location filtering (existing)
   - Name filtering (existing)
   - Domain filtering (existing)
4. **Finally Compress:**
   - Pass relevance scores to compressor (Option 1)
   - Compressor keeps most relevant entities first

**Token Savings:** 4,000-6,000 tokens  
**Implementation:**
- **Leverage Existing:** Use EntityValidator's `_find_best_match_full_chain()` for scoring
- **Enhance:** Add relevance scoring function that wraps EntityValidator
- **New Logic:** Score all entities, keep top N, then apply existing filters
- **Integration:** Pass relevance scores to Option 1's compressor

**Pros:**
- ✅ Highest token savings potential (4k-6k tokens)
- ✅ **Leverages existing EntityValidator infrastructure** (no new scoring logic needed)
- ✅ **Uses existing RAG/embedding system** (semantic similarity already working)
- ✅ Improves response quality (focuses on most relevant devices)
- ✅ Low risk (enhances existing filtering, can fallback to current behavior)
- ✅ Better user experience (more focused suggestions)
- ✅ **Follows 2025 patterns** (hybrid retrieval, semantic scoring)

**Cons:**
- ⚠️ Requires EntityValidator instantiation (may add ~10-20ms latency)
- ⚠️ May miss edge cases if scoring threshold too high (mitigated by keeping top N)

**Code Changes Required:**
```python
# services/ai-automation-service/src/api/ask_ai_router.py
# NEW: Add relevance scoring function (leverages existing EntityValidator)
async def _score_entities_by_relevance(
    entities: list[dict[str, Any]],
    query: str,
    clarification_answers: list[dict[str, Any]] | None = None,
    entity_validator: EntityValidator | None = None
) -> dict[str, float]:
    """
    Score entities by relevance using existing EntityValidator hybrid scoring.
    Leverages embedding similarity + exact match + fuzzy matching.
    """
    scores = {}
    
    # Build enriched query from original + clarification answers
    enriched_query = query
    if clarification_answers:
        qa_summary = "\n".join([f"Q: {qa['question']}\nA: {qa['answer']}" 
                               for qa in clarification_answers])
        enriched_query = f"{query}\n\nUser clarifications:\n{qa_summary}"
    
    # Use existing EntityValidator scoring for each entity
    if entity_validator:
        for entity in entities:
            entity_id = entity.get('entity_id', '')
            # Use existing _find_best_match_full_chain() logic
            # Score = embedding (35%) + exact (30%) + fuzzy (15%) + location (5%)
            score = await entity_validator._score_entity_relevance(
                entity_id=entity_id,
                query=enriched_query,
                entity_data=entity
            )
            scores[entity_id] = score
    
    return scores

# Enhance existing filtering (around line 3700):
# 1. Score all entities first (before location/name filtering)
relevance_scores = await _score_entities_by_relevance(
    enriched_entities,
    query=enriched_query,
    clarification_answers=clarification_context.get('questions_and_answers'),
    entity_validator=_entity_validator  # Use existing instance
)

# 2. Keep top N most relevant
top_n = 25
sorted_entity_ids = sorted(
    enriched_data.keys(),
    key=lambda eid: relevance_scores.get(eid, 0.0),
    reverse=True
)[:top_n]

# 3. Then apply existing location/name filters (lines 3700-3817)
# 4. Pass relevance_scores to compressor (Option 1)
```

**Affected Files:**
- `services/ai-automation-service/src/api/ask_ai_router.py` (~100 lines enhancement, leverages existing EntityValidator)
- `services/ai-automation-service/src/services/entity_validator.py` (add `_score_entity_relevance()` helper, wraps existing `_find_best_match_full_chain()`)

**2025 Architecture Pattern Compliance:**
- ✅ Uses existing hybrid retrieval (embedding + exact + fuzzy)
- ✅ Leverages RAG semantic search infrastructure
- ✅ Follows Epic 31 patterns (direct, no intermediate services)
- ✅ Uses existing EntityValidator (no new dependencies)

**Priority Score: 95/100** - Highest impact, leverages existing code, low complexity

---

### Option 4: Compact Prompt Template

**Description:**
Reduce verbosity in system prompt and user prompt instructions.

**Current Verbose Sections:**
- Long pattern guidance descriptions
- Repetitive device naming requirements
- Verbose capability examples
- Long critical requirements sections

**Optimizations:**
- Use bullet points instead of paragraphs
- Remove redundant instructions
- Compress pattern guidance (show patterns, not full descriptions)
- Reduce capability examples to 2-3 per type

**Token Savings:** 1,500-2,500 tokens  
**Implementation:**
- Edit `unified_prompt_builder.py` template strings
- Compress pattern guidance rendering
- Reduce capability examples

**Pros:**
- ✅ Quick to implement (text editing)
- ✅ Very low risk
- ✅ Improves prompt readability

**Cons:**
- ⚠️ Moderate token savings only
- ⚠️ May require testing to ensure instructions still clear

**Code Changes Required:**
```python
# services/ai-automation-service/src/prompt_building/unified_prompt_builder.py
# Compress template strings, reduce examples
```

**Priority Score: 70/100** - Good quick win, limited impact

---

### Option 5: Two-Stage Processing Approach

**Description:**
Generate suggestions in two stages:
1. **Stage 1 (Lightweight):** Generate suggestion structure with minimal context (~15,000 tokens)
2. **Stage 2 (Enrichment):** If needed, enrich specific suggestions with detailed entity context

**Flow:**
1. First API call: Compact prompt → Generate suggestion skeletons
2. If suggestions need entity details: Second API call with only relevant entities per suggestion

**Token Savings:** 5,000-7,000 tokens (in first call)  
**Implementation:**
- Split suggestion generation into two functions
- Add decision logic for when enrichment needed
- Cache entity context for stage 2

**Pros:**
- ✅ Highest potential token savings
- ✅ Allows for more detailed suggestions when needed
- ✅ Better scalability

**Cons:**
- ⚠️ High complexity (architectural change)
- ⚠️ Requires two API calls (latency increase)
- ⚠️ Medium risk (new code path)

**Code Changes Required:**
```python
# Major refactoring:
# 1. Create generate_suggestion_skeletons() - lightweight
# 2. Create enrich_suggestion() - detailed
# 3. Add orchestration logic
```

**Priority Score: 80/100** - High impact but high complexity

---

## Recommended Implementation Strategy

### Phase 1: Quick Wins (Implement Immediately) ⭐ UPDATED
1. **Option 3: Enhanced Relevance-Based Filtering** (95/100) - Highest impact, leverages existing code
2. **Option 1: Aggressive Entity Compression** (85/100) - Easy + effective, enhances existing compressor

**Combined Savings:** ~7,000-11,000 tokens  
**New Total:** ~14,557-18,557 tokens (48-62% of budget)  
**Available for Response:** ~11,443-15,443 tokens (enough for full response)

**Why This Order:**
- Option 3 provides relevance scores → Option 1 uses those scores for prioritized compression
- Both leverage existing infrastructure (EntityValidator, compression utilities)
- Minimal new code, maximum impact

### Phase 2: Further Optimization (If Needed)
3. **Option 2: Summarize Clarification Context** (75/100)
4. **Option 4: Compact Prompt Template** (70/100)

**Additional Savings:** ~2,500-4,000 tokens  
**New Total:** ~10,557-16,057 tokens (35-54% of budget)  
**Available for Response:** ~13,943-19,443 tokens (plenty of room)

### Phase 3: Advanced (Future Consideration)
5. **Option 5: Two-Stage Processing** (80/100) - Only if needed for more complex queries

---

## Implementation Priority Matrix (UPDATED)

| Priority | Options | Combined Token Savings | Estimated Effort | Leverages Existing | Recommended Order |
|----------|---------|----------------------|------------------|-------------------|-------------------|
| **HIGH** | #3 + #1 | ~7,000-11,000 tokens | 2-3 hours | ✅ EntityValidator, Compressor | Implement first |
| **MEDIUM** | #2 + #4 | ~2,500-4,000 tokens | 1-2 hours | ✅ Entity extraction, Templates | Implement if needed |
| **LOW** | #5 | ~5,000-7,000 tokens | 4-6 hours | ❌ New architecture | Consider later |

**Key Insight:**
- Options 1-3 all leverage existing code, reducing risk and implementation time
- Option 3's relevance scores feed into Option 1's prioritization (synergy)
- Minimal new code paths, mostly enhancements to existing utilities

---

## Decision Framework

**Choose Option 3 + Option 1 if:**
- ✅ You want maximum impact with moderate effort
- ✅ You want to maintain response quality
- ✅ You need solution quickly

**Add Option 2 if:**
- ✅ Clarification context is frequently verbose
- ✅ You want additional safety margin

**Consider Option 5 if:**
- ✅ After implementing options 1-4, you still hit token limits
- ✅ You need to support very complex queries (50+ entities)
- ✅ You're willing to accept architectural changes

---

## Expected Results After Phase 1

**Before:**
- Prompt: 25,557 tokens
- Available for response: ~4,443 tokens
- Result: Response truncated (`finish_reason: "length"`)

**After Phase 1 (Options 1 + 3):**
- Prompt: ~14,557-18,557 tokens
- Available for response: ~11,443-15,443 tokens
- Result: Full response generated successfully ✅

**Safety Margin:** 38-51% of budget available for response (healthy buffer)

---

## Next Steps

1. **Review and approve** one or multiple options
2. **Prioritize implementation** based on priority scores
3. **Implement Phase 1** (Options 1 + 3) for immediate relief
4. **Test with actual queries** to verify token savings
5. **Monitor** token usage to ensure improvements hold

---

---

## Code Review Findings

### Existing Code Leveraged

1. **Entity Filtering Infrastructure:**
   - Location filtering: `ask_ai_router.py:3700-3817`
   - Name filtering: `ask_ai_router.py:3751-3817`
   - Domain filtering: `ask_ai_router.py:3804-3807`
   - **Status:** ✅ Working, can be enhanced with relevance scoring

2. **Entity Compression Infrastructure:**
   - `compress_entity_context()`: `entity_context_compressor.py:15-129`
   - `filter_entity_attributes()`: `entity_context_compressor.py:159-203`
   - `summarize_entity_capabilities()`: `entity_context_compressor.py:132-157`
   - **Status:** ✅ Working, can be enhanced with effect_list summarization

3. **Relevance Scoring Infrastructure:**
   - EntityValidator hybrid scoring: `entity_validator.py:_find_best_match_full_chain()`
   - Embedding similarity: Uses sentence-transformers (35% weight)
   - RAG semantic search: `rag/client.py` with cosine similarity
   - **Status:** ✅ Working, can be reused for entity relevance scoring

4. **Token Budget System:**
   - `token_budget.py`: Enforces limits per component
   - `token_counter.py`: Accurate token counting
   - Config: `max_entity_context_tokens = 10_000`
   - **Status:** ✅ Working, just needs config adjustment

### Architecture Compliance

✅ **Epic 31 Compliance:** All options follow direct patterns (no intermediate services)  
✅ **2025 Patterns:** Uses hybrid retrieval, semantic scoring, structured data  
✅ **Code Reuse:** Leverages existing utilities (80% reuse, 20% enhancement)  
✅ **Risk Level:** Low (enhancing existing code vs. building new systems)

---

**Document Version:** 2.0 (Reviewed & Updated)  
**Last Updated:** November 20, 2025  
**Review Status:** ✅ Code reviewed, existing infrastructure identified, plan updated
