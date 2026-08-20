#!/usr/bin/env python3
"""Fail when a service directory is missing from its group CI matrix (TAP-6202).

A service under domains/<domain>/<service>/ that ships a requirements.txt or
pyproject.toml is Python code CI must gate. Each group workflow (ci-*.yml)
calls reusable-group-ci.yml with a domain_dir and a JSON services matrix; a
service absent from that matrix is invisible rather than green, so lint, test,
and migration debt accrues silently (zeek-network-service's migrations had
never run anywhere when this was written).

Run: python3 scripts/check_ci_matrix.py   (exit 1 on findings)
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WORKFLOWS = REPO / ".github" / "workflows"
DOMAINS = REPO / "domains"

#: services intentionally outside group CI, with the reason enforced in review
EXCLUDED_SERVICES: dict[str, str] = {}

PKG_MARKERS = ("requirements.txt", "pyproject.toml")


def matrices_by_domain() -> dict[str, tuple[str, set[str]]]:
    """domain_dir -> (workflow filename, services in its matrix)."""
    found: dict[str, tuple[str, set[str]]] = {}
    for wf in sorted(WORKFLOWS.glob("ci-*.yml")):
        text = wf.read_text()
        if "reusable-group-ci.yml" not in text:
            continue
        domain = re.search(r"domain_dir:\s*(\S+)", text)
        services = re.search(r"services:\s*'(\[.*?\])'", text, re.DOTALL)
        if not domain or not services:
            raise SystemExit(
                f"{wf.name}: calls reusable-group-ci.yml but domain_dir/services "
                f"inputs are not in the expected shape — update this check"
            )
        found[domain.group(1)] = (wf.name, set(json.loads(services.group(1))))
    return found


def main() -> int:
    matrices = matrices_by_domain()
    findings: list[str] = []
    for marker_file in sorted(DOMAINS.glob("*/*/")):
        domain, service = marker_file.parent.name, marker_file.name
        if not any((marker_file / m).is_file() for m in PKG_MARKERS):
            continue
        if service in EXCLUDED_SERVICES:
            continue
        if domain not in matrices:
            findings.append(
                f"domains/{domain}/{service}: no ci-*.yml workflow covers domain '{domain}' at all"
            )
        elif service not in matrices[domain][1]:
            findings.append(
                f"domains/{domain}/{service}: not in the services matrix of {matrices[domain][0]}"
            )
    if findings:
        print("Services outside group CI (TAP-6202):")
        for finding in findings:
            print(f"  {finding}")
        print(
            "\nAdd the service to its group workflow's services matrix, or "
            "record an exclusion with a reason in EXCLUDED_SERVICES."
        )
        return 1
    covered = sum(len(s) for _, s in matrices.values())
    print(f"check_ci_matrix: {covered} matrix entries cover every packaged service")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
