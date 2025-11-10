# Phase 1 ML/AI Improvements - Deployment Guide

**Date:** January 2025  
**Status:** Ready for Deployment

---

## Deployment Summary

Deploying Phase 1 ML/AI improvements:
- ✅ Incremental learning support
- ✅ Confidence calibration
- ✅ High utility pattern mining

**Services to Deploy:**
- `ai-automation-service` (backend with ML improvements)

**Impact:** No breaking changes, backward compatible

---

## Pre-Deployment Checklist

- [x] Code complete and reviewed
- [x] No linting errors
- [x] Syntax validated
- [x] Documentation complete
- [ ] Docker image built
- [ ] Service deployed
- [ ] Health checks passed
- [ ] Functionality verified

---

## Deployment Steps

### Step 1: Build Docker Image

```powershell
# Navigate to project root
cd C:\cursor\ha-ingestor

# Build ai-automation-service with new improvements
docker-compose build ai-automation-service
```

**Expected Time:** 2-3 minutes

---

### Step 2: Verify Build

```powershell
# Check image was built successfully
docker images | Select-String "ai-automation-service"
```

---

### Step 3: Deploy Service

```powershell
# Stop current service
docker-compose stop ai-automation-service

# Remove old container
docker-compose rm -f ai-automation-service

# Start with new image
docker-compose up -d ai-automation-service
```

---

### Step 4: Verify Health

```powershell
# Check service status
docker-compose ps ai-automation-service

# Check health endpoint
Invoke-RestMethod -Uri "http://localhost:8018/health" -Method Get

# Check logs for initialization
docker-compose logs ai-automation-service | Select-String "incremental\|calibrator\|utility"
```

**Expected:** Service shows "Up (healthy)" and logs show Phase 1 features initialized

---

### Step 5: Verify Functionality

#### Test Incremental Update Endpoint

```powershell
# Test incremental update API
Invoke-RestMethod -Uri "http://localhost:8018/api/patterns/incremental-update?hours=1" -Method Post
```

**Expected Response:**
```json
{
  "success": true,
  "message": "Incremental update complete...",
  "data": {
    "patterns_updated": 0,
    "events_processed": ...,
    "performance": {
      "duration_seconds": ...
    }
  }
}
```

#### Test Pattern List with Utility Scores

```powershell
# Check patterns include utility scores
Invoke-RestMethod -Uri "http://localhost:8018/api/patterns/list?limit=5" -Method Get
```

**Expected:** Patterns include `utility_score` and `metadata.utility` fields

---

### Step 6: Monitor Logs

```powershell
# Watch service logs
docker-compose logs -f ai-automation-service
```

**Look for:**
- ✅ "MLPatternDetector initialized: incremental=True"
- ✅ "Confidence calibrator and utility scorer initialized"
- ✅ No errors during startup

---

## Verification Checklist

### Immediate Verification

- [ ] Service starts successfully
- [ ] Health endpoint returns healthy
- [ ] Incremental update endpoint accessible
- [ ] No errors in logs

### Functional Verification

- [ ] Patterns include utility scores
- [ ] Confidence calibration model loads (if exists)
- [ ] Incremental update endpoint responds
- [ ] Daily analysis scheduler starts correctly

### Performance Verification

- [ ] Next daily analysis uses incremental updates (if enabled)
- [ ] Check logs for "incremental update stats"
- [ ] Verify faster processing times

---

## Rollback Plan

If issues occur:

```powershell
# Stop service
docker-compose stop ai-automation-service

# Restore previous image (if tagged)
docker-compose pull ai-automation-service:previous

# Or rebuild previous version from git
git checkout <previous-commit>
docker-compose build ai-automation-service
docker-compose up -d ai-automation-service
```

---

## Post-Deployment

### Next Daily Analysis

The next scheduled analysis (3 AM) will:
- Use incremental updates (if enabled)
- Include utility scores in all patterns
- Use calibrated confidence (if model trained)
- Log incremental statistics

### Monitor Performance

Watch for:
- Faster analysis times (15s vs 180s for incremental)
- Incremental update statistics in logs
- Pattern utility scores in database

---

## Troubleshooting

### Service Won't Start

```powershell
# Check logs for errors
docker-compose logs ai-automation-service

# Common issues:
# - Missing dependencies: Check requirements.txt
# - Port conflicts: Check port 8018 is available
# - Database connection: Verify InfluxDB is running
```

### Incremental Updates Not Working

- Verify `enable_incremental=True` in scheduler
- Check `_last_pattern_update_time` is being tracked
- First run is always full analysis (expected)

### Calibrator Not Loading

- Check `pattern_calibrator.pkl` file exists (if previously trained)
- Model is optional - service works without it
- Will train when feedback is collected

---

## Success Criteria

✅ **Deployment Successful When:**
1. Service starts and passes health checks
2. No errors in startup logs
3. API endpoints respond correctly
4. Patterns include utility scores
5. Incremental update endpoint works

---

## Notes

- **Backward Compatible:** All changes are additive, no breaking changes
- **Optional Features:** Calibration and incremental updates are opt-in
- **Performance:** First run after restart is full analysis (expected)
- **State:** Incremental state is in-memory (lost on restart)

---

**Ready to Deploy?** Run Step 1 to begin!









