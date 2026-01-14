# Device-Based Automation Suggestions Feature - Requirements Document

**Date:** January 16, 2026  
**Status:** 📋 **DRAFT - FOR APPROVAL**  
**Feature:** Device-First Automation Suggestion Workflow  
**Epic:** TBD  
**Story:** TBD

---

## Executive Summary

Enhance the HA AI Agent interface to allow users to start automation conversations by selecting a device. The system will generate 3-5 contextual **Home Assistant automation suggestions** leveraging all available data sources (device attributes, capabilities, design data, synergies, blueprints, sports data, weather data, 3rd party data). Each suggestion can be enhanced and refined through conversational chat, with the bot validating device capabilities and guiding users to optimal solutions.

**First Use Case:** Smart switches (e.g., Inovelli VZM31-SN - Office Light Switch)

**Critical Requirement:** Must preserve all existing ad-hoc suggestions, debugging, and enhancement features while adding this new device-first workflow.

### Home Assistant 2025 Focus

**This feature is specifically designed for Home Assistant 2025.10+ automation generation:**

- ✅ **Home Assistant YAML Format:** All suggestions generate valid Home Assistant 2025.10+ YAML automations
- ✅ **Entity Registry Integration:** Validates all entities exist in Home Assistant entity registry
- ✅ **Service Registry Integration:** Validates all services exist in Home Assistant service registry
- ✅ **Home Assistant Blueprints:** Prioritizes Home Assistant blueprint deployment when available
- ✅ **Home Assistant Patterns:** Uses Home Assistant-specific patterns (sports triggers, state restoration, etc.)
- ✅ **Home Assistant Context:** Leverages existing Home Assistant context building infrastructure
- ✅ **Home Assistant Validation:** Uses existing YAML validation and entity resolution services

**All automations must:**
- Generate valid Home Assistant 2025.10+ YAML format
- Use Home Assistant entity_ids from entity registry
- Use Home Assistant services from service registry
- Follow Home Assistant automation modes (single, restart, queued, parallel)
- Comply with Home Assistant best practices (initial_state, error handling, etc.)

---

## 1. Functional Requirements

### 1.1 Device Selection Interface

**FR-1.1.1: Device Picker Component**
- **Description:** Add a device selection interface to the Agent screen
- **Location:** `services/ai-automation-ui/src/components/ha-agent/`
- **Requirements:**
  - Device picker should be accessible from the Agent screen main interface
  - Support filtering by device type, area, manufacturer, model
  - Display device name, area, device type, and current state
  - Show device icon/visual representation
  - Support search functionality
  - **First Use Case:** Filter by device type "switch" to find smart switches
  - **Example Device:** "Office Light Switch" (VZM31-SN by Inovelli)

**FR-1.1.2: Device Context Display**
- **Description:** Show selected device information when device is chosen
- **Requirements:**
  - Display device name, manufacturer, model
  - Show device area/location
  - Display current state and capabilities
  - Show related entities (if device has multiple entities)
  - Display device health/status indicators

**FR-1.1.3: Device Selection Persistence**
- **Description:** Remember selected device during conversation
- **Requirements:**
  - Store selected device_id in conversation context
  - Persist device selection across conversation messages
  - Allow user to change device mid-conversation
  - Clear device selection when starting new conversation

### 1.2 Suggestion Generation

**FR-1.2.1: Multi-Source Data Aggregation**
- **Description:** Collect and aggregate data from all available sources for suggestion generation
- **Data Sources Required:**
  1. **Device Attributes & Capabilities**
     - Fetch from `data-api` (`/api/devices/{device_id}`)
     - Include: device_type, device_category, device_features_json, capabilities
     - Use `DeviceCapabilityAnalyzer` from `ai-pattern-service`
     - Include entity capabilities (supported_features, available_services)
  
  2. **Design Data**
     - Device metadata (manufacturer, model, sw_version)
     - Device intelligence fields (power_consumption, setup_instructions_url)
     - Device relationships (via_device, parent/child devices)
  
  3. **Synergies**
     - Query `ai-pattern-service` (`/api/v1/synergies?device_id={device_id}`)
     - Include: synergy_type, impact_score, confidence, quality_score
     - Filter by active devices and quality tier (high, medium)
     - Include XAI explanations from synergies
  
  4. **Blueprints**
     - Query `blueprint-suggestion-service` for device-compatible blueprints
     - Match blueprints based on device capabilities
     - Include blueprint fit scores and auto-fill suggestions
  
  5. **Sports Data**
     - Query sports-api for team tracker sensors
     - Include team colors, game schedules, state changes
     - Match sports data to device area/location if relevant
  
  6. **Weather Data**
     - Query weather-api for current conditions
     - Include temperature, conditions, forecasts
     - Match weather data to device area/location if relevant
  
  7. **3rd Party Data**
     - Any additional external data sources
     - Integration-specific data (e.g., Zigbee2MQTT attributes)

