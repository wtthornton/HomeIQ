# AI Automation Service - SQLite Schema Fix Plan

**Issue:** `sqlite3.OperationalError: no such column: suggestions.automation_json`

**Date:** January 2025  
**Service:** `ai-automation-service-new` (Port 8025)  
**Frontend:** `ai-automation-ui` (Port 3001)

## Problem Analysis

### Root Cause

The database schema is **out of sync** with the SQLAlchemy model definition:

1. **Model Definition** (`services/ai-automation-service-new/src/database/models.py`):
   - Defines `automation_json` column (line 23)
   - Defines `automation_yaml` column (line 24)
   - Defines `ha_version` column (line 25)
   - Defines `json_schema_version` column (line 26)

2. **Alembic Migration** (`services/ai-automation-service-new/alembic/versions/001_add_automation_json.py`):
   - Migration exists to add these columns
   - **But migration has NOT been run** on the database

3. **Current Database State**:
   - `suggestions` table exists (from previous schema)
   - Missing columns: `automation_json`, `automation_yaml`, `ha_version`, `json_schema_version`

4. **Current Code Behavior**:
   - `init_db()` function (line 82-132) manually adds some columns, but **NOT** the JSON-related ones
   - SQLAlchemy ORM queries fail because model expects columns that don't exist

### Error Location

**Error occurs when:**
- Frontend (`localhost:3001`) calls `/api/suggestions/list` endpoint
- Service uses SQLAlchemy `select(Suggestion)` which tries to SELECT all columns
- Database table doesn't have `automation_json` column

**Error SQL Query:**
```sql
SELECT suggestions.id, suggestions.pattern_id, suggestions.title, 
       suggestions.description, suggestions.automation_json,  -- ❌ Column doesn't exist
       suggestions.automation_yaml, ... 
FROM suggestions 
ORDER BY suggestions.created_at DESC 
LIMIT ? OFFSET ?
```

## Solution Options

### Option 1: Run Alembic Migration (RECOMMENDED)

**Pros:**
- ✅ Uses proper migration system
- ✅ Tracks migration history
- ✅ Can rollback if needed
- ✅ Standard practice

**Cons:**
- Requires manual execution (one-time)
- Need to ensure Alembic is configured correctly

**Steps:**
1. Verify Alembic configuration (`alembic.ini`, `alembic/env.py`)
2. Run migration: `alembic upgrade head`
3. Verify columns added: Check database schema
4. Test endpoint: Verify error is resolved

### Option 2: Add to `init_db()` Manual Schema Sync (QUICK FIX)

**Pros:**
- ✅ Fixes issue immediately
- ✅ No manual migration step needed
- ✅ Works on startup automatically

**Cons:**
- Not using migration system
- Code duplication (migration + manual sync)
- Harder to track schema changes

**Steps:**
1. Update `init_db()` to add missing columns
2. Test service startup
3. Verify columns added
4. Test endpoint

### Option 3: Hybrid Approach (BEST PRACTICE)

**Pros:**
- ✅ Uses migrations for tracked changes
- ✅ Has fallback for schema sync
- ✅ Handles both scenarios

**Cons:**
- More complex implementation

**Steps:**
1. Update `init_db()` to check for missing columns
2. Run Alembic migration on startup if needed
3. Fallback to manual column addition if migration fails

## Recommended Solution: Option 1 (Run Migration) + Option 2 (Update init_db for future)

### Implementation Plan

#### Phase 1: Immediate Fix (Run Migration)

1. **Verify Alembic Setup**
   ```bash
   cd services/ai-automation-service-new
   alembic current  # Check current migration state
   alembic history  # View migration history
   ```

2. **Run Migration**
   ```bash
   alembic upgrade head
   ```

3. **Verify Schema**
   ```sql
   PRAGMA table_info(suggestions);
   -- Should show: automation_json, automation_yaml, ha_version, json_schema_version
   ```

4. **Test Service**
   ```bash
   # Restart service
   docker compose restart ai-automation-service-new
   
   # Test endpoint
   curl http://localhost:8025/api/suggestions/list?limit=10
   ```

#### Phase 2: Update init_db() for Future Safety

Update `services/ai-automation-service-new/src/database/__init__.py`:

1. Add missing columns to `required_columns` dict in `init_db()`
2. Include: `automation_json`, `automation_yaml`, `ha_version`, `json_schema_version`
3. Handle JSON type correctly for SQLite (SQLite stores JSON as TEXT)

#### Phase 3: Add Migration Run on Startup (Optional Enhancement)

For future robustness, consider:
1. Running Alembic migrations automatically on startup
2. Adding migration check in `init_db()`
3. Warning if migrations are pending

## Detailed Implementation Steps

### Step 1: Run Alembic Migration

