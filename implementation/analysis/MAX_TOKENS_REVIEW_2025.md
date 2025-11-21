# Max Tokens Settings Review - 2025 Analysis

**Date:** January 2025  
**Purpose:** Review all max_tokens/max_completion_tokens settings to identify if they're too low  
**Status:** Analysis Complete

---

## Current Settings Analysis

### Critical Settings (High Priority)

#### 1. YAML Generation
**Location:** `ask_ai_router.py:2466, 2572`  
**Current:** `max_tokens=2000` / `max_completion_tokens=2000`  
**Config Default:** `yaml_max_tokens: int = 600` (config.py:123)

**Analysis:**
- Complex automations can be 500-1000 tokens
- Multi-trigger automations: 800-1500 tokens
- Complex conditions/sequences: 1000-2000 tokens
- **2000 tokens may be insufficient for very complex automations**

**Recommendation:** ⚠️ **Increase to 4000-6000 tokens**
- Provides safety margin for complex automations
- Cost impact: Minimal (~$0.02-0.04 per request)
- Prevents truncation of complex YAML

---

#### 2. Suggestion Generation
**Location:** `ask_ai_router.py:4280, 4322`  
**Current:** `max_tokens=8000` ✅ **RECENTLY FIXED**

**Status:** ✅ **Already increased from 2000 to 8000** - This is correct now

---

### Medium Priority Settings

#### 3. YAML Self-Correction - Full Restoration
**Location:** `yaml_self_correction.py:676`  
**Current:** `max_completion_tokens=1500`

**Analysis:**
- Full YAML restoration can be complex
- May need to restore entire automation
- 1500 tokens might be tight for complex automations

**Recommendation:** ⚠️ **Increase to 3000 tokens**

---

#### 4. Natural Language Generation
**Location:** `nl_automation_generator.py:594`  
**Current:** `max_completion_tokens=1500`  
**Config:** `nl_max_tokens: int = 1500` (config.py:112)

**Analysis:**
- NL descriptions can be lengthy
- Complex automations need detailed explanations
- 1500 tokens is reasonable but could be higher

**Recommendation:** ⚠️ **Consider 2000-2500 tokens** (optional)

---

#### 5. Clarification Question Generation
**Location:** `question_generator.py:80`  
**Current:** `max_completion_tokens=400`

**Analysis:**
- Questions are typically short (50-100 tokens each)
- JSON structure adds overhead
- Multiple questions in one response
- 400 tokens might be tight for 3-5 questions

**Recommendation:** ⚠️ **Increase to 800-1000 tokens**

---

### Low Priority Settings (Likely Appropriate)

#### 6. Entity Extraction
**Location:** `multi_model_extractor.py:215`  
**Current:** `max_completion_tokens=300`

**Analysis:**
- Entity extraction is typically short
- JSON with entity IDs and types
- 300 tokens is usually sufficient

**Recommendation:** ✅ **Keep at 300** (or increase to 500 for safety)

---

#### 7. Entity Validation
**Location:** `ensemble_entity_validator.py:244`  
**Current:** `max_completion_tokens=200`

**Analysis:**
- Validation responses are short (yes/no + entity ID)
- 200 tokens is sufficient

**Recommendation:** ✅ **Keep at 200**

---

#### 8. YAML Self-Correction - Syntax Detection
**Location:** `yaml_self_correction.py:488`  
**Current:** `max_completion_tokens=300`

**Analysis:**
- Error detection responses are short
- Just identifies errors, doesn't fix them
- 300 tokens is sufficient

**Recommendation:** ✅ **Keep at 300**

---

#### 9. YAML Self-Correction - Error Fixing
**Location:** `yaml_self_correction.py:585`  
**Current:** `max_completion_tokens=400`

**Analysis:**
- Error fixes are typically small patches
- 400 tokens might be tight for multiple fixes
- Could benefit from increase

**Recommendation:** ⚠️ **Increase to 800-1000 tokens**

---

#### 10. Command Extraction
**Location:** `ask_ai_router.py:2791`  
**Current:** `max_completion_tokens=60`

**Analysis:**
- Commands are very short (e.g., "turn_on", "set_brightness")
- 60 tokens is intentionally low for short output
- This is appropriate

**Recommendation:** ✅ **Keep at 60** (intentionally low)

---

#### 11. Ambiguity Analysis
**Location:** `ask_ai_router.py:7603`  
**Current:** `max_completion_tokens=400`

**Analysis:**
- Ambiguity detection is structured JSON
- Multiple ambiguities in one response
- 400 tokens might be tight

**Recommendation:** ⚠️ **Increase to 800 tokens**

---

#### 12. Component Restoration
**Location:** `ask_ai_router.py:8213`  
**Current:** `max_completion_tokens=500`

**Analysis:**
- Component restoration can be complex
- Nested components need full descriptions
- 500 tokens might be tight

**Recommendation:** ⚠️ **Increase to 1000-1500 tokens**

---

#### 13. Description Generation
**Location:** `description_generator.py:126`  
**Current:** `max_completion_tokens=200`  
**Config:** `description_max_tokens: int = 300` (config.py:122)

