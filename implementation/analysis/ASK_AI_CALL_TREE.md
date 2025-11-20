# Ask AI - Complete Call Tree Documentation

**Last Updated:** January 2025  
**Service:** ai-automation-service (Port 8024)  
**UI Service:** ai-automation-ui (Port 3001)  
**Endpoint:** http://localhost:3001/ask-ai

## Overview

This document traces the complete call tree from when a user submits a prompt in the Ask AI interface to the creation of an automation in Home Assistant via API call. The flow includes:

1. **Frontend (User Input)** → User sends prompt
2. **Backend (Query Processing)** → Entity extraction and suggestion generation
3. **Frontend (User Approval)** → User approves a suggestion
4. **Backend (YAML Generation)** → YAML creation from suggestion
5. **Backend (Home Assistant API)** → Automation creation in Home Assistant

---

## Phase 1: User Submits Prompt

### 1.1 Frontend: AskAI.tsx - handleSendMessage()

**File:** `services/ai-automation-ui/src/pages/AskAI.tsx`  
**Function:** `handleSendMessage()`  
**Lines:** 323-466

**Flow:**
```typescript
// User types prompt and clicks "Send"
handleSendMessage()
  ↓
// Create user message object
const userMessage: ChatMessage = {
  id: `user-${Date.now()}`,
  type: 'user',
  content: inputValue,
  timestamp: new Date()
}
  ↓
// Add to messages array
setMessages(prev => [...prev, userMessage])
  ↓
// Call API
api.askAIQuery(inputValue, {
  conversation_context: conversationContext,
  conversation_history: messages
})
```

**Key Code:**
```323:356:services/ai-automation-ui/src/pages/AskAI.tsx
const handleSendMessage = async () => {
  const inputValue = inputRef.current?.value.trim();
  if (!inputValue || isLoading) return;

  const userMessage: ChatMessage = {
    id: `user-${Date.now()}`,
    type: 'user',
    content: inputValue,
    timestamp: new Date()
  };

  setMessages(prev => [...prev, userMessage]);
  setInputValue('');
  setIsLoading(true);
  setIsTyping(true);

  try {
    // Use v2 API if enabled
    if (USE_V2_API) {
      return await handleSendMessageV2(inputValue, userMessage);
    }

    // v1 API (legacy)
    // Pass context and conversation history to API
    const response = await api.askAIQuery(inputValue, {
      conversation_context: conversationContext,
      conversation_history: messages
        .filter(msg => msg.type !== 'ai' || msg.id !== 'welcome')
        .map(msg => ({
          role: msg.type,
          content: msg.content,
          timestamp: msg.timestamp.toISOString()
        }))
    });
```

### 1.2 Frontend: api.ts - askAIQuery()

**File:** `services/ai-automation-ui/src/services/api.ts`  
**Function:** `askAIQuery()`  
**Lines:** 495-518

**Flow:**
```typescript
askAIQuery(query, options)
  ↓
// Build request body
const requestBody = {
  query,
  user_id: options?.userId || 'anonymous',
  context: options?.conversation_context,
  conversation_history: options?.conversation_history
}
  ↓
// POST to backend
fetchJSON(`${API_BASE_URL}/v1/ask-ai/query`, {
  method: 'POST',
  body: JSON.stringify(requestBody)
})
```

**Key Code:**
```495:518:services/ai-automation-ui/src/services/api.ts
async askAIQuery(query: string, options?: {
  conversation_context?: any;
  conversation_history?: any[];
  userId?: string;
}): Promise<any> {
  const requestBody: any = {
    query,
    user_id: options?.userId || 'anonymous'
  };
  
  // Add context and history if provided
  if (options?.conversation_context) {
    requestBody.context = options.conversation_context;
  }
  
  if (options?.conversation_history) {
    requestBody.conversation_history = options.conversation_history;
  }
  
  return fetchJSON(`${API_BASE_URL}/v1/ask-ai/query`, {
    method: 'POST',
    body: JSON.stringify(requestBody),
  });
},
```

**HTTP Request:**
```
POST http://localhost:8024/api/v1/ask-ai/query
Content-Type: application/json

{
  "query": "Turn on the office lights when I arrive",
  "user_id": "anonymous",
  "context": {...},
  "conversation_history": [...]
}
```

---

## Phase 2: Backend Processes Query

### 2.1 Backend: ask_ai_router.py - process_natural_language_query()

**File:** `services/ai-automation-service/src/api/ask_ai_router.py`  
**Function:** `process_natural_language_query()`  
**Lines:** 4495-4800+

**Flow:**
```python
@router.post("/query")
async def process_natural_language_query(request: AskAIQueryRequest)
  ↓
# Generate query_id
query_id = f"query-{uuid.uuid4().hex[:8]}"
  ↓
# Step 1: Extract entities using Home Assistant Conversation API
entities = await extract_entities_with_ha(request.query)
  ↓
# Step 1.5: Resolve generic entities to specific devices
entities = await resolve_entities_to_specific_devices(entities, ha_client)
  ↓
# Step 1.6: Check for clarification needs
clarification_detector.detect_ambiguities(...)
  ↓
# Step 2: Generate suggestions
suggestions = await generate_suggestions_from_query(...)
  ↓
# Step 3: Return response
return AskAIQueryResponse(...)
```

