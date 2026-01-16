"""
Tool Execution Service

Handles OpenAI tool calls and routes to appropriate handlers.
Implements tool call routing, result formatting, and error handling.
"""

import logging
from typing import Any

from typing import Any

from ..clients.ai_automation_client import AIAutomationClient
from ..clients.data_api_client import DataAPIClient
from ..clients.ha_client import HomeAssistantClient
from ..clients.hybrid_flow_client import HybridFlowClient
from ..clients.yaml_validation_client import YAMLValidationClient
from ..tools.ha_tools import HAToolHandler

logger = logging.getLogger(__name__)


class ToolService:
    """
    Service for executing OpenAI tool calls.

    Routes tool calls to appropriate handlers and formats results for OpenAI.
    """

    def __init__(
        self,
        ha_client: HomeAssistantClient,
        data_api_client: DataAPIClient,
        ai_automation_client: AIAutomationClient | None = None,
        yaml_validation_client: YAMLValidationClient | None = None,
        openai_client: Any = None
    ):
        """
        Initialize tool service.

        Args:
            ha_client: Home Assistant API client
            data_api_client: Data API client for entity queries
            ai_automation_client: AI Automation Service client (legacy, optional)
            yaml_validation_client: YAML Validation Service client for comprehensive validation (Epic 51, optional)
            openai_client: OpenAI client for enhancement generation (optional)
        """
        self.ha_client = ha_client
        self.data_api_client = data_api_client
        self.tool_handler = HAToolHandler(ha_client, data_api_client, ai_automation_client, yaml_validation_client, openai_client)

        # Map tool names to handler methods
        # 2025 Preview-and-Approval Workflow
        self.tool_handlers = {
            "preview_automation_from_prompt": self.tool_handler.preview_automation_from_prompt,
            "create_automation_from_prompt": self.tool_handler.create_automation_from_prompt,
            "suggest_automation_enhancements": self.tool_handler.suggest_automation_enhancements,
        }

        logger.info(f"ToolService initialized with {len(self.tool_handlers)} tool(s)")

    async def execute_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Execute a tool call and return formatted result.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments (parsed from OpenAI function call)

        Returns:
            Dictionary with tool execution result, formatted for OpenAI
        """
        if tool_name not in self.tool_handlers:
            logger.warning(f"Unknown tool requested: {tool_name}")
            return {
                "error": f"Unknown tool: {tool_name}",
                "available_tools": list(self.tool_handlers.keys())
            }

        try:
            logger.info(f"Executing tool: {tool_name} with arguments: {arguments}")

            # Get handler method
            handler = self.tool_handlers[tool_name]

            # Execute tool
            result = await handler(arguments)

            # Log result (without sensitive data)
            if result.get("success"):
                logger.info(f"Tool {tool_name} executed successfully")
            else:
                logger.warning(f"Tool {tool_name} returned error: {result.get('error', 'Unknown error')}")

            return result

        except ValueError as e:
            # Validation errors
            logger.warning(f"Tool {tool_name} validation error: {e}")
            return {
                "success": False,
                "error": f"Validation error: {str(e)}",
                "tool": tool_name
            }
        except Exception as e:
            # Unexpected errors
            logger.error(f"Tool {tool_name} execution failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Tool execution failed: {str(e)}",
                "tool": tool_name
            }

    async def execute_tool_call(
        self,
        tool_call: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Execute a tool call from OpenAI format.

        Args:
            tool_call: OpenAI tool call format:
                {
                    "id": "call_...",
                    "type": "function",
                    "function": {
                        "name": "tool_name",
                        "arguments": "{\"key\": \"value\"}"
                    }
                }

        Returns:
            Dictionary with tool execution result
        """
        import json

        try:
            # Extract tool name and arguments
            function = tool_call.get("function", {})
            tool_name = function.get("name")
            arguments_str = function.get("arguments", "{}")

            if not tool_name:
                return {
                    "success": False,
                    "error": "Tool name not provided in tool call"
                }

            # Parse arguments JSON
            try:
                arguments = json.loads(arguments_str) if isinstance(arguments_str, str) else arguments_str
            except json.JSONDecodeError as e:
                return {
                    "success": False,
                    "error": f"Invalid JSON in tool arguments: {str(e)}"
                }

            # Execute tool
            result = await self.execute_tool(tool_name, arguments)

            # Add tool call ID for OpenAI response format
            result["tool_call_id"] = tool_call.get("id")

            return result

        except Exception as e:
            logger.error(f"Error processing tool call: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Tool call processing failed: {str(e)}"
            }

    def get_available_tools(self) -> list[str]:
        """
        Get list of available tool names.

        Returns:
            List of tool function names
        """
        return list(self.tool_handlers.keys())

