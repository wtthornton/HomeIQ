"""
Data Patterns Analyzer for HA Simulator

Analyzes existing HA event logs to extract realistic patterns for simulation.
"""

import logging
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

class HADataPatternAnalyzer:
    """Analyzes HA event logs to extract patterns for simulation"""

    def __init__(self, log_file_path: str):
        self.log_file_path = log_file_path
        self.entity_patterns: dict[str, dict[str, Any]] = {}
        self.event_frequencies: dict[str, int] = defaultdict(int)
        self.temporal_patterns: dict[str, list[datetime]] = defaultdict(list)

    def analyze_log_file(self) -> dict[str, Any]:
        """Analyze HA event log file"""
        logger.info(f"Analyzing log file: {self.log_file_path}")

        if not Path(self.log_file_path).exists():
            logger.warning(f"Log file not found: {self.log_file_path}")
            return self._generate_default_patterns()

        try:
            with open(self.log_file_path) as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        self._parse_log_line(line)
                    except Exception as e:
                        logger.debug(f"Error parsing line {line_num}: {e}")
                        continue

            logger.info(f"Analyzed {line_num} log lines")
            return self._generate_patterns()

        except Exception as e:
            logger.exception(f"Error analyzing log file: {e}")
            return self._generate_default_patterns()

    def _parse_log_line(self, line: str):
        """Parse a single log line"""
        # Extract timestamp
        timestamp_match = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", line)
        if not timestamp_match:
            return

        try:
            timestamp = datetime.strptime(timestamp_match.group(1), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return

        # Extract entity information
        entity_match = re.search(r"Entity: ([a-zA-Z_\.]+)", line)
        if entity_match:
            entity_id = entity_match.group(1)
            self.temporal_patterns[entity_id].append(timestamp)
            self.event_frequencies[entity_id] += 1

    def _generate_patterns(self) -> dict[str, Any]:
        """Generate patterns from analyzed data"""
        patterns = {
            "entities": {},
            "event_frequencies": dict(self.event_frequencies),
            "temporal_patterns": {},
            "generated_at": datetime.now().isoformat(),
            "source": "log_analysis",
        }

        for entity_id, timestamps in self.temporal_patterns.items():
            if len(timestamps) < 2:
                continue

            # Calculate update intervals
            intervals = []
            for i in range(1, len(timestamps)):
                interval = (timestamps[i] - timestamps[i-1]).total_seconds()
                if interval > 0:  # Only positive intervals
                    intervals.append(interval)

            if not intervals:
                continue

            avg_interval = sum(intervals) / len(intervals)

            # Determine entity type and default values
            domain = entity_id.split(".")[0]
            device_class = self._infer_device_class(entity_id)
            base_value, variance = self._infer_value_range(entity_id, device_class)

            patterns["entities"][entity_id] = {
                "entity_id": entity_id,
                "domain": domain,
                "device_class": device_class,
                "update_interval": max(1, int(avg_interval)),  # Minimum 1 second
                "base_value": base_value,
                "variance": variance,
                "event_count": len(timestamps),
                "first_seen": timestamps[0].isoformat(),
                "last_seen": timestamps[-1].isoformat(),
                "unit_of_measurement": self._infer_unit(entity_id, device_class),
                "friendly_name": self._generate_friendly_name(entity_id),
            }

        logger.info(f"Generated patterns for {len(patterns['entities'])} entities")
        return patterns

    def _infer_device_class(self, entity_id: str) -> str | None:
        """Infer device class from entity ID"""
        entity_lower = entity_id.lower()

        if "temperature" in entity_lower or "temp" in entity_lower:
            return "temperature"
        if "current" in entity_lower:
            return "current"
        if "speed" in entity_lower:
            return "data_rate"
        if "cpu" in entity_lower or "percent" in entity_lower:
            return None  # No specific device class
        if entity_id == "sun.sun":
            return None
        return None

    def _infer_value_range(self, entity_id: str, device_class: str | None) -> tuple:
        """Infer base value and variance from entity ID and device class"""
        entity_lower = entity_id.lower()

        if device_class == "temperature":
            if "chip" in entity_lower or "coordinator" in entity_lower:
                return 45.0, 5.0  # Chip temperature
            return 22.0, 2.0  # Room temperature
        if device_class == "current":
            return 0.5, 0.2  # Current in Amperes
        if device_class == "data_rate":
            if "download" in entity_lower:
                return 100.0, 50.0  # Download speed
            if "upload" in entity_lower:
                return 50.0, 25.0  # Upload speed
            return 75.0, 25.0  # Generic data rate
        if "cpu" in entity_lower or "percent" in entity_lower:
            return 15.0, 10.0  # CPU percentage
        if entity_id == "sun.sun":
            return "above_horizon", None  # Sun state
        return 0.0, 1.0  # Default numeric value

    def _infer_unit(self, entity_id: str, device_class: str | None) -> str | None:
        """Infer unit of measurement from entity ID and device class"""
        if device_class == "temperature":
            return "°C"
        if device_class == "current":
            return "A"
        if device_class == "data_rate":
            return "Mbit/s"
        if "percent" in entity_id.lower() or "cpu" in entity_id.lower():
            return "%"
        return None

    def _generate_friendly_name(self, entity_id: str) -> str:
        """Generate friendly name from entity ID"""
        # Convert entity_id to friendly name
        parts = entity_id.split(".")
        if len(parts) < 2:
            return entity_id

        parts[0]
        name_parts = parts[1].split("_")

        # Capitalize each word
        friendly_parts = [part.capitalize() for part in name_parts]
        return " ".join(friendly_parts)


    def _generate_default_patterns(self) -> dict[str, Any]:
        """Generate default patterns when no log data available"""
        logger.info("Generating default patterns")
        return {
            "entities": {
                "sensor.living_room_temperature": {
                    "entity_id": "sensor.living_room_temperature",
                    "domain": "sensor",
                    "device_class": "temperature",
                    "update_interval": 30,
                    "base_value": 22.0,
                    "variance": 2.0,
                    "unit_of_measurement": "°C",
                    "friendly_name": "Living Room Temperature",
                },
                "sensor.wled_estimated_current": {
                    "entity_id": "sensor.wled_estimated_current",
                    "domain": "sensor",
                    "device_class": "current",
                    "update_interval": 10,
                    "base_value": 0.5,
                    "variance": 0.2,
                    "unit_of_measurement": "A",
                    "friendly_name": "WLED Estimated Current",
                },
                "sensor.bar_estimated_current": {
                    "entity_id": "sensor.bar_estimated_current",
                    "domain": "sensor",
                    "device_class": "current",
                    "update_interval": 10,
                    "base_value": 0.3,
                    "variance": 0.1,
                    "unit_of_measurement": "A",
                    "friendly_name": "Bar Estimated Current",
                },
                "sensor.archer_be800_download_speed": {
                    "entity_id": "sensor.archer_be800_download_speed",
                    "domain": "sensor",
                    "device_class": "data_rate",
                    "update_interval": 30,
                    "base_value": 100.0,
                    "variance": 50.0,
                    "unit_of_measurement": "Mbit/s",
                    "friendly_name": "Archer BE800 Download Speed",
                },
                "sensor.archer_be800_upload_speed": {
                    "entity_id": "sensor.archer_be800_upload_speed",
                    "domain": "sensor",
                    "device_class": "data_rate",
                    "update_interval": 30,
                    "base_value": 50.0,
                    "variance": 25.0,
                    "unit_of_measurement": "Mbit/s",
                    "friendly_name": "Archer BE800 Upload Speed",
                },
                "sun.sun": {
                    "entity_id": "sun.sun",
                    "domain": "sun",
                    "device_class": None,
                    "update_interval": 300,
                    "base_value": "above_horizon",
                    "variance": None,
                    "unit_of_measurement": None,
                    "friendly_name": "Sun",
                },
                "sensor.slzb_06p7_coordinator_zigbee_chip_temp": {
                    "entity_id": "sensor.slzb_06p7_coordinator_zigbee_chip_temp",
                    "domain": "sensor",
                    "device_class": "temperature",
                    "update_interval": 60,
                    "base_value": 45.0,
                    "variance": 5.0,
                    "unit_of_measurement": "°C",
                    "friendly_name": "SLZB-06P7 Coordinator Zigbee Chip Temperature",
                },
                "sensor.home_assistant_core_cpu_percent": {
                    "entity_id": "sensor.home_assistant_core_cpu_percent",
                    "domain": "sensor",
                    "device_class": None,
                    "update_interval": 60,
                    "base_value": 15.0,
                    "variance": 10.0,
                    "unit_of_measurement": "%",
                    "friendly_name": "Home Assistant Core CPU Percent",
                },
            },
            "event_frequencies": {
                "sensor.living_room_temperature": 10,
                "sensor.wled_estimated_current": 30,
                "sensor.bar_estimated_current": 30,
                "sensor.archer_be800_download_speed": 10,
                "sensor.archer_be800_upload_speed": 10,
                "sun.sun": 2,
                "sensor.slzb_06p7_coordinator_zigbee_chip_temp": 1,
                "sensor.home_assistant_core_cpu_percent": 1,
            },
            "generated_at": datetime.now().isoformat(),
            "source": "default_patterns",
        }