**Key Code:**
```4495:4531:services/ai-automation-service/src/api/ask_ai_router.py
@router.post("/query", response_model=AskAIQueryResponse, status_code=status.HTTP_201_CREATED)
async def process_natural_language_query(
    request: AskAIQueryRequest,
    db: AsyncSession = Depends(get_db)
) -> AskAIQueryResponse:
    """
    Process natural language query and generate automation suggestions.
    
    This is the main endpoint for the Ask AI tab.
    """
    start_time = datetime.now()
    query_id = f"query-{uuid.uuid4().hex[:8]}"
    
    logger.info(f"🤖 Processing Ask AI query: {request.query}")
    
    # Extract area/location from query if specified (for area-based filtering)
    from ..utils.area_detection import extract_area_from_request
    area_filter = extract_area_from_request(request.query)
    if area_filter:
        logger.info(f"📍 Detected area filter in clarification phase: '{area_filter}'")
    
    try:
        # Step 1: Extract entities using Home Assistant
        entities = await extract_entities_with_ha(request.query)
        
        # Step 1.5: Resolve generic device entities to specific devices BEFORE ambiguity detection
        # This ensures the ambiguity prompt shows specific device names (e.g., "Office Front Left")
        # instead of generic types (e.g., "hue lights")
        try:
            ha_client_for_resolution = get_ha_client()
            if ha_client_for_resolution:
                entities = await resolve_entities_to_specific_devices(entities, ha_client_for_resolution)
                logger.info(f"✅ Early device resolution completed: {len(entities)} entities (including specific devices)")
        except (HTTPException, Exception) as e:
            # HA client not available or resolution failed - continue with generic entities
            logger.debug(f"ℹ️ Early device resolution skipped (HA client unavailable or failed): {e}")
        
        # Step 1.6: Check for clarification needs (NEW)
        clarification_detector, question_generator, _, confidence_calculator = await get_clarification_services(db)
```

### 2.2 Backend: ask_ai_router.py - generate_suggestions_from_query()

**File:** `services/ai-automation-service/src/api/ask_ai_router.py`  
**Function:** `generate_suggestions_from_query()`  
**Lines:** 3263-4500+

**Flow:**
```python
async def generate_suggestions_from_query(query, entities, user_id, ...)
  ↓
# Resolve and enrich entities with full attribute data
enriched_entities = await resolve_and_enrich_entities(...)
  ↓
# Build prompt with entity context
prompt = build_prompt_with_entity_context(...)
  ↓
# Call OpenAI to generate suggestions
response = await openai_client.client.chat.completions.create(...)
  ↓
# Parse suggestions from response
suggestions = parse_suggestions_from_response(response)
  ↓
# Validate entities for each suggestion
for suggestion in suggestions:
    validated_entities = await validate_entities_in_suggestion(...)
    suggestion['validated_entities'] = validated_entities
  ↓
return suggestions
```

**Key Code:**
```3263:3295:services/ai-automation-service/src/api/ask_ai_router.py
async def generate_suggestions_from_query(
    query: str, 
    entities: List[Dict[str, Any]], 
    user_id: str,
    db_session: Optional[AsyncSession] = None,
    clarification_context: Optional[Dict[str, Any]] = None,  # NEW: Clarification Q&A
    query_id: Optional[str] = None  # NEW: Query ID for metrics tracking
) -> List[Dict[str, Any]]:
    """Generate automation suggestions based on query and entities"""
    if not openai_client:
        raise ValueError("OpenAI client not available - cannot generate suggestions")
    
    try:
        # Use unified prompt builder for consistent prompt generation
        from ..prompt_building.unified_prompt_builder import UnifiedPromptBuilder
        
        unified_builder = UnifiedPromptBuilder(device_intelligence_client=_device_intelligence_client)
        
        # NEW: Resolve and enrich entities with full attribute data (like YAML generation does)
        entity_context_json = ""
        resolved_entity_ids = []
        enriched_data = {}  # Initialize at function level for use in suggestion building
        enriched_entities: List[Dict[str, Any]] = []
        
        try:
            logger.info("🔍 Resolving and enriching entities for suggestion generation...")
            
            # Initialize HA client and entity validator
            ha_client = HomeAssistantClient(
                ha_url=settings.ha_url,
                access_token=settings.ha_token
            ) if settings.ha_url and settings.ha_token else None
            
            if ha_client:
```

**Response Structure:**
```json
{
  "query_id": "query-abc123",
  "clarification_needed": false,
  "suggestions": [
    {
      "suggestion_id": "sugg-xyz789",
      "title": "Office Lights Automation",
      "description": "Turn on office lights when motion detected",
      "trigger_summary": "Motion sensor detects movement",
      "action_summary": "Turn on office lights",
      "devices_involved": ["Office Lights", "Motion Sensor"],
      "validated_entities": {
        "Office Lights": "light.office_ceiling",
        "Motion Sensor": "binary_sensor.office_motion"
      },
      "enriched_entity_context": "{...}",
      "status": "pending"
    }
  ],
  "extracted_entities": [...],
  "confidence": 0.85
}
```

---

## Phase 3: User Approves Suggestion

### 3.1 Frontend: ConversationalSuggestionCard.tsx - handleApprove()

**File:** `services/ai-automation-ui/src/components/ConversationalSuggestionCard.tsx`  
**Function:** `handleApprove()`  
**Lines:** 144-151

**Flow:**
```typescript
// User clicks "Approve" button on suggestion card
handleApprove()
  ↓
// Call onApprove callback with suggestion ID and custom mappings
onApprove(suggestion.id, customMappings)
  ↓
// Triggers handleSuggestionAction in parent component
```

