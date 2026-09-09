"""Pure computation behind :class:`~homeiq_ha.agent.powercalc.PowercalcRecipe`.

Split out of :mod:`.powercalc` to keep both files under the maintainability
gate (TAP-6486 round 2) — everything here takes already-fetched HA state,
registry, and flow data and does no I/O of its own, so each function is also
independently unit-testable without a simulator.
"""

from __future__ import annotations

from typing import Any

#: Domains whose entities can carry a physical electrical load. A ``switch``
#: only qualifies as an outlet — HA models a smart plug as
#: ``device_class: outlet`` and a configuration toggle as ``switch`` or none,
#: and this home's 65 switches are entirely the latter (Inovelli device
#: parameters, WLED effect toggles, sensor enables). Metering a toggle is not
#: a gap to close; there is no load behind it.
LOAD_DOMAINS = ("light", "media_player")


def is_number(value: Any) -> bool:
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return True


def live_light_names(states: list[dict[str, Any]]) -> set[Any]:
    """Friendly names of every ``light.*`` entity that is not unavailable/unknown."""
    return {
        (state.get("attributes") or {}).get("friendly_name")
        for state in states
        if str(state.get("entity_id", "")).startswith("light.")
        and state.get("state") not in ("unavailable", "unknown")
    }


def flow_label(flow: dict[str, Any], live_names: set[Any]) -> tuple[bool, dict[str, Any], str]:
    """A flow paired with its device label and a not-alive sort key.

    The discovery title is ``"<light name> - <manufacturer>"``; the light
    half matches the light entity's friendly_name.
    """
    title = (flow.get("context") or {}).get("title_placeholders") or {}
    label = str(title.get("name") or flow["flow_id"])
    alive = label.rsplit(" - ", 1)[0].strip() in live_names
    return not alive, flow, label


def _device_of_entity(registry: list[dict[str, Any]]) -> dict[str, Any]:
    """Map ``entity_id`` to the entity registry's ``device_id`` — the join key."""
    return {str(e.get("entity_id")): e.get("device_id") for e in registry if e.get("entity_id")}


def _mac_of_device(devices_registry: list[dict[str, Any]]) -> dict[str, str]:
    """Map device registry id to its MAC.

    Collapses one physical device that several integrations each discovered
    as their own Home Assistant device (a Samsung TV is found by samsungtv,
    dlna_dmr and cast at once). The MAC is protocol-native identity: burned
    into the NIC, shared by every integration that reaches the same
    hardware, and unmoved by a rename — matching on the identical *names*
    those integrations report would be a name match wearing a better job
    title (``.claude/rules/friendly-names.md``).
    """
    mac_of_device: dict[str, str] = {}
    for device in devices_registry:
        for kind, value in device.get("connections") or []:
            if kind == "mac" and value:
                mac_of_device[str(device.get("id"))] = str(value).lower()
                break
    return mac_of_device


def _metered_devices(states: list[dict[str, Any]], device_of: dict[str, Any]) -> set[Any]:
    """Device ids carrying at least one reporting ``device_class: power`` sensor."""
    return {
        device_of.get(str(s.get("entity_id")))
        for s in states
        if (s.get("attributes") or {}).get("device_class") == "power"
        and is_number(s.get("state"))
        and device_of.get(str(s.get("entity_id")))
    }


def _eligible_loads_and_exclusions(
    states: list[dict[str, Any]], device_of: dict[str, Any]
) -> tuple[set[str], dict[str, list[str]]]:
    """Metering-eligible entities, and why every excluded one was skipped.

    * **group entities** — a light group's power is the sum of its members,
      so metering the group double-counts every member.
    * **non-outlet switches** — configuration toggles, not loads. HA models
      a smart plug as ``device_class: outlet``.
    """
    eligible: set[str] = set()
    excluded: dict[str, list[str]] = {
        "group_entity_sums_its_members": [],
        "switch_is_a_config_toggle_not_a_load": [],
        "no_device_in_the_entity_registry": [],
        "same_physical_device_already_counted": [],
    }
    for state in states:
        entity_id = str(state.get("entity_id", ""))
        domain, _, _ = entity_id.partition(".")
        attributes = state.get("attributes") or {}
        if domain in LOAD_DOMAINS:
            if attributes.get("entity_id"):
                excluded["group_entity_sums_its_members"].append(entity_id)
                continue
        elif domain == "switch":
            if attributes.get("device_class") != "outlet":
                excluded["switch_is_a_config_toggle_not_a_load"].append(entity_id)
                continue
        else:
            continue
        if not device_of.get(entity_id):
            excluded["no_device_in_the_entity_registry"].append(entity_id)
            continue
        eligible.add(entity_id)
    return eligible, excluded


