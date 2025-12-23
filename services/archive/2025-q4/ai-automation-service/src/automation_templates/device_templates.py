"""
Device-Specific Automation Templates
Phase 2.2: Library of device-specific automation templates
Enhanced: 2025 - Expanded to 50+ templates with scoring and variants
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


# Device-specific automation templates
# Structure: device_type -> list of templates
# Each template has: name, description, yaml_template, confidence, required_entities, 
# category, complexity, popularity, success_rate, variants
DEVICE_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    # Motion Sensors (5 variants)
    "motion_sensor": [
        {
            "name": "Basic Motion-Activated Light",
            "description": "Turn on light when motion detected",
            "yaml_template": """alias: Motion-Activated Light
description: Turn on light when motion detected
trigger:
  - platform: state
    entity_id: {motion_sensor}
    to: "on"
action:
  - service: light.turn_on
    target:
      entity_id: {target_light}
mode: single""",
            "confidence": 0.95,
            "required_entities": ["binary_sensor"],
            "category": "convenience",
            "complexity": "simple",
            "popularity": 0.9,
            "success_rate": 0.85,
            "variants": ["simple", "standard", "advanced"]
        },
        {
            "name": "Occupancy-Based Light Control",
            "description": "Turn on light when motion detected, turn off when no motion for delay period",
            "yaml_template": """alias: Occupancy-Based Light
description: Turn on light when motion detected, turn off after delay
trigger:
  - platform: state
    entity_id: {motion_sensor}
    to: "on"
  - platform: state
    entity_id: {motion_sensor}
    to: "off"
    for:
      minutes: {delay_minutes}
action:
  - choose:
      - conditions:
          - condition: state
            entity_id: {motion_sensor}
            state: "on"
        sequence:
          - service: light.turn_on
            target:
              entity_id: {target_light}
      - conditions:
          - condition: state
            entity_id: {motion_sensor}
            state: "off"
        sequence:
          - service: light.turn_off
            target:
              entity_id: {target_light}
mode: single""",
            "confidence": 0.9,
            "required_entities": ["binary_sensor", "light"],
            "category": "convenience",
            "complexity": "standard",
            "popularity": 0.85,
            "success_rate": 0.8,
            "variants": ["simple", "standard", "advanced"]
        },
        {
            "name": "Delayed Off Motion Light",
            "description": "Turn on light immediately, turn off after delay when motion stops",
            "yaml_template": """alias: Delayed Off Motion Light
description: Turn on light immediately, turn off after delay
trigger:
  - platform: state
    entity_id: {motion_sensor}
    to: "on"
action:
  - service: light.turn_on
    target:
      entity_id: {target_light}
  - wait_for_trigger:
      - platform: state
        entity_id: {motion_sensor}
        to: "off"
        for:
          minutes: {delay_minutes}
  - service: light.turn_off
    target:
      entity_id: {target_light}
mode: single""",
            "confidence": 0.88,
            "required_entities": ["binary_sensor", "light"],
            "category": "convenience",
            "complexity": "standard",
            "popularity": 0.8,
            "success_rate": 0.75,
            "variants": ["simple", "standard", "advanced"]
        },
        {
            "name": "Brightness-Aware Motion Light",
            "description": "Turn on light only if ambient brightness is below threshold",
            "yaml_template": """alias: Brightness-Aware Motion Light
description: Turn on light only if dark
trigger:
  - platform: state
    entity_id: {motion_sensor}
    to: "on"
condition:
  - condition: numeric_state
    entity_id: {brightness_sensor}
    below: {brightness_threshold}
action:
  - service: light.turn_on
    target:
      entity_id: {target_light}
mode: single""",
            "confidence": 0.85,
            "required_entities": ["binary_sensor", "light", "sensor"],
            "category": "energy",
            "complexity": "standard",
            "popularity": 0.75,
            "success_rate": 0.7,
            "variants": ["simple", "standard", "advanced"]
        },
        {
            "name": "Multi-Room Motion Lighting",
            "description": "Control multiple lights based on motion in different rooms",
            "yaml_template": """alias: Multi-Room Motion Lighting
description: Control lights based on room motion
trigger:
  - platform: state
    entity_id: {motion_sensor_1}
    to: "on"
  - platform: state
    entity_id: {motion_sensor_2}
    to: "on"
action:
  - choose:
      - conditions:
          - condition: state
            entity_id: {motion_sensor_1}
            state: "on"
        sequence:
          - service: light.turn_on
            target:
              entity_id: {target_light_1}
      - conditions:
          - condition: state
            entity_id: {motion_sensor_2}
            state: "on"
        sequence:
          - service: light.turn_on
            target:
              entity_id: {target_light_2}
mode: single""",
            "confidence": 0.8,
            "required_entities": ["binary_sensor", "light"],
            "category": "convenience",
            "complexity": "advanced",
            "popularity": 0.7,
            "success_rate": 0.65,
            "variants": ["standard", "advanced"]
        }
    ],
    # Door/Window Sensors (3 variants)
    "door_sensor": [
        {
            "name": "Door Open Alert",
            "description": "Notify when door is opened",
            "yaml_template": """alias: Door Open Alert
description: Notify when door is opened
trigger:
  - platform: state
    entity_id: {door_sensor}
    to: "on"
