"""Recipe hub for the HA init/setup agent.

Phases follow docs/ha-init-agent-design.md §7. Every ``check`` reads only, so
an ``audit`` run classifies the whole set without touching the instance.

Recipes live in small thematic modules re-exported here so callers import
them unchanged: safety/backups in :mod:`.backup`, registry and manifest
organization in :mod:`.registry` and :mod:`.organization` (+
:mod:`.device_areas`, :mod:`.helpers`), integrations in :mod:`.integration`, ZHA onboarding in
:mod:`.zha`, report-only diagnostics in :mod:`.diagnostics`. This module
keeps the small phase-2/4/5 recipes and :func:`default_recipes`.

Field names come from live reads of the target instance, not from
documentation — the backup API in particular renamed ``schedule.state`` to
``schedule.recurrence``, and the encryption key lives at
``create_backup.password``.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from homeiq_ha.client.errors import HAHumanGateRequired

from .backup import BackupScheduleRecipe, FirstBackupRecipe
from .device_areas import ManifestAreasRemoveRecipe, ManifestDeviceAreasRecipe
from .diagnostics import (
    ScenePolicyRecipe,
    ZigbeeCoordinatorWatchdogRecipe,
    ZigbeeMeshHealthRecipe,
)
from .enablement import LocalCalendarRecipe
from .helpers import ManifestHelpersRecipe
from .integration import IntegrationRecipe, TeamTrackerRecipe
from .manifest import DEFAULT_MANIFEST_PATH, OrganizationManifest, load_manifest
from .organization import (
    ManifestEntityAliasesRecipe,
    ManifestEntityLabelsRecipe,
)
from .powercalc import PowercalcRecipe
from .recipe import (
    PHASE_ADDONS,
    PHASE_CORRECTNESS,
    PHASE_HACS,
    PHASE_INTEGRATIONS,
    PHASE_ORGANIZATION,
    PHASE_SAFETY,
    ApplyResult,
    Change,
    CheckResult,
    CheckStatus,
    Plan,
    Recipe,
    VerifyResult,
)
from .registry import (
    AreasRecipe,
    DevicesHaveAreasRecipe,
    FloorsRecipe,
    LabelsRecipe,
)
from .zha import ZHA_SERIAL_PATH, ZHAFormationRefused, ZHARecipe

if TYPE_CHECKING:
    from homeiq_ha.client import HAClient

# ---------------------------------------------------------------------------
# Phase 2 — correctness
# ---------------------------------------------------------------------------


class CoreConfigRecipe(Recipe):
    """Align core config values that silently corrupt downstream data.

    Currency in particular defaults to EUR on some installs, which makes every
    Energy dashboard cost wrong without any error appearing anywhere.
    """

    name = "correctness.core_config"
    phase = PHASE_CORRECTNESS
    description = "Currency, country and timezone match intent"

    def __init__(self, **wanted: str) -> None:
        self.wanted = wanted

    def _drift(self, config: dict[str, Any]) -> list[Change]:
        return [
            Change("set", key, config.get(key), value)
            for key, value in self.wanted.items()
            if config.get(key) != value
        ]

    async def check(self, ha: HAClient) -> CheckResult:
        config = await ha.ws.send_command("get_config")
        drift = self._drift(config or {})
        if not drift:
            return CheckResult(
                CheckStatus.SATISFIED,
                "core config matches intent",
                {key: (config or {}).get(key) for key in self.wanted},
            )
        return CheckResult(
            CheckStatus.NEEDS_APPLY,
            f"{len(drift)} core setting(s) need changing",
            {"drift": [c.describe() for c in drift]},
        )

    async def plan(self, ha: HAClient) -> Plan:
        return Plan(tuple(self._drift(await ha.ws.send_command("get_config") or {})))

    async def apply(self, ha: HAClient) -> ApplyResult:
        drift = self._drift(await ha.ws.send_command("get_config") or {})
        if not drift:
            return ApplyResult((), "already aligned")
        await ha.ws.send_command("config/core/update", fields=dict(self.wanted))
        return ApplyResult(tuple(drift), f"updated {len(drift)} core setting(s)")

    async def verify(self, ha: HAClient) -> VerifyResult:
        drift = self._drift(await ha.ws.send_command("get_config") or {})
        return VerifyResult(
            not drift,
            "core config matches intent"
            if not drift
            else f"still drifted: {[c.describe() for c in drift]}",
        )


# ---------------------------------------------------------------------------
# Phase 4 — add-ons
# ---------------------------------------------------------------------------


class AddonRecipe(Recipe):
    """Install and start one add-on through the Supervisor passthrough.

    Slugs are read from the store at runtime rather than computed: custom
    repository slugs are ``<sha1(url)[:8]>_<folder>``, and several built-in
    add-ons (ESPHome, Music Assistant) are not ``core_``-prefixed, so any logic
    that derives a slug gets those wrong.
    """

    phase = PHASE_ADDONS

    def __init__(self, slug: str, *, title: str | None = None, start: bool = True) -> None:
        self.slug = slug
        self.title = title or slug
        self.start = start
        self.name = f"addons.{slug}"
        self.description = f"Add-on {self.title} installed"

    async def _installed(self, ha: Any) -> dict[str, Any] | None:
        result = await ha.ws.supervisor_api("/addons", timeout=60)
        for addon in (result or {}).get("addons") or []:
            if addon.get("slug") == self.slug:
                return dict(addon)
        return None

    async def _unconfigured_required(self, ha: Any) -> list[str]:
        """Required options a person has not set yet.

        The Supervisor refuses to start an add-on whose required options are
        null (observed live: OTBR's ``device`` — which serial port carries the
        Thread radio is a hardware fact no agent can infer). Schema shape read
        live: a list of ``{"name", "required": bool, ...}`` entries.
        """
        info = await ha.ws.supervisor_api(f"/addons/{self.slug}/info", timeout=60)
        options = (info or {}).get("options") or {}
        return [
            str(entry["name"])
            for entry in (info or {}).get("schema") or []
            if entry.get("required") and options.get(entry.get("name")) is None
        ]

    async def check(self, ha: HAClient) -> CheckResult:
        addon = await self._installed(ha)
        if addon is None:
            return CheckResult(CheckStatus.NEEDS_APPLY, f"{self.title} is not installed")
        if self.start and addon.get("state") != "started":
            missing = await self._unconfigured_required(ha)
            if missing:
                return CheckResult(
                    CheckStatus.BLOCKED_ON_HUMAN,
                    f"{self.title} is installed but requires configuration",
                    {"state": addon.get("state"), "unconfigured": missing},
                    human_action=(
                        f"Set required option(s) {missing} for {self.title} in "
                        "Settings > Add-ons. These are hardware/site facts the "
                        "agent must not guess."
                    ),
                )
            return CheckResult(
                CheckStatus.NEEDS_APPLY,
                f"{self.title} is installed but {addon.get('state')}",
                {"state": addon.get("state")},
            )
        return CheckResult(CheckStatus.SATISFIED, f"{self.title} installed and running")

    async def plan(self, ha: HAClient) -> Plan:
        addon = await self._installed(ha)
        changes: list[Change] = []
        if addon is None:
            changes.append(Change("install add-on", self.slug, after="installed"))
        if self.start and (addon or {}).get("state") != "started":
            changes.append(Change("start add-on", self.slug, (addon or {}).get("state"), "started"))
        return Plan(tuple(changes))

    async def apply(self, ha: HAClient) -> ApplyResult:
        changes: list[Change] = []
        addon = await self._installed(ha)
        if addon is None:
            await ha.ws.supervisor_api(f"/store/addons/{self.slug}/install", method="post")
            changes.append(Change("install add-on", self.slug, after="installed"))
        if self.start:
            addon = await self._installed(ha)
            if (addon or {}).get("state") != "started":
                missing = await self._unconfigured_required(ha)
                if missing:
                    # The engine turns this into BLOCKED_ON_HUMAN; starting
                    # anyway would just make the Supervisor error instead.
                    raise HAHumanGateRequired(
                        f"{self.title} needs required option(s) {missing} set "
                        "by a person before it can start",
                        {"type": "addon_options", "unconfigured": missing},
                    )
                await ha.ws.supervisor_api(f"/addons/{self.slug}/start", method="post")
                changes.append(Change("start add-on", self.slug, after="started"))
        return ApplyResult(tuple(changes), f"{self.title}: {len(changes)} change(s)")

    async def verify(self, ha: HAClient) -> VerifyResult:
        addon = await self._installed(ha)
        if addon is None:
            return VerifyResult(False, f"{self.title} is still not installed")
        if self.start and addon.get("state") != "started":
            return VerifyResult(False, f"{self.title} is {addon.get('state')}, not started")
        return VerifyResult(True, f"{self.title} installed and running")


# ---------------------------------------------------------------------------
# Phase 5 — HACS
# ---------------------------------------------------------------------------


class HACSBootstrapRecipe(Recipe):
    """Install HACS via the official "Get HACS" add-on.

    The ``wget | bash`` method in most online guides is Container/Core-only and
    does not apply to a Supervised install. Onboarding then needs a GitHub
    device code, which is a hard human gate — but a cheap one: the code and URL
    are machine-readable, so the agent prints them and waits.
    """

    name = "hacs.bootstrap"
    phase = PHASE_HACS
    description = "HACS installed and onboarded"
    requires_human = True

    async def _hacs_entry(self, ha: Any) -> dict[str, Any] | None:
        entries = await ha.rest.get_config_entries()
        for entry in entries or []:
            if entry.get("domain") == "hacs":
                return dict(entry)
        return None

    async def check(self, ha: HAClient) -> CheckResult:
        entry = await self._hacs_entry(ha)
        if entry is not None and entry.get("state") == "loaded":
            return CheckResult(CheckStatus.SATISFIED, "HACS is installed and loaded")
        if entry is not None:
            return CheckResult(
                CheckStatus.NEEDS_APPLY,
                f"HACS config entry is {entry.get('state')}",
                {"state": entry.get("state")},
            )
        return CheckResult(
            CheckStatus.BLOCKED_ON_HUMAN,
            "HACS is not installed",
            human_action=(
                "Install the 'Get HACS' add-on, then complete GitHub device "
                "authorization. The agent surfaces the URL and code."
            ),
        )

    async def plan(self, ha: HAClient) -> Plan:
        if await self._hacs_entry(ha) is None:
            return Plan((Change("install", "HACS", after="config entry"),))
        return Plan()

    async def apply(self, ha: HAClient) -> ApplyResult:
        # run_config_flow raises HAHumanGateRequired on the device-code step,
        # which the engine turns into a hard stop carrying the code.
        await ha.rest.run_config_flow("hacs", [{}])
        return ApplyResult((Change("install", "HACS", after="config entry"),), "HACS onboarded")

    async def verify(self, ha: HAClient) -> VerifyResult:
        entry = await self._hacs_entry(ha)
        return VerifyResult(
            entry is not None and entry.get("state") == "loaded",
            "HACS loaded" if entry else "HACS config entry absent",
        )


# ---------------------------------------------------------------------------
# Default set
# ---------------------------------------------------------------------------


def default_recipes(
    manifest: OrganizationManifest | None = None,
) -> list[Recipe]:
    """The recipe set from the design doc's priority list.

    Deliberately excludes anything the design marked "do not install" —
    superseded add-ons, redundant InfluxDB/Grafana, and protocol integrations
    with no hardware present.

    Args:
        manifest: The committed organization manifest. When ``None``, the
            default path is loaded if it exists; without a manifest the
            manifest-driven organization recipes are simply absent (the
            report-only ones still run).

    The Zigbee coordinator address defaults to :data:`ZHA_SERIAL_PATH` and
    can be overridden with the ``HOMEIQ_ZHA_SERIAL_PATH`` environment
    variable — both for a coordinator IP change and for staging a
    watchdog alert against an unreachable target without a code edit
    (see docs/operations/init-gateway.md).
    """
    if manifest is None and DEFAULT_MANIFEST_PATH.exists():
        manifest = load_manifest()
    zha_serial_path = os.environ.get("HOMEIQ_ZHA_SERIAL_PATH") or ZHA_SERIAL_PATH

    recipes: list[Recipe] = [
        BackupScheduleRecipe(),
        FirstBackupRecipe(),
        CoreConfigRecipe(currency="USD", country="US"),
        FloorsRecipe(("Main Floor",)),
        # Manifest-driven when a manifest exists: the hardcoded default set
        # included "Bedroom", which would recreate the very artifact area the
        # manifest removes (TAP-5974).
        AreasRecipe(
            tuple(a.name for a in manifest.areas)
            if manifest is not None and manifest.areas
            else ("Living Room", "Kitchen", "Bedroom", "Office")
        ),
        LabelsRecipe(("critical", "exterior")),
        DevicesHaveAreasRecipe(),
        AddonRecipe("core_ssh", title="Terminal & SSH"),
        AddonRecipe("core_configurator", title="File editor"),
        # OpenThread Border Router deliberately absent: no Thread radio on
        # this host — owner decision 2026-08-12, add-on uninstalled same day.
        HACSBootstrapRecipe(),
        # Powercalc rides HACS (phase 5): download, restart, confirm a
        # discovered power sensor. TAP-5431.
        PowercalcRecipe(),
        # NWS deliberately absent: the stack already carries three weather
        # feeds (data-collectors/weather-api, websocket-ingestion's
        # OpenWeatherMap client, HA's met.no entry) — owner call 2026-08-12.
        TeamTrackerRecipe(
            needs_user_input=(
                "Add Team Tracker in Settings > Integrations: league and team "
                "are personal preferences the agent must not guess. Name the "
                "sensor so its entity_id contains 'team_tracker'."
            ),
        ),
        # Local Calendar (phase 6): feeds calendar-service once the entity
        # exists and CALENDAR_ENTITIES names it. TAP-5431.
        LocalCalendarRecipe(),
        ZHARecipe(zha_serial_path),
        ZigbeeCoordinatorWatchdogRecipe(zha_serial_path),
        ZigbeeMeshHealthRecipe(),
    ]
    if manifest is not None:
        recipes.extend(
            [
                ManifestDeviceAreasRecipe(manifest),
                ManifestAreasRemoveRecipe(manifest),
                ScenePolicyRecipe(manifest),
                ManifestEntityLabelsRecipe(manifest),
                ManifestEntityAliasesRecipe(manifest),
                ManifestHelpersRecipe(manifest),
            ]
        )
    return recipes


__all__ = [
    "PHASE_ADDONS",
    "PHASE_CORRECTNESS",
    "PHASE_HACS",
    "PHASE_INTEGRATIONS",
    "PHASE_ORGANIZATION",
    "PHASE_SAFETY",
    "ZHA_SERIAL_PATH",
    "AddonRecipe",
    "AreasRecipe",
    "BackupScheduleRecipe",
    "CoreConfigRecipe",
    "DevicesHaveAreasRecipe",
    "ManifestAreasRemoveRecipe",
    "ScenePolicyRecipe",
    "ZigbeeCoordinatorWatchdogRecipe",
    "ZigbeeMeshHealthRecipe",
    "FirstBackupRecipe",
    "FloorsRecipe",
    "HACSBootstrapRecipe",
    "IntegrationRecipe",
    "LabelsRecipe",
    "LocalCalendarRecipe",
    "PowercalcRecipe",
    "ManifestDeviceAreasRecipe",
    "ManifestEntityAliasesRecipe",
    "ManifestEntityLabelsRecipe",
    "ManifestHelpersRecipe",
    "TeamTrackerRecipe",
    "ZHAFormationRefused",
    "ZHARecipe",
    "default_recipes",
]
