# Device Suggestions UI Improvements

**Date:** January 15, 2026  
**Status:** Recommendations for Implementation  
**Priority:** High

## Issues Identified

Based on user feedback and code analysis:

1. **Entity IDs displayed instead of friendly names** - Hash IDs like `d409615482917dcbee6e74e6a42ed86f` appear in titles and actions
2. **Capabilities button non-functional** - Button exists but provides no information
3. **Enhance button non-functional** - Button doesn't actually enhance suggestions
4. **Poor suggestion quality** - Generic, uninteresting suggestions with low confidence scores

## Root Cause Analysis

### Issue 1: Entity IDs in Display

**Location:** `services/ha-ai-agent-service/src/services/device_suggestion_service.py`

**Problem:**
- Lines 245-249, 313-317: Backend generates suggestions with `device_id` (hash) directly in titles and action text
- No conversion from device_id to friendly device name
- Frontend (`DeviceSuggestions.tsx`) displays backend data as-is without transformation

**Example:**
```python
title="Basic automation for {device_id}",  # device_id is a hash
action=f"Control {device_id}",  # Shows hash instead of friendly name
```

### Issue 2: Capabilities Button

**Location:** `services/ai-automation-ui/src/components/ha-agent/DeviceSuggestions.tsx`

**Problem:**
- No "Capabilities" button exists in `DeviceSuggestions.tsx`
- User may be seeing a button from a different component (`ConversationalSuggestionCard.tsx` has one)
- Even if present, no handler is wired up

### Issue 3: Enhance Button

**Location:** `services/ai-automation-ui/src/pages/HAAgentChat.tsx` (lines 713-721)

**Problem:**
- `onEnhanceSuggestion` only pre-populates input field
- Doesn't start a conversation or use `EnhancementButton` component
- No actual enhancement workflow triggered

**Current Implementation:**
```typescript
onEnhanceSuggestion={(suggestion: DeviceSuggestion) => {
  const prompt = `Enhance this automation: ${suggestion.title}\n\n${suggestion.description}`;
  setInputValue(prompt);
  // Just sets input - doesn't actually enhance
}}
```

### Issue 4: Poor Suggestion Quality

**Location:** `services/ha-ai-agent-service/src/services/device_suggestion_service.py`

**Problem:**
- Lines 226-328: Very basic placeholder implementation
- Generic titles like "Basic Device Automation"
- Low confidence/quality scores (0.6)
- No LLM-based generation
- No pattern matching or synergy analysis
- No blueprint matching

## Recommendations

### 1. Fix Entity ID to Friendly Name Conversion

#### Backend Fix (Priority: High)

**File:** `services/ha-ai-agent-service/src/services/device_suggestion_service.py`

**Changes:**
1. Fetch device friendly name from data-api when generating suggestions
2. Replace `device_id` with friendly name in titles and descriptions
3. Use entity friendly names in automation previews

**Implementation:**
```python
async def _generate_suggestions_from_data(
    self,
    device_id: str,
    device_context: DeviceContext,
    context: DeviceSuggestionContext,
) -> list[DeviceSuggestion]:
    """Generate suggestions with friendly names"""
    
    # Fetch device data to get friendly name
    device_data = await self._fetch_device_data(device_id)
    device_name = device_data.get("name") or device_data.get("friendly_name") or f"Device {device_id[:8]}"
    
    # Get entity friendly names
    entity_map = {}
    for entity in device_context.home_assistant_entities:
        entity_id = entity.get("entity_id")
        friendly_name = entity.get("friendly_name") or entity.get("name") or entity_id
        if entity_id:
            entity_map[entity_id] = friendly_name
    
    # Generate suggestions with friendly names
    if device_context.capabilities:
        suggestion = DeviceSuggestion(
            suggestion_id=str(uuid.uuid4()),
            title=f"Automation for {device_name}",
            description=f"Automation based on {device_name} capabilities",
            automation_preview=AutomationPreview(
                trigger="Device state change",
                action=f"Control {device_name}",
            ),
            # ... rest of suggestion
        )
```

#### Frontend Fix (Priority: Medium)

**File:** `services/ai-automation-ui/src/components/ha-agent/DeviceSuggestions.tsx`

**Changes:**
1. Add entity ID to friendly name mapping utility
2. Transform suggestion data before display
3. Replace any remaining entity IDs with friendly names

