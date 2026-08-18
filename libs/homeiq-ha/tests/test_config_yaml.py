"""Tests for the configuration.yaml recipes and their block editor.

The transport is a fake that keeps the file in memory and records every call,
so these never open a socket — and so "check writes nothing" is an assertion
about recorded calls rather than a promise.

The fixture text is the real target instance's file (read live 2026-08-18),
including the ``!include`` tags that make ``yaml.safe_load`` raise.
"""

from __future__ import annotations

import pytest
import yaml
from homeiq_ha.agent import CheckStatus
from homeiq_ha.agent.config_yaml import (
    HTTP_LOGIN_ATTEMPTS_THRESHOLD,
    RECORDER_EXCLUDED_DOMAINS,
    RECORDER_EXCLUDED_ENTITY_GLOBS,
    RECORDER_PURGE_KEEP_DAYS,
    ConfigYamlError,
    HttpLoginThresholdRecipe,
    RecorderTuningRecipe,
    parse_config,
    set_top_level,
)

LIVE_CONFIG = """# Loads default set of integrations. Do not remove.
default_config:

# Load frontend themes from the themes folder
frontend:
  themes: !include_dir_merge_named themes

automation: !include automations.yaml
script: !include scripts.yaml
scene: !include scenes.yaml
"""


class FakeHostFiles:
    """In-memory stand-in for the ssh transport that records every call."""

    def __init__(self, text: str = LIVE_CONFIG) -> None:
        self.files = {"/config/configuration.yaml": text}
        self.calls: list[str] = []

    @property
    def writes(self) -> list[str]:
        return [call for call in self.calls if call.startswith("write ")]

    async def read_text(self, path: str) -> str:
        self.calls.append(f"read {path}")
        return self.files[path]

    async def write_text(self, path: str, content: str) -> str:
        self.calls.append(f"write {path}")
        self.files[path] = content
        return f"{path}.homeiq-20260818T000000Z.bak"


def _recipe(cls, host_files):
    """A recipe wired for tests: no real restart waits."""
    return cls(
        host_files,
        restart_timeout=1.0,
        restart_poll_interval=0.0,
        restart_min_wait=0.0,
    )


# --- the block editor ------------------------------------------------------


def test_parse_config_tolerates_home_assistants_own_tags():
    parsed = parse_config(LIVE_CONFIG)

    assert parsed["automation"] == "!include automations.yaml"
    assert set(parsed) == {
        "default_config",
        "frontend",
        "automation",
        "script",
        "scene",
    }
    with pytest.raises(yaml.YAMLError):
        yaml.safe_load(LIVE_CONFIG)


def test_set_top_level_appends_without_touching_a_single_existing_byte():
    result = set_top_level(LIVE_CONFIG, "http", {"login_attempts_threshold": 5})

    assert result.startswith(LIVE_CONFIG)
    assert result.endswith("http:\n  login_attempts_threshold: 5\n")


def test_set_top_level_replaces_in_place_and_keeps_neighbouring_comments():
    text = LIVE_CONFIG + "\nhttp:\n  login_attempts_threshold: -1\n\n# tail comment\nlogger:\n  default: info\n"

    result = set_top_level(text, "http", {"login_attempts_threshold": 5})

    assert "login_attempts_threshold: 5" in result
    assert "login_attempts_threshold: -1" not in result
    # The comment introducing the *next* block stays with that block.
    assert "# tail comment\nlogger:\n  default: info\n" in result
    assert "# Load frontend themes from the themes folder" in result
    assert parse_config(result)["logger"] == {"default": "info"}


def test_set_top_level_indents_sequences_under_their_key():
    result = set_top_level(LIVE_CONFIG, "recorder", {"exclude": {"domains": ["update"]}})

    assert "  exclude:\n    domains:\n      - update\n" in result


