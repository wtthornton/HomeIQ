# Epic AI-4: Community Knowledge Augmentation
## Automation Miner Integration - Helper Layer

**Epic ID:** AI-4  
**Type:** Brownfield Enhancement  
**Status:** Draft  
**Created:** October 18, 2025  
**Target:** Phase 2 Enhancement

---

## Epic Goal

Augment the existing AI suggestion engine (Epic AI-1 + AI-2) with community-sourced automation knowledge to enhance pattern recognition, educate users on device potential, and provide data-driven device purchase recommendations - while keeping personal patterns as the primary intelligence source.

**Value:** Instant device onboarding + enhanced suggestions + smart shopping guidance

---

## Epic Description

### Existing System Context

**Current Functionality (Phase 1 - Epic AI-1 + AI-2):**
- Pattern detection from user's event history (30-day analysis)
- Feature analysis for underutilized device capabilities
- AI-powered suggestion generation via OpenAI GPT-4o-mini
- Daily batch job (3 AM) generating 10 personalized suggestions

**Technology Stack:**
- Backend: Python 3.11 + FastAPI + SQLAlchemy 2.0 + AsyncIO
- Database: SQLite (ai_automation.db) + InfluxDB (events)
- LLM: OpenAI GPT-4o-mini (or local Ollama)
- Scheduler: APScheduler (AsyncIOScheduler)

**Integration Points:**
- Phase 3b: Pattern enhancement (augment detected patterns)
- Phase 4b: Feature inspiration (show community examples)
- Phase 5c: Novel idea injection (suggest new automations)
- New API: Device recommendations and discovery

---

### Enhancement Details

**What's Being Added:**

A lightweight **Automation Miner** service that:

1. **Crawls** Home Assistant community sources (Discourse + GitHub)
2. **Normalizes** automation ideas into structured metadata (not raw YAML)
3. **Stores** insights in SQLite corpus (~2,000-3,000 quality automations)
4. **Queries** by device type, integration, use case
5. **Enhances** existing AI suggestions with community best practices
6. **Recommends** devices to purchase based on automation potential
7. **Refreshes** weekly to capture new community ideas

**How It Integrates:**

```
Existing AI Engine (PRIMARY)           Automation Miner (HELPER)
┌────────────────────┐                 ┌────────────────────┐
│ YOUR patterns      │ ←──enhances──── │ Community wisdom   │
│ YOUR devices       │ ←──inspires──── │ Device examples    │
│ YOUR preferences   │ ←──educates──── │ Best practices     │
└────────────────────┘                 └────────────────────┘

        Combined Intelligence
              ↓
    Enhanced Suggestions
```

**Key Principle:** Community knowledge **augments** personal patterns, doesn't replace them.

---

## Stories

### Story AI4.1: Community Corpus Foundation
**Goal:** Build lightweight crawler + storage for high-quality community automations

**Scope:**
- Selective crawler (500+ votes only, ~2,000 automations)
- SQLite schema optimized for insights (not full YAML)
- Basic query API (by device, integration, use case)
- Initial crawl + corpus population

**Estimated Effort:** 3-4 days  
**Value:** Foundation for all augmentation features

---

### Story AI4.2: Pattern Enhancement Integration
**Goal:** Augment YOUR detected patterns with community best practices

**Scope:**
- Query Miner for similar community patterns during Phase 3
- Extract common enhancements (conditions, timing, actions)
- Inject into OpenAI prompts as optional enhancements
- Track which enhancements users enable

**Estimated Effort:** 2-3 days  
**Value:** 10-15% better suggestion quality

---

### Story AI4.3: Device Discovery & Purchase Advisor
**Goal:** Help users maximize devices + guide smart purchases

**Scope:**
- "What can I do with X device?" API endpoint
- Device recommendation engine (gap analysis)
- ROI calculation for device purchases
- Dashboard "Discovery" tab

**Estimated Effort:** 3-4 days  
**Value:** Instant value for new devices + data-driven shopping

---

### Story AI4.4: Weekly Community Refresh
**Goal:** Keep corpus fresh with new community automations

**Scope:**
- Weekly crawl job (APScheduler)
- Incremental update (new posts since last crawl)
- Quality score updates (vote counts, recency)
- Automatic corpus pruning (remove low-quality)

**Estimated Effort:** 2 days  
**Value:** Corpus stays relevant, captures trending automations

---

## Compatibility Requirements

**Must Maintain:**
- ✅ Existing Phase 1-6 flow unchanged (Miner is additive only)
- ✅ Existing API endpoints remain identical
- ✅ Database schema backward compatible (new tables only)
- ✅ Performance impact <5% (async crawling, cached queries)
- ✅ Can be disabled via feature flag without breaking Phase 1

**Integration Pattern:**
- Miner runs as separate service (port 8019) or integrated module
- Queries are async and non-blocking
- Failures gracefully degrade (Phase 1 continues without Miner)
- Uses existing logging, metrics, health check patterns

---

## Risk Mitigation

**Primary Risks:**

