# Automation ID Generation

**Last Updated:** January 20, 2025  
**Status:** ✅ Production Ready

---

## Overview

The AI Automation Service generates unique automation IDs to ensure that each approval creates a **new automation** in Home Assistant, rather than updating an existing one. This prevents accidental overwrites when users approve multiple suggestions with similar names.

---

## ID Generation Strategy

### Default Behavior: Create New Automation

By default, each approval/deployment creates a new automation with a unique ID:

**Format:** `{base_id}_{timestamp}_{uuid_8chars}`

**Example:**
```
Base ID: "office_lights_flash"
Unique ID: "office_lights_flash_1737123456_a1b2c3d4"
```

### ID Generation Logic

1. **Extract Base ID:**
   - From YAML `id` field (if present)
   - From alias (if no `id` in YAML): `alias.lower().replace(' ', '_').replace('-', '_')`
   - From explicit `automation_id` parameter (if provided)

2. **Append Unique Suffix:**
   - Timestamp: Unix timestamp (seconds since epoch)
   - UUID: First 8 characters of UUID4 hex string
   - Format: `{base_id}_{timestamp}_{uuid_8chars}`

3. **Result:**
   - Always unique (timestamp + UUID ensures uniqueness)
   - Human-readable (base name preserved)
   - Home Assistant compatible (valid entity ID format)

---

## Implementation

### Code Location

**File:** `services/ai-automation-service/src/clients/ha_client.py`  
**Method:** `create_automation()`

### Parameters

```python
async def create_automation(
    automation_yaml: str,
    automation_id: Optional[str] = None,
    force_new: bool = True  # Default: always create new
) -> Dict[str, Any]:
```

### Behavior

- **`force_new=True` (default):** Always generates unique ID (creates new automation)
- **`force_new=False`:** Uses base ID as-is (updates existing automation)

---

## Use Cases

### 1. New Automation Creation (Default)

**Scenario:** User clicks "Approve & Create" on a suggestion

**Flow:**
```
User clicks "Approve & Create"
    ↓
YAML generated (may have base ID or alias)
    ↓
create_automation(yaml, force_new=True)  # Default
    ↓
Unique ID generated: "office_lights_1737123456_a1b2c3d4"
    ↓
New automation created in Home Assistant ✅
```

### 2. Multiple Approvals with Same Name

**Scenario:** User approves two suggestions with similar aliases

**Result:**
```
Approval 1: "office_lights_flash_1737123456_a1b2c3d4" → Creates automation ✅
Approval 2: "office_lights_flash_1737123457_b2c3d4e5" → Creates NEW automation ✅
```

**Before Fix:**
```
Approval 1: "office_lights_flash" → Creates automation
Approval 2: "office_lights_flash" → UPDATES same automation ❌
```

### 3. Re-deployment (Update Existing)

**Scenario:** User re-deploys an existing automation

**Flow:**
```
User re-deploys existing automation
    ↓
create_automation(yaml, automation_id="automation.existing_id", force_new=False)
    ↓
Uses existing ID as-is
    ↓
Existing automation updated in Home Assistant ✅
```

---

## API Endpoints

### Approve Suggestion

**Endpoint:** `POST /api/v1/ask-ai/query/{query_id}/suggestions/{suggestion_id}/approve`

**Behavior:** Always creates new automation (uses `force_new=True`)

**Response:**
```json
{
  "automation_id": "automation.office_lights_flash_1737123456_a1b2c3d4",
  "status": "approved"
}
```

### Deploy Automation (V2)

**Endpoint:** `POST /api/v2/automations/deploy`

**Behavior:** Always creates new automation (uses `force_new=True`)

**Response:**
```json
{
  "automation_id": "automation.office_lights_1737123456_a1b2c3d4",
  "success": true
}
```

### Re-deploy (Conversational Router)

**Endpoint:** `POST /api/v1/suggestions/{suggestion_id}/approve`

**Behavior:** Updates existing automation when `is_redeploy=True` (uses `force_new=False`)

---

## Benefits

### 1. Prevents Accidental Overwrites
- Multiple approvals with similar names create separate automations
- Users can experiment without losing previous automations

### 2. Maintains History
- Each approval creates a distinct automation
- Users can compare different versions

### 3. Human-Readable IDs
- Base name preserved for easy identification
- Timestamp provides chronological ordering
- UUID ensures uniqueness

### 4. Backward Compatible
- Default behavior ensures new automations are always created
- Re-deployments can still update existing automations when needed

---

## Technical Details

### ID Format Validation

Home Assistant requires automation IDs to:
- Be valid Python identifiers (alphanumeric + underscore)
- Not start with a number
- Be unique within the system

Our format satisfies all requirements:
- Base ID: Valid identifier (from alias or YAML)
- Timestamp: Numeric (valid)
- UUID: Hexadecimal (valid)
- Separator: Underscore (valid)

### Collision Prevention

**Probability of collision:** Effectively zero
- Timestamp: Changes every second
- UUID: 8 hex characters = 4.3 billion possibilities
- Combined: 4.3 billion × seconds = effectively infinite

### Performance Impact

**Minimal:**
- ID generation: <1ms (timestamp + UUID generation)
- No database lookups required
- No API calls to check existing automations

---

## Migration Notes

### Existing Automations

- **No migration required:** Existing automations are unaffected
- **New behavior:** Only applies to new approvals/deployments
- **Re-deployments:** Can still update existing automations

### Breaking Changes

**None:** The change is backward compatible:
- Default behavior creates new automations (safe)
- Re-deployments explicitly use `force_new=False` (preserves update behavior)

---

## Related Documentation

- [API Reference - Approve Endpoint](../api/API_REFERENCE.md#post-apiv1ask-aiqueryquery_idsuggestionssuggestion_idapprove)
- [AI Automation System Architecture](./ai-automation-system.md)
- [Home Assistant Client Implementation](../../services/ai-automation-service/src/clients/ha_client.py)

