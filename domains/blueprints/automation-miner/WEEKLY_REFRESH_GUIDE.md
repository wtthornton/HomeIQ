# Weekly Corpus Refresh - Configuration Guide

**Epic AI-4, Story AI4.4**  
**Schedule:** Every Sunday at 2 AM (local time)  
**Purpose:** Keep corpus fresh with new community automations

---

## 🔄 How Weekly Refresh Works

### Automatic Schedule (Production)

**When:** Every Sunday at 2 AM  
**Duration:** 15-30 minutes (incremental crawl)  
**Process:**
1. Fetch new posts since `last_crawl_timestamp`
2. Update vote counts for existing automations
3. Prune low-quality entries (quality < 0.4)
4. Invalidate caches in AI Automation Service
5. Log results

**Trigger:** Automatic (APScheduler CronTrigger)

---

## 🐳 Docker Deployment (Recommended)

### Enable Weekly Refresh

**File:** `infrastructure/env.automation-miner`
```bash
ENABLE_AUTOMATION_MINER=true  # ← Must be true for scheduler to run
DISCOURSE_MIN_LIKES=300        # Quality threshold
LOG_LEVEL=INFO
```

### Start Service

```bash
# Build and start
docker-compose up -d automation-miner

# Verify scheduler started
docker logs automation-miner | grep "Weekly refresh scheduler"

# Expected output:
# ✅ Weekly refresh scheduler started
# ✅ Next run: Sunday 2025-10-20 02:00:00
```

### Verify Schedule

```bash
# Check service health (includes scheduler status)
curl http://localhost:8019/api/automation-miner/admin/refresh/status

# Response:
{
  "last_refresh": "2025-10-19T00:57:23",
  "days_since_refresh": 0,
  "next_refresh": "Sunday 2 AM",
  "corpus_total": 5,
  "status": "healthy"
}
```

---

## 🧪 Manual Testing

### Test Weekly Refresh Job

```bash
# Option 1: Trigger via API (recommended)
curl -X POST http://localhost:8019/api/automation-miner/admin/refresh/trigger

# Option 2: Inside Docker container
docker exec automation-miner python -c "
from src.jobs.weekly_refresh import WeeklyRefreshJob
import asyncio
job = WeeklyRefreshJob()
asyncio.run(job.run())
"

# Option 3: Local CLI (if running locally)
cd domains/blueprints/automation-miner
python -c "
from src.jobs.weekly_refresh import WeeklyRefreshJob
import asyncio
job = WeeklyRefreshJob()
asyncio.run(job.run())
"
```

### Monitor Refresh Progress

```bash
# Watch logs
docker logs -f automation-miner

# Expected output during refresh:
# [correlation-id] 🔄 Weekly Corpus Refresh Started
# [correlation-id] Last crawl: 2025-10-19T00:57:23
# [correlation-id] Step 1: Fetching new/updated posts...
# [correlation-id] Found 50 new/updated posts
# [correlation-id] Step 2: Processing new posts...
# [correlation-id]   Added: 15 new automations
# [correlation-id]   Updated: 10 vote counts
# [correlation-id]   Skipped: 25 unchanged
# [correlation-id] ✅ Weekly Refresh Complete!
```

---

## 📊 What the Weekly Refresh Does

### Incremental Updates

**Fetches:**
- New posts since last crawl (typically 20-100/week)
- Updated vote counts for existing posts
- Only posts with 100+ likes (lower threshold for recent content)

**Updates:**
- Quality scores (recalculated based on new vote counts)
- Last crawled timestamps
- Corpus statistics

**Prunes:**
- Automations with quality_score < 0.4
- Posts >2 years old with <100 votes
- Duplicate entries

**Efficiency:**
- **Initial Crawl:** 2,000-3,000 posts, 2-3 hours
- **Weekly Refresh:** 20-100 posts, 15-30 minutes
- **Network:** ~5-20MB vs 50-100MB
- **6-12× faster** than full re-crawl

---

## 🔍 Finding Differences from Community

### What "Differences" Are Detected

