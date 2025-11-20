# Deploy and Test Token Optimization - Quick Commands

**Date:** November 20, 2025  
**Purpose:** Quick reference for deploying and testing token optimization changes

---

## 🚀 Deployment Commands

### Step 1: Rebuild Service
```powershell
docker compose build ai-automation-service
```

### Step 2: Restart Service
```powershell
docker compose up -d --force-recreate ai-automation-service
```

### Step 3: Check Status
```powershell
docker ps | findstr ai-automation-service
```

### Step 4: Monitor Logs
```powershell
docker compose logs -f ai-automation-service
```

---

## 🧪 Testing Commands

### Test 1: Original Failing Query
1. Navigate to: http://localhost:3001/ask-ai
2. Submit: "Every 15 mins I want the led in the office to randly pich an action or pattern. the led is WLED and has many patterns of lights to choose from. Turn the brightness to 100% during the 15 mins and then make sure it returns back to its current stat (color, pattern, brightness,...)."
3. Answer clarification questions
4. Click "Submit Answers"
5. **Expected:** ✅ Response completes without timeout

### Test 2: Check Token Usage in Logs
```powershell
docker compose logs ai-automation-service --tail 200 | findstr /i "token Token 📊 Relevance compressed"
```

### Test 3: Check Health
```powershell
Invoke-WebRequest -Uri http://localhost:8024/health -UseBasicParsing | Select-Object -ExpandProperty Content
```

---

## 📊 Success Indicators

✅ **Good Signs:**
- `📊 Relevance-scored: X/Y entities selected`
- `✅ Compressed entity context: X entities`
- `Token usage at X.X% of budget` (should be < 70%)
- Response completes successfully

⚠️ **Warning Signs:**
- `Token usage at > 80% of budget`
- `finish_reason: "length"`
- `Empty content from OpenAI API`
- 504 Gateway Timeout errors

---

## 🔄 Quick Rollback (If Needed)

```powershell
git checkout HEAD -- services/ai-automation-service/src/config.py
docker compose build ai-automation-service
docker compose up -d --force-recreate ai-automation-service
```