**Implementation:**
```typescript
// Add utility function
const getFriendlyName = (entityId: string, entities: Entity[]): string => {
  const entity = entities.find(e => e.entity_id === entityId);
  return entity?.friendly_name || entity?.name || entityId;
};

// Transform suggestion before display
const transformedSuggestion = {
  ...suggestion,
  title: suggestion.title.replace(/[a-f0-9]{32}/g, (hash) => {
    // Try to find device name from context
    return deviceName || `Device ${hash.substring(0, 8)}`;
  }),
  automation_preview: {
    ...suggestion.automation_preview,
    trigger: suggestion.automation_preview.trigger.replace(/[a-f0-9]{32}/g, deviceName),
    action: suggestion.automation_preview.action.replace(/[a-f0-9]{32}/g, deviceName),
  },
};
```

### 2. Implement Capabilities Button

**File:** `services/ai-automation-ui/src/components/ha-agent/DeviceSuggestions.tsx`

**Changes:**
1. Add capabilities modal/dropdown
2. Fetch device capabilities from API
3. Display capabilities in expandable section

**Implementation:**
```typescript
const [showCapabilities, setShowCapabilities] = useState<boolean>(false);
const [capabilities, setCapabilities] = useState<DeviceCapabilitiesResponse | null>(null);

// Fetch capabilities when button clicked
const handleShowCapabilities = async (suggestion: DeviceSuggestion) => {
  if (!capabilities) {
    try {
      const caps = await getDeviceCapabilities(deviceId!);
      setCapabilities(caps);
    } catch (error) {
      toast.error('Failed to load capabilities');
      return;
    }
  }
  setShowCapabilities(true);
};

// Add button in suggestion card
<button
  onClick={() => handleShowCapabilities(suggestion)}
  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
    darkMode
      ? 'bg-gray-600 text-white hover:bg-gray-500'
      : 'bg-gray-200 text-gray-900 hover:bg-gray-300'
  }`}
>
  💡 Capabilities
</button>

// Add capabilities modal
{showCapabilities && capabilities && (
  <CapabilitiesModal
    capabilities={capabilities}
    onClose={() => setShowCapabilities(false)}
    darkMode={darkMode}
  />
)}
```

### 3. Fix Enhance Button

**File:** `services/ai-automation-ui/src/pages/HAAgentChat.tsx`

**Changes:**
1. Start conversation if none exists
2. Send enhancement request to agent
3. Use proper enhancement workflow

**Implementation:**
```typescript
onEnhanceSuggestion={async (suggestion: DeviceSuggestion) => {
  try {
    // Ensure we have a conversation
    if (!currentConversationId) {
      // Start new conversation
      const response = await sendChatMessage({
        message: `I'd like to enhance this automation suggestion: ${suggestion.title}`,
        title: `Enhance: ${suggestion.title}`,
      });
      setCurrentConversationId(response.conversation_id);
    }
    
    // Send enhancement request
    const enhancementPrompt = `Enhance this automation suggestion:

Title: ${suggestion.title}
Description: ${suggestion.description}
Trigger: ${suggestion.automation_preview.trigger}
Action: ${suggestion.automation_preview.action}

Please provide an improved version with more details and better automation logic.`;
    
    await sendChatMessage({
      message: enhancementPrompt,
      conversation_id: currentConversationId,
    });
    
    // Reload conversation to show response
    await loadConversation();
    
    toast.success('Enhancement request sent');
  } catch (error) {
    console.error('Failed to enhance suggestion:', error);
    toast.error('Failed to enhance suggestion');
  }
}}
```

### 4. Improve Suggestion Quality

#### Backend Improvements (Priority: High)

**File:** `services/ha-ai-agent-service/src/services/device_suggestion_service.py`

**Changes:**
1. Integrate LLM-based suggestion generation
2. Use pattern detection service for synergy-based suggestions
3. Use blueprint matching service
4. Improve confidence/quality scoring

**Implementation:**
```python
async def _generate_suggestions_from_data(
    self,
    device_id: str,
    device_context: DeviceContext,
    context: DeviceSuggestionContext,
) -> list[DeviceSuggestion]:
    """Generate high-quality suggestions using LLM and pattern matching"""
    
    suggestions: list[DeviceSuggestion] = []
    
    # 1. LLM-based generation for intelligent suggestions
    if self.settings.openai_api_key:
        llm_suggestions = await self._generate_llm_suggestions(
            device_id=device_id,
            device_context=device_context,
        )
        suggestions.extend(llm_suggestions)
    
    # 2. Pattern-based suggestions from synergies
    if device_context.related_synergies:
        synergy_suggestions = await self._generate_synergy_suggestions(
            device_id=device_id,
            synergies=device_context.related_synergies,
            device_context=device_context,
        )
        suggestions.extend(synergy_suggestions)
    
    # 3. Blueprint-based suggestions
    if device_context.compatible_blueprints:
        blueprint_suggestions = await self._generate_blueprint_suggestions(
            device_id=device_id,
            blueprints=device_context.compatible_blueprints,
            device_context=device_context,
        )
        suggestions.extend(blueprint_suggestions)
    
    # 4. Capability-based suggestions (improved)
    if device_context.capabilities:
        capability_suggestions = await self._generate_capability_suggestions(
            device_id=device_id,
            capabilities=device_context.capabilities,
            device_context=device_context,
        )
        suggestions.extend(capability_suggestions)
    
    # If no suggestions, create a fallback with better quality
    if not suggestions:
        suggestions.append(await self._generate_fallback_suggestion(
            device_id=device_id,
            device_context=device_context,
        ))
    
    return suggestions

