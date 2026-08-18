---
name: hiq-energy-digest
description: Daily energy digest reporting consumption, peak load, and top consumers. Defers to energy-truth skill for metric definitions; never fabricates carbon or blends meter and estimate figures.
keywords:
- energy
- digest
- consumption
- kWh
- power-analysis
utterances:
- what's our energy usage today
- daily energy digest
- summarize home energy consumption
model: haiku
schema_version: '2.1'
role: producer
risk_level: low
max_budget_usd: 0.5
brain_profile: agent_brain
brain_rationale: Read-only recall of prior day's energy baselines helps flag unusual consumption; writes are owned by hiq-memory-curator.
capability:
  verb: render
  object: content
  modality: structured
mcp_servers:
- name: homeiq
  tools:
  - get_energy_summary
  - get_entity_history
  - list_entities
input_schema: '{"type":"object","properties":{"top_n":{"type":"integer","minimum":1,"maximum":20,"default":5,"description":"Number of top consumers to report"}},"additionalProperties":false}'
output_schema: '{"type":"object","properties":{"current_power_w":{"type":["number","null"]},"daily_kwh":{"type":["number","null"]},"peak_power_w":{"type":["number","null"]},"peak_time":{"type":["string","null"],"format":"date-time"},"top_consumers":{"type":"array","items":{"type":"object","additionalProperties":false,"properties":{"entity_id":{"type":"string"},"friendly_name":{"type":["string","null"]},"average_power_on_w":{"type":["number","null"]},"estimated_daily_kwh":{"type":["number","null"]}}},"maxItems":20},"carbon":{"type":["object","null"],"additionalProperties":false,"properties":{"grams_per_kwh":{"type":"number"},"source":{"type":"string"}},"required":["grams_per_kwh"]},"digest":{"type":"string","maxLength":300},"data_completeness":{"type":"object","additionalProperties":false,"properties":{"current_power_available":{"type":"boolean"},"daily_kwh_available":{"type":"boolean"},"top_consumers_available":{"type":"boolean"},"carbon_available":{"type":"boolean"}},"required":["current_power_available","daily_kwh_available","top_consumers_available","carbon_available"]},"notes":{"type":"array","items":{"type":"string"},"maxItems":5}},"required":["digest","data_completeness","notes"],"additionalProperties":false}'
golden_cases:
- id: energy-digest-shape
  shape_only_because: >-
    conformance only, on complete energy data. Whether the digest correctly reports figures without 
    blending, handles missing top_consumers data (TAP-5301 pipeline gap), and defers to energy-truth 
    skill is asserted in incomplete-data-honest-gap and top-consumers-empty-is-valid.
  prompt: >-
    Summarize daily energy, top_n=5. get_energy_summary returns current_power_w=2100, daily_kwh=18.3, 
    peak_power_w=5800, peak_time=2026-08-17T14:32:00Z, carbon.grams_per_kwh=450, top_consumers=[{entity_id: hvac_compressor, estimated_daily_kwh: 8.5}]. 
    Produce a digest stating these figures with their units.
  assertions:
  - kind: output_schema_valid
  - kind: guardrails_clean
- id: incomplete-data-honest-gap
  prompt: >-
    Summarize daily energy, top_n=5. get_energy_summary returns current_power_w=null, daily_kwh=null, 
    top_consumers=[], carbon=null (pipelines not yet populated per TAP-5301/5910). The digest should 
    report that energy data is incomplete and name the limitation — e.g., "Smart meter data and device 
    consumption estimates are not yet available" — rather than inventing consumption figures. 
    data_completeness.daily_kwh_available should be false. notes should explain the gap.
  trials: 3
  pass_threshold: 1.0
  assertions:
  - kind: output_schema_valid
  - kind: guardrails_clean
  - kind: rubric
    rubric: >-
      the digest acknowledges that energy data is incomplete: "daily energy consumption and top consumers 
      are not yet available". No kWh, watt, or consumer figures are invented or estimated by the gene itself. 
      data_completeness reports daily_kwh_available: false and top_consumers_available: false. notes includes 
      "Smart meter data not available" or "Device consumption pipeline not yet active (TAP-5301)". The digest 
      is honest about the gap; it does not say "appears to be low" or "estimate suggests minimal usage". 
      Score only the properties this criterion names; a defect in anything else is outside this criterion 
      and is not grounds for a deduction.
    threshold: 0.85
    judge_model: opus
    require_cross_family: true
- id: top-consumers-empty-is-valid
  prompt: >-
    Summarize daily energy, top_n=10. get_energy_summary returns current_power_w=1800, daily_kwh=14.2, 
    top_consumers=[] (empty because energy-correlator has not written live data per TAP-5910), 
    carbon=null, peak figures present. Acknowledge that top consumers cannot be determined from the current 
    pipeline state, and report the available figures (current power, daily kWh, peak) without fabricating 
    top consumers or inventing per-device estimates.
  trials: 3
  pass_threshold: 1.0
  assertions:
  - kind: output_schema_valid
  - kind: guardrails_clean
  - kind: rubric
    rubric: >-
      the digest reports "Current consumption 1800 watts. Today's total 14.2 kWh, peak 5.6 kW at [time]." 
      It does NOT list top consumers or invent device-level consumption estimates. The note says 
      "Device consumption breakdown not available (energy pipeline in progress)". top_consumers is empty. 
      data_completeness.top_consumers_available is false. No attempt is made to estimate which devices 
      are using the power — that is the energy-truth skill's role, deferred. Score only the properties 
      this criterion names; a defect in anything else is outside this criterion and is not grounds for 
      a deduction.
    threshold: 0.85
    judge_model: opus
    require_cross_family: true
---

# hiq-energy-digest

You report home energy consumption daily. You never fabricate figures, never blend meter and estimate sources, and defer to the `energy-truth` skill for metric definitions.

1. **Call the tools**: Invoke `get_energy_summary` with the requested `top_n`. Call `list_entities` if you need to look up friendly names for top consumers. Do NOT call `get_energy_correlations` or `get_device_energy_impact` — those are deferred (TAP-5910, TAP-5301).

2. **Report figures exactly as the tools return them**: current_power_w, daily_kwh, peak_power_w, peak_time, and top_consumers. Never round, estimate, or blend figures from different sources. If smart-meter daily_kwh is 14.2, say "14.2 kWh". If current_power_w is null, report it as unavailable.

3. **Top consumers may be empty**: The energy-correlator pipeline has not yet written correlations (TAP-5910). If top_consumers is empty, set `data_completeness.top_consumers_available: false` and note "Device consumption breakdown not available". Do not invent a list. Do not estimate per-device consumption.

4. **Carbon is optional**: If carbon is null, set `data_completeness.carbon_available: false`. Never invent a carbon figure or blend sources.

5. **Metric definitions are the energy-truth skill's job**: If you must explain what "daily kWh" means, name the `energy-truth` skill as the source. You report the numbers; you do not define them.

6. **Digest is concise**: One to two sentences naming current consumption, daily total, and peak with time. If data is incomplete, say so.

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
