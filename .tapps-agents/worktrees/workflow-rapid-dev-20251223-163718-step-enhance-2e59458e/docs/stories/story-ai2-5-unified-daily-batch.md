# Story AI2.5: Unified Daily Batch Job (Pattern + Feature Analysis)

**Epic:** Epic-AI-2 - Device Intelligence System  
**Story ID:** AI2.5  
**Priority:** High (Integration story - combines Epic-AI-1 and Epic-AI-2)  
**Estimated Effort:** 10-12 hours  
**Dependencies:** 
- Epic-AI-1 Stories 1.1-1.9 (Pattern detection + scheduler) ✅ Complete
- Epic-AI-2 Stories 2.1-2.4 (Device intelligence components) ✅ Complete

**Related Documents:**
- PRD v2.0: `docs/prd.md` (Story 2.5)
- Architecture: `docs/architecture-device-intelligence.md` (Section 9)
- Analysis: `implementation/REALTIME_VS_BATCH_ANALYSIS.md`

---

## User Story

**As a** system  
**I want** a single daily batch job that combines pattern detection and feature analysis  
**so that** I can provide comprehensive AI suggestions efficiently

---

## Business Value

- **Unified Analysis:** Single 3 AM job combines Epic-AI-1 (patterns) + Epic-AI-2 (features)
- **Resource Efficiency:** 99% less resource usage vs. real-time listener (5-10 min/day vs. 24/7)
- **Shared Data:** Single InfluxDB query serves both pattern detection and feature analysis
- **Combined Suggestions:** Can generate hybrid suggestions (e.g., "Automate light at 6 PM AND enable LED notifications")
- **Simpler Monitoring:** One job status vs. multiple services
- **Same User Experience:** User wakes up to suggestions regardless of real-time vs. batch

---

## Acceptance Criteria

### Unified Job Flow

1. ✅ **Single Scheduler Job:** Runs daily at 3 AM (extends Story 1.9 scheduler)
2. ✅ **Device Capability Update (AI-2):** 
   - Check HA device registry for new/updated devices
   - Query Zigbee2MQTT bridge for capabilities (one-time batch query)
   - Update `device_capabilities` table
3. ✅ **InfluxDB Query (Shared):** 
   - Fetch last 30 days of events (single query)
   - Share DataFrame between Epic-AI-1 and Epic-AI-2 components
4. ✅ **Pattern Detection (AI-1):** 
   - Run time-of-day clustering
   - Run co-occurrence detection
   - Run anomaly detection
5. ✅ **Feature Analysis (AI-2):** 
   - Match devices to capabilities
   - Analyze feature usage from InfluxDB events
   - Calculate utilization scores
   - Identify unused high-impact features
6. ✅ **Combined Suggestion Generation:** 
   - Generate pattern-based suggestions (Epic-AI-1)
   - Generate feature-based suggestions (Epic-AI-2)
   - Rank by unified scoring (confidence * impact)
   - Balance output (at least 1 of each type if available)
   - Limit to top 5-10 suggestions total
7. ✅ **Store Results:** Save all suggestions to SQLite
8. ✅ **Performance:** Complete full analysis in <10 minutes
9. ✅ **Logging:** Unified progress reporting
10. ✅ **Error Handling:** Graceful degradation if components fail

---

## Technical Implementation

### Refactored Architecture

**Before (Real-time + Batch):**
```
┌─────────────────┐
│ MQTT Listener   │  ← 24/7 service
│ (Always On)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐       ┌──────────────┐
│ device_         │       │ Pattern      │
│ capabilities    │       │ Detection    │
└─────────────────┘       │ (3 AM daily) │
                          └──────────────┘
```

