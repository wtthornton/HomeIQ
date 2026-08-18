"""Tests for the HA init/setup agent engine.

The two load-bearing guarantees are proven here:

* ``audit`` issues **zero writes**, enforced rather than asserted.
* ``apply`` is idempotent — a second run against converged state makes
  **zero changes**.
"""

from __future__ import annotations

from typing import Any

import pytest
from homeiq_ha.agent import (
    ApplyResult,
    BackupGateNotSatisfied,
    Change,
    CheckResult,
    CheckStatus,
    HAInitAgent,
    Mode,
    Plan,
    ReadOnlyViolation,
    Recipe,
    VerifyResult,
    is_read_command,
    read_only,
)


class FakeWs:
    """Records every command that reaches Home Assistant."""

    def __init__(self, state: dict[str, Any]) -> None:
        self.state = state
        self.commands: list[str] = []
        self.calls: list[dict[str, Any]] = []

    async def send_command(
        self,
        command_type: str,
        *,
        timeout: float | None = None,
        fields: dict[str, Any] | None = None,
        **payload: Any,
    ) -> Any:
        self.commands.append(command_type)
        self.calls.append({"type": command_type, "timeout": timeout, "fields": fields, **payload})
        if command_type == "config/area_registry/list":
            return list(self.state["areas"])
        if command_type == "config/area_registry/create":
            self.state["areas"].append({"area_id": payload["name"], "name": payload["name"]})
            return self.state["areas"][-1]
        return None

    async def list_areas(self) -> list[dict[str, Any]]:
        return await self.send_command("config/area_registry/list")

    async def create_area(self, name: str, **fields: Any) -> dict[str, Any]:
        return await self.send_command("config/area_registry/create", name=name, **fields)


class FakeRest:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def request(self, method: str, path: str, **_kwargs: Any) -> Any:
        self.calls.append((method, path))
        return {}


class FakeHA:
    def __init__(self, state: dict[str, Any] | None = None) -> None:
        self.base_url = "http://ha.test"
        self.ws = FakeWs(state or {"areas": []})
        self.rest = FakeRest()

    @property
    def writes(self) -> list[str]:
        write_cmds = [c for c in self.ws.commands if not is_read_command(c)]
        write_calls = [f"{m} {p}" for m, p in self.rest.calls if m.upper() != "GET"]
        return write_cmds + write_calls


class AreasRecipe(Recipe):
    """Ensures a fixed set of areas exists. Idempotent by construction."""

    name = "organization.areas"
    phase = 3
    description = "Create the expected areas"

    def __init__(self, wanted: list[str]) -> None:
        self.wanted = wanted

    async def _missing(self, ha: Any) -> list[str]:
        existing = {area["name"] for area in await ha.ws.list_areas()}
        return [name for name in self.wanted if name not in existing]

    async def check(self, ha: Any) -> CheckResult:
        missing = await self._missing(ha)
        if not missing:
            return CheckResult(CheckStatus.SATISFIED, "all areas present")
        return CheckResult(
            CheckStatus.NEEDS_APPLY, f"{len(missing)} area(s) missing", {"missing": missing}
        )

    async def plan(self, ha: Any) -> Plan:
        return Plan(
            tuple(Change("create area", name, after=name) for name in await self._missing(ha))
        )

    async def apply(self, ha: Any) -> ApplyResult:
        created = []
        for name in await self._missing(ha):
            await ha.ws.create_area(name)
            created.append(Change("create area", name, after=name))
        return ApplyResult(tuple(created), f"created {len(created)} area(s)")

    async def verify(self, ha: Any) -> VerifyResult:
        missing = await self._missing(ha)
        return VerifyResult(
            not missing,
            "all areas present" if not missing else f"still missing {missing}",
        )


class BackupRecipe(Recipe):
    name = "safety.backup"
    phase = 1
    description = "Configure automatic backups"

    def __init__(self, *, satisfied: bool = False) -> None:
        self.satisfied = satisfied

    async def check(self, _ha: Any) -> CheckResult:
        if self.satisfied:
            return CheckResult(CheckStatus.SATISFIED, "backups configured")
        return CheckResult(CheckStatus.NEEDS_APPLY, "no backups configured")

    async def plan(self, _ha: Any) -> Plan:
        return Plan((Change("set", "backup schedule", before="never", after="daily"),))

    async def apply(self, _ha: Any) -> ApplyResult:
        self.satisfied = True
        return ApplyResult((Change("set", "backup schedule", after="daily"),), "configured")

    async def verify(self, _ha: Any) -> VerifyResult:
        return VerifyResult(self.satisfied, "backups configured")


