"""
HomeIQ-specific MCP tool definitions with real service URLs.
"""

from typing import List, Dict, Any


class HomeIQMCPTools:
    """Registry of HomeIQ MCP tools"""

    # Service URLs (from docker-compose network)
    DATA_API_URL = "http://data-api:8006"
    AI_AUTOMATION_URL = "http://ai-automation-service:8024"
    DEVICE_INTELLIGENCE_URL = "http://device-intelligence-service:8028"

    @staticmethod
    def get_data_api_tools() -> List[Dict[str, Any]]:
        """Get Data API MCP tools"""
        return [
            {
                "name": "query_device_history",
                "description": "Query historical state data for a device from InfluxDB",
                "server_url": HomeIQMCPTools.DATA_API_URL,
                "endpoint": "/mcp/tools/query_device_history",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "entity_id": {
                            "type": "string",
                            "description": "Device entity ID (e.g., 'sensor.power')"
                        },
                        "start_time": {
                            "type": "string",
                            "description": "Start time (e.g., '-7d', '2024-01-01T00:00:00Z')"
                        },
                        "end_time": {
                            "type": "string",
                            "description": "End time (e.g., 'now', '2024-01-07T00:00:00Z')"
                        },
                        "fields": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional fields to filter (e.g., ['state', 'value'])"
                        }
                    },
                    "required": ["entity_id", "start_time", "end_time"]
                }
            },
            {
                "name": "get_devices",
                "description": "Get all registered devices from SQLite metadata",
                "server_url": HomeIQMCPTools.DATA_API_URL,
                "endpoint": "/mcp/tools/get_devices",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "search_events",
                "description": "Search events by criteria (entity_id, event_type, time range)",
                "server_url": HomeIQMCPTools.DATA_API_URL,
                "endpoint": "/mcp/tools/search_events",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "entity_id": {"type": "string"},
                        "event_type": {"type": "string"},
                        "start_time": {"type": "string"},
                        "end_time": {"type": "string"},
                        "limit": {"type": "integer", "default": 100}
                    }
                }
            }
        ]

    @staticmethod
    def get_ai_automation_tools() -> List[Dict[str, Any]]:
        """Get AI Automation MCP tools"""
        return [
            {
                "name": "detect_patterns",
                "description": "Detect automation patterns in event data (time-based, co-occurrence, sequence)",
                "server_url": HomeIQMCPTools.AI_AUTOMATION_URL,
                "endpoint": "/mcp/tools/detect_patterns",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "start_time": {"type": "string"},
                        "end_time": {"type": "string"},
                        "pattern_types": {
                            "type": "array",
                            "items": {"enum": ["time-based", "co-occurrence", "sequence"]}
                        }
                    },
                    "required": ["start_time", "end_time"]
                }
            }
        ]

    @staticmethod
    def get_device_intelligence_tools() -> List[Dict[str, Any]]:
        """Get Device Intelligence MCP tools"""
        return [
            {
                "name": "get_device_capabilities",
                "description": "Get capabilities for a specific device (actions, features, supported services)",
                "server_url": HomeIQMCPTools.DEVICE_INTELLIGENCE_URL,
                "endpoint": "/mcp/tools/get_capabilities",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "entity_id": {"type": "string"}
                    },
                    "required": ["entity_id"]
                }
            }
        ]

    @classmethod
    def get_all_tools(cls) -> Dict[str, List[Dict]]:
        """Get all HomeIQ MCP tools organized by server"""
        return {
            "data": cls.get_data_api_tools(),
            "automation": cls.get_ai_automation_tools(),
            "device": cls.get_device_intelligence_tools()
        }
