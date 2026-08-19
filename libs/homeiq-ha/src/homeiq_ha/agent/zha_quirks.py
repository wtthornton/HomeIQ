"""Recipe that installs HomeIQ's custom ZHA quirks on the Home Assistant host.

Some Zigbee devices report everything they measure on a manufacturer-specific
cluster that no shipped quirk claims. Home Assistant then joins the device
happily, marks ``quirk_applied = False``, and exposes every standard cluster it
found — while the one measurement the device exists to take stays invisible.
That is the Aqara FP1E's state on this mesh: illuminance, temperature,
humidity, battery, and no occupancy entity at all, because presence lives on
``0xFCC0`` and the shipped quirk for that hardware is registered under a
different model string. See :mod:`homeiq_ha.agent.quirks.aqara_fp1e` for the
attribute mapping and the evidence behind it.

Getting a quirk loaded takes three things, and this recipe owns all three so
that none of them can be half-done:

1. ``zha.custom_quirks_path`` in ``configuration.yaml``, which is the only way
   to tell ``zhaquirks.setup()`` where to look;
2. the quirk file itself in that directory, byte-identical to the copy in this
   repo — the repo is the source of truth and the host is a deployment target,
   never the other way round;
3. a core restart, because the ``zha:`` block is YAML-only config that Home
   Assistant reads once at startup.

The engine's contract is kept literally: ``check`` and ``plan`` only ever call
``read_text``, a converged instance produces an empty plan and a zero-change
``apply``, and without ``HOMEIQ_HA_SSH_HOST`` there is no write path so the
recipe is ``NOT_APPLICABLE`` rather than blocked on a person — nobody can
unblock a missing transport by clicking something in Home Assistant.
"""

from __future__ import annotations

import asyncio
from importlib import resources
from typing import TYPE_CHECKING, Any

from homeiq_ha.client.errors import HAClientError

from .config_yaml import HA_CONFIG_PATH, parse_config, set_top_level
from .core_restart import (
    RESTART_MIN_WAIT,
    RESTART_POLL_INTERVAL,
    RESTART_TIMEOUT,
    restart_core,
)
from .host_files import HA_CONFIG_DIR, HostFileNotFound
from .recipe import (
    PHASE_INTEGRATIONS,
    ApplyResult,
    Change,
    CheckResult,
    CheckStatus,
    Plan,
    Recipe,
    VerifyResult,
)

if TYPE_CHECKING:
    from homeiq_ha.client import HAClient

    from .host_files import HostFiles

#: Where Home Assistant is told to look for custom quirks.
CUSTOM_QUIRKS_DIR = f"{HA_CONFIG_DIR}/custom_zha_quirks"

#: The ``configuration.yaml`` block that carries the path.
ZHA_CONFIG_KEY = "zha"

#: Filename of the quirk inside :data:`CUSTOM_QUIRKS_DIR`, and of the module in
#: this package that is its source.
FP1E_QUIRK_FILENAME = "aqara_fp1e.py"

#: Zigbee model string of the units this quirk exists for.
FP1E_MODEL = "lumi.sensor_occupy.agl8"

#: What Home Assistant reports as the manufacturer of a device whose Basic
#: cluster never answered. Such a device carries no manufacturer/model pair for
#: any quirk to match, so it is reported rather than counted.
UNKNOWN_MANUFACTURER = "unk_manufacturer"

#: Seconds to keep re-reading ``zha/devices`` after a restart before deciding
#: the quirk did not take. ZHA rebuilds its device list asynchronously, so the
#: first read after ``state == RUNNING`` can still be empty.
QUIRK_SETTLE_TIMEOUT = 60.0

#: Gap between those reads.
QUIRK_SETTLE_INTERVAL = 5.0


def quirk_source(filename: str = FP1E_QUIRK_FILENAME) -> str:
    """The committed text of a quirk, read from this package's data.

    Read through :mod:`importlib.resources` rather than ``__file__`` so the
    recipe works from an installed wheel as well as a source checkout.
    """
    return (resources.files(__package__) / "quirks" / filename).read_text(encoding="utf-8")


