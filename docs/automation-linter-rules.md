# Automation Linter Rules Catalog

**Ruleset Version:** 2026.02.1
**Last Updated:** 2026-02-03
**Total Rules:** 15 (MVP)

---

## Overview

This document catalogs all lint rules implemented in the HomeIQ Automation Linter. Each rule helps ensure your Home Assistant automations are correct, maintainable, and follow best practices.

### Rule Format

Each rule entry includes:

| Field | Description |
|-------|-------------|
| **Rule ID** | Unique identifier (never changes after publication) |
| **Name** | Human-readable rule name |
| **Severity** | `error` \| `warn` \| `info` |
| **Category** | `syntax` \| `schema` \| `logic` \| `reliability` \| `maintainability` |
| **Auto-fixable** | Whether safe auto-fix is available |
| **Description** | What this rule checks |
| **Why It Matters** | Impact of violating this rule |
| **Examples** | Valid and invalid examples |

### Severity Levels

- **Error** (`error`): Must be fixed - automation will not work or will cause errors
- **Warning** (`warn`): Should be fixed - may cause unexpected behavior
- **Info** (`info`): Consider fixing - improves maintainability

### Categories

- **Syntax**: YAML syntax and structure
- **Schema**: Required keys and valid formats
- **Logic**: Potential logic errors or issues
- **Reliability**: Issues that may cause runtime failures
- **Maintainability**: Code quality and documentation

---

## Schema Rules

### SCHEMA001 - Missing Trigger

**Severity:** `error`
**Category:** `schema`
**Auto-fixable:** No

**Description:**
Checks that every automation has at least one trigger defined.

**Why It Matters:**
Automations without triggers will never execute. Home Assistant requires at least one trigger to activate an automation.

**Examples:**

❌ **Invalid:**
```yaml
alias: "Broken automation"
action:
  - service: light.turn_on
    target:
      entity_id: light.living_room
```

✅ **Valid:**
```yaml
alias: "Working automation"
trigger:
  - platform: state
    entity_id: sensor.temperature
    above: 25
action:
  - service: light.turn_on
    target:
      entity_id: light.living_room
```

---

### SCHEMA002 - Missing Action

**Severity:** `error`
**Category:** `schema`
**Auto-fixable:** No

**Description:**
Checks that every automation has at least one action defined.

**Why It Matters:**
Automations without actions do nothing when triggered. They waste resources and indicate incomplete configuration.

**Examples:**

❌ **Invalid:**
```yaml
alias: "Does nothing"
trigger:
  - platform: state
    entity_id: binary_sensor.motion
    to: "on"
```

✅ **Valid:**
```yaml
alias: "Motion light"
trigger:
  - platform: state
    entity_id: binary_sensor.motion
    to: "on"
action:
  - service: light.turn_on
    target:
      entity_id: light.hallway
```

---

### SCHEMA003 - Unknown Top-Level Keys

**Severity:** `warn`
**Category:** `schema`
**Auto-fixable:** No

**Description:**
Detects top-level keys that are not recognized by Home Assistant automation schema.

**Why It Matters:**
Unknown keys may indicate typos, deprecated configuration, or misunderstanding of the automation format. They are silently ignored by Home Assistant, which can hide configuration errors.

**Known Keys:**
`id`, `alias`, `description`, `trigger`, `condition`, `action`, `mode`, `max`, `max_exceeded`, `variables`, `trace`, `initial_state`

**Examples:**

⚠️ **Warning:**
```yaml
alias: "Typo in key"
triggers:  # Should be "trigger" (no 's')
  - platform: state
    entity_id: sensor.test
action:
  - service: light.turn_on
extra_key: "This is ignored"  # Unknown key
```

✅ **Valid:**
```yaml
alias: "Correct keys"
trigger:
  - platform: state
    entity_id: sensor.test
action:
  - service: light.turn_on
    target:
      entity_id: light.test
```

---

### SCHEMA004 - Duplicate Automation ID

**Severity:** `error`
**Category:** `schema`
**Auto-fixable:** No

**Description:**
Detects when multiple automations in a list have the same `id`.

