# 1. Project Analysis and Context

### 1.1 Analysis Source

**Analysis Type:** IDE-based fresh analysis with existing project documentation

**Available Documentation:**
- ✅ Existing tech stack documentation
- ✅ Source tree structure documentation
- ✅ Current project codebase and services
- ✅ Architecture documentation
- ✅ Context7 KB research completed

---

### 1.2 Current Project State

**Existing Home Assistant Ingestor Project:**

The **Home Assistant Ingestor** is a comprehensive microservices-based system that captures, processes, and stores Home Assistant event data.

**Core Architecture (15 microservices):**
- **WebSocket Ingestion Service** - Real-time HA event capture
- **Data API Service** (Port 8006) - Feature data hub (events, devices, sports, analytics)
- **Admin API Service** (Port 8003) - System monitoring and control
- **Health Dashboard** - React-based monitoring interface (12 tabs)
- **Enrichment Pipeline** - Data processing and normalization
- **Sports Data Service** - ESPN API integration
- **Data Retention Service** - Lifecycle management
- **AI Automation Service** (Port 8018) - AI-powered automation suggestions
- **Energy Correlator** (Port 8017) - Energy correlation analysis
- **Additional services** - Weather, carbon intensity, electricity pricing, air quality, calendar, smart meter

**Data Architecture:**
- **InfluxDB** - Time-series data storage (events, metrics)
- **SQLite** - Metadata storage (devices, entities, webhooks)
- **Hybrid approach** optimized for different data types

**Current Capabilities:**
- Real-time event streaming from Home Assistant
- Device and entity discovery and tracking
- Sports data integration with automation webhooks
- Multi-tab health dashboard for system monitoring
- Data enrichment and quality management

**Technology Stack:**
- **Backend:** Python 3.11, FastAPI, aiohttp
- **Frontend:** React 18, TypeScript 5, TailwindCSS
- **Infrastructure:** Docker Compose, Alpine-based containers

---

### 1.3 Enhancement Scope Definition

#### Enhancement Type:
- ✅ **New Feature Addition** (Major)
- ✅ **Integration with New Systems** (AI/ML models, HA automation API)
- ⚠️ **Technology Stack Expansion** (AI/ML frameworks)

#### Enhancement Description:

**Intelligent Automation Suggestion System** - A new AI-powered subsystem that analyzes Home Assistant event data, device patterns, and existing automations to suggest new automation opportunities.

**Key Features:**
1. **Backend AI Service** with pattern recognition and recommendation engine
2. **Automation Analysis Frontend** for viewing current automations and exploring suggestions
3. **Multi-model approach** analyzing temporal patterns, device relationships, and user behavior
4. **Categorized automation suggestions** organized by type, priority, and complexity
5. **Integration** with existing Data API for historical data access

#### Impact Assessment:
- ✅ **Significant Impact** (substantial existing code changes required)
  - New microservice addition to existing architecture
  - New frontend application alongside existing health dashboard
  - Integration with Data API service
  - New data models for automation tracking and suggestions
  - Requires AI/ML infrastructure not currently in the stack

---

### 1.4 Goals and Background Context

#### Goals:
- Enable users to discover automation opportunities they may not have considered
- Leverage historical event data to identify actionable patterns in home behavior
- Reduce friction in creating new Home Assistant automations
- Provide categorized, prioritized automation suggestions based on actual usage patterns
- Create a learning system that improves suggestions over time
- Bridge the gap between data collection and actionable insights

#### Background Context:

The Home Assistant Ingestor currently excels at **collecting and storing** event data from Home Assistant, but lacks capabilities for **analyzing and acting** on that data to improve the user's home automation setup. Users accumulate months of historical data showing device usage patterns, but have no automated way to discover optimization opportunities.

This enhancement addresses a critical gap: **turning passive data collection into active automation intelligence**. By analyzing device interactions, temporal patterns, and existing automations, the system can suggest new automations that align with observed behavior patterns. This transforms the ingestor from a monitoring tool into an **intelligent automation advisor**.

