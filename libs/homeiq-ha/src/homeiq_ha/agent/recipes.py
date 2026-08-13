"""Recipe sets for the HA init/setup agent.

Phases follow docs/ha-init-agent-design.md §7. Every ``check`` here reads only,
so an ``audit`` run classifies the whole set without touching the instance.

Field names come from live reads of the target instance, not from
documentation — the backup API in particular renamed ``schedule.state`` to
``schedule.recurrence``, and the encryption key lives at
``create_backup.password``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeiq_ha.client.errors import HAHumanGateRequired

from .backup import (
    BACKUP_TIMEOUT,
    BackupTimeout,
    available_agent_ids,
    wait_for_backup,
)
from .device_areas import ManifestDeviceAreasRecipe
from .diagnostics import (
    ScenePolicyRecipe,
    ZigbeeCoordinatorWatchdogRecipe,
    ZigbeeMeshHealthRecipe,
)
from .helpers import ManifestHelpersRecipe
from .integration import IntegrationRecipe
from .manifest import DEFAULT_MANIFEST_PATH, OrganizationManifest, load_manifest
from .organization import (
    ManifestEntityAliasesRecipe,
    ManifestEntityLabelsRecipe,
)
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
from .zha import ZHA_SERIAL_PATH, ZHAFormationRefused, ZHARecipe

if TYPE_CHECKING:
    from homeiq_ha.client import HAClient

# ---------------------------------------------------------------------------
# Phase 1 — safety
# ---------------------------------------------------------------------------


class BackupScheduleRecipe(Recipe):
    """Configure automatic backups.

    This is the gate for everything else. On a factory-fresh instance no
    backups exist at all, and ``automatic_backups_configured`` is false — the
    instance is one SD-card failure from total loss.
    """

    name = "safety.backup_schedule"
    phase = PHASE_SAFETY
    description = "Daily automatic backups with retention and encryption"

    def __init__(
        self,
        *,
        recurrence: str = "daily",
        copies: int = 7,
        agent_ids: tuple[str, ...] = (),
    ) -> None:
        self.recurrence = recurrence
        self.copies = copies
        #: Explicit destinations. Empty means "whatever this instance offers",
        #: resolved at run time from ``backup/agents/info``.
        self.agent_ids = agent_ids

    async def _config(self, ha: Any) -> dict[str, Any]:
        result = await ha.ws.send_command("backup/config/info")
        return dict((result or {}).get("config") or {})

    async def _available(self, ha: Any) -> tuple[str, ...]:
        return self.agent_ids or await available_agent_ids(ha)

    def _target_agent_ids(
        self, config: dict[str, Any], available: tuple[str, ...]
    ) -> tuple[str, ...]:
        """What ``create_backup.agent_ids`` should end up as.

        Explicitly named destinations are enforced. Otherwise an empty list is
        filled from what the instance offers, and a set the owner already chose
        is left alone.
        """
        if self.agent_ids:
            return self.agent_ids
        configured = self._configured_agent_ids(config)
        return configured or available

    @staticmethod
    def _configured_agent_ids(config: dict[str, Any]) -> tuple[str, ...]:
        create = config.get("create_backup") or {}
        return tuple(str(agent) for agent in create.get("agent_ids") or ())

    def _drift(self, config: dict[str, Any], available: tuple[str, ...]) -> list[Change]:
        """Drift this recipe can actually apply.

        The encryption key is deliberately excluded — not because the API
        can't set it (``backup/config/update`` accepts
        ``create_backup.password``; verified live 2026-08-11 on 2026.7.4)
        but because only a person can custody the key: a recipe-invented
        password makes every backup unrecoverable the day the store is lost.
        It is surfaced through :meth:`_needs_encryption_key` instead, and set
        on explicit human instruction only.
        """
        schedule = config.get("schedule") or {}
        retention = config.get("retention") or {}
        configured = self._configured_agent_ids(config)
        target = self._target_agent_ids(config, available)
        changes: list[Change] = []

        if schedule.get("recurrence") != self.recurrence:
            changes.append(
                Change("set", "schedule.recurrence", schedule.get("recurrence"), self.recurrence)
            )
        if retention.get("copies") != self.copies:
            changes.append(Change("set", "retention.copies", retention.get("copies"), self.copies))
        # A schedule with no destination is not a backup. Home Assistant leaves
        # automatic_backups_configured false and never writes anything, so a
        # recipe that skipped this would report success over a home with no
        # backups at all.
        if set(configured) != set(target):
            changes.append(Change("set", "create_backup.agent_ids", list(configured), list(target)))
        return changes

    @staticmethod
    def _needs_encryption_key(config: dict[str, Any]) -> bool:
        # Never read, log or diff the key itself — only whether one is set.
        return not (config.get("create_backup") or {}).get("password")

    async def check(self, ha: HAClient) -> CheckResult:
        config = await self._config(ha)
        available = await self._available(ha)
        drift = self._drift(config, available)
        details = {
            "automatic_backups_configured": config.get("automatic_backups_configured"),
            "drift": [c.describe() for c in drift],
            "encryption_key_set": not self._needs_encryption_key(config),
            "agent_ids": list(self._target_agent_ids(config, available)),
        }

        if not self._target_agent_ids(config, available):
            return CheckResult(
                CheckStatus.BLOCKED_ON_HUMAN,
                "no backup destination is available",
                details,
                human_action=(
                    "Add a backup location in Settings > System > Backups. "
                    "Home Assistant has nowhere to write a backup without one."
                ),
            )
        if drift:
            return CheckResult(
                CheckStatus.NEEDS_APPLY,
                f"{len(drift)} backup setting(s) need changing",
                details,
            )
        if self._needs_encryption_key(config):
            return CheckResult(
                CheckStatus.BLOCKED_ON_HUMAN,
                "backup schedule is configured but no encryption key is set",
                details,
                human_action=(
                    "Set a backup encryption password in Settings > System > "
                    "Backups and store the emergency kit off this host. "
                    "Without the key the backups are unrecoverable."
                ),
            )
        return CheckResult(CheckStatus.SATISFIED, "automatic backups configured", details)

    async def plan(self, ha: HAClient) -> Plan:
        config = await self._config(ha)
        return Plan(tuple(self._drift(config, await self._available(ha))))

    async def apply(self, ha: HAClient) -> ApplyResult:
        config = await self._config(ha)
        available = await self._available(ha)
        drift = self._drift(config, available)
        if not drift:
            return ApplyResult((), "already configured")

        payload: dict[str, Any] = {
            "schedule": {"recurrence": self.recurrence},
            "retention": {"copies": self.copies, "days": None},
        }
        target = self._target_agent_ids(config, available)
        if target:
            payload["create_backup"] = {"agent_ids": list(target)}
        await ha.ws.send_command("backup/config/update", fields=payload)
        return ApplyResult(tuple(drift), f"applied {len(drift)} backup setting(s)")

    async def verify(self, ha: HAClient) -> VerifyResult:
        config = await self._config(ha)
        remaining = [c.describe() for c in self._drift(config, await self._available(ha))]
        return VerifyResult(
            not remaining,
            "backup configuration matches intent"
            if not remaining
            else f"still drifted: {remaining}",
            {
                "remaining": remaining,
                "encryption_key_set": not self._needs_encryption_key(config),
                "automatic_backups_configured": config.get("automatic_backups_configured"),
            },
        )


class FirstBackupRecipe(Recipe):
    """Ensure at least one backup exists. An untested backup is a hope."""

    name = "safety.first_backup"
    phase = PHASE_SAFETY
    description = "At least one backup exists"

    def __init__(
        self,
        *,
        agent_ids: tuple[str, ...] = (),
        timeout: float = BACKUP_TIMEOUT,
    ) -> None:
        #: Explicit destinations; empty resolves from ``backup/agents/info``.
        self.agent_ids = agent_ids
        #: How long ``verify`` waits for the backup to finish being written.
        self.timeout = timeout

    async def _backups(self, ha: Any) -> list[dict[str, Any]]:
        result = await ha.ws.send_command("backup/info")
        return list((result or {}).get("backups") or [])

    async def _destinations(self, ha: Any) -> tuple[str, ...]:
        return self.agent_ids or await available_agent_ids(ha)

    async def check(self, ha: HAClient) -> CheckResult:
        backups = await self._backups(ha)
        if backups:
            return CheckResult(
                CheckStatus.SATISFIED, f"{len(backups)} backup(s) exist", {"count": len(backups)}
            )
        destinations = await self._destinations(ha)
        if not destinations:
            return CheckResult(
                CheckStatus.BLOCKED_ON_HUMAN,
                "no backups exist and there is nowhere to write one",
                {"count": 0, "agent_ids": []},
                human_action=(
                    "Add a backup location in Settings > System > Backups. "
                    "backup/generate needs at least one destination agent."
                ),
            )
        return CheckResult(
            CheckStatus.NEEDS_APPLY,
            "no backups exist",
            {"count": 0, "agent_ids": list(destinations)},
        )

    async def plan(self, ha: HAClient) -> Plan:
        if await self._backups(ha):
            return Plan()
        destinations = await self._destinations(ha)
        return Plan((Change("create", "full backup", after=list(destinations)),))

    async def apply(self, ha: HAClient) -> ApplyResult:
        if await self._backups(ha):
            return ApplyResult((), "a backup already exists")
        destinations = await self._destinations(ha)
        await ha.ws.send_command(
            "backup/generate",
            fields={"name": "homeiq-initial", "agent_ids": list(destinations)},
        )
        return ApplyResult((Change("create", "full backup"),), "backup requested")

    async def verify(self, ha: HAClient) -> VerifyResult:
        # backup/generate only *starts* the job. Re-reading straight away would
        # see zero backups and fail a run that is merely still writing one.
        try:
            status = await wait_for_backup(ha, timeout=self.timeout)
        except BackupTimeout as exc:
            return VerifyResult(False, str(exc), {"count": len(exc.last.backup_ids)})
        return VerifyResult(
            True,
            f"{len(status.backup_ids)} backup(s) present",
            {"count": len(status.backup_ids)},
        )


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
# Phase 3 — organization
# ---------------------------------------------------------------------------


class _RegistryNamesRecipe(Recipe):
    """Ensure a named set exists in one registry. Idempotent by name."""

    registry: str = ""

    def __init__(self, wanted: tuple[str, ...]) -> None:
        self.wanted = wanted

    async def _existing(self, ha: Any) -> set[str]:
        entries = await ha.ws.send_command(f"config/{self.registry}/list")
        return {entry["name"] for entry in entries or []}

    async def _missing(self, ha: Any) -> list[str]:
        existing = await self._existing(ha)
        return [name for name in self.wanted if name not in existing]

    async def check(self, ha: HAClient) -> CheckResult:
        missing = await self._missing(ha)
        if not missing:
            return CheckResult(CheckStatus.SATISFIED, f"all {len(self.wanted)} present")
        return CheckResult(CheckStatus.NEEDS_APPLY, f"{len(missing)} missing", {"missing": missing})

    async def plan(self, ha: HAClient) -> Plan:
        return Plan(
            tuple(
                Change("create", f"{self.registry}:{name}", after=name)
                for name in await self._missing(ha)
            )
        )

    async def apply(self, ha: HAClient) -> ApplyResult:
        created: list[Change] = []
        for name in await self._missing(ha):
            await ha.ws.send_command(f"config/{self.registry}/create", name=name)
            created.append(Change("create", f"{self.registry}:{name}", after=name))
        return ApplyResult(tuple(created), f"created {len(created)}")

    async def verify(self, ha: HAClient) -> VerifyResult:
        missing = await self._missing(ha)
        return VerifyResult(
            not missing,
            "all present" if not missing else f"still missing {missing}",
        )


class FloorsRecipe(_RegistryNamesRecipe):
    name = "organization.floors"
    phase = PHASE_ORGANIZATION
    description = "Floors exist"
    registry = "floor_registry"


class AreasRecipe(_RegistryNamesRecipe):
    """Areas are load-bearing, not cosmetic: 2026.7 graduated area-targeted
    triggers and conditions, so automations target areas and adapt as devices
    change."""

    name = "organization.areas"
    phase = PHASE_ORGANIZATION
    description = "Areas exist"
    registry = "area_registry"


class ManifestAreasRemoveRecipe(Recipe):
    """Remove areas the manifest declares as artifacts (``areas_remove``).

    Hard guard: removal only ever applies to an EMPTY area. While any device
    or entity is still assigned, the row reports BLOCKED_ON_HUMAN instead of
    deleting — the standing never-do is "deleting areas with assigned
    devices", and a stale removal row must not orphan anything. Runs after
    :class:`ManifestDeviceAreasRecipe` so manifest-declared device moves
    (e.g. the Hue "tv" zone's strips moving to living_room, TAP-5974) have
    already emptied the area by the time removal is considered.
    """

    name = "organization.areas_remove"
    phase = PHASE_ORGANIZATION
    description = "Manifest-declared artifact areas are absent"

    def __init__(self, manifest: OrganizationManifest) -> None:
        self.manifest = manifest

    async def _occupancy(self, ha: Any) -> dict[str, dict[str, int]]:
        """area_id -> counts of devices/entities still assigned, for rows that exist."""
        existing = {
            area["area_id"]
            for area in await ha.ws.send_command("config/area_registry/list") or []
        }
        wanted = [r for r in self.manifest.areas_remove if r.area_id in existing]
        if not wanted:
            return {}
        devices = await ha.ws.send_command("config/device_registry/list") or []
        entities = await ha.ws.send_command("config/entity_registry/list") or []
        occupancy: dict[str, dict[str, int]] = {}
        for removal in wanted:
            occupancy[removal.area_id] = {
                "devices": sum(1 for d in devices if d.get("area_id") == removal.area_id),
                "entities": sum(1 for e in entities if e.get("area_id") == removal.area_id),
            }
        return occupancy

    async def check(self, ha: HAClient) -> CheckResult:
        occupancy = await self._occupancy(ha)
        if not occupancy:
            return CheckResult(
                CheckStatus.SATISFIED,
                f"all {len(self.manifest.areas_remove)} declared removal(s) absent",
            )
        occupied = {a: c for a, c in occupancy.items() if c["devices"] or c["entities"]}
        if occupied:
            return CheckResult(
                CheckStatus.BLOCKED_ON_HUMAN,
                f"{len(occupied)} removal-declared area(s) still occupied",
                {"occupied": occupied},
                human_action=(
                    "Areas declared for removal still hold devices/entities: "
                    f"{sorted(occupied)}. Move or unassign them (or drop the "
                    "manifest areas_remove row) before removal can apply."
                ),
            )
        return CheckResult(
            CheckStatus.NEEDS_APPLY,
            f"{len(occupancy)} empty artifact area(s) to remove",
            {"to_remove": sorted(occupancy)},
        )

    async def plan(self, ha: HAClient) -> Plan:
        occupancy = await self._occupancy(ha)
        return Plan(
            tuple(
                Change("delete", f"area:{area_id}", before=area_id)
                for area_id, counts in sorted(occupancy.items())
                if not counts["devices"] and not counts["entities"]
            )
        )

    async def apply(self, ha: HAClient) -> ApplyResult:
        # Re-check emptiness at apply time — the registry may have changed
        # since check(); the guard is load-bearing, not advisory.
        occupancy = await self._occupancy(ha)
        deleted: list[Change] = []
        for area_id, counts in sorted(occupancy.items()):
            if counts["devices"] or counts["entities"]:
                continue
            await ha.ws.send_command("config/area_registry/delete", area_id=area_id)
            deleted.append(Change("delete", f"area:{area_id}", before=area_id))
        return ApplyResult(tuple(deleted), f"deleted {len(deleted)} empty area(s)")

    async def verify(self, ha: HAClient) -> VerifyResult:
        existing = {
            area["area_id"]
            for area in await ha.ws.send_command("config/area_registry/list") or []
        }
        lingering = [r.area_id for r in self.manifest.areas_remove if r.area_id in existing]
        return VerifyResult(
            not lingering,
            "all declared removals absent" if not lingering else f"still present: {lingering}",
        )


class LabelsRecipe(_RegistryNamesRecipe):
    name = "organization.labels"
    phase = PHASE_ORGANIZATION
    description = "Labels exist"
    registry = "label_registry"


class DevicesHaveAreasRecipe(Recipe):
    """Report devices with no area.

    Assignment is intentionally not automated: guessing which room a device is
    in from its name is exactly the kind of plausible-but-wrong change that is
    expensive to unpick later. The recipe surfaces the list and stops.
    """

    name = "organization.device_areas"
    phase = PHASE_ORGANIZATION
    description = "Every device is assigned to an area"

    async def _unassigned(self, ha: Any) -> list[str]:
        devices = await ha.ws.send_command("config/device_registry/list")
        return [
            device.get("name_by_user") or device.get("name") or device["id"]
            for device in devices or []
            if not device.get("area_id") and not device.get("disabled_by")
        ]

    async def check(self, ha: HAClient) -> CheckResult:
        unassigned = await self._unassigned(ha)
        if not unassigned:
            return CheckResult(CheckStatus.SATISFIED, "every device has an area")
        return CheckResult(
            CheckStatus.BLOCKED_ON_HUMAN,
            f"{len(unassigned)} device(s) have no area",
            {"unassigned": unassigned},
            human_action=(
                "Assign an area to each listed device. Which room a device is "
                "in cannot be inferred safely from its name."
            ),
        )

    async def plan(self, _ha: HAClient) -> Plan:
        return Plan()

    async def apply(self, _ha: HAClient) -> ApplyResult:
        return ApplyResult((), "device-to-area assignment is a human decision")

    async def verify(self, ha: HAClient) -> VerifyResult:
        unassigned = await self._unassigned(ha)
        return VerifyResult(not unassigned, f"{len(unassigned)} device(s) still unassigned")


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
# Phase 6 — integrations
# ---------------------------------------------------------------------------


class TeamTrackerRecipe(IntegrationRecipe):
    """Team Tracker, with the entity_id trap asserted rather than trusted.

    The README says the sensor will be ``sensor.team_tracker``. That is only
    true for the YAML path — the UI config flow prefills the name as
    ``"{league} - {team}"``, producing e.g. ``sensor.nfl_las_vegas_raiders``.
    HomeIQ's sports-api filters for entity_ids *containing* ``team_tracker``
    and would match nothing.

    So this recipe verifies the resulting entity_id instead of trusting the
    documented default, and fails loudly when the name does not carry the
    marker.
    """

    #: The substring sports-api filters on.
    MARKER = "team_tracker"

    name = "integrations.team_tracker"
    description = "Team Tracker configured with a sports-api-compatible entity_id"

    def __init__(
        self,
        *,
        steps: tuple[dict[str, Any], ...] = ({},),
        needs_user_input: str | None = None,
    ) -> None:
        super().__init__(
            "teamtracker",
            title="Team Tracker",
            steps=steps,
            needs_user_input=needs_user_input,
        )
        self.name = "integrations.team_tracker"

    async def _marked_entities(self, ha: Any) -> list[str]:
        entities = await ha.ws.list_entities()
        return [
            entity["entity_id"]
            for entity in entities or []
            if self.MARKER in entity.get("entity_id", "")
        ]

    async def check(self, ha: HAClient) -> CheckResult:
        base = await super().check(ha)
        if base.status is not CheckStatus.SATISFIED:
            return base

        marked = await self._marked_entities(ha)
        if marked:
            return CheckResult(
                CheckStatus.SATISFIED,
                f"Team Tracker loaded with {len(marked)} matching entity/entities",
                {"entity_ids": marked},
            )
        return CheckResult(
            CheckStatus.BLOCKED_ON_HUMAN,
            "Team Tracker is loaded but no entity_id contains 'team_tracker'",
            {"marker": self.MARKER},
            human_action=(
                "Rename the Team Tracker sensor so its entity_id contains "
                "'team_tracker' (e.g. sensor.team_tracker_raiders). sports-api "
                "filters on that substring and will otherwise see nothing."
            ),
        )

    async def verify(self, ha: HAClient) -> VerifyResult:
        base = await super().verify(ha)
        if not base.ok:
            return base
        marked = await self._marked_entities(ha)
        return VerifyResult(
            bool(marked),
            f"{len(marked)} entity_id(s) carry the '{self.MARKER}' marker",
            {"entity_ids": marked},
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
    """
    if manifest is None and DEFAULT_MANIFEST_PATH.exists():
        manifest = load_manifest()

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
        ZHARecipe(ZHA_SERIAL_PATH),
        ZigbeeCoordinatorWatchdogRecipe(ZHA_SERIAL_PATH),
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
    "ManifestDeviceAreasRecipe",
    "ManifestEntityAliasesRecipe",
    "ManifestEntityLabelsRecipe",
    "ManifestHelpersRecipe",
    "TeamTrackerRecipe",
    "ZHAFormationRefused",
    "ZHARecipe",
    "default_recipes",
]
