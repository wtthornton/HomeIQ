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

from .backup import BackupScheduleRecipe, FirstBackupRecipe
from .config_yaml import HttpLoginThresholdRecipe, RecorderTuningRecipe
from .device_areas import ManifestAreasRemoveRecipe, ManifestDeviceAreasRecipe
from .diagnostics import (
    ScenePolicyRecipe,
    ZigbeeCoordinatorWatchdogRecipe,
    ZigbeeMeshHealthRecipe,
)
from .enablement import LocalCalendarRecipe
from .helpers import ManifestHelpersRecipe
from .host_files import host_files_from_env
from .integration import IntegrationRecipe, TeamTrackerRecipe
from .manifest import DEFAULT_MANIFEST_PATH, OrganizationManifest, load_manifest
from .netobserve import observer_from_env
from .organization import (
    ManifestEntityAliasesRecipe,
    ManifestEntityLabelsRecipe,
)
from .powercalc import PowercalcRecipe
from .recipe import (
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
from .unclaimed import UnclaimedDevicesRecipe
from .zha import ZHA_SERIAL_PATH, ZHAFormationRefused, ZHARecipe
from .zha_quirks import AqaraFP1EQuirkRecipe

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
# Phase 5 — HACS (confirm-absent: the appliance vendors components at build
# time, domains/core-platform/home-assistant/Dockerfile — no Supervisor, no
# runtime HACS, so there is nothing for this phase to install)
# ---------------------------------------------------------------------------


class HACSAbsentRecipe(Recipe):
    """Confirm HACS is absent, as the headless appliance build intends.

    Powercalc, Team Tracker and the Aqara FP1E quirk are vendored into
    ``/config/custom_components`` (and ``custom_zha_quirks``) at image build
    time; the same build step asserts no ``hacs`` custom_component exists in
    the image. A HACS config entry appearing at runtime on this appliance is a
    build-integrity regression, not a setup step the agent should ever drive —
    there is no Supervisor to install a "Get HACS" add-on through in the first
    place.
    """

    name = "hacs.absent"
    phase = PHASE_HACS
    description = "HACS is absent by design (components vendored at build time)"

    async def _hacs_entry(self, ha: Any) -> dict[str, Any] | None:
        entries = await ha.rest.get_config_entries()
        for entry in entries or []:
            if entry.get("domain") == "hacs":
                return dict(entry)
        return None

    async def check(self, ha: HAClient) -> CheckResult:
        entry = await self._hacs_entry(ha)
        if entry is None:
            return CheckResult(CheckStatus.SATISFIED, "HACS is absent, as designed")
        return CheckResult(
            CheckStatus.BLOCKED_ON_HUMAN,
            f"HACS config entry present ({entry.get('state')}) on a build that "
            "vendors components directly",
            {"state": entry.get("state")},
            human_action=(
                "This appliance image ships no Supervisor and vendors Powercalc, "
                "Team Tracker and the Aqara FP1E quirk at build time — a HACS "
                "config entry here means the build itself needs fixing, not a "
                "setup step. Remove HACS and rebuild the image."
            ),
        )

    async def plan(self, _ha: HAClient) -> Plan:
        return Plan()

    async def apply(self, _ha: HAClient) -> ApplyResult:
        return ApplyResult((), "hacs.absent is confirm-only; there is nothing to apply")

    async def verify(self, ha: HAClient) -> VerifyResult:
        entry = await self._hacs_entry(ha)
        return VerifyResult(
            entry is None,
            "HACS absent" if entry is None else f"HACS config entry present ({entry.get('state')})",
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
    host_files = host_files_from_env()

    recipes: list[Recipe] = [
        BackupScheduleRecipe(),
        FirstBackupRecipe(),
        CoreConfigRecipe(currency="USD", country="US"),
        # The two YAML-only rows (design doc 1.1 and 2.4). They need the
        # core_ssh write path; without HOMEIQ_HA_SSH_HOST they report
        # NOT_APPLICABLE instead of pretending the instance is hardened.
        HttpLoginThresholdRecipe(host_files),
        RecorderTuningRecipe(host_files),
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
        # No add-on recipes: this appliance ships a headless HA Container with
        # no Supervisor (domains/core-platform/home-assistant/Dockerfile).
        # OpenThread Border Router deliberately absent too: no Thread radio on
        # this host — owner decision 2026-08-12, add-on uninstalled same day.
        HACSAbsentRecipe(),
        # Powercalc is vendored at build time (phase 5): confirm a discovered
        # power sensor, never a HACS download. TAP-5431.
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
        # The FP1E reports presence on Aqara's 0xFCC0 cluster, which no
        # shipped quirk claims for this model string, so the units join
        # with no occupancy entity at all. Needs the core_ssh write path
        # to deploy the quirk; without it, NOT_APPLICABLE. TAP-6018.
        AqaraFP1EQuirkRecipe(host_files),
        ZigbeeCoordinatorWatchdogRecipe(zha_serial_path),
        ZigbeeMeshHealthRecipe(),
        # LAN devices no configured integration owns. Needs a network
        # observer (HOMEIQ_NETWORK_OBSERVER_URL); without one it reports
        # NOT_APPLICABLE rather than implying the network is clean. TAP-6402.
        UnclaimedDevicesRecipe(observer_from_env()),
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
    "PHASE_CORRECTNESS",
    "PHASE_HACS",
    "PHASE_INTEGRATIONS",
    "PHASE_ORGANIZATION",
    "PHASE_SAFETY",
    "ZHA_SERIAL_PATH",
    "AqaraFP1EQuirkRecipe",
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
    "HACSAbsentRecipe",
    "HttpLoginThresholdRecipe",
    "IntegrationRecipe",
    "LabelsRecipe",
    "LocalCalendarRecipe",
    "PowercalcRecipe",
    "RecorderTuningRecipe",
    "ManifestDeviceAreasRecipe",
    "ManifestEntityAliasesRecipe",
    "ManifestEntityLabelsRecipe",
    "ManifestHelpersRecipe",
    "TeamTrackerRecipe",
    "ZHAFormationRefused",
    "ZHARecipe",
    "default_recipes",
]
