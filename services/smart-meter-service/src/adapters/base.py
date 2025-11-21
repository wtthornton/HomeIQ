"""Base adapter interface for smart meters"""

from abc import ABC, abstractmethod
from typing import Any

import aiohttp


class MeterAdapter(ABC):
    """Base class for smart meter adapters"""

    @abstractmethod
    async def fetch_consumption(self, session: aiohttp.ClientSession, api_token: str, device_id: str) -> dict[str, Any]:
        """Fetch consumption data from meter API"""

