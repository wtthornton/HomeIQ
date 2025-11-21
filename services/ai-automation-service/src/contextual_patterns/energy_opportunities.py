"""
Energy Opportunity Detector

Detects energy price-aware automation opportunities for cost optimization.

Epic AI-3: Cross-Device Synergy & Contextual Opportunities
Story AI3.6: Energy Price Context Integration
"""

import logging
import uuid

logger = logging.getLogger(__name__)


class EnergyOpportunityDetector:
    """
    Detects energy price-aware automation opportunities.

    Uses electricity pricing data from InfluxDB to suggest off-peak
    scheduling for high-power devices.

    Story AI3.6: Energy Price Context Integration
    """

    def __init__(
        self,
        influxdb_client,
        data_api_client,
        peak_price_threshold: float = 0.15,  # $/kWh
        min_confidence: float = 0.7,
    ):
        """Initialize energy opportunity detector."""
        self.influxdb = influxdb_client
        self.data_api = data_api_client
        self.peak_threshold = peak_price_threshold
        self.min_confidence = min_confidence

        # Cache
        self._pricing_cache = None
        self._high_power_devices_cache = None

        logger.info(f"EnergyOpportunityDetector initialized: peak_threshold=${peak_price_threshold}/kWh")

    async def detect_opportunities(self) -> list[dict]:
        """
        Detect energy price-aware opportunities.

        Returns:
            List of energy opportunity dictionaries
        """
        logger.info("⚡ Starting energy opportunity detection...")

        try:
            # Get pricing data (if available)
            pricing_data = await self._get_pricing_data()

            if not pricing_data:
                logger.info("ℹ️  No energy pricing data, skipping energy opportunities")
                return []

            # Get high-power devices
            high_power_devices = await self._get_high_power_devices()

            if not high_power_devices:
                logger.info("ℹ️  No high-power devices found")
                return []

            opportunities = []

            # For each high-power device, suggest off-peak scheduling
            for device in high_power_devices:
                opportunities.append({
                    "synergy_id": str(uuid.uuid4()),
                    "synergy_type": "energy_context",
                    "devices": [device["entity_id"]],
                    "action_entity": device["entity_id"],
                    "area": device.get("area_id", "unknown"),
                    "relationship": "offpeak_scheduling",
                    "impact_score": 0.80,  # High - cost savings
                    "complexity": "medium",
                    "confidence": 0.82,
                    "opportunity_metadata": {
                        "action_name": device.get("friendly_name", device["entity_id"]),
                        "energy_context": "High-power device with variable electricity pricing",
                        "suggested_action": "Schedule during off-peak hours (2-6 AM)",
                        "estimated_savings": "$10-15/month",
                        "rationale": f"Schedule {device.get('friendly_name', device['entity_id'])} during off-peak hours to reduce electricity costs",
                    },
                })

            logger.info(f"✅ Energy opportunities: {len(opportunities)}")
            return opportunities

        except Exception as e:
            logger.exception(f"❌ Energy opportunity detection failed: {e}")
            return []

    async def _get_pricing_data(self) -> list[dict]:
        """Get electricity pricing data from InfluxDB."""
        # Simplified - check if pricing data exists
        try:
            query = """
            from(bucket: "home_assistant_events")
              |> range(start: -7d)
              |> filter(fn: (r) => r["_measurement"] == "electricity_price")
              |> limit(n: 1)
            """

            result = self.influxdb.query_api.query(query, org=self.influxdb.org)

            has_data = False
            for table in result:
                if len(table.records) > 0:
                    has_data = True
                    break

            return [{"has_pricing": has_data}] if has_data else []

        except Exception as e:
            logger.debug(f"Energy pricing query failed: {e}")
            return []

    async def _get_high_power_devices(self) -> list[dict]:
        """Get high-power devices (switches, appliances)."""
        try:
            entities = await self.data_api.fetch_entities()

            # Filter for high-power device types
            return [
                e for e in entities
                if any(keyword in e["entity_id"].lower() for keyword in [
                    "dishwasher", "washer", "dryer", "water_heater",
                    "ev_charger", "pool_pump", "ac_unit",
                ])
            ]


        except Exception as e:
            logger.warning(f"Failed to get high-power devices: {e}")
            return []

