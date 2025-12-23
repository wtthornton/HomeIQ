# AI Pattern Service

**Pattern detection, synergy analysis, and community patterns service for HomeIQ**

**Port:** 8020 (internal), exposed as 8034 (external)
**Technology:** Python 3.11+, FastAPI, SQLAlchemy
**Container:** homeiq-ai-pattern-service
**Database:** SQLite (ai_automation.db)
**Scale:** Optimized for ~50-100 devices (single-home)

## Overview

The AI Pattern Service is a microservice extracted from ai-automation-service (Epic 39, Story 39.5) for independent scaling and maintainability. It handles pattern detection, synergy analysis, and community pattern mining operations that run on a scheduled basis.

**Port Mapping Note:** This service runs on port 8020 internally within the Docker network, but is exposed as port 8034 externally for host access. When making requests from outside Docker, use port 8034. Internal services should use port 8020.

### Key Features

- **Scheduled Pattern Analysis** - Automated pattern detection running on configurable cron schedule (default: 3 AM daily)
- **Time-of-Day Pattern Detection** - Identifies recurring automation patterns based on time
- **Co-occurrence Pattern Detection** - Discovers devices that are frequently used together
- **Synergy Detection** - Multi-hop device relationship discovery with confidence scoring
- **Community Pattern Mining** - Integration with automation-miner service for community insights
- **MQTT Notifications** - Optional notifications for pattern detection events
- **Incremental Updates** - Enable/disable incremental pattern analysis
- **Observability** - OpenTelemetry tracing, correlation middleware, structured logging

### 2025 Enhancements (Epic 39, Story 39.8)

- **Multi-Modal Context Integration** - Enhances synergy scores with external context (weather, energy, time)
- **Explainable AI (XAI)** - Generates human-readable explanations for synergy recommendations
- **Reinforcement Learning (RL) Feedback Loop** - Optimizes synergy scores based on user feedback using Thompson Sampling
- **Transformer-Based Sequence Modeling** - Optional transformer models for sequence predictions (framework ready)
- **Graph Neural Network (GNN) Integration** - Optional GNN models for advanced relationship learning (framework ready)
- **Enhanced API Endpoints** - Synergy router with XAI explanations and RL feedback endpoints
- **Community Pattern Router** - API endpoints for community pattern sharing and discovery

## API Endpoints

### Health Endpoints

```bash
GET /health
```
Health check with database connectivity verification.

**Response:**
```json
{
  "status": "ok",
  "database": "connected"
}
```

```bash
GET /ready
```
Kubernetes readiness probe endpoint.

**Response:**
```json
{
  "status": "ready"
}
```

```bash
GET /live
```
Kubernetes liveness probe endpoint.

**Response:**
```json
{
  "status": "live"
}
```

### Service Info

```bash
GET /
```
Root endpoint with service information.

**Response:**
```json
{
  "service": "ai-pattern-service",
  "version": "1.0.0",
  "status": "operational"
}
```

### Pattern Endpoints

```bash
GET /api/v1/patterns/list
```
List detected patterns with optional filters (pattern_type, device_id, min_confidence, limit).

### Synergy Endpoints (2025 Enhanced)

```bash
GET /api/v1/synergies/list
```
List synergy opportunities with enhanced features:
- **Filters**: synergy_type, min_confidence, synergy_depth, limit
- **Ordering**: By priority score (impact + confidence)
- **Enhanced Response**: Includes `explanation` (XAI) and `context_breakdown` (multi-modal context)

**Response:**
```json
{
  "success": true,
  "data": {
    "synergies": [
      {
        "id": 1,
        "synergy_id": "device_pair_abc123",
        "synergy_type": "device_pair",
        "devices": ["light.living_room", "switch.kitchen"],
        "impact_score": 0.85,
        "confidence": 0.92,
        "complexity": "medium",
        "area": "Living Room",
        "explanation": {
          "summary": "These devices work well together because...",
          "reasoning": ["Reason 1", "Reason 2"],
          "confidence_factors": ["High co-occurrence", "Similar time patterns"]
        },
        "context_breakdown": {
          "weather_impact": 0.1,
          "energy_impact": 0.05,
          "time_impact": 0.15
        }
      }
    ],
    "count": 1
  }
}
```

```bash
GET /api/v1/synergies/{synergy_id}
```
Get detailed synergy opportunity by ID with full explanation and context breakdown.

```bash
GET /api/v1/synergies/stats
```
Get synergy statistics (total count, types, depths, average scores).

```bash
POST /api/v1/synergies/{synergy_id}/feedback
```
Submit user feedback for RL optimization.

**Request Body:**
```json
{
  "accepted": true,
  "feedback_text": "This synergy worked perfectly!",
  "rating": 5
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "synergy_id": "device_pair_abc123",
    "feedback_received": true,
    "accepted": true,
    "rating": 5,
    "rl_updated": true
  }
}
```

