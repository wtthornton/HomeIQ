# Key Concepts

This document introduces the core concepts and terminology of the Home Assistant Ingestor project and BMAD framework integration.

## BMAD Framework Concepts

### Agents
Specialized AI personas that handle specific aspects of development:

- **@analyst** - Business analysis and research
- **@pm** - Product management and PRD creation  
- **@architect** - System architecture and design
- **@dev** - Full-stack development and implementation
- **@qa** - Quality assurance and testing
- **@po** - Product ownership and story management
- **@sm** - Scrum master and process management
- **@ux-expert** - User experience design
- **@bmad-master** - Universal task executor

### Tasks
Executable workflows that agents can run:

- **create-doc** - Document creation from templates
- **execute-checklist** - Quality validation workflows
- **shard-doc** - Document organization and sharding
- **document-project** - Comprehensive project documentation

### Templates
YAML-based document templates for consistent output:

- **prd-tmpl.yaml** - Product Requirements Document template
- **architecture-tmpl.yaml** - Architecture document template
- **story-tmpl.yaml** - Development story template

### Quality Gates
Validation checkpoints that ensure quality:

- **architect-checklist** - Architecture validation
- **story-dod-checklist** - Story definition of done
- **pm-checklist** - Product management validation

## Project-Specific Concepts

### Microservices Architecture
The Home Assistant Ingestor uses a microservices pattern with:

- **websocket-ingestion** - Real-time event capture from Home Assistant (writes directly to InfluxDB - Epic 31)
- **admin-api** - REST API for dashboard interactions
- **health-dashboard** - React-based monitoring interface
- **data-api** - Query API for events and metadata (Epic 13)
- **data-retention** - Cleanup and backup management

**Note**: enrichment-pipeline service was **deprecated in Epic 31 (October 2025)**. All normalization now happens inline in websocket-ingestion with direct writes to InfluxDB.

### Data Flow Concepts

#### Event-Driven Architecture
- **WebSocket Stream** - Real-time data from Home Assistant
- **Event Queue** - Asynchronous processing buffer
- **Batch Processing** - Efficient data handling
- **Time-Series Storage** - InfluxDB for sensor data

#### API Integration Patterns
- **REST API** - Standard HTTP endpoints for admin interface
- **WebSocket API** - Real-time communication with Home Assistant
- **Health Checks** - Service monitoring and status endpoints

### Technology Stack Concepts

#### Frontend Architecture
- **Component-Based UI** - React components with TypeScript
- **Utility-First CSS** - TailwindCSS for styling
- **State Management** - React Context and hooks
- **Build Optimization** - Vite for fast development and builds

#### Backend Architecture
- **Async Processing** - Python asyncio for concurrent operations
- **API Framework** - FastAPI for high-performance REST APIs
- **WebSocket Client** - aiohttp for real-time connections
- **Data Validation** - Pydantic models for type safety

#### Infrastructure Concepts
- **Container Orchestration** - Docker Compose for service management
- **Service Discovery** - Internal networking between containers
- **Persistent Storage** - Docker volumes for data persistence
- **Health Monitoring** - Built-in health checks for all services

## Development Concepts

### BMAD Workflow
The development process follows BMAD methodology:

1. **Planning Phase** - PRD and Architecture creation
2. **Story Creation** - Detailed development stories with acceptance criteria
3. **Implementation** - Development with embedded context and guidance
4. **Quality Assurance** - Automated testing and validation
5. **Documentation** - Continuous documentation updates

### Story Management
- **Epics** - Large feature groupings
- **Stories** - Individual development tasks
- **Tasks** - Specific implementation steps
- **Acceptance Criteria** - Definition of done requirements

### Quality Assurance
- **Unit Tests** - Component and service testing
- **Integration Tests** - Service interaction testing
- **E2E Tests** - Full application workflow testing
- **Code Quality** - Linting, formatting, and standards compliance

## Data Model Concepts

