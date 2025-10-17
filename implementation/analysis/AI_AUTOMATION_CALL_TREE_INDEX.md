# AutomateAI Subsystem: Call Tree Documentation Index

**Service:** ai-automation-service (Port 8018)  
**Epic:** AI-1 (Pattern Detection) + AI-2 (Device Intelligence)  
**Story:** AI2.5 - Unified Daily Batch Job  
**Last Updated:** October 17, 2025

---

## 📋 Overview

This is the master index for the AutomateAI subsystem call tree documentation. The complete system flow has been broken down into logical phases, each documented in detail.

### What is AutomateAI?

AutomateAI is an intelligent system that:
1. **Discovers** what your smart home devices can do (capabilities)
2. **Detects** usage patterns from historical data (time-of-day, co-occurrence)
3. **Analyzes** device utilization (underutilized features)
4. **Generates** AI-powered automation suggestions using OpenAI GPT-4o-mini
5. **Presents** suggestions to users for approval and deployment

### Daily Execution

The system runs automatically at **3:00 AM daily** via APScheduler cron job:
- **Duration:** 2-4 minutes typical
- **Cost:** ~$0.001-0.005 per run (OpenAI)
- **Output:** ~10 automation suggestions

---

## 📚 Call Tree Documents

### 1. [Main Execution Flow](AI_AUTOMATION_MAIN_FLOW.md)
**Topics:**
- Scheduler trigger at 3 AM
- Overall execution phases (1-6)
- Error handling and recovery
- Performance characteristics
- Manual trigger path

**Read this first** to understand the big picture.

---

### 2. [Phase 1: Device Capability Discovery](AI_AUTOMATION_PHASE1_CAPABILITIES.md)
**Topics:**
- Querying Zigbee2MQTT bridge
- Universal capability parser
- Device model examples (Inovelli, Aqara, IKEA)
- Caching strategy (30-day freshness)
- Database storage (SQLite)

**Epic:** AI-2 - Device Intelligence  
**Key Output:** Device capabilities in `device_capabilities` table

---

### 3. [Phase 2: Historical Event Fetching](AI_AUTOMATION_PHASE2_EVENTS.md)
**Topics:**
- InfluxDB queries (last 30 days)
- Event data structure
- Performance optimization (3-retry backoff)
- Data volume handling (100K events)

**Key Output:** pandas DataFrame with event history

---

### 4. [Phase 3: Pattern Detection](AI_AUTOMATION_PHASE3_PATTERNS.md)
**Topics:**
- Time-of-day pattern detection
- Co-occurrence pattern detection
- Confidence scoring
- Pattern storage in database

**Epic:** AI-1 - Pattern Detection  
**Key Output:** Detected patterns in `patterns` table

---

### 5. [Phase 4: Feature Analysis](AI_AUTOMATION_PHASE4_FEATURES.md)
**Topics:**
- Device utilization calculation
- Underutilized feature identification
- Opportunity scoring
- Usage statistics from InfluxDB

**Epic:** AI-2 - Device Intelligence  
**Key Output:** Feature opportunities list

---

### 6. [Phase 5: OpenAI Suggestion Generation](AI_AUTOMATION_PHASE5_OPENAI.md)
**Topics:**
- GPT-4o-mini configuration
- Prompt templates (3 types)
- API call flow and examples
- Response parsing
- Token usage and costs
- Error handling

**Key Output:** AI-generated automation suggestions

---

### 7. [Phase 5b: Suggestion Storage](AI_AUTOMATION_PHASE5B_STORAGE.md)
**Topics:**
- Database schema (`suggestions` table)
- Status lifecycle (pending → approved → deployed)
- Pattern vs feature-based suggestions
- User feedback integration
- Deployment tracking
- Analytics and reporting

**Key Output:** Suggestions stored in SQLite

---

### 8. [Phase 6: MQTT Notification](AI_AUTOMATION_PHASE6_MQTT.md)
**Topics:**
- MQTT notification payload
- Publishing to Home Assistant
- Completion metrics
- Error handling

**Key Output:** MQTT message to `ha-ai/analysis/complete`

---

## 🔍 Quick Navigation

### By Use Case

**"How does the 3 AM job work?"**
→ Start with [Main Execution Flow](AI_AUTOMATION_MAIN_FLOW.md)

**"How does it discover device features?"**
→ Read [Phase 1: Device Capability Discovery](AI_AUTOMATION_PHASE1_CAPABILITIES.md)

**"What patterns does it detect?"**
→ Read [Phase 3: Pattern Detection](AI_AUTOMATION_PHASE3_PATTERNS.md)

**"How does OpenAI generate automations?"**
→ Read [Phase 5: OpenAI Suggestion Generation](AI_AUTOMATION_PHASE5_OPENAI.md)

**"Where are suggestions stored?"**
→ Read [Phase 5b: Suggestion Storage](AI_AUTOMATION_PHASE5B_STORAGE.md)

### By Technology

**InfluxDB:**
- [Phase 2: Historical Event Fetching](AI_AUTOMATION_PHASE2_EVENTS.md)
- [Phase 4: Feature Analysis](AI_AUTOMATION_PHASE4_FEATURES.md)

