# Ask AI Enhancement Proposal - Device-Focused Suggestions with Debug Panel

**Date:** January 6, 2025  
**Status:** PROPOSAL  
**Author:** BMad Master

## Executive Summary

This proposal enhances the Ask AI feature to:
1. Generate only 2 high-quality suggestions (reduced from 5)
2. Add a debug panel showing device selection reasoning
3. Create technical prompts during suggestion phase (not YAML yet)
4. Separate technical prompt generation from YAML generation
5. Provide recommendations for tactical vs AI approach

## Current State Analysis

### Current Flow

```
User Query → Entity Extraction → Entity Resolution → Entity Enrichment → 
Suggestion Generation (5 suggestions) → Device Mapping → 
User Approves → YAML Generation → HA Deployment
```

### Current Issues

1. **Too Many Suggestions:** 5 suggestions can overwhelm users
2. **No Device Selection Transparency:** Users can't see why devices were chosen
3. **No Technical Prompt:** No intermediate technical prompt between suggestion and YAML
4. **YAML Generation Complexity:** Approve & Create does too much (entity resolution + YAML generation)
5. **No Debug Visibility:** Can't see OpenAI prompts, outputs, or reasoning

## Proposed Enhancements

### 1. Reduce Suggestions to 2

**Change:** Modify prompt to generate 2 suggestions instead of 5

**Location:** `services/ai-automation-service/src/prompt_building/unified_prompt_builder.py:182`

**Current Code:**
```python
Generate 3-5 {output_mode} that PROGRESS from CLOSE to your request → to CRAZY CREATIVE ideas:
```

**Proposed Change:**
```python
Generate EXACTLY 2 {output_mode} that PROGRESS from CLOSE to your request → to ENHANCED CREATIVE:

PROGRESSION STRATEGY:
1. FIRST suggestion: Direct, straightforward automation closely matching the request
   - Simple implementation
   - Exactly what was asked for
   - High confidence (0.9+)
   
2. SECOND suggestion: Enhanced variation building on the request
   - Practical improvements
   - Leverage device capabilities
   - Moderate-high confidence (0.8-0.9)
```

**Benefits:**
- ✅ Faster decision-making for users
- ✅ Higher quality suggestions (focus on best 2)
- ✅ Reduced API costs (fewer tokens)
- ✅ Better user experience (less cognitive load)

### 2. Add Debug Panel

**Location:** `services/ai-automation-ui/src/pages/AskAI.tsx`

**Features:**

#### A. Device Selection Debug

For each device in a suggestion, show:
- **Device Name:** e.g., "Office"
- **Why Selected:** 
  - "Matched query location 'office'"
  - "Fuzzy match score: 0.85"
  - "Domain match: light"
- **Entity ID Mapped:** e.g., "light.office_group"
- **Entity Type:** e.g., "group" or "individual"
- **Entities in Device:** List of all entities (for groups)
- **Capabilities:** e.g., "brightness, color_temp, rgb"
- **Actions Suggested:** e.g., "turn_on, set_brightness, flash"

#### B. OpenAI Prompt Display

Show:
- **System Prompt:** Full system prompt sent to OpenAI
- **User Prompt:** Full user prompt with entity context
- **OpenAI Response:** Raw JSON response from OpenAI
- **Token Usage:** Input tokens, output tokens, cost

#### C. Technical Prompt (NEW)

Show:
- **Technical Prompt:** Generated technical prompt for YAML generation
- **Trigger Entities:** List of entities used as triggers
- **Action Entities:** List of entities used in actions
- **Service Calls:** List of service calls with parameters
- **Conditions:** Any conditions or logic

**UI Design:**

```tsx
<CollapsibleDebugPanel>
  <DebugSection title="Device Selection">
    {suggestion.device_debug?.map(device => (
      <DeviceDebugCard
        deviceName={device.name}
        selectionReason={device.reason}
        entityId={device.entity_id}
        entityType={device.entity_type}
        entities={device.entities}
        capabilities={device.capabilities}
        actions={device.actions}
      />
    ))}
  </DebugSection>
  
  <DebugSection title="OpenAI Interaction">
    <SystemPrompt>{suggestion.debug?.system_prompt}</SystemPrompt>
    <UserPrompt>{suggestion.debug?.user_prompt}</UserPrompt>
    <OpenAIResponse>{suggestion.debug?.openai_response}</OpenAIResponse>
    <TokenUsage>{suggestion.debug?.token_usage}</TokenUsage>
  </DebugSection>
  
  <DebugSection title="Technical Prompt">
    <TechnicalPrompt>{suggestion.technical_prompt}</TechnicalPrompt>
  </DebugSection>
</CollapsibleDebugPanel>
```

