# 2025 Synergy Quality Scoring - Next Steps Implementation Complete

**Date:** January 16, 2025  
**Status:** ✅ **NEXT STEPS COMPLETE**

---

## Implementation Summary

All next steps from the implementation complete document have been created and are ready for execution.

---

## ✅ Step 1: Database Migration Script

**File:** `services/ai-pattern-service/scripts/add_quality_columns.py`

### Purpose
Adds the 4 quality columns to the `synergy_opportunities` table:
- `quality_score` (FLOAT, NULL)
- `quality_tier` (VARCHAR(20), NULL)
- `last_validated_at` (TIMESTAMP, NULL)
- `filter_reason` (VARCHAR(200), NULL)

### Features
- Checks if columns already exist (idempotent)
- Dry-run mode to preview changes
- Shows current schema after migration
- Error handling and rollback on failure

### Usage
```bash
# Preview changes (dry run)
python services/ai-pattern-service/scripts/add_quality_columns.py --dry-run

# Apply migration
python services/ai-pattern-service/scripts/add_quality_columns.py

# Custom database path
python services/ai-pattern-service/scripts/add_quality_columns.py --db-path /custom/path/database.db
```

### Docker Usage
```bash
# In Docker container
docker exec -it ai-pattern-service python /app/scripts/add_quality_columns.py

# Or with custom path
docker exec -it ai-pattern-service python /app/scripts/add_quality_columns.py --db-path /app/data/ai_automation.db
```

---

## ✅ Step 2: Backfill Quality Scores Script

**File:** `services/ai-pattern-service/scripts/backfill_quality_scores.py`

### Purpose
Calculates quality scores for all existing synergies that don't have quality scores yet.

### Features
- Processes synergies in batches (configurable batch size)
- Uses `SynergyQualityScorer` to calculate scores
- Updates `quality_score`, `quality_tier`, and `last_validated_at`
- Dry-run mode to preview changes
- Statistics reporting (tier distribution, update counts)
- Error handling per synergy (continues on errors)

### Usage
```bash
# Preview changes (dry run)
python services/ai-pattern-service/scripts/backfill_quality_scores.py --dry-run

# Apply backfill
python services/ai-pattern-service/scripts/backfill_quality_scores.py

# Custom database path and batch size
python services/ai-pattern-service/scripts/backfill_quality_scores.py \
    --db-path /custom/path/database.db \
    --batch-size 50
```

### Docker Usage
```bash
# In Docker container
docker exec -it ai-pattern-service python /app/scripts/backfill_quality_scores.py

# With dry-run
docker exec -it ai-pattern-service python /app/scripts/backfill_quality_scores.py --dry-run
```

### Output Example
```
Backfilling quality scores for existing synergies...
Database: /app/data/ai_automation.db
Batch size: 100

Found 1234 synergies without quality scores
Processing batch 1 (1-100 of 1234)...
Processing batch 2 (101-200 of 1234)...
...

Backfill complete!
  Total synergies: 1234
  Updated: 1234
  Errors: 0

Tier distribution:
  high: 245
  medium: 512
  low: 387
  poor: 90
```

---

## Execution Order

### 1. Run Database Migration (Required First)
```bash
# Step 1: Add columns
python services/ai-pattern-service/scripts/add_quality_columns.py
```

### 2. Run Backfill (After Migration)
```bash
# Step 2: Calculate quality scores for existing synergies
python services/ai-pattern-service/scripts/backfill_quality_scores.py
```

---

## Testing Recommendations

### Manual Testing
1. **Migration Script:**
   ```bash
   # Test with dry-run first
   python services/ai-pattern-service/scripts/add_quality_columns.py --dry-run
   
   # Verify output, then run for real
   python services/ai-pattern-service/scripts/add_quality_columns.py
   
   # Verify columns were added (check database schema)
   sqlite3 /app/data/ai_automation.db "PRAGMA table_info(synergy_opportunities);"
   ```

2. **Backfill Script:**
   ```bash
   # Test with dry-run first
   python services/ai-pattern-service/scripts/backfill_quality_scores.py --dry-run
   
   # Verify output, then run for real
   python services/ai-pattern-service/scripts/backfill_quality_scores.py
   
   # Verify scores were calculated
   sqlite3 /app/data/ai_automation.db "SELECT COUNT(*) FROM synergy_opportunities WHERE quality_score IS NOT NULL;"
   sqlite3 /app/data/ai_automation.db "SELECT quality_tier, COUNT(*) FROM synergy_opportunities GROUP BY quality_tier;"
   ```

### Integration Testing
After running both scripts, verify:
1. All synergies have quality scores (no NULL values)
2. Quality tiers are distributed correctly
3. Quality scores are in valid range (0.0-1.0)
4. Last validated timestamp is set

---

## Database Schema Verification

After running the migration, verify the schema:

```sql
-- Check columns exist
PRAGMA table_info(synergy_opportunities);

-- Check quality score distribution
SELECT 
    quality_tier,
    COUNT(*) as count,
    AVG(quality_score) as avg_score,
    MIN(quality_score) as min_score,
    MAX(quality_score) as max_score
FROM synergy_opportunities
GROUP BY quality_tier;

-- Check for NULL quality scores (should be 0 after backfill)
SELECT COUNT(*) FROM synergy_opportunities WHERE quality_score IS NULL;
```

---

## Next Steps After Scripts

### 3. Testing
- Run unit tests for quality scoring logic
- Run integration tests for storage and query functions
- Test API endpoints with quality filters

### 4. Monitoring
- Monitor quality score distribution
- Track filter rates (how many synergies are filtered)
- Monitor query performance with quality filters

### 5. Production Deployment
1. Run migration script in production
2. Run backfill script in production (during low-traffic window)
3. Monitor quality metrics
4. Enable quality filtering in production queries

---

## Files Created

1. ✅ `services/ai-pattern-service/scripts/add_quality_columns.py` (140 lines)
2. ✅ `services/ai-pattern-service/scripts/backfill_quality_scores.py` (280 lines)

---

## Status: ✅ READY FOR EXECUTION

Both scripts are complete, tested for syntax errors, and ready to run. They follow the same patterns as existing database migration scripts in the project.

---

## References

- **Implementation Complete Document**: `implementation/2025_SYNERGY_SCORING_FILTERING_IMPLEMENTATION_COMPLETE.md`
- **Quality Scorer Service**: `services/ai-pattern-service/src/services/synergy_quality_scorer.py`
- **Database Model**: `services/ai-pattern-service/src/database/models.py`
- **Existing Migration Script**: `services/ai-pattern-service/scripts/add_2025_synergy_fields.py`
