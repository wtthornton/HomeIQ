"""
Common Automation Patterns Library

Pre-built, hand-crafted automation templates for common scenarios.
Provides instant, zero-cost, high-quality automations.
"""

import hashlib
from dataclasses import dataclass


@dataclass
class PatternVariable:
    """Definition of a variable that needs to be filled in a pattern"""
    name: str
    type: str  # entity type (light, binary_sensor, etc.)
    domain: str  # HA domain
    device_class: str | None = None  # For binary_sensor (motion, door, etc.)
    default: str | None = None
    description: str = ""
    required: bool = True


@dataclass
class PatternDefinition:
    """Complete pattern definition with template and metadata"""
    id: str
    name: str
    description: str
    category: str
    keywords: list[str]
    variables: list[PatternVariable]
    template: str
    priority: int = 50  # Higher = preferred when multiple matches


# Pattern Library - Hand-crafted, validated automation templates
PATTERNS: dict[str, PatternDefinition] = {

    "motion_light_auto_off": PatternDefinition(
        id="motion_light_auto_off",
        name="Motion-Activated Light with Auto-Off",
        description="Turn on light when motion detected, automatically turn off after no motion",
        category="lighting",
        keywords=["motion", "light", "turn on", "movement", "sensor", "auto", "off"],
        priority=90,
        variables=[
            PatternVariable(
                name="motion_sensor",
                type="binary_sensor",
                domain="binary_sensor",
                device_class="motion",
                description="Motion sensor to trigger light"
            ),
            PatternVariable(
                name="light",
                type="light",
                domain="light",
                description="Light to control"
            ),
            PatternVariable(
                name="no_motion_delay",
                type="duration",
                domain="duration",
                default="5",
                description="Minutes to wait after no motion",
                required=False
            ),
            PatternVariable(
                name="timeout",
                type="duration",
                domain="duration",
                default="10",
                description="Maximum wait time in minutes",
                required=False
            )
        ],
        template="""id: '{automation_id}'
alias: '{alias}'
description: 'Turn on {light_name} when motion detected, auto-off after {no_motion_delay} min'
mode: restart
triggers:
  - trigger: state
    entity_id: {motion_sensor}
    to: 'on'
conditions: []
actions:
  - action: light.turn_on
    target:
      entity_id: {light}
    data:
      brightness: 255
  - wait_for_trigger:
      - trigger: state
        entity_id: {motion_sensor}
        to: 'off'
        for:
          minutes: {no_motion_delay}
    timeout: '00:{timeout_padded}:00'
    continue_on_timeout: true
  - action: light.turn_off
    target:
      entity_id: {light}"""
    ),

    "door_left_open_alert": PatternDefinition(
        id="door_left_open_alert",
        name="Door/Window Left Open Alert",
        description="Send notification if door or window is left open beyond timeout",
        category="security",
        keywords=["door", "window", "open", "alert", "notify", "left", "notification"],
        priority=80,
        variables=[
            PatternVariable(
                name="door_sensor",
                type="binary_sensor",
                domain="binary_sensor",
                device_class="door",
                description="Door/window sensor to monitor"
            ),
            PatternVariable(
                name="notification_service",
                type="notify",
                domain="notify",
                default="notify.mobile_app",
                description="Notification service",
                required=False
            ),
            PatternVariable(
                name="wait_time",
                type="duration",
                domain="duration",
                default="5",
                description="Minutes to wait before alerting",
                required=False
            )
        ],
        template="""id: '{automation_id}'
alias: '{alias}'
description: 'Alert if {door_name} left open for {wait_time} minutes'
mode: single
triggers:
  - trigger: state
    entity_id: {door_sensor}
    to: 'on'
conditions: []
actions:
  - wait_for_trigger:
      - trigger: state
        entity_id: {door_sensor}
        to: 'off'
    timeout: '00:{wait_time_padded}:00'
    continue_on_timeout: true
  - condition: state
    entity_id: {door_sensor}
    state: 'on'
  - action: {notification_service}
    data:
      title: 'Door Alert'
      message: '{{{{ trigger.to_state.attributes.friendly_name }}}} has been open for {wait_time} minutes!'"""
    ),

    "battery_low_notification": PatternDefinition(
        id="battery_low_notification",
        name="Low Battery Notification",
        description="Send notification when device battery is low",
        category="maintenance",
        keywords=["battery", "low", "alert", "notify", "notification", "charge"],
        priority=70,
        variables=[
            PatternVariable(
                name="battery_sensor",
                type="sensor",
                domain="sensor",
                device_class="battery",
                description="Battery level sensor"
            ),
            PatternVariable(
                name="notification_service",
                type="notify",
                domain="notify",
                default="notify.mobile_app",
                description="Notification service",
                required=False
            ),
            PatternVariable(
                name="threshold",
                type="number",
                domain="number",
                default="20",
                description="Battery percentage threshold",
                required=False
            )
        ],
        template="""id: '{automation_id}'
alias: '{alias}'
description: 'Alert when {battery_name} battery drops below {threshold}%'
mode: single
triggers:
  - trigger: numeric_state
    entity_id: {battery_sensor}
    below: {threshold}
conditions: []
actions:
  - action: {notification_service}
    data:
      title: 'Low Battery Alert'
      message: '{{{{ trigger.to_state.attributes.friendly_name }}}} battery is at {{{{ trigger.to_state.state }}}}%'"""
    ),

    "presence_lighting": PatternDefinition(
        id="presence_lighting",
        name="Presence-Based Lighting",
        description="Turn on lights when person arrives home, turn off when leaving",
        category="lighting",
        keywords=["home", "arrive", "leave", "presence", "light", "person", "away"],
        priority=75,
        variables=[
            PatternVariable(
                name="person",
                type="person",
                domain="person",
                description="Person entity to track"
            ),
            PatternVariable(
                name="lights",
                type="light",
                domain="light",
                description="Lights to control (can be multiple)"
            )
        ],
        template="""id: '{automation_id}'
alias: '{alias}'
description: 'Turn on lights when {person_name} arrives home'
mode: single
triggers:
  - trigger: state
    entity_id: {person}
    to: 'home'
conditions: []
actions:
  - action: light.turn_on
    target:
      entity_id: {lights}
    data:
      brightness: 200"""
    ),

    "presence_climate": PatternDefinition(
        id="presence_climate",
        name="Presence-Based Climate Control",
        description="Adjust temperature when person arrives or leaves",
        category="climate",
        keywords=["home", "arrive", "leave", "temperature", "climate", "thermostat", "heat", "cool"],
        priority=75,
        variables=[
            PatternVariable(
                name="person",
                type="person",
                domain="person",
                description="Person entity to track"
            ),
            PatternVariable(
                name="climate",
                type="climate",
                domain="climate",
                description="Climate control entity"
            ),
            PatternVariable(
                name="temperature",
                type="number",
                domain="number",
                default="72",
                description="Target temperature in Fahrenheit",
                required=False
            )
        ],
        template="""id: '{automation_id}'
alias: '{alias}'
description: 'Set {climate_name} to {temperature}°F when {person_name} arrives home'
mode: single
triggers:
  - trigger: state
    entity_id: {person}
    to: 'home'
conditions: []
actions:
  - action: climate.set_temperature
    target:
      entity_id: {climate}
    data:
      temperature: {temperature}"""
    ),

    "time_based_schedule": PatternDefinition(
        id="time_based_schedule",
        name="Time-Based Device Schedule",
        description="Turn device on/off at specific times",
        category="scheduling",
        keywords=["time", "schedule", "turn on", "turn off", "daily", "morning", "evening"],
        priority=60,
        variables=[
            PatternVariable(
                name="entity",
                type="any",
                domain="any",
                description="Entity to control"
            ),
            PatternVariable(
                name="time",
                type="time",
                domain="time",
                default="07:00:00",
                description="Time to trigger",
                required=False
            ),
            PatternVariable(
                name="action_type",
                type="action",
                domain="action",
                default="turn_on",
                description="Action to perform (turn_on/turn_off)",
                required=False
            )
        ],
        template="""id: '{automation_id}'
alias: '{alias}'
description: '{action_type_readable} {entity_name} at {time}'
mode: single
triggers:
  - trigger: time
    at: '{time}'
conditions: []
actions:
  - action: homeassistant.{action_type}
    target:
      entity_id: {entity}"""
    ),

    "sunset_lighting": PatternDefinition(
        id="sunset_lighting",
        name="Sunset/Sunrise Lighting",
        description="Turn lights on at sunset, off at sunrise",
        category="lighting",
        keywords=["sunset", "sunrise", "light", "evening", "morning", "sun", "dark"],
        priority=65,
        variables=[
            PatternVariable(
                name="lights",
                type="light",
                domain="light",
                description="Lights to control"
            ),
            PatternVariable(
                name="offset",
                type="duration",
                domain="duration",
                default="0",
                description="Minutes before/after sunset (negative for before)",
                required=False
            )
        ],
        template="""id: '{automation_id}'
alias: '{alias}'
description: 'Turn on {lights_name} at sunset'
mode: single
triggers:
  - trigger: sun
    event: sunset
    offset: '{offset_formatted}'
conditions: []
actions:
  - action: light.turn_on
    target:
      entity_id: {lights}
    data:
      brightness: 180"""
    ),

    "garage_door_auto_close": PatternDefinition(
        id="garage_door_auto_close",
        name="Garage Door Auto-Close",
        description="Close garage door if left open beyond timeout",
        category="security",
        keywords=["garage", "door", "close", "auto", "left open", "timeout"],
        priority=85,
        variables=[
            PatternVariable(
                name="garage_door",
                type="cover",
                domain="cover",
                device_class="garage",
                description="Garage door cover entity"
            ),
            PatternVariable(
                name="wait_time",
                type="duration",
                domain="duration",
                default="10",
                description="Minutes to wait before auto-closing",
                required=False
            )
        ],
        template="""id: '{automation_id}'
alias: '{alias}'
description: 'Auto-close {garage_name} if left open for {wait_time} minutes'
mode: single
triggers:
  - trigger: state
    entity_id: {garage_door}
    to: 'open'
conditions: []
actions:
  - wait_for_trigger:
      - trigger: state
        entity_id: {garage_door}
        to: 'closed'
    timeout: '00:{wait_time_padded}:00'
    continue_on_timeout: true
  - condition: state
    entity_id: {garage_door}
    state: 'open'
  - action: cover.close_cover
    target:
      entity_id: {garage_door}"""
    ),

    "appliance_completion_notify": PatternDefinition(
        id="appliance_completion_notify",
        name="Appliance Completion Notification",
        description="Notify when appliance (washer/dryer) completes",
        category="automation",
        keywords=["washer", "dryer", "dishwasher", "complete", "done", "finished", "notify"],
        priority=70,
        variables=[
            PatternVariable(
                name="power_sensor",
                type="sensor",
                domain="sensor",
                device_class="power",
                description="Power consumption sensor"
            ),
            PatternVariable(
                name="notification_service",
                type="notify",
                domain="notify",
                default="notify.mobile_app",
                description="Notification service",
                required=False
            ),
            PatternVariable(
                name="threshold",
                type="number",
                domain="number",
                default="5",
                description="Power threshold in watts (below = done)",
                required=False
            )
        ],
        template="""id: '{automation_id}'
alias: '{alias}'
description: 'Notify when {appliance_name} completes (power < {threshold}W)'
mode: single
triggers:
  - trigger: numeric_state
    entity_id: {power_sensor}
    below: {threshold}
    for:
      minutes: 2
conditions: []
actions:
  - action: {notification_service}
    data:
      title: 'Appliance Complete'
      message: '{{{{ trigger.to_state.attributes.friendly_name }}}} has finished!'"""
    ),

    "nighttime_motion_dim_light": PatternDefinition(
        id="nighttime_motion_dim_light",
        name="Nighttime Motion - Dim Light",
        description="Turn on light at low brightness during nighttime motion",
        category="lighting",
        keywords=["night", "motion", "dim", "low", "brightness", "bathroom", "hallway"],
        priority=80,
        variables=[
            PatternVariable(
                name="motion_sensor",
                type="binary_sensor",
                domain="binary_sensor",
                device_class="motion",
                description="Motion sensor"
            ),
            PatternVariable(
                name="light",
                type="light",
                domain="light",
                description="Light to control"
            ),
            PatternVariable(
                name="start_time",
                type="time",
                domain="time",
                default="22:00:00",
                description="Nighttime start time",
                required=False
            ),
            PatternVariable(
                name="end_time",
                type="time",
                domain="time",
                default="06:00:00",
                description="Nighttime end time",
                required=False
            )
        ],
        template="""id: '{automation_id}'
alias: '{alias}'
description: 'Dim {light_name} during nighttime motion'
mode: restart
triggers:
  - trigger: state
    entity_id: {motion_sensor}
    to: 'on'
conditions:
  - condition: time
    after: '{start_time}'
    before: '{end_time}'
actions:
  - action: light.turn_on
    target:
      entity_id: {light}
    data:
      brightness: 30
  - wait_for_trigger:
      - trigger: state
        entity_id: {motion_sensor}
        to: 'off'
        for:
          minutes: 2
    timeout: '00:10:00'
    continue_on_timeout: true
  - action: light.turn_off
    target:
      entity_id: {light}"""
    ),
}


def get_pattern(pattern_id: str) -> PatternDefinition | None:
    """Get pattern by ID"""
    return PATTERNS.get(pattern_id)


def get_all_patterns() -> dict[str, PatternDefinition]:
    """Get all available patterns"""
    return PATTERNS


def get_patterns_by_category(category: str) -> dict[str, PatternDefinition]:
    """Get patterns filtered by category"""
    return {
        pid: pattern
        for pid, pattern in PATTERNS.items()
        if pattern.category == category
    }


def generate_automation_id(pattern_id: str, variables: dict[str, str]) -> str:
    """Generate unique automation ID based on pattern and variables"""
    # Create deterministic ID from pattern + variables
    key = f"{pattern_id}_{'-'.join(sorted(variables.values()))}"
    hash_digest = hashlib.md5(key.encode()).hexdigest()
    # Take first 10 digits
    return hash_digest[:10]
