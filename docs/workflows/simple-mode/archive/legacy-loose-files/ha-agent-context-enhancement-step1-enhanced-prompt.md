# Step 1: Enhanced Prompt - HA AI Agent Context Enhancement

## Original Prompt
Enhance HA AI Agent ContextBuilder service to include device state context, recent automation patterns, conflict detection, and user enhancement preferences.

## Enhanced Analysis

### Scope
- **Type**: Brownfield Enhancement
- **Service**: `ha-ai-agent-service/src/services/context_builder.py`
- **Impact**: Medium - Adds new context services, maintains backward compatibility
- **Complexity**: Medium - Requires new services, integration with existing context system

### Requirements Analysis

#### Functional Requirements
1. **Device State Context Service**
   - Fetch current states of entities mentioned in user prompts
   - Extract entity IDs from user prompt using EntityResolutionService
   - Fetch states via Data API or Home Assistant Client
   - Format states for inclusion in context
   - Cache states (short TTL: 30-60 seconds)

2. **Recent Automation Patterns Service**
   - Query Home Assistant for last 5-10 automations
   - Extract patterns (triggers, actions, modes)
   - Format for context inclusion
   - Cache patterns (longer TTL: 5-10 minutes)

3. **Conflict Detection Service**
   - Analyze user prompt for entities/areas/triggers
   - Query existing automations
   - Detect potential conflicts
   - Generate warnings (included in preview, not context)

4. **Enhancement Preferences Tracking**
   - Track enhancement selections in conversation service
   - Include preferences in enhancement tool
   - Store preference patterns

#### Non-Functional Requirements
- **Performance**: State fetching must be async, cached appropriately
- **Compatibility**: Must maintain backward compatibility with existing context system
- **Token Budget**: New context must respect existing token limits (16K tokens)
- **Graceful Degradation**: Services should fail gracefully if dependencies unavailable
- **Caching**: Implement appropriate caching strategies (short TTL for states, longer for patterns)

### Technical Constraints
- Must integrate with existing ContextBuilder architecture
- Must use existing clients (DataAPIClient, HomeAssistantClient)
- Must follow existing service patterns (similar to EntityInventoryService, AreasService)
- Must respect token budget in PromptAssemblyService
- Must maintain async/await patterns throughout

### Implementation Strategy

**Phase 1: Device State Context (First Deliverable)**
- Create DeviceStateContextService
- Integrate into ContextBuilder
- Update PromptAssemblyService to extract entities and include state context
- Add caching with short TTL

**Phase 2: Recent Automation Patterns**
- Create AutomationPatternsService
- Query HA for recent automations
- Extract and format patterns
- Integrate into ContextBuilder

**Phase 3: Conflict Detection**
- Create ConflictDetectionService
- Analyze prompts for conflict indicators
- Query existing automations
- Generate warnings (included in preview)

**Phase 4: Enhancement Preferences**
- Extend ConversationService to track enhancements
- Include preferences in enhancement tool
- Store preference patterns

### Architecture Guidance
- Follow existing service patterns (see EntityInventoryService, AreasService)
- Use dependency injection (services passed to ContextBuilder)
- Implement graceful degradation (return empty/default if dependencies unavailable)
- Use async/await throughout
- Implement caching at service level
- Respect token budgets (truncate/limit context as needed)