action:
  - service: notify.mobile_app
    data:
      message: "{door_name} door has been opened"
      title: "Door Alert"
mode: single""",
            "confidence": 0.95,
            "required_entities": ["binary_sensor"],
            "category": "security",
            "complexity": "simple",
            "popularity": 0.9,
            "success_rate": 0.88,
            "variants": ["simple", "standard", "advanced"]
        },
        {
            "name": "Security Mode Door Alert",
            "description": "Alert when door opens while security mode is active",
            "yaml_template": """alias: Security Mode Door Alert
description: Alert when door opens in security mode
trigger:
  - platform: state
    entity_id: {door_sensor}
    to: "on"
condition:
  - condition: state
    entity_id: {security_mode}
    state: "armed"
action:
  - service: notify.mobile_app
    data:
      message: "Security alert: {door_name} door opened while armed"
      title: "Security Alert"
  - service: light.turn_on
    target:
      entity_id: {alarm_light}
    data:
      brightness_pct: 100
mode: single""",
            "confidence": 0.9,
            "required_entities": ["binary_sensor", "input_boolean"],
            "category": "security",
            "complexity": "standard",
            "popularity": 0.85,
            "success_rate": 0.8,
            "variants": ["standard", "advanced"]
        },
        {
            "name": "Door Temperature Alert",
            "description": "Alert if door left open and temperature changes significantly",
            "yaml_template": """alias: Door Temperature Alert
description: Alert if door left open causing temperature change
trigger:
  - platform: state
    entity_id: {door_sensor}
    to: "on"
    for:
      minutes: 10
condition:
  - condition: numeric_state
    entity_id: {temperature_sensor}
    above: {temp_threshold}
action:
  - service: notify.mobile_app
    data:
      message: "{door_name} has been open for 10 minutes, temperature is {temp_threshold}°F"
      title: "Temperature Alert"
mode: single""",
            "confidence": 0.85,
            "required_entities": ["binary_sensor", "sensor"],
            "category": "energy",
            "complexity": "standard",
            "popularity": 0.75,
            "success_rate": 0.7,
            "variants": ["standard", "advanced"]
        }
    ],
    # Lights (5 variants)
    "light": [
        {
            "name": "Sunset Light Automation",
            "description": "Turn on light at sunset",
            "yaml_template": """alias: Sunset Light
description: Turn on light at sunset
trigger:
  - platform: sun
    event: sunset
    offset: "-00:30:00"
action:
  - service: light.turn_on
    target:
      entity_id: {target_light}
mode: single""",
            "confidence": 0.95,
            "required_entities": ["light"],
            "category": "convenience",
            "complexity": "simple",
            "popularity": 0.9,
            "success_rate": 0.88,
            "variants": ["simple", "standard", "advanced"]
        },
        {
            "name": "Motion-Activated Light",
            "description": "Turn on light when motion detected",
            "yaml_template": """alias: Motion-Activated Light
description: Turn on light when motion detected
trigger:
  - platform: state
    entity_id: {motion_sensor}
    to: "on"
action:
  - service: light.turn_on
    target:
      entity_id: {target_light}
mode: single""",
            "confidence": 0.92,
            "required_entities": ["light", "binary_sensor"],
            "category": "convenience",
            "complexity": "simple",
            "popularity": 0.88,
            "success_rate": 0.85,
            "variants": ["simple", "standard", "advanced"]
        },
        {
            "name": "Presence-Based Light Control",
            "description": "Turn on light when person arrives home",
            "yaml_template": """alias: Presence-Based Light
description: Turn on light when person arrives
trigger:
  - platform: state
    entity_id: {person_entity}
    to: "home"
condition:
  - condition: state
    entity_id: {person_entity}
    state: "home"
action:
  - service: light.turn_on
    target:
      entity_id: {target_light}
mode: single""",
            "confidence": 0.9,
            "required_entities": ["light", "person"],
            "category": "convenience",
            "complexity": "standard",
            "popularity": 0.85,
            "success_rate": 0.8,
            "variants": ["simple", "standard", "advanced"]
        },
        {
            "name": "Scheduled Light Control",
            "description": "Turn on/off light on schedule",
            "yaml_template": """alias: Scheduled Light
description: Turn on/off light on schedule
trigger:
  - platform: time
    at: "{on_time}"
  - platform: time
    at: "{off_time}"
action:
  - choose:
      - conditions:
          - condition: time
            after: "{on_time}"
            before: "{off_time}"
        sequence:
          - service: light.turn_on
            target:
              entity_id: {target_light}
      - default:
          - service: light.turn_off
            target:
              entity_id: {target_light}
mode: single""",
            "confidence": 0.88,
            "required_entities": ["light"],
            "category": "convenience",
            "complexity": "standard",
            "popularity": 0.8,
            "success_rate": 0.75,
            "variants": ["simple", "standard", "advanced"]
        },
        {
            "name": "Away Mode Light Control",
            "description": "Turn off all lights when away, turn on when returning",
            "yaml_template": """alias: Away Mode Light Control
description: Control lights based on away status
trigger:
  - platform: state
    entity_id: {person_entity}
    to: "not_home"
  - platform: state
    entity_id: {person_entity}
    to: "home"
