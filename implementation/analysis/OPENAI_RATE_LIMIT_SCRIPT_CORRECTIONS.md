# OpenAI Rate Limit Script Corrections - 2025 Documentation Review

**Date:** November 25, 2025  
**Status:** Corrected Based on 2025 Documentation  
**Purpose:** Document corrections made to rate limit checking script

---

## Key Finding from 2025 Documentation

### ⚠️ CRITICAL: Rate Limit Headers Only in Successful Responses

**Rate limit headers are ONLY included in successful API responses (200 OK), NOT in 429 error responses.**

This is a critical distinction that affects how we check rate limits:

- ✅ **Successful Response (200 OK)**: Contains all rate limit headers
- ❌ **Rate Limit Error (429)**: Does NOT contain rate limit headers

---

## Corrections Made

### 1. Updated `check_rate_limits_via_test_call()` Function

**Before:**
- Attempted to extract headers from 429 responses
- No retry logic for rate limit errors
- Assumed headers would be in error responses

**After:**
- ✅ Retry logic with exponential backoff (up to 5 attempts)
- ✅ Waits for rate limit to reset using `retry-after` header
- ✅ Only extracts headers from successful responses (200 OK)
- ✅ Clear logging about why we're waiting

**Key Changes:**
```python
# Now checks for 200 OK before extracting headers
if response.status_code == 200:
    # Extract headers (only available in successful responses)
    response_headers = response.headers
    # ... extract rate limit info ...

# Handles 429 with retry logic
elif response.status_code == 429:
    # Wait for rate limit to reset
    retry_after = response.headers.get('retry-after', 60)
    await asyncio.sleep(wait_time)
    # Retry to get successful response
```

### 2. Improved API Endpoint Error Handling

**Before:**
- Generic error messages for 401 errors
- No guidance on how to fix authentication issues

**After:**
- ✅ Specific guidance for 401 errors
- ✅ Instructions to get organization ID
- ✅ Suggests using headers method as alternative
- ✅ Better error messages

### 3. Updated Documentation

**Updated Files:**
- `scripts/check_openai_rate_limits.py` - Added docstring warnings
- `implementation/analysis/OPENAI_RATE_LIMIT_CHECKING_2025.md` - Added critical note

**Key Documentation Updates:**
- Added warning that headers are only in successful responses
- Explained retry logic and why it's necessary
- Documented the `retry-after` header usage

---

## How It Works Now

### Method 1: API Endpoint
1. Attempts to query `/v1/organization/projects/{project_id}/rate_limits`
2. Falls back to organization-level endpoint if project not found
3. Provides clear error messages if authentication fails

### Method 2: Response Headers (Recommended)
1. Makes a minimal test API call (5 tokens)
2. If successful (200 OK), extracts rate limit headers
3. If rate limited (429):
   - Reads `retry-after` header (or defaults to 60s)
   - Waits for rate limit to reset
   - Retries up to 5 times
   - Only extracts headers from successful response

---

## Usage Examples

### Check Rate Limits (Headers Method - Recommended)
```bash
docker-compose exec ai-automation-service bash -c \
  "cd /app && PYTHONPATH=/app/src python scripts/check_openai_rate_limits.py \
   --method headers --models gpt-4o-mini"
```

### Check Rate Limits (Both Methods)
```bash
docker-compose exec ai-automation-service bash -c \
  "cd /app && PYTHONPATH=/app/src python scripts/check_openai_rate_limits.py \
   --method both --models gpt-5.1 gpt-5.1-mini"
```

---

## Expected Behavior

### When Rate Limited (429)
1. Script detects 429 error
2. Logs warning: "Rate limit hit (429) for {model}"
3. Reads `retry-after` header (or uses 60s default)
4. Waits for specified time
5. Retries the API call
6. Once successful (200 OK), extracts headers

### When Successful (200 OK)
1. Script extracts all rate limit headers
2. Logs header values
3. Returns structured rate limit information
4. Saves results to `openai_rate_limits.json`

---

## Verification

The script has been:
- ✅ Updated with correct 2025 documentation understanding
- ✅ Tested for syntax errors (no linter errors)
- ✅ Deployed to Docker container
- ✅ Documented with clear warnings and instructions

---

## Next Steps

1. **Test the Script**: Run it when not rate limited to verify it extracts headers correctly
2. **Monitor Rate Limits**: Use the script periodically to track your actual limits
3. **Update Configuration**: Use discovered limits to configure `--rate-limit-rpm` in synthetic generation

---

## References

- OpenAI Rate Limits Guide: https://platform.openai.com/docs/guides/rate-limits/how-do-rate-limits-work
- OpenAI API Reference: https://platform.openai.com/docs/api-reference
- Rate Limits API: https://platform.openai.com/docs/api-reference/project-rate-limits/object

