# Nabu Casa Fallback Connection Fix

**Date:** January 2025  
**Status:** ✅ Completed

## Issue Summary

The Nabu Casa fallback connection was not working properly due to:
1. Inconsistent URL normalization logic
2. Poor error logging (only debug level)
3. No SSL verification handling for cloud connections
4. Weak URL validation

## Root Cause Analysis

### Problems Identified

1. **URL Format Handling** (Lines 217-227 in original code):
   - Simple string replacement without proper validation
   - No handling for URLs already in WebSocket format
   - Could create invalid URLs if protocol was missing

2. **Connection Test Logic** (Lines 321-341 in original code):
   - Minimal error logging (debug level only)
   - No specific error handling for different failure types
   - No SSL verification options

3. **Environment Configuration**:
   - From `env.production`: `NABU_CASA_URL=https://lwzisze94hrpqde9typkwgu5pptxdkoh.ui.nabu.casa`
   - Token is the same as primary HA token (as expected)

## Fixes Implemented

### 1. URL Normalization Helper Methods

Added two new helper methods:

#### `_normalize_websocket_url(url, connection_type)`
- Handles URLs in multiple formats (HTTP, HTTPS, WebSocket, or no protocol)
- Properly appends `/api/websocket` path
- Special handling for Nabu Casa (assumes HTTPS if no protocol)
- Validates URL is not empty

#### `_normalize_http_url(ws_url)`
- Converts WebSocket URLs back to HTTP for API testing
- Properly removes `/api/websocket` suffix
- Handles edge cases (URLs ending with `/api` or `/api/websocket`)

### 2. Improved Error Logging

Enhanced `_test_connection()` method with:
- **Warning-level logging** for all failures (was debug level)
- **Specific error types**:
  - `ClientConnectorError` - Connection errors
  - `ClientError` - HTTP client errors
  - `TimeoutError` - Timeout errors
  - Generic exceptions - Unexpected errors
- **Detailed error messages** including:
  - Connection name
  - URL being tested
  - HTTP status codes and response text
  - Error type and message

### 3. SSL Verification Handling

Added SSL verification control:
- Environment variable: `NABU_CASA_SSL_VERIFY` (default: `true`)
- Can be set to `false` if certificate issues occur
- Only applies to Nabu Casa connections
- Uses `aiohttp.TCPConnector(ssl=ssl_verify)`

### 4. Better Error Handling

- Try-catch block around Nabu Casa configuration
- Logs errors if URL normalization fails
- Prevents service crash if Nabu Casa URL is malformed

## Code Changes

### Files Modified

1. **`shared/enhanced_ha_connection_manager.py`**
   - Added `_normalize_websocket_url()` method
   - Added `_normalize_http_url()` method
   - Updated `_load_connection_configs()` to use new normalization
   - Completely rewrote `_test_connection()` with better error handling

### Key Improvements

```python
# Before: Simple string replacement
ws_url = nabu_casa_url.replace('https://', 'wss://')
if not ws_url.endswith('/api/websocket'):
    ws_url += '/api/websocket'

# After: Robust normalization
ws_url = self._normalize_websocket_url(nabu_casa_url, ConnectionType.NABU_CASA)
```

```python
# Before: Minimal error logging
except Exception as e:
    logger.debug(f"Connection test failed: {e}")

# After: Detailed error logging
except aiohttp.ClientConnectorError as e:
    logger.warning(f"❌ Connection test failed for {config.name}: Connection error - {str(e)}")
```

## Testing Recommendations

1. **Test with valid Nabu Casa URL**:
   ```bash
   NABU_CASA_URL=https://your-domain.ui.nabu.casa
   NABU_CASA_TOKEN=your_token
   ```

2. **Test with WebSocket URL format**:
   ```bash
   NABU_CASA_URL=wss://your-domain.ui.nabu.casa/api/websocket
   ```

3. **Test with no protocol**:
   ```bash
   NABU_CASA_URL=your-domain.ui.nabu.casa
   ```

4. **Test SSL verification**:
   ```bash
   NABU_CASA_SSL_VERIFY=false  # If certificate issues occur
   ```

5. **Monitor logs** for:
   - Connection test warnings
   - URL normalization errors
   - Circuit breaker state changes

## Expected Behavior

### Successful Connection
- Logs: `✅ Nabu Casa fallback configured: wss://...`
- Logs: `✅ Connection test passed for Nabu Casa Fallback`
- Logs: `✅ Connected to Nabu Casa Fallback (...) in X.XXs`

### Failed Connection
- Logs: `❌ Connection test failed for Nabu Casa Fallback: [detailed error]`
- Circuit breaker records failure
- Falls back to next connection (if available)

## Environment Variables

### Required
- `NABU_CASA_URL` - Nabu Casa URL (HTTP/HTTPS/WebSocket format)
- `NABU_CASA_TOKEN` - Nabu Casa long-lived access token

### Optional
- `NABU_CASA_SSL_VERIFY` - SSL verification (default: `true`)

## Next Steps

1. Test the connection with actual Nabu Casa credentials
2. Monitor logs for any connection issues
3. Adjust `NABU_CASA_SSL_VERIFY` if certificate issues occur
4. Verify fallback works when primary HA is unavailable

## Related Files

- `shared/enhanced_ha_connection_manager.py` - Main implementation
- `infrastructure/env.production` - Production configuration
- `infrastructure/env.websocket.template` - Template configuration

