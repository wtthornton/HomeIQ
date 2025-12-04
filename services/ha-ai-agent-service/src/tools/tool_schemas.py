"""
OpenAI Function Schemas for Home Assistant Tools

Simplified to a single tool: create_automation_from_prompt
The agent's sole purpose is to take a user prompt and create a Home Assistant automation.
"""

HA_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_automation_from_prompt",
            "description": "Create a Home Assistant automation from a user's natural language prompt. This is the ONLY tool available. Use the provided Home Assistant context (entities, areas, services, capabilities) to generate valid automation YAML and create it in Home Assistant. The tool handles entity resolution, YAML validation, and automation creation automatically.",
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
