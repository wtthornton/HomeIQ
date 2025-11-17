# Ask AI Authentication Fix

**Date:** 2025-11-17  
**Issue:** Ask AI endpoint returning 401 Unauthorized errors  
**Status:** ✅ Fixed and Working (authentication working, OpenAI key configured)

## Issues Found and Fixed

### ✅ Fixed: Environment Variable Loading from .env

**Problem:**
- Service was not loading environment variables from `.env` file
- Only reading from `infrastructure/env.ai-automation` which had placeholder values
- OpenAI API key and other credentials in `.env` were not being used

**Solution:**
- Added `.env` to `env_file` list in `docker-compose.yml` for `ai-automation-service`
- Added environment variable mapping in `docker-compose.yml` to map `.env` variable names to service expected names:
  - `HA_URL=${LOCAL_HA_URL:-${HOME_ASSISTANT_URL:-...}}`
  - `HA_TOKEN=${LOCAL_HA_TOKEN:-${HOME_ASSISTANT_TOKEN:-...}}`
  - `OPENAI_API_KEY=${OPENAI_API_KEY:-}`
- Updated `infrastructure/env.ai-automation` to document that values come from `.env`

**Files Modified:**
- `docker-compose.yml` - Added `.env` to env_file and variable mappings
- `infrastructure/env.ai-automation` - Updated comments to reflect .env usage

### ✅ Fixed: Missing API Key Configuration

**Problem:**
- `infrastructure/env.ai-automation` was missing `AI_AUTOMATION_API_KEY` environment variable
- Service was rejecting all API requests with "Invalid API key" error
- All endpoints returning 401 Unauthorized

**Solution:**
- Added `AI_AUTOMATION_API_KEY=hs_P3rU9kQ2xZp6vL1fYc7bN4sTqD8mA0wR` to `infrastructure/env.ai-automation`
- Added `AI_AUTOMATION_ADMIN_API_KEY` for admin access
- Added `ENABLE_AUTHENTICATION=true` flag
- Restarted `ai-automation-service` to apply changes

**Files Modified:**
- `infrastructure/env.ai-automation` - Added authentication section

**Verification:**
- Authentication middleware now accepts requests with correct API key
- 401 errors resolved for authenticated requests

### ✅ Fixed: OpenAI API Key Configuration

**Solution Implemented:**
- OpenAI API key is now stored in `.env` file (not in `infrastructure/env.ai-automation`)
- `docker-compose.yml` maps it via: `OPENAI_API_KEY=${OPENAI_API_KEY:-}`
- This ensures the key persists and doesn't get lost when configuration files are updated

**Key Location:**
- **Primary:** `.env` file (root directory)
- **Why:** Prevents key loss during configuration updates
- **How:** docker-compose.yml loads from .env and passes to service

**Verification:**
- ✅ OpenAI client initialized successfully
- ✅ Ask AI endpoint working (Status: 201)
- ✅ Service can process natural language queries

### ⚠️ Non-Critical: MQTT Connection

**Problem:**
- MQTT connection failing with "Connection refused - not authorised"
- MQTT credentials in `infrastructure/env.ai-automation` may need updating

**Impact:**
- MQTT notifications won't work
- Does not affect Ask AI functionality (MQTT is optional for Ask AI)

**Solution (if needed):**
- Update MQTT credentials in `infrastructure/env.ai-automation`:
  ```
  MQTT_BROKER=your-broker-ip
  MQTT_USERNAME=your-username
  MQTT_PASSWORD=your-password
  ```

## Test Results

### Before Fix
```bash
POST /api/v1/ask-ai/query
Response: 401 Unauthorized
Error: "Invalid API key"
```

### After Fix (Authentication)
```bash
POST /api/v1/ask-ai/query
Response: 500 Internal Server Error
Error: OpenAI AuthenticationError (expected - needs valid OpenAI key)
```

**Status:** Authentication is working correctly. The 500 error is due to missing OpenAI key, not authentication.

## Next Steps

1. ✅ **Authentication Fixed** - API key authentication is working
2. ⚠️ **Configure OpenAI Key** - Set valid OpenAI API key to enable Ask AI functionality
3. ⚠️ **Optional: Fix MQTT** - Update MQTT credentials if notifications are needed

## Testing

Once OpenAI key is configured, test with:
```bash
curl -X POST http://localhost:8024/api/v1/ask-ai/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer hs_P3rU9kQ2xZp6vL1fYc7bN4sTqD8mA0wR" \
  -H "X-HomeIQ-API-Key: hs_P3rU9kQ2xZp6vL1fYc7bN4sTqD8mA0wR" \
  -d '{"query": "Make the office lights flash every 15 mins for 20 secs.", "user_id": "test-user"}'
```

Expected: 200 OK with automation suggestions

