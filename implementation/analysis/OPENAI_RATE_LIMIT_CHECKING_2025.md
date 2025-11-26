# OpenAI Rate Limit Checking - 2025 Guide

**Date:** November 25, 2025  
**Status:** Research Complete  
**Purpose:** How to check actual rate limits for your API key and models

---

## Summary

Yes, you can query OpenAI API to get your actual rate limits! There are **two methods**:

1. **API Endpoint** - Query rate limits programmatically
2. **Response Headers** - Monitor rate limits from API responses

---

## Method 1: Query Rate Limits via API Endpoint

### Endpoint

```
GET https://api.openai.com/v1/organization/projects/{project_id}/rate_limits
```

### Steps

1. **Get Your Project ID:**
   - Visit: https://platform.openai.com/projects
   - Find your project ID (or use default project)

2. **Make API Request:**
   ```bash
   curl -X GET https://api.openai.com/v1/organization/projects/{project_id}/rate_limits \
     -H "Authorization: Bearer YOUR_API_KEY"
   ```

3. **Response Format:**
   ```json
   {
     "object": "rate_limit",
     "rate_limits": [
       {
         "model": "gpt-5.1",
         "max_requests_per_1_minute": 5000,
         "max_tokens_per_1_minute": 500000
       },
       {
         "model": "gpt-5.1-mini",
         "max_requests_per_1_minute": 5000,
         "max_tokens_per_1_minute": 500000
       }
     ]
   }
   ```

---

## Method 2: Monitor Rate Limits from Response Headers

### ⚠️ IMPORTANT: Headers Only in Successful Responses

**Rate limit headers are ONLY included in successful API responses (200 OK), NOT in 429 error responses.**

To get rate limit information from headers:
1. Make a successful API call (200 OK)
2. Extract headers from the response
3. If you get a 429 error, wait for the rate limit to reset, then retry

### Headers Included in Successful API Responses

OpenAI includes rate limit information in response headers of successful responses:

- **`x-ratelimit-limit-requests`**: Maximum requests per minute allowed
- **`x-ratelimit-remaining-requests`**: Remaining requests before limit resets
- **`x-ratelimit-reset-requests`**: Time (in seconds) until request limit resets
- **`x-ratelimit-limit-tokens`**: Maximum tokens per minute allowed
- **`x-ratelimit-remaining-tokens`**: Remaining tokens before limit resets
- **`x-ratelimit-reset-tokens`**: Time (in seconds) until token limit resets

### Example Response Headers

```
x-ratelimit-limit-requests: 5000
x-ratelimit-remaining-requests: 4998
x-ratelimit-reset-requests: 45
x-ratelimit-limit-tokens: 500000
x-ratelimit-remaining-tokens: 485000
x-ratelimit-reset-tokens: 45
```

---

## 2025 Rate Limits (General Guidelines)

### Tier-Based Limits (September 2025 Update)

| Tier | RPM | TPM | Notes |
|------|-----|-----|-------|
| **Tier 1** | 5,000 | 500,000 | Default tier (was 30K TPM) |
| **Tier 2** | 10,000 | 1,000,000 | (was 150K TPM) |
| **Tier 3** | 20,000 | 2,000,000 | (was 800K TPM) |
| **Tier 4** | 40,000 | 4,000,000 | (was 2M TPM) |

**Note:** Actual limits vary by:
- Account tier
- Model type
- Usage history
- Billing status

**Always check your actual limits via API or headers!**

---

## Models We're Using

### Current Models (Phase 1)

1. **GPT-5.1** - Suggestion generation, YAML generation
2. **GPT-5.1-mini** - Classification, entity extraction, daily analysis, etc.

### Expected Limits (Typical Tier 1)

- **GPT-5.1**: 5,000 RPM, 500,000 TPM
- **GPT-5.1-mini**: 5,000 RPM, 500,000 TPM

---

## Implementation: Add Rate Limit Checking

### Option 1: Check Rate Limits on Startup

Add a function to check rate limits when service starts:

```python
async def check_openai_rate_limits(api_key: str, project_id: str | None = None) -> dict:
    """
    Check OpenAI rate limits for your API key.
    
    Args:
        api_key: OpenAI API key
        project_id: Optional project ID (uses default if None)
    
    Returns:
        Dictionary with rate limits per model
    """
    import httpx
    
    # Use default project if not specified
    if not project_id:
        project_id = "default"
    
    url = f"https://api.openai.com/v1/organization/projects/{project_id}/rate_limits"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
```

### Option 2: Monitor Response Headers

Extract rate limit info from API responses:

```python
async def get_rate_limit_info(response) -> dict:
    """
    Extract rate limit information from OpenAI API response headers.
    
    Returns:
        Dictionary with rate limit info
    """
    return {
        'limit_requests': response.headers.get('x-ratelimit-limit-requests'),
        'remaining_requests': response.headers.get('x-ratelimit-remaining-requests'),
        'reset_requests': response.headers.get('x-ratelimit-reset-requests'),
        'limit_tokens': response.headers.get('x-ratelimit-limit-tokens'),
        'remaining_tokens': response.headers.get('x-ratelimit-remaining-tokens'),
        'reset_tokens': response.headers.get('x-ratelimit-reset-tokens'),
    }
```

---

## Recommended Approach

### 1. Check Limits on Startup

Query rate limits when service starts to:
- Verify account tier
- Log actual limits
- Adjust rate limiting configuration

### 2. Monitor Headers During Runtime

Extract rate limit headers from responses to:
- Track remaining capacity
- Warn when approaching limits
- Adjust request rate dynamically

### 3. Update Configuration

Use discovered limits to:
- Set `rate_limit_rpm` in synthetic generation
- Configure delays between requests
- Optimize batch sizes

---

## Next Steps

1. **Create Rate Limit Checker Script** - Query limits on startup
2. **Add Header Monitoring** - Extract limits from responses
3. **Update Configuration** - Use actual limits instead of hardcoded values
4. **Add Logging** - Log rate limit status periodically

---

## References

- OpenAI Rate Limits API: https://platform.openai.com/docs/api-reference/project-rate-limits/object
- Rate Limits Guide: https://platform.openai.com/docs/guides/rate-limits/how-do-rate-limits-work
- Check Your Limits: https://platform.openai.com/account/limits