**Analysis:**
- Descriptions should be concise
- 200-300 tokens is appropriate for short descriptions
- Config says 300, code uses 200 - should align

**Recommendation:** ⚠️ **Use 300 to match config** (or update config to 200)

---

#### 14. Synergy Suggestions
**Location:** `synergy_suggestion_generator.py:136`  
**Current:** `max_completion_tokens=600`

**Analysis:**
- Synergy suggestions include YAML
- 600 tokens might be tight for full automation YAML
- Could benefit from increase

**Recommendation:** ⚠️ **Increase to 1500-2000 tokens**

---

## Summary of Recommendations

### High Priority (Should Fix)

| Setting | Current | Recommended | Reason |
|---------|---------|-------------|--------|
| YAML Generation | 2000 | **4000-6000** | Complex automations can exceed 2000 tokens |
| Clarification Questions | 400 | **800-1000** | Multiple questions + JSON overhead |
| YAML Self-Correction (Full) | 1500 | **3000** | Complex restoration needs more room |
| YAML Self-Correction (Fixing) | 400 | **800-1000** | Multiple fixes need more room |
| Ambiguity Analysis | 400 | **800** | Multiple ambiguities + JSON |
| Component Restoration | 500 | **1000-1500** | Nested components need space |
| Synergy Suggestions | 600 | **1500-2000** | Full automation YAML needs room |

### Medium Priority (Consider)

| Setting | Current | Recommended | Reason |
|---------|---------|-------------|--------|
| NL Generation | 1500 | **2000-2500** | Complex descriptions need space |
| Entity Extraction | 300 | **500** | Safety margin for complex extractions |

### Low Priority (Keep As-Is)

| Setting | Current | Status |
|---------|---------|--------|
| Entity Validation | 200 | ✅ Appropriate |
| YAML Syntax Detection | 300 | ✅ Appropriate |
| Command Extraction | 60 | ✅ Intentionally low |
| Description Generation | 200-300 | ✅ Appropriate (align with config) |

---

## Cost Impact Analysis

### GPT-5.1 Output Token Pricing
- **Cost:** $10.00 per 1M tokens
- **Per 1000 tokens:** $0.01

### Estimated Cost Increases

| Change | Tokens Added | Cost Per Request | Monthly (900 reqs) |
|--------|--------------|------------------|-------------------|
| YAML Gen: 2000→4000 | +2000 | +$0.02 | +$18 |
| YAML Gen: 2000→6000 | +4000 | +$0.04 | +$36 |
| Clarification: 400→800 | +400 | +$0.004 | +$3.60 |
| YAML Self-Corr: 1500→3000 | +1500 | +$0.015 | +$13.50 |
| YAML Fixing: 400→1000 | +600 | +$0.006 | +$5.40 |
| Ambiguity: 400→800 | +400 | +$0.004 | +$3.60 |
| Component Restore: 500→1500 | +1000 | +$0.01 | +$9 |
| Synergy: 600→2000 | +1400 | +$0.014 | +$12.60 |

**Total Monthly Cost Increase (if all changes):** ~$65-70/month

**Worth It?** ✅ **Yes** - Prevents truncation, improves quality, minimal cost impact

---

## Implementation Priority

### Phase 1: Critical (Do First)
1. ✅ YAML Generation: 2000 → **4000-6000**
2. ✅ Clarification Questions: 400 → **800-1000**
3. ✅ YAML Self-Correction (Full): 1500 → **3000**

### Phase 2: Important (Do Next)
4. ⚠️ YAML Self-Correction (Fixing): 400 → **800-1000**
5. ⚠️ Component Restoration: 500 → **1000-1500**
6. ⚠️ Ambiguity Analysis: 400 → **800**

### Phase 3: Optional (Consider)
7. ⚠️ Synergy Suggestions: 600 → **1500-2000**
8. ⚠️ NL Generation: 1500 → **2000-2500**
9. ⚠️ Entity Extraction: 300 → **500**

---

## Why Were They Set So Low?

### Historical Context
1. **Cost Optimization**: Lower tokens = lower costs
2. **GPT-4o-mini Era**: Older models had different limits
3. **Simple Automations**: Initial testing with basic automations
4. **Conservative Approach**: Set low to avoid waste

### Why They're Too Low Now
1. **GPT-5.1**: More capable, can generate longer outputs
2. **Complex Automations**: Real-world automations are more complex
3. **Rich Context**: More entity data = more detailed responses needed
4. **User Expectations**: Users want complete, detailed automations

---

## Recommendations Summary

**Primary Issue:** YAML generation at 2000 tokens is the biggest concern - complex automations can easily exceed this.

**Secondary Issues:** Several other endpoints are tight and could benefit from increases.

**Cost Impact:** Minimal (~$65-70/month for all changes) - well worth it for quality improvement.

**Action Items:**
1. Increase YAML generation to 4000-6000 tokens (highest priority)
2. Increase clarification questions to 800-1000 tokens
3. Review and increase other settings based on actual usage patterns

---

## Next Steps

1. Review actual token usage from logs
2. Identify which endpoints are hitting limits
3. Implement Phase 1 changes (critical)
4. Monitor for truncation issues
5. Adjust Phase 2/3 based on real-world usage

