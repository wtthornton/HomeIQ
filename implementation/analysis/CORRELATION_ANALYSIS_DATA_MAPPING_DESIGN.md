# Correlation Analysis Data Mapping Design Review

**Date:** January 2025  
**Status:** Design Review - Pre-Implementation  
**Purpose:** Map all project data sources to 2025 ML correlation analysis techniques for automation creation

---

## Executive Summary

This document reviews all data sources in the HomeIQ project and maps them to the 2025 ML correlation analysis design. The goal is to enhance automation creation by identifying correlations between devices, events, external data, and user patterns.

**Key Findings:**
- ✅ **Current Data Sources**: Well-structured for correlation analysis
- ✅ **Home Assistant API**: Rich data available, some underutilized
- ✅ **External Data**: Weather, sports, carbon, electricity pricing provide context
- ⚠️ **Gaps**: Missing calendar integration, limited state history usage, no automation execution tracking

**Recommendation:** Proceed with correlation analysis implementation using existing data sources, with enhancements for calendar and state history integration.

---

## 1. Current Data Sources Inventory

### 1.1 Home Assistant Event Data (Primary Source)

**Storage:** InfluxDB (`home_assistant_events` bucket)  
**Volume:** Real-time state change events  
**Retention:** 90+ days (configurable)

**Data Structure:**
- `entity_id`: Device/sensor identifier (e.g., `light.living_room`)
- `domain`: Entity domain (e.g., `light`, `sensor`, `binary_sensor`)
- `state`: Current state value (e.g., `on`, `off`, `72.5`)
- `attributes`: Entity-specific attributes (brightness, color, temperature, etc.)
- `timestamp`: Event occurrence time
- `context_id`: Automation context tracking (Epic 23.1)
- `context_parent_id`: Parent automation context (Epic 23.1)
- `device_id`: Associated device identifier (Epic 23.2)
- `area_id`: Spatial area identifier (Epic 23.2)
- `duration_in_state`: Time in current state (Epic 23.3)
- `manufacturer`: Device manufacturer (Epic 23.5)
- `model`: Device model (Epic 23.5)

**Correlation Analysis Value:**
- ✅ **Device Pair Correlations**: Identify which devices change together
- ✅ **Temporal Patterns**: Time-of-day, day-of-week patterns
- ✅ **Spatial Correlations**: Area-based device interactions
- ✅ **Sequence Detection**: Device activation sequences
- ✅ **Context Tracking**: Automation chains and dependencies

**Usage in Correlation Analysis:**
- Primary input for TabPFN correlation prediction
- Source for streaming correlation updates
- Basis for pattern detection and synergy identification

---

### 1.2 Device & Entity Metadata (SQLite)

**Storage:** SQLite database (via data-api)  
**Source:** Home Assistant Device/Entity Registry  
**Refresh:** Periodic sync (every 5 minutes) + real-time updates

**Data Structure:**
- `device_id`: Unique device identifier
- `name`: Device friendly name
- `manufacturer`: Device manufacturer
- `model`: Device model
- `sw_version`: Software version
- `area_id`: Associated area
- `integration`: Integration name (e.g., `hue`, `zwave`)
- `entity_count`: Number of entities per device
- `entity_id`: Entity identifier
- `domain`: Entity domain
- `device_class`: Entity device class
- `capabilities`: Entity capabilities (brightness, color, etc.)

**Correlation Analysis Value:**
- ✅ **Feature Extraction**: Domain, area, device class for TabPFN
- ✅ **Compatibility Detection**: Device pairing based on capabilities
- ✅ **Manufacturer Patterns**: Brand-specific usage patterns
- ✅ **Integration Correlations**: Devices from same integration

**Usage in Correlation Analysis:**
- Feature engineering for correlation prediction
- Filtering compatible device pairs
- Enriching correlation explanations

---

### 1.3 External Data Sources

#### A. Weather Data (Port 8009)

**Storage:** InfluxDB (`weather_data` measurement)  
**Refresh:** 15-minute intervals  
**Source:** OpenWeatherMap API

