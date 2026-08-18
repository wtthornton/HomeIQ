import pytest
from src.auth import READ_SCOPES, WRITE_SCOPES
from src.catalogue import ToolSpec
from src.errors import ToolError
from src.registry import ToolRegistry


async def test_list_tools_serves_catalogue_schemas_verbatim(registry, catalogue):
    @registry.register("get_entity_state")
    async def _handler(args):
        return {
            "entity_id": args["entity_id"],
            "state": "on",
            "t": None,
            "source": "last_observed_event",
        }

    (tool,) = registry.list_tools()
    spec = catalogue.tools["get_entity_state"]
    dumped = tool.model_dump(by_alias=True, exclude_none=True)
    assert dumped["inputSchema"] == spec.input_schema
    assert dumped["outputSchema"] == spec.output_schema
    assert dumped["annotations"]["readOnlyHint"] is True


async def test_input_validation_maps_to_invalid_input(registry):
    @registry.register("get_entity_state")
    async def _handler(args):
        return {}

    with pytest.raises(ToolError) as exc:
        await registry.call("get_entity_state", {"hours": 24}, scopes=READ_SCOPES)
    assert exc.value.code == "invalid_input"
    assert "entity_id" in exc.value.message

    with pytest.raises(ToolError) as exc:
        await registry.call(
            "get_entity_state", {"entity_id": "light.x", "hours": 0}, scopes=READ_SCOPES
        )
    assert exc.value.code == "invalid_input"


async def test_unknown_tool_is_not_found(registry):
    with pytest.raises(ToolError) as exc:
        await registry.call("nope", {}, scopes=READ_SCOPES)
    assert exc.value.code == "not_found"


async def test_off_contract_output_is_contract_violation(registry):
    @registry.register("get_entity_state")
    async def _handler(args):
        return {"entity_id": args["entity_id"], "state": "on", "t": None, "source": "not_in_enum"}

    with pytest.raises(ToolError) as exc:
        await registry.call("get_entity_state", {"entity_id": "light.x"}, scopes=READ_SCOPES)
    assert exc.value.code == "contract_violation"
    assert "source" in exc.value.message


async def test_budget_is_enforced_before_output_validation(registry):
    @registry.register("get_entity_history", narrow_hint="hours")
    async def _handler(args):
        return {
            "entity_id": args["entity_id"],
            "points": [{"t": "2026-08-17T00:00:00Z", "state": "x" * 200} for _ in range(500)],
            "count": 500,
            "truncated": False,
        }

    payload = await registry.call(
        "get_entity_history", {"entity_id": "light.x", "hours": 24}, scopes=READ_SCOPES
    )
    assert payload["truncated"] is True
    assert payload["hint"] == "hours"
    assert payload["count"] == len(payload["points"])


def test_deferred_tools_cannot_be_registered(registry):
    with pytest.raises(ValueError, match="deferred"):
        registry.register("get_energy_correlations")
    assert "get_energy_correlations" not in registry.unregistered_active()


def test_registering_twice_fails(registry):
    async def _h(args):
        return {}

    registry.register("list_areas")(_h)
    with pytest.raises(ValueError, match="twice"):
        registry.register("list_areas")(_h)


async def test_write_grant_requires_mutate_scope_and_allowlist(catalogue):
    # No v1 tool mutates, so synthesise a mutating spec to exercise design rule 1.
    from jsonschema import Draft202012Validator

    schema = {"type": "object", "additionalProperties": False, "properties": {}}
    spec = ToolSpec(
        name="set_thing",
        description="mutates",
        input_schema=schema,
        output_schema=schema,
        max_response_bytes=1024,
        read_only=False,
        input_validator=Draft202012Validator(schema),
        output_validator=Draft202012Validator(schema),
    )
    catalogue.tools["set_thing"] = spec

    async def _h(args):
        return {}

    ungranted = ToolRegistry(catalogue)
    ungranted.register("set_thing")(_h)
    with pytest.raises(ToolError, match="read-only"):
        await ungranted.call("set_thing", {}, scopes=READ_SCOPES)
    with pytest.raises(ToolError, match="HOMEIQ_MCP_ALLOW_WRITES"):
        await ungranted.call("set_thing", {}, scopes=WRITE_SCOPES)

    granted = ToolRegistry(catalogue, allowed_write_tools=frozenset({"set_thing"}))
    granted.register("set_thing")(_h)
    assert await granted.call("set_thing", {}, scopes=WRITE_SCOPES) == {}
