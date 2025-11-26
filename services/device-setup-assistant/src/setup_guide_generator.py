"""
Setup Guide Generator
Phase 2.3: Generate step-by-step setup instructions for devices
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class SetupGuideGenerator:
    """Generates setup guides for devices"""

    def __init__(self):
        """Initialize guide generator"""
        self.guides = {}

    def generate_setup_guide(
        self,
        device_id: str,
        device_name: str,
        device_type: str | None,
        integration: str | None,
        setup_instructions_url: str | None = None
    ) -> dict[str, Any]:
        """
        Generate setup guide for a device.
        
        Args:
            device_id: Device identifier
            device_name: Device name
            device_type: Device type (from classification)
            integration: Integration/platform name
            setup_instructions_url: URL to external setup guide (from Device Database)
            
        Returns:
            Setup guide dictionary
        """
        steps = []
        
        # If external guide URL available, reference it
        if setup_instructions_url:
            steps.append({
                "step": 1,
                "title": "Follow Official Setup Guide",
                "description": f"Visit the official setup guide: {setup_instructions_url}",
                "type": "link"
            })
        
        # Generate generic steps based on integration
        if integration:
            if integration == "hue":
                steps.extend(self._hue_setup_steps())
            elif integration == "zwave":
                steps.extend(self._zwave_setup_steps())
            elif integration == "zigbee":
                steps.extend(self._zigbee_setup_steps())
            elif integration == "mqtt":
                steps.extend(self._mqtt_setup_steps())
            else:
                steps.extend(self._generic_setup_steps(integration))
        else:
            steps.extend(self._generic_setup_steps())
        
        return {
            "device_id": device_id,
            "device_name": device_name,
            "device_type": device_type,
            "integration": integration,
            "steps": steps,
            "estimated_time_minutes": len(steps) * 5
        }

    def _hue_setup_steps(self) -> list[dict[str, Any]]:
        """Hue-specific setup steps"""
        return [
            {
                "step": 1,
                "title": "Ensure Hue Bridge is Connected",
                "description": "Make sure your Philips Hue Bridge is powered on and connected to your network",
                "type": "check"
            },
            {
                "step": 2,
                "title": "Add Device in Home Assistant",
                "description": "Go to Settings > Devices & Services > Philips Hue and click 'Add Device'",
                "type": "action"
            },
            {
                "step": 3,
                "title": "Press Bridge Button",
                "description": "Press the button on your Hue Bridge when prompted",
                "type": "action"
            },
            {
                "step": 4,
                "title": "Verify Device Appears",
                "description": "Check that the device appears in your device list",
                "type": "verify"
            }
        ]

    def _zwave_setup_steps(self) -> list[dict[str, Any]]:
        """Z-Wave-specific setup steps"""
        return [
            {
                "step": 1,
                "title": "Put Device in Inclusion Mode",
                "description": "Follow manufacturer instructions to put device in inclusion/pairing mode",
                "type": "action"
            },
            {
                "step": 2,
                "title": "Start Z-Wave Inclusion",
                "description": "In Home Assistant, go to Z-Wave integration and click 'Add Device'",
                "type": "action"
            },
            {
                "step": 3,
                "title": "Wait for Inclusion",
                "description": "Wait for device to be discovered and added (may take 30-60 seconds)",
                "type": "wait"
            },
            {
                "step": 4,
                "title": "Verify Device",
                "description": "Check that device appears in device list with all expected entities",
                "type": "verify"
            }
        ]

    def _zigbee_setup_steps(self) -> list[dict[str, Any]]:
        """Zigbee-specific setup steps"""
        return [
            {
                "step": 1,
                "title": "Ensure Zigbee Coordinator is Running",
                "description": "Make sure your Zigbee coordinator (ZHA or Zigbee2MQTT) is running",
                "type": "check"
            },
            {
                "step": 2,
                "title": "Put Device in Pairing Mode",
                "description": "Follow manufacturer instructions to put device in pairing mode",
                "type": "action"
            },
            {
                "step": 3,
                "title": "Start Pairing in Home Assistant",
                "description": "In ZHA or Zigbee2MQTT integration, click 'Add Device' or 'Permit Join'",
                "type": "action"
            },
            {
                "step": 4,
                "title": "Wait for Discovery",
                "description": "Wait for device to be discovered (may take 1-2 minutes)",
                "type": "wait"
            }
        ]

    def _mqtt_setup_steps(self) -> list[dict[str, Any]]:
        """MQTT-specific setup steps"""
        return [
            {
                "step": 1,
                "title": "Configure MQTT Broker",
                "description": "Ensure MQTT broker is configured in Home Assistant",
                "type": "check"
            },
            {
                "step": 2,
                "title": "Configure Device MQTT Settings",
                "description": "Configure device to connect to your MQTT broker",
                "type": "action"
            },
            {
                "step": 3,
                "title": "Verify MQTT Discovery",
                "description": "Check that device is discovered via MQTT discovery",
                "type": "verify"
            }
        ]

    def _generic_setup_steps(self, integration: str | None = None) -> list[dict[str, Any]]:
        """Generic setup steps"""
        steps = [
            {
                "step": 1,
                "title": "Check Device Power",
                "description": "Ensure device is powered on and connected",
                "type": "check"
            },
            {
                "step": 2,
                "title": "Add Integration",
                "description": f"Add {integration or 'the appropriate'} integration in Home Assistant" if integration else "Add the appropriate integration in Home Assistant",
                "type": "action"
            },
            {
                "step": 3,
                "title": "Follow Integration Instructions",
                "description": "Follow the integration-specific setup instructions",
                "type": "action"
            },
            {
                "step": 4,
                "title": "Verify Device",
                "description": "Check that device appears in device list",
                "type": "verify"
            }
        ]
        return steps

