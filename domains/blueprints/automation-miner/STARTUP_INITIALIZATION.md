# Startup Corpus Initialization

**Epic AI-4, Story AI4.4**  
**Feature:** Automatic corpus population on service startup

---

## 🚀 How Startup Initialization Works

### Automatic Checks on Startup

When automation-miner service starts, it checks:

**Condition 1: Empty Corpus**
```
if total_automations == 0:
    → Run initial crawl (populate corpus)
```

**Condition 2: Stale Corpus**
```
if last_crawl_timestamp > 7 days ago:
    → Run refresh (update corpus)
```

**Condition 3: Fresh Corpus**
```
if last_crawl_timestamp < 7 days ago:
    → Skip initialization (corpus is fresh)
```

### Behavior

**First Deployment:**
```
[Startup] Corpus is empty - will run initial population
[Startup] Starting corpus initialization (empty corpus)...
[Startup] Corpus initialization started in background
[Startup] ✅ Weekly refresh scheduler started
[Background] Fetching posts... (2-3 hours)
[Background] ✅ Initial crawl complete: 2,543 automations
```

**After Downtime (>7 days):**
```
[Startup] Corpus is stale (10 days) - will refresh on startup
[Startup] Starting corpus initialization (stale corpus)...
[Startup] Fetching posts since 2025-10-09...
[Background] ✅ Refresh complete: Added 35, Updated 20, Pruned 5
```

**Normal Restart (<7 days):**
```
[Startup] ✅ Corpus is fresh (2,543 automations, last crawl: 2025-10-17)
[Startup] Skipping initialization
[Startup] ✅ Weekly refresh scheduler started
```

---

## ⚙️ Configuration

### Enable/Disable Startup Init

**File:** `infrastructure/env.automation-miner`
```bash
ENABLE_AUTOMATION_MINER=true            # Master switch
ENABLE_STARTUP_INITIALIZATION=true      # Run on startup (default: true)
```

**Disable if:**
- You want manual control over crawling
- Testing with static corpus
- Bandwidth constraints on startup

### Initial Crawl Settings

**File:** `src/config.py`
```python
# For startup initialization, uses same settings as weekly refresh:
DISCOURSE_MIN_LIKES=300        # Quality threshold (lower than manual crawl)
CRAWLER_MAX_POSTS=3000         # Maximum to fetch
CRAWLER_BATCH_SIZE=50          # Batch size
```

---

## 🔄 Startup Flow

```
Docker Container Starts
        ↓
FastAPI Lifespan (Startup)
        ↓
Create Database Tables
        ↓
Check Corpus Status
   ├─ Empty? → Initialize in background ✅
   ├─ Stale (>7 days)? → Refresh in background ✅
   └─ Fresh? → Skip initialization ✅
        ↓
Start Weekly Scheduler (Sunday 2 AM)
        ↓
API Ready to Accept Requests
        ↓
[Background] Initialization runs if needed
```

**Key:** API starts immediately, initialization runs async in background

---

## 📊 Expected Startup Times

### Empty Corpus (First Deploy)
```
t=0s    - Container starts
t=2s    - Database initialized
t=3s    - Startup check: corpus empty
t=4s    - Background initialization started
t=5s    - API ready (200 OK)
t=10s   - Health check: healthy (corpus populating)
t=30min - Background: First batch complete (50 automations)
t=2hr   - Background: Full crawl complete (2,000+ automations)
```

**API is available immediately** (doesn't block startup)

### Fresh Corpus (Normal Restart)
```
t=0s  - Container starts
t=2s  - Database initialized
t=3s  - Startup check: corpus fresh (2,543 automations)
t=4s  - Skip initialization
t=5s  - API ready (200 OK)
```

**Instant startup** (no crawling needed)

### Stale Corpus (After Downtime)
```
t=0s   - Container starts
t=2s   - Database initialized
t=3s   - Startup check: corpus stale (10 days old)
t=4s   - Background refresh started
t=5s   - API ready (200 OK)
t=15min - Background: Incremental refresh complete (+35 automations)
```

**API available immediately, refresh in background**

---

## 🎯 Benefits of Startup Initialization

### For Users
✅ **Always Fresh Data** - No waiting for Sunday 2 AM  
✅ **Immediate Value** - First deploy populates automatically  
✅ **Recovery** - Handles downtime gracefully  
✅ **Zero Config** - Works out of the box  

### For Operations
✅ **Self-Healing** - Recovers from missed weekly runs  
✅ **Non-Blocking** - API starts immediately  
✅ **Resilient** - Handles empty/stale corpus automatically  
✅ **Observable** - Logs startup decisions clearly  

---

## 🧪 Testing Scenarios

### Test 1: First Deploy (Empty Corpus)

```bash
# Remove database to simulate first deploy
docker exec automation-miner rm /app/data/automation_miner.db

# Restart service
docker-compose restart automation-miner

# Check logs - should see:
# "Corpus is empty - will run initial population on startup"
# "Corpus initialization started in background"

# API should be immediately available
curl http://localhost:8019/health
# Status: healthy (corpus populating in background)
```

### Test 2: After 10 Days Downtime

```bash
# Simulate stale corpus (manually set last_crawl to 10 days ago)
docker exec automation-miner python -c "
from src.miner.database import get_database
from src.miner.repository import CorpusRepository
from datetime import datetime, timedelta
import asyncio

async def set_stale():
    db = get_database()
    async with db.get_session() as session:
        repo = CorpusRepository(session)
        old_date = datetime.utcnow() - timedelta(days=10)
        await repo.set_last_crawl_timestamp(old_date)
        print('Set last_crawl to 10 days ago')

asyncio.run(set_stale())
"

# Restart
docker-compose restart automation-miner

# Should see:
# "Corpus is stale (10 days) - will refresh on startup"
```

### Test 3: Normal Restart (Fresh Corpus)

```bash
# With recent last_crawl timestamp
docker-compose restart automation-miner

# Should see:
# "Corpus is fresh (2,543 automations, last crawl: 2025-10-18)"
# "Skipping initialization"
```

---

## ⚡ Quick Deploy Commands

```bash
# 1. Build and start with startup initialization
cd C:\cursor\homeiq
docker-compose build automation-miner
docker-compose up -d automation-miner

# 2. Watch initialization logs
docker logs -f automation-miner

# Expected logs:
# "Corpus is empty - will run initial population on startup"
# "Corpus initialization started in background"
# "✅ Weekly refresh scheduler started"
# [Background] "Fetching blueprints..."
# [Background] "✅ Initial crawl complete: 2,543 automations"

# 3. Verify API immediately available (while background crawl runs)
curl http://localhost:8019/health
# Status: healthy (even while initializing)
```

---

## 📋 Startup Initialization Checklist

- [x] Corpus status check on startup
- [x] Empty corpus detection
- [x] Stale corpus detection (>7 days)
- [x] Background initialization (async)
- [x] API available immediately (non-blocking)
- [x] Weekly scheduler still runs
- [x] Configuration option (ENABLE_STARTUP_INITIALIZATION)
- [x] Logging and observability

---

**Status:** ✅ **Startup initialization configured!**

**On every service start:**
1. Checks corpus status
2. Runs initialization if needed (background)
3. API ready immediately
4. Weekly scheduler active

**Zero manual intervention required!**