**Why It Matters:**
Automation IDs must be unique. Duplicate IDs can cause conflicts in Home Assistant's internal tracking, UI display issues, and problems with automation toggles.

**Examples:**

❌ **Invalid:**
```yaml
- alias: "First automation"
  id: "my_automation"
  trigger:
    - platform: state
      entity_id: sensor.temp
  action:
    - service: climate.set_temperature

- alias: "Second automation"
  id: "my_automation"  # Duplicate!
  trigger:
    - platform: time
      at: "09:00:00"
  action:
    - service: light.turn_on
```

✅ **Valid:**
```yaml
- alias: "First automation"
  id: "temp_automation"
  trigger:
    - platform: state
      entity_id: sensor.temp
  action:
    - service: climate.set_temperature

- alias: "Second automation"
  id: "morning_light"
  trigger:
    - platform: time
      at: "09:00:00"
  action:
    - service: light.turn_on
```

---

### SCHEMA005 - Invalid Service Format

**Severity:** `error`
**Category:** `schema`
**Auto-fixable:** No

**Description:**
Checks that service calls use the correct `domain.service` format.

**Why It Matters:**
Services must be in `domain.service` format to be recognized by Home Assistant. Invalid formats will cause the action to fail.

**Examples:**

❌ **Invalid:**
```yaml
alias: "Wrong service format"
trigger:
  - platform: state
    entity_id: binary_sensor.door
action:
  - service: turn_on  # Missing domain
    target:
      entity_id: light.hallway
```

✅ **Valid:**
```yaml
alias: "Correct service format"
trigger:
  - platform: state
    entity_id: binary_sensor.door
    to: "open"
action:
  - service: light.turn_on  # Correct: domain.service
    target:
      entity_id: light.hallway
```

---

## Syntax Rules

### SYNTAX001 - Trigger Missing Platform

**Severity:** `error`
**Category:** `syntax`
**Auto-fixable:** No

**Description:**
Checks that every trigger has a `platform` key specified.

**Why It Matters:**
Every trigger must specify a platform (state, time, event, etc.) to tell Home Assistant what type of trigger it is.

**Examples:**

❌ **Invalid:**
```yaml
alias: "Missing platform"
trigger:
  - entity_id: sensor.temperature  # No platform!
    above: 25
action:
  - service: fan.turn_on
```

✅ **Valid:**
```yaml
alias: "With platform"
trigger:
  - platform: numeric_state  # Platform specified
    entity_id: sensor.temperature
    above: 25
action:
  - service: fan.turn_on
    target:
      entity_id: fan.bedroom
```

---

## Logic Rules

### LOGIC001 - Delay with Single Mode

**Severity:** `warn`
**Category:** `logic`
**Auto-fixable:** No (requires user decision)

**Description:**
Detects automations using `delay` with `mode: single`, which may cause dropped triggers.

**Why It Matters:**
When an automation with `mode: single` and a delay is triggered while already running, the new trigger is ignored. This can lead to unexpected behavior like lights not turning on when motion is detected multiple times.

**Recommendation:**
Consider using `mode: restart`, `mode: queued`, or `mode: parallel` depending on your use case.

**Examples:**

⚠️ **Potentially Problematic:**
```yaml
alias: "May drop triggers"
mode: single  # Default mode
trigger:
  - platform: state
    entity_id: binary_sensor.motion
    to: "on"
action:
  - service: light.turn_on
    target:
      entity_id: light.hallway
  - delay: "00:05:00"  # Long delay with single mode
  - service: light.turn_off
    target:
      entity_id: light.hallway
```

✅ **Better Approach:**
```yaml
alias: "Won't drop triggers"
mode: restart  # Restarts on new trigger
trigger:
  - platform: state
    entity_id: binary_sensor.motion
    to: "on"
action:
  - service: light.turn_on
    target:
      entity_id: light.hallway
  - delay: "00:05:00"
  - service: light.turn_off
    target:
      entity_id: light.hallway
```

**Mode Options:**
- `single`: Only one run at a time (default)
- `restart`: Stop and restart on new trigger
- `queued`: Queue new runs
- `parallel`: Run multiple instances simultaneously