class WritingCheckRecipe(Recipe):
    """A deliberately buggy recipe whose check() tries to write."""

    name = "buggy.writes_in_check"
    phase = 2

    async def check(self, ha: Any) -> CheckResult:
        await ha.ws.create_area("Sneaky")
        return CheckResult(CheckStatus.SATISFIED, "unreachable")

    async def plan(self, _ha: Any) -> Plan:
        return Plan()

    async def apply(self, _ha: Any) -> ApplyResult:
        return ApplyResult()

    async def verify(self, _ha: Any) -> VerifyResult:
        return VerifyResult(True, "")


class HumanGateRecipe(Recipe):
    name = "hacs.bootstrap"
    phase = 5
    requires_human = True

    async def check(self, _ha: Any) -> CheckResult:
        return CheckResult(
            CheckStatus.BLOCKED_ON_HUMAN,
            "HACS needs GitHub device authorization",
            human_action="Open https://github.com/login/device and enter ABCD-1234",
        )

    async def plan(self, _ha: Any) -> Plan:
        return Plan()

    async def apply(self, _ha: Any) -> ApplyResult:
        return ApplyResult()

    async def verify(self, _ha: Any) -> VerifyResult:
        return VerifyResult(True, "")


# --- read-only classification ---------------------------------------------


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("config/area_registry/list", True),
        ("config/entity_registry/get", True),
        ("config/area_registry/create", False),
        ("config/entity_registry/update", False),
        ("config/entity_registry/remove", False),
        ("config/label_registry/delete", False),
        ("backup/config/update", False),
    ],
)
def test_read_command_classification(command, expected):
    assert is_read_command(command) is expected


def test_supervisor_api_is_classified_by_its_http_method():
    assert is_read_command("supervisor/api", {"method": "get"}) is True
    assert is_read_command("supervisor/api", {"method": "post"}) is False


# --- the no-write guarantee -----------------------------------------------


@pytest.mark.asyncio
async def test_audit_issues_zero_writes():
    ha = FakeHA({"areas": [{"area_id": "kitchen", "name": "Kitchen"}]})
    agent = HAInitAgent([BackupRecipe(), AreasRecipe(["Kitchen", "Office"])])

    report = await agent.audit(ha)

    assert report.mode is Mode.AUDIT
    assert ha.writes == [], f"audit issued writes: {ha.writes}"
    assert report.wrote_nothing
    assert len(report.outcomes) == 2


@pytest.mark.asyncio
async def test_audit_classifies_every_recipe():
    ha = FakeHA()
    agent = HAInitAgent([BackupRecipe(), AreasRecipe(["Kitchen"]), HumanGateRecipe()])

    report = await agent.audit(ha)

    statuses = {o.name: o.check.status for o in report.outcomes}
    assert statuses == {
        "safety.backup": CheckStatus.NEEDS_APPLY,
        "organization.areas": CheckStatus.NEEDS_APPLY,
        "hacs.bootstrap": CheckStatus.BLOCKED_ON_HUMAN,
    }
    # An unconfigured home reporting every recipe NEEDS_APPLY is a correct
    # result, not a failure.
    assert len(report.by_status(CheckStatus.NEEDS_APPLY)) == 2


@pytest.mark.asyncio
async def test_a_write_during_check_is_blocked_not_merely_reported():
    ha = FakeHA()
    agent = HAInitAgent([WritingCheckRecipe()])

    report = await agent.audit(ha)

    assert ha.writes == []
    assert ha.ws.state["areas"] == []
    outcome = report.outcomes[0]
    assert outcome.error is not None
    assert "read-only" in outcome.error.lower()


@pytest.mark.asyncio
async def test_read_only_proxy_raises_on_write():
    ha = FakeHA()
    guarded = read_only(ha)
    await guarded.ws.list_areas()  # reads are fine
    with pytest.raises(ReadOnlyViolation):
        await guarded.ws.create_area("Nope")
    with pytest.raises(ReadOnlyViolation):
        await guarded.rest.request("POST", "/api/services/homeassistant/restart")


@pytest.mark.asyncio
async def test_plan_writes_nothing_either():
    ha = FakeHA()
    agent = HAInitAgent([AreasRecipe(["Kitchen", "Office"])])

    report = await agent.plan(ha)

    assert ha.writes == []
    plan = report.outcomes[0].plan
    assert plan is not None
    assert [c.target for c in plan.changes] == ["Kitchen", "Office"]


# --- idempotency ----------------------------------------------------------


@pytest.mark.asyncio
async def test_second_apply_against_converged_state_makes_zero_changes():
    ha = FakeHA()
    agent = HAInitAgent([AreasRecipe(["Kitchen", "Office", "Garage"])])

    first = await agent.apply(ha, phase=3, backup=_noop_backup)
    assert first.total_changes == 3
    assert first.outcomes[0].verified is not None
    assert first.outcomes[0].verified.ok

    second = await agent.apply(ha, phase=3, backup=_noop_backup)
    assert second.total_changes == 0, second.describe()
    assert second.outcomes[0].check.status is CheckStatus.SATISFIED


async def _noop_backup(_label: str) -> None:
    return None


