"""Recipes that own one top-level block of ``/config/configuration.yaml``.

Two rows of docs/ha-init-agent-design.md have no API at all — ``http:``
(row 1.1) and ``recorder:`` (row 2.4) are read once at startup from YAML — so
they are the only recipes in the set that write a file instead of calling
Home Assistant. The file access is the ``core_ssh`` transport in
:mod:`.host_files`, taken by injection so these tests never open a socket.

Editing a file someone else also edits demands three properties the rest of
the engine gets for free from an API:

**Never blind-write.** :func:`set_top_level` replaces exactly the lines of the
one block being owned. Every other byte of the file — comments, blank lines,
key order, and the ``!include`` tags that ``yaml.safe_load`` cannot even
parse — is carried through untouched.

**Idempotence is structural.** ``check`` parses the file and compares *values*,
so a file that already says what we want produces no changes and no write.
Textual comparison would rewrite the file whenever someone reformatted it.

**Nothing is clobbered.** A block is merged key-by-key: unknown keys under
``http:``/``recorder:`` survive, and the exclusion lists are unions, so a
hand-added exclusion is never dropped.

Both settings need a full core restart — neither block is reloadable — so
``apply`` restarts through :func:`~.core_restart.restart_core`, which
validates the config first and polls the instance back to life. The restart
is reported as a :class:`~.recipe.Change`, never done silently.
"""

from __future__ import annotations

import abc
import re
from typing import TYPE_CHECKING, Any

import yaml

