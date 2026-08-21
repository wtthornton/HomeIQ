"""Tests for the shared device taxonomy.

The contract these pin is the one that broke: `match_device_pattern` returns a
two-tuple, and callers that bind it to a single name write the tuple into a
String column (TAP-6392).
"""

import pytest
from homeiq_device_taxonomy import (
    DEVICE_PATTERNS,
    DOMAIN_PRIORITY,
    DOMAIN_TO_DEVICE_TYPE,
    device_type_vocabulary,
    get_device_category,
    match_device_pattern,
)


class TestMatcherContract:
    def test_returns_a_two_tuple_of_type_and_confidence(self):
        result = match_device_pattern(["light"], set())
        assert isinstance(result, tuple)
        assert len(result) == 2
        device_type, confidence = result
        assert isinstance(device_type, str)
        assert isinstance(confidence, float)

    def test_no_domains_returns_none_at_zero_confidence(self):
        assert match_device_pattern([], set()) == (None, 0.0)

    def test_unmapped_domain_returns_none(self):
        device_type, _ = match_device_pattern(["not_a_domain"], set())
        assert device_type is None

    @pytest.mark.parametrize(
        "domain,expected",
        [
            ("light", "light"),
            ("switch", "switch"),
            ("binary_sensor", "sensor"),
            ("climate", "thermostat"),
            ("media_player", "media_player"),
            ("alarm_control_panel", "alarm"),
        ],
    )
    def test_domain_maps_to_device_type(self, domain, expected):
        device_type, confidence = match_device_pattern([domain], set())
        assert device_type == expected
        assert 0.0 < confidence <= 0.95

    def test_priority_order_decides_a_multi_domain_device(self):
        # A dimmer exposing both light and sensor entities is a light.
        device_type, _ = match_device_pattern(["sensor", "light"], set())
        assert device_type == "light"

    def test_confidence_rises_with_domain_prevalence(self):
        _, one_of_three = match_device_pattern(["light", "sensor", "sensor"], set())
        _, three_of_three = match_device_pattern(["light", "light", "light"], set())
        assert three_of_three > one_of_three


class TestVocabulary:
    def test_every_mapped_device_type_has_a_category(self):
        for device_type in DOMAIN_TO_DEVICE_TYPE.values():
            assert get_device_category(device_type) is not None, device_type

    def test_vocabulary_covers_both_sources(self):
        vocab = device_type_vocabulary()
        assert set(DOMAIN_TO_DEVICE_TYPE.values()) <= vocab
        assert set(DEVICE_PATTERNS) <= vocab

    def test_every_prioritised_domain_is_mapped(self):
        # A domain in DOMAIN_PRIORITY but not in the mapping is dead priority:
        # the loop finds it, looks it up, gets None and falls through silently.
        for domain in DOMAIN_PRIORITY:
            assert domain in DOMAIN_TO_DEVICE_TYPE, domain

    def test_get_device_category_of_none_is_none(self):
        assert get_device_category(None) is None

    def test_unknown_device_type_has_no_category(self):
        assert get_device_category("not_a_device_type") is None


class TestNameBlindness:
    def test_the_matcher_takes_no_name_argument(self):
        import inspect

        params = inspect.signature(match_device_pattern).parameters
        assert list(params) == ["entity_domains", "attribute_keys"]

    def test_a_room_label_cannot_be_classified(self):
        # Area labels and friendly names are not domains, so they resolve to
        # nothing rather than to a plausible-looking guess.
        for label in ("office", "kitchen", "Masters Closet", "Driveway"):
            device_type, _ = match_device_pattern([label], set())
            assert device_type is None