1. **Crawler Overload**
   - **Risk:** Excessive crawling banned by Discourse/GitHub
   - **Mitigation:** Selective crawling (500+ votes), rate limiting, respect robots.txt
   - **Rollback:** Disable crawler, use static corpus

2. **Storage Bloat**
   - **Risk:** 1GB+ database size
   - **Mitigation:** Store insights only (not full YAML), quality threshold
   - **Rollback:** Prune low-quality entries, archive old

3. **Performance Impact**
   - **Risk:** Miner queries slow down Phase 1
   - **Mitigation:** Async queries, 100ms timeout, cache results
   - **Rollback:** Disable Miner integration, Phase 1 runs standalone

4. **Suggestion Quality Dilution**
   - **Risk:** Community ideas override personal patterns
   - **Mitigation:** Personal patterns weighted 1.2×, community 0.8×
   - **Rollback:** Reduce community idea count (2 → 0)

**Overall Risk Level:** Low (additive feature with fallback)

---

## Definition of Done

Epic is complete when:

- ✅ All 4 stories completed with acceptance criteria met
- ✅ Corpus contains 2,000+ quality automations
- ✅ Weekly refresh running and verified
- ✅ Phase 1 suggestions enhanced with community wisdom
- ✅ Device discovery API functional
- ✅ Existing Phase 1 functionality unchanged (regression tested)
- ✅ Performance impact <5% measured
- ✅ Documentation updated (call trees, API docs)
- ✅ Feature can be toggled via ENABLE_MINER flag

---

## Dependencies

**Existing Epics:**
- Epic AI-1: Pattern Detection (complete) - Integration point for enhancement
- Epic AI-2: Device Intelligence (complete) - Integration point for feature inspiration
- Story AI1.23: Conversational Refinement (complete) - Voice integration ready

**External Dependencies:**
- Discourse API (community.home-assistant.io) - Public, no auth required
- GitHub API (optional token for higher rate limits)
- Python libraries: httpx, beautifulsoup4, rapidfuzz, pyyaml

**No Breaking Changes:** Epic is purely additive

---

## Success Metrics

**Corpus Quality:**
- ✅ 2,000+ automations in corpus
- ✅ Average quality score >0.7
- ✅ 50+ device types covered
- ✅ Weekly refresh adding 20-50 new ideas

**User Impact:**
- ✅ New device time-to-value: 30 days → 2 minutes (15,000× faster)
- ✅ Suggestion approval rate: +10-15% (community validation)
- ✅ Device purchase satisfaction: 80%+ (data-driven recommendations)
- ✅ Feature utilization: +20% (community examples inspire usage)

**System Health:**
- ✅ Phase 1 performance: <5% impact
- ✅ Phase 1 availability: 100% (no dependency on Miner)
- ✅ Crawler reliability: 95%+ success rate
- ✅ Query performance: <100ms p95

---

## Technical Approach

### Architecture Pattern

**Microservice Option (Recommended):**
```
automation-miner (Port 8019)
├─ Crawler job (weekly via APScheduler)
├─ SQLite corpus (automations.db)
├─ Query API (REST)
└─ Health check endpoint

ai-automation-service (Port 8018)
├─ Queries Miner via HTTP
├─ Enhances Phase 1 suggestions
└─ Graceful fallback if Miner unavailable
```

**Integrated Module Option (Simpler):**
```
ai-automation-service (Port 8018)
├─ miner/ module
│   ├─ crawler.py
│   ├─ corpus.py
│   └─ query.py
├─ Shares SQLite connection
└─ Same health check
```

**Recommendation:** Start with integrated module (simpler), extract to microservice if needed

---

### Selective Crawling Strategy

**Focus on Quality Over Quantity:**

```python
CRAWL_FILTERS = {
    'discourse': {
        'min_likes': 500,  # Only highly-voted
        'categories': [53],  # Blueprints Exchange only
        'max_age_days': 730,  # Last 2 years
        'complexity': ['low', 'medium']  # Skip "high"
    },
    'github': {
        'min_stars': 50,  # Popular repos only
        'topics': ['home-assistant-blueprint'],
        'max_age_days': 365
    }
}
```

**Expected Corpus:**
- 2,000-3,000 quality automations (vs 10,000 low-quality)
- 300-500MB storage (vs 1GB+)
- 2-3 hour initial crawl (vs 8-12 hours)
- Weekly refresh: 15-30 minutes (incremental)

---

### Weekly Refresh Design

**Scheduled Job (Every Sunday 2 AM):**

