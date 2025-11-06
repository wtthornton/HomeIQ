# AI Automation Service

AI-powered Home Assistant automation discovery and recommendation system with device intelligence.

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

## Quick Start

### Prerequisites

- Python 3.11+
- Home Assistant with MQTT integration
- OpenAI API key
- Data API service running (port 8006)

### Configuration

1. Configure credentials in `infrastructure/env.ai-automation`
2. See `docs/stories/MQTT_SETUP_GUIDE.md` for details

### Running Locally

```bash
cd services/ai-automation-service

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start service
python -m uvicorn src.main:app --host 0.0.0.0 --port 8018 --reload
# Note: Service runs on port 8018 internally, exposed as 8024 externally in Docker
```

### Running with Docker

```bash
# From project root
docker-compose up -d ai-automation-service
```

## API Endpoints

### Health & System
- `GET /health` - Service health check with device intelligence stats
- `GET /event-rate` - Standardized event rate metrics

### Analysis & Pattern Detection
- `GET /api/analysis/status` - Current analysis status and pattern statistics
- `POST /api/analysis/analyze-and-suggest` - Run complete analysis pipeline
- `POST /api/analysis/trigger` - Manually trigger daily analysis job
- `GET /api/analysis/schedule` - Get analysis schedule information

### Pattern Detection
- `POST /api/patterns/detect/time-of-day` - Detect time-of-day patterns
- `POST /api/patterns/detect/co-occurrence` - Detect co-occurrence patterns
- `GET /api/patterns/list` - List detected patterns with filtering
- `GET /api/patterns/stats` - Get pattern detection statistics

### Suggestion Management
- `POST /api/suggestions/generate` - Generate automation suggestions from patterns
- `GET /api/suggestions/list` - List suggestions with status filtering
- `GET /api/suggestions/usage-stats` - Get OpenAI API usage statistics
- `POST /api/suggestions/usage-stats/reset` - Reset usage statistics

### Conversational Automation Flow
- `POST /api/v1/suggestions/generate` - Generate description-only suggestion
- `POST /api/v1/suggestions/{id}/refine` - Refine suggestion with natural language
- `POST /api/v1/suggestions/{id}/approve` - Approve and generate YAML
- `GET /api/v1/suggestions/devices/{device_id}/capabilities` - Get device capabilities
- `GET /api/v1/suggestions/{id}` - Get detailed suggestion information

### Natural Language Generation
- `POST /api/nl/generate` - Generate automation from natural language
- `POST /api/nl/clarify/{id}` - Clarify automation request
- `GET /api/nl/examples` - Get example requests
- `GET /api/nl/stats` - Get NL generation statistics

### Ask AI - Natural Language Query Interface
- `POST /api/v1/ask-ai/query` - Process natural language query
- `POST /api/v1/ask-ai/query/{id}/refine` - Refine query results
- `GET /api/v1/ask-ai/query/{id}/suggestions` - Get query suggestions
- `POST /api/v1/ask-ai/query/{id}/suggestions/{id}/test` - Test suggestion
- `POST /api/v1/ask-ai/query/{id}/suggestions/{id}/approve` - Approve suggestion

### Entity Alias Management
- `POST /api/v1/ask-ai/aliases` - Create alias for entity (e.g., "sleepy light" → light.bedroom_1)
- `DELETE /api/v1/ask-ai/aliases/{alias}` - Delete alias
- `GET /api/v1/ask-ai/aliases` - List all aliases for user

### Deployment & Management
- `POST /api/deploy/{id}` - Deploy approved suggestion to Home Assistant
- `POST /api/deploy/batch` - Deploy multiple suggestions
- `GET /api/deploy/automations` - List deployed automations
- `GET /api/deploy/automations/{id}` - Get automation status
- `POST /api/deploy/automations/{id}/enable` - Enable automation
- `POST /api/deploy/automations/{id}/disable` - Disable automation
- `POST /api/deploy/automations/{id}/trigger` - Trigger automation
- `POST /api/deploy/{id}/rollback` - Rollback automation
- `GET /api/deploy/{id}/versions` - Get version history
- `GET /api/deploy/test-connection` - Test Home Assistant connection

### Suggestion Management Operations
- `DELETE /api/suggestions/{id}` - Delete suggestion
- `POST /api/suggestions/batch/approve` - Approve multiple suggestions
- `POST /api/suggestions/batch/reject` - Reject multiple suggestions

### Synergy Detection (Epic AI-3)
- `GET /api/synergies` - List detected device synergies with filtering
  - Query params: `synergy_type` (device_pair, weather_context, energy_context, event_context)
  - Query params: `min_confidence`, `validated_by_patterns`, `min_priority`
  - Results ordered by priority score (impact + confidence + pattern support)
- `GET /api/synergies/stats` - Get synergy statistics by type and complexity
- `GET /api/synergies/{id}` - Get detailed synergy information

### Data Access
- `GET /api/data/health` - Check Data API health
- `GET /api/data/events` - Get events with filtering
- `GET /api/data/devices` - Get devices
- `GET /api/data/entities` - Get entities

## Architecture

**Unified Daily Batch Job (3 AM):**
1. Phase 1: Device Capability Update (Epic AI-2)
2. Phase 2: Fetch Events from InfluxDB (Shared)
3. Phase 3: Pattern Detection (Epic AI-1)
4. Phase 3c: **Synergy Detection (Epic AI-3)** - Enhanced
   - Part A: Device Pair Synergies (cross-device automation opportunities)
   - Part B: Weather Context Synergies (weather-based automations)
   - Part C: Energy Context Synergies (cost optimization opportunities) - **NEW**
   - Part D: Event Context Synergies (entertainment automation) - **NEW**
   - Priority-based selection with validated pattern boost
