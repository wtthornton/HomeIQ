# BMAD Home Assistant Simulator - Implementation Tasks

## Overview
This document provides detailed implementation tasks for the HA Simulator based on the BMAD development plan. Tasks are organized by phase and include acceptance criteria, technical details, and dependencies.

## Phase 1: Core Simulator Foundation

### Epic 1: WebSocket Server & Authentication

#### Task 1.1: Project Structure Setup
**Priority**: High | **Estimated Time**: 2 hours

**Acceptance Criteria**:
- New service directory structure created
- Docker configuration added
- Basic Python project setup
- Environment configuration

**Technical Details**:
```bash
services/ha-simulator/
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── websocket_server.py
│   ├── authentication.py
│   ├── event_generator.py
│   ├── data_patterns.py
│   └── config_manager.py
├── tests/
│   ├── __init__.py
│   ├── test_websocket_server.py
│   ├── test_authentication.py
│   └── test_event_generator.py
├── config/
│   ├── simulator-config.yaml
│   └── entity-definitions.yaml
├── data/
│   └── ha-event-patterns.json
├── requirements.txt
├── Dockerfile
└── README.md
```

**Implementation Steps**:
1. Create service directory structure
2. Add to docker-compose.dev.yml
3. Create basic Python files with imports
4. Set up requirements.txt with dependencies
5. Create Dockerfile
6. Add environment variables to infrastructure/env.example

**Dependencies**: None

---

#### Task 1.2: WebSocket Server Foundation
**Priority**: High | **Estimated Time**: 4 hours

**Acceptance Criteria**:
- WebSocket server accepts connections on configurable port
- Handles connection lifecycle (connect/disconnect)
- Basic error handling and logging
- Health check endpoint

**Technical Details**:
```python
# services/ha-simulator/src/websocket_server.py
import asyncio
import json
import logging
from typing import Dict, Any, Set
from aiohttp import web, WSMsgType
from aiohttp.web_ws import WebSocketResponse

class HASimulatorWebSocketServer:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.clients: Set[WebSocketResponse] = set()
        self.logger = logging.getLogger(__name__)
        
    async def websocket_handler(self, request):
        """Handle WebSocket connections"""
        ws = WebSocketResponse()
        await ws.prepare(request)
        
        self.clients.add(ws)
        self.logger.info(f"Client connected. Total clients: {len(self.clients)}")
        
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    await self.handle_message(ws, msg.data)
                elif msg.type == WSMsgType.ERROR:
                    self.logger.error(f"WebSocket error: {ws.exception()}")
        finally:
            self.clients.remove(ws)
            self.logger.info(f"Client disconnected. Total clients: {len(self.clients)}")
    
    async def handle_message(self, ws: WebSocketResponse, data: str):
        """Handle incoming WebSocket messages"""
        try:
            message = json.loads(data)
            message_type = message.get("type")
            
            if message_type == "auth":
                await self.handle_auth(ws, message)
            elif message_type == "subscribe_events":
                await self.handle_subscribe_events(ws, message)
            else:
                self.logger.warning(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON message: {e}")
        except Exception as e:
            self.logger.error(f"Error handling message: {e}")
    
    async def start_server(self):
        """Start the WebSocket server"""
        app = web.Application()
        app.router.add_get('/api/websocket', self.websocket_handler)
        app.router.add_get('/health', self.health_check)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', self.config['port'])
        await site.start()
        
        self.logger.info(f"HA Simulator WebSocket server started on port {self.config['port']}")
```

**Implementation Steps**:
1. Implement WebSocket server class
2. Add connection management
3. Implement message handling framework
4. Add health check endpoint
5. Add comprehensive logging
6. Create unit tests

**Dependencies**: Task 1.1

---

#### Task 1.3: Authentication Simulation
**Priority**: High | **Estimated Time**: 3 hours

**Acceptance Criteria**:
- Implements HA authentication flow
- Supports configurable tokens
- Proper error responses for invalid auth
- Sends auth_required on connection