### Community Pattern Endpoints (2025 New)

```bash
GET /api/v1/community/patterns/list
```
List community patterns with filters (pattern_type, min_rating, tags, limit, order_by).

```bash
POST /api/v1/community/patterns/submit
```
Submit a pattern to the community.

**Request Body:**
```json
{
  "pattern_type": "time_of_day",
  "device_id": "light.living_room",
  "pattern_metadata": {...},
  "description": "Lights turn on automatically at sunset",
  "tags": ["automation", "lighting", "schedule"],
  "author": "John Doe"
}
```

```bash
GET /api/v1/community/patterns/{pattern_id}
```
Get detailed community pattern by ID.

```bash
POST /api/v1/community/patterns/{pattern_id}/rate
```
Rate a community pattern (1-5 stars with optional comment).

```bash
GET /api/v1/community/patterns/{pattern_id}/ratings
```
Get ratings and comments for a community pattern.

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_PATH` | `/app/data/ai_automation.db` | Path to SQLite database file |
| `DATABASE_URL` | `sqlite+aiosqlite:////app/data/ai_automation.db` | SQLAlchemy database URL |
| `DATABASE_POOL_SIZE` | `10` | Database connection pool size (max 20 per service) |
| `DATABASE_MAX_OVERFLOW` | `5` | Max overflow connections |
| `DATA_API_URL` | `http://data-api:8006` | Data API service URL |
| `SERVICE_PORT` | `8020` | Internal service port |
| `SERVICE_NAME` | `ai-pattern-service` | Service name for logging/tracing |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:3001` | Allowed CORS origins |

#### Pattern Detection Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `SYNERGY_MIN_CONFIDENCE` | `0.5` | Minimum confidence score for synergy detection |
| `SYNERGY_MIN_IMPACT_SCORE` | `0.3` | Minimum impact score for synergy detection |
| `TIME_OF_DAY_OCCURRENCE_OVERRIDES` | `{}` | Override occurrence thresholds (JSON dict) |
| `TIME_OF_DAY_CONFIDENCE_OVERRIDES` | `{}` | Override confidence thresholds (JSON dict) |
| `CO_OCCURRENCE_SUPPORT_OVERRIDES` | `{}` | Override support thresholds (JSON dict) |
| `CO_OCCURRENCE_CONFIDENCE_OVERRIDES` | `{}` | Override confidence thresholds (JSON dict) |

#### Scheduler Configuration (Story 39.6)

| Variable | Default | Description |
|----------|---------|-------------|
| `ANALYSIS_SCHEDULE` | `0 3 * * *` | Cron schedule for pattern analysis (default: 3 AM daily) |
| `ENABLE_INCREMENTAL` | `True` | Enable incremental pattern updates |

#### MQTT Configuration (Story 39.6)

| Variable | Default | Description |
|----------|---------|-------------|
| `MQTT_BROKER` | `None` | MQTT broker hostname (e.g., `192.168.1.86`) |
| `MQTT_PORT` | `1883` | MQTT broker port |
| `MQTT_USERNAME` | `None` | MQTT username (optional) |
| `MQTT_PASSWORD` | `None` | MQTT password (optional) |

## Development

### Running Locally

```bash
cd services/ai-pattern-service
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8020
```

### Running with Docker

```bash
# Build and start service
docker compose up -d ai-pattern-service

# View logs
docker compose logs -f ai-pattern-service

# Test health endpoint (external port)
curl http://localhost:8034/health

# Test from inside Docker network (internal port)
docker exec homeiq-ai-automation-ui curl http://ai-pattern-service:8020/health
```

### Testing Endpoints

```bash
# Health check
curl http://localhost:8034/health

# Readiness check
curl http://localhost:8034/ready

# Liveness check
curl http://localhost:8034/live

