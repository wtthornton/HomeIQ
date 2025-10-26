# Home Assistant Connection Manager Fix Summary

**Date:** October 25, 2025  
**Status:** Partial Implementation - Debugging Required

## 🎯 **Objective**
Fix the Home Assistant WebSocket connection issue causing ingestion count to be 0, and implement a unified connection strategy with automatic fallback from primary HA to Nabu Casa.

---

## ✅ **Successfully Completed**

### 1. **Unified Connection Strategy** ✅
- **File:** `shared/ha_connection_manager.py`
- **Changes:**
  - Fixed WebSocket API compatibility (`extra_headers` → `additional_headers`)
  - Added comprehensive error handling with specific exception types
  - Implemented retry mechanism with exponential backoff for cloud connections
  - Added SSL context support for Docker containers
  - Added detailed logging for debugging

### 2. **Environment Configuration** ✅
- **File:** `docker-compose.yml`
- **Changes:**
  - Updated `websocket-ingestion` service to use `.env` file
  - Added `DOCKER_CONTAINER=true` environment variable
  - Consolidated HA environment variables

### 3. **Local Testing** ✅
- **File:** `test_nabu_casa_connection.py`
- **Result:** **Nabu Casa connection works perfectly** when tested locally
- **Proof:** HTTP and WebSocket authentication successful with provided tokens

### 4. **Services Updated** ✅
- `services/websocket-ingestion/src/main.py` - Uses unified connection manager
- `services/calendar-service/src/main.py` - Uses unified connection manager
- `services/device-intelligence-service/src/core/discovery_service.py` - Uses unified connection manager

---

## ❌ **Remaining Issues**

### 1. **WebSocket Connection Failing in Docker Container** ❌
**Symptom:** No detailed logging appears, suggesting connection fails before authentication

**Evidence:**
```
❌ Connection failed for Primary HA: Connection error: [Errno 111] Connect call failed ('192.168.1.86', 8123)
❌ Authentication failed for Nabu Casa Fallback: Authentication failed: Unknown error
❌ Connection failed for Local HA Fallback: Connection error: Multiple exceptions
```

**Expected Logs (Not Appearing):**
- "🔌 Testing WebSocket connection to..."
- "✅ WebSocket connected to..."
- "⏳ Waiting for auth_required message..."
- "📨 Received auth response..."

**Root Cause Analysis:**
The absence of these logs suggests the WebSocket connection is failing at the connection level (before our code runs), likely due to:
1. **SSL Certificate Issues:** Docker containers may not trust Nabu Casa's SSL certificates
2. **Network Configuration:** Docker networking may be blocking outbound HTTPS/WSS connections
3. **WebSocket Library Issue:** The `websockets` library may have different behavior in Alpine Linux containers

### 2. **InfluxDB Authentication** ❌
**Symptom:** Unauthorized access errors

```
Failed to execute InfluxDB query: (401)
Reason: Unauthorized
HTTP response body: b'{"code":"unauthorized","message":"unauthorized access"}'
```

**Action Required:** Update InfluxDB token in `.env` file

---

## 🔍 **Key Findings from Context7 Research**

### WebSocket SSL/TLS in Docker Containers
From `/python-websockets/websockets` documentation:

1. **SSL Context Required for WSS:**
   ```python
   ssl_context = ssl.create_default_context()
   # For self-signed or custom certificates:
   ssl_context.check_hostname = False
   ssl_context.verify_mode = ssl.CERT_NONE
   
   async with websockets.connect(uri, ssl=ssl_context) as websocket:
       # connection code
   ```

2. **Docker Networking Considerations:**
   - Containers need proper CA certificates installed
   - Alpine Linux may lack default CA certificates
   - SSL verification may fail for cloud services

### Docker SSL Certificate Issues
From `/docker/docs` documentation:

1. **CA Certificates in Alpine:**
   ```dockerfile
   RUN apk add --no-cache ca-certificates
   ```

2. **Certificate Verification:**
   - Docker containers may not trust external SSL certificates by default
   - Need to either install CA certificates or disable verification for trusted services

---

## 🛠️ **Implemented Solutions**

### 1. SSL Context for WebSocket Connections
```python
def _create_ssl_context(self) -> Optional[ssl.SSLContext]:
    """Create SSL context for WebSocket connections in Docker containers."""
    ssl_context = ssl.create_default_context()
    
    if os.getenv('DOCKER_CONTAINER', '').lower() in ('true', '1', 'yes'):
        # Disable hostname verification for cloud services
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
    
    return ssl_context
```

**Status:** Implemented but temporarily disabled for testing

