---
name: hiq-device-health-triage
description: Fleet health triage that reads device health scores and anomalies, naming
  which devices need attention and why.
keywords:
- device-health
- triage
- fleet-status
- maintenance
- device-failure-risk
utterances:
- which devices need attention
- triage the fleet health
- device health summary
model: haiku
schema_version: '2.1'
role: router
risk_level: low
max_budget_usd: 0.25
brain_profile: agent_brain
brain_rationale: Read-only recall of device health trends helps distinguish recurring
  issues from new failures; writes are owned by hiq-memory-curator.
capability:
  verb: evaluate
  object: quality-verdict
  modality: structured
mcp_servers:
- name: homeiq
  tools:
  - get_device_health
  - get_device
  - detect_anomalies
input_schema: '{"type":"object","properties":{"min_score":{"type":"integer","minimum":0,"maximum":100,"default":70,"description":"Report
  devices with health score below this"},"health_status_filter":{"type":"string","enum":["healthy","degraded","critical","all"],"default":"all"}},"additionalProperties":false}'
output_schema: '{"additionalProperties":false,"properties":{"assessment_status":{"enum":["blocked","complete","needs_revision","skipped"],"type":"string"},"build_summary":{"type":"string"},"confidence":{"maximum":1,"minimum":0,"type":"number"},"devices_by_status":{"additionalProperties":false,"properties":{"critical":{"items":{"additionalProperties":false,"properties":{"anomalies":{"items":{"type":"string"},"maxItems":5,"type":"array"},"device_id":{"type":"string"},"health_score":{"type":"number"},"health_status":{"type":"string"},"issue_summary":{"maxLength":150,"type":"string"},"name":{"type":"string"}},"required":["device_id","name","health_score","health_status"],"type":"object"},"maxItems":20,"type":"array"},"degraded":{"items":{"additionalProperties":false,"properties":{"anomalies":{"items":{"type":"string"},"maxItems":5,"type":"array"},"device_id":{"type":"string"},"health_score":{"type":"number"},"health_status":{"type":"string"},"issue_summary":{"maxLength":150,"type":"string"},"name":{"type":"string"}},"required":["device_id","name","health_score","health_status"],"type":"object"},"maxItems":20,"type":"array"},"healthy":{"items":{"additionalProperties":false,"properties":{"device_id":{"type":"string"},"health_score":{"type":"number"},"health_status":{"type":"string"},"name":{"type":"string"}},"required":["device_id","name","health_score","health_status"],"type":"object"},"maxItems":20,"type":"array"}},"required":["critical","degraded","healthy"],"type":"object"},"errors":{"items":{"type":"string"},"type":"array"},"fleet_summary":{"additionalProperties":false,"properties":{"avg_score":{"type":"number"},"critical_count":{"type":"integer"},"degraded_count":{"type":"integer"},"healthy_count":{"type":"integer"},"total":{"type":"integer"}},"required":["total","critical_count","degraded_count","healthy_count"],"type":"object"},"reason":{"type":"object"},"spend_usd":{"type":"number"}},"required":["devices_by_status","fleet_summary","errors","assessment_status","confidence","build_summary","reason","spend_usd"],"type":"object"}'
golden_cases:
- id: device-health-shape
  shape_only_because: conformance only, on a mixed fleet. Whether the gene correctly
    names devices needing  attention and distinguishes critical from degraded is asserted
    in critical-devices-reported-first  and empty-fleet-is-honest.
  prompt: 'Triage device health min_score=70. get_device_health with no device_id
    returns summary.healthy=5,  summary.degraded=2, summary.critical=1, devices=[{device_id:
    d1, health_status: critical, overall_score: 25},  {device_id: d2, health_status:
    degraded, overall_score: 65}]. For each, call get_device to fetch name.  Call
    detect_anomalies to find any associated anomalies.'
  assertions:
  - kind: output_schema_valid
  - kind: guardrails_clean
- id: critical-devices-reported-first
  prompt: 'Triage device health min_score=70, health_status_filter=all. get_device_health
    returns devices:  [{device_id: garage_door_sensor, health_status: critical, overall_score:
    15},  {device_id: hallway_thermostat, health_status: degraded, overall_score:
    62},  {device_id: office_light, health_status: healthy, overall_score: 98}]. get_device
    returns names for each.  detect_anomalies with kind=all returns a failure_risk
    prediction for garage_door_sensor with probability=0.92.  Report critical devices
    first with their anomalies.'
  trials: 3
  pass_threshold: 1.0
  assertions:
  - kind: output_schema_valid
  - kind: guardrails_clean
  - kind: rubric
    rubric: 'devices_by_status.critical lists garage_door_sensor first with health_score:
      15 and an  anomalies array containing the failure risk (e.g., "High failure
      risk (probability 0.92)").  devices_by_status.degraded lists hallway_thermostat
      with score 62. devices_by_status.healthy  lists office_light. The issue_summary
      for critical devices names the problem: "Low health score  with high failure
      risk", not "Device may need attention". fleet_summary shows total=3,  critical_count=1,
      degraded_count=1, healthy_count=1. No device is omitted or misclassified.  Score
      only the properties this criterion names; a defect in anything else is outside
      this  criterion and is not grounds for a deduction.'
    threshold: 0.85
    judge_model: sonnet
    require_cross_family: true
- id: empty-fleet-is-honest
  prompt: Triage device health min_score=70. get_device_health returns summary.total=0,
    devices=[].  Report an empty fleet honestly.
  trials: 3
  pass_threshold: 1.0
  assertions:
  - kind: output_schema_valid
  - kind: guardrails_clean
  - kind: rubric
    rubric: devices_by_status.critical is an empty array, devices_by_status.degraded
      is empty,  devices_by_status.healthy is empty. fleet_summary.total is 0, all
      counts are 0.  No devices are fabricated. No error is raised for the empty fleet.
      errors is an empty array  (an empty fleet is not an error). Score only the properties
      this criterion names; a defect  in anything else is outside this criterion and
      is not grounds for a deduction.
    threshold: 0.85
    judge_model: sonnet
    require_cross_family: true
---

# hiq-device-health-triage
You triage the fleet's device health into critical, degraded, and healthy buckets. You name which devices need attention and what the issue is.

1. **Call the tools**: Invoke `get_device_health` with no device_id (fleet summary). For each device, call `get_device` to fetch its full metadata including name. Call `detect_anomalies` with kind=failure_risk to correlate health scores with detected failure risks.

2. **Three buckets** (from tool output):
   - **critical**: health_status="critical" or overall_score < min_score and failing. Needs immediate attention.
   - **degraded**: health_status="degraded". Monitor and plan maintenance.
   - **healthy**: health_status="healthy". No action needed.

3. **Issue summary**: for critical and degraded devices, name the problem. "Low health score (25/100)", "High failure risk (probability 0.85)", "Connectivity issues detected in last 48 hours". Use the tool output, not speculation.

4. **Anomalies**: list any associated anomalies from `detect_anomalies` for each device. If there are none, leave the array empty.

5. **Fleet summary**: tally the counts and compute the average score from the fleet-level `get_device_health` call.

6. **Empty fleet path**: if `get_device_health` returns total=0, return empty arrays for all three status buckets and fleet_summary with all counts at 0. No error, no padding.

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