# Epic 1 Foundation & Core Infrastructure

**Epic Goal:**
Establish project setup, Docker orchestration, and basic Home Assistant WebSocket connection with authentication and health monitoring. This epic creates the foundational infrastructure that enables reliable data capture and provides immediate value through basic connectivity testing.

### Story 1.1: Project Setup & Docker Infrastructure

As a Home Assistant user,
I want a complete Docker Compose setup with all required services configured,
so that I can deploy the ingestion layer with a single command.

**Acceptance Criteria:**
1. Docker Compose file includes InfluxDB, ingestion service, and weather API service containers
2. All services are properly networked and can communicate with each other
3. Environment variables are configured for Home Assistant connection and API keys
4. Services start successfully and remain running without errors
5. Basic health check endpoints are available for all services
6. Logging is configured and output is visible in Docker logs
7. Services automatically restart on failure with proper restart policies

### Story 1.2: Home Assistant WebSocket Authentication

As a system administrator,
I want secure authentication with Home Assistant using long-lived access tokens,
so that the ingestion service can establish reliable WebSocket connections.

**Acceptance Criteria:**
1. Long-lived access token is properly configured and validated
2. WebSocket connection is established successfully with Home Assistant
3. Authentication errors are logged with clear error messages
4. Connection retry logic handles authentication failures gracefully
5. Token validation occurs before attempting WebSocket connection
6. Authentication status is exposed through health check endpoint
7. Invalid or expired tokens result in clear error messages and service restart

### Story 1.3: Basic WebSocket Event Subscription

As a Home Assistant user,
I want the ingestion service to subscribe to all state_changed events,
so that I can verify the system is capturing events from my Home Assistant instance.

**Acceptance Criteria:**
1. WebSocket connection subscribes to all state_changed events successfully
2. Incoming events are logged with basic information (entity_id, state, timestamp)
3. Connection automatically reconnects on network interruption
4. Event subscription is maintained across reconnections
5. Basic event validation ensures only valid Home Assistant events are processed
6. Connection status is monitored and reported through health checks
7. Event capture rate is tracked and logged for monitoring purposes
