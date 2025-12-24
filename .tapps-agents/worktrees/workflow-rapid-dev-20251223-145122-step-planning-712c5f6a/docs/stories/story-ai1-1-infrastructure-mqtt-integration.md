# Story AI1.1: Infrastructure Setup and MQTT Integration

**Epic:** Epic-AI-1 - AI Automation Suggestion System  
**Story ID:** AI1.1  
**Priority:** Critical  
**Estimated Effort:** 2-3 hours  
**Dependencies:** None (foundation story)

**⚠️ UPDATED:** MQTT broker already running on HA server (port 1883)

---

## User Story

**As a** developer  
**I want** to configure MQTT connection to existing HA broker  
**so that** AI service can communicate with Home Assistant asynchronously

---

## Business Value

- Establishes communication foundation for entire AI automation system
- Enables loose coupling between AI service and Home Assistant
- Provides event-driven architecture for dynamic automations
- Minimal resource footprint (10-20MB RAM)

---

## Acceptance Criteria

1. ✅ AI service connects to existing HA MQTT broker (port 1883)
2. ✅ MQTT credentials loaded from environment variables
3. ✅ Topics `ha-ai/*` can be published and subscribed
4. ✅ QoS 1 message delivery confirmed
5. ✅ Connection resilient to network interruptions
6. ✅ MQTT topic namespace `ha-ai/*` configured
7. ✅ Test messages successfully published and received

---

## Technical Implementation Notes

### MQTT Connection (Existing HA Broker)

**Important:** MQTT broker is already running on Home Assistant server. We just need to connect to it.

**Environment Configuration:**

**Create: infrastructure/env.ai-automation.template**

```bash
# AI Automation Service Configuration

# Home Assistant MQTT Broker (already running)
MQTT_BROKER=<HA_SERVER_IP>  # e.g., 192.168.1.100 or home-assistant
MQTT_PORT=1883
MQTT_USERNAME=<your-mqtt-username>  # From HA MQTT integration
MQTT_PASSWORD=<your-mqtt-password>  # From HA MQTT integration

# Home Assistant API
HA_URL=http://<HA_SERVER_IP>:8123
HA_TOKEN=<your-ha-long-lived-token>

# Data API (from existing homeiq project)
DATA_API_URL=http://data-api:8006

# OpenAI API
OPENAI_API_KEY=<your-openai-api-key>

# Scheduling
ANALYSIS_SCHEDULE=0 3 * * *  # 3 AM daily

# Database
DATABASE_PATH=/app/data/ai_automation.db
```

### Home Assistant MQTT Integration Verification

**Check HA has MQTT configured:**

1. In Home Assistant UI → Settings → Devices & Services
2. Verify "MQTT" integration is installed
3. Note the broker address (usually localhost or HA server IP)
4. Create dedicated user for AI service (recommended):
   - Settings → People → Users → Add User
   - Or use existing MQTT credentials

### No Mosquitto Container Needed

**Update to docker-compose.yml:**

```yaml
# NO mosquitto service needed - using HA's MQTT broker

services:
  ai-automation-service:
    build: ./services/ai-automation-service
    container_name: ai-automation-service
    ports:
      - "8011:8011"
    environment:
      - MQTT_BROKER=${MQTT_BROKER}  # HA server IP
      - MQTT_PORT=${MQTT_PORT:-1883}
      - MQTT_USERNAME=${MQTT_USERNAME}
      - MQTT_PASSWORD=${MQTT_PASSWORD}
      - HA_URL=${HA_URL}
      - HA_TOKEN=${HA_TOKEN}
      - DATA_API_URL=http://data-api:8006
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    env_file:
      - infrastructure/env.ai-automation
    depends_on:
      - data-api
    networks:
      - ha-network
    restart: unless-stopped
```

### Topic Structure

**Topic Namespace: `ha-ai/*`**

```bash
# AI Service publishes
ha-ai/events/pattern/detected
ha-ai/events/suggestion/generated
ha-ai/events/sports/team_scored
ha-ai/commands/automation/deploy
ha-ai/status/analysis_complete

# Home Assistant publishes
ha-ai/responses/automation/executed
ha-ai/responses/automation/failed
homeassistant/status
```

### Testing MQTT Connection

