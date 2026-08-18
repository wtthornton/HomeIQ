---
name: hiq-anomaly-triage
description: Reads anomaly detection output and triages each anomaly into acted-on,
  watch, or dismiss with reasons drawn from device history and recent events.
keywords:
- anomaly
- triage
- alert
- device-status
- event-correlation
utterances:
- triage these anomalies
- which anomalies need attention
- classify detected anomalies by severity
model: haiku
schema_version: '2.1'
role: router
risk_level: low
max_budget_usd: 0.25
brain_profile: agent_brain
brain_rationale: Read-only recall of prior anomaly triages prevents duplicate alerts
  on recurring issues; writes are owned by hiq-memory-curator.
capability:
  verb: evaluate
  object: quality-verdict
  modality: structured
mcp_servers:
- name: homeiq
  tools:
  - detect_anomalies
  - get_entity_history
  - get_device
  - get_recent_events
input_schema: '{"type":"object","properties":{"anomaly_filter":{"type":"string","description":"Optional:
  filter kind (power, failure_risk, all)","default":"all"}},"additionalProperties":false}'
output_schema: '{"additionalProperties":false,"properties":{"assessment_status":{"enum":["blocked","complete","needs_revision","skipped"],"type":"string"},"build_summary":{"type":"string"},"confidence":{"maximum":1,"minimum":0,"type":"number"},"errors":{"items":{"type":"string"},"type":"array"},"reason":{"type":"object"},"spend_usd":{"type":"number"},"summary":{"additionalProperties":false,"properties":{"acted_on_count":{"type":"integer"},"dismiss_count":{"type":"integer"},"total_anomalies":{"type":"integer"},"watch_count":{"type":"integer"}},"required":["total_anomalies","acted_on_count","watch_count","dismiss_count"],"type":"object"},"triage_results":{"items":{"additionalProperties":false,"properties":{"anomaly_id":{"type":"string"},"device_id":{"type":["string","null"]},"entity_id":{"type":["string","null"]},"evidence":{"items":{"type":"string"},"type":"array"},"kind":{"type":"string"},"reasoning":{"maxLength":200,"type":"string"},"severity":{"type":"string"},"triage":{"enum":["acted_on","watch","dismiss"],"type":"string"}},"required":["anomaly_id","kind","severity","triage","reasoning"],"type":"object"},"maxItems":100,"type":"array"}},"required":["triage_results","summary","errors","assessment_status","confidence","build_summary","reason","spend_usd"],"type":"object"}'
golden_cases:
- id: triage-shape
  shape_only_because: conformance only, on a single well-formed anomaly. Whether triage
    correctly distinguishes  the three buckets and roots reasoning in device history
    is asserted in device-history-supports-dismiss  and recent-events-support-acting-on.
  prompt: 'Triage this anomaly: kind=failure_risk, device_id=garage_door_sensor, failure_probability=0.75,  risk_level=high,
    top_recommendation="Check battery voltage". Device history shows last state  change
    3 hours ago. Call the tools.'
  assertions:
  - kind: output_schema_valid
  - kind: guardrails_clean
- id: device-history-supports-dismiss
  prompt: 'Triage this anomaly: kind=power, entity_id=hvac_compressor, observed_w=6200,
    expected_w=5800,  severity=moderate, t=2026-08-17T14:30:00Z. get_entity_history
    for hvac_compressor shows  normal on/off cycles over 24 hours, no recent anomalies,
    and last engaged 1 hour ago for  30 minutes as expected. get_device shows no health
    issues. Dismiss this as within normal operation.'
  trials: 3
  pass_threshold: 1.0
  assertions:
  - kind: output_schema_valid
  - kind: guardrails_clean
  - kind: rubric
    rubric: the triage decision for hvac_compressor is "dismiss" because the entity
      history shows  normal operation and the device has no reported issues. The reasoning
      names the entity history  — "normal on/off cycles over 24 hours" or "power draw
      within expected range for recent duty cycle"  — and attributes the decision
      to that evidence. No anomaly is invented if the tools return  empty lists. Score
      only the properties this criterion names; a defect in anything else  is outside
      this criterion and is not grounds for a deduction.
    threshold: 0.85
    judge_model: sonnet
    require_cross_family: true
- id: recent-events-support-acting-on
  prompt: 'Triage this anomaly: kind=failure_risk, device_id=bedroom_switch, failure_probability=0.85,  risk_level=critical,
    top_recommendation="Replace device". get_device shows integration=zigbee,  sw_version=1.2.0
    from 2023. get_recent_events for this device shows three unresponsive  state-change
    attempts in the last 4 hours (commands sent but no state change observed).  Mark
    for action with reasoning drawn from the failure trend.'
  trials: 3
  pass_threshold: 1.0
  assertions:
  - kind: output_schema_valid
  - kind: guardrails_clean
  - kind: rubric
    rubric: the triage decision for bedroom_switch is "acted_on" because the recent
      events show  unresponsive state changes (commands that did not result in observed
      state change),  the failure probability is high (0.85), and the top_recommendation
      is to replace.  The reasoning names the concrete evidence — "device unresponsive
      to three recent commands"  and/or "high failure probability with device age
      (2023 firmware)" — and justifies escalation  to action. No invented device history
      or absent facts are assumed. Score only the properties  this criterion names;
      a defect in anything else is outside this criterion and is not grounds  for
      a deduction.
    threshold: 0.85
    judge_model: sonnet
    require_cross_family: true
---

# hiq-anomaly-triage
You triage anomalies into buckets for action. You read tool output and draw reasoning from device history and recent events, never from outside knowledge.

1. **Call the tools**: invoke `detect_anomalies` with the requested `anomaly_filter` (default "all"). For each anomaly returned, call `get_entity_history` (if entity_id is present) and `get_recent_events` (if entity_id or device_id is present), and `get_device` (if device_id is present).

2. **Three triage buckets**:
   - **acted_on**: anomaly shows in recent events (commands failing to execute, state unresponsive) or device health is critical and declining. High confidence action is needed.
   - **watch**: anomaly is real (device history confirms the pattern) but no immediate action. Monitor for escalation. Moderate confidence; worth a repeat check in 24 hours.
   - **dismiss**: anomaly is within normal operation (power draws are expected for the device's duty cycle, state changes are routine). Low confidence it is actually anomalous. Do not act.

3. **Reasoning**: name the tool output that supports your decision. "History shows normal operation", "three recent state changes failed", "failure probability high with device age and no recent errors". Never invent facts; if history is empty, say so and note that as a limitation (not grounds to invent normal operation).

4. **Empty result path**: if `detect_anomalies` returns empty arrays, return `triage_results: []`, `summary.total_anomalies: 0`, and `errors: []`. This is correct: there were no anomalies to triage.

## Tools
<!-- generated — do not edit -->
Use only the tools granted in your configuration (allowed_tools / tool_targets / mcp_servers). Do not invent additional grants.

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