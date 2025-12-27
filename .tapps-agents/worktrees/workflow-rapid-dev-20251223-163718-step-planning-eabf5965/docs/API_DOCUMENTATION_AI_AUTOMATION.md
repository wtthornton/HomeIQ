# ⛔ SUPERSEDED - See API_REFERENCE.md

> **This document has been SUPERSEDED by [api/API_REFERENCE.md](api/API_REFERENCE.md#ai-automation-service)**  
> **Last Updated:** October 20, 2025  
> **Status:** Historical reference only - will be archived in next cleanup
> 
> **Please use:** [api/API_REFERENCE.md#ai-automation-service](api/API_REFERENCE.md#ai-automation-service) - AI Automation section in consolidated API reference

---

# AI Automation Service API Documentation

## Overview
The AI Automation Service provides intelligent automation suggestions for Home Assistant based on historical device usage patterns. It features conversational refinement, MQTT integration, and optimized performance.

## Base URL
```
http://localhost:8018
```

## Authentication
Currently no authentication required for development. Production deployments should implement API key authentication.

## Endpoints

### Health Check
**GET** `/health`

Returns the current health status of the AI Automation Service.

**Response:**
```json
{
  "status": "healthy",
  "service": "ai-automation-service",
  "version": "1.0.0",
  "timestamp": "2025-10-17T20:19:01.149160Z",
  "device_intelligence": {
    "devices_discovered": 0,
    "devices_processed": 0,
    "devices_skipped": 0,
    "errors": 0
  }
}
```

### Analysis Status
**GET** `/api/analysis/status`

Returns the current analysis status and pattern statistics.

**Response:**
```json
{
  "status": "ready",
  "patterns": {
    "total_patterns": 1227,
    "by_type": {
      "co_occurrence": 1217,
      "time_of_day": 10
    },
    "unique_devices": 1227,
    "avg_confidence": 0.9874154097215839
  },
  "suggestions": {
    "pending_count": 0,
    "recent": []
  }
}
```

### Run Analysis
**POST** `/api/analysis/analyze-and-suggest`

Runs the complete analysis pipeline to detect patterns and generate automation suggestions.

**Request Body:**
```json
{
  "days": 30,
  "max_suggestions": 10,
  "min_confidence": 0.7,
  "time_of_day_enabled": true,
  "co_occurrence_enabled": true
}
```

**Parameters:**
- `days` (int, 1-90): Number of days to analyze
- `max_suggestions` (int, 1-50): Maximum suggestions to generate
- `min_confidence` (float, 0.0-1.0): Minimum pattern confidence threshold
- `time_of_day_enabled` (bool): Enable time-of-day pattern detection
- `co_occurrence_enabled` (bool): Enable co-occurrence pattern detection

**Response:**
```json
{
  "success": true,
  "message": "Successfully generated 10 automation suggestions",
  "data": {
    "summary": {
      "events_analyzed": 50000,
      "patterns_detected": 1227,
      "suggestions_generated": 10,
      "suggestions_failed": 0
    },
    "patterns": {
      "total": 1227,
      "by_type": {
        "time_of_day": 10,
        "co_occurrence": 1217
      },
      "top_confidence": 0.99,
      "avg_confidence": 0.987
    },
    "suggestions": [
      {
        "id": 1,
        "title": "Evening Light Automation",
        "category": "lighting",
        "priority": "high",
        "confidence": 0.95,
        "pattern_type": "time_of_day"
      }
    ],
    "openai_usage": {
      "total_tokens": 15000,
      "input_tokens": 12000,
      "output_tokens": 3000,
      "estimated_cost_usd": 0.0025,
      "model": "gpt-4o-mini"
    },
    "performance": {
      "total_duration_seconds": 180.5,
      "phase1_fetch_seconds": 45.2,
      "phase2_detect_seconds": 90.3,
      "phase3_store_seconds": 15.1,
      "phase4_generate_seconds": 29.9,
      "avg_time_per_suggestion": 2.99
    },
    "time_range": {
      "start": "2025-09-17T20:19:01.149160Z",
      "end": "2025-10-17T20:19:01.149160Z",
      "days": 30
    }
  }
}
```

### Generate Suggestion (Conversational)
**POST** `/api/v1/suggestions/generate`

Generates a new automation suggestion using the conversational flow.

**Request Body:**
```json
{
  "pattern_id": 1,
  "pattern_type": "time_of_day",
  "device_id": "light.living_room",
  "metadata": {
    "hour": 18,
    "confidence": 0.85
  }
}
```

**Response:**
```json
{
  "suggestion_id": "suggestion-1",
  "description": "Turn on the living room light at 6:00 PM",
  "trigger_summary": "Time-based trigger at 6:00 PM",
  "action_summary": "Turn on living room light",
  "devices_involved": ["light.living_room"],
  "confidence": 0.85,
  "status": "draft",
  "created_at": "2025-10-17T20:19:01.149160Z"
}
```

### Refine Suggestion
**POST** `/api/v1/suggestions/{suggestion_id}/refine`

Refines an automation suggestion based on user input.

**Path Parameters:**
- `suggestion_id`: The suggestion ID (e.g., "suggestion-1")

**Request Body:**
```json
{
  "user_input": "Make it blue and only on weekdays",
  "conversation_context": true
}
```

**Response:**
```json
{
  "suggestion_id": "suggestion-1",
  "updated_description": "Turn on the living room light in blue at 6:00 PM on weekdays only",
  "changes_detected": ["Added color preference", "Added weekday restriction"],
  "validation": {
    "ok": true,
    "messages": ["Changes applied successfully"],
    "warnings": [],
    "alternatives": []
  },
  "refinement_count": 1,
  "status": "refining"
}
```

### Approve and Generate YAML
**POST** `/api/v1/suggestions/{suggestion_id}/approve`

Approves a suggestion and generates the final Home Assistant YAML automation.

**Path Parameters:**
- `suggestion_id`: The suggestion ID (e.g., "suggestion-1")

**Request Body:**
```json
{
  "final_description": "Turn on the living room light in blue at 6:00 PM on weekdays only"
}
```

**Response:**
```json
{
  "suggestion_id": "suggestion-1",
  "status": "yaml_generated",
  "automation_yaml": "alias: 'Living Room Light - Weekday Blue'\ntrigger:\n  - platform: time\n    at: '18:00:00'\ncondition:\n  - condition: time\n    weekday:\n      - mon\n      - tue\n      - wed\n      - thu\n      - fri\naction:\n  - service: light.turn_on\n    target:\n      entity_id: light.living_room\n    data:\n      color_name: blue",
  "yaml_validation": {
    "syntax_valid": true,
    "safety_score": 95,
    "issues": []
  },
  "ready_to_deploy": true,
  "approved_at": "2025-10-17T20:19:01.149160Z"
}
```

### Get Device Capabilities
**GET** `/api/v1/suggestions/devices/{device_id}/capabilities`

Returns the capabilities of a specific device.

**Path Parameters:**
- `device_id`: The device ID (e.g., "light.living_room")

**Response:**
```json
{
  "device_id": "light.living_room",
  "capabilities": {
    "supports_color": true,
    "supports_brightness": true,
    "supports_color_temp": true,
    "supports_effects": false,
    "max_brightness": 255,
    "supported_colors": ["red", "green", "blue", "white", "yellow", "purple", "orange", "pink"]
  },
  "last_updated": "2025-10-17T20:19:01.149160Z"
}
```

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid suggestion ID format: invalid-id"
}
```

### 404 Not Found
```json
{
  "detail": "Suggestion not found"
}
```

### 408 Request Timeout
```json
{
  "detail": "Analysis timed out after 300 seconds. Try reducing the analysis scope."
}
```

### 500 Internal Server Error
```json
{
  "detail": "Analysis pipeline failed: Database connection error"
}
```

## Rate Limiting

### Rate Limit Configuration
- **External IPs**: 600 requests per minute, 10,000 per hour
- **Internal Docker Network** (172.x.x.x, 192.168.x.x, 10.x.x.x): 2,000 requests per minute
- **Health Endpoints** (`/health`, `/api/health`): **Exempt** from rate limiting
- Rate limiting is per-IP address using token bucket algorithm

### Refinement Limits
- Maximum 10 refinements per suggestion
- Rate limit: 1 refinement per 5 seconds
- Exceeding limits returns 429 Too Many Requests

### Analysis Limits
- Maximum 1 analysis per 5 minutes
- Large analysis requests (90 days) limited to 1 per hour
- Concurrent analysis requests are queued

### Rate Limit Headers
When rate limits are applied, the following headers are included:
```
X-RateLimit-Limit: 600
X-RateLimit-Remaining: 550
X-RateLimit-Reset: 1640995200
Retry-After: 60
```

## MQTT Integration

### Notifications
The service publishes MQTT notifications for:
- Analysis completion
- New suggestions created
- Suggestion status changes

**Topics:**
- `ha-ai/analysis/complete` - Analysis completion
- `ha-ai/suggestions/new` - New suggestions
- `ha-ai/suggestions/updated` - Suggestion updates

### Device Intelligence
The service subscribes to MQTT topics for:
- Device capability updates
- New device discovery
- Feature availability changes

## Performance Metrics

### Analysis Performance
- **Small datasets** (< 50k events): 1-2 minutes
- **Large datasets** (50k+ events): 2-3 minutes
- **Memory usage**: ~900MB average
- **Success rate**: 100% (with timeout handling)

### API Performance
- **Health check**: < 50ms
- **Status endpoint**: < 100ms
- **Suggestion generation**: 2-5 seconds
- **Refinement**: 1-3 seconds
- **YAML generation**: 3-8 seconds

## Configuration

### Environment Variables
```bash
# MQTT Configuration
MQTT_BROKER=192.168.1.86
MQTT_PORT=1883
MQTT_USERNAME=tapphousemqtt
MQTT_PASSWORD=your_password

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key

# Analysis Configuration
ANALYSIS_SCHEDULE=0 3 * * *  # 3:00 AM daily
LOG_LEVEL=INFO
```

### Docker Configuration
```yaml
services:
  ai-automation-service:
    image: homeiq-ai-automation-service:latest
    ports:
      - "8018:8018"
    environment:
      - MQTT_BROKER=192.168.1.86
      - MQTT_USERNAME=tapphousemqtt
      - MQTT_PASSWORD=your_password
      - OPENAI_API_KEY=your_api_key
    depends_on:
      - data-api
      - influxdb
```

## Troubleshooting

### Common Issues

1. **MQTT Connection Failed**
   - Check MQTT broker accessibility
   - Verify credentials
   - Check network connectivity

2. **Analysis Timeout**
   - Reduce analysis scope (fewer days)
   - Check system resources
   - Verify data availability

3. **OpenAI API Errors**
   - Check API key validity
   - Verify rate limits
   - Check network connectivity

### Debugging

1. **Check Service Logs**
   ```bash
   docker logs ai-automation-service
   ```

2. **Test MQTT Connection**
   ```bash
   docker exec ai-automation-service python -c "
   import paho.mqtt.client as mqtt
   client = mqtt.Client()
   client.username_pw_set('username', 'password')
   client.connect('192.168.1.86', 1883, 60)
   print('MQTT connection test:', client.is_connected())
   "
   ```

3. **Test API Endpoints**
   ```bash
   curl http://localhost:8018/health
   curl http://localhost:8018/api/analysis/status
   ```

## Status: ✅ Production Ready

The AI Automation Service is fully operational with:
- ✅ Reliable MQTT connectivity
- ✅ Optimized analysis process
- ✅ Enhanced error handling
- ✅ Complete conversational flow
- ✅ Production-ready stability
