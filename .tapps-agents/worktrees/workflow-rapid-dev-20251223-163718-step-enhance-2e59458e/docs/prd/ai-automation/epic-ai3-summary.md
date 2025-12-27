# Epic AI-3: Cross-Device Synergy & Contextual Opportunities - Summary

**Epic ID:** Epic-AI-3  
**Status:** Ready for Approval  
**Timeline:** 6-8 weeks  
**Total Effort:** 90-110 hours  
**Dependencies:** Epic-AI-1 (Complete), Epic-AI-2 (Complete)

---

## Quick Reference

### The Problem

**Current System Only Detects 20% of Automation Opportunities:**
- ✅ Patterns you ALREADY DO (time-of-day, co-occurrence)
- ✅ Features you DON'T USE (LED notifications, power monitoring)
- ❌ **MISSING: Devices that COULD work together**
- ❌ **MISSING: Weather/energy/event context**

**Examples of Missed Opportunities:**
- Motion sensor + light in same room → NO automation suggested
- Weather data flowing in → NOT used for climate automations
- Energy prices captured → NOT used for scheduling
- Sports schedule available → NOT used for scene activation

---

## The Solution

**Epic AI-3: Opportunity Pattern Detection**

### Three New Detection Types

**1. Device Synergy (Stories AI3.1-AI3.4)**
- Detects unconnected device pairs in same area
- Suggests: "Motion sensor + light → create motion-activated lighting"
- Impact: +40% suggestion coverage

**2. Weather Context (Story AI3.5)**
- Integrates weather data into climate decisions
- Suggests: "Enable frost protection when temp < 32°F tonight"
- Impact: +20% suggestion coverage, energy savings

**3. Energy/Event Context (Stories AI3.6-AI3.7)**
- Uses energy prices and sports schedules
- Suggests: "Run dishwasher during off-peak hours"
- Impact: +20% suggestion coverage, cost savings

---

## Story Breakdown

| Story | Title | Effort | Type | Value |
|-------|-------|--------|------|-------|
| **AI3.1** | Device Synergy Detector Foundation | 10-12h | Backend | 🔥 Critical - Foundation |
| **AI3.2** | Same-Area Device Pair Detection | 8-10h | Backend | 🔥 High - Core feature |
| **AI3.3** | Unconnected Relationship Analysis | 10-12h | Backend | 🔥 High - Intelligence |
| **AI3.4** | Synergy-Based Suggestion Generation | 10-12h | Backend | 🔥 Critical - User-facing |
| **AI3.5** | Weather Context Integration | 8-10h | Backend | ⚡ Medium - Enrichment |
| **AI3.6** | Energy Price Context Integration | 6-8h | Backend | ⚡ Medium - Cost savings |
| **AI3.7** | Sports/Event Context Integration | 6-8h | Backend | ⚙️ Low - Nice-to-have |
| **AI3.8** | Frontend Synergy Tab | 12-14h | Frontend | 🔥 High - UX |
| **AI3.9** | Testing & Documentation | 10-12h | QA | 🔥 High - Quality |

**Total:** 90-110 hours over 6-8 weeks

---

## Implementation Phases

### Phase 1: Core Synergy Detection (Weeks 1-3)
**Goal:** Detect and suggest cross-device automation opportunities

**Stories:** AI3.1 → AI3.2 → AI3.3 → AI3.4  
**Effort:** 38-46 hours  
**Deliverable:** 
- "Your motion sensor and bedroom light could work together"
- "Create motion-activated lighting automation"

**Value:** Addresses 40% of missed opportunities

---

### Phase 2: Context Integration (Weeks 3-5, PARALLEL)
**Goal:** Add weather/energy/event intelligence

**Stories:** AI3.5, AI3.6, AI3.7 (can run in parallel with Phase 1 completion)  
**Effort:** 20-26 hours  
**Deliverable:**
- "Enable frost protection when temp < 32°F"
- "Run dishwasher during off-peak hours ($15/month savings)"
- "Dim lights when game starts"

**Value:** Addresses 40% more opportunities

---

### Phase 3: Frontend & QA (Weeks 5-6)
**Goal:** User interface and comprehensive testing

**Stories:** AI3.8 → AI3.9  
**Effort:** 22-26 hours  
**Deliverable:**
- Synergy Tab in Health Dashboard
- Complete test coverage
- Production-ready Epic AI-3

**Value:** User-facing delivery

---

## Technical Architecture

### New Components

```
services/ai-automation-service/src/
├── synergy_detection/          # NEW (Stories AI3.1-AI3.4)
│   ├── synergy_detector.py     # Core detection engine
│   ├── device_pair_analyzer.py # Same-area pair detection
│   ├── relationship_analyzer.py # Automation checker
│   ├── opportunity_ranker.py   # Impact scoring
│   └── synergy_suggestion_generator.py # OpenAI integration
├── contextual_patterns/        # NEW (Stories AI3.5-AI3.7)
│   ├── weather_opportunities.py # Weather context
│   ├── energy_opportunities.py  # Energy context
│   └── event_opportunities.py   # Sports/events
└── scheduler/
    └── daily_analysis.py       # ENHANCED with Phase 3c
```

### Database Schema

**New Table:**
```sql
CREATE TABLE synergy_opportunities (
    id INTEGER PRIMARY KEY,
    synergy_type VARCHAR(50),     -- 'device_pair', 'weather', 'energy', 'event'
    device_ids TEXT,              -- JSON array
    opportunity_metadata JSON,
    impact_score FLOAT,
    complexity VARCHAR(20),
    confidence FLOAT,
    created_at DATETIME
);
```

**Enhanced Table:**
```sql
-- suggestions table (existing, add new types)
-- New type values:
--   'synergy_device_pair'
--   'synergy_weather'
--   'synergy_energy'
--   'synergy_event'
```

