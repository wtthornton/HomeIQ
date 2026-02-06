"""
Shared HTTP client session management

Provides a module-level aiohttp ClientSession to avoid creating
a new TCP connection pool on every HTTP request. The session is
created lazily on first use and closed during application shutdown.
"""
import aiohttp

_session: aiohttp.ClientSession | None = None


async def get_http_session() -> aiohttp.ClientSession:
    """Get or create the shared aiohttp ClientSession"""
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10),
            headers={"Content-Type": "application/json"}
        )
    return _session


async def close_http_session():
    """Close the shared aiohttp ClientSession"""
    global _session
    if _session and not _session.closed:
        await _session.close()
        _session = None
