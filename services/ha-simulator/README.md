# Home Assistant Simulator

A WebSocket server that simulates Home Assistant's WebSocket API for development and testing of the homeiq project.

## Overview

The HA Simulator provides a realistic Home Assistant environment without requiring a running Home Assistant instance. It generates authentic WebSocket events based on real data patterns and allows for configurable scenarios.

## Features

- **WebSocket API Compatibility**: Full compatibility with Home Assistant WebSocket API
- **Realistic Event Generation**: Based on analysis of real HA event logs
- **Configurable Entities**: Support for multiple entity types and domains
- **Authentication Simulation**: Proper HA authentication flow
- **Event Subscription Management**: Handles multiple client subscriptions
- **Health Monitoring**: Built-in health check endpoints
- **Docker Integration**: Easy deployment with Docker Compose

## Quick Start

### Using Docker Compose (Recommended)

1. **Start the simulator**:
   ```bash
   docker-compose -f docker-compose.dev.yml up ha-simulator
   ```

2. **Connect to the simulator**:
   - WebSocket URL: `ws://localhost:8123/api/websocket`
   - Authentication Token: `dev_simulator_token`

3. **Check health**:
   ```bash
   curl http://localhost:8123/health
   ```

### Manual Setup

1. **Install dependencies**:
   ```bash
   cd services/ha-simulator
   pip install -r requirements.txt
   ```

2. **Run the simulator**:
   ```bash
   python -m src.main
   ```

## Configuration

The simulator is configured via `config/simulator-config.yaml`:

```yaml
simulator:
  name: "HA Development Simulator"
  version: "2025.10.1"
  port: 8123

authentication:
  enabled: true
  token: "dev_simulator_token"

entities:
  - entity_id: "sensor.living_room_temperature"
    domain: "sensor"
    device_class: "temperature"
    base_value: 22.0
    variance: 2.0
    update_interval: 30
    unit_of_measurement: "°C"
```

### Environment Variables

- `SIMULATOR_PORT`: WebSocket server port (default: 8123)
- `SIMULATOR_AUTH_TOKEN`: Authentication token (default: dev_simulator_token)
- `SIMULATOR_HA_VERSION`: HA version to simulate (default: 2025.10.1)
- `SIMULATOR_LOG_LEVEL`: Logging level (default: INFO)

## API Usage

### WebSocket Connection

```javascript
const ws = new WebSocket('ws://localhost:8123/api/websocket');

ws.onopen = function() {
    console.log('Connected to HA Simulator');
};

ws.onmessage = function(event) {
    const message = JSON.parse(event.data);
    console.log('Received:', message);
};
```

### Authentication

```javascript
// Wait for auth_required
ws.onmessage = function(event) {
    const message = JSON.parse(event.data);
    
    if (message.type === 'auth_required') {
        // Send authentication
        ws.send(JSON.stringify({
            type: 'auth',
            access_token: 'dev_simulator_token'
        }));
    } else if (message.type === 'auth_ok') {
        console.log('Authenticated successfully');
        // Subscribe to events
        ws.send(JSON.stringify({
            id: 1,
            type: 'subscribe_events'
        }));
    }
};
```

### Event Subscription

```javascript
// Subscribe to all events
ws.send(JSON.stringify({
    id: 1,
    type: 'subscribe_events'
}));

// Handle events
ws.onmessage = function(event) {
    const message = JSON.parse(event.data);
    
    if (message.type === 'event') {
        const eventData = message.event;
        console.log('Event:', eventData.event_type, eventData.data);
    }
};
```

## Entity Types

The simulator supports various entity types based on real HA data:

### Sensors
- **Temperature Sensors**: `sensor.living_room_temperature`
- **Current Sensors**: `sensor.wled_estimated_current`
- **Network Sensors**: `sensor.archer_be800_download_speed`
- **System Sensors**: `sensor.home_assistant_core_cpu_percent`

### Other Entities
- **Sun Entity**: `sun.sun`
- **Custom Entities**: Configurable via YAML

## Event Patterns

Events are generated based on:

1. **Real Data Analysis**: Analyzes `ha_events.log` for patterns
2. **Configurable Intervals**: Each entity has its own update interval
3. **Realistic Values**: Base values with configurable variance
4. **State Transitions**: Proper old_state/new_state handling

## Integration with homeiq

The simulator integrates seamlessly with existing homeiq services:

1. **WebSocket Ingestion**: Connects to simulator instead of real HA
2. **Enrichment Pipeline**: Processes simulated events
3. **Weather API**: Enriches events with weather data
4. **Admin API**: Monitors simulator health
5. **Health Dashboard**: Displays simulator status

### Development Workflow

1. **Start simulator**: `docker-compose up ha-simulator`
2. **Update WebSocket service**: Point to `ws://ha-simulator:8123/api/websocket`
3. **Develop and test**: All services work with simulated data
4. **Switch back**: Change to real HA when needed

## Testing

Run the test suite:

```bash
cd services/ha-simulator
python -m pytest tests/
```

### Test Coverage

- WebSocket server functionality
- Authentication flow
- Event subscription management
- Event generation
- Configuration management

## Monitoring

### Health Check

```bash
curl http://localhost:8123/health
```

Response:
```json
{
  "status": "healthy",
  "service": "ha-simulator",
  "version": "2025.10.1",
  "clients": 2,
  "authenticated_clients": 1,
  "subscribed_clients": 1
}
```

### Logs

View simulator logs:

```bash
docker-compose logs -f ha-simulator
```

## Troubleshooting

### Common Issues

1. **Connection Refused**
   - Check if simulator is running: `docker-compose ps ha-simulator`
   - Verify port 8123 is available

2. **Authentication Failed**
   - Ensure correct token: `dev_simulator_token`
   - Check authentication configuration

3. **No Events Received**
   - Verify event subscription
   - Check entity configuration
   - Review simulator logs

### Debug Mode

Enable debug logging:

```bash
export SIMULATOR_LOG_LEVEL=DEBUG
docker-compose up ha-simulator
```

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   WebSocket     │    │   Authentication │    │   Subscription  │
│     Server      │◄──►│     Manager      │    │     Manager     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │
         ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Event Generator │◄──►│ Data Patterns    │    │ Configuration   │
│                 │    │    Analyzer      │    │    Manager      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Contributing

1. Follow the existing code structure
2. Add tests for new features
3. Update documentation
4. Ensure Docker compatibility

## License

Part of the homeiq project. See main project license.


## Related Documentation

- [WebSocket Ingestion](../websocket-ingestion/README.md) - Primary consumer
- [Docker Compose Development](../../docker-compose.dev.yml)
- [CLAUDE.md](../../CLAUDE.md)

## Version History

### 2.1 (November 15, 2025)
- Documentation verified for 2025 standards
- WebSocket API compatibility documented
- Event generation patterns reference
- Docker integration guide

### 2.0 (October 2025)
- Realistic event generation from real HA logs
- Configurable entities via YAML
- Multi-client support
- Health monitoring endpoints

### 1.0 (Initial Release)
- Basic Home Assistant WebSocket simulation
- Simple event generation

---

**Last Updated:** November 15, 2025
**Version:** 2.1
**Status:** Development Only (Not in Production) 🔧
**Port:** 8123 (Development environment only)
**Note:** For development/testing only - not deployed in production docker-compose