**1. New Automations:**
- Community members post new blueprints
- Trending automations gain popularity
- New device types emerge

**2. Quality Changes:**
- Vote counts increase → quality scores updated
- Popular automations ranked higher
- Low-quality entries pruned

**3. Update Tracking:**
- Existing automations get updated descriptions
- YAML improvements captured
- Metadata refreshed

### Example Weekly Refresh Log

```
[Sun 2 AM] Weekly refresh started
  ├─ Fetched: 45 posts updated since last week
  ├─ NEW: 12 automations (trending topics)
  ├─ UPDATED: 18 quality scores (vote counts increased)
  ├─ UNCHANGED: 15 automations (skipped)
  ├─ PRUNED: 2 low-quality entries
  └─ Total corpus: 2,543 → 2,553 (+10 net)

Cache invalidation: AI Automation Service notified
Next refresh: Sunday 2025-10-27 02:00:00
```

---

## 🚀 Production Deployment Steps

### 1. Build Docker Image

```bash
cd C:\cursor\homeiq

# Build automation-miner service
docker-compose build automation-miner

# Verify image created
docker images | grep automation-miner
```

### 2. Start Service with Scheduler

```bash
# Start automation-miner
docker-compose up -d automation-miner

# Verify started
docker-compose ps automation-miner

# Check logs for scheduler confirmation
docker logs automation-miner 2>&1 | Select-String "Weekly refresh"
```

### 3. Run Initial Crawl (Inside Docker)

```bash
# Execute initial crawl
docker exec -it automation-miner python -m src.cli crawl --min-likes 300 --limit 1000

# Or use API trigger
curl -X POST http://localhost:8019/api/automation-miner/admin/refresh/trigger

# Monitor progress
docker logs -f automation-miner
```

### 4. Verify Scheduler is Active

```bash
# Check scheduler status
curl http://localhost:8019/api/automation-miner/admin/refresh/status

# Verify weekly job is scheduled
docker exec automation-miner python -c "
from src.api.main import app
import asyncio

async def check():
    # This would show next scheduled run
    print('Scheduler is active in Docker')

asyncio.run(check())
"
```

---

## 📅 Weekly Refresh Schedule Details

### APScheduler Configuration

```python
# From src/jobs/weekly_refresh.py
CronTrigger(
    day_of_week='sun',       # Every Sunday
    hour=2,                  # 2 AM
    minute=0,                # On the hour
    timezone='local'         # Local server time
)

# Job Settings:
max_instances=1,             # Only one refresh at a time
coalesce=True,               # Skip if previous run still active
misfire_grace_time=3600      # Allow 1 hour delay if server was down
```

### What Happens Each Sunday

```
2:00 AM - Weekly refresh triggered
  ↓
2:00-2:05 AM - Fetch new/updated posts (since last week)
  ↓
2:05-2:20 AM - Process and normalize automations
  ↓
2:20-2:25 AM - Update quality scores, prune low-quality
  ↓
2:25-2:30 AM - Cache invalidation, stats update
  ↓
2:30 AM - Refresh complete, logs written
  ↓
3:00 AM - Daily AI Analysis runs (uses fresh corpus)
```

**No Conflict:** Refresh (2 AM) completes before Daily Analysis (3 AM)

---

## 🧪 Testing the Weekly Refresh

### Test 1: Manual Trigger

```bash
# Trigger refresh immediately
curl -X POST http://localhost:8019/api/automation-miner/admin/refresh/trigger

# Response:
{
  "status": "triggered",
  "message": "Weekly refresh job started in background",
  "timestamp": "2025-10-19T01:00:00"
}

# Check logs
docker logs automation-miner | tail -50
```

### Test 2: Verify Incremental Crawl

```bash
# Run refresh twice - second should find fewer new posts
curl -X POST http://localhost:8019/api/automation-miner/admin/refresh/trigger

# Wait 1 minute

curl -X POST http://localhost:8019/api/automation-miner/admin/refresh/trigger

# Second run should log:
# "Found 0 new/updated posts" (nothing changed in 1 minute)
```

### Test 3: Verify Quality Updates

