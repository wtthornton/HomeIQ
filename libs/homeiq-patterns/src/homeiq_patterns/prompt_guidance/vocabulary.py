"""
Shared vocabulary and terminology for HomeIQ automation system.

Use these terms consistently across all prompts.
"""

# Core Terms
TERMS = {
    "automation": "A set of rules that control smart devices and respond to events",
    "home automation": "Automation for home environments (lights, climate, security, etc.)",
    "HomeIQ automation": "An automation created by HomeIQ, stored in HomeIQ JSON format",
    "HomeIQ JSON": "The standard JSON format for HomeIQ automations (schema: shared/homeiq_automation/schema.py)",
    "Home Assistant YAML": "YAML format for deploying automations to Home Assistant (deployment-only)",
    "deployment": "The process of converting HomeIQ JSON to YAML and deploying to Home Assistant",
}

# What to Use
USE_TERMS = {
    "automation creation": "Creating home automations",
    "HomeIQ JSON format": "HomeIQ JSON Automation format",
    "automation data": "Automation in HomeIQ JSON format",
    "automation metadata": "HomeIQ metadata (use_case, complexity, confidence_score, etc.)",
}

# What NOT to Use
AVOID_TERMS = {
    "Home Assistant automation": "Use 'home automation' or 'HomeIQ automation' instead",
    "YAML creation": "Use 'YAML generation' or 'YAML deployment' instead",
    "automation YAML": "Use 'automation JSON' or 'HomeIQ JSON' instead (YAML is deployment-only)",
    "creating YAML": "Use 'generating YAML from JSON' or 'deploying to YAML' instead",
}