# Service info
curl http://localhost:8034/
```

## Dependencies

### Service Dependencies

- **data-api** (Port 8006) - Historical data queries, device/entity metadata
- **SQLite Database** - Shared ai_automation.db for pattern storage
- **MQTT Broker** (Optional) - Pattern detection notifications (typically Home Assistant's MQTT at 192.168.1.86:1883)

### Python Dependencies

**Core Dependencies:**
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `sqlalchemy` - Database ORM
- `aiosqlite` - Async SQLite driver
- `pydantic` - Configuration management
- `pydantic-settings` - Environment variable loading
- `shared` - HomeIQ shared libraries (logging, observability, error handling)

**2025 Enhancement Dependencies (Optional):**
- `numpy` - Required for RL optimizer (Thompson Sampling)
- `torch` - Required for transformer and GNN models (optional, framework ready)
- `torch-geometric` - Required for GNN models (optional, framework ready)
- `transformers` - Required for transformer models (optional, framework ready)

**Note:** The service works without optional dependencies. Multi-modal context, XAI, and RL feedback loop work with core dependencies. Transformer and GNN features are framework-ready but require additional dependencies for full functionality.

## Related Services

### Upstream Dependencies

- **data-api** - Provides historical event data for pattern analysis
- **automation-miner** - Community pattern corpus (optional)

### Downstream Consumers

- **ai-automation-service** - Uses detected patterns for automation generation
- **ai-automation-ui** - Displays pattern insights to users
- **health-dashboard** - Monitors pattern service health

## Architecture Notes

### Separation from AI Automation Service

This service was extracted from ai-automation-service in Epic 39, Story 39.5 to:
- Enable independent scaling of pattern detection workloads
- Isolate long-running batch operations from real-time query handling
- Improve maintainability and deployment flexibility
- Support nightly analysis without impacting interactive performance

### Scheduled Analysis

The service runs pattern analysis on a configurable cron schedule (default: 3 AM daily):
1. **Pattern Detection** - Time-of-day and co-occurrence patterns
2. **Synergy Analysis** - Multi-hop device relationships with 2025 enhancements:
   - Multi-modal context integration (weather, energy, time)
   - Explainable AI explanations
   - RL-optimized scoring based on user feedback
   - Optional transformer/GNN models for advanced detection
3. **Community Patterns** - Integration with automation-miner
4. **MQTT Notifications** - Optional alerts for new patterns

### 2025 Synergy Detection Pipeline

The enhanced synergy detection pipeline includes:

1. **Base Detection** - Traditional multi-hop relationship discovery
2. **Context Enhancement** - Multi-modal context integration:
   - Weather data impact
   - Energy consumption patterns
   - Time-of-day context
   - Device metadata (area, manufacturer, model)
3. **Explainable AI** - Human-readable explanations:
   - Summary of why devices work well together
   - Reasoning factors
   - Confidence breakdown
4. **RL Optimization** - Reinforcement learning feedback loop:
   - Thompson Sampling for exploration/exploitation
   - User feedback integration
   - Score optimization over time
5. **Advanced Models (Optional)**:
   - Transformer-based sequence modeling
   - Graph Neural Network (GNN) relationship learning

### Database Sharing

This service shares the `ai_automation.db` SQLite database with ai-automation-service:
- **Pattern Storage** - Detected patterns, synergy relationships
- **Community Patterns** - Mined automation patterns
- **Configuration** - Pattern detection thresholds and overrides

### 2025 Database Schema Updates

The following fields and tables were added for 2025 enhancements:

**Synergy Opportunities Table (`synergy_opportunities`):**
- `explanation` (JSON) - XAI-generated explanations
- `context_breakdown` (JSON) - Multi-modal context impact breakdown
- `rl_feedback` (JSON) - RL optimizer state (optional)

**Synergy Feedback Table (`synergy_feedback`):**
- `synergy_id` - Reference to synergy opportunity
- `accepted` - Boolean feedback (accepted/rejected)
- `feedback_text` - Optional text feedback
- `rating` - Optional 1-5 rating
- `created_at` - Timestamp

**Migration:** Run `python scripts/add_2025_synergy_fields.py` to add new columns and tables.

## Monitoring

### Health Checks

- **Liveness:** `GET /live` - Service is running
- **Readiness:** `GET /ready` - Service is ready to accept traffic
- **Health:** `GET /health` - Database connectivity verified

### Logging

All logs follow structured logging format with correlation IDs:
```json
{
  "timestamp": "2025-12-09T10:30:00Z",
  "level": "INFO",
  "service": "ai-pattern-service",
  "correlation_id": "abc-123",
  "message": "Pattern analysis completed",
  "duration_ms": 1234
}
```

### Observability

- **OpenTelemetry Tracing** - Distributed tracing across services
- **Correlation IDs** - Request tracking across service boundaries
- **Metrics** - Service health, database performance, pattern detection stats

## Version History

- **v1.1.0** (January 2025) - 2025 Synergy Improvements (Epic 39, Story 39.8)
  - Multi-modal context integration for enhanced synergy scoring
  - Explainable AI (XAI) for human-readable explanations
  - Reinforcement Learning feedback loop with Thompson Sampling
  - Transformer-based sequence modeling (optional, framework ready)
  - Graph Neural Network (GNN) integration (optional, framework ready)
  - Enhanced synergy API endpoints with explanations and context breakdown
  - Community pattern router for pattern sharing
  - Database schema updates (explanation, context_breakdown, synergy_feedback table)
  - Comprehensive integration tests

- **v1.0.0** (December 2025) - Initial service extraction from ai-automation-service (Epic 39, Story 39.5)
  - Scheduled pattern analysis with cron support
  - MQTT notification integration
  - Incremental pattern updates
  - Observability and structured logging

---

**Last Updated:** January 2025
**Version:** 1.1.0
**Status:** Production Ready ✅
**Port:** 8020 (internal) / 8034 (external)
