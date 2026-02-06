"""
Awattar Electricity Pricing Provider
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

import aiohttp

from providers import ProviderAPIError, ProviderParseError

logger = logging.getLogger(__name__)


class AwattarProvider:
    """Awattar electricity pricing provider"""

    BASE_URL = "https://api.awattar.de/v1/marketdata"
    MAX_RETRIES = 3

    async def fetch_pricing(self, session: aiohttp.ClientSession) -> dict[str, Any] | None:
        """Fetch pricing from Awattar API with retry logic"""

        params = {
            "start": int(datetime.now(timezone.utc).timestamp() * 1000)
        }

        last_exception = None
        for attempt in range(self.MAX_RETRIES):
            try:
                async with session.get(self.BASE_URL, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_response(data)
                    else:
                        raise ProviderAPIError(response.status, f"Awattar API returned status {response.status}")
            except (ProviderAPIError, ProviderParseError):
                raise
            except Exception as e:
                last_exception = e
                if attempt < self.MAX_RETRIES - 1:
                    wait = 2 ** attempt
                    logger.warning(f"Awattar fetch attempt {attempt + 1} failed: {e}, retrying in {wait}s")
                    await asyncio.sleep(wait)

        raise last_exception

    def _parse_response(self, data: dict) -> dict[str, Any] | None:
        """Parse Awattar API response"""

        market_data = data.get('data', [])

        if not market_data:
            return None

        # Validate required fields in each entry
        required_fields = {'marketprice', 'start_timestamp'}
        for entry in market_data:
            if not required_fields.issubset(entry.keys()):
                raise ProviderParseError(f"Missing fields in Awattar response: {required_fields - entry.keys()}")

        # Current price (first entry)
        current = market_data[0]
        current_price = current['marketprice'] / 10000  # Convert to €/kWh

        # Build 24-hour forecast
        forecast_24h = []
        for i, entry in enumerate(market_data[:24]):
            forecast_24h.append({
                'hour': i,
                'price': entry['marketprice'] / 10000,
                'timestamp': datetime.fromtimestamp(entry['start_timestamp'] / 1000, tz=timezone.utc)
            })

        # Find cheapest and most expensive hours
        sorted_by_price = sorted(forecast_24h, key=lambda x: x['price'])
        cheapest_hours = [h['hour'] for h in sorted_by_price[:4]]
        most_expensive_hours = [h['hour'] for h in sorted_by_price[-4:]]

        return {
            'current_price': current_price,
            'currency': 'EUR',
            'peak_period': current_price > sorted_by_price[len(sorted_by_price)//2]['price'],
            'forecast_24h': forecast_24h,
            'cheapest_hours': cheapest_hours,
            'most_expensive_hours': most_expensive_hours
        }

