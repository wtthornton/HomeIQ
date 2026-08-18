"""Contract tests for workflow node kinds, output contracts, and input refs.

Split from tests/test_validate.py (TAP-6023).
"""

from __future__ import annotations

import json

import kit_checks
import kit_rules
from validate_helpers import (  # noqa: F401
    AGENTS,
    SCHEMALESS,
    findings,
    isolated_findings,
    scheduled_workflow,
    write_agent,
    write_workflow,
)

# --- workflow node kinds ---


def test_unknown_node_kind_is_rejected(tmp_path) -> None:
    kit_checks.check_workflow(write_workflow(tmp_path, {"kpi": {"kind": "tranform"}}), {})
    assert "kind='tranform'" in findings()


def test_transform_node_requires_an_expression(tmp_path) -> None:
    kit_checks.check_workflow(write_workflow(tmp_path, {"kpi": {"kind": "transform"}}), {})
    assert "requires a non-empty 'expression'" in findings()


def test_transform_node_with_an_expression_passes(tmp_path) -> None:
    nodes = {"kpi": {"kind": "transform", "expression": "{'mer': revenue / ad_spend}"}}
    kit_checks.check_workflow(write_workflow(tmp_path, nodes), {})
    assert not kit_checks.ERRORS


def test_pattern_a_unavailable_kind_is_rejected(tmp_path) -> None:
    """`python` resolves only backend.* callables and this repo ships no AF-side code."""
    kit_checks.check_workflow(write_workflow(tmp_path, {"calc": {"kind": "python"}}), {})
    assert "Pattern A consumer" in findings()


# `kind: script` and `kind: sql` were both rejected by the hand-mirrored constant
# set, and both were probed against 4.57.1 and found reachable — a `PUT` carrying
# either returned 201 (then DELETE -> 204). The validator only ever exercised
# `kind: python`, which is why the drift survived. These pin the corrected axis:
# the kind is fine, the unregistered `script_id` is not.


def test_sql_is_a_real_node_kind(tmp_path) -> None:
    """Probed 2026-07-31: PUT with kind='sql' returned 201 against AF 4.57.1."""
    kit_checks.check_workflow(write_workflow(tmp_path, {"rollup": {"kind": "sql"}}), {})
    assert not kit_checks.ERRORS


def test_script_node_with_a_registered_id_passes(tmp_path) -> None:
    registered = sorted(kit_rules.VALID_SCRIPT_IDS)[0]
    nodes = {"relay": {"kind": "script", "script_id": registered}}
    kit_checks.check_workflow(write_workflow(tmp_path, nodes), {})
    assert not kit_checks.ERRORS


def test_script_node_without_an_id_is_rejected(tmp_path) -> None:
    kit_checks.check_workflow(write_workflow(tmp_path, {"relay": {"kind": "script"}}), {})
    assert "declares no 'script_id'" in findings()


def test_script_node_with_an_unregistered_id_is_rejected(tmp_path) -> None:
    """Publish accepts any id string; the failure lands at execution instead."""
    nodes = {"relay": {"kind": "script", "script_id": "external_job_relay"}}
    kit_checks.check_workflow(write_workflow(tmp_path, nodes), {})
    assert "is not registered in AF" in findings()


def test_node_kinds_come_from_the_committed_manifest(tmp_path) -> None:
    """The set is the platform's answer, not a copy of backend/workflows/models.py.

    Pinned because the constant it replaced drifted twice, silently, in a repo that
    cannot import the module it was mirroring.
    """
    snapshot = json.loads(kit_rules.CAPABILITIES_SNAPSHOT.read_text(encoding="utf-8"))
    assert kit_rules.VALID_NODE_KINDS == set(snapshot["manifest"]["workflow"]["node_kinds"])
    assert kit_rules.AF_VERSION == snapshot["af_version"]


# --- node output contracts: the gene's own schema is never the enforced one ---


