---
name: hiq-pattern-summary
description: Digests detected behavioral patterns and cross-device synergies into
  a summary for the home owner, naming high-confidence patterns and suggested automations.
keywords:
- pattern
- summary
- behavior
- digest
- automation-opportunity
utterances:
- summarize detected home patterns
- what automation opportunities exist
- digest behavior patterns
model: sonnet
schema_version: '2.1'
role: producer
risk_level: low
max_budget_usd: 0.5
brain_profile: agent_brain
brain_rationale: Read-only recall of prior pattern summaries prevents re-digesting
  the same patterns; writes are owned by hiq-memory-curator.
capability:
  verb: render
  object: content
  modality: structured
mcp_servers:
- name: homeiq
  tools:
  - list_patterns
  - list_synergies
  - list_devices
  - list_areas
input_schema: '{"type":"object","properties":{"min_pattern_confidence":{"type":"number","minimum":0,"maximum":1,"default":0.7,"description":"Filter
  patterns below this confidence"},"min_synergy_confidence":{"type":"number","minimum":0,"maximum":1,"default":0.6,"description":"Filter
  synergies below this confidence"}},"additionalProperties":false}'
output_schema: '{"type":"object","properties":{"patterns_found":{"type":"array","items":{"type":"object","additionalProperties":false,"properties":{"pattern_type":{"type":"string"},"summary":{"type":"string","maxLength":200},"confidence":{"type":"number"},"occurrences":{"type":"integer"},"devices_involved":{"type":"array","items":{"type":"string"},"maxItems":10}}},"maxItems":30},"synergies_found":{"type":"array","items":{"type":"object","additionalProperties":false,"properties":{"synergy_type":{"type":"string"},"explanation":{"type":"string","maxLength":200},"confidence":{"type":"number"},"devices":{"type":"array","items":{"type":"string"},"maxItems":10},"area":{"type":["string","null"]}}},"maxItems":20},"digest":{"type":"string","maxLength":500},"recommendations":{"type":"array","items":{"type":"string"},"maxItems":5},"stats":{"type":"object","additionalProperties":false,"properties":{"total_patterns":{"type":"integer"},"total_synergies":{"type":"integer"},"device_count":{"type":"integer"},"area_count":{"type":"integer"}},"required":["total_patterns","total_synergies"]},"errors":{"type":"array","items":{"type":"string"}}},"required":["patterns_found","synergies_found","digest","stats","errors"],"additionalProperties":false}'
golden_cases:
- id: pattern-summary-shape
  shape_only_because: conformance only, on patterns and synergies with confidence
    > threshold. Whether the digest  correctly captures the essence of patterns and
    synergies (vs. fabricating patterns the tools  did not return) is asserted in
    patterns-stay-faithful-to-tools and empty-patterns-produce-empty-digest.
  prompt: 'Summarize patterns min_pattern_confidence=0.7, min_synergy_confidence=0.6.
    list_patterns returns  [{"pattern_type": "morning_routine", "confidence": 0.85,
    "occurrences": 12, "summary": "Lights on 6:30 AM, HVAC 68F, coffee maker starts"}].  list_synergies
    returns [{"synergy_type": "lighting_comfort", "confidence": 0.75, "devices": ["bedroom_light",
    "hallway_light", "office_light"], "explanation": "Lights are often on together"}].  Call
    the tools and digest these findings.'
  assertions:
  - kind: output_schema_valid
  - kind: guardrails_clean
- id: patterns-stay-faithful-to-tools
  prompt: 'Summarize patterns min_pattern_confidence=0.7. list_patterns returns [{"pattern_type":
    "evening_shutdown", "confidence": 0.82, "occurrences": 9, "summary": "Lights off,
    HVAC to night mode, bedroom blinds close at 22:00"}].  list_devices returns [{"device_id":
    "d1", "name": "bedroom_light"}, {"device_id": "d2", "name": "living_room_light"}].  The
    digest should report the evening shutdown pattern as the tools state it — not
    invent additional devices or hours,  and not claim "routine at exactly 22:15"
    when the tools only said "at 22:00". Name devices returned by the tools only.'
  trials: 3
  pass_threshold: 1.0
  assertions:
  - kind: output_schema_valid
  - kind: guardrails_clean
  - kind: rubric
    rubric: the digest names the evening shutdown pattern at 22:00 exactly as list_patterns
      described it.  No additional devices, times, or inferred structure beyond what
      the tools returned is added.  The devices listed in patterns_found and synergies_found
      are either returned by the tools or  are null. No pattern is invented that list_patterns
      did not return. The recommendations  are grounded in the patterns — e.g., "automate
      the evening shutdown" — not speculative  ("you might benefit from motion sensors"
      when motion is not in any pattern). Score only the  properties this criterion
      names; a defect in anything else is outside this criterion and  is not grounds
      for a deduction.
    threshold: 0.85
    judge_model: opus
    require_cross_family: true
- id: empty-patterns-produce-empty-digest
  prompt: Summarize patterns min_pattern_confidence=0.7. list_patterns returns []
    (no patterns above threshold).  list_synergies returns [] (no synergies above
    threshold). Produce a digest that says no patterns were found,  not one that invents
    typical or expected behaviors. stats.total_patterns should be 0. recommendations
    should be empty.
  trials: 3
  pass_threshold: 1.0
  assertions:
  - kind: output_schema_valid
  - kind: guardrails_clean
  - kind: rubric
    rubric: patterns_found is empty, synergies_found is empty, and stats.total_patterns
      is 0. The digest  says there are no detected patterns above the confidence threshold
      — e.g., "No behavioral patterns  detected above the 0.7 confidence threshold."
      It does not invent typical patterns like "morning  routine" or suggest what
      patterns "usually" occur in homes. recommendations is empty. No error  is raised
      for the empty result. Score only the properties this criterion names; a defect
      in  anything else is outside this criterion and is not grounds for a deduction.
    threshold: 0.85
    judge_model: opus
    require_cross_family: true
---

# hiq-pattern-summary
You digest patterns and synergies into a narrative for the home owner. You stay faithful to what the tools return; you do not invent patterns.

1. **Call the tools**: Invoke `list_patterns` with the requested `min_pattern_confidence`. Invoke `list_synergies` with `min_synergy_confidence`. Call `list_devices` and `list_areas` to populate device names if needed for context.

2. **Patterns and synergies are filtered**: Return only patterns and synergies above the confidence thresholds. If all fall below, return empty arrays and report "no patterns detected above threshold".

3. **Digest is a narrative**: Write a one-to-three-sentence digest of what the home's behavioral patterns are. Name the strongest pattern and one synergy if any exist. Do not invent patterns that the tools did not return.

4. **Recommendations are conservative**: suggest automations only when a pattern is clear and high-confidence (≥0.8). Never suggest something the tool output does not support. "Automate the evening shutdown" is valid if the tools named an evening shutdown pattern. "Add motion sensors to every room" is not, unless motion patterns were actually detected.

5. **Empty path**: if `list_patterns` and `list_synergies` both return empty, set `patterns_found: []`, `synergies_found: []`, `digest: "No behavioral patterns detected above threshold."`, and `recommendations: []`. Do not pad with typical patterns.

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