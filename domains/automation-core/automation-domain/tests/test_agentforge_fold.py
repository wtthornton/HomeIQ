"""What the TAP-7275 fold actually has to get right.

Four invariants, each of which would otherwise fail silently:

1. **Three slices, three schemas, one process.** Each slice reads its own
   environment variable. Under one shared ``DATABASE_SCHEMA`` the two slices
   that lost would read and write the wrong schema without raising.
2. **Every environment variable the code reads is set by the compose we ship.**
   This is the TAP-7365 shape: `compose.yml` documented a
   ``CALENDAR_INFLUXDB_BUCKET`` mechanism that nothing set, the adapter fell
   back to a bucket that did not exist, and the container reported healthy the
   whole time.
3. **A steered run is polled, not treated as a failure.** AgentForge answers a
   ``kickoff=sync`` request with 202 ``pending`` when the run exceeds its sync
   threshold. Eight of this lane's nine workflows answered 200; one answered
   202, which is exactly how this defect stays hidden.
4. **The real AgentForge output parses into what the callers expect.** These
   assertions are driven from run records captured from live AgentForge runs
   (``tests/fixtures/agentforge_real_runs.json``), not from hand-built dicts —
   a fixture and an unreachable branch agree perfectly, so the producer's own
   output is what gets fed in.
"""

from __future__ import annotations

import importlib
import json
import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[4]
COMPOSE = REPO_ROOT / "domains" / "automation-core" / "compose.yml"
REAL_RUNS = json.loads(
    (Path(__file__).parent / "fixtures" / "agentforge_real_runs.json").read_text()
)


def _real(workflow: str) -> dict:
    """The output of a real, non-dry AgentForge run of ``workflow``."""
    record = REAL_RUNS[workflow]
    assert record["state"] == "complete", (
        f"{workflow} fixture is not a completed run: {record['state']!r}"
    )
    return json.loads(record["output"])


# ---------------------------------------------------------------------------
# 1. One process, three schemas
# ---------------------------------------------------------------------------


class TestSchemaSeparation:
    """The agent, authoring and proactive slices must not share a schema var."""

    def test_each_slice_reads_its_own_env_var(self, monkeypatch):
        # A single DATABASE_SCHEMA is deliberately set to a wrong value. If any
        # slice still reads it, that slice ends up in `wrong_schema`.
        monkeypatch.setenv("DATABASE_SCHEMA", "wrong_schema")
        monkeypatch.setenv("AGENT_DB_SCHEMA", "agent")
        monkeypatch.setenv("AUTOMATION_DB_SCHEMA", "automation")
        monkeypatch.setenv("ENERGY_DB_SCHEMA", "energy")

        import src.agent.database as agent_db
        import src.proactive.database as proactive_db
        from src.authoring.config import Settings as AuthoringSettings

        importlib.reload(agent_db)
        importlib.reload(proactive_db)

        assert agent_db._schema == "agent"
        assert proactive_db._schema == "energy"
        assert AuthoringSettings().database_schema == "automation"

    def test_the_three_schemas_are_distinct(self, monkeypatch):
        monkeypatch.delenv("DATABASE_SCHEMA", raising=False)
        monkeypatch.delenv("AGENT_DB_SCHEMA", raising=False)
        monkeypatch.delenv("ENERGY_DB_SCHEMA", raising=False)
        monkeypatch.delenv("AUTOMATION_DB_SCHEMA", raising=False)

        import src.agent.database as agent_db
        import src.proactive.database as proactive_db
        from src.authoring.config import Settings as AuthoringSettings

        importlib.reload(agent_db)
        importlib.reload(proactive_db)

        schemas = {agent_db._schema, AuthoringSettings().database_schema, proactive_db._schema}
        assert schemas == {"agent", "automation", "energy"}


# ---------------------------------------------------------------------------
# 2. Every var the code reads is set by the compose we ship
# ---------------------------------------------------------------------------


