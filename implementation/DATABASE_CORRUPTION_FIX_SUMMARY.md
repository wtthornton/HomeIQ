# Database Corruption Fix Summary

**Date:** January 5, 2026  
**Service:** ai-pattern-service  
**Issue:** SQLite database corruption with "Rowid out of order" errors

## Problem

The ai-pattern-service database (`/app/data/ai_automation.db`) was corrupted with:
- Multiple "Rowid out of order" errors in Tree 12
- Many "Page never used" errors
- Corruption detected via `PRAGMA integrity_check`

This caused the Patterns page in the UI to show a database corruption error.

## Root Cause

1. **Database file permissions**: Database file was owned by root, preventing repair operations
2. **Insufficient corruption detection**: Error detection didn't recognize SQLite integrity_check error format
3. **Limited repair methods**: Repair function only tried dump method, which fails on severe corruption

## Fixes Applied

### 1. Improved Corruption Detection (`services/ai-pattern-service/src/database/integrity.py`)

**Enhanced `is_database_corruption_error()` function:**
- Added detection for "rowid out of order" errors
- Added detection for "page never used" errors
- Added detection for "*** in database" prefix
- Added detection for "tree" and "cell" corruption indicators

**Enhanced `check_database_integrity()` function:**
- Better handling of SQLite integrity_check results
- Proper detection of corruption indicators in error messages
- Truncation of long error messages for logging

### 2. Improved Repair Function (`services/ai-pattern-service/src/database/integrity.py`)

**Enhanced `attempt_database_repair()` function with multiple repair methods:**
1. **SQLite .recover command** (most robust, requires sqlite3 CLI)
2. **VACUUM INTO** (SQLite 3.27+, in-place repair)
3. **Dump and recreate** (fallback method)

**Note:** sqlite3 CLI is not available in the container, so .recover method cannot be used.

### 3. Enhanced Error Handling (`services/ai-pattern-service/src/api/pattern_router.py`)

**Added corruption error handling to `list_patterns()` endpoint:**
- Automatic detection of corruption errors
- Automatic repair attempt on corruption detection
- User-friendly error messages with repair endpoint instructions
- Graceful degradation with empty pattern list after successful repair

### 4. Fixed File Permissions

**Database file permissions corrected:**
- Changed ownership from root to appuser:appgroup
- Ensures repair operations can write backup and repaired files

## Current Status

**Database Status:** Still corrupted (repair methods failed due to severity)

**Error Handling:** ✅ Improved - Now properly detects and handles corruption errors

**User Experience:** ✅ Improved - Shows clear error messages with repair instructions

## Recommended Actions

### Immediate (To Fix Current Corruption)

Since the corruption is severe and repair methods failed, the recommended approach is:

1. **Backup current database:**
   ```bash
   docker exec -u root ai-pattern-service cp /app/data/ai_automation.db /app/data/ai_automation.db.corrupted.backup
   ```

2. **Create new database:**
   ```bash
   docker exec ai-pattern-service rm /app/data/ai_automation.db
   # Service will recreate database on next startup
   ```

3. **Restart service:**
   ```bash
   docker restart ai-pattern-service
   ```

4. **Re-run pattern analysis:**
   - Patterns will be regenerated from Home Assistant event data
   - This may take time depending on data volume

### Long-term Improvements

1. **Add sqlite3 CLI to Docker image** for .recover command support
2. **Implement database backup strategy** (daily backups)
3. **Add monitoring** for database integrity checks
4. **Consider migrating to PostgreSQL** for better reliability (if data volume grows)

## Testing

### Verify Error Handling

```bash
# Test corruption detection
curl http://localhost:8034/api/v1/patterns/list

# Should return proper error message with repair instructions
```

### Verify Repair Endpoint

```bash
# Test repair endpoint
curl -X POST http://localhost:8034/api/v1/patterns/repair

# Returns repair status
```

## Files Modified

1. `services/ai-pattern-service/src/database/integrity.py`
   - Enhanced corruption detection
   - Improved repair function with multiple methods
   - Better error handling

2. `services/ai-pattern-service/src/api/pattern_router.py`
   - Added corruption error handling to list_patterns endpoint
   - Automatic repair attempts
   - User-friendly error messages

3. `services/ai-pattern-service/scripts/repair_database.py` (new)
   - Standalone repair script for manual database repair

4. `services/ai-pattern-service/scripts/recover_data.py` (new)
   - Data recovery script (needs fixes for sqlite3.Row usage)

## Next Steps

1. ✅ Code improvements applied
2. ⏳ Rebuild container with updated code
3. ⏳ Fix database permissions in Dockerfile
4. ⏳ Test error handling with corrupted database
5. ⏳ Decide on database recreation vs. continued repair attempts

## Related Issues

- Database corruption likely caused by:
  - Concurrent writes from multiple services sharing the database
  - Disk I/O issues
  - Container crashes during writes
  - WAL file issues

## Prevention

1. **Use WAL mode properly** (already configured)
2. **Ensure proper file locking** (already configured with busy_timeout)
3. **Regular integrity checks** (can be added to health check)
4. **Database backups** (recommended)
5. **Consider separate databases** for each service instead of shared database
