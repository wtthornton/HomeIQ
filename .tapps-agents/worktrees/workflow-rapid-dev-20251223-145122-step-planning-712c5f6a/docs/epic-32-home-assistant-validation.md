# Epic 32: Home Assistant Configuration Validation & Suggestions

**Status:** 📋 Planning  
**Priority:** High  
**Epic Owner:** TBD  
**Created:** December 4, 2025  
**Related Issues:** Office Lights Automation Review (OFFICE_LIGHTS_AUTOMATION_REVIEW.md)

---

## Executive Summary

Create a comprehensive validation page that checks Home Assistant configuration against best practices and suggests fixes for common issues, particularly area assignments. This will help users identify and resolve configuration problems like `light.hue_office_back_left` not being assigned to the correct area.

---

## Problem Statement

### Current Issues

1. **Missing Area Assignments**: Many entities have `area_id: null` in the database, causing:
   - AI automation agent to select wrong lights (e.g., office automation includes hallway lights)
   - Area-based filtering to fail
   - Poor automation accuracy

2. **No Validation Tools**: Users have no way to:
   - Identify misconfigured entities
   - See suggestions for fixing area assignments
   - Validate Home Assistant setup against best practices

3. **Manual Configuration Required**: Users must manually check and fix area assignments in Home Assistant UI, which is:
   - Time-consuming
   - Error-prone
   - Not discoverable

### Impact

- **User Experience**: Frustration when automations don't work as expected
- **System Reliability**: Incorrect automations due to wrong entity selection
- **Maintenance Burden**: Manual configuration checks required

---

## Goals & Success Criteria

### Primary Goals

1. **Validation Page**: Create a dedicated page that validates Home Assistant configuration
2. **Area Assignment Detection**: Identify entities with missing or incorrect area assignments
3. **Smart Suggestions**: Provide actionable suggestions based on entity names and patterns
4. **One-Click Fixes**: Allow users to apply fixes directly from the validation page

### Success Criteria

- ✅ Validation page accessible from health dashboard
- ✅ Detects all entities with missing area assignments
- ✅ Suggests correct area assignments based on entity names (e.g., "office" in name → office area)
- ✅ Users can apply fixes with single click
- ✅ Validation runs in < 5 seconds for typical setups (< 500 entities)
- ✅ Shows clear, actionable suggestions with confidence scores

---

## Research Findings

### Home Assistant 2025.10 APIs

**Entity Registry API:**
- **GET** `/api/config/entity_registry/list` - List all entities with area assignments
- **POST** `/api/config/entity_registry/update/{entity_id}` - Update entity area assignment
- **GET** `/api/config/area_registry/list` - List all areas

**Device Registry API:**
- **GET** `/api/config/device_registry/list` - List all devices with area assignments
- **POST** `/api/config/device_registry/update/{device_id}` - Update device area assignment

**Key Points:**
- Area assignments can be set at both entity and device level
- Device-level assignments propagate to all entities in that device
- Entity-level assignments override device-level assignments

### Existing Codebase Functions

**Found Functions:**
1. **`remediation_service._assign_area()`** (`services/device-intelligence-service/src/services/remediation_service.py:49-59`)
   - Updates device area assignment via HA API
   - Already has guardrails and error handling
   - Can be reused/extended

2. **`ha_client.get_entities_by_area_and_domain()`** (`services/ai-automation-service/src/clients/ha_client.py:940-961`)
   - Queries entities by area and domain
   - Uses real-time HA API
   - Can be used for validation

3. **`integration_checker`** (`services/ha-setup-service/src/integration_checker.py`)
   - Checks various integrations
   - Pattern for validation checks
   - Can be extended for area validation

**Admin Page:**
- `services/ai-automation-ui/src/pages/Admin.tsx` exists but is for training/admin functions
- Can add new section or create separate validation page

---

## User Stories

### Story 32.1: Validation Page UI
**As a** user  
**I want** a validation page that shows Home Assistant configuration issues  
**So that** I can identify and fix problems with my setup

**Acceptance Criteria:**
- Page accessible from health dashboard navigation
- Shows summary of issues (counts by category)
- Lists all validation issues with details
- Groups issues by category (Area Assignments, Entity Issues, etc.)
- Shows confidence scores for suggestions
- Responsive design, works on mobile

### Story 32.2: Area Assignment Detection
**As a** user  
**I want** the system to detect entities with missing or incorrect area assignments  
**So that** I can fix them and improve automation accuracy

**Acceptance Criteria:**
- Scans all entities from Home Assistant
- Identifies entities with `area_id: null`
- Compares entity names with area names to suggest matches
- Uses pattern matching (e.g., "office" in entity_id → office area)
- Shows current assignment vs. suggested assignment
- Provides confidence score (0-100%) for each suggestion

**Examples:**
- `light.hue_office_back_left` → Suggest: office area (confidence: 95%)
- `light.living_room_2` → Suggest: living_room area (confidence: 90%)
- `light.wled` → Suggest: office area (confidence: 60% - low, needs user confirmation)

