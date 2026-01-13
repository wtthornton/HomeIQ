# Blueprint Suggestion Fixes - Next Steps

**Date:** January 13, 2026  
**Status:** ✅ Code changes complete, migration needed

## Current Status

### ✅ Code Changes Complete
- Model updated with `blueprint_name` and `blueprint_description` columns
- Service updated to save name/description when creating suggestions
- API route updated with enrichment logic
- All code reviewed and accepted

### ⏳ Database Migration Needed
- SQLAlchemy's `create_all()` only creates tables, doesn't alter existing ones
- Need to manually add columns to existing `blueprint_suggestions` table
- Migration script created but needs proper path in container

## Migration Options

### Option 1: Manual SQL (Quick)
Connect to database and run:

```sql
-- For SQLite
ALTER TABLE blueprint_suggestions ADD COLUMN blueprint_name VARCHAR(255);
ALTER TABLE blueprint_suggestions ADD COLUMN blueprint_description TEXT;
```

### Option 2: Python Script (Recommended)
The migration script is ready at:
`services/blueprint-suggestion-service/scripts/add_blueprint_name_description_columns.py`

Run it from container:
```bash
docker compose exec blueprint-suggestion-service python /path/to/script.py
```

Or copy it into container:
```bash
docker compose cp services/blueprint-suggestion-service/scripts/add_blueprint_name_description_columns.py blueprint-suggestion-service:/tmp/migrate.py
docker compose exec blueprint-suggestion-service python /tmp/migrate.py
```

### Option 3: Recreate Table (If OK to lose data)
If existing suggestions can be regenerated:
```bash
# Delete database file (backup first!)
docker compose exec blueprint-suggestion-service rm /app/data/blueprint_suggestions.db
# Restart service - SQLAlchemy will create new schema
docker compose restart blueprint-suggestion-service
# Regenerate suggestions
curl -X POST http://localhost:8039/api/blueprint-suggestions/generate
```

## Verification

### Check Columns Added
```sql
PRAGMA table_info(blueprint_suggestions);
-- Should show blueprint_name and blueprint_description
```

### Test API
```bash
GET http://localhost:8039/api/blueprint-suggestions/suggestions?limit=1
```

Expected response:
```json
{
  "suggestions": [{
    "blueprint_name": "...",  // Should be populated (after enrichment)
    "blueprint_description": "...",  // Should be populated (after enrichment)
    ...
  }]
}
```

### Check Enrichment
1. Fetch suggestions (should trigger enrichment for NULL names)
2. Fetch again (should now have names populated)
3. Check database (names should be persisted)

## Expected Behavior

### New Suggestions
- Will automatically include `blueprint_name` and `blueprint_description`
- No enrichment needed

### Existing Suggestions
- Will have NULL `blueprint_name` and `blueprint_description` initially
- Will be enriched on first fetch (if blueprint-index service available)
- Database will be updated for future requests

## Troubleshooting

### If columns don't exist
- Run migration script
- Or manually add via SQL

### If enrichment doesn't work
- Check blueprint-index service is running
- Check logs for connection errors
- Verify `BLUEPRINT_INDEX_URL` is correct

### If names still empty after enrichment
- Check blueprint-index service response
- Verify blueprint exists in blueprint-index
- Check service logs for errors

## Summary

**Code is ready!** Just need to:
1. ✅ Run migration to add columns (or recreate table)
2. ✅ Test enrichment logic
3. ✅ Verify in UI

Once migration is complete, suggestions will show descriptive names and descriptions! 🎉
