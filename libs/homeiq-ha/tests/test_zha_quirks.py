"""Tests for the custom ZHA quirk deployment recipe.

The transport is an in-memory fake that records every call, so "check writes
nothing" is an assertion about recorded calls rather than a promise, and these
never open a socket. The device list is the live one, captured from
``zha/devices`` on the target instance 2026-08-18: one FP1E that interviewed
cleanly and one whose Basic cluster never answered, which is the case the
recipe has to classify rather than gate on.
"""

from __future__ import annotations

import pytest
from homeiq_ha.agent import CheckStatus
from homeiq_ha.agent.config_yaml import parse_config, set_top_level
from homeiq_ha.agent.host_files import HostFileError, HostFileNotFound
from homeiq_ha.agent.zha_quirks import (
    CUSTOM_QUIRKS_DIR,
    FP1E_MODEL,
    FP1E_QUIRK_FILENAME,
    UNKNOWN_MANUFACTURER,
    AqaraFP1EQuirkRecipe,
    quirk_source,
)

LIVE_CONFIG = """# Loads default set of integrations. Do not remove.
default_config:

# Load frontend themes from the themes folder
frontend:
  themes: !include_dir_merge_named themes

automation: !include automations.yaml
"""

QUIRK_PATH = f"{CUSTOM_QUIRKS_DIR}/{FP1E_QUIRK_FILENAME}"

#: The interviewed unit: Aqara in the Basic cluster, so a quirk can match it.
INTERVIEWED = {
    "ieee": "54:ef:44:10:01:46:c2:2c",
    "manufacturer": "Aqara",
    "model": FP1E_MODEL,
    "quirk_applied": False,
}

#: The unit whose interview stalled before the Basic cluster answered. No
#: manufacturer means no quirk of any kind can match it.
UNINTERVIEWED = {
    "ieee": "54:ef:44:10:01:46:c0:f4",
    "manufacturer": UNKNOWN_MANUFACTURER,
    "model": FP1E_MODEL,
    "quirk_applied": False,
}

#: The interviewed unit once the quirk has landed, captured live 2026-08-18.
#: The quirk's ``friendly_name`` rewrites ``model`` and the reported signature,
#: so the only field still naming the Zigbee model is ``quirk_class``.
QUIRKED = {
    "ieee": "54:ef:44:10:01:46:c2:2c",
    "manufacturer": "Aqara",
    "model": "Presence Sensor FP1E",
    "quirk_applied": True,
    "quirk_class": f"aqara_fp1e:(Aqara / {FP1E_MODEL})",
    "signature": {"manufacturer": "Aqara", "model": "Presence Sensor FP1E"},
}

OTHER_DEVICE = {
    "ieee": "00:12:4b:00:2a:00:00:01",
    "manufacturer": "IKEA of Sweden",
    "model": "TRADFRI bulb E27",
    "quirk_applied": True,
}


class FakeHostFiles:
    """In-memory stand-in for the ssh transport that records every call."""

    def __init__(self, text: str = LIVE_CONFIG, **extra: str) -> None:
        self.files = {"/config/configuration.yaml": text, **extra}
        self.calls: list[str] = []

    @property
    def writes(self) -> list[str]:
        return [call for call in self.calls if call.startswith("write ")]

    async def read_text(self, path: str) -> str:
        self.calls.append(f"read {path}")
        if path not in self.files:
            raise HostFileNotFound(f"{path} does not exist on the host")
        return self.files[path]

    async def write_text(self, path: str, content: str) -> str | None:
        self.calls.append(f"write {path}")
        existed = path in self.files
        self.files[path] = content
        return f"{path}.homeiq-20260818T000000Z.bak" if existed else None


def _recipe(host_files=None, **kwargs) -> AqaraFP1EQuirkRecipe:
    """A recipe wired for tests: no real restart or settle waits."""
    return AqaraFP1EQuirkRecipe(
        host_files,
        restart_timeout=1.0,
        restart_poll_interval=0.0,
        restart_min_wait=0.0,
        settle_timeout=0.0,
        settle_interval=0.0,
        **kwargs,
    )


def _with_devices(sim, *devices):
    sim.state["zha_devices"] = [dict(device) for device in devices]
    return sim


def _restart_applies_quirks(sim):
    """Model ZHA re-matching quirks when the core restarts.

    Wired to the restart service call rather than set eagerly, so a recipe that
    wrote the files but never restarted would still fail these tests.
    """
    original = sim.rest.call_service

    async def call_service(domain: str, service: str, **data):
        result = await original(domain, service, **data)
        if (domain, service) == ("homeassistant", "restart"):
            for device in sim.state["zha_devices"]:
                if device.get("manufacturer") != UNKNOWN_MANUFACTURER:
                    device["quirk_applied"] = True
        return result

    sim.rest.call_service = call_service
    return sim


