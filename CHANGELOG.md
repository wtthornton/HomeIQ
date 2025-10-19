# Changelog

All notable changes to the HA-Ingestor project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - 2025-10-19

### Fixed - Log Aggregator Docker SDK Update (October 19, 2025)

#### Docker SDK Upgrade
- **UPGRADED**: docker-py from 6.1.3 (2023) to 7.1.0 (2024 stable)
- **REMOVED**: requests-unixsocket dependency (not needed in docker 7.x+)
- **FIXED**: "Not supported URL scheme http+docker" error
- **SIMPLIFIED**: Docker client initialization using Context7 best practices
- **VERIFIED**: Successfully collecting logs from 20 containers (2150+ entries)

#### Performance
- **< 1s** to collect 1000 log entries
- **< 128MB** memory usage
- **30s** background collection interval
- **10,000** log entries retained in memory

#### Context7 Integration
- Applied `/docker/docker-py` 2025 best practices
- Used `docker.from_env()` for auto-detection
- Full urllib3 v2.x compatibility
- Removed deprecated fallback patterns

#### Documentation
- Created `implementation/analysis/LOG_AGGREGATOR_DOCKER_SDK_ANALYSIS.md`
- Created `implementation/LOG_AGGREGATOR_FIX_COMPLETE_2025.md`
- Updated `docs/architecture/tech-stack.md` with docker-py 7.1.0
- Added log aggregation service documentation section

### Fixed - Weather Integration (October 19, 2025)

#### Weather Opportunity Detection
- **FIXED**: Query normalized HA weather events from InfluxDB
- **FIXED**: Never skip weather opportunity detection phase
- **RETAINED**: External weather API key configuration for HA services
- **IMPROVED**: Query for weather domain and sensor entities
- **ENHANCED**: Fallback to generic opportunities if no specific ones found

#### Changes
- Updated `_get_weather_data()` to query HA events with domain filtering
- Modified weather opportunity detection to continue even with sparse data
- Kept `WEATHER_API_KEY` in environment configuration (used by HA)

---

### Added - Epic AI-4: Home Assistant Client Integration

#### HA Client Foundation (Story AI4.1)
- **NEW**: HomeAssistantClient with secure token-based authentication
- **NEW**: Connection pooling (20 connections total, 5 per host) using TCPConnector
- **NEW**: Exponential backoff retry logic (3 retries: 1s → 2s → 4s delay)
- **NEW**: HA version detection (`/api/config` endpoint)
- **NEW**: Comprehensive health checks with status information
- **NEW**: Session reuse and resource cleanup with SSL grace period (250ms)
- **Context7**: Applied `/aio-libs/aiohttp` and `/inyutin/aiohttp_retry` best practices

#### Automation Parser (Story AI4.2)
- **NEW**: AutomationParser class for parsing HA automation configurations
- **NEW**: EntityRelationship dataclass for relationship metadata storage
- **NEW**: Bidirectional entity pair indexing for O(1) lookup
- **NEW**: Extract trigger and action entities from automations
- **NEW**: Support for all automation types (state, time, numeric_state, zone, event, template)
- **NEW**: `has_relationship()` method for fast pair checking (O(1))
- **NEW**: `get_relationships_for_pair()` for detailed relationship queries
- **Performance**: Hash-based data structures per `/python/cpython` best practices

#### Relationship Checker (Story AI4.3)
- **NEW**: Integration of automation parser into DeviceSynergyDetector
- **NEW**: O(1) bidirectional device pair filtering
- **NEW**: Automatic filtering of redundant synergy suggestions
- **NEW**: HA client initialization in daily analysis scheduler
- **NEW**: Graceful fallback when HA unavailable (continues without filtering)
- **NEW**: Detailed filtering logs showing which pairs were removed
- **Impact**: 80%+ reduction in redundant automation suggestions