The new subsystem will integrate with the existing Data API rather than duplicating functionality, maintaining the microservices architecture while adding AI-powered intelligence.

---

### 1.5 Change Log

| Change | Date | Version | Description | Author |
|--------|------|---------|-------------|--------|
| Initial PRD Creation | 2025-10-15 | 0.1 | Brownfield PRD for AI Automation Suggestion System | PM Agent |
| Architecture Review | 2025-10-15 | 0.2 | Winston (Architect) validation - simplified to Phase 1 MVP | Architect |
| Context7 KB Research | 2025-10-15 | 0.3 | AI/ML best practices, Hugging Face analysis, deployment constraints | PM Agent |
| UI Pattern Analysis | 2025-10-15 | 0.4 | Analyzed existing Health Dashboard for consistent patterns | PM Agent |

---

### 1.6 AI/ML Technology Stack Research

**Context7 KB Research Completed** - Stored in: `docs/kb/context7-cache/`

Based on Context7 KB best practices research, here's the recommended technology stack for Phase 1 MVP:

#### **Phase 1 MVP Stack (Architect-Validated):**

| Component | Technology | Version | Purpose | Rationale from KB |
|-----------|-----------|---------|---------|-------------------|
| **Core ML Framework** | scikit-learn | 1.3+ | Pattern clustering, anomaly detection | Lightweight, perfect for edge deployment |
| **Statistical Analysis** | statsmodels | 0.14+ | Basic seasonal decomposition | Lighter alternative to Prophet |
| **LLM Provider** | OpenAI GPT-4o-mini | Latest | Automation suggestion generation | Cost-effective, good quality |
| **LLM Orchestration** | LangChain | 0.1+ | Prompt management (optional) | May defer to Phase 2 |
| **Data Validation** | Pydantic | 2.0+ | Automation schema validation | Type-safe automation structures |
| **MQTT Client** | paho-mqtt | 1.6+ | Event bus communication | Lightweight, proven |
| **Caching** | SQLite | 3.45+ | Pattern cache, suggestion storage | Simple, sufficient for single-home |
| **Scheduling** | APScheduler | 3.10+ | Daily batch jobs | Cron-style scheduling |

#### **Key Pattern Detection Strategies (from KB):**

1. **Time-of-Day Clustering** (KMeans)
   - Daily routine detection (morning, evening, bedtime patterns)
   - Cluster device usage by hour of day

2. **Device Co-Occurrence** (Association Rules)
   - Devices used together within time windows
   - Sequential patterns (Device A then Device B)

3. **Anomaly Detection** (Isolation Forest)
   - Manual interventions indicating automation opportunities
   - **Key Insight:** Anomalies often reveal unmet automation needs

#### **What We're NOT Using (Phase 1):**

- ❌ **Prophet** - Too memory intensive (100-200MB per device) for MVP
- ❌ **Deep Learning** - Overkill for Phase 1 patterns
- ❌ **Local LLM** - API simpler and better quality for MVP
- ❌ **Multi-scale hierarchies** - Too complex, deferred to Phase 2+

**Rationale:** Focus on delivering value quickly with proven, lightweight tools. Add complexity in future phases based on user feedback and data availability.

---

### 1.7 Deployment Constraints & Hardware Requirements

**Context7 KB Research:** `docs/kb/context7-cache/edge-ml-deployment-home-assistant.md`

#### **Deployment Context:**

This system must run in a **resource-constrained environment**:
- **Option A:** Inside Home Assistant OS (Raspberry Pi 4/5, 2-8GB RAM)
- **Option B:** Separate local server (Intel NUC, small form factor PC)

#### **Recommended Deployment: Single NUC (Intel i3/i5, 8-16GB RAM)**

**Hardware Requirements:**

