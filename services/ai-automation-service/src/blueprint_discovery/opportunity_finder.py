"""
Blueprint Opportunity Finder Service

Discovers blueprint opportunities from user device inventory.
Scans devices, searches blueprints, calculates fit scores.

Epic AI-6 Story AI6.1: Blueprint Opportunity Discovery Service Foundation
"""

import logging
from datetime import datetime, timezone
from typing import Any

from ..clients.data_api_client import DataAPIClient
from ..utils.miner_integration import MinerIntegration

logger = logging.getLogger(__name__)


class BlueprintOpportunityFinder:
    """
    Discovers blueprint opportunities from user device inventory.
    
    Scans devices, searches blueprints, calculates fit scores.
    """

    def __init__(
        self,
        data_api_client: DataAPIClient,
        miner: MinerIntegration
    ):
        """
        Initialize blueprint opportunity finder.

        Args:
            data_api_client: DataAPIClient for fetching device inventory
            miner: MinerIntegration instance for blueprint searches
        """
        self.data_api = data_api_client
        self.miner = miner
        self._device_cache: list[dict[str, Any]] | None = None
        self._entity_cache: list[dict[str, Any]] | None = None
        self._cache_timestamp: datetime | None = None
        self._cache_ttl = 300.0  # 5 minutes in seconds

    async def find_opportunities(
        self,
        min_fit_score: float = 0.6,
        min_blueprint_quality: float = 0.7,
        limit: int = 50
    ) -> list[dict[str, Any]]:
        """
        Discover blueprint opportunities from device inventory.

        Args:
            min_fit_score: Minimum fit score to include (0.0-1.0)
            min_blueprint_quality: Minimum blueprint quality score (0.0-1.0)
            limit: Maximum number of opportunities to return

        Returns:
            List of opportunity dictionaries with blueprint, fit_score, and metadata
        """
        try:
            # 1. Scan devices and entities
            devices, entities = await self._scan_devices()
            if not devices and not entities:
                logger.warning("No devices or entities found in inventory")
                return []

            # 2. Extract device types and integrations
            device_types, integrations = self._extract_device_info(devices, entities)

            if not device_types:
                logger.warning("No device types extracted from inventory")
                return []

            # 3. Search blueprints
            blueprints = await self._search_blueprints(
                device_types=device_types,
                min_quality=min_blueprint_quality
            )

            if not blueprints:
                logger.info("No blueprints found matching device types")
                return []

            # 4. Calculate fit scores for each blueprint
            opportunities = []
            for blueprint in blueprints:
                fit_score = self._calculate_fit_score(
                    blueprint=blueprint,
                    device_types=device_types,
                    integrations=integrations
                )

                if fit_score >= min_fit_score:
                    opportunities.append({
                        "blueprint": blueprint,
                        "fit_score": fit_score,
                        "device_types": device_types,
                        "integrations": integrations,
                        "metadata": blueprint.get("metadata", {})
                    })

            # 5. Sort by fit score descending
            opportunities.sort(key=lambda x: x["fit_score"], reverse=True)

            # 6. Return top opportunities
            result = opportunities[:limit]
            logger.info(
                f"Found {len(result)} blueprint opportunities "
                f"(fit_score >= {min_fit_score}, limit={limit})"
            )
            return result

        except Exception as e:
            logger.error(f"Failed to discover blueprint opportunities: {e}", exc_info=True)
            return []

    async def _scan_devices(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """
        Scan user device and entity inventory from Data API.

        Returns:
            Tuple of (devices list, entities list) with caching (5 min TTL)
        """
        # Check cache validity
        now = datetime.now(timezone.utc)
        if (self._device_cache is not None and
            self._cache_timestamp is not None and
            (now - self._cache_timestamp).total_seconds() < self._cache_ttl):
            logger.debug("Using cached device/entity inventory")
            # Return cached devices and entities
            return self._device_cache, self._entity_cache

        try:
            logger.info("Scanning device and entity inventory from Data API...")
            devices = await self.data_api.fetch_devices(limit=1000)
            entities = await self.data_api.fetch_entities(limit=5000)
            
            # Cache the result
            self._device_cache = devices
            self._entity_cache = entities
            self._cache_timestamp = now
            
            logger.info(
                f"Scanned {len(devices)} devices and {len(entities)} entities "
                f"(cached for 5 minutes)"
            )
            return devices, entities

        except Exception as e:
            logger.error(f"Failed to scan devices/entities: {e}", exc_info=True)
            # Return cached data if available, even if expired
            if self._device_cache is not None:
                logger.warning("Using expired cache due to fetch failure")
                return self._device_cache, self._entity_cache or []
            return [], []

    def _extract_device_info(
        self,
        devices: list[dict[str, Any]],
        entities: list[dict[str, Any]]
    ) -> tuple[list[str], list[str]]:
        """
        Extract device types and integrations from device and entity inventory.

        Args:
            devices: List of device dictionaries
            entities: List of entity dictionaries with domain and platform info

        Returns:
            Tuple of (device_types list, integrations list)
        """
        device_types_set = set()
        integrations_set = set()

        try:
            # Extract device types (domains) from entities
            for entity in entities:
                # Extract domain from entity_id (format: domain.entity_name)
                entity_id = entity.get("entity_id", "")
                if "." in entity_id:
                    domain = entity_id.split(".")[0]
                    device_types_set.add(domain)

                # Extract platform/integration from entity
                platform = entity.get("platform")
                if platform:
                    # Normalize platform name (remove common prefixes/suffixes)
                    platform_clean = platform.lower().split(".")[0].split("_")[0]
                    integrations_set.add(platform_clean)

            # Fallback: Extract device type from device name/model if no entities
            if not device_types_set:
                for device in devices:
                    name = device.get("name", "").lower()
                    model = device.get("model", "").lower()
                    
                    # Common device type keywords
                    if any(keyword in name or keyword in model for keyword in ["light", "bulb", "lamp"]):
                        device_types_set.add("light")
                    if any(keyword in name or keyword in model for keyword in ["switch", "outlet"]):
                        device_types_set.add("switch")
                    if any(keyword in name or keyword in model for keyword in ["sensor", "motion"]):
                        device_types_set.add("binary_sensor")
                    if any(keyword in name or keyword in model for keyword in ["thermostat", "climate"]):
                        device_types_set.add("climate")
                    if any(keyword in name or keyword in model for keyword in ["lock"]):
                        device_types_set.add("lock")

            # Fallback: Extract integration from device manufacturer if no platform info
            if not integrations_set:
                for device in devices:
                    manufacturer = device.get("manufacturer", "").lower()
                    model = device.get("model", "").lower()
                    
                    if "hue" in manufacturer or "philips" in manufacturer:
                        integrations_set.add("hue")
                    elif "zwave" in model or "zwave" in manufacturer:
                        integrations_set.add("zwave")
                    elif "zigbee" in model or "zigbee" in manufacturer:
                        integrations_set.add("zigbee")
                    elif "tuya" in manufacturer or "smart life" in manufacturer:
                        integrations_set.add("tuya")
                    elif "nest" in manufacturer or "google" in manufacturer:
                        integrations_set.add("nest")

        except Exception as e:
            logger.warning(f"Error extracting device info: {e}", exc_info=True)

        device_types = sorted(list(device_types_set))
        integrations = sorted(list(integrations_set))

        logger.debug(f"Extracted {len(device_types)} device types, {len(integrations)} integrations")
        return device_types, integrations

    async def _search_blueprints(
        self,
        device_types: list[str],
        min_quality: float = 0.7
    ) -> list[dict[str, Any]]:
        """
        Search blueprints matching device types.

        Args:
            device_types: List of device type strings (e.g., ['light', 'sensor'])
            min_quality: Minimum blueprint quality score

        Returns:
            List of blueprint dictionaries
        """
        # Check if automation-miner is available
        if not await self.miner.is_available():
            logger.warning("Automation-miner service unavailable, skipping blueprint search")
            return []

        all_blueprints = []
        seen_ids = set()

        try:
            # Batch search for each device type
            for device_type in device_types:
                blueprints = await self.miner.search_blueprints(
                    device=device_type,
                    min_quality=min_quality,
                    limit=50  # Get more results per device type for better matching
                )

                # Deduplicate by blueprint ID
                for blueprint in blueprints:
                    blueprint_id = blueprint.get("id")
                    if blueprint_id and blueprint_id not in seen_ids:
                        seen_ids.add(blueprint_id)
                        all_blueprints.append(blueprint)

            logger.info(f"Searched {len(device_types)} device types, found {len(all_blueprints)} unique blueprints")
            return all_blueprints

        except Exception as e:
            logger.error(f"Failed to search blueprints: {e}", exc_info=True)
            return []

    def _calculate_fit_score(
        self,
        blueprint: dict[str, Any],
        device_types: list[str],
        integrations: list[str]
    ) -> float:
        """
        Calculate fit score (0.0-1.0) for blueprint opportunity.

        Formula:
        - Device type compatibility: 60% weight
        - Integration compatibility: 20% weight
        - Use case relevance: 10% weight
        - Blueprint quality score: 10% weight

        Args:
            blueprint: Blueprint dictionary from automation-miner
            device_types: List of user's device types
            integrations: List of user's integrations

        Returns:
            Fit score between 0.0 and 1.0
        """
        try:
            metadata = blueprint.get("metadata", {})
            blueprint_metadata = metadata.get("_blueprint_metadata", {})
            
            # Extract blueprint device requirements
            blueprint_vars = metadata.get("_blueprint_variables", {})
            blueprint_devices = metadata.get("_blueprint_devices", [])
            
            # If no explicit blueprint devices list, extract from variables
            if not blueprint_devices and blueprint_vars:
                blueprint_devices = []
                for var_name, var_spec in blueprint_vars.items():
                    domain = var_spec.get("domain")
                    if domain and domain not in blueprint_devices:
                        blueprint_devices.append(domain)

            # 1. Device type compatibility (60% weight)
            device_compatibility = self._calculate_device_type_compatibility(
                blueprint_devices=blueprint_devices,
                user_device_types=device_types
            )

            # 2. Integration compatibility (20% weight)
            integration_compatibility = self._calculate_integration_compatibility(
                blueprint=blueprint,
                user_integrations=integrations
            )

            # 3. Use case relevance (10% weight)
            use_case_relevance = self._calculate_use_case_relevance(blueprint)

            # 4. Blueprint quality score (10% weight)
            quality_score = blueprint.get("quality_score", 0.7)
            # Normalize quality score (assume 0.7-1.0 range maps to 0.0-1.0)
            normalized_quality = max(0.0, min(1.0, (quality_score - 0.7) / 0.3))

            # Weighted fit score
            fit_score = (
                device_compatibility * 0.6 +
                integration_compatibility * 0.2 +
                use_case_relevance * 0.1 +
                normalized_quality * 0.1
            )

            return min(max(fit_score, 0.0), 1.0)  # Clamp to [0.0, 1.0]

        except Exception as e:
            logger.warning(f"Error calculating fit score: {e}", exc_info=True)
            return 0.0

    def _calculate_device_type_compatibility(
        self,
        blueprint_devices: list[str],
        user_device_types: list[str]
    ) -> float:
        """Calculate device type compatibility score (0.0-1.0)."""
        if not blueprint_devices or not user_device_types:
            return 0.0

        # Normalize device types (lowercase, extract domain)
        blueprint_domains = {d.lower().split(".")[0] for d in blueprint_devices}
        user_domains = {d.lower().split(".")[0] for d in user_device_types}

        # Calculate overlap
        overlap = blueprint_domains.intersection(user_domains)
        total_required = len(blueprint_domains)

        if total_required == 0:
            return 0.0

        # Score based on how many required devices the user has
        compatibility = len(overlap) / total_required
        return min(compatibility, 1.0)

    def _calculate_integration_compatibility(
        self,
        blueprint: dict[str, Any],
        user_integrations: list[str]
    ) -> float:
        """Calculate integration compatibility score (0.0-1.0)."""
        if not user_integrations:
            return 0.5  # Neutral if no integration info

        # Extract integration requirements from blueprint
        metadata = blueprint.get("metadata", {})
        blueprint_description = metadata.get("_blueprint_metadata", {}).get("description", "").lower()
        
        # Check if blueprint mentions specific integrations
        blueprint_integrations = set()
        integration_keywords = {
            "hue": ["hue", "philips"],
            "zwave": ["zwave", "z-wave"],
            "zigbee": ["zigbee"],
            "tuya": ["tuya", "smart life"],
            "nest": ["nest", "google"]
        }

        for integration, keywords in integration_keywords.items():
            if any(keyword in blueprint_description for keyword in keywords):
                blueprint_integrations.add(integration)

        # If no specific integration requirements, return neutral score
        if not blueprint_integrations:
            return 0.5

        # Check if user has any matching integrations
        user_integrations_lower = {i.lower() for i in user_integrations}
        blueprint_integrations_lower = {i.lower() for i in blueprint_integrations}

        overlap = user_integrations_lower.intersection(blueprint_integrations_lower)
        if overlap:
            return 1.0  # Perfect match
        else:
            return 0.2  # Partial penalty for mismatch

    def _calculate_use_case_relevance(self, blueprint: dict[str, Any]) -> float:
        """Calculate use case relevance score (0.0-1.0)."""
        # Extract use case from blueprint metadata
        use_case = blueprint.get("use_case", "")
        
        # If use case is specified, return high relevance
        if use_case:
            return 0.8
        
        # Otherwise, neutral score
        return 0.5

