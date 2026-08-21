"""Derive the device-knowledge columns from durable signals.

Six columns on ``devices.devices`` were NULL for all 93 devices. The cause was
the write path, not a missing rule — see ``services/device_service.py`` — but a
working write path still needs something true to write. This is that.

Every rule here is keyed on structure, never on a friendly name: entity domains,
entity categories, ``device_class`` attributes and the ZHA ``ieee`` address are
all platform-assigned and survive a rename. Ask of each rule "would a rename
break this?"; if the answer is ever yes the rule does not belong here. See
``.claude/rules/friendly-names.md``.

What this module will NOT do is guess. A device with no evidence for a column
gets ``None`` plus a written exclusion reason, because a confident wrong value
is worse than an honest gap — a NULL reads as "unknown", while "mains" on a
battery device reads as established fact.

The rules are the ones that survived adversarial refutation in the TAP-6393
fan-out. They are deliberately family-agnostic: per-integration branches were
proposed and refuted, and the generic form turns out to handle the awkward cases
for free. Hue Room and Zone groups, for instance, expose only ``scene``
entities, and ``scene`` is not in the domain map — so they fall out as NULL
without needing to be named.
"""

from __future__ import annotations

import logging
from typing import Any

from homeiq_device_taxonomy import (
    DOMAIN_PRIORITY,
    DOMAIN_TO_DEVICE_TYPE,
    device_type_vocabulary,
)

logger = logging.getLogger(__name__)

# ``availability_status`` accepts only these three. The vocabulary is declared on
# the model, and ha-ai-agent-service branches on the raw string, so a value
# outside the set is silently missed by consumers rather than rejected.
AVAILABILITY_ENABLED = "enabled"
AVAILABILITY_DISABLED = "disabled"

# Domains that cannot run on a coin cell. Presence of one, with no battery
# entity anywhere on the device, is what establishes mains power. This is an
# attestation from the device's own capabilities, not a measurement, and it is
# recorded as such.
MAINS_REQUIRING_DOMAINS = frozenset(
    {"light", "switch", "media_player", "climate", "fan", "vacuum", "water_heater", "humidifier"}
)

# Entity categories that describe the integration rather than the device. A
# motion sensor's four config switches would otherwise outvote its two binary
# sensors and classify it as a switch.
NON_FUNCTIONAL_ENTITY_CATEGORIES = frozenset({"diagnostic", "config"})


def _as_int_percent(raw: Any) -> int | None:
    """A battery state as a whole percent, or None if it is not a number.

    Home Assistant reports ``unknown`` and ``unavailable`` as state strings, so
    a bare float() would raise on perfectly normal devices.
    """
    try:
        value = int(round(float(raw)))
    except (TypeError, ValueError):
        return None
    return value if 0 <= value <= 100 else None


