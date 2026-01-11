"""
Core principles for HomeIQ automation system.

All LLM prompts should incorporate these principles to ensure consistency.
"""

CORE_IDENTITY = """HomeIQ is an intelligent home automation platform that creates home automations.

HomeIQ creates automations that:
- Control smart devices (lights, thermostats, locks, etc.)
- Respond to events (motion, time, state changes)
- Automate home tasks (energy management, comfort, security, convenience)
- Work with any smart home platform (primarily Home Assistant for deployment)

HomeIQ does NOT:
- Create "Home Assistant automations" (Home Assistant is only the deployment platform)
- Create platform-specific automations
- Focus on YAML syntax (YAML is only for deployment)
"""

AUTOMATION_FORMAT_STANDARD = """HomeIQ uses HomeIQ JSON format as the standard automation format.

HomeIQ JSON Format:
- Primary format for automation creation, validation, storage, and communication
- Includes: triggers, conditions, actions, metadata, device context, safety checks, energy impact
- Schema defined in shared/homeiq_automation/schema.py
- All services should work with HomeIQ JSON format

Home Assistant YAML:
- Only used for deployment to Home Assistant
- Generated from HomeIQ JSON (not created directly)
- Only the HA AI Agent Service generates YAML (deployment service)
- YAML generation is a deployment concern, not an automation creation concern
"""

AUTOMATION_CREATION_FLOW = """Automation Creation Flow:

1. **Suggestion Generation** (Proactive Agent Service):
   - Generates natural language automation suggestions
   - Suggestions describe automations in plain English
   - Suggestions reference devices, triggers, and actions

2. **Automation Generation** (AI Automation Service New):
   - Converts suggestions/descriptions to HomeIQ JSON format
   - Uses HomeIQ JSON schema (HomeIQAutomation, HomeIQMetadata, DeviceContext, etc.)
   - Validates automation structure, devices, safety, energy impact
   - Stores automations in HomeIQ JSON format

3. **YAML Generation** (HA AI Agent Service):
   - Converts HomeIQ JSON to Home Assistant YAML (deployment-only)
   - Uses yaml_transformer.py for conversion
   - Validates YAML syntax and Home Assistant compatibility
   - Deploys YAML to Home Assistant

Key Point: YAML generation is the LAST step (deployment), not the first step (creation).
"""
