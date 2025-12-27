# Epic AI-3: Cross-Device Synergy & Contextual Opportunities

**Epic ID:** Epic-AI-3  
**Epic Goal:** Detect cross-device automation opportunities and context-aware patterns that users don't realize are possible  
**Phase:** Enhancement to Epic-AI-1 (Patterns) and Epic-AI-2 (Device Intelligence)  
**Timeline:** 6-8 weeks  
**Total Effort:** 90-110 hours  
**Priority:** High (Addresses 80% of missed automation opportunities)

---

## Executive Summary

### The Gap

**Current System (Epic-AI-1 + AI-2):**
- ✅ Detects patterns from historical behavior (time-of-day, co-occurrence)
- ✅ Identifies unused device features (LED notifications, power monitoring)
- ❌ **MISSING:** Cross-device synergy opportunities
- ❌ **MISSING:** Context-aware patterns (weather, energy, events)
- ❌ **MISSING:** "You COULD do this" vs "You ARE doing this"

**Impact:** Current system finds 10-20% of automation opportunities. Epic AI-3 targets the remaining 80%.

---

## Business Value

### Problem Statement

Users have smart devices that could work together but don't because:

1. **Unaware of Combinations:** Motion sensor + light in same room, no automation
2. **Missing Context:** Weather data exists but not used in climate automations
3. **Isolated Features:** Power monitoring exists but not used for auto-shutoff
4. **No Discovery:** System only suggests based on what you DO, not what you COULD do

### Solution

**Epic AI-3 introduces "Opportunity Patterns":**

| Pattern Type | Example | Current System | With Epic AI-3 |
|--------------|---------|----------------|----------------|
| **Device Synergy** | Motion sensor + Light in hallway | ❌ Not detected | ✅ "Create motion-activated lighting" |
| **Weather Context** | Climate device + Weather data | ❌ Unused | ✅ "Enable frost protection when temp < 32°F" |
| **Energy Context** | High-power device + Energy prices | ❌ Unused | ✅ "Run dishwasher during off-peak hours" |
| **Event Context** | Sports schedule + Entertainment setup | ❌ Unused | ✅ "Dim lights when game starts" |
| **Feature Combo** | Power monitoring + Smart plug | ❌ Feature unused | ✅ "Auto-off when idle >30min" |

### Expected Outcomes

- **+300% suggestion diversity** (3 types → 6 types of suggestions)
- **80% opportunity coverage** (vs 20% with just patterns + features)
- **Higher user value** (proactive "you could" vs reactive "you do")
- **Contextual intelligence** (weather, energy, events integrated)

---

## Story List

| Story | Title | Effort | Priority | Dependencies |
|-------|-------|--------|----------|--------------|
| **AI3.1** | Device Synergy Detector Foundation | 10-12h | Critical | AI2.5 |
| **AI3.2** | Same-Area Device Pair Detection | 8-10h | High | AI3.1 |
| **AI3.3** | Unconnected Relationship Analysis | 10-12h | High | AI3.2 |
| **AI3.4** | Synergy-Based Suggestion Generation | 10-12h | Critical | AI3.3 |
| **AI3.5** | Weather Context Integration | 8-10h | Medium | AI3.1 |
| **AI3.6** | Energy Price Context Integration | 6-8h | Medium | AI3.5 |
| **AI3.7** | Sports/Event Context Integration | 6-8h | Low | AI3.5 |
| **AI3.8** | Frontend Synergy Tab | 12-14h | High | AI3.4 |
| **AI3.9** | Testing & Documentation | 10-12h | High | AI3.8 |

**Total Stories:** 9  
**Total Effort:** 90-110 hours

---

## Critical Path

```
Backend Critical Path:
AI3.1 → AI3.2 → AI3.3 → AI3.4 (Core synergy detection)
AI3.1 → AI3.5 → AI3.6 → AI3.7 (Context integration - parallel)

Frontend:
AI3.8 (After AI3.4 complete)

Testing:
AI3.9 (After AI3.8)
```

**Timeline:** 6-8 weeks for sequential execution, 5-6 weeks with parallel context integration

---

## Sequencing Strategy

### Phase 1: Core Synergy Detection (Weeks 1-3, 38-46h)

**Goal:** Detect unconnected device pairs that should work together

- **AI3.1:** Device Synergy Detector Foundation (10-12h)
- **AI3.2:** Same-Area Device Pair Detection (8-10h)
- **AI3.3:** Unconnected Relationship Analysis (10-12h)
- **AI3.4:** Synergy-Based Suggestion Generation (10-12h)

**Deliverable:** System suggests "Motion sensor + Light → Create automation"

### Phase 2: Context Integration (Weeks 3-5, 20-26h, PARALLEL)

**Goal:** Integrate enrichment data into opportunity detection

- **AI3.5:** Weather Context Integration (8-10h)
- **AI3.6:** Energy Price Context Integration (6-8h)
- **AI3.7:** Sports/Event Context Integration (6-8h)

**Deliverable:** Context-aware suggestions like "Pre-heat when forecast shows temp drop"

### Phase 3: UI & Testing (Weeks 5-6, 22-26h)

**Goal:** User-facing interface and comprehensive testing

- **AI3.8:** Frontend Synergy Tab (12-14h)
- **AI3.9:** Testing & Documentation (10-12h)

**Deliverable:** Complete Epic AI-3 ready for production

---

## Technical Architecture

### New Components

