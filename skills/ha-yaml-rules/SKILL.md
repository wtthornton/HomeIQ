---
name: ha-yaml-rules
description: Home Assistant 2026.x automation YAML correctness rules — 15 linter rules covering schema, syntax, logic, reliability, and maintainability. Enables retiring the linter container. Source of truth is docs/automation-linter-rules.md.
version: 1.0.0
allowed_tools: ""
---
# Home Assistant Automation YAML Lint Rules

Home Assistant automation YAML must pass a suite of correctness checks. This skill catalogs the 15 rules that genes use to draft and judge automations. It is the authoritative rule set; `docs/automation-linter-rules.md` is the source.

## Rule Set (15 Rules)

### Schema Rules (5)

**SCHEMA001 — Missing Trigger**
- Severity: `error`
- Checks: Every automation has ≥ 1 trigger
- Impact: Automations without triggers never execute

**SCHEMA002 — Missing Action**
- Severity: `error`
- Checks: Every automation has ≥ 1 action
- Impact: Automations without actions do nothing

**SCHEMA003 — Unknown Top-Level Keys**
- Severity: `warn`
- Checks: Only valid keys: `id`, `alias`, `description`, `trigger`, `condition`, `action`, `mode`, `max`, `max_exceeded`, `variables`, `trace`, `initial_state`
- Impact: Unknown keys are silently ignored, hiding configuration errors

**SCHEMA004 — Duplicate Automation ID**
- Severity: `error`
- Checks: No two automations in the same file share an `id`
- Impact: Duplicate IDs cause tracking conflicts and UI issues

**SCHEMA005 — Invalid Service Format**
- Severity: `error`
- Checks: All service calls use `domain.service` format (e.g., `light.turn_on`)
- Impact: Invalid formats fail at runtime

### Syntax Rules (1)

**SYNTAX001 — Trigger Missing Platform**
- Severity: `error`
- Checks: Every trigger object has a `platform` key
- Impact: Triggers without platform don't execute

### Logic Rules (5)

**LOGIC001 — Delay with Single Mode**
- Severity: `warn`
- Checks: When `mode: single` is set, `action` does not contain long delays (> 5 minutes)
- Impact: Single mode queues subsequent triggers; long delays block the queue

**LOGIC002 — High-Frequency Trigger Without Debounce**
- Severity: `warn`
- Checks: Triggers firing > 10x/minute (e.g., state_changed on a sensor) have debounce conditions
- Impact: Without debounce, automation executes excessively; can overload the system

**LOGIC003 — Choose Without Default**
- Severity: `warn`
- Checks: If `action` contains a `choose` block, it has a `default` clause
- Impact: Without default, some paths produce no action (silent failures)

**LOGIC004 — Empty Trigger List**
- Severity: `error`
- Checks: The `trigger` list is not empty (has ≥ 1 element)
- Impact: Same as SCHEMA001

**LOGIC005 — Empty Action List**
- Severity: `error`
- Checks: The `action` list is not empty (has ≥ 1 element)
- Impact: Same as SCHEMA002

### Reliability Rules (2)

**RELIABILITY001 — Service Missing Target**
- Severity: `warn`
- Checks: Service calls that require a `target` have one (e.g., `light.turn_on` needs `target.entity_id`)
- Impact: Service calls without target may fail silently or apply to wrong entities

**RELIABILITY002 — Invalid Entity ID Format**
- Severity: `error`
- Checks: All entity IDs match `domain.entity_slug` (lowercase, underscores only)
- Impact: Invalid entity IDs don't resolve; automation skips the action

### Maintainability Rules (2)

**MAINTAINABILITY001 — Missing Description**
- Severity: `info`
- Checks: Automation has a `description` field (optional but recommended)
- Impact: No field makes the automation's purpose unclear to operators

**MAINTAINABILITY002 — Missing Alias**
- Severity: `info`
- Checks: Automation has an `alias` field (human-readable name)
- Impact: Without alias, HA dashboard shows the automation ID, confusing users

## Application Rules

1. **All schema and syntax rules are mandatory** — violations must be fixed before automation can execute.
2. **Logic and reliability warnings should be heeded** — a draft gene assigns high risk to violations; a judge may require revision.
3. **Maintainability info is advisory** — automations without descriptions/aliases pass validation but receive an `info` note.
4. **Auto-fix available** — some rules (typos, missing keys, invalid IDs) can be auto-fixed; others require human judgment.

## Integration with Genes

- **hiq-draft-automation**: Uses these rules to guide YAML generation. Avoids creating automations that violate schema, syntax, or logic rules.
- **hiq-judge-automation**: Runs the full rule set against user-provided YAML. Blocks on errors; warns on violations; notes on info-level findings.
- **hiq-explain-anomaly**: May reference these rules when explaining why an automation failed or behaved unexpectedly.

## Version History and Sync

- **Ruleset Version:** 2026.02.1
- **Last Updated:** 2026-02-03
- **Total Rules:** 15 (MVP)

This rule set is synchronized with `docs/automation-linter-rules.md`. When the documentation is updated, this skill's rule summary is regenerated to match. No manual sync is needed — both are authoritative to the source version.

## Deprecated Rules

None yet. Existing rule IDs are permanent once published. New risks trigger new rule additions, not replacements.
