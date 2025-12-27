# Epic AI-6: Blueprint-Enhanced Suggestion Intelligence

**Status:** ✅ **COMPLETE** (All 14 Stories Complete)  
**Type:** Brownfield Enhancement (AI Automation Service)  
**Priority:** High  
**Effort:** 14 Stories (32 story points, 6-8 weeks estimated)  
**Created:** November 2025  
**Last Updated:** December 2025  
**Completed Stories:** AI6.1, AI6.2, AI6.3, AI6.4, AI6.5, AI6.6, AI6.7, AI6.8, AI6.9, AI6.10, AI6.11, AI6.12, AI6.13, AI6.14 (14/14 stories, 100% complete)

---

## Epic Goal

Transform blueprints from late-stage YAML generation tool into core suggestion quality and discovery mechanism. Enable proactive discovery of proven automation opportunities, blueprint-validated patterns, and user-configurable suggestion preferences. This epic enhances suggestion quality and user control while maintaining all existing functionality.

**Business Value:**
- **+50% suggestion diversity** - Add blueprint opportunities to existing patterns/features/synergies
- **+30% user trust** - Community-validated suggestions increase confidence
- **+40% adoption rate** - Proven automations preferred over experimental
- **100% user control** - Customizable suggestion count and creativity levels

---

## Existing System Context

### Current Functionality

**AI Automation Service** (Port 8024) currently:
- Runs daily 3 AM batch job analyzing historical Home Assistant events
- Detects patterns (time-of-day, co-occurrence, anomaly) from usage data
- Discovers device capabilities and underutilized features
- Detects cross-device synergies (Epic AI-3)
- Generates human-readable automation suggestions
- Uses blueprints **only after** user approval (YAML generation via BlueprintMatcher)

**Blueprint Integration Current State:**
- Blueprint matching in YAML generation (Blueprint-First Strategy)
- Automation-miner service provides blueprint corpus (Port 8029)
- MinerIntegration utility for blueprint search
- Blueprints used for reliability, not discovery

**Current Limitations:**
- Blueprints only used at YAML generation stage (too late for discovery)
- Users have no control over suggestion count (fixed top 10)
- Users have no control over creativity level
- System misses proven automation opportunities matching user devices
- No validation of detected patterns against community-proven automations
- Suggestions are purely data-driven (what you DO) vs opportunity-driven (what you COULD do)

### Technology Stack

- **Service:** `services/ai-automation-service/` (FastAPI 0.115.x, Python 3.12+)
- **Blueprint Service:** `services/automation-miner/` (Port 8029)
- **Integration:** `services/ai-automation-service/src/utils/miner_integration.py`
- **Existing Blueprint Matching:** `services/ai-automation-service/src/services/blueprints/matcher.py`
- **Daily Scheduler:** `services/ai-automation-service/src/scheduler/daily_analysis.py`
- **Ask AI Router:** `services/ai-automation-service/src/api/ask_ai_router.py`
- **Database:** SQLite (`user_preferences` table exists from Epic AI-2.4)

### Integration Points

- Daily batch job pipeline (Phase 1-6 in `daily_analysis.py`)
- Ask AI query processing (`ask_ai_router.py`)
- Blueprint matching infrastructure (existing `blueprints/matcher.py`)
- Suggestion generation pipeline (Phase 5 description generation)
- User preferences storage (SQLite `user_preferences` table)

---

## Enhancement Details

### What's Being Added/Changed

1. **Blueprint Opportunity Discovery** (NEW)
   - Phase 3d in daily batch: Scan user devices, search blueprints, find matching opportunities
   - Ask AI integration: Discover blueprint opportunities based on user queries
   - Proactive discovery of proven automations even without usage patterns

2. **Blueprint-Enhanced Pattern Validation** (ENHANCEMENT)
   - Validate detected patterns against blueprints
   - Boost confidence scores for blueprint-validated patterns
   - Improve suggestion ranking and quality

3. **Blueprint-Enriched Descriptions** (ENHANCEMENT)
   - Include blueprint hints in suggestion descriptions
   - Show community validation in user-facing text
   - Example: "Based on 'Motion-Activated Light' blueprint"

4. **User-Configurable Preferences** (NEW)
   - Suggestion count configuration (5-50 range, default: 10)
   - Creativity level (conservative/balanced/creative)
   - Blueprint preference (low/medium/high)
   - Apply preferences to both 3 AM run and Ask AI

### How It Integrates

- **Non-Breaking Changes:** All enhancements are additive, existing functionality unchanged
- **Graceful Degradation:** If automation-miner service unavailable, falls back to AI-only generation
- **Incremental Integration:** Each phase builds on previous work
- **Performance Optimized:** Caching, async operations, batch searches (<50ms additional latency)

### Success Criteria