```bash
# Navigate to service directory
cd services/ai-automation-service-new

# Check current migration state
alembic current

# Run migration (if not already run)
alembic upgrade head

# Verify migration ran
alembic current  # Should show: 001_add_automation_json (head)
```

**Expected Output:**
```
INFO  [alembic.runtime.migration] Running upgrade  -> 001_add_automation_json, Add automation JSON columns
```

### Step 2: Verify Database Schema

Connect to database and verify columns:

```bash
# SQLite CLI
sqlite3 data/ai_automation.db

# Check table schema
.schema suggestions

# Or check column info
PRAGMA table_info(suggestions);
```

**Expected Columns:**
- `automation_json` (type: JSON/TEXT)
- `automation_yaml` (type: TEXT)
- `ha_version` (type: TEXT/VARCHAR)
- `json_schema_version` (type: TEXT/VARCHAR)

### Step 3: Update init_db() Function

Update `services/ai-automation-service-new/src/database/__init__.py`:

**Current Code (lines 106-114):**
```python
required_columns = {
    'description': 'TEXT',
    'automation_id': 'TEXT',
    'deployed_at': 'TEXT',
    'confidence_score': 'REAL',
    'safety_score': 'REAL',
    'user_feedback': 'TEXT',
    'feedback_at': 'TEXT'
}
```

**Updated Code:**
```python
required_columns = {
    'description': 'TEXT',
    'automation_id': 'TEXT',
    'deployed_at': 'TEXT',
    'confidence_score': 'REAL',
    'safety_score': 'REAL',
    'user_feedback': 'TEXT',
    'feedback_at': 'TEXT',
    # JSON automation format columns (added in migration 001_add_automation_json)
    'automation_json': 'TEXT',  # SQLite stores JSON as TEXT
    'automation_yaml': 'TEXT',
    'ha_version': 'TEXT',
    'json_schema_version': 'TEXT'
}
```

### Step 4: Test Fix

1. **Restart Service**
   ```bash
   docker compose restart ai-automation-service-new
   ```

2. **Check Logs**
   ```bash
   docker compose logs ai-automation-service-new | grep -i "database\|migration\|column"
   ```

3. **Test API Endpoint**
   ```bash
   # Test suggestions list endpoint
   curl http://localhost:8025/api/suggestions/list?limit=10
   
   # Should return JSON response without errors
   ```

4. **Test Frontend**
   - Navigate to `http://localhost:3001`
   - Check that suggestions load without SQL errors
   - Verify error message disappears

## Verification Checklist

- [ ] Migration `001_add_automation_json` has been run
- [ ] Database schema includes `automation_json` column
- [ ] Database schema includes `automation_yaml` column
- [ ] Database schema includes `ha_version` column
- [ ] Database schema includes `json_schema_version` column
- [ ] Service starts without errors
- [ ] `/api/suggestions/list` endpoint returns successfully
- [ ] Frontend (`localhost:3001`) loads suggestions without errors
- [ ] No SQL errors in service logs
- [ ] `init_db()` function updated for future safety

## Rollback Plan

If migration causes issues:

1. **Rollback Migration**
   ```bash
   cd services/ai-automation-service-new
   alembic downgrade -1
   ```

2. **Manual Column Removal** (if needed)
   ```sql
   -- SQLite doesn't support DROP COLUMN directly
   -- Would need to recreate table without columns
   -- Only do this if absolutely necessary
   ```

3. **Restore Previous Database Backup** (if available)

## Related Files

- `services/ai-automation-service-new/src/database/models.py` - Model definition
- `services/ai-automation-service-new/src/database/__init__.py` - Database initialization
- `services/ai-automation-service-new/alembic/versions/001_add_automation_json.py` - Migration script
- `services/ai-automation-service-new/alembic.ini` - Alembic configuration
- `services/ai-automation-service-new/data/ai_automation.db` - SQLite database file

## Additional Notes

### SQLite JSON Type Handling

SQLite doesn't have a native JSON type. SQLAlchemy's `JSON` type maps to:
- **Storage:** TEXT in SQLite
- **Usage:** SQLAlchemy automatically serializes/deserializes JSON

The migration uses `sa.JSON()` which is correct - SQLAlchemy handles the conversion.

### Migration Safety

The migration script (`001_add_automation_json.py`) is safe:
- Checks if columns exist before adding (lines 41-49)
- Uses nullable columns (allows existing data)
- Can be run multiple times safely

### Future Schema Changes

For future schema changes:
1. Create Alembic migration: `alembic revision --autogenerate -m "description"`
2. Review generated migration
3. Run migration: `alembic upgrade head`
4. Update `init_db()` if needed for compatibility

## Success Criteria

✅ Service starts without database errors  
✅ `/api/suggestions/list` endpoint returns 200 OK  
✅ Frontend loads suggestions without SQL errors  
✅ All required columns exist in database schema  
✅ Migration history shows `001_add_automation_json` as applied