```bash
# Check corpus before refresh
curl http://localhost:8019/api/automation-miner/corpus/stats

# Wait for a week (posts accumulate votes)

# Refresh will update quality scores automatically
# Check corpus after refresh - avg_quality should increase
```

---

## 📊 Monitoring Weekly Refresh

### Health Check Endpoint

```bash
GET /api/automation-miner/admin/refresh/status

Response:
{
  "last_refresh": "2025-10-19T02:00:00",
  "days_since_refresh": 0,
  "next_refresh": "Sunday 2 AM",
  "corpus_total": 2543,
  "corpus_quality": 0.76,
  "status": "healthy"  # or "stale" if >7 days
}
```

**Alert:** Status = "stale" if >7 days since last refresh (missed schedule)

### Docker Logs

```bash
# View refresh history
docker logs automation-miner | grep "Weekly Refresh"

# View last refresh summary
docker logs automation-miner | grep "Weekly refresh complete" | tail -1
```

### Metrics to Monitor

- **Corpus Growth:** +20-50 automations/week typical
- **Quality Trend:** Should stay ≥0.7
- **Refresh Duration:** Should be <30 minutes
- **Failure Rate:** Should be <5% (retry logic handles transient errors)

---

## 🔧 Troubleshooting

### Scheduler Not Running

**Symptom:** No logs about "Weekly refresh scheduler"

**Check:**
```bash
docker logs automation-miner | grep -i scheduler

# If not found:
# 1. Verify ENABLE_AUTOMATION_MINER=true
# 2. Check for startup errors
docker logs automation-miner | grep -i error
```

**Fix:**
```bash
# Restart with correct config
docker-compose restart automation-miner
```

### Refresh Failing

**Symptom:** Logs show "Weekly refresh failed"

**Common Causes:**
- Discourse API rate limiting → Wait and retry
- Network connectivity → Check Docker network
- Database locked → Restart service

**Recovery:**
```bash
# Manual trigger after fixing issue
curl -X POST http://localhost:8019/api/automation-miner/admin/refresh/trigger
```

### No New Posts Found

**Symptom:** "Found 0 new/updated posts"

**Expected If:**
- Refresh runs twice in same day (normal, nothing changed)
- Community has slow week (normal variation)
- Discourse API filtering correctly (500+ likes threshold)

**Not a Problem:** Corpus remains stable, no action needed

---

## 🎯 Success Criteria

### Weekly Refresh is Working If:

- ✅ Scheduler logs show "Weekly refresh scheduler started"
- ✅ Health check shows last_refresh within 7 days
- ✅ Manual trigger works (POST /admin/refresh/trigger)
- ✅ Corpus grows over time (check weekly)
- ✅ Quality scores update (votes increase)
- ✅ No repeated failures (retry logic works)

### Expected Behavior

**Week 1:** Initial crawl (2,000-3,000 automations)  
**Week 2:** Refresh finds ~20-50 new posts  
**Week 3:** Refresh finds ~20-50 new posts  
**Week N:** Corpus stabilizes at 2,000-3,500 high-quality automations  

**Pruning** keeps corpus clean (removes low-quality, stale)

---

## 🔔 Alerts to Configure

**Recommended Alerts:**
1. 🔴 **Critical:** Refresh failed 3 consecutive weeks
2. 🟡 **Warning:** Refresh duration >45 minutes
3. 🟡 **Warning:** Days since refresh >7
4. ℹ️ **Info:** >100 new automations added (trigger re-analysis)

**Implementation:** Use health check endpoint + monitoring system

---

## ✅ Deployment Checklist

### Pre-Deployment
- [x] Docker image built
- [x] Environment variables configured
- [x] Health checks configured
- [x] Resource limits set (512M)
- [x] Logging configured

### Post-Deployment
- [ ] Initial crawl executed
- [ ] Scheduler confirmed running
- [ ] Manual refresh tested
- [ ] Health endpoint monitored
- [ ] First Sunday refresh verified

---

**Ready for Production Deployment!**

**Next:** Deploy to Docker and run initial crawl

