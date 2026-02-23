# Scene & Script Patterns for Home Assistant

## Scene Creation Patterns

### Movie Night Scene
```yaml
# Scene definition
scene:
  - name: Movie Night
    entities:
      light.living_room:
        state: "on"
        brightness: 30
        color_temp: 400
      light.tv_backlight:
        state: "on"
        brightness: 80
        rgb_color: [50, 50, 100]
      media_player.living_room:
        state: "on"
      cover.living_room_blinds:
        state: "closed"
```

### Morning Routine Scene
```yaml
scene:
  - name: Good Morning
    entities:
      light.bedroom:
        state: "on"
        brightness: 150
        color_temp: 300
      light.kitchen:
        state: "on"
        brightness: 255
      cover.bedroom_blinds:
        state: "open"
      climate.thermostat:
        state: "heat"
        temperature: 22
```

### Bedtime Scene
```yaml
scene:
  - name: Good Night
    entities:
      light.living_room:
        state: "off"
      light.kitchen:
        state: "off"
      light.bedroom:
        state: "on"
        brightness: 20
        color_temp: 450
      lock.front_door:
        state: "locked"
      cover.all_blinds:
        state: "closed"
```

### Away Scene
```yaml
scene:
  - name: Away
    entities:
      light.all_lights:
        state: "off"
      climate.thermostat:
        state: "heat"
        temperature: 17
      lock.front_door:
        state: "locked"
      lock.back_door:
        state: "locked"
```

## Scene Activation Automation
```yaml
alias: "Activate Movie Night at Sunset"
trigger:
  - platform: sun
    event: sunset
    offset: "+00:30:00"
condition:
  - condition: time
    weekday:
      - fri
      - sat
action:
  - service: scene.turn_on
    target:
      entity_id: scene.movie_night
mode: single
```

## Script Patterns

### Sequential Actions with Delays
```yaml
script:
  morning_routine:
    alias: "Morning Routine"
    sequence:
      - service: light.turn_on
        target:
          entity_id: light.bedroom
        data:
          brightness: 50
      - delay:
          minutes: 5
      - service: light.turn_on
        target:
          entity_id: light.bedroom
        data:
          brightness: 150
      - service: light.turn_on
        target:
          entity_id: light.kitchen
        data:
          brightness: 255
      - service: media_player.play_media
        target:
          entity_id: media_player.kitchen_speaker
        data:
          media_content_type: music
          media_content_id: "morning playlist"
    mode: single
```

### Conditional Script
```yaml
script:
  welcome_home:
    alias: "Welcome Home"
    sequence:
      - choose:
          - conditions:
              - condition: sun
                after: sunset
            sequence:
              - service: light.turn_on
                target:
                  entity_id: light.hallway
                data:
                  brightness: 200
          - conditions:
              - condition: numeric_state
                entity_id: sensor.outdoor_temperature
                below: 10
            sequence:
              - service: climate.set_temperature
                target:
                  entity_id: climate.thermostat
                data:
                  temperature: 23
      - service: notify.notify
        data:
          message: "Welcome home!"
    mode: single
```

### Repeat Actions
```yaml
script:
  flash_lights_alert:
    alias: "Flash Lights Alert"
    sequence:
      - repeat:
          count: 5
          sequence:
            - service: light.turn_on
              target:
                entity_id: light.living_room
              data:
                brightness: 255
            - delay:
                milliseconds: 500
            - service: light.turn_off
              target:
                entity_id: light.living_room
            - delay:
                milliseconds: 500
      - service: light.turn_on
        target:
          entity_id: light.living_room
        data:
          brightness: 200
    mode: single
```

## Common Scene Archetypes

| Scene | Typical Entities | Key Settings |
|-------|-----------------|-------------|
| Movie Night | Lights (dim), TV backlight, blinds (closed) | Low brightness, warm color temp |
| Morning | Bedroom light, kitchen light, blinds (open) | Full brightness, cool color temp |
| Bedtime | All lights off except bedroom (dim), locks | Very low brightness, warm |
| Party | All lights on, colored, music | High brightness, RGB colors |
| Dinner | Dining lights, candle effect | Medium brightness, warm |
| Away | All lights off, locks, thermostat eco | Security focused |
| Reading | Single light, high brightness | Focused, cool white |
