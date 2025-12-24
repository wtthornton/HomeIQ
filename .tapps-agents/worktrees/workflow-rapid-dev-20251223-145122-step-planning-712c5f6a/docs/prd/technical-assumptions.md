# Technical Assumptions

### Repository Structure: Monorepo

Single repository with Docker Compose orchestration containing all services (ingestion, weather API, database) in a unified structure. This simplifies deployment and maintenance for home users while keeping all components tightly integrated.

### Service Architecture: Microservices

Microservices approach with separate containers for WebSocket client, enrichment pipeline, and database. This provides loose coupling, independent scaling, and fault isolation while maintaining simple orchestration through Docker Compose.

### Testing Requirements: Unit + Integration

Comprehensive testing approach including unit tests for individual components, integration tests for service interactions, and end-to-end tests for complete data flow. Focus on testing WebSocket connectivity, data transformation, and database operations with mock Home Assistant instances for reliable CI/CD.

### Additional Technical Assumptions and Requests

- **Language:** Python with aiohttp for WebSocket client and asyncio for concurrent processing
- **Database:** InfluxDB 2.x for time-series storage with InfluxQL/SQL query support
- **Deployment:** Docker Compose orchestration with local deployment focus
- **Authentication:** Long-lived access tokens for Home Assistant WebSocket API
- **External APIs:** Weather API integration (OpenWeatherMap/WeatherAPI) with rate limiting and fallback handling
- **Monitoring:** Structured logging with health check endpoints for service monitoring
- **Storage:** Local data storage for privacy with optional cloud backup capabilities
- **Network:** WebSocket API for real-time event capture with automatic reconnection
- **Schema:** Optimized InfluxDB schema with proper tagging (entity_id, domain, device_class) for efficient querying
- **Retention:** 1-year data retention policy with automatic cleanup and storage optimization