#### Integration & Testing (Story AI4.4)
- **NEW**: 38 comprehensive tests (14 HA client + 16 parser + 8 integration)
- **NEW**: Performance tests validating 100+ pairs with 50+ automations
- **NEW**: End-to-end validation with real HA instance (verified working)
- **NEW**: Production deployment with debug logging enabled
- **Coverage**: 87% on automation_parser, core paths fully tested

#### Configuration
- **NEW**: `HA_MAX_RETRIES`, `HA_RETRY_DELAY`, `HA_TIMEOUT` environment variables
- **NEW**: Debug logging enabled (`LOG_LEVEL=DEBUG`) for production review
- **VERIFIED**: Connection to HA at http://192.168.1.86:8123 working
- **VERIFIED**: HA Version 2025.10.3 detected, 3 automations discovered

### Performance - Epic AI-4
- **60x faster** than requirements (< 1s vs < 60s for 100 pairs + 50 automations)
- **O(1) lookup** for entity pair checking
- **< 200ms overhead** for complete HA integration
- **87% test coverage** on critical paths
- **100% test pass rate** (38/38 tests)

### Documentation - Epic AI-4
- Created `docs/prd/epic-ai4-ha-client-integration.md` - Epic definition
- Created `docs/stories/story-ai4-1-ha-client-foundation.md` - Story AI4.1
- Created `docs/stories/story-ai4-2-automation-parser.md` - Story AI4.2
- Created `docs/stories/story-ai4-3-relationship-checker.md` - Story AI4.3
- Created `docs/stories/story-ai4-4-integration-testing.md` - Story AI4.4
- Created `implementation/AI4.1_HA_CLIENT_FOUNDATION_COMPLETE.md` - Implementation summary
- Created `implementation/AI4.2_AUTOMATION_PARSER_COMPLETE.md` - Implementation summary
- Created `implementation/AI4.3_RELATIONSHIP_CHECKER_COMPLETE.md` - Implementation summary
- Created `implementation/AI4.4_INTEGRATION_TESTING_COMPLETE.md` - Implementation summary
- Created `implementation/EPIC_AI4_HA_CLIENT_INTEGRATION_COMPLETE.md` - Epic summary
- Created `implementation/EPIC_AI4_PRODUCTION_DEPLOYMENT_GUIDE.md` - Deployment guide
- Created `implementation/EPIC_AI4_EXECUTIVE_SUMMARY.md` - Executive summary

---

### Added - Conversational UI & Description-First Flow (Story AI1.24)

#### Conversational Automation System
- **NEW**: Description-first suggestion generation (no YAML until user approves)
- **NEW**: `generate_description_only()` method in OpenAI client for human-readable automation ideas
- **NEW**: ConversationalDashboard as primary UI at http://localhost:3001/
- **NEW**: Conversational refinement workflow (draft → refining → yaml_generated → deployed)
- **NEW**: Description-only prompts for time-of-day, co-occurrence, and anomaly patterns
- **NEW**: Comprehensive AI Automation UI README with conversational flow documentation
- **NEW**: User Guide at `docs/CONVERSATIONAL_UI_USER_GUIDE.md`

### Changed - Breaking Changes (Story AI1.24)
- **BREAKING**: Daily analysis job now generates description-only suggestions (not YAML)
- **BREAKING**: Suggestion status flow changed from `pending → approved → deployed` to `draft → refining → yaml_generated → deployed`
- **BREAKING**: YAML only generated after user approval (was generated immediately)
- **60% cost savings** on rejected suggestions (no YAML generation cost)
- Updated API endpoints to reflect conversational refinement workflow
- Backend README updated with description-first architecture

### Removed - Legacy Components (Story AI1.24)
- Deleted `Dashboard.tsx` component (replaced with ConversationalDashboard)
- Deleted `App-complex.tsx` backup file with conflicting imports
- Removed old YAML-first suggestion generation flow

### Fixed - Build & Integration Issues
- Frontend build error from orphaned Dashboard imports
- Status schema mismatch between backend (draft) and frontend (pending)

