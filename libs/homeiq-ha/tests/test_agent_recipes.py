"""Recipe tests against fixtures, never the live home.

The fixture below mirrors the shapes read live from the target instance, so a
recipe that works here works there — including the backup API's
``schedule.recurrence`` (not ``schedule.state``) rename.
"""

from __future__ import annotations

import copy
from typing import Any

import pytest
from homeiq_ha.agent import CheckStatus, HAInitAgent
from homeiq_ha.agent.recipes import (
    AddonRecipe,
    AreasRecipe,
    BackupScheduleRecipe,
    CoreConfigRecipe,
    DevicesHaveAreasRecipe,
    FirstBackupRecipe,
    TeamTrackerRecipe,
    default_recipes,
)

#: Captured from the live instance on 2026-08-01, before any change.
FRESH_INSTANCE: dict[str, Any] = {
    "backup_config": {
        "agents": {},
        "automatic_backups_configured": False,
        "create_backup": {"agent_ids": [], "password": None, "include_database": True},
        "retention": {"copies": None, "days": None},
        "schedule": {"days": [], "recurrence": "never", "time": None},
    },
    "backups": [],
    "core_config": {"currency": "USD", "country": "US", "time_zone": "America/Los_Angeles"},
    "areas": [
        {"area_id": "living_room", "name": "Living Room"},
        {"area_id": "kitchen", "name": "Kitchen"},
        {"area_id": "bedroom", "name": "Bedroom"},
    ],
    "floors": [],
    "labels": [],
    "devices": [{"id": f"dev{i}", "name": f"WLED {i}", "area_id": None} for i in range(19)],
    "entities": [{"entity_id": f"light.wled_{i}"} for i in range(164)],
    "addons": [],
    "config_entries": [],
}


class SimWs:
    """WebSocket half of the simulator."""

    def __init__(self, state: dict[str, Any]) -> None:
        self.state = state
        self.writes: list[str] = []

    async def send_command(
        self,
        command_type: str,
        *,
        _timeout: float | None = None,
        fields: dict[str, Any] | None = None,
        **payload: Any,
    ) -> Any:
        fields = fields or {}
        args = {**payload, **fields}

        if command_type == "backup/config/info":
            return {"config": self.state["backup_config"]}
        if command_type == "backup/info":
            return {"backups": self.state["backups"], "state": "idle"}
        if command_type == "get_config":
            return self.state["core_config"]
        if command_type.endswith("_registry/list"):
            return self.state[_registry_key(command_type)]

        if command_type == "supervisor/api":
            return await self._supervisor(args)

        # Everything below writes.
        self.writes.append(command_type)

        if command_type == "backup/config/update":
            self.state["backup_config"]["schedule"].update(args.get("schedule") or {})
            self.state["backup_config"]["retention"].update(args.get("retention") or {})
            self.state["backup_config"]["automatic_backups_configured"] = True
            return None
        if command_type == "backup/generate":
            self.state["backups"].append({"backup_id": "b1", "name": args.get("name")})
            return {"backup_id": "b1"}
        if command_type == "config/core/update":
            self.state["core_config"].update(args)
            return None
        if command_type.endswith("_registry/create"):
            key = _registry_key(command_type)
            self.state[key].append({f"{key[:-1]}_id": args["name"], "name": args["name"]})
            return self.state[key][-1]
        return None

    async def _supervisor(self, args: dict[str, Any]) -> Any:
        endpoint = args["endpoint"]
        method = args.get("method", "get")
        if method == "get" and endpoint == "/addons":
            return {"addons": self.state["addons"]}
        self.writes.append(f"supervisor {method} {endpoint}")
        if endpoint.startswith("/store/addons/") and endpoint.endswith("/install"):
            slug = endpoint.split("/")[3]
            self.state["addons"].append({"slug": slug, "state": "stopped"})
            return None
        if endpoint.startswith("/addons/") and endpoint.endswith("/start"):
            slug = endpoint.split("/")[2]
            for addon in self.state["addons"]:
                if addon["slug"] == slug:
                    addon["state"] = "started"
            return None
        return None

    async def list_entities(self) -> list[dict[str, Any]]:
        return self.state["entities"]

    async def supervisor_api(
        self, endpoint: str, *, method: str = "get", _payload: dict[str, Any] | None = None,
        timeout: float = 900,
    ) -> Any:
        return await self.send_command(
            "supervisor/api",
            fields={"endpoint": endpoint, "method": method, "timeout": int(timeout)},
        )


def _registry_key(command_type: str) -> str:
    # config/area_registry/list -> areas
    registry = command_type.split("/")[1].removesuffix("_registry")
    return {"area": "areas", "floor": "floors", "label": "labels", "device": "devices"}[registry]