**Option 1: Test from AI Service Container**

```bash
# Install MQTT client in AI service for testing
docker exec -it ai-automation-service pip install paho-mqtt

# Test subscription
docker exec -it ai-automation-service python -c "
import paho.mqtt.client as mqtt
client = mqtt.Client()
client.username_pw_set('${MQTT_USERNAME}', '${MQTT_PASSWORD}')
client.connect('${MQTT_BROKER}', 1883, 60)
print('✅ MQTT connection successful')
"

# Test publish
docker exec -it ai-automation-service python -c "
import paho.mqtt.client as mqtt
client = mqtt.Client()
client.username_pw_set('${MQTT_USERNAME}', '${MQTT_PASSWORD}')
client.connect('${MQTT_BROKER}', 1883, 60)
client.publish('ha-ai/test', 'Hello from AI service')
print('✅ Message published')
"
```

**Option 2: Test from Home Assistant**

Home Assistant → Developer Tools → MQTT

```yaml
# Subscribe to topic
ha-ai/#

# Publish test message
Topic: ha-ai/test
Payload: {"message": "test"}
```

**Option 3: Use MQTT Explorer (GUI)**

Download: http://mqtt-explorer.com/  
Connect to: `<HA_SERVER_IP>:1883`  
Subscribe to: `ha-ai/#`

---

## Integration Verification

**IV1: AI service connects to HA MQTT broker successfully**
- Connection established without errors
- Authentication successful (username/password)
- Can subscribe to topics

**IV2: Can publish to ha-ai/* topics**
- Test message published successfully
- Home Assistant can see messages (Developer Tools → MQTT)
- QoS 1 delivery confirmed

**IV3: HA MQTT broker handles additional client**
- No performance impact on HA
- HA's existing MQTT automations still work
- Broker resource usage acceptable

**IV4: Topic namespace ha-ai/* doesn't conflict**
- No overlap with existing HA topics (homeassistant/*)
- Topics organized and documented
- Easy to filter in HA Developer Tools

---

## Definition of Done

- [ ] Mosquitto container running and healthy
- [ ] MQTT accessible on ports 1883 and 9001
- [ ] Configuration file created and mounted
- [ ] Topic namespace `ha-ai/*` tested
- [ ] Docker volumes created for persistence
- [ ] Health check passes
- [ ] Resource usage within limits (<20MB RAM)
- [ ] Documentation updated (README.md)
- [ ] Integration verification complete
- [ ] Code reviewed and approved

---

## Testing Strategy

### Unit Tests
- N/A (infrastructure configuration)

### Integration Tests
```python
# Test MQTT connectivity from Python
import paho.mqtt.client as mqtt

def test_mqtt_connection():
    client = mqtt.Client()
    client.connect("localhost", 1883, 60)
    assert client.is_connected()
    
def test_mqtt_publish_subscribe():
    messages_received = []
    
    def on_message(client, userdata, msg):
        messages_received.append(msg.payload.decode())
    
    client = mqtt.Client()
    client.on_message = on_message
    client.connect("localhost", 1883, 60)
    client.subscribe("ha-ai/test")
    client.loop_start()
    
    client.publish("ha-ai/test", "test message")
    time.sleep(1)
    
    assert "test message" in messages_received
```

### Manual Testing
1. Start Docker Compose
2. Connect to MQTT using MQTT Explorer or CLI
3. Publish test messages
4. Verify message delivery
5. Check persistence after broker restart

---

## Reference Files

**Copy patterns from:**
- `docker-compose.yml` - Existing service definitions
- `services/*/Dockerfile` - Docker patterns

**Documentation:**
- MQTT Protocol: https://mqtt.org/
- Mosquitto Docker: https://hub.docker.com/_/eclipse-mosquitto
- paho-mqtt: https://pypi.org/project/paho-mqtt/

---

## Notes

- MQTT is lightweight and battle-tested for IoT
- Internal network only - no external exposure needed
- QoS 1 balances reliability and performance
- 5-minute TTL prevents stale automation triggers
- WebSocket on 9001 allows frontend to subscribe

---

**Story Status:** Not Started  
**Assigned To:** TBD  
**Created:** 2025-10-15  
**Updated:** 2025-10-15


