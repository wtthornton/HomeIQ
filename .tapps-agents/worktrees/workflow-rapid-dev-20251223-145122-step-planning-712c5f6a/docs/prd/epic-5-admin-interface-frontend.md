# Epic 5 Admin Interface & Frontend

**Epic Goal:**
Implement a comprehensive admin web interface for system monitoring, configuration management, and data visualization. This epic provides users with an intuitive dashboard to monitor ingestion health, view recent events, manage configuration, and perform basic data queries.

### Story 5.1: Admin REST API Development

As a system administrator,
I want a REST API for admin operations,
so that I can monitor system health and manage configuration through a web interface.

**Acceptance Criteria:**
1. REST API provides endpoints for system health monitoring (`/api/health`)
2. API includes statistics endpoints for event processing metrics (`/api/stats`)
3. Configuration management endpoints allow viewing and updating system settings (`/api/config`)
4. Recent events endpoint provides filtered access to captured data (`/api/events/recent`)
5. All endpoints return structured JSON responses with proper error handling
6. API includes request validation and authentication for sensitive operations
7. API documentation is available through OpenAPI/Swagger specification

### Story 5.2: Health Dashboard Interface

As a system administrator,
I want a real-time health dashboard,
so that I can quickly assess system status and identify any issues requiring attention.

**Acceptance Criteria:**
1. Dashboard displays service status indicators for all components (WebSocket, Enrichment, InfluxDB, Weather API)
2. Real-time event capture metrics show events per hour, total today, and error rates
3. Connection health status displays WebSocket connection state and last reconnect information
4. Recent events feed shows latest captured events with entity_id, state changes, and timestamps
5. Dashboard auto-refreshes every 30 seconds with manual refresh capability
6. Color-coded status indicators (green=healthy, yellow=warning, red=error) provide immediate visual feedback
7. Clickable service status provides drill-down to detailed health information and logs

### Story 5.3: Configuration Management Interface

As a system administrator,
I want a web-based configuration interface,
so that I can update system settings without manually editing configuration files.

**Acceptance Criteria:**
1. Configuration form displays current Home Assistant connection settings with masked sensitive data
2. Weather API configuration section allows updating API key and location settings
3. Data retention policy settings can be modified through the interface
4. Environment variables are displayed with masked sensitive values and update capabilities
5. Configuration changes are validated before saving with clear error messages
6. Save/apply buttons trigger service restart confirmation for affected components
7. Backup/restore functionality allows configuration versioning and rollback

### Story 5.4: Data Query Interface

As a data analyst,
I want a web interface to query and explore captured data,
so that I can perform basic analysis and data validation without complex database queries.

**Acceptance Criteria:**
1. Time range selector supports predefined ranges (hour, day, week, month) and custom date ranges
2. Entity filter dropdown with search functionality allows filtering by specific Home Assistant entities
3. Weather context filter enables filtering by temperature ranges and weather conditions
4. Query results table displays events with pagination for large datasets
5. Export functionality provides data download in CSV and JSON formats
6. Basic visualization charts show event patterns and trends over time
7. Query builder includes common patterns (energy usage, occupancy patterns) for quick analysis

### Story 5.5: Frontend Build & Deployment

As a developer,
I want a complete frontend build and deployment pipeline,
so that the admin interface can be deployed and maintained alongside the backend services.

**Acceptance Criteria:**
1. React + TypeScript frontend builds successfully with Vite build tool
2. Frontend container builds and deploys via Docker with nginx serving static files
3. Frontend integrates with backend REST API through configured base URL
4. Build process includes TypeScript compilation, linting, and testing
5. Production build optimizes bundle size and performance for deployment
6. Frontend container includes health checks and proper logging configuration
7. Docker Compose integration includes frontend service with proper networking

### Story 5.6: CLI Tools & Documentation

As a power user,
I want comprehensive CLI tools and documentation,
so that I can manage the system through command-line interfaces when needed.

**Acceptance Criteria:**
1. CLI command reference documentation provides examples for all Docker Compose operations
2. Health check scripts can be executed via command line for system monitoring
3. Log viewing commands support filtering and real-time streaming of service logs
4. Configuration validation commands check system settings and connectivity
5. Troubleshooting command sequences guide users through common issue resolution
6. Service management commands (start, stop, restart, status) provide full control
7. CLI tools include help text and error handling for user guidance

**Technical Feasibility Assessment:**
Epic 5 is technically feasible with high confidence. All components use proven technologies (React, TypeScript, FastAPI) with established patterns. The architecture provides clear separation between frontend and backend concerns, and the API design supports the required functionality.