**After (Unified Batch):**
```
┌───────────────────────────────────────────────┐
│ Unified Daily AI Analysis (3 AM)              │
│                                               │
│  1. Device Capability Update (AI-2)          │
│     - Check new devices                       │
│     - Query Zigbee2MQTT bridge (batch)        │
│                                               │
│  2. InfluxDB Query (Shared)                   │
│     - Fetch last 30 days (ONE query)          │
│                                               │
│  3. Pattern Detection (AI-1)                  │
│     - Time-of-day clustering                  │
│     - Co-occurrence detection                 │
│     - Anomaly detection                       │
│                                               │
│  4. Feature Analysis (AI-2)                   │
│     - Device-capability matching              │
│     - Utilization calculation                 │
│     - Unused feature identification           │
│                                               │
│  5. Combined Suggestion Generation            │
│     - Pattern suggestions                     │
│     - Feature suggestions                     │
│     - Unified ranking                         │
│                                               │
└───────────────┬───────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────┐
│ SQLite Database                               │
│  - device_capabilities (updated)              │
│  - patterns (stored)                          │
│  - suggestions (pattern + feature)            │
└───────────────────────────────────────────────┘
```

---

### Code Structure

**File:** `services/ai-automation-service/src/scheduler.py`

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from .pattern_analyzer import TimeOfDayPatternDetector, CoOccurrencePatternDetector
from .device_intelligence import CapabilityParser, FeatureAnalyzer, FeatureSuggestionGenerator
from .llm import OpenAIClient
import logging

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


