# AI Automation Service - Action Plan (Simplified)

**Date:** January 2025  
**Status:** Ready for Execution  
**Approach:** Small, focused tasks to avoid connection issues

## Strategy: One Issue at a Time

Instead of processing everything at once, we'll tackle issues in small, focused chunks.

---

## Priority 1: Memory Leak Fixes (CRITICAL)

### Task 1.1: Fix Idempotency Store TTL Cleanup
**File:** `services/ai-automation-service/src/api/middlewares.py`  
**Lines:** ~21  
**Action:** Add background task to clean expired entries

**Simple Fix:**
```python
# Add to middlewares.py
import asyncio
from collections import OrderedDict

# Replace dict with OrderedDict for LRU
_idempotency_store: OrderedDict[str, tuple] = OrderedDict()
MAX_IDEMPOTENCY_SIZE = 1000
IDEMPOTENCY_TTL = 3600  # 1 hour

async def cleanup_idempotency_store():
    """Background task to clean expired idempotency entries"""
    while True:
        await asyncio.sleep(300)  # Run every 5 minutes
        current_time = time.time()
        expired_keys = [
            key for key, (timestamp, _) in _idempotency_store.items()
            if current_time - timestamp > IDEMPOTENCY_TTL
        ]
        for key in expired_keys:
            _idempotency_store.pop(key, None)
        
        # LRU eviction if over max size
        while len(_idempotency_store) > MAX_IDEMPOTENCY_SIZE:
            _idempotency_store.popitem(last=False)
```

**Estimated Time:** 15 minutes  
**Risk:** Low

---

### Task 1.2: Fix Rate Limiting TTL Cleanup
**File:** `services/ai-automation-service/src/api/middlewares.py`  
**Lines:** ~113-141  
**Action:** Add cleanup for rate limit buckets

**Simple Fix:**
```python
# Add cleanup task similar to idempotency
async def cleanup_rate_limit_buckets():
    """Background task to clean expired rate limit buckets"""
    while True:
        await asyncio.sleep(300)  # Run every 5 minutes
        current_time = time.time()
        for api_key in list(_rate_limit_buckets.keys()):
            bucket = _rate_limit_buckets[api_key]
            # Remove if last access > 1 hour ago
            if current_time - bucket.get('last_access', 0) > 3600:
                _rate_limit_buckets.pop(api_key, None)
```

**Estimated Time:** 15 minutes  
**Risk:** Low

---

## Priority 2: Test Coverage (HIGH)

### Task 2.1: Create Test Structure
**Action:** Set up basic test structure for critical paths

**Files to Create:**
- `services/ai-automation-service/tests/test_safety_validator.py`
- `services/ai-automation-service/tests/test_llm_integration.py`
- `services/ai-automation-service/tests/test_entity_extraction.py`

**Estimated Time:** 30 minutes  
**Risk:** Low

---

## Priority 3: Code Organization (MEDIUM)

### Task 3.1: Split Large Router File
**File:** `services/ai-automation-service/src/api/ask_ai_router.py` (7000+ lines)

**Approach:** Split into logical modules
- `ask_ai_router.py` - Main router (imports from submodules)
- `ask_ai_handlers/` - Directory for handlers
  - `chat_handlers.py`
  - `automation_handlers.py`
  - `entity_handlers.py`
  - etc.

**Estimated Time:** 2-3 hours  
**Risk:** Medium (requires careful refactoring)

---

## Execution Strategy

### Phase 1: Quick Wins (Today)
1. ✅ Task 1.1: Idempotency TTL cleanup
2. ✅ Task 1.2: Rate limiting TTL cleanup

### Phase 2: Testing (This Week)
3. ✅ Task 2.1: Test structure setup
4. Add tests for safety validator

### Phase 3: Refactoring (Next Week)
5. ✅ Task 3.1: Split router file (do in small chunks)

---

## How to Execute Safely

1. **One task at a time** - Don't try to do everything at once
2. **Test after each change** - Verify service still works
3. **Commit frequently** - Small, focused commits
4. **Use Simple Mode** - For code generation: `@simple-mode *fix {file} "{description}"`

---

## Next Steps

**Choose ONE task to start with:**
- [ ] Task 1.1: Fix idempotency store
- [ ] Task 1.2: Fix rate limiting cleanup
- [ ] Task 2.1: Create test structure
- [ ] Something else?

**Tell me which task you want to tackle first, and I'll help you implement it step-by-step.**