**Key Code:**
```144:151:services/ai-automation-ui/src/components/ConversationalSuggestionCard.tsx
const handleApprove = async () => {
  try {
    await onApprove(suggestion.id, Object.keys(customMappings).length > 0 ? customMappings : undefined);
    toast.success('✅ Automation created successfully!');
  } catch (error) {
    toast.error('❌ Failed to create automation');
  }
};
```

### 3.2 Frontend: AskAI.tsx - handleSuggestionAction()

**File:** `services/ai-automation-ui/src/pages/AskAI.tsx`  
**Function:** `handleSuggestionAction()`  
**Lines:** 534-900+

**Flow:**
```typescript
handleSuggestionAction(suggestionId, 'approve', undefined, customMappings)
  ↓
// Find message containing the suggestion
const messageWithQuery = messages.find(...)
const queryId = messageWithQuery?.id
  ↓
// Extract device info and selected entities
const deviceInfo = extractDeviceInfo(suggestion)
const selectedEntityIds = getSelectedEntityIds(suggestionId, deviceInfo)
  ↓
// Show loading state
setReverseEngineeringStatus({ visible: true, action: 'approve' })
  ↓
// Call API
const response = await api.approveAskAISuggestion(
  queryId,
  suggestionId,
  selectedEntityIds,
  customMappings
)
```

**Key Code:**
```827:871:services/ai-automation-ui/src/pages/AskAI.tsx
try {
  // Get selected entity IDs for this suggestion
  const messageWithSuggestion = messages.find(msg => 
    msg.suggestions?.some(s => s.suggestion_id === suggestionId)
  );
  const suggestion = messageWithSuggestion?.suggestions?.find(s => s.suggestion_id === suggestionId);
  // Extract device info inline (since it's used in render too)
  const deviceInfo = suggestion ? (() => {
    const devices: Array<{ friendly_name: string; entity_id: string; domain?: string; selected?: boolean }> = [];
    const seenEntityIds = new Set<string>();
    const addDevice = (friendlyName: string, entityId: string, domain?: string) => {
      if (entityId && !seenEntityIds.has(entityId)) {
        let isSelected = true;
        if (deviceSelections.has(suggestionId)) {
          const selectionMap = deviceSelections.get(suggestionId)!;
          if (selectionMap.has(entityId)) {
            isSelected = selectionMap.get(entityId)!;
          }
        }
        devices.push({ friendly_name: friendlyName, entity_id: entityId, domain: domain || entityId.split('.')[0], selected: isSelected });
        seenEntityIds.add(entityId);
      }
    };
    if (suggestion.validated_entities) {
      Object.entries(suggestion.validated_entities).forEach(([fn, eid]: [string, any]) => {
        if (eid && typeof eid === 'string') addDevice(fn, eid);
      });
    }
    return devices;
  })() : undefined;
  const selectedEntityIds = getSelectedEntityIds(suggestionId, deviceInfo);
  
  console.log('📡 [APPROVE] Calling API', { 
    queryId, 
    suggestionId, 
    selectedEntityIdsCount: selectedEntityIds.length,
    hasCustomMappings: !!(customMappings && Object.keys(customMappings).length > 0)
  });
  
  const response = await api.approveAskAISuggestion(
    queryId, 
    suggestionId, 
    selectedEntityIds.length > 0 ? selectedEntityIds : undefined,
    customMappings && Object.keys(customMappings).length > 0 ? customMappings : undefined
  );
```

### 3.3 Frontend: api.ts - approveAskAISuggestion()

**File:** `services/ai-automation-ui/src/services/api.ts`  
**Function:** `approveAskAISuggestion()`  
**Lines:** 534-551

**Flow:**
```typescript
approveAskAISuggestion(queryId, suggestionId, selectedEntityIds, customEntityMapping)
  ↓
// Build request body
const body = {
  selected_entity_ids: selectedEntityIds,
  custom_entity_mapping: customEntityMapping
}
  ↓
// POST to backend
fetchJSON(`${API_BASE_URL}/v1/ask-ai/query/${queryId}/suggestions/${suggestionId}/approve`, {
  method: 'POST',
  body: JSON.stringify(body)
})
```

**Key Code:**
```534:551:services/ai-automation-ui/src/services/api.ts
async approveAskAISuggestion(
  queryId: string, 
  suggestionId: string, 
  selectedEntityIds?: string[],
  customEntityMapping?: Record<string, string>
): Promise<any> {
  const body: any = {};
  if (selectedEntityIds && selectedEntityIds.length > 0) {
    body.selected_entity_ids = selectedEntityIds;
  }
  if (customEntityMapping && Object.keys(customEntityMapping).length > 0) {
    body.custom_entity_mapping = customEntityMapping;
  }
  return fetchJSON(`${API_BASE_URL}/v1/ask-ai/query/${queryId}/suggestions/${suggestionId}/approve`, {
    method: 'POST',
    body: Object.keys(body).length > 0 ? JSON.stringify(body) : undefined,
  });
},
```

**HTTP Request:**
```
POST http://localhost:8024/api/v1/ask-ai/query/query-abc123/suggestions/sugg-xyz789/approve
Content-Type: application/json

{
  "selected_entity_ids": ["light.office_ceiling"],
  "custom_entity_mapping": {
    "Office Lights": "light.office_ceiling"
  }
}
```

---

## Phase 4: Backend Generates YAML

