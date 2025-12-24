# Story AI3.4: Synergy-Based Suggestion Generation

**Epic:** Epic-AI-3 - Cross-Device Synergy & Contextual Opportunities  
**Story ID:** AI3.4  
**Priority:** Critical  
**Estimated Effort:** 10-12 hours  
**Dependencies:** Story AI3.3 (Unconnected Relationship Analysis)

---

## User Story

**As a** user  
**I want** AI-generated automation suggestions from detected device synergies  
**so that** I can discover automation opportunities I didn't know were possible

---

## Business Value

- **Converts Opportunities to Actions:** Transforms synergy detection into deployable automations
- **AI-Powered Discovery:** Uses OpenAI to generate creative automation ideas
- **User-Friendly:** Natural language descriptions + Home Assistant YAML
- **Educational:** Teaches users what's possible with their devices

---

## Acceptance Criteria

### Synergy Suggestion Generation

1. ✅ **SynergySuggestionGenerator Class:**
   - Takes synergy opportunities from AI3.3
   - Generates LLM prompts for each synergy type
   - Calls OpenAI to create automation suggestions
   - Returns structured suggestions

2. ✅ **Prompt Templates by Synergy Type:**
   - **Device Pair:** "Motion sensor + light → motion-activated lighting"
   - **Weather Context:** "Climate device + weather data → frost protection"
   - **Energy Context:** "High-power device + energy prices → off-peak scheduling"
   - **Event Context:** "Sports schedule + entertainment → game-time scenes"

3. ✅ **Generated Suggestion Structure:**
   ```python
   {
       'type': 'synergy_device_pair',
       'synergy_id': str,
       'title': 'Motion-Activated Bedroom Lighting',
       'description': 'Automatically turn on bedroom light when motion detected',
       'automation_yaml': '...',  # Valid HA YAML
       'rationale': 'You have motion sensor and light in bedroom with no automation...',
       'category': 'convenience',
       'priority': 'medium',
       'confidence': 0.85,
       'complexity': 'low',
       'devices_involved': [device1_id, device2_id]
   }
   ```

4. ✅ **Integration with Daily Batch:**
   - Add to Phase 5 (Suggestion Generation)
   - Generate synergy suggestions alongside pattern/feature suggestions
   - Combine and rank all suggestion types
   - Limit total suggestions to top 10

5. ✅ **Suggestion Ranking:**
   - Unified scoring across all types (pattern, feature, synergy)
   - Priority: confidence * impact * (1 - complexity_penalty)
   - Ensure diversity: At least 1 of each type if available
   - Balance: No more than 50% from single type

6. ✅ **Database Storage:**
   - Store in existing `suggestions` table
   - New `type` values: 'synergy_device_pair', 'synergy_weather', etc.
   - Link back to synergy_opportunity via `synergy_id`
   - Track approval/deployment rates by synergy type

7. ✅ **Performance:**
   - Generate 5 synergy suggestions in <30 seconds
   - OpenAI token usage <2000 tokens per suggestion
   - Total cost <$0.01 per daily run
   - Memory usage <50MB

8. ✅ **Error Handling:**
   - Retry failed OpenAI calls (3 attempts)
   - Graceful fallback if OpenAI unavailable
   - Continue with other suggestion types
   - Log all generation errors

---

## Tasks / Subtasks

### Task 1: Create Synergy Suggestion Generator (AC: 1, 2)

- [x] Create `src/synergy_detection/synergy_suggestion_generator.py`
- [x] Implement `SynergySuggestionGenerator` class
- [x] Build prompt templates for each synergy type:
  - [x] Device pair template
  - [x] Weather context template (placeholder for AI3.5)
  - [x] Energy context template (placeholder for AI3.6)
  - [x] Event context template (placeholder for AI3.7)
- [x] Implement OpenAI integration (reuse existing client from Epic AI-1)
- [x] Parse and validate OpenAI responses

### Task 2: Implement Prompt Building Logic (AC: 2, 3)

**Device Pair Prompt Example:**
```python
def _build_device_pair_prompt(self, synergy: Dict) -> str:
    """
    Build prompt for device pair synergy.
    
    Example synergy:
    {
        'trigger_device': 'binary_sensor.bedroom_motion',
        'action_device': 'light.bedroom_ceiling',
        'area': 'bedroom',
        'relationship': 'motion_to_light'
    }
    """
    return f"""Create a Home Assistant automation for this device synergy:

DETECTED OPPORTUNITY:
- Trigger Device: {synergy['trigger_device_name']} (bedroom)
- Action Device: {synergy['action_device_name']} (bedroom)
- Relationship: Motion-activated lighting
- Impact: High (frequently used area)
- Complexity: Low (simple trigger + action)

INSIGHT:
You have a motion sensor and light in the same room with NO automation 
connecting them. This is a common opportunity for convenience automation.

INSTRUCTIONS:
1. Create valid Home Assistant automation YAML
2. Use motion sensor as trigger
3. Turn on light when motion detected
4. Optional: Turn off after no motion for 5 minutes
5. Provide clear rationale explaining the benefit
6. Categorize appropriately (energy/comfort/security/convenience)

OUTPUT FORMAT:
```yaml
alias: "AI Suggested: Motion-Activated Bedroom Lighting"
description: "Automatically control bedroom light based on motion"
trigger:
  - platform: state
    entity_id: binary_sensor.bedroom_motion
    to: 'on'
action:
  - service: light.turn_on
    target:
      entity_id: light.bedroom_ceiling
  - wait_for_trigger:
      - platform: state
        entity_id: binary_sensor.bedroom_motion
        to: 'off'
        for: '00:05:00'
  - service: light.turn_off
    target:
      entity_id: light.bedroom_ceiling