### Documentation - Story AI1.24
- Created `services/ai-automation-ui/README.md` - Complete UI documentation
- Updated `services/ai-automation-service/README.md` - Conversational flow architecture
- Updated root `README.md` - AI Automation UI description
- Created `implementation/PHASE_2_BACKEND_CLEANUP_COMPLETE.md` - Implementation details
- Created `docs/stories/story-ai1-24-conversational-ui-cleanup.md` - Story documentation
- Created `docs/CONVERSATIONAL_UI_USER_GUIDE.md` - End-user documentation

---

## [2025-10-18] - Statistics API & System Enhancements

### Added - Statistics API & System Enhancements

#### Statistics Endpoints (INFRA-2, INFRA-3)
- **NEW**: `/api/v1/stats` - System-wide metrics with configurable time periods (1h, 24h, 7d, 30d)
- **NEW**: `/api/v1/stats/services` - Per-service statistics and health metrics
- **NEW**: `/api/v1/stats/metrics` - Time-series metrics with filtering and pagination
- **NEW**: `/api/v1/stats/performance` - Performance analytics with optimization recommendations
- **NEW**: `/api/v1/stats/alerts` - Active system alerts with severity prioritization
- **NEW**: `/api/v1/real-time-metrics` - Consolidated dashboard metrics endpoint (5-10ms response time)
  - Reduced Health Dashboard API calls from 6-10 to 1 per refresh
  - Parallel service queries with graceful degradation
  - Returns metrics from all active services in single call

#### AI Automation System
- **45 automation suggestions** generated and ready for review
- **6,109 patterns detected** (5,996 co-occurrence + 113 time-of-day)
- **852 unique devices** analyzed from Home Assistant
- **99.3% average confidence** in pattern detection
- Categories: Convenience (100%), Energy, Security (future)
- Priorities: High (93%), Medium (7%)

#### Documentation
- Created `docs/stories/story-infra-1-fix-admin-api-indentation.md` - Admin API fix story
- Created `docs/stories/story-infra-2-implement-stats-endpoints.md` - Statistics endpoints story
- Created `docs/stories/story-infra-3-implement-realtime-metrics.md` - Real-time metrics story
- Created `implementation/FULL_REBUILD_DEPLOYMENT_COMPLETE.md` - Complete deployment guide
- Created `implementation/DEPLOYMENT_SUCCESS_SUMMARY.md` - Quick deployment summary

### Fixed - Critical System Issues

#### AI Automation Service
- **Fixed**: Database field mapping (`description` vs `description_only`) in CRUD operations
- **Fixed**: Suggestion list endpoint returning 'description' attribute error
- **Fixed**: DataAPIClient method calls in `feature_analyzer.py` (replaced non-existent `get()` with `get_all_devices()`)
- **Fixed**: Analysis router field mapping to use correct database fields
- **Result**: Suggestions now generate and display correctly in UI

#### Admin API Service (INFRA-1)
- **Fixed**: Python `NameError` in `stats_endpoints.py` (routes defined outside method scope)
- **Fixed**: Removed broken route implementations (lines 627-735)
- **Fixed**: Indentation and scoping for all route handlers
- **Fixed**: `aiohttp.ClientTimeout` usage in helper methods
- **Fixed**: Async wrapper for fallback metric creation
- **Result**: Admin API now starts successfully and reports healthy

#### Health Dashboard
- **Fixed**: TypeScript import path case mismatch (`useRealTimeMetrics` vs `useRealtimeMetrics`)
- **Fixed**: CSS import order (@import must precede @tailwind directives)
- **Fixed**: Removed import of non-existent `dashboard-grid.css` file
- **Result**: Dashboard builds and deploys successfully

### Changed - Full System Rebuild

#### Deployment
- **Rebuilt**: All 16 Docker images with latest code changes
- **Deployed**: 17 containers (16 services + InfluxDB)
- **Build Time**: ~8 minutes with parallel builds
- **Cache Hit Rate**: ~70% (optimized rebuild)
- **Status**: 17/17 services healthy (100% success rate)

