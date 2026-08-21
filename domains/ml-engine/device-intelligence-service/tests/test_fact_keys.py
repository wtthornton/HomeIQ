"""Tests for fact-key canonicalisation.

`fact_key` is a join key, so a synonym is not a cosmetic problem: the fact is in
the store and the lookup cannot reach it. Twenty-five claims landed carrying
`wattage`, `standby_power_consumption`, `communication_protocol` and
`upstream_zha_quirk_reference`, and a cache probe for the canonical spelling came
back empty against a store that already held the answer.
"""

import pytest
from src.services.fact_keys import (
    CANONICAL_FACT_KEYS,
    FACT_KEY_ALIASES,
    canonical_fact_key,
    is_canonical,
)


class TestSynonymsCollapse:
    @pytest.mark.parametrize(
        "written,canonical",
        [
            ("wattage", "typical_power_watts"),
            ("power_consumption", "typical_power_watts"),
            ("standby_power_consumption", "standby_power_watts"),
            ("max_load_watts", "max_power_watts"),
            ("communication_protocol", "radio_protocol"),
            ("upstream_zha_quirk_reference", "zha_quirk_required"),
            ("neutral_wire_required", "requires_neutral"),
            ("zigbee_model_identifier", "zigbee_model_id"),
            ("zigbee_device_type", "zigbee_role"),
            ("supports_ota_updates", "firmware_update_path"),
            ("product_type", "device_type"),
        ],
    )
    def test_an_observed_synonym_maps_to_its_canonical_key(self, written, canonical):
        assert canonical_fact_key(written) == canonical

    def test_wattage_means_running_power_not_a_peak_rating(self):
        # Reading a peak rating as a running figure is what makes an energy
        # estimate several times wrong, so this mapping is load-bearing.
        assert canonical_fact_key("wattage") == "typical_power_watts"
        assert canonical_fact_key("maximum_wattage") == "max_power_watts"

    def test_case_and_whitespace_do_not_make_a_second_key(self):
        assert canonical_fact_key("  Wattage  ") == "typical_power_watts"
        assert canonical_fact_key("POWER_SOURCE") == "power_source"


class TestUnknownKeysSurvive:
    @pytest.mark.parametrize("key", ["lumen_output", "ip_rating", "mounting_options"])
    def test_a_fact_nothing_branches_on_is_still_stored(self, key):
        # A closed vocabulary would throw these away to buy a tidiness nobody
        # benefits from. They are real facts; they simply drive no decision.
        assert canonical_fact_key(key) == key
        assert not is_canonical(key)

    def test_an_empty_key_is_returned_untouched(self):
        assert canonical_fact_key("") == ""


class TestTheVocabularyIsCoherent:
    def test_every_alias_targets_a_canonical_key(self):
        # An alias pointing at a non-canonical key would move a fact from one
        # unreachable name to another.
        for alias, target in FACT_KEY_ALIASES.items():
            assert target in CANONICAL_FACT_KEYS, f"{alias} -> {target} is not canonical"

    def test_no_canonical_key_is_also_an_alias(self):
        # A key that is both would make canonicalisation depend on lookup order.
        assert not (CANONICAL_FACT_KEYS & set(FACT_KEY_ALIASES)), (
            "a key is both canonical and an alias"
        )

    def test_canonicalisation_is_idempotent(self):
        for key in list(FACT_KEY_ALIASES) + sorted(CANONICAL_FACT_KEYS):
            once = canonical_fact_key(key)
            assert canonical_fact_key(once) == once, f"{key} does not settle"