class SimRest:
    def __init__(self, state: dict[str, Any]) -> None:
        self.state = state
        self.writes: list[str] = []

    async def request(self, method: str, path: str, **_kwargs: Any) -> Any:
        if method.upper() != "GET":
            self.writes.append(f"{method.upper()} {path}")
        if path == "/api/config/config_entries/entry":
            return self.state["config_entries"]
        return {}

    async def get_config_entries(self) -> list[dict[str, Any]]:
        return await self.request("GET", "/api/config/config_entries/entry")

    async def run_config_flow(self, domain: str, _steps: list[dict[str, Any]], **_c: Any) -> Any:
        self.writes.append(f"config_flow {domain}")
        self.state["config_entries"].append({"domain": domain, "state": "loaded"})
        return {"type": "create_entry"}


class SimHA:
    """Fixture-backed Home Assistant simulator."""

    def __init__(self, state: dict[str, Any] | None = None) -> None:
        self.state = copy.deepcopy(state or FRESH_INSTANCE)
        self.base_url = "http://sim.test"
        self.ws = SimWs(self.state)
        self.rest = SimRest(self.state)

    @property
    def writes(self) -> list[str]:
        return self.ws.writes + self.rest.writes


@pytest.fixture
def sim() -> SimHA:
    return SimHA()


# --- audit over the full default set --------------------------------------


@pytest.mark.asyncio
async def test_audit_of_the_default_set_writes_nothing_and_classifies_everything(sim):
    agent = HAInitAgent(default_recipes())

    report = await agent.audit(sim)

    assert sim.writes == [], f"audit wrote: {sim.writes}"
    assert report.wrote_nothing
    assert len(report.outcomes) == len(default_recipes())
    # Every recipe produced a status and none crashed.
    assert all(o.error is None for o in report.outcomes), [
        (o.name, o.error) for o in report.outcomes if o.error
    ]
    assert {o.check.status for o in report.outcomes} <= set(CheckStatus)


# --- backup ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_backup_schedule_detects_a_never_scheduled_instance(sim):
    result = await BackupScheduleRecipe().check(sim)
    assert result.status is CheckStatus.NEEDS_APPLY
    assert result.details["automatic_backups_configured"] is False


@pytest.mark.asyncio
async def test_backup_schedule_uses_recurrence_not_state(sim):
    """schedule.state was renamed to schedule.recurrence; writing the old key
    would silently no-op."""
    await BackupScheduleRecipe(recurrence="daily", copies=7).apply(sim)
    assert sim.state["backup_config"]["schedule"]["recurrence"] == "daily"
    assert sim.state["backup_config"]["retention"]["copies"] == 7


@pytest.mark.asyncio
async def test_backup_schedule_is_idempotent(sim):
    recipe = BackupScheduleRecipe(recurrence="daily", copies=7)
    await recipe.apply(sim)
    sim.ws.writes.clear()

    second = await recipe.apply(sim)

    assert second.change_count == 0
    assert sim.writes == []


@pytest.mark.asyncio
async def test_a_missing_encryption_key_is_a_human_gate_not_an_endless_diff(sim):
    """backup/config/update cannot set the encryption key, so treating it as
    appliable drift would make the recipe re-apply forever."""
    recipe = BackupScheduleRecipe(recurrence="daily", copies=7)
    await recipe.apply(sim)

    result = await recipe.check(sim)

    assert result.status is CheckStatus.BLOCKED_ON_HUMAN
    assert result.details["encryption_key_set"] is False
    assert "emergency kit" in (result.human_action or "")
    # The appliable half has converged.
    assert (await recipe.verify(sim)).ok


@pytest.mark.asyncio
async def test_backup_schedule_satisfied_once_a_key_exists(sim):
    sim.state["backup_config"]["create_backup"]["password"] = "set"
    recipe = BackupScheduleRecipe(recurrence="daily", copies=7)
    await recipe.apply(sim)

    assert (await recipe.check(sim)).status is CheckStatus.SATISFIED


@pytest.mark.asyncio
async def test_first_backup_reports_zero_backups(sim):
    result = await FirstBackupRecipe().check(sim)
    assert result.status is CheckStatus.NEEDS_APPLY
    assert result.details["count"] == 0


@pytest.mark.asyncio
async def test_first_backup_is_idempotent(sim):
    recipe = FirstBackupRecipe()
    assert (await recipe.apply(sim)).change_count == 1
    assert (await recipe.apply(sim)).change_count == 0


# --- core config ----------------------------------------------------------


