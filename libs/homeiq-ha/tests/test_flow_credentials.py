"""Tests for owner-supplied config-flow credentials."""

from __future__ import annotations

from homeiq_ha.agent.flow_credentials import (
    credentials_for,
    env_var_for,
    missing_env_vars,
)


class TestEnvVarNaming:
    def test_domain_and_field_are_uppercased(self):
        assert env_var_for("ring", "username") == "HOMEIQ_INTEGRATION_RING_USERNAME"

    def test_non_alphanumerics_collapse_to_underscores(self):
        assert env_var_for("lg_thinq", "client-id") == "HOMEIQ_INTEGRATION_LG_THINQ_CLIENT_ID"

    def test_no_trailing_underscore_from_punctuation(self):
        assert env_var_for("foo.", ".bar") == "HOMEIQ_INTEGRATION_FOO_BAR"


class TestCredentialsFor:
    def test_returns_every_field_when_all_are_set(self, monkeypatch):
        monkeypatch.setenv("HOMEIQ_INTEGRATION_RING_USERNAME", "owner@example.com")
        monkeypatch.setenv("HOMEIQ_INTEGRATION_RING_PASSWORD", "hunter2")

        assert credentials_for("ring", ("username", "password")) == {
            "username": "owner@example.com",
            "password": "hunter2",
        }

    def test_all_or_nothing_when_one_is_missing(self, monkeypatch):
        """A half-filled form errors in a way indistinguishable from a bad password."""
        monkeypatch.setenv("HOMEIQ_INTEGRATION_RING_USERNAME", "owner@example.com")
        monkeypatch.delenv("HOMEIQ_INTEGRATION_RING_PASSWORD", raising=False)

        assert credentials_for("ring", ("username", "password")) is None

    def test_whitespace_only_counts_as_missing(self, monkeypatch):
        monkeypatch.setenv("HOMEIQ_INTEGRATION_RING_USERNAME", "   ")

        assert credentials_for("ring", ("username",)) is None

    def test_no_required_fields_yields_an_empty_mapping_not_none(self):
        """A flow needing nothing is fillable; None would read as 'cannot fill'."""
        assert credentials_for("wled", ()) == {}


class TestMissingEnvVars:
    def test_names_exactly_what_a_person_must_set(self, monkeypatch):
        monkeypatch.setenv("HOMEIQ_INTEGRATION_ROBOROCK_USERNAME", "owner@example.com")
        monkeypatch.delenv("HOMEIQ_INTEGRATION_ROBOROCK_REGION", raising=False)

        assert missing_env_vars("roborock", ("username", "region")) == [
            "HOMEIQ_INTEGRATION_ROBOROCK_REGION"
        ]

    def test_empty_when_everything_is_set(self, monkeypatch):
        monkeypatch.setenv("HOMEIQ_INTEGRATION_ROBOROCK_USERNAME", "owner@example.com")
        monkeypatch.setenv("HOMEIQ_INTEGRATION_ROBOROCK_REGION", "us")

        assert missing_env_vars("roborock", ("username", "region")) == []
