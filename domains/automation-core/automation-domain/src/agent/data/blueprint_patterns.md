# Blueprint Patterns for Home Assistant

## Blueprint Selection Criteria

When suggesting blueprints, match based on:
1. **Device type** — the user's devices must match the blueprint's required domains
2. **Input requirements** — all required inputs must be satisfiable with available entities
3. **Category** — match the user's intent (lighting, climate, security, media, etc.)
4. **Complexity** — prefer simpler blueprints for users who haven't expressed advanced needs

## Blueprint Input Mapping

### Mapping User Entities to Blueprint Inputs
When a blueprint requires inputs, map user's available entities:

```yaml
# Blueprint defines inputs:
blueprint:
  name: Motion-Activated Light
  domain: automation
  input:
    motion_entity:
      name: Motion Sensor
      selector:
        entity:
          domain: binary_sensor
          device_class: motion
    light_target:
      name: Light
      selector:
        target:
          entity:
            domain: light
    no_motion_wait:
      name: Wait time (seconds)
      default: 120
      selector:
        number:
          min: 0
          max: 3600
          unit_of_measurement: seconds
```

### Applying a Blueprint
```yaml
# When deploying a blueprint automation:
alias: "Kitchen Motion Light"
use_blueprint:
  path: homeassistant/motion_light.yaml
  input:
    motion_entity: binary_sensor.kitchen_motion
    light_target:
      entity_id: light.kitchen_ceiling
    no_motion_wait: 180
```

## Common Blueprint Categories

### Lighting Blueprints
- **Motion-activated lights** — Requires: motion sensor (binary_sensor, device_class: motion), light entity
- **Adaptive lighting** — Requires: light entity, optional sun entity
- **Light scheduling** — Requires: light entity, time inputs
- **Scene activation** — Requires: scene entity, trigger entity

### Climate Blueprints
- **Thermostat scheduling** — Requires: climate entity, time inputs
- **Window-open detection** — Requires: window sensor (binary_sensor, device_class: window), climate entity
- **Temperature alerts** — Requires: temperature sensor, notification target

### Security Blueprints
- **Door/window alerts** — Requires: door/window sensor (binary_sensor, device_class: door/window), notification target
- **Presence-based alarm** — Requires: person entity, alarm_control_panel entity
- **Camera motion alerts** — Requires: camera entity, notification target

### Media Blueprints
- **Media player automation** — Requires: media_player entity, trigger entity
- **TTS announcements** — Requires: media_player entity (with TTS support)

### Energy Blueprints
- **Solar surplus actions** — Requires: solar power sensor, switch entities
- **EV charging schedules** — Requires: EV charger switch, time inputs

## Blueprint Validation Checklist

Before deploying a blueprint:
1. All required inputs have valid entity matches
2. Entity domains match the blueprint's selector requirements
3. Device classes match (e.g., `device_class: motion` for motion sensors)
4. Optional inputs have sensible defaults or user-provided values
5. The blueprint's domain matches the intended automation type

## Blueprint Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| "Input entity not found" | Entity ID doesn't exist | Verify entity_id in Developer Tools > States |
| "Domain mismatch" | Entity domain doesn't match selector | Use correct domain (e.g., binary_sensor not sensor) |
| "Blueprint not found" | Blueprint path incorrect | Check blueprint is imported in HA |
| "Required input missing" | Input without default not provided | Provide value for all required inputs |