**Data Structure:**
- `temperature`: Current temperature
- `humidity`: Humidity percentage
- `pressure`: Atmospheric pressure
- `wind_speed`: Wind speed
- `wind_direction`: Wind direction
- `condition`: Weather condition (sunny, cloudy, rain, etc.)
- `timestamp`: Data timestamp

**Correlation Analysis Value:**
- ✅ **Climate Correlations**: HVAC usage vs weather
- ✅ **Seasonal Patterns**: Weather-driven automation opportunities
- ✅ **Energy Optimization**: Weather-based energy scheduling
- ✅ **Comfort Automation**: Pre-heating/cooling based on forecasts

**Usage in Correlation Analysis:**
- Context feature for correlation prediction
- Explaining weather-driven correlations
- Enhancing automation suggestions with weather context

**Current Integration:**
- ✅ Weather API service (Epic 31)
- ✅ InfluxDB storage
- ⚠️ Not yet used in correlation analysis

---

#### B. Sports Data (Port 8005)

**Storage:** InfluxDB (`sports_data` measurement)  
**Refresh:** 15 seconds (live games), 5 minutes (upcoming)  
**Source:** ESPN API

**Data Structure:**
- `game_id`: Unique game identifier
- `home_team`: Home team name
- `away_team`: Away team name
- `home_score`: Home team score
- `away_score`: Away team score
- `status`: Game status (live, scheduled, final)
- `timestamp`: Game timestamp

**Correlation Analysis Value:**
- ✅ **Behavioral Patterns**: Device usage during games
- ✅ **Entertainment Automation**: TV/lighting during game events
- ✅ **Presence Detection**: Home activity during games
- ⚠️ **Limited Value**: Sports data is entertainment-focused, less relevant for core automation

**Usage in Correlation Analysis:**
- Low priority for correlation analysis
- Could enhance presence detection patterns
- Entertainment-focused automations only

**Current Integration:**
- ✅ Sports API service
- ✅ InfluxDB storage
- ✅ Dashboard integration

---

#### C. Carbon Intensity Data (Port 8010)

**Storage:** InfluxDB (`carbon_intensity` measurement)  
**Refresh:** 15-minute intervals  
**Source:** WattTime API

**Data Structure:**
- `carbon_intensity`: gCO2/kWh
- `renewable_percentage`: Percentage of renewable energy
- `grid_region`: Grid region identifier
- `timestamp`: Data timestamp

**Correlation Analysis Value:**
- ✅ **Energy Scheduling**: Correlate device usage with carbon intensity
- ✅ **Green Automation**: Optimize automations for low-carbon periods
- ✅ **Energy Patterns**: Identify high-carbon usage patterns
- ✅ **Cost Optimization**: Combine with electricity pricing

**Usage in Correlation Analysis:**
- High value for energy-related correlations
- Feature for energy optimization automations
- Context for explaining energy usage patterns

**Current Integration:**
- ✅ Carbon intensity service
- ✅ InfluxDB storage
- ⚠️ Not yet used in correlation analysis

---

#### D. Electricity Pricing Data (Port 8011)

**Storage:** InfluxDB (`electricity_pricing` measurement)  
**Refresh:** Hourly  
**Source:** Awattar API (Germany/Austria)

**Data Structure:**
- `price_per_kwh`: Electricity price (EUR/kWh)
- `timestamp`: Price timestamp
- `region`: Pricing region

**Correlation Analysis Value:**
- ✅ **Cost Optimization**: Correlate device usage with pricing
- ✅ **Scheduling Automation**: Schedule high-energy devices during low-price periods
- ✅ **Energy Patterns**: Identify expensive usage patterns
- ⚠️ **Regional Limitation**: Only available for Germany/Austria

**Usage in Correlation Analysis:**
- High value for cost-optimization automations
- Feature for energy correlation analysis
- Context for explaining cost-related patterns

**Current Integration:**
- ✅ Electricity pricing service
- ✅ InfluxDB storage
- ⚠️ Not yet used in correlation analysis

---

#### E. Air Quality Data (Port 8012)

**Storage:** InfluxDB (`air_quality` measurement)  
**Refresh:** Hourly  
**Source:** AirNow API

