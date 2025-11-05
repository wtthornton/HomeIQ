# Lessons Learned: Nginx Query Parameter Handling

**Date:** January 6, 2025  
**Issue:** Device entities popup showing 0 entities instead of 4  
**Root Cause:** Nginx stripping query parameters in proxy_pass configuration

## Problem

When proxying requests through nginx to backend services, query parameters were being lost, causing API endpoints to return unfiltered data.

### Symptoms
- Frontend requests: `GET /api/entities?device_id=xxx&limit=5`
- Backend received: `GET /api/entities` (no query params)
- Result: API returned 100 unfiltered entities instead of 4 filtered ones

## Root Cause Analysis

### Nginx `proxy_pass` Behavior

When using `proxy_pass` with a URI path, nginx behavior depends on the configuration:

**Problematic Pattern:**
```nginx
location /api/entities {
    proxy_pass http://backend/api/entities;  # ❌ Path specified
}
```

**Why it fails:**
- When `proxy_pass` includes a path (`/api/entities`), nginx replaces the entire location path
- Query parameters may be lost depending on nginx version and configuration
- The request URI is reconstructed, potentially without query string

**Working Pattern:**
```nginx
location /api/entities {
    proxy_pass http://backend$request_uri;  # ✅ Preserves full URI
}
```

**Why it works:**
- `$request_uri` contains the full original request URI including query string
- No path replacement occurs
- Query parameters are preserved exactly as sent

## Solution

### Before (Broken)
```nginx
location /api/entities {
    proxy_pass http://data_api/api/entities$is_args$args;
    # ... other settings
}
```

### After (Fixed)
```nginx
location /api/entities {
    proxy_pass http://data_api$request_uri;
    # ... other settings
}
```

## Key Learnings

### 1. Always Preserve Query Parameters
When proxying API requests, always use `$request_uri` to preserve the complete original request:
- Query parameters
- Path parameters
- Original request structure

### 2. Test Through Proxy, Not Just Direct
- Direct API calls may work: `curl http://backend:8006/api/entities?device_id=xxx`
- Proxied calls may fail: `curl http://frontend:3000/api/entities?device_id=xxx`
- **Always test the actual user path** (through nginx)

### 3. Debug Proxy Configuration
Add logging to verify what reaches the backend:
```nginx
access_log /var/log/nginx/access.log combined;
error_log /var/log/nginx/error.log debug;
```

Check backend logs to confirm query parameters are received:
```python
logger.info(f"Raw query params: {request.query_params}")
logger.info(f"Parsed device_id: {device_id}")
```

### 4. Nginx Variables Reference
- `$request_uri` - Full original request URI (path + query)
- `$uri` - Requested URI without query string
- `$args` - Query string only
- `$is_args` - "?" if query string exists, empty otherwise

### 5. FastAPI Query Parameter Handling
FastAPI's `Query()` parameters work correctly when:
- Query string is present in the request
- Parameters are properly URL-encoded
- No proxy middleware strips them

## Best Practices

### For Nginx Proxy Configuration

1. **Use `$request_uri` for API endpoints:**
   ```nginx
   location /api/ {
       proxy_pass http://backend$request_uri;
   }
   ```

2. **Use `$is_args$args` only when you need control:**
   ```nginx
   location /api/ {
       set $backend "http://backend";
       proxy_pass $backend/api$is_args$args;
   }
   ```

3. **Always test both paths:**
   - Direct backend access
   - Through nginx proxy

4. **Add debugging:**
   - Log access patterns
   - Verify query parameters in backend logs
   - Use browser dev tools to inspect requests

### For Backend API Development

1. **Log raw query parameters:**
   ```python
   logger.debug(f"Raw query: {request.query_params}")
   ```

2. **Handle missing parameters gracefully:**
   ```python
   device_id: Optional[str] = Query(None)
   if not device_id:
       logger.warning("device_id missing from query params")
   ```

3. **Validate proxy configuration:**
   - Test with query parameters
   - Test with special characters (URL-encoded)
   - Test with multiple parameters

## Prevention Checklist

- [ ] Nginx proxy uses `$request_uri` for API endpoints
- [ ] Test API calls through proxy (not just direct)
- [ ] Backend logs show query parameters correctly
- [ ] Frontend dev tools show query string in requests
- [ ] Error handling for missing query parameters
- [ ] Integration tests include proxy path

## Related Issues

- Initial fix attempted `$is_args$args` but still failed
- Frontend was correctly sending query parameters
- Backend FastAPI code was correct
- Issue was purely in nginx configuration

## References

- [Nginx proxy_pass documentation](http://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_pass)
- [Nginx variables documentation](http://nginx.org/en/docs/varindex.html)
- FastAPI Query Parameters: https://fastapi.tiangolo.com/tutorial/query-params/