def test_node_without_a_schema_whose_agent_has_one_is_rejected(tmp_path) -> None:
    """The four-times-shipped defect: prose stored as a successful node output."""
    kit_checks.check_workflow(write_workflow(tmp_path, {"digest": {"agent": "digest-gene"}}), AGENTS)
    assert "declares no node-level output_schema" in findings()


def test_node_that_restates_the_contract_passes(tmp_path) -> None:
    nodes = {"digest": {"agent": "digest-gene", "output_schema": {"type": "object"}}}
    kit_checks.check_workflow(write_workflow(tmp_path, nodes), AGENTS)
    assert not kit_checks.ERRORS


def test_node_whose_agent_declares_no_schema_is_exempt(tmp_path) -> None:
    """The rule mirrors the gene's own contract — with none, there is none to enforce."""
    kit_checks.check_workflow(write_workflow(tmp_path, {"probe": {"agent": "bare"}}), {"bare": SCHEMALESS})
    assert not kit_checks.ERRORS


# --- $all_outputs is the scanner's privilege, not a convenience ---


def test_wildcard_input_outside_the_scanner_is_rejected(tmp_path) -> None:
    nodes = {
        "curate": {
            "agent": "digest-gene",
            "output_schema": {"type": "object"},
            "inputs": {"run_outputs": "$all_outputs"},
        }
    }
    kit_checks.check_workflow(write_workflow(tmp_path, nodes), AGENTS)
    assert "$all_outputs" in findings()


def test_the_scanner_may_read_the_wildcard(tmp_path) -> None:
    """A scanner that cannot see everything cannot scan — this row must stay legal."""
    nodes = {
        "scan": {
            "agent": "scan-gene",
            "output_schema": {"type": "object"},
            "inputs": {"items": "$all_outputs"},
        }
    }
    kit_checks.check_workflow(write_workflow(tmp_path, nodes), AGENTS)
    assert not kit_checks.ERRORS


# --- a gene that writes to shared memory must know what it is handling ---


def test_memory_writer_blind_to_the_trust_envelope_is_rejected(tmp_path) -> None:
    kit_checks.check_agent(write_agent(tmp_path, memory_profile="full"))
    assert "trust envelope" in findings()


def test_memory_writer_that_names_the_envelope_passes(tmp_path) -> None:
    path = write_agent(tmp_path, memory_profile="full")
    path.write_text(
        path.read_text(encoding="utf-8") + "\nPersist nothing absent from scan's safe_items.\n",
        encoding="utf-8",
    )
    kit_checks.check_agent(path)
    assert not kit_checks.ERRORS


def test_a_readonly_gene_needs_no_trust_vocabulary(tmp_path) -> None:
    """Only writers can poison the namespace — readers are out of scope for this rule."""
    kit_checks.check_agent(write_agent(tmp_path, memory_profile="readonly"))
    assert not kit_checks.ERRORS


# --- quarantine routing: downstream reads the gate, not what the gate judged ---


def quarantine_workflow(tmp_path, digest_inputs: dict, **extra_nodes):
    nodes = {
        "fetch": {"agent": "ingest-gene", "output_schema": {"type": "object"}},
        "scan": {
            "agent": "scan-gene",
            "output_schema": {"type": "object"},
            "depends_on": ["fetch"],
            "inputs": {"items": "$fetch"},
        },
        "digest": {
            "agent": "digest-gene",
            "output_schema": {"type": "object"},
            "depends_on": ["scan"],
            "inputs": digest_inputs,
        },
        **extra_nodes,
    }
    return write_workflow(tmp_path, nodes, output="digest")


def test_downstream_node_reading_the_gates_source_is_rejected(tmp_path) -> None:
    """D3's exact shape: the verdict is in the DAG, the unjudged payload in the inputs."""
    kit_checks.check_workflow(quarantine_workflow(tmp_path, {"picture": "$fetch"}), AGENTS)
    assert "reads ['fetch'] directly" in findings()


def test_downstream_node_reading_through_the_gate_passes(tmp_path) -> None:
    kit_checks.check_workflow(quarantine_workflow(tmp_path, {"picture": "$scan.safe_payload"}), AGENTS)
    assert not kit_checks.ERRORS


