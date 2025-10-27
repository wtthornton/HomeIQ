# Home Assistant Automation Management Scripts

## Overview

Scripts for managing Home Assistant automations via API.

---

## Scripts Available

### `delete_all_automations.py` ⭐
**Purpose:** Delete ALL automations from Home Assistant using the API

**Usage:**
```bash
python scripts/delete_all_automations.py
```

**Features:**
- Retrieves all automation entities
- Shows what will be deleted
- Requires confirmation ("DELETE ALL")
- Uses correct API endpoint and parameter format
- Reports success/failure for each deletion

**Requirements:**
- `.env` file with `HA_HTTP_URL` and `HA_TOKEN`
- Long-lived access token with appropriate permissions

---

## Documentation

### `HOME_ASSISTANT_AUTOMATION_API_RESEARCH.md`
**Purpose:** Comprehensive research findings on automation API

**Contents:**
- Critical discovery: API deletion IS possible
- Correct endpoint and parameter format
- Verification results with actual test data
- What works vs. what doesn't
- Best practices and recommendations

---

## Key Discovery (October 2025)

### ✅ API Deletion EXISTS!

**Correct Method:**
```
DELETE /api/config/automation/config/{id-from-attributes}
```

**Critical Finding:**
- Use the `id` from automation's `attributes` field
- NOT the `entity_id`
- Tested and verified on Home Assistant 2025.10.x

**Example:**
```python
automation = {
    "entity_id": "automation.test",
    "attributes": {
        "id": "test_abc123"  # ← Use THIS!
    }
}

# This works:
DELETE /api/config/automation/config/test_abc123  # ✅ 200 OK

# These don't work:
DELETE /api/config/automation/config/automation.test  # ❌ 400 Error
DELETE /api/config/automation/config/test            # ❌ 400 Error
```

---

## Test Results

**Date:** October 20, 2025  
**Home Assistant Version:** 2025.10.x  
**Status:** ✅ SUCCESS

**Results:**
- Connected to Home Assistant at `192.168.1.86:8123`
- Found 28 automations
- Disabled 28 automations initially (wrong method)
- Deleted 27 automations via API (correct method - 1 already deleted)
- Verified: 0 automations remaining

**Final Status:**
```
Remaining automations: 0
*** ALL AUTOMATIONS DELETED SUCCESSFULLY! ***
```

---

## Configuration

### `.env` File Required
```bash
# Home Assistant Configuration
HA_HTTP_URL=http://192.168.1.86:8123
HA_TOKEN=your_long_lived_access_token_here
```

### How to Get Token
1. Open Home Assistant
2. Go to Profile → Security
3. Scroll to "Long-Lived Access Tokens"
4. Click "Create Token"
5. Copy token to `.env` file

---

## Why This Matters

### Previous Understanding (Wrong)
- Many online sources claimed no API deletion exists
- Only disable/enable was thought possible
- Manual file editing required for deletion

### Current Reality (Correct)
- API deletion DOES exist
- Requires using correct parameter (`id` from attributes)
- Not well documented
- Works reliably when used correctly

---

## Files

- `delete_all_automations.py` - Main script to delete all automations
- `HOME_ASSISTANT_AUTOMATION_API_RESEARCH.md` - Detailed research findings
- `README.md` - This file

---

## References

- [Home Assistant API Documentation](https://developers.home-assistant.io/docs/api/rest/)
- [Community Discussion on Automation API](https://community.home-assistant.io/t/rest-api-docs-for-automations/119997)
- [Context7 Home Assistant Docs](https://context7.com/home-assistant/core)

---

**Last Updated:** October 20, 2025  
**Status:** ✅ Verified and Working

