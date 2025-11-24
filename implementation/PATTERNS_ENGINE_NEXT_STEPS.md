# Patterns Engine Improvements - Next Steps

**Date:** January 22, 2025  
**Status:** Implementation Complete, Migration Pending

## ✅ Completed

1. **Pattern Occurrence Accumulation Fix** - Time-windowed tracking implemented
2. **Detector Health Monitoring** - System implemented and integrated
3. **Pattern Lifecycle Management** - System implemented and integrated
4. **Database Migration Created** - `20250122_add_pattern_lifecycle_fields.py`

## 🔄 Next Steps Required

### Step 1: Apply Database Migration

The migration file has been created but needs to be applied. Since the Docker container is running, you have two options:

#### Option A: Restart Service (Recommended)
```powershell
# Restart the service to pick up the new migration file
docker-compose restart ai-automation-service

# Wait for service to start
Start-Sleep -Seconds 10

# Run migration
docker exec ai-automation-service alembic upgrade head
```

#### Option B: Rebuild Container
```powershell
# Rebuild to include new migration file
docker-compose build ai-automation-service

# Restart service
docker-compose up -d ai-automation-service

# Wait for service to start
Start-Sleep -Seconds 10

# Run migration
docker exec ai-automation-service alembic upgrade head
```

#### Option C: Manual SQL (If migration fails)
If the migration doesn't work, you can manually apply the SQL:

```powershell
docker exec ai-automation-service sqlite3 /app/data/ai_automation.db "
ALTER TABLE patterns ADD COLUMN deprecated BOOLEAN NOT NULL DEFAULT 0;
ALTER TABLE patterns ADD COLUMN deprecated_at DATETIME;
ALTER TABLE patterns ADD COLUMN needs_review BOOLEAN NOT NULL DEFAULT 0;
CREATE INDEX IF NOT EXISTS idx_patterns_deprecated ON patterns(deprecated);
CREATE INDEX IF NOT EXISTS idx_patterns_needs_review ON patterns(needs_review);
"
```

### Step 2: Verify Migration

After running the migration, verify the fields were added:

```powershell
# Check if fields exist
docker exec ai-automation-service sqlite3 /app/data/ai_automation.db "
PRAGMA table_info(patterns);
" | Select-String -Pattern "deprecated|needs_review"

# Should show:
# deprecated|BOOLEAN|1|0|0
# deprecated_at|DATETIME|0|0|0
# needs_review|BOOLEAN|1|0|0
```

### Step 3: Verify Current Migration Status

```powershell
# Check current migration
docker exec ai-automation-service alembic current

# Should show: 20250122_pattern_lifecycle (head)
```

### Step 4: Test the Improvements

Once migration is complete, the improvements will be active:

1. **Time-Windowed Occurrences:**
   - Next pattern detection run will use time-windowed tracking
   - Check logs for "windowed occurrences" messages

2. **Detector Health Monitoring:**
   - Health monitoring runs automatically during daily analysis
   - Check logs for "Detector Health Report"
   - Access via API: `GET /api/patterns/detector-health`

3. **Pattern Lifecycle Management:**
   - Runs automatically during daily analysis
   - Check logs for "Pattern lifecycle management complete"
   - Access via API: `GET /api/patterns/lifecycle-stats`
   - Manually trigger: `POST /api/patterns/lifecycle-manage`

### Step 5: Monitor First Daily Analysis Run

The next scheduled daily analysis (default: 3 AM) will:
- Use time-windowed occurrence tracking
- Track detector health for all detectors
- Run pattern lifecycle management
- Log health reports and lifecycle results

To trigger manually (if you don't want to wait):
```powershell
# Via API (requires admin auth)
curl -X POST http://localhost:8024/api/analysis/run \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

## 📊 Expected Results

After migration and first analysis run:

1. **Pattern Occurrences:**
   - Should show windowed counts (not accumulated)
   - Patterns will reflect last 30 days of activity

2. **Detector Health:**
   - Health report for all 10 detectors
   - Success rates, pattern yields, processing times
   - Identification of unhealthy detectors

3. **Pattern Lifecycle:**
   - Stale patterns (60+ days) automatically deprecated
   - Very old patterns (90+ days deprecated) automatically deleted
   - Active patterns validated for recent activity

## 🔍 Verification Commands

```powershell
# Check migration status
docker exec ai-automation-service alembic current

# Check database schema
docker exec ai-automation-service sqlite3 /app/data/ai_automation.db ".schema patterns"

# Check for lifecycle fields
docker exec ai-automation-service sqlite3 /app/data/ai_automation.db "
SELECT COUNT(*) FROM patterns WHERE deprecated = 1;
SELECT COUNT(*) FROM patterns WHERE needs_review = 1;
"

# View service logs
docker logs ai-automation-service --tail 100 | Select-String -Pattern "health|lifecycle|windowed"
```

## ⚠️ Notes

- Migration file is in: `services/ai-automation-service/alembic/versions/20250122_add_pattern_lifecycle_fields.py`
- If container doesn't have the file, restart/rebuild is needed
- All improvements are backward compatible
- Existing patterns will get lifecycle fields with default values (deprecated=false, needs_review=false)

---

**Ready to proceed with migration application.**