action:
  - choose:
      - conditions:
          - condition: state
            entity_id: {person_entity}
            state: "not_home"
        sequence:
          - service: light.turn_off
            target:
              area_id: {area_id}
      - default:
          - service: light.turn_on
            target:
              area_id: {area_id}
mode: single""",
            "confidence": 0.85,
            "required_entities": ["light", "person"],
            "category": "energy",
            "complexity": "advanced",
            "popularity": 0.75,
            "success_rate": 0.7,
            "variants": ["standard", "advanced"]
        }
    ],
    # Switches (4 variants)
    "switch": [
        {
            "name": "Energy Monitoring Switch",
            "description": "Alert when switch uses excessive energy",
            "yaml_template": """alias: Energy Monitoring Switch
description: Alert on high energy usage
trigger:
  - platform: numeric_state
    entity_id: {energy_sensor}
    above: {energy_threshold}
    for:
      minutes: 5
action:
  - service: notify.mobile_app
    data:
      message: "{switch_name} is using {energy_threshold}W - high energy consumption"
      title: "Energy Alert"
mode: single""",
            "confidence": 0.9,
            "required_entities": ["switch", "sensor"],
            "category": "energy",
            "complexity": "standard",
            "popularity": 0.8,
            "success_rate": 0.75,
            "variants": ["simple", "standard", "advanced"]
        },
        {
            "name": "Scheduled Switch Control",
            "description": "Turn switch on/off on schedule",
            "yaml_template": """alias: Scheduled Switch
description: Turn switch on/off on schedule
trigger:
  - platform: time
    at: "{on_time}"
  - platform: time
    at: "{off_time}"
action:
  - choose:
      - conditions:
          - condition: time
            after: "{on_time}"
            before: "{off_time}"
        sequence:
          - service: switch.turn_on
            target:
              entity_id: {target_switch}
      - default:
          - service: switch.turn_off
            target:
              entity_id: {target_switch}
mode: single""",
            "confidence": 0.88,
            "required_entities": ["switch"],
            "category": "convenience",
            "complexity": "simple",
            "popularity": 0.85,
            "success_rate": 0.8,
            "variants": ["simple", "standard", "advanced"]
        },
        {
            "name": "Away Mode Switch Control",
            "description": "Turn off switch when away",
            "yaml_template": """alias: Away Mode Switch
description: Turn off switch when away
trigger:
  - platform: state
    entity_id: {person_entity}
    to: "not_home"
action:
  - service: switch.turn_off
    target:
      entity_id: {target_switch}
mode: single""",
            "confidence": 0.85,
            "required_entities": ["switch", "person"],
            "category": "energy",
            "complexity": "simple",
            "popularity": 0.8,
            "success_rate": 0.75,
            "variants": ["simple", "standard", "advanced"]
        },
        {
            "name": "Time-Based Switch Control",
            "description": "Turn switch on for specific duration",
            "yaml_template": """alias: Time-Based Switch
description: Turn switch on for duration
trigger:
  - platform: time
    at: "{on_time}"
action:
  - service: switch.turn_on
    target:
      entity_id: {target_switch}
  - delay: "{duration}"
  - service: switch.turn_off
    target:
      entity_id: {target_switch}
mode: single""",
            "confidence": 0.82,
            "required_entities": ["switch"],
            "category": "convenience",
            "complexity": "standard",
            "popularity": 0.75,
            "success_rate": 0.7,
            "variants": ["standard", "advanced"]
        }
    ],
    # Thermostats (4 variants)
    "thermostat": [
        {
            "name": "Scheduled Thermostat Control",
            "description": "Set thermostat temperature on schedule",
            "yaml_template": """alias: Scheduled Thermostat
description: Set temperature on schedule
trigger:
  - platform: time
    at: "{morning_time}"
  - platform: time
    at: "{evening_time}"
action:
  - choose:
      - conditions:
          - condition: time
            after: "{morning_time}"
            before: "{evening_time}"
        sequence:
          - service: climate.set_temperature
            target:
              entity_id: {thermostat}
            data:
              temperature: {day_temp}
      - default:
          - service: climate.set_temperature
            target:
              entity_id: {thermostat}
            data:
              temperature: {night_temp}
mode: single""",
            "confidence": 0.9,
            "required_entities": ["climate"],
            "category": "energy",
            "complexity": "standard",
            "popularity": 0.88,
            "success_rate": 0.85,
            "variants": ["simple", "standard", "advanced"]
        },
        {
            "name": "Away Mode Thermostat",
            "description": "Set thermostat to energy-saving mode when away",
            "yaml_template": """alias: Away Mode Thermostat
description: Set energy-saving mode when away
trigger:
  - platform: state
    entity_id: {person_entity}
    to: "not_home"
  - platform: state
    entity_id: {person_entity}
    to: "home"
action:
  - choose:
      - conditions:
          - condition: state
            entity_id: {person_entity}
            state: "not_home"
        sequence:
          - service: climate.set_temperature
            target:
              entity_id: {thermostat}
            data:
              temperature: {away_temp}
      - default:
          - service: climate.set_temperature
            target:
              entity_id: {thermostat}
            data:
              temperature: {home_temp}