@scheduler.scheduled_job('cron', hour=3, minute=0)
async def unified_daily_ai_analysis():
    """
    Unified daily AI analysis combining Epic-AI-1 and Epic-AI-2.
    
    Runs at 3 AM daily:
    1. Device capability discovery (AI-2)
    2. Pattern detection (AI-1)
    3. Feature analysis (AI-2)
    4. Combined suggestion generation
    
    Story AI2.5: Unified Daily Batch Job
    """
    logger.info("=" * 80)
    logger.info("🤖 Starting Unified Daily AI Analysis (3 AM)")
    logger.info("=" * 80)
    
    start_time = datetime.utcnow()
    stats = {
        "devices_updated": 0,
        "events_analyzed": 0,
        "patterns_detected": 0,
        "opportunities_found": 0,
        "suggestions_generated": 0
    }
    
    try:
        # =====================================================================
        # STEP 1: Device Capability Update (AI-2, Story 2.1 refactored)
        # =====================================================================
        logger.info("📡 Step 1/5: Device Capability Update (AI-2)")
        
        # Check for new/updated devices
        ha_devices = await ha_api.get_devices()
        new_devices = await db.get_devices_needing_capability_update(ha_devices)
        
        if new_devices:
            logger.info(f"   Found {len(new_devices)} devices needing capability update")
            
            # Query Zigbee2MQTT bridge (one-time batch query)
            mqtt_bridge_data = await mqtt_client.query_bridge_devices()
            
            # Parse and store capabilities
            parser = CapabilityParser()
            for device in new_devices:
                capabilities = parser.parse_device(device, mqtt_bridge_data)
                if capabilities:
                    await db.upsert_device_capability(capabilities)
                    stats["devices_updated"] += 1
            
            logger.info(f"   ✅ Updated capabilities for {stats['devices_updated']} devices")
        else:
            logger.info("   ℹ️  No new devices found")
        
        # =====================================================================
        # STEP 2: InfluxDB Query (SHARED by both epics)
        # =====================================================================
        logger.info("📊 Step 2/5: InfluxDB Query (Shared Data)")
        
        # Single query for last 30 days (used by BOTH epics)
        start_date = datetime.now() - timedelta(days=30)
        events_df = await data_api.fetch_events(start_time=start_date)
        stats["events_analyzed"] = len(events_df)
        
        logger.info(f"   ✅ Fetched {stats['events_analyzed']} events (last 30 days)")
        
        # =====================================================================
        # STEP 3: Pattern Detection (AI-1, Stories 1.4-1.6)
        # =====================================================================
        logger.info("🔍 Step 3/5: Pattern Detection (AI-1)")
        
        patterns = []
        
        # Time-of-day clustering
        time_detector = TimeOfDayPatternDetector()
        time_patterns = time_detector.detect_patterns(events_df)
        patterns.extend(time_patterns)
        logger.info(f"   - Time-of-day: {len(time_patterns)} patterns")
        
        # Co-occurrence detection
        co_detector = CoOccurrencePatternDetector()
        co_patterns = co_detector.detect_patterns(events_df)
        patterns.extend(co_patterns)
        logger.info(f"   - Co-occurrence: {len(co_patterns)} patterns")
        
        # Anomaly detection (placeholder - Story 1.6)
        # anomaly_patterns = anomaly_detector.detect_patterns(events_df)
        # patterns.extend(anomaly_patterns)
        
        stats["patterns_detected"] = len(patterns)
        logger.info(f"   ✅ Detected {stats['patterns_detected']} patterns total")
        
        # =====================================================================
        # STEP 4: Feature Analysis (AI-2, Story 2.3)
        # =====================================================================
        logger.info("🧠 Step 4/5: Feature Analysis (AI-2)")
        
        # Analyze all devices for unused features
        feature_analyzer = FeatureAnalyzer(
            data_api_client=data_api,
            db_session=db,
            influxdb_client=influxdb  # Now used! (Story 2.5 enhancement)
        )
        
        analysis = await feature_analyzer.analyze_all_devices()
        opportunities = analysis.get("opportunities", [])
        stats["opportunities_found"] = len(opportunities)
        
        logger.info(f"   ✅ Found {stats['opportunities_found']} unused feature opportunities")
        
        # =====================================================================
        # STEP 5: Combined Suggestion Generation
        # =====================================================================
        logger.info("💡 Step 5/5: Combined Suggestion Generation")
        
        llm_client = OpenAIClient(api_key=settings.openai_api_key)
        suggestions = []
        
        # Generate pattern-based suggestions (AI-1)
        for pattern in patterns:
            try:
                suggestion = await llm_client.generate_automation_suggestion(pattern)
                suggestions.append({
                    "type": "pattern_automation",
                    "source": "Epic-AI-1",
                    "pattern_type": pattern["pattern_type"],
                    **suggestion.dict()
                })
            except Exception as e:
                logger.error(f"   ❌ Pattern suggestion failed: {e}")
        
        # Generate feature-based suggestions (AI-2)
        generator = FeatureSuggestionGenerator(llm_client, feature_analyzer, db)
        feature_suggestions = await generator.generate_suggestions(max_suggestions=10)
        suggestions.extend(feature_suggestions)
        
        # Unified ranking (confidence * impact)
        suggestions.sort(key=lambda s: s.get("confidence", 0.5), reverse=True)
        suggestions = suggestions[:10]  # Top 10
        
        stats["suggestions_generated"] = len(suggestions)
        logger.info(f"   ✅ Generated {stats['suggestions_generated']} suggestions")
        logger.info(f"      - Pattern-based: {len([s for s in suggestions if s['type'] == 'pattern_automation'])}")
        logger.info(f"      - Feature-based: {len([s for s in suggestions if s['type'] == 'feature_discovery'])}")
        
        # Store all suggestions
        for suggestion in suggestions:
            await db.store_suggestion(suggestion)
        
        # =====================================================================
        # Summary
        # =====================================================================
        duration = (datetime.utcnow() - start_time).total_seconds()
        
        logger.info("=" * 80)
        logger.info("✅ Unified Daily AI Analysis Complete")
        logger.info(f"   Duration: {duration:.1f}s")
        logger.info(f"   Devices updated: {stats['devices_updated']}")
        logger.info(f"   Events analyzed: {stats['events_analyzed']}")
        logger.info(f"   Patterns detected: {stats['patterns_detected']}")
        logger.info(f"   Opportunities found: {stats['opportunities_found']}")
        logger.info(f"   Suggestions generated: {stats['suggestions_generated']}")
        logger.info(f"   LLM cost: ${llm_client.get_usage_stats()['estimated_cost_usd']:.4f}")
        logger.info("=" * 80)
        
        # Store run metadata
        await db.store_analysis_run({
            "timestamp": datetime.utcnow(),
            "duration_seconds": duration,
            **stats
        })
        
    except Exception as e:
        logger.error(f"❌ Unified daily analysis failed: {e}", exc_info=True)
        # Graceful degradation - don't crash service