def _dedupe_shared_macs(
    eligible: set[str],
    device_of: dict[str, Any],
    mac_of_device: dict[str, str],
    excluded: dict[str, list[str]],
) -> None:
    """Keep one representative entity per physical MAC, in place.

    Chosen deterministically (sorted order) so the count does not move
    between runs.
    """
    by_mac: dict[str, list[str]] = {}
    for entity_id in sorted(eligible):
        mac = mac_of_device.get(str(device_of.get(entity_id)))
        if mac:
            by_mac.setdefault(mac, []).append(entity_id)
    for mac_group in by_mac.values():
        for duplicate in mac_group[1:]:
            eligible.discard(duplicate)
            excluded["same_physical_device_already_counted"].append(duplicate)


def _covered_loads(
    eligible: set[str],
    device_of: dict[str, Any],
    metered_devices: set[Any],
    mac_of_device: dict[str, str],
) -> set[str]:
    """Eligible entities whose device — or a MAC-sibling device — is metered.

    A physical device is metered if ANY of its Home Assistant devices is —
    the reading belongs to the hardware, not to the integration that
    happened to surface it.
    """
    metered_macs = {
        mac_of_device[device_id] for device_id in metered_devices if device_id in mac_of_device
    }
    return {
        eid
        for eid in eligible
        if device_of.get(eid) in metered_devices
        or mac_of_device.get(str(device_of.get(eid))) in metered_macs
    }


def _uncovered_reasons(uncovered: set[str], states: list[dict[str, Any]]) -> dict[str, str]:
    """Why each uncovered load has no reading — one of three distinct causes.

    A bare list of 30 entity ids says "something is wrong somewhere"; this
    says which of them a person could act on, and how.
    """
    state_of = {str(s.get("entity_id")): str(s.get("state")) for s in states}
    reasons: dict[str, str] = {}
    for entity_id in sorted(uncovered):
        state = state_of.get(entity_id, "unknown")
        if state == "unavailable":
            reasons[entity_id] = (
                "the load itself is unavailable — a sensor cannot read a device "
                "that is not reachable, so this clears when the device is powered"
            )
        elif entity_id.startswith("media_player."):
            reasons[entity_id] = (
                "no Powercalc profile for this media player; it needs a manually "
                "stated wattage, which is a fact about the hardware"
            )
        else:
            reasons[entity_id] = (
                "Powercalc raised no discovery flow that closes on defaults — "
                "typically a profile asking for supply voltage, which is a fact "
                "about the installation rather than the device"
            )
    return reasons


def compute_coverage(
    states: list[dict[str, Any]],
    registry: list[dict[str, Any]],
    devices_registry: list[dict[str, Any]],
) -> dict[str, Any]:
    """Which metering-eligible loads carry a power reading, and which do not.

    Takes the three already-fetched HA reads (states, entity registry,
    device registry) and returns the same shape
    :meth:`~homeiq_ha.agent.powercalc.PowercalcRecipe._coverage` always has:
    ``eligible``, ``covered``, ``excluded``, ``uncovered_reasons``.
    """
    device_of = _device_of_entity(registry)
    metered_devices = _metered_devices(states, device_of)
    mac_of_device = _mac_of_device(devices_registry)

    eligible, excluded = _eligible_loads_and_exclusions(states, device_of)
    _dedupe_shared_macs(eligible, device_of, mac_of_device, excluded)
    covered = _covered_loads(eligible, device_of, metered_devices, mac_of_device)
    reasons = _uncovered_reasons(eligible - covered, states)

    for entity_ids in excluded.values():
        entity_ids.sort()
    return {
        "eligible": eligible,
        "covered": covered,
        "excluded": excluded,
        "uncovered_reasons": reasons,
    }


__all__ = ["LOAD_DOMAINS", "compute_coverage", "flow_label", "is_number", "live_light_names"]
