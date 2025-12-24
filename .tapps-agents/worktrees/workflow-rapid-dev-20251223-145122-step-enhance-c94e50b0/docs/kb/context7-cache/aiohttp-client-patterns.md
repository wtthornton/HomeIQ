# aiohttp Client Patterns
**Context7 KB Cache**

**Library:** aiohttp (/aio-libs/aiohttp)  
**Topic:** Client session, caching, error handling  
**Retrieved:** October 10, 2025  
**Code Snippets:** 678 available  
**Trust Score:** 9.3

---

## Error Handling Patterns

### SSL Error Handling

**Catch All SSL Errors:**
```python
try:
    await session.get('https://expired.badssl.com/')
except aiohttp.ClientSSLError as e:
    assert isinstance(e, ssl.SSLError)

try:
    await session.get('https://wrong.host.badssl.com/')
except aiohttp.ClientSSLError as e:
    assert isinstance(e, ssl.CertificateError)
```

**Specific SSL Errors:**
```python
# Certificate verification errors
try:
    await session.get('https://expired.badssl.com/')
except aiohttp.ClientConnectorSSLError as e:
    assert isinstance(e, ssl.SSLError)

# Hostname mismatch errors
try:
    await session.get('https://wrong.host.badssl.com/')
except aiohttp.ClientConnectorCertificateError as e:
    assert isinstance(e, ssl.CertificateError)
```

### WebSocket Exception Handling

```python
error = websocket.exception()
if error:
    print(f"An error occurred: {error}")
```

---

## Session Management

### Persistent Client Session with cleanup_ctx

**Best Practice for Application Lifecycle:**
```python
from aiohttp import web

persistent_session = web.AppKey("persistent_session", aiohttp.ClientSession)

async def persistent_session_context(app):
    app[persistent_session] = session = aiohttp.ClientSession()
    yield
    await session.close()

app.cleanup_ctx.append(persistent_session_context)

async def my_request_handler(request):
    session = request.app[persistent_session]
    async with session.get('https://api.example.com') as resp:
        return await resp.json()
```

**Key Points:**
- Session initialized once per application
- Automatically cleaned up on shutdown
- Shared across all request handlers
- Efficient connection pooling

---

## Patterns for HA Ingestor

### External API Integration Pattern

```python
import aiohttp
from datetime import datetime, timedelta

class ExternalAPIService:
    """Base pattern for external API services"""
    
    def __init__(self):
        self.cache = {}
        self.cache_ttl = timedelta(minutes=15)
        self.session = None
    
    async def startup(self):
        """Initialize session on startup"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10)
        )
    
    async def shutdown(self):
        """Cleanup on shutdown"""
        if self.session:
            await self.session.close()
    
    async def fetch_with_cache(self, url: str, cache_key: str) -> dict:
        """Fetch from API with caching and error handling"""
        
        # Check cache
        if cache_key in self.cache:
            cached_data, cached_time = self.cache[cache_key]
            if datetime.now() - cached_time < self.cache_ttl:
                return cached_data
        
        # Fetch from API
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    self.cache[cache_key] = (data, datetime.now())
                    return data
                else:
                    # Fall back to cached data
                    if cache_key in self.cache:
                        return self.cache[cache_key][0]
                    raise Exception(f"HTTP {response.status}")
                    
        except aiohttp.ClientError as e:
            # Network error - use cached data
            if cache_key in self.cache:
                return self.cache[cache_key][0]
            raise Exception(f"API error: {e}")
```

---

**Source:** Context7 via /aio-libs/aiohttp  
**Usage:** External API integration in data source services  
**Cached:** 2025-10-10