1. **Functional:**
   - Blueprint opportunities discovered in 3 AM run and Ask AI
   - Patterns validated with confidence boosting
   - Suggestions include blueprint hints
   - Users can configure all preferences

2. **Technical:**
   - Performance requirements met (<50ms additional latency)
   - Graceful degradation implemented
   - Unit tests >90% coverage
   - Integration tests cover all paths

3. **Quality:**
   - Blueprint searches cached
   - Service health checks prevent failures
   - Sensible defaults for preferences
   - Comprehensive documentation

---

## Stories

### Phase 1: Blueprint Opportunity Discovery (Weeks 1-3)

#### Story AI6.1: Blueprint Opportunity Discovery Service Foundation
**Type:** Foundation  
**Points:** 2  
**Effort:** 4-6 hours

Create foundation service for discovering blueprint opportunities from user device inventory. Scan devices, search blueprints, calculate fit scores.

**Acceptance Criteria:**
- `blueprint_discovery/opportunity_finder.py` service created
- Device scanning from Home Assistant integration
- Blueprint search via MinerIntegration
- Fit score calculation (device types, use case, integration)
- Unit tests with >90% coverage

---

#### Story AI6.2: Blueprint Validation Service for Patterns
**Type:** Foundation  
**Points:** 2  
**Effort:** 4-6 hours

Create service to validate detected patterns against blueprints and boost confidence scores for matches.

**Acceptance Criteria:**
- `blueprint_discovery/blueprint_validator.py` service created
- Pattern-to-blueprint matching logic
- Confidence boost calculation (0.1-0.3 boost for validated patterns)
- Integration with existing pattern detection
- Unit tests with >90% coverage

---

#### Story AI6.3: Blueprint Opportunity Discovery in 3 AM Run
**Type:** Feature  
**Points:** 3  
**Effort:** 6-8 hours

Integrate blueprint opportunity discovery into daily batch job as new Phase 3d.

**Acceptance Criteria:**
- Phase 3d added to `daily_analysis.py`
- Blueprint opportunities discovered after Phase 3 (pattern detection)
- Opportunities stored in SQLite for Phase 5 processing
- Performance impact <30ms per run
- Integration tests verify discovery works

---

#### Story AI6.4: Blueprint Opportunity Discovery in Ask AI
**Type:** Feature  
**Points:** 3  
**Effort:** 6-8 hours

Add blueprint opportunity discovery to Ask AI query processing.

**Acceptance Criteria:**
- Blueprint discovery in `ask_ai_router.py` query flow
- Device extraction from user query
- Blueprint search for matching device types
- Blueprint-inspired suggestions generated
- Integration tests verify discovery in queries

---

### Phase 2: Blueprint-Enhanced Suggestions (Weeks 3-5)

#### Story AI6.5: Pattern Validation with Blueprint Boost
**Type:** Feature  
**Points:** 2  
**Effort:** 4-6 hours

Validate patterns against blueprints and boost confidence scores during Phase 5.

**Acceptance Criteria:**
- Pattern validation integrated into Phase 5
- Confidence boost applied to validated patterns (0.1-0.3 increase)
- Validation logged for debugging
- Unit tests verify boost calculation
- Integration tests verify ranking changes

---

#### Story AI6.6: Blueprint-Enriched Description Generation
**Type:** Feature  
**Points:** 2  
**Effort:** 4-6 hours

Enhance suggestion descriptions to include blueprint hints and community validation.

**Acceptance Criteria:**
- Description generation includes blueprint hints
- Format: "Based on 'Motion-Activated Light' blueprint"
- Hints only shown when blueprint match score ≥0.8
- OpenAI prompt enhanced with blueprint context
- Unit tests verify description format

---

#### Story AI6.7: User Preference Configuration System
**Type:** Foundation  
**Points:** 2  
**Effort:** 4-6 hours

Create preference management system using existing `user_preferences` SQLite table.

**Acceptance Criteria:**
- `blueprint_discovery/preference_manager.py` service created
- Preference storage in SQLite (max_suggestions, creativity_level, blueprint_preference)
- Default values defined and applied
- Preference validation (ranges, enum values)
- Unit tests with >90% coverage

---

### Phase 3: User-Configurable Suggestions (Weeks 5-7)

#### Story AI6.8: Configurable Suggestion Count (5-50)
**Type:** Feature  
**Points:** 2  
**Effort:** 4-6 hours

Enable users to configure maximum suggestion count in both 3 AM run and Ask AI.

**Acceptance Criteria:**
- Preference `max_suggestions` (5-50, default: 10)
- Applied in Phase 5 description generation
- Applied in Ask AI suggestion generation
- Validation prevents invalid ranges
- Integration tests verify count limits

---

#### Story AI6.9: Configurable Creativity Levels
**Type:** Feature  
**Points:** 3  
**Effort:** 6-8 hours