**Data Structure:**
- `pm25`: PM2.5 concentration
- `pm10`: PM10 concentration
- `ozone`: Ozone concentration
- `aqi`: Air Quality Index
- `timestamp`: Data timestamp

**Correlation Analysis Value:**
- ✅ **HVAC Correlations**: Air quality vs HVAC usage
- ✅ **Health Automation**: Window/ventilation automation based on air quality
- ✅ **Pattern Detection**: Air quality-driven device usage
- ✅ **Comfort Optimization**: Indoor air quality management

**Usage in Correlation Analysis:**
- Medium-high value for HVAC correlations
- Feature for health-focused automations
- Context for explaining air quality patterns

**Current Integration:**
- ✅ Air quality service
- ✅ InfluxDB storage
- ⚠️ Not yet used in correlation analysis

---

### 1.4 Pattern Detection Data (SQLite)

**Storage:** SQLite database  
**Source:** AI Automation Service pattern detection

**Data Structure:**
- `pattern_id`: Unique pattern identifier
- `pattern_type`: Pattern type (time-of-day, co-occurrence, sequence, etc.)
- `confidence`: Pattern confidence score
- `entities`: Entities involved in pattern
- `frequency`: Pattern occurrence frequency
- `first_seen`: First occurrence timestamp
- `last_seen`: Last occurrence timestamp
- `metadata`: Pattern-specific metadata

**Correlation Analysis Value:**
- ✅ **Pre-computed Correlations**: Already identified device relationships
- ✅ **Validation**: Validate correlation predictions against known patterns
- ✅ **Feature Engineering**: Use patterns as features for correlation analysis
- ✅ **Synergy Detection**: Patterns indicate synergy opportunities

**Usage in Correlation Analysis:**
- Ground truth for correlation validation
- Feature input for correlation prediction
- Explanation source for correlation insights

**Current Integration:**
- ✅ Pattern detection system
- ✅ SQLite storage
- ✅ Used in synergy detection

---

### 1.5 Synergy Opportunities (SQLite)

**Storage:** SQLite database  
**Source:** AI Automation Service synergy detection

**Data Structure:**
- `synergy_id`: Unique synergy identifier
- `device_i`: First device identifier
- `device_j`: Second device identifier
- `relationship_type`: Relationship type (motion_to_light, etc.)
- `confidence`: Synergy confidence score
- `impact_score`: Impact score
- `area`: Associated area
- `validated_by_patterns`: Pattern validation flag

**Correlation Analysis Value:**
- ✅ **Known Correlations**: Pre-identified device relationships
- ✅ **Training Data**: Use synergies as training data for correlation models
- ✅ **Validation**: Validate correlation predictions
- ✅ **Automation Targets**: Direct targets for automation creation

**Usage in Correlation Analysis:**
- Training data for TabPFN
- Validation for correlation predictions
- Direct automation opportunities

**Current Integration:**
- ✅ Synergy detection system
- ✅ SQLite storage
- ✅ Used in automation suggestions

---

## 2. Home Assistant API 2025 - Additional Data Sources

### 2.1 Currently Used HA API Endpoints

**WebSocket API:**
- ✅ `config/device_registry/list` - Device registry
- ✅ `config/entity_registry/list` - Entity registry
- ✅ `config/area_registry/list` - Area registry
- ✅ `subscribe_events` - Real-time event subscription

**REST API:**
- ✅ `GET /api/states/{entity_id}` - Single entity state
- ✅ `GET /api/states` - All entity states
- ✅ `GET /api/config` - HA configuration

---

### 2.2 Missing/Underutilized HA API Endpoints (2025)

#### A. State History API ⭐⭐⭐⭐⭐ (HIGH VALUE)

**Endpoint:** `GET /api/history/period/{timestamp}`  
**Purpose:** Historical state changes for entities

**Data Available:**
- Historical state changes over time
- State transitions and durations
- Historical patterns and trends
- Long-term correlation data

**Correlation Analysis Value:**
- ✅ **Long-term Correlations**: 90+ days of historical data
- ✅ **Seasonal Patterns**: Year-over-year patterns
- ✅ **Temporal Analysis**: Time-series correlation analysis
- ✅ **Pattern Validation**: Validate correlation predictions against history

