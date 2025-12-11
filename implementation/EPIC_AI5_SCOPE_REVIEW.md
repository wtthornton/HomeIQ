# Epic AI-5: Unified Contextual Intelligence Service - Scope Review

**Review Date:** December 2025  
**Deployment Context:** Single-home NUC (Intel NUC i3/i5, 8-16GB RAM)  
**Goal:** Ensure epic is appropriately scoped, not over-engineered

## Current State Analysis

### ✅ Existing Infrastructure

**Contextual Pattern Detectors (Already Implemented):**
- ✅ `WeatherOpportunityDetector` - Detects frost protection, pre-heating/cooling opportunities
- ✅ `EnergyOpportunityDetector` - Detects off-peak scheduling opportunities
- ✅ `EventOpportunityDetector` - Detects sports/calendar/holiday event opportunities

**Current Usage:**
- ✅ **3 AM Workflow** (`daily_analysis.py`) - Uses all 3 detectors (lines 1092-1162)
- ❌ **Ask AI Router** (`ask_ai_router.py`) - Does NOT use contextual detectors yet

**Architecture Gap:**
- Contextual intelligence is ONLY available in 3 AM batch workflow
- User-initiated Ask AI queries do NOT get contextual suggestions
- Code duplication risk if we add contextual logic to Ask AI separately

## Epic Scope Review

### Phase 1: Quick Integration (Stories AI5.1-AI5.2)
**Goal:** Quick weather context integration for Ask AI queries

**Story AI5.1: Quick Weather Context Integration for Ask AI**
- Add weather context to Ask AI queries for climate devices
- Reuse existing `WeatherOpportunityDetector`
- Simple integration, no architectural changes

**Story AI5.2: Weather Context Configuration and Toggle**
- Add configuration to enable/disable weather context
- Simple settings flag

**Assessment:** ✅ **APPROPRIATELY SCOPED**
- Quick win (2-3 hours per story)
- Reuses existing detector
- No over-engineering
- Immediate user value

### Phase 2: Unified Service Architecture (Stories AI5.3-AI5.11)
**Goal:** Unified service for all contextual patterns (weather, energy, events)

**Story AI5.3: Create UnifiedSuggestionEngine Class**
- Create unified class that wraps all contextual detectors
- Single interface for both 3 AM workflow and Ask AI

**Stories AI5.4-AI5.6: Add Context to Unified Service**
- Add weather, energy, event context to unified service
- Reuse existing detectors

**Stories AI5.7-AI5.8: Refactor to Use Unified Service**
- Refactor Ask AI router to use unified service
- Refactor daily analysis to use unified service
- Eliminate code duplication

**Stories AI5.9-AI5.11: Configuration, Monitoring, Testing**
- Advanced configuration system
- Monitoring and health checks
- Comprehensive testing

**Assessment:** ⚠️ **NEEDS SIMPLIFICATION**

**Concerns:**
1. **Story AI5.9 (Advanced Configuration System)** - May be over-engineered
   - Current: Simple settings flags sufficient
   - Risk: Complex configuration system not needed for single-home
   - **Recommendation:** Simplify to basic enable/disable flags

2. **Story AI5.10 (Monitoring and Health Checks)** - May be over-engineered
   - Current: Basic logging sufficient
   - Risk: Complex monitoring not needed for single-home
   - **Recommendation:** Simplify to basic logging/metrics

3. **Story AI5.11 (Comprehensive Testing Suite)** - Appropriate
   - Unit tests for unified service
   - Integration tests for both paths
   - **Recommendation:** Keep as-is

## Recommended Scope Adjustments

### ✅ KEEP (Appropriately Scoped)
- Story AI5.1: Quick Weather Context Integration
- Story AI5.2: Weather Context Configuration
- Story AI5.3: UnifiedSuggestionEngine Class
- Story AI5.4: Add Weather Context to Unified Service
- Story AI5.5: Add Energy Context to Unified Service
- Story AI5.6: Add Event Context to Unified Service
- Story AI5.7: Refactor Ask AI Router
- Story AI5.8: Refactor Daily Analysis
- Story AI5.11: Comprehensive Testing Suite

### ⚠️ SIMPLIFY
- **Story AI5.9: Advanced Configuration System** → **Simple Configuration Flags**
  - Replace with simple enable/disable flags per context type
  - Use existing settings system (no new infrastructure)
  - Estimated: 1-2 hours (vs 2 points/4-6 hours)

- **Story AI5.10: Monitoring and Health Checks** → **Basic Logging**
  - Replace with basic logging/metrics
  - Use existing logging infrastructure
  - Estimated: 1-2 hours (vs 2 points/4-6 hours)