Implement creativity level system (conservative/balanced/creative) affecting confidence thresholds and suggestion types.

**Acceptance Criteria:**
- Creativity levels defined in config (conservative/balanced/creative)
- Each level has min_confidence, blueprint_weight, experimental_boost
- Applied in Phase 5 and Ask AI suggestion filtering
- Conservative: high confidence, blueprint-focused
- Creative: lower confidence, more experimental suggestions
- Integration tests verify filtering works

---

#### Story AI6.10: Blueprint Preference Configuration
**Type:** Feature  
**Points:** 2  
**Effort:** 4-6 hours

Enable users to configure blueprint preference (low/medium/high) affecting blueprint opportunity ranking.

**Acceptance Criteria:**
- Preference `blueprint_preference` (low/medium/high)
- Affects blueprint opportunity priority in ranking
- High preference: blueprint opportunities ranked higher
- Low preference: blueprint opportunities ranked lower
- Integration tests verify ranking changes

---

### Phase 4: Integration & Polish (Weeks 7-8)

#### Story AI6.11: Preference-Aware Suggestion Ranking
**Type:** Feature  
**Points:** 2  
**Effort:** 4-6 hours

Implement unified ranking system that applies all user preferences (count, creativity, blueprint preference).

**Acceptance Criteria:**
- Unified ranking in `preference_aware_ranker.py`
- Applies max_suggestions limit
- Applies creativity level filtering
- Applies blueprint preference weighting
- Integration tests verify full ranking logic

---

#### Story AI6.12: Frontend Preference Settings UI
**Type:** Feature  
**Points:** 3  
**Effort:** 8-10 hours

Add preference settings UI to AI Automation UI (Port 3001) for configuring suggestions.

**Acceptance Criteria:**
- Settings page/component created
- Controls for max_suggestions (slider 5-50)
- Controls for creativity_level (dropdown)
- Controls for blueprint_preference (dropdown)
- API endpoint to update preferences
- E2E tests verify UI works

---

#### Story AI6.13: Comprehensive Testing Suite
**Type:** Polish  
**Points:** 3  
**Effort:** 8-10 hours

Create comprehensive test suite covering all blueprint discovery and preference features.

**Acceptance Criteria:**
- Unit tests for all new services (>90% coverage)
- Integration tests for 3 AM run integration
- Integration tests for Ask AI integration
- Performance tests (<50ms latency)
- E2E tests for preference settings UI
- All tests passing

---

#### Story AI6.14: Documentation & User Guide
**Type:** Polish  
**Points:** 2  
**Effort:** 4-6 hours

Document all new features, update technical whitepaper, create user guide for preferences.

**Acceptance Criteria:**
- Technical documentation updated (architecture, data flow)
- User guide for preference settings
- API documentation updated
- Code comments for complex logic
- README updated with new features

---

## Compatibility Requirements

- [x] Existing suggestion generation continues unchanged
- [x] All existing patterns/features/synergies still work
- [x] Blueprint YAML generation unchanged (still Blueprint-First Strategy)
- [x] Graceful degradation if automation-miner unavailable
- [x] Performance impact minimal (<50ms additional latency)
- [x] No breaking changes to existing APIs

---

## Risk Mitigation

### Technical Risks

**Blueprint Service Availability:**
- **Risk:** Automation-miner service unavailable
- **Mitigation:** Graceful degradation, service health checks, fallback to AI-only generation
- **Monitoring:** Health check before blueprint searches

**Performance Impact:**
- **Risk:** Blueprint searches add latency
- **Mitigation:** Caching, async operations, batch searches, performance monitoring
- **Target:** <50ms additional latency per suggestion batch

**Configuration Complexity:**
- **Risk:** Too many options confuse users
- **Mitigation:** Sensible defaults, clear documentation, progressive disclosure in UI
- **Testing:** User acceptance testing for preference UI

### Timeline Risks

**Integration Complexity:**
- **Risk:** Complex integration with existing suggestion pipeline
- **Mitigation:** Incremental integration, comprehensive testing, clear interfaces
- **Approach:** Phase-by-phase integration with testing at each step

**Dependency Delays:**
- **Risk:** Automation-miner service changes
- **Mitigation:** API abstraction layer, version compatibility checks
- **Isolation:** MinerIntegration utility provides abstraction

### User Experience Risks

**Suggestion Overload:**
- **Risk:** Too many suggestions overwhelm users
- **Mitigation:** Configurable limits (5-50), smart ranking, user feedback loop
- **Default:** Conservative default (10 suggestions)

**Quality Concerns:**
- **Risk:** Low-quality blueprints affect suggestions
- **Mitigation:** Quality filtering (min_quality=0.7), user feedback tracking
- **Validation:** Blueprint quality score checked before matching

---

## Dependencies

