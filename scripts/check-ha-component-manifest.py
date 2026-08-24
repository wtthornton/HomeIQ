#!/usr/bin/env python3
"""Enforce infrastructure/ha-components.lock.json against the HA image (TAP-6483).

Vendored components do not self-update, so the lock file is the only record of
what the appliance actually ships. This check makes a disagreement between that
record and reality a build failure rather than a silent drift.

Two modes, because CI needs a cheap always-on check and a deep one when an image
exists:

* **static** (default) -- the lock file agrees with the Dockerfile: same HA pin,
  same component versions in the matching ``ARG`` defaults, and the pin is never
  a moving tag. Needs no Docker.
* **image** (``--image TAG``) -- additionally inspects the built image: each
  component's ``manifest.json`` carries the locked version, the ZHA quirk is
  present at its installed path, and no structural HACS artifact shipped.

Exit 0 when everything agrees, 1 on any disagreement, 2 on a usage/IO error.

    python scripts/check-ha-component-manifest.py
    python scripts/check-ha-component-manifest.py --image homeiq/home-assistant:2026.8.3
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LOCK_PATH = REPO_ROOT / "infrastructure" / "ha-components.lock.json"
DOCKERFILE_PATH = REPO_ROOT / "domains" / "core-platform" / "home-assistant" / "Dockerfile"

# Tags that move under you. An appliance following one will eventually boot into
# a breaking release with nobody present to notice.
MOVING_TAGS = frozenset({"stable", "latest", "beta", "dev", "rc"})


def _fail(failures: list[str], message: str) -> None:
    failures.append(message)


def _check_ha_pin(ha: dict, dockerfile: str, failures: list[str]) -> None:
    """The HA pin is a real release, matches the Dockerfile, and clears the floor."""
    want = ha["version"]
    if want in MOVING_TAGS:
        _fail(failures, f"HA version {want!r} is a moving tag; pin a release")

    from_match = re.search(
        r"^FROM\s+ghcr\.io/home-assistant/home-assistant:(\S+)", dockerfile, re.MULTILINE
    )
    if not from_match:
        _fail(failures, "no `FROM ghcr.io/home-assistant/home-assistant:<version>` in Dockerfile")
    elif from_match.group(1) in MOVING_TAGS:
        _fail(failures, f"Dockerfile pins the moving tag {from_match.group(1)!r}; use a release")
    elif from_match.group(1) != want:
        _fail(failures, f"HA pin: lock says {want}, Dockerfile says {from_match.group(1)}")

    floor = ha.get("version_floor")
    if floor and _version_key(want) < _version_key(floor):
        _fail(failures, f"HA pin {want} is below the declared floor {floor}")


def _check_component(component: dict, dockerfile: str, failures: list[str]) -> None:
    """One component agrees with its Dockerfile ARG (vendored) or manifest (in-repo)."""
    name = component["name"]
    arg = component.get("dockerfile_arg")
    if arg:
        arg_match = re.search(rf"^ARG\s+{re.escape(arg)}=v?(\S+)", dockerfile, re.MULTILINE)
        if not arg_match:
            _fail(failures, f"{name}: no `ARG {arg}=` default in Dockerfile")
        elif arg_match.group(1) != component["version"]:
            _fail(
                failures,
                f"{name}: lock says {component['version']}, "
                f"Dockerfile ARG {arg} says {arg_match.group(1)}",
            )

    source = component.get("source", "")
    if not source.startswith("in-repo:"):
        return
    manifest_path = REPO_ROOT / source[len("in-repo:") :] / "manifest.json"
    if not manifest_path.is_file():
        _fail(failures, f"{name}: {manifest_path} does not exist")
        return
    got = json.loads(manifest_path.read_text(encoding="utf-8")).get("version")
    if got != component["version"]:
        _fail(
            failures,
            f"{name}: lock says {component['version']}, "
            f"{manifest_path.relative_to(REPO_ROOT)} says {got}",
        )


def check_static(lock: dict, dockerfile: str, failures: list[str]) -> None:
    """The lock file and the Dockerfile tell the same story."""
    _check_ha_pin(lock["home_assistant"], dockerfile, failures)

    for component in lock["custom_components"]:
        _check_component(component, dockerfile, failures)

    for quirk in lock.get("zha_quirks", []):
        source = quirk.get("source", "")
        if source.startswith("in-repo:"):
            path = REPO_ROOT / source[len("in-repo:") :]
            if not path.is_file():
                _fail(failures, f"quirk {quirk['name']}: {path} does not exist")


def _version_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", version))


def _docker_run(image: str, *command: str) -> tuple[int, str]:
    """Run one command in the image. Resolves docker to an absolute path so the
    argv carries no PATH ambiguity, and never goes through a shell."""
    docker = shutil.which("docker")
    if docker is None:
        raise FileNotFoundError("docker is not on PATH; --image needs a Docker daemon")
    result = subprocess.run(
        [docker, "run", "--rm", "--entrypoint", *command[:1], image, *command[1:]],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    return result.returncode, result.stdout


def check_image(lock: dict, image: str, failures: list[str]) -> None:
    """The built image really carries what the lock file claims."""
    for component in lock["custom_components"]:
        name = component["name"]
        code, out = _docker_run(image, "cat", f"/config/custom_components/{name}/manifest.json")
        if code != 0:
            _fail(failures, f"{name}: /config/custom_components/{name}/manifest.json not in image")
            continue
        got = json.loads(out).get("version")
        if got != component["version"]:
            _fail(failures, f"{name}: lock says {component['version']}, image ships {got}")

    for quirk in lock.get("zha_quirks", []):
        path = quirk["installed_to"]
        code, _ = _docker_run(image, "test", "-f", path)
        if code != 0:
            _fail(failures, f"quirk {quirk['name']}: {path} not in image")

    # An unlocked component smuggled into the image would otherwise pass, because
    # the loop above only asserts that everything *locked* is present.
    code, out = _docker_run(image, "ls", "-1", "/config/custom_components/")
    if code != 0:
        _fail(failures, "/config/custom_components/ is not readable in the image")
    else:
        found = {line.strip() for line in out.splitlines() if line.strip()}
        locked = {component["name"] for component in lock["custom_components"]}
        for extra in sorted(found - locked):
            _fail(failures, f"unlocked component {extra!r} is in the image but not the lock file")

    # Structural checks only. A substring grep for "hacs" matches the Hungarian
    # word "hacsak" in a Powercalc translation and would fail a correct image.
    # Several paths, because HACS installs itself in more than one place and
    # checking only custom_components/ would miss a partial install.
    for forbidden in lock.get("must_not_contain", []):
        for path in (
            f"/config/custom_components/{forbidden}",
            f"/config/{forbidden}",
            f"/config/{forbidden}.json",
            f"/config/.storage/{forbidden}",
            f"/config/.storage/{forbidden}.repositories",
        ):
            code, _ = _docker_run(image, "test", "-e", path)
            if code == 0:
                _fail(failures, f"forbidden artifact {forbidden!r} present in the image at {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", help="also verify this built image tag")
    args = parser.parse_args()

    try:
        lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        dockerfile = DOCKERFILE_PATH.read_text(encoding="utf-8")
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    failures: list[str] = []
    check_static(lock, dockerfile, failures)
    if args.image:
        check_image(lock, args.image, failures)

    if failures:
        print("FAIL: HA component manifest disagrees with reality")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    scope = f"static + image {args.image}" if args.image else "static"
    counts = (
        f"{len(lock['custom_components'])} components, {len(lock.get('zha_quirks', []))} quirks"
    )
    print(f"OK: HA {lock['home_assistant']['version']} pinned, {counts} ({scope})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
