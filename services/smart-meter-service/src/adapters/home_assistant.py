"""
Home Assistant Energy Sensor Adapter
Pulls energy data from HA's existing energy sensors
"""

import logging
import math
from datetime import datetime, timezone
from typing import Any

import aiohttp

from .base import MeterAdapter

logger = logging.getLogger(__name__)


class HomeAssistantAdapter(MeterAdapter):
    """Adapter for Home Assistant energy monitoring sensors"""

    def __init__(self, ha_url: str, ha_token: str):
        """
        Initialize Home Assistant adapter
        
        Args:
            ha_url: Home Assistant URL (e.g., http://homeassistant:8123)
            ha_token: Long-lived access token
        """
        self.ha_url = ha_url.rstrip('/')
        self.ha_token = ha_token
        self.headers = {
            "Authorization": f"Bearer {ha_token}",
            "Content-Type": "application/json"
        }
        self._discovered_circuits: list[str] | None = None
        self._last_discovery: datetime | None = None
        self._discovery_interval = 3600  # Re-discover every hour

        logger.info(f"Home Assistant adapter initialized for {ha_url}")

    def __repr__(self):
        return f"HomeAssistantAdapter(url={self.ha_url})"

    async def fetch_consumption(
        self,
        session: aiohttp.ClientSession,
        api_token: str,
        device_id: str
    ) -> dict[str, Any]:
        """
        Fetch power consumption from Home Assistant sensors
        
        Expected HA sensors (configure based on your HA setup):
        - sensor.total_power or sensor.power_total (whole-home power in watts)
        - sensor.daily_energy or sensor.energy_daily (daily energy in kWh)
        - sensor.power_* (individual circuit/device sensors)
        
        Args:
            session: aiohttp session
            api_token: Not used (HA token from init)
            device_id: Not used (HA sensors are discovered)
            
        Returns:
            Dict with total_power_w, daily_kwh, circuits, timestamp
        """

        try:
            # Get whole-home power (try multiple common sensor names)
            total_power = await self._get_power_sensor(session)

            # Get daily energy
            daily_kwh = await self._get_energy_sensor(session)

            # Get circuit-level data (scan for power sensors)
            circuits = await self._get_circuit_data(session)

            # Calculate percentages
            for circuit in circuits:
                circuit['percentage'] = (
                    (circuit['power_w'] / total_power * 100)
                    if total_power > 0 else 0
                )

            return {
                'total_power_w': float(total_power),
                'daily_kwh': float(daily_kwh),
                'circuits': circuits,
                'timestamp': datetime.now(timezone.utc)
            }

        except Exception as e:
            logger.error(f"Error fetching from Home Assistant: {e}")
            raise

    async def _get_power_sensor(self, session: aiohttp.ClientSession) -> float:
        """
        Get whole-home power consumption
        
        Tries multiple common sensor names:
        - sensor.total_power
        - sensor.power_total
        - sensor.home_power
        - sensor.power_consumption
        """
        sensor_names = [
            'sensor.total_power',
            'sensor.power_total',
            'sensor.home_power',
            'sensor.power_consumption'
        ]

        for sensor_name in sensor_names:
            power = await self._get_sensor_state(session, sensor_name)
            if power is not None:
                logger.debug(f"Found power sensor: {sensor_name} = {power}W")
                return float(power)

        logger.warning("No total power sensor found, returning 0")
        return 0.0

    async def _get_energy_sensor(self, session: aiohttp.ClientSession) -> float:
        """
        Get daily energy consumption
        
        Tries multiple common sensor names:
        - sensor.daily_energy
        - sensor.energy_daily
        - sensor.energy_today
        """
        sensor_names = [
            'sensor.daily_energy',
            'sensor.energy_daily',
            'sensor.energy_today'
        ]

        for sensor_name in sensor_names:
            energy = await self._get_sensor_state(session, sensor_name)
            if energy is not None:
                logger.debug(f"Found energy sensor: {sensor_name} = {energy}kWh")
                return float(energy)

        logger.warning("No daily energy sensor found, returning 0")
        return 0.0

    async def _get_sensor_state(
        self,
        session: aiohttp.ClientSession,
        entity_id: str
    ) -> str | None:
        """
        Get state of a single HA sensor
        
        Args:
            session: aiohttp session
            entity_id: Entity ID (e.g., sensor.total_power)
            
        Returns:
            Sensor state as string, or None if not found
        """
        url = f"{self.ha_url}/api/states/{entity_id}"

        try:
            async with session.get(url, headers=self.headers) as response:
                if response.status == 200:
                    data = await response.json()
                    state = data.get('state', '0')

                    # Handle unavailable/unknown states
                    if state in ('unavailable', 'unknown', 'none', None):
                        return None

                    return state
                elif response.status == 404:
                    # Sensor doesn't exist
                    return None
                else:
                    logger.warning(f"Error fetching {entity_id}: HTTP {response.status}")
                    return None

        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching {entity_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching {entity_id}: {e}")
            return None

    @staticmethod
    def _validate_power_reading(value: float, entity_id: str) -> float | None:
        """Validate a power reading, returning None if invalid"""
        if math.isnan(value) or math.isinf(value):
            logger.warning(f"Invalid power reading from {entity_id}: {value}")
            return None
        if value < 0:
            logger.warning(f"Negative power reading from {entity_id}: {value}W")
            return None
        if value > 100000:  # 100kW sanity check for residential
            logger.warning(f"Unreasonably high power from {entity_id}: {value}W")
            return None
        return value

    async def _discover_circuits(self, session: aiohttp.ClientSession) -> None:
        """Discover circuit power sensors from HA and cache entity IDs"""
        url = f"{self.ha_url}/api/states"

        try:
            async with session.get(url, headers=self.headers) as response:
                if response.status != 200:
                    logger.error(f"Failed to fetch states for discovery: HTTP {response.status}")
                    return

                states = await response.json()
                discovered = []

                for state in states:
                    entity_id = state.get('entity_id', '')
                    attributes = state.get('attributes', {})

                    device_class = attributes.get('device_class', '')
                    unit = attributes.get('unit_of_measurement', '')

                    is_power_sensor = (
                        entity_id.startswith('sensor.power_') or
                        device_class == 'power' or
                        unit in ('W', 'kW')
                    )

                    is_total = any(x in entity_id.lower() for x in ['total', 'home', 'consumption'])

                    if is_power_sensor and not is_total:
                        discovered.append(entity_id)

                self._discovered_circuits = discovered
                self._last_discovery = datetime.now(timezone.utc)
                logger.info(f"Discovered {len(discovered)} circuit power sensors")

        except Exception as e:
            logger.error(f"Error during circuit discovery: {e}")

    async def _get_circuit_data(
        self,
        session: aiohttp.ClientSession
    ) -> list[dict[str, Any]]:
        """
        Get all power circuit sensors from HA

        Uses cached circuit discovery (refreshed every hour) and validates
        power readings before including them.

        Returns:
            List of circuits with name, entity_id, power_w
        """
        # Re-discover circuits periodically
        if (self._discovered_circuits is None or
                self._last_discovery is None or
                (datetime.now(timezone.utc) - self._last_discovery).total_seconds() > self._discovery_interval):
            await self._discover_circuits(session)

        circuits = []

        for entity_id in (self._discovered_circuits or []):
            state_str = await self._get_sensor_state(session, entity_id)
            if state_str is None:
                continue

            try:
                power_w = float(state_str)
            except (ValueError, TypeError):
                continue

            # Validate the reading
            power_w = self._validate_power_reading(power_w, entity_id)
            if power_w is None:
                continue

            circuits.append({
                'name': entity_id,
                'entity_id': entity_id,
                'power_w': power_w
            })

        logger.info(f"Found {len(circuits)} circuit power sensors")
        return circuits

    async def test_connection(self, session: aiohttp.ClientSession) -> bool:
        """
        Test connection to Home Assistant using the shared session

        Args:
            session: aiohttp session to use for the connection test

        Returns:
            True if connection successful, False otherwise
        """
        url = f"{self.ha_url}/api/"

        try:
            async with session.get(url, headers=self.headers) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Connected to Home Assistant: {data.get('message', 'OK')}")
                    return True
                else:
                    logger.error(f"Failed to connect to HA: HTTP {response.status}")
                    return False
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