### External Dependencies
- **Automation-miner Service** (Port 8029): Blueprint corpus and search API
- **MinerIntegration** utility: Existing blueprint search infrastructure

### Internal Dependencies
- **Pattern Detection** (Epic AI-1): Pattern-based suggestions to validate
- **Device Intelligence** (Epic AI-2): Device capability data
- **Synergy Detection** (Epic AI-3): Synergy opportunities
- **Daily Analysis Scheduler**: 3 AM batch job pipeline
- **Ask AI Router**: Real-time query processing
- **Suggestion Generation Service**: Description generation pipeline
- **User Preferences System**: Preference storage (Epic AI-2.4 / user_preferences table)

### Integration Points
- `services/ai-automation-service/src/scheduler/daily_analysis.py` - Phase 3d (new), Phase 5 (enhanced)
- `services/ai-automation-service/src/api/ask_ai_router.py` - Suggestion generation
- `services/ai-automation-service/src/services/blueprints/` - Existing blueprint matching infrastructure
- `services/ai-automation-service/src/utils/miner_integration.py` - Blueprint search client

---

## Architecture Overview

### New Components

```
services/ai-automation-service/src/
├── blueprint_discovery/              # NEW (Epic AI-6)
│   ├── __init__.py
│   ├── opportunity_finder.py         # Blueprint opportunity discovery
│   ├── blueprint_validator.py        # Pattern validation against blueprints
│   └── preference_manager.py         # User preference management
├── services/blueprints/              # EXISTING (Enhanced)
│   ├── matcher.py                    # EXISTING (used for validation)
│   ├── opportunity_discovery.py      # NEW (Epic AI-6)
│   └── description_enricher.py       # NEW (Epic AI-6)
├── suggestion_generation/            # EXISTING (Enhanced)
│   └── preference_aware_ranker.py    # NEW (Epic AI-6)
└── scheduler/
    └── daily_analysis.py             # MODIFY: Add Phase 3d + enhance Phase 5
```

### Configuration Schema

```python
# User Preferences (stored in user_preferences table)
{
    "max_suggestions": 10,              # 5-50, default: 10
    "creativity_level": "balanced",     # conservative|balanced|creative
    "blueprint_preference": "high"      # low|medium|high
}

# Creativity Configuration
CREATIVITY_CONFIG = {
    "conservative": {
        "min_confidence": 0.85,
        "blueprint_weight": 0.8,
        "experimental_boost": 0.0,
        "max_experimental": 0
    },
    "balanced": {
        "min_confidence": 0.70,
        "blueprint_weight": 0.6,
        "experimental_boost": 0.1,
        "max_experimental": 2
    },
    "creative": {
        "min_confidence": 0.55,
        "blueprint_weight": 0.4,
        "experimental_boost": 0.3,
        "max_experimental": 5
    }
}
```

### Data Flow

```
3 AM Run:
Phase 1-4: [Existing phases]
Phase 3d: Blueprint Opportunity Discovery → NEW
  - Scan user devices
  - Search blueprints
  - Find matching opportunities
Phase 5: Description Generation → ENHANCED
  - Pattern validation (blueprint boost)
  - Description enrichment (blueprint hints)
  - Preference-aware ranking
  - Apply user preferences (count, creativity)

Ask AI:
Query → Entity Extraction → Blueprint Opportunity Discovery → NEW
  - Search blueprints for device types
  - Generate blueprint-inspired suggestions
  - Preference-aware ranking
  - Apply user preferences (count, creativity)
```

---

## Definition of Done

- [ ] All 14 stories completed and tested
- [ ] Integration testing passed (3 AM run + Ask AI)
- [ ] Performance requirements met (<50ms latency)
- [ ] Configuration system tested with all valid ranges
- [ ] Frontend UI tested across browsers
- [ ] Documentation updated (technical + user guides)
- [ ] Code reviewed and approved
- [ ] All existing functionality verified unchanged
- [ ] Graceful degradation tested (automation-miner unavailable)
- [ ] User acceptance testing completed

---

## Related Documentation

- [AI Automation Service Technical Whitepaper](../current/AI_AUTOMATION_SERVICE_TECHNICAL_WHITEPAPER.md)
- [Blueprint Matching Service](../implementation/analysis/HA_BLUEPRINT_ENGINE_IMPLEMENTATION_PLAN.md)
- [Automation Miner Service API](../../services/automation-miner/BLUEPRINT_API.md)
- Epic AI-1: Pattern Detection
- Epic AI-3: Cross-Device Synergy
- Epic AI-4: Community Knowledge Augmentation

---

**Epic Owner:** Product Manager  
**Technical Lead:** AI Automation Service Team  
**Status:** 📋 Planning  
**Next Steps:** Begin Story AI6.1 - Blueprint Opportunity Discovery Service Foundation
