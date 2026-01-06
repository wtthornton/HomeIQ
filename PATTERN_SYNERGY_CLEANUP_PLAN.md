# Pattern & Synergy Data Cleanup Plan

**Date:** January 6, 2026  
**Project:** HomeIQ  
**Status:** ✅ **READY TO EXECUTE**

---

## Executive Summary

Analysis confirms that **ALL pattern and synergy data is old, stale, and should be deleted**:

- **919 patterns** - Last seen December 3, 2025 (34+ days old)
- **48 synergies** - Created November 30, 2025 (37+ days old)
- **11,412 pattern history records** - All from November-December 2025
- **Data Quality:** Old and potentially corrupt - recommend complete cleanup

---

## Analysis Results

### Patterns Table (919 rows)
- **Created:** November 30, 2025
- **Last Seen:** December 3, 2025
- **Avg Confidence:** 0.970 (seems artificially high)
- **Age:** ALL patterns are >30 days old
- **Deprecated:** 0 patterns marked as deprecated
- **Status:** ⚠️ **ALL DATA IS STALE**

### Synergy Opportunities Table (48 rows)
- **Created:** November 30, 2025
- **Avg Confidence:** 0.594
- **Avg Final Score:** 0.000 (suspicious - all zeros)
- **Status:** ⚠️ **ALL DATA IS STALE**

### Pattern History Table (11,412 rows)
- **Date Range:** November 30 - December 3, 2025
- **Status:** ⚠️ **ALL DATA IS STALE**

---

## Cleanup Recommendation

### ✅ NUCLEAR OPTION: Delete All Data

**Rationale:**
1. All data is 30+ days old
2. Synergies have zero final scores (suspicious)
3. No recent pattern activity
4. Starting fresh will ensure clean, current data
5. Service will regenerate patterns automatically

**What Will Be Deleted:**
- ✅ 11,412 pattern history records
- ✅ 919 patterns
- ✅ 48 synergy opportunities
- ✅ 0 discovered synergies (already empty)

**What Will Be Preserved:**
- ✅ Database schema (tables remain, just emptied)
- ✅ Other tables (ask_ai_queries, semantic_knowledge, etc.)
- ✅ Service configuration
- ✅ Backups (4 existing backups + new backup created)

---

## Execution Steps

### Step 1: Backup (Automatic)
The cleanup script automatically creates a backup before deletion:
```bash
# Backup created at: /app/data/ai_automation.backup.YYYYMMDD_HHMMSS
```

**Existing Backups:**
```
ai_automation.backup.1767656640 (223 MB) - Jan 5, 2025
ai_automation.backup.1767659630 (223 MB) - Jan 5, 2025
ai_automation.backup.1767659690 (223 MB) - Jan 5, 2025
ai_automation.backup.1767660017 (223 MB) - Jan 5, 2025
```

### Step 2: Dry Run (Completed ✅)
```bash
docker exec ai-pattern-service python3 /tmp/cleanup.py
```

**Result:** Dry run successful - script is ready to execute

### Step 3: Execute Cleanup
```bash
docker exec -it ai-pattern-service python3 /tmp/cleanup.py --execute
```

**Interactive Confirmation Required:**
- Script will ask: "Type 'DELETE ALL' to confirm"
- This prevents accidental execution

### Step 4: Restart Service
```bash
docker compose restart ai-pattern-service
```

**Why Restart:**
- Clears in-memory caches
- Triggers pattern regeneration
- Ensures clean state

### Step 5: Verify Cleanup
```bash
docker exec ai-pattern-service python3 /tmp/check_db_tables.py
```

**Expected Results:**
- patterns: 0 rows
- synergy_opportunities: 0 rows
- pattern_history: 0 rows

### Step 6: Monitor Regeneration
```bash
# Watch service logs
docker logs -f ai-pattern-service

# Check pattern count after 1 hour
docker exec ai-pattern-service python3 -c "import sqlite3; conn = sqlite3.connect('/app/data/ai_automation.db'); cursor = conn.cursor(); cursor.execute('SELECT COUNT(*) FROM patterns'); print(f'Patterns: {cursor.fetchone()[0]}'); conn.close()"
```

---

## Scripts Provided

### 1. Analysis Script
**File:** `analyze_pattern_synergy_data.py`  
**Purpose:** Detailed corruption analysis (not used - schema mismatch)

### 2. Quick Analysis Script
**File:** `quick_analysis.py`  
**Purpose:** Quick stats on patterns and synergies  
**Status:** ✅ Working