def test_the_routing_rule_reaches_transitive_descendants(tmp_path) -> None:
    """A grandchild of the gate reads around it just as effectively as a child."""
    tail = {
        "notify": {
            "agent": "digest-gene",
            "output_schema": {"type": "object"},
            "depends_on": ["digest"],
            "inputs": {"message": "$digest", "raw": "$fetch"},
        }
    }
    path = quarantine_workflow(tmp_path, {"picture": "$scan.safe_payload"}, **tail)
    kit_checks.check_workflow(path, AGENTS)
    assert "node 'notify'" in findings()


# --- input refs: the platform resolves these at runtime only ---


def ref_workflow(tmp_path, digest_inputs: dict, **extra):
    nodes = {
        "scan": {
            "agent": "scan-gene",
            "output_schema": {
                "type": "object",
                "properties": {
                    "safe_payload": {"type": "array"},
                    "metrics": {"type": "object", "properties": {"revenue": {"type": "number"}}},
                },
            },
        },
        "digest": {
            "agent": "digest-gene",
            "output_schema": {"type": "object"},
            "depends_on": ["scan"],
            "inputs": digest_inputs,
        },
    }
    return write_workflow(tmp_path, nodes, output="digest", **extra)


def test_ref_to_an_unknown_name_is_rejected(tmp_path) -> None:
    kit_checks.check_workflow(ref_workflow(tmp_path, {"x": "$noplace"}), AGENTS)
    assert "neither a node nor a declared workflow input" in findings()


def test_dotted_ref_to_a_field_the_schema_lacks_is_rejected(tmp_path) -> None:
    """The typo that at spec_version 1 reads downstream as 'the gate cleared nothing'."""
    kit_checks.check_workflow(ref_workflow(tmp_path, {"x": "$scan.safe_paylod"}), AGENTS)
    assert "declares no 'safe_paylod'" in findings()


def test_dotted_ref_the_schema_declares_passes(tmp_path) -> None:
    kit_checks.check_workflow(ref_workflow(tmp_path, {"x": "$scan.safe_payload"}), AGENTS)
    assert not kit_checks.ERRORS


def test_nested_dotted_ref_is_walked(tmp_path) -> None:
    kit_checks.check_workflow(ref_workflow(tmp_path, {"x": "$scan.metrics.revenue"}), AGENTS)
    assert not kit_checks.ERRORS
    kit_checks.check_workflow(ref_workflow(tmp_path, {"x": "$scan.metrics.revenu"}), AGENTS)
    assert "declares no 'metrics.revenu'" in findings()


def test_declared_workflow_input_is_not_a_node_ref(tmp_path) -> None:
    path = ref_workflow(tmp_path, {"since": "$since_ts"}, inputs=["since_ts"])
    kit_checks.check_workflow(path, AGENTS)
    assert not kit_checks.ERRORS


def test_typed_workflow_inputs_are_recognised(tmp_path) -> None:
    """`inputs:` takes bare names or typed objects, mixed in one list."""
    typed = [{"name": "since_ts", "type": "string", "required": False}, "channels"]
    path = ref_workflow(tmp_path, {"since": "$since_ts", "ch": "$channels"}, inputs=typed)
    kit_checks.check_workflow(path, AGENTS)
    assert not kit_checks.ERRORS


def test_reserved_tokens_are_not_treated_as_node_refs(tmp_path) -> None:
    """`$all_outputs` and friends are resolver keywords, not nodes."""
    nodes = {
        "scan": {
            "agent": "scan-gene",
            "output_schema": {"type": "object"},
            "inputs": {"items": "$all_outputs", "n": "$iteration_index", "r": "$run_id"},
        }
    }
    kit_checks.check_workflow(write_workflow(tmp_path, nodes), AGENTS)
    assert not kit_checks.ERRORS


def test_a_partial_schema_is_not_read_as_a_denial(tmp_path) -> None:
    """A node schema that stops describing a subtree must not fail refs into it."""
    kit_checks.check_workflow(ref_workflow(tmp_path, {"x": "$scan.safe_payload.0.body_text"}), AGENTS)
    assert not kit_checks.ERRORS


