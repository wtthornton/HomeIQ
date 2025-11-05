# Ask AI Suggestion Logic Review

**Date:** January 6, 2025  
**Endpoint:** `http://localhost:3001/ask-ai`  
**User Query:** "when I trigger my desk sensor, I want the lights to in the office to switch to 100% brightness and Natural light scene"

## Executive Summary

This document reviews the suggestion logic for the Ask AI feature, focusing on:
1. Why 1 device ("Office") was selected for the first suggestion
2. Whether YAML was created for the first suggestion
3. Complete call tree understanding

## 1. Device Selection Analysis

### Why Only 1 Device Was Selected

Based on the screenshot and code analysis, here's why "Office" was the only device shown:

#### Query Analysis
- **User Request:** "when I trigger my desk sensor, I want the lights to in the office to switch to 100% brightness and Natural light scene"
- **Entities Mentioned:** 
  - "desk sensor" (trigger device)
  - "office" (location/area)
  - "lights" (target device type)

#### Device Selection Process

The device selection follows this flow:

```
1. Entity Extraction (extract_entities_with_ha)
   ↓
2. Entity Enrichment (enrich_entities_comprehensively)
   ↓
3. OpenAI Suggestion Generation (generate_suggestions_from_query)
   ↓
4. Device Mapping (map_devices_to_entities)
   ↓
5. Validation (verify_entities_exist_in_ha)
   ↓
6. Frontend Display (extractDeviceInfo in AskAI.tsx)
```

**Key Code Path:**

```629:754:services/ai-automation-service/src/api/ask_ai_router.py
async def map_devices_to_entities(
    devices_involved: List[str], 
    enriched_data: Dict[str, Dict[str, Any]],
    ha_client: Optional[HomeAssistantClient] = None,
    fuzzy_match: bool = True
) -> Dict[str, str]:
    """
    Map device friendly names to entity IDs from enriched data.
    
    Optimized for single-home local solutions:
    - Deduplicates redundant mappings (multiple friendly names → same entity_id)
    - Prioritizes exact matches over fuzzy matches
    - Uses area context for better matching in single-home scenarios
    - Consolidates devices_involved to unique entity mappings
    
    IMPORTANT: Only includes entity IDs that actually exist in Home Assistant.
    """
```

**Three-Tier Matching Strategy:**

1. **Exact Match** (highest priority)
   - Searches for exact friendly_name match (case-insensitive)
   - Example: "Office" → matches "Office" entity

2. **Fuzzy Matching** (area-aware)
   - Substring matching with area context bonus
   - Example: "office lights" → matches entities in "Office" area
   - Score calculation includes area context bonus

3. **Domain Matching** (lowest priority)
   - Matches by domain name if no better match found

**Why "Office" Was Selected:**

1. **Entity Extraction:** The system extracted:
   - "office" as an area entity
   - "lights" as a device entity
   - "desk sensor" as a device entity

2. **Area Expansion:** When "office" is detected as an area:
   - System fetches ALL devices in the office area
   - But only devices that match the query intent are included

3. **Device Consolidation:** The code includes deduplication logic:

```956:1011:services/ai-automation-service/src/api/ask_ai_router.py
def _pre_consolidate_device_names(
    devices_involved: List[str],
    enriched_data: Optional[Dict[str, Dict[str, Any]]] = None
) -> List[str]:
    """
    Pre-consolidate device names by removing generic/redundant terms BEFORE entity mapping.
    
    This handles cases where OpenAI includes:
    - Generic domain names ("light", "switch")
    - Device type names ("wled", "hue")  
    - Area-only references that don't map to actual entities
    - Very short/generic terms (< 3 chars)
    """
```

4. **Frontend Display Logic:** The frontend extracts devices from `validated_entities`:

```1177:1330:services/ai-automation-ui/src/pages/AskAI.tsx
const extractDeviceInfo = (suggestion: any, extractedEntities?: any[], suggestionId?: string): Array<{ friendly_name: string; entity_id: string; domain?: string; selected?: boolean }> => {
    const devices: Array<{ friendly_name: string; entity_id: string; domain?: string; selected?: boolean }> = [];
    const seenEntityIds = new Set<string>();
    
    // Helper to add device safely
    const addDevice = (friendlyName: string, entityId: string, domain?: string) => {
        // Filter out generic/redundant device names (same as backend)
        const friendlyNameLower = friendlyName.toLowerCase().trim();
        const genericTerms = ['light', 'lights', 'device', 'devices', 'sensor', 'sensors', 'switch', 'switches'];
        if (genericTerms.includes(friendlyNameLower)) {
            return; // Skip generic terms
        }
        
        // ... device addition logic
    };
    
    // 1. Try validated_entities (most reliable - direct mapping from API)
    if (suggestion.validated_entities && typeof suggestion.validated_entities === 'object') {
        Object.entries(suggestion.validated_entities).forEach(([friendlyName, entityId]: [string, any]) => {
            if (entityId && typeof entityId === 'string') {
                addDevice(friendlyName, entityId);
            }
        });
    }
```