**Technical Details**:
```python
# services/ha-simulator/src/authentication.py
import json
import logging
from typing import Dict, Any, Optional
from aiohttp.web_ws import WebSocketResponse

class AuthenticationManager:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.authenticated_clients: Dict[WebSocketResponse, Dict[str, Any]] = {}
        self.logger = logging.getLogger(__name__)
    
    async def send_auth_required(self, ws: WebSocketResponse):
        """Send auth_required message to client"""
        auth_required = {
            "type": "auth_required",
            "ha_version": self.config.get("ha_version", "2025.10.1")
        }
        await ws.send_str(json.dumps(auth_required))
        self.logger.info("Sent auth_required to client")
    
    async def handle_auth(self, ws: WebSocketResponse, message: Dict[str, Any]) -> bool:
        """Handle authentication message"""
        access_token = message.get("access_token")
        expected_token = self.config.get("auth_token")
        
        if not access_token:
            await self.send_auth_invalid(ws, "Missing access_token")
            return False
        
        if access_token != expected_token:
            await self.send_auth_invalid(ws, "Invalid access_token")
            return False
        
        # Authentication successful
        await self.send_auth_ok(ws)
        self.authenticated_clients[ws] = {
            "authenticated": True,
            "token": access_token
        }
        self.logger.info("Client authenticated successfully")
        return True
    
    async def send_auth_ok(self, ws: WebSocketResponse):
        """Send auth_ok message"""
        auth_ok = {
            "type": "auth_ok",
            "ha_version": self.config.get("ha_version", "2025.10.1")
        }
        await ws.send_str(json.dumps(auth_ok))
    
    async def send_auth_invalid(self, ws: WebSocketResponse, message: str):
        """Send auth_invalid message"""
        auth_invalid = {
            "type": "auth_invalid",
            "message": message
        }
        await ws.send_str(json.dumps(auth_invalid))
    
    def is_authenticated(self, ws: WebSocketResponse) -> bool:
        """Check if client is authenticated"""
        return ws in self.authenticated_clients
```

**Implementation Steps**:
1. Implement authentication manager
2. Add auth_required message sending
3. Implement auth message handling
4. Add token validation
5. Implement auth_ok/auth_invalid responses
6. Add authentication state tracking
7. Create unit tests

**Dependencies**: Task 1.2

---

#### Task 1.4: Event Subscription Management
**Priority**: High | **Estimated Time**: 3 hours

**Acceptance Criteria**:
- Handles subscribe_events messages
- Manages multiple subscriptions
- Sends subscription confirmations
- Tracks subscription state

**Technical Details**:
```python
# services/ha-simulator/src/subscription_manager.py
import json
import logging
from typing import Dict, Any, Set
from aiohttp.web_ws import WebSocketResponse

class SubscriptionManager:
    def __init__(self):
        self.subscriptions: Dict[WebSocketResponse, Set[int]] = {}
        self.subscription_counter = 0
        self.logger = logging.getLogger(__name__)
    
    async def handle_subscribe_events(self, ws: WebSocketResponse, message: Dict[str, Any]):
        """Handle subscribe_events message"""
        subscription_id = message.get("id")
        if subscription_id is None:
            await self.send_subscription_error(ws, "Missing subscription ID")
            return
        
        # Add subscription
        if ws not in self.subscriptions:
            self.subscriptions[ws] = set()
        self.subscriptions[ws].add(subscription_id)
        
        # Send confirmation
        await self.send_subscription_result(ws, subscription_id, True)
        self.logger.info(f"Client subscribed to events with ID: {subscription_id}")
    
    async def send_subscription_result(self, ws: WebSocketResponse, subscription_id: int, success: bool):
        """Send subscription result"""
        result = {
            "id": subscription_id,
            "type": "result",
            "success": success,
            "result": None
        }
        await ws.send_str(json.dumps(result))
    
    async def send_subscription_error(self, ws: WebSocketResponse, message: str):
        """Send subscription error"""
        error = {
            "type": "result",
            "success": False,
            "error": {
                "code": "invalid_format",
                "message": message
            }
        }
        await ws.send_str(json.dumps(error))
    
    def has_subscriptions(self, ws: WebSocketResponse) -> bool:
        """Check if client has active subscriptions"""
        return ws in self.subscriptions and len(self.subscriptions[ws]) > 0
    
    def get_subscriptions(self, ws: WebSocketResponse) -> Set[int]:
        """Get client's subscription IDs"""
        return self.subscriptions.get(ws, set())
    
    def remove_client(self, ws: WebSocketResponse):
        """Remove client and all subscriptions"""
        if ws in self.subscriptions:
            del self.subscriptions[ws]
            self.logger.info("Removed client subscriptions")
```