### 4.1 Backend: ask_ai_router.py - approve_suggestion_from_query()

**File:** `services/ai-automation-service/src/api/ask_ai_router.py`  
**Function:** `approve_suggestion_from_query()`  
**Lines:** 7518-8000+

**Flow:**
```python
@router.post("/query/{query_id}/suggestions/{suggestion_id}/approve")
async def approve_suggestion_from_query(query_id, suggestion_id, request, db, ha_client, openai_client)
  ↓
# Get query from database
query = await db.get(AskAIQueryModel, query_id)
  ↓
# Find suggestion in query.suggestions
suggestion = find_suggestion_by_id(query.suggestions, suggestion_id)
  ↓
# Validate validated_entities exists
validated_entities = suggestion.get('validated_entities')
  ↓
# Apply user filters (selected_entity_ids, custom_entity_mapping)
final_suggestion = apply_user_filters(suggestion, request)
  ↓
# Generate YAML
automation_yaml = await generate_automation_yaml(final_suggestion, query.original_query, ...)
  ↓
# Validate YAML entities exist in HA
await validate_all_entities_in_yaml(automation_yaml, ha_client)
  ↓
# Run safety checks
safety_report = await safety_validator.validate_automation(automation_yaml, ...)
  ↓
# Create automation in Home Assistant
creation_result = await ha_client.create_automation(automation_yaml)
  ↓
# Return result
return {
  "suggestion_id": suggestion_id,
  "query_id": query_id,
  "status": "success",
  "automation_id": creation_result.get('automation_id'),
  ...
}
```

**Key Code:**
```7518:7615:services/ai-automation-service/src/api/ask_ai_router.py
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
    # Phase 1: Add comprehensive logging for debugging
    logger.info(f"🚀 [APPROVAL START] query_id={query_id}, suggestion_id={suggestion_id}")
    logger.info(f"📝 [APPROVAL] Request body: {request}")
    
    try:
        # Get the query from database
        logger.info(f"🔍 [APPROVAL] Fetching query record: {query_id}")
        query = await db.get(AskAIQueryModel, query_id)
        if not query:
            logger.error(f"❌ [APPROVAL] Query {query_id} not found in database")
            raise HTTPException(status_code=404, detail=f"Query {query_id} not found")
        logger.info(f"✅ [APPROVAL] Found query with {len(query.suggestions)} suggestions")
        
        # Find the specific suggestion
        logger.info(f"🔍 [APPROVAL] Searching for suggestion_id={suggestion_id}")
        suggestion = None
        for s in query.suggestions:
            if s.get('suggestion_id') == suggestion_id:
                suggestion = s
                break
        
        if not suggestion:
            logger.error(f"❌ [APPROVAL] Suggestion {suggestion_id} not found in query suggestions")
            raise HTTPException(status_code=404, detail=f"Suggestion {suggestion_id} not found")
        
        logger.info(f"✅ [APPROVAL] Found suggestion: {suggestion.get('title', 'Untitled')[:50]}")
        
        # Fail fast if validated_entities is missing - should already be set during suggestion creation
        validated_entities = suggestion.get('validated_entities')
        if not validated_entities or not isinstance(validated_entities, dict) or len(validated_entities) == 0:
            logger.error(f"❌ Suggestion {suggestion_id} missing validated_entities - should be set during creation")
            raise HTTPException(
                status_code=400,
                detail=f"Suggestion {suggestion_id} is missing validated entities. This should be set during suggestion creation. Please regenerate the suggestion."
            )
        
        logger.info(f"✅ Using validated_entities from suggestion: {len(validated_entities)} entities")
        
        # Start with suggestion as-is (no component restoration - not implemented)
        final_suggestion = suggestion.copy()
        
        # Apply user filters if provided
        if request:
            # Filter by selected_entity_ids if provided
            if request.selected_entity_ids and len(request.selected_entity_ids) > 0:
                logger.info(f"🎯 Filtering validated_entities to selected devices: {request.selected_entity_ids}")
                final_suggestion['validated_entities'] = {
                    friendly_name: entity_id 
                    for friendly_name, entity_id in validated_entities.items()
                    if entity_id in request.selected_entity_ids
                }
                logger.info(f"✅ Filtered to {len(final_suggestion['validated_entities'])} selected entities")
            
            # Apply custom entity mappings if provided
            if request.custom_entity_mapping and len(request.custom_entity_mapping) > 0:
                logger.info(f"🔧 Applying custom entity mappings: {request.custom_entity_mapping}")
                # Verify custom entity IDs exist in Home Assistant
                custom_entity_ids = list(request.custom_entity_mapping.values())
                if ha_client:
                    verification_results = await verify_entities_exist_in_ha(custom_entity_ids, ha_client)
                    # Apply only verified mappings
                    for friendly_name, new_entity_id in request.custom_entity_mapping.items():
                        if verification_results.get(new_entity_id, False):
                            final_suggestion['validated_entities'][friendly_name] = new_entity_id
                            logger.info(f"✅ Applied custom mapping: '{friendly_name}' → {new_entity_id}")
                        else:
                            logger.warning(f"⚠️ Custom entity_id {new_entity_id} for '{friendly_name}' does not exist in HA - skipped")
                else:
                    # No HA client - apply without verification
                    logger.warning(f"⚠️ No HA client - applying custom mappings without verification")
                    final_suggestion['validated_entities'].update(request.custom_entity_mapping)
        
        # Generate YAML for the suggestion (validated_entities already in final_suggestion)
        logger.info(f"🔧 [YAML_GEN] Starting YAML generation for suggestion {suggestion_id}")
        logger.info(f"📋 [YAML_GEN] Validated entities: {final_suggestion.get('validated_entities')}")
        logger.info(f"📝 [YAML_GEN] Suggestion title: {final_suggestion.get('title', 'Untitled')}")
        
        # Track which model generated the suggestion for metrics update
        suggestion_model_used = None
        if suggestion.get('debug') and suggestion['debug'].get('model_used'):
            suggestion_model_used = suggestion['debug']['model_used']
        elif suggestion.get('debug') and suggestion['debug'].get('token_usage'):
            suggestion_model_used = suggestion['debug']['token_usage'].get('model')
        
        try:
            automation_yaml = await generate_automation_yaml(final_suggestion, query.original_query, [], db_session=db, ha_client=ha_client)
```

