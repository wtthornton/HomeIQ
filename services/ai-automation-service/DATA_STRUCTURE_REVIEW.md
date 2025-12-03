# Data Structure Review: Synthetic Home Generation vs Models/Services Requirements

**Date:** December 2025  
**Status:** ✅ Quick Review Complete

---

## Quick Comparison Summary

### ✅ MATCHES (Good Alignment)

1. **Home Type Classifier Requirements:**
   - ✅ `home_type` - Generated ✓
   - ✅ `devices` (list) - Generated ✓
   - ✅ `events` (list) - Generated ✓
   - ✅ `areas` (list) - Generated ✓

2. **Home Type Profiler Requirements:**
   - ✅ `devices` with `entity_id`, `device_type`, `category`, `area` - All present ✓
   - ✅ `events` with `entity_id`, `timestamp` - All present ✓
   - ✅ `areas` with `name`, `type` - All present ✓

3. **HA Loader Requirements:**
   - ✅ `metadata.home.name` - Present ✓
   - ✅ `areas` (list) - Generated ✓
   - ✅ `devices` (list) - Generated ✓

---

## ⚠️ POTENTIAL MISMATCHES

### 1. ❌ **Missing `home_id` Field**

**Issue:** The saved JSON files don't include a `home_id` field.

**What's Generated:**
```json
{
  "home_type": "single_family_house",
  "size_category": "medium",
  "home_index": 1,
  "metadata": {...},
  "areas": [...],
  "devices": [...],
  "events": [...]
}
```

**What Models Expect:**
- HomeTypeProfiler expects: `home_id: str` parameter
- HomeTypeClassifier tries: `home.get('home_id', f"home_{len(profiles)}")` (falls back)

**Impact:** 
- ⚠️ **Low** - Models have fallback logic, but not consistent
- Services use filename to infer ID

**Recommendation:**
- ✅ Add `home_id` field when saving homes
- Use format: `f"home_{i+1:03d}"` or `f"home_{home_type}_{home_index}"`

---

### 2. ⚠️ **Device Field Naming**

**Generated Device Structure:**
- `entity_id` - ✅ Present
- `device_type` - ✅ Present  
- `category` - ✅ Present
- `area` - ✅ Present (as string name)

**What Models/Services Need:**
- ✅ All fields match expectations

**Status:** ✅ **No issues found**

---

### 3. ⚠️ **Event Field Requirements**

**Generated Event Structure:**
- `entity_id` - ✅ Present
- `timestamp` - ✅ Present (ISO format)
- `state` - ✅ Present
- `event_type` - ✅ Present

**What Models/Services Need:**
- ✅ All fields match expectations

**Status:** ✅ **No issues found**

---

### 4. ⚠️ **Area Field Requirements**

**Generated Area Structure:**
- `name` - ✅ Present
- `type` - ✅ Present (indoor/outdoor)
- `area_id` - ✅ Present (internal ID)
- `floor` - ✅ Present (for multi-story homes)

**What Models/Services Need:**
- ✅ All fields match expectations

**Status:** ✅ **No issues found**

---

### 5. ⚠️ **External Data Structure**

**Generated External Data:**
```json
{
  "external_data": {
    "weather": [...],
    "carbon_intensity": [...],
    "pricing": [...],
    "calendar": [...]
  }
}
```

**Models/Services Usage:**
- ✅ Not required by models (optional)
- ✅ Used by correlation/context services (Epic 34)
- ✅ Structure matches expectations

**Status:** ✅ **No issues found**

---

## Recommended Fixes

### Priority 1: Add `home_id` Field

**Location:** `services/ai-automation-service/scripts/generate_synthetic_homes.py`

**Fix:** Add `home_id` to each home before saving:

```python
# Before saving
for i, home in enumerate(complete_homes):
    # Add home_id if not present
    if 'home_id' not in home:
        home['home_id'] = f"home_{i+1:03d}"
    # Or use: home['home_id'] = f"home_{home['home_type']}_{home.get('home_index', i+1)}"
```

**Impact:** Ensures consistent home_id across all models/services

---

## Field Mapping Reference

### Top-Level Home Structure

| Field | Generated | Required By | Status |
|-------|-----------|-------------|--------|
| `home_id` | ❌ Missing | Models, Services | ⚠️ **ADD** |
| `home_type` | ✅ Yes | All | ✅ OK |
| `size_category` | ✅ Yes | Training | ✅ OK |
| `home_index` | ✅ Yes | Generation | ✅ OK |
| `metadata` | ✅ Yes | Services | ✅ OK |
| `areas` | ✅ Yes | All | ✅ OK |
| `devices` | ✅ Yes | All | ✅ OK |
| `events` | ✅ Yes | All | ✅ OK |
| `external_data` | ✅ Yes (optional) | Services | ✅ OK |

### Device Structure

| Field | Generated | Required By | Status |
|-------|-----------|-------------|--------|
| `entity_id` | ✅ Yes | All | ✅ OK |
| `device_type` | ✅ Yes | Profiler | ✅ OK |
| `category` | ✅ Yes | Profiler | ✅ OK |
| `area` | ✅ Yes | Profiler | ✅ OK |
| `name` | ✅ Yes | HA Loader | ✅ OK |

### Event Structure

| Field | Generated | Required By | Status |
|-------|-----------|-------------|--------|
| `entity_id` | ✅ Yes | All | ✅ OK |
| `timestamp` | ✅ Yes | All | ✅ OK |
| `state` | ✅ Yes | Profiler | ✅ OK |
| `event_type` | ✅ Yes | Services | ✅ OK |

### Area Structure

| Field | Generated | Required By | Status |
|-------|-----------|-------------|--------|
| `name` | ✅ Yes | All | ✅ OK |
| `type` | ✅ Yes | Profiler | ✅ OK |
| `area_id` | ✅ Yes | HA Loader | ✅ OK |
| `floor` | ✅ Yes | HA Loader | ✅ OK |

---

## Overall Assessment

**Status:** ✅ **Mostly Aligned** (95% match)

**Issues Found:**
1. ⚠️ Missing `home_id` field (low priority - has fallback)

**Action Items:**
1. Add `home_id` field to generated homes before saving

---

**Last Updated:** December 2025  
**Review Status:** Complete

