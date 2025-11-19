# AI Automation Service

AI-powered Home Assistant automation discovery and recommendation system with device intelligence.

**Port:** 8018 (internal), exposed as 8024 (external)
**Technology:** Python 3.11+, FastAPI 0.121, OpenAI GPT-4o-mini, OpenVINO
**Container:** `homeiq-ai-automation-service`
**Database:** SQLite (ai_automation.db - 13 tables)

## Recent Updates (November 2025)

### ✅ Import Errors Fixed (November 19, 2025)
**Status**: ✅ **DEPLOYED** - Service validation now working correctly

**What Changed**:
- Fixed 3 relative import errors in `service_validator.py`
- Changed `from ...clients` to `from ..clients`
- Service validation now works reliably

**Impact**:
- No more "attempted relative import beyond top-level package" errors
- Entity service capabilities properly validated
- Improved automation generation reliability

---

## Overview

**Epic AI-1: Pattern Automation** - Analyzes historical usage to detect patterns and suggest automations
**Epic AI-2: Device Intelligence** - Discovers device capabilities and suggests unused features
**Epic AI-3: N-Level Synergy Detection** - Multi-hop device relationship discovery
**Epic AI-4: Advanced Synergy Analysis** - Device embedding generation and similarity matching

### Features

**Pattern Detection (Epic AI-1):**
- 🔍 Time-of-day patterns (consistent usage times)
- 🔗 Device co-occurrence (frequently used together)
- ⚠️ Anomaly detection (repeated manual interventions)
- 💡 AI-generated automation suggestions

**Device Intelligence (Epic AI-2):**
- 📡 Universal device capability discovery (6,000+ Zigbee models)
- 📊 Utilization analysis (how much of device features you use)
- 💎 Feature suggestions (LED notifications, power monitoring, etc.)
- 🎯 Smart recommendations based on manufacturer specs

**N-Level Synergy Detection (Epic AI-3):**
- 🔗 Multi-hop device relationship discovery
- 🧠 Device embedding generation for similarity matching
- 📈 Advanced synergy pattern detection
- 🎯 Smart device pairing recommendations

**Conversational Automation System (Story AI1.23-24):**
- 🤖 Unified daily batch job (3 AM)
- 💡 8-10 suggestions per day (mixed pattern + feature)
- 💬 **Description-first flow** - See automation ideas in plain language
- ✏️ **Conversational refinement** - Say "make it 6:30am instead" to edit
- ✅ **Approve to generate YAML** - Code only created after you approve
- 🚀 One-click deploy to Home Assistant

**Natural Language Generation (Story AI1.21):**
- 🗣️ Create automations from plain English
- 🔍 Entity extraction from Home Assistant
- 🛡️ Safety validation (6-rule engine)
- 📝 YAML generation with OpenAI GPT-4o-mini

**Ask AI Interface:**
- ❓ Natural language queries about devices and automations
- 🔍 Entity discovery and capability analysis
- 💡 Intelligent suggestion generation
- 🎯 Context-aware recommendations
- 🎨 **Enhanced Entity Resolution** - Multi-signal matching with fuzzy search, blocking, and user aliases
- 🧠 **Semantic Understanding (RAG)** - Self-improving clarification system that learns from successful queries
- 🔄 **Persistent Clarification Sessions** - Database-backed clarification flow with query ID linkage (AI1.26)
- 🏠 **Area Filtering** - Automatically filters devices by area when specified in queries (e.g., "In the office, flash all lights")
- 📍 **Multi-Area Support** - Handles queries specifying multiple areas with proper device filtering

**LangChain Integration (Feature Flags):**
- 🔧 `USE_LANGCHAIN_ASK_AI` - Enable LangChain for Ask AI prompts
- 🔧 `USE_LANGCHAIN_PATTERNS` - Enable LangChain for pattern detection
- 📝 LCEL chain-based prompt orchestration

**PDL Workflows:**
- 📋 YAML-based procedure orchestration
- 🌙 Nightly analysis coordination
- 🛡️ Synergy guardrails (when enabled)

## Quick Start

### Prerequisites

- Python 3.11+
- Home Assistant with MQTT integration
- OpenAI API key
- Data API service running (port 8006)
- Device Intelligence Service (port 8028)
- OpenVINO Service (port 8019) - For embeddings and semantic understanding
- InfluxDB 2.x (365-day retention)

### Configuration

1. Configure credentials in `infrastructure/env.ai-automation`
2. See `docs/stories/MQTT_SETUP_GUIDE.md` for MQTT setup details
3. Set OpenAI API key: `OPENAI_API_KEY`
4. Configure Data API URL: `DATA_API_URL=http://data-api:8006`
5. Configure Device Intelligence URL: `DEVICE_INTELLIGENCE_URL=http://device-intelligence-service:8028`

### Environment Variables

```bash
# Service Configuration
PORT=8018                                    # Internal port
HOST=0.0.0.0

# External Services
DATA_API_URL=http://data-api:8006
DEVICE_INTELLIGENCE_URL=http://device-intelligence-service:8028

# Home Assistant (Standard)
HOME_ASSISTANT_URL=http://homeassistant:8123
HOME_ASSISTANT_TOKEN=your-ha-long-lived-access-token

# Nabu Casa Cloud Fallback (Optional)
NABU_CASA_URL=https://your-instance.ui.nabu.casa
NABU_CASA_TOKEN=your-nabu-casa-token

# MQTT Configuration
MQTT_BROKER=192.168.1.86
MQTT_PORT=1883
MQTT_USERNAME=your-mqtt-username
MQTT_PASSWORD=your-mqtt-password

# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4o-mini

# Authentication
ENABLE_AUTHENTICATION=true
AI_AUTOMATION_API_KEY=generate-a-random-user-key
AI_AUTOMATION_ADMIN_API_KEY=generate-a-separate-admin-key

# Analysis Schedule
ANALYSIS_SCHEDULE=0 3 * * *                  # 3 AM daily (cron format)

# Feature Flags
USE_LANGCHAIN_ASK_AI=false                   # Enable LangChain for Ask AI
USE_LANGCHAIN_PATTERNS=false                 # Enable LangChain for patterns

# Database
DATABASE_URL=sqlite+aiosqlite:///./data/ai_automation.db

# OpenVINO Service (for RAG embeddings)
OPENVINO_SERVICE_URL=http://openvino-service:8019

# Logging
LOG_LEVEL=INFO
```