### 4.2 Backend: ask_ai_router.py - generate_automation_yaml()

**File:** `services/ai-automation-service/src/api/ask_ai_router.py`  
**Function:** `generate_automation_yaml()`  
**Lines:** 1874-2500+

**Flow:**
```python
async def generate_automation_yaml(suggestion, original_query, entities, db_session, ha_client)
  ↓
# Get validated_entities from suggestion
validated_entities = suggestion.get('validated_entities')
  ↓
# Get enriched_entity_context from suggestion
entity_context_json = suggestion.get('enriched_entity_context', '')
  ↓
# Build validated entities text for prompt
validated_entities_text = build_validated_entities_prompt(validated_entities, entity_context_json)
  ↓
# Build comprehensive prompt with examples and rules
prompt = build_yaml_generation_prompt(suggestion, original_query, validated_entities_text)
  ↓
# Call OpenAI to generate YAML
response = await openai_client.client.chat.completions.create(
  model=openai_client.model,
  messages=[
    {"role": "system", "content": "You are a Home Assistant 2025 YAML automation expert..."},
    {"role": "user", "content": prompt}
  ],
  temperature=0.1,
  response_format={"type": "json_object"} or "text"
)
  ↓
# Extract YAML from response
yaml_content = extract_yaml_from_response(response)
  ↓
# Return YAML string
return yaml_content
```

**Key Code:**
```1874:1962:services/ai-automation-service/src/api/ask_ai_router.py
async def generate_automation_yaml(
    suggestion: Dict[str, Any], 
    original_query: str, 
    entities: Optional[List[Dict[str, Any]]] = None,
    db_session: Optional[AsyncSession] = None,
    ha_client: Optional[HomeAssistantClient] = None
) -> str:
    """
    Generate Home Assistant automation YAML from a suggestion.
    
    Uses OpenAI to convert the natural language suggestion into valid HA YAML.
    Now includes entity validation to prevent "Entity not found" errors.
    Includes capability details for more precise YAML generation.
    
    Args:
        suggestion: Suggestion dictionary with description, trigger_summary, action_summary, devices_involved
        original_query: Original user query for context
        entities: Optional list of entities with capabilities for enhanced context
        db_session: Optional database session for alias support
    
    Returns:
        YAML string for the automation
    """
    logger.info(f"🚀 GENERATE_YAML CALLED - Query: {original_query[:50]}...")
    logger.info(f"🚀 Suggestion: {suggestion}")
    
    if not openai_client:
        raise ValueError("OpenAI client not initialized - cannot generate YAML")
    
    # Get validated_entities from suggestion (already set during suggestion creation)
    validated_entities = suggestion.get('validated_entities', {})
    if not validated_entities or not isinstance(validated_entities, dict):
        devices_involved = suggestion.get('devices_involved', [])
        error_msg = (
            f"Cannot generate automation YAML: No validated entities found. "
            f"The system could not map any of {len(devices_involved)} requested devices "
            f"({', '.join(devices_involved[:5])}{'...' if len(devices_involved) > 5 else ''}) "
            f"to actual Home Assistant entities."
        )
        logger.error(f"❌ {error_msg}")
        raise ValueError(error_msg)
    
    # Use enriched_entity_context from suggestion (already computed during creation)
    entity_context_json = suggestion.get('enriched_entity_context', '')
    if entity_context_json:
        logger.info("✅ Using cached enriched entity context from suggestion")
    else:
        logger.warning("⚠️ No enriched_entity_context in suggestion (should be set during creation)")
    
    # Build validated entities text for prompt
    if validated_entities:
        # Build explicit mapping examples GENERICALLY (not hardcoded for specific terms)
        mapping_examples = []
        entity_id_list = []
        
        for term, entity_id in validated_entities.items():
            entity_id_list.append(f"- {term}: {entity_id}")
            # Build generic mapping instructions
            domain = entity_id.split('.')[0] if '.' in entity_id else 'unknown'
            term_variations = [term, term.lower(), term.upper(), term.title()]
            mapping_examples.append(
                f"  - If you see any variation of '{term}' (or domain '{domain}') in the description → use EXACTLY: {entity_id}"
            )
        
        mapping_text = ""
        if mapping_examples:
            mapping_text = f"""
EXPLICIT ENTITY ID MAPPINGS (use these EXACT mappings - ALL have been verified to exist in Home Assistant):
{chr(10).join(mapping_examples[:15])}

"""
        
        # Build dynamic example entity IDs for the prompt
        example_light = next((eid for eid in validated_entities.values() if eid.startswith('light.')), None)
        example_entity = list(validated_entities.values())[0] if validated_entities else '{EXAMPLE_ENTITY_ID}'
        
        validated_entities_text = f"""
VALIDATED ENTITIES (ALL verified to exist in Home Assistant - use these EXACT entity IDs):
{chr(10).join(entity_id_list)}
{mapping_text}
CRITICAL: Use ONLY the entity IDs listed above. Do NOT create new entity IDs.
Entity IDs must ALWAYS be in format: domain.entity (e.g., {example_entity})

COMMON MISTAKES TO AVOID:
❌ WRONG: entity_id: wled (missing domain prefix - will cause "Entity not found" error)
❌ WRONG: entity_id: WLED (missing domain prefix and wrong format)
❌ WRONG: entity_id: office (missing domain prefix - incomplete entity ID)
✅ CORRECT: entity_id: {example_entity} (complete domain.entity format from validated list above)
"""
```

