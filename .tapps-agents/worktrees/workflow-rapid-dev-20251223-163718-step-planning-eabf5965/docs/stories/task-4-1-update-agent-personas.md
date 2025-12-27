# Task 4.1: Update Agent Personas with KB Awareness

## Task Information
- **Story**: Context7 Knowledge Base Cache Implementation
- **Task ID**: 4.1
- **Priority**: High
- **Estimate**: 30 minutes
- **Status**: Pending

## Task Description
Update all BMad agent personas to include knowledge base awareness, ensuring agents know about KB-first lookup, fuzzy matching, and intelligent caching capabilities.

## Acceptance Criteria
- [ ] Architect agent persona updated with KB awareness
- [ ] Dev agent persona updated with KB awareness
- [ ] QA agent persona updated with KB awareness
- [ ] BMad Master agent persona updated with KB awareness
- [ ] KB-first lookup principles added to all agents
- [ ] Fuzzy matching awareness added to all agents
- [ ] Cross-reference lookup awareness added to all agents
- [ ] Performance optimization awareness added to all agents

## Implementation Steps

### Step 1: Update Architect Agent Persona
```yaml
# Enhanced architect agent persona
core_principles:
  - Context7 KB Integration - Check local knowledge base first, then Context7 if needed
  - Intelligent Caching - Automatically cache Context7 results for future use
  - Cross-Reference Lookup - Use topic expansion and library relationships
  - Sharded Knowledge - Leverage BMad sharding for organized documentation storage
  - Fuzzy Matching - Handle library/topic name variants intelligently
  - Performance Optimization - Target 87%+ cache hit rate and 0.15s response time
```

### Step 2: Update Dev Agent Persona
```yaml
# Enhanced dev agent persona
core_principles:
  - Context7 KB Integration - Check local knowledge base first, then Context7 if needed
  - Intelligent Caching - Automatically cache Context7 results for future use
  - Cross-Reference Lookup - Use topic expansion and library relationships
  - Sharded Knowledge - Leverage BMad sharding for organized documentation storage
  - Fuzzy Matching - Handle library/topic name variants intelligently
  - Performance Optimization - Target 87%+ cache hit rate and 0.15s response time
  - Library Implementation - Use KB-first approach for external library implementations
```

### Step 3: Update QA Agent Persona
```yaml
# Enhanced QA agent persona
core_principles:
  - Context7 KB Integration - Check local knowledge base first, then Context7 if needed
  - Intelligent Caching - Automatically cache Context7 results for future use
  - Cross-Reference Lookup - Use topic expansion and library relationships
  - Sharded Knowledge - Leverage BMad sharding for organized documentation storage
  - Fuzzy Matching - Handle library/topic name variants intelligently
  - Performance Optimization - Target 87%+ cache hit rate and 0.15s response time
  - Risk Assessment - Use KB-first approach for library risk assessments
```

### Step 4: Update BMad Master Agent Persona
```yaml
# Enhanced BMad Master agent persona
core_principles:
  - Context7 KB Integration - Check local knowledge base first, then Context7 if needed
  - Intelligent Caching - Automatically cache Context7 results for future use
  - Cross-Reference Lookup - Use topic expansion and library relationships
  - Sharded Knowledge - Leverage BMad sharding for organized documentation storage
  - Fuzzy Matching - Handle library/topic name variants intelligently
  - Performance Optimization - Target 87%+ cache hit rate and 0.15s response time
  - KB Management - Provide KB management commands and analytics
```

## Files to Modify
- `.bmad-core/agents/architect.md`
- `.bmad-core/agents/dev.md`
- `.bmad-core/agents/qa.md`
- `.bmad-core/agents/bmad-master.md`

## Testing
- [ ] All agent personas updated with KB awareness
- [ ] KB-first lookup principles added to all agents
- [ ] Fuzzy matching awareness added to all agents
- [ ] Cross-reference lookup awareness added to all agents
- [ ] Performance optimization awareness added to all agents
- [ ] Agent personas maintain existing functionality
- [ ] KB awareness integrates with existing principles
- [ ] All agents load without errors

## Success Criteria
- All agent personas updated with KB awareness
- KB-first lookup principles integrated
- Fuzzy matching awareness added
- Cross-reference lookup awareness added
- Performance optimization awareness added
- Ready for Phase 4 completion