### Running Locally

```bash
cd services/ai-automation-service

# Install dependencies
pip install -r requirements.txt

# Download spaCy model (for NER fallback)
python -m spacy download en_core_web_sm

# Run database migrations
alembic upgrade head

# Seed RAG knowledge base (optional, but recommended)
python scripts/seed_rag_knowledge_base.py

# Start service
python -m uvicorn src.main:app --host 0.0.0.0 --port 8018 --reload
```

### Running with Docker

```bash
# From project root
docker compose up -d ai-automation-service

# View logs
docker compose logs -f ai-automation-service

# Check health
curl http://localhost:8024/health
```

## API Endpoints

> 🔐 All endpoints (except `/health`, `/docs`, and `/redoc`) require the `X-HomeIQ-API-Key` header. Use the admin key for deployment, admin, and suggestion-management routes.

### Health & System

#### `GET /health`
Service health check with device intelligence statistics
```bash
curl http://localhost:8024/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-15T12:00:00Z",
  "service": "ai-automation-service",
  "uptime_seconds": 3600,
  "device_intelligence": {
    "devices_tracked": 45,
    "capabilities_discovered": 234,
    "last_update": "2025-11-15T03:00:00Z"
  }
}
```

#### `GET /event-rate`
Standardized event rate metrics
```bash
curl http://localhost:8024/event-rate
```

### Analysis & Pattern Detection

#### `GET /api/analysis/status`
Current analysis status and pattern statistics
```bash
curl http://localhost:8024/api/analysis/status
```

#### `POST /api/analysis/analyze-and-suggest`
Run complete analysis pipeline manually
```bash
curl -X POST http://localhost:8024/api/analysis/analyze-and-suggest
```

#### `POST /api/analysis/trigger`
Manually trigger daily analysis job (3 AM job)
```bash
curl -X POST http://localhost:8024/api/analysis/trigger
```

#### `GET /api/analysis/schedule`
Get analysis schedule information
```bash
curl http://localhost:8024/api/analysis/schedule
```

### Pattern Detection (Epic AI-1)

#### `POST /api/patterns/detect/time-of-day`
Detect time-of-day patterns from historical data
```bash
curl -X POST http://localhost:8024/api/patterns/detect/time-of-day \
  -H "Content-Type: application/json" \
  -d '{"days_lookback": 30}'
```

#### `POST /api/patterns/detect/co-occurrence`
Detect device co-occurrence patterns
```bash
curl -X POST http://localhost:8024/api/patterns/detect/co-occurrence \
  -H "Content-Type: application/json" \
  -d '{"days_lookback": 30, "min_co_occurrences": 3}'
```

#### `GET /api/patterns/list`
List detected patterns with filtering
```bash
curl "http://localhost:8024/api/patterns/list?pattern_type=time_of_day&min_confidence=0.7"
```

Query parameters:
- `pattern_type`: `time_of_day`, `co_occurrence`, `anomaly`
- `min_confidence`: Minimum confidence score (0.0-1.0)
- `entity_id`: Filter by specific entity

#### `GET /api/patterns/stats`
Get pattern detection statistics
```bash
curl http://localhost:8024/api/patterns/stats
```

### Suggestion Management

#### `POST /api/suggestions/generate`
Generate automation suggestions from detected patterns
```bash
curl -X POST http://localhost:8024/api/suggestions/generate
```

#### `GET /api/suggestions/list`
List suggestions with status filtering
```bash
curl "http://localhost:8024/api/suggestions/list?status=draft&limit=10"
```

Query parameters:
- `status`: `draft`, `approved`, `rejected`, `deployed`
- `suggestion_type`: `pattern`, `feature`, `synergy`
- `limit`: Maximum number of results

#### `GET /api/suggestions/usage-stats`
Get OpenAI API usage statistics
```bash
curl http://localhost:8024/api/suggestions/usage-stats
```

#### `POST /api/suggestions/usage-stats/reset`
Reset usage statistics
```bash
curl -X POST http://localhost:8024/api/suggestions/usage-stats/reset
```

### Conversational Automation Flow (Story AI1.23-24)

#### `POST /api/v1/suggestions/generate`
Generate description-only suggestion (no YAML yet)
```bash
curl -X POST http://localhost:8024/api/v1/suggestions/generate \
  -H "Content-Type: application/json" \
  -d '{
    "pattern_id": "abc123",
    "description": "Turn on office light when motion detected"
  }'
```

#### `POST /api/v1/suggestions/{id}/refine`
Refine suggestion with natural language
```bash
curl -X POST http://localhost:8024/api/v1/suggestions/abc123/refine \
  -H "Content-Type: application/json" \
  -d '{
    "refinement": "make it 6:30am instead of 7:00am"
  }'
```

#### `POST /api/v1/suggestions/{id}/approve`
Approve and generate YAML
```bash
curl -X POST http://localhost:8024/api/v1/suggestions/abc123/approve
```

#### `GET /api/v1/suggestions/devices/{device_id}/capabilities`
Get device capabilities for suggestion refinement
```bash
curl http://localhost:8024/api/v1/suggestions/devices/light.office/capabilities
```