```

RATIONALE: [Explain benefit using device names]
CATEGORY: [energy|comfort|security|convenience]
PRIORITY: [high|medium|low]
"""
```

### Task 3: Integrate with Daily Batch (AC: 4, 5)

- [x] Modify `src/scheduler/daily_analysis.py` Phase 5
- [x] Add synergy suggestion generation (Part C)
- [x] Implement unified scoring algorithm
- [x] Implement diversity balancing (ensure mix of types)
- [x] Store all suggestions in database

### Task 4: Database Integration (AC: 6)

- [x] Update `suggestions` table to support synergy types
- [x] Suggestions table already supports all required fields
- [x] CRUD operations reuse existing functions (store_suggestion)
- [x] Synergy_id tracked in suggestion metadata

### Task 5: Testing (AC: 7, 8)

- [x] Unit tests for `SynergySuggestionGenerator`:
  - [x] Test prompt building for device pair
  - [x] Test OpenAI response parsing
  - [x] Test error handling
  - [x] Test max suggestions limit
- [x] Integration tests:
  - [x] Test with real synergy data
  - [x] Test database storage compatibility
  - [x] Test daily batch integration
  - [x] Test unified ranking
- [x] Cost analysis:
  - [x] Token usage tracked per suggestion
  - [x] Estimated <350 tokens per suggestion
  - [x] Cost <$0.01 per run verified

---

## Dev Notes

### OpenAI Integration (Reuse from Epic AI-1)

**Existing Client:** `src/llm/openai_client.py` (OpenAIClient)  
**Model:** gpt-4o-mini (cost-effective)  
**Temperature:** 0.7 (balanced creativity)  
**Max Tokens:** 600 (sufficient for automation YAML)

### Unified Suggestion Ranking Algorithm

```python
def calculate_unified_score(suggestion):
    """
    Unified scoring across all suggestion types.
    
    Score = confidence * impact * (1 - complexity_penalty)
    
    complexity_penalty:
    - low: 0.0 (no penalty)
    - medium: 0.1 (slight penalty)
    - high: 0.3 (significant penalty)
    """
    complexity_penalties = {
        'low': 0.0,
        'medium': 0.1,
        'high': 0.3
    }
    
    penalty = complexity_penalties.get(suggestion.get('complexity', 'medium'), 0.1)
    impact = suggestion.get('impact_score', suggestion.get('confidence', 0.7))
    
    return suggestion['confidence'] * impact * (1 - penalty)
```

### Diversity Balancing

```python
def balance_suggestions(all_suggestions, max_total=10):
    """
    Ensure diversity across suggestion types.
    
    Rules:
    - At least 1 of each type if available
    - No more than 50% from single type
    - Fill remaining slots by highest score
    """
    types = ['pattern_automation', 'feature_discovery', 'synergy_device_pair', 
             'synergy_weather', 'synergy_energy', 'synergy_event']
    
    balanced = []
    
    # Step 1: Take top 1 from each type
    for stype in types:
        type_suggestions = [s for s in all_suggestions if s['type'] == stype]
        if type_suggestions:
            balanced.append(max(type_suggestions, key=calculate_unified_score))
    
    # Step 2: Fill remaining slots with highest scores
    remaining_slots = max_total - len(balanced)
    remaining_suggestions = [s for s in all_suggestions if s not in balanced]
    remaining_suggestions.sort(key=calculate_unified_score, reverse=True)
    
    balanced.extend(remaining_suggestions[:remaining_slots])
    
    return balanced[:max_total]
```

### Example Synergy Suggestions

**Device Pair (Motion → Light):**
```yaml
title: "Motion-Activated Bedroom Lighting"
description: "Turn on bedroom light when motion detected, auto-off after 5 minutes"
type: "synergy_device_pair"
category: "convenience"
priority: "medium"
confidence: 0.85
complexity: "low"
```

**Weather Context:**
```yaml
title: "Frost Protection for Living Room"
description: "Set thermostat to 68°F when outdoor temp drops below 32°F overnight"
type: "synergy_weather"
category: "comfort"
priority: "high"
confidence: 0.78
complexity: "medium"
```

**Energy Context:**
```yaml
title: "Off-Peak Dishwasher Scheduling"
description: "Start dishwasher at 2 AM when electricity rates are lowest"
type: "synergy_energy"
category: "energy"
priority: "high"
confidence: 0.82
complexity: "medium"
```

### Testing Standards

**Test Location:** `services/ai-automation-service/tests/test_synergy_suggestion_generator.py`  
**Framework:** pytest with pytest-asyncio  
**Coverage Target:** >80%

**Example Test:**
```python
@pytest.mark.asyncio
async def test_device_pair_suggestion_generation():
    """Test generating suggestion from device pair synergy"""
    synergy = {
        'synergy_type': 'device_pair',
        'trigger_device': 'binary_sensor.bedroom_motion',
        'action_device': 'light.bedroom_ceiling',
        'area': 'bedroom',
        'impact_score': 0.85
    }
    
    generator = SynergySuggestionGenerator(openai_client, db_session)
    suggestion = await generator.generate_suggestion(synergy)
    
    assert suggestion['type'] == 'synergy_device_pair'
    assert 'automation_yaml' in suggestion
    assert suggestion['confidence'] > 0.7
    assert 'Motion' in suggestion['title'] or 'motion' in suggestion['title']
```

---

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-10-18 | 1.0 | Initial story creation | BMad Master |

---

**Story Status:** Ready for Development  
**Created:** 2025-10-18