**Implementation Steps**:
1. Implement subscription manager
2. Add subscribe_events handling
3. Implement subscription tracking
4. Add result message sending
5. Add error handling
6. Create unit tests

**Dependencies**: Task 1.3

---

## Phase 2: Event Generation System

### Epic 2: Realistic Event Generation

#### Task 2.1: Data Pattern Analysis
**Priority**: High | **Estimated Time**: 4 hours

**Acceptance Criteria**:
- Analyzes existing HA event logs
- Extracts entity patterns and frequencies
- Generates entity definitions
- Creates pattern database

**Technical Details**:
```python
# services/ha-simulator/src/data_patterns.py
import json
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from collections import defaultdict, Counter
from pathlib import Path

class HADataPatternAnalyzer:
    def __init__(self, log_file_path: str):
        self.log_file_path = log_file_path
        self.logger = logging.getLogger(__name__)
        self.entity_patterns: Dict[str, Dict[str, Any]] = {}
        self.event_frequencies: Dict[str, int] = defaultdict(int)
        self.temporal_patterns: Dict[str, List[datetime]] = defaultdict(list)
    
    def analyze_log_file(self) -> Dict[str, Any]:
        """Analyze HA event log file"""
        self.logger.info(f"Analyzing log file: {self.log_file_path}")
        
        if not Path(self.log_file_path).exists():
            self.logger.warning(f"Log file not found: {self.log_file_path}")
            return self._generate_default_patterns()
        
        with open(self.log_file_path, 'r') as f:
            for line in f:
                self._parse_log_line(line)
        
        return self._generate_patterns()
    
    def _parse_log_line(self, line: str):
        """Parse a single log line"""
        # Extract timestamp
        timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
        if not timestamp_match:
            return
        
        timestamp = datetime.strptime(timestamp_match.group(1), '%Y-%m-%d %H:%M:%S')
        
        # Extract entity information
        entity_match = re.search(r'Entity: ([a-zA-Z_\.]+)', line)
        if entity_match:
            entity_id = entity_match.group(1)
            self.temporal_patterns[entity_id].append(timestamp)
            self.event_frequencies[entity_id] += 1
    
    def _generate_patterns(self) -> Dict[str, Any]:
        """Generate patterns from analyzed data"""
        patterns = {
            "entities": {},
            "event_frequencies": dict(self.event_frequencies),
            "temporal_patterns": {},
            "generated_at": datetime.now().isoformat()
        }
        
        for entity_id, timestamps in self.temporal_patterns.items():
            if len(timestamps) < 2:
                continue
            
            # Calculate update intervals
            intervals = []
            for i in range(1, len(timestamps)):
                interval = (timestamps[i] - timestamps[i-1]).total_seconds()
                intervals.append(interval)
            
            avg_interval = sum(intervals) / len(intervals) if intervals else 30
            
            patterns["entities"][entity_id] = {
                "entity_id": entity_id,
                "domain": entity_id.split('.')[0],
                "update_interval": avg_interval,
                "event_count": len(timestamps),
                "first_seen": timestamps[0].isoformat(),
                "last_seen": timestamps[-1].isoformat()
            }
        
        return patterns
    
    def _generate_default_patterns(self) -> Dict[str, Any]:
        """Generate default patterns when no log data available"""
        return {
            "entities": {
                "sensor.living_room_temperature": {
                    "entity_id": "sensor.living_room_temperature",
                    "domain": "sensor",
                    "device_class": "temperature",
                    "update_interval": 30,
                    "base_value": 22.0,
                    "variance": 2.0,
                    "unit_of_measurement": "°C"
                },
                "sensor.wled_estimated_current": {
                    "entity_id": "sensor.wled_estimated_current",
                    "domain": "sensor",
                    "device_class": "current",
                    "update_interval": 10,
                    "base_value": 0.5,
                    "variance": 0.2,
                    "unit_of_measurement": "A"
                }
            },
            "event_frequencies": {
                "sensor.living_room_temperature": 10,
                "sensor.wled_estimated_current": 30
            },
            "generated_at": datetime.now().isoformat()
        }
```

