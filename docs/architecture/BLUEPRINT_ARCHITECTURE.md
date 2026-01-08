# Blueprint-First Architecture

**Date:** January 7, 2026  
**Status:** Production  
**Epic:** Blueprint Transformation (Research-Driven Enhancement)

## Executive Summary

The Blueprint-First Architecture represents a paradigm shift in how HomeIQ handles automation creation. Instead of using Home Assistant blueprints for post-hoc validation, the system now proactively recommends, matches, and deploys community blueprints based on the user's device inventory.

### Key Benefits

1. **Reduced Manual Effort**: Users don't need to search for blueprints - the system recommends them
2. **Better Automations**: Community-vetted blueprints are often more robust than generated YAML
3. **Higher Success Rate**: Blueprint-matched automations have higher deployment success rates
4. **Community Integration**: Direct access to thousands of community blueprints

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Blueprint Index Service                          │
│                        (Port 8031)                                   │
│  ┌─────────────┐  ┌──────────────────┐  ┌───────────────────────┐  │
│  │  GitHub     │  │    Discourse     │  │    Blueprint Parser   │  │
│  │  Indexer    │  │    Indexer       │  │  (domains, inputs,    │  │
│  │             │  │                  │  │   device classes)     │  │
│  └──────┬──────┘  └────────┬─────────┘  └───────────┬───────────┘  │
│         │                  │                        │              │
│         └──────────────────┴────────────────────────┘              │
│                            │                                       │
│              ┌─────────────▼─────────────────┐                    │
│              │   Search Engine + Ranking     │                    │
│              │  (community rating, stars)    │                    │
│              └─────────────┬─────────────────┘                    │
└────────────────────────────┼────────────────────────────────────────┘
                             │
                             │ Search API
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     AI Pattern Service                              │
│                        (Port 8020)                                  │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │              Blueprint Opportunity Engine                     │  │
│  │  ┌──────────────────┐    ┌───────────────────────────────┐  │  │
│  │  │  Device Matcher  │    │      Input Autofill           │  │  │
│  │  │  (fit scoring)   │    │  (entity ID suggestions)      │  │  │
│  │  └──────────────────┘    └───────────────────────────────┘  │  │
│  └────────────────────────────────┬──────────────────────────────┘  │
│                                   │                                 │
│  ┌────────────────────────────────▼──────────────────────────────┐  │
│  │              Blueprint Deployer                               │  │
│  │  - HA Blueprint API integration                               │  │
│  │  - YAML fallback for unmatched patterns                       │  │
│  └────────────────────────────────┬──────────────────────────────┘  │
│                                   │                                 │
│  ┌────────────────────────────────▼──────────────────────────────┐  │
│  │              Synergy Detector (Enhanced)                      │  │
│  │  - Blueprint enrichment during detection                      │  │
│  │  - Confidence boost for blueprint matches                     │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                             │
                             │ API Responses
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Health Dashboard                                │
│                        (Port 3000)                                  │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │              Synergies Tab                                    │  │
│  │  ┌───────────────────┐  ┌─────────────────────────────────┐  │  │
│  │  │   Synergies List  │  │   Blueprint Opportunities Tab   │  │  │
│  │  │  (with blueprint  │  │   - Fit scores                  │  │  │
│  │  │   metadata)       │  │   - Preview & Deploy            │  │  │
│  │  └───────────────────┘  └─────────────────────────────────┘  │  │
│  └─────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Blueprint Index Service (Port 8031)

**Location:** `services/blueprint-index/`

A new microservice that indexes community blueprints from multiple sources.

**Key Features:**
- GitHub repository crawler (home-assistant/core, community repos)
- Discourse forum crawler (community.home-assistant.io)
- Blueprint YAML parser (extracts domains, device classes, inputs)
- Full-text search with filters
- Community-based ranking

**Database Model:**
```python
class IndexedBlueprint:
    id: str                    # Unique blueprint ID
    source_url: str            # GitHub/Discourse URL
    name: str                  # Blueprint name
    description: str           # Blueprint description
    domain: str                # Primary domain (automation, script)
    required_domains: list     # ["binary_sensor", "light"]
    required_device_classes: list  # ["motion", "door"]
    inputs: dict               # Blueprint input schema
    stars: int                 # GitHub stars
    downloads: int             # Forum downloads
    community_rating: float    # 0.0-1.0
    author: str                # Blueprint author
    ha_min_version: str        # Minimum HA version
    yaml_content: str          # Full blueprint YAML
```