**Conclusion:** Only "Office" was shown because:
1. The system matched "office" from the query to an actual device/area entity
2. Generic terms like "lights" were filtered out (as per `genericTerms` filter)
3. The "desk sensor" may not have been matched or may have been filtered
4. Only devices that exist in Home Assistant AND are in `validated_entities` are displayed

## 2. YAML Generation Status

### Was YAML Created for the First Suggestion?

**Answer: NO** - YAML was NOT created for the first suggestion shown in the screenshot.

**Evidence:**

1. **Phase-Based Architecture:**
   - **Phase 1 (Description Only):** Suggestions are generated with descriptions, triggers, and actions - NO YAML
   - **Phase 2 (YAML Generation):** YAML is ONLY created when user clicks "APPROVE & CREATE"

2. **Code Evidence:**

```2422:2506:services/ai-automation-service/src/api/ask_ai_router.py
@router.post("/query", response_model=AskAIQueryResponse, status_code=status.HTTP_201_CREATED)
async def process_natural_language_query(
    request: AskAIQueryRequest,
    db: AsyncSession = Depends(get_db)
) -> AskAIQueryResponse:
    """
    Process natural language query and generate automation suggestions.
    
    This is the main endpoint for the Ask AI tab.
    """
    # Step 1: Extract entities using Home Assistant
    entities = await extract_entities_with_ha(request.query)
    
    # Step 2: Generate suggestions using OpenAI + entities
    suggestions = await generate_suggestions_from_query(
        request.query, 
        entities, 
        request.user_id
    )
    # ... NO YAML generation here
```

3. **YAML Generation Only on Approval:**

```3618:3695:services/ai-automation-service/src/api/ask_ai_router.py
@router.post("/query/{query_id}/suggestions/{suggestion_id}/approve")
async def approve_suggestion_from_query(
    query_id: str,
    suggestion_id: str,
    request: Optional[ApproveSuggestionRequest] = Body(default=None),
    db: AsyncSession = Depends(get_db),
    ha_client: HomeAssistantClient = Depends(get_ha_client),
    openai_client: OpenAIClient = Depends(get_openai_client)
) -> Dict[str, Any]:
    """
    Approve a suggestion and create the automation in Home Assistant.
    """
    # ... fetch suggestion ...
    
    # Generate YAML for the suggestion (validated_entities already in final_suggestion)
    try:
        automation_yaml = await generate_automation_yaml(final_suggestion, query.original_query, [], db_session=db, ha_client=ha_client)
```

4. **UI Button Indicates Action:**

The screenshot shows "✓ APPROVE & CREATE" button, which means:
- User has NOT yet clicked it
- YAML has NOT been generated
- Automation has NOT been created

**When YAML is Created:**
- User clicks "APPROVE & CREATE" button
- Frontend calls `POST /api/v1/ask-ai/query/{query_id}/suggestions/{suggestion_id}/approve`
- Backend generates YAML using `generate_automation_yaml()`
- YAML is validated and automation is created in Home Assistant

## 3. Complete Call Tree

### High-Level Flow