**Implementation Steps**:
1. Implement data pattern analyzer
2. Add log file parsing
3. Extract entity patterns
4. Calculate temporal patterns
5. Generate entity definitions
6. Create pattern database
7. Add unit tests

**Dependencies**: None

---

#### Task 2.2: Basic Event Generator
**Priority**: High | **Estimated Time**: 5 hours

**Acceptance Criteria**:
- Generates state_changed events
- Supports configurable entities
- Realistic timing patterns
- Proper event format

**Technical Details**:
```python
# services/ha-simulator/src/event_generator.py
import asyncio
import json
import logging
import random
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from aiohttp.web_ws import WebSocketResponse

class EventGenerator:
    def __init__(self, config: Dict[str, Any], patterns: Dict[str, Any]):
        self.config = config
        self.patterns = patterns
        self.logger = logging.getLogger(__name__)
        self.entity_states: Dict[str, Dict[str, Any]] = {}
        self.generation_tasks: Dict[str, asyncio.Task] = {}
        self.running = False
    
    async def start_generation(self, clients: List[WebSocketResponse]):
        """Start event generation for all entities"""
        self.running = True
        self.clients = clients
        
        for entity_id, entity_config in self.patterns["entities"].items():
            task = asyncio.create_task(
                self._generate_entity_events(entity_id, entity_config)
            )
            self.generation_tasks[entity_id] = task
        
        self.logger.info(f"Started event generation for {len(self.generation_tasks)} entities")
    
    async def stop_generation(self):
        """Stop all event generation"""
        self.running = False
        
        for task in self.generation_tasks.values():
            task.cancel()
        
        await asyncio.gather(*self.generation_tasks.values(), return_exceptions=True)
        self.generation_tasks.clear()
        
        self.logger.info("Stopped event generation")
    
    async def _generate_entity_events(self, entity_id: str, entity_config: Dict[str, Any]):
        """Generate events for a specific entity"""
        update_interval = entity_config.get("update_interval", 30)
        
        # Initialize entity state
        self.entity_states[entity_id] = {
            "state": self._generate_initial_value(entity_config),
            "last_updated": datetime.now(timezone.utc),
            "attributes": self._generate_attributes(entity_config)
        }
        
        while self.running:
            try:
                await asyncio.sleep(update_interval)
                
                if not self.running:
                    break
                
                # Generate new state
                new_state = self._generate_new_state(entity_id, entity_config)
                old_state = self.entity_states[entity_id]["state"]
                
                if new_state != old_state:
                    await self._send_state_changed_event(entity_id, old_state, new_state)
                    self.entity_states[entity_id]["state"] = new_state
                    self.entity_states[entity_id]["last_updated"] = datetime.now(timezone.utc)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error generating events for {entity_id}: {e}")
    
    def _generate_initial_value(self, entity_config: Dict[str, Any]) -> str:
        """Generate initial value for entity"""
        base_value = entity_config.get("base_value", 0)
        variance = entity_config.get("variance", 1.0)
        
        if isinstance(base_value, (int, float)):
            value = base_value + random.uniform(-variance, variance)
            return f"{value:.1f}"
        else:
            return str(base_value)
    
    def _generate_new_state(self, entity_id: str, entity_config: Dict[str, Any]) -> str:
        """Generate new state value"""
        current_state = self.entity_states[entity_id]["state"]
        base_value = entity_config.get("base_value", 0)
        variance = entity_config.get("variance", 1.0)
        
        if isinstance(base_value, (int, float)):
            try:
                current_numeric = float(current_state)
                # Add small random change
                change = random.uniform(-variance * 0.1, variance * 0.1)
                new_value = current_numeric + change
                return f"{new_value:.1f}"
            except ValueError:
                return self._generate_initial_value(entity_config)
        else:
            return str(base_value)
    
    def _generate_attributes(self, entity_config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate entity attributes"""
        attributes = {
            "friendly_name": entity_config.get("friendly_name", entity_config["entity_id"]),
            "device_class": entity_config.get("device_class"),
            "unit_of_measurement": entity_config.get("unit_of_measurement")
        }
        
        # Remove None values
        return {k: v for k, v in attributes.items() if v is not None}
    
    async def _send_state_changed_event(self, entity_id: str, old_state: str, new_state: str):
        """Send state_changed event to all clients"""
        event = self._create_state_changed_event(entity_id, old_state, new_state)
        
        for client in self.clients:
            try:
                await client.send_str(json.dumps(event))
            except Exception as e:
                self.logger.error(f"Error sending event to client: {e}")
    
    def _create_state_changed_event(self, entity_id: str, old_state: str, new_state: str) -> Dict[str, Any]:
        """Create state_changed event"""
        now = datetime.now(timezone.utc)
        entity_config = self.patterns["entities"][entity_id]
        
        return {
            "type": "event",
            "event": {
                "event_type": "state_changed",
                "time_fired": now.isoformat(),
                "origin": "LOCAL",
                "context": {
                    "id": f"sim_{int(now.timestamp() * 1000)}",
                    "parent_id": None,
                    "user_id": None
                },
                "data": {
                    "entity_id": entity_id,
                    "old_state": {
                        "entity_id": entity_id,
                        "state": old_state,
                        "attributes": self.entity_states[entity_id]["attributes"],
                        "last_changed": self.entity_states[entity_id]["last_updated"].isoformat(),
                        "last_updated": self.entity_states[entity_id]["last_updated"].isoformat()
                    },
                    "new_state": {
                        "entity_id": entity_id,
                        "state": new_state,
                        "attributes": self.entity_states[entity_id]["attributes"],
                        "last_changed": now.isoformat(),
                        "last_updated": now.isoformat()
                    }
                }
            }
        }
```

