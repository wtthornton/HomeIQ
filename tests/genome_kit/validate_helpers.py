"""Shared fixtures and fixture-builders for the test_validate_*.py split.

TAP-6023 split ``tests/test_validate.py`` (2069 lines, MI 0.0 against the tapps
gate) into one file per concern, mirroring the earlier ``scripts/validate.py``
split into ``kit_checks.py`` + ``kit_rules.py`` (TAP-5153/5195). This module is
the shared base every split file imports from — not itself a test module.
"""

from __future__ import annotations

import kit_checks
import pytest
import yaml
from kit_rules import QUARANTINE_CAPABILITY

AGENT_BASE = {
    "name": "wstore-probe",
    "description": "a gene",
    "schema_version": "2.1",
    "brain_rationale": "why it reads memory",
}


@pytest.fixture(autouse=True)
def isolated_findings(tmp_path, monkeypatch) -> None:
    """Point err()/warn() at a scratch root and give each test a clean slate."""
    monkeypatch.setattr(kit_checks, "ROOT", tmp_path)
    monkeypatch.setattr(kit_checks, "ERRORS", [])
    monkeypatch.setattr(kit_checks, "WARNINGS", [])


def write_agent(tmp_path, **overrides):
    fm = {**AGENT_BASE, **overrides}
    path = tmp_path / f"{fm['name']}.md"
    path.write_text(f"---\n{yaml.safe_dump(fm)}---\n\nbody\n", encoding="utf-8")
    return path


def write_workflow(tmp_path, nodes: dict, **extra):
    spec = {"name": "wf", "nodes": nodes, "output": next(iter(nodes)), **extra}
    path = tmp_path / "wf.yaml"
    path.write_text(yaml.safe_dump(spec), encoding="utf-8")
    return path


def findings() -> str:
    return "\n".join(kit_checks.ERRORS)


# Shared agent fixtures for workflow-node tests (test_validate_workflow.py and
# test_validate_atlas.py both build multi-agent AGENTS maps against these).
SCANNER = {"capabilities": [QUARANTINE_CAPABILITY], "output_schema": '{"type": "object"}'}
PRODUCER = {"capabilities": ["wstore.produce.digest"], "output_schema": '{"type": "object"}'}
SCHEMALESS: dict = {"capabilities": []}
INGEST = {"capabilities": ["wstore.ingest.ticket"], "output_schema": '{"type": "object"}'}
AGENTS = {"ingest-gene": INGEST, "scan-gene": SCANNER, "digest-gene": PRODUCER}


def scheduled_workflow(tmp_path, inputs: list, **extra):
    nodes = {
        "probe": {
            "agent": "ingest-gene",
            "output_schema": {"type": "object"},
            "inputs": {"hosts": "$hosts"},
        }
    }
    return write_workflow(tmp_path, nodes, inputs=inputs, **extra)
