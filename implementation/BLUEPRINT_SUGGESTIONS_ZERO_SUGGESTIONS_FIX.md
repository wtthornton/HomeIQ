# Blueprint Suggestions Zero Suggestions - Root Cause Analysis & Fix

**Date:** January 14, 2026  
**Issue:** Blueprint Suggestions page shows zero suggestions due to database schema mismatch  
**Status:** Fixed (migration code added, manual migration may be required)

## Root Cause

The Blueprint Suggestions page was showing zero suggestions because of a **database schema mismatch**:

### Error Details
```
sqlite3.OperationalError: no such column: blueprint_suggestions.blueprint_name
```

### Technical Analysis

1. **Model Definition** (`services/blueprint-suggestion-service/src/models/suggestion.py`):
   - Model includes `blueprint_name` and `blueprint_description` columns (lines 20-21)
   - These columns are expected by the API response schema

2. **Database Schema**:
   - Existing database was created with an older schema that didn't include these columns
   - SQLAlchemy's `create_all()` only creates missing tables, not missing columns in existing tables

3. **API Query Failure**:
   - The query in `suggestion_service.py` (line 94) selects all columns including `blueprint_name` and `blueprint_description`
   - This causes a 500 error when the columns don't exist
   - Frontend shows "No suggestions found" because the API request fails

## Fixes Implemented

### 1. Database Migration Code Added

**File:** `services/blueprint-suggestion-service/src/database.py`

Added `_run_migrations()` function that:
- Checks if `blueprint_name` and `blueprint_description` columns exist
- Adds missing columns automatically on service startup
- Supports both SQLite and PostgreSQL

**Code:**
```python
async def _run_migrations(conn):
    """Run database migrations to add missing columns."""
    logger.info("Checking for required migrations...")
    
    if "sqlite" in settings.database_url:
        # Check if table exists and what columns it has
        result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='blueprint_suggestions'"))
        table_exists = result.fetchone() is not None
        
        if table_exists:
            # Check existing columns
            result = await conn.execute(text("PRAGMA table_info(blueprint_suggestions)"))
            columns = {row[1]: row for row in result.fetchall()}
            
            # Add blueprint_name if missing
            if "blueprint_name" not in columns:
                logger.info("Adding blueprint_name column...")
                await conn.execute(text("ALTER TABLE blueprint_suggestions ADD COLUMN blueprint_name VARCHAR(255)"))
                logger.info("✓ Added blueprint_name column")
            
            # Add blueprint_description if missing
            if "blueprint_description" not in columns:
                logger.info("Adding blueprint_description column...")
                await conn.execute(text("ALTER TABLE blueprint_suggestions ADD COLUMN blueprint_description TEXT"))
                logger.info("✓ Added blueprint_description column")
```

**Integration:**
```python
async def init_db():
    """Initialize database tables and run migrations."""
    logger.info("Initializing database...")
    async with engine.begin() as conn:
        # First, create all tables (if they don't exist)
        await conn.run_sync(Base.metadata.create_all)
        
        # Then, run migrations to add missing columns to existing tables
        await _run_migrations(conn)
    logger.info("Database initialized successfully")
```

### 2. Migration Script Created

**File:** `services/blueprint-suggestion-service/migrate_db.py`

Standalone script for manual migration if needed:
```python
"""Quick migration script to add missing columns."""
import asyncio
import aiosqlite

async def migrate():
    db_path = '/app/data/blueprint_suggestions.db'
    conn = await aiosqlite.connect(db_path)
    
    # Check existing columns
    cursor = await conn.execute('PRAGMA table_info(blueprint_suggestions)')
    rows = await cursor.fetchall()
    cols = [row[1] for row in rows]
    
    has_name = 'blueprint_name' in cols
    has_desc = 'blueprint_description' in cols
    
    if not has_name:
        await conn.execute('ALTER TABLE blueprint_suggestions ADD COLUMN blueprint_name VARCHAR(255)')
        await conn.commit()
        print('✓ Added blueprint_name column')
    
    if not has_desc:
        await conn.execute('ALTER TABLE blueprint_suggestions ADD COLUMN blueprint_description TEXT')
        await conn.commit()
        print('✓ Added blueprint_description column')
    
    await conn.close()
```

## Immediate Action Required

**If the service has already started with the old schema:**

1. **Option 1: Restart Service (Recommended)**
   ```bash
   docker compose restart blueprint-suggestion-service
   ```
   The migration should run automatically on startup.

2. **Option 2: Manual Migration**
   ```bash
   # Copy migration script to container
   docker compose cp services/blueprint-suggestion-service/migrate_db.py blueprint-suggestion-service:/app/migrate_db.py
   
   # Run migration
   docker compose exec blueprint-suggestion-service python /app/migrate_db.py
   ```