**Implementation Steps**:
1. Implement event generator class
2. Add entity state management
3. Implement state value generation
4. Add timing controls
5. Create event message format
6. Add client broadcasting
7. Create unit tests

**Dependencies**: Task 2.1

---

## Phase 3: Integration & Testing

### Epic 3: Service Integration & Validation

#### Task 3.1: Docker Integration
**Priority**: Medium | **Estimated Time**: 2 hours

**Acceptance Criteria**:
- Simulator service added to docker-compose
- Environment variables configured
- Service networking setup
- Health checks configured

**Technical Details**:
```yaml
# docker-compose.dev.yml addition
services:
  ha-simulator:
    build:
      context: ./services/ha-simulator
      dockerfile: Dockerfile
    ports:
      - "8123:8123"
    environment:
      - SIMULATOR_PORT=8123
      - SIMULATOR_AUTH_TOKEN=dev_simulator_token
      - SIMULATOR_HA_VERSION=2025.10.1
      - SIMULATOR_LOG_LEVEL=INFO
    volumes:
      - ./services/ha-simulator/config:/app/config
      - ./services/ha-simulator/data:/app/data
      - ./ha_events.log:/app/data/ha_events.log:ro
    networks:
      - homeiq-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8123/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    depends_on:
      - influxdb
```