**Recommendation:** **HIGH PRIORITY** - Essential for correlation analysis

**Implementation:**
- Query state history for correlation pairs
- Use historical data for TabPFN training
- Validate correlations against historical patterns

---

#### B. Calendar API ⭐⭐⭐⭐ (MEDIUM-HIGH VALUE)

**Endpoint:** `GET /api/calendars`  
**Purpose:** Calendar events and schedules

**Data Available:**
- Calendar events (Google Calendar, iCal, etc.)
- Event schedules and recurring events
- Event metadata (location, attendees, etc.)

**Correlation Analysis Value:**
- ✅ **Presence Patterns**: Calendar events indicate presence/absence
- ✅ **Schedule Correlations**: Device usage vs calendar events
- ✅ **Routine Detection**: Calendar-driven routines
- ✅ **Context Enhancement**: Calendar context for automations

**Recommendation:** **MEDIUM-HIGH PRIORITY** - Valuable for presence and routine detection

**Implementation:**
- Integrate calendar events as correlation features
- Use calendar for presence detection
- Enhance automation suggestions with calendar context

**Current Status:**
- ⚠️ Calendar service exists (Port 8013) but is disabled
- ⚠️ No integration with correlation analysis

---

#### C. Automation API ⭐⭐⭐ (MEDIUM VALUE)

**Endpoint:** `GET /api/config/automation/config`  
**Purpose:** Existing automation configurations

**Data Available:**
- All existing automations
- Automation triggers and actions
- Automation metadata

**Correlation Analysis Value:**
- ✅ **Avoid Duplicates**: Don't suggest automations that already exist
- ✅ **Pattern Learning**: Learn from existing automations
- ✅ **Validation**: Validate correlation predictions against existing automations
- ✅ **Enhancement**: Enhance existing automations based on correlations

**Recommendation:** **MEDIUM PRIORITY** - Important for avoiding duplicate suggestions

**Current Integration:**
- ✅ Used in synergy detection to filter existing automations
- ⚠️ Not used in correlation analysis

---

#### D. Service API ⭐⭐⭐ (MEDIUM VALUE)

**Endpoint:** `GET /api/services`  
**Purpose:** Available services and capabilities

**Data Available:**
- All available services (e.g., `light.turn_on`, `climate.set_temperature`)
- Service parameters and capabilities
- Service descriptions

**Correlation Analysis Value:**
- ✅ **Capability Detection**: Understand what devices can do
- ✅ **Action Validation**: Validate automation actions
- ✅ **Feature Engineering**: Use services as correlation features

**Recommendation:** **MEDIUM PRIORITY** - Useful for automation generation

**Current Integration:**
- ⚠️ Limited usage in automation generation
- ⚠️ Not used in correlation analysis

---

#### E. Template API ⭐⭐ (LOW-MEDIUM VALUE)

**Endpoint:** Template rendering via WebSocket  
**Purpose:** Jinja2 template evaluation

**Data Available:**
- Template evaluation results
- State access via templates
- Complex condition evaluation

**Correlation Analysis Value:**
- ✅ **Condition Evaluation**: Evaluate complex correlation conditions
- ✅ **State Access**: Access historical states for correlation
- ⚠️ **Limited Direct Value**: More useful for automation execution than correlation

**Recommendation:** **LOW-MEDIUM PRIORITY** - Useful but not critical

---

### 2.3 WebSocket Subscriptions (2025)

**Available Subscriptions:**
- ✅ `state_changed` - State change events (currently used)
- ⚠️ `device_registry_updated` - Device registry changes (not subscribed)
- ⚠️ `entity_registry_updated` - Entity registry changes (not subscribed)
- ⚠️ `automation_triggered` - Automation execution events (not subscribed)

**Correlation Analysis Value:**
- ✅ **Real-time Updates**: Real-time correlation updates
- ✅ **Registry Changes**: Track device/entity changes
- ✅ **Automation Tracking**: Track automation executions for correlation

**Recommendation:** **MEDIUM PRIORITY** - Subscribe to registry updates for real-time correlation

---

## 3. Data Mapping to Correlation Analysis Techniques

### 3.1 TabPFN Correlation Prediction