### 3. Create Technical Prompt During Suggestion Phase

**Purpose:** Generate a detailed technical prompt that will be used to create YAML during approval

**Location:** `services/ai-automation-service/src/api/ask_ai_router.py`

**New Function:**

```python
async def generate_technical_prompt(
    suggestion: Dict[str, Any],
    validated_entities: Dict[str, str],
    enriched_data: Dict[str, Dict[str, Any]],
    query: str
) -> Dict[str, Any]:
    """
    Generate technical prompt for YAML generation.
    
    This prompt contains:
    - Trigger entities and their states
    - Action entities and their service calls
    - Conditions and logic
    - Entity capabilities and constraints
    
    Returns:
        Dictionary with technical prompt details
    """
    # Extract trigger entities from suggestion
    trigger_entities = extract_trigger_entities(suggestion, validated_entities)
    
    # Extract action entities from suggestion
    action_entities = extract_action_entities(suggestion, validated_entities)
    
    # Build technical prompt
    technical_prompt = {
        "trigger": {
            "entities": trigger_entities,
            "platform": "state",  # or "numeric_state", "time", etc.
            "conditions": []
        },
        "action": {
            "entities": action_entities,
            "service_calls": [],
            "parameters": {}
        },
        "conditions": [],
        "entity_capabilities": {
            entity_id: enriched_data.get(entity_id, {}).get("capabilities", [])
            for entity_id in list(validated_entities.values())
        }
    }
    
    return technical_prompt
```

**Integration:**

Modify `generate_suggestions_from_query()` to:
1. Generate suggestions (2 instead of 5)
2. Map devices to entities
3. **Generate technical prompt for each suggestion**
4. Store technical prompt in suggestion object
5. Return suggestions with technical prompts

**Suggestion Object Structure:**

```python
{
    "suggestion_id": "ask-ai-xxx",
    "description": "...",
    "trigger_summary": "...",
    "action_summary": "...",
    "devices_involved": ["Office"],
    "validated_entities": {"Office": "light.office_group"},
    "technical_prompt": {
        "trigger": {...},
        "action": {...},
        "conditions": [...],
        "entity_capabilities": {...}
    },
    "debug": {
        "device_selection": [...],
        "system_prompt": "...",
        "user_prompt": "...",
        "openai_response": {...},
        "token_usage": {...}
    }
}
```

### 4. Separate Technical Prompt from YAML Generation

**Current Flow (PROBLEM):**
```
Approve & Create → Entity Resolution → YAML Generation → HA Deployment
```

**Proposed Flow (SOLUTION):**
```
Approve & Create → Use Technical Prompt → YAML Generation → HA Deployment
```

**Changes:**

#### A. Modify `approve_suggestion_from_query()`

**Location:** `services/ai-automation-service/src/api/ask_ai_router.py:3618`

**Current Code:**
```python
# Generate YAML for the suggestion (validated_entities already in final_suggestion)
automation_yaml = await generate_automation_yaml(
    final_suggestion, 
    query.original_query, 
    [], 
    db_session=db, 
    ha_client=ha_client
)
```

**Proposed Code:**
```python
# Get technical prompt from suggestion (already generated during suggestion phase)
technical_prompt = final_suggestion.get('technical_prompt')
if not technical_prompt:
    raise HTTPException(
        status_code=400,
        detail="Suggestion missing technical_prompt. Please regenerate suggestion."
    )

# Generate YAML using technical prompt ONLY
automation_yaml = await generate_yaml_from_technical_prompt(
    technical_prompt,
    ha_client=ha_client
)
```

#### B. New Function: `generate_yaml_from_technical_prompt()`

**Location:** `services/ai-automation-service/src/api/ask_ai_router.py`

