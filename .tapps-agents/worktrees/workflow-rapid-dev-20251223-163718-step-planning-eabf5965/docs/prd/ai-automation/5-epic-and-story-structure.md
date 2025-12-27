# 5. Epic and Story Structure

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
**I want** to add MQTT broker and configure infrastructure  
**so that** AI service can communicate with Home Assistant asynchronously

**Acceptance Criteria:**
1. ✅ Mosquitto container starts successfully
2. ✅ MQTT broker accessible on port 1883 (internal)
3. ✅ Topics ha-ai/* can be published/subscribed
4. ✅ Home Assistant can connect to MQTT broker
5. ✅ Resource usage: <20MB RAM, <1% CPU

**Estimated Effort:** 4-6 hours

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