**Example Generated YAML:**
```yaml
id: 'office_lights_automation_1704067200_abc12345'
alias: "Office Lights Automation"
description: "Turn on office lights when motion detected"
mode: single
trigger:
  - platform: state
    entity_id: binary_sensor.office_motion
    to: 'on'
action:
  - service: light.turn_on
    target:
      entity_id: light.office_ceiling
    data:
      brightness_pct: 100
```

---

## Phase 5: Backend Creates Automation in Home Assistant

### 5.1 Backend: ask_ai_router.py - Continue approve_suggestion_from_query()

**File:** `services/ai-automation-service/src/api/ask_ai_router.py`  
**Function:** `approve_suggestion_from_query()` (continued)  
**Lines:** 7898-8000+

**Flow:**
```python
# After YAML generation and validation...
  ↓
# Run safety checks
safety_validator = SafetyValidator(ha_client=ha_client)
safety_report = await safety_validator.validate_automation(automation_yaml, validated_entity_ids)
  ↓
# Create automation in Home Assistant
if ha_client:
    creation_result = await ha_client.create_automation(automation_yaml)
else:
    return error response
  ↓
# Return success response
return {
    "suggestion_id": suggestion_id,
    "query_id": query_id,
    "status": "success",
    "automation_id": creation_result.get('automation_id'),
    "safe": safety_report.get('safe', True),
    "warnings": safety_report.get('warnings', [])
}
```

**Key Code:**
```7884:7900:services/ai-automation-service/src/api/ask_ai_router.py
# Run safety checks
logger.info("🔒 Running safety validation...")
safety_validator = SafetyValidator(ha_client=ha_client)
safety_report = await safety_validator.validate_automation(
    automation_yaml,
    validated_entities=validated_entity_ids
)

# Log warnings but don't block unless critical
if safety_report.get('warnings'):
    logger.info(f"⚠️ Safety validation warnings: {len(safety_report.get('warnings', []))}")
if not safety_report.get('safe', True):
    logger.warning(f"⚠️ Safety validation found issues, but continuing (user can review)")

# Create automation in Home Assistant
if not ha_client:
```

### 5.2 Backend: ha_client.py - create_automation()

**File:** `services/ai-automation-service/src/clients/ha_client.py`  
**Function:** `create_automation()`  
**Lines:** 666-780

**Flow:**
```python
async def create_automation(automation_yaml, automation_id=None, force_new=True)
  ↓
# Validate the automation YAML first
validation = await self.validate_automation(automation_yaml)
if not validation.get('valid', False):
    return {"success": False, "error": "Validation failed: ..."}
  ↓
# Parse YAML
automation_data = yaml.safe_load(automation_yaml)
  ↓
# Generate unique automation ID
if force_new:
    timestamp = int(time.time())
    unique_suffix = uuid.uuid4().hex[:8]
    automation_data['id'] = f"{base_id}_{timestamp}_{unique_suffix}"
  ↓
automation_entity_id = f"automation.{automation_data['id']}"
  ↓
# POST to Home Assistant Config API
async with session.post(
    f"{self.ha_url}/api/config/automation/config/{automation_data['id']}",
    headers=self.headers,
    json=automation_data,
    timeout=aiohttp.ClientTimeout(total=30)
) as response:
  ↓
if response.status in [200, 201]:
    result = await response.json()
    # Enable the automation
    await self.enable_automation(automation_entity_id)
    return {
        "success": True,
        "automation_id": automation_entity_id,
        "message": "Automation created and enabled successfully"
    }
```