**Implementation Steps**:
1. Add service to docker-compose.dev.yml
2. Update environment variables
3. Configure networking
4. Add health checks
5. Test service startup
6. Update documentation

**Dependencies**: Task 2.2

---

#### Task 3.2: Configuration System
**Priority**: Medium | **Estimated Time**: 3 hours

**Acceptance Criteria**:
- YAML configuration support
- Environment variable override
- Runtime configuration changes
- Configuration validation

**Technical Details**:
```python
# services/ha-simulator/src/config_manager.py
import os
import yaml
import logging
from typing import Dict, Any, Optional
from pathlib import Path

class ConfigManager:
    def __init__(self, config_path: str = "config/simulator-config.yaml"):
        self.config_path = config_path
        self.logger = logging.getLogger(__name__)
        self.config: Dict[str, Any] = {}
        self.load_config()
    
    def load_config(self):
        """Load configuration from file and environment"""
        # Load base configuration
        if Path(self.config_path).exists():
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f)
        else:
            self.config = self._get_default_config()
        
        # Override with environment variables
        self._apply_environment_overrides()
        
        # Validate configuration
        self._validate_config()
        
        self.logger.info("Configuration loaded successfully")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "simulator": {
                "name": "HA Development Simulator",
                "version": "2025.10.1",
                "port": 8123
            },
            "authentication": {
                "enabled": True,
                "token": "dev_simulator_token"
            },
            "entities": [
                {
                    "entity_id": "sensor.living_room_temperature",
                    "domain": "sensor",
                    "device_class": "temperature",
                    "base_value": 22.0,
                    "variance": 2.0,
                    "update_interval": 30,
                    "unit_of_measurement": "°C"
                }
            ],
            "scenarios": [
                {
                    "name": "normal_operation",
                    "description": "Normal home operation patterns",
                    "event_rate": "medium",
                    "duration": "unlimited"
                }
            ]
        }
    
    def _apply_environment_overrides(self):
        """Apply environment variable overrides"""
        env_mappings = {
            "SIMULATOR_PORT": ["simulator", "port"],
            "SIMULATOR_AUTH_TOKEN": ["authentication", "token"],
            "SIMULATOR_HA_VERSION": ["simulator", "version"],
            "SIMULATOR_LOG_LEVEL": ["logging", "level"]
        }
        
        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                self._set_nested_config(config_path, value)
    
    def _set_nested_config(self, path: List[str], value: Any):
        """Set nested configuration value"""
        config = self.config
        for key in path[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        config[path[-1]] = value
    
    def _validate_config(self):
        """Validate configuration"""
        required_keys = ["simulator", "authentication", "entities"]
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"Missing required configuration key: {key}")
        
        # Validate port
        port = self.config["simulator"]["port"]
        if not isinstance(port, int) or port < 1 or port > 65535:
            raise ValueError(f"Invalid port: {port}")
        
        # Validate entities
        entities = self.config["entities"]
        if not isinstance(entities, list) or len(entities) == 0:
            raise ValueError("Entities must be a non-empty list")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        keys = key.split('.')
        config = self.config
        
        for k in keys:
            if isinstance(config, dict) and k in config:
                config = config[k]
            else:
                return default
        
        return config
```

**Implementation Steps**:
1. Implement configuration manager
2. Add YAML file support
3. Add environment variable overrides
4. Implement configuration validation
5. Add runtime configuration changes
6. Create unit tests

**Dependencies**: Task 1.1

---

#### Task 3.3: Integration Testing
**Priority**: High | **Estimated Time**: 4 hours

**Acceptance Criteria**:
- End-to-end WebSocket communication tests
- Service integration tests
- Event processing pipeline tests
- Performance benchmarks