class TestComposeSetsWhatTheCodeReads:
    """A documented env mechanism that nothing sets is the TAP-7365 defect."""

    @staticmethod
    def _compose_env_keys() -> set[str]:
        doc = yaml.safe_load(COMPOSE.read_text())
        service = doc["services"]["automation-domain"]
        keys = set()
        for entry in service["environment"]:
            keys.add(entry.split("=", 1)[0])
        return keys

    @pytest.mark.parametrize(
        "var",
        [
            "AGENTFORGE_URL",
            "AGENTFORGE_API_KEY",
            "AGENTFORGE_PROJECT_SLUG",
            "AGENTFORGE_TIMEOUT",
            "AGENT_DB_SCHEMA",
            "AUTOMATION_DB_SCHEMA",
            "ENERGY_DB_SCHEMA",
        ],
    )
    def test_var_is_set_by_the_shipped_compose(self, var):
        assert var in self._compose_env_keys(), (
            f"{var} is read by automation-domain's code but no compose entry sets it"
        )

    def test_no_openai_key_is_shipped(self):
        assert "OPENAI_API_KEY" not in self._compose_env_keys()

    def test_every_schema_var_the_code_reads_is_in_compose(self):
        """Derived from the source, not from a hand-written list.

        A new ``os.getenv("..._DB_SCHEMA")`` added later is caught here even if
        nobody remembers to extend the parametrised list above.
        """
        src_root = Path(__file__).resolve().parents[1] / "src"
        found = set()
        for path in src_root.rglob("*.py"):
            found |= set(re.findall(r'os\.getenv\(\s*"([A-Z0-9_]*_DB_SCHEMA)"', path.read_text()))
        assert found, "no *_DB_SCHEMA getenv found — this test would pass vacuously"
        assert found <= self._compose_env_keys()


# ---------------------------------------------------------------------------
# 3. A steered (202 pending) run is polled to completion
# ---------------------------------------------------------------------------


class TestSteeredRunIsPolled:
    """`kickoff=sync` is a request, not a guarantee."""

    @pytest.mark.asyncio
    async def test_pending_kickoff_is_polled_until_terminal(self, monkeypatch):
        from src import agentforge_client as af

        # The kickoff shape AgentForge really answered with for
        # `suggestion-describe`: 202, state pending, no output.
        kickoff = {"run_id": "fe1b5f14715a4b4d8a73cb71493621c3", "state": "pending"}
        # The poll route wraps the settled record under "run" — the real shape
        # from GET /workflows/runs/{id}.
        settled = {"run": {**REAL_RUNS["suggestion-describe"]}}

        class FakeResponse:
            def __init__(self, payload, status=200):
                self._payload = payload
                self.status_code = status
                self.text = json.dumps(payload)

            def json(self):
                return self._payload

        class FakeHTTP:
            def __init__(self):
                self.polls = 0

            async def post(self, *_a, **_kw):
                return FakeResponse(kickoff, status=202)

            async def get(self, *_a, **_kw):
                self.polls += 1
                return FakeResponse(settled)

        http = FakeHTTP()
        monkeypatch.setattr(af, "POLL_INTERVAL_SECONDS", 0.0)
        client = af.AgentForgeClient("http://af", "afp-test")
        monkeypatch.setattr(client, "_http", lambda: http)

        answer = await client.run_workflow_json("suggestion-describe", {"pattern_data": "{}"})

        assert http.polls >= 1, "a pending kickoff must be polled, not returned as-is"
        assert answer["description"]

    @pytest.mark.asyncio
    async def test_a_run_that_never_settles_raises_rather_than_hanging(self, monkeypatch):
        from src import agentforge_client as af

        class FakeResponse:
            def __init__(self, payload, status=200):
                self._payload = payload
                self.status_code = status
                self.text = json.dumps(payload)

            def json(self):
                return self._payload

        class FakeHTTP:
            async def post(self, *_a, **_kw):
                return FakeResponse({"run_id": "r1", "state": "pending"}, status=202)

            async def get(self, *_a, **_kw):
                return FakeResponse({"run": {"run_id": "r1", "state": "running"}})

        monkeypatch.setattr(af, "POLL_INTERVAL_SECONDS", 0.0)
        client = af.AgentForgeClient("http://af", "afp-test", timeout=0.05)
        monkeypatch.setattr(client, "_http", lambda: FakeHTTP())

        with pytest.raises(af.AgentForgeError) as excinfo:
            await client.run_workflow("automation-draft", {})
        assert excinfo.value.code == "timeout"