```
User Query: "when I trigger my desk sensor, I want the lights to in the office..."
    ↓
POST /api/v1/ask-ai/query
    ↓
process_natural_language_query()
    ├──> Step 1: extract_entities_with_ha()
    │    │
    │    ├──> MultiModelEntityExtractor.extract_entities()
    │    │    ├──> Try NER (BERT-based, ~50ms)
    │    │    │    └──> dslim/bert-base-NER model
    │    │    │         └──> Detects: "office" (area), "lights" (device), "desk sensor" (device)
    │    │    │
    │    │    └──> Enhance with device intelligence
    │    │         ├──> GET /api/discovery/devices?area=office
    │    │         │    └──> device-intelligence-service:8028
    │    │         │         └──> Returns: All devices in office area
    │    │         │
    │    │         ├──> For each device: GET /api/discovery/devices/{device_id}
    │    │         │    └──> Returns: Full device details (capabilities, health_score, etc.)
    │    │         │
    │    │         └──> Fuzzy match "lights" and "desk sensor" against all devices
    │    │              └──> Returns: Matched devices with entity_ids
    │    │
    │    └──> Return: List[Dict] with enriched entities
    │
    ├──> Step 2: generate_suggestions_from_query()
    │    │
    │    ├──> Resolve entity IDs from extracted entities
    │    │    ├──> Extract entity_ids from enriched entities
    │    │    └──> Expand group entities to individual members
    │    │
    │    ├──> Enrich entities comprehensively
    │    │    ├──> enrich_entities_comprehensively()
    │    │    │    ├──> Fetch from HA API (state, attributes)
    │    │    │    ├──> Fetch from device-intelligence-service (capabilities)
    │    │    │    └──> Fetch from data-api (historical patterns, optional)
    │    │    │
    │    │    └──> Build entity_context_json
    │    │         └──> Format all entity data for OpenAI prompt
    │    │
    │    ├──> Build unified prompt
    │    │    └──> UnifiedPromptBuilder.build_query_prompt()
    │    │         ├──> System prompt (AI persona, guidelines)
    │    │         └──> User prompt (query + entity context)
    │    │
    │    ├──> Generate suggestions with OpenAI
    │    │    └──> OpenAIClient.generate_with_unified_prompt()
    │    │         ├──> AsyncOpenAI.chat.completions.create()
    │    │         │    ├──> Model: gpt-4o-mini
    │    │         │    ├──> Temperature: 0.7
    │    │         │    ├──> Max tokens: 1200
    │    │         │    └──> Response format: JSON
    │    │         │
    │    │         └──> Parse JSON response
    │    │              └──> Returns: List of suggestion objects
    │    │
    │    └──> Process each suggestion
    │         ├──> Pre-consolidate device names (remove generic terms)
    │         ├──> Deduplicate devices
    │         ├──> Map devices to entities (map_devices_to_entities)
    │         │    ├──> Exact match by friendly_name
    │         │    ├──> Fuzzy match (substring + area context)
    │         │    └──> Domain match (fallback)
    │         │
    │         ├──> Validate entities exist in HA
    │         │    └──> verify_entities_exist_in_ha()
    │         │         └──> Ensemble validation (HA API + embeddings)
    │         │
    │         ├──> Consolidate devices_involved
    │         │    └──> Remove redundant mappings
    │         │
    │         └──> Build suggestion object
    │              ├──> suggestion_id
    │              ├──> description
    │              ├──> trigger_summary
    │              ├──> action_summary
    │              ├──> devices_involved (consolidated)
    │              ├──> validated_entities (friendly_name → entity_id mapping)
    │              ├──> capabilities_used
    │              ├──> confidence
    │              └──> status: 'draft'
    │
    ├──> Step 3: Calculate confidence
    │    └──> Formula: min(0.9, 0.5 + (len(entities) * 0.1) + (len(suggestions) * 0.1))
    │
    ├──> Step 4: Determine parsed intent
    │    └──> Keywords matching (automation/control/monitoring/energy/general)
    │
    ├──> Step 5: Save to database
    │    └──> AskAIQueryModel (SQLite)
    │         ├──> query_id
    │         ├──> original_query
    │         ├──> extracted_entities (JSON)
    │         ├──> suggestions (JSON)
    │         └──> confidence
    │
    └──> Return AskAIQueryResponse
         └──> Frontend displays suggestions
```

### Approval Flow (When User Clicks "APPROVE & CREATE")

```
User clicks "APPROVE & CREATE"
    ↓
POST /api/v1/ask-ai/query/{query_id}/suggestions/{suggestion_id}/approve
    ↓
approve_suggestion_from_query()
    ├──> Fetch query and suggestion from database
    │
    ├──> Apply user filters (if provided)
    │    ├──> Filter validated_entities by selected_entity_ids
    │    └──> Apply custom_entity_mapping
    │
    ├──> Generate YAML
    │    └──> generate_automation_yaml()
    │         ├──> Build YAML generation prompt
    │         │    ├──> System prompt (YAML expert instructions)
    │         │    └──> User prompt (suggestion + validated entities)
    │         │
    │         ├──> Call OpenAI API
    │         │    └──> Generate YAML content
    │         │
    │         ├──> Validate YAML syntax
    │         │    └──> yaml_lib.safe_load()
    │         │
    │         └──> Fix YAML structure (if needed)
    │              └──> YAMLStructureValidator
    │
    ├──> Final validation
    │    └──> Verify ALL entity IDs in YAML exist in HA
    │         └──> EntityIDValidator._extract_all_entity_ids()
    │
    ├──> Safety validation
    │    └──> SafetyValidator.validate_automation()
    │         └──> Check for dangerous operations
    │
    ├──> Create automation in Home Assistant
    │    └──> ha_client.create_automation(automation_yaml)
    │         └──> POST /api/config/automation/config/{automation_id}
    │              └──> Home Assistant API
    │
    └──> Return response
         ├──> status: 'approved'
         ├──> automation_id
         ├──> automation_yaml
         └──> safety_report
```

