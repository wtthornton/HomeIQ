"""HARegistryWriter tests: the single verified path for name and area writes.

The load-bearing case is ``test_a_write_that_changes_nothing_is_not_reported_as
_success`` -- every other property here is in service of it.
"""

from __future__ import annotations

from typing import Any

import pytest
from homeiq_ha.registry_writer import (
    HARegistryWriter,
    UnknownTarget,
    WriteNotVerified,
)

from tests.simulators import SimHA


@pytest.fixture
def sim() -> SimHA:
    instance = SimHA()
    instance.state["areas"] = [{"area_id": "office", "name": "Office"}]
    return instance


@pytest.fixture
def writer(sim: SimHA) -> HARegistryWriter:
    return HARegistryWriter(sim.ws)


def _device(sim: SimHA, device_id: str) -> dict[str, Any]:
    return next(d for d in sim.state["devices"] if d["id"] == device_id)


def _entity(sim: SimHA, entity_id: str) -> dict[str, Any]:
    return next(e for e in sim.state["entities"] if e["entity_id"] == entity_id)


@pytest.mark.asyncio
async def test_entity_name_lands_and_is_reported_with_its_previous_value(sim, writer):
    result = await writer.set_entity_name("light.wled_0", "Desk Lamp")

    assert result.wrote is True
    assert result.previous is None
    assert _entity(sim, "light.wled_0")["name"] == "Desk Lamp"


@pytest.mark.asyncio
async def test_device_name_is_written_to_name_by_user_not_name(sim, writer):
    # HA keeps `name` integration-owned; a rename that targeted it would be
    # rejected by the command schema, which accepts only name_by_user.
    await writer.set_device_name("dev0", "Office Ceiling")

    entry = _device(sim, "dev0")
    assert entry["name_by_user"] == "Office Ceiling"
    assert entry["name"] == "WLED 0"


@pytest.mark.asyncio
async def test_a_write_that_changes_nothing_is_not_reported_as_success(sim, writer):
    """The sync_name_to_ha failure mode, reproduced at the gateway boundary.

    A command that is accepted and silently drops the field is indistinguishable
    from a successful one until the registry is read back.
    """

    async def accepts_and_ignores(command_type: str, **kwargs: Any) -> Any:
        if command_type == "config/entity_registry/update":
            return {}  # 200 OK, nothing written -- exactly what HA did
        return await original(command_type, **kwargs)

    original = sim.ws.send_command
    sim.ws.send_command = accepts_and_ignores

    with pytest.raises(WriteNotVerified, match="changed nothing"):
        await writer.set_entity_name("light.wled_0", "Desk Lamp")


@pytest.mark.asyncio
async def test_a_value_already_in_the_registry_is_not_rewritten(sim, writer):
    await writer.set_entity_area("light.wled_0", "office")
    sim.ws.calls.clear()

    result = await writer.set_entity_area("light.wled_0", "office")

    assert result.wrote is False
    assert not [c for c in sim.ws.calls if c[0].endswith("/update")]


@pytest.mark.asyncio
async def test_entity_id_slugs_are_never_renamed(sim, writer):
    """entity_id is a foreign key in HomeIQ; only new_entity_id can move it."""
    await writer.set_entity_name("light.wled_0", "Desk Lamp")
    await writer.set_entity_area("light.wled_0", "office")
    await writer.set_device_name("dev0", "Office Ceiling")

    assert all("new_entity_id" not in fields for _, fields in sim.ws.calls)
    assert _entity(sim, "light.wled_0")["entity_id"] == "light.wled_0"


@pytest.mark.asyncio
async def test_an_area_that_does_not_exist_is_refused_before_the_write(sim, writer):
    # HA stores an unknown area_id verbatim, so this would read back equal to the
    # request and verify cleanly while stranding the device in a phantom area.
    with pytest.raises(UnknownTarget, match="no area 'attic'"):
        await writer.set_device_area("dev0", "attic")

    assert not [c for c in sim.ws.calls if c[0].endswith("/update")]


@pytest.mark.asyncio
async def test_unknown_device_and_entity_are_distinguished_from_a_failed_write(writer):
    with pytest.raises(UnknownTarget, match="no device 'ghost'"):
        await writer.set_device_name("ghost", "Nope")

    with pytest.raises(UnknownTarget, match="no entity 'light.ghost'"):
        await writer.set_entity_name("light.ghost", "Nope")


@pytest.mark.asyncio
async def test_every_write_is_logged_with_caller_before_and_after(sim, caplog):
    """An unexpected rename must be traceable to its origin (TAP-6232)."""
    writer = HARegistryWriter(sim.ws, caller="test-suite.audit")

    with caplog.at_level("INFO", logger="homeiq_ha.registry_writer"):
        await writer.set_entity_name("light.wled_0", "Desk Lamp")

    record = caplog.records[-1].getMessage()
    assert "caller=test-suite.audit" in record
    assert "None -> 'Desk Lamp'" in record  # before -> after
    assert "light.wled_0" in record


@pytest.mark.asyncio
async def test_a_refused_write_is_logged_before_it_raises(sim, caplog):
    async def accepts_and_ignores(command_type: str, **kwargs: Any) -> Any:
        if command_type == "config/entity_registry/update":
            return {}
        return await original(command_type, **kwargs)

    original = sim.ws.send_command
    sim.ws.send_command = accepts_and_ignores
    writer = HARegistryWriter(sim.ws, caller="test-suite.audit")

    with (
        caplog.at_level("WARNING", logger="homeiq_ha.registry_writer"),
        pytest.raises(WriteNotVerified),
    ):
        await writer.set_entity_name("light.wled_0", "Desk Lamp")

    record = caplog.records[-1].getMessage()
    assert "NOT verified" in record
    assert "caller=test-suite.audit" in record


@pytest.mark.asyncio
async def test_clearing_a_name_restores_the_integration_default(sim, writer):
    await writer.set_device_name("dev0", "Office Ceiling")

    result = await writer.set_device_name("dev0", None)

    assert result.wrote is True
    assert _device(sim, "dev0")["name_by_user"] is None