**Input Data:**
- ✅ Device metadata (domain, area, device class)
- ✅ Entity metadata (capabilities, manufacturer, model)
- ✅ Usage frequency (from event counts)
- ✅ Temporal patterns (from pattern detection)
- ⚠️ **Missing**: State history (for long-term patterns)
- ⚠️ **Missing**: Calendar events (for presence patterns)

**Feature Engineering:**
- Domain similarity (same domain = 1.0)
- Area proximity (same area = 1.0)
- Usage frequency similarity
- Temporal pattern similarity
- Device class similarity
- Manufacturer similarity
- **Enhancement**: Add calendar event correlation
- **Enhancement**: Add state history patterns

**Training Data:**
- ✅ Known synergies (from synergy detection)
- ✅ Pattern detections (from pattern detection)
- ⚠️ **Missing**: Historical correlations (from state history)

---

### 3.2 Streaming Continual Learning

**Input Data:**
- ✅ Real-time events (from WebSocket)
- ✅ Event values (state changes)
- ✅ Timestamps
- ⚠️ **Missing**: Automation execution events (for automation correlation)

**Update Frequency:**
- Real-time (as events arrive)
- O(1) per event update

**Enhancement Opportunities:**
- Subscribe to `automation_triggered` events
- Track automation execution correlations
- Correlate automations with device usage

---

### 3.3 Vector Database for Correlation Storage

**Input Data:**
- ✅ Correlation strength
- ✅ Lag time (temporal offset)
- ✅ Temporal consistency
- ✅ Domain/area similarity
- ⚠️ **Missing**: External data correlations (weather, carbon, etc.)

**Enhancement Opportunities:**
- Add weather correlation features
- Add carbon intensity features
- Add electricity pricing features
- Add air quality features

**Vector Dimensions:**
- Current: 100 dimensions
- Enhanced: 120+ dimensions (add external data features)

---

### 3.4 AutoML Hyperparameter Optimization

**Input Data:**
- ✅ Correlation features
- ✅ User feedback (accepted/rejected automations)
- ✅ Pattern validation results
- ⚠️ **Missing**: Automation execution success/failure

**Enhancement Opportunities:**
- Track automation execution success
- Use execution data for optimization
- Learn from automation failures

---

### 3.5 Wide & Deep Learning

**Wide Features (High-dimensional):**
- ✅ Time-series correlation data
- ✅ Event sequences
- ⚠️ **Missing**: State history sequences

**Deep Features (Low-dimensional):**
- ✅ Domain, area, device class
- ✅ Usage frequency
- ⚠️ **Missing**: Calendar event presence
- ⚠️ **Missing**: External data context (weather, carbon, etc.)

**Enhancement Opportunities:**
- Add calendar event features
- Add external data context features
- Add state history patterns

---

### 3.6 Augmented Analytics

**Input Data:**
- ✅ Correlation matrix
- ✅ Device metadata
- ✅ Area information
- ⚠️ **Missing**: External data context
- ⚠️ **Missing**: Calendar context

**Enhancement Opportunities:**
- Explain correlations with weather context
- Explain correlations with calendar context
- Explain correlations with energy pricing
- Explain correlations with carbon intensity

---

## 4. Data Integration Design for Automation Creation

### 4.1 Correlation Analysis → Automation Pipeline

**Current Flow:**
```
Events → Pattern Detection → Synergy Detection → Automation Suggestions
```

**Enhanced Flow with Correlation Analysis:**
```
Events + External Data + State History + Calendar
    ↓
Correlation Analysis (TabPFN + Streaming + Vector DB)
    ↓
Correlation Insights
    ↓
Pattern Detection (enhanced with correlations)
    ↓
Synergy Detection (enhanced with correlations)
    ↓
Automation Suggestions (with correlation explanations)
    ↓
YAML Generation
```

---

### 4.2 Data Sources for Automation Creation

#### A. Device Pair Automations

**Data Sources:**
- ✅ Device metadata (domain, area, capabilities)
- ✅ Event correlations (TabPFN predictions)
- ✅ Pattern detections
- ✅ Synergy opportunities
- ⚠️ **Enhancement**: State history for validation

