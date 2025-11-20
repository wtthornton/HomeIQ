# Token Optimization Testing Guide

**Date:** November 20, 2025  
**Status:** ✅ Deployment Complete - Ready for Testing

---

## ✅ Deployment Status

**Service:** ai-automation-service  
**Port:** 8024  
**Status:** Restarted with new code

---

## 🧪 Testing Steps

### Test 1: Original Failing Query (CRITICAL TEST)

**This is the query that was failing before - let's verify it works now!**

1. **Navigate to:** http://localhost:3001/ask-ai

2. **Submit Query:**
   ```
   Every 15 mins I want the led in the office to randly pich an action or pattern. the led is WLED and has many patterns of lights to choose from. Turn the brightness to 100% during the 15 mins and then make sure it returns back to its current stat (color, pattern, brightness,...).
   ```

3. **Answer Clarification Questions:**
   - When prompted, select "office" as location
   - Select the WLED device when asked

4. **Click "Submit Answers"**

5. **Expected Results:**
   - ✅ No timeout error (no 504 Gateway Timeout)
   - ✅ Suggestions appear successfully
   - ✅ Response completes in < 60 seconds
   - ✅ No "Empty content from OpenAI API" error

---

### Test 2: Verify Token Usage Improvement

**Check logs for token usage:**

```powershell
# Watch logs in real-time
docker compose logs -f ai-automation-service
```

**Look for these log messages:**

✅ **Success Indicators:**
- `📊 Relevance-scored: X/Y entities selected (top 25 by relevance)`
- `✅ Compressed entity context: X entities (max 7000 tokens)`
- `Token usage at X.X% of budget` (should be < 70%, not 86.5%)
- `✅ Compressed entity context: X/Y entities, ~XXXX tokens (limit: 7000)`

**Expected Token Usage:**
- **Before:** ~25,557 tokens (86.5% of budget)
- **After:** ~14,557-18,557 tokens (48-62% of budget)
- **Savings:** 7,000-11,000 tokens (28-43% reduction)

---

### Test 3: Verify Entity Filtering

**Check that relevance scoring is working:**

```powershell
docker compose logs ai-automation-service --tail 200 | findstr /i "📊 Relevance-scored Top 5 scored entities"
```

**Expected Log Output:**
- `📊 Relevance-scored: 15-25/33-45 entities selected`
- `📊 Top 5 scored entities: [('light.office_wled', 0.8), ...]`
- Entities from clarification answers should have high scores (> 0.5)

---

### Test 4: Verify Compression Improvements

**Check compression logs:**

```powershell
docker compose logs ai-automation-service --tail 200 | findstr /i "compressed Compressed entity context effect_list"
```

**Expected:**
- `✅ Compressed entity context: X entities, ~XXXX tokens (limit: 7000)`
- Entity count should be 15-25 (down from 33-45)
- Token count should be ~3,500-5,500 (down from ~9,158)

---

## 📊 Success Metrics

### ✅ **Deployment Success:**
- [ ] Service starts without errors
- [ ] Health check passes: http://localhost:8024/health
- [ ] No syntax errors in logs

### ✅ **Token Optimization Success:**
- [ ] Token usage reduced from 25,557 to ~14,557-18,557
- [ ] Entity count reduced from 33-45 to 15-25
- [ ] Response completes without timeout
- [ ] No `finish_reason: "length"` errors

### ✅ **Quality Success:**
- [ ] Suggestions still accurate
- [ ] Relevant entities preserved (office, WLED)
- [ ] Suggestions use correct entities from clarification answers

---

## 🔍 Monitoring Commands

**Watch logs in real-time:**
```powershell
docker compose logs -f ai-automation-service
```

**Filter for token/relevance messages:**
```powershell
docker compose logs ai-automation-service --tail 500 | findstr /i "token Token 📊 Relevance compressed Compressed"
```

**Check for errors:**
```powershell
docker compose logs ai-automation-service --tail 200 | findstr /i "error Error ERROR ❌ timeout Timeout"
```

**Check service health:**
```powershell
docker ps | findstr ai-automation-service
```

---

## 🎯 What to Test

1. **Original Query Test** (Most Important)
   - Submit the exact query that was failing
   - Answer clarification questions
   - Verify it completes successfully

2. **Token Usage Verification**
   - Check logs show reduced token usage
   - Verify entity count is reduced
   - Confirm response completes

3. **Quality Verification**
   - Suggestions should still be accurate
   - Correct entities should be used
   - No loss of important information

---

## 🐛 If Issues Occur

**If you see timeouts or token limit errors:**

1. **Check logs:**
   ```powershell
   docker compose logs ai-automation-service --tail 200
   ```

2. **Verify config:**
   - `max_entity_context_tokens` should be 7_000 (not 10_000)

3. **Check relevance scoring:**
   - Look for `📊 Relevance-scored` messages
   - Verify top entities are being selected

4. **Rollback if needed:**
   ```powershell
   git checkout HEAD -- services/ai-automation-service/src/config.py
   docker compose build ai-automation-service
   docker compose up -d --force-recreate ai-automation-service
   ```

---

## ✅ Ready to Test

The service has been deployed with the optimization changes. Please:

1. **Test the original failing query** (Test 1)
2. **Monitor the logs** during the test (Test 2)
3. **Verify token usage** has improved (Test 2)
4. **Report the results**

**Expected Outcome:** The query should now complete successfully without timeout, with reduced token usage and maintained response quality!

---

**Deployment Status:** ✅ COMPLETE  
**Testing Status:** Ready to begin  
**Next Step:** Test the original failing query
