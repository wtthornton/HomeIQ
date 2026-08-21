"""Canonical names for the device facts the system reasons about.

`fact_key` is a join key. A reader asking "what does this model draw?" looks up one
string, and if the writer stored a synonym the lookup finds nothing — the fact is
in the store, and it is unreachable. That is not hypothetical: 164 claims landed
carrying `wattage`, `standby_power_consumption`, `communication_protocol` and
`upstream_zha_quirk_reference`, so a cache probe for `typical_power_watts` came
back empty against a store that already held the answer three times over.

The cause was an asymmetry between two genes writing to one column. The researcher
declares a `fact_key` enum in its output schema; the curator's schema types the
same field as a free string, and the curator is the write path. A vocabulary
enforced on the proposer and not on the approver is not enforced.

So it is enforced here, at the write, which is the one place every claim passes
through regardless of which gene proposed it.

**Aliasing, not rejection.** A closed vocabulary would throw away `lumen_output`,
`ip_rating` and `mounting_options` — real facts a person or a model can use, that
simply do not drive a decision in HomeIQ today. Those are stored verbatim. What is
normalised is the set of keys something actually branches on, so that two spellings
of one fact cannot both be live and disagree.
"""

from __future__ import annotations

#: Facts HomeIQ itself branches on. Adding one here is a commitment that some code
#: reads it; a fact nobody reads belongs in the free-text tail, not in this set.
CANONICAL_FACT_KEYS = frozenset(
    {
        "device_type",
        "power_source",
        "radio_protocol",
        "typical_power_watts",
        "max_power_watts",
        "standby_power_watts",
        "supply_voltage",
        "mains_voltage_range",
        "battery_type",
        "requires_neutral",
        "zha_quirk_required",
        "zigbee_model_id",
        "zigbee_role",
        "firmware_update_path",
        "supports_power_metering",
        "supports_color_temp",
        "bulb_base",
        "known_defect",
    }
)

#: Synonyms observed in the store, mapped to the canonical key. Every entry here is
#: a spelling a gene actually produced, not a guess at what one might produce.
#:
#: `wattage` is deliberately mapped to `typical_power_watts` rather than to
#: `max_power_watts`: the claims carrying it quote running-power figures, and
#: reading a peak rating as a running one is the error that makes an energy
#: estimate several times wrong. Where a claim genuinely means the rating, the
#: gene emits `max_power_watts` directly.
FACT_KEY_ALIASES = {
    "wattage": "typical_power_watts",
    "power_watts": "typical_power_watts",
    "power_consumption": "typical_power_watts",
    "power_consumption_watts": "typical_power_watts",
    "typical_power_consumption": "typical_power_watts",
    "standby_power_consumption": "standby_power_watts",
    "standby_power": "standby_power_watts",
    "idle_power_watts": "standby_power_watts",
    "max_power_consumption": "max_power_watts",
    "maximum_wattage": "max_power_watts",
    "max_load_watts": "max_power_watts",
    "communication_protocol": "radio_protocol",
    "protocol": "radio_protocol",
    "wireless_protocol": "radio_protocol",
    "zigbee_model_identifier": "zigbee_model_id",
    "zigbee_manufacturer_model": "zigbee_model_id",
    "zigbee_device_type": "zigbee_role",
    "zigbee_router_capable": "zigbee_role",
    "zigbee_device_role": "zigbee_role",
    "upstream_zha_quirk_reference": "zha_quirk_required",
    "upstream_zha_quirk_class": "zha_quirk_required",
    "zha_quirk": "zha_quirk_required",
    "neutral_wire_required": "requires_neutral",
    "requires_neutral_wire": "requires_neutral",
    "power_supply": "power_source",
    "power_source_type": "power_source",
    "supports_ota_updates": "firmware_update_path",
    "ota_supported": "firmware_update_path",
    "home_assistant_update_mechanism": "firmware_update_path",
    "product_type": "device_type",
    "supports_metering": "supports_power_metering",
    "measured_power_accuracy": "supports_power_metering",
}


def canonical_fact_key(fact_key: str) -> str:
    """The canonical spelling of a fact key.

    Unknown keys pass through unchanged rather than being rejected. A fact nothing
    branches on is still worth storing for a person to read, and refusing it would
    lose information to buy a tidiness nobody benefits from.
    """
    normalized = str(fact_key or "").strip().lower()
    if not normalized:
        return fact_key
    return FACT_KEY_ALIASES.get(normalized, normalized)


def is_canonical(fact_key: str) -> bool:
    """Whether this key is one the system branches on."""
    return canonical_fact_key(fact_key) in CANONICAL_FACT_KEYS
