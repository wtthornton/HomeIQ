"""
AI Name Suggester

TAP-7275: name generation runs as the AgentForge `device-name-suggest`
workflow. This service holds no OpenAI credential and no provider SDK; what
stays here is the device record it builds, the naming convention it enforces,
and the `strip_brands` guard that is applied to every name the gene returns --
a prompt forbidding brands is a request, not a guarantee, so the rule is
enforced in code (TAP-6234 round 3).
"""

import json
import logging
from typing import Any

import httpx

from ...models.database import Device, DeviceEntity
from ..naming_convention.name_builder import strip_brands
from .name_generator import NameSuggestion

logger = logging.getLogger(__name__)

WORKFLOW_DEVICE_NAME = "device-name-suggest"

#: The naming convention handed to the gene as a workflow input. It used to be
#: the system prompt of a provider call; it is data now, and the gene's own
#: instructions own how to apply it.
NAMING_CONVENTION = """Use natural, conversational language.
Include the location when it helps uniqueness.
Be descriptive but concise: two to four words is ideal.
Avoid technical terms and model numbers.
NEVER include a brand or manufacturer word (Hue, Aqara, IKEA, Sonoff, ...) -- the
HomeIQ naming rubric penalises them.
Make the device's purpose obvious.

Examples:
- "Hue Color Downlight 1 7" -> "Office Back Left Light"
- "TRADFRI bulb E27 WS opal" -> "Kitchen Ceiling Light"
- "Xiaomi Motion Sensor" -> "Front Door Motion Sensor"
"""


class AINameSuggester:
    """AI name generation with 2025 optimizations"""

    def __init__(self, settings: Any):
        self.settings = settings
        self.agentforge_url = getattr(settings, "AGENTFORGE_URL", "http://localhost:8010").rstrip(
            "/"
        )
        key = getattr(settings, "AGENTFORGE_API_KEY", None)
        self.api_key = (
            key.get_secret_value()
            if key is not None and hasattr(key, "get_secret_value")
            else (key or "")
        )
        self.project_slug = getattr(settings, "AGENTFORGE_PROJECT_SLUG", "homeiq")
        self.timeout = float(getattr(settings, "AGENTFORGE_TIMEOUT", 180.0))
        if not self.api_key:
            logger.warning(
                "AGENTFORGE_API_KEY not set - AI name suggestion unavailable; "
                "the deterministic name generator still runs."
            )

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    async def suggest_name(
        self,
        device: Device,
        entity: DeviceEntity | None = None,
        context: dict[str, Any] | None = None,
    ) -> list[NameSuggestion]:
        """
        Generate name suggestions with 2025 optimizations.

        Cost Strategy:
        - Use GPT-4o-mini: $0.15/1M input (cost-optimized)
        - Enable prompt caching: 90% discount on cached inputs
        - Generate 3 suggestions per device

        Performance:
        - With caching: 0.5-1s per device
        - Without caching: 1-2s per device
        - Local LLM: 3-5s per device (no cost)
        """
        if not self.configured:
            logger.warning("No AgentForge key available for name suggestion")
            return []
        try:
            return await self._suggest_with_agentforge(device, entity, context)
        except Exception as e:
            logger.warning("AgentForge name suggestion failed: %s", e)
            return []

    async def _suggest_with_agentforge(
        self,
        device: Device,
        entity: DeviceEntity | None = None,
        context: dict[str, Any] | None = None,
    ) -> list[NameSuggestion]:
        """Run the `device-name-suggest` workflow for one device."""
        payload = {
            "inputs": {
                "device": json.dumps(self._build_device_record(device, entity, context)),
                "convention": NAMING_CONVENTION,
            },
            "dry_run": False,
        }
        url = f"{self.agentforge_url}/projects/{self.project_slug}/workflows/{WORKFLOW_DEVICE_NAME}/run"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url,
                json=payload,
                params={"kickoff": "sync"},
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
            )
        response.raise_for_status()
        record = response.json()
        if record.get("state") != "complete":
            raise RuntimeError(
                f"device-name-suggest run {record.get('run_id')} ended in state "
                f"{record.get('state')!r}"
            )
        raw = record.get("output")
        answer = json.loads(raw) if isinstance(raw, str) else (raw or {})

        suggestions: list[NameSuggestion] = []
        for item in (answer.get("suggestions") or [])[:3]:
            if not isinstance(item, dict):
                continue
            # strip_brands on every gene-produced name: the convention forbids
            # brands, but a convention is a request, not a guarantee -- the
            # no-brand rule is enforced here, in code (TAP-6234 round 3).
            name = strip_brands(str(item.get("name", "")))
            if not name:
                continue
            suggestions.append(
                NameSuggestion(
                    name=name,
                    confidence=float(item.get("confidence", 0.8)),
                    source="ai",
                    reasoning=str(item.get("reasoning", "")),
                )
            )
        return suggestions

    def _build_device_record(
        self,
        device: Device,
        entity: DeviceEntity | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Assemble the device facts the gene names from.

        Structured rather than prose: the gene's contract is that every
        suggestion says which supplied field it came from, and a field it never
        received cannot be one of them.
        """
        record: dict[str, Any] = {
            "manufacturer": device.manufacturer or None,
            "model": device.model or None,
            "area": device.area_name or device.area_id or None,
            "current_name": device.name or None,
            "device_class": device.device_class or None,
        }
        if getattr(device, "model_id", None):
            record["model_id"] = device.model_id
        if getattr(device, "name_by_user", None):
            record["name_by_user"] = device.name_by_user
        if getattr(device, "labels", None):
            record["labels"] = list(device.labels)
        if entity is not None:
            record["entities"] = [
                {
                    "domain": entity.domain,
                    "entity_id": entity.entity_id,
                    "role": "primary",
                    "aliases": list(getattr(entity, "aliases", None) or []),
                }
            ]
        if context and context.get("existing_devices"):
            record["existing_devices_in_area"] = list(context["existing_devices"])[:5]
        return record
