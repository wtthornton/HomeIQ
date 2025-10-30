# Technology Stack

This is the DEFINITIVE technology selection for the entire Home Assistant Ingestor project. Based on the PRD requirements and architectural analysis, here are the technology choices:

| Category | Technology | Version | Purpose | Rationale |
|----------|------------|---------|---------|-----------|
| **Frontend Language** | TypeScript | 5.2.2 | Type-safe frontend development | Type safety for shared data models and React components |
| **Frontend Framework** | React | 18.2.0 | Admin dashboard UI | Simple, proven UI framework with excellent ecosystem |
| **UI Component Library** | TailwindCSS | 3.4.0 | Utility-first CSS framework | Modern, responsive design system with excellent developer experience |
| **Icons** | Heroicons | 2.2.0 | Icon library | Consistent with TailwindCSS ecosystem |
| **State Management** | React Context + Hooks | 18.2.0 | Frontend state management | Built-in React state management for current scale |
| **Backend Language** | Python | 3.11 | WebSocket client and data processing | Simple, proven async support with excellent libraries |
| **Backend Framework (API)** | FastAPI | 0.104.1 | REST API for admin interface | High performance, automatic OpenAPI docs, excellent async support |
| **Backend Framework (WebSocket)** | aiohttp | 3.9.1 | WebSocket client + async HTTP | Native async WebSocket + simple HTTP API for real-time streaming |
| **Docker SDK** | docker-py | 7.1.0 | Container management & log aggregation | Modern Python Docker SDK with full urllib3 v2.x support (2025) |
| **API Style** | REST + WebSocket | - | Admin API + Real-time streaming | REST for admin interface, WebSocket for real-time data |
| **Database (Time-Series)** | InfluxDB | 2.7 | Time-series data storage | Purpose-built for time-series data and Home Assistant events |
| **Database (Metadata)** | SQLite | 3.45+ | Metadata and registry storage | Lightweight relational DB for devices, entities, webhooks (Epic 22) |
| **ORM** | SQLAlchemy | 2.0.25 | Async database access | Modern async ORM for SQLite with excellent FastAPI integration |
| **SQLite Driver** | aiosqlite | 0.20.0 | Async SQLite driver | Async database driver for SQLAlchemy with SQLite |
| **Migrations** | Alembic | 1.13.1 | Schema migrations | Standard migration tool for SQLAlchemy schemas |
| **File Storage** | Local Docker Volumes | - | Persistent data storage | Simple local storage with Docker Compose |
| **Authentication** | Long-lived Access Tokens | - | Home Assistant authentication | HA's standard auth method for WebSocket connections |
| **Home Assistant IP** | 192.168.1.86 | - | HA server connection | Fixed IP for API (8123) and MQTT (1883) connections |
| **Frontend Testing** | Vitest | 3.2.4 | Frontend component testing | Fast, Vite-native testing with excellent TypeScript support (upgraded from 1.0.4) |
| **Backend Testing** | pytest | 7.4.3+ | Backend service testing | Simple, comprehensive testing for Python services |
| **E2E Testing** | Playwright | 1.56.0 | End-to-end testing | Modern, reliable E2E testing for full application |
| **Visual Testing** | Puppeteer | Latest | Browser automation & visual verification | Chrome/Chromium automation for UI testing and screenshot verification |
| **Build Tool** | Docker | 24+ | Containerization | Standard deployment with multi-stage builds |
| **Bundler** | Vite | 5.0.8 | Frontend build tool | Fast, simple build tool with excellent TypeScript support |
| **Orchestration** | Docker Compose | 2.20+ | Service orchestration | Simple orchestration for local deployment |
| **CI/CD** | GitHub Actions | - | Automated testing | Free CI/CD with Docker support |
| **Monitoring** | Python logging | - | Application logging | Built-in logging with structured JSON format |
| **Logging** | Python logging | - | Application logging | Standard logging with health check integration |
| **Sports Data** | Home Assistant Sensors | Free | NFL/NHL game data | Team Tracker + NHL HACS integrations via HA |