@pytest.mark.asyncio
async def test_core_config_satisfied_when_already_correct(sim):
    result = await CoreConfigRecipe(currency="USD", country="US").check(sim)
    assert result.status is CheckStatus.SATISFIED


@pytest.mark.asyncio
async def test_core_config_detects_the_eur_default():
    sim = SimHA({**FRESH_INSTANCE, "core_config": {"currency": "EUR", "country": "US"}})
    result = await CoreConfigRecipe(currency="USD").check(sim)
    assert result.status is CheckStatus.NEEDS_APPLY
    assert "EUR" in result.details["drift"][0]


# --- organization ---------------------------------------------------------


@pytest.mark.asyncio
async def test_areas_creates_only_what_is_missing(sim):
    recipe = AreasRecipe(("Living Room", "Kitchen", "Bedroom", "Office"))

    result = await recipe.apply(sim)

    assert result.change_count == 1
    assert "Office" in result.changed[0].target


@pytest.mark.asyncio
async def test_areas_is_idempotent(sim):
    recipe = AreasRecipe(("Living Room", "Office"))
    await recipe.apply(sim)
    assert (await recipe.apply(sim)).change_count == 0
    assert (await recipe.verify(sim)).ok


@pytest.mark.asyncio
async def test_unassigned_devices_are_a_human_decision_not_a_guess(sim):
    result = await DevicesHaveAreasRecipe().check(sim)
    assert result.status is CheckStatus.BLOCKED_ON_HUMAN
    assert len(result.details["unassigned"]) == 19
    # Nothing is inferred from device names.
    assert (await DevicesHaveAreasRecipe().apply(sim)).change_count == 0


# --- add-ons --------------------------------------------------------------


@pytest.mark.asyncio
async def test_addon_installs_and_starts(sim):
    recipe = AddonRecipe("core_ssh", title="Terminal & SSH")
    assert (await recipe.check(sim)).status is CheckStatus.NEEDS_APPLY

    result = await recipe.apply(sim)

    assert result.change_count == 2
    assert (await recipe.verify(sim)).ok


@pytest.mark.asyncio
async def test_addon_is_idempotent(sim):
    recipe = AddonRecipe("otbr")
    await recipe.apply(sim)
    assert (await recipe.apply(sim)).change_count == 0


@pytest.mark.asyncio
async def test_installed_but_stopped_addon_needs_apply():
    sim = SimHA({**FRESH_INSTANCE, "addons": [{"slug": "otbr", "state": "stopped"}]})
    result = await AddonRecipe("otbr").check(sim)
    assert result.status is CheckStatus.NEEDS_APPLY
    assert result.details["state"] == "stopped"


# --- Team Tracker entity_id trap ------------------------------------------


@pytest.mark.asyncio
async def test_team_tracker_blocks_when_the_entity_id_lacks_the_marker():
    """The UI flow names the sensor "{league} - {team}", so the entity_id is
    sensor.nfl_las_vegas_raiders and sports-api — which filters on the
    substring 'team_tracker' — would match nothing."""
    sim = SimHA(
        {
            **FRESH_INSTANCE,
            "config_entries": [{"domain": "teamtracker", "state": "loaded"}],
            "entities": [{"entity_id": "sensor.nfl_las_vegas_raiders"}],
        }
    )

    result = await TeamTrackerRecipe().check(sim)

    assert result.status is CheckStatus.BLOCKED_ON_HUMAN
    assert "team_tracker" in (result.human_action or "")
    assert not (await TeamTrackerRecipe().verify(sim)).ok


@pytest.mark.asyncio
async def test_team_tracker_satisfied_when_the_entity_id_carries_the_marker():
    sim = SimHA(
        {
            **FRESH_INSTANCE,
            "config_entries": [{"domain": "teamtracker", "state": "loaded"}],
            "entities": [{"entity_id": "sensor.team_tracker_raiders"}],
        }
    )

    result = await TeamTrackerRecipe().check(sim)

    assert result.status is CheckStatus.SATISFIED
    assert result.details["entity_ids"] == ["sensor.team_tracker_raiders"]
    assert (await TeamTrackerRecipe().verify(sim)).ok


# --- end-to-end idempotency ----------------------------------------------


@pytest.mark.asyncio
async def test_second_apply_of_phase_three_makes_zero_changes(sim):
    agent = HAInitAgent([AreasRecipe(("Living Room", "Office"))])

    async def backup(_label: str) -> None:
        return None

    first = await agent.apply(sim, phase=3, backup=backup)
    second = await agent.apply(sim, phase=3, backup=backup)

    assert first.total_changes == 1
    assert second.total_changes == 0, second.describe()