**API Endpoints:**
- `GET /api/blueprints/search?query=&domain=&device_class=&use_case=`
- `GET /api/blueprints/{blueprint_id}`
- `POST /api/blueprints/index` (trigger re-indexing)
- `GET /health`

### 2. Blueprint Opportunity Engine

**Location:** `services/ai-pattern-service/src/blueprint_opportunity/`

Discovers and ranks blueprint opportunities for users based on their device inventory.

**Key Components:**

#### Device Matcher (`device_matcher.py`)
Calculates fit scores for blueprints against user devices.

**Fit Score Formula:**
```
Fit Score = (Domain Match × 0.40) + (Device Class Match × 0.30) + 
            (Same Area Bonus × 0.20) + (Community Rating × 0.10)
```

#### Input Autofill (`input_autofill.py`)
Automatically suggests entity IDs for blueprint inputs.

```python
# Example: Motion Light Blueprint
# Required input: motion_sensor (binary_sensor, device_class: motion)
# User has: binary_sensor.kitchen_motion

# Autofill suggestion:
{
    "motion_sensor": {
        "suggested_entity": "binary_sensor.kitchen_motion",
        "confidence": 0.95,
        "alternatives": ["binary_sensor.hallway_motion"]
    }
}
```

#### Opportunity Engine (`opportunity_engine.py`)
Orchestrates the discovery process:
1. Fetch device inventory from data-api
2. Search Blueprint Index for matching blueprints
3. Calculate fit scores for each blueprint
4. Generate autofill suggestions
5. Return ranked opportunities

**API Endpoints:**
- `GET /api/v1/blueprint-opportunities?min_fit_score=0.5&domain=light`
- `POST /api/v1/blueprint-opportunities/discover` (custom device inventory)
- `GET /api/v1/blueprint-opportunities/{blueprint_id}`
- `POST /api/v1/blueprint-opportunities/{blueprint_id}/preview`
- `GET /api/v1/blueprint-opportunities/synergy/{synergy_id}/matches`

### 3. Blueprint Deployer

**Location:** `services/ai-pattern-service/src/blueprint_deployment/`

Handles deployment of blueprints as Home Assistant automations.

**Key Features:**
- Blueprint import via HA REST API
- Automation creation with blueprint reference
- Input auto-fill with device inventory
- Deployment preview without committing
- Automatic fallback to YAML generation

**Home Assistant API Integration:**
```python
# Import blueprint from URL
POST /api/blueprint/import
{"url": "https://github.com/user/repo/blueprint.yaml"}

# Create automation from blueprint
POST /api/config/automation/config/{automation_id}
{
    "alias": "Kitchen Motion Light",
    "use_blueprint": {
        "path": "homeassistant/motion_light",
        "input": {
            "motion_entity": "binary_sensor.kitchen_motion",
            "light_entity": "light.kitchen_main"
        }
    }
}

# Reload automations
POST /api/services/automation/reload
```

### 4. Enhanced Synergy Detector

**Location:** `services/ai-pattern-service/src/synergy_detection/synergy_detector.py`

The synergy detector now enriches detected synergies with blueprint metadata.

**Enhancement:** `_enrich_with_blueprints()` method
- Finds matching blueprints for each synergy
- Adds blueprint_id, blueprint_name, blueprint_fit_score
- Boosts confidence for high-fit blueprint matches
  - ≥80% fit: +15% confidence, +10% impact
  - ≥60% fit: +10% confidence, +5% impact

**API Response Enhancement:**
```json
{
    "synergy_id": "device_pair_abc123",
    "synergy_type": "device_pair",
    "confidence": 0.85,
    "impact_score": 0.72,
    "blueprint_id": "homeassistant/motion_light",
    "blueprint_name": "Motion-activated Light",
    "blueprint_fit_score": 0.92,
    "has_blueprint_match": true
}
```

### 5. Synergies Tab (UI)

**Location:** `services/health-dashboard/src/components/tabs/SynergiesTab.tsx`

New dashboard tab with two views:
1. **Synergies List**: Displays detected synergies with blueprint metadata
2. **Blueprint Opportunities**: Shows recommended blueprints with fit scores

**Features:**
- Filter by confidence/fit score
- Filter by domain
- Preview blueprint deployment
- One-click deploy (coming in Phase 3.2)
- Community stats (stars, ratings)