---

### LOGIC002 - High-Frequency Trigger Without Debounce

**Severity:** `warn`
**Category:** `logic`
**Auto-fixable:** No

**Description:**
Detects state triggers that can fire very frequently without a `for:` duration to debounce.

**Why It Matters:**
State triggers fire every time the entity state changes, which can be very frequent for sensors like power consumption or temperature. Without debouncing, you may trigger hundreds of times per minute.

**Recommendation:**
Add `for: HH:MM:SS` or `for: { seconds: N }` to require the state to be stable before triggering.

**Examples:**

⚠️ **High Frequency:**
```yaml
alias: "Fires on every state change"
trigger:
  - platform: state
    entity_id: sensor.power_consumption  # Updates every few seconds!
action:
  - service: notify.mobile_app
    data:
      message: "Power: {{ states('sensor.power_consumption') }}W"
```

✅ **With Debounce:**
```yaml
alias: "Fires only after stable for 30 seconds"
trigger:
  - platform: state
    entity_id: sensor.power_consumption
    for: "00:00:30"  # Debounce: wait 30 seconds
action:
  - service: notify.mobile_app
    data:
      message: "Power stable at {{ states('sensor.power_consumption') }}W"
```

---

### LOGIC003 - Choose Without Default

**Severity:** `info`
**Category:** `logic`
**Auto-fixable:** No

**Description:**
Detects `choose` actions that don't have a `default` sequence.

**Why It Matters:**
Without a default, nothing happens if no conditions match. This may be intentional, but often it's better to have a fallback action or at least log the situation.

**Recommendation:**
Add a `default:` key with fallback actions, even if it's just logging.

**Examples:**

ℹ️ **No Default:**
```yaml
alias: "Weather-based blinds"
trigger:
  - platform: state
    entity_id: sensor.weather_condition
action:
  - choose:
      - conditions:
          - condition: state
            entity_id: sensor.weather_condition
            state: "sunny"
        sequence:
          - service: cover.open_cover
            target:
              entity_id: cover.living_room
      - conditions:
          - condition: state
            entity_id: sensor.weather_condition
            state: "rainy"
        sequence:
          - service: cover.close_cover
            target:
              entity_id: cover.living_room
  # No default - what if weather is "cloudy"?
```

✅ **With Default:**
```yaml
alias: "Weather-based blinds with fallback"
trigger:
  - platform: state
    entity_id: sensor.weather_condition
action:
  - choose:
      - conditions:
          - condition: state
            entity_id: sensor.weather_condition
            state: "sunny"
        sequence:
          - service: cover.set_cover_position
            target:
              entity_id: cover.living_room
            data:
              position: 100
      - conditions:
          - condition: state
            entity_id: sensor.weather_condition
            state: "rainy"
        sequence:
          - service: cover.close_cover
            target:
              entity_id: cover.living_room
    default:
      - service: cover.set_cover_position
        target:
          entity_id: cover.living_room
        data:
          position: 50  # Half-open for other weather
```

---

### LOGIC004 - Empty Trigger List

**Severity:** `error`
**Category:** `logic`
**Auto-fixable:** No

**Description:**
Checks for automations with an empty trigger list.

**Why It Matters:**
Automation will never execute without triggers. This is redundant with SCHEMA001 but provides an additional check.

---

### LOGIC005 - Empty Action List

**Severity:** `error`
**Category:** `logic`
**Auto-fixable:** No

**Description:**
Checks for automations with an empty action list.

**Why It Matters:**
Automation does nothing when triggered without actions. This is redundant with SCHEMA002 but provides an additional check.

---

## Reliability Rules

### RELIABILITY001 - Service Missing Target

**Severity:** `error`
**Category:** `reliability`
**Auto-fixable:** No

**Description:**
Checks that service calls have a target specified (entity_id, device_id, or area_id).

**Why It Matters:**
Most services require a target to know what to act on. Without a target, the service call will fail or have no effect.

**Exceptions:**
Some services don't require targets (e.g., `homeassistant.restart`, `persistent_notification.*`, `script.*`)

**Examples:**