# --- the shipped quirk file ------------------------------------------------


def test_the_shipped_quirk_is_valid_python_registering_the_evidenced_attribute():
    source = quirk_source()

    compile(source, FP1E_QUIRK_FILENAME, "exec")
    assert 'QuirkBuilder("Aqara", "lumi.sensor_occupy.agl8")' in source
    # 0x0142 is the one attribute with both an upstream definition and live
    # wire evidence; the header comment records both.
    assert "0x0142" in source
    assert "add_to_registry()" in source


# --- check -----------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_is_not_applicable_without_a_configured_write_path(sim):
    _with_devices(sim, INTERVIEWED)

    result = await _recipe().check(sim)

    assert result.status is CheckStatus.NOT_APPLICABLE
    assert "HOMEIQ_HA_SSH_HOST" in str(result.details)
    assert (await _recipe().plan(sim)).is_empty


@pytest.mark.asyncio
async def test_check_is_not_applicable_when_no_fp1e_is_joined(sim):
    _with_devices(sim, OTHER_DEVICE)
    files = FakeHostFiles()

    result = await _recipe(files).check(sim)

    assert result.status is CheckStatus.NOT_APPLICABLE
    assert files.calls == []


@pytest.mark.asyncio
async def test_check_needs_apply_on_an_instance_that_has_neither_key_nor_file(sim):
    _with_devices(sim, INTERVIEWED, UNINTERVIEWED)
    files = FakeHostFiles()

    result = await _recipe(files).check(sim)

    assert result.status is CheckStatus.NEEDS_APPLY
    assert result.details["unquirked"] == [INTERVIEWED["ieee"]]
    assert result.details["uninterviewed"] == [UNINTERVIEWED["ieee"]]
    assert any("custom_quirks_path" in d for d in result.details["drift"])
    assert any(QUIRK_PATH in d for d in result.details["drift"])


@pytest.mark.asyncio
async def test_check_issues_no_writes(sim):
    _with_devices(sim, INTERVIEWED)
    files = FakeHostFiles()

    await _recipe(files).check(sim)

    assert files.writes == []


@pytest.mark.asyncio
async def test_check_propagates_a_transport_failure_instead_of_calling_it_absent(sim):
    """ssh being down must not be classified as "the quirk is not deployed"."""
    _with_devices(sim, INTERVIEWED)
    files = FakeHostFiles()

    async def broken(_path: str) -> str:
        raise HostFileError("connection refused", returncode=255)

    files.read_text = broken

    with pytest.raises(HostFileError, match="connection refused"):
        await _recipe(files).check(sim)


# --- plan ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_plan_lists_the_key_the_file_and_the_restart(sim):
    _with_devices(sim, INTERVIEWED)
    files = FakeHostFiles()

    plan = await _recipe(files).plan(sim)

    described = plan.describe()
    assert "zha.custom_quirks_path" in described
    assert QUIRK_PATH in described
    assert "restart" in described
    assert files.writes == []


# --- apply -----------------------------------------------------------------


@pytest.mark.asyncio
async def test_apply_writes_the_key_and_the_file_then_restarts(sim):
    _restart_applies_quirks(_with_devices(sim, INTERVIEWED))
    files = FakeHostFiles()

    result = await _recipe(files).apply(sim)

    assert files.files[QUIRK_PATH] == quirk_source()
    block = parse_config(files.files["/config/configuration.yaml"])["zha"]
    assert block["custom_quirks_path"] == CUSTOM_QUIRKS_DIR
    assert any(change.action == "restart" for change in result.changed)
    assert sim.state["zha_devices"][0]["quirk_applied"] is True


@pytest.mark.asyncio
async def test_apply_keeps_every_other_line_of_configuration_yaml(sim):
    _restart_applies_quirks(_with_devices(sim, INTERVIEWED))
    files = FakeHostFiles()

    await _recipe(files).apply(sim)

    after = files.files["/config/configuration.yaml"]
    assert after.startswith(LIVE_CONFIG)
    assert "# Load frontend themes from the themes folder" in after


@pytest.mark.asyncio
async def test_apply_merges_into_an_existing_zha_block(sim):
    _restart_applies_quirks(_with_devices(sim, INTERVIEWED))
    files = FakeHostFiles(set_top_level(LIVE_CONFIG, "zha", {"database_path": "/config/zigbee.db"}))

    await _recipe(files).apply(sim)

    block = parse_config(files.files["/config/configuration.yaml"])["zha"]
    assert block["database_path"] == "/config/zigbee.db"
    assert block["custom_quirks_path"] == CUSTOM_QUIRKS_DIR


