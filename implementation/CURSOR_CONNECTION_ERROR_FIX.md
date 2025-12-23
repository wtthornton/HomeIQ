# Cursor Connection Error Fix

**Date:** January 2026  
**Issue:** Connection errors (Request ID: 20d46c18-bc9b-4d45-992f-e1a924887362) when using TappsCodingAgents  
**Status:** ✅ **FIXED**

---

## Problem

TappsCodingAgents was attempting to connect to Cursor's Background Agent API (`https://api.cursor.com/v0`) even when:
1. The API is not publicly available
2. No API key is configured
3. The connection would fail

This caused user-facing connection error notifications in Cursor IDE, even though the framework gracefully falls back to file-based execution.

## Root Cause

1. **Hardcoded API Usage**: `CursorExecutor` was hardcoded to `use_api=True`
2. **Long Timeouts**: 30-second timeouts caused long delays before fallback
3. **Error Visibility**: Connection errors were not properly suppressed, causing user-facing notifications

## Solution

### 1. Conditional API Usage

**File:** `TappsCodingAgents/tapps_agents/workflow/cursor_executor.py`

**Change:**
- Only use Background Agent API if `CURSOR_API_KEY` environment variable is set
- Added `TAPPS_AGENTS_USE_BG_API` environment variable for explicit control (default: `true`)

```python
# Only use Background Agent API if CURSOR_API_KEY is set
# This prevents connection errors when the API is not available
use_api = os.getenv("CURSOR_API_KEY") is not None and os.getenv("TAPPS_AGENTS_USE_BG_API", "true").lower() == "true"
self.skill_invoker = SkillInvoker(
    project_root=self.project_root, use_api=use_api
)
```

### 2. Reduced Timeouts

**File:** `TappsCodingAgents/tapps_agents/workflow/background_agent_api.py`

**Changes:**
- Reduced timeout from 30 seconds to 5 seconds for faster failure detection
- Applied to all API methods: `list_agents()`, `trigger_agent()`, `get_agent_status()`

### 3. Improved Error Handling

**File:** `TappsCodingAgents/tapps_agents/workflow/background_agent_api.py`

**Changes:**
- Catch `ConnectionError` and `Timeout` exceptions explicitly
- Suppress error messages to prevent user-facing notifications
- Log only error type (not full error message) at debug level

```python
except (requests.RequestException, requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
    # Suppress these errors to prevent user-facing connection error notifications
    import logging
    logger = logging.getLogger(__name__)
    logger.debug(f"Background Agent API request failed (suppressed): {type(e).__name__}")
    return {
        "status": "pending",
        "job_id": f"local-{agent_id}",
        "message": "API not available, using file-based fallback",
        "fallback_mode": True,
    }
```

## Configuration

### Disable Background Agent API

**Option 1: Environment Variable**
```bash
# Disable API usage (use file-based fallback only)
$env:TAPPS_AGENTS_USE_BG_API = "false"
```

**Option 2: Don't Set CURSOR_API_KEY**
- If `CURSOR_API_KEY` is not set, API is automatically disabled
- This is the default behavior for most users

### Enable Background Agent API (Future)

When Cursor's Background Agent API becomes publicly available:

1. Set `CURSOR_API_KEY` environment variable:
   ```bash
   $env:CURSOR_API_KEY = "your-api-key-here"
   ```

2. Ensure `TAPPS_AGENTS_USE_BG_API` is `true` (default):
   ```bash
   $env:TAPPS_AGENTS_USE_BG_API = "true"
   ```

## Impact

✅ **Connection errors eliminated**: No more user-facing connection error notifications  
✅ **Faster fallback**: 5-second timeout instead of 30 seconds  
✅ **Automatic detection**: API disabled automatically when no API key is set  
✅ **Backward compatible**: Existing functionality unchanged, file-based fallback still works  

## Testing

**Verify fix:**
```bash
# Should not show connection errors
python -m tapps_agents.cli --version

# Should work without connection errors
python -m tapps_agents.cli enhancer enhance "Test prompt"
```

**Expected behavior:**
- ✅ No connection error notifications
- ✅ Commands execute successfully
- ✅ File-based fallback works automatically
- ✅ Debug logs show suppressed errors (if logging enabled)

## Files Modified

1. `TappsCodingAgents/tapps_agents/workflow/cursor_executor.py`
   - Conditional API usage based on `CURSOR_API_KEY`
   - Added `TAPPS_AGENTS_USE_BG_API` environment variable support

2. `TappsCodingAgents/tapps_agents/workflow/background_agent_api.py`
   - Reduced timeouts from 30s to 5s
   - Improved error handling to suppress connection errors
   - Applied to all API methods

## Related Issues

- Connection errors with Request ID: `20d46c18-bc9b-4d45-992f-e1a924887362`
- Background Agent API not publicly available
- User-facing error notifications for internal framework operations

---

**Status:** ✅ **FIXED** - Connection errors eliminated, framework works correctly with file-based fallback

