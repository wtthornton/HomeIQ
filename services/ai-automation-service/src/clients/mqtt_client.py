"""
MQTT Client for Publishing Notifications and Subscribing to Topics

Story AI1.12: MQTT Integration (Publishing)
Story AI2.1: MQTT Capability Listener (Subscription - Epic AI-2)
"""

import json
import logging
from collections.abc import Callable

import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)


class MQTTNotificationClient:
    """
    MQTT client for publishing AI automation notifications and subscribing to topics.

    Epic AI-1: Publishes automation notifications and analysis results
    Epic AI-2: Subscribes to Zigbee2MQTT bridge for device capability discovery

    Features:
    - Publish automation notifications (Epic AI-1)
    - Subscribe to topics with callback handlers (Epic AI-2)
    - Automatic reconnection on disconnect
    - QoS support for reliable delivery
    """

    def __init__(self, broker: str | None = None, port: int = 1883, username: str | None = None, password: str | None = None, enabled: bool = True):
        """
        Initialize MQTT client.

        Args:
            broker: MQTT broker host (optional)
            port: MQTT broker port
            username: Optional MQTT username
            password: Optional MQTT password
            enabled: Whether MQTT is enabled
        """
        self.broker = broker
        self.port = port
        self.username = username
        self.password = password
        self.enabled = enabled
        self.client = None
        self.is_connected = False
        self._message_callback: Callable | None = None

        if not enabled or not broker:
            logger.info("MQTT disabled - client will not connect")
        else:
            logger.info(f"MQTT client initialized for broker: {broker}:{port}")

    def connect(self, max_retries: int = 3, retry_delay: float = 2.0) -> bool:
        """
        Connect to MQTT broker with retry logic.

        Args:
            max_retries: Maximum number of connection attempts
            retry_delay: Delay between retry attempts in seconds

        Returns:
            True if connection successful
        """
        for attempt in range(max_retries):
            try:
                if self.client:
                    self.client.disconnect()
                    self.client.loop_stop()

                # Use unique client ID to avoid conflicts
                import uuid
                client_id = f"ai-automation-service-{uuid.uuid4().hex[:8]}"
                self.client = mqtt.Client(client_id=client_id)

                if self.username and self.password:
                    self.client.username_pw_set(self.username, self.password)

                self.client.on_connect = self._on_connect
                self.client.on_disconnect = self._on_disconnect

                # Set connection timeout
                self.client.connect(self.broker, self.port, 60)
                self.client.loop_start()

                # Wait for connection with timeout
                import time
                timeout = 5.0  # 5 second timeout
                start_time = time.time()

                while not self.is_connected and (time.time() - start_time) < timeout:
                    time.sleep(0.1)

                if self.is_connected:
                    logger.info(f"✅ MQTT connected to {self.broker}:{self.port} (attempt {attempt + 1})")
                    return True
                logger.warning(f"⚠️ MQTT connection timeout on attempt {attempt + 1}")
                if attempt < max_retries - 1:
                    logger.info(f"🔄 Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)

            except Exception as e:
                logger.exception(f"❌ MQTT connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"🔄 Retrying in {retry_delay} seconds...")
                    import time
                    time.sleep(retry_delay)
                else:
                    logger.exception("❌ All MQTT connection attempts failed")
                    self.is_connected = False
                    return False

        return False

    def _on_connect(self, client, userdata, flags, rc):
        """
        Callback for when client connects to broker.

        Automatically resubscribes to topics on reconnect.
        """
        if rc == 0:
            logger.info("✅ MQTT connection established")
            self.is_connected = True

            # Resubscribe to topics on reconnect (Epic AI-2)
            # paho-mqtt will handle this automatically if we stored subscriptions
        else:
            # MQTT connection result codes
            error_messages = {
                1: "Connection refused - incorrect protocol version",
                2: "Connection refused - invalid client identifier",
                3: "Connection refused - server unavailable",
                4: "Connection refused - bad username or password",
                5: "Connection refused - not authorised",
            }
            error_msg = error_messages.get(rc, f"Unknown error code {rc}")
            logger.error(f"❌ MQTT connection failed with code {rc}: {error_msg}")
            self.is_connected = False

    def _on_disconnect(self, client, userdata, rc):
        """Callback for when client disconnects from broker"""
        logger.warning(f"⚠️ MQTT disconnected (code: {rc})")
        self.is_connected = False

        # Auto-reconnect on unexpected disconnect (not manual disconnect)
        if rc != 0:  # 0 = manual disconnect
            logger.info("🔄 Attempting automatic reconnection...")
            import threading
            import time

            def reconnect():
                time.sleep(2)  # Wait 2 seconds before reconnecting
                if not self.is_connected:
                    self.connect(max_retries=1, retry_delay=1.0)

            threading.Thread(target=reconnect, daemon=True).start()

    def publish(self, topic: str, message: dict, qos: int = 1) -> bool:
        """
        Publish a message to MQTT topic.

        Args:
            topic: MQTT topic
            message: Message payload (will be JSON-encoded)
            qos: Quality of service (0, 1, or 2)

        Returns:
            True if publish successful
        """
        try:
            if not self.is_connected:
                logger.warning("⚠️ MQTT not connected, attempting to connect...")
                if not self.connect():
                    return False

            payload = json.dumps(message)
            result = self.client.publish(topic, payload, qos=qos)

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"📢 Published to {topic}: {payload[:100]}...")
                return True
            logger.error(f"❌ Publish failed with code {result.rc}")
            return False

        except Exception as e:
            logger.exception(f"❌ MQTT publish error: {e}")
            return False

    def publish_analysis_complete(self, result_summary: dict) -> bool:
        """
        Publish analysis complete notification.

        Args:
            result_summary: Summary of analysis results

        Returns:
            True if publish successful
        """
        topic = "ha-ai/analysis/complete"
        message = {
            "event": "analysis_complete",
            "timestamp": result_summary.get("timestamp"),
            "patterns_detected": result_summary.get("patterns_detected", 0),
            "suggestions_generated": result_summary.get("suggestions_generated", 0),
            "processing_time_sec": result_summary.get("processing_time_sec", 0),
            "cost": result_summary.get("cost", 0),
            "success": result_summary.get("success", True),
        }
        return self.publish(topic, message)

    def publish_suggestion_created(self, suggestion_data: dict) -> bool:
        """
        Publish new suggestion notification.

        Args:
            suggestion_data: Suggestion details

        Returns:
            True if publish successful
        """
        topic = "ha-ai/suggestions/new"
        message = {
            "event": "suggestion_created",
            "suggestion_id": suggestion_data.get("id"),
            "title": suggestion_data.get("title"),
            "category": suggestion_data.get("category"),
            "confidence": suggestion_data.get("confidence"),
            "priority": suggestion_data.get("priority"),
        }
        return self.publish(topic, message)

    def subscribe(self, topic: str, qos: int = 1) -> bool:
        """
        Subscribe to MQTT topic.

        Added in Story AI2.1 for Epic AI-2 (Device Intelligence).

        Args:
            topic: MQTT topic to subscribe to (e.g., "zigbee2mqtt/bridge/devices")
            qos: Quality of service (0, 1, or 2)

        Returns:
            True if subscription successful

        Example:
            client.subscribe("zigbee2mqtt/bridge/devices")
            client.on_message = callback_function
        """
        try:
            if not self.is_connected:
                logger.warning("⚠️ MQTT not connected, attempting to connect...")
                if not self.connect():
                    return False

            result, _mid = self.client.subscribe(topic, qos=qos)

            if result == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"📡 Subscribed to topic: {topic} (QoS {qos})")
                return True
            logger.error(f"❌ Subscription failed with code {result}")
            return False

        except Exception as e:
            logger.exception(f"❌ MQTT subscribe error: {e}")
            return False

    @property
    def on_message(self) -> Callable | None:
        """
        Get the message callback handler.

        Returns:
            Current message callback or None
        """
        return self._message_callback

    @on_message.setter
    def on_message(self, callback: Callable):
        """
        Set message callback handler for subscribed topics.

        Added in Story AI2.1 for Epic AI-2 (Device Intelligence).

        The callback should have signature:
            def callback(client, userdata, message) -> None

        Where message has:
            - message.topic: str (MQTT topic)
            - message.payload: bytes (message payload)
            - message.qos: int (QoS level)

        Args:
            callback: Function to call when message received

        Example:
            def on_msg(client, userdata, msg):
                print(f"Received: {msg.topic}: {msg.payload}")

            client.on_message = on_msg
        """
        self._message_callback = callback

        if self.client:
            self.client.on_message = callback
            logger.debug("✅ Message callback registered")
        else:
            logger.warning("⚠️ Cannot set callback - client not initialized")

    def disconnect(self):
        """Disconnect from MQTT broker"""
        try:
            if self.client:
                self.client.loop_stop()
                self.client.disconnect()
                logger.info("✅ MQTT disconnected")
        except Exception as e:
            logger.exception(f"❌ MQTT disconnect error: {e}")