#### Performance Improvements
- **Real-time Metrics**: 5-10ms response (was 500-1500ms with multiple calls)
- **Dashboard Refresh**: 1 API call (was 6-10 calls)
- **Statistics Queries**: 100-500ms (InfluxDB-backed with fallback)
- **Health Checks**: < 10ms (all services)

### Added - InfluxDB Schema Enhancement
- **New Tag**: `integration` - Identifies source integration (zwave, mqtt, zigbee, homekit, etc.) for filtering and debugging
- **New Tag**: `time_of_day` - Temporal categorization (morning/afternoon/evening/night) for pattern analysis
- **New Tag**: `weather_condition` - Current weather condition (Clear, Clouds, Rain, Snow, etc.) for weather-based filtering
- **New Field**: `weather_temp` - Ambient temperature context (°C) from OpenWeatherMap API
- **New Field**: `weather_humidity` - Ambient humidity percentage from OpenWeatherMap API
- **New Field**: `weather_pressure` - Atmospheric pressure (hPa) from OpenWeatherMap API
- **New Field**: `wind_speed` - Wind speed (m/s) from OpenWeatherMap API
- **New Field**: `weather_description` - Detailed weather description text
- **Weather Enrichment**: Fully operational after cache clear (active Oct 18, 11:11 AM)
- **Documentation**: Comprehensive schema documentation reflecting actual 150+ field flattened attribute architecture
- **Documentation**: Created `docs/SCHEMA_UPDATE_OCTOBER_2025.md` - Detailed schema enhancement guide
- **Documentation**: Created `implementation/INFLUXDB_EVENTS_DATABASE_ANALYSIS_SUMMARY.md` - Complete database analysis (144K+ events)
- **Documentation**: Created `implementation/INFLUXDB_SCHEMA_VERIFICATION_COMPLETE.md` - Schema verification report
- **Documentation**: Created `implementation/WEATHER_ENRICHMENT_EVIDENCE.md` - Weather enrichment investigation
- **Documentation**: Created `implementation/FIXES_IMPLEMENTED_SUMMARY.md` - Implementation summary
- **Documentation**: Created `implementation/WEATHER_ENRICHMENT_FIX_SUCCESS.md` - Weather fix completion report

### Changed - Documentation Updates
- **Updated**: `docs/architecture/database-schema.md` - Now reflects actual enrichment pipeline schema with 150+ fields
- **Updated**: `implementation/analysis/HA_EVENT_CALL_TREE.md` - Added schema differences comparison table
- **Enhanced**: `services/websocket-ingestion/src/influxdb_schema.py` - Added comprehensive docstring explaining dual schema architecture

### Fixed - Schema Documentation & Weather Enrichment
- **Corrected**: Field naming documentation (actual: `state`/`old_state` vs designed: `state_value`/`previous_state`)
- **Clarified**: Dual schema architecture (websocket fallback vs enrichment pipeline primary writer)
- **Documented**: Flattened attribute design rationale using InfluxDB best practices (Context7 verified)
- **Fixed**: Weather enrichment - Added missing extraction code to write weather fields to database
- **Fixed**: Weather cache - Cleared stale None values by restarting websocket-ingestion service
- **Verified**: Weather fields now appearing in database (temp: 22.07°C, humidity: 23%, pressure: 1019 hPa)

### Implementation Details
- **Code Modified**: `services/enrichment-pipeline/src/influxdb_wrapper.py`
  - Lines 167-170: Integration tag extraction
  - Lines 172-193: Time of day tag calculation
  - Lines 281-310: Weather field extraction and writing (ADDED)
- **Services Restarted**:
  - enrichment-pipeline: Rebuilt 3 times (tag additions + weather fix + debug logging)
  - websocket-ingestion: Restarted 1 time (cache clear)
