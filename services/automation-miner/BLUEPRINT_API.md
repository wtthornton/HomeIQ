# Blueprint API Documentation

## Overview

The Automation Miner service now properly stores and provides access to Home Assistant automation blueprints. Blueprints are reusable automation templates with configurable inputs that can be filled with user-specific entities.

## Blueprint Storage

### What Changed

**Before:** Blueprint metadata (`_blueprint_metadata`, `_blueprint_variables`, `_blueprint_devices`) was parsed but not stored in the database.

**After:** When a blueprint is detected during parsing, all blueprint-specific metadata is now stored in the `extra_metadata` field of the `community_automations` table.

### Storage Format

Blueprints are identified by the presence of `_blueprint_metadata` in the `extra_metadata` JSON field:

```json
{
  "tags": [...],
  "views": 1234,
  "author": "...",
  "has_yaml": true,
  "_blueprint_metadata": {
    "name": "Motion-Activated Light",
    "description": "Turn on lights when motion detected",
    "domain": "automation"
  },
  "_blueprint_variables": {
    "motion_sensor": {
      "domain": "binary_sensor",
      "device_class": "motion",
      "name": "Motion Sensor"
    },
    "target_light": {
      "domain": "light",
      "name": "Light to Control"
    }
  },
  "_blueprint_devices": ["binary_sensor", "light"]
}
```

## API Endpoints

### 1. Search Blueprints

**Endpoint:** `GET /api/automation-miner/corpus/blueprints`

**Description:** Search for Home Assistant automation blueprints with optional filters.

**Query Parameters:**
- `device` (optional): Filter by device type (e.g., `light`, `motion_sensor`)
- `integration` (optional): Filter by integration (e.g., `mqtt`, `zigbee2mqtt`)
- `use_case` (optional): Filter by use case (`energy`, `comfort`, `security`, `convenience`)
- `min_quality` (optional, default: 0.7): Minimum quality score (0.0-1.0)
- `limit` (optional, default: 50): Maximum results (1-500)

**Example Request:**
```bash
curl "http://localhost:8029/api/automation-miner/corpus/blueprints?device=light&use_case=comfort&min_quality=0.8"
```

**Example Response:**
```json
{
  "automations": [
    {
      "id": 1,
      "title": "Motion-Activated Light",
      "description": "Turn on lights when motion detected",
      "devices": ["binary_sensor", "light"],
      "use_case": "comfort",
      "quality_score": 0.85,
      "metadata": {
        "_blueprint_metadata": {
          "name": "Motion-Activated Light",
          "domain": "automation"
        },
        "_blueprint_variables": {
          "motion_sensor": {
            "domain": "binary_sensor",
            "device_class": "motion"
          }
        }
      }
    }
  ],
  "count": 1,
  "filters": {
    "device": "light",
    "use_case": "comfort",
    "min_quality": 0.8,
    "limit": 50
  }
}
```

### 2. Get Corpus Statistics (Updated)

**Endpoint:** `GET /api/automation-miner/corpus/stats`

**Description:** Get corpus statistics including blueprint count.

**Response Fields:**
- `total`: Total number of automations
- `avg_quality`: Average quality score
- `device_count`: Number of unique device types
- `integration_count`: Number of unique integrations
- `blueprint_count`: **NEW** - Number of blueprints in the corpus
- `by_use_case`: Breakdown by use case
- `by_complexity`: Breakdown by complexity
- `last_crawl_time`: Last crawl timestamp

**Example Response:**
```json
{
  "total": 2143,
  "avg_quality": 0.76,
  "device_count": 52,
  "integration_count": 35,
  "blueprint_count": 856,
  "by_use_case": {
    "energy": 450,
    "comfort": 890,
    "security": 780,
    "convenience": 423
  },
  "by_complexity": {
    "low": 1200,
    "medium": 980,
    "high": 363
  },
  "last_crawl_time": "2025-11-21T10:00:00"
}
```

## Usage Examples

### Find All Blueprints for Lights

```bash
curl "http://localhost:8029/api/automation-miner/corpus/blueprints?device=light"
```

### Find High-Quality Security Blueprints

```bash
curl "http://localhost:8029/api/automation-miner/corpus/blueprints?use_case=security&min_quality=0.8"
```

### Get Blueprint Count

```bash
curl "http://localhost:8029/api/automation-miner/corpus/stats" | jq '.blueprint_count'
```

## Integration with AI Automation Service

### Current Status

Blueprints are now properly stored and queryable, but **not yet integrated** into the AI automation service's suggestion generation.

### Future Integration

The blueprint engine implementation plan (`implementation/analysis/HA_BLUEPRINT_ENGINE_IMPLEMENTATION_PLAN.md`) outlines how blueprints can be used:

1. **Blueprint Matching**: Match user queries to appropriate blueprints
2. **Input Filling**: Fill blueprint inputs with user's actual entities
3. **YAML Generation**: Generate valid HA YAML from blueprints
4. **Hybrid Approach**: Combine AI suggestions with blueprint templates

## Notes

- **Re-crawling Required**: Existing automations in the database don't have blueprint metadata. A fresh crawl will populate blueprint metadata for newly discovered blueprints.
- **Blueprint Detection**: Blueprints are detected by the presence of a `blueprint:` key in the YAML structure.
- **Metadata Preservation**: All blueprint metadata is preserved, including input definitions, selectors, and variable mappings.

