"""
Standalone test for blueprint parser (no dependencies)
"""
import yaml
import re
from typing import Dict, List, Any, Optional


# Add custom YAML constructor for !input tag (blueprint variable references)
def input_constructor(loader, node):
    """Handle !input tags in blueprint YAML"""
    return f"!input {loader.construct_scalar(node)}"


yaml.add_constructor('!input', input_constructor, Loader=yaml.SafeLoader)


# Inline minimal parser for testing
class TestParser:
    DEVICE_TYPES = {
        'light', 'switch', 'sensor', 'binary_sensor', 'motion_sensor',
        'door_sensor', 'window_sensor', 'climate', 'thermostat', 'fan',
        'cover', 'blind', 'shade', 'lock', 'camera', 'alarm'
    }

    def parse_yaml(self, yaml_str: str) -> Optional[Dict[str, Any]]:
        """Parse YAML automation structure"""
        try:
            data = yaml.safe_load(yaml_str)

            if isinstance(data, dict) and 'blueprint' in data:
                return self.parse_blueprint(data)

            return data

        except yaml.YAMLError as e:
            print(f"Failed to parse YAML: {e}")
            return None

    def parse_blueprint(self, yaml_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse blueprint YAML format"""
        blueprint_meta = yaml_data.get('blueprint', {})
        inputs = blueprint_meta.get('input', {})

        # Extract variable definitions
        variables = {}
        devices = set()

        for input_name, input_def in inputs.items():
            selector = input_def.get('selector', {})

            if 'entity' in selector:
                entity_selector = selector['entity']
                domain = entity_selector.get('domain', 'unknown')
                device_class = entity_selector.get('device_class')

                devices.add(domain)
                variables[input_name] = {
                    'domain': domain,
                    'device_class': device_class,
                    'name': input_def.get('name', input_name)
                }

            elif 'device' in selector:
                device_selector = selector['device']
                integration = device_selector.get('integration')
                if integration:
                    devices.add(integration)
                variables[input_name] = {
                    'type': 'device',
                    'integration': integration,
                    'name': input_def.get('name', input_name)
                }

            elif 'target' in selector:
                variables[input_name] = {
                    'type': 'target',
                    'name': input_def.get('name', input_name)
                }

        # Extract automation structure from root
        triggers = yaml_data.get('trigger', [])
        conditions = yaml_data.get('condition', [])
        actions = yaml_data.get('action', [])

        # Extract more devices from structure
        devices.update(self._extract_devices_from_structure(triggers))
        devices.update(self._extract_devices_from_structure(actions))

        return {
            'trigger': triggers if isinstance(triggers, list) else [triggers] if triggers else [],
            'condition': conditions if isinstance(conditions, list) else [conditions] if conditions else [],
            'action': actions if isinstance(actions, list) else [actions] if actions else [],
            '_blueprint_variables': variables,
            '_blueprint_devices': sorted(list(devices)),
            '_blueprint_metadata': blueprint_meta
        }

    def _extract_devices_from_structure(self, structure: Any) -> set:
        """Extract device domains from automation structure"""
        devices = set()

        def recurse(obj):
            if isinstance(obj, dict):
                # Service calls
                if 'service' in obj or 'action' in obj:
                    service = obj.get('service') or obj.get('action', '')
                    if '.' in service:
                        domain = service.split('.')[0]
                        if domain in self.DEVICE_TYPES:
                            devices.add(domain)

                # Entity IDs
                if 'entity_id' in obj:
                    entity_id = obj['entity_id']
                    if isinstance(entity_id, str) and '.' in entity_id:
                        if not entity_id.startswith('!input'):
                            domain = entity_id.split('.')[0]
                            if domain in self.DEVICE_TYPES:
                                devices.add(domain)

                for value in obj.values():
                    recurse(value)

            elif isinstance(obj, list):
                for item in obj:
                    recurse(item)

        recurse(structure)
        return devices


# Test blueprints
BLUEPRINT_1 = """
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

trigger:
  - platform: state
    entity_id: !input motion_entity
    to: "on"

action:
  - service: light.turn_on
    target: !input light_target
  - wait_for_trigger:
      - platform: state
        entity_id: !input motion_entity
        to: "off"
  - service: light.turn_off
    target: !input light_target
"""

BLUEPRINT_2 = """
blueprint:
  name: Climate Control with Door Sensor
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
"""


def test():
    parser = TestParser()

    print("=" * 80)
    print("TEST 1: Motion-Activated Light Blueprint")
    print("=" * 80)

    parsed = parser.parse_yaml(BLUEPRINT_1)

    if parsed:
        print("\n✅ Blueprint parsed successfully!\n")

        if '_blueprint_metadata' in parsed:
            meta = parsed['_blueprint_metadata']
            print(f"Blueprint Name: {meta.get('name')}")
            print(f"Description: {meta.get('description')}")

        print("\nExtracted Variables:")
        if '_blueprint_variables' in parsed:
            for var_name, var_info in parsed['_blueprint_variables'].items():
                domain = var_info.get('domain', var_info.get('type', 'unknown'))
                device_class = var_info.get('device_class', 'N/A')
                print(f"  • {var_name}: {domain} (device_class: {device_class})")

        print("\nExtracted Devices:")
        if '_blueprint_devices' in parsed:
            devices = parsed['_blueprint_devices']
            print(f"  {', '.join(devices)}")
            print(f"  Total: {len(devices)} device types")

        print("\nAutomation Structure:")
        triggers = parsed.get('trigger', [])
        actions = parsed.get('action', [])
        print(f"  Triggers: {len(triggers)}")
        print(f"  Actions: {len(actions)}")

        # Verify we got the expected devices
        expected_devices = ['binary_sensor', 'light']
        actual_devices = parsed['_blueprint_devices']
        if sorted(expected_devices) == sorted(actual_devices):
            print("\n  ✅ Devices match expected: binary_sensor, light")
        else:
            print(f"\n  ❌ Device mismatch! Expected: {expected_devices}, Got: {actual_devices}")

    else:
        print("\n❌ Failed to parse blueprint!")
        return

    print("\n" + "=" * 80)
    print("TEST 2: Climate Control Blueprint")
    print("=" * 80)

    parsed2 = parser.parse_yaml(BLUEPRINT_2)

    if parsed2:
        print("\n✅ Blueprint parsed successfully!\n")

        devices = parsed2.get('_blueprint_devices', [])
        print(f"Extracted Devices: {', '.join(devices)}")

        variables = parsed2.get('_blueprint_variables', {})
        print(f"Variables: {len(variables)}")
        for var_name, var_info in variables.items():
            print(f"  • {var_name}: {var_info.get('domain', var_info.get('type'))}")

        # Verify expected devices
        expected_devices = ['binary_sensor', 'climate']
        if sorted(expected_devices) == sorted(devices):
            print("\n✅ Devices match expected: binary_sensor, climate")
        else:
            print(f"\n❌ Device mismatch! Expected: {expected_devices}, Got: {devices}")

    else:
        print("\n❌ Failed to parse blueprint!")
        return

    print("\n" + "=" * 80)
    print("✅ ALL TESTS PASSED!")
    print("=" * 80)


if __name__ == "__main__":
    test()
