"""
OpenAI Function Schemas for Home Assistant Tools

2025 Preview-and-Approval Workflow:
1. preview_automation_from_prompt - Generate detailed preview (no execution)
2. create_automation_from_prompt - Execute approved automation creation
"""

HA_TOOLS = [
    {
        "type": "function",
        "function": {
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
        }
    },
    {
        "type": "function",
        "function": {
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
        }
    },
    {
        "type": "function",
        "function": {
            "name": "suggest_automation_enhancements",
            "description": "Generate 5 enhancement suggestions for an existing automation preview. Returns enhancements ranging from small tweaks to fun/crazy creative options. Use this when a user wants to see enhancement options for an automation preview. The enhancements include: 1-3 LLM-based (small, medium, large), 4 pattern-driven (advanced), and 5 synergy-driven (fun/crazy).",
            "parameters": {
                "type": "object",
                "properties": {
                    "automation_yaml": {
                        "type": "string",
                        "description": "The automation YAML to enhance. This should be the complete automation YAML from a preview."
                    },
                    "original_prompt": {
                        "type": "string",
                        "description": "The user's original request that generated this automation. Used for context when generating enhancements."
                    },
                    "conversation_id": {
                        "type": "string",
                        "description": "The conversation ID for tracking and context."
                    }
                },
                "required": ["automation_yaml", "original_prompt", "conversation_id"]
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