mode: single""",
            "confidence": 0.88,
            "required_entities": ["climate", "person"],
            "category": "energy",
            "complexity": "standard",
            "popularity": 0.85,
            "success_rate": 0.8,
            "variants": ["simple", "standard", "advanced"]
        },
        {
            "name": "Weather-Responsive Thermostat",
            "description": "Adjust thermostat based on outdoor temperature",
            "yaml_template": """alias: Weather-Responsive Thermostat
description: Adjust based on outdoor temperature
trigger:
  - platform: state
    entity_id: {weather_sensor}
action:
  - choose:
      - conditions:
          - condition: numeric_state
            entity_id: {weather_sensor}
            below: {cold_threshold}
        sequence:
          - service: climate.set_temperature
            target:
              entity_id: {thermostat}
            data:
              temperature: {warm_temp}
      - conditions:
          - condition: numeric_state
            entity_id: {weather_sensor}
            above: {hot_threshold}
        sequence:
          - service: climate.set_temperature
            target:
              entity_id: {thermostat}
            data:
              temperature: {cool_temp}
mode: single""",
            "confidence": 0.85,
            "required_entities": ["climate", "weather"],
            "category": "energy",
            "complexity": "advanced",
            "popularity": 0.75,
            "success_rate": 0.7,
            "variants": ["standard", "advanced"]
        },
        {
            "name": "Occupancy-Based Thermostat",
            "description": "Adjust thermostat based on room occupancy",
            "yaml_template": """alias: Occupancy-Based Thermostat
description: Adjust based on room occupancy
trigger:
  - platform: state
    entity_id: {occupancy_sensor}
    to: "on"
  - platform: state
    entity_id: {occupancy_sensor}
    to: "off"
    for:
      minutes: 30
action:
  - choose:
      - conditions:
          - condition: state
            entity_id: {occupancy_sensor}
            state: "on"
        sequence:
          - service: climate.set_temperature
            target:
              entity_id: {thermostat}
            data:
              temperature: {occupied_temp}
      - default:
          - service: climate.set_temperature
            target:
              entity_id: {thermostat}
            data:
              temperature: {unoccupied_temp}
mode: single""",
            "confidence": 0.82,
            "required_entities": ["climate", "binary_sensor"],
            "category": "energy",
            "complexity": "advanced",
            "popularity": 0.7,
            "success_rate": 0.65,
            "variants": ["standard", "advanced"]
        }
    ],
    # Cameras (3 variants)
    "camera": [
        {
            "name": "Motion Alert Camera",
            "description": "Notify when camera detects motion",
            "yaml_template": """alias: Motion Alert Camera
description: Notify on camera motion
trigger:
  - platform: state
    entity_id: {motion_sensor}
    to: "on"
condition:
  - condition: state
    entity_id: {camera}
    state: "idle"
action:
  - service: notify.mobile_app
    data:
      message: "Motion detected by {camera_name}"
      title: "Camera Alert"
      data:
        image: {camera_image}
mode: single""",
            "confidence": 0.9,
            "required_entities": ["camera", "binary_sensor"],
            "category": "security",
            "complexity": "simple",
            "popularity": 0.85,
            "success_rate": 0.8,
            "variants": ["simple", "standard", "advanced"]
        },
        {
            "name": "Recording Trigger",
            "description": "Start recording when motion detected",
            "yaml_template": """alias: Recording Trigger
description: Start recording on motion
trigger:
  - platform: state
    entity_id: {motion_sensor}
    to: "on"
action:
  - service: camera.record
    target:
      entity_id: {camera}
    data:
      duration: 60
mode: single""",
            "confidence": 0.88,
            "required_entities": ["camera", "binary_sensor"],
            "category": "security",
            "complexity": "standard",
            "popularity": 0.8,
            "success_rate": 0.75,
            "variants": ["standard", "advanced"]
        },
        {
            "name": "Person Detection Alert",
            "description": "Alert when person detected in camera view",
            "yaml_template": """alias: Person Detection Alert
description: Alert on person detection
trigger:
  - platform: state
    entity_id: {person_detection_sensor}
    to: "detected"
action:
  - service: notify.mobile_app
    data:
      message: "Person detected by {camera_name}"
      title: "Person Detection"
      data:
        image: {camera_image}
mode: single""",
            "confidence": 0.85,
            "required_entities": ["camera", "binary_sensor"],
            "category": "security",
            "complexity": "standard",
            "popularity": 0.75,
            "success_rate": 0.7,
            "variants": ["standard", "advanced"]
        }
    ],
    # Locks (3 variants)
    "lock": [
        {
            "name": "Auto-Lock Door",
            "description": "Automatically lock door after delay when unlocked",
            "yaml_template": """alias: Auto-Lock Door
description: Auto-lock after delay
trigger:
  - platform: state
    entity_id: {lock}
    to: "unlocked"
action:
  - delay: "{lock_delay}"
  - service: lock.lock
    target:
      entity_id: {lock}
mode: single""",
            "confidence": 0.92,
            "required_entities": ["lock"],
            "category": "security",
            "complexity": "simple",
            "popularity": 0.9,
            "success_rate": 0.85,
            "variants": ["simple", "standard", "advanced"]
        },
        {
            "name": "Unlock Notification",
            "description": "Notify when door is unlocked",
            "yaml_template": """alias: Unlock Notification
description: Notify on door unlock
trigger:
  - platform: state
    entity_id: {lock}
    to: "unlocked"