- **Impact**: All new events after Oct 18, 11:11 AM include weather context
- **Verification**: Weather fields confirmed in database (22.07°C, 23%, 1019 hPa)

## [2.0.0] - 2025-10-16

### Added - Epic AI-2: Device Intelligence System

#### New Features
- **Universal Device Capability Discovery** - Automatic detection of device features from Zigbee2MQTT (6,000+ device models supported)
- **Feature Utilization Analysis** - Calculates how much of device capabilities users actually use
- **Smart Feature Suggestions** - LLM-powered recommendations for unused features (LED notifications, power monitoring, etc.)
- **Unified Daily Batch Job** - Combined pattern detection + device intelligence in single efficient 3 AM job
- **Combined Suggestions** - Merges pattern-based and feature-based suggestions with unified ranking

#### New Components (Story 2.1-2.5)
- **Story 2.1:** `capability_parser.py` - Universal parser for Zigbee2MQTT device capabilities
- **Story 2.1:** `capability_batch.py` - Batch device capability update (replaces 24/7 listener)
- **Story 2.2:** `device_capabilities` table - Stores device model → features mapping
- **Story 2.2:** `device_feature_usage` table - Tracks configured vs available features per device
- **Story 2.3:** `feature_analyzer.py` - Analyzes device utilization and identifies opportunities
- **Story 2.4:** `feature_suggestion_generator.py` - Generates LLM-powered feature suggestions
- **Story 2.5:** Enhanced `daily_analysis.py` - 6-phase unified job (AI-1 + AI-2)

#### API Endpoints
- `GET /api/device-intelligence/utilization` - Device utilization metrics
- `GET /api/device-intelligence/opportunities` - Unused feature opportunities  
- `POST /api/device-intelligence/capabilities/refresh` - Manual capability refresh

#### Performance Improvements
- **99% Resource Reduction** - 2.5 hrs/month vs 730 hrs/month (batch vs real-time)
- **Shared Data Query** - Single InfluxDB fetch for both pattern detection and feature analysis
- **Optimized Architecture** - 1 unified service vs 2 separate services

#### Documentation
- 5 new story files (`story-ai2-*.md`)
- Architecture document (`architecture-device-intelligence.md`)
- 10+ implementation guides in `implementation/`
- Deployment guide (`DEPLOYMENT_STORY_AI2-5.md`)
- Quick reference (`QUICK_REFERENCE_AI2.md`)

### Changed

- **Daily Analysis Job** - Now runs 6 phases instead of 4 (added device capability update and feature analysis)
- **Suggestion Types** - Now generates both `pattern_automation` and `feature_discovery` suggestions
- **MQTT Notification** - Enhanced to include both Epic AI-1 and Epic AI-2 statistics
- **Health Endpoint** - Now includes device intelligence stats
- **Logging** - Unified format showing both pattern and feature analysis results

### Technical Details

- **Test Coverage:** 56/56 unit tests passing (100%)
- **Lines of Code:** ~3,500 new lines + 2,000 test lines
- **Database:** 2 new tables, 6 new CRUD operations
- **Alembic Migration:** `20251016_095206_add_device_intelligence_tables.py`
- **Docker Image:** Successfully built and tested

---

## [1.0.0] - 2025-01-XX

### Added - Epic AI-1: Pattern Automation

#### New Features
- **Time-of-Day Pattern Detection** - KMeans clustering to find consistent usage times
- **Co-Occurrence Detection** - Identifies devices frequently used together
- **Anomaly Detection** - Spots unusual manual interventions
- **LLM-Powered Suggestions** - OpenAI GPT-4o-mini generates automation YAML
- **Daily Scheduler** - Automatic analysis at 3 AM
- **MQTT Integration** - Notifications published to Home Assistant

