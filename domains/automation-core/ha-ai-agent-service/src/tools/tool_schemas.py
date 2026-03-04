"""
OpenAI Function Schemas for Home Assistant Tools

2025 Preview-and-Approval Workflow:
1. preview_automation_from_prompt - Generate detailed preview (no execution)
2. create_automation_from_prompt - Execute approved automation creation

Migrated to Responses API format (Feb 2026):
- Tool definitions flattened: name/description/parameters at top level
- No nested "function" wrapper
"""

HA_TOOLS = [
    {
        "type": "function",
        "name": "preview_automation_from_prompt",
        "description": "Generate a detailed preview of a Home Assistant automation from a user's natural language prompt. This tool ONLY generates a preview - it does NOT create the automation. Use this tool FIRST when a user requests an automation. The preview includes automation details, YAML, entities affected, and safety considerations. Wait for user approval before calling create_automation_from_prompt.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_prompt": {
                    "type": "string",
                    "description": "The user's natural language request for an automation (e.g., 'Make the office lights blink red every 15 minutes and then return back to the state they were'). Use this exact prompt to understand what automation to create."
                },
                "automation_yaml": {
                    "type": "string",
                    "description": "Complete Home Assistant automation YAML configuration. Must be valid YAML with required fields: alias, description, trigger, action. Include initial_state: true, proper mode selection, and use entities/areas/services from the provided context. Follow Home Assistant 2025.10+ format."
                },
                "alias": {
                    "type": "string",
                    "description": "Human-readable name for the automation. Should be descriptive and match the user's intent (e.g., 'Office lights blink red every 15 minutes')."
                }
            },
            "required": ["user_prompt", "automation_yaml", "alias"]
        }
    },
    {
        "type": "function",
        "name": "create_automation_from_prompt",
        "description": "Create a Home Assistant automation from a user's natural language prompt. This tool ACTUALLY CREATES the automation in Home Assistant. ONLY call this tool after the user has approved a preview (via preview_automation_from_prompt). Use the provided Home Assistant context (entities, areas, services, capabilities) to generate valid automation YAML. The tool handles entity resolution, YAML validation, and automation creation automatically.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_prompt": {
                    "type": "string",
                    "description": "The user's natural language request for an automation (e.g., 'Make the office lights blink red every 15 minutes and then return back to the state they were'). Use this exact prompt to understand what automation to create."
                },
                "automation_yaml": {
                    "type": "string",
                    "description": "Complete Home Assistant automation YAML configuration. Must be valid YAML with required fields: alias, description, trigger, action. Include initial_state: true, proper mode selection, and use entities/areas/services from the provided context. Follow Home Assistant 2025.10+ format."
                },
                "alias": {
                    "type": "string",
                    "description": "Human-readable name for the automation. Should be descriptive and match the user's intent (e.g., 'Office lights blink red every 15 minutes')."
                }
            },
            "required": ["user_prompt", "automation_yaml", "alias"]
        }
    },
    {
        "type": "function",
        "name": "suggest_automation_enhancements",
        "description": "Generate 5 enhancement suggestions. Supports two modes: (1) Prompt enhancement - enhance user prompts before YAML generation (no YAML required), (2) YAML enhancement - enhance existing automation YAML (YAML required). Returns enhancements ranging from small tweaks to fun/crazy creative options. The enhancements include: 1-3 LLM-based (small, medium, large), 4 pattern-driven (advanced), and 5 synergy-driven (fun/crazy).",
        "parameters": {
            "type": "object",
            "properties": {
                "automation_yaml": {
                    "type": "string",
                    "description": "The automation YAML to enhance (optional). If provided, enhances the YAML. If omitted, enhances the original prompt instead."
                },
                "original_prompt": {
                    "type": "string",
                    "description": "The user's original request. Required for both prompt and YAML enhancement modes."
                },
                "conversation_id": {
                    "type": "string",
                    "description": "The conversation ID for tracking and context."
                }
            },
            "required": ["original_prompt", "conversation_id"]
        }
    }
]

# -------------------------------------------------------------------------
# Device Control Tools (Epic 25 — Direct HA device control via ha-device-control service)
# -------------------------------------------------------------------------

