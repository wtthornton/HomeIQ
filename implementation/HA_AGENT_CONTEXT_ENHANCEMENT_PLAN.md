# HA AI Agent Context Enhancement Implementation Plan

## Overview

Enhance the HA AI Agent service to include additional context information that will improve LLM automation generation accuracy and reduce user back-and-forth.

## Current State

### What's Currently Passed to LLM:
- System prompt with Home Assistant context (cached)
  - Entity inventory (IDs, names, states, areas, device IDs)
  - Areas (IDs, names, aliases)
  - Services (schemas, parameters, capabilities)
  - Device capabilities (enum values, ranges, types)
  - Helpers & scenes
  - Entity attributes (effects, presets, color modes)
- Conversation history (with token budget truncation)
- Current user message

### Enhancement Tool:
- Uses `suggest_automation_enhancements` tool
- Includes: original prompt, optional YAML, creativity level
- Uses Patterns API and Synergies API

## Recommended Enhancements (Priority Order)

### Priority 1: Device State Context (HIGH IMPACT)
**What:** Include current states of entities mentioned in user prompt
**Why:** LLM can make smarter decisions about automation logic
**Implementation:**
- Add device state snapshot service
- Extract entity IDs from user prompt
- Fetch current states via HA Client or Data API
- Inject into context when entities are mentioned

### Priority 2: Recent Automation Patterns (HIGH IMPACT)
**What:** Include user's last 5-10 created automations
**Why:** Learn user preferences and common patterns
**Implementation:**
- Query Home Assistant for recent automations
- Extract patterns (triggers, actions, modes)
- Include in context as "User's Recent Automation Patterns"

### Priority 3: Conflict Detection (MEDIUM IMPACT)
**What:** Check for existing automations that might conflict
**Why:** Prevent overlapping automations, warn user
**Implementation:**
- Analyze user prompt for entities/areas/triggers
- Query existing automations
- Detect potential conflicts (same entities, overlapping times)
- Include warnings in context or preview

### Priority 4: Enhancement Preferences (MEDIUM IMPACT)
**What:** Track user's enhancement selection history
**Why:** Better enhancement suggestions based on preferences
**Implementation:**
- Store enhancement selections in conversation or user profile
- Include preferred enhancement types in enhancement tool
- Pass to LLM when generating suggestions

## Implementation Approach

### Phase 1: Device State Context (Simplest)
1. Create `DeviceStateContextService`
2. Extract entities from user prompt
3. Fetch current states
4. Inject into context

### Phase 2: Recent Automation Patterns
1. Create `AutomationPatternsService`
2. Query HA for recent automations
3. Extract patterns
4. Add to context

### Phase 3: Conflict Detection
1. Create `ConflictDetectionService`
2. Analyze prompt for conflict indicators
3. Query existing automations
4. Generate conflict warnings

### Phase 4: Enhancement Preferences
1. Extend conversation service to track enhancements
2. Add preference tracking
3. Include in enhancement tool

## Technical Considerations

- **Token Budget:** New context must fit within existing token limits
- **Performance:** State fetching should be async and cached
- **Backward Compatibility:** All changes should be optional/graceful degradation
- **Caching:** Device states should be cached (short TTL)
- **Privacy:** Only include relevant context, not all device states

## Integration Points

- **ContextBuilder:** Add new context services
- **PromptAssemblyService:** Optionally include enhanced context
- **Enhancement Tool:** Include preferences
- **Preview Tool:** Include conflict warnings
