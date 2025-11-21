"""
Feature Analyzer for Device Intelligence

Analyzes device instances to identify unused features and calculate utilization metrics.
Matches device instances from Home Assistant to capability definitions from device_capabilities table.

Story: AI2.3 - Device Matching & Feature Analysis
Epic: AI-2 - Device Intelligence System
"""

import logging
from datetime import datetime

from src.database.crud import get_capability_freshness

logger = logging.getLogger(__name__)


class FeatureAnalyzer:
    """
    Analyzes device instances for unused features and utilization metrics.

    Matches device instances from Home Assistant to capability definitions
    from device_capabilities table, then identifies which features are
    configured vs. available.

    Story AI2.3: Device Matching & Feature Analysis
    Epic AI-2: Device Intelligence System

    Example Usage:
        analyzer = FeatureAnalyzer(data_api_client, db_session)
        analysis = await analyzer.analyze_all_devices()
        print(f"Overall utilization: {analysis['overall_utilization']}%")
    """

    def __init__(self, device_intelligence_client, db_session, influxdb_client=None, capability_lookup_func=None):
        """
        Initialize feature analyzer.

        Args:
            device_intelligence_client: Client for querying devices from Device Intelligence Service
            db_session: SQLAlchemy async session factory
            influxdb_client: Optional InfluxDB client for historical data (Story 2.4)
            capability_lookup_func: Optional function to get capabilities (for testing)
        """
        self.device_intelligence = device_intelligence_client
        self.db = db_session
        self.influxdb = influxdb_client
        self._capability_lookup = capability_lookup_func

    async def analyze_all_devices(self) -> dict:
        """
        Analyze all devices in Home Assistant.

        Queries devices from data-api, matches to capability definitions,
        and calculates utilization metrics across all devices.

        Returns:
            Dictionary with:
            - overall_utilization: float (percentage)
            - total_devices: int (total devices from HA)
            - devices_analyzed: int (devices with capabilities)
            - total_configured: int (total configured features)
            - total_available: int (total available features)
            - by_manufacturer: Dict[str, Dict] (utilization by brand)
            - opportunities: List[Dict] (top unused features)

        Example Output:
            {
                "overall_utilization": 32.5,
                "total_devices": 99,
                "devices_analyzed": 95,
                "total_configured": 185,
                "total_available": 570,
                "by_manufacturer": {
                    "Inovelli": {
                        "utilization": 35.2,
                        "devices": 12,
                        "configured": 42,
                        "available": 119
                    },
                    "Aqara": {
                        "utilization": 38.1,
                        "devices": 15,
                        "configured": 45,
                        "available": 118
                    }
                },
                "opportunities": [
                    {
                        "device_id": "light.kitchen_switch",
                        "device_name": "Kitchen Switch",
                        "manufacturer": "Inovelli",
                        "model": "VZM31-SN",
                        "feature_name": "led_notifications",
                        "feature_type": "composite",
                        "complexity": "medium",
                        "impact": "high"
                    }
                ]
            }
        """
        logger.info("🔍 Starting device utilization analysis...")
        start_time = datetime.utcnow()

        # Get all devices from Device Intelligence Service
        devices = await self._get_devices_from_device_intelligence()
        logger.info(f"📊 Found {len(devices)} devices from Device Intelligence Service")

        if not devices:
            logger.warning("⚠️ No devices found from Device Intelligence Service")
            return {
                "overall_utilization": 0.0,
                "total_devices": 0,
                "devices_analyzed": 0,
                "total_configured": 0,
                "total_available": 0,
                "by_manufacturer": {},
                "opportunities": [],
            }

        # Guard: ensure capability data is fresh before continuing
        capability_freshness = await self._check_capability_freshness()
        if capability_freshness["total_models"] == 0:
            logger.warning(
                "⚠️ Device capability cache is empty. Skipping feature analysis until "
                "the nightly capability refresh populates data.",
            )
            return self._build_skip_result(
                devices_found=len(devices),
                reason="no_capabilities",
                stale_info=capability_freshness,
            )

        if capability_freshness["stale_count"] > 0:
            stale_preview = capability_freshness["stale_models"][:5]
            preview_text = ", ".join(model["model"] for model in stale_preview)
            logger.warning(
                "⚠️ Device capability cache has %s stale models (threshold: %s). "
                "Preview: %s",
                capability_freshness["stale_count"],
                capability_freshness["threshold_iso"],
                preview_text or "n/a",
            )
            return self._build_skip_result(
                devices_found=len(devices),
                reason="capabilities_stale",
                stale_info=capability_freshness,
            )

        total_configured = 0
        total_available = 0
        by_manufacturer = {}
        all_opportunities = []
        analyzed_count = 0

        for device in devices:
            try:
                # Pass device data to avoid redundant API call
                analysis = await self.analyze_device(device["device_id"], device_data=device)

                if analysis:
                    analyzed_count += 1
                    total_configured += analysis["configured_count"]
                    total_available += analysis["total_features"]

                    # Track by manufacturer
                    manufacturer = analysis.get("manufacturer", "Unknown")
                    if manufacturer not in by_manufacturer:
                        by_manufacturer[manufacturer] = {
                            "utilization": 0.0,
                            "devices": 0,
                            "configured": 0,
                            "available": 0,
                        }

                    by_manufacturer[manufacturer]["devices"] += 1
                    by_manufacturer[manufacturer]["configured"] += analysis["configured_count"]
                    by_manufacturer[manufacturer]["available"] += analysis["total_features"]

                    # Collect opportunities
                    all_opportunities.extend(analysis.get("opportunities", []))

            except Exception as e:
                logger.warning(f"⚠️ Failed to analyze device {device.get('device_id')}: {e}")
                continue

        # Calculate manufacturer utilizations
        for _manuf, stats in by_manufacturer.items():
            if stats["available"] > 0:
                stats["utilization"] = round(
                    (stats["configured"] / stats["available"]) * 100,
                    1,
                )

        # Calculate overall utilization
        overall_utilization = 0.0
        if total_available > 0:
            overall_utilization = round(
                (total_configured / total_available) * 100,
                1,
            )

        # Rank opportunities by impact and complexity
        ranked_opportunities = self._rank_opportunities(all_opportunities)

        duration = (datetime.utcnow() - start_time).total_seconds()

        logger.info(
            f"✅ Analysis complete in {duration:.1f}s\n"
            f"   Overall utilization: {overall_utilization}%\n"
            f"   Devices analyzed: {analyzed_count}/{len(devices)}\n"
            f"   Total features: {total_configured}/{total_available}\n"
            f"   Opportunities found: {len(ranked_opportunities)}",
        )

        return {
            "overall_utilization": overall_utilization,
            "avg_utilization": overall_utilization,
            "total_devices": len(devices),
            "devices_analyzed": analyzed_count,
            "total_configured": total_configured,
            "total_available": total_available,
            "by_manufacturer": by_manufacturer,
            "opportunities": ranked_opportunities[:20],  # Top 20
            "analysis_duration_seconds": round(duration, 2),
        }

    async def _check_capability_freshness(self) -> dict:
        """Return capability freshness stats using the shared CRUD helper."""
        async with self.db() as session:
            return await get_capability_freshness(session)

    def _build_skip_result(
        self,
        devices_found: int,
        reason: str,
        stale_info: dict,
    ) -> dict:
        """Construct a structured response when analysis is skipped."""
        return {
            "overall_utilization": 0.0,
            "avg_utilization": 0.0,
            "total_devices": devices_found,
            "devices_analyzed": 0,
            "total_configured": 0,
            "total_available": 0,
            "by_manufacturer": {},
            "opportunities": [],
            "skipped": True,
            "skip_reason": reason,
            "stale_capabilities": stale_info,
        }

    async def analyze_device(self, device_id: str, device_data: dict | None = None) -> dict | None:
        """
        Analyze single device for unused features.

        Matches device to capability definition, determines configured features,
        and calculates utilization.

        Args:
            device_id: Device entity ID (e.g., "light.kitchen_switch")

        Returns:
            Dict with analysis results or None if device has no capabilities

        Example Output:
            {
                "device_id": "light.kitchen_switch",
                "manufacturer": "Inovelli",
                "model": "VZM31-SN",
                "total_features": 8,
                "configured_count": 2,
                "utilization": 25.0,
                "unused_features": ["led_notifications", "auto_off_timer", ...],
                "opportunities": [...]
            }
        """
        # Get device metadata (use provided data or query data-api)
        device = device_data if device_data else await self._get_device_metadata(device_id)
        if not device:
            logger.debug(f"Device {device_id} not found")
            return None

        model = device.get("model")
        if not model:
            logger.debug(f"Device {device_id} has no model identifier")
            return None

        # Get capabilities for this device model
        capabilities = await self._get_capabilities_by_model(model)
        if not capabilities:
            logger.debug(f"No capabilities found for model {model}")
            return None

        # Determine configured features (simplified for Story 2.3)
        configured_features = await self._get_configured_features(device_id, device)

        # Compare configured vs. available
        available_features = set(capabilities.capabilities.keys())
        configured_set = set(configured_features)
        unused_features = available_features - configured_set

        utilization = 0.0
        if len(available_features) > 0:
            utilization = round(
                (len(configured_set) / len(available_features)) * 100,
                1,
            )

        # Create opportunities for unused features
        opportunities = []
        for feature_name in unused_features:
            feature_data = capabilities.capabilities[feature_name]
            opportunities.append({
                "device_id": device_id,
                "device_name": device.get("name", device_id),
                "manufacturer": capabilities.manufacturer,
                "model": model,
                "feature_name": feature_name,
                "feature_type": feature_data.get("type", "unknown"),
                "complexity": feature_data.get("complexity", "easy"),
                "impact": self._assess_impact(feature_name, feature_data),
            })

        return {
            "device_id": device_id,
            "manufacturer": capabilities.manufacturer,
            "model": model,
            "total_features": len(available_features),
            "configured_count": len(configured_set),
            "utilization": utilization,
            "unused_features": list(unused_features),
            "configured_features": list(configured_set),
            "opportunities": opportunities,
        }

    async def _get_devices_from_device_intelligence(self) -> list[dict]:
        """
        Query all devices from Device Intelligence Service.

        Returns:
            List of device dictionaries from Device Intelligence Service

        Example Response:
            [
                {
                    "id": "light.kitchen_switch",
                    "name": "Kitchen Switch",
                    "model": "VZM31-SN",
                    "manufacturer": "Inovelli",
                    "area_id": "kitchen",
                    "integration": "zigbee2mqtt"
                },
                ...
            ]
        """
        try:
            devices = await self.device_intelligence.get_devices()
            logger.debug(f"Retrieved {len(devices)} devices from Device Intelligence Service")
            return devices
        except Exception as e:
            logger.exception(f"❌ Failed to get devices from Device Intelligence Service: {e}")
            return []

    async def _get_device_metadata(self, device_id: str) -> dict | None:
        """
        Get device metadata from Device Intelligence Service.

        Args:
            device_id: Device entity ID

        Returns:
            Device metadata dict or None if not found
        """
        try:
            device = await self.device_intelligence.get_device_by_id(device_id)
            if device:
                logger.debug(f"Retrieved metadata for {device_id}")
            return device
        except Exception as e:
            logger.debug(f"Device {device_id} not found in Device Intelligence Service: {e}")
            return None

    async def _get_capabilities_by_model(self, model: str):
        """
        Get capabilities from database for device model.

        Args:
            model: Device model identifier (e.g., "VZM31-SN")

        Returns:
            DeviceCapability object or None if not found
        """
        # Use injected lookup function if provided (for testing)
        if self._capability_lookup:
            try:
                return await self._capability_lookup(model)
            except Exception as e:
                logger.debug(f"No capabilities found for model {model}: {e}")
                return None

        # Production: Use database session
        from src.database.crud import get_device_capability

        try:
            async with self.db() as session:
                return await get_device_capability(session, model)
        except Exception as e:
            logger.debug(f"No capabilities found for model {model}: {e}")
            return None

    async def _get_configured_features(
        self,
        device_id: str,
        device: dict,
    ) -> list[str]:
        """
        Determine which features are configured for a device.

        **SIMPLIFIED APPROACH FOR STORY 2.3:**
        - Check entity type (light, switch, climate)
        - Assume only basic features are configured
        - Mark advanced features as unconfigured

        **STORY 2.4 WILL ENHANCE:**
        - Query HA entity attributes
        - Check automation triggers
        - Analyze historical usage patterns

        Args:
            device_id: Device entity ID
            device: Device metadata from data-api

        Returns:
            List of feature names that appear to be configured

        Example:
            For "light.kitchen_switch" → ["light_control"]
            For "climate.thermostat" → ["climate_control"]
        """
        configured = []
        entity_id = device.get("entity_id", device_id)

        # Detect basic features by entity type
        if entity_id.startswith("light."):
            configured.append("light_control")
        elif entity_id.startswith("switch."):
            configured.append("switch_control")
        elif entity_id.startswith("climate."):
            configured.append("climate_control")
        elif entity_id.startswith("binary_sensor."):
            # Check sensor type
            if "contact" in entity_id.lower():
                configured.append("contact")
            if "motion" in entity_id.lower():
                configured.append("occupancy")

        logger.debug(f"Device {device_id}: {len(configured)} configured features detected (simplified)")

        # Story 2.4 will add:
        # - Query HA for entity attributes
        # - Check if 'smartBulbMode' attribute exists → smart_bulb_mode configured
        # - Check if 'led_effect' attribute exists → led_notifications configured
        # - etc.

        return configured

    def _assess_impact(self, feature_name: str, feature_data: dict) -> str:
        """
        Assess impact of enabling a feature.

        Uses keyword-based heuristics to estimate user value.

        Args:
            feature_name: Feature name (e.g., "led_notifications")
            feature_data: Feature capability data

        Returns:
            "high" | "medium" | "low"

        Heuristics:
            - High: notifications, alerts, automation, energy management
            - Medium: timers, modes, presets, scheduling
            - Low: minor tweaks, cosmetic settings
        """
        high_impact_keywords = [
            "led", "notification", "alert", "automation",
            "energy", "power", "status", "indicator",
        ]
        medium_impact_keywords = [
            "timer", "mode", "preset", "schedule", "delay",
            "duration", "threshold", "sensitivity",
        ]

        name_lower = feature_name.lower()

        # Check for high impact features
        if any(kw in name_lower for kw in high_impact_keywords):
            return "high"

        # Check for medium impact features
        if any(kw in name_lower for kw in medium_impact_keywords):
            return "medium"

        # Default to low impact
        return "low"

    def _rank_opportunities(self, opportunities: list[dict]) -> list[dict]:
        """
        Rank opportunities by impact and complexity.

        Priority formula:
        - High impact + Easy complexity = 9 points (Top priority!)
        - High impact + Medium complexity = 6 points
        - Medium impact + Easy complexity = 6 points
        - High impact + Advanced complexity = 3 points
        - Medium impact + Medium complexity = 4 points
        - Low impact = 1-3 points

        Args:
            opportunities: List of opportunity dicts

        Returns:
            Sorted list of opportunities (highest priority first)

        Example:
            [
                {priority_score: 9, feature: "led_notifications", impact: "high", complexity: "easy"},
                {priority_score: 6, feature: "auto_off_timer", impact: "high", complexity: "medium"},
                {priority_score: 6, feature: "smart_bulb_mode", impact: "medium", complexity: "easy"},
                ...
            ]
        """
        def priority_score(opp):
            impact_scores = {"high": 3, "medium": 2, "low": 1}
            complexity_scores = {"easy": 3, "medium": 2, "advanced": 1}

            impact = impact_scores.get(opp.get("impact", "low"), 1)
            complexity = complexity_scores.get(opp.get("complexity", "medium"), 2)

            return impact * complexity  # Max = 9 (high impact + easy)

        # Sort by priority score (highest first)
        ranked = sorted(opportunities, key=priority_score, reverse=True)

        logger.debug(
            f"Ranked {len(ranked)} opportunities "
            f"(top priority: {priority_score(ranked[0]) if ranked else 0})",
        )

        return ranked

