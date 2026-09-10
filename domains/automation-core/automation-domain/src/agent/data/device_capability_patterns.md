# Device Capability Patterns for Home Assistant

## WLED (Addressable LEDs)

### Effect List Control
```yaml
# WLED provides an effect_list attribute with all available effects
# Use select_effect to activate effects by name
- service: light.turn_on
  target:
    entity_id: light.wled_strip
  data:
    effect: "Rainbow"
    brightness: 200

# Common WLED effects: Solid, Blink, Breathe, Color Wipe, Rainbow,
# Theater Chase, Fire 2012, Colorful, Gradient, Loading, Police,
# Fairy, Fireworks, Rain, Merry Christmas, Halloween
```

### WLED Segment Control
```yaml
# WLED supports segments for independent LED strip sections
# Each segment is a separate light entity
- service: light.turn_on
  target:
    entity_id: light.wled_segment_0
  data:
    rgb_color: [255, 0, 0]
    brightness: 200

- service: light.turn_on
  target:
    entity_id: light.wled_segment_1
  data:
    rgb_color: [0, 0, 255]
    brightness: 200
```

### WLED Preset Activation
```yaml
# Activate saved WLED presets
- service: select.select_option
  target:
    entity_id: select.wled_preset
  data:
    option: "Game Day"
```

## Philips Hue

### Hue Scene Activation
```yaml
# Hue scenes are different from HA scenes
# Activate using the hue.activate_scene service
- service: hue.activate_scene
  data:
    group_name: "Living Room"
    scene_name: "Energize"
```

### Hue Group Control
```yaml
# Control all lights in a Hue room/zone at once
- service: light.turn_on
  target:
    entity_id: light.living_room  # Hue room group entity
  data:
    brightness: 200
    color_temp: 350
```

## Smart Plugs (Power Monitoring)

### Power-Based Automation (Appliance Finished)
```yaml
alias: "Washer Finished"
description: "Notify when washing machine finishes (power drops)"
trigger:
  - platform: numeric_state
    entity_id: sensor.washing_machine_power
    below: 5
    for:
      minutes: 2
condition:
  - condition: numeric_state
    entity_id: sensor.washing_machine_power
    above: 0
action:
  - service: notify.notify
    data:
      title: "Washer Done"
      message: "The washing machine has finished its cycle"
mode: single
```

### Energy Monitoring Threshold
```yaml
alias: "High Power Alert"
description: "Alert when a plug exceeds power threshold"
trigger:
  - platform: numeric_state
    entity_id: sensor.smart_plug_power
    above: 2000
action:
  - service: notify.notify
    data:
      message: "High power usage: {{ states('sensor.smart_plug_power') }}W"
mode: single
```

## Covers / Blinds

### Sun-Based Blind Control
```yaml
alias: "Auto Close Blinds - Sun"
description: "Close blinds when sun elevation is high (prevent heat gain)"
trigger:
  - platform: numeric_state
    entity_id: sun.sun
    attribute: elevation
    above: 40
action:
  - service: cover.close_cover
    target:
      entity_id: cover.living_room_blinds
mode: single
```

### Tilt Control
```yaml
# Some covers support tilt position (0-100)
- service: cover.set_cover_tilt_position
  target:
    entity_id: cover.office_blinds
  data:
    tilt_position: 50
```

## Media Players

### TTS Announcement
```yaml
- service: tts.speak
  target:
    entity_id: tts.google_en
  data:
    media_player_entity_id: media_player.kitchen_speaker
    message: "Dinner is ready!"
```

### Volume Control with Restore
```yaml
script:
  announce_with_restore:
    sequence:
      # Save current volume
      - service: media_player.volume_set
        target:
          entity_id: media_player.speaker
        data:
          volume_level: 0.7
      - service: tts.speak
        target:
          entity_id: tts.google_en
        data:
          media_player_entity_id: media_player.speaker
          message: "{{ message }}"
      - delay:
          seconds: 5
      - service: media_player.volume_set
        target:
          entity_id: media_player.speaker
        data:
          volume_level: 0.4
```

## ESPHome / Sonoff / Shelly / Tasmota

### ESPHome Button Press
```yaml
# ESPHome devices expose button entities for actions
- service: button.press
  target:
    entity_id: button.esphome_device_restart
```

### Shelly Relay with Power Monitoring
```yaml
# Shelly devices expose switch + power sensor
trigger:
  - platform: numeric_state
    entity_id: sensor.shelly_plug_power
    above: 100
action:
  - service: switch.turn_off
    target:
      entity_id: switch.shelly_plug
```

## Common Capability Entity Patterns

| Device Type | Entities Created | Key Attributes |
|-------------|-----------------|---------------|
| WLED | `light.wled_*`, `select.wled_preset` | `effect_list`, `effect`, `rgb_color` |
| Hue Bulb | `light.{room}_{name}` | `brightness`, `color_temp`, `rgb_color` |
| Smart Plug | `switch.*`, `sensor.*_power`, `sensor.*_energy` | `current_power_w` |
| Cover | `cover.*` | `current_position`, `current_tilt_position` |
| Media Player | `media_player.*` | `volume_level`, `media_title`, `source` |
| ESPHome | `sensor.*`, `switch.*`, `button.*` | varies by config |
