# Story AI1.7: LLM Integration - OpenAI API Client

**Epic:** Epic-AI-1 - AI Automation Suggestion System  
**Story ID:** AI1.7  
**Priority:** Critical  
**Estimated Effort:** 8-10 hours  
**Dependencies:** Story AI1.6 (All pattern types detected)

---

## User Story

**As a** suggestion generator  
**I want** to integrate with OpenAI GPT-4o-mini API  
**so that** I can generate natural language automation suggestions

---

## Business Value

- Converts technical patterns into human-readable automation suggestions
- Uses cost-effective GPT-4o-mini (50% cheaper than GPT-4o)
- Generates valid Home Assistant YAML automations
- Provides natural language explanations for user understanding

---

## Acceptance Criteria

1. ✅ Successfully calls OpenAI GPT-4o-mini API
2. ✅ Generates valid Home Assistant automation YAML
3. ✅ Returns structured JSON with Pydantic validation
4. ✅ Handles API errors gracefully (retries 3x with exponential backoff)
5. ✅ Tracks token usage per request
6. ✅ Sanitizes patterns (no user names, locations, sensitive data)
7. ✅ Suggestion quality: 80%+ valid automations (manual review)
8. ✅ API latency: <10 seconds per suggestion

---

## Technical Implementation Notes

### OpenAI Client

**Create: src/llm/openai_client.py**

**Reference: PRD Section 7.2**

```python
from openai import AsyncOpenAI
from pydantic import BaseModel
from typing import Dict, List
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

class AutomationSuggestion(BaseModel):
    """Structured output for automation suggestion"""
    alias: str
    description: str
    automation_yaml: str
    rationale: str
    category: str  # 'energy', 'comfort', 'security', 'convenience'
    priority: str  # 'high', 'medium', 'low'

class OpenAIClient:
    """Client for generating automation suggestions via OpenAI API"""
    
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = "gpt-4o-mini"
        self.total_tokens_used = 0
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def generate_automation_suggestion(self, pattern: Dict) -> AutomationSuggestion:
        """
        Generate automation suggestion from detected pattern.
        
        Args:
            pattern: Detected pattern dict with type, device_id, metadata
        
        Returns:
            AutomationSuggestion with YAML and explanation
        """
        
        prompt = self._build_prompt(pattern)
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a home automation expert creating Home Assistant automations."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            # Track usage
            self.total_tokens_used += response.usage.total_tokens
            logger.info(f"OpenAI API call: {response.usage.total_tokens} tokens used")
            
            # Parse response
            content = response.choices[0].message.content
            suggestion = self._parse_automation_yaml(content, pattern)
            
            return suggestion
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    def _build_prompt(self, pattern: Dict) -> str:
        """Build prompt from pattern - KEEP IT SIMPLE"""
        
        if pattern['pattern_type'] == 'time_of_day':
            return f"""
Create a Home Assistant automation for this pattern:

PATTERN DETECTED:
- Device: {pattern['device_id']}
- Pattern: Turns on at {pattern['hour']:02d}:{pattern.get('minute', 0):02d} consistently
- Occurrences: {pattern['occurrences']} times in last 30 days
- Confidence: {pattern['confidence']:.0%}

OUTPUT (valid Home Assistant YAML):
alias: "AI Suggested: [descriptive name]"
trigger:
  - platform: time
    at: "{pattern['hour']:02d}:{pattern.get('minute', 0):02d}:00"
action:
  - service: [appropriate service for {pattern['device_id']}]
    target:
      entity_id: {pattern['device_id']}

Then explain in 1-2 sentences why this automation makes sense based on the pattern.
"""
        
        elif pattern['pattern_type'] == 'co_occurrence':
            return f"""
Create a Home Assistant automation for device co-occurrence:

PATTERN: {pattern['device1']} and {pattern['device2']} are used together {pattern['occurrences']} times
Confidence: {pattern['confidence']:.0%}

Create an automation where {pattern['device1']} triggers {pattern['device2']}.
"""
        
        # ... other pattern types
    
    def _parse_automation_yaml(self, llm_response: str, pattern: Dict) -> AutomationSuggestion:
        """Parse LLM response into structured format"""
        # Simple parsing - extract YAML block and description
        # Don't over-engineer, LLM usually formats correctly
        
        return AutomationSuggestion(
            alias=self._extract_alias(llm_response),
            description=self._extract_description(llm_response),
            automation_yaml=self._extract_yaml(llm_response),
            rationale=self._extract_rationale(llm_response),
            category=self._infer_category(pattern),
            priority='medium'  # Default, can be refined
        )
```

### Cost Tracking

