# Automation Suggestions Generation Flow

**Date:** January 9, 2026  
**Status:** Current Implementation Analysis

## Overview

This document explains how automation suggestions are generated and converted into Home Assistant automations based on the current system implementation.

## Flow Diagram

```
Home Assistant Events (InfluxDB)
        ↓
Data API (Port 8006)
        ↓
Suggestion Service (ai-automation-service-new)
  ├─ Fetches events (last 30 days, up to 10,000 events)
  ├─ Batches events (100 events per suggestion)
  ├─ Sends to OpenAI GPT-4o-mini
  └─ Stores in database with status="draft"
        ↓
UI (ai-automation-ui, Port 3001)
  ├─ Displays suggestions with confidence scores
  ├─ User can edit, approve, or reject
  └─ On approval: generates YAML
        ↓
YAML Generation Service
  ├─ Converts description → HomeIQ JSON
  ├─ Validates entities
  └─ Converts JSON → Home Assistant YAML
        ↓
Home Assistant
  └─ Automation deployed and active
```

## Step-by-Step Process

### 1. Suggestion Generation (`POST /api/suggestions/refresh`)

**Service:** `ai-automation-service-new` (Port 8025/8036)  
**Code:** `services/ai-automation-service-new/src/services/suggestion_service.py`

**Process:**
1. **Fetch Events**: Retrieves up to 10,000 events from Data API (last 30 days)
   - Endpoint: `GET /api/events?days=30&limit=10000`
   - Events include: entity_id, state, timestamp, attributes

2. **Batch Processing**: Groups events into batches of 100
   - Each batch becomes one suggestion
   - Formula: `max_suggestions = len(events) // 100`

3. **OpenAI Generation**: For each batch:
   - Sends event data to OpenAI GPT-4o-mini
   - Prompt: "Generate automation description from these events"
   - Returns: Natural language description of automation pattern

4. **Database Storage**: Creates `Suggestion` record:
   ```python
   Suggestion(
       title=f"Automation Suggestion {i + 1}",
       description=<openai_generated_description>,
       status="draft",
       confidence_score=None  # ⚠️ Currently not set during generation
   )
   ```

**Current Limitations:**
- ❌ `confidence_score` is not set (defaults to NULL)
- ❌ Uses raw events instead of detected patterns (Epic 39.13 - pending)
- ❌ No automatic scheduling (requires APScheduler integration)

### 2. Suggestion Display (UI)

**Service:** `ai-automation-ui` (Port 3001)  
**Code:** `services/ai-automation-ui/src/pages/ConversationalDashboard.tsx`

**Process:**
1. **Fetch Suggestions**: `GET /api/suggestions/list?status=draft&limit=50`
2. **API Response**: Includes `confidence` field (mapped from `confidence_score`, defaults to 0.5 if null)
3. **Display**: Shows suggestion cards with:
   - Title and description
   - Confidence badge (0-100%)
   - Category tag (convenience, energy, security, comfort)
   - Status badge (New, Editing, Ready, Deployed)
   - Action buttons (Approve & Create, Edit, Not Interested)

**Fixed Issues (January 9, 2026):**
- ✅ Confidence now defaults to 0.5 (50%) if `confidence_score` is NULL
- ✅ UI handles null/undefined confidence gracefully (no more NaN%)
- ✅ API includes confidence in response

### 3. YAML Generation (On Approval)

**Service:** `ai-automation-service-new`  
**Code:** `services/ai-automation-service-new/src/services/yaml_generation_service.py`

**Process:**
1. **User Approval**: User clicks "APPROVE & CREATE" button
2. **HomeIQ JSON Generation**: 
   - Description → OpenAI → HomeIQ JSON format
   - Includes: triggers, actions, conditions, metadata
   - Validates against HomeIQ schema

3. **Entity Validation**:
   - Fetches entity context from Home Assistant
   - Validates all entity_ids exist
   - Fails if invalid entities found

4. **YAML Conversion**:
   - HomeIQ JSON → AutomationSpec (intermediate format)
   - AutomationSpec → Home Assistant YAML
   - Uses version-aware renderer (Home Assistant 2025.10+ format)

5. **Database Update**:
   ```python
   suggestion.automation_yaml = <generated_yaml>
   suggestion.status = "yaml_generated"
   ```

### 4. Deployment to Home Assistant

**Process:**
1. **YAML Validation**: Validates YAML syntax and structure
2. **Home Assistant API**: POSTs to Home Assistant `/api/config/automation/config/{automation_id}`
3. **Database Update**:
   ```python
   suggestion.status = "deployed"
   suggestion.ha_automation_id = <automation_id>
   suggestion.deployed_at = <timestamp>
   ```

## Confidence Score Calculation