### Time-Series Data
Home Assistant events are stored as time-series data:

- **Measurement** - Data type (sensor, binary, etc.)
- **Tags** - Categorization metadata
- **Fields** - Actual data values
- **Timestamp** - When the event occurred

### Data Normalization
Raw Home Assistant events are processed:

- **Unit Conversion** - Standardized units of measurement
- **Schema Validation** - Consistent data structure
- **Enrichment** - Additional context (weather, location)
- **Quality Metrics** - Data validation and quality scoring

### Event Types
Different categories of Home Assistant events:

- **State Changes** - Device state transitions
- **Sensor Readings** - Continuous sensor data
- **Binary Sensors** - On/off device states
- **Automation Triggers** - Rule execution events

## Integration Concepts

### Home Assistant Integration
- **Long-Lived Access Tokens** - Secure authentication
- **WebSocket API** - Real-time event streaming
- **Entity States** - Device and sensor status
- **Event History** - Historical data access

### External API Integration
- **Weather Data** - OpenWeatherMap API integration
- **Rate Limiting** - API usage management
- **Error Handling** - Graceful failure handling
- **Caching** - Response caching for performance

### Data Export
- **CSV Export** - Historical data download
- **JSON API** - Programmatic data access
- **Real-time Streaming** - Live data feeds
- **Batch Processing** - Scheduled data exports

## Security Concepts

### Authentication & Authorization
- **Token-Based Auth** - Secure API access
- **Role-Based Access** - Permission management
- **Session Management** - User session handling
- **API Security** - Rate limiting and validation

### Data Protection
- **Input Validation** - Sanitize all inputs
- **Output Encoding** - Prevent injection attacks
- **Secure Storage** - Encrypted sensitive data
- **Audit Logging** - Track all operations

### Network Security
- **CORS Configuration** - Cross-origin request control
- **HTTPS Enforcement** - Encrypted communications
- **Firewall Rules** - Network access control
- **Service Isolation** - Container network segmentation

## Monitoring Concepts

### Health Monitoring
- **Service Health** - Individual service status
- **System Health** - Overall system status
- **Dependency Health** - External service status
- **Performance Metrics** - System performance indicators

### Logging Strategy
- **Structured Logging** - JSON-formatted log entries
- **Log Levels** - DEBUG, INFO, WARNING, ERROR
- **Log Aggregation** - Centralized log collection
- **Log Rotation** - Automated log management

### Alerting
- **Threshold-Based** - Performance and error alerts
- **Pattern-Based** - Anomaly detection
- **Escalation** - Alert routing and escalation
- **Notification** - Multi-channel alert delivery

## Deployment Concepts

### Environment Management
- **Development** - Local development environment
- **Staging** - Pre-production testing
- **Production** - Live environment
- **Configuration** - Environment-specific settings

### Container Strategy
- **Multi-Stage Builds** - Optimized Docker images
- **Base Images** - Consistent runtime environments
- **Volume Management** - Persistent data storage
- **Network Configuration** - Service communication

### CI/CD Pipeline
- **Automated Testing** - Quality validation
- **Build Automation** - Consistent builds
- **Deployment Automation** - Automated deployments
- **Rollback Capability** - Quick recovery from issues

## Performance Concepts

### Scalability
- **Horizontal Scaling** - Add more service instances
- **Vertical Scaling** - Increase resource allocation
- **Load Balancing** - Distribute traffic
- **Caching** - Reduce database load

### Optimization
- **Async Processing** - Non-blocking operations
- **Batch Processing** - Efficient data handling
- **Connection Pooling** - Database connection reuse
- **Resource Management** - Memory and CPU optimization

### Monitoring
- **Performance Metrics** - Response times and throughput
- **Resource Usage** - CPU, memory, and disk usage
- **Error Rates** - Failure and success rates
- **User Experience** - Frontend performance metrics

These key concepts provide the foundation for understanding and working with the Home Assistant Ingestor project and its integration with the BMAD framework methodology.
