# Synergies API 404 Fix - Research, Architecture & Planning

## Research Findings

### FastAPI Route Matching Behavior

From FastAPI documentation (found in `populate_all_docs.py`):
> **"The more specific path `/users/me` must be declared before the generic path `/users/{user_id}` to ensure the specific route is matched first."**

**Key Insight**: FastAPI matches routes in the order they're **declared/registered**, not alphabetically or by specificity. This means:
1. Routes are matched in the order they're added via `app.include_router()` or `@app.get()`
2. Within a router, routes are matched in the order they're decorated
3. Specific routes MUST be registered before parameterized routes

### Current Architecture Analysis

**Current State:**
- `specific_router` is defined in `synergy_router.py` (line 34)
- `/stats` route is on `specific_router` (line 50)
- `/list` route is on `specific_router` (line 133)
- `/{synergy_id}` route is on `router` (line 346)
- `main.py` tries to include `specific_router` first (line 220-221)
- **Problem**: `specific_router` is NOT accessible when module is imported (`hasattr` returns `False`)

**Route Registration Order (Current):**
1. `/list` (from `specific_router` - but `specific_router` not accessible, so this fails)
2. `/{synergy_id}` (from `router` - matches `/stats` first!)
3. `/stats` (from `router` - never reached)

### Root Cause

**Primary Issue**: `specific_router` is defined but not accessible when `synergy_router` module is imported. This could be due to:
1. Python module import order issue
2. Exception during module import that prevents `specific_router` from being set
3. Module structure preventing proper export

**Secondary Issue**: Even if `specific_router` were accessible, FastAPI route matching within a single router follows decoration order, not file order.

## Architecture Solutions

### Solution 1: Fix `specific_router` Accessibility (Recommended)

**Approach**: Ensure `specific_router` is properly exported and accessible.

**Implementation:**
1. Verify `specific_router` is defined at module level (✅ already done)
2. Check for import errors that might prevent `specific_router` from being set
3. Explicitly export `specific_router` in `__init__.py` if needed
4. Use direct import: `from .api.synergy_router import specific_router, router`

**Pros:**
- Maintains separation of concerns (specific vs parameterized routes)
- Follows FastAPI best practices
- Clean architecture

**Cons:**
- Requires debugging why `specific_router` isn't accessible
- May require module structure changes

### Solution 2: Move `/stats` to `router` and Ensure Correct Order

**Approach**: Put all routes on `router` but ensure `/stats` is decorated before `/{synergy_id}`.

**Implementation:**
1. Move `/stats` from `specific_router` to `router`
2. Ensure `/stats` decorator appears before `/{synergy_id}` decorator in file
3. Remove `specific_router` entirely (or keep only for `/list`)

**Pros:**
- Simpler - single router
- No module import issues
- FastAPI should match in decoration order

**Cons:**
- Less separation of concerns
- Route order depends on file order (more fragile)

### Solution 3: Use Different Route Structure

**Approach**: Change route paths to avoid conflict.

**Implementation:**
1. Change `/stats` to `/api/v1/synergies/statistics` or `/api/v1/synergies/_stats`
2. Update frontend to use new path
3. No route matching conflicts

**Pros:**
- No route matching issues
- Clear separation

**Cons:**
- Requires frontend changes
- Breaking change for API consumers

## Recommended Solution: Hybrid Approach

**Phase 1: Quick Fix (Solution 2)**
- Move `/stats` to `router` 
- Ensure it's defined before `/{synergy_id}`
- Test immediately

**Phase 2: Proper Fix (Solution 1)**
- Debug why `specific_router` isn't accessible
- Fix module import/export
- Restore proper architecture with `specific_router`

## Implementation Plan

### Step 1: Research & Analysis ✅
- [x] Research FastAPI route matching behavior
- [x] Analyze current architecture
- [x] Identify root cause

### Step 2: Quick Fix Implementation ✅
- [x] Move `/stats` from `specific_router` to `router`
- [x] Ensure `/stats` decorator is before `/{synergy_id}` decorator
- [x] Remove dependency on `specific_router` for `/stats`
- [x] Test route order

### Step 3: Verification ✅
- [x] Verify route order: `/stats` before `/{synergy_id}`
- [x] Test `/api/v1/synergies/stats` endpoint (returns 200 OK)
- [x] Test frontend integration (Playwright - page loads successfully)
- [x] Check Docker logs for route handler calls (200 OK confirmed)

### Step 4: Debug `specific_router` Issue (Optional - Phase 2)
- [ ] Check for import errors in `synergy_router.py`
- [ ] Verify module structure
- [ ] Test direct import: `from src.api.synergy_router import specific_router`
- [ ] Fix module export if needed
- [ ] Restore proper architecture
- **Status**: Deferred - current solution works correctly

## Technical Details

### FastAPI Route Matching Algorithm

FastAPI uses a **first-match-wins** algorithm:
1. Routes are checked in the order they're registered via `app.include_router()`
2. Within a router, routes are checked in the order they're decorated
3. First matching route wins (specific or parameterized)

### Current Route Definitions

```python
# Line 34: specific_router = APIRouter(...)
# Line 50: @specific_router.get("/stats")  # NOT ACCESSIBLE
# Line 133: @specific_router.get("/list")   # Works (why?)
# Line 346: @router.get("/{synergy_id}")   # Matches first
```

### Expected Route Order (After Fix)

```
1. /api/v1/synergies/stats        (specific_router or router)
2. /api/v1/synergies/list         (specific_router)
3. /api/v1/synergies/{synergy_id} (router)
```

## Testing Strategy

1. **Unit Test**: Verify route order in FastAPI app
2. **Integration Test**: Test `/api/v1/synergies/stats` endpoint
3. **E2E Test**: Playwright test for frontend integration
4. **Log Verification**: Check Docker logs for route handler calls

## Success Criteria ✅ ALL MET

- ✅ `/api/v1/synergies/stats` returns 200 OK with stats data
- ✅ Route order shows `/stats` before `/{synergy_id}`
- ✅ Frontend Synergies page loads without errors
- ✅ No 404 errors in browser console
- ✅ Docker logs show `/stats` route handler being called (200 OK)

## Implementation Complete ✅

1. ✅ Implemented Quick Fix (Solution 2)
2. ✅ Tested and verified - all tests passing
3. ⏸️ Phase 2 (debug `specific_router`) - deferred, current solution works
4. ✅ Documented final solution in `SYNERGIES_API_FIX_EXECUTION_SUMMARY.md`

## Final Solution

**Applied:** Solution 2 - Move `/stats` to `router` and ensure correct order

**Result:** Route order corrected after full container restart. Endpoint now works correctly.

**Route Order (Final):**
```
1. /api/v1/synergies/stats        ✅ FIRST
2. /api/v1/synergies/list
3. /api/v1/synergies/{synergy_id}
4. /api/v1/synergies/{synergy_id}/feedback
```

