#!/usr/bin/env python3
"""Fail when a lib imports a distribution its pyproject does not declare (TAP-6066).

For each libs/homeiq-*/ package: AST-parse every module under src/, take the
top-level (unguarded, module-level) third-party imports, map module names to
distribution names, and require each to appear in [project.dependencies] or
any optional-dependencies group. Guarded imports (inside try/except or a
function) are exempt by construction — only module-level, unconditional
imports can break a clean-venv install at import time.

Run: python3 scripts/check_lib_deps.py   (exit 1 on findings)
"""

from __future__ import annotations

import ast
import sys
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LIBS = sorted((REPO / "libs").glob("homeiq-*"))

#: import name -> distribution name where they differ
DIST_FOR_MODULE = {
    "yaml": "pyyaml",
    "jose": "python-jose",
    "dateutil": "python-dateutil",
    "influxdb_client": "influxdb-client",
    "pydantic_settings": "pydantic-settings",
    "prometheus_client": "prometheus-client",
    "opentelemetry": "opentelemetry-api",
    "zhaquirks": "zha-quirks",
}

#: modules that are intentionally NOT declared, with the reason enforced in review
ALLOWED_UNDECLARED = {
    # vendored quirk data deployed verbatim to the HA host; agent/quirks/ has
    # no __init__.py and is outside the package import graph
    "homeiq-ha": {"zhaquirks", "zigpy"},
}

STDLIB = sys.stdlib_module_names


def module_level_imports(tree: ast.Module) -> set[str]:
    """Top-level import roots — guarded (try/except, function, TYPE_CHECKING) exempt."""
    roots: set[str] = set()
    for node in tree.body:  # module level only, deliberately not ast.walk
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


def declared_distributions(pyproject: Path) -> set[str]:
    data = tomllib.loads(pyproject.read_text())
    project = data.get("project", {})
    deps = list(project.get("dependencies", []))
    for group in project.get("optional-dependencies", {}).values():
        deps.extend(group)
    names = set()
    for dep in deps:
        name = dep.split(";")[0].strip()
        for sep in ("[", ">", "<", "=", "!", "~", " "):
            name = name.split(sep)[0]
        names.add(name.lower())
    return names


def main() -> int:
    findings: list[str] = []
    for lib in LIBS:
        src = lib / "src"
        pyproject = lib / "pyproject.toml"
        if not src.is_dir() or not pyproject.is_file():
            continue
        declared = declared_distributions(pyproject)
        allowed = ALLOWED_UNDECLARED.get(lib.name, set())
        # Bare sibling imports ("from constants import ...") resolve to files
        # inside this lib's own src tree via a sys.path hack — a code smell,
        # but not a missing pip distribution, which is all this check judges.
        in_tree = {p.stem for p in src.rglob("*.py")} | {
            p.name for p in src.rglob("*") if p.is_dir()
        }
        imports: set[str] = set()
        for py in src.rglob("*.py"):
            try:
                imports |= module_level_imports(ast.parse(py.read_text()))
            except SyntaxError as exc:
                findings.append(f"{lib.name}: {py} does not parse: {exc}")
        for root in sorted(imports):
            if root in STDLIB or root.startswith("homeiq_") or root in ("src", "tests"):
                continue
            if root in allowed or root in in_tree:
                continue
            dist = DIST_FOR_MODULE.get(root, root).lower()
            if dist not in declared and root.replace("_", "-") not in declared:
                findings.append(
                    f"{lib.name}: imports '{root}' (distribution '{dist}') "
                    f"but {pyproject.relative_to(REPO)} does not declare it"
                )
    if findings:
        print("Undeclared lib imports (TAP-6066):")
        for finding in findings:
            print(f"  {finding}")
        return 1
    print(f"check_lib_deps: {len(LIBS)} libs clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