❌ **Missing Target:**
```yaml
alias: "No target specified"
trigger:
  - platform: time
    at: "09:00:00"
action:
  - service: light.turn_on
    data:
      brightness_pct: 75  # But which light?
```

✅ **With Target:**
```yaml
alias: "Target specified"
trigger:
  - platform: time
    at: "09:00:00"
action:
  - service: light.turn_on
    target:
      entity_id: light.living_room
    data:
      brightness_pct: 75
```

✅ **Using Area:**
```yaml
alias: "Area target"
trigger:
  - platform: time
    at: "09:00:00"
action:
  - service: light.turn_on
    target:
      area_id: living_room
    data:
      brightness_pct: 75
```

---

### RELIABILITY002 - Invalid Entity ID Format

**Severity:** `warn`
**Category:** `reliability`
**Auto-fixable:** No

**Description:**
Checks that entity IDs follow the correct format: `domain.object_id` (lowercase, underscores only).

**Why It Matters:**
Entity IDs should be in format `domain.object_id` (lowercase with underscores). Invalid formats may not match entities or cause lookup failures.

**Valid Format:**
- Lowercase letters (a-z)
- Numbers (0-9)
- Underscores (_)
- Must contain one dot (.) separating domain and object_id

**Templates Allowed:**
Templates (containing `{{` or `{%`) are allowed and not checked.

**Examples:**

⚠️ **Invalid Format:**
```yaml
alias: "Bad entity IDs"
trigger:
  - platform: state
    entity_id: Binary_Sensor.Motion-Detector  # Capitals and hyphens!
    to: "on"
action:
  - service: light.turn_on
    target:
      entity_id: Light.Living-Room  # Should be light.living_room
```

✅ **Valid Format:**
```yaml
alias: "Correct entity IDs"
trigger:
  - platform: state
    entity_id: binary_sensor.motion_detector  # Lowercase, underscore
    to: "on"
action:
  - service: light.turn_on
    target:
      entity_id: light.living_room  # Correct format
```

✅ **Template (Allowed):**
```yaml
alias: "Dynamic entity ID"
trigger:
  - platform: state
    entity_id: binary_sensor.motion
    to: "on"
action:
  - service: light.turn_on
    target:
      entity_id: "{{ trigger.entity_id | replace('binary_sensor', 'light') }}"
```

---

## Maintainability Rules

### MAINTAINABILITY001 - Missing Description

**Severity:** `info`
**Category:** `maintainability`
**Auto-fixable:** Yes (safe mode)

**Description:**
Checks for automations without a `description` field.

**Why It Matters:**
Descriptions help document the purpose of automations for future maintenance. When you (or someone else) comes back to this automation in 6 months, a clear description explains what it does and why.

**Auto-fix:**
Adds an empty `description: ""` field that you can fill in manually.

**Examples:**

ℹ️ **Missing Description:**
```yaml
alias: "Garage alert"
id: "garage_door_alert"
trigger:
  - platform: state
    entity_id: binary_sensor.garage_door
    to: "open"
    for: "00:10:00"
action:
  - service: notify.mobile_app
    data:
      message: "Garage door open for 10 minutes"
```

✅ **With Description:**
```yaml
alias: "Garage alert"
description: "Send notification if garage door is left open for more than 10 minutes to prevent security issues and energy loss"
id: "garage_door_alert"
trigger:
  - platform: state
    entity_id: binary_sensor.garage_door
    to: "open"
    for: "00:10:00"
action:
  - service: notify.mobile_app
    data:
      message: "Garage door open for 10 minutes"
```

---

### MAINTAINABILITY002 - Missing Alias

**Severity:** `info`
**Category:** `maintainability`
**Auto-fixable:** Yes (safe mode)

**Description:**
Checks for automations without an `alias` field.

**Why It Matters:**
Aliases provide a friendly name for automations in the Home Assistant UI. Without an alias, automations show their ID or "Unnamed Automation" which makes them hard to identify.

**Auto-fix:**
Adds an empty `alias: ""` field that you can fill in manually.

**Examples:**