## Data Flow

### 1. Blueprint Discovery Flow

```
User opens Synergies Tab
        │
        ▼
Frontend calls GET /api/v1/blueprint-opportunities
        │
        ▼
AI Pattern Service fetches device inventory from data-api
        │
        ▼
AI Pattern Service searches Blueprint Index
        │
        ▼
Blueprint Opportunity Engine calculates fit scores
        │
        ▼
Input Autofill generates entity suggestions
        │
        ▼
Response with ranked opportunities
        │
        ▼
Frontend displays Blueprint Opportunities tab
```

### 2. Blueprint Deployment Flow

```
User clicks "Deploy" on blueprint
        │
        ▼
Frontend sends POST /api/v1/blueprint-opportunities/{id}/preview
        │
        ▼
BlueprintDeployer generates preview YAML
        │
        ▼
User reviews and confirms
        │
        ▼
BlueprintDeployer calls HA Blueprint API
        │
        ▼
Automation created in Home Assistant
        │
        ▼
Automations reloaded
        │
        ▼
Success response to frontend
```

### 3. Synergy Enrichment Flow

```
Pattern Analysis Scheduler runs
        │
        ▼
Synergy Detector detects synergies
        │
        ▼
_enrich_with_blueprints() called
        │
        ▼
Blueprint Index searched for matches
        │
        ▼
Synergies enriched with blueprint metadata
        │
        ▼
Confidence boosted for good matches
        │
        ▼
Synergies stored in database
```

## Configuration

### Environment Variables

```bash
# Blueprint Index Service
BLUEPRINT_INDEX_DATABASE_URL=sqlite:///data/blueprint_index.db
BLUEPRINT_INDEX_GITHUB_TOKEN=${GITHUB_TOKEN}
BLUEPRINT_INDEX_UPDATE_INTERVAL_HOURS=24

# AI Pattern Service
BLUEPRINT_INDEX_URL=http://blueprint-index:8031

# Health Dashboard
VITE_AI_PATTERN_SERVICE_URL=http://localhost:8020
```

### Docker Compose

```yaml
blueprint-index:
  build: ./services/blueprint-index
  ports:
    - "8031:8031"
  environment:
    - DATABASE_URL=sqlite:///data/blueprint_index.db
    - GITHUB_TOKEN=${GITHUB_TOKEN}
  volumes:
    - ./data:/app/data
  networks:
    - homeiq-network
```

## Performance Considerations

### Blueprint Index
- Initial indexing: ~30 minutes for 5,000+ blueprints
- Search latency: <100ms
- Refresh interval: Every 24 hours

### Fit Score Calculation
- Per blueprint: <5ms
- Typical request (20 blueprints): <100ms

### Synergy Enrichment
- Per synergy: ~50ms (includes API call)
- Batch optimization available for large synergy sets

## Security Considerations

1. **GitHub Token**: Used for API rate limiting, stored as environment variable
2. **Blueprint Validation**: All blueprints validated before indexing
3. **Input Sanitization**: User inputs sanitized before HA API calls
4. **API Authentication**: Blueprint endpoints use standard HA token auth

## Monitoring

### Key Metrics

1. **Blueprint Index**
   - Total indexed blueprints
   - Index freshness (last update time)
   - Search latency (P50, P95, P99)

2. **Opportunity Engine**
   - Opportunities discovered per request
   - Average fit score
   - Autofill success rate

3. **Deployment**
   - Deployment success rate
   - Deployment latency
   - Fallback to YAML rate

### Health Checks

- `GET /health` on Blueprint Index (8031)
- Blueprint-related metrics in AI Pattern Service `/health`

## Future Enhancements

1. **Blueprint Rating System**: Allow users to rate blueprints after deployment
2. **Custom Blueprint Upload**: Let users contribute blueprints to the index
3. **Blueprint Version Tracking**: Track and notify about blueprint updates
4. **Multi-Home Support**: Separate blueprint recommendations per home
5. **Blueprint Analytics**: Track which blueprints are most successful

## Related Documentation

- [Event Flow Architecture](./event-flow-architecture.md)
- [Database Schema](./database-schema.md)
- [API Reference](../api/API_REFERENCE.md)
- [PATTERNS_SYNERGIES_IMPROVEMENT_RECOMMENDATIONS.md](../../services/ai-pattern-service/tests/PATTERNS_SYNERGIES_IMPROVEMENT_RECOMMENDATIONS.md)
