---
name: automation-safety-rules
description: Hard-deny list for unsafe automation patterns (lock unlocking, alarm disarming, safety detector disablement, away-mode access opening, safety automation self-modification). Everything outside the deny list is annotate-only risk scoring.
version: 1.0.0
allowed_tools: ""
---
# Automation Safety Rules — Hard-Deny List and Risk Annotation

A gene that drafts or judges home automation YAML receives this skill to determine whether an automation is allowed, unsafe-but-passable-with-annotation, or forbidden.

## Deny List Structure

The authoritative deny list is in `deny.yaml` (same directory). It contains 6 rule IDs (`SAFETY001`–`SAFETY006`):

1. **SAFETY001**: Lock unlocking — hard-deny
2. **SAFETY002**: Alarm/security system disarming — hard-deny
3. **SAFETY003**: Smoke/CO detector disablement — hard-deny
4. **SAFETY004**: Safety automation self-modification — hard-deny
5. **SAFETY005**: Garage door/gate opening while home is away — hard-deny
6. **SAFETY006**: Autonomous lock control without explicit approval — hard-deny

See `deny.yaml` for the exact matchers, descriptions, and rationale for each rule.

## Validation Behavior

### Hard-Deny Path (Blocked)

When an automation matches **any** rule in the deny list:

1. Validation fails.
2. Error message includes the matching `rule_id` and rationale.
3. Automation is logged to the safety audit trail.
4. **Human escalation required** — the automation cannot be executed without explicit human override and sign-off.

Example validation failure:
```
SAFETY001: Lock unlocking — always requires human confirmation
Reason: Physical access control. Unlocking remotely without verification of the intent actor creates liability.
Status: BLOCKED — escalate to human approval
```

### Annotate-Only Path (Allowed with Annotation)

When an automation is **outside** the deny list:

1. Validation passes.
2. The automation is scanned for common risk patterns (high power draw, frequently-triggered, modifying climate/security settings).
3. A risk label (`low`, `medium`, or `high`) is assigned with a one-line reason.
4. The label and reason are included in the validation report but do NOT block execution.

Example annotation:
```
Risk: medium — affects climate system (thermostat change 3x per day).
Reason: Frequent thermostat adjustments may indicate tuning loop; monitor for oscillation.
```

## Judge Integration

The hiq-judge-automation gene or hiq-draft-automation gene requests this skill as input (along with the YAML under review) and uses the deny list to:

1. **Block** if the automation matches a deny rule.
2. **Annotate** if it does not, with risk assessment for human context.
3. Never override the deny list — the skill is the source of truth.

## Versioning and Updates

- **Version** is in the frontmatter (currently 1.0.0).
- **Deny rules are never deleted**, only added. Existing `rule_id` values are permanent.
- When a new safety risk is identified (e.g., a vulnerability or reported incident), TAP-5319 owner adds a new rule to `deny.yaml` and increments the version.
- Agents always fetch the latest version from the repository at the start of an ingest session.

## Related Skills

- `ha-yaml-rules`: YAML schema and linter rules (orthogonal to safety; both are applied).
- `energy-truth`: Metric definitions for risk annotation (e.g., "power draw anomaly").
- `home-atlas`: Home structure (e.g., for matching "away_mode" presence state).