```
services/ai-automation-service/src/
├── synergy_detection/              # NEW (Epic AI-3)
│   ├── __init__.py
│   ├── synergy_detector.py         # Core synergy detection engine
│   ├── device_pair_analyzer.py     # Same-area device pair detection
│   ├── relationship_analyzer.py    # Automation existence checker
│   └── opportunity_ranker.py       # Rank synergy opportunities
├── contextual_patterns/            # NEW (Epic AI-3)
│   ├── __init__.py
│   ├── weather_opportunities.py    # Weather-aware patterns
│   ├── energy_opportunities.py     # Energy price patterns
│   └── event_opportunities.py      # Sports/event patterns
├── scheduler/
│   └── daily_analysis.py           # MODIFY: Add Phase 3c (Synergy)
└── api/
    └── synergy_router.py           # NEW: Synergy API endpoints
```

### Database Changes

**New Table: `synergy_opportunities`**

```sql
CREATE TABLE synergy_opportunities (
    id INTEGER PRIMARY KEY,
    synergy_type VARCHAR(50) NOT NULL,  -- 'device_pair', 'weather_context', 'energy_context', 'event_context'
    device_ids TEXT NOT NULL,            -- JSON array of involved device IDs
    opportunity_metadata JSON,           -- Synergy-specific data
    impact_score FLOAT NOT NULL,         -- Expected value (0.0-1.0)
    complexity VARCHAR(20),              -- 'low', 'medium', 'high'
    confidence FLOAT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**Update: `suggestions` table** (No schema change, new `type` values)

```python
# New suggestion types:
# - 'synergy_device_pair'
# - 'synergy_weather'
# - 'synergy_energy'
# - 'synergy_event'
```

### Integration with Daily Batch

**Extends Story AI2.5 (Unified Daily Batch):**

```
PHASE 3c: Synergy Detection (NEW - Epic AI-3)
├─ Part A: Device Synergy Detection
│  ├─ Find same-area device pairs
│  ├─ Check automation existence
│  └─ Rank opportunities
├─ Part B: Contextual Opportunity Detection
│  ├─ Weather-aware patterns
│  ├─ Energy-aware patterns
│  └─ Event-aware patterns
└─ Output: synergy_opportunities table

PHASE 5: Suggestion Generation (ENHANCED)
├─ Pattern-based (Epic AI-1)
├─ Feature-based (Epic AI-2)
└─ Synergy-based (Epic AI-3) ← NEW
```

---

## Success Criteria

### Functional Success

- ✅ Detects unconnected device pairs in same area
- ✅ Identifies weather-aware automation opportunities
- ✅ Suggests energy-optimized automations
- ✅ Generates 3-5 synergy suggestions per week
- ✅ Synergy suggestions have >70% user approval rate

### Performance Success

- ✅ Synergy detection adds <2 minutes to daily batch
- ✅ Memory usage increase <200MB
- ✅ API response times <500ms
- ✅ Frontend loads synergy data <1 second

### Quality Success

- ✅ >80% code coverage for synergy components
- ✅ Zero critical bugs in synergy detection
- ✅ Context integration doesn't break existing patterns
- ✅ Graceful degradation if context data unavailable

---

## Risk Mitigation

| Risk | Mitigation | Story |
|------|-----------|-------|
| Too many low-value suggestions | Implement impact scoring, high threshold | AI3.3 |
| Weather API failures | Cache last known conditions, graceful skip | AI3.5 |
| Energy data unavailable | Optional feature, doesn't block other synergies | AI3.6 |
| Performance degradation | Run synergy detection in parallel with patterns | AI3.1 |
| User overwhelmed by suggestions | Limit to top 5 synergies, combine with existing limit | AI3.4 |
| Complex cross-device setups | Start with 2-device pairs, expand later | AI3.2 |

---

## Definition of Done (Epic Level)

### All Stories Complete

- [ ] All 9 stories marked as "Done"
- [ ] All acceptance criteria met
- [ ] All integration verifications passed

### System Functional

- [ ] Synergy detection runs daily at 3 AM
- [ ] Context-aware suggestions generated
- [ ] Frontend displays synergy opportunities
- [ ] User can approve/deploy synergy automations

### Quality Gates

- [ ] Unit tests: >80% coverage
- [ ] Integration tests: All passing
- [ ] E2E tests: Synergy flow passing
- [ ] Performance: All NFRs met

### Documentation

- [ ] Epic documentation complete
- [ ] API docs updated
- [ ] User guide includes synergy examples
- [ ] Architecture docs reflect new components

---

## Post-Epic: Future Enhancements

**Epic AI-4 (Potential):**
- ML-based opportunity prediction
- Multi-device synergies (3+ devices)
- Temporal context (season, time-of-year patterns)
- Community pattern library (anonymized successful automations)

---

## Story Files

All story files located in: `docs/stories/`

- `story-ai3-1-synergy-detector-foundation.md`
- `story-ai3-2-same-area-device-pairs.md`
- `story-ai3-3-unconnected-relationships.md`
- `story-ai3-4-synergy-suggestion-generation.md`
- `story-ai3-5-weather-context-integration.md`
- `story-ai3-6-energy-context-integration.md`
- `story-ai3-7-event-context-integration.md`
- `story-ai3-8-frontend-synergy-tab.md`
- `story-ai3-9-testing-documentation.md`

---

**Epic Status:** Ready for Approval  
**Created:** 2025-10-18  
**Updated:** 2025-10-18  
**Author:** BMad Master (based on system architect analysis)