def test_set_top_level_refuses_a_file_with_a_duplicate_top_level_key():
    text = "http:\n  a: 1\nhttp:\n  b: 2\n"

    with pytest.raises(ConfigYamlError, match="duplicate top-level key"):
        set_top_level(text, "http", {"a": 1})


# --- http.login_attempts_threshold ----------------------------------------


@pytest.mark.asyncio
async def test_http_check_needs_apply_on_the_stock_file_and_writes_nothing(sim):
    files = FakeHostFiles()

    result = await _recipe(HttpLoginThresholdRecipe, files).check(sim)

    assert result.status is CheckStatus.NEEDS_APPLY
    assert files.writes == []
    assert sim.writes == []


@pytest.mark.asyncio
async def test_http_check_satisfied_when_the_value_is_already_five(sim):
    files = FakeHostFiles(LIVE_CONFIG + f"\nhttp:\n  login_attempts_threshold: {HTTP_LOGIN_ATTEMPTS_THRESHOLD}\n")

    result = await _recipe(HttpLoginThresholdRecipe, files).check(sim)

    assert result.status is CheckStatus.SATISFIED
    assert files.writes == []


@pytest.mark.asyncio
async def test_http_check_needs_apply_on_the_disabled_default(sim):
    files = FakeHostFiles(LIVE_CONFIG + "\nhttp:\n  login_attempts_threshold: -1\n")

    result = await _recipe(HttpLoginThresholdRecipe, files).check(sim)

    assert result.status is CheckStatus.NEEDS_APPLY
    assert "-1" in result.details["drift"][0]


@pytest.mark.asyncio
async def test_http_plan_writes_nothing_and_names_the_restart(sim):
    files = FakeHostFiles()

    plan = await _recipe(HttpLoginThresholdRecipe, files).plan(sim)

    assert files.writes == []
    assert [change.action for change in plan.changes] == ["set", "restart"]


@pytest.mark.asyncio
async def test_http_apply_merges_without_clobbering_the_rest_of_the_block(sim):
    files = FakeHostFiles(
        LIVE_CONFIG + "\nhttp:\n  server_port: 8123\n  use_x_forwarded_for: true\n"
    )
    recipe = _recipe(HttpLoginThresholdRecipe, files)

    result = await recipe.apply(sim)

    block = parse_config(files.files["/config/configuration.yaml"])["http"]
    assert block == {
        "server_port": 8123,
        "use_x_forwarded_for": True,
        "login_attempts_threshold": HTTP_LOGIN_ATTEMPTS_THRESHOLD,
    }
    assert "automation: !include automations.yaml" in files.files["/config/configuration.yaml"]
    assert ("homeassistant", "restart", {}) in sim.state["service_calls"]
    assert [change.action for change in result.changed] == ["set", "restart"]
    assert (await recipe.verify(sim)).ok


@pytest.mark.asyncio
async def test_http_second_apply_is_a_no_op(sim):
    files = FakeHostFiles()
    recipe = _recipe(HttpLoginThresholdRecipe, files)
    await recipe.apply(sim)
    after_first = files.files["/config/configuration.yaml"]
    writes_after_first = len(files.writes)

    second = await recipe.apply(sim)

    assert second.change_count == 0
    assert len(files.writes) == writes_after_first
    assert files.files["/config/configuration.yaml"] == after_first
    assert (await recipe.check(sim)).status is CheckStatus.SATISFIED


# --- recorder --------------------------------------------------------------


@pytest.mark.asyncio
async def test_recorder_check_needs_apply_when_the_block_is_absent(sim):
    files = FakeHostFiles()

    result = await _recipe(RecorderTuningRecipe, files).check(sim)

    assert result.status is CheckStatus.NEEDS_APPLY
    assert len(result.details["drift"]) == 3  # purge + domains + globs
    assert files.writes == []