5. Phase 4: Feature Analysis (Epic AI-2)
6. Phase 5: **Description-Only Generation** (OpenAI GPT-4o-mini) - Story AI1.24
   - Generates human-readable descriptions (NO YAML yet)
   - Saves as status='draft' with automation_yaml=NULL
   - YAML only generated after user approval via UI
   - Combined ranking: Pattern + Feature + Synergy suggestions (top 10)
7. Phase 6: Publish MQTT Notification

### 📖 Complete System Documentation

**🎯 START HERE:** [**Call Tree Index**](../../implementation/analysis/AI_AUTOMATION_CALL_TREE_INDEX.md)

The complete call tree documentation provides exhaustive detail on every phase:
- Detailed call stacks from 3 AM wake-up to completion
- OpenAI prompt templates and API integration
- Database schemas and storage patterns
- Performance characteristics and costs
- Real-world examples with actual JSON payloads

**Quick Links:**
- [Complete Call Tree](../../implementation/analysis/AI_AUTOMATION_CALL_TREE.md) - All phases in one document
- [OpenAI Integration Details](../../implementation/analysis/AI_AUTOMATION_CALL_TREE_INDEX.md#6-phase-5-openai-suggestion-generation) - Prompts, templates, costs
- [Device Discovery Process](../../implementation/analysis/AI_AUTOMATION_CALL_TREE_INDEX.md#2-phase-1-device-capability-discovery) - Zigbee2MQTT integration

**Additional Documentation:**
- PRD: `docs/prd.md` (Stories AI1.*, AI2.*, AI3.*, AI4.*)
- Epic AI-1 Stories: `docs/stories/story-ai1-*.md`
- Epic AI-2 Stories: `docs/stories/story-ai2-*.md`
- Epic AI-3 Stories: `docs/stories/story-ai3-*.md`
- Epic AI-4 Stories: `docs/stories/story-ai4-*.md`
- Architecture: `docs/architecture-device-intelligence.md`

## Development

### Epic AI-1 (Pattern Detection)
- Stories: `docs/stories/story-ai1-*.md`
- Components: `src/pattern_analyzer/`
- Tests: `tests/test_*_detector.py`

### Epic AI-2 (Device Intelligence)
- Stories: `docs/stories/story-ai2-*.md`
- Components: `src/device_intelligence/`
- Tests: `tests/test_feature_*.py`, `tests/test_database_models.py`

### Epic AI-3 (N-Level Synergy Detection)
- Stories: `docs/stories/story-ai3-*.md`
- Components: `src/synergy_detection/`
- Tests: `tests/test_synergy_*.py`

### Epic AI-4 (Advanced Synergy Analysis)
- Stories: `docs/stories/story-ai4-*.md`
- Components: `src/nlevel_synergy/`
- Tests: `tests/test_nlevel_*.py`

### Database
- **SQLite**: Patterns, suggestions, device capabilities, feature usage, synergies, embeddings, entity aliases
- **Alembic migrations**: `alembic/versions/`
- **Models**: `src/database/models.py`
- **New Tables**: `entity_aliases` (user-defined nicknames for entities)

### Entity Resolution Enhancements
- **Multi-Signal Matching**: Combines embeddings (35%), exact matches (30%), fuzzy matching (15%), numbered devices (15%), and location (5%)
- **Fuzzy String Matching**: Handles typos and abbreviations using rapidfuzz (e.g., "office lite" → "office light")
- **Enhanced Blocking**: Domain and location filtering reduces candidate entities by 90-95% before ML matching
- **User Aliases**: Create personalized names for entities (e.g., "sleepy light" → light.bedroom_1)
- **Additional Metadata**: Leverages `name_by_user`, `suggested_area`, and `integration` from device registry

## Testing

```bash
pytest tests/
```

**Test Coverage:** 56/56 unit tests passing ✅

## Performance

- **Job Duration:** 2-4 minutes typical (70-230s per phase breakdown in [call tree](../../implementation/analysis/AI_AUTOMATION_CALL_TREE_INDEX.md))
- **Memory Usage:** 200-400MB peak
- **OpenAI Cost:** ~$0.001-0.005 per run (~$0.50/year) - See [detailed cost analysis](../../implementation/analysis/AI_AUTOMATION_CALL_TREE_INDEX.md)
- **Resource Reduction:** 99% less uptime vs real-time (2.5 hrs vs 730 hrs/month)

**Detailed Performance Metrics:**
See [Call Tree Index](../../implementation/analysis/AI_AUTOMATION_CALL_TREE_INDEX.md) for:
- Per-phase timing breakdown
- Token usage per OpenAI call
- Database query performance
- Scaling characteristics (100-1000 devices)

## Documentation

### User Documentation
- **PRD:** `docs/prd.md` (Complete product requirements)
- **Architecture:** `docs/architecture-device-intelligence.md`
- **Brief:** `docs/brief.md` (Project overview)

### Developer Documentation
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

---

**Version:** 2.0.0  
**Epic AI-1:** Complete (Pattern Detection)  
**Epic AI-2:** Complete (Device Intelligence - Stories 2.1-2.5)  
**Epic AI-3:** Complete (N-Level Synergy Detection)  
**Epic AI-4:** In Progress (Advanced Synergy Analysis)  
**Status:** Production Ready ✅