#### `GET /api/v1/suggestions/{id}`
Get detailed suggestion information
```bash
curl http://localhost:8024/api/v1/suggestions/abc123
```

### Natural Language Generation (Story AI1.21)

#### `POST /api/nl/generate`
Generate automation from natural language
```bash
curl -X POST http://localhost:8024/api/nl/generate \
  -H "Content-Type: application/json" \
  -d '{
    "request": "Turn on office light when I arrive home after sunset"
  }'
```

#### `POST /api/nl/clarify/{id}`
Clarify automation request
```bash
curl -X POST http://localhost:8024/api/nl/clarify/abc123 \
  -H "Content-Type: application/json" \
  -d '{
    "clarification": "Use the front door sensor, not the garage"
  }'
```

#### `GET /api/nl/examples`
Get example natural language requests
```bash
curl http://localhost:8024/api/nl/examples
```

#### `GET /api/nl/stats`
Get NL generation statistics
```bash
curl http://localhost:8024/api/nl/stats
```

### Ask AI - Natural Language Query Interface

#### `POST /api/v1/ask-ai/query`
Process natural language query about devices and automations
```bash
curl -X POST http://localhost:8024/api/v1/ask-ai/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What can I do with my bedroom lights?"
  }'
```

Response (No Clarification):
```json
{
  "query_id": "query-abc123",
  "clarification_needed": false,
  "suggestions": [...]
}
```

Response (Clarification Needed):
```json
{
  "query_id": "query-abc123",
  "clarification_needed": true,
  "clarification_session_id": "clarify-def456",
  "questions": [{"id": "q1", "question_text": "..."}]
}
```

#### `POST /api/v1/ask-ai/clarify`
Provide answers to clarification questions
```bash
curl -X POST http://localhost:8024/api/v1/ask-ai/clarify \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "clarify-def456",
    "answers": [{
      "question_id": "q1",
      "answer_text": "bedroom ceiling",
      "selected_entities": ["light.bedroom_ceiling"]
    }]
  }'
```

#### `POST /api/v1/ask-ai/query/{id}/refine`
Refine query results
```bash
curl -X POST http://localhost:8024/api/v1/ask-ai/query/abc123/refine \
  -H "Content-Type: application/json" \
  -d '{
    "refinement": "Show me energy-saving options"
  }'
```

#### `GET /api/v1/ask-ai/query/{id}/suggestions`
Get automation suggestions from query (supports both direct and clarification query IDs)
```bash
curl http://localhost:8024/api/v1/ask-ai/query/abc123/suggestions?include_clarifications=true
```

Response (Direct Query):
```json
{
  "query_id": "query-abc123",
  "suggestions": [...],
  "source": "direct"
}
```

Response (From Clarification):
```json
{
  "query_id": "query-abc123",
  "original_query_id": "query-abc123",
  "clarification_session_id": "clarify-def456",
  "clarification_query_id": "clarify-def456",
  "suggestions": [...],
  "source": "clarification"
}
```

#### `POST /api/v1/ask-ai/query/{id}/suggestions/{suggestion_id}/test`
Test a suggestion from query
```bash
curl -X POST http://localhost:8024/api/v1/ask-ai/query/abc123/suggestions/456/test
```

#### `POST /api/v1/ask-ai/query/{id}/suggestions/{suggestion_id}/approve`
Approve and deploy suggestion
```bash
curl -X POST http://localhost:8024/api/v1/ask-ai/query/abc123/suggestions/456/approve
```

### Semantic Understanding (RAG System)

The RAG (Retrieval-Augmented Generation) system provides semantic understanding for the clarification system, reducing false positive clarification questions by learning from successful queries.

#### Features

- **Semantic Similarity Search:** Uses embeddings to find similar successful queries
- **Self-Improving:** Learns from user interactions and successful automations
- **Knowledge Base:** Stores queries, patterns, and automations with semantic embeddings
- **Reduced False Positives:** Skips clarification for queries similar to successful ones

#### Seeding Knowledge Base

Populate the knowledge base with initial data:

```bash
cd services/ai-automation-service
python scripts/seed_rag_knowledge_base.py
```

This extracts:
- Successful queries (confidence >= 0.85) from `AskAIQuery` table
- Common patterns from `common_patterns.py`
- Deployed automations from `Suggestion` table

#### How It Works

1. **Query Processing:** When a user query comes in, the system checks for similar successful queries
2. **Semantic Matching:** Uses cosine similarity on embeddings (threshold: 0.85)
3. **Smart Clarification:** If similar query found, skips clarification (query is clear)
4. **Fallback:** If no similar query found, uses hardcoded rules as fallback
5. **Learning:** Successful queries are automatically stored for future reference

#### Configuration

The RAG system uses:
- **OpenVINO Service:** For embedding generation (384-dim vectors)
- **SQLite:** For semantic knowledge storage
- **No additional infrastructure required**

#### Example

**Before RAG:**
```
User: "flash all four Hue office lights using the Hue Flash command for 30 secs at the top of every hour"
System: Asks 3 clarification questions (false positives)
```

**After RAG (with similar successful query in knowledge base):**
```
User: "flash all four Hue office lights using the Hue Flash command for 30 secs at the top of every hour"
System: Processes directly, no clarification needed (similarity > 0.85)
```

### Entity Alias Management

#### `POST /api/v1/ask-ai/aliases`
Create alias for entity (e.g., "sleepy light" → light.bedroom_1)
```bash
curl -X POST http://localhost:8024/api/v1/ask-ai/aliases \
  -H "Content-Type: application/json" \
  -d '{
    "alias": "sleepy light",
    "entity_id": "light.bedroom_1",
    "user_id": "user123"
  }'
```

