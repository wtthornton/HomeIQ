#!/usr/bin/env python3
"""Validate that local shared libs are installed before pip resolves requirements.txt.

A Dockerfile that runs `pip install -r requirements.txt` before installing a
local-only package from `libs/` (via `/tmp/libs/<pkg>/`) will fail the moment
that requirements file names that package as a version-pinned dependency: pip
has no PyPI distribution for it and the build breaks (TAP-7383). This scans
every service Dockerfile under domains/ and flags that ordering.

Usage:
    python scripts/validate-dockerfile-lib-order.py          # warn mode (default)
    python scripts/validate-dockerfile-lib-order.py --strict  # exit 1 on violation
"""

import argparse
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# COPY <path>/requirements[-suffix].txt <dest> — captures the source path.
REQUIREMENTS_COPY_RE = re.compile(r"^\s*COPY\s+(\S*requirements[\w.-]*\.txt)\s")
# RUN ... pip install ... -r <basename>  (the step that makes pip resolve it)
REQUIREMENTS_INSTALL_RE = re.compile(r"pip install.*-r\s+\S*requirements[\w.-]*\.txt")
# A local lib install line: pip install .../tmp/libs/<pkg>/...
LOCAL_LIB_INSTALL_RE = re.compile(r"/tmp/libs/(homeiq-[\w-]+)/")
# A hard dependency line inside a requirements file: "homeiq-xxx>=1.0.0" etc.,
# not a comment and not just mentioned inside another comment/extra.
REQUIREMENT_LINE_RE = re.compile(r"^\s*(homeiq-[\w-]+)\s*([<>=!~].*)?$")


def discover_shared_libs() -> set[str]:
    """Return the set of local-only package names available under libs/."""
    libs_dir = PROJECT_ROOT / "libs"
    if not libs_dir.exists():
        return set()
    return {
        d.name
        for d in libs_dir.iterdir()
        if d.is_dir() and d.name.startswith("homeiq-") and (d / "pyproject.toml").exists()
    }


def requirements_names_local_pkgs(req_path: Path, local_libs: set[str]) -> set[str]:
    """Return which local-only packages a requirements file pins as dependencies."""
    if not req_path.exists():
        return set()
    named = set()
    for line in req_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = REQUIREMENT_LINE_RE.match(stripped)
        if match and match.group(1) in local_libs:
            named.add(match.group(1))
    return named


def find_line(lines: list[str], pattern: re.Pattern, start: int = 0) -> int | None:
    """1-indexed line number of the first match at or after `start` (0-indexed)."""
    for i in range(start, len(lines)):
        if pattern.search(lines[i]):
            return i + 1
    return None


def check_dockerfile(dockerfile: Path, local_libs: set[str]) -> list[str]:
    """Return a list of violation messages for one Dockerfile, empty if clean."""
    lines = dockerfile.read_text(encoding="utf-8", errors="ignore").splitlines()
    rel = dockerfile.relative_to(PROJECT_ROOT)
    violations: list[str] = []

    for i, line in enumerate(lines):
        copy_match = REQUIREMENTS_COPY_RE.match(line)
        if not copy_match:
            continue
        req_rel_path = copy_match.group(1)
        req_path = PROJECT_ROOT / req_rel_path
        needed = requirements_names_local_pkgs(req_path, local_libs)
        if not needed:
            continue

        req_install_line = find_line(lines, REQUIREMENTS_INSTALL_RE, i)
        if req_install_line is None:
            continue

        for pkg in sorted(needed):
            pkg_install_line = None
            for j, other in enumerate(lines):
                if LOCAL_LIB_INSTALL_RE.search(other) and pkg in other:
                    pkg_install_line = j + 1
                    break
            if pkg_install_line is None:
                violations.append(
                    f"  {rel}: names '{pkg}' in {req_rel_path} but never installs "
                    f"it from /tmp/libs/{pkg}/"
                )
            elif pkg_install_line > req_install_line:
                violations.append(
                    f"  {rel}:{req_install_line}: 'pip install -r {req_rel_path}' "
                    f"names local-only package '{pkg}', but that package is not "
                    f"installed until line {pkg_install_line} (/tmp/libs/{pkg}/). "
                    f"pip cannot resolve it from PyPI — reorder so the local "
                    f"install precedes the requirements install."
                )

    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true", help="Exit non-zero on any violation")
    parser.add_argument(
        "--service",
        help="Only check the Dockerfile whose path contains this substring "
        "(e.g. 'model-server'). Useful for guard self-checks.",
    )
    args = parser.parse_args()

    local_libs = discover_shared_libs()
    if not local_libs:
        print("No shared libs found in libs/. Nothing to validate.")
        return 0

    domains_dir = PROJECT_ROOT / "domains"
    if not domains_dir.exists():
        print("No domains/ directory found.")
        return 0

    dockerfiles = sorted(domains_dir.rglob("Dockerfile"))
    if args.service:
        dockerfiles = [d for d in dockerfiles if args.service in str(d)]

    all_violations: list[str] = []
    for dockerfile in dockerfiles:
        all_violations.extend(check_dockerfile(dockerfile, local_libs))

    print(f"Checked {len(dockerfiles)} Dockerfile(s) against {len(local_libs)} shared libs.")

    if all_violations:
        label = "ERROR" if args.strict else "WARNING"
        print(f"\n{label}: {len(all_violations)} local-lib install-order violation(s):\n")
        for v in all_violations:
            print(v)
        return 1 if args.strict else 0

    print("All checked Dockerfiles install local-only packages before requirements.txt.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
