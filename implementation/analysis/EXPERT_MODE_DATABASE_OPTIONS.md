# Expert Mode Database Schema Options - Alpha Analysis

**Date:** November 5, 2025  
**Context:** Commit ca86050 added Expert Mode but schema is missing  
**Status:** Alpha Phase - Data loss acceptable  
**Issue:** Migration file in wrong location, model missing fields, database missing columns

---

## 🔍 Current Situation

### Problem Summary
1. **Migration file exists** but in wrong location: `database/alembic/versions/006_add_auto_draft_fields.py`
2. **Dockerfile expects** migrations in: `alembic/versions/` (root level)
3. **Model missing fields**: `Suggestion` class doesn't have `mode`, `yaml_edited_at`, `yaml_edit_count`
4. **Database missing columns**: Only 18 columns, missing 4 new expert mode fields
5. **Service uses BOTH**: `Base.metadata.create_all` (init_db) AND `alembic upgrade head` (Dockerfile)

### Missing Fields in Model
```python
# Should be in Suggestion model but missing:
mode = Column(String(20), nullable=True, server_default='auto_draft')
yaml_edited_at = Column(DateTime, nullable=True)
yaml_edit_count = Column(Integer, nullable=True, server_default='0')
yaml_generation_method = Column(String(50), nullable=True)
```

---

## ✅ Option 1: Update Model + Alpha Database Reset (RECOMMENDED)

### Approach
1. Add missing fields to `Suggestion` model in `models.py`
2. Use existing `alpha_reset_database.py` script to recreate database
3. Database gets created from models (no migration needed)

### Pros
✅ **Simplest for Alpha** - No migration complexity  
✅ **Fast** - 30 seconds vs 5+ minutes for migration debugging  
✅ **Clean slate** - Fresh database with correct schema  
✅ **Uses existing tool** - `alpha_reset_database.py` already exists for this  
✅ **Model-driven** - Single source of truth (model defines schema)  
✅ **No conflicts** - Bypasses migration/init_db conflict  
✅ **Easy rollback** - Just delete DB and recreate again  

### Cons
❌ **Data loss** - All suggestions deleted (acceptable in Alpha)  
❌ **Requires reprocessing** - Patterns need to regenerate suggestions  
❌ **Not production-ready** - Would need proper migration later  

### Steps
```bash
# 1. Update model
# Add fields to services/ai-automation-service/src/database/models.py

# 2. Stop service
docker-compose stop ai-automation-service

# 3. Run alpha reset (inside container or locally)
docker exec ai-automation-service python scripts/alpha_reset_database.py
# OR from host:
cd services/ai-automation-service
python scripts/alpha_reset_database.py

# 4. Restart service
docker-compose up -d ai-automation-service

# 5. Reprocess patterns (if needed)
# Patterns will regenerate suggestions with new schema
```

### Time Estimate
- Model update: 2 minutes
- Database reset: 30 seconds
- Service restart: 10 seconds
- **Total: ~3 minutes**

---

## ✅ Option 2: Fix Migration + Run Migration

