# AI Automation Service: Technical White Paper

**Version:** 2.4  
**Date:** November 2025  
**Status:** Production Ready  
**Service:** AI-Powered Home Assistant Automation Discovery and Recommendation System

---

## Executive Summary

The AI Automation Service represents a breakthrough in intelligent home automation, combining advanced machine learning, natural language processing, and real-time data analysis to automatically discover, suggest, and deploy home automation opportunities. This service transforms raw device event data into actionable automation suggestions through a sophisticated multi-stage pipeline that leverages state-of-the-art AI models, pattern recognition algorithms, and device intelligence systems.

**Key Innovation:** The service operates as a unified daily batch job that analyzes historical usage patterns, discovers device capabilities, detects multi-hop device synergies, and generates human-readable automation suggestions—all while maintaining cost efficiency through optimized model selection and resource management.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Data Sources and Architecture](#data-sources-and-architecture)
3. [AI Models and Machine Learning](#ai-models-and-machine-learning)
4. [Data Flow and Processing Pipeline](#data-flow-and-processing-pipeline)
5. [Technical Architecture](#technical-architecture)
6. [Performance and Scalability](#performance-and-scalability)
7. [Award-Winning Combination](#award-winning-combination)
8. [Conclusion](#conclusion)

---

## System Overview

### Purpose and Mission

The AI Automation Service addresses a fundamental challenge in smart home automation: **discovering automation opportunities from actual usage patterns rather than requiring manual configuration**. The service:

- **Analyzes** historical device usage to detect behavioral patterns
- **Discovers** device capabilities automatically (6,000+ Zigbee models)
- **Detects** multi-hop device relationships and synergies
- **Generates** human-readable automation suggestions
- **Deploys** validated automations directly to Home Assistant

### Deployment Context

**Target Environment:**
- Single-home Home Assistant deployment
- Intel NUC hardware (i3/i5, 8-16GB RAM)
- 50-100 devices typical
- CPU-only (no GPU acceleration required)
- Resource-efficient design for edge computing

**Technology Stack:**
- **Framework:** FastAPI 0.115.x (Python 3.12+)
- **Database:** SQLite (27 tables, 365-day retention)
- **Port:** 8018 (internal), 8024 (external)
- **Container:** Docker with persistent model volumes

---

## Data Sources and Architecture

### Primary Data Sources

#### 1. InfluxDB Time-Series Database (PRIMARY DATA SOURCE)

**Purpose:** Historical event storage and querying - THE PRIMARY DATA SOURCE for all pattern analysis  
**Location:** Port 8086  
**Bucket:** `home_assistant_events`  
**Retention:** 365 days  
**Access Methods:** Dual-path architecture (Data API + Direct InfluxDB client)

**Data Structure:**
```python
# Event schema (normalized from Home Assistant, stored in InfluxDB)
{
    "event_type": "state_changed",
    "entity_id": "light.office",
    "state": "on",
    "timestamp": "2025-11-15T07:00:00Z",
    "domain": "light",
    "device_id": "device_123",
    "area_id": "office",
    "attributes": {
        "brightness": 255,
        "color_temp": 370,
        "device_class": "light"
    }
}
```

**Access Architecture:**

**Primary Path (Data API):**
- **Route:** InfluxDB → Data API Service (Port 8006) → AI Automation Service
- **Method:** HTTP REST API calls to Data API
- **Advantages:** Pre-processed, normalized, tested, reliable
- **Usage:** Main event fetching for pattern detection (Phase 2)

**Fallback Path (Direct InfluxDB):**
- **Route:** InfluxDB → AI Automation Service (direct)
- **Method:** Direct Flux queries via `InfluxDBEventClient`
- **Advantages:** Lower latency, direct access, specialized queries
- **Usage:** Fallback if Data API unavailable, weather data queries, attribute queries

**Query Patterns:**
- **Time Range:** 7-30 days lookback (configurable, falls back to 24 hours if no data)
- **Event Types:** `state_changed` (primary), `event` (secondary)
- **Filtering:** Domain-based (light, switch, sensor, etc.), entity_id, device_id
- **Volume:** 10,000-100,000 events per query (typical)
- **Flux Queries:** Direct Flux language queries for specialized use cases

**Direct InfluxDB Usage Examples:**

1. **Weather Data Queries:**
   ```flux
   from(bucket: "home_assistant_events")
     |> range(start: -7d)
     |> filter(fn: (r) => r["domain"] == "weather" or 
               (r["domain"] == "sensor" and strings.containsStr(v: r["entity_id"], substr: "weather")))
     |> filter(fn: (r) => r["_field"] == "state")
   ```

2. **Entity Attribute Queries:**
   - Queries `attr_brightness`, `attr_color_temp`, `attr_led_effect` fields
   - Detects feature usage patterns (Phase 4)
   - Checks which device capabilities are actually used

3. **Event Injection (Testing):**
   - Direct writes to InfluxDB for synthetic event generation
   - Testing pattern detection algorithms

**Key Features:**
- **Dual-Path Access:** Data API (primary) + Direct InfluxDB (fallback/specialized)
- **Incremental Processing:** Pattern aggregate buckets for optimized queries
- **Real-time Capability:** Direct queries for low-latency access
- **Flux Query Support:** Full Flux language support for complex queries
- **Attribute-Level Queries:** Direct access to attribute fields (brightness, color_temp, etc.)

#### 2. Home Assistant Integration

**Purpose:** Device metadata, entity discovery, automation deployment  
**Connection:** HTTP REST API + WebSocket (optional)  
**Authentication:** Long-lived access tokens

**Data Retrieved:**
- **Entity Registry:** All entities (lights, switches, sensors, etc.)
- **Device Registry:** Device metadata (manufacturer, model, area)
- **State History:** Current and historical device states
- **Automation Management:** Deploy, enable, disable, trigger automations

**Integration Points:**
- Entity extraction for natural language queries
- Device capability validation
- Automation YAML deployment
- Real-time state monitoring

#### 3. Device Intelligence Service

**Purpose:** Universal device capability discovery  
**Location:** Port 8028  
**Source:** Zigbee2MQTT bridge (MQTT topic: `zigbee2mqtt/bridge/devices`)

**Capability Discovery:**
- **Coverage:** 6,000+ Zigbee device models
- **Manufacturers:** Inovelli, Aqara, IKEA, Xiaomi, Sonoff, Tuya, Philips, SmartThings, and 100+ more
- **Format:** Standardized `exposes` JSON structure
- **Update Frequency:** Real-time (when devices are paired)

**Example Capability Data:**
```json
{
    "device_model": "VZM31-SN",
    "manufacturer": "Inovelli",
    "capabilities": {
        "led_notifications": true,
        "smart_bulb_mode": true,
        "auto_off_timer": true,
        "power_monitoring": true,
        "scene_control": true
    }
}
```

**Storage:**
- SQLite database (`device_capabilities` table)
- Automatic parsing and normalization
- Feature utilization tracking

#### 4. MQTT Broker (Home Assistant)

**Purpose:** Real-time capability updates and notifications  
**Topics:**
- `zigbee2mqtt/bridge/devices` - Device capability discovery
- `homeassistant/automation/+` - Automation state changes
- `ai-automation/suggestions/new` - Suggestion notifications

**MQTT Client Features:**
- Automatic reconnection with retry logic
- Graceful degradation (service continues without MQTT)
- Read-only subscriptions (security best practice)

#### 5. Automation-Miner Service

**Purpose:** Home Assistant blueprint corpus and community automation patterns  
**Location:** Port 8029  
**Source:** Home Assistant Community Forum (Blueprints Exchange)

**Blueprint Corpus:**
- **Content:** Community-validated Home Assistant automation blueprints
- **Storage:** SQLite database with blueprint metadata
- **Metadata:** Blueprint variables, device requirements, use cases, quality scores
- **Update Frequency:** Periodic crawls from Home Assistant Discourse forum

**Blueprint Structure:**
```yaml
blueprint:
  name: "Motion-Activated Light"
  description: "Turn on lights when motion detected"
  domain: automation
  input:
    motion_sensor:
      selector:
        entity:
          domain: binary_sensor
          device_class: motion
    target_light:
      selector:
        entity:
          domain: light
```

**Integration:**
- Blueprint matching for YAML generation (reliable, tested automations)
- Pattern validation against community patterns
- Quality scoring based on community feedback

**Data Retrieved:**
- Blueprint YAML templates
- Blueprint metadata (variables, device requirements)
- Quality scores and community ratings
- Use case classifications

#### 6. External Context Services

**Weather Data:**
- Source: Home Assistant weather entities
- Storage: InfluxDB (normalized events)
- Usage: Weather-based automation opportunities

**Energy Data:**
- Source: Smart meter entities, electricity pricing service
- Storage: InfluxDB
- Usage: Cost optimization automations

**Calendar Data:**
- Source: Home Assistant calendar integration
- Usage: Time-based pattern validation

### Data Architecture Principles

1. **InfluxDB as Primary Data Source:** All historical event data originates from InfluxDB; the service uses dual-path access (Data API primary, direct InfluxDB fallback/specialized queries)
2. **Single Source of Truth:** InfluxDB for time-series events, SQLite for metadata
3. **Normalization:** All events normalized to consistent schema (via Data API or direct queries)
4. **Incremental Processing:** Pattern aggregates for faster queries
5. **Real-time + Batch:** MQTT for real-time updates, batch for analysis
6. **Graceful Degradation:** Service continues if external services unavailable (falls back to direct InfluxDB queries)
7. **Dual-Path Access:** Data API provides abstraction and reliability; direct InfluxDB provides specialized queries (weather, attributes) and fallback capability

---

## AI Models and Machine Learning

### Model Architecture Overview

The service employs a **distributed microservices architecture** with containerized AI models, enabling optimal resource management and scalability:

```
┌─────────────────────────────────────────────────────────────┐
│              AI Services Layer (Containerized)              │
├─────────────────────────────────────────────────────────────┤
│  OpenVINO Service (Port 8019)                              │
│  ├─ all-MiniLM-L6-v2 (INT8) - Embeddings (384-dim)        │
│  ├─ bge-reranker-base (INT8) - Re-ranking                  │
│  └─ flan-t5-small (INT8) - Classification                  │
│                                                             │
│  ML Service (Port 8020)                                    │
│  ├─ K-Means Clustering (scikit-learn)                     │
│  ├─ Isolation Forest (Anomaly Detection)                  │
│  └─ Statistical Analysis (scipy)                          │
│                                                             │
│  NER Service (Port 8031)                                   │
│  └─ dslim/bert-base-NER - Named Entity Recognition        │
│                                                             │
│  OpenAI Service (Port 8020)                               │
│  ├─ GPT-5.1 - High-quality generation (50% cost savings)  │
│  └─ GPT-5.1-mini - Fast classification (80% cost savings) │
└─────────────────────────────────────────────────────────────┘
```

### Core AI Models

#### 1. OpenAI GPT-5.1 / GPT-5.1-mini

**Primary Use Cases:**
- **Automation Description Generation:** Convert patterns to human-readable descriptions
- **YAML Generation:** Generate valid Home Assistant automation YAML
- **Natural Language Understanding:** Parse user queries in Ask AI interface
- **Entity Extraction:** Fallback when NER service unavailable

**Model Selection Strategy:**
- **GPT-5.1:** High-quality generation (suggestions, YAML) - 50% cost savings vs GPT-4o
- **GPT-5.1-mini:** Fast classification, extraction - 80% cost savings vs GPT-4o

**Token Usage:**
- **Per Run:** 1,000-5,000 tokens (daily batch job)
- **Cost per Run:** $0.001-0.005
- **Annual Cost:** ~$0.50 (365 runs)

**Prompt Engineering:**
- Structured prompts with pattern context
- Few-shot examples for YAML generation
- Safety validation rules embedded in prompts
- Temperature: 0.7 (balanced creativity + consistency)

#### 2. OpenVINO Optimized Models

**all-MiniLM-L6-v2 (Embeddings):**
- **Purpose:** Semantic similarity, RAG knowledge base, device embeddings
- **Dimensions:** 384
- **Optimization:** INT8 quantization (20MB vs 80MB standard)
- **Performance:** <50ms per batch (CPU-only)

**bge-reranker-base (Re-ranking):**
- **Purpose:** Re-rank pattern candidates, improve suggestion quality
- **Optimization:** INT8 quantization
- **Usage:** Post-processing for top-K retrieval

**flan-t5-small (Classification):**
- **Purpose:** Pattern categorization, automation type classification
- **Optimization:** INT8 quantization
- **Performance:** <30ms per classification

**Total Model Size:** 380MB (INT8) or 1.5GB (standard)

#### 3. Named Entity Recognition (NER)

**Model:** dslim/bert-base-NER  
**Service:** NER Service (Port 8031)  
**Purpose:** Extract device names, locations, actions from natural language

**Usage:**
- Ask AI query processing
- Natural language automation generation
- Entity extraction from user queries

**Fallback:** spaCy `en_core_web_sm` (if NER service unavailable)

#### 4. Machine Learning Algorithms (scikit-learn)

**K-Means Clustering:**
- **Purpose:** Group similar usage patterns
- **Usage:** Time-of-day pattern clustering, device grouping
- **Configuration:** Adaptive cluster count based on data

**Isolation Forest (Anomaly Detection):**
- **Purpose:** Detect unusual usage patterns
- **Contamination:** 0.1 (10% expected anomalies)
- **Usage:** Anomaly-based automation suggestions

**Statistical Analysis (scipy):**
- **Purpose:** Pattern confidence calculation, statistical validation
- **Methods:** Chi-square tests, correlation analysis, time-series decomposition

#### 5. Advanced ML Components

**Graph Neural Networks (PyTorch Geometric):**
- **Purpose:** Multi-hop device relationship detection
- **Usage:** 3-level and 4-level synergy chains
- **Model:** GNN-based synergy detector

**TabPFN (Tabular Prior-data Fitted Networks):**
- **Purpose:** Fast correlation prediction (100-1000x faster than traditional ML)
- **Usage:** Device correlation analysis
- **Performance:** O(1) inference time

**River (Streaming Statistics):**
- **Purpose:** Real-time statistical updates
- **Usage:** Incremental pattern detection
- **Performance:** O(1) per-event updates

**FAISS (Vector Similarity Search):**
- **Purpose:** Fast similarity search for embeddings
- **Usage:** RAG knowledge base retrieval, device similarity matching
- **Index Type:** Flat index (CPU-only, single-home optimized)

### Model Management

**Service-Based Architecture:**
- Models run in separate containers for resource isolation
- Lazy loading (models load on first use)
- Persistent Docker volumes for model caching
- Automatic fallback if services unavailable

**Optimization Strategy:**
- INT8 quantization for 4x size reduction
- CPU-only deployment (no GPU required)
- Batch processing for efficiency
- Model caching to reduce load times

### Model Training and Retraining

The service includes several models that are trained or retrained to adapt to user behavior and improve accuracy over time. This section documents which models get trained, when training occurs, and why training is necessary.

#### 1. GNN Synergy Detector (Graph Neural Network)

**Model Type:** PyTorch Geometric GNN (Graph Neural Network)  
**Purpose:** Learn multi-hop device relationships for synergy detection  
**Training Method:** Supervised learning from known synergies

**When Training Occurs:**
- **Manual Trigger:** Via API endpoint `POST /api/admin/training/gnn/trigger`
- **Standalone Script:** `scripts/train_gnn_synergy.py` (for scheduled retraining)
- **Frequency:** On-demand (not automatic in daily batch job)
- **Recommended:** Monthly or when significant new synergies are validated

**Training Data:**
- **Positive Examples:** Validated synergies from `discovered_synergies` database table
- **Negative Examples:** Automatically generated negative pairs (non-synergy device pairs)
- **Cold Start:** Synthetic synergies generated from device graph if no validated synergies exist
- **Graph Structure:** Device entities with event history for graph construction

**Training Process:**
1. Load entities from Data API (up to 10,000 entities)
2. Load known synergies from database (or generate synthetic if none exist)
3. Build device graph with nodes (entities) and edges (relationships)
4. Create training pairs: positive (synergy pairs) + negative (random non-synergy pairs)
5. Split data: 80% training, 20% validation
6. Train GNN model with early stopping (patience-based)
7. Save model state and metadata to persistent storage

**Why Training is Needed:**
- Learns device relationship patterns specific to user's home
- Improves detection of 3-level and 4-level synergy chains
- Adapts to new devices and usage patterns over time
- Reduces false positives in synergy detection

**Training Metrics:**
- Training/validation loss tracking
- Accuracy metrics (binary classification: synergy vs. non-synergy)
- Early stopping based on validation loss improvement
- Model saved with training date and statistics

**Configuration:**
- Default epochs: 30 (configurable)
- Learning rate: 0.001 (configurable)
- Hidden dimensions: 64 (configurable)
- Early stopping patience: 5 epochs
- Model path: Persistent Docker volume

#### 2. Clarification Confidence Calibrator

**Model Type:** Statistical calibration model (Platt scaling / Isotonic regression)  
**Purpose:** Calibrate raw confidence scores to accurate probabilities for clarification questions  
**Training Method:** Supervised learning from user feedback

**When Training Occurs:**
- **Automatic Retraining:** Weekly (default, configurable via `clarification_calibration_retrain_interval_days`)
- **Sample-Based Trigger:** When ≥50 new feedback samples accumulate since last retrain
- **Manual Trigger:** Via calibration retrainer API
- **Frequency:** Weekly (default) or monthly (configurable)

**Training Data:**
- **Source:** `clarification_confidence_feedback` database table
- **Features:**
  - Raw confidence scores (before calibration)
  - Actual user behavior (proceeded vs. skipped clarification)
  - Ambiguity counts (number of ambiguous entities)
  - Critical ambiguity flags
  - Clarification rounds and answer counts
- **Minimum Samples:** 10 samples required for training (configurable)

**Training Process:**
1. Check if retraining is needed (time-based or sample-based)
2. Load feedback records from database (up to 10,000 records)
3. Extract features: raw confidence, ambiguity counts, user outcomes
4. Train calibration model (Platt scaling or Isotonic regression)
5. Save calibrated model to persistent storage
6. Update calibration statistics

**Why Training is Needed:**
- Raw confidence scores may not reflect actual probability of needing clarification
- User behavior provides ground truth for calibration
- Reduces false positive clarification questions (improves UX)
- Improves confidence threshold accuracy over time

**Retraining Conditions:**
- **Time-Based:** Every 7 days (default, configurable)
- **Sample-Based:** ≥50 new feedback samples since last retrain
- **Manual:** On-demand via API

**Configuration:**
- Retrain interval: 7 days (default)
- Minimum samples: 10 (configurable)
- Minimum new samples: 50 (for sample-based retraining)
- Enabled by default: `clarification_calibration_enabled = True`

#### 3. Device Intelligence Service Models (External Service)

**Note:** These models are part of the separate Device Intelligence Service (Port 8028), not the AI Automation Service, but are documented here for completeness.

**Model Types:**
- **RandomForestClassifier:** Device failure prediction
- **IsolationForest:** Anomaly detection

**When Training Occurs:**
- **Manual API Trigger:** `POST /api/predictions/train` (Device Intelligence Service)
- **Scheduled:** Weekly/monthly via cron or systemd timer
- **Standalone Script:** `scripts/train_models.py`
- **Frequency:** Weekly (recommended) or monthly

**Training Data:**
- **Source:** Historical device metrics from InfluxDB
- **Time Range:** 180 days (default, configurable)
- **Minimum Samples:** 100 samples required (falls back to rule-based if insufficient)
- **Features:** Device metrics, usage patterns, error rates, connectivity data

**Why Training is Needed:**
- Predicts device failures before they occur
- Detects anomalies in device behavior
- Adapts to specific device models and usage patterns
- Improves accuracy with more historical data

**Training Process:**
1. Collect historical device data (180 days default)
2. Prepare features: device metrics, usage patterns, error rates
3. Split data: 80% training, 20% testing
4. Train RandomForestClassifier (failure prediction)
5. Train IsolationForest (anomaly detection)
6. Evaluate models and save to persistent storage

#### 4. Home Type Classifier (One-Time Training)

**Model Type:** RandomForest (scikit-learn)  
**Purpose:** Classify home types (apartment, house, etc.) from device inventory  
**Training Method:** Pre-trained on synthetic data before release

**When Training Occurs:**
- **One-Time:** Before service release (included in Docker image)
- **Not Retrained:** Model is static in production
- **Training Script:** `scripts/train_home_type_models.py` (development only)

**Training Data:**
- **Source:** Synthetic home profiles with data augmentation
- **Augmentation:** 3-5 variations per synthetic home
- **Features:** Device counts, room types, integration platforms, device classes

**Why Training is Needed:**
- Provides baseline home type classification
- Enables home-type-specific automation suggestions
- Pre-trained model ensures consistent behavior

**Note:** This model is not retrained in production. Future versions may support fine-tuning on real user data.

#### Training Infrastructure

**Database Tracking:**
- **`training_runs` Table:** Tracks all training jobs with:
  - Training type (gnn_synergy, soft_prompt, etc.)
  - Status (pending, running, completed, failed)
  - Start/finish timestamps
  - Training statistics (loss, accuracy, dataset size)
  - Error messages (if failed)

**API Endpoints:**
- `POST /api/admin/training/gnn/trigger` - Trigger GNN training
- `GET /api/admin/training/runs` - List training runs
- `GET /api/admin/training/runs/{id}` - Get training run details

**Monitoring:**
- Training run status tracked in database
- Logs include training progress and metrics
- Failed training runs include error messages
- Training statistics stored for analysis

**Best Practices:**
- **GNN Training:** Monthly or when 20+ new synergies validated
- **Calibration Retraining:** Weekly (automatic) or monthly (if low feedback volume)
- **Device Intelligence:** Weekly (recommended) for failure prediction accuracy
- **Resource Management:** Training runs in background, doesn't block daily analysis

---

## Data Flow and Processing Pipeline

### Unified Daily Batch Job (3 AM)

The service runs a comprehensive analysis pipeline every day at 3 AM (configurable via cron schedule). The pipeline consists of 7 phases:

#### Phase 1: Device Capability Update

**Duration:** 10-30 seconds  
**Purpose:** Discover and update device capabilities

**Process:**
1. Fetch device list from Device Intelligence Service
2. Query Zigbee2MQTT bridge via MQTT (if available)
3. Parse capability definitions from `exposes` JSON
4. Update `device_capabilities` table in SQLite
5. Track new devices and capability changes

**Output:**
- Updated capability registry
- Feature utilization baseline
- New device notifications

**Data Sources:**
- Device Intelligence Service (HTTP)
- MQTT broker (`zigbee2mqtt/bridge/devices`)
- SQLite database (existing capabilities)

#### Phase 2: Fetch Historical Events

**Duration:** 20-60 seconds  
**Purpose:** Retrieve event data for pattern analysis

**Process:**
1. **Primary Path:** Query Data API service (which queries InfluxDB internally)
2. **Fallback Path:** If Data API unavailable, query InfluxDB directly via `InfluxDBEventClient`
3. Time range: 7-30 days (configurable, falls back to 24 hours if no data)
4. Filter relevant entities (lights, switches, sensors, etc.)
5. Normalize event schema
6. Prepare DataFrame for analysis

**Data API Query (Primary):**
```python
# Via DataAPIClient.fetch_events()
# Internally queries InfluxDB and returns normalized events
events_df = await data_client.fetch_events(
    start_time=start_date,
    limit=100000
)
```

**Direct InfluxDB Query (Fallback):**
```flux
from(bucket: "home_assistant_events")
  |> range(start: -7d)
  |> filter(fn: (r) => r["_measurement"] == "home_assistant_events")
  |> filter(fn: (r) => r["_field"] == "context_id")
  |> filter(fn: (r) => r["event_type"] == "state_changed")
  |> sort(columns: ["_time"])
  |> limit(n: 100000)
```

**Output:**
- Pandas DataFrame with normalized events
- Event count statistics
- Data quality metrics

**Data Sources:**
- **Primary:** InfluxDB (via Data API service - Port 8006)
- **Fallback:** InfluxDB (direct - Port 8086)
- **Note:** All event data originates from InfluxDB; Data API provides a normalized abstraction layer

#### Phase 3: Pattern Detection

**Duration:** 30-90 seconds  
**Purpose:** Detect usage patterns from historical events

**Pattern Types:**

1. **Time-of-Day Patterns:**
   - Detects consistent activation times
   - Example: "Light turns on at 7:00 AM on weekdays"
   - Algorithm: Statistical analysis + clustering
   - Confidence: Based on frequency and consistency

2. **Co-Occurrence Patterns:**
   - Detects devices frequently used together
   - Example: "Motion sensor triggers light activation"
   - Algorithm: Correlation analysis + frequency counting
   - Confidence: Based on co-occurrence frequency

3. **Anomaly Patterns:**
   - Detects repeated manual interventions
   - Example: "User manually turns off light after automation"
   - Algorithm: Isolation Forest + statistical analysis
   - Confidence: Based on anomaly frequency

**Process:**
1. Initialize pattern detectors (TimeOfDay, CoOccurrence, Anomaly)
2. Run detectors in parallel on event DataFrame
3. Cross-validate patterns (remove duplicates, validate confidence)
4. Store patterns in SQLite (`patterns` table)
5. Generate pattern statistics

**Output:**
- List of detected patterns with confidence scores
- Pattern metadata (entity_id, time_range, frequency)
- Pattern validation results

**Data Flow:**
```
Events DataFrame
    ↓
[TimeOfDayDetector, CoOccurrenceDetector, AnomalyDetector]
    ↓
Pattern Cross-Validator
    ↓
Pattern Deduplicator
    ↓
SQLite (patterns table)
```

#### Phase 3c: Synergy Detection

**Duration:** 15-45 seconds  
**Purpose:** Discover multi-hop device relationships

**Synergy Types:**

1. **Device Pair Synergies (2-level):**
   - Direct device relationships
   - Example: Motion → Light
   - Algorithm: Frequency analysis + confidence scoring

2. **Weather Context Synergies:**
   - Weather-based automation opportunities
   - Example: "Close windows when rain detected"
   - Algorithm: Weather data correlation + device state analysis

3. **Energy Context Synergies:**
   - Cost optimization opportunities
   - Example: "Turn off devices during peak pricing"
   - Algorithm: Energy data correlation + pricing analysis

4. **Event Context Synergies:**
   - Entertainment/event-based automations
   - Example: "Dim lights when TV turns on"
   - Algorithm: Event correlation + temporal analysis

5. **Multi-Hop Chains:**
   - **3-level chains:** A → B → C (e.g., Door → Lock → Light)
   - **4-level chains:** A → B → C → D (e.g., Door → Lock → Alarm → Notification)
   - Algorithm: Graph traversal + GNN-based detection

**Process:**
1. Initialize synergy detectors (DevicePair, Weather, Energy, Event, MultiHop)
2. Run detectors in parallel
3. Generate device embeddings (OpenVINO all-MiniLM-L6-v2)
4. Calculate similarity scores
5. Apply priority-based ranking (impact + confidence + pattern validation)
6. Store synergies in SQLite (`discovered_synergies` table)

**Output:**
- List of synergies with priority scores
- Multi-hop chain relationships
- Synergy validation results

**Data Sources:**
- Event DataFrame (from Phase 2 - InfluxDB via Data API or direct)
- Weather data (InfluxDB - direct Flux queries)
- Energy data (InfluxDB - direct Flux queries)
- Device embeddings (OpenVINO service)

#### Phase 3d: Blueprint Opportunity Discovery (Epic AI-6)

**Duration:** 2-5 seconds  
**Purpose:** Discover blueprint opportunities from user device inventory

**Process:**
1. Fetch user device inventory (devices + entities from Data API)
2. Extract device types (domains) and integration platforms
3. Search automation-miner service for matching blueprints
4. Calculate fit scores based on device type compatibility and blueprint quality
5. Store discovered opportunities in SQLite (`blueprint_opportunities` table)

**Fit Score Calculation:**
- Device type compatibility (60%): Match between user devices and blueprint requirements
- Integration compatibility (20%): Platform/integration matching
- Blueprint quality (20%): Community rating and usage statistics

**Example Discovery:**
```python
User Devices: [light.office_light, binary_sensor.motion]
Device Types: ["light", "binary_sensor"]
Integrations: ["hue", "generic"]

Matching Blueprint: "Motion-Activated Light"
Fit Score: 0.85
Opportunity: "Turn on lights when motion detected"
```

**Output:**
- List of blueprint opportunities with fit scores
- Stored in `blueprint_opportunities` table
- Available for both 3 AM batch job and Ask AI queries

**Data Sources:**
- Device inventory (Data API Service)
- Automation-miner service (blueprint corpus)
- Blueprint metadata (quality scores, device requirements)

**Graceful Degradation:**
- If automation-miner service unavailable, returns empty list
- Daily analysis continues without blueprint discovery
- Logs warning but doesn't block execution

#### Phase 4: Feature Analysis

**Duration:** 10-30 seconds  
**Purpose:** Analyze device feature utilization

**Process:**
1. Load device capabilities from SQLite
2. Query event history for feature usage
3. Calculate utilization percentages
4. Identify underutilized features
5. Generate feature suggestions

**Example Analysis:**
```python
Device: VZM31-SN (Inovelli Dimmer)
Capabilities: [led_notifications, smart_bulb_mode, auto_off_timer, power_monitoring]
Usage: [0%, 100%, 0%, 0%]  # Only smart_bulb_mode used
Suggestion: "Enable LED notifications for visual feedback"
```

**Output:**
- Feature utilization statistics
- Underutilized feature list
- Feature suggestion candidates

**Data Sources:**
- Device capabilities (SQLite)
- Event history (InfluxDB, via Phase 2 - Data API or direct)
- Entity attributes (InfluxDB - direct queries for `attr_brightness`, `attr_color_temp`, etc.)

#### Phase 5: Description-Only Generation

**Duration:** 5-15 seconds  
**Purpose:** Generate human-readable automation descriptions

**Process:**
1. Combine pattern, feature, synergy, and blueprint opportunity suggestions
2. Validate patterns against blueprints (Epic AI-6):
   - Search for matching blueprints for each pattern
   - Calculate confidence boost for validated patterns
   - Add blueprint hints to high-confidence matches (≥0.8)
3. Apply preference-aware ranking (Epic AI-6):
   - Apply creativity level filtering (conservative/balanced/creative)
   - Apply blueprint preference weighting (low/medium/high)
   - Sort by adjusted confidence scores
   - Apply max_suggestions limit (user-configurable, default: 10)
4. Generate descriptions using OpenAI GPT-5.1-mini (with blueprint context if available)
5. Store as `status='draft'` with `automation_yaml=NULL`

**Prompt Template:**
```
Based on the following pattern:
- Entity: {entity_id}
- Pattern Type: {pattern_type}
- Confidence: {confidence}
- Frequency: {frequency}

Generate a human-readable automation description that explains:
1. What the automation does
2. Why it's useful
3. When it triggers
```

**Example Output:**
```
"Turn on the office light every weekday at 7:00 AM. This automation 
is based on your consistent morning routine and will help you start 
your day with proper lighting."
```

**Output:**
- List of suggestions (status='draft')
- Human-readable descriptions
- No YAML yet (generated after user approval)

**Data Sources:**
- Patterns (SQLite, from Phase 3)
- Features (SQLite, from Phase 4)
- Synergies (SQLite, from Phase 3c)
- Blueprint opportunities (SQLite, from Phase 3d - Epic AI-6)
- User preferences (SQLite, `suggestion_preferences` table - Epic AI-6)
- Automation-miner service (blueprint validation - Epic AI-6)
- OpenAI API (GPT-5.1-mini)

### YAML Generation (After User Approval)

When a user approves a suggestion, the service generates Home Assistant automation YAML using a **hybrid approach** that prioritizes reliability:

**Blueprint-First Strategy:**
1. **Blueprint Matching** (if enabled):
   - Search automation-miner service for matching Home Assistant blueprints
   - Calculate fit score based on device types (60%), use case (30%), integration (10%)
   - If fit score ≥ 0.8 (configurable threshold), use blueprint
   - Fill blueprint inputs with user's actual entities
   - Render blueprint YAML by replacing `!input` variables
   - **Advantages:** Tested, reliable, community-validated automations

2. **AI Generation** (fallback):
   - If no blueprint match or score too low, use OpenAI GPT-5.1
   - Generate YAML from scratch using pattern context
   - Apply safety validation (5-check engine)
   - **Advantages:** Handles unique patterns not covered by blueprints

**Blueprint Integration Components:**

- **BlueprintMatcher:** Matches suggestions to blueprints from automation-miner service
  - Searches by device types and use case
  - Calculates weighted fit scores
  - Returns best match if score exceeds threshold

- **BlueprintInputFiller:** Fills blueprint template inputs
  - Maps user entities to blueprint input requirements
  - Extracts numeric/boolean/text values from suggestion descriptions
  - Handles entity selectors, number selectors, boolean selectors, time selectors

- **BlueprintRenderer:** Renders final automation YAML
  - Replaces `!input variable_name` with actual values
  - Removes blueprint metadata section
  - Adds Home Assistant 2025 standards (id, alias, description)

**Configuration:**
- `blueprint_enabled`: Enable/disable blueprint matching (default: true)
- `blueprint_match_threshold`: Minimum fit score to use blueprint (default: 0.8)
- `automation_miner_url`: URL to automation-miner service (Port 8029)

**Data Sources:**
- Automation-miner service (blueprint corpus from Home Assistant community)
- Validated entities (from user approval)
- Suggestion metadata (description, devices_involved)

#### Phase 6: Publish MQTT Notification

**Duration:** <1 second  
**Purpose:** Notify UI of new suggestions

**Process:**
1. Count new suggestions
2. Generate summary statistics
3. Publish to MQTT topic: `ai-automation/suggestions/new`
4. Include suggestion count and metadata

**MQTT Message:**
```json
{
    "suggestion_count": 8,
    "pattern_suggestions": 5,
    "feature_suggestions": 2,
    "synergy_suggestions": 1,
    "timestamp": "2025-11-15T03:05:00Z"
}
```

**Output:**
- MQTT notification (if broker available)
- Analysis run status (SQLite)

**Data Sources:**
- Suggestions (SQLite, from Phase 5)
- MQTT broker

### Real-Time Processing (Ask AI Interface)

In addition to the daily batch job, the service supports real-time natural language queries:

**Flow:**
```
User Query: "What can I do with my office lights?"
    ↓
Entity Extraction (NER Service / spaCy fallback)
    ↓
Entity Resolution (Multi-signal matching)
    ├─ Embeddings (35%) - OpenVINO all-MiniLM-L6-v2
    ├─ Exact matches (30%)
    ├─ Fuzzy matching (15%) - rapidfuzz
    ├─ Numbered devices (15%)
    └─ Location (5%) - area filtering
    ↓
RAG Knowledge Base Check (OpenVINO embeddings)
    ├─ Similarity search (FAISS)
    └─ Threshold: 0.85 (skip clarification if similar query found)
    ↓
Clarification (if needed)
    ├─ Question generation (OpenAI GPT-5.1-mini)
    └─ Confidence calculation
    ↓
Suggestion Generation
    ├─ Pattern matching
    ├─ Device capability analysis
    └─ Natural language generation (OpenAI GPT-5.1)
    ↓
Response to User
```

**Data Sources:**
- Entity registry (Home Assistant)
- RAG knowledge base (SQLite + OpenVINO embeddings)
- Patterns (SQLite)
- Device capabilities (SQLite)

---

## Technical Architecture

### Service Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              AI Automation Service (Port 8024)              │
├─────────────────────────────────────────────────────────────┤
│  FastAPI Application (Python 3.12+)                        │
│  ├─ API Routers (25+ endpoints)                            │
│  ├─ Middleware (Auth, Rate Limiting, Idempotency)          │
│  ├─ Dependency Injection                                    │
│  └─ Lifespan Management                                     │
│                                                             │
│  Core Components:                                           │
│  ├─ Pattern Analyzer                                        │
│  ├─ Device Intelligence                                     │
│  ├─ Synergy Detection                                       │
│  ├─ Suggestion Generation                                   │
│  ├─ Safety Validation (5-check engine)                      │
│  └─ Deployment Service                                      │
│                                                             │
│  External Service Clients:                                  │
│  ├─ Data API Client (InfluxDB queries)                     │
│  ├─ Device Intelligence Client                              │
│  ├─ Home Assistant Client                                   │
│  ├─ MQTT Client                                             │
│  └─ OpenAI Client                                           │
│                                                             │
│  Database:                                                   │
│  └─ SQLite (27 tables, 365-day retention)                  │
│                                                             │
│  Scheduler:                                                  │
│  └─ APScheduler (daily 3 AM job)                           │
└─────────────────────────────────────────────────────────────┘
```

### Database Schema (27 Tables)

**Core Tables:**
1. `patterns` - Detected patterns (time-of-day, co-occurrence, anomaly)
2. `suggestions` - Automation suggestions (draft, approved, rejected, deployed)
3. `device_capabilities` - Device capability metadata (6,000+ models)
4. `device_feature_usage` - Feature utilization tracking
5. `synergy_opportunities` - Detected synergy opportunities
6. `discovered_synergies` - Multi-hop device relationships
7. `blueprint_opportunities` - Discovered blueprint opportunities (Epic AI-6)

**Note:** The service uses a hybrid database architecture where device/entity metadata is stored in the Data API service's SQLite database (`metadata.db`), while pattern analysis and suggestions are stored in the AI Automation Service's SQLite database (`ai_automation.db`). See [Missing HA 2025 Database Attributes Analysis](mdc:implementation/analysis/MISSING_HA_2025_DATABASE_ATTRIBUTES.md) for a comprehensive review of Home Assistant 2025 API attributes and potential schema enhancements.

**Learning System Tables:**
8. `ask_ai_queries` - Query history and results
9. `clarification_sessions` - Persistent clarification sessions
10. `semantic_knowledge` - RAG knowledge base (queries + embeddings)
11. `user_preferences` - Learned user preferences
12. `question_quality_metrics` - Question quality tracking
13. `qa_outcomes` - Q&A learning outcome tracking

**Management Tables:**
14. `system_settings` - System configuration
15. `automation_versions` - Version history
16. `analysis_run_status` - Daily job tracking
17. `user_feedback` - User feedback on suggestions
18. `pattern_history` - Historical pattern tracking
19. `entity_aliases` - User-defined entity nicknames
20. `clarification_confidence_feedback` - Confidence calibration
21. `clarification_outcomes` - Clarification outcome tracking
22. `reverse_engineering_metrics` - Performance metrics
23. `model_comparison_metrics` - Model comparison data
24. `training_runs` - Training run tracking
25. `auto_resolution_metrics` - Auto-resolution performance
26. `manual_refresh_triggers` - Manual refresh tracking
27. `suggestion_preferences` - User preference settings for suggestions (Epic AI-6)

### API Architecture

**REST API Endpoints (25+ routers):**

**Analysis & Pattern Detection:**
- `GET /api/analysis/status` - Analysis status
- `POST /api/analysis/trigger` - Manual trigger
- `POST /api/patterns/detect/time-of-day` - Time-of-day detection
- `POST /api/patterns/detect/co-occurrence` - Co-occurrence detection
- `GET /api/patterns/list` - List patterns

**Suggestion Management:**
- `POST /api/suggestions/generate` - Generate suggestions
- `GET /api/suggestions/list` - List suggestions
- `POST /api/v1/suggestions/{id}/approve` - Approve and generate YAML
- `POST /api/v1/suggestions/{id}/refine` - Refine with natural language

**Ask AI Interface:**
- `POST /api/v1/ask-ai/query` - Natural language query
- `POST /api/v1/ask-ai/clarify` - Provide clarification answers
- `GET /api/v1/ask-ai/query/{id}/suggestions` - Get suggestions from query

**Synergy Detection:**
- `GET /api/synergies` - List synergies
- `POST /api/synergies/detect` - Real-time detection
- `GET /api/synergies/stats` - Synergy statistics

**Deployment:**
- `POST /api/deploy/{id}` - Deploy automation
- `GET /api/deploy/automations` - List deployed automations
- `POST /api/deploy/automations/{id}/enable` - Enable automation

**Natural Language Generation:**
- `POST /api/nl/generate` - Generate from natural language
- `POST /api/nl/clarify/{id}` - Clarify request

### Safety Validation (5-Check Engine)

All generated automations must pass 5 safety checks before deployment:

1. **Conflicting Automations Check** - Detects existing automations with same trigger/action patterns
2. **Dangerous Actions Check** - Validates destructive actions (lock/unlock, alarm disarm, extreme climate settings)
3. **Energy Consumption Check** - Flags high-power actions (heaters, AC units, devices > 500W)
4. **Time Conflicts Check** - Validates time-based conditions don't conflict (impossible ranges, always-on patterns)
5. **Entity Availability Check** - Ensures all entities exist and are accessible, with fuzzy matching for suggestions

**Note:** The safety validator performs 5 implementation-level checks that cover the conceptual safety rules including destructive actions, entity mismatches, automation conflicts, unsafe combinations, and time range validation.

---

## Performance and Scalability

### Performance Metrics

**Daily Batch Job:**
- **Total Duration:** 2-4 minutes (typical)
- **Memory Usage:** 200-400MB peak
- **CPU Usage:** Moderate (CPU-only, no GPU)
- **OpenAI Cost:** $0.001-0.005 per run (~$0.50/year)

**Phase Breakdown:**
- Phase 1 (Device Capability Update): 10-30s
- Phase 2 (Fetch Events): 20-60s
- Phase 3 (Pattern Detection): 30-90s
- Phase 3c (Synergy Detection): 15-45s
- Phase 3d (Blueprint Opportunity Discovery): 2-5s
- Phase 4 (Feature Analysis): 10-30s
- Phase 5 (Description Generation): 5-15s
- Phase 6 (MQTT Notification): <1s

**Scaling Characteristics:**
- 100 devices: ~2 minutes
- 500 devices: ~3 minutes
- 1000 devices: ~4 minutes

**Real-Time Query Performance:**
- Entity extraction: <100ms
- RAG similarity search: <50ms
- Suggestion generation: 200-500ms
- Total query time: <1 second (typical)

### Resource Optimization

**Model Optimization:**
- INT8 quantization: 4x size reduction (380MB vs 1.5GB)
- Lazy loading: Models load on first use
- Persistent volumes: Models cached across restarts
- CPU-only deployment: No GPU required

**Data Optimization:**
- Incremental processing: Pattern aggregates for faster queries
- Event filtering: Only relevant entities processed
- Batch processing: Efficient DataFrame operations
- SQLite indexing: Fast pattern/synergy lookups

**Cost Optimization:**
- GPT-5.1: 50% cost savings vs GPT-4o
- GPT-5.1-mini: 80% cost savings vs GPT-4o
- Batch processing: Single daily run vs continuous processing
- Token optimization: Efficient prompt engineering

---

## Award-Winning Combination

### Innovation Highlights

#### 1. Unified Multi-Source Intelligence

The service combines **four distinct data sources** into a cohesive intelligence system:

- **Historical Patterns** (InfluxDB) - What you actually do
- **Device Capabilities** (Device Intelligence) - What your devices can do
- **Multi-Hop Synergies** (Graph Analysis) - How devices relate
- **External Context** (Weather, Energy, Events) - Environmental factors

**Result:** Automation suggestions that are both **data-driven** (based on actual usage) and **capability-aware** (leveraging device features).

#### 2. Description-First Conversational Flow

Unlike traditional automation systems that generate code immediately, the service uses a **description-first approach**:

1. Generate human-readable description (no YAML yet)
2. User reviews and approves
3. Conversational refinement ("make it 6:30am instead")
4. YAML generated only after approval

**Result:** Users understand automations before committing, reducing errors and increasing adoption.

#### 3. Self-Improving RAG System

The service includes a **Retrieval-Augmented Generation (RAG) system** that learns from successful queries:

- Stores successful queries with semantic embeddings
- Skips clarification for similar queries (similarity > 0.85)
- Reduces false positive clarification questions
- Improves over time as knowledge base grows

**Result:** System gets smarter with each interaction, reducing user friction.

#### 4. Multi-Signal Entity Resolution

Entity extraction uses **five complementary signals** for robust matching:

- **Embeddings (35%)** - Semantic similarity
- **Exact matches (30%)** - Direct entity_id/name matching
- **Fuzzy matching (15%)** - Typo handling (rapidfuzz)
- **Numbered devices (15%)** - Smart parsing ("bedroom light 1")
- **Location (5%)** - Area-based filtering

**Result:** Handles user queries with typos, nicknames, and ambiguous references.

#### 5. Multi-Hop Synergy Detection

The service detects **complex device relationships** beyond simple pairs:

- **2-level pairs:** Motion → Light
- **3-level chains:** Door → Lock → Light
- **4-level chains:** Door → Lock → Alarm → Notification

**Result:** Discovers automation opportunities that span multiple devices and actions.

#### 6. Cost-Efficient AI Stack

The service achieves **award-winning cost efficiency** through:

- **Model Selection:** GPT-5.1 for quality, GPT-5.1-mini for speed (50-80% savings)
- **INT8 Quantization:** 4x model size reduction
- **Batch Processing:** Single daily run vs continuous processing
- **Containerized Services:** Resource isolation and optimization

**Result:** Annual OpenAI cost: ~$0.50 (vs $10-50 for continuous processing).

#### 7. Universal Device Support

The service automatically discovers capabilities for **6,000+ Zigbee device models** across **100+ manufacturers**:

- No manual research required
- Real-time capability updates
- Feature utilization tracking
- Underutilized feature suggestions

**Result:** Works out-of-the-box with any Zigbee device, regardless of manufacturer.

#### 8. Blueprint-First YAML Generation

The service uses a **hybrid YAML generation strategy** that prioritizes reliability:

- **Blueprint Matching:** Searches automation-miner service for community-validated blueprints
- **Fit Scoring:** Calculates match quality (device types, use case, integration compatibility)
- **Smart Fallback:** Uses AI generation only when no suitable blueprint found
- **Input Filling:** Automatically maps user entities to blueprint template variables
- **Quality Assurance:** Blueprints are community-tested and validated

**Result:** More reliable automations with faster generation (blueprints are pre-validated) and lower AI costs (blueprints don't require OpenAI API calls).

#### 9. Blueprint-Enhanced Suggestion Intelligence (Epic AI-6)

The service proactively discovers blueprint opportunities from user device inventory and applies intelligent preference-based ranking:

**Blueprint Opportunity Discovery:**
- **Proactive Discovery:** Scans user device inventory to find matching blueprints
- **Fit Scoring:** Calculates compatibility scores (device types, integrations, quality)
- **Opportunity Storage:** Stores discovered opportunities for batch and real-time use

**Pattern Validation:**
- **Blueprint Validation:** Validates detected patterns against community blueprints
- **Confidence Boosting:** Increases confidence scores for validated patterns
- **Blueprint Context:** Adds blueprint hints to pattern descriptions (≥0.8 match score)

**Preference-Aware Ranking:**
- **Creativity Levels:** Conservative/Balanced/Creative filtering (confidence thresholds, experimental limits)
- **Blueprint Preference:** Low/Medium/High weighting for blueprint opportunities
- **Max Suggestions:** User-configurable limit (5-50, default: 10)
- **Unified Ranking:** Single service applies all preferences in optimal order

**Integration Points:**
- **3 AM Batch Job:** Phase 3d discovers blueprint opportunities, Phase 5 validates patterns and applies preferences
- **Ask AI Queries:** Real-time blueprint discovery from query context, preference-aware ranking
- **Settings UI:** User-friendly interface for configuring all preferences

**Result:** More relevant suggestions, better user control, and intelligent ranking based on user preferences and blueprint validation.

### Technical Excellence

**Architecture:**
- Microservices design with containerized AI models
- Graceful degradation (continues if services unavailable)
- Comprehensive error handling and retry logic
- Observability and monitoring built-in

**Data Quality:**
- Multi-source validation
- Pattern cross-validation
- Confidence calibration
- Statistical significance testing

**User Experience:**
- Natural language interface
- Conversational refinement
- Safety validation (5-check engine)
- One-click deployment

**Scalability:**
- Optimized for single-home (50-100 devices)
- CPU-only deployment (no GPU required)
- Efficient resource usage (200-400MB peak)
- Fast query response (<1 second)

### Competitive Advantages

1. **Data-Driven:** Suggestions based on actual usage, not assumptions
2. **Capability-Aware:** Leverages device features automatically
3. **Self-Learning:** RAG system improves over time
4. **Cost-Efficient:** ~$0.50/year for AI processing
5. **Universal:** Works with 6,000+ device models automatically
6. **Safe:** 5-check validation engine prevents dangerous automations
7. **User-Friendly:** Description-first flow, natural language interface

---

## Conclusion

The AI Automation Service represents a **breakthrough in intelligent home automation**, combining:

- **Advanced AI Models** (OpenAI GPT-5.1, OpenVINO optimized models, NER, ML clustering)
- **Multi-Source Data** (InfluxDB events, Device Intelligence, MQTT, Home Assistant)
- **Sophisticated Algorithms** (Pattern detection, synergy analysis, RAG, entity resolution)
- **Cost-Efficient Architecture** (Containerized services, INT8 quantization, batch processing)
- **User-Centric Design** (Description-first flow, conversational refinement, safety validation)

The result is an **award-winning combination** that:

✅ **Discovers** automation opportunities automatically  
✅ **Suggests** human-readable automation ideas  
✅ **Learns** from user interactions  
✅ **Deploys** validated automations safely  
✅ **Scales** efficiently for single-home deployments  
✅ **Costs** less than $1/year for AI processing  

This technical foundation enables the service to transform raw device data into actionable automation suggestions, making smart home automation accessible, intelligent, and cost-effective.

---

**Document Version:** 2.5  
**Last Updated:** December 2025 (Epic AI-6: Blueprint-Enhanced Suggestion Intelligence)  
**Status:** Production Ready  
**Service Port:** 8018 (internal), 8024 (external)

