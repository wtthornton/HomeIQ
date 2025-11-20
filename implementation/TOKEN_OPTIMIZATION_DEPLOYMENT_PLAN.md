# Token Optimization Deployment & Testing Plan

**Date:** November 20, 2025  
**Status:** Ready for Deployment  
**Changes:** Option 1 (Aggressive Compression) + Option 3 (Relevance Filtering)

---

## 📋 Pre-Deployment Checklist

✅ **Code Changes Complete:**
- Config updated: `max_entity_context_tokens = 7_000`
- Compression enhanced: relevance scoring, effect_list summarization, device_intelligence removal
- Relevance scoring function added and integrated
- All files modified and verified

✅ **Linter Status:** No errors

✅ **Architecture Compliance:** Epic 31 patterns followed

---

## 🚀 Deployment Steps

### Option A: Quick Restart (If Service Already Running)

```powershell
# Restart just the AI automation service
docker compose restart ai-automation-service

# Or rebuild and restart
docker compose build ai-automation-service
docker compose up -d --force-recreate ai-automation-service
```

### Option B: Full Deployment (Recommended)

```powershell
# Rebuild the service
docker compose build ai-automation-service

# Restart the service
docker compose up -d --force-recreate ai-automation-service

# Check logs
docker compose logs -f ai-automation-service
```

---

## 🧪 Testing Plan

### Test 1: Original Failing Query (Critical)

**Query:** "Every 15 mins I want the led in the office to randly pich an action or pattern. the led is WLED and has many patterns of lights to choose from. Turn the brightness to 100% during the 15 mins and then make sure it returns back to its current stat (color, pattern, brightness,...)."

**Steps:**
1. Navigate to http://localhost:3001/ask-ai
2. Submit the query
3. Answer clarification questions
4. Click "Submit Answers"
5. **Expected:** Response completes without timeout (no 504 error)
6. **Expected:** Suggestions generated successfully

**Verification:**
- ✅ No timeout error
- ✅ Suggestions appear
- ✅ Response completes in < 60 seconds

---

### Test 2: Token Usage Verification

**Check Logs:**
```powershell
docker compose logs ai-automation-service --tail 100 | Select-String -Pattern "token|Token|📊|Relevance"
```

**Expected Log Messages:**
- `📊 Relevance-scored: X/Y entities selected (top 25 by relevance)`
- `✅ Compressed entity context: X entities (max 7000 tokens)`
- `⚠️ Token usage at X.X% of budget` (should be lower, < 70%)

**Metrics to Verify:**
- Token count should be ~14,557-18,557 (down from 25,557)
- Entity count should be ~15-25 (down from 33-45)
- Response should complete successfully

---

### Test 3: Entity Filtering Verification

**Query:** "Turn on the office lights"

**Expected:**
- Relevance scoring should prioritize office entities
- Location filtering should keep only office entities
- Token count should be lower than before

**Check Logs For:**
- `📊 Top 5 scored entities:` - Should show office entities with high scores
- `📍 Location-filtered: X/Y entities` - Should filter to office only
- `✅ Compressed entity context: X entities` - Should be ~10-20 entities

---

### Test 4: Clarification Flow Test

**Query:** "Turn on lights when motion detected"

**Steps:**
1. Submit query (should trigger clarification)
2. Answer questions
3. Submit answers
4. **Expected:** Response completes successfully

**Verify:**
- Relevance scores should prioritize entities from clarification answers
- Token count should be within budget
- Suggestions should use entities from clarification answers

---

## 📊 Success Criteria

### ✅ **Deployment Success:**
- Service restarts without errors
- Health check passes: http://localhost:8024/health
- No exceptions in logs

### ✅ **Token Optimization Success:**
- Token usage reduced from ~25,557 to ~14,557-18,557 (28-43% reduction)
- Response completes without timeout (no `finish_reason: "length"`)
- Entity count reduced from 33-45 to 15-25

### ✅ **Quality Success:**
- Suggestions still accurate (relevant entities preserved)
- Response quality maintained (most relevant entities included)
- No loss of critical information

---

## 🔍 Monitoring After Deployment

**Watch for These Log Messages:**

✅ **Good Signs:**
- `📊 Relevance-scored: X/Y entities selected`
- `✅ Compressed entity context: X entities`
- `Token usage at X.X% of budget` (should be < 70%)

⚠️ **Warning Signs:**
- `Token usage at > 80% of budget` (still too high)
- `finish_reason: "length"` (still hitting token limit)
- `Empty content from OpenAI API` (token limit exceeded)

**If Issues Occur:**
1. Check logs: `docker compose logs ai-automation-service --tail 200`
2. Verify config: `max_entity_context_tokens = 7_000`
3. Check if relevance scoring is working: Look for `📊 Top 5 scored entities:`
4. Verify compression is working: Look for `✅ Compressed entity context`

---

## 🔄 Rollback Plan (If Needed)

If issues occur, rollback is simple:

**Option 1: Config Rollback**
```python
# In services/ai-automation-service/src/config.py
max_entity_context_tokens: int = 10_000  # Revert to original
```

**Option 2: Code Rollback**
```bash
git checkout HEAD -- services/ai-automation-service/src/
docker compose build ai-automation-service
docker compose up -d --force-recreate ai-automation-service
```

---

## 📝 Expected Results

### Before (Current State):
- Token usage: 25,557 tokens (86.5% of budget)
- Entities: 33-45 entities
- Result: Timeout, `finish_reason: "length"`

### After (Expected):
- Token usage: ~14,557-18,557 tokens (48-62% of budget)
- Entities: 15-25 most relevant entities
- Result: ✅ Full response generated successfully

**Token Savings:** 7,000-11,000 tokens (28-43% reduction)  
**Available for Response:** 11,443-15,443 tokens (38-51% buffer)

---

## ✅ Ready to Deploy?

**Recommended:** Yes, deploy and test

**Risk Level:** Low
- ✅ Changes are enhancements (not breaking changes)
- ✅ Existing filtering logic still works
- ✅ Compression already existed (just enhanced)
- ✅ Easy rollback if needed

**Confidence:** High
- ✅ Code reviewed
- ✅ Linter passes
- ✅ Architecture compliant
- ✅ Leverages existing infrastructure

---

**Next Steps:**
1. Deploy using Option A or B above
2. Run Test 1 (original failing query)
3. Monitor logs for token usage
4. Verify response completes successfully
5. Report results

---

**Implementation Status:** ✅ COMPLETE  
**Deployment Status:** Ready  
**Testing Status:** Pending