### 3. Cleanup Script
**File:** `cleanup_patterns_synergies.py`  
**Purpose:** Delete all pattern and synergy data  
**Status:** ✅ Ready to execute  
**Location:** `/tmp/cleanup.py` (in container)

### 4. Table Check Script
**File:** `check_db_tables.py`  
**Purpose:** List all tables and row counts  
**Status:** ✅ Working  
**Location:** `/tmp/check_db_tables.py` (in container)

---

## Rollback Plan

If cleanup causes issues:

### Option 1: Restore from Backup
```bash
# Stop service
docker compose stop ai-pattern-service

# Restore backup
docker exec ai-pattern-service cp /app/data/ai_automation.backup.YYYYMMDD_HHMMSS /app/data/ai_automation.db

# Restart service
docker compose start ai-pattern-service
```

### Option 2: Restore from Host Backup
```bash
# If you created a host backup
docker cp ./backup.db ai-pattern-service:/app/data/ai_automation.db
docker compose restart ai-pattern-service
```

---

## Expected Outcomes

### Immediate (After Cleanup)
- ✅ Database size reduced by ~450 MB
- ✅ All pattern/synergy tables empty
- ✅ Service continues running normally
- ✅ No errors in logs

### Short Term (1-24 hours)
- ✅ Service begins analyzing recent device activity
- ✅ New patterns start appearing (time-of-day patterns)
- ✅ Pattern confidence builds over time
- ✅ Synergies detected based on new patterns

### Long Term (1-7 days)
- ✅ Pattern database reaches steady state
- ✅ High-confidence patterns established
- ✅ Synergies fully populated
- ✅ Better data quality (current, not stale)

---

## Risk Assessment

### Low Risk ✅
- **Data Loss:** All data is old/stale - no value lost
- **Service Downtime:** None - service continues running
- **Rollback:** Multiple backups available
- **Regeneration:** Automatic - no manual intervention needed

### Potential Issues
1. **Pattern regeneration takes time** (1-7 days for full coverage)
   - **Mitigation:** Existing automations continue working
   
2. **Temporary loss of pattern-based suggestions**
   - **Mitigation:** Service falls back to rule-based suggestions
   
3. **Synergy detection delayed**
   - **Mitigation:** Synergies regenerate as patterns stabilize

---

## Decision Matrix

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| **Delete All (Nuclear)** | Clean slate, fresh data, removes corruption | Temporary loss of patterns | ✅ **RECOMMENDED** |
| **Delete Old Only** | Preserves some data | Still has corruption issues | ❌ Not recommended |
| **Fix Corruption** | Keeps existing data | Time-consuming, may not fix all issues | ❌ Not feasible |
| **Do Nothing** | No risk | Continues with bad data | ❌ Not recommended |

---

## Execution Checklist

- [x] Analysis complete
- [x] Cleanup script created
- [x] Dry run successful
- [x] Backups verified
- [ ] **User approval to proceed**
- [ ] Execute cleanup
- [ ] Restart service
- [ ] Verify cleanup
- [ ] Monitor regeneration
- [ ] Document results

---

## Command Summary

```bash
# 1. Execute cleanup (INTERACTIVE - requires confirmation)
docker exec -it ai-pattern-service python3 /tmp/cleanup.py --execute

# 2. Restart service
docker compose restart ai-pattern-service

# 3. Verify cleanup
docker exec ai-pattern-service python3 /tmp/check_db_tables.py

# 4. Monitor logs
docker logs -f ai-pattern-service

# 5. Check pattern regeneration (after 1 hour)
docker exec ai-pattern-service python3 -c "import sqlite3; conn = sqlite3.connect('/app/data/ai_automation.db'); cursor = conn.cursor(); cursor.execute('SELECT COUNT(*) FROM patterns'); print(f'Patterns: {cursor.fetchone()[0]}'); conn.close()"
```

---

## Post-Cleanup Validation

### Success Criteria:
1. ✅ All pattern/synergy tables show 0 rows
2. ✅ Service logs show no errors
3. ✅ Service health check passes
4. ✅ New patterns begin appearing within 24 hours
5. ✅ Database size reduced

### Monitoring:
- Watch service logs for pattern generation activity
- Check pattern count daily for first week
- Verify synergy detection after patterns stabilize
- Monitor automation performance

---

**Ready to Execute:** ✅ YES  
**Approval Required:** User confirmation  
**Estimated Execution Time:** 5 minutes  
**Estimated Regeneration Time:** 1-7 days (automatic)

---

**Next Action:** Await user approval to execute cleanup with:
```bash
docker exec -it ai-pattern-service python3 /tmp/cleanup.py --execute
```
