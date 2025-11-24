# Synergies Fix - Next Steps Execution Summary

**Date:** January 2025  
**Status:** ✅ Frontend & API Fixes Applied | ⚠️ Database Setup Required

---

## ✅ Fixes Applied

### 1. Frontend Display Fix
**File:** `services/ai-automation-ui/src/pages/Synergies.tsx`
- ✅ Fixed "Total Opportunities" to show `stats.total_synergies` instead of `synergies.length`
- ✅ Shows filtered count when filters are active, total when no filters

### 2. API Default Alignment
**File:** `services/ai-automation-service/src/api/synergy_router.py`
- ✅ Changed default `min_confidence` from `0.7` to `0.0` to match frontend

---

## ⚠️ Issues Found

### Issue 1: Database Table Missing
**Status:** `synergy_opportunities` table does not exist

**Root Cause:** Database migrations have not been run

**Solution:**
```bash
cd services/ai-automation-service

# Run migrations
alembic upgrade head

# Verify migration
alembic current
```

**Expected Result:**
- Creates `synergy_opportunities` table
- Creates all required columns (synergy_id, synergy_type, impact_score, etc.)
- Creates indexes for performance

---

### Issue 2: Service Not Running
**Status:** API endpoint not accessible at `http://localhost:8005`

**Possible Causes:**
1. Service not started
2. Different port number
3. Service running in Docker with different host/port

**Solution:**

**Option A: Check Docker Services**
```bash
# List running containers
docker ps

# Check ai-automation-service
docker ps | findstr ai-automation

# View logs
docker logs ai-automation-service

# Restart if needed
docker restart ai-automation-service
```

**Option B: Check Service Port**
```bash
# Check docker-compose.yml for port mapping
# Default might be 8005, 8018, or 8024

# Test different ports
curl http://localhost:8005/api/synergies/stats
curl http://localhost:8018/api/synergies/stats
curl http://localhost:8024/api/synergies/stats
```

**Option C: Run Locally**
```bash
cd services/ai-automation-service

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start service
python -m uvicorn src.main:app --host 0.0.0.0 --port 8005 --reload
```

---

## 📋 Step-by-Step Execution Plan

### Step 1: Run Database Migrations

```bash
cd services/ai-automation-service

# Check current migration status
alembic current

# Run migrations
alembic upgrade head

# Verify
alembic current  # Should show latest migration
```

**If using Docker:**
```bash
# Run migration inside container
docker exec -it ai-automation-service alembic upgrade head

# Or if service not running, start it first
docker compose up -d ai-automation-service
docker exec -it ai-automation-service alembic upgrade head
```

---

### Step 2: Verify Database

```bash
# Run verification script
python scripts/verify_synergies_fix.py
```

**Expected Output:**
- ✅ Database found
- ✅ synergy_opportunities table exists
- ✅ Total Synergies: 0 (initially, before detection)

---

### Step 3: Start/Restart Service

**If using Docker:**
```bash
# Start service
docker compose up -d ai-automation-service

# Check status
docker ps | findstr ai-automation

# View logs
docker compose logs -f ai-automation-service
```

**If running locally:**
```bash
cd services/ai-automation-service
python -m uvicorn src.main:app --host 0.0.0.0 --port 8005 --reload
```

---

### Step 4: Populate Synergies

Synergies need to be detected before they appear. Two options:

#### Option A: Wait for Daily Analysis (Automatic)
- Daily analysis scheduler runs automatically (default: 3 AM)
- Check logs to see if it ran:
  ```bash
  docker logs ai-automation-service | findstr "synergy"
  ```

#### Option B: Trigger Detection Manually (Immediate)

**Via API (requires admin auth):**
```bash
# Get admin API key from environment or config
ADMIN_KEY="your-admin-api-key"

# Trigger detection
curl -X POST "http://localhost:8005/api/synergies/detect?use_patterns=true" \
     -H "X-HomeIQ-API-Key: ${ADMIN_KEY}"
```

**Via Python Script:**
```python
import asyncio
import aiohttp

async def trigger_detection():
    async with aiohttp.ClientSession() as session:
        headers = {"X-HomeIQ-API-Key": "your-admin-key"}
        async with session.post(
            "http://localhost:8005/api/synergies/detect?use_patterns=true",
            headers=headers
        ) as response:
            result = await response.json()
            print(f"Detected: {result.get('data', {}).get('count', 0)} synergies")

asyncio.run(trigger_detection())
```

---

### Step 5: Verify Fix

1. **Check Database:**
   ```bash
   python scripts/verify_synergies_fix.py
   ```

2. **Check API:**
   ```bash
   curl http://localhost:8005/api/synergies/stats
   ```

3. **Check Frontend:**
   - Navigate to `http://localhost:3001/synergies`
   - Refresh page
   - Verify "Total Opportunities" shows correct count (not 0 if synergies exist)

---

## 🔍 Troubleshooting

### Problem: "synergy_opportunities table does not exist"

**Solution:**
1. Run migrations: `alembic upgrade head`
2. Verify: `alembic current`
3. Check database: `sqlite3 data/ai_automation.db ".tables"`

### Problem: "API connection error"

**Solution:**
1. Check service is running: `docker ps` or check process
2. Check port: Verify port in docker-compose.yml or service config
3. Check logs: `docker logs ai-automation-service` for errors
4. Restart service: `docker restart ai-automation-service`

### Problem: "Total Opportunities still shows 0"

**Possible Causes:**
1. No synergies detected yet → Run detection (Step 4)
2. API returning wrong data → Check API response: `curl http://localhost:8005/api/synergies/stats`
3. Frontend cache → Hard refresh browser (Ctrl+Shift+R)
4. Service not restarted → Restart after code changes

### Problem: "Database locked"

**Solution:**
1. Stop all services using the database
2. Run migration
3. Restart services

---

## 📊 Verification Checklist

- [ ] Database migrations run successfully
- [ ] `synergy_opportunities` table exists
- [ ] Service is running and accessible
- [ ] API endpoint `/api/synergies/stats` returns data
- [ ] Synergies detected (count > 0) or detection triggered
- [ ] Frontend displays correct total count
- [ ] Filters work correctly (type, validation, confidence)

---

## 📝 Notes

- **Frontend fix is complete** - Will show correct count once database has synergies
- **API fix is complete** - Default confidence now matches frontend (0.0)
- **Database setup required** - Run migrations before first use
- **Detection required** - Synergies must be detected before they appear

---

## 🚀 Quick Start (All Steps)

```bash
# 1. Navigate to service directory
cd services/ai-automation-service

# 2. Run migrations
alembic upgrade head

# 3. Start service (Docker)
docker compose up -d ai-automation-service

# OR start locally
python -m uvicorn src.main:app --host 0.0.0.0 --port 8005 --reload

# 4. Verify
python ../../scripts/verify_synergies_fix.py

# 5. Trigger detection (if needed)
# Use API endpoint or wait for daily analysis
```

---

## Related Files

- `implementation/analysis/SYNERGIES_ZERO_ANALYSIS.md` - Full analysis
- `scripts/verify_synergies_fix.py` - Verification script
- `services/ai-automation-ui/src/pages/Synergies.tsx` - Frontend fix
- `services/ai-automation-service/src/api/synergy_router.py` - API fix

