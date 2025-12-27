# Story AI1.8: Suggestion Generation Pipeline

**Epic:** Epic-AI-1 - AI Automation Suggestion System  
**Story ID:** AI1.8  
**Priority:** Critical  
**Estimated Effort:** 10-12 hours  
**Dependencies:** Story AI1.7 (LLM integration)

---

## User Story

**As a** user  
**I want** the system to generate automation suggestions from detected patterns  
**so that** I can review and approve them

---

## Business Value

- Transforms patterns into actionable suggestions
- Limits to 5-10 best suggestions per week (quality over quantity)
- Ranks by confidence for user prioritization
- Avoids duplicates and low-value suggestions

---

## Acceptance Criteria

1. ✅ Generates 5-10 suggestions per weekly run
2. ✅ Suggestions ranked by confidence (highest first)
3. ✅ Each suggestion linked to source pattern
4. ✅ No duplicate suggestions (same device + action)
5. ✅ Suggestions stored with status tracking (pending/approved/deployed/rejected)
6. ✅ Generation time <5 minutes for 10 suggestions
7. ✅ API cost <$1 per batch
8. ✅ Suggestion quality manually validated (>70% acceptance expected)

---

## Technical Implementation Notes

### Suggestion Generator

**Create: src/suggestion_generator.py**

```python
from src.llm.openai_client import OpenAIClient
from src.database.crud import store_suggestions
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class SuggestionGenerator:
    """Generates automation suggestions from detected patterns"""
    
    def __init__(self, llm_client: OpenAIClient):
        self.llm = llm_client
        self.max_suggestions_per_run = 10
    
    async def generate_suggestions(
        self, 
        patterns: Dict[str, List[Dict]]
    ) -> List[Dict]:
        """
        Generate automation suggestions from all pattern types.
        
        Args:
            patterns: Dict with keys 'time_of_day', 'co_occurrence', 'anomaly_opportunities'
        
        Returns:
            List of suggestion dicts ready for database storage
        """
        
        # 1. Flatten and rank all patterns by confidence
        all_patterns = []
        for pattern_type, pattern_list in patterns.items():
            for pattern in pattern_list:
                pattern['_type'] = pattern_type  # Preserve type
                all_patterns.append(pattern)
        
        # Sort by confidence (highest first)
        all_patterns.sort(key=lambda p: p['confidence'], reverse=True)
        
        # 2. Limit to top patterns (quality over quantity)
        top_patterns = all_patterns[:self.max_suggestions_per_run]
        
        logger.info(f"Selected top {len(top_patterns)} patterns for suggestion generation")
        
        # 3. Generate suggestions via LLM
        suggestions = []
        
        for pattern in top_patterns:
            try:
                # Call LLM for each pattern
                suggestion = await self.llm.generate_automation_suggestion(pattern)
                
                # Add metadata
                suggestion_dict = {
                    'title': suggestion.alias,
                    'description': suggestion.description,
                    'automation_yaml': suggestion.automation_yaml,
                    'rationale': suggestion.rationale,
                    'category': suggestion.category,
                    'priority': suggestion.priority,
                    'confidence': pattern['confidence'],
                    'pattern_id': pattern.get('id'),  # Link to pattern
                    'pattern_type': pattern['_type'],
                    'status': 'pending'
                }
                
                suggestions.append(suggestion_dict)
                logger.info(f"Generated suggestion: {suggestion.alias}")
                
            except Exception as e:
                logger.error(f"Failed to generate suggestion for pattern {pattern}: {e}")
                continue
        
        logger.info(f"Generated {len(suggestions)} suggestions (cost: ${self.llm.total_tokens_used * 0.0000006:.2f})")
        
        return suggestions
    
    def deduplicate_suggestions(self, suggestions: List[Dict]) -> List[Dict]:
        """Remove duplicate suggestions"""
        seen = set()
        unique = []
        
        for sugg in suggestions:
            # Create key from device + action
            key = (sugg.get('device_id'), sugg.get('action_type'))
            
            if key not in seen:
                seen.add(key)
                unique.append(sugg)
        
        logger.info(f"Deduplication: {len(suggestions)} → {len(unique)} suggestions")
        return unique
```

### Batch Generation Workflow

