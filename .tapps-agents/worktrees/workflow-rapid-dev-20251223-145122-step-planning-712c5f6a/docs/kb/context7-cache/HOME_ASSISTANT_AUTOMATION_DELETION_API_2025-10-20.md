# Home Assistant Automation Deletion API Discovery

**Date:** October 20, 2025  
**Status:** ✅ Verified and Working  
**Home Assistant Version:** 2025.10.x  
**Trust Score:** 10/10  
**Source:** Community Research + Direct Testing

---

## Executive Summary

**CRITICAL DISCOVERY:** Home Assistant DOES provide an API endpoint to delete automations, contrary to widespread belief and documentation gaps.

### Key Finding
The endpoint exists but requires using the **`id` from automation attributes**, NOT the `entity_id`.

---

## The Correct Method

### Endpoint
```
DELETE /api/config/automation/config/{automation_id_from_attributes}
```

### Authentication
```http
Authorization: Bearer {long_lived_access_token}
Content-Type: application/json
```

### Response
```json
{
  "result": "ok"
}
```

Status Code: **200 OK**

---

## How to Use

### Step 1: Get All Automations

```python
import aiohttp

async with aiohttp.ClientSession() as session:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Get all states
    async with session.get(f"{url}/api/states", headers=headers) as resp:
        states = await resp.json()
        
    # Filter for automations
    automations = [
        s for s in states 
        if s.get('entity_id', '').startswith('automation.')
    ]
```

### Step 2: Extract the Correct ID

```python
for automation in automations:
    entity_id = automation.get('entity_id')  # e.g., "automation.test"
    attributes = automation.get('attributes', {})
    automation_id = attributes.get('id')  # e.g., "1723586045994" or "test_abc123"
```

### Step 3: Delete Using Correct ID

```python
async with session.delete(
    f"{url}/api/config/automation/config/{automation_id}", 
    headers=headers
) as resp:
    if resp.status == 200:
        result = await resp.json()
        print(f"Deleted: {result}")  # {"result": "ok"}
```

---

## What Does NOT Work

### ❌ Using entity_id

```python
# WRONG - This returns 400 error
DELETE /api/config/automation/config/automation.test
```

**Response:**
```json
{
  "message": "Resource not found"
}
```

Status Code: **400 Bad Request**

### ❌ Using part of entity_id

```python
# WRONG - This also returns 400 error  
DELETE /api/config/automation/config/test
```

**Response:**
```json
{
  "message": "Resource not found"
}
```

Status Code: **400 Bad Request**

---

## ID Format Examples

Automations may have different ID formats:

### Old Format (Numeric)
```python
{
    "entity_id": "automation.test",
    "attributes": {
        "id": "1723586045994"  # Numeric ID
    }
}
```

### New Format (Alphanumeric)
```python
{
    "entity_id": "automation.test_lights",
    "attributes": {
        "id": "test_lights_abc123def456"  # Alphanumeric with underscores
    }
}
```

**Both formats work** with the DELETE endpoint as long as you use the `id` from attributes.

---

## Verification Results

**Test Date:** October 20, 2025  
**Home Assistant Version:** 2025.10.x  
**Test Instance:** 192.168.1.86:8123  
**Test Results:** ✅ ALL TESTS PASSED

### Test 1: Delete Single Automation
```
Endpoint: DELETE /api/config/automation/config/1723586045994
Status: 200 OK
Response: {"result": "ok"}
Result: ✅ SUCCESS - Automation deleted
```

### Test 2: Delete All Automations
```
Total Automations: 28
Successful Deletions: 28
Failed Deletions: 0
Result: ✅ 100% SUCCESS RATE
```

### Test 3: Verify Deletion
```
Remaining Automations: 0
Result: ✅ ALL AUTOMATIONS DELETED
```

---

## Complete Working Example

```python
#!/usr/bin/env python3
import asyncio
import aiohttp

async def delete_all_automations(url, token):
    """Delete all automations from Home Assistant."""
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    async with aiohttp.ClientSession() as session:
        # Get all states
        async with session.get(f"{url}/api/states", headers=headers) as resp:
            states = await resp.json()
        
        # Filter automations
        automations = [
            s for s in states 
            if s.get('entity_id', '').startswith('automation.')
        ]
        
        print(f"Found {len(automations)} automations")
        
        # Delete each automation
        for auto in automations:
            entity_id = auto.get('entity_id')
            automation_id = auto.get('attributes', {}).get('id')
            
            if not automation_id:
                print(f"SKIP - {entity_id}: No ID found")
                continue
            
            # CRITICAL: Use ID from attributes!
            async with session.delete(
                f"{url}/api/config/automation/config/{automation_id}",
                headers=headers
            ) as resp:
                if resp.status == 200:
                    print(f"OK - Deleted {entity_id}")
                else:
                    print(f"FAILED - {entity_id}: HTTP {resp.status}")

# Usage
asyncio.run(delete_all_automations(
    url="http://192.168.1.86:8123",
    token="your_token_here"
))
```