### Story 32.3: Smart Area Suggestions
**As a** user  
**I want** intelligent suggestions for area assignments based on entity names  
**So that** I can quickly fix misconfigured entities

**Acceptance Criteria:**
- Analyzes entity_id and friendly_name for location keywords
- Matches keywords to existing areas (case-insensitive)
- Handles common patterns:
  - Entity ID contains area name: `light.office_desk` → office
  - Friendly name contains area name: "Office Light" → office
  - Partial matches: `light.lr_back` → living_room
- Provides multiple suggestions if ambiguous
- Shows reasoning for each suggestion

**Suggestion Algorithm:**
1. Extract location keywords from entity_id and friendly_name
2. Normalize keywords (lowercase, remove underscores/hyphens)
3. Match against area names (exact match = 100%, partial = 80%, keyword = 60%)
4. Consider device-level area assignment (if device has area, suggest same for entity)
5. Return top 3 suggestions with confidence scores

### Story 32.4: One-Click Area Assignment Fixes
**As a** user  
**I want** to apply area assignment fixes with a single click  
**So that** I can quickly fix configuration issues

**Acceptance Criteria:**
- "Apply Fix" button for each suggestion
- Confirmation dialog for high-confidence suggestions (>80%)
- Required confirmation for low-confidence suggestions (<80%)
- Shows progress indicator during fix
- Updates UI immediately after successful fix
- Handles errors gracefully with clear error messages
- Supports bulk apply for multiple entities

**Implementation:**
- Use existing `remediation_service._assign_area()` method
- Call HA API: `POST /api/config/entity_registry/update/{entity_id}`
- Update both entity and device if device has multiple entities

### Story 32.5: Validation API Endpoint
**As a** developer  
**I want** a REST API endpoint for validation checks  
**So that** the validation page can fetch results and other tools can use it

**Acceptance Criteria:**
- Endpoint: `GET /api/v1/validation/ha-config`
- Returns validation results as JSON
- Includes:
  - Summary (total issues, by category)
  - Detailed issues with suggestions
  - Confidence scores
  - Metadata (scan timestamp, HA version, etc.)
- Supports filtering by category
- Caches results for 5 minutes
- Runs validation asynchronously for large setups

**Response Format:**
```json
{
  "summary": {
    "total_issues": 15,
    "by_category": {
      "missing_area_assignment": 12,
      "incorrect_area_assignment": 3
    },
    "scan_timestamp": "2025-12-04T10:30:00Z",
    "ha_version": "2025.10.0"
  },
  "issues": [
    {
      "entity_id": "light.hue_office_back_left",
      "category": "missing_area_assignment",
      "current_area": null,
      "suggestions": [
        {
          "area_id": "office",
          "area_name": "Office",
          "confidence": 95,
          "reasoning": "Entity ID contains 'office' keyword"
        }
      ],
      "device_id": "f53d6da537d76c7718c8b53d112c4d17"
    }
  ]
}
```

### Story 32.6: Apply Fix API Endpoint
**As a** developer  
**I want** a REST API endpoint to apply area assignment fixes  
**So that** the validation page can apply fixes programmatically

**Acceptance Criteria:**
- Endpoint: `POST /api/v1/validation/apply-fix`
- Request body: `{ "entity_id": "...", "area_id": "..." }`
- Validates entity exists and area exists
- Applies fix via HA API
- Returns success/error response
- Logs all fixes for audit trail
- Requires authentication (admin role)

---

## Technical Design

### Architecture

```
┌─────────────────┐
│  Health         │
│  Dashboard      │
│  (Frontend)     │
└────────┬────────┘
         │
         │ HTTP
         │
┌────────▼────────────────────────┐
│  Validation Service            │
│  (New Service or Extension)     │
│                                 │
│  - Validation API Endpoint     │
│  - Apply Fix Endpoint          │
│  - Suggestion Engine           │
└────────┬────────────────────────┘
         │
         │ HTTP
         │
┌────────▼────────┐
│  Home Assistant  │
│  REST API        │
│  (2025.10)       │
└──────────────────┘
```

### Components

**1. Validation Service**
- **Location**: New service or extend `ha-setup-service`
- **Responsibilities**:
  - Scan HA entities and areas
  - Detect missing/incorrect area assignments
  - Generate suggestions
  - Apply fixes via HA API

**2. Suggestion Engine**
- **Location**: `services/validation-service/src/services/suggestion_engine.py`
- **Algorithm**:
  1. Extract location keywords from entity names
  2. Match against area names
  3. Calculate confidence scores
  4. Return ranked suggestions

**3. Validation Page**
- **Location**: `services/health-dashboard/src/pages/Validation.tsx`
- **Features**:
  - Issue summary cards
  - Filterable issue list
  - Apply fix buttons
  - Bulk operations

### Data Flow

