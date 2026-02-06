"""Base adapter interface for smart meters"""

from abc import ABC, abstractmethod
from typing import Any

import aiohttp


class MeterAdapter(ABC):
    """Base class for smart meter adapters"""

    @abstractmethod
    async def fetch_consumption(self, session: aiohttp.ClientSession, api_token: str, device_id: str) -> dict[str, Any]:
        """Fetch consumption data from meter API"""
        pass

    async def test_connection(self, session: aiohttp.ClientSession) -> bool:
        """Test connection to meter API. Override in subclasses."""
        return True

