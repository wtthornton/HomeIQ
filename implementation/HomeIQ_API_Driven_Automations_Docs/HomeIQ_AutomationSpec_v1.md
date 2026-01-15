# HomeIQ Automation Spec (v1): Schema + Examples

**Status:** Draft v1  
**Last updated:** 2026-01-15  
**Purpose:** Typed, versioned source of truth for automations executed via HomeIQ using Home Assistant APIs.

---

## 1. Design goals
- Declarative: represent *intent* and *constraints*.
- Typed: validate without HA YAML.
- Capability-driven: refer to capabilities, resolve to entities per home.
- Safe: explicit risk classification and policy gates.
- Observable: first-class correlation IDs and explanation hooks.

---

## 2. Core concepts

### 2.1 Capability
A stable function HomeIQ can perform in a home:
- `light.turn_on`
- `climate.set_temperature`
- `lock.lock`
- `notify.send`

Capabilities are mapped at runtime to HA domain/service + supported fields.

### 2.2 Targets
Targets are resolved at deploy-time or run-time:
- by `entity_id`
- by `area`
- by `device_class`
- by tags/labels (future)

### 2.3 Policy & risk
Each spec declares risk level and gating:
- `low`: may auto-run
- `medium`: may require extra checks
- `high`: requires confirmation and/or additional constraints

---

## 3. Examples

### 3.1 Motion lighting with quiet hours
```yaml
id: auto_lr_motion_evening
version: 1.0.0
name: Living room motion evening lights
enabled: true

triggers:
  - type: ha_event
    event_type: state_changed
    match:
      entity_id: binary_sensor.living_room_motion
      to: "on"

conditions:
  - type: after_sunset
  - type: not_in_time_range
    start: "22:30:00"
    end: "06:30:00"
  - type: not_manual_override
    scope: area:living_room
    ttl_seconds: 900

policy:
  risk: low
  allow_when_ha_unstable: false

actions:
  - id: act1
    capability: light.turn_on
    target:
      area: living_room
    data:
      brightness_pct: 35
      transition: 2
```

### 3.2 Leak safety shutdown (high risk)
```yaml
id: safety_leak_shutoff
version: 1.0.0
name: Leak detected - shut off water
enabled: true

triggers:
  - type: ha_event
    event_type: state_changed
    match:
      entity_id: binary_sensor.kitchen_leak
      to: "on"

policy:
  risk: high
  require_confirmations:
    - type: human_ack
      channel: mobile_push
      timeout_seconds: 120
  fallback_on_timeout: proceed

actions:
  - id: valve_off
    capability: valve.close
    target:
      entity_id: valve.main_water
    data: {}
  - id: notify
    capability: notify.send
    target:
      user: primary
    data:
      title: "Leak detected"
      message: "Main water valve closed. Check kitchen sensor."
```

---

## 4. Files shipped with this doc
- `HomeIQ_AutomationSpec_v1.schema.json` (machine-readable JSON Schema)