```python
# src/batch_suggestion_job.py
async def run_daily_suggestion_generation():
    """
    Daily batch job to generate suggestions.
    Called by scheduler (Story 1.9)
    """
    
    # 1. Fetch patterns from database
    patterns = await fetch_latest_patterns()
    
    # 2. Generate suggestions
    generator = SuggestionGenerator(llm_client)
    suggestions = await generator.generate_suggestions(patterns)
    
    # 3. Deduplicate
    suggestions = generator.deduplicate_suggestions(suggestions)
    
    # 4. Store in database
    await store_suggestions(suggestions)
    
    # 5. Publish MQTT notification
    await mqtt_client.publish(
        "ha-ai/status/suggestions_ready",
        json.dumps({"count": len(suggestions)})
    )
    
    logger.info(f"Batch job complete: {len(suggestions)} suggestions generated")
```

---

## Integration Verification

**IV1: Suggestion generation doesn't block pattern analysis**
- Runs after pattern detection completes
- Async processing (non-blocking)
- Can be cancelled if needed

**IV2: SQLite database handles concurrent reads/writes**
- WAL mode enabled
- Patterns read, suggestions written
- No lock contention

**IV3: LLM API costs tracked and logged**
- Total tokens logged per batch
- Cost calculated and logged
- Alert if exceeds $2 per batch

**IV4: Total pipeline (pattern + suggestion) <15 minutes**
- Pattern detection: ~10 min
- LLM generation: <5 min
- Total: <15 min (acceptable)

---

## Tasks Breakdown

1. **Create SuggestionGenerator class** (2 hours)
2. **Implement pattern ranking logic** (1 hour)
3. **Integrate with OpenAI client** (2 hours)
4. **Implement deduplication** (1.5 hours)
5. **Add suggestion storage** (1 hour)
6. **Create batch workflow** (1.5 hours)
7. **Unit tests** (1.5 hours)
8. **End-to-end test with real patterns** (1 hour)
9. **Quality validation** (1 hour)

**Total:** 10-12 hours

---

## Testing Strategy

### Unit Tests

```python
# tests/test_suggestion_generator.py
import pytest
from src.suggestion_generator import SuggestionGenerator
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_limits_to_max_suggestions():
    """Test only generates max 10 suggestions even if more patterns"""
    
    # 20 patterns, but should only generate 10 suggestions
    patterns = {
        'time_of_day': [{'confidence': 0.9}] * 20
    }
    
    mock_llm = AsyncMock()
    generator = SuggestionGenerator(mock_llm)
    
    await generator.generate_suggestions(patterns)
    
    # Should only call LLM 10 times
    assert mock_llm.generate_automation_suggestion.call_count <= 10

@pytest.mark.asyncio
async def test_ranks_by_confidence():
    """Test suggestions generated from highest confidence patterns"""
    
    patterns = {
        'time_of_day': [
            {'confidence': 0.95, 'device_id': 'high'},
            {'confidence': 0.60, 'device_id': 'low'},
            {'confidence': 0.85, 'device_id': 'medium'},
        ]
    }
    
    mock_llm = AsyncMock()
    generator = SuggestionGenerator(mock_llm)
    
    await generator.generate_suggestions(patterns)
    
    # First call should be highest confidence pattern
    first_call_args = mock_llm.generate_automation_suggestion.call_args_list[0][0][0]
    assert first_call_args['confidence'] == 0.95
```

---

## Definition of Done

- [ ] SuggestionGenerator class implemented
- [ ] Pattern ranking by confidence
- [ ] LLM integration working
- [ ] Deduplication logic implemented
- [ ] Suggestion storage to SQLite
- [ ] Batch workflow functional
- [ ] Generates 5-10 suggestions per run
- [ ] Cost <$1 per batch verified
- [ ] Unit tests pass (80%+ coverage)
- [ ] Quality validation >70% acceptance
- [ ] Code reviewed and approved

---

## Reference Files

**Copy patterns from:**
- Story AI1.7 for LLM client usage
- `services/data-api/src/database/crud.py` for database patterns

---

## Notes

- Quality > quantity (5-10 suggestions is intentional)
- Ranking ensures best patterns get suggested first
- Deduplication prevents annoying users with duplicates
- Cost tracking critical to stay within $10/month budget
- Manual quality validation important in early runs

---

**Story Status:** Not Started  
**Assigned To:** TBD  
**Created:** 2025-10-15  
**Updated:** 2025-10-15

