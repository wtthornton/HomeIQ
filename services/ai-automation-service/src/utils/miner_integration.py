"""
Automation Miner Integration Utilities

Utilities for integrating automation-miner with AI automation service.
Provides functions to fetch community data and enrich pattern generation.
"""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class MinerIntegration:
    """
    Integration with automation-miner service.

    Provides methods to:
    - Fetch community automations
    - Get usage statistics for devices
    - Find similar automations
    - Enrich LLM prompts with community examples
    """

    def __init__(self, miner_url: str = "http://localhost:8029"):
        """
        Initialize miner integration.

        Args:
            miner_url: Base URL for automation-miner service
        """
        self.miner_url = miner_url
        self.client = httpx.AsyncClient(timeout=10.0)
        self._available = None  # Cache availability check

    async def is_available(self) -> bool:
        """
        Check if automation-miner service is available.

        Returns:
            True if service is reachable
        """
        if self._available is not None:
            return self._available

        try:
            response = await self.client.get(
                f"{self.miner_url}/health",
                timeout=2.0
            )
            self._available = response.status_code == 200
            return self._available
        except Exception as e:
            logger.debug(f"Automation miner not available: {e}")
            self._available = False
            return False

    async def search_automations(
        self,
        device: str | None = None,
        use_case: str | None = None,
        min_quality: float = 0.7,
        limit: int = 50
    ) -> list[dict[str, Any]]:
        """
        Search community automations.

        Args:
            device: Filter by device type
            use_case: Filter by use case (energy, comfort, security, convenience)
            min_quality: Minimum quality score (0.0-1.0)
            limit: Maximum results

        Returns:
            List of automation metadata dictionaries
        """
        if not await self.is_available():
            logger.warning("Automation miner not available")
            return []

        try:
            params = {
                "min_quality": min_quality,
                "limit": limit
            }

            if device:
                params["device"] = device

            if use_case:
                params["use_case"] = use_case

            response = await self.client.get(
                f"{self.miner_url}/api/automation-miner/corpus/search",
                params=params
            )

            response.raise_for_status()
            data = response.json()

            return data.get("automations", [])

        except Exception as e:
            logger.error(f"Failed to search automations: {e}")
            return []

    async def get_device_usage_stats(
        self,
        device: str
    ) -> dict[str, Any]:
        """
        Get usage statistics for a device type from community.

        Args:
            device: Device type (e.g., 'light', 'motion_sensor')

        Returns:
            Dictionary with usage statistics
        """
        automations = await self.search_automations(device=device, limit=100)

        if not automations:
            return {
                "device": device,
                "total_automations": 0,
                "common_patterns": [],
                "avg_complexity": "unknown"
            }

        # Analyze automations
        use_cases = [a.get("use_case") for a in automations]
        complexities = [a.get("complexity") for a in automations]

        from collections import Counter

        use_case_counts = Counter(use_cases)
        complexity_counts = Counter(complexities)

        return {
            "device": device,
            "total_automations": len(automations),
            "common_use_cases": dict(use_case_counts.most_common(3)),
            "common_complexity": complexity_counts.most_common(1)[0][0] if complexity_counts else "unknown",
            "avg_quality": sum(a.get("quality_score", 0) for a in automations) / len(automations)
        }

    async def get_similar_automations(
        self,
        devices: list[str],
        limit: int = 5
    ) -> list[dict[str, Any]]:
        """
        Find similar automations based on device types.

        Args:
            devices: List of device types to match
            limit: Maximum results

        Returns:
            List of similar automation metadata
        """
        # Search for each device and combine results
        all_automations = []

        for device in devices:
            autos = await self.search_automations(device=device, limit=limit * 2)
            all_automations.extend(autos)

        # Deduplicate by ID
        seen_ids = set()
        unique_automations = []

        for auto in all_automations:
            auto_id = auto.get("id")
            if auto_id not in seen_ids:
                seen_ids.add(auto_id)
                unique_automations.append(auto)

        # Sort by quality
        unique_automations.sort(key=lambda x: x.get("quality_score", 0), reverse=True)

        return unique_automations[:limit]

    async def enrich_llm_prompt(
        self,
        base_prompt: str,
        devices: list[str]
    ) -> str:
        """
        Enrich LLM prompt with community examples.

        Args:
            base_prompt: Original LLM prompt
            devices: Device types mentioned in request

        Returns:
            Enhanced prompt with community examples
        """
        if not await self.is_available():
            return base_prompt

        # Find similar community automations
        similar = await self.get_similar_automations(devices, limit=2)

        if not similar:
            return base_prompt

        # Add community examples section
        examples_section = "\n\n**Community Examples:**\n"
        examples_section += "Here are similar automations from the community:\n\n"

        for i, auto in enumerate(similar, 1):
            examples_section += f"{i}. {auto.get('title', 'Untitled')}\n"
            examples_section += f"   Description: {auto.get('description', '')[:100]}...\n"
            examples_section += f"   Devices: {', '.join(auto.get('devices', []))}\n"
            examples_section += f"   Quality: {auto.get('quality_score', 0):.2f}\n\n"

        # Insert before output format section
        if "**Output Format" in base_prompt:
            parts = base_prompt.split("**Output Format")
            return parts[0] + examples_section + "**Output Format" + parts[1]
        else:
            return base_prompt + examples_section

    async def search_blueprints(
        self,
        device: str | None = None,
        use_case: str | None = None,
        min_quality: float = 0.7,
        limit: int = 10
    ) -> list[dict[str, Any]]:
        """
        Search for Home Assistant blueprints from automation-miner.

        Args:
            device: Filter by device type (e.g., 'light', 'motion_sensor')
            use_case: Filter by use case (energy, comfort, security, convenience)
            min_quality: Minimum quality score (0.0-1.0)
            limit: Maximum results (1-500)

        Returns:
            List of blueprint metadata dictionaries with _blueprint_metadata and _blueprint_variables
        """
        if not await self.is_available():
            logger.warning("Automation miner not available for blueprint search")
            return []

        try:
            params = {
                "min_quality": min_quality,
                "limit": limit
            }

            if device:
                params["device"] = device

            if use_case:
                params["use_case"] = use_case

            response = await self.client.get(
                f"{self.miner_url}/api/automation-miner/corpus/blueprints",
                params=params
            )

            response.raise_for_status()
            data = response.json()

            # Return only blueprints (those with _blueprint_metadata)
            blueprints = []
            for automation in data.get("automations", []):
                metadata = automation.get("metadata", {})
                if "_blueprint_metadata" in metadata:
                    blueprints.append(automation)

            return blueprints

        except Exception as e:
            logger.error(f"Failed to search blueprints: {e}")
            return []

    async def get_corpus_stats(self) -> dict[str, Any]:
        """
        Get overall corpus statistics.

        Returns:
            Dictionary with corpus statistics
        """
        if not await self.is_available():
            return {"available": False}

        try:
            response = await self.client.get(
                f"{self.miner_url}/api/automation-miner/corpus/stats"
            )

            response.raise_for_status()
            stats = response.json()

            return {
                "available": True,
                **stats
            }

        except Exception as e:
            logger.error(f"Failed to get corpus stats: {e}")
            return {"available": False, "error": str(e)}

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


def get_miner_integration(miner_url: str = "http://localhost:8029") -> MinerIntegration:
    """Factory function to create miner integration"""
    return MinerIntegration(miner_url)
