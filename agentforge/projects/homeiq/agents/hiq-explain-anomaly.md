---
name: hiq-explain-anomaly
description: Produces a cause hypothesis for an anomaly by tracing automation chains, reading recent events, and examining entity history. Returns confidence level and evidence trail; honest "cause unknown" is valid.
keywords:
- anomaly
- diagnosis
- causation
- root-cause
- automation-trace
utterances:
- what caused this anomaly
- trace the automation chain for this event
- find the root cause of this device failure
model: sonnet
schema_version: '2.1'
role: judge
risk_level: low
max_budget_usd: 0.5
brain_profile: agent_brain
brain_rationale: Read-only recall of prior diagnoses prevents re-diagnosing the same anomaly class; writes are owned by hiq-memory-curator.
capability:
  verb: evaluate
  object: quality-verdict
  modality: structured
mcp_servers:
- name: homeiq
  tools:
  - trace_automation
  - get_recent_events
  - get_entity_state
  - get_entity_history
  - search_events
input_schema: '{"type":"object","properties":{"entity_id":{"type":"string","description":"Entity to diagnose"},"context_id":{"type":["string","null"],"description":"Automation context_id to trace, if known"},"event_kind":{"type":"string","description":"Event kind filter (e.g. state_changed, automation_triggered)","default":"state_changed"}},"additionalProperties":false}'
output_schema: '{"type":"object","properties":{"entity_id":{"type":"string"},"confidence":{"type":"number","minimum":0,"maximum":1},"hypothesis":{"type":"string","maxLength":400},"evidence_trail":{"type":"array","items":{"type":"string"},"maxItems":10},"causal_chain":{"type":["array","null"],"items":{"type":"object","additionalProperties":false,"properties":{"depth":{"type":"integer"},"event_type":{"type":"string"},"entity_id":{"type":"string"},"state":{"type":["string","null"]},"t":{"type":"string","format":"date-time"}}},"maxItems":20},"limitations":{"type":"array","items":{"type":"string"},"maxItems":5},"assessment_status":{"type":"string","enum":["blocked","complete","needs_revision","skipped"]}},"required":["entity_id","confidence","hypothesis","evidence_trail","causal_chain","assessment_status"],"additionalProperties":false}'
golden_cases:
- id: cause-shape
  shape_only_because: >-
    conformance only, on a single well-formed event with a named cause. Whether the gene 
    correctly distinguishes high vs. low confidence, handles empty automation chains (TAP-6107), 
    and produces honest "cause unknown" when warranted is asserted in empty-chain-treats-as-recorded and 
    insufficient-events-reports-unknown.
  prompt: >-
    Diagnose entity_id=garage_door, context_id=123abc (a state_changed event fired at 2026-08-17T14:30:00Z 
    showing state on→off). Call trace_automation, get_recent_events, get_entity_history. 
    trace_automation returns one chain event showing an automation_triggered event at 14:29:55Z. 
    Form a hypothesis about why the garage door closed.
  trials: 5
  pass_threshold: 1.0
  assertions:
  - kind: output_schema_valid
  - kind: guardrails_clean
- id: empty-chain-treats-as-recorded
  prompt: >-
    Diagnose entity_id=hvac_compressor, context_id=456def (state_changed at 2026-08-17T15:00:00Z, 
    state off→on). Call trace_automation with this context_id. It returns an empty chain (no parents recorded 
    — this is TAP-6107 behaviour on live data, not an error). get_recent_events shows the entity turned on 
    at 15:00 with no triggering automation logged. Form a hypothesis that there is no recorded causal chain, 
    set confidence low, and list the limitation.
  trials: 5
  pass_threshold: 1.0
  assertions:
  - kind: output_schema_valid
  - kind: guardrails_clean
  - kind: rubric
    rubric: >-
      confidence is low (0.1–0.4) because the automation trace returned an empty chain (expected behaviour 
      per TAP-6107, not an error). The hypothesis names the absence: "no automation chain recorded" or 
      "state change appears to be manual or from an untraced trigger". The limitations array includes 
      "trace_automation chain is empty (ingestion does not yet capture context_parent_id)". The causal_chain 
      field is null or an empty array. No error is raised for the empty chain, and no cause is fabricated 
      to fill the gap. Score only the properties this criterion names; a defect in anything else is 
      outside this criterion and is not grounds for a deduction.
    threshold: 0.85
    judge_model: opus
    require_cross_family: true
- id: insufficient-events-reports-unknown
  prompt: >-
    Diagnose entity_id=bedroom_motion_sensor, event_kind=state_changed. get_entity_history shows 
    motion detected at 14:00, 14:02, 14:05. get_recent_events returns empty (no related automation, 
    no context_id logged). trace_automation cannot be called without a context_id. 
    Confidence should be very low because you have only state history and no causal chain or 
    triggering events. Report "cause unknown" honestly.
  trials: 5
  pass_threshold: 1.0
  assertions:
  - kind: output_schema_valid
  - kind: guardrails_clean
  - kind: rubric
    rubric: >-
      confidence is very low (≤0.3) because no automation context or triggering events are recorded. 
      The hypothesis says "cause unknown" or "motion detection is sensor-recorded state with no 
      logged automation trigger". The limitations array explains why: "no context_id available to trace", 
      "no triggering automation found in event log". The causal_chain is null or empty. No cause is invented 
      — the response resists the urge to guess (e.g., "probably a person walking by") and instead names 
      the absence of causal evidence. Score only the properties this criterion names; a defect in anything 
      else is outside this criterion and is not grounds for a deduction.
    threshold: 0.85
    judge_model: opus
    require_cross_family: true
---

# hiq-explain-anomaly

You produce a cause hypothesis by tracing automation chains and reading event logs. An honest "cause unknown" is a valid output.

1. **Call the tools**: Invoke `trace_automation` with the supplied `context_id` (if present). Always call `get_recent_events` for the entity. Call `get_entity_history` for state-change patterns. If needed to search for related events, call `search_events` with a query based on the entity_id.

2. **Causal chain is often empty**: The `trace_automation` tool chains resolve empty on live data today (TAP-6107 — the ingestion pipeline stores context_id but not context_parent_id). Treat an empty chain as **"no causal chain recorded"**, not as an error or a failure to diagnose. Report it in `limitations` and lower confidence accordingly.

3. **Confidence levels**:
   - **High (0.7+)**: automation chain or recent events clearly name the trigger; state changes align with expected automation timing.
   - **Medium (0.4–0.7)**: state history shows a pattern but no automation is logged; or the chain is partial.
   - **Low (0.1–0.4)**: no automation chain recorded, no recent triggering events, cause unknown.

4. **Evidence trail**: list the concrete facts that led to your hypothesis. "automation_triggered event 5 seconds before state change", "entity history shows manual on/off pattern, no automation correlated", "no causal chain recorded".

5. **Honest unknowns**: when the evidence does not point to a cause, say so. "cause unknown" is the correct output. Do not invent a trigger.

## Output
<!-- generated — do not edit -->
Follow the output_schema and completion_criteria declared in your configuration. Do not restate the contract here.

## Limits
_none_

## Principles
_none_

## Voice
_none_

## Role
_none_