```
1. User opens Validation page
   ↓
2. Frontend calls GET /api/v1/validation/ha-config
   ↓
3. Validation Service:
   a. Fetches entities from HA API
   b. Fetches areas from HA API
   c. Detects issues
   d. Generates suggestions
   ↓
4. Returns validation results
   ↓
5. Frontend displays issues and suggestions
   ↓
6. User clicks "Apply Fix"
   ↓
7. Frontend calls POST /api/v1/validation/apply-fix
   ↓
8. Validation Service:
   a. Validates request
   b. Calls HA API to update area assignment
   c. Returns success/error
   ↓
9. Frontend updates UI
```

---

## Implementation Plan

### Phase 1: Backend API (Week 1)

**Tasks:**
1. Create validation service or extend ha-setup-service
2. Implement area assignment detection
3. Implement suggestion engine
4. Create validation API endpoint
5. Create apply fix API endpoint
6. Add unit tests

**Deliverables:**
- Validation API endpoint
- Apply fix API endpoint
- Suggestion engine with tests

### Phase 2: Frontend UI (Week 2)

**Tasks:**
1. Create Validation page component
2. Add navigation link in health dashboard
3. Implement issue list with filtering
4. Implement apply fix buttons
5. Add confirmation dialogs
6. Add loading states and error handling
7. Add bulk operations

**Deliverables:**
- Validation page UI
- Integration with backend API
- User testing

### Phase 3: Enhancement (Week 3)

**Tasks:**
1. Add more validation checks (beyond area assignments)
2. Add validation history/audit log
3. Add scheduled validation runs
4. Add email/notification for critical issues
5. Performance optimization for large setups

**Deliverables:**
- Enhanced validation checks
- Audit logging
- Performance improvements

---

## API Specifications

### GET /api/v1/validation/ha-config

**Description:** Get Home Assistant configuration validation results

**Query Parameters:**
- `category` (optional): Filter by issue category (e.g., "missing_area_assignment")
- `min_confidence` (optional): Minimum confidence score (0-100)

**Response:**
```json
{
  "summary": {
    "total_issues": 15,
    "by_category": {
      "missing_area_assignment": 12,
      "incorrect_area_assignment": 3
    },
    "scan_timestamp": "2025-12-04T10:30:00Z",
    "ha_version": "2025.10.0"
  },
  "issues": [...]
}
```

### POST /api/v1/validation/apply-fix

**Description:** Apply area assignment fix

**Request Body:**
```json
{
  "entity_id": "light.hue_office_back_left",
  "area_id": "office"
}
```

**Response:**
```json
{
  "success": true,
  "entity_id": "light.hue_office_back_left",
  "area_id": "office",
  "applied_at": "2025-12-04T10:35:00Z"
}
```

---

## Testing Strategy

### Unit Tests
- Suggestion engine algorithm
- Area matching logic
- Confidence score calculation
- API endpoints

### Integration Tests
- End-to-end validation flow
- Apply fix flow
- Error handling
- HA API integration

### Manual Testing
- Test with real Home Assistant setup
- Verify suggestions are accurate
- Test bulk operations
- Test error scenarios

---

## Dependencies

### External
- Home Assistant 2025.10+ (for entity registry API)
- Home Assistant REST API access token

### Internal
- `ha-setup-service` (for HA client)
- `device-intelligence-service` (for remediation service)
- `health-dashboard` (for UI)

---

## Risks & Mitigations

### Risk 1: Incorrect Suggestions
**Mitigation:** 
- Use conservative confidence thresholds
- Require user confirmation for low-confidence suggestions
- Allow users to override suggestions

### Risk 2: Performance with Large Setups
**Mitigation:**
- Cache validation results
- Run validation asynchronously
- Paginate issue list
- Optimize HA API queries

### Risk 3: HA API Changes
**Mitigation:**
- Version check HA API
- Graceful degradation if API unavailable
- Clear error messages

---

## Future Enhancements

1. **Additional Validation Checks:**
   - Duplicate entity names
   - Disabled entities
   - Missing device assignments
   - Integration health

2. **Automated Fixes:**
   - Scheduled validation runs
   - Auto-apply high-confidence fixes
   - Notification system

3. **Analytics:**
   - Track common issues
   - Success rate of suggestions
   - User feedback on suggestions

---

## References

- **Home Assistant REST API**: https://developers.home-assistant.io/docs/api/rest
- **Entity Registry API**: https://developers.home-assistant.io/docs/api/rest#get-apiconfigentity_registrylist
- **Related Analysis**: `implementation/analysis/OFFICE_LIGHTS_AUTOMATION_REVIEW.md`
- **Existing Code**: `services/device-intelligence-service/src/services/remediation_service.py`

---

## Acceptance

- [ ] Epic approved by product owner
- [ ] Technical design reviewed
- [ ] Dependencies identified and available
- [ ] Stories created and estimated
- [ ] Ready for sprint planning