# --- safety rules ---------------------------------------------------------


@pytest.mark.asyncio
async def test_phase_past_the_gate_refuses_to_run_without_a_backup():
    agent = HAInitAgent([AreasRecipe(["Kitchen"])])
    with pytest.raises(BackupGateNotSatisfied):
        await agent.apply(FakeHA(), phase=3)


@pytest.mark.asyncio
async def test_backup_phase_runs_without_a_backup_taker():
    """Phase 1 is the thing that creates the backup; requiring one would
    deadlock the gate."""
    agent = HAInitAgent([BackupRecipe()])
    report = await agent.apply(FakeHA(), phase=1)
    assert report.total_changes == 1
    assert report.halted_reason is None


@pytest.mark.asyncio
async def test_a_failed_pre_phase_backup_halts_before_applying():
    applied: list[str] = []

    class Tracking(AreasRecipe):
        async def apply(self, ha: Any) -> ApplyResult:
            applied.append("ran")
            return await super().apply(ha)

    async def failing_backup(_label: str) -> None:
        raise RuntimeError("storage agent unreachable")

    agent = HAInitAgent([Tracking(["Kitchen"])])
    report = await agent.apply(FakeHA(), phase=3, backup=failing_backup)

    assert applied == [], "recipe applied despite the pre-phase backup failing"
    assert report.halted_reason is not None
    assert "backup failed" in report.halted_reason


@pytest.mark.asyncio
async def test_human_gate_stops_progression_to_a_later_phase():
    """The gate is phase 5; a phase-6 recipe after it must never run, because a
    later phase may depend on what is still blocked."""

    class LaterRecipe(AreasRecipe):
        name = "later.areas"
        phase = 6

    ha = FakeHA()
    agent = HAInitAgent([HumanGateRecipe(), LaterRecipe(["Kitchen"])])
    report = await agent.apply(ha, backup=_noop_backup)

    assert report.halted_reason is not None
    assert "needs a person" in report.halted_reason
    assert report.blocked_on_human == ["hacs.bootstrap"]
    assert [o.name for o in report.outcomes] == ["hacs.bootstrap"]
    assert ha.writes == [], "work continued into a later phase past a human gate"


@pytest.mark.asyncio
async def test_human_gate_does_not_block_independent_siblings_in_the_same_phase():
    """Found by running the agent against a real instance: one device without
    an area used to prevent floors and labels from ever being created. On any
    real home something is always blocked, so that made the agent useless."""

    class BlockedSibling(Recipe):
        name = "organization.aaa_blocked"  # sorts first, so it runs first
        phase = 3

        async def check(self, _ha: Any) -> CheckResult:
            return CheckResult(
                CheckStatus.BLOCKED_ON_HUMAN, "needs a person", human_action="do a thing"
            )

        async def plan(self, _ha: Any) -> Plan:
            return Plan()

        async def apply(self, _ha: Any) -> ApplyResult:
            return ApplyResult()

        async def verify(self, _ha: Any) -> VerifyResult:
            return VerifyResult(True, "")

    ha = FakeHA()
    agent = HAInitAgent([BlockedSibling(), AreasRecipe(["Kitchen"])])

    report = await agent.apply(ha, phase=3, backup=_noop_backup)

    # The independent sibling still did its work...
    assert report.total_changes == 1
    assert {o.name for o in report.outcomes} == {
        "organization.aaa_blocked",
        "organization.areas",
    }
    # ...and the gate is still reported.
    assert report.blocked_on_human == ["organization.aaa_blocked"]
    assert report.halted_reason is not None


@pytest.mark.asyncio
async def test_verify_failure_marks_the_outcome_failed():
    class LyingRecipe(AreasRecipe):
        async def apply(self, _ha: Any) -> ApplyResult:
            # Claims success without doing anything — verify must catch it,
            # because a config POST returns before the reload lands.
            return ApplyResult((Change("create area", "Kitchen"),), "claimed")

    agent = HAInitAgent([LyingRecipe(["Kitchen"])])
    report = await agent.apply(FakeHA(), phase=3, backup=_noop_backup)

    assert not report.outcomes[0].ok
    assert report.halted_reason is not None


@pytest.mark.asyncio
async def test_recipes_run_in_phase_order():
    agent = HAInitAgent([AreasRecipe(["Kitchen"]), BackupRecipe(), HumanGateRecipe()])
    assert [r.phase for r in agent.recipes] == [1, 3, 5]


@pytest.mark.asyncio
async def test_report_describe_names_every_recipe_and_its_status():
    agent = HAInitAgent([BackupRecipe(), AreasRecipe(["Kitchen"]), HumanGateRecipe()])
    text = (await agent.audit(FakeHA())).describe()

    assert "mode: audit" in text
    for name in ("safety.backup", "organization.areas", "hacs.bootstrap"):
        assert name in text
    assert "blocked_on_human" in text
    assert "changes applied: 0" in text