**Current State:**
- ⚠️ **Not calculated during generation** - `confidence_score` defaults to NULL
- ✅ **UI displays 50%** as default when NULL (fixed January 9, 2026)
- ⚠️ **Should be calculated** based on:
  - Pattern strength (occurrences, frequency)
  - Entity availability
  - Historical success rate
  - User preferences

**Database Field:**
- Column: `confidence_score` (Float, nullable)
- Location: `services/ai-automation-service-new/src/database/models.py:34`

**API Mapping:**
- Field: `confidence` (0.0-1.0, defaults to 0.5 if NULL)
- Location: `services/ai-automation-service-new/src/services/suggestion_service.py:197`

## How Suggestions Become Automations

### Current Flow (Approval-Based)

1. **Suggestion Created**: Generated from events, stored with status="draft"
2. **User Reviews**: Sees suggestion in UI, can edit description
3. **User Approves**: Clicks "APPROVE & CREATE"
4. **YAML Generated**: Description → HomeIQ JSON → Home Assistant YAML
5. **Deployed**: YAML sent to Home Assistant API
6. **Status Updated**: suggestion.status = "deployed"

### Future Flow (Pattern-Based - Epic 39.13)

**Planned Enhancement:**
1. **Pattern Detection**: ai-pattern-service detects patterns (time-of-day, co-occurrence, etc.)
2. **Pattern → Suggestion**: Patterns include confidence scores, metadata
3. **Better Quality**: Suggestions based on detected patterns (not raw events)
4. **Higher Confidence**: Confidence scores from pattern analysis

## API Endpoints

### Suggestion Management

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/suggestions/list` | GET | List suggestions with filtering |
| `/api/suggestions/generate` | POST | Generate suggestions from events |
| `/api/suggestions/refresh` | POST | Manual trigger (calls generate) |
| `/api/suggestions/{id}/json` | GET | Get HomeIQ JSON for suggestion |
| `/api/suggestions/{id}/rebuild-json` | POST | Rebuild JSON from description/YAML |

### YAML Generation

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/suggestions/{id}/yaml` | GET | Get generated YAML |
| `/api/suggestions/{id}/generate-yaml` | POST | Generate YAML from description |

## Data Models

### Suggestion (Database)

```python
class Suggestion:
    id: int
    title: str
    description: str
    status: str  # draft, refining, yaml_generated, deployed, rejected
    confidence_score: float | None  # 0.0-1.0
    automation_json: dict | None  # HomeIQ JSON format
    automation_yaml: str | None  # Home Assistant YAML
    ha_automation_id: str | None  # After deployment
    created_at: datetime
    updated_at: datetime
    deployed_at: datetime | None
```

### Suggestion (API Response)

```typescript
interface Suggestion {
  id: number
  title: string
  description: string
  status: 'draft' | 'refining' | 'yaml_generated' | 'deployed' | 'rejected'
  confidence: number  // 0.0-1.0, defaults to 0.5 if confidence_score is NULL
  category?: 'energy' | 'comfort' | 'security' | 'convenience'
  automation_yaml?: string | null
  created_at?: string
  updated_at?: string
  deployed_at?: string | null
  ha_automation_id?: string | null
}
```

## Current Issues & Fixes

### ✅ Fixed: NaN% Confidence Display (January 9, 2026)

**Problem:** UI displayed "NaN% confident" because:
- API didn't return `confidence` field
- `confidence_score` was NULL in database
- UI tried to calculate `Math.round(undefined * 100)` = NaN

**Fix:**
1. **API**: Added `confidence` field to response, maps from `confidence_score`, defaults to 0.5 if NULL
2. **UI**: Added nullish coalescing operator (`??`) to handle null/undefined gracefully

**Files Changed:**
- `services/ai-automation-service-new/src/services/suggestion_service.py` (lines 197, 236)
- `services/ai-automation-ui/src/components/ConversationalSuggestionCard.tsx` (line 348)

### ⚠️ Pending: Confidence Score Calculation

**Problem:** `confidence_score` is not calculated during suggestion generation.

**Future Solution:**
- Calculate based on pattern strength (if using patterns)
- Use occurrence frequency
- Consider entity availability
- Factor in user preferences

## References

- **Service Analysis**: `implementation/analysis/AUTOMATION_SUGGESTIONS_SERVICE_ANALYSIS.md`
- **Database Models**: `services/ai-automation-service-new/src/database/models.py`
- **Suggestion Service**: `services/ai-automation-service-new/src/services/suggestion_service.py`
- **YAML Generation**: `services/ai-automation-service-new/src/services/yaml_generation_service.py`
- **UI Component**: `services/ai-automation-ui/src/components/ConversationalSuggestionCard.tsx`