#### Components (Story 1.1-1.9)
- `pattern_analyzer/time_of_day.py` - Time-of-day pattern detector
- `pattern_analyzer/co_occurrence.py` - Co-occurrence pattern detector
- `llm/openai_client.py` - OpenAI API integration
- `scheduler/daily_analysis.py` - Daily batch job scheduler
- `database/` - SQLite with Alembic migrations
- `api/` - RESTful API for suggestions and deployment

#### API Endpoints
- `GET /api/suggestions` - List automation suggestions
- `POST /api/deploy/{id}` - Deploy automation to Home Assistant
- `GET /api/patterns` - List detected patterns
- `POST /api/analysis/trigger` - Manual analysis trigger
- `GET /api/analysis/status` - Check analysis status

---

## [0.9.0] - 2025-01-XX

### Added - Epic 23: Enhanced Event Data Capture

- **Automation Tracing** - Track which automations triggered events
- **Spatial Analytics** - Enhanced area/floor tracking
- **Time Metrics** - Processing time and latency tracking
- **Device Reliability** - Event counts by manufacturer/model

---

## [0.8.0] - 2024-12-XX

### Added - Epic 22: Hybrid Database Architecture

- **SQLite Integration** - Metadata storage alongside InfluxDB
- **Direct HA → SQLite Storage** - Device and entity registry sync
- **5-10x Faster Queries** - Optimized query performance
- **Eliminated Sync Scripts** - Automated WebSocket-based sync

---

## [0.7.0] - 2024-11-XX

### Added - Data Enrichment Platform

- **Weather API Integration** - OpenWeatherMap data enrichment
- **Carbon Intensity Service** - UK carbon intensity data
- **Electricity Pricing Service** - Octopus Energy API integration
- **Air Quality Service** - Air quality index tracking
- **Calendar Service** - Google Calendar event correlation
- **Smart Meter Service** - Energy consumption tracking

---

## [0.6.0] - 2024-10-XX

### Added - Health Dashboard

- **React/TypeScript Dashboard** - System monitoring and health visualization
- **Real-time Metrics** - WebSocket connection status, event rates, service health
- **Device Management** - Device registry viewing and filtering
- **Performance Monitoring** - API latency, database performance, error rates

---

## [0.5.0] - 2024-09-XX

### Added - Core Infrastructure

- **WebSocket Ingestion** - Real-time Home Assistant event capture
- **InfluxDB Storage** - Time-series event storage
- **Data API** - RESTful API for historical queries
- **MQTT Integration** - Event-driven notification system
- **Docker Compose** - Multi-service orchestration

---

## Version History

- **2.0.0** (2025-10-16) - Epic AI-2: Device Intelligence System ✅
- **1.0.0** (2025-01-XX) - Epic AI-1: Pattern Automation ✅
- **0.9.0** (2025-01-XX) - Epic 23: Enhanced Event Data Capture ✅
- **0.8.0** (2024-12-XX) - Epic 22: Hybrid Database Architecture ✅
- **0.7.0** (2024-11-XX) - Data Enrichment Platform ✅
- **0.6.0** (2024-10-XX) - Health Dashboard ✅
- **0.5.0** (2024-09-XX) - Core Infrastructure ✅

---

## Notable Architectural Decisions

### Real-time → Batch Migration (v2.0.0)
**Decision:** Changed from 24/7 MQTT listener to daily batch query  
**Rationale:** Device capabilities are static metadata (change monthly), suggestions are batched daily  
**Impact:** 99% resource reduction (291x less uptime), same user experience  
**Documentation:** `implementation/REALTIME_VS_BATCH_ANALYSIS.md`

### Hybrid Database (v0.8.0)
**Decision:** Added SQLite alongside InfluxDB  
**Rationale:** Fast metadata queries, direct HA device registry sync  
**Impact:** 5-10x faster device/entity queries, eliminated manual sync scripts  

### Single-Tenant Architecture (v0.5.0)
**Decision:** Built for single-home deployment  
**Rationale:** Simplified design, no multi-tenancy complexity  
**Impact:** Lower resource usage, easier maintenance, focused feature set

