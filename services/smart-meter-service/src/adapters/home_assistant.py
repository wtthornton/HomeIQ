"""
Home Assistant Energy Sensor Adapter
Pulls energy data from HA's existing energy sensors
"""

import logging
from datetime import datetime
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
        logger.info(f"Home Assistant adapter initialized for {ha_url}")

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
                'timestamp': datetime.now()
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
    ) -> str:
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

    async def _get_circuit_data(
        self,
        session: aiohttp.ClientSession
    ) -> list[dict[str, Any]]:
        """
        Get all power circuit sensors from HA
        
        Searches for sensors with:
        - entity_id starting with 'sensor.power_'
        - device_class = 'power'
        - unit_of_measurement = 'W' or 'kW'
        
        Returns:
            List of circuits with name, entity_id, power_w
        """
        url = f"{self.ha_url}/api/states"
        circuits = []

        try:
            async with session.get(url, headers=self.headers) as response:
                if response.status != 200:
                    logger.error(f"Failed to fetch states: HTTP {response.status}")
                    return []

                states = await response.json()

                # Filter for power sensors
                for state in states:
                    entity_id = state.get('entity_id', '')
                    attributes = state.get('attributes', {})
                    state_value = state.get('state', '0')

                    # Skip unavailable sensors
                    if state_value in ('unavailable', 'unknown', 'none', None):
                        continue

                    # Check if it's a power sensor
                    device_class = attributes.get('device_class', '')
                    unit = attributes.get('unit_of_measurement', '')

                    is_power_sensor = (
                        entity_id.startswith('sensor.power_') or
                        device_class == 'power' or
                        unit in ('W', 'kW')
                    )

                    # Exclude the total power sensor
                    is_total = any(x in entity_id.lower() for x in ['total', 'home', 'consumption'])

                    if is_power_sensor and not is_total:
                        try:
                            power_w = float(state_value)

                            # Convert kW to W if needed
                            if unit == 'kW':
                                power_w *= 1000

                            circuits.append({
                                'name': attributes.get('friendly_name', entity_id),
                                'entity_id': entity_id,
                                'power_w': power_w
                            })
                        except (ValueError, TypeError):
                            # Skip sensors with non-numeric states
                            continue

                logger.info(f"Found {len(circuits)} circuit power sensors")
                return circuits

        except Exception as e:
            logger.error(f"Error fetching circuit data: {e}")
            return []

    async def test_connection(self) -> bool:
        """
        Test connection to Home Assistant
        
        Returns:
            True if connection successful, False otherwise
        """
        url = f"{self.ha_url}/api/"

        try:
            async with aiohttp.ClientSession() as session:
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