**Technical Details**:
```python
# tests/test_integration.py
import asyncio
import json
import pytest
from aiohttp import web, WSMsgType
from services.ha_simulator.src.main import HASimulatorService

class TestIntegration:
    @pytest.fixture
    async def simulator_service(self):
        service = HASimulatorService()
        await service.start()
        yield service
        await service.stop()
    
    @pytest.fixture
    async def websocket_client(self, simulator_service):
        session = aiohttp.ClientSession()
        ws = await session.ws_connect('ws://localhost:8123/api/websocket')
        yield ws
        await ws.close()
        await session.close()
    
    async def test_authentication_flow(self, websocket_client):
        """Test complete authentication flow"""
        # Receive auth_required
        msg = await websocket_client.receive()
        assert msg.type == WSMsgType.TEXT
        data = json.loads(msg.data)
        assert data["type"] == "auth_required"
        
        # Send authentication
        auth_msg = {
            "type": "auth",
            "access_token": "dev_simulator_token"
        }
        await websocket_client.send_str(json.dumps(auth_msg))
        
        # Receive auth_ok
        msg = await websocket_client.receive()
        assert msg.type == WSMsgType.TEXT
        data = json.loads(msg.data)
        assert data["type"] == "auth_ok"
    
    async def test_event_subscription(self, websocket_client):
        """Test event subscription"""
        # Authenticate first
        await self._authenticate_client(websocket_client)
        
        # Subscribe to events
        subscribe_msg = {
            "id": 1,
            "type": "subscribe_events"
        }
        await websocket_client.send_str(json.dumps(subscribe_msg))
        
        # Receive subscription confirmation
        msg = await websocket_client.receive()
        assert msg.type == WSMsgType.TEXT
        data = json.loads(msg.data)
        assert data["type"] == "result"
        assert data["success"] is True
        assert data["id"] == 1
    
    async def test_event_generation(self, websocket_client):
        """Test event generation"""
        # Authenticate and subscribe
        await self._authenticate_client(websocket_client)
        await self._subscribe_to_events(websocket_client)
        
        # Wait for events
        events_received = []
        for _ in range(5):  # Wait for up to 5 events
            try:
                msg = await asyncio.wait_for(websocket_client.receive(), timeout=10.0)
                if msg.type == WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    if data.get("type") == "event":
                        events_received.append(data)
            except asyncio.TimeoutError:
                break
        
        assert len(events_received) > 0
        assert all(event["event"]["event_type"] == "state_changed" for event in events_received)
    
    async def _authenticate_client(self, ws):
        """Helper method to authenticate client"""
        # Receive auth_required
        await ws.receive()
        
        # Send authentication
        auth_msg = {
            "type": "auth",
            "access_token": "dev_simulator_token"
        }
        await ws.send_str(json.dumps(auth_msg))
        
        # Receive auth_ok
        await ws.receive()
    
    async def _subscribe_to_events(self, ws):
        """Helper method to subscribe to events"""
        subscribe_msg = {
            "id": 1,
            "type": "subscribe_events"
        }
        await ws.send_str(json.dumps(subscribe_msg))
        
        # Receive subscription confirmation
        await ws.receive()
```

**Implementation Steps**:
1. Create integration test framework
2. Implement authentication flow tests
3. Add event subscription tests
4. Create event generation tests
5. Add performance benchmarks
6. Run full test suite

**Dependencies**: Task 3.1, Task 3.2

---

## Summary

This implementation plan provides a comprehensive roadmap for developing the HA Simulator using BMAD methodology. The phased approach ensures:

1. **Manageable Complexity**: Each phase builds on the previous one
2. **Clear Acceptance Criteria**: Each task has specific, testable outcomes
3. **Technical Detail**: Implementation guidance with code examples
4. **Dependency Management**: Clear task dependencies and sequencing
5. **Quality Assurance**: Testing integrated throughout development

The simulator will enable independent development and testing of the homeiq services while maintaining compatibility with the existing Home Assistant WebSocket API.