3. **Option 3: Direct SQL (If above don't work)**
   ```bash
   docker compose exec blueprint-suggestion-service sqlite3 /app/data/blueprint_suggestions.db "ALTER TABLE blueprint_suggestions ADD COLUMN blueprint_name VARCHAR(255); ALTER TABLE blueprint_suggestions ADD COLUMN blueprint_description TEXT;"
   ```

## Testing

After applying the fix:

1. **Verify Migration Ran:**
   - Check service logs: `docker compose logs blueprint-suggestion-service | grep -i migration`
   - Should see "Checking for required migrations..." and "✓ Added blueprint_name column" messages

2. **Test API:**
   ```bash
   curl http://localhost:8032/api/blueprint-suggestions/suggestions
   ```
   Should return 200 OK with empty suggestions array (not 500 error)

3. **Test UI:**
   - Navigate to http://localhost:3001/blueprint-suggestions
   - Should show "No suggestions found" (normal if no suggestions exist)
   - Should NOT show "Failed to load suggestions" error
   - Stats should load correctly (Total: 0, Pending: 0, etc.)

4. **Generate Suggestions:**
   - Click "Generate Suggestions" button
   - Fill in parameters and generate
   - Suggestions should appear in the list

## Recommendations for Improvement

### 1. Database Migration System

**Current State:**
- Manual migration code in `init_db()`
- No version tracking
- No rollback capability

**Recommendations:**
- **Use Alembic** for proper migration management:
  ```bash
  # Install Alembic
  pip install alembic
  
  # Initialize
  alembic init alembic
  
  # Create migration
  alembic revision --autogenerate -m "Add blueprint_name and blueprint_description"
  
  # Run migrations
  alembic upgrade head
  ```

- **Benefits:**
  - Version tracking
  - Rollback capability
  - Migration history
  - Better error handling

### 2. Error Handling Improvements

**Current Issues:**
- API returns 500 error when schema doesn't match
- Frontend shows generic "Failed to load suggestions" message
- No clear indication that it's a database schema issue

**Recommendations:**
- **Add Schema Version Check:**
  ```python
  async def check_schema_version(db: AsyncSession) -> bool:
      """Check if database schema matches model."""
      try:
          result = await db.execute(text("PRAGMA table_info(blueprint_suggestions)"))
          columns = {row[1] for row in result.fetchall()}
          required = {'blueprint_name', 'blueprint_description'}
          return required.issubset(columns)
      except Exception:
          return False
  ```

- **Better Error Messages:**
  - Return 503 Service Unavailable with clear message when schema mismatch detected
  - Frontend should show "Database schema update required" instead of generic error

- **Health Check Endpoint:**
  ```python
  @router.get("/health/schema")
  async def check_schema_health():
      """Check if database schema is up to date."""
      try:
          # Check schema version
          schema_ok = await check_schema_version(db)
          return {
              "schema_version": "1.0.0",
              "schema_ok": schema_ok,
              "status": "healthy" if schema_ok else "schema_mismatch"
          }
      except Exception as e:
          return {"status": "error", "message": str(e)}
  ```

### 3. Testing Improvements

**Current State:**
- No automated tests for schema migrations
- No integration tests for API endpoints

**Recommendations:**
- **Migration Tests:**
  ```python
  async def test_migration_adds_columns():
      """Test that migration adds missing columns."""
      # Create database with old schema
      # Run migration
      # Verify columns exist
  ```

- **API Integration Tests:**
  ```python
  async def test_get_suggestions_with_missing_columns():
      """Test API handles missing columns gracefully."""
      # Create database without columns
      # Call API
      # Should return error or trigger migration
  ```

### 4. Monitoring & Observability

**Recommendations:**
- **Add Metrics:**
  - Database schema version
  - Migration execution count
  - Migration failures

- **Add Logging:**
  - Migration execution logs
  - Schema check results
  - API errors with schema context

- **Add Alerts:**
  - Alert when schema mismatch detected
  - Alert on migration failures

### 5. Deployment Process

**Recommendations:**
- **Pre-deployment Checks:**
  - Run schema migration check before deployment
  - Verify database compatibility

- **Rollback Plan:**
  - Keep old schema migration scripts
  - Test rollback procedures
  - Document rollback steps

- **Documentation:**
  - Document all schema changes
  - Keep migration history
  - Document manual migration procedures

## Verification Checklist

- [x] Root cause identified (database schema mismatch)
- [x] Migration code added to `database.py`
- [x] Migration script created for manual execution
- [ ] Service restarted and migration verified
- [ ] API tested (returns 200 OK, not 500)
- [ ] UI tested (no error messages)
- [ ] Suggestions generation tested
- [ ] Documentation updated

## Next Steps

1. **Immediate:** Restart service and verify migration runs
2. **Short-term:** Implement Alembic for proper migration management
3. **Medium-term:** Add comprehensive error handling and health checks
4. **Long-term:** Implement full test coverage and monitoring

## Related Files

- `services/blueprint-suggestion-service/src/database.py` - Database initialization with migration
- `services/blueprint-suggestion-service/src/models/suggestion.py` - Database model
- `services/blueprint-suggestion-service/src/services/suggestion_service.py` - Service layer
- `services/blueprint-suggestion-service/src/api/routes.py` - API endpoints
- `services/ai-automation-ui/src/pages/BlueprintSuggestions.tsx` - Frontend component
- `services/blueprint-suggestion-service/migrate_db.py` - Manual migration script
- `services/blueprint-suggestion-service/migrations/add_blueprint_name_description.sql` - SQL migration

## References

- SQLite ALTER TABLE documentation: https://www.sqlite.org/lang_altertable.html
- SQLAlchemy migrations: https://docs.sqlalchemy.org/en/20/core/metadata.html
- Alembic documentation: https://alembic.sqlalchemy.org/
