# Step 3: Architecture Design - Proactive Suggestions Device Validation

## System Overview

### Current Architecture (Before Fix)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    proactive-agent-service                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌───────────────────┐    ┌──────────────────────┐                 │
│  │ ContextAnalysis   │───▶│ AIPromptGeneration   │                 │
│  │ Service           │    │ Service              │                 │
│  │                   │    │                      │                 │
│  │ - Weather         │    │ - Truncated context  │◄─── PROBLEM:    │
│  │ - Sports          │    │   (3000 chars)       │     No device   │
│  │ - Energy          │    │ - Generic insights   │     validation  │
│  │ - Patterns        │    │ - Weak prompt        │                 │
│  └───────────────────┘    └──────────┬───────────┘                 │
│                                      │                              │
│                                      ▼                              │
│                           ┌──────────────────────┐                 │
│                           │ OpenAI GPT-4o-mini   │                 │
│                           │                      │                 │
│                           │ ⚠️ Can hallucinate   │                 │
│                           │   non-existent       │                 │
│                           │   devices            │                 │
│                           └──────────┬───────────┘                 │
│                                      │                              │
│                                      ▼                              │
│                           ┌──────────────────────┐                 │
│                           │ SuggestionStorage    │                 │
│                           │ Service              │                 │
│                           │                      │                 │
│                           │ ❌ No validation     │                 │
│                           └──────────────────────┘                 │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### New Architecture (After Fix)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    proactive-agent-service                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌───────────────────┐    ┌──────────────────────┐                 │
│  │ ContextAnalysis   │───▶│ AIPromptGeneration   │                 │
│  │ Service           │    │ Service              │                 │
│  │                   │    │                      │                 │
│  │ ✅ Device-aware   │    │ ✅ Full device list  │                 │
│  │    insights only  │    │ ✅ Strong prompt     │                 │
│  └───────────────────┘    │ ✅ Device constraints│                 │
│                           └──────────┬───────────┘                 │
│          ┌───────────────────────────┤                              │
│          │                           │                              │
│          ▼                           ▼                              │
│  ┌───────────────────┐    ┌──────────────────────┐                 │
│  │ DeviceInventory   │    │ OpenAI GPT-4o-mini   │                 │
│  │ Client            │    │                      │                 │
│  │                   │    │ Constrained by:      │                 │
│  │ - Get all devices │    │ - Explicit list      │                 │
│  │ - Cache inventory │    │ - Strong prompt      │                 │
│  └─────────┬─────────┘    └──────────┬───────────┘                 │
│            │                         │                              │
│            │    ┌────────────────────┘                              │
│            │    │                                                   │
│            ▼    ▼                                                   │
│  ┌───────────────────────────────────────────────┐                 │
│  │ NEW: DeviceValidationService                  │                 │
│  │                                               │                 │
│  │ - validate_suggestion_devices()               │                 │
│  │ - Extract device names from text              │                 │
│  │ - Check against inventory                     │                 │
│  │ - Reject invalid suggestions                  │                 │
│  └───────────────────────┬───────────────────────┘                 │
│                          │                                          │
│                          ▼                                          │
│  ┌───────────────────────────────────────────────┐                 │
│  │ SuggestionStorage Service                     │                 │
│  │                                               │                 │
│  │ ✅ Only validated suggestions stored          │                 │
│  │ ✅ Invalid reports tracking                   │                 │
│  └───────────────────────────────────────────────┘                 │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Component Design

### 1. DeviceValidationService (NEW)

**Purpose:** Validates that suggestions only reference devices that exist in Home Assistant.

**Location:** `services/proactive-agent-service/src/services/device_validation_service.py`

**Responsibilities:**
- Fetch device inventory from ha-ai-agent-service
- Cache device inventory (5-minute TTL)
- Extract device names from suggestion text
- Validate device existence
- Return validation result with reasons

**Interface:**
```python
class DeviceValidationService:
    async def get_device_inventory(self) -> list[dict]
    async def validate_suggestion(self, suggestion_text: str) -> ValidationResult
    def extract_device_mentions(self, text: str) -> list[str]
    async def has_device_type(self, device_type: str) -> bool
```

### 2. AIPromptGenerationService (MODIFIED)

**Changes:**
- Add `_get_device_inventory()` method
- Update `_build_llm_context()` to include explicit device list
- Update `SUGGESTION_SYSTEM_PROMPT` with device constraints
- Add device validation before returning suggestions

### 3. ContextAnalysisService (MODIFIED)

**Changes:**
- Remove generic device-type insights (line 132)
- Add device-aware insight generation
- Pass device inventory to insight generators

### 4. SuggestionStorageService (MODIFIED)

**Changes:**
- Add `InvalidSuggestionReport` model
- Add `report_invalid_suggestion()` method
- Add `get_invalid_reports()` method

### 5. Suggestions API (MODIFIED)

**New Endpoints:**
- `POST /api/v1/suggestions/{id}/report` - Report invalid suggestion
- `GET /api/v1/suggestions/reports` - Get invalid reports (admin)

## Data Flow

### Suggestion Generation Flow (After Fix)

```
1. Scheduler triggers generation
   │
2. ContextAnalysisService.analyze_all_context()
   │  ├── Weather data
   │  ├── Sports data  
   │  ├── Energy data
   │  └── Historical patterns
   │  └── ✅ Device-aware insights only
   │
3. AIPromptGenerationService.generate_prompts()
   │  ├── ✅ Fetch full device inventory
   │  ├── ✅ Build context with explicit device list
   │  ├── ✅ Use enhanced system prompt
   │  └── Call OpenAI
   │
4. DeviceValidationService.validate_suggestion()
   │  ├── Extract device mentions from text
   │  ├── Check each against inventory
   │  └── ✅ Reject if invalid devices found
   │
5. SuggestionStorageService.create_suggestion()
   │  └── Store only validated suggestions
   │
6. HAAgentClient.send_message()
   └── Send to HA AI Agent Service
```

## Database Changes

### New Table: invalid_suggestion_reports

```sql
CREATE TABLE invalid_suggestion_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    suggestion_id INTEGER NOT NULL,
    reason TEXT,
    reported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_feedback TEXT,
    FOREIGN KEY (suggestion_id) REFERENCES suggestions(id)
);
```

## API Changes

### New Endpoint: Report Invalid Suggestion

```
POST /api/v1/suggestions/{id}/report
Content-Type: application/json

{
    "reason": "device_not_found",
    "feedback": "I don't have a Smart Humidifier"
}

Response: 200 OK
{
    "success": true,
    "report_id": 123
}
```

## Performance Considerations

1. **Device Inventory Caching:** 5-minute TTL to avoid repeated API calls
2. **Validation Latency:** Target <100ms per suggestion
3. **Batch Validation:** Validate all suggestions in parallel when possible

## Error Handling

1. **Device Inventory Unavailable:** Skip validation, log warning, proceed with generation
2. **Validation Timeout:** Skip validation, log warning, proceed with storage
3. **Invalid Suggestion:** Log rejection reason, do not store, continue with next

---
*Generated by TappsCodingAgents Simple Mode - Step 3: @architect *design*
