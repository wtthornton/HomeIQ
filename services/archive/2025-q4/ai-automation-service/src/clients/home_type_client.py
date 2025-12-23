"""
Home Type Client (Single Home NUC Optimized)

Provides access to home type classification and profiling data.
Optimized for single home deployment with aggressive caching.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class HomeTypeError(Exception):
    """Base exception for home type errors."""
    pass


class HomeTypeAPIError(HomeTypeError):
    """API error when fetching home type."""
    pass


class HomeTypeClient:
    """
    Client for accessing home type data (single home optimized).
    
    Features:
    - In-memory caching (24-hour TTL)
    - Connection pooling (httpx)
    - Retry logic with exponential backoff
    - Graceful fallback to default home type
    - Single home optimization (always 'default')
    """
    
    def __init__(self, base_url: str = "http://ai-automation-service:8018", api_key: str | None = None):
        """
        Initialize home type client.
        
        Args:
            base_url: Base URL for home type API
            api_key: Optional API key for authentication (if None, tries to get from settings)
        """
        self.base_url = base_url.rstrip('/')
        
        # Get API key from settings if not provided
        if api_key is None:
            try:
                from ..config import settings
                api_key = settings.ai_automation_api_key
            except Exception:
                api_key = None
        
        self.api_key = api_key
        
        # Initialize HTTP client with connection pooling (2025 best practice)
        headers = {}
        if self.api_key:
            headers["X-HomeIQ-API-Key"] = self.api_key
        
        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers=headers,
            limits=httpx.Limits(
                max_keepalive_connections=5,
                max_connections=10
            )
        )
        
        # Single home cache (not dict - just one entry for NUC optimization)
        self._cache: dict[str, Any] | None = None
        self._cache_time: datetime | None = None
        self._cache_ttl = timedelta(hours=24)
        
        logger.info(f"HomeTypeClient initialized (base_url={self.base_url})")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True
    )
    async def get_home_type(
        self,
        use_cache: bool = True
    ) -> dict[str, Any]:
        """
        Get current home type classification (single home).
        
        Optimized for single home deployment - always uses 'default' home_id.
        
        Args:
            use_cache: Whether to use cached value
        
        Returns:
            {
                'home_type': str,
                'confidence': float,
                'method': str,
                'features_used': list[str],
                'last_updated': str
            }
        """
        # Check cache
        if use_cache and self._cache and self._cache_time:
            age = datetime.now(timezone.utc) - self._cache_time
            if age < self._cache_ttl:
                logger.debug(
                    f"Using cached home type: {self._cache['home_type']} "
                    f"(age: {age.total_seconds():.0f}s)"
                )
                return self._cache
        
        # Fetch from API (single home, always 'default')
        try:
            url = f"{self.base_url}/api/home-type/classify"
            response = await self.client.get(url, params={'home_id': 'default'})
            
            if response.status_code == 200:
                data = response.json()
                # Cache result
                data['cached_at'] = datetime.now(timezone.utc).isoformat()
                self._cache = data
                self._cache_time = datetime.now(timezone.utc)
                
                logger.info(
                    "Home type fetched",
                    extra={
                        "home_type": data.get("home_type"),
                        "confidence": data.get("confidence"),
                        "cached": False
                    }
                )
                return data
            else:
                logger.warning(
                    f"Failed to get home type: HTTP {response.status_code}",
                    extra={"status_code": response.status_code}
                )
                return self._get_default_home_type()
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching home type: {e}")
            raise HomeTypeAPIError(f"Failed to fetch home type: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error fetching home type: {e}", exc_info=True)
            return self._get_default_home_type()
    
    async def startup(self):
        """
        Pre-fetch home type on service startup.
        
        This ensures home type is available immediately when needed.
        """
        try:
            await self.get_home_type(use_cache=False)
            logger.info("Home type pre-fetched at startup")
        except Exception as e:
            logger.warning(
                f"Failed to pre-fetch home type: {e}, will use default",
                exc_info=True
            )
    
    def _get_default_home_type(self) -> dict[str, Any]:
        """Return default home type when API unavailable."""
        return {
            'home_type': 'standard_home',
            'confidence': 0.5,
            'method': 'default_fallback',
            'features_used': [],
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'cached_at': datetime.now(timezone.utc).isoformat()
        }
    
    def clear_cache(self):
        """Clear cache (for testing or manual refresh)."""
        self._cache = None
        self._cache_time = None
        logger.debug("Home type cache cleared")
    
    async def close(self):
        """Close HTTP client (call on service shutdown)."""
        await self.client.aclose()
        logger.debug("HomeTypeClient closed")

