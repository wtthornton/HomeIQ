# AI Automation & Device Intelligence System - Brownfield Enhancement PRD

**Product Requirements Document**  
**Version:** 2.0  
**Date:** 2025-01-16  
**Author:** John (Product Manager)  
**Status:** Updated - Device Intelligence Phase Added  
**Epic ID:** Epic-AI-1 (Pattern Automation) + Epic-AI-2 (Device Intelligence)  
**Previous Version:** 1.0 (Pattern Automation Only)  
**Project Brief:** docs/brief.md

---

## Table of Contents

1. [Project Analysis and Context](#1-project-analysis-and-context)
2. [Requirements](#2-requirements)
3. [User Interface Enhancement Goals](#3-user-interface-enhancement-goals)
4. [Technical Constraints and Integration](#4-technical-constraints-and-integration)
5. [Epic and Story Structure](#5-epic-and-story-structure)

---

## 1. Project Analysis and Context

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
- **AI Automation Service** (Port 8018) - AI-powered automation suggestions
- **Energy Correlator** (Port 8017) - Energy correlation analysis
- **Sports Data Service** - ESPN API integration
- **Data Retention Service** - Lifecycle management
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
- ✅ **Major Feature Addition** (Two-Phase Enhancement)
- ✅ **Integration with New Systems** (AI/ML models, HA automation API, Zigbee2MQTT MQTT bridge)
- ⚠️ **Technology Stack Expansion** (AI/ML frameworks for Phase 1, Device Intelligence for Phase 2)

#### Enhancement Description:

**AI Automation & Device Intelligence System** - An integrated AI-powered system with two complementary phases:

**Phase 1: Pattern-Based Automation (EXISTING - Epic-AI-1):**
- Backend AI Service with pattern recognition (time-of-day, co-occurrence, anomaly)
- LLM-powered automation suggestion generation
- Daily batch analysis scheduler
- Suggestion approval workflow
- **Status:** Partially implemented (Stories 1-18 defined)

**Phase 2: Device Intelligence (NEW - Epic-AI-2):**
- Universal device capability discovery via Zigbee2MQTT MQTT bridge
- Feature-based suggestion engine (unused device capabilities)
- Device utilization tracking and dashboard
- Proactive feature discovery notifications
- Multi-manufacturer support (6,000+ Zigbee device models)

**Key Features (Combined System):**
1. **Pattern-Based Suggestions** - "Create automation when bedroom light turns on 6am daily" (EXISTING)
2. **Feature-Based Suggestions** - "Enable LED notifications on Inovelli switch" (NEW)
3. **Universal Capability Discovery** - Automatic detection for ALL Zigbee manufacturers (NEW)
4. **Device Intelligence Dashboard** - Utilization tracking and opportunity identification (NEW)
5. **Unified Suggestion Pipeline** - Merges pattern + feature suggestions (ENHANCED)

#### Impact Assessment:
- ✅ **Significant Impact** (enhancement to existing AI Automation Service)
  - **Phase 1 (Pattern):** New microservice (ai-automation-service) - Partially Complete
  - **Phase 2 (Intelligence):** Enhancement to existing service - New Development
  - New database tables in ai_automation.db (2 tables for device intelligence)
  - New Health Dashboard tab (Device Intelligence)
  - Integration with Zigbee2MQTT via MQTT bridge
  - Universal capability database for 6,000+ device models

---

### 1.4 Goals and Background Context

#### Goals:

**Phase 1 Goals (Pattern-Based Automation):**
- Enable users to discover automation opportunities they may not have considered
- Leverage historical event data to identify actionable patterns in home behavior
- Reduce friction in creating new Home Assistant automations
- Provide categorized, prioritized automation suggestions based on actual usage patterns
- Create a learning system that improves suggestions over time

**Phase 2 Goals (Device Intelligence):**
- **Maximize device ROI**: Increase device utilization from ~20% to 45% within 12 months
- **Discover hidden capabilities**: Help users configure 15+ previously unknown device features
- **Reduce energy costs**: Achieve $150+ annual savings through device optimization
- **Universal support**: Work automatically for ALL Zigbee manufacturers (6,000+ models)
- **Proactive guidance**: Daily feature discovery alongside pattern automation

**Combined System Goals:**
- Bridge the gap between data collection and actionable insights
- Transform HA-Ingestor from passive infrastructure into active intelligence layer
- Provide both behavior-based (patterns) AND capability-based (features) suggestions
- Deliver measurable ROI through automation quality AND device optimization

#### Background Context:

The Home Assistant Ingestor currently excels at **collecting and storing** event data from Home Assistant, with 99.9% capture reliability and comprehensive historical storage. However, two critical intelligence gaps exist:

**Gap #1: Pattern Intelligence (Addressed by Phase 1 - Epic-AI-1)**
Users accumulate months of historical data showing device usage patterns, but have no automated way to discover automation opportunities. The system can detect "bathroom light left on >30min frequently" but doesn't suggest "configure auto-off timer."

**Gap #2: Device Intelligence (Addressed by Phase 2 - Epic-AI-2)**  
Users own sophisticated devices (Inovelli switches, Aqara sensors, IKEA bulbs, Xiaomi sensors, etc.) but use only ~20% of available capabilities. The system knows a device is an "Inovelli VZM31-SN" but doesn't know it supports LED notifications, button events, smart bulb mode, power monitoring, and auto-off timers. **This gap exists for ALL manufacturers** - users with devices from Aqara, IKEA, Xiaomi, Sonoff, and 100+ other brands are missing 70-90% of their devices' capabilities.

**The Integrated Solution:**

This two-phase enhancement transforms the ingestor from a monitoring tool into an **intelligent automation advisor** that suggests BOTH:
- **Pattern-based automations** - "Create automation based on your 6am daily routine"
- **Feature-based optimizations** - "Enable LED notifications on your Inovelli switch (unused)"

**Critical Insight from Analysis:**  
Zigbee2MQTT publishes a complete device capability database via MQTT topic `zigbee2mqtt/bridge/devices` containing ALL capabilities for ALL Zigbee manufacturers (~6,000 device models). One MQTT subscription provides universal device intelligence without manual research.

The enhancement integrates with existing Data API and maintains the microservices architecture while adding AI-powered intelligence that understands both **behavior patterns** (from data) AND **device capabilities** (from Zigbee2MQTT bridge).

---

### 1.5 Change Log

| Change | Date | Version | Description | Author |
|--------|------|---------|-------------|--------|
| Initial PRD Creation | 2025-10-15 | 0.1 | Brownfield PRD for AI Automation Suggestion System | PM Agent |
| Architecture Review | 2025-10-15 | 0.2 | Winston (Architect) validation - simplified to Phase 1 MVP | Architect |
| Context7 KB Research | 2025-10-15 | 0.3 | AI/ML best practices, Hugging Face analysis, deployment constraints | PM Agent |
| UI Pattern Analysis | 2025-10-15 | 0.4 | Analyzed existing Health Dashboard for consistent patterns | PM Agent |
| **Project Brief Created** | **2025-01-16** | **1.5** | **Comprehensive brief for Device Intelligence enhancement created by Analyst** | **Analyst (Mary)** |
| **Device Intelligence Phase** | **2025-01-16** | **2.0** | **Added Epic-AI-2: Universal device capability discovery and feature-based suggestions** | **PM Agent (John)** |
| **Requirements Updated** | **2025-01-16** | **2.0** | **Added requirements for Zigbee2MQTT MQTT bridge integration, capability database, unified suggestions** | **PM Agent (John)** |

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
├── Home Assistant (Port 8123) - includes MQTT broker
├── Data API (Port 8006) - existing
├── AI Automation Service (Port 8011) - NEW (connects to HA MQTT)
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

**Communication Layer:** MQTT (existing on Home Assistant) as event bus

**Important:** MQTT broker already running on Home Assistant server (port 1883). AI service will connect as client.

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

## 2. Requirements

### 2.1 Functional Requirements

**FR1:** The system SHALL analyze historical Home Assistant event data from the Data API to identify automation opportunities
- **Scope:** Last 30 days of device state changes and events
- **Frequency:** Daily batch analysis at 3 AM
- **Patterns:** Time-of-day, device co-occurrence, manual intervention anomalies

**FR2:** The system SHALL detect three types of automation patterns:
- **FR2.1:** Time-of-day patterns (device actions at consistent times)
- **FR2.2:** Device co-occurrence patterns (devices used together)
- **FR2.3:** Anomaly patterns (manual interventions indicating automation opportunities)

**FR3:** The system SHALL generate 5-10 automation suggestions per week using LLM-based natural language generation
- **Quality over quantity:** Focus on high-confidence patterns only (>70%)
- **LLM:** OpenAI GPT-4o-mini for cost-effectiveness
- **Format:** Natural language explanation + Home Assistant YAML automation

**FR4:** The system SHALL provide a web-based interface for users to browse, review, and manage automation suggestions
- **Actions:** View, Approve, Modify, Reject, Archive
- **Status tracking:** Pending, Approved, Deployed, Rejected
- **History:** Track suggestion evolution and user feedback

**FR5:** The system SHALL allow users to approve automation suggestions before deployment
- **Human-in-the-loop:** No automations deploy without explicit approval
- **Modification:** Users can edit suggested automations before deployment
- **Preview:** Show automation logic in human-readable format

**FR6:** The system SHALL deploy approved automations to Home Assistant via REST API
- **Format:** Convert to Home Assistant automation YAML schema
- **Validation:** Verify automation syntax before deployment
- **Rollback:** Track deployed automations for potential removal

**FR7:** The system SHALL communicate dynamic automation triggers via MQTT
- **Topics:** `ha-ai/events/*` for AI-detected events
- **HA Integration:** Home Assistant subscribed to AI topics
- **Bi-directional:** HA publishes execution feedback to `ha-ai/responses/*`

**FR8:** The system SHALL display current Home Assistant automations
- **Source:** Query HA API for existing automations
- **Purpose:** Avoid suggesting duplicate automations
- **Comparison:** Show how suggestions differ from existing

**FR9:** The system SHALL store pattern detection results and suggestions in SQLite database
- **Persistence:** Patterns, suggestions, user decisions, deployment status
- **History:** Track pattern evolution over time
- **Analytics:** Support future reporting and ML improvements

**FR10:** The system SHALL provide real-time status updates via MQTT
- **Events:** Analysis complete, new suggestions available, deployment status
- **Feedback loop:** Automation execution success/failure from HA

---

### 2.1.1 Device Intelligence Functional Requirements (NEW - Epic-AI-2)

**FR11:** The system SHALL automatically discover device capabilities for ALL Zigbee devices via Zigbee2MQTT MQTT bridge
- **Method:** Subscribe to `zigbee2mqtt/bridge/devices` MQTT topic
- **Coverage:** ~6,000 Zigbee device models from 100+ manufacturers (Inovelli, Aqara, IKEA, Xiaomi, Sonoff, Tuya, etc.)
- **Real-time:** Auto-update when new devices are paired
- **Storage:** Persist capabilities in `device_capabilities` SQLite table
- **Universal:** Works for ANY Zigbee manufacturer automatically

**FR12:** The system SHALL parse Zigbee2MQTT 'exposes' format into unified capability structure
- **Input:** Raw Zigbee2MQTT device definition JSON
- **Output:** Structured capability format with feature name, type, description, configuration options
- **Mapping:** Convert MQTT parameter names to friendly capability names (e.g., "smartBulbMode" → "smart_bulb_mode")
- **Categories:** Group by capability type (lighting, sensors, configuration, advanced features)

**FR13:** The system SHALL track device feature utilization at individual device level
- **Tracking:** For each device, track which capabilities are configured vs. available
- **Storage:** `device_feature_usage` table linking device_id to feature_name
- **Status:** Binary configured/not-configured status
- **Timestamps:** Track when feature was discovered and last checked

**FR14:** The system SHALL calculate device utilization scores
- **Per-device:** (configured_features / total_available_features) * 100
- **Per-manufacturer:** Aggregated score by brand (Inovelli, Aqara, IKEA, etc.)
- **Overall home:** Total configured / total available across all devices
- **Trending:** Track utilization changes over time
- **Target:** Help users reach 45% utilization from baseline ~20%

**FR15:** The system SHALL generate feature-based suggestions for unused device capabilities
- **Analysis:** Scan all devices for unused features (configured = false)
- **Prioritization:** Rank by impact (energy savings, convenience, security)
- **Context-aware:** Consider device location (area), patterns, and user behavior
- **LLM Generation:** Use OpenAI to create human-readable suggestions with device-specific context
- **Multi-brand:** Work automatically for all Zigbee manufacturers

**FR16:** The system SHALL merge pattern-based and feature-based suggestions into unified daily report
- **Combination:** Mix pattern automation suggestions (FR3) with feature discovery suggestions (FR15)
- **Ranking:** Unified confidence scoring across both types
- **Limit:** Top 5-10 suggestions total per day (not 5 pattern + 5 feature)
- **Balance:** Ensure mix of both types when relevant
- **Priority:** High-confidence suggestions regardless of type

**FR17:** The system SHALL provide Device Intelligence dashboard in Health Dashboard
- **Location:** New 13th tab in existing Health Dashboard (port 3000)
- **Metrics:** Overall utilization score, features discovered count, energy savings estimate
- **Breakdown:** Utilization by manufacturer (chart)
- **Opportunities:** Top 10 unused features ranked by impact
- **Device List:** All devices with utilization % and feature details
- **Visual:** Progress charts showing utilization trends

**FR18:** The system SHALL expose Device Intelligence via REST API endpoints
- **Endpoints:**
  - `GET /api/device-intelligence/utilization` - Overall and per-brand utilization scores
  - `GET /api/device-intelligence/devices/{device_id}/capabilities` - All capabilities for specific device
  - `GET /api/device-intelligence/opportunities` - Top unused feature opportunities
  - `POST /api/device-intelligence/capabilities/refresh` - Manual refresh trigger
- **Integration:** Add to existing ai-automation-service (port 8018)

**FR19:** The system SHALL support manual capability refresh for edge cases
- **Trigger:** API endpoint or dashboard button
- **Fallback:** Use Context7 for devices not in Zigbee2MQTT bridge
- **Custom:** Allow manual capability definitions for unsupported devices
- **Update:** Refresh capabilities when firmware updates change features

**FR20:** The system SHALL provide multi-manufacturer support roadmap
- **Phase 1 (MVP):** Zigbee2MQTT devices (~6,000 models) - Full support
- **Phase 2:** Z-Wave JS devices (~3,000 models) - Similar MQTT/API approach
- **Phase 3:** Native HA integrations (Hue, Shelly, etc.) - Integration-specific APIs
- **Fallback:** Context7 research for unsupported integration types

---

### 2.2 Non-Functional Requirements

**NFR1:** The system SHALL complete daily pattern analysis within 10 minutes
- **Target:** 5-10 minutes for 30 days of data
- **Acceptable:** Up to 15 minutes on high-load days
- **Failure:** Alert if exceeds 20 minutes

**NFR2:** The system SHALL operate within 1GB of RAM during pattern analysis
- **Peak:** <1GB during analysis
- **Idle:** <200MB between analyses
- **Constraint:** Must coexist with Home Assistant on single NUC

**NFR3:** The system SHALL support 100-200 devices in Phase 1
- **Minimum:** 50 devices (small home)
- **Target:** 100-150 devices (typical home)
- **Maximum:** 200 devices (large home)

**NFR4:** The API SHALL respond to UI requests within 500ms
- **Cached data:** <200ms
- **Database queries:** <500ms
- **LLM generation:** Async (background job)

**NFR5:** The system SHALL maintain 95% uptime
- **Critical:** Pattern analysis can run next day if missed
- **Non-critical:** Service restarts don't affect deployed automations (they live in HA)
- **Recovery:** Automatic restart on failure

**NFR6:** The system SHALL integrate with existing Home Assistant Ingestor architecture
- **Data API:** Use existing Data API (port 8006) for historical data
- **MQTT:** Share MQTT broker with other services
- **Docker:** Deploy as Docker Compose service
- **Minimal impact:** <5% CPU usage when idle

**NFR7:** The system SHALL limit API costs to $10/month
- **LLM:** GPT-4o-mini for cost optimization
- **Batch processing:** Generate 5-10 suggestions weekly
- **Monitoring:** Track token usage and costs

**NFR8:** The system SHALL be maintainable by developers with Python and React experience
- **Code quality:** Follow existing coding standards
- **Documentation:** Comprehensive inline documentation
- **Testing:** Unit tests for pattern detection logic
- **Debugging:** Logging for pattern analysis steps

**NFR9:** The system SHALL secure communication between services
- **MQTT:** Internal network only (no external exposure)
- **API:** Authentication via Home Assistant tokens
- **Data:** No sensitive data sent to external LLM (only anonymized patterns)

**NFR10:** The system SHALL gracefully handle insufficient data scenarios
- **Bootstrap:** Provide helpful messages when <7 days of data
- **Confidence:** Only suggest patterns with >70% confidence
- **Feedback:** Explain why suggestions may be limited initially

---

### 2.2.1 Device Intelligence Non-Functional Requirements (NEW - Epic-AI-2)

**NFR11:** The system SHALL populate device capability database within 5 minutes for 100 devices
- **Initial load:** Parse MQTT bridge message and populate database
- **Per-device:** <3 seconds to parse and store capabilities
- **Bulk operation:** Process all devices in parallel where possible
- **Progress:** Show progress indicator for initial population

**NFR12:** The system SHALL maintain device capability database with minimal storage overhead
- **Per-device model:** <10KB storage per device capability definition
- **Total estimate:** <5MB for 500 unique device models
- **Indexing:** Fast lookups by manufacturer, model, integration type (<10ms)
- **Efficiency:** Store raw MQTT exposes + parsed capabilities (redundancy for debugging)

**NFR13:** The system SHALL generate feature-based suggestions within the same daily batch window
- **Combined runtime:** Pattern analysis (5-10 min) + Feature analysis (<5 min) = <15 min total
- **No impact:** Device intelligence SHALL NOT increase existing batch time by >50%
- **Parallel processing:** Run pattern and feature analysis concurrently where possible

**NFR14:** The Device Intelligence dashboard SHALL load within 2 seconds
- **Metrics query:** <500ms for utilization scores
- **Device list:** <1 second for all devices with capabilities
- **Charts:** Client-side rendering with cached data
- **Pagination:** Support 100+ devices without performance degradation

**NFR15:** The system SHALL support incremental capability discovery
- **Real-time:** Update capabilities when new devices paired (within 30 seconds of MQTT message)
- **No downtime:** Capability updates SHALL NOT require service restart
- **Graceful degradation:** If MQTT unavailable, use cached capabilities
- **Recovery:** Auto-reconnect to MQTT broker if connection lost

**NFR16:** The system SHALL scale to 500+ devices from multiple manufacturers
- **Minimum:** 50 devices (small home)
- **Target:** 100-200 devices (typical home with multi-brand ecosystem)
- **Maximum:** 500 devices (large home)
- **Per-manufacturer:** Support 20+ different Zigbee manufacturers simultaneously

**NFR17:** Device Intelligence SHALL add minimal resource overhead to existing AI Automation Service
- **Memory:** +200MB maximum (capability database + feature analysis)
- **CPU:** <10% additional CPU during daily batch
- **Disk:** <100MB for capability database
- **Network:** One-time MQTT subscription (minimal bandwidth)

---

### 2.3 Compatibility Requirements

**CR1:** The system SHALL maintain compatibility with existing Home Assistant installation
- **HA Version:** Support Home Assistant 2024.1+
- **API:** Use stable HA REST API endpoints
- **Automations:** Generated automations must be valid HA YAML
- **No modification:** Do not require HA configuration changes

**CR2:** The system SHALL integrate with existing Data API without modification
- **Endpoints:** Use existing `/api/events`, `/api/devices`, `/api/entities`
- **No schema changes:** Do not require Data API updates
- **Graceful degradation:** Handle Data API downtime

**CR3:** The system SHALL use existing MQTT broker on Home Assistant server
- **Existing broker:** Connect to HA's MQTT broker (port 1883)
- **Authentication:** Use MQTT username/password from HA integration
- **Topic namespace:** Use `ha-ai/*` to avoid conflicts with HA topics
- **QoS:** Respect broker capacity limits (QoS 1 for reliability)

**CR4:** The system SHALL deploy alongside existing services without resource conflicts
- **Ports:** Use available port 8011 (AI service), 3002 (frontend)
- **Memory:** Stay within hardware constraints (8-16GB total)
- **CPU:** Batch processing scheduled during low-usage times (3 AM)

**CR5:** The system SHALL preserve all existing Home Assistant automations
- **Non-destructive:** Never delete or modify existing automations without user approval
- **Additive only:** Only add new automations when user approves
- **Rollback:** Support removing deployed automations

---

### 2.3.1 Device Intelligence Compatibility Requirements (NEW - Epic-AI-2)

**CR6:** The system SHALL integrate with Zigbee2MQTT without requiring configuration changes
- **MQTT subscription:** Read-only subscription to `zigbee2mqtt/bridge/devices`
- **No Zigbee2MQTT changes:** Do not modify Zigbee2MQTT configuration
- **Passive discovery:** Listen to existing MQTT topics without publishing to bridge topics
- **Compatibility:** Support Zigbee2MQTT 1.30.0+ (current stable versions)

**CR7:** The system SHALL enhance existing AI Automation Service without breaking pattern automation
- **Additive:** Add new tables to ai_automation.db without modifying existing tables
- **API extension:** Add new endpoints without changing existing endpoints
- **Backward compatible:** Existing pattern-based suggestions continue to work
- **Migration path:** Existing suggestions table supports new `feature_discovery` type

**CR8:** Device Intelligence SHALL integrate seamlessly with existing Health Dashboard
- **13th tab:** Add Device Intelligence as new tab without modifying existing 12 tabs
- **Consistent UI:** Follow existing React/TypeScript/TailwindCSS patterns
- **Chart library:** Use existing Recharts components for consistency
- **Navigation:** Integrate with existing tab navigation system
- **No conflicts:** Device Intelligence SHALL NOT interfere with existing dashboard functionality

**CR9:** The system SHALL support multi-integration architecture for future expansion
- **Phase 1:** Zigbee2MQTT MQTT bridge (primary)
- **Phase 2:** Z-Wave JS API integration (similar pattern)
- **Phase 3:** Native HA integration APIs (Hue, Shelly, etc.)
- **Extensible:** Database schema supports multiple integration types via `integration_type` column
- **Future-proof:** Architecture allows adding new integration sources without schema changes

---

## 3. User Interface Enhancement Goals

### 3.1 Integration with Existing UI

**Existing Health Dashboard Architecture (http://localhost:3000):**

The Health Dashboard uses a proven tab-based navigation pattern with:
- 12 tabs (Overview, Services, Dependencies, Devices, Events, Logs, Sports, Data Sources, Energy, Analytics, Alerts, Configuration)
- Dark mode toggle with localStorage persistence
- Auto-refresh capability
- Time range selector
- Mobile-first responsive design
- Error boundaries for graceful failures
- Custom navigation events for cross-linking

**New AI Automation Frontend SHALL Follow Same Patterns:**

```typescript
// Match existing Dashboard.tsx structure
- Tab-based navigation (not sidebar)
- Dark mode prop passed to all components
- TabProps interface for consistency
- Error boundaries around tab content
- Custom hooks for data fetching (useHealth pattern)
- Loading skeletons (SkeletonCard components)
- Modal detail views (ServiceDetailsModal pattern)
```

**Design System Consistency:**

```typescript
// Use existing tailwind.config.js
- CSS Custom Properties (var(--color-primary))
- Design tokens: design-primary, design-success, design-warning, design-error
- Consistent shadows: shadow-design-sm/md/lg/xl
- Animation system: fade-in, slide-up, scale-in
- Dark mode class: 'dark'
- Status color system (getStatusColors helper)
```

---

### 3.2 Screens and Views

#### **Main Dashboard Structure:**

```typescript
// AI Automation Dashboard (Port 3002)
const AI_TAB_CONFIG = [
  { id: 'suggestions', label: '💡 Suggestions', icon: '💡' },
  { id: 'patterns', label: '📊 Patterns', icon: '📊' },
  { id: 'automations', label: '⚙️ Automations', icon: '⚙️' },
  { id: 'insights', label: '🔍 Insights', icon: '🔍' },
];
```

#### **Tab 1: Suggestions Browser (Primary)**

**Layout Pattern:** Card grid with modals (matches OverviewTab's CoreSystemCard)

**Features:**
- Card grid (1/2/3 columns responsive)
- Search and filter controls
- Status badges (pending/approved/deployed/rejected)
- Confidence scores (>70%, >80%, >90%)
- Click card → detail modal
- Modal shows: pattern analysis + YAML preview + approve/reject actions
- Loading skeletons (SkeletonCard pattern)

**Status Colors (from existing getStatusColors):**

```typescript
pending:  blue-100 / blue-900/30 (dark)  ⏳
approved: green-100 / green-900/30       ✅
deployed: purple-100 / purple-900/30     🚀
rejected: red-100 / red-900/30           ❌
```

#### **Tab 2: Patterns Insights**

**Layout Pattern:** Stat cards + charts (matches AnalyticsTab)

**Features:**
- Pattern detection summary (stat cards)
- Category breakdown (time-of-day/co-occurrence/anomaly)
- Pattern chart (PerformanceSparkline style)
- Confidence score indicators
- Pattern detail modals
- Filter by pattern type

#### **Tab 3: Current Automations**

**Layout Pattern:** Search + filters + list (exactly like DevicesTab)

**Features:**
- Search automations by name
- Filter by source (user-created vs AI-deployed)
- Filter by status (active/disabled)
- List view with badges (👤 User / 🤖 AI)
- Detail modal (ServiceDetailsModal pattern)
- Remove AI automations action
- Execution history and success rates
- "View in HA" links (opens HA UI)

#### **Tab 4: Insights Dashboard**

**Layout Pattern:** Hero card + system status (matches OverviewTab)

**Features:**
- Hero card: Last analysis summary
- Stat cards: Suggestions generated/approved/deployed
- API cost tracking (budget monitor)
- Acceptance rate chart
- Pattern trends (last 7 days)
- System status cards (green/yellow/red)
- Service health indicators (Data API, MQTT, LLM API)

---

### 3.2.1 Device Intelligence UI (NEW - Health Dashboard Tab)

**Location:** New 13th tab in existing Health Dashboard (Port 3000)

**Tab Configuration:**
```typescript
const DASHBOARD_TABS = [
  // ... existing 12 tabs
  { id: 'device-intelligence', label: '🧠 Device Intelligence', icon: '🧠' }
];
```

#### **Device Intelligence Page Layout**

**Section 1: Utilization Overview (Hero Metrics)**
```typescript
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
  <MetricCard
    title="Device Utilization"
    value="32%"
    trend="+12%"
    target="45%"
    progressBar={true}
  />
  <MetricCard
    title="Features Discovered"
    value="18"
    trend="+4 this month"
  />
  <MetricCard
    title="Energy Savings"
    value="$67"
    subtitle="6 months cumulative"
  />
  <MetricCard
    title="Automation Quality"
    value="42%"
    subtitle="Fewer manual actions"
  />
</div>
```

**Section 2: Utilization by Manufacturer (Chart)**
```typescript
<Card title="Utilization by Brand">
  <BarChart 
    data={manufacturerUtilization}
    xKey="manufacturer"
    yKey="utilization"
    height={300}
  />
</Card>
```

**Section 3: Top Opportunities (Ranked List)**
```typescript
<Card title="Top Feature Opportunities">
  <OpportunityList items={opportunities} />
  {/* Each item shows:
    - Device name + manufacturer
    - Feature name
    - Impact badge (high/medium/low)
    - Complexity (easy/medium/hard)
    - [Configure Now] button
  */}
</Card>
```

**Section 4: All Devices Table**
```typescript
<Card title="All Devices">
  <DeviceUtilizationTable
    columns={['Device', 'Manufacturer', 'Model', 'Utilization', 'Unused Features']}
    data={devices}
    searchable={true}
    sortable={['Utilization', 'Manufacturer']}
    filterable={['Manufacturer']}
    onRowClick={(device) => showDeviceDetails(device)}
  />
</Card>
```

**Section 5: Recent Activity (Timeline)**
```typescript
<Card title="Recently Configured">
  <Timeline events={recentFeatures} />
  {/* Shows last 10 feature configurations with dates */}
</Card>
```

**Reused Patterns from Existing Dashboard:**
- **Card component** (OverviewTab, AnalyticsTab, etc.)
- **MetricCard** (OverviewTab pattern)
- **BarChart via Recharts** (AnalyticsTab pattern)
- **DataTable** (DevicesTab pattern)
- **Timeline** (EventsTab pattern)
- **ProgressBar** (OverviewTab pattern)
- **StatusBadge** (ServicesTab pattern)
- **Dark mode support** (existing theme)
- **Mobile responsiveness** (existing grid system)

**NO New Component Patterns Required** - 100% reuse of existing patterns!

---

### 3.3 Reusable Components from Existing Dashboard

**Components to Import/Reuse:**

```typescript
// From existing health-dashboard
import { SkeletonCard } from '../skeletons'
import { ErrorBoundary } from './ErrorBoundary'
import { AlertBanner } from './AlertBanner'

// Pattern-based components to create (matching existing style):
- SuggestionCard (like CoreSystemCard)
- SuggestionDetailModal (like ServiceDetailsModal)
- PatternChartCard (like PerformanceSparkline)
- AutomationListItem (like device list items)
- StatCard (reuse from AnalyticsTab)
```

**Proven UX Patterns to Reuse:**

1. **Search + Filter** (DevicesTab pattern)
2. **Card → Modal detail view** (ServiceDetailsModal pattern)
3. **Loading skeletons** (SkeletonCard components)
4. **Status color system** (getStatusColors helper)
5. **Error boundaries** (graceful degradation)
6. **44px touch targets** (mobile-friendly)
7. **Horizontal tab scrolling** (mobile optimization)
8. **Custom navigation events** (cross-tab linking)

---

### 3.4 Design System Specifications

**TailwindCSS Configuration (from existing health-dashboard):**

```javascript
// Use existing tailwind.config.js
colors: {
  'design-primary': 'var(--color-primary)',     // Blue
  'design-success': 'var(--color-success)',     // Green
  'design-warning': 'var(--color-warning)',     // Yellow
  'design-error': 'var(--color-error)',         // Red
  'design-info': 'var(--color-info)',           // Cyan
}

// Status colors
healthy:  green-100 / green-900/30
degraded: yellow-100 / yellow-900/30
unhealthy: red-100 / red-900/30
paused:   gray-100 / gray-700

// Animations
'fade-in': 'fadeIn 0.5s ease-in-out'
'slide-up': 'slideUp 0.3s ease-out'
'scale-in': 'scaleIn 0.2s ease-out'
```

**Typography:**

```css
H1: text-2xl sm:text-3xl font-bold
H2: text-xl sm:text-2xl font-bold
H3: text-lg font-semibold
Body: text-sm sm:text-base
Small: text-xs sm:text-sm
```

**Spacing:**

```css
gap-4: Cards on mobile
gap-6: Cards on desktop
p-4: Mobile cards
p-6: Desktop cards
p-8: Main container
```

---

### 3.5 Mobile Responsiveness

**Responsive Breakpoints (Tailwind defaults):**

```
sm: 640px   // Tablet
md: 768px   // Desktop
lg: 1024px  // Large desktop
```

**Proven patterns from existing dashboard:**

- Grid: 1 col (mobile) → 2 cols (tablet) → 3-4 cols (desktop)
- Text: text-sm (mobile) → text-base (desktop)
- Padding: p-4 (mobile) → p-6 (desktop)
- Header: stacked (mobile) → side-by-side (desktop)
- Tabs: horizontal scroll (mobile) → full width (desktop)
- Buttons: min-w-[44px] min-h-[44px] (touch-friendly)

---

### 3.6 User Experience Consistency Requirements

**UC1:** The AI Automation frontend SHALL match the existing Health Dashboard's visual design
- ✅ Same tab navigation pattern
- ✅ Same card styles (rounded-lg, shadow-lg, padding)
- ✅ Same status colors (green/yellow/red system)
- ✅ Same modal patterns (ServiceDetailsModal structure)
- ✅ Same emoji icons (💡 🚀 ⚙️ ✅ ❌)

**UC2:** The frontend SHALL reuse proven interaction patterns
- ✅ Search + filters (DevicesTab pattern)
- ✅ Click card → modal details
- ✅ Loading states (SkeletonCard components)
- ✅ Error handling (ErrorBoundary wrapper)
- ✅ Dark mode toggle (header button, localStorage)

**UC3:** The frontend SHALL maintain performance standards
- ✅ Initial load: <2 seconds
- ✅ Tab switching: Instant (no re-fetch)
- ✅ Modal animations: 200-300ms
- ✅ Auto-refresh: 30-60 seconds (optional, user-controlled)

**UC4:** The frontend SHALL provide cross-linking
- ✅ Link from Health Dashboard → AI Automation
- ✅ Link from AI Automation → Health Dashboard Devices tab
- ✅ Custom navigation events for modal cross-linking

**UC5:** The frontend SHALL be mobile-optimized
- ✅ Touch targets: 44px minimum
- ✅ Horizontal scroll tabs (works well on mobile)
- ✅ Responsive grids (1→2→3 columns)
- ✅ Stacked headers on mobile

---

## 4. Technical Constraints and Integration

### 4.1 Existing Technology Stack (Must Use)

**Backend Stack:**
- Python 3.11
- FastAPI 0.104.1
- Docker + Docker Compose 2.20+
- InfluxDB 2.7 (via Data API)
- SQLite 3.45+

**Frontend Stack:**
- React 18.2.0
- TypeScript 5.2.2
- TailwindCSS 3.4.0
- Vite 5.0.8
- Heroicons 2.2.0

**Infrastructure:**
- MQTT (existing on Home Assistant server)
- Docker Volumes
- Python logging

---

### 4.2 Phase 1 MVP Technology Stack (NEW)

**Machine Learning:**

```python
scikit-learn==1.3.2
  - KMeans (clustering)
  - DBSCAN (density-based clustering)
  - Isolation Forest (anomaly detection)

pandas==2.1.4
  - Data manipulation
  - Feature engineering

numpy==1.26.2
  - Numerical operations
```

**LLM Integration:**

```python
openai==1.12.0
  - GPT-4o-mini API client
  - Structured outputs (Pydantic)

langchain==0.1.0 (Optional - may defer to Phase 2)
  - Prompt management
  - Chain orchestration
```

**MQTT Communication:**

```python
paho-mqtt==1.6.1
  - MQTT client
  - Pub/sub patterns
```

**Database & Storage:**

```python
aiosqlite==0.19.0
  - Async SQLite
  - Pattern storage
```

**Scheduling:**

```python
apscheduler==3.10.4
  - Cron-style scheduling
  - Daily batch jobs
```

---

### 4.3 Integration Approach

#### Data API Integration (Read-Only):

```python
# Query existing Data API for historical data
async def fetch_historical_events():
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://data-api:8006/api/events",
            params={
                "start": "-30d",
                "group_by": "device_id"
            }
        )
        return response.json()
```

**No Direct InfluxDB Access:**
- ✅ Use Data API as abstraction layer
- ❌ Do NOT query InfluxDB directly

#### Home Assistant API Integration:

```python
# Read existing automations
GET http://ha:8123/api/config/automation/config

# Deploy new automation
POST http://ha:8123/api/config/automation/config
{
  "alias": "AI Suggested: Morning Lights",
  "trigger": [...],
  "action": [...]
}

# Remove automation
DELETE http://ha:8123/api/config/automation/config/{automation_id}
```

#### MQTT Integration:

```bash
# Topic structure
ha-ai/events/*          # AI publishes
ha-ai/commands/*        # AI sends commands
ha-ai/responses/*       # HA responds
homeassistant/status    # HA status
```

---

### 4.4 Code Organization

```
services/ai-automation-service/
├── src/
│   ├── main.py                      # FastAPI entry point
│   ├── config.py                    # Configuration
│   ├── pattern_analyzer/            # Pattern detection
│   │   ├── time_of_day.py
│   │   ├── co_occurrence.py
│   │   └── anomaly_detector.py
│   ├── llm/                         # LLM integration
│   │   ├── openai_client.py
│   │   └── prompt_templates.py
│   ├── mqtt/                        # MQTT communication
│   │   ├── client.py
│   │   └── topics.py
│   ├── database/                    # Database layer
│   │   ├── models.py
│   │   └── crud.py
│   ├── api/                         # FastAPI endpoints
│   │   ├── suggestions.py
│   │   ├── patterns.py
│   │   └── deployment.py
│   └── scheduler/                   # Batch scheduling
│       └── daily_analysis.py
├── tests/
├── Dockerfile
├── requirements.txt
└── README.md
```

---

### 4.5 Deployment Configuration

**Docker Compose Integration:**

```yaml
services:
  # NEW: AI Automation Service
  # Note: Uses existing MQTT broker on Home Assistant server
  ai-automation-service:
    build: ./services/ai-automation-service
    ports:
      - "8011:8011"
    environment:
      - DATA_API_URL=http://data-api:8006
      - HA_URL=${HA_URL}  # HA server address
      - HA_TOKEN=${HA_TOKEN}
      - MQTT_BROKER=${MQTT_BROKER}  # HA server IP (has MQTT)
      - MQTT_PORT=${MQTT_PORT:-1883}
      - MQTT_USERNAME=${MQTT_USERNAME}
      - MQTT_PASSWORD=${MQTT_PASSWORD}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANALYSIS_SCHEDULE=0 3 * * *
    env_file:
      - infrastructure/env.ai-automation
    depends_on:
      - data-api
    volumes:
      - ai_data:/app/data
    networks:
      - ha-network
  
  # NEW: AI Frontend
  ai-automation-frontend:
    build: ./services/ai-automation-frontend
    ports:
      - "3002:80"
    environment:
      - AI_API_URL=http://localhost:8011
    depends_on:
      - ai-automation-service
    networks:
      - ha-network
```

---

### 4.6 Performance Constraints

**Memory Limits:**
- Peak (analysis): 1GB
- Idle: 200MB
- Total system: Must fit within NUC 8-16GB RAM

**Processing Time:**
- Daily analysis: 10 minutes target, 15 minutes max
- API response: 500ms target
- LLM generation: 30 seconds per suggestion (async)

**Storage:**
- Code + dependencies: 500MB
- Pattern database: 100MB
- Logs: 50MB (rotating)
- Total: <1GB

---

### 4.7 Security Constraints

**Network Security:**
- ✅ MQTT on internal network only
- ✅ All services within Docker network
- ✅ No public endpoints except frontend

**API Security:**
- ✅ Home Assistant token authentication
- ✅ CORS restricted to localhost
- ✅ Rate limiting on API endpoints

**Data Security:**
- ✅ No raw event data sent to LLM (only anonymized patterns)
- ✅ HA tokens stored securely (environment variables)
- ✅ OpenAI API key in environment (not code)

---

## 5. Epic and Story Structure

### 5.1 Epic Approach

**Epic Structure Decision:** Single comprehensive epic for Phase 1 MVP

**Rationale:**
- Phase 1 is a cohesive MVP with tightly coupled components
- All stories work toward single goal: deliver working automation suggestion system
- Maintains simplicity and clear scope boundaries
- Allows for focused 2-4 week delivery timeline

---

### 5.2 Epic 1: AI Automation Suggestion System (Phase 1 MVP)

**Epic ID:** Epic-AI-1  
**Epic Goal:** Enable users to discover and deploy Home Assistant automations based on AI-detected patterns from historical data

**Success Criteria:**
- ✅ User receives 5-10 automation suggestions weekly
- ✅ Pattern analysis completes in <10 minutes daily
- ✅ Approved automations deploy successfully to Home Assistant
- ✅ System runs within 1GB RAM budget
- ✅ API costs stay under $10/month
- ✅ No impact on existing services

---

### 5.3 Story List

#### **Story 1.1: Infrastructure Setup and MQTT Integration**

**As a** developer  
**I want** to configure connection to existing HA MQTT broker  
**so that** AI service can communicate with Home Assistant asynchronously

**⚠️ IMPORTANT:** MQTT broker already running on Home Assistant server (port 1883). This story configures connection credentials only.

**Acceptance Criteria:**
1. ✅ AI service connects to HA MQTT broker successfully
2. ✅ MQTT credentials configured in environment (.env.ai-automation)
3. ✅ Topics ha-ai/* can be published/subscribed
4. ✅ Connection authenticated with username/password
5. ✅ Test messages verified in HA Developer Tools

**Estimated Effort:** 2-3 hours

---

#### **Story 1.2: AI Service Backend Foundation**

**As a** developer  
**I want** to create the AI automation service backend structure  
**so that** we have a foundation for pattern detection and LLM integration

**Acceptance Criteria:**
1. ✅ Service starts successfully in Docker
2. ✅ FastAPI health endpoint returns 200 OK
3. ✅ SQLite database initializes with schema
4. ✅ Service accessible on port 8011
5. ✅ Logging outputs to stdout (JSON format)

**Dependencies:** Story 1.1  
**Estimated Effort:** 6-8 hours

---

#### **Story 1.3: Data API Integration and Historical Data Fetching**

**As a** pattern analyzer  
**I want** to query the Data API for historical event data  
**so that** I can detect patterns in device usage

**Acceptance Criteria:**
1. ✅ Can fetch last 30 days of events from Data API
2. ✅ Can fetch device and entity metadata
3. ✅ Data transformed to pandas DataFrame format
4. ✅ Handles Data API downtime gracefully
5. ✅ Query response time <5 seconds for 30 days

**Dependencies:** Story 1.2  
**Estimated Effort:** 8-10 hours

---

#### **Story 1.4: Pattern Detection - Time-of-Day Clustering**

**As a** pattern analyzer  
**I want** to detect time-of-day patterns using KMeans clustering  
**so that** I can identify when devices are consistently used

**Acceptance Criteria:**
1. ✅ Detects patterns for devices used at consistent times
2. ✅ Minimum 3 occurrences required for pattern
3. ✅ Confidence score >70% required
4. ✅ Processes 30 days in <5 minutes
5. ✅ Memory usage <500MB

**Dependencies:** Story 1.3  
**Estimated Effort:** 10-12 hours

---

#### **Story 1.5: Pattern Detection - Device Co-Occurrence**

**As a** pattern analyzer  
**I want** to detect device co-occurrence patterns  
**so that** I can identify devices frequently used together

**Acceptance Criteria:**
1. ✅ Detects devices used within 5-minute window
2. ✅ Minimum support: 5 occurrences
3. ✅ Minimum confidence: 70%
4. ✅ Processing time <3 minutes for 100 devices

**Dependencies:** Story 1.4  
**Estimated Effort:** 8-10 hours

---

#### **Story 1.6: Pattern Detection - Anomaly Detection**

**As a** pattern analyzer  
**I want** to detect anomalies indicating automation opportunities  
**so that** I can suggest automations for repeated manual interventions

**Acceptance Criteria:**
1. ✅ Detects repeated manual interventions
2. ✅ Minimum 3 occurrences to qualify
3. ✅ Confidence score based on consistency
4. ✅ Processing time <2 minutes
5. ✅ Precision >60%

**Dependencies:** Story 1.5  
**Estimated Effort:** 8-10 hours

---

#### **Story 1.7: LLM Integration - OpenAI API Client**

**As a** suggestion generator  
**I want** to integrate with OpenAI GPT-4o-mini API  
**so that** I can generate natural language automation suggestions

**Acceptance Criteria:**
1. ✅ Successfully calls OpenAI GPT-4o-mini API
2. ✅ Generates valid Home Assistant automation YAML
3. ✅ Returns structured JSON with Pydantic validation
4. ✅ Tracks token usage per request
5. ✅ Suggestion quality: 80%+ valid automations

**Dependencies:** Story 1.6  
**Estimated Effort:** 8-10 hours

---

#### **Story 1.8: Suggestion Generation Pipeline**

**As a** user  
**I want** the system to generate automation suggestions from detected patterns  
**so that** I can review and approve them

**Acceptance Criteria:**
1. ✅ Generates 5-10 suggestions per weekly run
2. ✅ Suggestions ranked by confidence
3. ✅ No duplicate suggestions
4. ✅ Generation time <5 minutes
5. ✅ API cost <$1 per batch

**Dependencies:** Story 1.7  
**Estimated Effort:** 10-12 hours

---

#### **Story 1.9: Daily Batch Scheduler**

**As a** system  
**I want** to run pattern analysis daily at 3 AM  
**so that** users wake up to new automation suggestions

**Acceptance Criteria:**
1. ✅ Job runs daily at 3:00 AM automatically
2. ✅ Job completes in <15 minutes
3. ✅ MQTT notification on completion
4. ✅ Manual trigger endpoint available

**Dependencies:** Story 1.8  
**Estimated Effort:** 6-8 hours

---

#### **Story 1.10: REST API - Suggestion Management**

**As a** frontend  
**I want** REST API endpoints for suggestion CRUD operations  
**so that** users can browse, approve, and reject suggestions

**Acceptance Criteria:**
1. ✅ List endpoint returns paginated suggestions
2. ✅ Filter by status and confidence
3. ✅ Update suggestion status
4. ✅ API response time <200ms (cached)

**Dependencies:** Story 1.9  
**Estimated Effort:** 8-10 hours

---

#### **Story 1.11: REST API - Home Assistant Integration**

**As a** user  
**I want** to deploy approved automations to Home Assistant  
**so that** they run automatically

**Acceptance Criteria:**
1. ✅ Converts suggestion to valid HA YAML
2. ✅ Deploys to HA via REST API
3. ✅ Tracks deployment status
4. ✅ Can remove deployed automations

**Dependencies:** Story 1.10  
**Estimated Effort:** 10-12 hours

---

#### **Story 1.12: MQTT Event Publishing**

**As a** AI service  
**I want** to publish events to MQTT topics  
**so that** Home Assistant can subscribe to dynamic triggers

**Acceptance Criteria:**
1. ✅ Publishes to ha-ai/events/* topics
2. ✅ QoS 1 ensures message delivery
3. ✅ HA can subscribe and receive messages
4. ✅ Message latency <100ms

**Dependencies:** Story 1.11  
**Estimated Effort:** 6-8 hours

---

#### **Story 1.13: Frontend - Project Setup and Dashboard Shell**

**As a** frontend developer  
**I want** to set up the React project with tab navigation  
**so that** we have a foundation matching the Health Dashboard

**Acceptance Criteria:**
1. ✅ Project builds successfully with Vite
2. ✅ TailwindCSS matches health-dashboard config
3. ✅ Dark mode toggle works
4. ✅ Tab navigation in place
5. ✅ Container runs on port 3002

**Dependencies:** None  
**Estimated Effort:** 8-10 hours

---

#### **Story 1.14: Frontend - Suggestions Tab**

**As a** user  
**I want** to browse automation suggestions in a card grid  
**so that** I can review AI-generated automations

**Acceptance Criteria:**
1. ✅ Displays suggestions in card grid
2. ✅ Search and filter controls
3. ✅ Click card opens detail modal
4. ✅ Approve/reject actions work
5. ✅ Mobile responsive

**Dependencies:** Story 1.13, Story 1.10  
**Estimated Effort:** 12-14 hours

---

#### **Story 1.15: Frontend - Patterns Tab**

**As a** user  
**I want** to view detected patterns and analysis insights  
**so that** I understand what the AI detected

**Acceptance Criteria:**
1. ✅ Shows pattern summary stats
2. ✅ Displays patterns grouped by type
3. ✅ Chart shows detection over time
4. ✅ Filter by pattern type

**Dependencies:** Story 1.14  
**Estimated Effort:** 10-12 hours

---

#### **Story 1.16: Frontend - Current Automations Tab**

**As a** user  
**I want** to view existing HA automations and AI-deployed ones  
**so that** I can manage my automations

**Acceptance Criteria:**
1. ✅ Displays user-created + AI-deployed automations
2. ✅ Badges distinguish source
3. ✅ Can remove AI-deployed automations
4. ✅ Shows execution stats

**Dependencies:** Story 1.15  
**Estimated Effort:** 10-12 hours

---

#### **Story 1.17: Frontend - Insights Dashboard Tab**

**As a** user  
**I want** to see system status and AI service health  
**so that** I know everything is working correctly

**Acceptance Criteria:**
1. ✅ Shows last analysis summary
2. ✅ Displays API cost tracking
3. ✅ System status cards
4. ✅ Acceptance rate chart

**Dependencies:** Story 1.16  
**Estimated Effort:** 10-12 hours

---

#### **Story 1.18: End-to-End Testing and Documentation**

**As a** developer  
**I want** comprehensive E2E tests and documentation  
**so that** the system is reliable and maintainable

**Acceptance Criteria:**
1. ✅ E2E test: Full suggestion approval flow
2. ✅ E2E tests run in CI/CD
3. ✅ README documents setup
4. ✅ API documentation complete

**Dependencies:** Story 1.17  
**Estimated Effort:** 12-14 hours

---

### 5.4 Epic 2: Device Intelligence System (NEW - Phase 2)

**Epic ID:** Epic-AI-2  
**Epic Goal:** Enable users to discover and utilize device capabilities across ALL Zigbee manufacturers through universal capability discovery and feature-based suggestions

**Dependencies:** Epic-AI-1 (AI Automation Service foundation must exist)

**Success Criteria:**
- ✅ Capability database populated for 95%+ of user's Zigbee devices automatically
- ✅ Device utilization score increases from 20% to 25%+ within 30 days
- ✅ User discovers and configures 3+ previously unknown device features
- ✅ Feature-based suggestions integrated with pattern-based suggestions
- ✅ Device Intelligence dashboard tab functional in Health Dashboard
- ✅ Works automatically for ALL Zigbee manufacturers (6,000+ models)

**Key Differentiator:** Universal, automated capability discovery via Zigbee2MQTT MQTT bridge (no manual research needed)

---

### 5.5 Epic-AI-2 Story List

#### **Story 2.1: MQTT Capability Listener & Universal Parser**

**As a** system administrator  
**I want** automatic device capability discovery from Zigbee2MQTT during daily batch analysis  
**so that** the system knows what ALL my Zigbee devices can do (any manufacturer)

**Acceptance Criteria:**
1. Query `zigbee2mqtt/bridge/devices` MQTT topic during daily batch (3 AM)
2. Check HA device registry for new/updated devices since last run
3. Parse Zigbee2MQTT `exposes` format for ANY manufacturer (universal parser)
4. Extract capabilities (features, configuration options, MQTT topics)
5. Handle all device types (switches, sensors, bulbs, plugs, thermostats, etc.)
6. Process 100+ devices within 3 minutes
7. Log successful capability extraction for each device
8. Integrate with existing daily scheduler (Story 1.9 - no 24/7 listener)

**Architecture Change:**
- **Before:** Real-time MQTT listener (24/7 subscription)
- **After:** Batch query during daily analysis (5 min/day)
- **Benefit:** Same user experience, 99% less resource usage, simpler failure modes

**Integration Points:**
- Existing MQTT client in ai-automation-service
- Daily scheduler (Story 1.9)
- Zigbee2MQTT bridge (external, read-only)

**Estimated Effort:** 8-10 hours (reduced - simpler than real-time listener)

---

#### **Story 2.2: Device Capability Database Schema & Storage**

**As a** developer  
**I want** to store device capabilities in SQLite database  
**so that** we can match devices to their available features

**Acceptance Criteria:**
1. Create `device_capabilities` table with universal schema (supports any manufacturer)
2. Create `device_feature_usage` table for tracking utilization
3. Index by manufacturer, model, integration_type for fast lookups
4. Store raw MQTT exposes + parsed capabilities
5. Support upsert operations (update existing, insert new)
6. Query performance <10ms for capability lookups

**Database Schema:**
```sql
CREATE TABLE device_capabilities (
    device_model TEXT PRIMARY KEY,
    manufacturer TEXT NOT NULL,
    integration_type TEXT NOT NULL,
    description TEXT,
    capabilities JSON NOT NULL,
    mqtt_exposes JSON,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source TEXT DEFAULT 'zigbee2mqtt_bridge'
);

CREATE TABLE device_feature_usage (
    device_id TEXT,
    feature_name TEXT,
    configured BOOLEAN DEFAULT FALSE,
    discovered_date TIMESTAMP,
    last_checked TIMESTAMP,
    PRIMARY KEY (device_id, feature_name),
    FOREIGN KEY (device_id) REFERENCES devices(device_id)
);
```

**Dependencies:** Story 2.1  
**Estimated Effort:** 8-10 hours

---

#### **Story 2.3: Device-to-Capability Matching Engine**

**As a** feature analyzer  
**I want** to link device instances to their capability definitions  
**so that** I can identify which features are unused

**Acceptance Criteria:**
1. Query existing devices from data-api service
2. Match devices to capabilities via manufacturer + model
3. For each device, determine which features are configured
4. Calculate utilization score per device (configured / total * 100)
5. Store results in device_feature_usage table
6. Handle devices without capability definitions gracefully (log, use fallback)

**Dependencies:** Story 2.2  
**Estimated Effort:** 10-12 hours

---

#### **Story 2.4: Feature-Based Suggestion Generator**

**As a** user  
**I want** the system to suggest unused device features  
**so that** I can discover capabilities I didn't know existed

**Acceptance Criteria:**
1. Scan all devices for unused features (configured = false)
2. Prioritize by impact (energy savings, convenience, security)
3. Consider device location (area) and usage patterns
4. Generate natural language suggestions via OpenAI LLM
5. Include device-specific context (manufacturer, model, current config)
6. Store suggestions with type = 'feature_discovery'
7. Generate 5-10 feature suggestions per daily run

**Example Output:**
```
[Inovelli VZM31-SN - Kitchen Switch]
Enable LED Notifications (unused feature)

Your kitchen switch supports 7 individually controllable RGB LEDs that can show status indicators. Pattern detected: You frequently check garage door status from kitchen. 

Suggestion: Configure red LED to show when garage door is open.
Complexity: Easy (5-minute setup)
Impact: High (visual awareness, no phone checking)
```

**Dependencies:** Story 2.3  
**Estimated Effort:** 12-14 hours

---

#### **Story 2.5: Unified Daily Batch Job (Pattern + Feature Analysis)**

**As a** system  
**I want** a single daily batch job that combines pattern detection and feature analysis  
**so that** I can provide comprehensive AI suggestions efficiently

**Acceptance Criteria:**
1. **Unified 3 AM Daily Job:** Combines Epic-AI-1 and Epic-AI-2 analysis
2. **Device Capability Update:** Query new devices, fetch capabilities from Zigbee2MQTT bridge (Story 2.1 batch query)
3. **InfluxDB Query:** Fetch last 30 days of events (shared by both epics)
4. **Pattern Detection:** Run time-of-day, co-occurrence, anomaly detection (Epic-AI-1)
5. **Feature Analysis:** Analyze device utilization, detect unused features (Epic-AI-2)
6. **Combined Suggestions:** Generate pattern-based + feature-based suggestions
7. **Unified Ranking:** Rank by combined score (confidence * impact)
8. **Balanced Output:** Limit to top 5-10 suggestions total with type balance
9. **Performance:** Complete full analysis in <10 minutes
10. **Logging:** Show unified progress: "Device capabilities: 5 updated, Pattern detection: 3 patterns, Feature analysis: 7 opportunities, Suggestions: 8 generated"

**Example Combined Output:**
```
Daily AI Analysis Complete (3:08 AM):
- Devices scanned: 99 (5 new capabilities updated)
- Events analyzed: 14,523 (last 30 days)
- Patterns detected: 3 time-of-day, 2 co-occurrence, 1 anomaly
- Unused features: 23 high-impact opportunities found
- Suggestions generated: 8 total (4 pattern + 4 feature)

Top Suggestions:
1. [Pattern] Create sunrise automation (bedroom light 6am daily) - 92% confidence
2. [Feature] Enable LED notifications on kitchen switch (Inovelli) - 88% confidence
3. [Pattern] Motion + light automation (hallway correlation) - 85% confidence
4. [Feature] Configure vibration detection on front door sensor (Aqara) - 82% confidence
5. [Feature] Use color temperature presets on bedroom bulb (IKEA) - 78% confidence
```

**Architecture Benefits:**
- ✅ Single unified job (vs. separate real-time listener + pattern batch)
- ✅ Shared InfluxDB query (one 30-day fetch for both epics)
- ✅ Combined suggestion generation (can create hybrid suggestions)
- ✅ 99% less resource usage (5-10 min/day vs. 24/7 listener)
- ✅ Simpler monitoring (one job status vs. multiple services)

**Dependencies:** Stories 2.1-2.4 + Epic-AI-1 Stories 1.1-1.9  
**Estimated Effort:** 10-12 hours (increased to include refactoring 2.1 to batch)

---

#### **Story 2.6: Device Utilization Calculator & Metrics API**

**As a** user  
**I want** to see how much of my devices' capabilities I'm actually using  
**so that** I can track ROI and discover optimization opportunities

**Acceptance Criteria:**
1. Calculate overall home utilization score (total configured / total available * 100)
2. Calculate per-device utilization scores
3. Calculate per-manufacturer aggregate scores (Inovelli, Aqara, IKEA, etc.)
4. Track utilization trends over time
5. API endpoint: GET /api/device-intelligence/utilization
6. API endpoint: GET /api/device-intelligence/opportunities
7. Response time <500ms

**Example API Response:**
```json
{
  "overall_utilization": 32,
  "target": 45,
  "trend": "+12% this month",
  "total_devices": 99,
  "total_features": 387,
  "configured_features": 124,
  "by_manufacturer": {
    "Inovelli": { "utilization": 35, "devices": 12 },
    "Aqara": { "utilization": 38, "devices": 15 },
    "IKEA": { "utilization": 32, "devices": 8 },
    "Xiaomi": { "utilization": 28, "devices": 20 },
    "Other": { "utilization": 30, "devices": 44 }
  }
}
```

**Dependencies:** Story 2.3  
**Estimated Effort:** 8-10 hours

---

#### **Story 2.7: Device Intelligence Dashboard Tab (Health Dashboard)**

**As a** user  
**I want** a Device Intelligence tab in my Health Dashboard  
**so that** I can visualize device utilization and discover opportunities

**Acceptance Criteria:**
1. Add 13th tab to existing Health Dashboard navigation
2. Display overall utilization score with progress bar
3. Show utilization breakdown by manufacturer (bar chart)
4. List top 10 unused features with device details
5. Display all devices table (searchable, filterable, sortable)
6. Show recent feature configurations timeline
7. Page loads in <2 seconds
8. Follows existing Health Dashboard UI patterns (Card, Charts, Table)
9. Dark mode support (existing theme)
10. Mobile responsive (existing grid system)

**Reused Components:**
- Card, MetricCard, ProgressBar (OverviewTab)
- BarChart via Recharts (AnalyticsTab)
- DataTable (DevicesTab)
- Timeline (EventsTab)

**Dependencies:** Story 2.6  
**Estimated Effort:** 12-14 hours

---

#### **Story 2.8: Manual Capability Refresh & Context7 Fallback**

**As a** user  
**I want** to manually refresh device capabilities  
**so that** I can update capability data or research unsupported devices

**Acceptance Criteria:**
1. API endpoint: POST /api/device-intelligence/capabilities/refresh
2. Dashboard button: "Refresh Device Capabilities"
3. For devices in Zigbee2MQTT: Re-query MQTT bridge
4. For devices NOT in bridge: Query Context7 for documentation
5. Show progress indicator during refresh
6. Handle errors gracefully (log, show user-friendly message)
7. Update last_updated timestamp in database

**Fallback Flow:**
```
1. Check device_capabilities table
2. If found and fresh (<30 days): Use cached
3. If stale or missing:
   a. Try Zigbee2MQTT MQTT bridge first
   b. If not found, query Context7
   c. If not found, mark as "manual definition required"
```

**Dependencies:** Story 2.2  
**Estimated Effort:** 8-10 hours

---

#### **Story 2.9: Feature Discovery Integration Testing**

**As a** QA tester  
**I want** comprehensive tests for device intelligence  
**so that** the system reliably discovers capabilities for all manufacturers

**Acceptance Criteria:**
1. Unit tests: MQTT exposes parser (test 10+ different manufacturers)
2. Unit tests: Utilization calculator (multi-brand scenarios)
3. Integration test: MQTT listener → database population
4. Integration test: Feature suggestion generation (Inovelli, Aqara, IKEA examples)
5. E2E test: Dashboard loads Device Intelligence tab
6. E2E test: Utilization metrics display correctly
7. Test data: Mock Zigbee2MQTT bridge message with 20+ device models
8. Documentation: Device Intelligence setup guide

**Test Coverage:**
- Inovelli switch capabilities
- Aqara sensor capabilities
- IKEA bulb capabilities
- Xiaomi sensor capabilities
- Generic Zigbee device capabilities

**Dependencies:** Stories 2.1-2.7  
**Estimated Effort:** 10-12 hours

---

## 6. Epic Summary

### 6.1 Epic-AI-1 Summary (Pattern Automation)

**Total Stories:** 18  
**Estimated Total Effort:** 160-192 hours (4-5 weeks for single developer)  
**Status:** Partially implemented (Stories 1-18 defined)

---

### 6.2 Epic-AI-2 Summary (Device Intelligence)

**Total Stories:** 9 (Stories 2.1-2.9)  
**Estimated Total Effort:** 84-102 hours (2-3 weeks for single developer)  
**Status:** New - Ready for implementation

**Sequencing Strategy:**
1. Foundation (Stories 2.1-2.2): 18-22 hours - MQTT listener + database
2. Analysis Engine (Stories 2.3-2.4): 22-26 hours - Matching + suggestions
3. Integration (Story 2.5): 6-8 hours - Merge with pattern automation
4. Dashboard (Stories 2.6-2.7): 20-24 hours - API + UI
5. Polish (Stories 2.8-2.9): 18-22 hours - Fallback + testing

**Critical Path:** Stories 2.1 → 2.2 → 2.3 → 2.4 → 2.5 → 2.6 → 2.7

**Parallel Development:** Frontend (2.7) can start after backend API (2.6) is complete

---

### 6.3 Combined System Summary

**Total Stories:** 27 (18 pattern + 9 device intelligence)  
**Total Estimated Effort:** 244-294 hours (6-8 weeks total)  
**Phased Approach:** 
- Phase 1 (Epic-AI-1): Pattern Automation - 4-5 weeks
- Phase 2 (Epic-AI-2): Device Intelligence - 2-3 weeks
**Parallel Development:** Yes (frontend + backend after Story 1.2)

**Sequencing Strategy:**
1. Foundation (Stories 1.1-1.2): 10-14 hours
2. Pattern Detection (Stories 1.3-1.6): 34-42 hours
3. LLM & Suggestions (Stories 1.7-1.9): 24-30 hours
4. Backend API (Stories 1.10-1.12): 24-30 hours
5. Frontend (Stories 1.13-1.17): 50-60 hours
6. Testing & Docs (Story 1.18): 12-14 hours

**Critical Path:** Stories 1.1 → 1.2 → 1.3 → 1.4 → 1.7 → 1.8 → 1.9 → 1.10 → 1.14

---

## 7. Implementation Guide (Practical Examples)

### 7.1 Simple Pattern Detection Code Examples

**Keep It Simple Principle:** Use simplest approach that works. No over-engineering.

#### **Example 1: Time-of-Day Clustering (Story 1.4)**

```python
import pandas as pd
from sklearn.cluster import KMeans
from datetime import datetime

def detect_time_of_day_patterns(events: pd.DataFrame) -> list:
    """
    Simple KMeans clustering to find consistent usage times.
    
    Input: events DataFrame with columns [device_id, timestamp, state]
    Output: List of patterns with confidence scores
    """
    
    # 1. Feature engineering (keep simple!)
    events['hour'] = events['timestamp'].dt.hour
    events['minute'] = events['timestamp'].dt.minute
    events['time_decimal'] = events['hour'] + events['minute'] / 60
    
    patterns = []
    
    # 2. Analyze each device separately
    for device_id in events['device_id'].unique():
        device_events = events[events['device_id'] == device_id]
        
        # Need minimum data
        if len(device_events) < 5:
            continue
        
        # 3. Cluster time patterns (simple KMeans)
        times = device_events[['time_decimal']].values
        kmeans = KMeans(n_clusters=min(3, len(times)), random_state=42)
        labels = kmeans.fit_predict(times)
        
        # 4. Find consistent clusters (confidence = size / total)
        for cluster_id in range(kmeans.n_clusters):
            cluster_times = times[labels == cluster_id]
            
            if len(cluster_times) >= 3:  # Minimum 3 occurrences
                avg_time = cluster_times.mean()
                confidence = len(cluster_times) / len(times)
                
                if confidence > 0.7:  # Only high confidence
                    patterns.append({
                        'device_id': device_id,
                        'pattern_type': 'time_of_day',
                        'hour': int(avg_time),
                        'minute': int((avg_time % 1) * 60),
                        'occurrences': len(cluster_times),
                        'confidence': confidence
                    })
    
    return patterns

# That's it! ~40 lines, no complexity.
```

#### **Example 2: Device Co-Occurrence (Story 1.5)**

```python
from itertools import combinations
from collections import defaultdict

def detect_co_occurrence_patterns(events: pd.DataFrame, window_minutes=5) -> list:
    """
    Find devices used together within time window.
    Simple approach: sliding window + counting.
    """
    
    # 1. Sort by time
    events = events.sort_values('timestamp')
    
    # 2. Find co-occurrences
    co_occurrences = defaultdict(int)
    
    for i, event in events.iterrows():
        # Look ahead within window
        window_end = event['timestamp'] + pd.Timedelta(minutes=window_minutes)
        nearby = events[
            (events['timestamp'] > event['timestamp']) &
            (events['timestamp'] <= window_end)
        ]
        
        # Count co-occurrences
        for _, nearby_event in nearby.iterrows():
            if nearby_event['device_id'] != event['device_id']:
                # Create sorted pair (avoid duplicates)
                pair = tuple(sorted([event['device_id'], nearby_event['device_id']]))
                co_occurrences[pair] += 1
    
    # 3. Filter for significant patterns
    patterns = []
    total_events = len(events)
    
    for (device1, device2), count in co_occurrences.items():
        confidence = count / total_events
        
        if count >= 5 and confidence > 0.7:  # Thresholds
            patterns.append({
                'pattern_type': 'co_occurrence',
                'device1': device1,
                'device2': device2,
                'occurrences': count,
                'confidence': confidence
            })
    
    return patterns

# ~35 lines. Simple and effective.
```

#### **Example 3: Anomaly Detection (Story 1.6)**

```python
from sklearn.ensemble import IsolationForest

def detect_automation_opportunities(events: pd.DataFrame) -> list:
    """
    Find repeated manual interventions = automation opportunities.
    Use Isolation Forest to find "too regular" patterns.
    """
    
    # 1. Feature engineering
    events['hour'] = events['timestamp'].dt.hour
    events['day_of_week'] = events['timestamp'].dt.dayofweek
    
    patterns = []
    
    # 2. Analyze each device
    for device_id in events['device_id'].unique():
        device_events = events[events['device_id'] == device_id]
        
        if len(device_events) < 10:
            continue
        
        # 3. Create features
        features = device_events[['hour', 'day_of_week']].values
        
        # 4. Isolation Forest (inverted - find regular patterns, not anomalies)
        iso_forest = IsolationForest(contamination=0.1, random_state=42)
        scores = iso_forest.fit_predict(features)
        
        # 5. Regular patterns (NOT anomalies) = automation candidates
        regular = device_events[scores == 1]  # Inliers
        
        # Group by hour
        for hour in regular['hour'].unique():
            hour_events = regular[regular['hour'] == hour]
            
            if len(hour_events) >= 3:
                patterns.append({
                    'device_id': device_id,
                    'pattern_type': 'anomaly_opportunity',
                    'hour': hour,
                    'occurrences': len(hour_events),
                    'confidence': len(hour_events) / len(device_events)
                })
    
    return patterns

# ~40 lines. Isolation Forest = pattern detector.
```

---

### 7.2 Simple LLM Prompt Template (Story 1.7)

**Keep Prompts Simple - Don't Over-Engineer:**

```python
SIMPLE_AUTOMATION_PROMPT = """
You are a home automation expert. Create a Home Assistant automation based on this pattern.

PATTERN DETECTED:
- Device: {device_id}
- Pattern: Turns on at {hour}:{minute:02d} consistently
- Occurrences: {occurrences} times in last 30 days
- Confidence: {confidence:.0%}

OUTPUT (valid Home Assistant YAML):
alias: "AI Suggested: [descriptive name]"
trigger:
  - platform: time
    at: "{hour:02d}:{minute:02d}:00"
action:
  - service: [appropriate service]
    target:
      entity_id: {device_id}

Explain why this automation makes sense in 1-2 sentences.
"""

# That's it! No complex prompt engineering needed for MVP.
```

---

### 7.3 Data Schemas (Simple SQLite)

**Database Schema - Keep It Minimal:**

```sql
-- patterns table
CREATE TABLE patterns (
    id INTEGER PRIMARY KEY,
    pattern_type TEXT,          -- 'time_of_day', 'co_occurrence', 'anomaly'
    device_id TEXT,
    metadata JSON,              -- Pattern-specific data
    confidence REAL,
    occurrences INTEGER,
    created_at TIMESTAMP,
    
    INDEX idx_device (device_id),
    INDEX idx_type (pattern_type)
);

-- suggestions table
CREATE TABLE suggestions (
    id INTEGER PRIMARY KEY,
    pattern_id INTEGER,
    title TEXT,
    description TEXT,
    automation_yaml TEXT,       -- HA automation YAML
    status TEXT,                -- 'pending', 'approved', 'deployed', 'rejected'
    confidence REAL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    deployed_at TIMESTAMP,
    ha_automation_id TEXT,      -- HA's ID after deployment
    
    FOREIGN KEY (pattern_id) REFERENCES patterns(id)
);

-- user_feedback table
CREATE TABLE user_feedback (
    id INTEGER PRIMARY KEY,
    suggestion_id INTEGER,
    action TEXT,                -- 'approved', 'rejected', 'modified'
    feedback_text TEXT,         -- User's comments (optional)
    created_at TIMESTAMP,
    
    FOREIGN KEY (suggestion_id) REFERENCES suggestions(id)
);

-- No complex joins needed. Keep it simple.
```

---

### 7.4 API Endpoint Specifications (Story 1.10-1.11)

**Simple REST API - No Over-Engineering:**

```python
# GET /api/suggestions
# Query params: status, min_confidence, limit, offset
Response: {
    "suggestions": [
        {
            "id": 1,
            "title": "Morning Bedroom Lights",
            "description": "Turn on bedroom lights at 7 AM on weekdays",
            "confidence": 0.85,
            "status": "pending",
            "created_at": "2025-10-15T03:05:00Z"
        }
    ],
    "total": 8,
    "page": 1
}

# GET /api/suggestions/{id}
Response: {
    "id": 1,
    "title": "Morning Bedroom Lights",
    "pattern": {
        "type": "time_of_day",
        "hour": 7,
        "minute": 0,
        "occurrences": 42,
        "confidence": 0.93
    },
    "automation_yaml": "alias: ...\ntrigger: ...",
    "status": "pending"
}

# PATCH /api/suggestions/{id}
Body: {"status": "approved"}
Response: {"success": true, "deployed_automation_id": "automation.ai_morning_lights"}

# POST /api/deploy/{suggestion_id}
# Deploys to Home Assistant
Response: {"success": true, "ha_automation_id": "automation.1234"}
```

---

### 7.5 MQTT Message Examples (Story 1.12)

**Simple MQTT Messages - No Complex Schemas:**

```json
// Topic: ha-ai/events/suggestion/generated
{
  "event_type": "suggestions_ready",
  "count": 8,
  "timestamp": "2025-10-15T03:10:00Z"
}

// Topic: ha-ai/commands/automation/test
{
  "automation_id": "test_123",
  "device_id": "light.bedroom",
  "action": "turn_on"
}

// Topic: ha-ai/responses/automation/executed
{
  "automation_id": "morning_lights",
  "status": "success",
  "execution_time_ms": 234,
  "timestamp": "2025-10-15T07:00:01Z"
}
```

---

### 7.6 Key Implementation Principles (From Context7 KB)

**MVP-First Principles:**

1. ✅ **Start Simple** - Use simplest algorithm that works (KMeans before DBSCAN)
2. ✅ **Iterate Based on Data** - Don't optimize prematurely
3. ✅ **Measure Everything** - Log pattern counts, confidence scores, execution times
4. ✅ **Fail Fast** - Quick validation, discard low-confidence patterns early
5. ✅ **User Feedback Loop** - Track approval/rejection rates to improve

**Anti-Patterns to Avoid:**

1. ❌ **Over-Engineering** - Don't build complex hierarchies in Phase 1
2. ❌ **Premature Optimization** - Don't optimize before measuring
3. ❌ **Feature Creep** - Resist adding "just one more pattern type"
4. ❌ **Complex Prompt Engineering** - Simple prompts work for MVP
5. ❌ **Heavy Dependencies** - Avoid Prophet, deep learning in Phase 1

**Testing Strategy:**

```python
# Simple validation approach
def validate_pattern(pattern):
    """3 checks, that's it."""
    return (
        pattern['occurrences'] >= 3 and
        pattern['confidence'] > 0.7 and
        pattern['device_id'] in known_devices
    )

# Don't overthink it.
```

---

### 7.7 Reference Architecture Diagram

**Simple Data Flow (No Complex Orchestration):**

```
┌──────────────┐
│  Data API    │  (existing)
│  Port 8006   │
└──────┬───────┘
       │ HTTP GET /api/events?start=-30d
       │
┌──────▼───────────────────────────────────┐
│  Daily Batch Job (3 AM)                  │
│  ┌──────────────────────────────────┐    │
│  │ 1. Fetch data (pandas DataFrame) │    │
│  │ 2. Run 3 pattern detectors       │    │
│  │ 3. Store patterns (SQLite)       │    │
│  │ 4. Call OpenAI (top 5-10)        │    │
│  │ 5. Store suggestions (SQLite)    │    │
│  │ 6. Publish MQTT (done!)          │    │
│  └──────────────────────────────────┘    │
│  Time: 5-10 minutes                      │
└──────────────────────────────────────────┘
       │
       │ MQTT: ha-ai/status/analysis_complete
       │
┌──────▼───────┐
│  Frontend    │  User browses suggestions
│  Port 3002   │  Clicks "Approve"
└──────┬───────┘
       │
       │ POST /api/deploy/{id}
       │
┌──────▼──────────┐
│  AI Service     │  Converts to HA YAML
│  Port 8011      │  POST to HA API
└──────┬──────────┘
       │
       │ POST http://ha:8123/api/config/automation/config
       │
┌──────▼──────────┐
│  Home Assistant │  Automation now runs!
│  Port 8123      │
└─────────────────┘
```

**Total Complexity:** LOW  
**Moving Parts:** 5 services  
**Dependencies:** Minimal

---

### 7.8 Practical Development Tips

#### **For Backend Developers (Stories 1.2-1.12):**

**Start Here:**
1. Copy `services/data-api/` structure (proven pattern)
2. Use `shared/logging_config.py` (already exists)
3. Follow FastAPI patterns from `admin-api/src/main.py`
4. SQLite example in `services/sports-data/` (webhooks.db)

**Don't Reinvent:**
- ✅ Copy existing Docker patterns
- ✅ Reuse existing error handling
- ✅ Use existing health check format
- ✅ Follow existing logging patterns

#### **For Frontend Developers (Stories 1.13-1.17):**

**Start Here:**
1. Copy `services/health-dashboard/` structure
2. Copy `tailwind.config.js` exactly
3. Copy tab navigation from `Dashboard.tsx`
4. Copy modal pattern from `ServiceDetailsModal.tsx`
5. Copy hooks pattern from `useHealth.ts`

**Don't Reinvent:**
- ✅ Reuse SkeletonCard, ErrorBoundary, AlertBanner
- ✅ Copy status color helpers
- ✅ Use same dark mode pattern
- ✅ Follow same responsive breakpoints

---

### 7.9 Quick Reference: Key Files to Copy/Reference

| What You're Building | Reference This File | Why |
|---------------------|-------------------|-----|
| **FastAPI Service** | `services/admin-api/src/main.py` | Proven FastAPI setup |
| **SQLite Models** | `services/data-api/src/models/device.py` | SQLAlchemy patterns |
| **Docker Setup** | `services/data-api/Dockerfile` | Multi-stage build |
| **Tab Component** | `health-dashboard/src/components/tabs/OverviewTab.tsx` | Tab structure |
| **Modal Pattern** | `health-dashboard/src/components/ServiceDetailsModal.tsx` | Modal UX |
| **Custom Hook** | `health-dashboard/src/hooks/useHealth.ts` | Data fetching |
| **Card Component** | `health-dashboard/src/components/CoreSystemCard.tsx` | Card UI |

**Time Saved:** 20-30 hours by copying proven patterns

---

### 7.10 Common Pitfalls to Avoid

**Backend:**
1. ❌ Don't query InfluxDB directly (use Data API)
2. ❌ Don't block the main thread (use async/background jobs)
3. ❌ Don't store patterns in InfluxDB (use SQLite)
4. ❌ Don't over-complicate pattern detection (simple is better)
5. ❌ Don't send raw data to LLM (anonymize first)

**Frontend:**
1. ❌ Don't create new design system (copy health-dashboard)
2. ❌ Don't use different UI patterns (consistency matters)
3. ❌ Don't skip loading states (use skeletons)
4. ❌ Don't forget error boundaries (graceful failures)
5. ❌ Don't ignore mobile (44px touch targets)

**ML/AI:**
1. ❌ Don't use Prophet in Phase 1 (too heavy)
2. ❌ Don't implement complex hierarchies (Phase 1 = simple)
3. ❌ Don't tune hyperparameters excessively (defaults work)
4. ❌ Don't train models (use pre-built scikit-learn algorithms)
5. ❌ Don't cache LLM responses forever (7 day TTL max)

---

### 7.11 Success Metrics (Measure These)

**Phase 1 MVP Success:**

```python
# Track in SQLite and log these metrics
metrics = {
    'patterns_detected_per_run': 20-50,      # Target range
    'suggestions_generated_per_run': 5-10,   # Quality over quantity
    'user_approval_rate': '>60%',            # High acceptance
    'analysis_duration_minutes': '<10',      # Performance target
    'api_cost_monthly': '<$10',              # Budget constraint
    'memory_peak_mb': '<1000',               # Resource constraint
    'false_positive_rate': '<30%',           # Pattern quality
}
```

**How to Measure:**
1. Log all metrics during batch job
2. Store in SQLite for trending
3. Display in Insights Dashboard (Story 1.17)
4. Review weekly, adjust thresholds

---

## 8. Appendices

### 8.1 Context7 KB Research Documents

- `docs/kb/context7-cache/ai-ml-recommendation-systems-best-practices.md`
- `docs/kb/context7-cache/edge-ml-deployment-home-assistant.md`
- `docs/kb/context7-cache/multi-scale-temporal-pattern-detection.md`
- `docs/kb/context7-cache/huggingface-vs-traditional-ml-for-pattern-detection.md`

### 8.2 Architecture Review

- **Reviewed by:** Winston (Architect)
- **Date:** 2025-10-15
- **Verdict:** ✅ Approved with Phase 1 MVP simplifications
- **Key Recommendations:** scikit-learn only, 3 pattern types, OpenAI API, no Prophet
- **Timeline:** 2-4 weeks realistic for MVP

### 8.3 Future Phases (Post-MVP)

**Phase 2 (Month 3-4):**
- Add weekly patterns (statsmodels)
- Day-of-week awareness
- 10-20 suggestions per week
- Pattern trend tracking

**Phase 3 (Month 6+):**
- Prophet for seasonal patterns (if 6+ months data + user value proven)
- Composite patterns ("Monday in Summer")
- Local LLM option (Ollama, privacy-focused)
- Advanced categorization

**Phase 4 (Year 2):**
- Multi-home aggregation (if applicable)
- Federated learning (privacy-preserving)
- Deep learning (only if simple ML insufficient)

---

**End of PRD**