```

---

## Migration from Real-time to Batch

### Changes to Story 2.1 Components

**MQTTCapabilityListener (Before):**
```python
# Real-time listener (24/7)
class MQTTCapabilityListener:
    async def start(self):
        self.mqtt_client.subscribe("zigbee2mqtt/bridge/devices")
        self.mqtt_client.on_message = self._on_message  # Callback
    
    def _on_message(self, client, userdata, msg):
        # Process immediately
        devices = json.loads(msg.payload)
        await self._process_devices(devices)
```

**Batch Query (After - Story 2.5):**
```python
# Batch query (called from scheduler)
async def update_device_capabilities_batch():
    """
    Query Zigbee2MQTT bridge for device capabilities (batch).
    Replaces real-time listener from Story 2.1.
    """
    # One-time query
    mqtt_client = MQTTNotificationClient(...)
    bridge_data = await mqtt_client.query_bridge_devices()
    
    # Parse and store
    parser = CapabilityParser()
    for device in bridge_data:
        capabilities = parser.parse_device(device)
        await db.upsert_device_capability(capabilities)
```

---

## Testing

### Unit Tests

1. **Test unified scheduler job:**
   - Mock all components (HA API, MQTT, InfluxDB, LLM)
   - Verify correct execution order
   - Verify error handling and graceful degradation

2. **Test data sharing:**
   - Verify InfluxDB query happens once
   - Verify same DataFrame used by pattern detection and feature analysis

3. **Test combined ranking:**
   - Verify pattern + feature suggestions ranked together
   - Verify balance (mix of both types)

### Integration Tests

1. **Full batch run:**
   - Test complete 3 AM job
   - Verify all 5 steps execute
   - Verify results stored in database

2. **Performance test:**
   - 100 devices, 10K events
   - Complete in <10 minutes
   - Memory usage <500MB

---

## Acceptance Validation

- [ ] Single scheduler job runs at 3 AM
- [ ] Device capabilities updated (batch query)
- [ ] InfluxDB queried once (shared)
- [ ] Pattern detection executes (AI-1)
- [ ] Feature analysis executes (AI-2)
- [ ] Combined suggestions generated
- [ ] Unified ranking applied
- [ ] Results stored in SQLite
- [ ] Complete in <10 minutes
- [ ] Unified logging shows progress
- [ ] Error handling graceful

---

## Benefits Summary

| Metric | Real-time (Before) | Batch (After) | Improvement |
|--------|-------------------|--------------|-------------|
| **Uptime** | 730 hrs/month | 2.5 hrs/month | **291x less** |
| **Resource Usage** | 24/7 | 5-10 min/day | **99% less** |
| **Complexity** | High (reconnect, monitoring) | Low (simple cron) | **Simpler** |
| **User Experience** | Suggestions at 7 AM | Suggestions at 7 AM | **Identical** |
| **InfluxDB Queries** | Separate | Shared | **Efficient** |
| **Failure Modes** | Many | Few | **Reliable** |
| **Suggestion Quality** | Separate | Combined | **Better** |

---

## Related Stories

- **Story 1.9:** Daily scheduler (extends this)
- **Story 2.1:** Device capability discovery (refactored to batch)
- **Story 2.3:** Feature analyzer (uses shared InfluxDB data)
- **Story 2.4:** Suggestion generator (called from unified job)

---

## Notes

- This story represents an architectural improvement based on user feedback
- Maintains all functionality while reducing complexity
- Enables future enhancements (hybrid suggestions combining pattern + feature)
- See `implementation/REALTIME_VS_BATCH_ANALYSIS.md` for detailed analysis

