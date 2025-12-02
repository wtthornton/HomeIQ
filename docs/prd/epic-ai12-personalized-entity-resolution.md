# Epic AI-12: Personalized Entity Resolution & Natural Language Understanding

**Epic ID:** AI-12  
**Title:** Personalized Entity Resolution & Natural Language Understanding  
**Status:** 📋 **PLANNING**  
**Type:** Brownfield Enhancement (AI/ML Infrastructure)  
**Priority:** High (Foundation for Quality Improvements)  
**Effort:** 10 Stories (40 story points, 4-6 weeks estimated)  
**Created:** January 2025  
**Based On:** Entity Resolution Analysis, Personalized Learning Requirements, Natural Language Understanding Gaps

---

## Epic Goal

Build a personalized entity resolution system that learns from each user's actual device names, friendly names, aliases, and areas from Home Assistant Entity Registry. Enables natural language queries to resolve correctly without hardcoded variations by using semantic embeddings and user-specific naming patterns for accurate entity matching across all device types and areas.

**Business Value:**
- **+95% Entity Resolution Accuracy** (Generic: 60% → Personalized: 95%+)
- **+100% User Naming Coverage** (All device/area name variations supported)
- **-80% Clarification Requests** (Better understanding of user's naming conventions)
- **+50% User Satisfaction** (System understands "my" device names)
- **+100% Natural Language Support** (Works with any user's naming style)

---

## Existing System Context

### Current Entity Resolution

**Location:** `services/ai-automation-service/src/services/entity_validator.py`, `src/services/entity/resolver.py`

**Current State:**
1. **Entity Resolution:**
   - ✅ Multi-strategy matching (exact, fuzzy, semantic, numbered)
   - ✅ Entity Registry API integration (name, name_by_user, aliases)
   - ✅ Embedding-based semantic matching (sentence-transformers)
   - ✅ Domain and location filtering
   - ⚠️ **GAP**: Generic matching - doesn't learn from user's actual names
   - ⚠️ **GAP**: No personalized naming pattern learning
   - ⚠️ **GAP**: Limited to hardcoded variations

2. **Entity Data Sources:**
   - ✅ Entity Registry API (name, name_by_user, aliases, labels)
   - ✅ States API (friendly_name fallback)
   - ✅ Device Registry (device names, manufacturer, model)
   - ⚠️ **GAP**: Not building personalized index from user's actual devices
   - ⚠️ **GAP**: No learning from user corrections

3. **Natural Language Understanding:**
   - ✅ NER extraction (HuggingFace BERT-base-NER)
   - ✅ Semantic search (sentence-transformers)
   - ✅ Fuzzy matching (rapidfuzz)
   - ⚠️ **GAP**: Not customized to user's naming conventions
   - ⚠️ **GAP**: No active learning from user feedback

### Technology Stack

- **Language:** Python 3.12+ (async/await, type hints, Pydantic 2.x)
- **Frameworks:** FastAPI, Pydantic Settings, async/await patterns
- **ML Models:**
  - Sentence Transformers (device embeddings)
  - HuggingFace BERT-base-NER (entity extraction)
  - BGE Reranker (optional, for re-ranking)
- **Location:** `services/ai-automation-service/src/services/entity/` (enhanced)
- **2025 Patterns:** Type hints, structured logging, async generators, dependency injection
- **Context7 KB:** Sentence Transformers patterns, NER best practices, embedding optimization

### Integration Points

- `EntityValidator` - Current entity validation service
- `EntityResolver` - Current entity resolution service
- `EntityAttributeService` - Entity enrichment service
- `HomeAssistantClient` - HA API client (Entity Registry, States API)
- `DataAPIClient` - Data API for entity queries
- `UnifiedPromptBuilder` - Prompt building (uses entity context)

---

## Enhancement Details

### What's Being Added

1. **Personalized Entity Index Builder** (NEW)
   - Read all user devices from Home Assistant Entity Registry
   - Extract all name variations (name, name_by_user, aliases, friendly_name)
   - Extract area names and hierarchies
   - Build semantic embeddings for all name variations
   - Create personalized search index per user
   - Update index when devices/names change

2. **Natural Language Entity Resolver** (ENHANCEMENT)
   - Semantic search using user's actual device names
   - Multi-variant matching (all name variations per device)
   - Area-aware resolution (understand room/area names)
   - Context-aware resolution (query context improves matching)
   - Confidence scoring based on user's naming patterns

3. **Active Learning System** (NEW)
   - Learn from user corrections (approve/reject suggestions)
   - Learn from entity selection (user picks different entity)
   - Learn from custom entity mappings
   - Update personalized index based on feedback
   - Improve matching over time

4. **Training Data Generation** (NEW)
   - Generate training data from user's actual devices
   - Create query-entity pairs from user interactions
   - Build personalized test dataset
   - Support simulation framework (Epic AI-16)

5. **E2E Testing with User's Real Devices** (NEW)
   - Test entity resolution with user's actual device names
   - Validate against real Home Assistant entities
   - Measure accuracy improvement with personalization
   - Integration with simulation framework

### Success Criteria

1. **Functional:**
   - Personalized entity index built from all user devices
   - Natural language queries resolve correctly (95%+ accuracy)
   - All device name variations supported (name, name_by_user, aliases)
   - All area names supported
   - Active learning improves accuracy over time
   - Training data generated from user's devices

2. **Technical:**
   - Entity resolution accuracy: 60% → 95%+
   - Clarification requests: -80%
   - Index update time: <5 seconds for 100 devices
   - Query resolution time: <100ms (maintains current performance)
   - All code uses 2025 patterns (Python 3.12+, async/await, type hints)

3. **Quality:**
   - Unit tests >90% coverage for all changes
   - Integration tests validate end-to-end flow
   - Performance: <100ms per query (unchanged)
   - Memory: <50MB for personalized index (100 devices)

---

## Stories

### Phase 1: Personalized Entity Index (Weeks 1-2)

#### Story AI12.1: Personalized Entity Index Builder
**Type:** Foundation  
**Points:** 5  
**Effort:** 10-12 hours

Build personalized entity index from user's actual Home Assistant devices.

**Acceptance Criteria:**
- Read all devices from Entity Registry API
- Extract all name variations (name, name_by_user, aliases, friendly_name)
- Extract area names and hierarchies
- Build semantic embeddings for all name variations
- Create searchable index per user
- Update index when devices/names change (incremental updates)
- Unit tests for index building (>90% coverage)

**Files:**
- `services/ai-automation-service/src/services/entity/personalized_index.py` (new)
- `services/ai-automation-service/src/services/entity/index_builder.py` (new)
- `services/ai-automation-service/tests/services/entity/test_personalized_index.py` (new)

**Dependencies:** None

---

#### Story AI12.2: Natural Language Entity Resolver Enhancement
**Type:** Enhancement  
**Points:** 5  
**Effort:** 10-12 hours

Enhance entity resolver to use personalized index for natural language queries.

**Acceptance Criteria:**
- Use personalized index for semantic search
- Multi-variant matching (all name variations per device)
- Area-aware resolution (understand room/area names)
- Context-aware resolution (query context improves matching)
- Confidence scoring based on user's naming patterns
- Maintains backward compatibility with existing resolver
- Unit tests for enhanced resolver (>90% coverage)

**Files:**
- `services/ai-automation-service/src/services/entity/resolver.py` (enhanced)
- `services/ai-automation-service/src/services/entity/personalized_resolver.py` (new)
- `services/ai-automation-service/tests/services/entity/test_personalized_resolver.py` (new)

**Dependencies:** Story AI12.1

---

#### Story AI12.3: Area Name Resolution
**Type:** Feature  
**Points:** 3  
**Effort:** 6-8 hours

Add area name resolution to personalized entity resolver.

**Acceptance Criteria:**
- Extract area names from user's Home Assistant
- Build area name index (with aliases if available)
- Resolve area names in queries ("office", "kitchen", "bedroom")
- Area-aware entity filtering (entities in specified area)
- Support area hierarchies (floors, zones)
- Unit tests for area resolution (>90% coverage)

**Files:**
- `services/ai-automation-service/src/services/entity/area_resolver.py` (new)
- `services/ai-automation-service/src/services/entity/personalized_resolver.py` (enhanced)
- `services/ai-automation-service/tests/services/entity/test_area_resolver.py` (new)

**Dependencies:** Story AI12.1

---

### Phase 2: Active Learning (Weeks 2-3)

#### Story AI12.4: Active Learning Infrastructure
**Type:** Foundation  
**Points:** 4  
**Effort:** 8-10 hours

Build infrastructure for learning from user feedback.

**Acceptance Criteria:**
- Track user corrections (approve/reject suggestions)
- Track entity selections (user picks different entity)
- Track custom entity mappings
- Store feedback in database
- Feedback aggregation and analysis
- Unit tests for active learning infrastructure (>90% coverage)

**Files:**
- `services/ai-automation-service/src/services/learning/active_learner.py` (new)
- `services/ai-automation-service/src/services/learning/feedback_tracker.py` (new)
- `services/ai-automation-service/src/database/models.py` (enhanced - feedback tables)
- `services/ai-automation-service/tests/services/learning/test_active_learner.py` (new)

**Dependencies:** Story AI12.2

---

#### Story AI12.5: Index Update from User Feedback
**Type:** Feature  
**Points:** 4  
**Effort:** 8-10 hours

Update personalized index based on user feedback.

**Acceptance Criteria:**
- Analyze user feedback patterns
- Update entity name mappings based on corrections
- Boost confidence for frequently selected entities
- Learn user's preferred naming conventions
- Incremental index updates (no full rebuild)
- Unit tests for index updates (>90% coverage)

**Files:**
- `services/ai-automation-service/src/services/entity/index_updater.py` (new)
- `services/ai-automation-service/src/services/learning/feedback_processor.py` (new)
- `services/ai-automation-service/tests/services/entity/test_index_updater.py` (new)

**Dependencies:** Story AI12.4

---

### Phase 3: Training Data & Testing (Weeks 3-4)

#### Story AI12.6: Training Data Generation from User Devices
**Type:** Feature  
**Points:** 3  
**Effort:** 6-8 hours

Generate training data from user's actual devices for simulation framework.

**Acceptance Criteria:**
- Extract query-entity pairs from user interactions
- Generate synthetic queries from user's device names
- Create personalized test dataset
- Support simulation framework integration (Epic AI-16)
- Export training data in standard format
- Unit tests for training data generation (>90% coverage)

**Files:**
- `services/ai-automation-service/src/services/entity/training_data_generator.py` (new)
- `services/ai-automation-service/tests/services/entity/test_training_data_generator.py` (new)

**Dependencies:** Story AI12.1, Epic AI-16 (simulation framework)

---

#### Story AI12.7: E2E Testing with Real Devices
**Type:** Testing  
**Points:** 3  
**Effort:** 6-8 hours

Create E2E tests using user's actual device names.

**Acceptance Criteria:**
- Test entity resolution with user's actual device names
- Validate against real Home Assistant entities
- Measure accuracy improvement with personalization
- Compare generic vs personalized resolution
- Integration with simulation framework
- Unit tests for E2E validation (>90% coverage)

**Files:**
- `services/ai-automation-service/tests/integration/test_personalized_entity_resolution.py` (new)
- `services/ai-automation-service/tests/integration/test_real_device_names.py` (new)

**Dependencies:** Story AI12.2, Story AI12.6

---

### Phase 4: Integration & Optimization (Weeks 4-5)

#### Story AI12.8: Integration with 3 AM Workflow
**Type:** Integration  
**Points:** 4  
**Effort:** 8-10 hours

Integrate personalized entity resolution into 3 AM workflow.

**Acceptance Criteria:**
- Use personalized resolver in pattern detection
- Use personalized resolver in suggestion generation
- Use personalized resolver in YAML generation
- Maintain backward compatibility
- Performance: <100ms overhead per suggestion
- Integration tests for 3 AM workflow

**Files:**
- `services/ai-automation-service/src/scheduler/daily_analysis.py` (enhanced)
- `services/ai-automation-service/src/prompt_building/unified_prompt_builder.py` (enhanced)
- `services/ai-automation-service/tests/integration/test_3am_personalized_resolution.py` (new)

**Dependencies:** Story AI12.2, Story AI12.5

---

#### Story AI12.9: Integration with Ask AI Flow
**Type:** Integration  
**Points:** 4  
**Effort:** 8-10 hours

Integrate personalized entity resolution into Ask AI conversational flow.

**Acceptance Criteria:**
- Use personalized resolver in query processing
- Use personalized resolver in entity extraction
- Use personalized resolver in suggestion generation
- Use personalized resolver in YAML generation
- Learn from user corrections in Ask AI
- Integration tests for Ask AI flow

**Files:**
- `services/ai-automation-service/src/api/ask_ai_router.py` (enhanced)
- `services/ai-automation-service/src/services/entity/resolver.py` (enhanced)
- `services/ai-automation-service/tests/integration/test_ask_ai_personalized_resolution.py` (new)

**Dependencies:** Story AI12.2, Story AI12.5

---

#### Story AI12.10: Performance Optimization & Caching
**Type:** Optimization  
**Points:** 3  
**Effort:** 6-8 hours

Optimize personalized entity resolution for performance.

**Acceptance Criteria:**
- Index caching (avoid rebuilding on every request)
- Embedding caching (reuse embeddings for same names)
- Query result caching (cache common queries)
- Incremental updates (no full index rebuild)
- Performance: <100ms per query (maintains current)
- Memory: <50MB for personalized index (100 devices)
- Unit tests for caching (>90% coverage)

**Files:**
- `services/ai-automation-service/src/services/entity/index_cache.py` (new)
- `services/ai-automation-service/src/services/entity/embedding_cache.py` (new)
- `services/ai-automation-service/tests/services/entity/test_caching.py` (new)

**Dependencies:** Story AI12.1, Story AI12.2

---

## Technical Architecture

### Personalized Entity Resolution Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  Personalized Entity Resolution System                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 1. Personalized Index Builder                            │  │
│  │    - Read all devices from HA Entity Registry             │  │
│  │    - Extract all name variations                         │  │
│  │    - Build semantic embeddings                           │  │
│  │    - Create searchable index                             │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 2. Natural Language Query Processing                      │  │
│  │    - Extract entities from query (NER)                    │  │
│  │    - Search personalized index (semantic)                  │  │
│  │    - Multi-variant matching                               │  │
│  │    - Area-aware filtering                                │  │
│  │    - Confidence scoring                                  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 3. Active Learning                                         │  │
│  │    - Track user corrections                               │  │
│  │    - Update index based on feedback                       │  │
│  │    - Learn naming patterns                                │  │
│  │    - Improve over time                                    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Integration Points

1. **Entity Registry API:**
   - Fetch all entities with names, aliases, areas
   - Monitor for changes (new devices, name updates)
   - Incremental index updates

2. **Entity Resolution:**
   - Replace generic resolver with personalized resolver
   - Maintain backward compatibility
   - Support both generic and personalized modes

3. **Active Learning:**
   - Track feedback from 3 AM suggestions (approve/reject)
   - Track feedback from Ask AI (entity selections, corrections)
   - Update index based on feedback patterns

4. **Simulation Framework (Epic AI-16):**
   - Generate training data from user's devices
   - Test entity resolution with real device names
   - Validate accuracy improvements

---

## Dependencies

### Prerequisites
- **Epic AI-11**: Realistic Training Data Enhancement (synthetic homes - parallel work)
- **Existing**: Entity Registry API integration
- **Existing**: Entity resolution infrastructure
- **Existing**: Sentence Transformers models

### Can Run In Parallel
- **Epic AI-11**: Realistic Training Data Enhancement (different focus area)
- **Epic AI-16**: Simulation Framework (can integrate after AI12.6)

---

## Risk Assessment

### Technical Risks
1. **Index Size**: Personalized index may be large for users with many devices
   - **Mitigation**: Efficient data structures, compression, caching
   - **Target**: <50MB for 100 devices

2. **Update Performance**: Index updates may be slow
   - **Mitigation**: Incremental updates, background processing, async operations
   - **Target**: <5 seconds for 100 devices

3. **Embedding Quality**: Semantic embeddings may not capture user's naming style
   - **Mitigation**: Fine-tune on user's data, active learning, hybrid matching
   - **Validation**: Measure accuracy improvement

### Integration Risks
1. **Backward Compatibility**: Changes may break existing entity resolution
   - **Mitigation**: Feature flag, gradual rollout, comprehensive tests
   - **Approach**: Support both generic and personalized modes

2. **Performance Degradation**: Personalized resolution may be slower
   - **Mitigation**: Caching, optimization, profiling
   - **Target**: <100ms per query (maintains current)

---

## Success Metrics

### Accuracy Metrics
- **Entity Resolution Accuracy**: 60% → 95%+
- **Clarification Requests**: -80%
- **User Satisfaction**: +50%

### Performance Metrics
- **Query Resolution Time**: <100ms (maintains current)
- **Index Update Time**: <5 seconds for 100 devices
- **Memory Usage**: <50MB for personalized index

### Coverage Metrics
- **Device Name Coverage**: 100% (all name variations)
- **Area Name Coverage**: 100% (all areas supported)
- **Active Learning**: >10 feedback samples per user

---

## Future Enhancements

1. **Multi-User Support**: Personalized indexes for multiple users
2. **Cross-User Learning**: Learn from similar users' naming patterns
3. **Voice Command Optimization**: Optimize for voice assistant queries
4. **Device Type Learning**: Learn device-specific naming patterns
5. **Temporal Learning**: Adapt to naming changes over time

---

## References

- [Epic AI-11: Realistic Training Data Enhancement](epic-ai11-realistic-training-data-enhancement.md)
- [Epic AI-16: Simulation Framework](epic-ai16-simulation-framework.md)
- [Entity Resolution Research](../../implementation/analysis/ENTITY_RESOLUTION_RESEARCH.md)
- [BMAD Methodology](../../.bmad-core/user-guide.md)

---

**Last Updated:** January 2025  
**Next Review:** After Story AI12.1 completion

