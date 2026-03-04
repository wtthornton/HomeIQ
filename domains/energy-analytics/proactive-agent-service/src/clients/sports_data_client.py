"""
Sports Data Client for Proactive Agent Service (cross-group: core-platform)

Fetches sports scores and schedules via data-api service.
Uses CrossGroupClient with shared circuit breaker for resilience.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx
from homeiq_resilience import CircuitOpenError, CrossGroupClient

from .breakers import core_platform_breaker

logger = logging.getLogger(__name__)


class SportsDataClient:
    """Resilient client for fetching sports data via Data API (core-platform group)."""

    def __init__(self, base_url: str = "http://data-api:8006"):
        self.base_url = base_url.rstrip("/")
        api_key = os.getenv("DATA_API_API_KEY") or os.getenv("API_KEY")
        self._cross_client = CrossGroupClient(
            base_url=self.base_url,
            group_name="core-platform",
            timeout=30.0,
            max_retries=3,
            auth_token=api_key,
            circuit_breaker=core_platform_breaker,
        )
        logger.info("Sports Data client initialized with base_url=%s", self.base_url)

    async def get_live_games(self, team_ids: str | None = None) -> list[dict[str, Any]]:
        """Get live games. Returns [] on failure."""
        try:
            params: dict[str, Any] = {}
            if team_ids:
                params["team_ids"] = team_ids

            logger.debug("Fetching live games from Data API: %s", params)
            response = await self._cross_client.call(
                "GET", "/api/v1/sports/games/live", params=params,
            )
            response.raise_for_status()
            data = response.json()
            games = data if isinstance(data, list) else data.get("games", [])
            logger.info("Fetched %d live games", len(games))
            return games
        except CircuitOpenError:
            logger.warning("Data API circuit open — returning empty games")
            return []
        except httpx.HTTPError as e:
            logger.warning("HTTP error fetching sports data: %s", e)
            return []
        except Exception:
            logger.warning("Error fetching sports data", exc_info=True)
            return []

    async def get_upcoming_games(self, team: str | None = None) -> list[dict[str, Any]]:
        """Get upcoming games. Returns [] on failure."""
        try:
            params: dict[str, Any] = {}
            if team:
                params["team"] = team

            logger.debug("Fetching upcoming games from Data API: %s", params)
            response = await self._cross_client.call(
                "GET", "/api/v1/sports/games/upcoming", params=params,
            )
            response.raise_for_status()
            data = response.json()
            games = data if isinstance(data, list) else data.get("games", [])
            logger.info("Fetched %d upcoming games", len(games))
            return games
        except CircuitOpenError:
            logger.warning("Data API circuit open — returning empty upcoming games")
            return []
        except Exception:
            logger.warning("Error fetching upcoming games", exc_info=True)
            return []

    async def close(self):
        """No-op — CrossGroupClient uses per-request clients."""
        logger.debug("Sports Data client close (no-op with CrossGroupClient)")