**Key Code:**
```666:780:services/ai-automation-service/src/clients/ha_client.py
async def create_automation(self, automation_yaml: str, automation_id: Optional[str] = None, force_new: bool = True) -> Dict[str, Any]:
    """
    Create or update an automation in Home Assistant.
    
    This writes the automation config directly to Home Assistant's configuration.
    
    Args:
        automation_yaml: YAML string for the automation
        automation_id: Optional automation entity ID to enforce (e.g. "automation.my_automation")
                      If provided and force_new=False, will update existing automation.
        force_new: If True (default), always generate a unique ID to create a new automation.
                  If False and automation_id is provided, will update existing automation.
    
    Returns:
        Dict with creation result including automation_id and status
    """
    try:
        # First validate the automation
        validation = await self.validate_automation(automation_yaml)
        if not validation.get('valid', False):
            return {
                "success": False,
                "error": f"Validation failed: {validation.get('error', 'Unknown error')}",
                "details": validation.get('details', [])
            }
        
        # Parse YAML
        automation_data = yaml.safe_load(automation_yaml)

        if not isinstance(automation_data, dict):
            raise ValueError("Invalid automation YAML: must be a dict")

        # Generate automation ID
        if automation_id:
            # Explicit ID provided
            base_id = automation_id.replace('automation.', '')
            if force_new:
                # Force new: append unique suffix even if ID is provided
                timestamp = int(time.time())
                unique_suffix = uuid.uuid4().hex[:8]
                automation_data['id'] = f"{base_id}_{timestamp}_{unique_suffix}"
                logger.info(f"🆕 Force new automation: {base_id} → {automation_data['id']}")
            else:
                # Update existing: use provided ID as-is
                automation_data['id'] = base_id
                logger.info(f"🔄 Updating existing automation: {automation_data['id']}")
        elif 'id' not in automation_data:
            # No ID in YAML: generate from alias
            alias = automation_data.get('alias', 'ai_automation')
            base_id = alias.lower().replace(' ', '_').replace('-', '_')
            if force_new:
                # Always create new: append unique suffix
                timestamp = int(time.time())
                unique_suffix = uuid.uuid4().hex[:8]
                automation_data['id'] = f"{base_id}_{timestamp}_{unique_suffix}"
                logger.info(f"🆕 Generated unique ID from alias '{alias}': {automation_data['id']}")
            else:
                # Use base ID (may update existing)
                automation_data['id'] = base_id
                logger.info(f"📝 Using base ID from alias '{alias}': {automation_data['id']}")
        else:
            # ID exists in YAML
            base_id = automation_data['id']
            if force_new:
                # Force new: append unique suffix to existing ID
                timestamp = int(time.time())
                unique_suffix = uuid.uuid4().hex[:8]
                automation_data['id'] = f"{base_id}_{timestamp}_{unique_suffix}"
                logger.info(f"🆕 Force new: {base_id} → {automation_data['id']}")
            else:
                # Use ID as-is (may update existing)
                logger.info(f"📝 Using ID from YAML: {automation_data['id']}")

        automation_entity_id = f"automation.{automation_data['id']}"
        
        # Create automation via HA REST API
        # Note: HA doesn't have a direct REST endpoint to create automations
        # We need to use the config/automation/config endpoint (requires HA config write access)
        session = await self._get_session()
        async with session.post(
            f"{self.ha_url}/api/config/automation/config/{automation_data['id']}",
            headers=self.headers,
            json=automation_data,
            timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            if response.status in [200, 201]:
                result = await response.json()
                logger.info(f"✅ Automation created: {automation_entity_id}")
                
                # Enable the automation
                await self.enable_automation(automation_entity_id)
                
                return {
                    "success": True,
                    "automation_id": automation_entity_id,
                    "message": "Automation created and enabled successfully",
                    "warnings": validation.get('warnings', [])
                }
            else:
                error_text = await response.text()
                error_json = {}
                try:
                    error_json = await response.json()
                    error_text = error_json.get('message', error_text)
                except:
                    pass  # Use text if JSON parsing fails
                
                logger.error(f"❌ Failed to create automation ({response.status}): {error_text}")
                raise Exception(f"HTTP {response.status}: {error_text}")
    except Exception as e:
        logger.error(f"❌ Error creating automation: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }
```

### 5.3 Home Assistant API Call

**HTTP Request to Home Assistant:**
```
POST http://192.168.1.86:8123/api/config/automation/config/office_lights_automation_1704067200_abc12345
Authorization: Bearer {HA_ACCESS_TOKEN}
Content-Type: application/json

{
  "id": "office_lights_automation_1704067200_abc12345",
  "alias": "Office Lights Automation",
  "description": "Turn on office lights when motion detected",
  "mode": "single",
  "trigger": [
    {
      "platform": "state",
      "entity_id": "binary_sensor.office_motion",
      "to": "on"
    }
  ],
  "action": [
    {
      "service": "light.turn_on",
      "target": {
        "entity_id": "light.office_ceiling"
      },
      "data": {
        "brightness_pct": 100
      }
    }
  ]
}
```

**HTTP Response from Home Assistant:**
```
HTTP 200 OK
Content-Type: application/json

{
  "result": "created",
  "id": "office_lights_automation_1704067200_abc12345"
}
```

### 5.4 Backend: ha_client.py - enable_automation()

**File:** `services/ai-automation-service/src/clients/ha_client.py`  
**Function:** `enable_automation()`  
**Lines:** 418-450

**Flow:**
```python
async def enable_automation(automation_entity_id)
  ↓
# POST to Home Assistant to enable automation
async with session.post(
    f"{self.ha_url}/api/services/automation/turn_on",
    headers=self.headers,
    json={"entity_id": automation_entity_id}
) as response:
  ↓
if response.status == 200:
    logger.info(f"✅ Automation enabled: {automation_entity_id}")
    return True
```

**HTTP Request to Home Assistant:**
```
POST http://192.168.1.86:8123/api/services/automation/turn_on
Authorization: Bearer {HA_ACCESS_TOKEN}
Content-Type: application/json

{
  "entity_id": "automation.office_lights_automation_1704067200_abc12345"
}
```

---

## Complete Call Tree Summary

