"""TAP-5297 contract tests: the running server's tool surface is pinned to the catalogue.

Renaming, removing or retyping a tool changes `docs/mcp/homeiq-mcp-tools.schema.json`
(the normative contract) — these tests fail loudly, naming any AgentForge gene that
depends on the changed tool via `docs/mcp/gene-tool-dependencies.json`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from src.backends import build_backings
from src.catalogue import load_catalogue
from src.registry import ToolRegistry
from src.tools import register_all

REPO = Path(__file__).resolve().parents[4]
CATALOGUE_JSON = REPO / "docs" / "mcp" / "homeiq-mcp-tools.schema.json"
GENE_MAP_JSON = REPO / "docs" / "mcp" / "gene-tool-dependencies.json"
CATALOGUE_MD = REPO / "docs" / "mcp" / "homeiq-mcp-tool-catalogue.md"


@pytest.fixture(scope="module")
def served():
    catalogue = load_catalogue(CATALOGUE_JSON)
    registry = ToolRegistry(catalogue)
    from src.config import Settings

    register_all(
        registry,
        build_backings(Settings(read_tokens="r", data_api_url="http://x", data_api_key="k")),
    )
    return catalogue, {
        t.name: t.model_dump(by_alias=True, exclude_none=True) for t in registry.list_tools()
    }


@pytest.fixture(scope="module")
def raw_catalogue():
    return json.loads(CATALOGUE_JSON.read_text())


@pytest.fixture(scope="module")
def gene_map():
    return json.loads(GENE_MAP_JSON.read_text())


def _genes_for(gene_map, tool):
    return sorted(g for g, tools in gene_map["genes"].items() if tool in tools)


ACTIVE = [
    t["name"]
    for t in json.loads(CATALOGUE_JSON.read_text())["tools"]
    if t.get("status") != "deferred"
]
DEFERRED = [
    t["name"]
    for t in json.loads(CATALOGUE_JSON.read_text())["tools"]
    if t.get("status") == "deferred"
]


def test_versions_agree(raw_catalogue, gene_map):
    assert raw_catalogue["catalogue_version"] == gene_map["catalogue_version"]
    assert (
        f"**catalogue_version:** {raw_catalogue['catalogue_version']}" in CATALOGUE_MD.read_text()
    )


def test_every_active_tool_is_served_and_nothing_else(served, raw_catalogue, gene_map):
    _, tools = served
    missing = sorted(set(ACTIVE) - set(tools))
    extra = sorted(set(tools) - set(ACTIVE))
    assert not missing, (
        f"catalogue tools not served: {missing} (genes: {[_genes_for(gene_map, m) for m in missing]})"
    )
    assert not extra, f"served tools not in catalogue: {extra}"
    assert not set(DEFERRED) & set(tools), "deferred tools must not be served"


@pytest.mark.parametrize("name", ACTIVE)
def test_tool_schemas_are_served_verbatim(served, raw_catalogue, gene_map, name):
    _, tools = served
    spec = next(t for t in raw_catalogue["tools"] if t["name"] == name)
    served_tool = tools[name]
    who = _genes_for(gene_map, name)
    assert served_tool["inputSchema"] == spec["input_schema"], (
        f"{name} input schema drifted; affected genes: {who}"
    )
    assert served_tool["outputSchema"] == spec["output_schema"], (
        f"{name} output schema drifted; affected genes: {who}"
    )
    assert served_tool["description"] == spec["description"], (
        f"{name} description drifted; affected genes: {who}"
    )
    assert served_tool["annotations"]["readOnlyHint"] is spec["annotations"]["readOnlyHint"]


@pytest.mark.parametrize("name", ACTIVE)
def test_catalogue_entry_is_well_formed(raw_catalogue, name):
    spec = next(t for t in raw_catalogue["tools"] if t["name"] == name)
    Draft202012Validator.check_schema(spec["input_schema"])
    Draft202012Validator.check_schema(spec["output_schema"])
    assert spec["input_schema"].get("additionalProperties") is False
    assert spec["output_schema"].get("additionalProperties") is False
    assert 0 < spec["max_response_bytes"] <= 65536
    assert spec["annotations"]["readOnlyHint"] is True, "v1 is read-only (design rule 1)"
    props = spec["output_schema"]["properties"]
    has_list = any(
        v.get("type") == "array" or "array" in (v.get("type") or []) for v in props.values()
    )
    if has_list:
        assert "truncated" in props and "hint" in props, (
            f"{name}: list outputs need truncated+hint (rule 2)"
        )


def test_gene_map_names_only_active_tools(gene_map):
    unknown = {
        g: sorted(set(ts) - set(ACTIVE))
        for g, ts in gene_map["genes"].items()
        if set(ts) - set(ACTIVE)
    }
    assert not unknown, f"genes depend on tools that are deferred or unknown: {unknown}"
    assert gene_map["genes"], "gene map must not be empty"


def test_every_active_tool_has_at_least_one_consumer_or_is_listed_as_orphan(gene_map):
    consumers = {t for ts in gene_map["genes"].values() for t in ts}
    orphans = sorted(set(ACTIVE) - consumers)
    # Orphans are allowed but must be deliberate: list them here when adding a tool nobody consumes yet.
    assert orphans == ["search_events"], (
        f"unexpected orphan tools (add a gene or record here): {orphans}"
    )