#### `DELETE /api/v1/ask-ai/aliases/{alias}`
Delete alias
```bash
curl -X DELETE http://localhost:8024/api/v1/ask-ai/aliases/sleepy%20light
```

#### `GET /api/v1/ask-ai/aliases`
List all aliases for user
```bash
curl http://localhost:8024/api/v1/ask-ai/aliases?user_id=user123
```

### Deployment & Management

#### `POST /api/deploy/{id}`
Deploy approved suggestion to Home Assistant
```bash
curl -X POST http://localhost:8024/api/deploy/abc123
```

#### `POST /api/deploy/batch`
Deploy multiple suggestions
```bash
curl -X POST http://localhost:8024/api/deploy/batch \
  -H "Content-Type: application/json" \
  -d '{
    "suggestion_ids": ["abc123", "def456"]
  }'
```

#### `GET /api/deploy/automations`
List deployed automations
```bash
curl http://localhost:8024/api/deploy/automations
```

#### `GET /api/deploy/automations/{id}`
Get automation status and details
```bash
curl http://localhost:8024/api/deploy/automations/automation.office_motion
```

#### `POST /api/deploy/automations/{id}/enable`
Enable deployed automation
```bash
curl -X POST http://localhost:8024/api/deploy/automations/automation.office_motion/enable
```

#### `POST /api/deploy/automations/{id}/disable`
Disable deployed automation
```bash
curl -X POST http://localhost:8024/api/deploy/automations/automation.office_motion/disable
```

#### `POST /api/deploy/automations/{id}/trigger`
Manually trigger automation
```bash
curl -X POST http://localhost:8024/api/deploy/automations/automation.office_motion/trigger
```

#### `POST /api/deploy/{id}/rollback`
Rollback automation to previous version
```bash
curl -X POST http://localhost:8024/api/deploy/abc123/rollback
```

#### `GET /api/deploy/{id}/versions`
Get version history for automation
```bash
curl http://localhost:8024/api/deploy/abc123/versions
```

#### `GET /api/deploy/test-connection`
Test Home Assistant connection
```bash
curl http://localhost:8024/api/deploy/test-connection
```

### Suggestion Management Operations

#### `DELETE /api/suggestions/{id}`
Delete suggestion
```bash
curl -X DELETE http://localhost:8024/api/suggestions/abc123
```

#### `POST /api/suggestions/batch/approve`
Approve multiple suggestions
```bash
curl -X POST http://localhost:8024/api/suggestions/batch/approve \
  -H "Content-Type: application/json" \
  -d '{
    "suggestion_ids": ["abc123", "def456"]
  }'
```

#### `POST /api/suggestions/batch/reject`
Reject multiple suggestions
```bash
curl -X POST http://localhost:8024/api/suggestions/batch/reject \
  -H "Content-Type: application/json" \
  -d '{
    "suggestion_ids": ["abc123", "def456"]
  }'
```

### Synergy Detection (Epic AI-3, AI-4)

#### `GET /api/synergies`
List detected device synergies with filtering
```bash
curl "http://localhost:8024/api/synergies?synergy_type=device_pair&min_confidence=0.7"
```

Query parameters:
- `synergy_type`: `device_pair`, `weather_context`, `energy_context`, `event_context`
- `min_confidence`: Minimum confidence score (0.0-1.0)
- `validated_by_patterns`: Filter by pattern validation
- `min_priority`: Minimum priority score
- `synergy_depth`: `2` (pair), `3` (3-chain), `4` (4-chain)

Results ordered by priority score (impact + confidence + pattern support)

Supports:
- 2-level pairs (e.g., Motion → Light)
- 3-level chains (e.g., Door → Lock → Light)
- 4-level chains (e.g., Door → Lock → Alarm → Notification)

#### `GET /api/synergies/stats`
Get synergy statistics by type and complexity
```bash
curl http://localhost:8024/api/synergies/stats
```

Response:
```json
{
  "total_synergies": 45,
  "by_type": {
    "device_pair": 20,
    "weather_context": 10,
    "energy_context": 8,
    "event_context": 7
  },
  "by_depth": {
    "2": 20,
    "3": 15,
    "4": 10
  },
  "validated_by_patterns": 12
}
```

#### `GET /api/synergies/{id}`
Get detailed synergy information
```bash
curl http://localhost:8024/api/synergies/abc123
```

#### `POST /api/synergies/detect`
Real-time synergy detection (includes 4-level chains)
```bash
curl -X POST http://localhost:8024/api/synergies/detect \
  -H "Content-Type: application/json" \
  -d '{
    "days_lookback": 30,
    "include_4_level": true
  }'
```

### Data Access

#### `GET /api/data/health`
Check Data API health and connectivity
```bash
curl http://localhost:8024/api/data/health
```

#### `GET /api/data/events`
Get events with filtering
```bash
curl "http://localhost:8024/api/data/events?entity_id=light.office&days=7"
```

#### `GET /api/data/devices`
Get devices from Data API
```bash
curl http://localhost:8024/api/data/devices
```

#### `GET /api/data/entities`
Get entities from Data API
```bash
curl http://localhost:8024/api/data/entities
```

### Validation & Ranking

#### Validation endpoints
Safety validation for generated automations (6-rule engine)

#### Ranking endpoints
Suggestion ranking and prioritization

### Community Pattern Discovery

#### Community pattern mining endpoints
Access to automation-miner service for community automation patterns

### Settings Management

#### Settings endpoints
Feature flag configuration and service settings

### Admin Operations

#### Admin endpoints
Service administration and maintenance operations

## Architecture

### Unified Daily Batch Job (3 AM)

The service runs a comprehensive analysis job every day at 3 AM:

**Phase 1: Device Capability Update (Epic AI-2)**
- Fetch device capabilities from Device Intelligence Service
- Update device registry with latest capabilities
- Track feature utilization

**Phase 2: Fetch Events from InfluxDB**
- Query last 30 days of state_changed events
- Filter relevant entities
- Prepare data for pattern detection

**Phase 3: Pattern Detection (Epic AI-1)**
- Time-of-day pattern detection
- Co-occurrence pattern detection
- Anomaly detection

**Phase 3c: Synergy Detection (Epic AI-3, AI-4)**
- **Part A: Device Pair Synergies** (2-level: cross-device automation opportunities)
- **Part B: Weather Context Synergies** (weather-based automations)
- **Part C: Energy Context Synergies** (cost optimization opportunities)
- **Part D: Event Context Synergies** (entertainment automation)
- **Part E: Multi-Hop Chains** (3-level and 4-level chains)
  - 3-level chains: A → B → C (e.g., Door → Lock → Light)
  - 4-level chains: A → B → C → D (e.g., Door → Lock → Alarm → Notification)
- Priority-based selection with validated pattern boost

**Phase 4: Feature Analysis (Epic AI-2)**
- Analyze device feature utilization
- Identify underutilized features
- Generate feature suggestions

**Phase 5: Description-Only Generation (Story AI1.24)**
- Generate human-readable descriptions (NO YAML yet)
- Use OpenAI GPT-4o-mini for natural language generation
- Save as status='draft' with automation_yaml=NULL
- YAML only generated after user approval via UI
- Combined ranking: Pattern + Feature + Synergy suggestions (top 10)

**Phase 6: Publish MQTT Notification**
- Notify AI Automation UI of new suggestions
- Include suggestion count and summary

### Components

```
ai-automation-service/
├── src/
│   ├── main.py                          # FastAPI application with lifespan
│   ├── config.py                        # Pydantic settings
│   ├── api/                             # API endpoints
│   │   ├── health_router.py
│   │   ├── pattern_router.py
│   │   ├── suggestion_router.py
│   │   ├── analysis_router.py
│   │   ├── deployment_router.py
│   │   ├── nl_generation_router.py
│   │   ├── conversational_router.py
│   │   ├── ask_ai_router.py
│   │   ├── synergy_router.py            # Epic AI-3, AI-4
│   │   ├── validation_router.py
│   │   ├── ranking_router.py
│   │   ├── community_pattern_router.py
│   │   ├── devices_router.py
│   │   ├── settings_router.py
│   │   ├── admin_router.py
│   │   └── middlewares.py               # Idempotency, Rate limiting
│   ├── database/
│   │   └── models.py                    # SQLAlchemy models (12 tables)
│   ├── pattern_analyzer/               # Epic AI-1
│   │   ├── time_of_day_detector.py
│   │   ├── co_occurrence_detector.py
│   │   └── anomaly_detector.py
│   ├── device_intelligence/            # Epic AI-2
│   │   ├── capability_parser.py
│   │   ├── mqtt_listener.py
│   │   └── feature_analyzer.py
│   ├── synergy_detection/              # Epic AI-3
│   │   ├── device_pair_detector.py
│   │   ├── weather_context.py
│   │   ├── energy_context.py
│   │   └── event_context.py
│   ├── nlevel_synergy/                 # Epic AI-4
│   │   ├── embedding_generator.py
│   │   ├── chain_detector.py
│   │   └── similarity_matcher.py
│   ├── clients/
│   │   ├── data_api_client.py
│   │   ├── device_intelligence_client.py
│   │   └── mqtt_client.py
│   ├── models/
│   │   └── model_manager.py             # OpenVINO model management
│   ├── langchain_integration/          # Feature flags
│   │   └── chains.py                    # LCEL chains
│   ├── pdl/                            # PDL workflows
│   │   └── workflows.py
│   ├── services/
│   │   ├── clarification/              # Clarification system
│   │   │   ├── detector.py            # Ambiguity detection (with RAG integration)
│   │   │   ├── question_generator.py  # Question generation
│   │   │   └── confidence_calculator.py
│   │   └── rag/                        # RAG (Retrieval-Augmented Generation)
│   │       ├── client.py              # Generic RAG client
│   │       ├── models.py              # Data models
│   │       └── exceptions.py          # Custom exceptions
│   ├── safety_validator.py             # 6-rule safety engine
│   ├── nl_automation_generator.py      # Natural language → YAML
│   └── scheduler.py                     # Daily analysis scheduler
├── alembic/                            # Database migrations
│   └── versions/
├── scripts/
│   └── seed_rag_knowledge_base.py     # Seed RAG knowledge base
├── tests/                              # 56/56 tests passing ✅
├── Dockerfile                          # Production container
├── requirements.txt                    # Python dependencies
└── pytest.ini                          # Test configuration
```

### Database Schema

**SQLite Database: ai_automation.db (13 tables)**

1. **patterns** - Detected patterns (time-of-day, co-occurrence, anomaly)
2. **suggestions** - Automation suggestions (draft, approved, rejected, deployed)
3. **device_capabilities** - Device capability metadata
4. **feature_usage** - Device feature utilization tracking
5. **synergies** - Detected device synergies (2-4 level chains)
6. **device_embeddings** - Device similarity embeddings
7. **entity_aliases** - User-defined entity nicknames
8. **deployment_history** - Automation deployment tracking
9. **openai_usage** - OpenAI API usage statistics
10. **analysis_runs** - Daily analysis job tracking
11. **validation_results** - Safety validation results
12. **semantic_knowledge** - RAG knowledge base (queries, patterns, automations with embeddings)
13. **clarification_sessions** - Persistent clarification sessions with query linkage (AI1.26)

### Entity Resolution Enhancements

