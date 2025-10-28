# Test Button Action Plan

**Date:** January 2025  
**Status:** Ready for Implementation

---

## Summary

Instead of manually debugging by clicking the Test button repeatedly, we need a systematic approach:

1. ✅ Automated test script created
2. 🔄 Fix entity mapping in production code
3. 🔄 Run automated tests to validate
4. 🔄 Deploy when tests pass

---

## The Core Issue

The Test button fails because:
- Entity mapping is not being passed to YAML generator
- YAML generator uses `"office"` instead of `"light.office"`
- HA rejects invalid entity IDs

---

## Solution

### 1. Fix Entity Mapping (Already Done)
- Extract entity names from dict format
- Map entities using EntityValidator
- Pass validated_entities to test_suggestion

### 2. Automated Testing
- Created `tests/unit/test_ask_ai_test_button_automated.py`
- Tests entity extraction, mapping, and YAML generation
- Validates that entity IDs are full format

### 3. Next Steps

**Option A: Fix in Production Code**
- The entity mapping fix is already deployed
- Need to verify it works with the automated test

**Option B: Simplified Test**
- Create a simpler test that doesn't require full HA integration
- Just validate the YAML generation with proper entity IDs

---

## Running the Test

```bash
cd C:\cursor\ha-ingestor
python -m pytest tests/unit/test_ask_ai_test_button_automated.py -v
```

---

## Current Status

- ✅ Test script created
- ✅ Entity name extraction fixed in code
- ⏳ Need to run tests to validate
- ⏳ Deploy after tests pass

