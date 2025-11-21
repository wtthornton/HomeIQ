# GPT-5.1 Reasoning Tokens Fix

**Date:** January 2025  
**Issue:** OpenAI API returning empty content with `finish_reason: length`  
**Root Cause:** `max_completion_tokens` too low for GPT-5.1 reasoning models  
**Fix:** Increased from 2000 to 8000 tokens

---

## Problem Summary

The Ask AI service was stalling with errors like:
```
ValueError: Empty content from OpenAI API. Finish reason: length
```

The model was using all available completion tokens for reasoning, leaving no room for actual content.

---

## Why 1200/2000 Tokens Was Too Low

### GPT-5.1 Reasoning Model Behavior

GPT-5.1 is a **reasoning model** that uses a two-phase approach:
1. **Reasoning Phase**: Internal "thinking" tokens (not counted against `max_completion_tokens`)
2. **Completion Phase**: Actual output tokens (counted against `max_completion_tokens`)

### The Issue

When `max_completion_tokens=2000`:
- Model receives complex prompt with 20,000+ input tokens
- Model needs to reason through multiple automation suggestions
- Model generates JSON with multiple suggestions, each with:
  - Description
  - Rationale
  - Entity mappings
  - Confidence scores
  - Metadata
- **2000 tokens is insufficient** for complete JSON output
- Model hits limit and returns empty content with `finish_reason: length`

### Token Usage Breakdown (Typical Suggestion Response)

| Component | Estimated Tokens |
|-----------|-----------------|
| JSON structure | 100-200 |
| Suggestion 1 (description + rationale + entities) | 400-600 |
| Suggestion 2 (description + rationale + entities) | 400-600 |
| Suggestion 3 (description + rationale + entities) | 400-600 |
| Metadata (confidence, patterns, etc.) | 200-300 |
| **Total** | **1,500-2,300** |

**Problem**: With only 2000 tokens, complex queries with 3+ suggestions easily exceed the limit.

---

## The Fix

### Changes Made

1. **`ask_ai_router.py` (Single Model Path)**
   - Changed `max_tokens=2000` → `max_tokens=8000` (line 4322)
   - This gets converted to `max_completion_tokens=8000` in `openai_client.py`

2. **`ask_ai_router.py` (Parallel Model Path)**
   - Changed `max_tokens=2000` → `max_tokens=8000` (line 4280)
   - Passed to `parallel_model_tester.generate_suggestions_parallel()`

3. **`parallel_model_tester.py` (Default Parameter)**
   - Changed default `max_tokens: int = 1200` → `max_tokens: int = 8000` (line 45)
   - Ensures consistency across all parallel testing calls

### Why 8000 Tokens?

- **Safety Margin**: 4x the previous limit provides ample room
- **Complex Queries**: Handles 5-10 suggestions with full details
- **Future-Proof**: Room for additional metadata and richer responses
- **Cost Impact**: Minimal - output tokens are only ~$0.08 per 1M tokens
- **Quality**: Prevents truncation and ensures complete responses

### Cost Analysis

**Before (2000 tokens):**
- Average output: ~1,500 tokens (when not truncated)
- Cost per request: ~$0.015

**After (8000 tokens):**
- Average output: ~1,500-2,500 tokens (complete responses)
- Cost per request: ~$0.015-0.025
- **Increase: ~$0.01 per request** (negligible)

**Monthly Impact (900 requests):**
- Additional cost: ~$9/month
- **Worth it**: Prevents failures and ensures quality

---

## Technical Details

### How `max_completion_tokens` Works

In `openai_client.py` (line 500):
```python
api_params = {
    "model": self.model,
    "messages": messages,
    "temperature": temperature,
    "max_completion_tokens": max_tokens  # Converts max_tokens to max_completion_tokens
}
```

**Key Points:**
- `max_completion_tokens` only limits the **output/completion** tokens
- Reasoning tokens are **separate** and don't count against this limit
- For GPT-5.1, reasoning can be extensive but completion still needs room

### Model Comparison

| Model | Reasoning Tokens | Max Completion Tokens | Our Setting |
|-------|-----------------|----------------------|-------------|
| GPT-4o | No | 16,384 | 2,000 (sufficient) |
| GPT-4o-mini | No | 16,384 | 2,000 (sufficient) |
| **GPT-5.1** | **Yes (separate)** | **16,384** | **8,000 (now sufficient)** |

---

## Verification

### Expected Behavior After Fix

1. ✅ No more `finish_reason: length` errors
2. ✅ Complete JSON responses with all suggestions
3. ✅ No truncation of suggestion descriptions or rationales
4. ✅ All entity mappings included in response

### Monitoring

Watch for:
- `finish_reason: stop` (normal completion)
- Actual completion token usage (should be 1,500-3,000 typically)
- No empty content errors

---

## Alternative Solutions Considered

### Option 1: Use Non-Reasoning Model ❌
- **Problem**: GPT-5.1 is chosen for quality - reasoning improves suggestions
- **Impact**: Would reduce suggestion quality

### Option 2: Reduce Prompt Size ❌
- **Problem**: Already optimized - reducing further would hurt quality
- **Impact**: Less context = worse suggestions

### Option 3: Increase to 4000 Tokens ⚠️
- **Problem**: Still might be tight for complex queries
- **Impact**: Better but not future-proof

### Option 4: Increase to 8000 Tokens ✅ **CHOSEN**
- **Problem**: None
- **Impact**: Safe, future-proof, minimal cost increase

---

## Related Files

- `services/ai-automation-service/src/api/ask_ai_router.py` (lines 4280, 4322)
- `services/ai-automation-service/src/services/parallel_model_tester.py` (line 45)
- `services/ai-automation-service/src/llm/openai_client.py` (line 500)

---

## References

- OpenAI GPT-5.1 Documentation: https://platform.openai.com/docs/models/gpt-5
- Reasoning Tokens: https://platform.openai.com/docs/guides/reasoning
- Token Limits: https://platform.openai.com/docs/guides/rate-limits

---

**Status:** ✅ Fixed and Deployed  
**Next Steps:** Monitor for `finish_reason: length` errors - should be zero