def test_a_gates_indirect_ancestors_are_not_its_payload(tmp_path) -> None:
    """A mid-DAG gate inherits ancestors that have nothing to do with the payload.

    cx-inbox's evidence gate transitively descends from `classify`, whose output
    is triage derived from an already-gated source. Flagging that would push a
    reader toward rewiring something already correct.
    """
    nodes = {
        "triage": {"agent": "digest-gene", "output_schema": {"type": "object"}},
        "evidence": {
            "agent": "ingest-gene",
            "output_schema": {"type": "object"},
            "depends_on": ["triage"],
            "inputs": {"for": "$triage"},
        },
        "gate": {
            "agent": "scan-gene",
            "output_schema": {"type": "object", "properties": {"safe_payload": {"type": "array"}}},
            "depends_on": ["evidence"],
            "inputs": {"items": "$evidence"},
        },
        "reply": {
            "agent": "digest-gene",
            "output_schema": {"type": "object"},
            "depends_on": ["gate"],
            "inputs": {"threads": "$triage", "evidence": "$gate.safe_payload"},
        },
    }
    kit_checks.check_workflow(write_workflow(tmp_path, nodes, output="reply"), AGENTS)
    assert not kit_checks.ERRORS


def test_the_gates_own_source_is_still_caught_mid_dag(tmp_path) -> None:
    """The same shape, but reading the judged source directly, must still fire."""
    nodes = {
        "triage": {"agent": "digest-gene", "output_schema": {"type": "object"}},
        "evidence": {
            "agent": "ingest-gene",
            "output_schema": {"type": "object"},
            "depends_on": ["triage"],
            "inputs": {"for": "$triage"},
        },
        "gate": {
            "agent": "scan-gene",
            "output_schema": {"type": "object"},
            "depends_on": ["evidence"],
            "inputs": {"items": "$evidence"},
        },
        "reply": {
            "agent": "digest-gene",
            "output_schema": {"type": "object"},
            "depends_on": ["gate"],
            "inputs": {"evidence": "$evidence"},
        },
    }
    kit_checks.check_workflow(write_workflow(tmp_path, nodes, output="reply"), AGENTS)
    assert "reads ['evidence'] directly" in findings()


def test_a_workflow_with_no_quarantine_node_is_unaffected(tmp_path) -> None:
    nodes = {
        "fetch": {"agent": "ingest-gene", "output_schema": {"type": "object"}},
        "digest": {
            "agent": "digest-gene",
            "output_schema": {"type": "object"},
            "depends_on": ["fetch"],
            "inputs": {"picture": "$fetch"},
        },
    }
    kit_checks.check_workflow(write_workflow(tmp_path, nodes), AGENTS)
    assert not kit_checks.ERRORS


# --- described is not enough: at spec_version 2 a referenced field must be required ---


def strict_ref_workflow(tmp_path, digest_inputs: dict, required: list, **extra):
    """A producer whose schema describes two fields but requires only what `required` names."""
    nodes = {
        "fetch": {
            "agent": "ingest-gene",
            "output_schema": {
                "type": "object",
                "required": required,
                "properties": {
                    "items": {"type": "array"},
                    "sources_unavailable": {"type": "array", "items": {"type": "string"}},
                    "metrics": {
                        "type": "object",
                        "required": ["revenue"],
                        "properties": {"revenue": {"type": "number"}, "aov": {"type": "number"}},
                    },
                },
            },
        },
        "digest": {
            "agent": "digest-gene",
            "output_schema": {"type": "object"},
            "depends_on": ["fetch"],
            "inputs": digest_inputs,
        },
    }
    return write_workflow(tmp_path, nodes, output="digest", **extra)