class AqaraFP1EQuirkRecipe(Recipe):
    """Install the Aqara FP1E quirk so each unit gains an occupancy entity.

    ``check`` is satisfied when the config key points at
    :data:`CUSTOM_QUIRKS_DIR`, the file there matches this repo byte for byte,
    and every FP1E the coordinator knows *by manufacturer and model* has
    ``quirk_applied = True``.

    That last qualifier is load-bearing. A device whose interview never got as
    far as reading the Basic cluster reports its manufacturer as
    :data:`UNKNOWN_MANUFACTURER`, and a quirk registry keyed on
    manufacturer/model has nothing to match it against — no quirk, custom or
    shipped, can reach it until the device is woken and re-interviewed. Gating
    on those devices would make this recipe permanently unsatisfiable for a
    reason it cannot fix, so they are excluded from the gate and named in
    ``details["uninterviewed"]`` and in the summary instead of being silently
    dropped. When they are *all* that is left — a correct install with nothing
    it can match — the answer is ``BLOCKED_ON_HUMAN``, because waking the
    hardware needs hands and no number of re-applies substitutes for them.
    """

    name = "zha.aqara_fp1e_quirk"
    phase = PHASE_INTEGRATIONS
    description = "Aqara FP1E custom ZHA quirk installed, giving each unit an occupancy entity"

    def __init__(
        self,
        host_files: HostFiles | None = None,
        *,
        config_path: str = HA_CONFIG_PATH,
        quirks_dir: str = CUSTOM_QUIRKS_DIR,
        restart_timeout: float = RESTART_TIMEOUT,
        restart_poll_interval: float = RESTART_POLL_INTERVAL,
        restart_min_wait: float = RESTART_MIN_WAIT,
        settle_timeout: float = QUIRK_SETTLE_TIMEOUT,
        settle_interval: float = QUIRK_SETTLE_INTERVAL,
    ) -> None:
        """
        Args:
            host_files: Transport to the HA host. ``None`` means no write path
                is provisioned, which the recipe reports rather than works
                around.
            config_path: The ``configuration.yaml`` to edit.
            quirks_dir: Directory the quirk is deployed to.
            restart_timeout: Seconds to wait for the core after the restart.
            restart_poll_interval: Gap between liveness polls.
            restart_min_wait: Floor before the first liveness poll.
            settle_timeout: Seconds to wait for ZHA to re-apply quirks.
            settle_interval: Gap between those reads.
        """
        self.host_files = host_files
        self.config_path = config_path
        self.quirks_dir = quirks_dir
        self.restart_timeout = restart_timeout
        self.restart_poll_interval = restart_poll_interval
        self.restart_min_wait = restart_min_wait
        self.settle_timeout = settle_timeout
        self.settle_interval = settle_interval

    @property
    def quirk_path(self) -> str:
        """Absolute path of the quirk on the Home Assistant host."""
        return f"{self.quirks_dir}/{FP1E_QUIRK_FILENAME}"

    @property
    def _transport(self) -> HostFiles:
        if self.host_files is None:
            raise HAClientError(
                f"no SSH write path to {self.quirks_dir}: set HOMEIQ_HA_SSH_HOST "
                "(see docs/deployment/DEPLOYMENT_RUNBOOK.md)"
            )
        return self.host_files

    # -- reads ---------------------------------------------------------------

    async def _config_text(self) -> str:
        return await self._transport.read_text(self.config_path)

    def _config_drift(self, text: str) -> tuple[dict[str, Any], list[Change]]:
        """The ``zha:`` block this recipe wants, and the change that gets there.

        Merged key by key, so an operator's other ``zha:`` settings survive.
        """
        block = parse_config(text).get(ZHA_CONFIG_KEY)
        if block is not None and not isinstance(block, dict):
            raise HAClientError(
                f"{self.config_path}: top-level {ZHA_CONFIG_KEY!r} is a "
                f"{type(block).__name__}, not a mapping; refusing to merge"
            )
        merged = dict(block or {})
        current = merged.get("custom_quirks_path")
        if current == self.quirks_dir:
            return merged, []
        merged["custom_quirks_path"] = self.quirks_dir
        return merged, [
            Change("set", f"{ZHA_CONFIG_KEY}.custom_quirks_path", current, self.quirks_dir)
        ]

    async def _file_drift(self) -> list[Change]:
        """Whether the deployed quirk differs from the committed one."""
        wanted = quirk_source()
        # Bytes, not characters: the header carries em dashes, so len() of the
        # str disagrees with what the host reports and makes the diff look wrong.
        size = f"{len(wanted.encode())} bytes"
        try:
            on_host = await self._transport.read_text(self.quirk_path)
        except HostFileNotFound:
            # Only this: a transport that could not reach the host raises
            # HostFileError and is left to propagate, because "ssh is down"
            # must not read as "the quirk is missing" and trigger a rewrite.
            return [Change("create", self.quirk_path, None, size)]
        if on_host == wanted:
            return []
        return [Change("update", self.quirk_path, f"{len(on_host.encode())} bytes", size)]

    @staticmethod
    def _is_fp1e(device: dict[str, Any]) -> bool:
        """Whether a ``zha/devices`` entry is one of the units this recipe owns.

        Three fields are consulted because the quirk changes two of them.
        ``friendly_name`` in the quirk rewrites ``model`` — and the reported
        signature with it — from ``lumi.sensor_occupy.agl8`` to "Presence
        Sensor FP1E", so a filter on ``model`` alone finds the device before
        the quirk lands and loses it afterwards. ``quirk_class`` is what
        survives: ZHA reports it as ``aqara_fp1e:(Aqara / <zigbee model>)``,
        naming the model the quirk actually matched on.
        """
        return FP1E_MODEL in (
            str(device.get("model") or ""),
            str((device.get("signature") or {}).get("model") or ""),
        ) or FP1E_MODEL in str(device.get("quirk_class") or "")

    async def _fp1e_devices(self, ha: Any) -> list[dict[str, Any]]:
        devices = await ha.ws.send_command("zha/devices")
        return [d for d in devices or [] if self._is_fp1e(d)]

    @staticmethod
    def _split(devices: list[dict[str, Any]]) -> tuple[list[str], list[str], list[str]]:
        """Split FP1E units into quirked, still-unquirked, and uninterviewed."""
        quirked, unquirked, uninterviewed = [], [], []
        for device in devices:
            ieee = str(device.get("ieee"))
            manufacturer = str(device.get("manufacturer") or "")
            if not manufacturer or manufacturer == UNKNOWN_MANUFACTURER:
                uninterviewed.append(ieee)
            elif device.get("quirk_applied"):
                quirked.append(ieee)
            else:
                unquirked.append(ieee)
        return quirked, unquirked, uninterviewed

    # -- recipe contract -----------------------------------------------------

    async def check(self, ha: HAClient) -> CheckResult:
        """Read config, the deployed file and the device list. Writes nothing."""
        if self.host_files is None:
            return CheckResult(
                CheckStatus.NOT_APPLICABLE,
                f"no SSH write path to {self.quirks_dir}; the quirk cannot be deployed",
                {"quirks_dir": self.quirks_dir, "env": "HOMEIQ_HA_SSH_HOST"},
            )
        devices = await self._fp1e_devices(ha)
        if not devices:
            return CheckResult(
                CheckStatus.NOT_APPLICABLE,
                f"no {FP1E_MODEL} device is joined to this mesh",
                {"model": FP1E_MODEL},
            )
        _, config_changes = self._config_drift(await self._config_text())
        file_changes = await self._file_drift()
        quirked, unquirked, uninterviewed = self._split(devices)
        details: dict[str, Any] = {
            "quirked": quirked,
            "unquirked": unquirked,
            "uninterviewed": uninterviewed,
        }
        drift = [*config_changes, *file_changes]
        if drift or unquirked:
            return CheckResult(
                CheckStatus.NEEDS_APPLY,
                f"{len(drift)} install step(s) and {len(unquirked)} device(s) need the quirk",
                {"drift": [change.describe() for change in drift], **details},
            )
        if not quirked:
            # Every FP1E on the mesh is uninterviewed, so the install is
            # correct and has nothing to act on. Not SATISFIED — that would
            # report a presence sensor as fixed while no occupancy entity
            # exists — and not NEEDS_APPLY either, because re-running apply
            # cannot interview a device. Someone has to wake the hardware.
            return CheckResult(
                CheckStatus.BLOCKED_ON_HUMAN,
                f"quirk installed, but all {len(uninterviewed)} FP1E unit(s) are "
                f"uninterviewed so none can match it: {uninterviewed}",
                details,
                human_action=(
                    "Press the FP1E's reset button once to wake it, then "
                    "re-interview it in Settings > Devices > ZHA. Its Basic "
                    "cluster has to answer before any quirk can match it, and "
                    "only physical access can make that happen."
                ),
            )
        summary = f"quirk installed; {len(quirked)} FP1E unit(s) quirked"
        if uninterviewed:
            # Partial success is not success. Reporting SATISFIED here because
            # *some* unit matched demoted "this presence sensor has no
            # occupancy entity" to a suffix on a green line, which is how a
            # dead FP1E survived six nightly audits unnoticed.
            summary += (
                f"; {len(uninterviewed)} uninterviewed and unmatchable until "
                f"re-interviewed: {uninterviewed}"
            )
            return CheckResult(
                CheckStatus.BLOCKED_ON_HUMAN,
                summary,
                details,
                human_action=(
                    f"{len(uninterviewed)} FP1E unit(s) never finished the Zigbee "
                    f"interview, so their manufacturer reads "
                    f"'{UNKNOWN_MANUFACTURER}' and no quirk can match them: "
                    f"{uninterviewed}. Confirm the unit has power, press its "
                    "reset button once to wake it, then re-interview it in "
                    "Settings > Devices > ZHA. Its Basic cluster has to answer "
                    "before any quirk can match it, and only physical access "
                    "can make that happen."
                ),
            )
        return CheckResult(CheckStatus.SATISFIED, summary, details)

    async def plan(self, ha: HAClient) -> Plan:
        if self.host_files is None or not await self._fp1e_devices(ha):
            return Plan()
        _, config_changes = self._config_drift(await self._config_text())
        changes = [*config_changes, *await self._file_drift()]
        if not changes:
            return Plan()
        return Plan((*changes, Change("restart", "home assistant core", after="RUNNING")))

    async def apply(self, ha: HAClient) -> ApplyResult:
        text = await self._config_text()
        merged, changes = self._config_drift(text)
        file_changes = await self._file_drift()
        if not changes and not file_changes:
            return ApplyResult((), "quirk already installed; nothing to write")

        if file_changes:
            await self._transport.write_text(self.quirk_path, quirk_source())
        if changes:
            await self._transport.write_text(
                self.config_path, set_top_level(text, ZHA_CONFIG_KEY, merged)
            )
        applied = [*changes, *file_changes]
        try:
            await restart_core(
                ha,
                timeout=self.restart_timeout,
                poll_interval=self.restart_poll_interval,
                min_wait=self.restart_min_wait,
            )
        except Exception:
            # An instance that will not boot cannot be fixed remotely, so put
            # the previous configuration.yaml back before surfacing why the
            # restart failed. The quirk file itself is inert until the config
            # key points at it, so it is left in place.
            if changes:
                await self._transport.write_text(self.config_path, text)
            raise
        applied.append(Change("restart", "home assistant core", after="RUNNING"))

        quirked, unquirked, uninterviewed = await self._settled(ha)
        if unquirked:
            raise HAClientError(
                f"quirk deployed to {self.quirk_path} and HA restarted, but "
                f"{unquirked} still report quirk_applied=False — refusing to "
                "report success. Check the HA log for 'Unexpected exception "
                "importing custom quirk'."
            )
        summary = f"quirk installed; {len(quirked)} FP1E unit(s) now quirked"
        if uninterviewed:
            summary += f"; {len(uninterviewed)} uninterviewed: {uninterviewed}"
        return ApplyResult(tuple(applied), summary)

    async def _settled(self, ha: Any) -> tuple[list[str], list[str], list[str]]:
        """Re-read the device list until nothing is left unquirked, or time runs out."""
        deadline = asyncio.get_running_loop().time() + self.settle_timeout
        while True:
            split = self._split(await self._fp1e_devices(ha))
            if not split[1] or asyncio.get_running_loop().time() > deadline:
                return split
            await asyncio.sleep(self.settle_interval)

    async def verify(self, ha: HAClient) -> VerifyResult:
        """Independently re-read the host and the device list."""
        result = await self.check(ha)
        ok = result.status in (CheckStatus.SATISFIED, CheckStatus.NOT_APPLICABLE)
        return VerifyResult(ok, result.summary, result.details)


__all__ = [
    "CUSTOM_QUIRKS_DIR",
    "FP1E_MODEL",
    "FP1E_QUIRK_FILENAME",
    "QUIRK_SETTLE_INTERVAL",
    "QUIRK_SETTLE_TIMEOUT",
    "UNKNOWN_MANUFACTURER",
    "ZHA_CONFIG_KEY",
    "AqaraFP1EQuirkRecipe",
    "quirk_source",
]