### 2. Enhanced Error Handling
```python
except asyncio.TimeoutError as e:
    error_msg = f"Connection timeout after {config.timeout}s: {str(e)}"
except websockets.exceptions.ConnectionClosed as e:
    error_msg = f"WebSocket connection closed: {str(e)}"
except websockets.exceptions.InvalidURI as e:
    error_msg = f"Invalid WebSocket URI: {str(e)}"
except websockets.exceptions.InvalidHandshake as e:
    error_msg = f"WebSocket handshake failed: {str(e)}"
except Exception as e:
    error_msg = f"Unexpected error: {type(e).__name__}: {str(e)}"
```

**Status:** Implemented

### 3. Retry Mechanism with Exponential Backoff
```python
async def _test_connection_with_retry(self, config: HAConnectionConfig):
    """Test connection with retry logic for cloud connections."""
    max_retries = config.max_retries
    retry_delay = config.retry_delay
    
    for attempt in range(max_retries):
        result = await self.test_connection(config)
        if result.success:
            return result
        
        if attempt < max_retries - 1:
            await asyncio.sleep(retry_delay)
            retry_delay *= 2  # Exponential backoff
```

**Status:** Implemented

---

## 🚨 **Critical Issue: Logging Not Appearing**

The most critical issue is that **none of our detailed logging is appearing** in the Docker logs. This suggests:

1. **The WebSocket connection is failing immediately** (before our code runs)
2. **The exception is being caught elsewhere** (not in our error handlers)
3. **The connection manager is not being called** (service using old code)

### Debugging Steps Needed:

1. **Verify Container is Using Updated Code:**
   ```bash
   docker exec homeiq-websocket cat /app/shared/ha_connection_manager.py | grep "Testing WebSocket"
   ```

2. **Check if Connection Manager is Being Called:**
   Add logging at the start of `test_connection` method

3. **Test WebSocket Connection from Container:**
   ```bash
   docker exec homeiq-websocket python -c "import websockets; import asyncio; asyncio.run(websockets.connect('wss://lwzisze94hrpqde9typkwgu5pptxdkoh.ui.nabu.casa/api/websocket'))"
   ```

4. **Check CA Certificates in Container:**
   ```bash
   docker exec homeiq-websocket ls -la /etc/ssl/certs/
   ```

---

## 📋 **Next Steps**

### Immediate Actions:
1. **Add CA Certificates to Dockerfile:**
   ```dockerfile
   RUN apk add --no-cache ca-certificates
   ```

2. **Add Debug Logging at Entry Point:**
   ```python
   logger.info("🚀 HAConnectionManager initialized")
   logger.info(f"📋 Loaded {len(self.connections)} connection configs")
   ```

3. **Test WebSocket Library in Container:**
   Create a minimal test script to verify `websockets` library works in Alpine Linux

4. **Enable SSL Context:**
   Re-enable the SSL context code once debugging is complete

### Long-term Solutions:
1. **Implement Health Checks:** Add connection health monitoring
2. **Add Metrics:** Track connection success/failure rates
3. **Improve Logging:** Add structured logging with correlation IDs
4. **Add Alerts:** Notify when all connections fail

---

## 📊 **Current Status**

| Component | Status | Notes |
|-----------|--------|-------|
| Connection Manager | ✅ Implemented | Code complete, needs debugging |
| SSL Context | ⚠️ Disabled | Temporarily disabled for testing |
| Error Handling | ✅ Complete | Comprehensive exception handling |
| Retry Logic | ✅ Complete | Exponential backoff implemented |
| Local Testing | ✅ Passed | Nabu Casa works locally |
| Docker Testing | ❌ Failed | No logging appearing |
| InfluxDB Connection | ❌ Failed | Token issue |

---

## 🎓 **Lessons Learned**

1. **Local ≠ Docker:** What works locally may not work in Docker containers
2. **Alpine Linux:** Requires explicit CA certificate installation
3. **SSL/TLS:** Cloud services need proper SSL context in containers
4. **Logging:** Critical for debugging - add logging early and often
5. **Testing:** Test in the actual deployment environment (Docker)

---

## 📚 **References**

- **Context7 - Python WebSockets:** `/python-websockets/websockets`
- **Context7 - Docker Docs:** `/docker/docs`
- **Home Assistant WebSocket API:** https://developers.home-assistant.io/docs/api/websocket
- **Nabu Casa Documentation:** https://www.nabucasa.com/config/remote/

---

## 🔗 **Related Files**

- `shared/ha_connection_manager.py` - Main connection manager
- `test_nabu_casa_connection.py` - Local test script (PASSED)
- `docker-compose.yml` - Docker configuration
- `.env` - Environment variables (contains Nabu Casa tokens)
- `services/websocket-ingestion/Dockerfile` - Container definition

---

**Last Updated:** October 25, 2025, 3:55 PM  
**Next Review:** After implementing CA certificates fix