```python
@scheduler.scheduled_job('cron', day_of_week='sun', hour=2)
async def weekly_corpus_refresh():
    """
    Incremental refresh of community corpus
    """
    
    # Step 1: Fetch new/updated content since last crawl
    last_crawl = await get_last_crawl_timestamp()
    
    # Discourse: New posts since last week
    new_posts = await discourse_crawler.get_recent(
        since=last_crawl,
        min_likes=100  # Lower threshold for recent posts
    )
    
    # GitHub: Updated repos
    updated_repos = await github_crawler.get_updated(
        since=last_crawl
    )
    
    # Step 2: Normalize and add to corpus
    new_items = await normalize_and_store(new_posts + updated_repos)
    
    # Step 3: Update quality scores for existing items
    await update_quality_scores()  # Vote counts may have increased
    
    # Step 4: Prune low-quality entries
    pruned = await prune_corpus(min_quality=0.4, max_age_days=730)
    
    # Step 5: Log results
    logger.info(f"✅ Weekly refresh complete:")
    logger.info(f"   Added: {len(new_items)} new automations")
    logger.info(f"   Updated: {updated_count} quality scores")
    logger.info(f"   Pruned: {pruned} stale entries")
    logger.info(f"   Total corpus: {await count_corpus()} automations")
```

**Refresh Metrics:**
- Duration: 15-30 minutes
- New items: 20-50/week typical
- Updates: 100-200 vote count updates
- Pruned: 5-10 stale entries
- Network: ~10-20MB

---

## Non-Functional Requirements

**Performance:**
- ✅ Miner queries: <100ms p95
- ✅ Corpus size: <500MB
- ✅ Weekly refresh: <30 minutes
- ✅ Phase 1 impact: <5% overhead

**Reliability:**
- ✅ Graceful degradation (Phase 1 works without Miner)
- ✅ Crawler retry logic (3 attempts with backoff)
- ✅ Feature flag: ENABLE_MINER (default: true)
- ✅ Health check: /health includes Miner status

**Maintainability:**
- ✅ Separate concerns (crawler vs query vs integration)
- ✅ Modular design (can swap Discourse for Reddit, etc.)
- ✅ Clear logging (correlation IDs)
- ✅ Self-healing (auto-retry failed crawls)

---

## Story Handoff to Story Manager

**Story Manager Handoff:**

"Please develop detailed user stories for Epic AI-4: Community Knowledge Augmentation. Key considerations:

**Context:**
- This is an enhancement to the existing ai-automation-service (Phase 1 complete)
- Existing system: Epic AI-1 (Pattern Detection) + Epic AI-2 (Device Intelligence)
- Technology stack: Python 3.11, FastAPI, SQLAlchemy 2.0 (async), SQLite, APScheduler
- Integration must maintain Phase 1 integrity (Miner is helper, not replacement)

**Integration Points:**
- Phase 3b: Pattern enhancement (query Miner during pattern detection)
- Phase 4b: Feature inspiration (query Miner for unused feature examples)
- Phase 5c: Novel idea injection (add 2-3 community ideas to suggestions)
- New APIs: Device discovery, purchase recommendations

**Existing Patterns to Follow:**
- Async database sessions: `async with get_db_session() as db:`
- APScheduler for jobs: `AsyncIOScheduler` + `CronTrigger`
- Graceful degradation: try/except with fallback, don't fail parent job
- Structured logging: correlation IDs, operation tracking
- Health checks: /health endpoint pattern

**Critical Compatibility Requirements:**
- NO changes to existing Phase 1-6 flow (additive only)
- NO changes to existing database schema (new tables only)
- NO performance degradation of existing suggestions (async, cached)
- CAN be disabled via feature flag without breaking Phase 1
- Weekly refresh must not impact daily 3 AM analysis job

**Each story must:**
1. Include verification that existing Phase 1 functionality remains intact
2. Follow async/await patterns consistently
3. Implement proper error handling with graceful degradation
4. Include unit tests + integration tests
5. Update call tree documentation

The epic should deliver community knowledge augmentation while maintaining system integrity and keeping personal patterns as the primary intelligence source."

---

## Out of Scope

**Explicitly NOT included:**
- ❌ Replacing Phase 1 pattern detection
- ❌ Storing full YAML templates (generate fresh instead)
- ❌ Crawling low-quality content (<500 votes)
- ❌ Complex NLP/embeddings (keep simple for Phase 2)
- ❌ Multi-user corpus sharing (single-house focus)
- ❌ Real-time crawling (weekly batch is sufficient)
- ❌ Advanced ML ranking (rule-based is sufficient)

---

## Estimated Timeline

| Story | Effort | Dependencies |
|-------|--------|--------------|
| AI4.1: Corpus Foundation | 3-4 days | None |
| AI4.2: Pattern Enhancement | 2-3 days | AI4.1 complete |
| AI4.3: Device Discovery | 3-4 days | AI4.1 complete |
| AI4.4: Weekly Refresh | 2 days | AI4.1 complete |
| **Total** | **10-13 days** | **Sequential** |

**Note:** Stories AI4.2, AI4.3, AI4.4 can run in parallel after AI4.1 is done.

**Parallel execution:** 3-4 days total if AI4.2/3/4 done simultaneously after AI4.1

---

## Version History

| Date | Version | Change | Author |
|------|---------|--------|--------|
| 2025-10-18 | 1.0 | Epic created | BMad Master |

---

**Next Step:** Story Manager to create detailed stories with acceptance criteria, tasks, and dev notes.