```python
async def generate_yaml_from_technical_prompt(
    technical_prompt: Dict[str, Any],
    ha_client: Optional[HomeAssistantClient] = None
) -> str:
    """
    Generate Home Assistant automation YAML from technical prompt.
    
    This is a PURE function that only converts technical prompt to YAML.
    No entity resolution, no enrichment, no complex logic.
    
    Args:
        technical_prompt: Technical prompt dictionary with trigger/action details
        ha_client: Optional HA client for validation only
        
    Returns:
        Valid Home Assistant automation YAML string
    """
    # Build YAML structure from technical prompt
    yaml_structure = {
        "alias": technical_prompt.get("alias", "AI Generated Automation"),
        "description": technical_prompt.get("description", ""),
        "trigger": build_trigger_yaml(technical_prompt["trigger"]),
        "action": build_action_yaml(technical_prompt["action"]),
    }
    
    # Add conditions if present
    if technical_prompt.get("conditions"):
        yaml_structure["condition"] = build_condition_yaml(technical_prompt["conditions"])
    
    # Convert to YAML string
    import yaml
    yaml_content = yaml.dump(yaml_structure, default_flow_style=False, sort_keys=False)
    
    # Validate YAML structure
    if ha_client:
        validate_yaml_structure(yaml_content, ha_client)
    
    return yaml_content
```

**Benefits:**
- ✅ Separation of concerns (suggestion phase vs YAML phase)
- ✅ Faster YAML generation (no entity resolution needed)
- ✅ More predictable YAML output
- ✅ Easier to debug (technical prompt is clear)

## Research Findings: Tactical vs AI Approach

### Option 1: Pure AI Approach (Current)

**How it works:**
- OpenAI generates YAML directly from suggestion
- AI determines entity IDs, service calls, parameters
- Flexible but unpredictable

**Pros:**
- ✅ Handles complex scenarios
- ✅ Can create creative automations
- ✅ Adapts to edge cases

**Cons:**
- ❌ Unpredictable output
- ❌ May generate invalid YAML
- ❌ Harder to debug
- ❌ Higher token costs

### Option 2: Pure Tactical Approach

**How it works:**
- Technical prompt defines exact structure
- Template-based YAML generation
- No AI for YAML generation

**Pros:**
- ✅ Predictable output
- ✅ Always valid YAML
- ✅ Faster generation
- ✅ Lower costs
- ✅ Easier to debug

**Cons:**
- ❌ Less flexible
- ❌ May not handle edge cases
- ❌ Requires more templates

### Option 3: Hybrid Approach (RECOMMENDED)

**How it works:**
- Technical prompt defines structure (tactical)
- AI generates YAML from technical prompt (AI)
- Template fallback for simple cases (tactical)

**Implementation:**

```python
async def generate_yaml_from_technical_prompt(
    technical_prompt: Dict[str, Any],
    ha_client: Optional[HomeAssistantClient] = None,
    use_ai: bool = True
) -> str:
    """
    Generate YAML using hybrid approach.
    
    - Simple cases: Use template (tactical)
    - Complex cases: Use AI (AI)
    """
    # Determine complexity
    is_simple = (
        len(technical_prompt["trigger"]["entities"]) == 1 and
        len(technical_prompt["action"]["entities"]) == 1 and
        not technical_prompt.get("conditions") and
        technical_prompt["action"]["service_calls"][0]["service"] in ["light.turn_on", "light.turn_off"]
    )
    
    if is_simple and not use_ai:
        # Tactical: Use template
        return generate_yaml_from_template(technical_prompt)
    else:
        # AI: Use OpenAI to generate YAML from technical prompt
        return await generate_yaml_with_ai(technical_prompt, ha_client)
```

**Recommendation:** Use Hybrid Approach

**Rationale:**
1. **Best of Both Worlds:** Flexibility when needed, predictability when possible
2. **Cost Optimization:** Use templates for 80% of simple cases, AI for 20% complex cases
3. **Quality Assurance:** Templates ensure valid YAML, AI handles edge cases
4. **User Control:** Allow users to choose AI vs Template (debug panel toggle)

## Implementation Plan

### Phase 1: Reduce Suggestions & Add Debug Data (Week 1)

**Tasks:**
1. Modify prompt to generate 2 suggestions
2. Add device selection debug data to suggestions
3. Add OpenAI prompt/response logging
4. Update frontend to display debug panel

**Files to Modify:**
- `services/ai-automation-service/src/prompt_building/unified_prompt_builder.py`
- `services/ai-automation-service/src/api/ask_ai_router.py`
- `services/ai-automation-ui/src/pages/AskAI.tsx`

### Phase 2: Technical Prompt Generation (Week 2)

**Tasks:**
1. Create `generate_technical_prompt()` function
2. Integrate into suggestion generation
3. Store technical prompt in suggestion object
4. Update frontend to display technical prompt

**Files to Modify:**
- `services/ai-automation-service/src/api/ask_ai_router.py`
- Database models (if needed)

### Phase 3: Separate YAML Generation (Week 3)

