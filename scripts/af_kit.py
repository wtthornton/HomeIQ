#!/usr/bin/env python3
"""Locate the AgentForge integration kit and publish through its CLI.

TAP-5436. Three documents named ``af_publish.py`` as this project's publish lane
while nothing here could resolve it: the kit is installed as symlinks (the
``af-*`` skills under ``.claude/skills/`` and the plugin under
``~/.claude/plugins/local/``), but ``AF_KIT_ROOT`` was never set and the
skill's relative fallback ``clients/agentforge-integration-kit`` does not exist
in a consumer repo. The script was always on disk; only the resolution rule was
missing. This module is that rule, in one place.

It deliberately does **not** reimplement the publish order. ``PUT`` then
activate-on-201, agents before workflows, and the refusal to publish a workflow
referencing an unpublished agent are the platform's contract, and a second copy
of them here would be free to drift from the kit's. Callers get a subprocess
invocation of the real CLI instead.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

# The kit ships no installable package, so it is located by path and its scripts
# directory imported directly. This marker file is the cheapest proof that a
# candidate directory really is the kit rather than a same-named empty folder.
KIT_MARKER = "scripts/af_publish_discover.py"
KIT_ENV_VARS = ("AF_KIT_ROOT", "AGENTFORGE_KIT_ROOT")
# install_kit.sh --plugin-symlink writes this, so it is present on any machine
# where the kit was installed the documented way — including ones where nobody
# remembered to export AF_KIT_ROOT.
PLUGIN_SYMLINK = Path.home() / ".claude/plugins/local/agentforge-integration-kit"
# Third-party imports the kit CLI needs. This repo's own scripts are stdlib-only,
# so they are not guaranteed present in the running interpreter.
KIT_REQUIREMENTS = ("httpx", "yaml")
UV_EXTRAS = ("--with", "httpx", "--with", "pyyaml")


class KitUnavailableError(RuntimeError):
    """The integration kit could not be located."""


def kit_candidates(explicit: str | Path | None = None) -> list[Path]:
    """Return every place the kit is looked for, in priority order."""
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    candidates.extend(Path(os.environ[var]) for var in KIT_ENV_VARS if os.environ.get(var))
    candidates.append(PLUGIN_SYMLINK)
    return candidates


def resolve_kit_root(explicit: str | Path | None = None) -> Path:
    """Return the integration-kit root, or raise naming everywhere that was tried.

    Priority: an explicit path, then ``AF_KIT_ROOT`` / ``AGENTFORGE_KIT_ROOT``,
    then the plugin symlink. The error lists the candidates because "kit not
    found" without them sends the reader hunting for a path this function
    already knows it rejected.
    """
    candidates = kit_candidates(explicit)
    for candidate in candidates:
        if (candidate / KIT_MARKER).is_file():
            return candidate.resolve()

    looked = ", ".join(str(c) for c in candidates) or "<no candidates>"
    msg = (
        f"AgentForge integration kit not found (no {KIT_MARKER}). Looked in: {looked}. "
        "Set AF_KIT_ROOT, or install the kit with its scripts/install_kit.sh."
    )
    raise KitUnavailableError(msg)


def _missing_requirements() -> list[str]:
    """Return the kit's third-party imports absent from this interpreter."""
    return [mod for mod in KIT_REQUIREMENTS if importlib.util.find_spec(mod) is None]


def load_api_key(repo_root: Path | None = None) -> str:
    """The project bearer, from the environment or this repo's `.env`.

    `.mcp.json` sets `AGENTFORGE_LOAD_DOTENV=1`, so the MCP server reads the key
    out of `.env` and every agent-driven call authenticates. The scripts in this
    directory read `os.environ` only, so the same key on the same disk gave them
    a 401 unless the caller remembered `set -a && . ./.env && set +a` first —
    a 401 that reads as "the token is bad" when the token is fine. Honouring the
    same convention the MCP entry already declares removes the trap rather than
    documenting it.

    The environment still wins: an explicitly exported key is a deliberate
    override, and a dotenv that silently beat it would be its own surprise.
    """
    if key := os.environ.get("AGENTFORGE_API_KEY", ""):
        return key
    env_file = (repo_root or Path(__file__).resolve().parent.parent) / ".env"
    if not env_file.is_file():
        return ""
    for line in env_file.read_text(encoding="utf-8").splitlines():
        name, sep, value = line.partition("=")
        if sep and name.strip() == "AGENTFORGE_API_KEY":
            return value.strip().strip('"').strip("'")
    return ""


def kit_command(script: Path) -> list[str]:
    """Return the argv prefix that can actually run a kit script.

    The kit needs ``httpx`` and ``pyyaml``. When the running interpreter already
    has them, it is used directly; otherwise the call goes through ``uv run
    --with``, which is how the rest of this repo obtains dependencies. Choosing
    up front rather than retrying on ImportError keeps the failure mode
    "uv is missing" instead of a confusing second traceback.
    """
    if not _missing_requirements():
        return [sys.executable, str(script)]
    return ["uv", "run", *UV_EXTRAS, "python", str(script)]


def publish(
    slug: str,
    repo_root: Path,
    *,
    api_key: str = "",
    layout: str = "scout",
    dry_run: bool = False,
    kit_root: str | Path | None = None,
    timeout: int = 900,
) -> subprocess.CompletedProcess[str]:
    """Publish a consumer repo through the kit CLI and return the completed run.

    Raises ``KitUnavailableError`` when the kit cannot be resolved. Every other
    failure is left in the returned ``CompletedProcess`` so callers can report
    the CLI's own message rather than a paraphrase of it.
    """
    script = resolve_kit_root(kit_root) / "scripts/af_publish.py"
    cmd = [
        *kit_command(script),
        "--slug",
        slug,
        "--layout",
        layout,
        "--repo-root",
        str(repo_root),
    ]
    if dry_run:
        cmd.append("--dry-run")

    env = dict(os.environ)
    if api_key:
        env["AGENTFORGE_API_KEY"] = api_key
    return subprocess.run(
        cmd, cwd=str(repo_root), capture_output=True, text=True, timeout=timeout, env=env, check=False
    )


def main(argv: list[str] | None = None) -> int:
    """Print the resolved kit root — the answer to 'where is af_publish.py'."""
    argv = sys.argv[1:] if argv is None else argv
    try:
        root = resolve_kit_root(argv[0] if argv else None)
    except KitUnavailableError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(root)
    return 0


if __name__ == "__main__":
    sys.exit(main())