def test_ref_to_a_described_but_optional_field_is_rejected_at_spec_version_2(tmp_path) -> None:
    """The Phase 5 hazard: every ingest node described `sources_unavailable`, none required it.

    A producer that legally omits the key kills the consumer with InputRefError
    on the day it degrades — the one day the field was worth reading.
    """
    path = strict_ref_workflow(
        tmp_path, {"gaps": "$fetch.sources_unavailable"}, required=["items"], spec_version=2
    )
    kit_checks.check_workflow(path, AGENTS)
    assert "does not mark 'sources_unavailable' required" in findings()


def test_ref_to_a_required_field_passes_at_spec_version_2(tmp_path) -> None:
    path = strict_ref_workflow(
        tmp_path,
        {"gaps": "$fetch.sources_unavailable"},
        required=["items", "sources_unavailable"],
        spec_version=2,
    )
    kit_checks.check_workflow(path, AGENTS)
    assert not kit_checks.ERRORS


def test_an_optional_field_ref_is_tolerated_at_spec_version_1(tmp_path) -> None:
    """At 1 the resolver collapses an absent field to "" instead of raising, so this is not fatal."""
    path = strict_ref_workflow(tmp_path, {"gaps": "$fetch.sources_unavailable"}, required=["items"])
    kit_checks.check_workflow(path, AGENTS)
    assert not kit_checks.ERRORS


def test_the_required_walk_reaches_nested_fields(tmp_path) -> None:
    path = strict_ref_workflow(
        tmp_path, {"x": "$fetch.metrics.revenue"}, required=["metrics"], spec_version=2
    )
    kit_checks.check_workflow(path, AGENTS)
    assert not kit_checks.ERRORS
    path = strict_ref_workflow(
        tmp_path, {"x": "$fetch.metrics.aov"}, required=["metrics"], spec_version=2
    )
    kit_checks.check_workflow(path, AGENTS)
    assert "does not mark 'metrics.aov' required" in findings()


# --- the one field readable around the gate, and only that field ---


def test_downstream_may_read_sources_unavailable_around_the_gate(tmp_path) -> None:
    """The Phase 5 `availability` node's shape: connectivity metadata, never item text.

    It reads the ingest node directly and deliberately: the soak metric must not
    be relayed through `scan`, the gene that narrated instead of scanning on 71
    consecutive runs while every node reported `complete`.
    """
    availability = {
        "availability": {
            "kind": "transform",
            "depends_on": ["scan"],
            "inputs": {"fetch": "$fetch.sources_unavailable"},
            "expression": '{"degraded": len(fetch or []) > 0}',
        }
    }
    path = quarantine_workflow(tmp_path, {"picture": "$scan.safe_payload"}, **availability)
    kit_checks.check_workflow(path, AGENTS)
    assert not kit_checks.ERRORS


def test_the_gate_transparent_exemption_covers_only_that_one_field(tmp_path) -> None:
    """`sources_unavailable` is an allowlist of exactly one field, not a precedent."""
    for field, expected in (("items", "reads ['fetch'] directly"), ("", "reads ['fetch'] directly")):
        kit_checks.ERRORS.clear()
        leak = {
            "leaky": {
                "kind": "transform",
                "depends_on": ["scan"],
                "inputs": {"raw": f"$fetch.{field}" if field else "$fetch"},
                "expression": "raw",
            }
        }
        path = quarantine_workflow(tmp_path, {"picture": "$scan.safe_payload"}, **leak)
        kit_checks.check_workflow(path, AGENTS)
        assert expected in findings(), f"field={field!r} should still be caught"


# --- a scheduled fire passes no inputs, so what it references needs a default ---


def test_scheduled_workflow_referencing_a_defaultless_input_is_rejected(tmp_path) -> None:
    """agent-readiness' latent weekly failure: required corpus + schedule trigger.

    Each decision was sensible alone. Together they guarantee an InputRefError
    before any node executes, at $0, once a week.
    """
    path = scheduled_workflow(
        tmp_path,
        inputs=[{"name": "hosts", "required": True}],
        triggers=[{"type": "schedule", "interval_seconds": 604800}],
    )
    kit_checks.check_workflow(path, AGENTS)
    assert "fires on a schedule and a node references input 'hosts'" in findings()