ℹ️ **Missing Alias:**
```yaml
description: "Low battery notification"
id: "battery_alert"
trigger:
  - platform: numeric_state
    entity_id: sensor.phone_battery
    below: 20
action:
  - service: notify.mobile_app
    data:
      message: "Phone battery low: {{ states('sensor.phone_battery') }}%"
```

✅ **With Alias:**
```yaml
alias: "Low Battery Alert"  # Shows in UI
description: "Low battery notification"
id: "battery_alert"
trigger:
  - platform: numeric_state
    entity_id: sensor.phone_battery
    below: 20
action:
  - service: notify.mobile_app
    data:
      message: "Phone battery low: {{ states('sensor.phone_battery') }}%"
```

---

## Rule Categories

### Syntax
Rules that check YAML syntax and basic structure. These are critical errors that prevent the automation from being parsed.

**Rules:** SYNTAX001

### Schema
Rules that validate automation schema - required keys, valid formats, and Home Assistant-specific requirements.

**Rules:** SCHEMA001, SCHEMA002, SCHEMA003, SCHEMA004, SCHEMA005

### Logic
Rules that detect potential logic errors, unexpected behavior, or inefficient patterns.

**Rules:** LOGIC001, LOGIC002, LOGIC003, LOGIC004, LOGIC005

### Reliability
Rules that improve automation reliability and prevent runtime failures.

**Rules:** RELIABILITY001, RELIABILITY002

### Maintainability
Rules that improve code quality, documentation, and long-term maintainability.

**Rules:** MAINTAINABILITY001, MAINTAINABILITY002

---

## Disabling Rules

Currently, rules can only be disabled by the service administrator via engine configuration. User-level rule configuration is planned for Phase 1.

**Service-Level Configuration:**

```python
from ha_automation_lint import LintEngine

# Disable specific rules
engine = LintEngine(rule_config={
    "MAINTAINABILITY001": False,  # Disable missing description rule
    "MAINTAINABILITY002": False,  # Disable missing alias rule
})
```

**Future (Phase 1):**
User-level configuration via API or config file.

---

## Rule Versioning

Rules are versioned via the `RULESET_VERSION` constant. When rules are added, removed, or significantly changed, the ruleset version is incremented.

**Version Format:** `YYYY.MM.PATCH`

**Current Version:** `2026.02.1`

### Version History

- **2026.02.1** (MVP): Initial release with 15 rules
  - 5 Schema rules
  - 1 Syntax rule
  - 5 Logic rules
  - 2 Reliability rules
  - 2 Maintainability rules

### Stability Guarantee

For a given `RULESET_VERSION`, outputs are stable:
- Same input → same findings
- Same fix mode → same fixed YAML
- Rule IDs never change after publication

When upgrading ruleset versions:
- Existing rule IDs remain stable
- New rules are added with new IDs
- Deprecated rules are marked but not removed
- Breaking changes increment major version (YYYY.MM → YYYY.(MM+1))

---

## Contributing Rules

Want to propose a new rule? Follow these guidelines:

### Rule Proposal Template

```markdown
## Proposed Rule: [NAME]

**Rule ID:** [CATEGORY###]
**Severity:** [error|warn|info]
**Category:** [syntax|schema|logic|reliability|maintainability]

**Description:**
[What does this rule check?]

**Why It Matters:**
[Why is this important? What problems does it prevent?]

**Examples:**
[Provide valid and invalid examples]

**Auto-fixable:**
[Can this be safely auto-fixed? If yes, how?]

**False Positives:**
[Are there cases where this rule might incorrectly trigger?]
```

### Submission Process

1. Create an issue with the rule proposal
2. Gather feedback from the community
3. Implement the rule following the code patterns
4. Add test cases (valid, invalid, edge)
5. Update documentation
6. Submit pull request

---

## See Also

- **[Service Documentation](./automation-linter.md)** - API reference and usage guide
- **[Implementation Plan](./implementation/automation-linter-implementation-plan.md)** - Technical details
- **[Test Corpus](../simulation/automation-linter/README.md)** - Example automations

---

**Last Updated:** 2026-02-03
**Ruleset Version:** 2026.02.1
**Maintainer:** HomeIQ Team
