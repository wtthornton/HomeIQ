"""
OpenAI Function Schemas for Home Assistant Tools

Following 2025 best practices for tool calling:
- Clear, specific function names
- Detailed descriptions explaining when to use each tool
- Complete parameter schemas with types, constraints, enums
- Required vs optional parameters clearly marked
"""

HA_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_entity_state",
            "description": "Get the current state and attributes of a Home Assistant entity. Use this when you need real-time entity information not available in the context, or to verify entity states before creating automations. Prefer using context when information is already available.",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": "The entity ID (e.g., 'light.kitchen', 'sensor.temperature'). Must follow pattern: domain.entity_id",
                        "pattern": "^[a-z_]+\\.[a-z0-9_]+$"
                    }
                },
                "required": ["entity_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "call_service",
            "description": "Call a Home Assistant service to control devices or perform actions. Use this to test service calls or execute immediate actions requested by the user. For automations, prefer creating automation YAML instead of calling services directly.",
            "parameters": {
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": "Service domain (e.g., 'light', 'switch', 'climate', 'cover', 'fan', 'lock', 'media_player', 'scene')",
                        "enum": [
                            "light", "switch", "climate", "cover", "fan", "lock",
                            "media_player", "scene", "input_boolean", "input_number",
                            "input_select", "input_text", "automation", "script"
                        ]
                    },
                    "service": {
                        "type": "string",
                        "description": "Service name (e.g., 'turn_on', 'turn_off', 'set_temperature', 'toggle')"
                    },
                    "entity_id": {
                        "type": "string",
                        "description": "Target entity ID (optional if using area_id or device_id). Can be a single entity or list of entities."
                    },
                    "area_id": {
                        "type": "string",
                        "description": "Target area ID (optional, alternative to entity_id). Affects all entities in the area."
                    },
                    "device_id": {
                        "type": "string",
                        "description": "Target device ID (optional, alternative to entity_id). Affects all entities in the device."
                    },
                    "service_data": {
                        "type": "object",
                        "description": "Additional service parameters (e.g., brightness, temperature, color). Structure depends on the service."
                    }
                },
                "required": ["domain", "service"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_entities",
            "description": "Search for entities by domain, area, or name. Use this when the user mentions a device not in the context, or to find entities matching a description. Returns entity IDs, friendly names, and current states.",
            "parameters": {
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": "Filter by domain (e.g., 'light', 'sensor', 'switch'). Optional - if not provided, searches all domains."
                    },
                    "area_id": {
                        "type": "string",
                        "description": "Filter by area ID (e.g., 'kitchen', 'bedroom'). Optional - if not provided, searches all areas."
                    },
                    "search_term": {
                        "type": "string",
                        "description": "Search in entity friendly names or aliases. Supports partial matches. Optional - if not provided, returns all matching entities."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_automation",
            "description": "Create a new Home Assistant automation. Use this when the user explicitly asks to create or save an automation. Always validate the YAML syntax before calling this tool using test_automation_yaml. Returns the created automation ID and status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "automation_yaml": {
                        "type": "string",
                        "description": "Complete Home Assistant automation YAML configuration. Must be valid YAML with required fields: id (optional, auto-generated), alias, description, trigger, action. May include conditions, mode, initial_state, etc."
                    },
                    "alias": {
                        "type": "string",
                        "description": "Human-readable name for the automation. Used for identification and display in Home Assistant UI."
                    }
                },
                "required": ["automation_yaml", "alias"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_automation",
            "description": "Update an existing Home Assistant automation. Use this when the user wants to modify an existing automation. Requires the automation ID and new YAML configuration. Always validate YAML syntax first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "automation_id": {
                        "type": "string",
                        "description": "The ID of the automation to update (e.g., 'automation.morning_lights')"
                    },
                    "automation_yaml": {
                        "type": "string",
                        "description": "Updated Home Assistant automation YAML configuration. Must be valid YAML."
                    }
                },
                "required": ["automation_id", "automation_yaml"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_automation",
            "description": "Delete a Home Assistant automation. Use this when the user explicitly asks to delete or remove an automation. Returns confirmation of deletion.",
            "parameters": {
                "type": "object",
                "properties": {
                    "automation_id": {
                        "type": "string",
                        "description": "The ID of the automation to delete (e.g., 'automation.morning_lights')"
                    }
                },
                "required": ["automation_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_automations",
            "description": "List all Home Assistant automations. Use this when the user asks about existing automations, wants to see what automations are configured, or needs to reference an automation ID for updates/deletes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "search_term": {
                        "type": "string",
                        "description": "Optional search term to filter automations by alias or description. If not provided, returns all automations."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "test_automation_yaml",
            "description": "Validate Home Assistant automation YAML syntax without creating the automation. Use this before creating or updating automations to catch syntax errors early. Returns validation result with any errors found.",
            "parameters": {
                "type": "object",
                "properties": {
                    "automation_yaml": {
                        "type": "string",
                        "description": "Automation YAML to validate. Must be valid YAML format with required fields: alias, trigger, action."
                    }
                },
                "required": ["automation_yaml"]
            }
        }
    }
]


def get_tool_schemas() -> list[dict]:
    """
    Get all tool schemas for OpenAI function calling.

    Returns:
        List of tool schema dictionaries compatible with OpenAI API
    """
    return HA_TOOLS


def get_tool_names() -> list[str]:
    """
    Get list of available tool names.

    Returns:
        List of tool function names
    """
    return [tool["function"]["name"] for tool in HA_TOOLS]