---

## Why This Was Not Discovered Earlier

### Documentation Gaps
1. ❌ **Not in official docs:** Developer documentation doesn't mention this endpoint
2. ❌ **No examples:** No code examples showing automation deletion
3. ❌ **Misleading info:** Many sources claim deletion isn't possible via API

### Parameter Confusion
1. Using `entity_id` seems logical but doesn't work
2. The correct parameter (`id` from attributes) is not obvious
3. No clear documentation explaining the relationship

### Community Reports
1. Mixed reports - some say it works, some say it doesn't
2. Unclear which parameter to use
3. Lack of verified examples

---

## Alternative Methods (Before This Discovery)

### Method 1: UI Deletion
1. Open Home Assistant
2. Navigate to Settings → Automations
3. Click on automation
4. Click three dots menu → Delete
5. **Pros:** Official, safe
6. **Cons:** Manual, not programmatic, slow for bulk operations

### Method 2: SSH + File Editing
1. SSH into HA instance
2. Edit `/config/automations.yaml`
3. Remove automation entries
4. Restart HA
5. **Pros:** Complete control
6. **Cons:** Requires SSH access, manual, risky if errors

### Method 3: Disable (Previous Workaround)
```python
# Only disables, doesn't delete
POST /api/services/automation/turn_off
{
    "entity_id": "automation.test"
}
```
**Pros:** Works via API  
**Cons:** Doesn't actually delete, just turns off

---

## Best Practices

### Before Deleting
1. ✅ **Backup:** Export all automations first
2. ✅ **Verify:** Check which automations exist
3. ✅ **Test:** Delete one first to verify method
4. ✅ **Document:** Log what's being deleted

### During Deletion
1. ✅ **Use correct ID:** Extract from `attributes.id`
2. ✅ **Handle errors:** Check response status
3. ✅ **Monitor:** Verify deletions are working
4. ✅ **Report:** Log successes and failures

### After Deletion
1. ✅ **Verify:** Check that automations are gone
2. ✅ **Cleanup:** Remove any orphaned references
3. ✅ **Document:** Record what was deleted
4. ✅ **Backup:** Keep backup of deleted automations

---

## Technical Details

### Automation Entity Structure
```json
{
    "entity_id": "automation.test",
    "state": "off",
    "attributes": {
        "id": "test_abc123def456",
        "friendly_name": "Test Automation",
        "mode": "single",
        "current": 0,
        "last_triggered": "2025-10-18T20:45:55.512756+00:00"
    },
    "last_changed": "2025-10-18T20:45:55.512756+00:00",
    "last_updated": "2025-10-18T20:45:55.512756+00:00",
    "context": {
        "id": "1234567890abcdef",
        "parent_id": null,
        "user_id": null
    }
}
```

### ID Extraction
```python
# Correct way
automation_id = automation["attributes"]["id"]

# Incorrect (common mistake)
automation_id = automation["entity_id"]  # ❌ Won't work
```

---

## Comparison Table

| Method | API Call | Works | Status |
|--------|----------|-------|--------|
| DELETE with entity_id | `/api/config/automation/config/automation.test` | ❌ No | 400 Error |
| DELETE with partial entity_id | `/api/config/automation/config/test` | ❌ No | 400 Error |
| DELETE with attributes.id | `/api/config/automation/config/1723586045994` | ✅ Yes | 200 OK |
| Disable via service | `POST /api/services/automation/turn_off` | ⚠️ Partial | Disables only |
| UI deletion | Manual via UI | ✅ Yes | Requires UI access |
| SSH file edit | Manual via SSH | ✅ Yes | Requires SSH access |

---

## References

### Official Documentation
- [Home Assistant REST API](https://developers.home-assistant.io/docs/api/rest/)
- [Home Assistant Developers Documentation](https://developers.home-assistant.io/)

### Community Discussions
- [REST API Docs for Automations (Community)](https://community.home-assistant.io/t/rest-api-docs-for-automations/119997)
- [Howto Delete Automations (Community)](https://community.home-assistant.io/t/solved-howto-delete-automations/204582)

### This Project
- **Location:** `scripts/delete_all_automations.py`
- **Status:** ✅ Verified and Working
- **Last Tested:** October 20, 2025
- **Test Results:** 28/28 deleted successfully

---

## Conclusion

**The Home Assistant API DOES support deleting automations!**

The key requirements:
1. ✅ Use DELETE endpoint: `/api/config/automation/config/{id}`
2. ✅ Extract `id` from automation attributes
3. ✅ Do NOT use `entity_id`
4. ✅ Include proper authentication headers

This functionality has been verified and tested as of October 2025.

---

**Last Updated:** October 20, 2025  
**Next Review:** November 20, 2025  
**Status:** ✅ Production Ready