action:
  - service: notify.mobile_app
    data:
      message: "{lock_name} has been unlocked"
      title: "Lock Alert"
mode: single""",
            "confidence": 0.9,
            "required_entities": ["lock"],
            "category": "security",
            "complexity": "simple",
            "popularity": 0.85,
            "success_rate": 0.8,
            "variants": ["simple", "standard", "advanced"]
        },
        {
            "name": "Away Mode Auto-Lock",
            "description": "Lock all doors when away",
            "yaml_template": """alias: Away Mode Auto-Lock
description: Lock doors when away
trigger:
  - platform: state
    entity_id: {person_entity}
    to: "not_home"
action:
  - service: lock.lock
    target:
      area_id: {area_id}
mode: single""",
            "confidence": 0.88,
            "required_entities": ["lock", "person"],
            "category": "security",
            "complexity": "standard",
            "popularity": 0.8,
            "success_rate": 0.75,
            "variants": ["standard", "advanced"]
        }
    ],
    # Smart Plugs (3 variants)
    "smart_plug": [
        {
            "name": "Energy Monitoring Smart Plug",
            "description": "Alert when plug uses excessive energy",
            "yaml_template": """alias: Energy Monitoring Plug
description: Alert on high energy usage
trigger:
  - platform: numeric_state
    entity_id: {energy_sensor}
    above: {energy_threshold}
    for:
      minutes: 5
action:
  - service: notify.mobile_app
    data:
      message: "{plug_name} is using {energy_threshold}W"
      title: "Energy Alert"
mode: single""",
            "confidence": 0.9,
            "required_entities": ["switch", "sensor"],
            "category": "energy",
            "complexity": "standard",
            "popularity": 0.8,
            "success_rate": 0.75,
            "variants": ["simple", "standard", "advanced"]
        },
        {
            "name": "Scheduled Smart Plug",
            "description": "Turn plug on/off on schedule",
            "yaml_template": """alias: Scheduled Smart Plug
description: Turn plug on/off on schedule
trigger:
  - platform: time
    at: "{on_time}"
  - platform: time
    at: "{off_time}"
action:
  - choose:
      - conditions:
          - condition: time
            after: "{on_time}"
            before: "{off_time}"
        sequence:
          - service: switch.turn_on
            target:
              entity_id: {target_plug}
      - default:
          - service: switch.turn_off
            target:
              entity_id: {target_plug}
mode: single""",
            "confidence": 0.88,
            "required_entities": ["switch"],
            "category": "convenience",
            "complexity": "simple",
            "popularity": 0.85,
            "success_rate": 0.8,
            "variants": ["simple", "standard", "advanced"]
        },
        {
            "name": "Away Mode Smart Plug",
            "description": "Turn off plug when away",
            "yaml_template": """alias: Away Mode Smart Plug
description: Turn off plug when away
trigger:
  - platform: state
    entity_id: {person_entity}
    to: "not_home"
action:
  - service: switch.turn_off
    target:
      entity_id: {target_plug}
mode: single""",
            "confidence": 0.85,
            "required_entities": ["switch", "person"],
            "category": "energy",
            "complexity": "simple",
            "popularity": 0.8,
            "success_rate": 0.75,
            "variants": ["simple", "standard", "advanced"]
        }
    ],
    # Legacy templates (keeping for backward compatibility)
    "fridge": [
        {
            "name": "Fridge Door Left Open",
            "description": "Alert if fridge door is open for more than 5 minutes",
            "yaml_template": """alias: Fridge Door Left Open Alert
description: Alert if fridge door is open for more than 5 minutes
trigger:
  - platform: state
    entity_id: binary_sensor.fridge_door
    to: "on"
    for:
      minutes: 5
condition:
  - condition: state
    entity_id: binary_sensor.fridge_door
    state: "on"
action:
  - service: notify.mobile_app
    data:
      message: "Fridge door has been open for 5 minutes"
      title: "Fridge Alert"
mode: single""",
            "confidence": 0.9,
            "required_entities": ["binary_sensor.fridge_door"]
        },
        {
            "name": "Fridge Water Leakage Detection",
            "description": "Detect water leakage from fridge",
            "yaml_template": """alias: Fridge Water Leakage Alert
description: Alert if water leakage is detected
trigger:
  - platform: state
    entity_id: binary_sensor.fridge_water_leak
    to: "on"
action:
  - service: notify.mobile_app
    data:
      message: "Water leakage detected from fridge"
      title: "Fridge Alert - Water Leakage"
mode: single""",
            "confidence": 0.85,
            "required_entities": ["binary_sensor.fridge_water_leak"]
        }
    ],
    "car": [
        {
            "name": "EV Charging Complete Notification",
            "description": "Notify when EV charging is complete",
            "yaml_template": """alias: EV Charging Complete
description: Notify when EV charging is complete
trigger:
  - platform: state
    entity_id: sensor.car_battery
    to: "100"
condition:
  - condition: state
    entity_id: binary_sensor.car_charging
    state: "on"
action:
  - service: notify.mobile_app
    data:
      message: "EV charging is complete"
      title: "Charging Complete"
mode: single""",
            "confidence": 0.95,
            "required_entities": ["sensor.car_battery", "binary_sensor.car_charging"]
        },
        {
            "name": "Low Battery Alert",
            "description": "Alert when car battery is low",
            "yaml_template": """alias: Car Low Battery Alert