@pytest.mark.asyncio
async def test_recorder_check_satisfied_on_an_already_tuned_instance(sim):
    tuned = {
        "purge_keep_days": RECORDER_PURGE_KEEP_DAYS,
        "exclude": {
            "domains": list(RECORDER_EXCLUDED_DOMAINS),
            "entity_globs": list(RECORDER_EXCLUDED_ENTITY_GLOBS),
        },
    }
    files = FakeHostFiles(set_top_level(LIVE_CONFIG, "recorder", tuned))

    result = await _recipe(RecorderTuningRecipe, files).check(sim)

    assert result.status is CheckStatus.SATISFIED
    assert files.writes == []


@pytest.mark.asyncio
async def test_recorder_apply_unions_exclusions_and_keeps_sqlite(sim):
    existing = {
        "commit_interval": 10,
        "exclude": {
            "domains": ["automation"],
            "entities": ["sensor.private_thing"],
            "entity_globs": ["sensor.*_rssi"],
        },
    }
    files = FakeHostFiles(set_top_level(LIVE_CONFIG, "recorder", existing))
    recipe = _recipe(RecorderTuningRecipe, files)

    await recipe.apply(sim)

    block = parse_config(files.files["/config/configuration.yaml"])["recorder"]
    assert block["purge_keep_days"] == RECORDER_PURGE_KEEP_DAYS
    assert block["commit_interval"] == 10
    assert block["exclude"]["entities"] == ["sensor.private_thing"]
    assert block["exclude"]["domains"] == ["automation", "update"]
    # Union: the hand-added glob is kept and appears exactly once.
    assert block["exclude"]["entity_globs"].count("sensor.*_rssi") == 1
    assert set(RECORDER_EXCLUDED_ENTITY_GLOBS) <= set(block["exclude"]["entity_globs"])
    assert "db_url" not in block
    assert (await recipe.verify(sim)).ok


@pytest.mark.asyncio
async def test_recorder_apply_leaves_an_existing_db_url_alone(sim):
    files = FakeHostFiles(
        set_top_level(LIVE_CONFIG, "recorder", {"db_url": "mysql://elsewhere/ha"})
    )

    await _recipe(RecorderTuningRecipe, files).apply(sim)

    block = parse_config(files.files["/config/configuration.yaml"])["recorder"]
    assert block["db_url"] == "mysql://elsewhere/ha"


@pytest.mark.asyncio
async def test_recorder_second_apply_is_a_no_op(sim):
    files = FakeHostFiles()
    recipe = _recipe(RecorderTuningRecipe, files)
    await recipe.apply(sim)
    after_first = files.files["/config/configuration.yaml"]
    writes_after_first = len(files.writes)

    second = await recipe.apply(sim)

    assert second.change_count == 0
    assert len(files.writes) == writes_after_first
    assert files.files["/config/configuration.yaml"] == after_first
    assert (await recipe.check(sim)).status is CheckStatus.SATISFIED


# --- failure and absent-transport behaviour --------------------------------


@pytest.mark.asyncio
async def test_apply_restores_the_previous_file_when_the_config_check_fails(sim):
    sim.state["check_config"] = {"result": "invalid", "errors": "bad indentation"}
    files = FakeHostFiles()
    recipe = _recipe(RecorderTuningRecipe, files)

    with pytest.raises(Exception, match="config check"):
        await recipe.apply(sim)

    assert files.files["/config/configuration.yaml"] == LIVE_CONFIG
    assert ("homeassistant", "restart", {}) not in sim.state.get("service_calls", [])


@pytest.mark.asyncio
async def test_check_is_not_applicable_without_a_configured_write_path(sim):
    for cls in (HttpLoginThresholdRecipe, RecorderTuningRecipe):
        result = await cls().check(sim)
        assert result.status is CheckStatus.NOT_APPLICABLE
        assert (await cls().plan(sim)).is_empty


@pytest.mark.asyncio
async def test_both_recipes_are_in_the_default_set():
    from homeiq_ha.agent.recipes import default_recipes

    names = {recipe.name for recipe in default_recipes()}

    assert "correctness.http_login_threshold" in names
    assert "correctness.recorder_tuning" in names