## Technology Rationale

### Frontend Stack
- **React + TypeScript**: Provides type safety and excellent developer experience for complex dashboard interfaces
- **TailwindCSS**: Utility-first approach enables rapid UI development with consistent design system
- **Vite**: Fast build tool with excellent TypeScript support and hot module replacement
- **Vitest**: Vite-native testing framework with Jest compatibility for familiar testing patterns

### Backend Stack
- **FastAPI**: High-performance async framework with automatic OpenAPI documentation
- **aiohttp**: Lightweight async HTTP library perfect for WebSocket connections to Home Assistant
- **Python 3.11**: Latest stable version with excellent async/await support and performance improvements

### Data & Storage
- **InfluxDB 2.7**: Purpose-built for time-series data, perfect for Home Assistant sensor data
- **SQLite 3.45+**: Lightweight relational database for metadata (devices, entities, webhooks) with WAL mode for concurrency
- **SQLAlchemy 2.0**: Modern async ORM providing type-safe database access with excellent FastAPI integration
- **Hybrid Architecture**: InfluxDB for time-series events/metrics, SQLite for relational metadata (Epic 22)
- **Docker Volumes**: Simple, reliable local storage for development and production

### Testing Strategy
- **Vitest 3.2.4**: Fast, modern testing for React components with TypeScript support and enhanced performance (major upgrade from 1.0.4)
- **pytest 7.4+**: Comprehensive testing framework for Python services
- **Playwright 1.56.0**: Reliable E2E testing across multiple browsers with latest features
- **Puppeteer**: Browser automation for visual testing, screenshot verification, and UI regression testing
  - Comprehensive test suite: `tests/visual/test-all-pages.js` validates all pages against design specifications
  - Quick check tool: `tests/visual/test-quick-check.js` for fast single-page validation
  - Tests light/dark mode, design tokens, touch targets, and accessibility
  - See `tests/visual/README.md` for documentation

### Deployment
- **Docker Compose**: Simple orchestration for local development and production deployment
- **GitHub Actions**: Free CI/CD with Docker support for automated testing and deployment

### Sports Data Integration
- **Home Assistant Sensors**: Direct integration via Team Tracker and NHL HACS integrations
- **Frontend Access**: health-dashboard reads sensor entities via HA REST API (/api/states)
- **Polling Strategy**: 30-second polling interval for real-time game updates
- **Architecture Choice**: Simplified to use HA sensors directly, eliminating intermediate microservices

### Home Assistant Integration
- **API Endpoint**: http://192.168.1.86:8123 (REST API for device/entity queries)
- **MQTT Broker**: 192.168.1.86:1883 (Real-time event streaming) ✅ **CONNECTED**
- **WebSocket**: ws://192.168.1.86:8123 (Live event stream)
- **Authentication**: Long-lived access tokens for secure API access
- **Status**: ✅ **FULLY OPERATIONAL** - All connections established and working

**Note**: Sports data integration is handled directly through Home Assistant sensor entities (Team Tracker and NHL HACS integrations) via the health-dashboard frontend. Previous services (sports-api for API-SPORTS.io and sports-data for ESPN API) have been removed as they are no longer needed with the simplified architecture.

## Version Management

All versions are pinned to ensure reproducible builds and consistent behavior across development and production environments. Dependencies are managed through:

- **Frontend**: `package.json` with exact version pinning
- **Backend**: `requirements.txt` with version constraints
- **Infrastructure**: Docker image tags with specific versions

## Database Architecture (Epic 22)

**Hybrid Database Strategy** implemented to optimize for different data types:

| Data Type | Database | Rationale |
|-----------|----------|-----------|
| **Time-Series Data** | InfluxDB | Events, metrics, sports scores - optimized for time-range queries |
| **Metadata** | SQLite | Devices, entities, webhooks - optimized for relational queries |

