# Automation Unique ID Fix Plan

**Date:** January 2025  
**Issue:** "Approve & Create" updates the same automation instead of creating new ones  
**Status:** 🔧 In Progress

---

## Problem Analysis

### Root Cause
When clicking "Approve & Create" multiple times, the system generates deterministic automation IDs based on the alias, causing Home Assistant to **update** existing automations instead of creating new ones.

### Current Behavior
1. AI generates YAML with `id` field (or doesn't)
2. If no `id`, fallback generates ID from alias: `alias.lower().replace(' ', '_').replace('-', '_')`
3. Same alias → Same ID → Home Assistant updates existing automation

### Example
- Alias: "Office Lights Flash" → ID: `office_lights_flash`
- Second approval with same alias → Same ID → **Updates** instead of creating new

---

## Solution

### Strategy 1: Always Generate Unique IDs (Recommended)
**Approach:** Append timestamp/UUID to base ID to ensure uniqueness

**Pros:**
- Simple and reliable
- No need to check existing automations
- Always creates new automations

**Cons:**
- IDs become longer
- Less human-readable

### Strategy 2: Check and Append Suffix
**Approach:** Check if ID exists, append numeric suffix if needed

**Pros:**
- Keeps IDs shorter and more readable
- Preserves base name

**Cons:**
- Requires API call to check existing automations
- More complex logic

---

## Implementation Plan

### Phase 1: Modify `create_automation` Method
**File:** `services/ai-automation-service/src/clients/ha_client.py`

**Changes:**
1. Add parameter `force_new: bool = True` to always create new automations
2. Generate unique ID by appending timestamp/UUID to base ID
3. Only use provided `automation_id` if explicitly updating (force_new=False)

### Phase 2: Update YAML Generation Prompt
**File:** `services/ai-automation-service/src/api/ask_ai_router.py`

**Changes:**
1. Update prompt to instruct AI to generate unique IDs (timestamp-based)
2. Provide examples with unique ID generation

### Phase 3: Handle Explicit Updates
**File:** `services/ai-automation-service/src/api/ask_ai_router.py` (approve endpoint)

**Changes:**
1. For re-deployments, allow explicit automation_id to be passed
2. Use `force_new=False` when updating existing automations

---

## Implementation Details

### Unique ID Generation
```python
import time
import uuid

def generate_unique_automation_id(base_id: str) -> str:
    """Generate unique automation ID with timestamp suffix"""
    timestamp = int(time.time())
    unique_suffix = uuid.uuid4().hex[:8]  # 8 chars for uniqueness
    return f"{base_id}_{timestamp}_{unique_suffix}"
```

### Modified create_automation Signature
```python
async def create_automation(
    self, 
    automation_yaml: str, 
    automation_id: Optional[str] = None,
    force_new: bool = True  # NEW: Always create new by default
) -> Dict[str, Any]:
```

---

## Testing Plan

1. **Test 1:** Create two automations with same alias → Should create two separate automations
2. **Test 2:** Explicit update (force_new=False) → Should update existing automation
3. **Test 3:** Verify IDs are unique and readable
4. **Test 4:** Check Home Assistant shows multiple automations

---

## Rollout

1. ✅ Create plan
2. ⏳ Implement unique ID generation
3. ⏳ Update YAML generation prompt
4. ⏳ Test with multiple approvals
5. ⏳ Verify in Home Assistant UI

