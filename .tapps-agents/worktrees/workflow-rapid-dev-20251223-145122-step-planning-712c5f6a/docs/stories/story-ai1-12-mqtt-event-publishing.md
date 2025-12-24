# Story AI1.12: MQTT Event Publishing

**Epic:** Epic-AI-1 - AI Automation Suggestion System  
**Story ID:** AI1.12  
**Priority:** Medium  
**Estimated Effort:** 6-8 hours  
**Dependencies:** Story AI1.11 (HA integration), Story AI1.1 (MQTT connection)

**⚠️ NOTE:** Using existing MQTT broker on Home Assistant server (port 1883)

---

## User Story

**As a** AI service  
**I want** to publish events to MQTT topics  
**so that** Home Assistant can subscribe to dynamic triggers

---

## Business Value

- Enables event-driven automations (sports scores, pattern alerts)
- Completes bi-directional communication with HA
- Supports future real-time features (Phase 2+)
- Provides execution feedback loop

---

## Acceptance Criteria

1. ✅ Publishes to ha-ai/events/* topics successfully
2. ✅ Messages use JSON format
3. ✅ QoS 1 ensures at-least-once delivery
4. ✅ TTL prevents stale messages (30 second expiry)
5. ✅ HA can subscribe and receive messages
6. ✅ Message publishing latency <100ms
7. ✅ No message loss under normal conditions
8. ✅ Connection resilient to broker restarts

---

## Technical Implementation Notes

### MQTT Client

**Create: src/mqtt/client.py**

**Reference: PRD Section 7.5**

```python
import paho.mqtt.client as mqtt
import json
import logging
from typing import Dict, Callable

logger = logging.getLogger(__name__)

class MQTTClientWrapper:
    """MQTT client for publishing events and subscribing to responses"""
    
    def __init__(self, broker: str, port: int = 1883, username: str = None, password: str = None):
        self.broker = broker  # HA server IP (from environment)
        self.port = port
        self.client = mqtt.Client(client_id="ai-automation-service")
        self.connected = False
        
        # Set authentication if provided
        if username and password:
            self.client.username_pw_set(username, password)
        
        # Set callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
    
    def connect(self):
        """Connect to HA's MQTT broker"""
        try:
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()
            logger.info(f"MQTT client connected to HA broker at {self.broker}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to HA MQTT broker: {e}")
            raise
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback when connected"""
        if rc == 0:
            self.connected = True
            logger.info("MQTT connected successfully")
            
            # Subscribe to response topics
            client.subscribe("ha-ai/responses/#", qos=1)
            logger.info("Subscribed to ha-ai/responses/#")
        else:
            logger.error(f"MQTT connection failed with code {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback when disconnected"""
        self.connected = False
        logger.warning(f"MQTT disconnected (code: {rc})")
    
    def _on_message(self, client, userdata, msg):
        """Callback for received messages"""
        try:
            payload = json.loads(msg.payload.decode())
            logger.info(f"MQTT message received on {msg.topic}: {payload}")
            
            # Handle responses from HA
            if msg.topic.startswith("ha-ai/responses/automation/"):
                self._handle_automation_response(payload)
                
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")
    
    def _handle_automation_response(self, payload: Dict):
        """Handle automation execution feedback from HA"""
        automation_id = payload.get('automation_id')
        status = payload.get('status')
        
        logger.info(f"Automation {automation_id} execution: {status}")
        
        # Store execution result (for metrics)
        # This can be expanded in Phase 2 for tracking
    
    async def publish_event(self, topic: str, payload: Dict, ttl_seconds: int = 30):
        """
        Publish event to MQTT topic.
        
        Args:
            topic: MQTT topic (should start with ha-ai/)
            payload: Event data (will be JSON serialized)
            ttl_seconds: Message expiry time (default 30 seconds)
        """
        
        if not self.connected:
            logger.error("MQTT not connected, cannot publish")
            raise RuntimeError("MQTT client not connected")
        
        # Add TTL and timestamp
        payload['ttl'] = ttl_seconds
        payload['timestamp'] = datetime.now().isoformat()
        
        # Publish with QoS 1 (at least once delivery)
        result = self.client.publish(
            topic,
            json.dumps(payload),
            qos=1,
            retain=False  # Don't retain (use TTL)
        )
        
        if result.rc == 0:
            logger.info(f"Published to {topic}: {payload}")
        else:
            logger.error(f"Failed to publish to {topic}: {result.rc}")
    
    async def publish_analysis_complete(self, patterns: int, suggestions: int, duration: float):
        """Publish analysis complete notification"""
        await self.publish_event(
            "ha-ai/status/analysis_complete",
            {
                "patterns_detected": patterns,
                "suggestions_generated": suggestions,
                "duration_seconds": duration
            }
        )
    
    async def publish_suggestion_generated(self, suggestion_id: int, title: str):
        """Publish new suggestion notification"""
        await self.publish_event(
            "ha-ai/events/suggestion/generated",
            {
                "suggestion_id": suggestion_id,
                "title": title
            }
        )
    
    def disconnect(self):
        """Disconnect from broker"""
        self.client.loop_stop()
        self.client.disconnect()
        logger.info("MQTT client disconnected")
```

### Integration with Batch Job

**Update: src/scheduler/daily_analysis.py**

```python
# After suggestions generated
await mqtt_client.publish_analysis_complete(
    patterns=total_patterns,
    suggestions=len(suggestions),
    duration=duration_seconds
)
```

---

## Integration Verification

**IV1: MQTT broker handles messages from AI service**
- Mosquitto logs show published messages
- No broker errors or warnings
- Message delivery confirmed

**IV2: HA receives and processes MQTT events**
- HA logs show subscription to ha-ai/events/*
- HA can trigger automations from MQTT topics
- Messages received within 100ms

**IV3: No interference with existing MQTT traffic**
- Other services using MQTT unaffected
- No message collisions
- Broker capacity sufficient

**IV4: Broker resource usage stays <50MB**
- Monitor Mosquitto memory usage
- Check message queue size
- Verify no memory leaks

---

## Tasks Breakdown

1. **Create MQTTClientWrapper class** (2 hours)
2. **Implement publish_event method** (1 hour)
3. **Add subscription and message handling** (1.5 hours)
4. **Create convenience methods** (1 hour)
5. **Integrate with batch job** (1 hour)
6. **Error handling and reconnection logic** (1 hour)
7. **Unit tests with mock MQTT** (1 hour)
8. **Integration test with real broker** (1 hour)

**Total:** 6-8 hours

---

## Testing Strategy

### Unit Tests

```python
# tests/test_mqtt_client.py
import pytest
from src.mqtt.client import MQTTClientWrapper
from unittest.mock import MagicMock, patch

def test_publishes_message():
    """Test successful message publishing"""
    client = MQTTClientWrapper()
    
    with patch.object(client.client, 'publish') as mock_publish:
        mock_publish.return_value.rc = 0
        
        await client.publish_event("ha-ai/test", {"data": "test"})
        
        assert mock_publish.called
        args = mock_publish.call_args
        assert args[0][0] == "ha-ai/test"
        assert "data" in json.loads(args[0][1])

def test_handles_disconnection():
    """Test reconnection logic"""
    client = MQTTClientWrapper()
    
    # Simulate disconnect
    client._on_disconnect(None, None, 1)
    
    assert client.connected == False
    # Should attempt reconnect (tested in integration)
```

---

## Definition of Done

- [ ] MQTTClientWrapper implemented
- [ ] Publish methods functional
- [ ] Subscription and message handling
- [ ] Integration with batch job
- [ ] QoS 1 delivery confirmed
- [ ] TTL implemented (30 seconds)
- [ ] Connection resilience tested
- [ ] Unit tests pass
- [ ] Integration test with real broker
- [ ] Message latency <100ms verified
- [ ] Code reviewed and approved

---

## Reference Files

**Copy patterns from:**
- paho-mqtt docs: https://www.eclipse.org/paho/index.php?page=clients/python/docs/index.php
- PRD Section 7.5 (MQTT message examples)

---

## Notes

- QoS 1 balance (not 0 or 2)
- TTL prevents stale triggers (critical for time-sensitive events)
- Subscription to responses/* enables feedback loop
- Keep messages simple (JSON, not binary)
- Log all publishes for debugging

---

**Story Status:** Not Started  
**Assigned To:** TBD  
**Created:** 2025-10-15  
**Updated:** 2025-10-15

