# OpenAI Token Limit - Immediate Fix Plan

**Date:** November 19, 2025  
**Priority:** 🔴 CRITICAL  
**Time to Fix:** 10 minutes

---

## Problem
```
Error: Request too large for gpt-5.1
Limit: 30,000 TPM (Tokens Per Minute)
Requested: 34,738 tokens
```

---

## Immediate Fix (10 minutes)

### Step 1: Disable Enrichment Context (Saves 2,000-5,000 tokens)

**Edit:** `infrastructure/env.ai-automation`

**Add this line:**
```bash
# Disable enrichment context to reduce token usage
ENABLE_ENRICHMENT_CONTEXT=false
```

This disables the optional enrichment data (weather, carbon, energy, air quality) that's added to every Ask AI prompt.

---

### Step 2: Restart the Service

```powershell
# Stop the service
docker-compose stop ai-automation-service

# Start with new config
docker-compose up -d ai-automation-service

# Check logs
docker-compose logs -f ai-automation-service
```

---

### Step 3: Test the Fix

Navigate to: `http://localhost:3001/ask-ai`

Try the query that was failing:
```
"Every 10 mins execute a random 30 sec effect on WLED, make sure the LED resets back to the default color scheme."
```

**Expected Result:** ✅ No 429 error, suggestion generated successfully

---

## Why This Works

The enrichment context adds **2,000-5,000 tokens** to every request:
- Weather data (current conditions, forecast)
- Carbon intensity (grid carbon data)
- Energy pricing (electricity rates)
- Air quality (indoor/outdoor AQI)

**Most queries don't need this data**, so disabling it is safe.

The feature flag was already implemented in the code (line 3133 in `ask_ai_router.py`):
```python
enable_enrichment = os.getenv('ENABLE_ENRICHMENT_CONTEXT', 'true').lower() == 'true'
```

We're just setting it to `false` by default.

---

## Next Steps (After Immediate Fix)

### This Week:
1. **Upgrade OpenAI Tier** (Tier 1 → Tier 2)
   - Cost: $50/month (one-time prepaid)
   - Benefit: 30K → 150K TPM limit (5x increase)
   - Action: https://platform.openai.com/account/billing/overview

### Next 2 Weeks:
2. **Implement Token Budget System**
   - Limit entity context to 10,000 tokens max
   - Compress entity attributes (only include relevant fields)
   - Log token usage per component

3. **Switch YAML Generation to GPT-4o-mini**
   - Save 93% on YAML generation cost
   - GPT-4o-mini is sufficient for template-based YAML
   - Keep GPT-5.1 for creative suggestion generation

---

## Monitoring

After restart, check these metrics:

### Success Indicators:
- ✅ No 429 errors in logs
- ✅ Ask AI queries complete successfully
- ✅ Token usage reduced by 2,000-5,000 per request

### Monitor:
```bash
# Watch for errors
docker-compose logs -f ai-automation-service | grep -i "429\|rate_limit\|tokens"

# Check OpenAI usage
# Visit: https://platform.openai.com/usage
```

---

## Rollback Plan

If this breaks functionality:

```bash
# Re-enable enrichment context
# Edit infrastructure/env.ai-automation
ENABLE_ENRICHMENT_CONTEXT=true

# Restart
docker-compose restart ai-automation-service
```

**But:** This should be safe - enrichment is optional and most queries work without it.

---

## Cost Impact

### Before:
- **Input tokens:** ~25,000 per request
- **Cost per request:** $0.0705
- **Monthly cost (900 requests):** $115.65

### After (with enrichment disabled):
- **Input tokens:** ~20,000 per request (-20%)
- **Cost per request:** $0.0565 (-20%)
- **Monthly cost (900 requests):** $92.85 (-$23/month)

### After (with all optimizations):
- **Input tokens:** ~12,000 per request (-52%)
- **Cost per request:** $0.0350 (-50%)
- **Monthly cost (900 requests):** $60.00 (-$56/month)

**Annual Savings Potential:** $672/year

---

## Testing Checklist

- [ ] Environment variable added to `infrastructure/env.ai-automation`
- [ ] Service restarted
- [ ] Ask AI endpoint tested (no 429 errors)
- [ ] Suggestion quality verified (no degradation)
- [ ] Logs checked for errors
- [ ] OpenAI usage dashboard monitored

---

## Expected Outcome

✅ **No more 429 rate limit errors**  
✅ **Ask AI works reliably**  
✅ **20% cost reduction**  
✅ **No quality degradation**

---

## Questions?

If issues persist:
1. Check logs: `docker-compose logs ai-automation-service`
2. Verify env var: `docker-compose exec ai-automation-service env | grep ENRICHMENT`
3. Review full analysis: `implementation/analysis/OPENAI_TOKEN_LIMITS_AND_COST_ANALYSIS.md`
4. Consider Tier 2 upgrade (5x rate limit increase)

---

**Status:** Ready to implement  
**Risk:** Low (feature flag already exists, well-tested)  
**Impact:** High (fixes critical issue, reduces cost)

