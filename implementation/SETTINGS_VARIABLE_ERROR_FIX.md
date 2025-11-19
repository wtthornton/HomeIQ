# Settings Variable Error Fix

## Issue Summary

**Error Message:** `cannot access local variable 'settings' where it is not associated with a value`

**Location:** `services/ai-automation-service/src/api/ask_ai_router.py`

**User Impact:** Ask AI endpoint was failing when processing natural language queries, preventing users from creating automations.

## Root Cause

The error occurred due to a redundant import of `settings` inside the `generate_suggestions_from_query` function:

1. **Module-level import (line 33):** `from ..config import settings` - This is correct and available throughout the module
2. **Function-level import (line 3234):** `from ..config import settings` - This was redundant and caused the issue

**Why it failed:**
- When Python encounters an import statement inside a function, it treats that variable as a **local variable** for the entire function scope
- The function uses `settings` on lines 3014-3016 (before the redundant import on line 3234)
- Python detected that `settings` would be assigned locally (via the import on line 3234), but it was referenced before that assignment
- This triggered the error: "cannot access local variable 'settings' where it is not associated with a value"

## Fix Applied

**File:** `services/ai-automation-service/src/api/ask_ai_router.py`

**Change:** Removed the redundant import on line 3234:

```python
# BEFORE (lines 3232-3238):
# Check cache first (Phase 4: Entity Context Caching)
from ..services.entity_context_cache import get_entity_cache
from ..config import settings  # ❌ REDUNDANT - causes local variable conflict

entity_cache = get_entity_cache(
    ttl_seconds=getattr(settings, 'entity_cache_ttl_seconds', 300)
)

# AFTER (lines 3232-3237):
# Check cache first (Phase 4: Entity Context Caching)
from ..services.entity_context_cache import get_entity_cache

entity_cache = get_entity_cache(
    ttl_seconds=getattr(settings, 'entity_cache_ttl_seconds', 300)  # ✅ Uses module-level import
)
```

## Verification

- ✅ Removed redundant import
- ✅ Verified all `settings` references in the file use the module-level import (line 33)
- ✅ No linting errors introduced
- ✅ Function logic unchanged - only removed unnecessary import

## Testing Recommendations

1. **Test the Ask AI endpoint** with the same query that failed:
   ```
   "Every 10 mins execute a random 30 sec effect on the office led. The LED is managed by WLED. make sure the LED resets back to the original state."
   ```

2. **Verify entity caching** still works correctly (the code that was using the redundant import)

3. **Test other Ask AI queries** to ensure no regressions

## Related Code

- **Module-level import:** Line 33: `from ..config import settings`
- **Function using settings:** `generate_suggestions_from_query()` (starts at line 2986)
- **Settings usage in function:** Lines 3014-3016, 3237, and others throughout the function

## Status

✅ **FIXED** - Redundant import removed. The error no longer occurs when processing Ask AI queries.

## Verification Results

**Test Date:** 2025-11-19  
**Test Query:** "Every 10 mins execute a random 30 sec effect on the office led. The LED is managed by WLED. make sure the LED resets back to the original state."

**Before Fix:**
- Error: `cannot access local variable 'settings' where it is not associated with a value`
- Status Code: 500
- Location: Line 3016 and 3579 in `generate_suggestions_from_query()`

**After Fix:**
- ✅ No more `settings` variable error
- ✅ Service successfully processes the query past the entity enrichment phase
- ⚠️ Note: A different unrelated error appeared (`cache_control` parameter issue with OpenAI API), but the original `settings` variable error is completely resolved

**Action Taken:**
1. Removed redundant `from ..config import settings` on line 3234
2. Rebuilt Docker image: `docker-compose build ai-automation-service`
3. Restarted service: `docker-compose up -d ai-automation-service`
4. Verified fix with test query

The `settings` variable error is **completely resolved**.