class DeviceKnowledge:
    """Computes the knowledge columns for a discovery pass.

    Construction takes already-fetched payloads rather than doing its own I/O,
    so the rules are directly testable against fixtures and the network calls
    stay in the discovery service where the rest of them live.
    """

    def __init__(
        self,
        entities: list[Any],
        states: list[dict[str, Any]] | None = None,
        zha_devices: list[dict[str, Any]] | None = None,
    ) -> None:
        self._functional_domains: dict[str, list[str]] = {}
        self._battery_entities: dict[str, str] = {}

        for entity in entities or []:
            device_id = getattr(entity, "device_id", None)
            if not device_id:
                # Helper entities and integration-level entities carry no device.
                continue
            domain = getattr(entity, "domain", None) or ""
            if getattr(entity, "entity_category", None) in NON_FUNCTIONAL_ENTITY_CATEGORIES:
                continue
            if domain:
                self._functional_domains.setdefault(device_id, []).append(domain)

        # device_class lives on the state, not on the registry entry, so the
        # battery join needs both: registry for entity_id -> device_id, states
        # for which of those entities is a battery.
        entity_to_device = {
            getattr(e, "entity_id", None): getattr(e, "device_id", None) for e in entities or []
        }
        self._states_by_entity: dict[str, dict[str, Any]] = {}
        for state in states or []:
            entity_id = state.get("entity_id")
            if not entity_id:
                continue
            self._states_by_entity[entity_id] = state
            if (state.get("attributes") or {}).get("device_class") != "battery":
                continue
            device_id = entity_to_device.get(entity_id)
            if device_id:
                self._battery_entities[device_id] = entity_id

        # ZHA keys on the radio's ieee address, which is burned into the chip and
        # survives re-pairing, renaming and re-interviewing.
        self._zha_by_ieee: dict[str, dict[str, Any]] = {}
        for zha_device in zha_devices or []:
            ieee = zha_device.get("ieee")
            if ieee:
                self._zha_by_ieee[str(ieee).lower()] = zha_device

        self._vocabulary = device_type_vocabulary()

    # -- individual rules ---------------------------------------------------

    def _device_type(self, device_id: str) -> tuple[str | None, str | None]:
        domains = self._functional_domains.get(device_id) or []
        if not domains:
            return None, "device exposes no functional entities, so it has no observable kind"
        for domain in DOMAIN_PRIORITY:
            if domain in domains:
                device_type = DOMAIN_TO_DEVICE_TYPE.get(domain)
                if device_type in self._vocabulary:
                    return device_type, None
        return None, (
            f"no entity domain maps to a device type (domains: {sorted(set(domains))}) — "
            f"this is an integration or grouping construct, not a physical device kind"
        )

    def _power_source(
        self, device_id: str, zigbee_ieee: str | None
    ) -> tuple[str | None, str | None]:
        if device_id in self._battery_entities:
            return "battery", None

        zha_device = self._zha_by_ieee.get((zigbee_ieee or "").lower())
        if zha_device:
            # ZHA hedges as "Battery or Unknown" for quirks it cannot resolve.
            # Only an unhedged Mains is evidence.
            reported = str(zha_device.get("power_source") or "")
            if reported.strip().lower() == "mains":
                return "mains", None

        domains = set(self._functional_domains.get(device_id) or [])
        if domains & MAINS_REQUIRING_DOMAINS:
            return "mains", None

        return None, (
            "no battery entity, no ZHA mains report, and no entity domain that "
            "requires mains — absence of a battery is not evidence of mains power"
        )

    def _battery_level(self, device_id: str) -> tuple[int | None, str | None]:
        entity_id = self._battery_entities.get(device_id)
        if not entity_id:
            return None, "device exposes no battery-class entity"
        level = _as_int_percent((self._states_by_entity.get(entity_id) or {}).get("state"))
        if level is None:
            return None, f"battery entity {entity_id} reports a non-numeric state"
        return level, None

    def _lqi(self, zigbee_ieee: str | None) -> tuple[int | None, str | None]:
        if not zigbee_ieee:
            return None, "not a Zigbee device, so it has no link quality"
        zha_device = self._zha_by_ieee.get(zigbee_ieee.lower())
        if not zha_device:
            return None, "Zigbee address is not known to ZHA"
        lqi = zha_device.get("lqi")
        if lqi is None:
            # The coordinator has no link to itself. This is the honest value,
            # not a gap in the method.
            return (
                None,
                "ZHA reports no LQI for this device (the coordinator has no link to itself)",
            )
        try:
            return int(lqi), None
        except (TypeError, ValueError):
            return None, f"ZHA reported a non-numeric LQI ({lqi!r})"

    # -- entry point --------------------------------------------------------

    @staticmethod
    def _zigbee_ieee(device: Any) -> str | None:
        """The device's Zigbee address, from whichever source carries it.

        Derived here rather than read off the caller's payload because the
        discovery service fills its own `zigbee_ieee` key *after* this runs — a
        call-ordering dependency that silently produced None for all 93 devices
        and excluded every LQI reading.

        Home Assistant reports it as a `("zha", "<ieee>")` identifier pair. The
        address is burned into the radio and survives renaming, re-pairing and
        re-interviewing, which is exactly why it is the join key.
        """
        direct = getattr(device, "zigbee_ieee", None)
        if direct:
            return str(direct)
        ha_device = getattr(device, "ha_device", None)
        for identifier in getattr(ha_device, "identifiers", None) or []:
            if len(identifier) >= 2 and identifier[0] == "zha":
                return str(identifier[1])
        return None

    def for_device(self, device: Any) -> tuple[dict[str, Any], dict[str, str]]:
        """Return ``(values, exclusions)`` for one device.

        ``values`` carries only the columns that could be established. Every
        column left out has an entry in ``exclusions`` explaining why, so a NULL
        is always accompanied by a stated reason rather than a shrug.
        """
        device_id = getattr(device, "id", None) or ""
        zigbee_ieee = self._zigbee_ieee(device)
        values: dict[str, Any] = {}
        exclusions: dict[str, str] = {}

        # source: the integration slug, resolved from Home Assistant's config
        # entries. Available for every device, and a rename cannot move it.
        integration = (getattr(device, "integration", None) or "").strip()
        if integration and integration != "unknown":
            values["source"] = integration
        else:
            exclusions["source"] = "device has no resolved integration"

        # availability_status: a device present in this pass is enabled unless
        # Home Assistant says otherwise. Devices absent from the pass are not
        # touched here — _mark_absent_devices_unavailable owns 'unavailable'.
        values["availability_status"] = (
            AVAILABILITY_DISABLED if getattr(device, "disabled_by", None) else AVAILABILITY_ENABLED
        )

        for column, (value, reason) in {
            "device_type": self._device_type(device_id),
            "power_source": self._power_source(device_id, zigbee_ieee),
            "battery_level": self._battery_level(device_id),
            "lqi": self._lqi(zigbee_ieee),
        }.items():
            if value is None:
                exclusions[column] = reason or "no rule produced a value"
            else:
                values[column] = value

        return values, exclusions
