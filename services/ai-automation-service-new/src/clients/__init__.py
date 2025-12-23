"""
HTTP Clients for External Services

Epic 39, Story 39.10: Automation Service Foundation
Clients for communicating with other microservices.
"""

from .data_api_client import DataAPIClient
from .ha_client import HomeAssistantClient
from .openai_client import OpenAIClient

__all__ = [
    "DataAPIClient",
    "HomeAssistantClient",
    "OpenAIClient",
]

