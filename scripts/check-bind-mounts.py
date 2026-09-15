#!/usr/bin/env python3
"""TAP-7646: fail while any running container bind-mounts into the primary checkout.

`/home/wtthornton/code/HomeIQ` is a live deploy root: running production
containers bind-mount paths inside it, so switching that checkout's branch (or
deleting a mounted path from it) silently changes what a running container
reads. This script is the instrument that proves the hazard is gone once
mounts move to a dedicated deploy root — it does not move anything itself.

Two failure modes must both be loud:
  - a real bind mount resolves inside the repo -> exit VIOLATIONS_FOUND.
  - the probe inspected nothing (no containers, or no bind sources) -> exit
    INSPECTION_FAILED. `docker inspect` returns a JSON array; a probe written
    over an object's top-level keys reads zero mounts and would otherwise
    exit 0 having checked nothing.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

EXIT_OK = 0
EXIT_VIOLATIONS_FOUND = 1
EXIT_INSPECTION_FAILED = 2

# Seam: point at a pre-baked `docker inspect`-shaped JSON array instead of
# shelling out to the real daemon. Unset in normal use.
DOCKER_JSON_ENV = "BIND_MOUNT_CHECK_DOCKER_JSON"


def resolve_repo_root(arg: str | None) -> Path:
    """The tree to guard against: an explicit argument, or `git rev-parse --show-toplevel`."""
    if arg:
        return Path(arg).resolve()
    proc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"could not resolve repo root via git: {proc.stderr.strip()}")
    return Path(proc.stdout.strip()).resolve()


def list_running_container_ids() -> list[str]:
    proc = subprocess.run(["docker", "ps", "-q"], capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"docker ps failed: {proc.stderr.strip()}")
    return [line for line in proc.stdout.splitlines() if line.strip()]


def inspect_containers(ids: list[str]) -> list[dict[str, Any]]:
    if not ids:
        return []
    proc = subprocess.run(["docker", "inspect", *ids], capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"docker inspect failed: {proc.stderr.strip()}")
    data = json.loads(proc.stdout)
    if not isinstance(data, list):
        raise RuntimeError("docker inspect did not return a JSON array")
    return data


def load_containers() -> list[dict[str, Any]]:
    """Every running container's inspect record, real or (for tests) synthetic."""
    override = os.environ.get(DOCKER_JSON_ENV)
    if override:
        data = json.loads(Path(override).read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise RuntimeError(
                f"{DOCKER_JSON_ENV} must contain a JSON array, got {type(data).__name__}"
            )
        return data
    return inspect_containers(list_running_container_ids())


def bind_sources(container: dict[str, Any]) -> list[str]:
    """Bind-mount `Source` paths for one `docker inspect` record. Refuses malformed shapes."""
    if not isinstance(container, dict):
        raise RuntimeError(f"container record is not an object: {container!r}")
    mounts = container.get("Mounts", [])
    if not isinstance(mounts, list):
        raise RuntimeError(f"container 'Mounts' is not an array: {mounts!r}")
    sources = []
    for mount in mounts:
        if not isinstance(mount, dict):
            raise RuntimeError(f"mount entry is not an object: {mount!r}")
        if mount.get("Type") != "bind":
            continue
        source = mount.get("Source")
        if source:
            sources.append(source)
    return sources


def is_inside(path: Path, root: Path) -> bool:
    """True path is `root` itself or somewhere under it, on a path-segment boundary."""
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def check(repo_root: Path) -> int:
    try:
        containers = load_containers()
    except (RuntimeError, OSError, json.JSONDecodeError) as exc:
        print(f"INSPECTION FAILED: {exc}", file=sys.stderr)
        return EXIT_INSPECTION_FAILED

    containers_inspected = len(containers)
    sources_examined = 0
    violations: list[tuple[str, str]] = []

    try:
        for container in containers:
            name = str(container.get("Name") or container.get("Id") or "?").lstrip("/")
            for raw_source in bind_sources(container):
                sources_examined += 1
                resolved = Path(raw_source).resolve()
                if is_inside(resolved, repo_root):
                    violations.append((name, str(resolved)))
    except RuntimeError as exc:
        print(f"INSPECTION FAILED: {exc}", file=sys.stderr)
        return EXIT_INSPECTION_FAILED

    print(
        f"inspected {containers_inspected} container(s), examined {sources_examined} "
        f"bind source(s) against {repo_root}"
    )

    if containers_inspected == 0 or sources_examined == 0:
        print(
            "INSPECTION FAILED: inspected nothing "
            f"(containers={containers_inspected}, bind sources={sources_examined}); "
            "refusing to report OK on an empty probe.",
            file=sys.stderr,
        )
        return EXIT_INSPECTION_FAILED

    if violations:
        print(f"FAIL: {len(violations)} bind mount(s) resolve inside {repo_root}:", file=sys.stderr)
        for name, source in violations:
            print(f"    {name}: {source}", file=sys.stderr)
        return EXIT_VIOLATIONS_FOUND

    print(f"OK: no running container binds into {repo_root}.")
    return EXIT_OK


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "repo_root",
        nargs="?",
        default=None,
        help="tree to guard (default: `git rev-parse --show-toplevel`)",
    )
    args = parser.parse_args()

    try:
        repo_root = resolve_repo_root(args.repo_root)
    except RuntimeError as exc:
        print(f"INSPECTION FAILED: {exc}", file=sys.stderr)
        return EXIT_INSPECTION_FAILED

    return check(repo_root)


if __name__ == "__main__":
    sys.exit(main())