**Tasks:**
1. Create `generate_yaml_from_technical_prompt()` function
2. Modify `approve_suggestion_from_query()` to use technical prompt
3. Implement hybrid approach (tactical + AI)
4. Add template-based YAML generation for simple cases

**Files to Modify:**
- `services/ai-automation-service/src/api/ask_ai_router.py`
- Create new file: `services/ai-automation-service/src/services/yaml_generator.py`

### Phase 4: Testing & Refinement (Week 4)

**Tasks:**
1. Test with various query types
2. Verify debug panel displays correctly
3. Validate technical prompt quality
4. Optimize hybrid approach thresholds

## Technical Prompt Structure

### Example Technical Prompt

```json
{
  "alias": "Turn on Office Lights on Motion",
  "description": "Turn on office lights when motion is detected",
  "trigger": {
    "platform": "state",
    "entities": [
      {
        "entity_id": "binary_sensor.presence_sensor_fp2_8b8a_desk",
        "from": "off",
        "to": "on",
        "attribute": "occupancy"
      }
    ]
  },
  "action": {
    "entities": [
      {
        "entity_id": "light.office_group",
        "service": "light.turn_on",
        "parameters": {
          "brightness_pct": 100
        }
      }
    ]
  },
  "conditions": [],
  "entity_capabilities": {
    "binary_sensor.presence_sensor_fp2_8b8a_desk": {
      "device_class": "motion",
      "state": "on/off"
    },
    "light.office_group": {
      "supported_features": ["brightness", "color_temp", "rgb"],
      "capabilities": ["turn_on", "turn_off", "set_brightness", "set_color_temp"]
    }
  },
  "metadata": {
    "query": "Turn on the office lights when I enter the office",
    "devices_involved": ["Office"],
    "confidence": 0.95
  }
}
```

## Home Assistant 2025 Best Practices

Based on research:

### 1. Use Entity Selectors

Home Assistant 2025 recommends using entity selectors for precise input:

```yaml
selector:
  entity:
    filter:
      - domain: light
      - area_id: office
```

**Recommendation:** Use this pattern in technical prompt for entity filtering.

### 2. Use Target Syntax

Home Assistant 2025 recommends using `target` key for service calls:

```yaml
action:
  - service: light.turn_on
    target:
      entity_id: light.office_group
```

**Recommendation:** Always use `target` syntax in generated YAML.

### 3. Leverage Areas and Labels

Home Assistant 2025 supports area and label targeting:

```yaml
action:
  - service: light.turn_on
    target:
      area_id: office
```

**Recommendation:** Use area_id when all entities in area should be targeted.

### 4. Template API for Complex Queries

Home Assistant 2025 Template API can be used for complex entity queries:

```python
template = """
{% set office_lights = states.light | selectattr('attributes.area_id', 'eq', 'office') | list %}
{{ office_lights | map(attribute='entity_id') | list | tojson }}
"""
```

**Recommendation:** Use Template API for entity resolution during suggestion phase.

## Success Metrics

### User Experience
- ✅ Faster decision-making (2 suggestions vs 5)
- ✅ Better understanding of device selection (debug panel)
- ✅ Confidence in automation (technical prompt visibility)

### Technical
- ✅ Reduced API costs (fewer tokens, templates for simple cases)
- ✅ Faster YAML generation (tactical approach for simple cases)
- ✅ More predictable output (technical prompt structure)
- ✅ Easier debugging (full visibility into process)

### Quality
- ✅ Higher suggestion quality (focus on best 2)
- ✅ More accurate YAML (technical prompt structure)
- ✅ Better device selection (debug visibility)

## Open Questions

1. **Should technical prompt be editable?** (Yes - allow users to refine before YAML generation)
2. **Should we cache technical prompts?** (Yes - for similar queries)
3. **Should we allow AI vs Template toggle?** (Yes - in debug panel)
4. **Should we show technical prompt by default?** (No - collapsible debug panel)

## Next Steps

1. Review and approve this proposal
2. Create detailed implementation tasks
3. Begin Phase 1 implementation
4. Test with real queries
5. Iterate based on feedback

## References

- `implementation/analysis/ASK_AI_API_FLOW_REVIEW.md` - Current flow analysis
- `implementation/analysis/HA_API_2025_RESEARCH.md` - HA API research
- `services/ai-automation-service/src/api/ask_ai_router.py` - Current implementation
- `services/ai-automation-service/src/prompt_building/unified_prompt_builder.py` - Prompt builder

---

**Status:** PROPOSAL - Awaiting Approval  
**Estimated Effort:** 4 weeks  
**Priority:** HIGH

