# Epic AI-5: Unified Contextual Intelligence Service

**Epic ID**: AI-5  
**Title**: Unified Contextual Intelligence Service (Phase 1 + Phase 2)  
**Status**: Planning  
**Priority**: High  
**Estimated Duration**: 2-3 weeks (1-2 days Phase 1 + 1-2 weeks Phase 2) ⚠️ **SIMPLIFIED SCOPE**  
**Value**: High (8/10)  
**Complexity**: Medium (5/10)  
**Created**: December 19, 2024  
**Last Updated**: December 2025  
**Scope Review**: Simplified Stories AI5.9 and AI5.10 (see `implementation/EPIC_AI5_SCOPE_REVIEW.md`)  

## Epic Description

Implement a comprehensive unified intelligence service that provides consistent contextual awareness across both automated batch processing and user-initiated queries. This epic includes Phase 1 quick integration enhancements and Phase 2 unified service architecture, eliminating the current architectural split and creating a seamless user experience.

## Business Value

- **Immediate Value**: Quick weather context integration for climate queries (Phase 1)
- **Consistency**: Users receive the same quality of contextual suggestions regardless of entry point
- **Enhanced User Experience**: Real-time queries include weather-aware, energy-aware, and event-aware suggestions
- **Code Reuse**: Single implementation of contextual intelligence eliminates duplication
- **Maintainability**: Centralized contextual logic easier to maintain and extend
- **Feature Parity**: User queries get same intelligence as automated suggestions

## Success Criteria

- [ ] **Phase 1**: Weather context works in Ask AI queries within 4 weeks
- [ ] **Phase 2**: All contextual patterns (weather, energy, events) work in both paths
- [ ] User queries include relevant contextual suggestions
- [ ] Daily analysis and user queries use the same contextual intelligence service
- [ ] Performance impact is minimal (<100ms additional latency for user queries)
- [ ] All existing functionality continues to work unchanged
- [ ] Contextual features can be enabled/disabled via configuration

## Stories

### Phase 1: Quick Integration (Weeks 1-4)
- [AI5.1: Quick Weather Context Integration for Ask AI](story-ai5-1-quick-weather-context-integration.md) - Foundation (2 points)
- [AI5.2: Weather Context Configuration and Toggle](story-ai5-2-weather-context-configuration.md) - Foundation (1 point)

### Phase 2: Unified Service Architecture (Weeks 5-10)
- [AI5.3: Create UnifiedSuggestionEngine Class](story-ai5-3-create-unified-suggestion-engine-class.md) - Foundation (2 points)
- [AI5.4: Add Weather Context to Unified Service](story-ai5-4-add-weather-context-unified-service.md) - Feature (2 points)
- [AI5.5: Add Energy Context to Unified Service](story-ai5-5-add-energy-context-unified-service.md) - Feature (2 points)
- [AI5.6: Add Event Context to Unified Service](story-ai5-6-add-event-context-unified-service.md) - Feature (2 points)
- [AI5.7: Refactor Ask AI Router to Use Unified Service](story-ai5-7-refactor-ask-ai-router-unified-service.md) - Feature (3 points)
- [AI5.8: Refactor Daily Analysis to Use Unified Service](story-ai5-8-refactor-daily-analysis-unified-service.md) - Feature (3 points)
- [AI5.9: Simple Configuration Flags](story-ai5-9-simple-configuration-flags.md) - Foundation (1 point) ⚠️ **SIMPLIFIED**
- [AI5.10: Basic Logging](story-ai5-10-basic-logging.md) - Foundation (1 point) ⚠️ **SIMPLIFIED**
- [AI5.11: Comprehensive Testing Suite](story-ai5-11-comprehensive-testing-suite.md) - Polish (3 points)

## Timeline

### Phase 1: Quick Integration (1-2 days)
- **Day 1**: Quick Weather Context Integration for Ask AI
- **Day 2**: Weather Context Configuration and Testing

### Phase 2: Unified Service Architecture (1-2 weeks)
- **Week 1**: Unified Suggestion Engine Foundation + Energy/Event Context Integration
- **Week 2**: Ask AI Router Refactoring + Daily Analysis Integration + Simple Configuration/Logging + Testing

## Value Delivery Timeline

- **Day 1**: First Value Delivery - Weather context working in Ask AI queries
- **Day 2**: Phase 1 Complete - Weather context fully integrated and configured
- **Week 1**: Energy and Event Context - All contextual patterns available in unified service
- **Week 2**: Full Integration Complete - Both user queries and daily analysis use unified service
- **Week 2**: Production Ready - Comprehensive testing and documentation

## Risk Mitigation

### Technical Risks
- **Performance Impact**: Implement caching and optimization strategies
- **Integration Complexity**: Use incremental integration approach
- **Configuration Complexity**: Start with simple configuration, enhance iteratively

### Timeline Risks
- **Dependency Delays**: Parallel development where possible
- **Testing Overhead**: Implement testing incrementally
- **Integration Issues**: Early integration testing

### User Experience Risks
- **Response Time**: Performance monitoring and optimization
- **Suggestion Quality**: A/B testing and user feedback
- **Configuration Complexity**: Sensible defaults and clear documentation

## Dependencies

- Existing contextual pattern detectors (WeatherOpportunityDetector, EnergyOpportunityDetector, EventOpportunityDetector)
- Ask AI Router (services/ai-automation-service/src/api/ask_ai_router.py)
- Daily Analysis Scheduler (services/ai-automation-service/src/scheduler/daily_analysis.py)
- Data API Client, InfluxDB Client, OpenAI Client

## Acceptance Criteria

- [ ] Weather context works in Ask AI queries for climate devices
- [ ] All contextual patterns (weather, energy, events) work in both user queries and daily analysis
- [ ] Unified service provides consistent suggestion format across all paths
- [ ] Performance requirements met (<100ms additional latency for user queries)
- [ ] Configuration system allows enabling/disabling contextual features
- [ ] Comprehensive testing and documentation completed
- [ ] All existing functionality continues to work unchanged

## Definition of Done

- [ ] All stories completed and tested
- [ ] Integration testing passed
- [ ] Performance requirements met
- [ ] Documentation updated
- [ ] Code reviewed and approved
- [ ] Deployed to production
- [ ] User acceptance testing completed