**FR-1.2.2: Suggestion Generation Service**
- **Description:** Generate 3-5 Home Assistant automation suggestions based on aggregated data
- **Service:** New endpoint in `ha-ai-agent-service` or enhancement to existing service
- **Endpoint:** `POST /api/v1/chat/device-suggestions`
- **Home Assistant Focus:** All suggestions must generate valid Home Assistant 2025.10+ YAML automations
- **Input:**
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
- **Output:**
  ```json
  {
    "suggestions": [
      {
        "suggestion_id": "uuid",
        "title": "Suggestion Title",
        "description": "Detailed description",
        "automation_preview": {
          "trigger": "Home Assistant trigger description (e.g., 'Motion sensor detects movement')",
          "action": "Home Assistant action description (e.g., 'Turn on Office Light Switch')",
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

**FR-1.2.3: Suggestion Ranking & Filtering**
- **Description:** Rank and filter suggestions by relevance and quality
- **Requirements:**
  - Prioritize suggestions with high confidence scores (≥0.7)
  - Prioritize suggestions validated by patterns (pattern_support_score ≥0.7)
  - Prioritize suggestions with blueprint matches (blueprint_fit_score ≥0.6)
  - Filter out suggestions that exceed device capabilities
  - Limit to 3-5 top suggestions
  - Include diversity (different trigger types, different use cases)

### 1.3 Suggestion Display & Interaction

**FR-1.3.1: Suggestion Cards UI**
- **Description:** Display suggestions in interactive cards
- **Location:** `services/ai-automation-ui/src/components/ha-agent/DeviceSuggestions.tsx` (new component)
- **Requirements:**
  - Display suggestion title and description
  - Show automation preview (trigger → action summary)
  - Display data source indicators (synergy, blueprint, sports, weather icons)
  - Show confidence/quality scores
  - "Enhance" button to start chat conversation
  - "Create" button to directly create automation (optional)
  - Visual distinction between suggestion types

**FR-1.3.2: Suggestion Enhancement Flow**
- **Description:** Allow users to chat with suggestions to refine them
- **Requirements:**
  - Clicking "Enhance" on a suggestion starts a conversation
  - Pre-populate conversation with suggestion context
  - Include device_id, suggestion_id, and suggestion details in context
  - Allow user to modify trigger, conditions, actions through chat
  - Bot validates device capabilities during conversation
  - Bot suggests alternatives if requested feature not supported
  - Maintain conversation history with suggestion context

**FR-1.3.3: Device Capability Validation**
- **Description:** Bot validates device capabilities during suggestion enhancement
- **Requirements:**
  - Check if requested service/action is available for device
  - Check if requested attributes (brightness, color, etc.) are supported
  - Check if requested effects/presets exist for device
  - Provide clear error messages if capability not supported
  - Suggest alternatives when capability not available
  - Use device capabilities from `data-api` and entity registry

### 1.4 Integration with Existing Features

**FR-1.4.1: Preserve Ad-Hoc Suggestions**
- **Description:** Keep existing proactive/pattern-based suggestions
- **Requirements:**
  - Existing suggestion flows remain unchanged
  - "Suggestions" tab continues to work as before
  - "Proactive" suggestions continue to appear
  - "Pattern" suggestions continue to work
  - Device-based suggestions are additive, not replacement

**FR-1.4.2: Preserve Debugging Features**
- **Description:** Keep existing debugging capabilities
- **Requirements:**
  - Debug tab continues to show tool calls, context, YAML
  - Debug information includes device context when device selected
  - All existing debugging features remain functional

**FR-1.4.3: Preserve Enhancement Features**
- **Description:** Keep existing automation enhancement suggestions
- **Requirements:**
  - `suggest_automation_enhancements` tool continues to work
  - Enhancement suggestions after automation creation remain
  - Device context enhances existing enhancement suggestions

**FR-1.4.4: Dual Workflow Support**
- **Description:** Support both device-first and prompt-first workflows
- **Requirements:**
  - Users can start conversation with device selection OR natural language prompt
  - Device selection is optional, not required
  - Natural language prompts work as before
  - Device context enhances natural language prompts when device selected

### 1.5 Home Assistant Integration & Validation

**FR-1.5.1: Home Assistant Entity Validation**
- **Description:** Validate all entities exist in Home Assistant before suggesting automations
- **Requirements:**
  - Verify entity_ids exist in Home Assistant entity registry
  - Use Home Assistant context from `ha-ai-agent-service` (entity inventory, areas, services)
  - Validate entity capabilities match suggested automation actions
  - Check entity availability (not disabled, not unavailable)
  - Use exact entity_ids from Home Assistant (no invented IDs)

**FR-1.5.2: Home Assistant Service Validation**
- **Description:** Validate all service calls are valid for Home Assistant
- **Requirements:**
  - Verify service.domain exists in Home Assistant service registry
  - Validate service parameters match Home Assistant service schemas
  - Check service target options (entity_id, area_id, device_id)
  - Use exact service names from Home Assistant context (e.g., `switch.turn_on`, not `switch.on`)

**FR-1.5.3: Home Assistant 2025.10+ YAML Format Compliance**
- **Description:** All suggested automations must generate valid Home Assistant 2025.10+ YAML
- **Requirements:**
  - Use singular `trigger:` and `action:` (not plural)
  - Include `platform:` field in triggers (required in 2025.10+)
  - Include `service:` field in actions (required in 2025.10+)
  - Include `initial_state: true` (required in 2025.10+)
  - Use `target.area_id` or `target.entity_id` for service calls
  - Use `error: continue` for non-critical actions (2025.10+ format)
  - Follow Home Assistant mode options: `single`, `restart`, `queued`, `parallel`
  - Validate YAML structure before suggesting

**FR-1.5.4: Home Assistant Sports Automation Patterns**
- **Description:** Use Home Assistant Team Tracker sensor patterns for sports automations
- **Requirements:**
  - **NEVER use fixed time triggers** for sports events (game times change)
  - Use Team Tracker sensor state changes as triggers:
    - `PRE` → `IN` for game start
    - `IN` → `POST` for game end
    - Template triggers for pre-game (15 minutes before)
  - Use `team_colors` attribute for lighting automations (convert hex to RGB)
  - Match sports data to device area if Team Tracker sensors exist in same area

**FR-1.5.5: Home Assistant Blueprint Integration**
- **Description:** Prioritize Home Assistant blueprints when available
- **Requirements:**
  - Query `blueprint-suggestion-service` for device-compatible blueprints
  - Match blueprints based on device capabilities and entity types
  - Use blueprint auto-fill suggestions for entity mapping
  - Deploy via blueprint when fit_score ≥ 0.6
  - Fall back to YAML generation only if no suitable blueprint found

### 1.6 Conversation Context Management

**FR-1.6.1: Device Context in System Prompt**
- **Description:** Include device context in HA AI Agent system prompt
- **Location:** `services/ha-ai-agent-service/src/prompts/system_prompt.py`
- **Requirements:**
  - When device_id present in conversation, include device context
  - Include Home Assistant entity inventory for device entities
  - Include Home Assistant service schemas for device capabilities
  - Include device capabilities, attributes, related entities
  - Include related synergies and blueprints
  - Include device area and related devices in same area
  - Context builder should fetch device data from data-api
  - **Home Assistant Focus:** Use Home Assistant context (entities, areas, services) from existing context builder

**FR-1.6.2: Context Builder Enhancement**
- **Description:** Enhance context builder to include device-specific Home Assistant data
- **Location:** `services/ha-ai-agent-service/src/services/context_builder.py`
- **Requirements:**
  - Add device context fetching when device_id present
  - Aggregate device data from all sources (synergies, blueprints, etc.)
  - Include Home Assistant entity registry data for device entities
  - Include Home Assistant service registry data for device capabilities
  - Include device context in system prompt
  - Cache device context to reduce API calls
  - **Home Assistant Focus:** Leverage existing Home Assistant context building infrastructure

---

## 2. Non-Functional Requirements

### 2.1 Performance

**NFR-2.1.1: Suggestion Generation Time**
- **Target:** Generate suggestions within 3-5 seconds
- **Measurement:** Time from device selection to suggestion display
- **Optimization:**
  - Cache device capabilities
  - Parallel API calls for data aggregation
  - Limit data fetching to essential sources

**NFR-2.1.2: Context Loading Time**
- **Target:** Load device context within 1-2 seconds
- **Measurement:** Time to fetch and aggregate device data
- **Optimization:**
  - Use existing caches (device capabilities, synergies)
  - Batch API calls where possible
  - Lazy load non-critical data sources

### 2.2 Usability

**NFR-2.2.1: Device Selection UX**
- **Target:** Users can find and select device within 10 seconds
- **Requirements:**
  - Clear device picker interface
  - Effective search and filtering
  - Visual device representation
  - Intuitive selection flow

**NFR-2.2.2: Suggestion Clarity**
- **Target:** Users understand suggestions without explanation
- **Requirements:**
  - Clear, concise suggestion titles
  - Descriptive automation previews
  - Visual data source indicators
  - Confidence/quality score explanations

### 2.3 Reliability

**NFR-2.3.1: Graceful Degradation**
- **Description:** System works even if some data sources unavailable
- **Requirements:**
  - Suggestions generated even if synergies API unavailable
  - Suggestions generated even if blueprints API unavailable
  - Fallback to device capabilities only if other sources fail
  - Clear indication of missing data sources

**NFR-2.3.2: Error Handling**
- **Description:** Handle errors gracefully
- **Requirements:**
  - Clear error messages for API failures
  - Retry logic for transient failures
  - Fallback suggestions if generation fails
  - User-friendly error messages

### 2.4 Security

**NFR-2.4.1: Data Access Control**
- **Description:** Ensure proper access control for device data
- **Requirements:**
  - Verify user has access to selected device
  - Validate device_id before fetching data
  - Sanitize device data in responses
  - Follow existing authentication patterns

---

## 3. Technical Constraints

### 3.1 Home Assistant Constraints

**TC-3.1.1: Home Assistant 2025.10+ YAML Format**
- **Requirement:** All automations must generate valid Home Assistant 2025.10+ YAML
- **Format Requirements:**
  - Singular `trigger:` and `action:` (not plural)
  - `platform:` field required in all triggers
  - `service:` field required in all actions
  - `initial_state: true` required
  - `target.area_id` or `target.entity_id` for service calls
  - `error: continue` for non-critical actions (2025.10+ format)
- **Validation:** Use existing YAML validation in `ha-ai-agent-service` (ValidationChain, YAMLValidationStrategy)

**TC-3.1.2: Home Assistant Entity Registry**
- **Requirement:** All entity_ids must exist in Home Assistant entity registry
- **Validation:** Use Home Assistant context from `ha-ai-agent-service` (entity inventory)
- **Entity Resolution:** Use existing EntityResolutionService for entity matching
- **No Invented IDs:** Never create entity_ids that don't exist in Home Assistant

**TC-3.1.3: Home Assistant Service Registry**
- **Requirement:** All service calls must be valid Home Assistant services
- **Validation:** Use Home Assistant context service schemas
- **Service Format:** Use exact service names (e.g., `switch.turn_on`, not `switch.on`)
- **Parameter Validation:** Validate service parameters against Home Assistant service schemas

**TC-3.1.4: Home Assistant Automation Modes**
- **Requirement:** Use only valid Home Assistant automation modes
- **Valid Modes:** `single`, `restart`, `queued`, `parallel`
- **Mode Selection:** Follow Home Assistant best practices:
  - `single`: One-time actions
  - `restart`: Cancel previous runs (motion-activated lights)
  - `queued`: Sequential execution
  - `parallel`: Independent actions

### 3.2 Architecture Constraints

**TC-3.2.1: Service Dependencies**
- **Existing Services:**
  - `ha-ai-agent-service` (port 8000) - Main agent service (Home Assistant YAML generation)
  - `data-api` (port 8006) - Device/entity data (Home Assistant entity registry)
  - `ai-pattern-service` - Synergies
  - `blueprint-suggestion-service` (port 8032) - Home Assistant blueprints
  - `sports-api` (port 8005) - Sports data (Team Tracker sensors)
  - `weather-api` (port 8009) - Weather data
- **Requirement:** New feature must work with existing service architecture
- **Home Assistant Integration:** Leverage existing Home Assistant context building in `ha-ai-agent-service`

**TC-3.2.2: Database Schema**
- **Existing Tables:**
  - `devices` - Device registry (data-api, syncs with Home Assistant device registry)
  - `entities` - Entity registry (data-api, syncs with Home Assistant entity registry)
  - `synergy_opportunities` - Synergies (ai-pattern-service)
  - `blueprint_suggestions` - Home Assistant blueprint suggestions
- **Requirement:** No schema changes required (use existing tables)
- **Home Assistant Sync:** Device/entity data synced from Home Assistant via data-api

### 3.3 API Constraints

**TC-3.3.1: Existing API Endpoints**
- **Must Use:**
  - `GET /api/devices/{device_id}` - Device data (Home Assistant device registry)
  - `GET /api/devices/{device_id}/capabilities` - Device capabilities (Home Assistant entity capabilities)
  - `GET /api/v1/synergies` - Synergies
  - `GET /api/suggestions` - Home Assistant blueprint suggestions
  - `POST /api/v1/chat` - Chat endpoint (Home Assistant automation generation)
- **Requirement:** Leverage existing endpoints, add new endpoints only if necessary
- **Home Assistant Context:** Use existing Home Assistant context in `ha-ai-agent-service` (entity inventory, services, areas)

**TC-3.3.2: Chat API Enhancement**
- **Existing:** `POST /api/v1/chat` - Chat endpoint (generates Home Assistant YAML)
- **Requirement:** Enhance chat endpoint to support device context, or add new endpoint
- **Home Assistant Focus:** Device context should include Home Assistant entity registry data for device entities

### 3.4 Frontend Constraints

**TC-3.4.1: React/TypeScript**
- **Framework:** React with TypeScript
- **UI Library:** Existing components (framer-motion, react-hot-toast)
- **Requirement:** Follow existing component patterns and styling
- **Home Assistant Integration:** Display Home Assistant entity names (friendly_name) not entity_ids

**TC-3.4.2: State Management**
- **Current:** React hooks (useState, useEffect)
- **Requirement:** Use existing state management patterns
- **Home Assistant Data:** Store Home Assistant entity/device data in component state

---

## 4. Assumptions

### 4.1 Data Availability

**A-4.1.1: Device Data Completeness**
- **Assumption:** Device data in `data-api` is complete and up-to-date
- **Impact:** If device data incomplete, suggestions may be less accurate
- **Mitigation:** Validate device data before generating suggestions

**A-4.1.2: Synergy Data Quality**
- **Assumption:** Synergies are detected and stored with quality scores ≥0.50
- **Impact:** If synergies low quality, suggestions may be less relevant
- **Mitigation:** Filter synergies by quality score (≥0.7 for high priority)

### 4.2 User Behavior

**A-4.2.1: Device Selection Frequency**
- **Assumption:** Users will select devices frequently for automation suggestions
- **Impact:** If rarely used, feature may not provide value
- **Mitigation:** Make device selection prominent and easy to use

**A-4.2.2: Suggestion Enhancement**
- **Assumption:** Users will enhance suggestions through chat
- **Impact:** If users don't enhance, feature may be underutilized
- **Mitigation:** Make enhancement flow intuitive and valuable

### 4.3 System Performance

**A-4.3.1: API Response Times**
- **Assumption:** All dependent APIs respond within 2-3 seconds
- **Impact:** If APIs slow, suggestion generation will be slow
- **Mitigation:** Implement caching and parallel API calls

---

## 5. Open Questions

### 5.1 Feature Scope

**Q-5.1.1: Device Type Support**
- **Question:** Should we support all device types from the start, or only smart switches initially?
- **Recommendation:** Start with smart switches (first use case), expand to other device types in Phase 2
- **Decision Needed:** Scope for initial release

**Q-5.1.2: Suggestion Count**
- **Question:** Should we always show 3-5 suggestions, or vary based on available data?
- **Recommendation:** Show 3-5 suggestions, but allow fewer if data limited
- **Decision Needed:** Minimum/maximum suggestion count

### 5.2 UI/UX

**Q-5.2.1: Device Picker Placement**
- **Question:** Where should device picker appear on Agent screen?
- **Options:**
  - Above chat input (always visible)
  - In conversation header (when device selected)
  - Modal/dialog (on demand)
- **Recommendation:** Above chat input with "Select Device" button
- **Decision Needed:** UI placement

**Q-5.2.2: Suggestion Display Format**
- **Question:** How should suggestions be displayed?
- **Options:**
  - Cards in main chat area
  - Sidebar panel
  - Modal overlay
  - Inline in conversation
- **Recommendation:** Cards in main chat area, similar to automation previews
- **Decision Needed:** Display format

### 5.3 Technical Implementation

**Q-5.3.1: New Service vs Enhancement**
- **Question:** Should we create a new service or enhance existing services?
- **Options:**
  - New `device-suggestion-service`
  - Enhance `ha-ai-agent-service`
  - Enhance `ai-pattern-service`
- **Recommendation:** Enhance `ha-ai-agent-service` with new endpoint
- **Decision Needed:** Service architecture

**Q-5.3.2: Caching Strategy**
- **Question:** How should we cache device data and suggestions?
- **Options:**
  - In-memory cache (per request)
  - Redis cache (shared)
  - Database cache
- **Recommendation:** In-memory cache for request duration, consider Redis for shared cache
- **Decision Needed:** Caching approach

### 5.4 Data Sources

**Q-5.4.1: Required vs Optional Data Sources**
- **Question:** Which data sources are required vs optional for suggestions?
- **Recommendation:**
  - **Required:** Device capabilities, device attributes
  - **Optional:** Synergies, blueprints, sports, weather (enhance suggestions if available)
- **Decision Needed:** Data source priority

**Q-5.4.2: Data Source Weighting**
- **Question:** How should we weight different data sources when ranking suggestions?
- **Recommendation:**
  - Device capabilities: 40%
  - Synergies: 30%
  - Blueprints: 20%
  - Sports/Weather: 10%
- **Decision Needed:** Weighting algorithm

---

## 6. Success Criteria

### 6.1 Functional Success

**SC-6.1.1: Device Selection Works**
- **Criteria:** Users can select a device and see device information
- **Measurement:** 100% success rate for device selection
- **Target:** Week 1

**SC-6.1.2: Suggestions Generated**
- **Criteria:** System generates 3-5 suggestions for selected device
- **Measurement:** Suggestions generated within 5 seconds
- **Target:** Week 2

**SC-6.1.3: Suggestions Enhanced**
- **Criteria:** Users can enhance suggestions through chat
- **Measurement:** Users successfully enhance at least 1 suggestion
- **Target:** Week 3

### 6.2 Quality Success

**SC-6.2.1: Suggestion Relevance**
- **Criteria:** Suggestions are relevant to selected device
- **Measurement:** User feedback (thumbs up/down on suggestions)
- **Target:** ≥70% positive feedback

**SC-6.2.2: Capability Validation**
- **Criteria:** Bot correctly validates device capabilities
- **Measurement:** No false positives (suggesting unsupported features)
- **Target:** 100% accuracy

### 6.3 User Experience Success

**SC-6.3.1: User Adoption**
- **Criteria:** Users use device selection feature
- **Measurement:** % of conversations that start with device selection
- **Target:** ≥20% of conversations use device selection (after 1 month)

**SC-6.3.2: Feature Satisfaction**
- **Criteria:** Users find feature valuable
- **Measurement:** User survey/feedback
- **Target:** ≥4/5 satisfaction rating

---

## 7. Implementation Phases

### Phase 1: Core Device Selection (Week 1-2)
- **Deliverables:**
  - Device picker UI component
  - Device selection state management
  - Device context display
  - Basic device data fetching

### Phase 2: Suggestion Generation (Week 3-4)
- **Deliverables:**
  - Multi-source data aggregation
  - Suggestion generation service/endpoint
  - Suggestion ranking algorithm
  - Suggestion display UI

### Phase 3: Enhancement Flow (Week 5-6)
- **Deliverables:**
  - Suggestion enhancement chat flow
  - Device capability validation
  - Context management for device conversations
  - Integration with existing chat system

### Phase 4: Polish & Testing (Week 7-8)
- **Deliverables:**
  - Error handling and graceful degradation
  - Performance optimization
  - User testing and feedback
  - Documentation

---

## 8. Dependencies

### 8.1 External Dependencies
- **data-api** - Device/entity data (existing)
- **ai-pattern-service** - Synergies (existing)
- **blueprint-suggestion-service** - Blueprints (existing)
- **sports-api** - Sports data (existing)
- **weather-api** - Weather data (existing)

### 8.2 Internal Dependencies
- **ha-ai-agent-service** - Chat/automation service (existing)
- **ai-automation-ui** - Frontend UI (existing)
- **Device capability discovery** - Existing capability analysis

### 8.3 Data Dependencies
- Device registry (devices table)
- Entity registry (entities table)
- Synergy opportunities (synergy_opportunities table)
- Blueprint suggestions (blueprint_suggestions table)

---

## 9. Risks & Mitigations

### 9.1 Technical Risks

**R-9.1.1: API Latency**
- **Risk:** Multiple API calls slow down suggestion generation
- **Mitigation:** Parallel API calls, caching, timeout handling

**R-9.1.2: Data Inconsistency**
- **Risk:** Device data inconsistent across services
- **Mitigation:** Validate data, use authoritative source (data-api), handle missing data gracefully

### 9.2 User Experience Risks

**R-9.2.1: Feature Discoverability**
- **Risk:** Users don't discover device selection feature
- **Mitigation:** Prominent UI placement, onboarding/tooltips, documentation

**R-9.2.2: Suggestion Quality**
- **Risk:** Suggestions not relevant or useful
- **Mitigation:** Quality scoring, user feedback, iterative improvement

### 9.3 Integration Risks

**R-9.3.1: Breaking Existing Features**
- **Risk:** New feature breaks existing ad-hoc suggestions
- **Mitigation:** Comprehensive testing, feature flags, gradual rollout

**R-9.3.2: Service Dependencies**
- **Risk:** Dependent services unavailable
- **Mitigation:** Graceful degradation, fallback suggestions, error handling

---

## 10. Approval Checklist

- [ ] Functional requirements reviewed and approved
- [ ] Non-functional requirements reviewed and approved
- [ ] Technical constraints understood and accepted
- [ ] Assumptions validated
- [ ] Open questions answered
- [ ] Success criteria agreed upon
- [ ] Implementation phases approved
- [ ] Dependencies identified and available
- [ ] Risks assessed and mitigations accepted
- [ ] UI/UX approach approved
- [ ] Data source priorities decided
- [ ] Service architecture approach approved

---

## 11. Next Steps

1. **Review & Approval:** Stakeholder review of this requirements document
2. **Answer Open Questions:** Resolve all open questions (Section 5)
3. **Design Phase:** Create detailed design documents (UI mockups, API specs, data flow)
4. **Implementation Planning:** Break down into user stories and tasks
5. **Development:** Begin Phase 1 implementation

---

## Appendix A: Example User Flow

### Scenario: User wants automation suggestions for Office Light Switch

1. **User opens Agent screen** (`/ha-agent`)
2. **User clicks "Select Device"** button above chat input
3. **Device picker opens** with list of devices
4. **User searches/filters** for "Office Light Switch" or "switch" device type
5. **User selects** "Office Light Switch" (VZM31-SN by Inovelli)
6. **Device context displays** showing:
   - Device name: "Office Light Switch"
   - Manufacturer: "Inovelli"
   - Model: "VZM31-SN"
   - Area: "Office"
   - Current state: "on"
   - Capabilities: "brightness control", "scene control", "notification"
7. **System generates 3-5 suggestions** leveraging:
   - Device capabilities (brightness, scenes)
   - Synergies (motion-to-light, door-to-light)
   - Blueprints (motion-activated lighting)
   - Sports data (if office has team tracker sensors)
   - Weather data (if relevant to office)
8. **Suggestions display** as cards:
   - "Motion-activated office lighting"
   - "Sports game lighting (VGK colors)"
   - "Time-based dimming schedule"
   - "Door-triggered office lights"
   - "Weather-based lighting adjustment"
9. **User clicks "Enhance"** on "Motion-activated office lighting"
10. **Chat conversation starts** with suggestion context pre-loaded
11. **User chats** to refine: "Make it only work during business hours"
12. **Bot validates** device capabilities and suggests automation
13. **User approves** and automation is created

---

## Appendix B: Data Source Integration Details

### Device Capabilities (Home Assistant Focus)
- **Source:** `data-api` `/api/devices/{device_id}/capabilities`
- **Data:** 
  - Home Assistant entity capabilities (supported_features, available_services)
  - Device features from Home Assistant device registry
  - Entity attributes (effects, presets, color modes) from Home Assistant entity registry
- **Usage:** 
  - Validate Home Assistant automation actions
  - Suggest compatible Home Assistant services
  - Check entity capabilities match suggested automations

### Synergies (Home Assistant Integration)
- **Source:** `ai-pattern-service` `/api/v1/synergies?device_id={device_id}`
- **Data:** Device interaction patterns, impact scores, confidence
- **Usage:** Suggest Home Assistant automations based on detected patterns
- **Home Assistant Entities:** Synergies include Home Assistant entity_ids for triggers/actions

### Blueprints (Home Assistant Blueprints)
- **Source:** `blueprint-suggestion-service` `/api/suggestions?device_id={device_id}`
- **Data:** 
  - Compatible Home Assistant blueprints
  - Blueprint fit scores
  - Auto-fill suggestions (Home Assistant entity mappings)
- **Usage:** 
  - Suggest Home Assistant blueprint-based automations
  - Deploy via Home Assistant blueprint API when fit_score ≥ 0.6
  - Use blueprint auto-fill for entity mapping

### Sports Data (Home Assistant Team Tracker Sensors)
- **Source:** `sports-api` (Team Tracker sensors)
- **Data:** 
  - Home Assistant Team Tracker sensor states (PRE, IN, POST, NOT_FOUND)
  - Team colors (hex codes, convert to RGB for Home Assistant)
  - Game schedules (use sensor state changes, not fixed times)
- **Usage:** 
  - Suggest Home Assistant automations with Team Tracker sensor triggers
  - Use sensor state changes (PRE → IN for game start, IN → POST for game end)
  - Use team_colors attribute for lighting automations (convert hex to RGB)
  - **Critical:** NEVER use fixed time triggers for sports (game times change)

### Weather Data (Home Assistant Weather Integration)
- **Source:** `weather-api`
- **Data:** Current conditions, forecasts (Home Assistant weather entities)
- **Usage:** Suggest Home Assistant automations with weather conditions/triggers
- **Home Assistant Entities:** Use Home Assistant weather sensor entities for triggers

### Home Assistant Context (Primary Source)
- **Source:** `ha-ai-agent-service` system prompt context
- **Data:**
  - Home Assistant entity inventory (IDs, friendly names, states, areas, device IDs)
  - Home Assistant areas (IDs, names, aliases)
  - Home Assistant services (schemas, parameters, capabilities)
  - Home Assistant device capabilities (enum values, ranges, types)
  - Home Assistant helpers & scenes
  - Home Assistant entity attributes (effects, presets, color modes)
- **Usage:** 
  - Primary source for Home Assistant entity/service validation
  - Entity resolution (find entities by name, area, type)
  - Service validation (check service exists, validate parameters)
  - Capability validation (check entity supports requested features)

---

---

## Appendix C: Home Assistant 2025.10+ YAML Format Requirements

### Required YAML Structure

All suggested automations must generate valid Home Assistant 2025.10+ YAML:

```yaml
alias: "Descriptive Name"
description: "What this automation does"
initial_state: true  # REQUIRED in 2025.10+
mode: single|restart|queued|parallel
trigger:  # SINGULAR (not plural)
  - platform: state|time|time_pattern|template  # platform: REQUIRED
    entity_id: binary_sensor.motion_office
    to: "on"
