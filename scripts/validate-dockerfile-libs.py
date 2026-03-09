#!/usr/bin/env python3
"""Validate that Dockerfiles install all shared libs their Python code imports.

Scans each service under domains/ for `from homeiq_*` or `import homeiq_*`,
then checks the service's Dockerfile for the corresponding /tmp/libs/homeiq-*/
install line. Exits non-zero if any mismatch is found.

Usage:
    python scripts/validate-dockerfile-libs.py          # warn mode (default)
    python scripts/validate-dockerfile-libs.py --strict  # exit 1 on mismatch
"""

import argparse
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Map import names (underscores) to lib directory names (hyphens)
# e.g. homeiq_memory -> homeiq-memory
IMPORT_PATTERN = re.compile(r"(?:from|import)\s+(homeiq_\w+)")
DOCKERFILE_LIB_PATTERN = re.compile(r"/tmp/libs/(homeiq-[\w-]+)/")


def discover_shared_libs() -> set[str]:
    """Return set of available shared lib directory names (e.g. 'homeiq-memory')."""
    libs_dir = PROJECT_ROOT / "libs"
    if not libs_dir.exists():
        return set()
    return {
        d.name
        for d in libs_dir.iterdir()
        if d.is_dir() and d.name.startswith("homeiq-") and (d / "pyproject.toml").exists()
    }


def import_name_to_lib_name(import_name: str) -> str:
    """Convert Python import name to lib directory name: homeiq_memory -> homeiq-memory."""
    return import_name.replace("_", "-")


def scan_service_imports(service_dir: Path) -> set[str]:
    """Scan all .py files in a service for homeiq_* imports. Returns lib dir names."""
    imports = set()
    src_dirs = [service_dir / "src", service_dir]
    for src_dir in src_dirs:
        if not src_dir.exists():
            continue
        for py_file in src_dir.rglob("*.py"):
            # Skip test files — they don't run in Docker
            rel = str(py_file.relative_to(service_dir))
            if rel.startswith("tests"):
                continue
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for match in IMPORT_PATTERN.finditer(content):
                lib_name = import_name_to_lib_name(match.group(1))
                imports.add(lib_name)
    return imports


def scan_dockerfile_libs(dockerfile: Path) -> set[str]:
    """Parse a Dockerfile for /tmp/libs/homeiq-*/ install references."""
    if not dockerfile.exists():
        return set()
    content = dockerfile.read_text(encoding="utf-8", errors="ignore")
    return set(DOCKERFILE_LIB_PATTERN.findall(content))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict", action="store_true", help="Exit non-zero on any mismatch"
    )
    args = parser.parse_args()

    available_libs = discover_shared_libs()
    if not available_libs:
        print("No shared libs found in libs/. Nothing to validate.")
        return 0

    domains_dir = PROJECT_ROOT / "domains"
    if not domains_dir.exists():
        print("No domains/ directory found.")
        return 0

    issues: list[str] = []
    checked = 0

    for group_dir in sorted(domains_dir.iterdir()):
        if not group_dir.is_dir():
            continue
        for service_dir in sorted(group_dir.iterdir()):
            if not service_dir.is_dir():
                continue
            dockerfile = service_dir / "Dockerfile"
            if not dockerfile.exists():
                continue

            checked += 1
            needed_libs = scan_service_imports(service_dir) & available_libs
            installed_libs = scan_dockerfile_libs(dockerfile)

            missing = needed_libs - installed_libs
            if missing:
                rel_path = service_dir.relative_to(PROJECT_ROOT)
                for lib in sorted(missing):
                    issues.append(
                        f"  {rel_path}/Dockerfile: missing /tmp/libs/{lib}/ "
                        f"(imported in Python source)"
                    )

    print(f"Checked {checked} services against {len(available_libs)} shared libs.")

    if issues:
        print(f"\n{'ERROR' if args.strict else 'WARNING'}: "
              f"{len(issues)} missing Dockerfile lib install(s):\n")
        for issue in issues:
            print(issue)
        print(
            "\nFix: Add the missing lib to the 'pip install' shared libs step "
            "in each Dockerfile."
        )
        return 1 if args.strict else 0

    print("All Dockerfiles have the shared libs their code imports.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