| Tier | Hardware | RAM | Cost | Use Case |
|------|----------|-----|------|----------|
| **Minimum** | Raspberry Pi 5 (8GB) | 8GB | $80 | Batch processing only, works! |
| **Recommended** | Intel NUC i3 (8-16GB) ⭐ | 8-16GB | $400-500 | Smooth, no worries |
| **Comfortable** | Intel NUC i5 (16GB) | 16GB | $600-700 | Future-proof |

**Phase 1 Resource Profile:**

```
Memory Usage: 500MB-1GB (vs 2-4GB if using Prophet)
Processing Time: 5-10 minutes daily (vs 15-60 min multi-scale)
Hardware: $400-500 (vs $1,000+ dual NUC)
API Cost: $5-10/month
Development Time: 2-4 weeks (vs 3-6 months multi-scale)
```

#### **Architecture Pattern:**

```
Single NUC (i3/i5, 8-16GB RAM)
├── Home Assistant (Port 8123)
├── Data API (Port 8006) - existing
├── MQTT Broker (Mosquitto) - NEW
├── AI Automation Service (Port 8011) - NEW
│   ├── Pattern Analyzer (batch, daily 3 AM)
│   ├── LLM Suggester (OpenAI API)
│   ├── Suggestion DB (SQLite)
│   └── REST API (FastAPI)
└── AI Automation Frontend (Port 3002) - NEW
```

#### **Processing Schedule:**

```
Daily (3 AM): Pattern analysis (5-10 minutes)
  1. Query Data API (30 days of data)
  2. Feature engineering (pandas)
  3. Pattern detection (scikit-learn)
  4. LLM generation (5-10 suggestions)
  5. Store in SQLite

User reviews suggestions at leisure (non-real-time)
```

---

### 1.8 Architect Review Summary

**Reviewer:** Winston (Architect)  
**Date:** 2025-10-15  
**Verdict:** ✅ Approved with simplifications for MVP

**Key Recommendations Accepted:**

1. ✅ **Phase 1 MVP approach** - Prove value in 2-4 weeks vs 3-6 months
2. ✅ **scikit-learn only** - No Prophet in Phase 1 (too heavy)
3. ✅ **3 pattern types** - Time-of-day, co-occurrence, anomaly (no multi-scale)
4. ✅ **OpenAI API** - Better quality than local LLM for MVP
5. ✅ **Push to HA** - Leverage HA's execution engine (brilliant decision)
6. ✅ **MQTT architecture** - Sound choice for IoT systems
7. ✅ **Single NUC** - Sufficient for Phase 1

**Red Flags Avoided:**

- 🚨 Prophet memory footprint (100-200MB/device) - SKIPPED
- 🚨 Multi-scale hierarchies (3-6 months dev time) - DEFERRED
- 🚨 Seasonal patterns (need 6-12 months data) - PHASE 3+

**Architecture Validated:** ✅ Technical soundness confirmed, complexity appropriate for timeline

---

### 1.9 MQTT-Centric Architecture

**Communication Layer:** MQTT (Mosquitto) as event bus

#### **Topic Structure:**

```bash
# AI Service publishes events
ha-ai/events/pattern/detected
ha-ai/events/suggestion/generated
ha-ai/commands/automation/deploy

# HA publishes responses
ha-ai/responses/automation/executed
ha-ai/responses/automation/failed
homeassistant/status
```

#### **Message Flow Example (Sports Score):**

```
1. AI Service detects event (team scored)
2. AI publishes: ha-ai/events/sports/patriots/scored
3. HA automation (MQTT trigger) listens to topic
4. HA executes action (flash lights)
5. HA publishes result: ha-ai/responses/automation/executed
6. AI logs execution success
```

#### **Benefits:**

- ✅ **Loose coupling** - AI and HA don't need to know internals
- ✅ **Async by design** - Non-blocking communication
- ✅ **Native HA integration** - HA has built-in MQTT support
- ✅ **Minimal overhead** - 10-20MB RAM
- ✅ **Future-proof** - Easy to add more services

---