**Multi-Signal Matching:**
- Embeddings (35%): Semantic similarity using sentence-transformers
- Exact matches (30%): Direct entity_id or name matching
- Fuzzy matching (15%): Typo handling with rapidfuzz (e.g., "office lite" → "office light")
- Numbered devices (15%): Smart parsing of "bedroom light 1"
- Location (5%): Area/room-based filtering

**Enhanced Blocking:**
- Domain filtering (light, switch, sensor, etc.)
- Location filtering (bedroom, office, kitchen, etc.)
- Reduces candidate entities by 90-95% before ML matching

**User Aliases:**
- Create personalized names for entities
- Example: "sleepy light" → light.bedroom_1
- Stored in entity_aliases table

**Additional Metadata:**
- Leverages `name_by_user` from device registry
- Uses `suggested_area` for location context
- Includes `integration` for filtering

### Safety Validation (6-Rule Engine)

Implemented in `src/safety_validator.py`:

1. **No destructive actions without confirmation** - Prevent device damage
2. **No entity ID mismatches** - Ensure correct device references
3. **No excessive automation frequency** - Prevent automation spam
4. **No unsafe device combinations** - Block dangerous pairings
5. **No privacy-violating data collection** - Protect user privacy
6. **No unrealistic time ranges** - Validate time specifications

All generated automations must pass all 6 rules before deployment.

### Design Patterns

- **FastAPI Router Pattern** - Modular endpoint organization
- **Dependency Injection** - Client and service management
- **Repository Pattern** - Database access abstraction
- **Lifespan Management** - Proper startup/shutdown with async context managers
- **Middleware Pattern** - Idempotency and rate limiting
- **Scheduler Pattern** - APScheduler for daily batch jobs
- **Client Pattern** - External service communication
- **Strategy Pattern** - Multiple pattern detection strategies
- **Chain of Responsibility** - Safety validation rules
- **Factory Pattern** - Model manager for OpenVINO models

## Development

### Epic AI-1 (Pattern Detection)
- **Stories:** `docs/stories/story-ai1-*.md`
- **Components:** `src/pattern_analyzer/`
- **Tests:** `tests/test_*_detector.py`
- **Status:** Complete ✅

### Epic AI-2 (Device Intelligence)
- **Stories:** `docs/stories/story-ai2-*.md`
- **Components:** `src/device_intelligence/`
- **Tests:** `tests/test_feature_*.py`, `tests/test_database_models.py`
- **Status:** Complete ✅ (Stories 2.1-2.5)

### Epic AI-3 (N-Level Synergy Detection)
- **Stories:** `docs/stories/story-ai3-*.md`
- **Components:** `src/synergy_detection/`
- **Tests:** `tests/test_synergy_*.py`
- **Status:** Complete ✅

### Epic AI-4 (Advanced Synergy Analysis)
- **Stories:** `docs/stories/story-ai4-*.md`
- **Components:** `src/nlevel_synergy/`
- **Tests:** `tests/test_nlevel_*.py`
- **Status:** In Progress 🚧

### Local Development

```bash
cd services/ai-automation-service

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm

# Run migrations
alembic upgrade head

# Run service
uvicorn src.main:app --reload --port 8018
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1

# View migration history
alembic history
```

### API Documentation

When running locally, interactive API documentation is available at:
- **Swagger UI:** http://localhost:8018/docs
- **ReDoc:** http://localhost:8018/redoc
- **OpenAPI JSON:** http://localhost:8018/openapi.json

## Testing

### Run Unit Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=src --cov-report=html tests/

# Run specific test file
pytest tests/test_pattern_analyzer.py

# Run specific test
pytest tests/test_pattern_analyzer.py::test_time_of_day_detection

# Run async tests
pytest tests/ -v
```

**Test Coverage:** 56/56 unit tests passing ✅

### Test Categories

- **Pattern Detection:** `tests/test_*_detector.py`
- **Device Intelligence:** `tests/test_feature_*.py`
- **Synergy Detection:** `tests/test_synergy_*.py`
- **Database Models:** `tests/test_database_models.py`
- **API Endpoints:** `tests/test_api_*.py`
- **Safety Validation:** `tests/test_safety_validator.py`

### Manual Testing

```bash
# Test health endpoint
curl http://localhost:8024/health

# Test pattern detection
curl -X POST http://localhost:8024/api/patterns/detect/time-of-day \
  -H "Content-Type: application/json" \
  -d '{"days_lookback": 30}'

# Test suggestion generation
curl -X POST http://localhost:8024/api/suggestions/generate