**Automation Creation:**
- Use correlations to identify device pairs
- Validate against state history
- Generate automation YAML
- Explain with correlation insights

---

#### B. Weather-Aware Automations

**Data Sources:**
- ✅ Weather data (temperature, humidity, condition)
- ✅ HVAC device events
- ✅ Window/door sensor events
- ⚠️ **Enhancement**: Weather correlation features

**Automation Creation:**
- Correlate weather with HVAC usage
- Identify weather-driven patterns
- Generate weather-aware automations
- Explain with weather context

---

#### C. Energy Optimization Automations

**Data Sources:**
- ✅ Carbon intensity data
- ✅ Electricity pricing data
- ✅ Energy-consuming device events
- ⚠️ **Enhancement**: Energy correlation features

**Automation Creation:**
- Correlate device usage with carbon/pricing
- Identify energy optimization opportunities
- Generate scheduling automations
- Explain with energy context

---

#### D. Presence-Aware Automations

**Data Sources:**
- ✅ Calendar events
- ✅ Device usage patterns
- ✅ Motion/presence sensors
- ⚠️ **Enhancement**: Calendar correlation features

**Automation Creation:**
- Correlate calendar with device usage
- Identify presence patterns
- Generate presence-aware automations
- Explain with calendar context

---

## 5. Pros and Cons Analysis

### 5.1 Pros of Current Data Architecture

**Strengths:**
1. ✅ **Rich Event Data**: Comprehensive event tracking with context, spatial, and temporal metadata
2. ✅ **External Data Integration**: Weather, sports, carbon, electricity, air quality services
3. ✅ **Hybrid Storage**: InfluxDB for time-series, SQLite for metadata (fast queries)
4. ✅ **Real-time Processing**: WebSocket ingestion for real-time correlation updates
5. ✅ **Pattern Detection**: Pre-computed patterns for correlation validation
6. ✅ **Synergy Detection**: Pre-identified device relationships
7. ✅ **Scalable Architecture**: Microservices architecture for independent scaling

**Data Quality:**
- ✅ **High Quality**: Well-structured, validated data
- ✅ **Comprehensive**: Covers devices, events, external context
- ✅ **Real-time**: Live data updates
- ✅ **Historical**: 90+ days of event history

---

### 5.2 Cons and Gaps

**Missing Data Sources:**
1. ❌ **State History API**: Not used for long-term correlation analysis
2. ❌ **Calendar Integration**: Calendar service disabled, not integrated
3. ❌ **Automation Execution Tracking**: No tracking of automation success/failure
4. ❌ **Registry Update Subscriptions**: Not subscribed to device/entity registry updates

**Underutilized Data:**
1. ⚠️ **External Data**: Weather, carbon, electricity, air quality not used in correlation analysis
2. ⚠️ **State History**: Available but not queried for correlation analysis
3. ⚠️ **Automation Config**: Used for filtering but not for learning

**Data Integration Gaps:**
1. ⚠️ **Correlation Features**: External data not included in correlation feature vectors
2. ⚠️ **Context Features**: Calendar and state history not used as context
3. ⚠️ **Validation Data**: No automation execution data for validation

---

### 5.3 Implementation Complexity

**Low Complexity (Easy to Add):**
- ✅ Use existing external data services (weather, carbon, etc.)
- ✅ Add external data features to correlation vectors
- ✅ Subscribe to registry update events

**Medium Complexity (Moderate Effort):**
- ⚠️ Integrate state history API for long-term correlations
- ⚠️ Enable and integrate calendar service
- ⚠️ Track automation execution events

**High Complexity (Significant Effort):**
- ❌ Real-time correlation updates with all data sources
- ❌ Multi-source correlation analysis (events + external + calendar)
- ❌ Automation execution tracking and learning

---

### 5.4 Value vs Complexity Matrix

| Data Source | Value for Automation | Complexity | Priority |
|------------|---------------------|------------|----------|
| **State History API** | ⭐⭐⭐⭐⭐ | Medium | **HIGH** |
| **External Data (Weather/Carbon/Pricing)** | ⭐⭐⭐⭐ | Low | **HIGH** |
| **Calendar Integration** | ⭐⭐⭐⭐ | Medium | **MEDIUM-HIGH** |
| **Automation Execution Tracking** | ⭐⭐⭐ | Medium | **MEDIUM** |
| **Registry Update Subscriptions** | ⭐⭐⭐ | Low | **MEDIUM** |
| **Service API Integration** | ⭐⭐ | Low | **LOW-MEDIUM** |