# ---------------------------------------------------------------------------
# 4. Real AgentForge output parses into what the callers expect
# ---------------------------------------------------------------------------


class TestRealWorkflowOutputParses:
    """Driven from live run records, never from a constructed input."""

    def test_draft_becomes_a_plan_the_parser_accepts(self):
        from src.authoring.clients.llm_client import plan_from_draft
        from src.authoring.services.plan_parser import PlanParser

        plan = plan_from_draft(_real("automation-draft"))

        assert plan["alias"], "the plan needs the alias PlanParser requires"
        assert plan["trigger"], "modern `triggers:` must normalise to `trigger`"
        assert plan["action"], "modern `actions:` must normalise to `action`"
        # The real consumer, not a shape assertion: PlanParser is what the
        # authoring service feeds this into.
        spec = PlanParser().parse_plan(plan)
        assert spec is not None

    def test_automation_json_carries_the_envelope_the_caller_reads(self):
        automation = _real("automation-json")["automation"]
        assert automation["alias"]
        assert automation["triggers"] and automation["actions"]

    def test_intent_plan_parameters_hold_no_envelope_fields(self):
        """The defect the first real run of `intent-plan` exposed.

        The gene answered with its whole envelope nested under `parameters`,
        which HomeIQ passes straight to the template renderer. The workflow
        schema now forbids the envelope's own field names in there.
        """
        plan = _real("intent-plan")
        envelope_fields = {
            "template_id",
            "template_version",
            "parameters",
            "confidence",
            "clarifications_needed",
            "safety_class",
            "explanation",
        }
        assert not (envelope_fields & set(plan["parameters"])), (
            f"parameters carries envelope fields: {sorted(envelope_fields & set(plan['parameters']))}"
        )

    def test_memory_extract_nulls_what_the_message_never_said(self):
        """The property memory extraction depends on: no guessed facts."""
        answer = _real("memory-extract")
        assert "favourite_colour" in answer["unsourced_fields"]
        assert answer["instance"]["favourite_colour"] is None
        assert answer["instance"]["work_from_home_days"], "a stated fact must survive"

    def test_proactive_suggestions_stay_inside_the_supplied_inventory(self):
        answer = _real("proactive-suggest")
        allowed = {"light.kitchen"}
        for action in answer["actions"]:
            assert action["entity_id"] in allowed
            assert action["entity_domain"] not in {"lock", "alarm_control_panel"}

    def test_device_name_suggestions_carry_no_brand(self):
        answer = _real("device-name-suggest")
        assert answer["suggestions"], "the run must have produced at least one name"
        for suggestion in answer["suggestions"]:
            lowered = suggestion["name"].lower()
            assert "signify" not in lowered
            assert "philips" not in lowered
            assert "lca001" not in lowered

    def test_enhancements_are_graded_and_avoid_the_lock(self):
        answer = _real("automation-enhance")
        assert answer["enhancements"]
        for item in answer["enhancements"]:
            assert item["level"] in {"small", "medium", "large"}
            assert "lock.front_door" not in json.dumps(item)

    def test_assistant_chat_answers_prose_the_endpoint_can_return(self):
        answer = _real("assistant-chat")
        assert isinstance(answer["answer"], str) and answer["answer"].strip()

    def test_describe_transform_renames_summary_to_description(self):
        answer = _real("suggestion-describe")
        assert "description" in answer and answer["description"].strip()
        assert "summary" not in answer, "the workflow's transform owns the rename"