condition: []  # Optional
action:  # SINGULAR (not plural)
  - service: switch.turn_on  # service: REQUIRED
    target:
      entity_id: switch.office_light_switch
    data:
      brightness: 255
    error: continue  # 2025.10+ format (not continue_on_error: true)
```

### Critical YAML Rules

1. **Singular Forms:** Use `trigger:` and `action:` (not `triggers:` and `actions:`)
2. **Platform Field:** All triggers must include `platform:` field
3. **Service Field:** All actions must include `service:` field
4. **Initial State:** Always include `initial_state: true`
5. **Target Structure:** Use `target.entity_id` or `target.area_id` for service calls
6. **Error Handling:** Use `error: continue` for non-critical actions (2025.10+ format)
7. **Entity Validation:** All entity_ids must exist in Home Assistant entity registry
8. **Service Validation:** All services must exist in Home Assistant service registry

### Sports Automation Patterns (Home Assistant)

**NEVER use fixed time triggers for sports events.** Use Team Tracker sensor state changes:

```yaml
# Game Start Trigger (PRE → IN)
trigger:
  - platform: state
    entity_id: sensor.vgk_team_tracker  # or any team_tracker sensor
    from: "PRE"
    to: "IN"

# Game End Trigger (IN → POST)
trigger:
  - platform: state
    entity_id: sensor.vgk_team_tracker
    from: "IN"
    to: "POST"
```

### State Restoration Pattern (Home Assistant)

```yaml
action:
  # 1. Capture current state
  - service: scene.create
    data:
      scene_id: office_light_switch_restore  # lowercase, underscores, _restore suffix
      snapshot_entities:
        - switch.office_light_switch
  # 2. Perform action
  - service: switch.turn_on
    target:
      entity_id: switch.office_light_switch
  # 3. Wait
  - delay: "00:00:01"
  # 4. Restore state
  - service: scene.turn_on
    target:
      entity_id: scene.office_light_switch_restore
```

---

**Document Status:** Ready for Review - Home Assistant 2025 Focused  
**Last Updated:** January 16, 2026  
**Next Review:** After stakeholder feedback  
**Home Assistant Version:** 2025.10+ (Current Standard)
