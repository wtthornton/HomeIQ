"""
Device Recommender

Analyzes user's device inventory and recommends devices based on:
- Automation potential (how many automations unlocked)
- Quality of automations
- ROI calculation (value / cost)

Epic AI-4, Story AI4.3
"""
import json
import logging
from collections import Counter
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from ..miner.repository import CorpusRepository

logger = logging.getLogger(__name__)


class DeviceRecommendation(BaseModel):
    """Device purchase recommendation with ROI"""

    device_type: str
    automations_unlocked: int
    example_use_cases: list[str]  # Top 3 use cases
    cost_estimate_usd: tuple[int, int]  # (min, max)
    roi_score: float
    compatible_integrations: list[str]
    example_automations: list[dict[str, Any]] = Field(default_factory=list)  # Top 3

    class Config:
        json_schema_extra = {
            "example": {
                "device_type": "motion_sensor",
                "automations_unlocked": 120,
                "example_use_cases": ["security", "energy", "comfort"],
                "cost_estimate_usd": [15, 35],
                "roi_score": 2.77,
                "compatible_integrations": ["mqtt", "zigbee2mqtt", "zha"],
                "example_automations": []
            }
        }


class DeviceRecommender:
    """Recommend devices based on automation potential"""

    def __init__(self, corpus_repo: CorpusRepository):
        """
        Initialize device recommender
        
        Args:
            corpus_repo: CorpusRepository for querying automations
        """
        self.repo = corpus_repo
        self.device_costs = self._load_device_costs()

    def _load_device_costs(self) -> dict[str, tuple[int, int]]:
        """
        Load device cost estimates from JSON file
        
        Returns:
            Dictionary mapping device types to (min_cost, max_cost) tuples
            Falls back to default costs if file cannot be loaded
        """
        costs_file = Path(__file__).parent.parent.parent / "data" / "device_costs.json"

        if not costs_file.exists():
            logger.warning(f"Device costs file not found: {costs_file}. Using default costs.")
            return {}

        try:
            with open(costs_file, encoding='utf-8') as f:
                data = json.load(f)

            # Validate and convert to tuple format
            costs = {}
            for k, v in data.items():
                if isinstance(v, list) and len(v) == 2:
                    try:
                        min_cost = int(v[0])
                        max_cost = int(v[1])
                        if min_cost > 0 and max_cost >= min_cost:
                            costs[k] = (min_cost, max_cost)
                        else:
                            logger.warning(f"Invalid cost range for {k}: {v}. Skipping.")
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid cost format for {k}: {v}. Skipping.")
                else:
                    logger.warning(f"Invalid cost entry for {k}: {v}. Expected [min, max]. Skipping.")

            logger.info(f"Loaded {len(costs)} device cost entries from {costs_file}")
            return costs

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse device costs JSON file {costs_file}: {e}. Using default costs.")
            return {}
        except Exception as e:
            logger.error(f"Failed to load device costs from {costs_file}: {e}. Using default costs.", exc_info=True)
            return {}

    async def recommend_devices(
        self,
        user_devices: list[str],
        user_integrations: list[str],
        limit: int = 10
    ) -> list[DeviceRecommendation]:
        """
        Recommend devices to purchase based on automation potential
        
        Args:
            user_devices: List of device types user currently has
            user_integrations: List of integrations user has configured
            limit: Maximum recommendations to return
        
        Returns:
            List of DeviceRecommendation objects, sorted by ROI score
        """
        logger.info(f"Generating device recommendations for user with {len(user_devices)} devices")

        # Get all high-quality automations
        all_automations = await self.repo.get_all(min_quality=0.5)

        logger.info(f"Analyzing {len(all_automations)} automations from corpus")

        # Map: device_type -> list of automations that require it
        device_unlock_map: dict[str, list] = {}

        for auto in all_automations:
            # Check if user can already do this automation
            auto_devices = auto.devices if hasattr(auto, 'devices') else []

            if all(d in user_devices for d in auto_devices):
                continue  # User can already do this

            # Find missing devices
            missing = [d for d in auto_devices if d not in user_devices]

            for missing_device in missing:
                if missing_device not in device_unlock_map:
                    device_unlock_map[missing_device] = []
                device_unlock_map[missing_device].append(auto)

        logger.info(f"Found {len(device_unlock_map)} device types that unlock new automations")

        # Calculate ROI for each device
        recommendations = []

        for device_type, unlocked_autos in device_unlock_map.items():
            if len(unlocked_autos) < 5:  # Minimum threshold (was 10, reduced for testing)
                continue

            # Average quality of unlocked automations
            total_quality = sum(
                auto.quality_score if hasattr(auto, 'quality_score') else 0.0
                for auto in unlocked_autos
            )
            avg_quality = total_quality / len(unlocked_autos) if unlocked_autos else 0.0

            # Estimate usage frequency (simplistic: high quality = more useful)
            use_frequency = avg_quality * 0.8  # 0.0-0.8 scale

            # Get cost estimate
            cost_range = self.device_costs.get(device_type, (20, 50))  # Default $20-50
            avg_cost = (cost_range[0] + cost_range[1]) / 2

            # ROI calculation
            # ROI = (automations_unlocked × avg_quality × use_frequency) / avg_cost
            roi = (len(unlocked_autos) * avg_quality * use_frequency) / avg_cost if avg_cost > 0 else 0

            # Extract use cases
            use_cases = []
            for auto in unlocked_autos:
                if hasattr(auto, 'use_case'):
                    use_cases.append(auto.use_case)
            use_case_counter = Counter(use_cases)
            top_use_cases = [uc for uc, count in use_case_counter.most_common(3)]

            # Compatible integrations
            integrations = set()
            for auto in unlocked_autos:
                if hasattr(auto, 'integrations'):
                    integrations.update(auto.integrations)

            # Top 3 example automations
            sorted_examples = sorted(
                unlocked_autos,
                key=lambda a: a.quality_score if hasattr(a, 'quality_score') else 0,
                reverse=True
            )[:3]

            example_automations = []
            for auto in sorted_examples:
                example_automations.append({
                    'title': auto.title if hasattr(auto, 'title') else 'Unknown',
                    'quality_score': auto.quality_score if hasattr(auto, 'quality_score') else 0.0,
                    'use_case': auto.use_case if hasattr(auto, 'use_case') else 'unknown'
                })

            recommendations.append(DeviceRecommendation(
                device_type=device_type,
                automations_unlocked=len(unlocked_autos),
                example_use_cases=top_use_cases,
                cost_estimate_usd=cost_range,
                roi_score=round(roi, 2),
                compatible_integrations=sorted(list(integrations)),
                example_automations=example_automations
            ))

        # Sort by ROI descending
        recommendations.sort(key=lambda r: r.roi_score, reverse=True)

        logger.info(f"Generated {len(recommendations)} device recommendations")

        return recommendations[:limit]

    async def get_device_possibilities(
        self,
        device_type: str,
        user_devices: list[str]
    ) -> list[dict[str, Any]]:
        """
        Get automation possibilities for a specific device type
        
        Args:
            device_type: Device type (e.g., "motion_sensor")
            user_devices: List of devices user currently has
        
        Returns:
            List of automation possibilities grouped by use case
        """
        logger.info(f"Getting possibilities for device: {device_type}")

        # Query corpus for automations using this device
        automations = await self.repo.search({
            'device': device_type,
            'min_quality': 0.5,
            'limit': 100
        })

        logger.info(f"Found {len(automations)} automations using {device_type}")

        # Group by use case
        by_use_case = {}
        for auto in automations:
            use_case = auto.get('use_case', 'convenience')
            if use_case not in by_use_case:
                by_use_case[use_case] = []
            by_use_case[use_case].append(auto)

        # Build possibilities
        possibilities = []

        for use_case, autos in by_use_case.items():
            # Calculate what user CAN do now vs COULD do with more devices
            required_devices = set()
            optional_devices = set()

            for auto in autos:
                auto_devices = auto.get('devices', [])
                for device in auto_devices:
                    if device != device_type:
                        if device in user_devices:
                            required_devices.add(device)
                        else:
                            optional_devices.add(device)

            # Average quality
            avg_quality = sum(a.get('quality_score', 0) for a in autos) / len(autos) if autos else 0

            # Difficulty based on required devices
            if len(required_devices) == 0:
                difficulty = 'low'
            elif len(required_devices) <= 2:
                difficulty = 'medium'
            else:
                difficulty = 'high'

            possibilities.append({
                'use_case': use_case,
                'automation_count': len(autos),
                'required_devices': sorted(list(required_devices)),
                'optional_enhancements': sorted(list(optional_devices)),
                'example_automations': autos[:3],  # Top 3
                'difficulty': difficulty,
                'avg_quality': round(avg_quality, 2)
            })

        # Sort by automation count descending
        possibilities.sort(key=lambda p: p['automation_count'], reverse=True)

        return possibilities