# Test Ask AI
curl -X POST http://localhost:8024/api/v1/ask-ai/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What can I do with my office lights?"}'
```

## Performance

### Performance Metrics

- **Job Duration:** 2-4 minutes typical (70-230s per phase)
- **Memory Usage:** 200-400MB peak
- **OpenAI Cost:** ~$0.001-0.005 per run (~$0.50/year)
- **Resource Reduction:** 99% less uptime vs real-time (2.5 hrs vs 730 hrs/month)

### Detailed Performance Breakdown

**Phase Timings:**
1. Device Capability Update: 10-30s
2. Fetch Events: 20-60s
3. Pattern Detection: 30-90s
4. Synergy Detection: 15-45s (includes 4-level chains)
5. Feature Analysis: 10-30s
6. Description Generation: 5-15s (OpenAI API calls)
7. MQTT Notification: <1s

**OpenAI Usage:**
- **Model:** GPT-4o-mini
- **Tokens per run:** ~1,000-5,000 tokens
- **Cost per run:** $0.001-0.005
- **Annual cost:** ~$0.50 (365 runs)

**Scaling Characteristics:**
- 100 devices: ~2 minutes
- 500 devices: ~3 minutes
- 1000 devices: ~4 minutes

See [Call Tree Index](../../implementation/analysis/AI_AUTOMATION_CALL_TREE_INDEX.md) for exhaustive performance details.

## Configuration

### Feature Flags

**LangChain Integration:**
- `USE_LANGCHAIN_ASK_AI=false` - Enable LangChain for Ask AI prompts
- `USE_LANGCHAIN_PATTERNS=false` - Enable LangChain for pattern detection

**PDL Workflows:**
- PDL-based orchestration available in `src/pdl/`
- Nightly analysis coordination
- Synergy guardrails (when enabled)

### Settings UI

Configure feature flags and service settings via:
- AI Automation UI: http://localhost:3001/settings
- Admin API: http://localhost:8004/api/v1/config

## Documentation

### User Documentation
- **PRD:** `docs/prd.md` (Complete product requirements)
- **Architecture:** `docs/architecture-device-intelligence.md`
- **Brief:** `docs/brief.md` (Project overview)
- **User Manual:** `docs/USER_MANUAL.md`

### Developer Documentation
- **Call Tree Index:** [AI_AUTOMATION_CALL_TREE_INDEX.md](../../implementation/analysis/AI_AUTOMATION_CALL_TREE_INDEX.md)
- **Complete Call Tree:** [AI_AUTOMATION_CALL_TREE.md](../../implementation/analysis/AI_AUTOMATION_CALL_TREE.md)
- **Epic AI-1 Stories:** `docs/stories/story-ai1-*.md` (Pattern detection)
- **Epic AI-2 Stories:** `docs/stories/story-ai2-*.md` (Device intelligence)
- **Epic AI-3 Stories:** `docs/stories/story-ai3-*.md` (Synergy detection)
- **Epic AI-4 Stories:** `docs/stories/story-ai4-*.md` (Advanced synergy analysis)
- **MQTT Setup:** `docs/stories/MQTT_SETUP_GUIDE.md`
- **Implementation Guides:** `implementation/`

### Operations Documentation
- **Deployment:** `implementation/DEPLOYMENT_STORY_AI2-5.md`
- **Quick Reference:** `implementation/QUICK_REFERENCE_AI2.md`
- **Troubleshooting:** See deployment guide
- **CLAUDE.md:** `CLAUDE.md` (AI assistant development guide)

### API Documentation
- **API Reference:** `docs/api/API_REFERENCE.md`
- **OpenAPI Spec:** http://localhost:8024/openapi.json

## Dependencies

### Core Dependencies

```
fastapi==0.121.2              # Web framework
uvicorn==0.38.0               # ASGI server
python-multipart==0.0.20      # Form data parsing
pydantic==2.12.4              # Data validation
pydantic-settings==2.12.0     # Settings management
```

### Database

```
sqlalchemy==2.0.44            # ORM
aiosqlite==0.21.0             # Async SQLite driver
alembic==1.17.2               # Database migrations
```

### HTTP & MQTT

```
httpx==0.27.2                 # Async HTTP client
aiohttp==3.13.2               # Async HTTP client
paho-mqtt==1.6.1              # MQTT client
```

### Data Processing

```
pandas==2.3.3                 # Data analysis
numpy==2.3.4                  # Numerical computing
scikit-learn==1.4.2           # Machine learning
influxdb-client==1.49.0       # InfluxDB 2.x client
```

### AI & ML

```
openai==1.40.2                # OpenAI API client (GPT-4o-mini)
spacy==3.7.2                  # NLP and NER fallback
sentence-transformers==3.3.1  # Embeddings (all-MiniLM-L6-v2)
transformers==4.46.1          # HuggingFace models
torch==2.3.1+cpu              # CPU-only PyTorch
openvino==2024.6.0            # Intel optimization
optimum-intel==1.21.0         # OpenVINO + Transformers
peft==0.14.0                  # LoRA fine-tuning support
```

### Utilities

```
apscheduler==3.11.1           # Job scheduling
python-dotenv==1.2.1          # Environment variables
tenacity==8.2.3               # Retry logic
pyyaml==6.0.3                 # YAML parsing
rapidfuzz>=3.14.3             # Fuzzy string matching
langchain==0.2.14             # Prompt orchestration (optional)
deprecated==1.2.14            # Deprecation warnings
```

### Development & Testing

```
pytest==8.3.3                 # Testing framework
pytest-asyncio==0.23.0        # Async test support
```

## Troubleshooting

### Service Won't Start

**Check logs:**
```bash
docker compose logs ai-automation-service
```

**Common issues:**
- Data API not accessible → Check `DATA_API_URL`
- Device Intelligence Service not accessible → Check `DEVICE_INTELLIGENCE_URL`
- OpenAI API key missing → Set `OPENAI_API_KEY`
- MQTT broker not accessible → Check `MQTT_BROKER` and credentials
- Database migration needed → Run `alembic upgrade head`

### Daily Analysis Not Running

**Check scheduler:**
```bash
curl http://localhost:8024/api/analysis/schedule
```

**Verify schedule:**
- Default: `0 3 * * *` (3 AM daily)
- Check `ANALYSIS_SCHEDULE` environment variable
- Look for cron syntax errors

**Manual trigger:**
```bash
curl -X POST http://localhost:8024/api/analysis/trigger
```

### OpenAI API Errors

**Check usage stats:**
```bash
curl http://localhost:8024/api/suggestions/usage-stats
```

**Common issues:**
- API key invalid → Verify `OPENAI_API_KEY`
- Rate limit exceeded → Check OpenAI dashboard
- Insufficient credits → Add credits to OpenAI account

### MQTT Connection Issues

**Test MQTT connection:**
- Check MQTT broker is running
- Verify credentials: `MQTT_USERNAME`, `MQTT_PASSWORD`
- Check network connectivity to broker
- Service continues without MQTT if connection fails (warning logged)

### Database Issues

**Reset database:**
```bash
rm data/ai_automation.db
alembic upgrade head
```

**Check migrations:**
```bash
alembic current
alembic history
```

### RAG System Issues

**Knowledge base not working:**
- Verify OpenVINO service is running: `curl http://localhost:8019/health`
- Check `OPENVINO_SERVICE_URL` environment variable
- Seed knowledge base: `python scripts/seed_rag_knowledge_base.py`
- Check database migration: `alembic current` (should include `20250120_semantic_knowledge`)

