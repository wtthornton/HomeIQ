# Entity Safety Blacklist — Epic 93

## Overview

HomeIQ implements defence-in-depth entity safety to prevent the AI from
creating automations that control security-sensitive devices (locks, alarms).

**Two enforcement layers:**

1. **Context filtering** — blocked entities are removed from the LLM context
   so it cannot reference them in generated YAML.
2. **Validation rejection** — if a blocked entity or service appears in YAML
   (e.g. via prompt injection or hallucination), the yaml-validation-service
   Stage 5 rejects the automation with `valid: false`.

## What's Blocked

| Domain | Examples | Behaviour |
|--------|----------|-----------|
| `lock` | `lock.front_door` | **Blocked** — hidden from AI, rejected in validation |
| `alarm_control_panel` | `alarm_control_panel.home` | **Blocked** — hidden from AI, rejected in validation |
| `cover` | `cover.garage_door` | **Warning** — visible with safety annotation |
| `siren` | `siren.alarm` | **Warning** — visible with safety annotation |
| `valve` | `valve.main_water` | **Warning** — visible with safety annotation |

Blocked services: `lock.lock`, `lock.unlock`, `alarm_control_panel.alarm_arm_away`,
`alarm_control_panel.alarm_arm_home`, `alarm_control_panel.alarm_disarm`.

## Configuration

The blacklist is defined in YAML:

```
ha-ai-agent-service/src/config/entity_blacklist.yaml
yaml-validation-service/src/yaml_validation_service/entity_blacklist.yaml
```

Both files must stay in sync. Edit the ha-ai-agent-service copy as the
source of truth and copy to yaml-validation-service.

### Config Format

```yaml
blocked_domains:
  - lock
  - alarm_control_panel

blocked_entities:
  - cover.garage_door        # block specific entities

blocked_services:
  - lock.lock
  - lock.unlock

warn_domains:
  - cover
  - siren
  - valve
```

## Admin Override

For power users who understand the risk:

### Environment Variable

Set on `ha-ai-agent-service`:

```bash
ENTITY_BLACKLIST_OVERRIDE=lock,alarm_control_panel
```

This unblocks the specified domains from context filtering.

### HTTP Header

Send to yaml-validation-service:

```
X-Safety-Override: true
```

This converts validation errors to warnings for blocked entities.

### Docker Compose

```yaml
services:
  ha-ai-agent-service:
    environment:
      - ENTITY_BLACKLIST_OVERRIDE=lock  # Unblock lock domain
```

## Security Implications of Override

- Override is intended for advanced users managing their own HA installation
- Override only affects HomeIQ's AI pipeline — it does not change Home
  Assistant's own access controls
- When override is active, the system logs a warning at startup
- Recommendation: use override sparingly and only when you need AI-generated
  lock/alarm automations

## Examples

### Blocked Request

**User:** "Unlock the front door when I leave"
**AI response:** "For security reasons, lock and alarm automations must be
created directly in Home Assistant. I can help you with lighting, climate,
sensor, and other non-security automations."

### Allowed Request

**User:** "Turn on the office lights when motion is detected"
**AI:** Generates valid YAML with `light.turn_on` + motion triggers.

### Warning Request

**User:** "Open the garage door at 7 AM"
**AI:** Generates YAML with `cover.open_cover` but includes a safety warning
in the preview response.