```
USER ACTION: Submit Prompt
│
├─► Frontend: AskAI.tsx
│   └─► handleSendMessage()
│       └─► api.askAIQuery()
│           └─► HTTP POST /api/v1/ask-ai/query
│
├─► Backend: ask_ai_router.py
│   └─► process_natural_language_query()
│       ├─► extract_entities_with_ha()
│       ├─► resolve_entities_to_specific_devices()
│       ├─► detect_ambiguities() [if needed]
│       └─► generate_suggestions_from_query()
│           ├─► resolve_and_enrich_entities()
│           ├─► build_prompt_with_entity_context()
│           ├─► OpenAI API call (suggestion generation)
│           └─► validate_entities_in_suggestion()
│       └─► Return AskAIQueryResponse
│
├─► Frontend: Display suggestions
│
└─► USER ACTION: Approve Suggestion
    │
    ├─► Frontend: ConversationalSuggestionCard.tsx
    │   └─► handleApprove()
    │       └─► onApprove(suggestion.id, customMappings)
    │
    ├─► Frontend: AskAI.tsx
    │   └─► handleSuggestionAction('approve')
    │       └─► api.approveAskAISuggestion()
    │           └─► HTTP POST /api/v1/ask-ai/query/{query_id}/suggestions/{suggestion_id}/approve
    │
    ├─► Backend: ask_ai_router.py
    │   └─► approve_suggestion_from_query()
    │       ├─► Get query and suggestion from database
    │       ├─► Apply user filters (selected_entity_ids, custom_entity_mapping)
    │       ├─► generate_automation_yaml()
    │       │   ├─► Extract validated_entities from suggestion
    │       │   ├─► Build YAML generation prompt
    │       │   ├─► OpenAI API call (YAML generation)
    │       │   └─► Return YAML string
    │       ├─► validate_all_entities_in_yaml()
    │       ├─► SafetyValidator.validate_automation()
    │       └─► ha_client.create_automation()
    │           ├─► validate_automation() [HA API]
    │           ├─► Parse YAML to dict
    │           ├─► Generate unique automation ID
    │           └─► HTTP POST to HA Config API
    │               └─► POST /api/config/automation/config/{automation_id}
    │           └─► enable_automation()
    │               └─► POST /api/services/automation/turn_on
    │
    └─► Frontend: Display success/error message
```

---

## Key Data Structures

### Suggestion Object (in Query Response)
```typescript
{
  suggestion_id: string;
  title: string;
  description: string;
  trigger_summary: string;
  action_summary: string;
  devices_involved: string[];
  validated_entities: {
    [friendly_name: string]: entity_id;  // e.g., "Office Lights": "light.office_ceiling"
  };
  enriched_entity_context: string;  // JSON string with entity details
  status: "pending" | "approved" | "deployed";
}
```

### YAML Structure (Generated)
```yaml
id: 'unique_id_timestamp_uuid'
alias: "Descriptive Name"
description: "What it does"
mode: single
trigger:
  - platform: state|time|time_pattern|...
    entity_id: domain.entity
    # trigger-specific fields
action:
  - service: domain.service
    target:
      entity_id: domain.entity
    data:
      # service-specific parameters
```

### Approval Request Body
```json
{
  "selected_entity_ids": ["light.office_ceiling", "binary_sensor.office_motion"],
  "custom_entity_mapping": {
    "Office Lights": "light.office_ceiling"
  }
}
```

### Approval Response
```json
{
  "suggestion_id": "sugg-xyz789",
  "query_id": "query-abc123",
  "status": "success",
  "automation_id": "automation.office_lights_automation_1704067200_abc12345",
  "safe": true,
  "warnings": [],
  "message": "Automation created and enabled successfully"
}
```

---

## Error Handling Points

1. **Entity Extraction Failure**
   - Location: `extract_entities_with_ha()`
   - Response: Empty entities list, low confidence suggestions

2. **Missing Validated Entities**
   - Location: `approve_suggestion_from_query()`
   - Response: HTTP 400 with error message

3. **YAML Generation Failure**
   - Location: `generate_automation_yaml()`
   - Response: HTTP 400 with validation error

4. **Invalid Entity IDs in YAML**
   - Location: `validate_all_entities_in_yaml()`
   - Response: Attempts auto-fix, returns error if fix fails

5. **Home Assistant API Failure**
   - Location: `ha_client.create_automation()`
   - Response: Returns `{"success": false, "error": "..."}`

6. **Safety Validation Failure**
   - Location: `SafetyValidator.validate_automation()`
   - Response: Warnings logged but doesn't block (user can review)

---

## Performance Considerations

1. **Entity Resolution**: Happens during suggestion generation to cache results
2. **YAML Generation**: Single OpenAI API call with comprehensive prompt
3. **Entity Validation**: Validates all entities before creating automation
4. **Safety Checks**: Non-blocking, logs warnings only
5. **Home Assistant API**: Validates before creating, enables after creation

---

## Dependencies

- **OpenAI Client**: Used for both suggestion generation and YAML generation
- **Home Assistant Client**: Used for entity validation, automation creation, and enabling
- **Database (SQLite)**: Stores query and suggestion metadata
- **Data API Client**: Fetches device/entity information for context
- **Entity Validator**: Validates entity IDs exist in Home Assistant
- **Safety Validator**: Checks automation safety (non-destructive, etc.)

---

## Notes

- All entity IDs are validated before YAML generation
- YAML uses 2025 Home Assistant format (trigger/action singular at top level, platform/service in items)
- Automations are automatically enabled after creation
- Unique IDs prevent overwriting existing automations (force_new=True by default)
- Custom entity mappings allow users to override device-to-entity mappings
- Selected entity IDs filter which devices are included in the automation

