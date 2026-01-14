# FastAPI Dependency Pattern Audit

**Date:** January 16, 2026  
**Status:** ✅ **FIXED**

## Issue

FastAPI doesn't allow `= None` default values for dependency injection types like `AsyncSession` or `DatabaseSession`. This causes startup errors:

```
fastapi.exceptions.FastAPIError: Invalid args for response field! Hint: check that 
sqlalchemy.ext.asyncio.session.AsyncSession | None is a valid Pydantic field type.
```

## Pattern Searched

We searched for the problematic pattern:
- `AsyncSession | None = None`
- `DatabaseSession = None`

## Results

### ✅ Fixed Issues

**1. `services/ai-automation-service-new/src/api/preference_router.py`**
- **Line 59:** `db: AsyncSession | None = None` in `get_preferences()`
- **Line 81:** `db: AsyncSession | None = None` in `update_preferences()`
- **Fix:** Removed unused `db` parameters (stub implementation doesn't use database)
- **Also removed:** Unused `AsyncSession` import

**2. `services/ai-automation-service-new/src/api/deployment_router.py`**
- **Line 35:** `db: DatabaseSession = None` in `deploy_suggestion()`
- **Fix:** Removed unused `db` parameter

**3. `services/ai-automation-service-new/src/api/suggestion_router.py`**
- **Line 71:** `db: DatabaseSession = None` in `list_suggestions()`
- **Fix:** Removed unused `db` parameter (service handles database access)

### ✅ Correct Patterns Found

Most services use the correct pattern with `Depends()`:

**Correct Examples:**
```python
# ✅ CORRECT - Using Depends()
async def endpoint(db: AsyncSession = Depends(get_db)):
    ...

# ✅ CORRECT - Using Annotated with Depends()
async def endpoint(db: Annotated[AsyncSession, Depends(get_db)]):
    ...

# ✅ CORRECT - Using DatabaseSession type alias
async def endpoint(db: DatabaseSession):
    # DatabaseSession is already Annotated[AsyncSession, Depends(get_db)]
    ...
```

**Services with correct patterns:**
- `services/automation-miner/src/api/routes.py` - Uses `Depends(get_db_session)`
- `services/data-api/src/devices_endpoints.py` - Uses `Depends(get_db)`
- `services/device-intelligence-service/src/api/recommendations_router.py` - Uses `Depends(get_db_session)`
- `services/ai-query-service/src/api/query_router.py` - Uses `Depends(get_db)`
- All other services checked use correct dependency injection

### ⚠️ Archived Service (Not Critical)

**`services/archive/2025-q4/ai-automation-service/src/api/ask_ai_router.py`**
- **Line 3072:** `db_session: AsyncSession | None = None`
- **Status:** Archived service, not in active use
- **Action:** No fix needed (archived)

## Summary

**Total Issues Found:** 3 (all in `ai-automation-service-new`)  
**Total Issues Fixed:** 3 ✅  
**Other Services:** All use correct patterns ✅

## Verification

After fixes:
1. ✅ Service starts successfully
2. ✅ No FastAPI type annotation errors
3. ✅ Code review passed (80/100 score)
4. ✅ All endpoints functional

## Best Practices

**DO:**
```python
# Use Depends() for dependency injection
async def endpoint(db: AsyncSession = Depends(get_db)):
    ...

# Or use Annotated type alias
from ..api.dependencies import DatabaseSession

async def endpoint(db: DatabaseSession):
    # DatabaseSession = Annotated[AsyncSession, Depends(get_db)]
    ...
```

**DON'T:**
```python
# ❌ WRONG - FastAPI can't handle None defaults for dependency types
async def endpoint(db: AsyncSession | None = None):
    ...

# ❌ WRONG - Same issue
async def endpoint(db: DatabaseSession = None):
    ...
```

## Related Files

- `services/ai-automation-service-new/src/api/preference_router.py` - Fixed
- `services/ai-automation-service-new/src/api/deployment_router.py` - Fixed
- `services/ai-automation-service-new/src/api/suggestion_router.py` - Fixed
- `implementation/AUTOMATION_MISMATCH_FIX.md` - Related fix documentation