**Clarification still asking too many questions:**
- Ensure knowledge base is seeded with successful queries
- Check similarity threshold (default: 0.85) - may need adjustment
- Verify embeddings are being generated (check logs for RAG client initialization)
- System falls back to hardcoded rules if RAG unavailable (expected behavior)

### Pattern Detection Not Finding Patterns

**Check event data:**
```bash
curl http://localhost:8024/api/data/events?days=30
```

**Verify:**
- Sufficient historical data (30+ days recommended)
- Events being captured by websocket-ingestion service
- InfluxDB contains state_changed events

### Memory Usage High

**Normal behavior:**
- Peak during daily analysis: 200-400MB
- Baseline: ~100-150MB

**If excessive:**
- Check for memory leaks in logs
- Restart service: `docker compose restart ai-automation-service`
- Review analysis job configuration

## Security

### API Security
- CORS configured for AI Automation UI
- No authentication required (internal service)
- Input validation with Pydantic models
- Safety validation before deployment

### OpenAI API Key
- Store in environment variable, never commit to code
- Rotate periodically
- Monitor usage via OpenAI dashboard

### Home Assistant Token
- Long-lived access token required
- Store in `HA_TOKEN` environment variable
- Minimum required permissions: automation management

### MQTT Credentials
- Username/password authentication
- Store in environment variables
- No unencrypted credentials in logs

## Contributing

1. Follow Python PEP 8 style guidelines
2. Use Black for code formatting
3. Use type hints for all functions
4. Add docstrings for all classes and functions
5. Write tests for new functionality
6. Run `pytest tests/` before committing
7. Update documentation when adding features

### Code Style Example

```python
"""Module docstring explaining purpose"""

from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

async def detect_patterns(
    days_lookback: int = 30,
    min_confidence: float = 0.7
) -> List[Dict[str, Any]]:
    """
    Detect patterns from historical data

    Args:
        days_lookback: Number of days to analyze
        min_confidence: Minimum confidence threshold (0.0-1.0)

    Returns:
        List of detected patterns with metadata

    Raises:
        ValueError: If days_lookback is invalid
        DataAPIError: If data fetching fails
    """
    try:
        # Implementation
        pass
    except Exception as e:
        logger.error(f"Pattern detection failed: {e}")
        raise
```

## Related Documentation

- [API Reference](../../docs/api/API_REFERENCE.md) - Complete API documentation
- [Architecture Overview](../../docs/architecture/) - System architecture
- [Database Schema](../../docs/architecture/database-schema.md) - Database structure
- [Deployment Guide](../../docs/DEPLOYMENT_GUIDE.md) - Deployment instructions
- [CLAUDE.md](../../CLAUDE.md) - AI assistant development guide
- [Call Tree Documentation](../../implementation/analysis/AI_AUTOMATION_CALL_TREE_INDEX.md) - Exhaustive system internals

## Support

- **Issues:** File on GitHub at https://github.com/wtthornton/HomeIQ/issues
- **Documentation:** Check `/docs` directory
- **API Docs:** http://localhost:8024/docs
- **Health Status:** http://localhost:8024/health

## Version History

### 2.3 (November 17, 2025)
- Added area filtering to Ask AI interface
- Automatically extracts area from user queries and filters devices accordingly
- Enhanced prompt template with area restriction warnings
- Supports single and multiple area specifications
- Improved device selection accuracy for area-specific automations

### 2.2 (November 18, 2025)
- Story AI1.26: Persistent clarification session storage
- Database-backed clarification flow with query ID linkage
- Smart suggestion retrieval (supports both direct and clarification query IDs)
- HOME_ASSISTANT_TOKEN standardization (removed LOCAL_HA_TOKEN/LOCAL_HA_URL)
- YAML 2025 standards enforcement
- New clarification API endpoints
- Updated database schema (13 tables)

### 2.1 (November 15, 2025)
- Updated documentation to 2025 standards
- Enhanced dependency documentation
- Added comprehensive API endpoint documentation
- Updated performance metrics
- Improved troubleshooting section
- Added security best practices

### 2.0 (October 2025)
- Epic AI-4 implementation (Advanced Synergy Analysis)
- Multi-hop chain detection (4-level chains)
- Enhanced entity resolution with fuzzy matching
- LangChain integration (feature flags)
- PDL workflow support

### 1.5 (September 2025)
- Epic AI-3 complete (N-Level Synergy Detection)
- 3-level chain detection
- Weather, energy, and event context synergies

### 1.0 (Initial Release)
- Epic AI-1 complete (Pattern Detection)
- Epic AI-2 complete (Device Intelligence)
- Conversational automation flow
- Natural language generation
- Ask AI interface

---

**Last Updated:** November 17, 2025
**Version:** 2.3
**Status:** Production Ready ✅
**Port:** 8018 (internal), 8024 (external)

**Epic AI-1:** Complete ✅ (Pattern Detection + Clarification Flow - Story AI1.26)
**Epic AI-2:** Complete ✅ (Device Intelligence - Stories 2.1-2.5)
**Epic AI-3:** Complete ✅ (N-Level Synergy Detection)
**Epic AI-4:** In Progress 🚧 (Advanced Synergy Analysis)