async def _generate_llm_suggestions(
    self,
    device_id: str,
    device_context: DeviceContext,
) -> list[DeviceSuggestion]:
    """Generate suggestions using OpenAI"""
    # TODO: Implement LLM-based generation
    # Use device context to create intelligent prompts
    # Generate 3-5 high-quality suggestions
    pass

async def _generate_synergy_suggestions(
    self,
    device_id: str,
    synergies: list[dict[str, Any]],
    device_context: DeviceContext,
) -> list[DeviceSuggestion]:
    """Generate suggestions based on device synergies"""
    # TODO: Implement synergy-based generation
    # Use synergy patterns to create meaningful automations
    pass
```

#### Scoring Improvements

**File:** `services/ha-ai-agent-service/src/services/device_suggestion_service.py`

**Changes:**
1. Improve confidence scoring based on data sources
2. Add quality scoring based on automation complexity and usefulness
3. Filter out low-quality suggestions

**Implementation:**
```python
def _calculate_confidence_score(
    self,
    suggestion: DeviceSuggestion,
    device_context: DeviceContext,
) -> float:
    """Calculate confidence score based on data sources"""
    score = 0.5  # Base score
    
    # Boost for blueprint matches
    if suggestion.data_sources.blueprints:
        score += 0.2
    
    # Boost for synergy support
    if suggestion.data_sources.synergies:
        score += 0.15
    
    # Boost for device capabilities
    if suggestion.data_sources.device_capabilities:
        score += 0.1
    
    # Boost for validated services
    if suggestion.home_assistant_services.validated:
        score += 0.05
    
    return min(score, 1.0)

def _calculate_quality_score(
    self,
    suggestion: DeviceSuggestion,
) -> float:
    """Calculate quality score based on automation usefulness"""
    score = 0.5  # Base score
    
    # Boost for specific triggers (not generic)
    if "Time-based" not in suggestion.automation_preview.trigger:
        score += 0.1
    
    # Boost for detailed descriptions
    if len(suggestion.description) > 50:
        score += 0.1
    
    # Boost for multiple data sources
    source_count = sum([
        1 if suggestion.data_sources.blueprints else 0,
        1 if suggestion.data_sources.synergies else 0,
        1 if suggestion.data_sources.device_capabilities else 0,
    ])
    if source_count > 1:
        score += 0.1
    
    return min(score, 1.0)
```

## Implementation Priority

1. **High Priority:**
   - Fix entity ID to friendly name conversion (backend)
   - Fix Enhance button functionality
   - Improve suggestion quality (LLM integration)

2. **Medium Priority:**
   - Implement Capabilities button
   - Frontend entity ID transformation
   - Better scoring algorithms

3. **Low Priority:**
   - UI polish and animations
   - Additional data source indicators
   - Suggestion filtering and sorting options

## Testing Checklist

- [ ] Entity IDs replaced with friendly names in all suggestion displays
- [ ] Capabilities button shows device capabilities modal
- [ ] Enhance button starts conversation and sends enhancement request
- [ ] Suggestions have confidence scores ≥ 0.7
- [ ] Suggestions have quality scores ≥ 0.7
- [ ] Suggestions are interesting and relevant to device
- [ ] No hash IDs visible in UI
- [ ] All buttons are functional

## Related Files

- `services/ha-ai-agent-service/src/services/device_suggestion_service.py` - Backend suggestion generation
- `services/ai-automation-ui/src/components/ha-agent/DeviceSuggestions.tsx` - Frontend display
- `services/ai-automation-ui/src/pages/HAAgentChat.tsx` - Main chat page with device selection
- `services/ai-automation-ui/src/components/ha-agent/DeviceContextDisplay.tsx` - Device info display

## Next Steps

1. Create implementation tasks for each recommendation
2. Prioritize backend fixes (entity ID conversion, suggestion quality)
3. Implement frontend fixes (buttons, UI improvements)
4. Test with real device data
5. Gather user feedback on improvements