@pytest.mark.asyncio
async def test_second_apply_is_a_no_op(sim):
    _restart_applies_quirks(_with_devices(sim, INTERVIEWED))
    files = FakeHostFiles()
    recipe = _recipe(files)
    await recipe.apply(sim)
    writes_after_first = len(files.writes)
    config_after_first = files.files["/config/configuration.yaml"]

    second = await recipe.apply(sim)

    assert second.change_count == 0
    assert len(files.writes) == writes_after_first
    assert files.files["/config/configuration.yaml"] == config_after_first
    assert (await recipe.check(sim)).status is CheckStatus.SATISFIED
    assert (await recipe.plan(sim)).is_empty


@pytest.mark.asyncio
async def test_apply_rewrites_a_quirk_that_drifted_on_the_host(sim):
    _restart_applies_quirks(_with_devices(sim, INTERVIEWED))
    files = FakeHostFiles(
        set_top_level(LIVE_CONFIG, "zha", {"custom_quirks_path": CUSTOM_QUIRKS_DIR}),
        **{QUIRK_PATH: "# somebody edited this on the host\n"},
    )

    result = await _recipe(files).apply(sim)

    assert files.files[QUIRK_PATH] == quirk_source()
    assert result.change_count > 0


@pytest.mark.asyncio
async def test_apply_restores_configuration_yaml_when_the_config_check_fails(sim):
    _with_devices(sim, INTERVIEWED)
    sim.state["check_config"] = {"result": "invalid", "errors": "bad indentation"}
    files = FakeHostFiles()

    with pytest.raises(Exception, match="config check"):
        await _recipe(files).apply(sim)

    assert files.files["/config/configuration.yaml"] == LIVE_CONFIG


@pytest.mark.asyncio
async def test_apply_refuses_to_claim_success_when_a_device_stays_unquirked(sim):
    """The restart happened, the file is there, and the device did not take it."""
    _with_devices(sim, INTERVIEWED)  # no _restart_applies_quirks
    files = FakeHostFiles()

    with pytest.raises(Exception, match="still report quirk_applied=False"):
        await _recipe(files).apply(sim)


# --- the uninterviewed unit ------------------------------------------------


@pytest.mark.asyncio
async def test_an_uninterviewed_unit_is_reported_but_does_not_block_satisfied(sim):
    _restart_applies_quirks(_with_devices(sim, INTERVIEWED, UNINTERVIEWED))
    files = FakeHostFiles()
    recipe = _recipe(files)
    await recipe.apply(sim)

    result = await recipe.check(sim)

    assert result.status is CheckStatus.SATISFIED
    assert result.details["uninterviewed"] == [UNINTERVIEWED["ieee"]]
    assert result.details["quirked"] == [INTERVIEWED["ieee"]]
    # Named in the summary, not quietly dropped from the count.
    assert UNINTERVIEWED["ieee"] in result.summary


@pytest.mark.asyncio
async def test_verify_re_reads_rather_than_trusting_apply(sim):
    _restart_applies_quirks(_with_devices(sim, INTERVIEWED))
    files = FakeHostFiles()
    recipe = _recipe(files)
    await recipe.apply(sim)

    assert (await recipe.verify(sim)).ok is True

    del files.files[QUIRK_PATH]
    assert (await recipe.verify(sim)).ok is False


@pytest.mark.asyncio
async def test_a_quirked_unit_is_still_recognised_after_its_model_is_renamed(sim):
    """The quirk renames the model, so a filter on it alone loses the device."""
    _with_devices(sim, QUIRKED)
    files = FakeHostFiles(
        set_top_level(LIVE_CONFIG, "zha", {"custom_quirks_path": CUSTOM_QUIRKS_DIR}),
        **{QUIRK_PATH: quirk_source()},
    )

    result = await _recipe(files).check(sim)

    assert result.status is CheckStatus.SATISFIED
    assert result.details["quirked"] == [QUIRKED["ieee"]]


@pytest.mark.asyncio
async def test_an_install_with_only_uninterviewed_units_blocks_on_a_human(sim):
    """A correct install and no occupancy entity is not "satisfied"."""
    _with_devices(sim, UNINTERVIEWED)
    files = FakeHostFiles(
        set_top_level(LIVE_CONFIG, "zha", {"custom_quirks_path": CUSTOM_QUIRKS_DIR}),
        **{QUIRK_PATH: quirk_source()},
    )

    result = await _recipe(files).check(sim)

    assert result.status is CheckStatus.BLOCKED_ON_HUMAN
    assert "re-interview" in (result.human_action or "")
    assert (await _recipe(files).verify(sim)).ok is False


# --- registration ----------------------------------------------------------


def test_the_recipe_is_in_the_default_set():
    from homeiq_ha.agent.recipes import default_recipes

    assert "zha.aqara_fp1e_quirk" in {recipe.name for recipe in default_recipes()}
