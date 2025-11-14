"""
Test blueprint parser with real blueprint YAML from HA docs
"""
import sys
sys.path.insert(0, 'src')

from miner.parser import AutomationParser

# Real blueprint example from https://www.home-assistant.io/docs/blueprint/tutorial/
BLUEPRINT_YAML = """
blueprint:
  name: Motion-activated Light
  description: Turn on a light when motion is detected.
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
      name: Wait time
      description: Time to leave the light on after last motion is detected.
      default: 120
      selector:
        number:
          min: 0
          max: 3600
          unit_of_measurement: seconds

# Automation structure at root level
trigger:
  - platform: state
    entity_id: !input motion_entity
    from: "off"
    to: "on"

action:
  - service: light.turn_on
    target: !input light_target
  - wait_for_trigger:
      - platform: state
        entity_id: !input motion_entity
        from: "on"
        to: "off"
    timeout:
      seconds: !input no_motion_wait
  - service: light.turn_off
    target: !input light_target
"""

# More complex blueprint with multiple device types
COMPLEX_BLUEPRINT_YAML = """
blueprint:
  name: Climate Control with Door Sensor
  description: Pause climate control when door opens, resume when closed.
  domain: automation
  input:
    door_sensor:
      name: Door Sensor
      selector:
        entity:
          domain: binary_sensor
          device_class: door
    climate_entity:
      name: Climate Device
      selector:
        entity:
          domain: climate
    pause_time:
      name: Pause Duration
      default: 300
      selector:
        number:
          min: 60
          max: 3600
          unit_of_measurement: seconds

trigger:
  - platform: state
    entity_id: !input door_sensor
    to: "on"

action:
  - service: climate.set_hvac_mode
    target:
      entity_id: !input climate_entity
    data:
      hvac_mode: "off"
  - wait_for_trigger:
      - platform: state
        entity_id: !input door_sensor
        to: "off"
    timeout:
      seconds: !input pause_time
  - service: climate.set_hvac_mode
    target:
      entity_id: !input climate_entity
    data:
      hvac_mode: "auto"
"""

def test_parser():
    """Test blueprint parsing"""
    parser = AutomationParser()

    print("=" * 80)
    print("TEST 1: Motion-Activated Light Blueprint")
    print("=" * 80)

    parsed = parser.parse_yaml(BLUEPRINT_YAML)

    if parsed:
        print("\n✅ Blueprint parsed successfully!\n")

        print("Blueprint Metadata:")
        if '_blueprint_metadata' in parsed:
            meta = parsed['_blueprint_metadata']
            print(f"  Name: {meta.get('name')}")
            print(f"  Description: {meta.get('description')}")
            print(f"  Domain: {meta.get('domain')}")

        print("\nExtracted Variables:")
        if '_blueprint_variables' in parsed:
            for var_name, var_info in parsed['_blueprint_variables'].items():
                print(f"  {var_name}:")
                print(f"    Domain: {var_info.get('domain', var_info.get('type'))}")
                print(f"    Device Class: {var_info.get('device_class', 'N/A')}")

        print("\nExtracted Devices:")
        if '_blueprint_devices' in parsed:
            devices = parsed['_blueprint_devices']
            print(f"  {devices}")

        print("\nTriggers:")
        triggers = parsed.get('trigger', [])
        print(f"  Count: {len(triggers)}")
        for i, trigger in enumerate(triggers, 1):
            print(f"  {i}. Platform: {trigger.get('platform')}")

        print("\nActions:")
        actions = parsed.get('action', [])
        print(f"  Count: {len(actions)}")
        for i, action in enumerate(actions, 1):
            service = action.get('service', action.get('wait_for_trigger', 'wait_for_trigger' if 'wait_for_trigger' in action else 'unknown'))
            print(f"  {i}. Type: {service}")

        # Test device extraction
        print("\nDevice Extraction Test:")
        devices = parser.extract_devices(parsed)
        print(f"  Extracted devices: {devices}")

        # Test use case classification
        use_case = parser.classify_use_case(parsed, "Motion-activated Light", "Turn on a light when motion is detected")
        print(f"  Classified use case: {use_case}")

        # Test complexity calculation
        complexity = parser.calculate_complexity(parsed)
        print(f"  Complexity: {complexity}")

    else:
        print("\n❌ Failed to parse blueprint!")

    print("\n" + "=" * 80)
    print("TEST 2: Complex Climate Control Blueprint")
    print("=" * 80)

    parsed2 = parser.parse_yaml(COMPLEX_BLUEPRINT_YAML)

    if parsed2:
        print("\n✅ Blueprint parsed successfully!\n")

        print("Extracted Devices:")
        devices = parser.extract_devices(parsed2)
        print(f"  {devices}")

        print("\nBlueprint Variables:")
        if '_blueprint_variables' in parsed2:
            for var_name, var_info in parsed2['_blueprint_variables'].items():
                print(f"  {var_name}: {var_info.get('domain', var_info.get('type'))}")

        print("\nTriggers: {}", len(parsed2.get('trigger', [])))
        print(f"Actions: {len(parsed2.get('action', []))}")

        use_case = parser.classify_use_case(parsed2, "Climate Control", "Pause climate when door opens")
        print(f"Use Case: {use_case}")

    else:
        print("\n❌ Failed to parse blueprint!")

if __name__ == "__main__":
    test_parser()
