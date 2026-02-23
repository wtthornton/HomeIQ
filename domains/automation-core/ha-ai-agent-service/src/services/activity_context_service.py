"""
Activity Context Service
Epic Activity Recognition Integration - Story 2.1

Fetches current household activity from data-api and injects into Tier 1 context.
Graceful degradation: on timeout, 404, or 503, omits activity or uses fallback.
"""

import contextlib
import logging

import httpx

from ..config import Settings
from ..services.context_builder import ContextBuilder

logger = logging.getLogger(__name__)

ACTIVITY_CACHE_TTL = 90  # 1.5 min
ACTIVITY_TIMEOUT = 5.0


class ActivityContextService:
    """
    Fetches latest activity from data-api for Tier 1 context injection.
    Caches briefly; degrades gracefully when data-api or activity unavailable.
    """

    def __init__(self, settings: Settings, context_builder: ContextBuilder):
        self.settings = settings
        self.context_builder = context_builder
        self._cache_key = "activity_context"
        self._cache_ttl = ACTIVITY_CACHE_TTL

    def _get_cache_key(self, home_id: str | None = None) -> str:
        return f"{self._cache_key}_{home_id or 'default'}"

    async def get_activity_context_line(self, home_id: str | None = None) -> str:
        """
        Get one-line activity context for system prompt injection.

        Returns:
            "Current household activity: cooking (confidence 0.85)" or empty string
            / "Activity unavailable" on graceful degradation.
        """
        cache_key = self._get_cache_key(home_id)
        try:
            cached = await self.context_builder._get_cached_value(cache_key)
            if cached is not None:
                return cached
        except Exception:
            pass

        activity_str = await self._fetch_and_format()
        if activity_str:
            with contextlib.suppress(Exception):
                await self.context_builder._set_cached_value(
                    cache_key, activity_str, self._cache_ttl
                )
        return activity_str

    async def _fetch_and_format(self) -> str:
        """Fetch from data-api, format one line. Returns empty on failure."""
        base_url = (self.settings.data_api_url or "http://data-api:8006").rstrip("/")
        url = f"{base_url}/api/v1/activity"
        headers = {}
        if self.settings.data_api_key:
            headers["Authorization"] = f"Bearer {self.settings.data_api_key.get_secret_value()}"

        try:
            async with httpx.AsyncClient(timeout=ACTIVITY_TIMEOUT) as client:
                response = await client.get(url, headers=headers or None)
                if response.status_code == 404:
                    logger.debug("No activity data (404) - omitting from context")
                    return ""
                if response.status_code == 503:
                    logger.debug("Activity service unavailable (503) - omitting")
                    return ""
                if response.status_code != 200:
                    logger.debug("Activity API returned %d - omitting", response.status_code)
                    return ""
                data = response.json()
        except httpx.TimeoutException:
            logger.debug("Activity fetch timeout - omitting from context")
            return ""
        except httpx.HTTPError as e:
            logger.debug("Activity fetch failed: %s - omitting", e)
            return ""
        except Exception as e:
            logger.debug("Activity fetch error: %s - omitting", e)
            return ""

        activity = data.get("activity") or "unknown"
        confidence = data.get("confidence")
        if confidence is not None:
            try:
                conf = float(confidence)
                return f"Current household activity: {activity} (confidence {conf:.2f})"
            except (TypeError, ValueError):
                pass
        return f"Current household activity: {activity}"
