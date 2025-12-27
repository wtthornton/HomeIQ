# Story DI-1.2: Multi-Source Discovery Engine

**Story ID:** DI-1.2  
**Epic:** DI-1 (Device Intelligence Service Foundation)  
**Status:** Review  
**Priority:** P0  
**Story Points:** 13  
**Complexity:** High  

---

## Story Description

Implement a comprehensive multi-source device discovery engine that integrates with Home Assistant WebSocket API and Zigbee2MQTT bridge to discover all devices, entities, and capabilities. This story creates the core discovery functionality that will serve as the foundation for all device intelligence features.

## User Story

**As a** system administrator  
**I want** the Device Intelligence Service to automatically discover all devices from Home Assistant and Zigbee2MQTT  
**So that** I have a complete inventory of all connected devices and their capabilities  

## Acceptance Criteria

### AC1: Home Assistant WebSocket Integration
- [x] WebSocket connection to Home Assistant established
- [x] Device registry discovery (`config/device_registry/list`)
- [x] Entity registry discovery (`config/entity_registry/list`)
- [x] Area registry discovery (`config/area_registry/list`)
- [x] Integration registry discovery (`config/config_entries/list`)
- [x] Automatic reconnection on connection loss
- [x] Connection health monitoring

### AC2: Zigbee2MQTT Bridge Integration
- [x] MQTT connection to Zigbee2MQTT bridge established
- [x] Device capabilities discovery (`zigbee2mqtt/bridge/devices`)
- [x] Device groups discovery (`zigbee2mqtt/bridge/groups`)
- [x] Network map discovery (`zigbee2mqtt/bridge/networkmap`)
- [x] Automatic reconnection on connection loss
- [x] Connection health monitoring

### AC3: Device Data Processing
- [x] Raw device data parsing and normalization
- [x] Device capability extraction from Zigbee2MQTT exposes
- [x] Device metadata enrichment from Home Assistant
- [x] Device relationship mapping (HA ↔ Zigbee2MQTT)
- [x] Data validation and error handling

### AC4: Discovery API Endpoints
- [x] `GET /api/discovery/status` - Discovery service status
- [x] `GET /api/discovery/sources` - Available discovery sources
- [x] `POST /api/discovery/refresh` - Manual discovery refresh
- [x] `GET /api/discovery/devices` - Discovered devices summary

## Technical Requirements

### Discovery Service Architecture
```python
# src/core/discovery_service.py
class DiscoveryService:
    def __init__(self):
        self.ha_client = HomeAssistantClient()
        self.mqtt_client = MQTTClient()
        self.device_parser = DeviceParser()
        self.capability_parser = CapabilityParser()
    
    async def start_discovery(self):
        """Start all discovery sources"""
        await self.ha_client.connect()
        await self.mqtt_client.connect()
        await self._start_ha_discovery()
        await self._start_mqtt_discovery()
    
    async def _start_ha_discovery(self):
        """Start Home Assistant discovery"""
        # WebSocket subscriptions for real-time updates
        await self.ha_client.subscribe_device_registry()
        await self.ha_client.subscribe_entity_registry()
        await self.ha_client.subscribe_area_registry()
    
    async def _start_mqtt_discovery(self):
        """Start Zigbee2MQTT discovery"""
        # MQTT subscriptions for device updates
        await self.mqtt_client.subscribe("zigbee2mqtt/bridge/devices")
        await self.mqtt_client.subscribe("zigbee2mqtt/bridge/groups")
```

### Home Assistant Client
```python
# src/clients/ha_client.py
class HomeAssistantClient:
    def __init__(self, url: str, token: str):
        self.url = url
        self.token = token
        self.websocket = None
    
    async def connect(self):
        """Establish WebSocket connection to HA"""
        # Implementation details
    
    async def get_device_registry(self) -> List[Device]:
        """Get all devices from HA device registry"""
        # Implementation details
    
    async def get_entity_registry(self) -> List[Entity]:
        """Get all entities from HA entity registry"""
        # Implementation details
```

### MQTT Client
```python
# src/clients/mqtt_client.py
class MQTTClient:
    def __init__(self, broker: str, username: str, password: str):
        self.broker = broker
        self.username = username
        self.password = password
        self.client = None
    
    async def connect(self):
        """Establish MQTT connection"""
        # Implementation details
    
    async def subscribe(self, topic: str):
        """Subscribe to MQTT topic"""
        # Implementation details
    
    def on_message(self, client, userdata, msg):
        """Handle incoming MQTT messages"""
        # Implementation details
```

### Device Models
```python
# src/models/device.py
class Device(BaseModel):
    id: str
    name: str
    manufacturer: str
    model: str
    area_id: Optional[str]
    integration: str
    capabilities: List[Capability]
    ha_device: Optional[HADevice]
    zigbee_device: Optional[ZigbeeDevice]
    last_seen: datetime
    health_score: Optional[int]

class Capability(BaseModel):
    name: str
    type: str
    properties: Dict[str, Any]
    exposed: bool
    configured: bool
```

## Implementation Tasks

### Task 1: Home Assistant WebSocket Client
- [x] Create WebSocket client for HA connection
- [x] Implement device registry discovery
- [x] Implement entity registry discovery
- [x] Implement area registry discovery
- [x] Add connection health monitoring
- [x] Implement automatic reconnection

### Task 2: Zigbee2MQTT MQTT Client
- [x] Create MQTT client for Zigbee2MQTT bridge
- [x] Implement device capabilities discovery
- [x] Implement device groups discovery
- [x] Implement network map discovery
- [x] Add connection health monitoring
- [x] Implement automatic reconnection

### Task 3: Device Data Processing
- [x] Create device data parser
- [x] Implement capability extraction
- [x] Implement device relationship mapping
- [x] Add data validation
- [x] Implement error handling

### Task 4: Discovery Service Integration
- [x] Create main discovery service
- [x] Integrate HA and MQTT clients
- [x] Implement discovery orchestration
- [x] Add service health monitoring
- [x] Implement graceful shutdown

### Task 5: Discovery API Endpoints
- [x] Create discovery router
- [x] Implement status endpoint
- [x] Implement sources endpoint
- [x] Implement refresh endpoint
- [x] Implement devices summary endpoint

### Task 6: Testing & Validation
- [x] Create unit tests for clients
- [x] Create integration tests for discovery
- [x] Test connection resilience
- [x] Test data parsing accuracy
- [x] Test API endpoints

## Dependencies

- **External**: Home Assistant WebSocket API, Zigbee2MQTT bridge, MQTT broker
- **Internal**: Story DI-1.1 (Service Foundation)
- **Infrastructure**: Docker environment with HA and Zigbee2MQTT

## Definition of Done

- [x] Home Assistant WebSocket integration functional
- [x] Zigbee2MQTT MQTT integration functional
- [x] Device discovery working for both sources
- [x] Device data processing operational
- [x] Discovery API endpoints functional
- [x] Connection resilience tested
- [x] All tests passing
- [x] Documentation updated

## Notes

This story implements the core discovery functionality that will be used by all subsequent device intelligence features. The discovery engine should be designed to handle real-time updates and maintain data consistency between different discovery sources.

---

**Created**: January 24, 2025  
**Last Updated**: January 24, 2025  
**Author**: BMAD Product Manager  
**Reviewers**: System Architect, QA Lead