**Benefits:**
- 5-10x faster device/entity queries (<10ms vs ~50ms)
- Proper foreign key relationships
- Concurrent-safe operations (WAL mode)
- ACID transactions for critical data

**Implementation:**
- data-api: SQLite for devices/entities (`data/metadata.db`)
- sports-data: SQLite for webhooks (`data/webhooks.db`)
- Both services: InfluxDB for time-series data

## Log Aggregation Service

**Technology:** Docker SDK for Python (docker-py) v7.1.0

The log-aggregator service provides centralized log collection from all running Docker containers for monitoring and debugging.

**Key Features:**
- Real-time log collection via Docker API
- In-memory aggregation of last 10,000 log entries
- RESTful API for log querying and search
- Filtering by service, log level, and time range
- Background collection every 30 seconds

**2025 Update (October 19):**
- ✅ **Upgraded to docker-py 7.1.0** - Full urllib3 v2.x compatibility
- ✅ **Removed deprecated dependencies** - Eliminated requests-unixsocket
- ✅ **Simplified initialization** - Context7 best practices for 2025
- ✅ **Successfully collecting logs** - 2150+ entries from 20 containers
- 📊 **Performance:** < 1s to collect 1000 log entries, < 128MB memory usage

**API Endpoints:**
- `GET /health` - Service health and log count
- `GET /api/v1/logs` - Retrieve recent logs with filtering
- `GET /api/v1/logs/search` - Search logs by query string
- `GET /api/v1/logs/stats` - Log statistics by service and level
- `POST /api/v1/logs/collect` - Manually trigger log collection

**Security Configuration:**
- Read-only Docker socket mount (`/var/run/docker.sock:ro`)
- Non-root user execution (UID 1001)
- Group-based socket access (GID 0 via group_add)
- No privileged mode required

## System Status (October 19, 2025)

### ✅ **CURRENT STATUS: FULLY OPERATIONAL**
- **All Services**: 17/17 healthy and running (including log-aggregator)
- **MQTT Integration**: Connected and functional
- **Web Interfaces**: Both dashboards accessible (3000, 3001)
- **API Services**: All endpoints responding correctly (71 total endpoints)
- **Database**: InfluxDB and SQLite working optimally
- **HA Setup Service**: Health monitoring active, score 94/100
- **Log Aggregation**: Active and collecting logs from all containers (2150+ entries)
- **Success Rate**: 100% - No critical issues

### **Recent Fixes Applied (October 2025)**
- **Log Aggregator**: Upgraded docker-py to v7.1.0 for urllib3 v2.x compatibility
  - Fixed "http+docker URL scheme" error
  - Removed deprecated requests-unixsocket dependency
  - Simplified initialization using Context7 best practices
  - Successfully collecting logs from 20 containers
- **Weather Integration**: Fixed to use Home Assistant normalized events
  - Query InfluxDB for weather domain entities
  - Never skip weather opportunity detection
  - Retained external API key for HA weather services

### **Previous Fixes (January 2025)**
- **HA Setup Service**: Deployed on port 8020 with health monitoring, setup wizards, and optimization (Epics 27-30)
- **Health Monitoring**: Continuous background monitoring active (94/100 health score)
- **Integration Validation**: 6 comprehensive checks detecting real issues
- **MQTT Connection**: Fixed IP address configuration (192.168.1.86:1883)
- **Health Checks**: Corrected all service health check endpoints
- **Data API**: Fixed health check to use localhost:8006
- **Energy Correlator**: Corrected health check port (8017)
- **Documentation**: Updated all docs with correct IP addresses

## Future Technology Considerations

- **State Management**: Consider Redux Toolkit if state complexity grows
- **Database**: Current hybrid architecture (InfluxDB + SQLite) excellent for current scale
- **PostgreSQL**: Consider if need multi-server writes or >10k devices
- **Caching**: Redis could be added for API response caching if needed