**SQLite:**
- [Phase 1: Device Capability Discovery](AI_AUTOMATION_PHASE1_CAPABILITIES.md)
- [Phase 5b: Suggestion Storage](AI_AUTOMATION_PHASE5B_STORAGE.md)

**OpenAI GPT-4o-mini:**
- [Phase 5: OpenAI Suggestion Generation](AI_AUTOMATION_PHASE5_OPENAI.md)

**MQTT:**
- [Phase 1: Device Capability Discovery](AI_AUTOMATION_PHASE1_CAPABILITIES.md) (Zigbee2MQTT)
- [Phase 6: MQTT Notification](AI_AUTOMATION_PHASE6_MQTT.md) (Home Assistant)

---

## 📊 Key Metrics Summary

### Performance
| Phase | Duration | Bottleneck |
|-------|----------|-----------|
| Phase 1: Capabilities | 10-30s | MQTT request/response |
| Phase 2: Events | 5-15s | InfluxDB query |
| Phase 3: Patterns | 15-45s | Co-occurrence algorithm |
| Phase 4: Features | 10-20s | InfluxDB usage queries |
| Phase 5: Suggestions | 30-120s | OpenAI API calls |
| Phase 6: Notification | <1s | MQTT publish |
| **Total** | **70-230s** | **OpenAI rate limiting** |

### Cost Analysis
| Item | Per Run | Daily | Monthly | Annual |
|------|---------|-------|---------|--------|
| OpenAI (10 suggestions) | $0.00137 | $0.00137 | $0.041 | $0.50 |
| InfluxDB queries | Free | Free | Free | Free |
| SQLite operations | Free | Free | Free | Free |
| **Total** | **$0.00137** | **$0.00137** | **$0.041** | **$0.50** |

### Database Growth
| Table | Records/Run | Size/Run | Monthly Growth |
|-------|-------------|----------|----------------|
| `device_capabilities` | 0-10 | ~1-10 KB | ~300 KB |
| `patterns` | 10-50 | ~2-5 KB | ~150 KB |
| `suggestions` | 10 | ~30 KB | ~900 KB |
| **Total** | **20-70** | **33-45 KB** | **~1.35 MB** |

---

## 🔗 Related Documentation

### Architecture
- [Tech Stack](../../docs/architecture/tech-stack.md)
- [Source Tree](../../docs/architecture/source-tree.md)
- [Testing Strategy](../../docs/architecture/testing-strategy.md)

### Stories
- [AI1.1: MQTT Integration](../../docs/stories/story-ai1-1-infrastructure-mqtt-integration.md)
- [AI2.1: Capability Discovery](../../docs/stories/)
- [AI2.5: Unified Daily Batch](../../docs/stories/)

### Implementation Notes
- [Code Review & Complexity Analysis](../CODE_REVIEW_COMPLEXITY_ANALYSIS.md)
- [Visual Testing Implementation](../VISUAL_TESTING_IMPLEMENTATION.md)

---

## 🛠️ Development Guide

### Running the Analysis Manually

```bash
# Trigger analysis via API (don't wait for 3 AM)
curl -X POST http://localhost:8018/api/analysis/trigger
```

### Checking Status

```bash
# Get scheduler status and next run time
curl http://localhost:8018/api/analysis/schedule

# Get analysis results
curl http://localhost:8018/api/analysis/status
```

### Testing Individual Phases

See each phase document for specific testing instructions.

---

## 📝 Document Maintenance

**When to Update:**
- Code changes to any phase
- New pattern types added
- OpenAI prompt modifications
- Database schema changes
- Performance optimizations

**Update Process:**
1. Update relevant phase document
2. Update metrics in this index
3. Update related architecture docs
4. Tag with version/date

---

## 📖 Reading Order

**For New Developers:**
1. Read this index (you are here)
2. [Main Execution Flow](AI_AUTOMATION_MAIN_FLOW.md) - Get the big picture
3. [Phase 1: Capabilities](AI_AUTOMATION_PHASE1_CAPABILITIES.md) - Understand device discovery
4. [Phase 5: OpenAI](AI_AUTOMATION_PHASE5_OPENAI.md) - See how AI works
5. [Phase 5b: Storage](AI_AUTOMATION_PHASE5B_STORAGE.md) - Understand data persistence

**For Code Review:**
- Focus on the phase(s) being modified
- Check cross-phase impacts
- Verify database schema changes

**For Debugging:**
- Start with [Main Execution Flow](AI_AUTOMATION_MAIN_FLOW.md) error handling
- Dive into specific phase causing issues
- Check logs against documented flow

---

## 🎯 Success Criteria

A successful daily run produces:
- ✅ Device capabilities updated (0-10 devices)
- ✅ 50,000-100,000 events analyzed
- ✅ 10-50 patterns detected
- ✅ 10 automation suggestions generated
- ✅ All suggestions stored in database
- ✅ MQTT notification published
- ✅ Total cost < $0.01
- ✅ Total duration < 4 minutes

---

**Total Documentation:** 8 documents covering complete system flow from 3 AM wake-up to completion.

**Combined Length:** ~2500+ lines of detailed call trees, examples, and explanations.

**Coverage:** 100% of AutomateAI subsystem execution path with deep dives into each phase.