description: Alert when car battery is low
trigger:
  - platform: numeric_state
    entity_id: sensor.car_battery
    below: 20
action:
  - service: notify.mobile_app
    data:
      message: "Car battery is below 20%"
      title: "Low Battery Alert"
mode: single""",
            "confidence": 0.9,
            "required_entities": ["sensor.car_battery"]
        }
    ],
    "3d_printer": [
        {
            "name": "3D Print Complete Notification",
            "description": "Notify when 3D print is complete",
            "yaml_template": """alias: 3D Print Complete
description: Notify when 3D print is complete
trigger:
  - platform: state
    entity_id: sensor.printer_status
    to: "complete"
action:
  - service: notify.mobile_app
    data:
      message: "3D print is complete"
      title: "Print Complete"
mode: single""",
            "confidence": 0.9,
            "required_entities": ["sensor.printer_status"]
        },
        {
            "name": "3D Printer Temperature Monitoring",
            "description": "Alert if printer temperature is too high",
            "yaml_template": """alias: 3D Printer Temperature Alert
description: Alert if printer temperature is too high
trigger:
  - platform: numeric_state
    entity_id: sensor.printer_temperature
    above: 250
action:
  - service: notify.mobile_app
    data:
      message: "3D printer temperature is above 250°C"
      title: "Temperature Alert"
mode: single""",
            "confidence": 0.85,
            "required_entities": ["sensor.printer_temperature"]
        }
    ],
    "thermostat": [
        {
            "name": "Energy-Saving Schedule",
            "description": "Set thermostat to energy-saving mode when away",
            "yaml_template": """alias: Energy-Saving Thermostat
description: Set thermostat to energy-saving mode when away
trigger:
  - platform: state
    entity_id: person.home
    to: "not_home"
action:
  - service: climate.set_temperature
    target:
      entity_id: climate.thermostat
    data:
      temperature: 18
mode: single""",
            "confidence": 0.8,
            "required_entities": ["climate.thermostat", "person.home"],
            "category": "energy",
            "complexity": "simple",
            "popularity": 0.8,
            "success_rate": 0.75,
            "variants": ["simple", "standard"]
        }
    ],
    # Legacy device types (keeping for backward compatibility)
    "fridge": [
        {
            "name": "Fridge Door Left Open",
            "description": "Alert if fridge door is open for more than 5 minutes",
            "yaml_template": """alias: Fridge Door Left Open Alert
description: Alert if fridge door is open for more than 5 minutes
trigger:
  - platform: state
    entity_id: binary_sensor.fridge_door
    to: "on"
    for:
      minutes: 5
condition:
  - condition: state
    entity_id: binary_sensor.fridge_door
    state: "on"
action:
  - service: notify.mobile_app
    data:
      message: "Fridge door has been open for 5 minutes"
      title: "Fridge Alert"
mode: single""",
            "confidence": 0.9,
            "required_entities": ["binary_sensor.fridge_door"],
            "category": "energy",
            "complexity": "simple",
            "popularity": 0.85,
            "success_rate": 0.8,
            "variants": ["simple", "standard"]
        },
        {
            "name": "Fridge Water Leakage Detection",
            "description": "Detect water leakage from fridge",
            "yaml_template": """alias: Fridge Water Leakage Alert
description: Alert if water leakage is detected
trigger:
  - platform: state
    entity_id: binary_sensor.fridge_water_leak
    to: "on"
action:
  - service: notify.mobile_app
    data:
      message: "Water leakage detected from fridge"
      title: "Fridge Alert - Water Leakage"
mode: single""",
            "confidence": 0.85,
            "required_entities": ["binary_sensor.fridge_water_leak"],
            "category": "security",
            "complexity": "simple",
            "popularity": 0.75,
            "success_rate": 0.7,
            "variants": ["simple", "standard"]
        }
    ],
    "car": [
        {
            "name": "EV Charging Complete Notification",
            "description": "Notify when EV charging is complete",
            "yaml_template": """alias: EV Charging Complete
description: Notify when EV charging is complete
trigger:
  - platform: state
    entity_id: sensor.car_battery
    to: "100"
condition:
  - condition: state
    entity_id: binary_sensor.car_charging
    state: "on"
action:
  - service: notify.mobile_app
    data:
      message: "EV charging is complete"
      title: "Charging Complete"
mode: single""",
            "confidence": 0.95,
            "required_entities": ["sensor.car_battery", "binary_sensor.car_charging"],
            "category": "convenience",
            "complexity": "standard",
            "popularity": 0.8,
            "success_rate": 0.75,
            "variants": ["simple", "standard"]
        },
        {
            "name": "Low Battery Alert",
            "description": "Alert when car battery is low",
            "yaml_template": """alias: Car Low Battery Alert
description: Alert when car battery is low
trigger:
  - platform: numeric_state
    entity_id: sensor.car_battery
    below: 20
action:
  - service: notify.mobile_app
    data:
      message: "Car battery is below 20%"
      title: "Low Battery Alert"