---

## Daily Batch Integration

**Extends Story AI2.5 (Unified Daily Batch):**

```
┌─────────────────────────────────────────────────────────────┐
│ 3 AM Daily AI Analysis (ENHANCED for Epic AI-3)            │
│                                                             │
│ Phase 1: Device Capability Update (AI-2)                   │
│ Phase 2: Fetch Events (Shared)                             │
│ Phase 3: Pattern Detection (AI-1)                          │
│                                                             │
│ Phase 3c: Synergy Detection (AI-3) ← NEW                   │
│   ├─ Device pair detection (same-area)                     │
│   ├─ Weather opportunity detection                         │
│   ├─ Energy opportunity detection                          │
│   └─ Event opportunity detection                           │
│                                                             │
│ Phase 4: Feature Analysis (AI-2)                           │
│                                                             │
│ Phase 5: Suggestion Generation (ENHANCED)                  │
│   ├─ Pattern suggestions (AI-1)                            │
│   ├─ Feature suggestions (AI-2)                            │
│   ├─ Synergy suggestions (AI-3) ← NEW                      │
│   └─ Unified ranking & balancing                           │
│                                                             │
│ Phase 6: MQTT Notification                                 │
└─────────────────────────────────────────────────────────────┘
```

**Performance Impact:**
- +2-3 minutes to daily batch (total: 4-6 minutes)
- +200MB memory peak
- +$0.005 daily OpenAI cost (synergy suggestions)

---

## Expected Outcomes

### Quantitative Metrics

| Metric | Before (AI-1 + AI-2) | After (+ AI-3) | Improvement |
|--------|---------------------|----------------|-------------|
| **Suggestion Types** | 2 types | 6 types | +300% |
| **Opportunity Coverage** | 20% | 80% | +400% |
| **Daily Suggestions** | 5-8 | 8-12 | +50% |
| **User Approval Rate** | 60% | 70% (est) | +10% |
| **Context Utilization** | 0% | 60% | +60% |

### Qualitative Benefits

**For Users:**
- ✅ Discover automations they didn't know were possible
- ✅ Learn what their devices can do together
- ✅ Save energy through weather-aware climate control
- ✅ Reduce costs through energy-aware scheduling
- ✅ Enhance comfort through contextual intelligence

**For System:**
- ✅ Unlocks enrichment data value (weather, energy, events)
- ✅ Proactive suggestions vs reactive observations
- ✅ Educational value (teaches users possibilities)
- ✅ Differentiator from generic home automation platforms

---

## Success Criteria

### Functional
- ✅ Detects 5+ synergy opportunities per week
- ✅ Generates 3-5 synergy suggestions daily
- ✅ >70% user approval rate for synergy suggestions
- ✅ Weather context integrated for all climate devices
- ✅ Energy context available for high-power devices

### Performance
- ✅ Synergy detection <3 minutes
- ✅ Total batch time <6 minutes
- ✅ Memory usage <1.5GB peak
- ✅ API responses <500ms

### Quality
- ✅ >80% code coverage
- ✅ Zero critical bugs
- ✅ Graceful degradation if context unavailable
- ✅ No impact on existing Epic AI-1/AI-2 features

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Too many low-value suggestions | Medium | Medium | Implement high threshold (0.75+), limit to top 5 |
| Weather API failures | Low | Low | Cache last known, graceful skip |
| Performance degradation | Low | Medium | Parallel processing, profiling |
| User overwhelmed | Medium | Medium | Balanced mix, clear categorization |
| Complex cross-device logic | Medium | High | Start with 2-device pairs only |

---

## Dependencies

**Epic AI-1 (Pattern Automation):**
- ✅ Complete - Daily batch scheduler
- ✅ Complete - OpenAI integration
- ✅ Complete - Suggestion storage

**Epic AI-2 (Device Intelligence):**
- ✅ Complete - Device capability discovery
- ✅ Complete - Feature analysis
- ✅ Complete - Unified batch job

**External Systems:**
- ✅ InfluxDB with weather data (enrichment-pipeline)
- ✅ InfluxDB with energy prices (if available)
- ✅ Sports API data (existing)
- ✅ Home Assistant automation API

---

## Next Steps After Approval

1. **Week 1:** Implement AI3.1 (Synergy Detector Foundation)
2. **Week 2:** Implement AI3.2 (Same-Area Device Pairs)
3. **Week 3:** Implement AI3.3 + AI3.4 (Relationship Analysis + Suggestions)
4. **Week 4:** Implement AI3.5 (Weather Context)
5. **Week 5:** Implement AI3.6 + AI3.7 (Energy + Event Context)
6. **Week 6:** Implement AI3.8 + AI3.9 (Frontend + Testing)
7. **Week 7:** Buffer week for fixes/polish
8. **Week 8:** Production deployment

---

## Related Documents

- **Full Epic:** [epic-ai3-cross-device-synergy.md](../epic-ai3-cross-device-synergy.md)
- **Story AI3.1:** [story-ai3-1-synergy-detector-foundation.md](../../stories/story-ai3-1-synergy-detector-foundation.md)
- **Story AI3.4:** [story-ai3-4-synergy-suggestion-generation.md](../../stories/story-ai3-4-synergy-suggestion-generation.md)
- **Story AI3.5:** [story-ai3-5-weather-context-integration.md](../../stories/story-ai3-5-weather-context-integration.md)
- **Architecture:** [architecture-device-intelligence.md](../../architecture-device-intelligence.md)
- **PRD v2.0:** [prd.md](../prd.md)

---

**Epic Status:** Ready for Approval  
**Next Action:** Review with stakeholders, approve, begin Sprint 1  
**Created:** 2025-10-18  
**Updated:** 2025-10-18