def test_scheduled_workflow_whose_input_has_a_default_passes(tmp_path) -> None:
    path = scheduled_workflow(
        tmp_path,
        inputs=[{"name": "hosts", "required": False, "default": ""}],
        triggers=[{"type": "schedule", "cron": "0 7 * * *"}],
    )
    kit_checks.check_workflow(path, AGENTS)
    assert not kit_checks.ERRORS


def test_an_untriggered_workflow_may_require_inputs_of_its_caller(tmp_path) -> None:
    """listing-pipeline working as intended — the caller supplies the supplier docs."""
    path = scheduled_workflow(tmp_path, inputs=[{"name": "hosts", "required": True}])
    kit_checks.check_workflow(path, AGENTS)
    assert not kit_checks.ERRORS


def test_an_unreferenced_defaultless_input_does_not_trip_the_schedule_rule(tmp_path) -> None:
    """Only inputs a node actually reads can raise InputRefError."""
    path = scheduled_workflow(
        tmp_path,
        inputs=[{"name": "hosts", "default": ""}, {"name": "unused", "required": True}],
        triggers=[{"type": "schedule", "cron": "0 7 * * *"}],
    )
    kit_checks.check_workflow(path, AGENTS)
    assert not kit_checks.ERRORS


# --- judgment gates run 5 trials at threshold 1.0 (skills/passk-eval/SKILL.md:25) ---
#
# This rule is enforced in code because prose failed. The invariant lived only in
# a skill pack no gene can read, `.ralph/fix_plan.md` recorded the audit as
# complete, and two cases were then added to `wstore-judge-disclosure` at
# `trials: 3` — copied from a `role: gateway` gene where 3 is correct — with
# validate.py staying green throughout.


def judge_case(**overrides) -> dict:
    case = {
        "id": "blocks-the-bad-thing",
        "prompt": "judge this",
        "trials": 5,
        "pass_threshold": 1.0,
        # Declared, because a rubric-less case that does not say why is now an
        # error in its own right — and these tests are about trials, not that.
        "shape_only_because": "fixture for the trial-count rules only",
        "assertions": [{"kind": "guardrails_clean"}],
    }
    return {**case, **overrides}


def test_judge_case_below_five_trials_fails(tmp_path) -> None:
    path = write_agent(tmp_path, role="judge", golden_cases=[judge_case(trials=3)])
    kit_checks.check_agent(path)
    assert "requires trials: 5" in findings()


def test_judge_case_above_five_trials_also_fails(tmp_path) -> None:
    """Not a floor — the number is the contract, so drift in either direction is caught."""
    path = write_agent(tmp_path, role="judge", golden_cases=[judge_case(trials=7)])
    kit_checks.check_agent(path)
    assert "requires trials: 5" in findings()


def test_judge_case_with_lowered_threshold_fails(tmp_path) -> None:
    """A judge that half-agrees has not judged."""
    path = write_agent(tmp_path, role="judge", golden_cases=[judge_case(pass_threshold=0.9)])
    kit_checks.check_agent(path)
    assert "requires pass_threshold: 1.0" in findings()


def test_conforming_judge_case_passes(tmp_path) -> None:
    path = write_agent(tmp_path, role="judge", golden_cases=[judge_case()])
    kit_checks.check_agent(path)
    assert not kit_checks.ERRORS


def test_non_judge_gene_may_use_three_trials(tmp_path) -> None:
    """`wstore-upsert-product` is role: gateway and legitimately sits at 3.

    The rule must not spread to every gene — that would force a 67% cost rise on
    producer evals for no gate value.
    """
    path = write_agent(tmp_path, role="gateway", golden_cases=[judge_case(trials=3)])
    kit_checks.check_agent(path)
    assert not kit_checks.ERRORS


def test_out_of_range_trials_still_reports_the_range_not_the_judge_rule(tmp_path) -> None:
    """The generic bound fires first; the judge rule must not mask it."""
    path = write_agent(tmp_path, role="judge", golden_cases=[judge_case(trials=99)])
    kit_checks.check_agent(path)
    assert "must be an int in 1..20" in findings()