from .core_restart import (
    RESTART_MIN_WAIT,
    RESTART_POLL_INTERVAL,
    RESTART_TIMEOUT,
    restart_core,
)
from .host_files import HA_CONFIG_DIR
from .recipe import (
    PHASE_CORRECTNESS,
    ApplyResult,
    Change,
    CheckResult,
    CheckStatus,
    Plan,
    Recipe,
    VerifyResult,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from homeiq_ha.client import HAClient

    from .host_files import HostFiles

#: The file both recipes edit.
HA_CONFIG_PATH = f"{HA_CONFIG_DIR}/configuration.yaml"


class ConfigYamlError(RuntimeError):
    """``configuration.yaml`` is not shaped the way a safe edit requires."""


# ---------------------------------------------------------------------------
# Parsing and block-level editing
# ---------------------------------------------------------------------------


def _opaque_tag(_loader: yaml.SafeLoader, tag_suffix: str, node: yaml.Node) -> str:
    """Render an unknown local tag as text instead of failing to construct it.

    ``configuration.yaml`` is full of HA's own tags — ``!include``,
    ``!include_dir_merge_named``, ``!secret``, ``!env_var`` — and
    ``yaml.safe_load`` raises on every one of them. The values are never
    inspected here; they only have to survive a parse so the blocks we *do*
    own can be compared.
    """
    value = getattr(node, "value", "")
    return f"!{tag_suffix} {value}" if isinstance(value, str) else f"!{tag_suffix}"


class _HAConfigLoader(yaml.SafeLoader):
    """SafeLoader that keeps Home Assistant's local tags as opaque text."""


_HAConfigLoader.add_multi_constructor("!", _opaque_tag)


class _BlockDumper(yaml.SafeDumper):
    """SafeDumper that indents sequences under their parent key.

    PyYAML's default puts list items at the parent's indent level. That is
    valid YAML but not how anyone writes ``configuration.yaml``, and this file
    is read by people.
    """

    def increase_indent(self, flow: bool = False, indentless: bool = False) -> None:
        # `indentless` is the thing being overridden: PyYAML passes True for a
        # sequence under a mapping key, and that is what strips its indent.
        del indentless
        super().increase_indent(flow, False)


#: A top-level mapping key: name at column zero followed by a colon.
_TOP_LEVEL_KEY = re.compile(r"^([A-Za-z_][A-Za-z0-9_.\-]*)\s*:")


def parse_config(text: str) -> dict[str, Any]:
    """Parse ``configuration.yaml`` into a mapping, tolerating HA's tags.

    Raises:
        ConfigYamlError: the document is not a mapping.
    """
    # The loader is driven directly rather than through ``yaml.load``, which
    # is the same three lines: ``_HAConfigLoader`` is a SafeLoader subclass, so
    # routing it through the API named "unsafe load" only invites the question.
    loader = _HAConfigLoader(text)
    try:
        data = loader.get_single_data()
    finally:
        loader.dispose()
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigYamlError(f"expected a mapping at the top level, got {type(data).__name__}")
    return data


def _top_level_lines(text: str, parsed: Mapping[str, Any]) -> list[tuple[int, str]]:
    """Line index of every top-level key, cross-checked against the parse.

    The editor works on lines so it can leave comments alone, but a regex over
    lines could be fooled by a column-zero key inside a quoted block. Agreeing
    with the parser is the guard: when the two disagree the file is shaped in
    a way this editor does not understand, and it refuses rather than guessing.
    """
    lines = text.splitlines(keepends=True)
    found = [
        (index, match.group(1))
        for index, line in enumerate(lines)
        if (match := _TOP_LEVEL_KEY.match(line))
    ]
    names = [name for _, name in found]
    if len(names) != len(set(names)):
        raise ConfigYamlError(f"duplicate top-level key(s) in the file: {names}")
    if set(names) != set(parsed):
        raise ConfigYamlError(
            "line scan and YAML parse disagree on the top-level keys "
            f"({sorted(set(names) ^ set(parsed))}); refusing to edit"
        )
    return found


def render_block(key: str, value: Any) -> str:
    """Render one top-level key as a YAML block, newline-terminated."""
    return yaml.dump(
        {key: value},
        Dumper=_BlockDumper,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
    )


def set_top_level(text: str, key: str, value: Any) -> str:
    """Return ``text`` with top-level ``key`` set to ``value``.

    Every line outside the replaced block is preserved byte for byte. A key
    that is absent is appended; a key that is present has its block swapped in
    place, keeping the surrounding comments — including the comment lines that
    introduce the *next* block, which are left with that block rather than
    consumed by this one.
    """
    parsed = parse_config(text)
    found = _top_level_lines(text, parsed)
    block = render_block(key, value)
    names = [name for _, name in found]

    if key not in names:
        base = text if text.endswith("\n") or not text else text + "\n"
        return f"{base}\n{block}"

    lines = text.splitlines(keepends=True)
    position = names.index(key)
    start = found[position][0]
    end = found[position + 1][0] if position + 1 < len(found) else len(lines)
    while end > start + 1 and (
        not lines[end - 1].strip() or lines[end - 1].lstrip().startswith("#")
    ):
        end -= 1
    return "".join(lines[:start]) + block + "".join(lines[end:])


# ---------------------------------------------------------------------------
# Recipes
# ---------------------------------------------------------------------------


class _ConfigYamlRecipe(Recipe):
    """Base for a recipe that owns some keys of one top-level block."""

    phase = PHASE_CORRECTNESS
    #: The top-level key this recipe owns keys inside of.
    key: str = ""

    def __init__(
        self,
        host_files: HostFiles | None = None,
        *,
        path: str = HA_CONFIG_PATH,
        restart_timeout: float = RESTART_TIMEOUT,
        restart_poll_interval: float = RESTART_POLL_INTERVAL,
        restart_min_wait: float = RESTART_MIN_WAIT,
    ) -> None:
        """
        Args:
            host_files: Transport to the HA host. ``None`` means no write path
                is provisioned, which the recipe reports rather than works
                around.
            path: The file to edit.
            restart_timeout: Seconds to wait for the core after the restart.
            restart_poll_interval: Gap between liveness polls.
            restart_min_wait: Floor before the first liveness poll.
        """
        self.host_files = host_files
        self.path = path
        self.restart_timeout = restart_timeout
        self.restart_poll_interval = restart_poll_interval
        self.restart_min_wait = restart_min_wait

    @abc.abstractmethod
    def merge(self, current: Mapping[str, Any]) -> tuple[dict[str, Any], list[Change]]:
        """Return the block this recipe wants, and the changes that get there.

        An empty change list means the current block already satisfies the
        recipe — that is the whole idempotence contract, expressed once.
        """

    @property
    def _transport(self) -> HostFiles:
        if self.host_files is None:
            raise ConfigYamlError(
                f"no SSH write path to {self.path}: set HOMEIQ_HA_SSH_HOST "
                "(see docs/deployment/DEPLOYMENT_RUNBOOK.md)"
            )
        return self.host_files

    def _unconfigured(self) -> CheckResult:
        return CheckResult(
            CheckStatus.NOT_APPLICABLE,
            f"no SSH write path to {self.path}; nothing can be read or changed",
            {"path": self.path, "env": "HOMEIQ_HA_SSH_HOST"},
        )

    async def _read(self) -> tuple[str, dict[str, Any]]:
        """The file's text and the current contents of this recipe's block."""
        text = await self._transport.read_text(self.path)
        block = parse_config(text).get(self.key)
        if block is not None and not isinstance(block, dict):
            raise ConfigYamlError(
                f"{self.path}: top-level {self.key!r} is a "
                f"{type(block).__name__}, not a mapping; refusing to merge"
            )
        return text, dict(block or {})

    async def check(self, _ha: HAClient) -> CheckResult:
        """Compare parsed values. Reads the file; writes nothing, ever."""
        if self.host_files is None:
            return self._unconfigured()
        _, current = await self._read()
        _, changes = self.merge(current)
        if not changes:
            return CheckResult(
                CheckStatus.SATISFIED,
                f"{self.key}: block already matches intent",
                {self.key: current},
            )
        return CheckResult(
            CheckStatus.NEEDS_APPLY,
            f"{self.key}: {len(changes)} value(s) need changing",
            {"drift": [change.describe() for change in changes], "current": current},
        )

    async def plan(self, _ha: HAClient) -> Plan:
        if self.host_files is None:
            return Plan()
        _, current = await self._read()
        _, changes = self.merge(current)
        if not changes:
            return Plan()
        return Plan((*changes, Change("restart", "home assistant core", after="RUNNING")))

    async def apply(self, ha: HAClient) -> ApplyResult:
        text, current = await self._read()
        merged, changes = self.merge(current)
        if not changes:
            return ApplyResult((), f"{self.key}: already converged")

        backup = await self._transport.write_text(self.path, set_top_level(text, self.key, merged))
        try:
            await restart_core(
                ha,
                timeout=self.restart_timeout,
                poll_interval=self.restart_poll_interval,
                min_wait=self.restart_min_wait,
            )
        except Exception:
            # An instance that will not boot cannot be fixed remotely, so put
            # the previous file back before surfacing why the restart failed.
            await self._transport.write_text(self.path, text)
            raise
        changes.append(Change("restart", "home assistant core", after="RUNNING"))
        return ApplyResult(
            tuple(changes),
            f"{self.key}: {len(changes)} change(s) applied, backup at {backup}",
        )

    async def verify(self, ha: HAClient) -> VerifyResult:
        """Re-read the file from the host and confirm the core is back up."""
        if self.host_files is None:
            return VerifyResult(False, f"no SSH write path to {self.path}")
        _, current = await self._read()
        _, drift = self.merge(current)
        state = await ha.rest.request("GET", "/api/config")
        running = (state or {}).get("state") == "RUNNING"
        if drift:
            return VerifyResult(
                False,
                f"{self.key} still drifted: {[c.describe() for c in drift]}",
                {self.key: current},
            )
        if not running:
            return VerifyResult(
                False,
                f"{self.key} written but HA reports state {(state or {}).get('state')!r}",
                {self.key: current},
            )
        return VerifyResult(
            True,
            f"{self.key} matches intent and HA is RUNNING",
            {self.key: current},
        )


#: Failed logins tolerated before the IP is banned.
HTTP_LOGIN_ATTEMPTS_THRESHOLD = 5


class HttpLoginThresholdRecipe(_ConfigYamlRecipe):
    """Give Home Assistant's IP ban the threshold it needs to actually ban.

    ``ip_ban_enabled`` defaults to **true**, but ``login_attempts_threshold``
    defaults to **-1**, which means "never ban" — so a stock instance counts
    failed logins forever and acts on none of them. That is design-doc row 1.1,
    and 5 is its value: high enough that a mistyped password does not lock the
    owner out, low enough that credential stuffing stops immediately.

    This is the LAN-side control, not the remote one. Behind Nabu Casa every
    remote request arrives as ``127.0.0.1``, so IP banning cannot see remote
    clients at all — MFA (row 1.2, a human action) is that control.
    """

    name = "correctness.http_login_threshold"
    key = "http"
    description = "http.login_attempts_threshold set so IP banning is real"

    def merge(self, current: Mapping[str, Any]) -> tuple[dict[str, Any], list[Change]]:
        merged = dict(current)
        if merged.get("login_attempts_threshold") == HTTP_LOGIN_ATTEMPTS_THRESHOLD:
            return merged, []
        change = Change(
            "set",
            "http.login_attempts_threshold",
            merged.get("login_attempts_threshold"),
            HTTP_LOGIN_ATTEMPTS_THRESHOLD,
        )
        merged["login_attempts_threshold"] = HTTP_LOGIN_ATTEMPTS_THRESHOLD
        return merged, [change]


#: Days of state history the recorder keeps. Design-doc row 2.4.
RECORDER_PURGE_KEEP_DAYS = 3

#: Domains excluded from the recorder entirely.
RECORDER_EXCLUDED_DOMAINS = ("update",)

#: Diagnostic sensors excluded from the recorder. Scoped to the ``sensor.``
#: domain so a same-suffixed entity elsewhere is not silently dropped.
RECORDER_EXCLUDED_ENTITY_GLOBS = (
    "sensor.*_rssi",
    "sensor.*_signal_strength",
    "sensor.*_lqi",
    "sensor.*_linkquality",
    "sensor.*_uptime",
)


class RecorderTuningRecipe(_ConfigYamlRecipe):
    """Shrink the recorder to what Home Assistant itself still needs.

    ``purge_keep_days: 3`` is design-doc row 2.4's value, and two specific
    facts make it safe rather than merely small: HomeIQ's InfluxDB already
    owns long-term history, and HA's long-term *statistics* are never purged,
    so the Energy dashboard is unaffected. What shrinks is the history and
    logbook window, which is a UI convenience served better by HomeIQ.

    The exclusions are the entities that dominate the database without anyone
    asking about them. Every ``update.*`` entity writes a state row on each
    core/add-on/HACS version poll, and radio-quality sensors (``_rssi``,
    ``_signal_strength``, ``_lqi``/``_linkquality`` — the same metric named
    differently by ZHA, Z-Wave and Zigbee2MQTT — plus ``_uptime``) change on
    nearly every mesh report.

    SQLite is kept deliberately: no ``db_url`` is ever written, and an
    existing one passes through the merge untouched (the whole block is
    reported in the check's details). Current HA guidance favours SQLite over
    MariaDB at this scale, and a database migration is not something a setup
    agent should do to someone's home.
    """

    name = "correctness.recorder_tuning"
    key = "recorder"
    description = "recorder purge window and diagnostic-entity exclusions"

    def merge(self, current: Mapping[str, Any]) -> tuple[dict[str, Any], list[Change]]:
        merged = dict(current)
        changes: list[Change] = []

        if merged.get("purge_keep_days") != RECORDER_PURGE_KEEP_DAYS:
            changes.append(
                Change(
                    "set",
                    "recorder.purge_keep_days",
                    merged.get("purge_keep_days"),
                    RECORDER_PURGE_KEEP_DAYS,
                )
            )
            merged["purge_keep_days"] = RECORDER_PURGE_KEEP_DAYS

        exclude = dict(merged.get("exclude") or {})
        for field, wanted in (
            ("domains", RECORDER_EXCLUDED_DOMAINS),
            ("entity_globs", RECORDER_EXCLUDED_ENTITY_GLOBS),
        ):
            existing = list(exclude.get(field) or [])
            missing = [value for value in wanted if value not in existing]
            if not missing:
                continue
            # Union, never replacement: a hand-added exclusion is somebody's
            # decision about their own home and outranks this default set.
            changes.append(
                Change("add", f"recorder.exclude.{field}", existing or None, existing + missing)
            )
            exclude[field] = existing + missing

        if exclude:
            merged["exclude"] = exclude
        return merged, changes


__all__ = [
    "HA_CONFIG_PATH",
    "HTTP_LOGIN_ATTEMPTS_THRESHOLD",
    "RECORDER_EXCLUDED_DOMAINS",
    "RECORDER_EXCLUDED_ENTITY_GLOBS",
    "RECORDER_PURGE_KEEP_DAYS",
    "ConfigYamlError",
    "HttpLoginThresholdRecipe",
    "RecorderTuningRecipe",
    "parse_config",
    "render_block",
    "set_top_level",
]