---

## 6. Recommended Enhancements

### 6.1 Phase 1: Quick Wins (Week 1)

**Enhancements:**
1. ✅ **Add External Data Features**: Include weather, carbon, electricity, air quality in correlation vectors
2. ✅ **Subscribe to Registry Updates**: Real-time device/entity registry change tracking
3. ✅ **Use State History for Validation**: Query state history to validate correlations

**Impact:**
- Enhanced correlation features
- Real-time correlation updates
- Better correlation validation

**Effort:** Low (1-2 days)

---

### 6.2 Phase 2: Medium Priority (Week 2-3)

**Enhancements:**
1. ⚠️ **Integrate State History API**: Use state history for long-term correlation analysis
2. ⚠️ **Enable Calendar Service**: Integrate calendar events for presence patterns
3. ⚠️ **Add Calendar Features**: Include calendar events in correlation features

**Impact:**
- Long-term correlation patterns
- Presence-aware automations
- Calendar-driven correlations

**Effort:** Medium (1-2 weeks)

---

### 6.3 Phase 3: Advanced (Week 4+)

**Enhancements:**
1. ❌ **Automation Execution Tracking**: Track automation success/failure
2. ❌ **Multi-Source Correlation**: Correlate events + external + calendar + state history
3. ❌ **Learning from Executions**: Use execution data to improve correlations

**Impact:**
- Self-improving correlation system
- Better automation suggestions
- Execution-based learning

**Effort:** High (2-3 weeks)

---

## 7. Summary and Recommendations

### 7.1 Current State Assessment

**Strengths:**
- ✅ Comprehensive event data with rich metadata
- ✅ External data services (weather, carbon, electricity, air quality)
- ✅ Pattern and synergy detection systems
- ✅ Real-time WebSocket ingestion
- ✅ Hybrid storage architecture (InfluxDB + SQLite)

**Gaps:**
- ❌ State history API not used for correlation analysis
- ❌ Calendar service disabled, not integrated
- ❌ External data not included in correlation features
- ❌ No automation execution tracking

---

### 7.2 Recommended Approach

**Immediate (Phase 1):**
1. Add external data features to correlation vectors (weather, carbon, electricity, air quality)
2. Subscribe to registry update events for real-time correlation updates
3. Use state history API for correlation validation

**Short-term (Phase 2):**
1. Integrate state history API for long-term correlation analysis
2. Enable and integrate calendar service
3. Add calendar features to correlation analysis

**Long-term (Phase 3):**
1. Track automation execution events
2. Implement multi-source correlation analysis
3. Learn from automation executions

---

### 7.3 Expected Outcomes

**Automation Creation Improvements:**
- ✅ **Better Correlations**: More accurate device relationship detection
- ✅ **Context-Aware**: Weather, calendar, energy context in automations
- ✅ **Validated Suggestions**: Correlations validated against state history
- ✅ **Explained Automations**: Clear explanations with correlation insights

**User Experience:**
- ✅ **Higher Quality Suggestions**: More accurate automation suggestions
- ✅ **Better Explanations**: Clear correlation-based explanations
- ✅ **Context-Aware Automations**: Automations that adapt to context
- ✅ **Energy Optimization**: Cost and carbon-aware automations

---

## 8. Conclusion

The current data architecture is **well-suited for correlation analysis** with some enhancements needed. The existing data sources (events, devices, external data) provide a solid foundation, and the recommended enhancements (state history, calendar, execution tracking) will significantly improve correlation analysis and automation creation.

**Key Recommendation:** Proceed with correlation analysis implementation using existing data sources, with Phase 1 enhancements (external data features, registry subscriptions, state history validation) for immediate value.

---

**Next Steps:**
1. Review this design with stakeholders
2. Prioritize enhancements based on value/complexity
3. Update correlation analysis document with data mapping
4. Begin Phase 1 implementation

