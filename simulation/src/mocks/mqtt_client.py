"""
Mock MQTT Client

No-op implementation for simulation.
Maintains same interface as production MQTT client.
"""

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)


class MockMQTTClient:
    """
    Mock MQTT client for simulation.
    
    No-op implementation - all methods do nothing.
    Maintains same interface as production MQTT client.
    """

    def __init__(
        self,
        broker: str = "mock-broker",
        port: int = 1883,
        username: str | None = None,
        password: str | None = None
    ):
        """
        Initialize mock MQTT client.
        
        Args:
            broker: Mock broker address (not used)
            port: Mock port (not used)
            username: Mock username (not used)
            password: Mock password (not used)
        """
        self.broker = broker
        self.port = port
        self.username = username
        self.password = password
        self.is_connected = False
        
        logger.info(f"MockMQTTClient initialized: broker={broker}")

    async def connect(self) -> bool:
        """Connect to mock MQTT broker (no-op)."""
        self.is_connected = True
        logger.debug("MockMQTTClient connected")
        return True

    async def disconnect(self) -> None:
        """Disconnect from mock MQTT broker (no-op)."""
        self.is_connected = False
        logger.debug("MockMQTTClient disconnected")

    async def publish(self, topic: str, payload: str | bytes, qos: int = 0) -> None:
        """
        Publish message to mock MQTT broker (no-op).
        
        Args:
            topic: Topic name
            payload: Message payload
            qos: Quality of service level
        """
        logger.debug(f"MockMQTTClient: Would publish to {topic} (qos={qos})")

    async def subscribe(self, topic: str, callback: Callable[[str, str], None] | None = None) -> None:
        """
        Subscribe to mock MQTT topic (no-op).
        
        Args:
            topic: Topic name
            callback: Callback function (not used)
        """
        logger.debug(f"MockMQTTClient: Would subscribe to {topic}")

    async def unsubscribe(self, topic: str) -> None:
        """
        Unsubscribe from mock MQTT topic (no-op).
        
        Args:
            topic: Topic name
        """
        logger.debug(f"MockMQTTClient: Would unsubscribe from {topic}")

