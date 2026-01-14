# Phase 2: Suggestion Generation Implementation Plan

**Date:** January 14, 2026  
**Feature:** Device-Based Automation Suggestions - Phase 2  
**Status:** 🚧 Planning

## Overview

Phase 2 implements the suggestion generation service/endpoint and the suggestion display UI. This phase involves both backend (suggestion generation) and frontend (suggestion cards) work.

## Requirements Summary

### Backend Requirements (FR-1.2.2)

**New Endpoint:** `POST /api/v1/chat/device-suggestions`

**Input:**
```json
{
  "device_id": "device_id_string",
  "conversation_id": "optional_conversation_id",
  "context": {
    "include_synergies": true,
    "include_blueprints": true,
    "include_sports": true,
    "include_weather": true
  }
}
```

**Output:**
```json
{
  "suggestions": [
    {
      "suggestion_id": "uuid",
      "title": "Suggestion Title",
      "description": "Detailed description",
      "automation_preview": {
        "trigger": "Home Assistant trigger description",
        "action": "Home Assistant action description",
        "yaml_preview": "Optional: Preview of Home Assistant YAML structure"
      },
      "data_sources": {
        "synergies": ["synergy_id_1"],
        "blueprints": ["blueprint_id_1"],
        "sports": true,
        "weather": true,
        "device_capabilities": true
      },
      "home_assistant_entities": {
        "trigger_entities": ["binary_sensor.motion_office"],
        "action_entities": ["switch.office_light_switch"],
        "condition_entities": []
      },
      "home_assistant_services": {
        "actions": ["switch.turn_on"],
        "validated": true
      },
      "confidence_score": 0.85,
      "quality_score": 0.78,
      "enhanceable": true,
      "home_assistant_compatible": true
    }
  ],
  "device_context": {
    "device_id": "...",
    "capabilities": [...],
    "related_synergies": [...],
    "compatible_blueprints": [...],
    "home_assistant_entities": [...],
    "home_assistant_services": [...]
  }
}
```

### Multi-Source Data Aggregation (FR-1.2.1)

1. **Device Attributes** - From `data-api` (device metadata, capabilities)
2. **Design Data** - Device features, community ratings
3. **Synergies** - From `ai-pattern-service` (device interaction patterns)
4. **Blueprints** - From `blueprint-suggestion-service` (Home Assistant automation templates)
5. **Sports Data** - From `sports-api` (Team Tracker sensors)
6. **Weather Data** - From `weather-api` (current conditions, forecasts)
7. **3rd Party Data** - Additional external data sources

### Suggestion Ranking (FR-1.2.3)

- Prioritize suggestions with high confidence scores (≥0.7)
- Prioritize suggestions validated by patterns (pattern_support_score ≥0.7)
- Prioritize suggestions with blueprint matches (blueprint_fit_score ≥0.6)
- Filter out suggestions that exceed device capabilities
- Limit to 3-5 top suggestions
- Include diversity (different trigger types, different use cases)

### Frontend Requirements (FR-1.3.1)

**Suggestion Cards UI Component:**
- Display suggestion title and description
- Show automation preview (trigger → action summary)
- Display data source indicators (synergy, blueprint, sports, weather icons)
- Show confidence/quality scores
- "Enhance" button to start chat conversation
- "Create" button to directly create automation (optional)

## Implementation Approach

### Option 1: Full Implementation (Recommended)

1. **Backend Endpoint** (ha-ai-agent-service)
   - Create new endpoint `/api/v1/chat/device-suggestions`
   - Implement data aggregation service
   - Implement suggestion generation logic
   - Implement ranking algorithm
   - Return formatted suggestions

2. **Frontend UI** (ai-automation-ui)
   - Create `DeviceSuggestions.tsx` component
   - Display suggestion cards
   - Integrate with backend endpoint
   - Add "Enhance" and "Create" buttons

### Option 2: Incremental Implementation

1. **Frontend First** (Can start now)
   - Create `DeviceSuggestions.tsx` component with mock data
   - Display suggestion cards UI
   - Add "Enhance" button (connects to existing chat)

2. **Backend Later**
   - Create backend endpoint
   - Connect frontend to real endpoint
   - Replace mock data with real suggestions

## Recommended Approach

**Start with Frontend UI (Option 2)** because:
- UI can be built and tested independently
- Can use mock data initially
- "Enhance" button can connect to existing chat functionality
- Backend can be built in parallel or after UI is ready

## Implementation Steps

### Step 1: Frontend Suggestion Cards UI (Start Here)

1. Create `DeviceSuggestions.tsx` component
2. Create suggestion card component
3. Add mock data structure matching backend API format
4. Display suggestion cards with:
   - Title and description
   - Automation preview
   - Data source indicators
   - Confidence/quality scores
   - "Enhance" button (connects to chat)
   - "Create" button (optional, connects to automation creation)

### Step 2: Backend Endpoint Structure

1. Create endpoint route in `ha-ai-agent-service`
2. Define request/response schemas
3. Create service for data aggregation
4. Implement suggestion generation logic
5. Implement ranking algorithm

### Step 3: Data Aggregation Service

1. Device data (data-api)
2. Synergies (ai-pattern-service)
3. Blueprints (blueprint-suggestion-service)
4. Sports data (sports-api)
5. Weather data (weather-api)
6. Aggregate and combine data

### Step 4: Suggestion Generation Logic

1. Generate suggestions from aggregated data
2. Validate Home Assistant entities/services
3. Generate automation previews
4. Calculate confidence/quality scores

### Step 5: Integration

1. Connect frontend to backend endpoint
2. Replace mock data with real suggestions
3. Test end-to-end flow

## Files to Create/Modify

### Frontend (ai-automation-ui)
- `src/components/ha-agent/DeviceSuggestions.tsx` (new)
- `src/components/ha-agent/SuggestionCard.tsx` (new)
- `src/services/deviceSuggestionsApi.ts` (new)
- `src/pages/HAAgentChat.tsx` (modify - integrate suggestions display)

### Backend (ha-ai-agent-service)
- `src/api/device_suggestions_endpoints.py` (new)
- `src/services/device_suggestion_service.py` (new)
- `src/services/device_data_aggregator.py` (new)
- `src/models/device_suggestion.py` (new schemas)
- `src/main.py` (modify - register new router)

## Next Steps

1. ✅ Create Phase 2 implementation plan (this document)
2. ⏭️ Start with frontend UI (DeviceSuggestions component)
3. ⏭️ Create backend endpoint structure
4. ⏭️ Implement data aggregation
5. ⏭️ Implement suggestion generation
6. ⏭️ Implement ranking algorithm
7. ⏭️ Connect frontend to backend
8. ⏭️ Test and refine

## Notes

- Frontend can be built with mock data first
- Backend requires integration with multiple services
- Suggestion generation should leverage existing LLM capabilities in ha-ai-agent-service
- All suggestions must generate valid Home Assistant 2025.10+ YAML
- Ranking algorithm should balance quality, diversity, and relevance
