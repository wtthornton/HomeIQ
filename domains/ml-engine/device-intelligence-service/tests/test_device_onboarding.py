"""Tests for the device-onboarding planner.

The planner decides what a lookup costs before one is spent, so the properties
worth pinning are the ones that keep the bill down and keep a name out of the
decision:

* a model the claim store already answers is not looked up at all
* twenty identical bulbs are one model and one lookup
* a friendly name never reaches the signature the gene identifies from
"""

import pytest
from src.services.device_onboarding import (
    DEFAULT_WANTED_FACTS,
    build_signature,
    normalize_model_key,
    plan_onboarding,
)


def device(**kw):
    base = {
        "id": kw.pop("id", "d1"),
        "name": kw.pop("name", "Office Lamp"),
        "manufacturer": kw.pop("manufacturer", "Inovelli"),
        "model": kw.pop("model", "VZM31-SN"),
        "integration": kw.pop("integration", "zha"),
    }
    base.update(kw)
    return base


def claim(fact_key, value="x"):
    return {"fact_key": fact_key, "fact_value": value, "evidence_class": "vendor_doc"}


class TestTheCacheDecidesBeforeAnythingIsSpent:
    def test_a_fully_answered_model_is_not_looked_up(self):
        claims = {"inovelli/vzm31-sn": [claim(k) for k in DEFAULT_WANTED_FACTS]}
        assert plan_onboarding([device()], {}, claims) == []

    def test_a_partially_answered_model_asks_only_for_the_gaps(self):
        claims = {"inovelli/vzm31-sn": [claim("device_type"), claim("power_source")]}
        [candidate] = plan_onboarding([device()], {}, claims)
        assert "device_type" not in candidate.gaps
        assert "power_source" not in candidate.gaps
        assert "typical_power_watts" in candidate.gaps

    def test_an_unknown_model_is_looked_up_in_full(self):
        [candidate] = plan_onboarding([device()], {}, {})
        assert candidate.gaps == DEFAULT_WANTED_FACTS
        assert candidate.needs_lookup

    def test_the_cache_is_passed_through_for_the_gene_to_see(self):
        # The gene reports cache_hits from `known`, so it has to receive it even
        # for the keys the planner already knows are covered.
        claims = {"inovelli/vzm31-sn": [claim("device_type")]}
        [candidate] = plan_onboarding([device()], {}, claims)
        assert candidate.known == [claim("device_type")]


class TestOneLookupPerModel:
    def test_twenty_identical_bulbs_are_one_candidate(self):
        bulbs = [
            device(id=f"d{n}", manufacturer="Signify", model="Hue color downlight")
            for n in range(20)
        ]
        [candidate] = plan_onboarding(bulbs, {}, {})
        assert candidate.device_count == 20
        assert candidate.subject_key == "signify/hue color downlight"

    def test_bigger_populations_come_first(self):
        devices = [device(id="a", manufacturer="Signify", model="Hue color downlight")] * 5
        devices += [device(id="b", manufacturer="Aqara", model="FP1E")]
        plan = plan_onboarding(devices, {}, {})
        assert [c.subject_key for c in plan][0] == "signify/hue color downlight"

    def test_only_subjects_narrows_to_newly_seen_models(self):
        devices = [
            device(id="a", manufacturer="Signify", model="Hue color downlight"),
            device(id="b", manufacturer="Aqara", model="FP1E"),
        ]
        plan = plan_onboarding(devices, {}, {}, only_subjects={"aqara/fp1e"})
        assert [c.subject_key for c in plan] == ["aqara/fp1e"]


class TestAModelStringThatNamesNothing:
    @pytest.mark.parametrize("model", ["Unknown", "", "  ", "none", "N/A"])
    def test_is_not_searched_on(self, model):
        # Searching the web for "Unknown" returns whatever the word means.
        assert plan_onboarding([device(model=model)], {}, {}) == []

    @pytest.mark.parametrize("manufacturer", ["Unknown", "", "null"])
    def test_an_unknown_manufacturer_is_skipped_too(self, manufacturer):
        assert plan_onboarding([device(manufacturer=manufacturer)], {}, {}) == []


class TestTheSignatureCarriesNoName:
    def test_the_friendly_name_is_absent(self):
        signature = build_signature(
            device(name="Family Room TV", model="MediaRenderer", manufacturer="Sony"), []
        )
        assert "name" not in signature
        assert "Family Room" not in str(signature)

    def test_structural_identity_is_present(self):
        signature = build_signature(
            device(
                manufacturer="Samsung Electronics",
                model="UN65TU700DFXZA",
                integration="samsungtv",
                connections=[["mac", "4C:C9:5E:3B:E9:22"]],
            ),
            ["media_player"],
        )
        assert signature["manufacturer"] == "Samsung Electronics"
        assert signature["model"] == "UN65TU700DFXZA"
        # Lowercased so the same NIC matches whichever integration reported it.
        assert signature["mac"] == "4c:c9:5e:3b:e9:22"
        assert signature["entity_domains"] == ["media_player"]

    def test_the_zigbee_address_is_carried(self):
        signature = build_signature(device(zigbee_ieee="54:ef:44:10:01:46:c2:2c"), [])
        assert signature["ieee"] == "54:ef:44:10:01:46:c2:2c"

    def test_an_uninformative_model_is_omitted_not_passed_as_text(self):
        # The scout is built to work from a signature with no model; handing it
        # the literal word "Unknown" invites it to research the word.
        signature = build_signature(device(model="Unknown", manufacturer="Sony"), [])
        assert "model" not in signature
        assert signature["manufacturer"] == "Sony"

    def test_entity_domains_are_deduplicated_and_ordered(self):
        signature = build_signature(device(), ["light", "sensor", "light"])
        assert signature["entity_domains"] == ["light", "sensor"]


class TestSubjectKey:
    def test_it_matches_the_stores_canonical_form(self):
        assert normalize_model_key("Signify Netherlands B.V.", "Hue Color Downlight") == (
            "signify netherlands b.v./hue color downlight"
        )

    def test_surrounding_whitespace_does_not_make_a_second_subject(self):
        assert normalize_model_key("  Inovelli ", " VZM31-SN ") == "inovelli/vzm31-sn"


class TestServiceEntriesAreNotDevices:
    def test_a_hue_room_group_is_not_onboarded(self):
        # "Signify Netherlands B.V. / Room" is a search that can only return
        # something misleading: there is no such product.
        room = device(manufacturer="Signify Netherlands B.V.", model="Room", entry_type="service")
        assert plan_onboarding([room], {}, {}) == []

    def test_an_add_on_is_not_onboarded(self):
        addon = device(
            manufacturer="Home Assistant", model="Home Assistant Core", entry_type="service"
        )
        assert plan_onboarding([addon], {}, {}) == []

    def test_a_real_device_is_unaffected(self):
        assert len(plan_onboarding([device(entry_type=None)], {}, {})) == 1