mode: single""",
            "confidence": 0.9,
            "required_entities": ["sensor.car_battery"],
            "category": "convenience",
            "complexity": "simple",
            "popularity": 0.85,
            "success_rate": 0.8,
            "variants": ["simple", "standard"]
        }
    ],
    "3d_printer": [
        {
            "name": "3D Print Complete Notification",
            "description": "Notify when 3D print is complete",
            "yaml_template": """alias: 3D Print Complete
description: Notify when 3D print is complete
trigger:
  - platform: state
    entity_id: sensor.printer_status
    to: "complete"
action:
  - service: notify.mobile_app
    data:
      message: "3D print is complete"
      title: "Print Complete"
mode: single""",
            "confidence": 0.9,
            "required_entities": ["sensor.printer_status"],
            "category": "convenience",
            "complexity": "simple",
            "popularity": 0.75,
            "success_rate": 0.7,
            "variants": ["simple", "standard"]
        },
        {
            "name": "3D Printer Temperature Monitoring",
            "description": "Alert if printer temperature is too high",
            "yaml_template": """alias: 3D Printer Temperature Alert
description: Alert if printer temperature is too high
trigger:
  - platform: numeric_state
    entity_id: sensor.printer_temperature
    above: 250
action:
  - service: notify.mobile_app
    data:
      message: "3D printer temperature is above 250°C"
      title: "Temperature Alert"