```python
# src/llm/cost_tracker.py
class CostTracker:
    """Track OpenAI API costs"""
    
    # GPT-4o-mini pricing (as of Oct 2025)
    INPUT_COST_PER_1M = 0.15  # $0.15 per 1M tokens
    OUTPUT_COST_PER_1M = 0.60  # $0.60 per 1M tokens
    
    @staticmethod
    def calculate_cost(input_tokens: int, output_tokens: int) -> float:
        """Calculate cost in USD"""
        input_cost = (input_tokens / 1_000_000) * CostTracker.INPUT_COST_PER_1M
        output_cost = (output_tokens / 1_000_000) * CostTracker.OUTPUT_COST_PER_1M
        return input_cost + output_cost
```

---

## Integration Verification

**IV1: API key securely stored in environment variables**
- No hardcoded API keys in code
- Loaded from `.env` file
- Not logged or exposed in error messages

**IV2: Network egress doesn't affect other services**
- API calls are async (non-blocking)
- Timeout set to 30 seconds
- Retries don't cascade failures

**IV3: Cost tracking logs to shared logging system**
- Token usage logged per request
- Daily/weekly totals calculated
- Alert if approaching budget ($10/month)

**IV4: No sensitive HA data exposed in API calls**
- Only device IDs sent (e.g., "light.bedroom")
- No user names, locations, or personal data
- Patterns anonymized before sending

---

## Tasks Breakdown

1. **Create OpenAIClient class** (2 hours)
2. **Implement prompt templates** (2 hours)
3. **Add Pydantic models for structured output** (1.5 hours)
4. **Implement retry logic** (1 hour)
5. **Add cost tracking** (1 hour)
6. **Implement data sanitization** (1 hour)
7. **Unit tests with mocked API** (1.5 hours)
8. **Integration test with real OpenAI API** (0.5 hours)
9. **Quality validation** (1 hour)

**Total:** 8-10 hours

---

## Testing Strategy

### Unit Tests

```python
# tests/test_openai_client.py
import pytest
from src.llm.openai_client import OpenAIClient, AutomationSuggestion
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_generates_valid_suggestion():
    """Test successful suggestion generation"""
    
    pattern = {
        'device_id': 'light.bedroom',
        'pattern_type': 'time_of_day',
        'hour': 7,
        'minute': 0,
        'occurrences': 28,
        'confidence': 0.93
    }
    
    client = OpenAIClient(api_key="test-key")
    
    with patch.object(client.client.chat.completions, 'create') as mock_create:
        mock_create.return_value = AsyncMock(
            choices=[AsyncMock(message=AsyncMock(content="alias: Morning Lights\n..."))],
            usage=AsyncMock(total_tokens=450)
        )
        
        suggestion = await client.generate_automation_suggestion(pattern)
        
        assert isinstance(suggestion, AutomationSuggestion)
        assert 'Morning' in suggestion.alias
        assert client.total_tokens_used == 450

@pytest.mark.asyncio
async def test_retry_on_api_error():
    """Test retry logic on API failures"""
    client = OpenAIClient(api_key="test-key")
    
    with patch.object(client.client.chat.completions, 'create') as mock_create:
        # Fail twice, then succeed
        mock_create.side_effect = [
            Exception("Rate limit"),
            Exception("Timeout"),
            AsyncMock(choices=[...])  # Success
        ]
        
        suggestion = await client.generate_automation_suggestion({...})
        
        assert mock_create.call_count == 3
```

### Integration Tests

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_openai_api():
    """Test with real OpenAI API (requires API key)"""
    import os
    
    client = OpenAIClient(api_key=os.getenv('OPENAI_API_KEY'))
    
    pattern = {
        'device_id': 'light.test',
        'pattern_type': 'time_of_day',
        'hour': 7,
        'occurrences': 20,
        'confidence': 0.9
    }
    
    suggestion = await client.generate_automation_suggestion(pattern)
    
    assert 'alias' in suggestion.automation_yaml
    assert 'trigger' in suggestion.automation_yaml
    assert len(suggestion.rationale) > 10  # Has explanation
```

---

## Definition of Done

- [ ] OpenAIClient class implemented
- [ ] Prompt templates for all 3 pattern types
- [ ] Pydantic models for validation
- [ ] Retry logic with exponential backoff
- [ ] Cost tracking implemented
- [ ] Data sanitization verified
- [ ] Unit tests pass with mocked API
- [ ] Integration test with real API passes
- [ ] Automation YAML validated (80%+ valid)
- [ ] Cost per suggestion <$0.10
- [ ] Documentation complete
- [ ] Code reviewed and approved

---

## Reference Files

**Copy patterns from:**
- PRD Section 7.2 (simple prompt template)
- OpenAI API docs: https://platform.openai.com/docs/api-reference

---

## Notes

- Use GPT-4o-mini (not GPT-4o) for cost savings
- Keep prompts simple - don't over-engineer
- Structured output nice-to-have, not required for MVP
- Log all API calls for debugging
- Monitor costs daily (budget: $10/month)

---

**Story Status:** Not Started  
**Assigned To:** TBD  
**Created:** 2025-10-15  
**Updated:** 2025-10-15

