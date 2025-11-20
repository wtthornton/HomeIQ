"""
Awattar Electricity Pricing Provider
"""

from datetime import datetime
from typing import Any

import aiohttp


class AwattarProvider:
    """Awattar electricity pricing provider"""

    BASE_URL = "https://api.awattar.de/v1/marketdata"

    async def fetch_pricing(self, session: aiohttp.ClientSession) -> dict[str, Any]:
        """Fetch pricing from Awattar API"""

        params = {
            "start": int(datetime.now().timestamp() * 1000)
        }

        async with session.get(self.BASE_URL, params=params) as response:
            if response.status == 200:
                data = await response.json()

                # Parse Awattar response
                return self._parse_response(data)
            else:
                raise Exception(f"Awattar API returned status {response.status}")

    def _parse_response(self, data: dict) -> dict[str, Any]:
        """Parse Awattar API response"""

        market_data = data.get('data', [])

        if not market_data:
            return {}

        # Current price (first entry)
        current = market_data[0]
        current_price = current['marketprice'] / 10000  # Convert to €/kWh

        # Build 24-hour forecast
        forecast_24h = []
        for i, entry in enumerate(market_data[:24]):
            forecast_24h.append({
                'hour': i,
                'price': entry['marketprice'] / 10000,
                'timestamp': datetime.fromtimestamp(entry['start_timestamp'] / 1000)
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