mode: single""",
            "confidence": 0.85,
            "required_entities": ["sensor.printer_temperature"],
            "category": "security",
            "complexity": "simple",
            "popularity": 0.7,
            "success_rate": 0.65,
            "variants": ["simple", "standard"]
        }
    ]
}


class DeviceTemplateGenerator:
    """
    Generator for device-specific automation templates.
    
    Enhanced 2025:
    - Template scoring algorithm (match quality + popularity + success rate)
    - Template matching with capability awareness
    - Template-based entity resolution
    - Template-first YAML generation
    """

    def __init__(self):
        """Initialize template generator"""
        self.templates = DEVICE_TEMPLATES

    def get_device_templates(self, device_type: str) -> list[dict[str, Any]]:
        """
        Get automation templates for a device type.
        
        Args:
            device_type: Device type (motion_sensor, door_sensor, light, etc.)
            
        Returns:
            List of template dictionaries
        """
        return self.templates.get(device_type, [])

    def score_template(
        self,
        template: dict[str, Any],
        device_entities: list[dict[str, Any]],
        match_quality: float = 1.0
    ) -> float:
        """
        Score a template using multi-factor algorithm.
        
        Scoring formula (from ai_automation_suggester):
        - Match quality: 90% weight
        - Popularity: 5% weight
        - Success rate: 5% weight
        
        Args:
            template: Template dictionary
            device_entities: List of device entities
            match_quality: Quality of match (0.0-1.0), default 1.0
            
        Returns:
            Template score (0.0-1.0)
        """
        # Match quality (90% weight)
        match_score = match_quality * 0.90
        
        # Popularity (5% weight)
        popularity = template.get("popularity", 0.5)
        popularity_score = popularity * 0.05
        
        # Success rate (5% weight)
        success_rate = template.get("success_rate", 0.5)
        success_score = success_rate * 0.05
        
        total_score = match_score + popularity_score + success_score
        
        # Cap at 1.0
        return min(total_score, 1.0)

    def match_templates_to_device(
        self,
        device_type: str | None,
        device_entities: list[dict[str, Any]],
        max_templates: int = 5
    ) -> list[tuple[dict[str, Any], float]]:
        """
        Match templates to device and return top matches with scores.
        
        Args:
            device_type: Device type
            device_entities: List of entity dictionaries
            max_templates: Maximum number of templates to return
            
        Returns:
            List of (template, score) tuples, sorted by score descending
        """
        if not device_type:
            return []
        
        templates = self.get_device_templates(device_type)
        if not templates:
            return []
        
        # Build entity domain/type set for matching
        entity_domains = {e.get("entity_id", "").split(".")[0] for e in device_entities if e.get("entity_id")}
        entity_ids = {e.get("entity_id") for e in device_entities if e.get("entity_id")}
        
        scored_templates = []
        
        for template in templates:
            # Calculate match quality based on required entities
            required_entities = template.get("required_entities", [])
            match_quality = 1.0
            
            if required_entities:
                # Check if required entity types/domains are available
                required_domains = {req.split(".")[0] if "." in req else req for req in required_entities}
                available_domains = entity_domains
                
                # Calculate match: how many required domains are available
                if required_domains:
                    matched_domains = len(required_domains.intersection(available_domains))
                    match_quality = matched_domains / len(required_domains)
                
                # Bonus if exact entity IDs match
                if required_entities and any(req in entity_ids for req in required_entities):
                    match_quality = min(match_quality + 0.2, 1.0)
            
            # Score template
            score = self.score_template(template, device_entities, match_quality)
            scored_templates.append((template, score))
        
        # Sort by score descending
        scored_templates.sort(key=lambda x: x[1], reverse=True)
        
        # Return top N
        return scored_templates[:max_templates]

    def resolve_entities_for_template(
        self,
        template: dict[str, Any],
        device_entities: list[dict[str, Any]],
        all_entities: list[dict[str, Any]] | None = None
    ) -> dict[str, str]:
        """
        Resolve entity IDs for template placeholders using template requirements.
        
        Template-based entity resolution (from ai_automation_suggester):
        - Use template requirements to filter candidates
        - Match by domain/device_class
        - Prefer entities from same device
        
        Args:
            template: Template dictionary
            device_entities: Entities from the target device
            all_entities: Optional list of all available entities
            
        Returns:
            Dictionary mapping template placeholders to entity IDs
        """
        resolved = {}
        required_entities = template.get("required_entities", [])
        
        if not all_entities:
            all_entities = device_entities
        
        # Build entity lookup by domain
        entities_by_domain: dict[str, list[dict[str, Any]]] = {}
        for entity in all_entities:
            entity_id = entity.get("entity_id")
            if not entity_id:
                continue
            domain = entity_id.split(".")[0]
            if domain not in entities_by_domain:
                entities_by_domain[domain] = []
            entities_by_domain[domain].append(entity)
        
        # Resolve each required entity
        for req_entity in required_entities:
            # Parse required entity (e.g., "binary_sensor" or "binary_sensor.motion")
            if "." in req_entity:
                domain, device_class = req_entity.split(".", 1)
            else:
                domain = req_entity
                device_class = None
            
            # Prefer entities from same device
            candidates = []
            if domain in entities_by_domain:
                # First try device entities
                for entity in device_entities:
                    entity_id = entity.get("entity_id", "")
                    if entity_id.startswith(f"{domain}."):
                        if not device_class or device_class in entity_id:
                            candidates.append(entity)
                            break
                
                # Fall back to all entities
                if not candidates:
                    for entity in entities_by_domain[domain]:
                        entity_id = entity.get("entity_id", "")
                        if not device_class or device_class in entity_id:
                            candidates.append(entity)
            
            # Use first candidate
            if candidates:
                resolved[req_entity] = candidates[0].get("entity_id")
        
        return resolved

    def generate_yaml_from_template(
        self,
        template: dict[str, Any],
        entity_mapping: dict[str, str],
        custom_values: dict[str, Any] | None = None
    ) -> str:
        """
        Generate YAML from template by filling placeholders.
        
        Template-first YAML generation (from ai_automation_suggester):
        - Start with validated template structure
        - Fill placeholders with resolved entities
        - Apply custom values if provided
        
        Args:
            template: Template dictionary
            entity_mapping: Dictionary mapping template placeholders to entity IDs
            custom_values: Optional dictionary of custom values (times, thresholds, etc.)
            
        Returns:
            Generated YAML string
        """
        yaml_template = template.get("yaml_template", "")
        
        if not yaml_template:
            return ""
        
        # Replace entity placeholders
        for placeholder, entity_id in entity_mapping.items():
            # Replace {placeholder} with entity_id
            yaml_template = yaml_template.replace(f"{{{placeholder}}}", entity_id)
        
        # Replace custom values
        if custom_values:
            for key, value in custom_values.items():
                yaml_template = yaml_template.replace(f"{{{key}}}", str(value))
        
        # Clean up any remaining placeholders (optional - could raise error instead)
        import re
        yaml_template = re.sub(r"\{[^}]+\}", "REPLACE_WITH_ENTITY", yaml_template)
        
        return yaml_template

    def suggest_device_automations(
        self,
        device_id: str,
        device_type: str | None,
        device_entities: list[dict[str, Any]],
        all_entities: list[dict[str, Any]] | None = None,
        max_suggestions: int = 5
    ) -> list[dict[str, Any]]:
        """
        Generate automation suggestions based on device type and capabilities.
        
        Enhanced 2025:
        - Uses template scoring algorithm
        - Returns top N templates by score
        - Includes template metadata
        
        Args:
            device_id: Device identifier
            device_type: Device type (from classification)
            device_entities: List of entity dictionaries for this device
            all_entities: Optional list of all available entities
            max_suggestions: Maximum number of suggestions to return
            
        Returns:
            List of automation suggestions with scores
        """
        if not device_type:
            return []
        
        # Match templates to device
        matched_templates = self.match_templates_to_device(
            device_type,
            device_entities,
            max_templates=max_suggestions
        )
        
        if not all_entities:
            all_entities = device_entities
        
        suggestions = []
        
        for template, score in matched_templates:
            # Resolve entities for template
            entity_mapping = self.resolve_entities_for_template(
                template,
                device_entities,
                all_entities
            )
            
            # Generate YAML from template
            yaml_content = self.generate_yaml_from_template(
                template,
                entity_mapping
            )
            
            # Create suggestion
            suggestion = {
                "type": "device_template",
                "title": template["name"],
                "description": template["description"],
                "automation_yaml": yaml_content,
                "device_ids": [device_id],
                "confidence": score,  # Use calculated score
                "source": "device_template",
                "device_type": device_type,
                "template_score": score,
                "template_match_quality": score,  # For tracking
                "category": template.get("category", "convenience"),
                "complexity": template.get("complexity", "simple"),
                "variants": template.get("variants", ["simple"]),
                "entity_mapping": entity_mapping
            }
            suggestions.append(suggestion)
        
        return suggestions


def get_device_templates(device_type: str) -> list[dict[str, Any]]:
    """
    Get device templates for a device type.
    
    Args:
        device_type: Device type
        
    Returns:
        List of templates
    """
    generator = DeviceTemplateGenerator()
    return generator.get_device_templates(device_type)

