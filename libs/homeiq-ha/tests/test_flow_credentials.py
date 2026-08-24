"""Tests for owner-supplied config-flow credentials.

Credentials arrive as a caller-supplied mapping. There is deliberately no
environment-variable path: a consumer has a browser and no shell, so a design
that asks someone to edit a file on the Docker host is an unshipped feature.
"""

from __future__ import annotations

from homeiq_ha.agent.flow_credentials import credentials_for, missing_fields


class TestCredentialsFor:
    def test_returns_every_field_when_all_are_supplied(self):
        supplied = {"username": "owner@example.com", "password": "hunter2"}

        assert credentials_for(("username", "password"), supplied) == {
            "username": "owner@example.com",
            "password": "hunter2",
        }

    def test_ignores_fields_the_form_did_not_ask_for(self):
        """The submitted input is the form's shape, not whatever was handed over."""
        supplied = {"username": "owner@example.com", "password": "hunter2", "region": "us"}

        assert credentials_for(("username", "password"), supplied) == {
            "username": "owner@example.com",
            "password": "hunter2",
        }

    def test_all_or_nothing_when_one_is_missing(self):
        """A half-filled form errors in a way indistinguishable from a bad password."""
        assert credentials_for(("username", "password"), {"username": "owner@example.com"}) is None

    def test_whitespace_only_counts_as_missing(self):
        assert credentials_for(("username",), {"username": "   "}) is None

    def test_nothing_supplied_is_not_fillable(self):
        assert credentials_for(("username",), None) is None
        assert credentials_for(("username",), {}) is None

    def test_no_required_fields_yields_an_empty_mapping_not_none(self):
        """A flow needing nothing is fillable; None would read as 'cannot fill'."""
        assert credentials_for((), None) == {}
        assert credentials_for((), {"stray": "value"}) == {}


class TestMissingFields:
    def test_names_exactly_what_is_still_needed(self):
        supplied = {"username": "owner@example.com"}

        assert missing_fields(("username", "region"), supplied) == ["region"]

    def test_empty_when_everything_is_supplied(self):
        supplied = {"username": "owner@example.com", "region": "us"}

        assert missing_fields(("username", "region"), supplied) == []

    def test_everything_is_missing_when_nothing_was_supplied(self):
        assert missing_fields(("username", "region"), None) == ["username", "region"]
        assert missing_fields(("username", "region"), {}) == ["username", "region"]

    def test_whitespace_only_counts_as_missing(self):
        assert missing_fields(("region",), {"region": "  "}) == ["region"]

    def test_preserves_the_forms_field_order(self):
        """The order is the form's, so a prompt can be built straight from it."""
        assert missing_fields(("username", "password", "region"), None) == [
            "username",
            "password",
            "region",
        ]
