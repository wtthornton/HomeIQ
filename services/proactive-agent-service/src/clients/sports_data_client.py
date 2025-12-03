"""
Sports Data Client for Proactive Agent Service

Fetches sports scores and schedules from sports-data service.
Note: Sports data is now accessed via data-api service.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class SportsDataClient:
    """Client for fetching sports data from Data API service"""

    def __init__(self, base_url: str = "http://data-api:8006"):
        """
        Initialize Sports Data client.

        Args:
            base_url: Base URL for Data API (default: http://data-api:8006)
        """
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
        logger.info(f"Sports Data client initialized with base_url={self.base_url}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=False  # Don't reraise - return empty list for graceful degradation
    )
    async def get_live_games(self, team_ids: str | None = None) -> list[dict[str, Any]]:
        """
        Get live games.

        Args:
            team_ids: Optional comma-separated team IDs

        Returns:
            List of game dictionaries or empty list if unavailable
        """
        try:
            params: dict[str, Any] = {}
            if team_ids:
                params["team_ids"] = team_ids

            logger.debug(f"Fetching live games from Data API: {params}")
            response = await self.client.get(
                f"{self.base_url}/api/v1/sports/games/live",
                params=params
            )
            response.raise_for_status()
            data = response.json()
            games = data if isinstance(data, list) else data.get("games", [])
            logger.info(f"Fetched {len(games)} live games")
            return games
        except httpx.HTTPStatusError as e:
            error_msg = f"Data API returned {e.response.status_code}: {e.response.text[:200]}"
            logger.warning(f"HTTP error fetching sports data: {error_msg}")
            return []  # Graceful degradation
        except httpx.ConnectError as e:
            error_msg = f"Could not connect to Data API at {self.base_url}"
            logger.warning(f"Connection error: {error_msg}")
            return []  # Graceful degradation
        except Exception as e:
            logger.warning(f"Error fetching sports data: {str(e)}", exc_info=True)
            return []  # Graceful degradation

    async def get_upcoming_games(self, team: str | None = None) -> list[dict[str, Any]]:
        """
        Get upcoming games.

        Args:
            team: Optional team name or ID

        Returns:
            List of upcoming game dictionaries or empty list if unavailable
        """
        try:
            params: dict[str, Any] = {}
            if team:
                params["team"] = team

            logger.debug(f"Fetching upcoming games from Data API: {params}")
            response = await self.client.get(
                f"{self.base_url}/api/v1/sports/games/upcoming",
                params=params
            )
            response.raise_for_status()
            data = response.json()
            games = data if isinstance(data, list) else data.get("games", [])
            logger.info(f"Fetched {len(games)} upcoming games")
            return games
        except Exception as e:
            logger.warning(f"Error fetching upcoming games: {str(e)}", exc_info=True)
            return []  # Graceful degradation

    async def close(self):
        """Close HTTP client connection pool"""
        await self.client.aclose()
        logger.debug("Sports Data client closed")

