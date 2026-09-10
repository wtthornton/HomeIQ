# Security Automation Patterns for Home Assistant

## Motion-Triggered Notifications

### Alert When Motion Detected and Nobody Home
```yaml
alias: "Motion Alert - Nobody Home"
description: "Send notification when motion detected and nobody is home"
trigger:
  - platform: state
    entity_id: binary_sensor.living_room_motion
    to: "on"
condition:
  - condition: state
    entity_id: group.all_persons
    state: "not_home"
action:
  - service: notify.mobile_app
    data:
      title: "Motion Detected"
      message: "Motion detected in {{ trigger.to_state.attributes.friendly_name }} while nobody is home."
      data:
        tag: "security-motion"
        importance: high
mode: single
```

### Camera Snapshot on Motion
```yaml
alias: "Camera Snapshot on Motion"
description: "Take camera snapshot when motion is detected"
trigger:
  - platform: state
    entity_id: binary_sensor.front_door_motion
    to: "on"
action:
  - service: camera.snapshot
    target:
      entity_id: camera.front_door
    data:
      filename: "/config/www/snapshots/front_door_{{ now().strftime('%Y%m%d_%H%M%S') }}.jpg"
  - service: notify.mobile_app
    data:
      title: "Front Door Motion"
      message: "Motion detected at front door"
      data:
        image: "/local/snapshots/front_door_{{ now().strftime('%Y%m%d_%H%M%S') }}.jpg"
mode: single
```

## Lock Management

### Auto-Lock After Timeout
```yaml
alias: "Auto-Lock Front Door"
description: "Lock front door after 5 minutes if left unlocked"
trigger:
  - platform: state
    entity_id: lock.front_door
    to: "unlocked"
    for:
      minutes: 5
action:
  - service: lock.lock
    target:
      entity_id: lock.front_door
  - service: notify.notify
    data:
      message: "Front door auto-locked after 5 minutes"
mode: single
```

### Lock All Doors at Bedtime
```yaml
alias: "Lock All Doors at Bedtime"
description: "Lock all doors when bedtime scene activates"
trigger:
  - platform: state
    entity_id: input_boolean.bedtime_mode
    to: "on"
action:
  - service: lock.lock
    target:
      entity_id:
        - lock.front_door
        - lock.back_door
        - lock.garage_door
mode: single
```

## Presence-Based Arming / Disarming

### Arm Alarm When Everyone Leaves
```yaml
alias: "Arm Alarm - Everyone Left"
description: "Arm alarm system when all persons leave home"
trigger:
  - platform: state
    entity_id: group.all_persons
    to: "not_home"
    for:
      minutes: 5
action:
  - service: alarm_control_panel.alarm_arm_away
    target:
      entity_id: alarm_control_panel.home_alarm
mode: single
```

### Disarm Alarm on Arrival
```yaml
alias: "Disarm Alarm - Arrival"
description: "Disarm alarm when first person arrives home"
trigger:
  - platform: state
    entity_id: group.all_persons
    from: "not_home"
action:
  - service: alarm_control_panel.alarm_disarm
    target:
      entity_id: alarm_control_panel.home_alarm
    data:
      code: !secret alarm_code
mode: single
```

## Geofencing Patterns

### Notify When Person Leaves Zone
```yaml
alias: "Left Home Zone Alert"
description: "Notify when a family member leaves the home zone"
trigger:
  - platform: zone
    entity_id: person.family_member
    zone: zone.home
    event: leave
action:
  - service: notify.mobile_app
    data:
      message: "{{ trigger.entity_id.split('.')[1] | replace('_',' ') | title }} has left home"
mode: parallel
```

## Doorbell Alerts

### Doorbell Press Notification
```yaml
alias: "Doorbell Alert"
description: "Send notification with camera snapshot when doorbell is pressed"
trigger:
  - platform: state
    entity_id: binary_sensor.doorbell
    to: "on"
action:
  - service: camera.snapshot
    target:
      entity_id: camera.front_door
    data:
      filename: "/config/www/snapshots/doorbell_{{ now().strftime('%Y%m%d_%H%M%S') }}.jpg"
  - service: notify.mobile_app
    data:
      title: "Doorbell"
      message: "Someone is at the front door"
      data:
        image: "/local/snapshots/doorbell_{{ now().strftime('%Y%m%d_%H%M%S') }}.jpg"
        actions:
          - action: UNLOCK_DOOR
            title: "Unlock Door"
mode: single
```

## Common Entity Patterns

| Purpose | Entity Pattern |
|---------|---------------|
| Motion sensor | `binary_sensor.{area}_motion` |
| Door sensor | `binary_sensor.{area}_door` |
| Window sensor | `binary_sensor.{area}_window` |
| Lock | `lock.{area}_door` |
| Camera | `camera.{area}` |
| Alarm panel | `alarm_control_panel.{name}` |
| Person | `person.{name}` |
| Siren | `siren.{name}` |