### Key Components

#### Entity Extraction
- **Multi-Model Approach:** NER (fast) → OpenAI (smart) → Pattern (fallback)
- **Device Intelligence Enhancement:** Fetches capabilities, health scores, manufacturer/model
- **Area Expansion:** Area entities expand to all devices in that area
- **Fuzzy Matching:** Device entities matched by name variations

#### Suggestion Generation
- **OpenAI GPT-4o-mini:** Generates 3-5 creative suggestions
- **Entity Context:** Full device capabilities and constraints included in prompt
- **Progressive Creativity:** Suggestions progress from close match to creative ideas

#### Device Mapping
- **Three-Tier Matching:** Exact → Fuzzy → Domain
- **Deduplication:** Removes redundant mappings (multiple friendly names → same entity_id)
- **Validation:** Only includes entities that exist in Home Assistant

#### YAML Generation (On Approval Only)
- **Separate Endpoint:** Only called when user approves
- **Entity Validation:** Uses validated_entities from suggestion
- **Safety Checks:** Validates automation safety
- **HA Integration:** Creates automation directly in Home Assistant

## 4. Key Findings

### Why Only 1 Device Appeared

1. **Generic Term Filtering:**
   - Terms like "lights", "sensor" are filtered out as generic
   - Only specific device names (like "Office") pass through

2. **Entity Matching:**
   - "office" likely matched to an actual device/area entity
   - "desk sensor" may not have been matched or may have been filtered
   - "lights" was filtered as generic term

3. **Validation:**
   - Only devices that exist in Home Assistant are shown
   - Only devices in `validated_entities` are displayed

### YAML Generation Status

- **NOT Created:** YAML is only generated on approval
- **Button State:** "APPROVE & CREATE" indicates user hasn't approved yet
- **Architecture:** Phase-based (description → YAML on approval)

### Call Tree Complexity

- **5 Major Phases:** Entity extraction → Enrichment → Suggestion generation → Mapping → Validation
- **Multiple Services:** HA API, device-intelligence-service, OpenAI API, data-api
- **Async Operations:** Multiple parallel API calls for performance
- **Error Handling:** Fallbacks at each stage

## 5. Recommendations

### For Device Selection

1. **Improve Generic Term Handling:**
   - Consider context when filtering generic terms
   - "lights" in "office lights" should be kept if it's part of a specific device name

2. **Better Device Matching:**
   - Improve fuzzy matching for "desk sensor"
   - Consider partial word matching (e.g., "desk sensor" → "Desk Motion Sensor")

3. **Display All Matched Devices:**
   - Show trigger devices (desk sensor) separately from action devices (lights)
   - Don't filter out trigger devices from display

### For YAML Generation

- **Status:** Architecture is correct - YAML should only be generated on approval
- **Consider:** Optional preview YAML generation (not saved) for user review

### For Call Tree

- **Performance:** Good use of async operations
- **Observability:** Add more detailed logging for device matching decisions
- **Caching:** Consider caching entity enrichment results

## 6. References

- [AI Automation Suggestion Call Tree](../docs/architecture/ai-automation-suggestion-call-tree.md)
- [Ask AI Router Implementation](../../services/ai-automation-service/src/api/ask_ai_router.py)
- [Frontend Ask AI Component](../../services/ai-automation-ui/src/pages/AskAI.tsx)

## 7. Summary

**Device Selection:**
- Only "Office" shown due to generic term filtering and entity matching logic
- "lights" and "desk sensor" were filtered or not matched

**YAML Generation:**
- NOT created - only generated on user approval
- Architecture follows phase-based approach (description → YAML on approval)

**Call Tree:**
- Complex multi-stage pipeline with entity extraction, enrichment, suggestion generation, and validation
- Multiple service integrations (HA, device-intelligence, OpenAI)
- Async operations for performance optimization