## Revised Epic Scope

### Phase 1: Quick Integration (2 stories, ~4-6 hours)
- ✅ AI5.1: Quick Weather Context Integration
- ✅ AI5.2: Weather Context Configuration

### Phase 2: Unified Service Architecture (7 stories, ~20-30 hours)
- ✅ AI5.3: Create UnifiedSuggestionEngine Class
- ✅ AI5.4: Add Weather Context to Unified Service
- ✅ AI5.5: Add Energy Context to Unified Service
- ✅ AI5.6: Add Event Context to Unified Service
- ✅ AI5.7: Refactor Ask AI Router
- ✅ AI5.8: Refactor Daily Analysis
- ✅ AI5.9: Simple Configuration Flags (SIMPLIFIED)
- ✅ AI5.10: Basic Logging (SIMPLIFIED)
- ✅ AI5.11: Comprehensive Testing Suite

**Total Effort:** 9 stories, ~24-36 hours (vs 11 stories, 10 weeks estimated)

## Architecture Design

### UnifiedSuggestionEngine Class Structure

```python
class UnifiedSuggestionEngine:
    """
    Unified service for contextual intelligence.
    Used by both 3 AM workflow and Ask AI queries.
    """
    def __init__(
        self,
        weather_detector: WeatherOpportunityDetector | None = None,
        energy_detector: EnergyOpportunityDetector | None = None,
        event_detector: EventOpportunityDetector | None = None,
        enable_weather: bool = True,
        enable_energy: bool = True,
        enable_events: bool = True
    ):
        # Simple enable/disable flags
        self.enable_weather = enable_weather
        self.enable_energy = enable_energy
        self.enable_events = enable_events
        
        # Reuse existing detectors
        self.weather_detector = weather_detector
        self.energy_detector = energy_detector
        self.event_detector = event_detector
    
    async def get_contextual_suggestions(
        self,
        query: str | None = None,
        device_names: list[str] | None = None,
        area_id: str | None = None
    ) -> list[dict]:
        """
        Get contextual suggestions based on query context.
        Returns list of opportunity dictionaries.
        """
        suggestions = []
        
        if self.enable_weather and self.weather_detector:
            weather_suggestions = await self.weather_detector.detect_opportunities()
            suggestions.extend(weather_suggestions)
        
        if self.enable_energy and self.energy_detector:
            energy_suggestions = await self.energy_detector.detect_opportunities()
            suggestions.extend(energy_suggestions)
        
        if self.enable_events and self.event_detector:
            event_suggestions = await self.event_detector.detect_opportunities()
            suggestions.extend(event_suggestions)
        
        return suggestions
```

**Key Design Principles:**
- ✅ Reuse existing detectors (no duplication)
- ✅ Simple enable/disable flags (no complex configuration)
- ✅ Single interface for both paths
- ✅ Backward compatible (existing code continues to work)

## Performance Considerations

**Current Performance:**
- 3 AM workflow: Contextual detection takes ~5-10 seconds (acceptable for batch)
- Ask AI queries: Need <100ms additional latency (per epic requirements)

**Optimization Strategy:**
- Cache weather/energy/event data (already implemented in detectors)
- Lazy initialization (only create detectors when needed)
- Async operations (already async)
- Filter suggestions by query context (device names, area)

**Expected Performance:**
- Ask AI queries: +50-100ms latency (acceptable)
- 3 AM workflow: No change (same performance)

## Risk Assessment

### ✅ Low Risk
- Reusing existing detectors (proven code)
- Simple integration (no complex architecture)
- Backward compatible (existing code continues to work)

### ⚠️ Medium Risk
- Performance impact on Ask AI queries (mitigated by caching)
- Integration complexity (mitigated by phased approach)

### ❌ No High Risks
- No over-engineering concerns
- No complex infrastructure needed
- No breaking changes

## Verdict

**Status:** ✅ **APPROPRIATELY SCOPED** (with simplifications)

**Recommendations:**
1. ✅ **Proceed with execution** - Epic is well-scoped
2. ⚠️ **Simplify Stories AI5.9 and AI5.10** - Replace with simple flags/logging
3. ✅ **Use phased approach** - Phase 1 quick wins, Phase 2 unified service
4. ✅ **Reuse existing detectors** - No duplication, proven code

**Estimated Timeline:**
- Phase 1: 1-2 days (2 stories)
- Phase 2: 1-2 weeks (7 stories)
- **Total: 2-3 weeks** (vs 10 weeks estimated - 70% reduction)

---

**Review Status:** ✅ **APPROVED FOR EXECUTION** (with simplifications)  
**Next Step:** Start with Story AI5.1 (Quick Weather Context Integration)

