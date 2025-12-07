# Debug ID Endpoint Fix

## Issue
The user requested prompt context for debug_id `753229c4-38db-47e5-be6e-337fd33cf467` (Troubleshooting ID from UI), but the API was only accepting `conversation_id`, not `debug_id`.

## Root Cause
1. **Two Different IDs**: The UI shows `debug_id` (Troubleshooting ID), but the API endpoint only accepted `conversation_id`
2. **No Lookup Method**: No way to find conversation by `debug_id`
3. **Route Conflicts**: Attempted `/debug/{debug_id}/prompt` route but FastAPI routing didn't match correctly

## Fixes Applied

### 1. Added Database Lookup by Debug ID
- ✅ Added `get_conversation_by_debug_id()` in `conversation_persistence.py`
- ✅ Added `get_conversation_by_debug_id()` in `conversation_service.py`
- ✅ Both methods query database by `debug_id` column

### 2. Enhanced Existing Endpoint
- ✅ Modified `/{conversation_id}/debug/prompt` endpoint to accept both:
  - `conversation_id` (tries first)
  - `debug_id` (if UUID format and conversation_id lookup fails)
- ✅ Added automatic fallback: If ID looks like UUID (36 chars, 4 dashes) and not found as conversation_id, tries as debug_id

### 3. Added Dedicated Debug Endpoint (Backup)
- ✅ Created `/debug/{debug_id}/prompt` route (but routing may need adjustment)

## Current Status

**Code Changes**: ✅ Deployed
- All lookup methods added
- Endpoint enhanced to handle both ID types
- Service restarted

**Testing**: ⚠️ Needs Verification
- Endpoint returns 404 - conversation may not exist in database
- OR route matching issue preventing endpoint execution

## Next Steps

1. **Verify Conversation Exists**: The debug_id might be from:
   - A different database
   - An expired/deleted conversation
   - A cached value in UI

2. **Test with Valid Conversation**: Try with a known conversation_id that has a debug_id

3. **Alternative**: Use the UI's debug screen directly (which is working according to user)

## Usage

Once working, you can call:
```bash
# Using conversation_id (original)
GET /api/v1/conversations/{conversation_id}/debug/prompt?refresh_context=true

# Using debug_id (now supported - automatic fallback)
GET /api/v1/conversations/{debug_id}/debug/prompt?refresh_context=true
```

The endpoint will:
1. Try to find conversation by conversation_id
2. If not found and ID is UUID format, try as debug_id
3. Return full prompt breakdown

## Files Modified

- `services/ha-ai-agent-service/src/services/conversation_persistence.py`
- `services/ha-ai-agent-service/src/services/conversation_service.py`
- `services/ha-ai-agent-service/src/api/conversation_endpoints.py`

