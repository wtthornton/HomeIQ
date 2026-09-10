"""The authoring slice's LLM calls, now AgentForge workflow runs (TAP-7275).

This module replaces the OpenAI-client unit tests that lived here. The methods
under test kept their names and return types on purpose -- the authoring
services were not rewritten around a new shape, only the engine changed -- so
what has to be proven is that each one reaches the right workflow with the
right inputs and turns the answer back into what its caller already expects.

The parsing assertions are driven from a run record captured from a live
AgentForge run, not from a hand-built dict.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from src.authoring.clients.llm_client import (
    WORKFLOW_DESCRIBE,
    WORKFLOW_DRAFT,
    WORKFLOW_INTENT_PLAN,
    WORKFLOW_JSON,
    AutomationLLMClient,
    AutomationLLMError,
    format_entity_context,
    plan_from_draft,
)

REAL_RUNS = json.loads(
    (Path(__file__).resolve().parents[1] / "fixtures" / "agentforge_real_runs.json").read_text()
)


def real_output(workflow: str) -> dict:
    return json.loads(REAL_RUNS[workflow]["output"])


@pytest.fixture
def fake_agentforge():
    """A double for AgentForgeClient that records the calls made through it."""
    af = AsyncMock()
    af.configured = True
    af.calls = []

    async def run_workflow_json(name, inputs, dry_run=False):
        af.calls.append((name, inputs))
        return {
            WORKFLOW_DRAFT: real_output("automation-draft"),
            WORKFLOW_JSON: real_output("automation-json"),
            WORKFLOW_DESCRIBE: real_output("suggestion-describe"),
            WORKFLOW_INTENT_PLAN: real_output("intent-plan"),
        }[name]

    af.run_workflow_json = run_workflow_json
    return af


@pytest.fixture
def client(fake_agentforge):
    return AutomationLLMClient(agentforge=fake_agentforge)


class TestEntityContextIsPassedAsData:
    """R2: the automation must only name entities this home actually has."""

    def test_inventory_renders_per_domain(self):
        rendered = format_entity_context(
            {
                "entities": {
                    "light": [{"entity_id": "light.patio_patio"}, {"entity_id": "light.porch"}],
                    "binary_sensor": [{"entity_id": "binary_sensor.front_motion"}],
                }
            }
        )
        assert "LIGHT: light.patio_patio, light.porch" in rendered
        assert "BINARY_SENSOR: binary_sensor.front_motion" in rendered

    def test_absent_inventory_is_empty_not_a_claim_of_no_entities(self):
        assert format_entity_context(None) == ""
        assert format_entity_context({"entities": {}}) == ""

    def test_oversized_domain_is_sampled_and_says_so(self):
        entities = [{"entity_id": f"light.l{i}"} for i in range(45)]
        rendered = format_entity_context({"entities": {"light": entities}})
        assert "(and 15 more)" in rendered

    @pytest.mark.asyncio
    async def test_generate_yaml_sends_the_inventory_to_the_workflow(self, client, fake_agentforge):
        await client.generate_yaml(
            "Turn on the patio lights at sunset",
            entity_context={"entities": {"light": [{"entity_id": "light.patio_patio"}]}},
        )
        name, inputs = fake_agentforge.calls[-1]
        assert name == WORKFLOW_DRAFT
        assert inputs["behavior_requirement"] == "Turn on the patio lights at sunset"
        assert "light.patio_patio" in inputs["entity_inventory"]


class TestGenerationCallsReachTheRightWorkflow:
    @pytest.mark.asyncio
    async def test_generate_yaml_returns_the_automation_yaml(self, client):
        yaml_text = await client.generate_yaml("Turn on the patio lights at sunset")
        assert "triggers:" in yaml_text
        assert "light.patio_patio" in yaml_text

    @pytest.mark.asyncio
    async def test_structured_plan_uses_the_same_workflow(self, client, fake_agentforge):
        plan = await client.generate_structured_plan("Turn on the patio lights at sunset")
        assert fake_agentforge.calls[-1][0] == WORKFLOW_DRAFT
        assert plan["alias"]
        assert plan["trigger"] and plan["action"]

    @pytest.mark.asyncio
    async def test_homeiq_json_unwraps_the_automation_object(self, client, fake_agentforge):
        automation = await client.generate_homeiq_automation_json("Turn on the patio lights")
        assert fake_agentforge.calls[-1][0] == WORKFLOW_JSON
        assert automation["alias"]
        assert automation["triggers"]

    @pytest.mark.asyncio
    async def test_homeiq_context_is_serialised_for_the_workflow(self, client, fake_agentforge):
        await client.generate_homeiq_automation_json(
            "Turn on the patio lights", homeiq_context={"areas": ["Patio"]}
        )
        _, inputs = fake_agentforge.calls[-1]
        assert json.loads(inputs["homeiq_context"]) == {"areas": ["Patio"]}

    @pytest.mark.asyncio
    async def test_description_reads_the_transformed_key(self, client, fake_agentforge):
        text = await client.generate_suggestion_description({"pattern_type": "time_of_day"})
        assert fake_agentforge.calls[-1][0] == WORKFLOW_DESCRIBE
        assert "kitchen light" in text.lower()

    @pytest.mark.asyncio
    async def test_intent_plan_passes_the_catalogue_through(self, client, fake_agentforge):
        plan = await client.plan_intent(
            user_text="turn on the office light when someone walks in",
            template_catalog="room_entry_light_on (v1)",
            context={"entity_summary": "Office has no motion sensor"},
        )
        name, inputs = fake_agentforge.calls[-1]
        assert name == WORKFLOW_INTENT_PLAN
        assert inputs["template_catalog"] == "room_entry_light_on (v1)"
        assert plan["template_id"] == "room_entry_light_on"


class TestRefusalsSurfaceRatherThanReturningEmptyYaml:
    """A refused draft must raise, not return "" that renders as an automation."""

    @pytest.mark.asyncio
    async def test_refusal_raises_with_the_rule_id(self, fake_agentforge):
        async def refuse(name, inputs, dry_run=False):
            return {
                "automation_yaml": None,
                "alias": "",
                "assumptions": [],
                "entities_referenced": [],
                "refused": {"rule_id": "deny.unlock_lock", "reason": "unlocking is prohibited"},
            }

        fake_agentforge.run_workflow_json = refuse
        client = AutomationLLMClient(agentforge=fake_agentforge)

        with pytest.raises(AutomationLLMError) as excinfo:
            await client.generate_yaml("unlock the front door when I arrive")
        assert "deny.unlock_lock" in str(excinfo.value)

    def test_plan_from_a_refused_draft_raises(self):
        with pytest.raises(AutomationLLMError):
            plan_from_draft({"automation_yaml": None, "refused": {"rule_id": "deny.unlock_lock"}})


class TestUsageStatsReportWhatThisProcessCanSee:
    def test_stats_name_the_engine_and_count_runs(self, client):
        stats = client.get_usage_stats()
        assert stats["engine"] == "agentforge"
        assert stats["workflow_runs"] == 0

    @pytest.mark.asyncio
    async def test_runs_are_counted(self, client):
        await client.generate_yaml("Turn on the patio lights at sunset")
        assert client.get_usage_stats()["workflow_runs"] == 1

    @pytest.mark.asyncio
    async def test_reset_clears_the_counter(self, client):
        await client.generate_yaml("Turn on the patio lights at sunset")
        client.reset_usage_stats()
        assert client.get_usage_stats()["workflow_runs"] == 0
