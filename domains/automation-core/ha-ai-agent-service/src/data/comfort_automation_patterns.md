# Comfort / Climate Automation Patterns for Home Assistant

## Thermostat Scheduling

### Weekday Schedule
```yaml
alias: "Weekday Thermostat Schedule"
description: "Set thermostat to comfort temperature on weekday mornings"
trigger:
  - platform: time
    at: "06:30:00"
condition:
  - condition: time
    weekday:
      - mon
      - tue
      - wed
      - thu
      - fri
action:
  - service: climate.set_temperature
    target:
      entity_id: climate.thermostat
    data:
      temperature: 22
      hvac_mode: heat
mode: single
```

### Night Setback
```yaml
alias: "Night Temperature Setback"
description: "Lower thermostat at bedtime for energy savings"
trigger:
  - platform: time
    at: "22:00:00"
action:
  - service: climate.set_temperature
    target:
      entity_id: climate.thermostat
    data:
      temperature: 18
mode: single
```

## Away Mode Detection

### Away Mode When Nobody Home
```yaml
alias: "Away Mode - Nobody Home"
description: "Set thermostat to eco when everyone leaves"
trigger:
  - platform: state
    entity_id: group.all_persons
    to: "not_home"
    for:
      minutes: 15
action:
  - service: climate.set_preset_mode
    target:
      entity_id: climate.thermostat
    data:
      preset_mode: eco
mode: single
```

### Restore Comfort on Arrival
```yaml
alias: "Restore Comfort - Arrival"
description: "Restore comfort temperature when someone arrives home"
trigger:
  - platform: state
    entity_id: group.all_persons
    from: "not_home"
action:
  - service: climate.set_preset_mode
    target:
      entity_id: climate.thermostat
    data:
      preset_mode: comfort
mode: single
```

## Window-Open Detection

### Pause HVAC When Window Opens
```yaml
alias: "Pause HVAC - Window Open"
description: "Turn off HVAC when a window is opened to save energy"
trigger:
  - platform: state
    entity_id: binary_sensor.living_room_window
    to: "on"
    for:
      minutes: 2
condition:
  - condition: not
    conditions:
      - condition: state
        entity_id: climate.thermostat
        state: "off"
action:
  - service: climate.turn_off
    target:
      entity_id: climate.thermostat
  - service: notify.notify
    data:
      message: "HVAC paused — window open in {{ trigger.to_state.attributes.friendly_name }}"
mode: single
```

### Resume HVAC When Window Closes
```yaml
alias: "Resume HVAC - Window Closed"
description: "Turn HVAC back on when all windows are closed"
trigger:
  - platform: state
    entity_id: binary_sensor.living_room_window
    to: "off"
    for:
      minutes: 1
action:
  - service: climate.turn_on
    target:
      entity_id: climate.thermostat
mode: single
```

## Humidity Management

### Dehumidifier When Humidity High
```yaml
alias: "Dehumidifier - High Humidity"
description: "Turn on dehumidifier when indoor humidity exceeds threshold"
trigger:
  - platform: numeric_state
    entity_id: sensor.indoor_humidity
    above: 65
action:
  - service: switch.turn_on
    target:
      entity_id: switch.dehumidifier
mode: single
```

### Fan When Temperature High
```yaml
alias: "Fan On - High Temperature"
description: "Turn on ceiling fan when room temperature is high"
trigger:
  - platform: numeric_state
    entity_id: sensor.living_room_temperature
    above: 26
action:
  - service: fan.turn_on
    target:
      entity_id: fan.living_room_ceiling
    data:
      percentage: 50
mode: single
```

## Seasonal Presets

### Summer Mode
```yaml
alias: "Summer Mode"
description: "Switch to summer cooling schedule"
trigger:
  - platform: numeric_state
    entity_id: sensor.outdoor_temperature
    above: 28
    for:
      hours: 2
action:
  - service: climate.set_hvac_mode
    target:
      entity_id: climate.thermostat
    data:
      hvac_mode: cool
  - service: climate.set_temperature
    target:
      entity_id: climate.thermostat
    data:
      temperature: 24
mode: single
```

## Common Entity Patterns

| Purpose | Entity Pattern |
|---------|---------------|
| Thermostat | `climate.{area}_thermostat` |
| Temperature | `sensor.{area}_temperature` |
| Humidity | `sensor.{area}_humidity` |
| Window sensor | `binary_sensor.{area}_window` |
| Fan | `fan.{area}_ceiling` |
| Dehumidifier | `switch.dehumidifier` |
| Outdoor temp | `sensor.outdoor_temperature` |