### Approach
1. Move migration file from `database/alembic/versions/` to `alembic/versions/`
2. Update migration chain (ensure proper down_revision)
3. Run `alembic upgrade head`
4. Add missing fields to model (migration doesn't update model)

### Pros
✅ **Proper process** - Uses migration system correctly  
✅ **Preserves data** - Existing suggestions kept (if any)  
✅ **Production-ready** - Correct approach for later phases  
✅ **Versioned** - Migration history preserved  

### Cons
❌ **Complex** - Need to fix migration file location  
❌ **Model still needs update** - Migration updates DB, not model  
❌ **Potential conflicts** - `init_db()` may conflict with migrations  
❌ **Time-consuming** - Debugging migration issues can take 10+ minutes  
❌ **Two-step** - Must update both migration AND model  

### Steps
```bash
# 1. Move migration file
mv services/ai-automation-service/database/alembic/versions/006_add_auto_draft_fields.py \
   services/ai-automation-service/alembic/versions/006_add_auto_draft_fields.py

# 2. Update model (still required!)
# Add fields to Suggestion model

# 3. Check migration chain
docker exec ai-automation-service alembic history

# 4. Run migration
docker exec ai-automation-service alembic upgrade head

# 5. Verify schema
docker exec ai-automation-service python -c "
from src.database.models import Suggestion
print(hasattr(Suggestion, 'mode'))
"
```

### Time Estimate
- File move: 30 seconds
- Model update: 2 minutes
- Migration debugging: 5-15 minutes (variable)
- **Total: ~10-20 minutes**

---

## ✅ Option 3: Manual SQL + Model Update (Hybrid)

### Approach
1. Add missing fields to `Suggestion` model
2. Run SQL directly to add columns to existing database
3. Skip migration system entirely

### Pros
✅ **Fast** - Direct SQL execution  
✅ **Preserves data** - No data loss  
✅ **Simple** - No file moving or migration chain  

### Cons
❌ **Bypasses system** - Doesn't use migration or init_db  
❌ **Not reproducible** - Manual SQL hard to track  
❌ **Risk of errors** - Manual SQL can have typos  
❌ **No history** - Migration system won't know about changes  
❌ **Still need model** - Model must be updated separately  

### Steps
```bash
# 1. Update model (required)
# Add fields to Suggestion model

# 2. Run SQL directly
docker exec ai-automation-service sqlite3 /app/data/ai_automation.db "
ALTER TABLE suggestions ADD COLUMN mode VARCHAR(20) DEFAULT 'auto_draft';
ALTER TABLE suggestions ADD COLUMN yaml_edited_at DATETIME;
ALTER TABLE suggestions ADD COLUMN yaml_edit_count INTEGER DEFAULT 0;
ALTER TABLE suggestions ADD COLUMN yaml_generation_method VARCHAR(50);

CREATE INDEX ix_suggestions_mode ON suggestions(mode);
CREATE INDEX ix_suggestions_yaml_edited_at ON suggestions(yaml_edited_at);
"

# 3. Restart service to load updated model
docker-compose restart ai-automation-service
```

### Time Estimate
- Model update: 2 minutes
- SQL execution: 1 minute
- Service restart: 10 seconds
- **Total: ~3-4 minutes**

---

## 📊 Comparison Matrix

| Factor | Option 1: Model + Reset | Option 2: Fix Migration | Option 3: Manual SQL |
|--------|------------------------|-------------------------|---------------------|
| **Speed** | ⭐⭐⭐⭐⭐ (3 min) | ⭐⭐ (10-20 min) | ⭐⭐⭐⭐ (3-4 min) |
| **Data Loss** | ❌ Yes (OK in Alpha) | ✅ No | ✅ No |
| **Simplicity** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| **Production-Ready** | ❌ No | ✅ Yes | ⭐ Partial |
| **Risk** | ⭐⭐⭐⭐⭐ Low | ⭐⭐⭐ Medium | ⭐⭐ Higher |
| **Maintainability** | ⭐⭐⭐⭐ Good | ⭐⭐⭐⭐⭐ Best | ⭐⭐ Poor |
| **Debugging** | ⭐⭐⭐⭐⭐ Easy | ⭐⭐ Complex | ⭐⭐⭐ Medium |

---

## 🎯 Recommendation: Option 1 (Model + Alpha Reset)

### Why This is Best for Alpha

1. **Fastest path to working code** - 3 minutes vs 10-20 minutes
2. **Leverages existing tool** - `alpha_reset_database.py` designed for this
3. **Clean state** - Fresh database eliminates any schema drift
4. **No migration conflicts** - Bypasses the init_db vs alembic issue
5. **Alpha-appropriate** - Data loss acceptable, speed matters

### Implementation Plan

```python
# Step 1: Update models.py
# Add to Suggestion class (around line 90):

# ===== Expert Mode Fields (NEW) =====
mode = Column(String(20), nullable=True, server_default='auto_draft',
              comment='Suggestion mode: auto_draft or expert')
yaml_edited_at = Column(DateTime, nullable=True,
                        comment='Timestamp when YAML was manually edited')
yaml_edit_count = Column(Integer, nullable=True, server_default='0',
                         comment='Number of manual YAML edits made')
yaml_generation_method = Column(String(50), nullable=True,
                                comment='Method: auto_draft, expert_manual, etc.')
```

### Future Consideration

When moving to Beta/Production:
- **Option 2 becomes required** - Proper migrations needed
- **Migration file location** - Should be in `alembic/versions/` (root)
- **Migration chain** - Must maintain proper down_revision order
- **Test migrations** - Should test upgrade/downgrade paths

---

## 🔧 Quick Fix for Option 1

### Code Changes Required

**File:** `services/ai-automation-service/src/database/models.py`

**Add after line 90 (after `ha_automation_id`):**

```python
    # ===== Expert Mode Fields (NEW - Commit ca86050) =====
    mode = Column(String(20), nullable=True, server_default='auto_draft',
                  comment='Suggestion mode: auto_draft or expert')
    yaml_edited_at = Column(DateTime, nullable=True,
                            comment='Timestamp when YAML was manually edited in expert mode')
    yaml_edit_count = Column(Integer, nullable=True, server_default='0',
                             comment='Number of manual YAML edits made in expert mode')
    yaml_generation_method = Column(String(50), nullable=True,
                                    comment='Method: auto_draft, expert_manual, expert_manual_edited, etc.')
```

### Execution

```bash
# 1. Update model (add fields above)
# 2. Stop service
docker-compose stop ai-automation-service

# 3. Delete database (Alpha reset)
docker exec ai-automation-service rm -f /app/data/ai_automation.db

# 4. Restart service (creates DB from updated model)
docker-compose up -d ai-automation-service

# 5. Verify schema
docker exec ai-automation-service python -c "
from src.database.models import Suggestion
print('mode:', hasattr(Suggestion, 'mode'))
print('yaml_edited_at:', hasattr(Suggestion, 'yaml_edited_at'))
print('yaml_edit_count:', hasattr(Suggestion, 'yaml_edit_count'))
"
```

---

## 📝 Notes

- **Migration file location**: The `006_add_auto_draft_fields.py` file is in `database/alembic/versions/` but should be in `alembic/versions/` for Dockerfile to find it. This is a separate issue to fix later.

- **Dual initialization**: The service uses both `init_db()` (creates from models) AND `alembic upgrade head` (runs migrations). This can cause conflicts. Option 1 avoids this.

- **Alpha reset script**: The `alpha_reset_database.py` script exists and is designed for exactly this use case - resetting the database in Alpha phase.

---

**Recommended Action:** Proceed with Option 1 (Model Update + Alpha Reset)

