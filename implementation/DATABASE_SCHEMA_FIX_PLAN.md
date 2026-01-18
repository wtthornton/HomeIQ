# Database Schema Fix - Missing plan_id Column

**Date:** January 16, 2026  
**Issue:** SQL Error - `no such column: suggestions.plan_id`  
**Service:** `ai-automation-service-new` (Port 8004)

## Problem Summary

The `ha-ai-agent-service` UI is failing with a SQL error when querying the `suggestions` table:

```
(sqlite3.OperationalError) no such column: suggestions.plan_id
```

**SQL Query:**
```sql
SELECT suggestions.id, suggestions.pattern_id, ..., suggestions.plan_id, 
       suggestions.compiled_id, suggestions.deployment_id 
FROM suggestions 
ORDER BY suggestions.created_at DESC 
LIMIT ? OFFSET ?
```

## Root Cause

1. **Model Definition** (`services/ai-automation-service-new/src/database/models.py`):
   - The `Suggestion` model includes `plan_id`, `compiled_id`, and `deployment_id` columns (lines 42-44)
   - These columns are part of the Hybrid Flow Integration (Epic 39)

2. **Migration Exists** (`services/ai-automation-service-new/alembic/versions/002_add_hybrid_flow_tables.py`):
   - Migration `002_add_hybrid_flow_tables` should add these columns to the suggestions table (lines 97-107)
   - The migration checks if columns exist before adding them (safe to run multiple times)

3. **Migration Not Run**:
   - The migration hasn't been executed on the database
   - Database schema doesn't match the model definition

4. **Manual Fallback Missing** (`services/ai-automation-service-new/src/database/__init__.py`):
   - The `init_db()` function has a manual schema sync fallback (lines 159-171)
   - This fallback was missing `plan_id`, `compiled_id`, and `deployment_id` columns
   - Even if migrations fail, the manual fallback should add missing columns

## Fix Applied

### 1. Updated Manual Fallback (✅ COMPLETED)

**File:** `services/ai-automation-service-new/src/database/__init__.py`

**Change:** Added missing columns to `required_columns` dictionary:

```python
required_columns = {
    # ... existing columns ...
    # Hybrid Flow Integration columns (Epic 39 - Hybrid Flow)
    'plan_id': 'TEXT',  # Link to plans table
    'compiled_id': 'TEXT',  # Link to compiled_artifacts table
    'deployment_id': 'TEXT'  # Link to deployments table
}
```

**Impact:**
- When `init_db()` runs, it will check for these columns and add them if missing
- Works as a fallback even if Alembic migrations fail
- Service startup will automatically fix the schema

## Deployment Steps

### Option 1: Restart Service (Recommended)

The fix is in the code. Simply restart the service and `init_db()` will add the missing columns:

```powershell
# Stop the service
docker compose stop ai-automation-service-new

# Start the service (init_db() will run on startup)
docker compose up -d ai-automation-service-new

# Verify service is healthy
Invoke-RestMethod -Uri "http://localhost:8004/health"
```

**Expected Behavior:**
- Service starts successfully
- `init_db()` runs and detects missing columns
- Adds `plan_id`, `compiled_id`, `deployment_id` columns automatically
- Logs: `"✅ Added 'plan_id' column to suggestions table"`

### Option 2: Run Migration Manually (If Needed)

If you want to run the migration explicitly:

```powershell
# Run Alembic migration
docker compose run --rm ai-automation-service-new alembic upgrade head

# Restart service
docker compose restart ai-automation-service-new
```

### Option 3: Manual SQL Fix (Emergency Only)

If migrations and fallback both fail, you can manually add the columns:

```sql
ALTER TABLE suggestions ADD COLUMN plan_id TEXT;
ALTER TABLE suggestions ADD COLUMN compiled_id TEXT;
ALTER TABLE suggestions ADD COLUMN deployment_id TEXT;

-- Create indexes (optional, for performance)
CREATE INDEX IF NOT EXISTS ix_suggestions_plan_id ON suggestions(plan_id);
CREATE INDEX IF NOT EXISTS ix_suggestions_compiled_id ON suggestions(compiled_id);
CREATE INDEX IF NOT EXISTS ix_suggestions_deployment_id ON suggestions(deployment_id);
```

## Verification

### 1. Check Service Health

```powershell
$health = Invoke-RestMethod -Uri "http://localhost:8004/health"
Write-Host "Status: $($health.status)"
```

### 2. Check Database Schema

```powershell
# Using sqlite3 command-line tool (if available)
sqlite3 data/ai_automation.db "PRAGMA table_info(suggestions);"
```

**Expected Output:**
- Should show `plan_id`, `compiled_id`, `deployment_id` columns

### 3. Test Query via API

```powershell
# Test suggestions endpoint
$suggestions = Invoke-RestMethod -Uri "http://localhost:8004/api/suggestions?limit=10"
Write-Host "Suggestions returned: $($suggestions.suggestions.Count)"
```

**Expected:** No SQL errors, suggestions list returned successfully

### 4. Check UI (ha-ai-agent-service)

Navigate to: `http://localhost:3001/ha-agent`

**Expected:**
- No SQL errors displayed
- Suggestions list loads correctly
- No errors in browser console

## Migration Details

### Migration File: `002_add_hybrid_flow_tables.py`

**Creates:**
- `plans` table - Automation plans (template_id + parameters)
- `compiled_artifacts` table - Compiled YAML artifacts
- `deployments` table - Deployment records with audit trail
- Adds columns to `suggestions` table:
  - `plan_id` (TEXT, nullable, indexed)
  - `compiled_id` (TEXT, nullable, indexed)
  - `deployment_id` (TEXT, nullable, indexed)

**Migration ID:** `002_add_hybrid_flow_tables`  
**Depends on:** `001_add_automation_json`

## Related Files

### Model Definition
- `services/ai-automation-service-new/src/database/models.py` (lines 15-44)

### Migration
- `services/ai-automation-service-new/alembic/versions/002_add_hybrid_flow_tables.py`

### Database Initialization
- `services/ai-automation-service-new/src/database/__init__.py` (lines 116-189)

### Service Startup
- `services/ai-automation-service-new/src/main.py` (line 212: `await init_db()`)

## Notes

1. **Hybrid Flow Integration:**
   - These columns enable linking suggestions to the Hybrid Flow lifecycle
   - `plan_id` → Links to automation plans
   - `compiled_id` → Links to compiled YAML artifacts
   - `deployment_id` → Links to deployment records

2. **Backward Compatibility:**
   - All three columns are nullable (`nullable=True`)
   - Existing suggestions without these columns will work fine
   - Columns are optional - suggestions can exist without Hybrid Flow linkage

3. **Indexes:**
   - The migration creates indexes on these columns for performance
   - Manual fallback doesn't create indexes (not critical for functionality)
   - Indexes will be created when migration runs successfully

4. **Future Migrations:**
   - Ensure all new columns are added to `required_columns` in `init_db()` fallback
   - This provides resilience if migrations fail

## Status

- ✅ **Code Fix Applied:** Manual fallback updated with missing columns
- ⏳ **Deployment Pending:** Service restart required to apply fix
- ⏳ **Verification Pending:** Need to verify fix works after restart

## Next Steps

1. **Restart Service** - Apply the fix by restarting the service
2. **Verify Fix** - Check service health and UI functionality
3. **Monitor Logs** - Ensure no errors during startup or query execution
4. **Update Documentation** - If needed, update deployment docs

---

**Related Issues:**
- Epic 39: Hybrid Flow Implementation
- Story 39.10: Automation Service Foundation