DEVICE_CONTROL_TOOLS = [
    {
        "type": "function",
        "name": "control_light",
        "description": "Control a specific light — turn on/off, set brightness (0-100), or set RGB color. Use this for IMMEDIATE light control when the user says things like 'turn off the kitchen light' or 'set bedroom to 50%'. Do NOT use this for automation rules (use preview_automation_from_prompt for those).",
        "parameters": {
            "type": "object",
            "properties": {
                "entity_id_or_name": {
                    "type": "string",
                    "description": "Light entity ID (e.g., 'light.kitchen') or friendly name (e.g., 'Kitchen Light')"
                },
                "brightness": {
                    "type": "integer",
                    "description": "Brightness 0-100 (0 = off, 100 = full). Required."
                },
                "rgb": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Optional RGB color as [R, G, B] with values 0-255 (e.g., [255, 0, 0] for red)"
                }
            },
            "required": ["entity_id_or_name", "brightness"]
        }
    },
    {
        "type": "function",
        "name": "control_light_area",
        "description": "Control ALL lights in an area/room — set brightness or color for every light at once. Use for requests like 'turn off all living room lights' or 'set bedroom lights to blue'.",
        "parameters": {
            "type": "object",
            "properties": {
                "area": {
                    "type": "string",
                    "description": "Area/room name (e.g., 'Living Room', 'Bedroom', 'Kitchen')"
                },
                "brightness": {
                    "type": "integer",
                    "description": "Brightness 0-100 (0 = off)"
                },
                "rgb": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Optional RGB color as [R, G, B] with values 0-255"
                }
            },
            "required": ["area", "brightness"]
        }
    },
    {
        "type": "function",
        "name": "control_switch",
        "description": "Turn a switch on or off. Use for requests like 'turn on the fan' or 'turn off the heater'.",
        "parameters": {
            "type": "object",
            "properties": {
                "entity_id_or_name": {
                    "type": "string",
                    "description": "Switch entity ID or friendly name"
                },
                "state": {
                    "type": "string",
                    "enum": ["on", "off"],
                    "description": "Desired state"
                }
            },
            "required": ["entity_id_or_name", "state"]
        }
    },
    {
        "type": "function",
        "name": "get_climate",
        "description": "Get current thermostat/climate status for all zones. Shows current temperature, target temperature, and HVAC mode. Use when user asks about temperature or thermostat.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "type": "function",
        "name": "set_climate",
        "description": "Set thermostat temperature or HVAC mode. Use for requests like 'set temperature to 72' or 'turn on heating'.",
        "parameters": {
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "Climate entity ID (e.g., 'climate.living_room'). Use get_climate first to find available entities."
                },
                "temperature": {
                    "type": "number",
                    "description": "Target temperature in the entity's native unit"
                },
                "hvac_mode": {
                    "type": "string",
                    "description": "Optional HVAC mode: heat, cool, auto, off, fan_only, dry"
                }
            },
            "required": ["entity_id", "temperature"]
        }
    },
    {
        "type": "function",
        "name": "activate_scene",
        "description": "Activate a Home Assistant scene or run a script by name. Use when user says 'activate movie night' or 'run bedtime routine'.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Scene or script name (e.g., 'movie_night', 'bedtime')"
                }
            },
            "required": ["name"]
        }
    },
    {
        "type": "function",
        "name": "house_status",
        "description": "Get a comprehensive snapshot of the current home status: climate, presence, lights by area, doors/windows, motion sensors, active switches, and automations. Use when user asks 'what's the status of the house?' or 'are any lights on?'.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "type": "function",
        "name": "send_notification",
        "description": "Send a push notification to the user's phone via Home Assistant mobile app. Use when user says 'remind me' or 'send me a notification'.",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Notification message body"
                },
                "title": {
                    "type": "string",
                    "description": "Optional notification title"
                }
            },
            "required": ["message"]
        }
    }
]


def get_tool_schemas() -> list[dict]:
    """
    Get all tool schemas for OpenAI function calling.

    Returns:
        List of tool schema dictionaries compatible with OpenAI Responses API
    """
    return HA_TOOLS + DEVICE_CONTROL_TOOLS


def get_tool_names() -> list[str]:
    """
    Get list of available tool names.

    Returns:
        List of tool function names
    """
    return [tool["name"] for tool in HA_TOOLS]
