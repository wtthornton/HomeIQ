# Enrichment Data Integration Plan for Ask AI

**Date:** 2025-11-04
**Purpose:** Integrate weather, carbon, energy, and air quality enrichment data into Ask AI suggestions

---

## Architecture Overview

### Current State
Ask AI uses 3 data sources:
1. Home Assistant (state, attributes)
2. Device Intelligence (capabilities, health)
3. Data API (metadata)

### Target State
Add 4 enrichment sources (via cached InfluxDB queries):
4. Weather data (temperature, conditions, forecast)
5. Carbon intensity (grid carbon levels)
6. Electricity pricing (current/peak rates)
7. Air quality (AQI, pollutants)

---

## Implementation Strategy

### **Approach: Cached Enrichment (Phase 1)**

**Rationale:**
- Fast: <100ms (read from InfluxDB cache)
- No external API calls needed
- Data already populated by scheduled services
- Minimal latency impact on Ask AI

**Data Freshness:**
- Weather: 15 min (updated every 15 min)
- Carbon: 15 min (updated every 15 min)
- Air Quality: 1 hour (updated hourly)
- Energy Pricing: 1 hour (updated hourly)

---

## Components to Create

### 1. Enrichment Context Fetcher
**File:** `services/ai-automation-service/src/services/enrichment_context_fetcher.py`

**Purpose:** Fetch cached enrichment data from InfluxDB

**Methods:**
- `get_current_weather()` - Latest weather data
- `get_carbon_intensity()` - Current grid carbon level
- `get_electricity_pricing()` - Current energy rates
- `get_air_quality()` - Current AQI
- `get_all_enrichment()` - Fetch all available enrichment

**Performance Target:** <100ms for all data

### 2. Query Intent Classifier
**Location:** `services/ai-automation-service/src/services/enrichment_context_fetcher.py`

**Purpose:** Determine which enrichment data is relevant to the query

**Logic:**
```python
def should_include_weather(query_text, entity_ids):
    # Weather relevant for:
    # - Queries mentioning "weather", "temperature", "cold", "hot"
    # - Entities: climate, thermostat, hvac

def should_include_carbon(query_text, entity_ids):
    # Carbon relevant for:
    # - Queries mentioning "green", "eco", "sustainable", "carbon"
    # - Any schedulable high-power device

def should_include_energy(query_text, entity_ids):
    # Energy relevant for:
    # - Queries mentioning "schedule", "save", "cost", "cheap"
    # - High-power devices: HVAC, EV charger, pool pump

def should_include_air_quality(query_text, entity_ids):
    # Air quality relevant for:
    # - Queries mentioning "air", "purifier", "ventilation"
    # - Entities: fan, air_purifier, climate
```

### 3. Comprehensive Enrichment Integration
**File:** `services/ai-automation-service/src/services/comprehensive_entity_enrichment.py`

**Changes:**
- Update `enrich_entities_comprehensively()` to accept `enrichment_context_fetcher`
- Add enrichment data to entity context
- Include enrichment in prompt formatting

### 4. Ask AI Router Integration
**File:** `services/ai-automation-service/src/api/ask_ai_router.py`

**Changes:**
- Import `EnrichmentContextFetcher`
- Call enrichment fetcher before suggestion generation
- Pass enrichment context to prompt builder
- Include enrichment in LLM context

---

## Data Schema

### Weather Context
```python
{
    "current_temperature": 45.2,      # °F
    "feels_like": 42.0,
    "condition": "Cloudy",
    "humidity": 65,                   # %
    "wind_speed": 10.5,               # mph
    "forecast_1h": 44.0,
    "timestamp": "2025-11-04T10:30:00Z"
}
```

### Carbon Intensity Context
```python
{
    "carbon_intensity": 450,          # gCO2/kWh
    "renewable_percentage": 35.2,     # %
    "fossil_percentage": 64.8,        # %
    "forecast_1h": 420,               # Improving
    "timestamp": "2025-11-04T10:30:00Z"
}
```

### Electricity Pricing Context
```python
{
    "current_price": 0.22,            # $/kWh
    "currency": "USD",
    "peak_period": true,
    "cheapest_hours": [2, 3, 4, 5],   # Hours of day
    "timestamp": "2025-11-04T10:30:00Z"
}
```

### Air Quality Context
```python
{
    "aqi": 85,                        # AQI value
    "category": "Moderate",           # Good/Moderate/Unhealthy
    "pm25": 35,                       # μg/m³
    "pm10": 50,
    "ozone": 45,
    "timestamp": "2025-11-04T10:30:00Z"
}
```

---

## Prompt Enhancement Examples

### Before (No Enrichment)
```
User Query: "Automate my thermostat"

Prompt to OpenAI:
- Office Thermostat (climate.office)
- Capabilities: temperature, hvac_mode
- Current state: off
```

### After (With Enrichment)
```
User Query: "Automate my thermostat"

Prompt to OpenAI:
- Office Thermostat (climate.office)
- Capabilities: temperature, hvac_mode
- Current state: off

Environmental Context:
- Current outdoor temperature: 42°F (feels like 38°F)
- Forecast: Dropping to 28°F tonight (frost warning)
- Grid carbon intensity: 350 gCO2/kWh (35% renewable)
- Electricity rate: $0.22/kWh (peak), off-peak: $0.08/kWh (2-6 AM)

Suggestion opportunity: Consider pre-heating before frost and
scheduling during off-peak hours for cost savings.
```

---

## Performance Impact Analysis

### Current Ask AI Performance
- Entity enrichment: ~500ms
- Total response time: ~1-2s

### With Enrichment (Estimated)
- Cached enrichment fetch: ~50-100ms
- New total response time: ~1.5-2.5s

**Acceptable:** Still under 3s target for interactive queries

---

## Implementation Phases

### Phase 1: Core Infrastructure (This PR)
- ✅ Create `EnrichmentContextFetcher` module
- ✅ Implement InfluxDB cached queries
- ✅ Add query intent classifier
- ✅ Integrate into `comprehensive_entity_enrichment.py`
- ✅ Update Ask AI prompt builder

### Phase 2: Enhancement (Future)
- ⏳ Add historical enrichment patterns (7-day trends)
- ⏳ Implement smart caching layer
- ⏳ Add enrichment quality scoring
- ⏳ Create enrichment visualization in UI

### Phase 3: Advanced Features (Future)
- ⏳ Predictive enrichment (forecast-based suggestions)
- ⏳ Async enrichment with WebSocket updates
- ⏳ User preferences for enrichment types

---

## Testing Strategy

### Unit Tests
- `test_enrichment_context_fetcher.py`
  - Test InfluxDB query construction
  - Test data parsing and normalization
  - Test error handling (no data available)

### Integration Tests
- Test Ask AI with enrichment enabled
- Test selective enrichment loading
- Test prompt generation with enrichment context

### Example Test Queries
1. "Automate thermostat" → Should include weather + energy
2. "Schedule EV charging" → Should include energy + carbon
3. "Automate air purifier" → Should include air quality
4. "Turn on lights when home" → Should NOT include enrichment (not relevant)

---

## Rollout Plan

### Step 1: Feature Flag (Recommended)
```python
ENABLE_ENRICHMENT_CONTEXT = os.getenv('ENABLE_ENRICHMENT_CONTEXT', 'true').lower() == 'true'
```

### Step 2: Gradual Rollout
- Week 1: Enable for 10% of queries (A/B test)
- Week 2: Monitor response times and suggestion quality
- Week 3: Enable for 100% if metrics are positive

### Step 3: Monitoring
- Track enrichment fetch times
- Monitor Ask AI response latency
- Measure suggestion acceptance rate (with vs without enrichment)

---

## Success Metrics

### Performance
- ✅ Ask AI response time < 3s (p95)
- ✅ Enrichment fetch time < 100ms (p95)
- ✅ No increase in error rate

### Quality
- 📈 Suggestion acceptance rate increase > 10%
- 📈 User engagement with enriched suggestions > baseline
- 📈 Automation execution rate increase > 15%

---

## Risks & Mitigations

### Risk 1: InfluxDB Latency
**Mitigation:** Use single-point queries (latest value), fallback to empty enrichment on timeout

### Risk 2: Missing Enrichment Data
**Mitigation:** Graceful degradation - Ask AI works without enrichment

### Risk 3: Increased Response Time
**Mitigation:** Selective loading + feature flag + monitoring

---

## Files to Modify

1. **NEW:** `services/ai-automation-service/src/services/enrichment_context_fetcher.py`
2. **UPDATE:** `services/ai-automation-service/src/services/comprehensive_entity_enrichment.py`
3. **UPDATE:** `services/ai-automation-service/src/api/ask_ai_router.py`
4. **NEW:** `services/ai-automation-service/tests/test_enrichment_context_fetcher.py`
5. **UPDATE:** `.env.example` - Add feature flag

---

## Dependencies

- ✅ InfluxDB client (already available)
- ✅ Weather API service (running, port 8009)
- ✅ Carbon Intensity service (running, port 8010)
- ✅ Air Quality service (running, port 8012)
- ✅ Electricity Pricing service (running, port 8011)

---

## Completion Checklist

- [ ] Create EnrichmentContextFetcher module
- [ ] Implement all enrichment queries
- [ ] Add query intent classifier
- [ ] Integrate into comprehensive enrichment
- [ ] Update Ask AI prompt builder
- [ ] Write unit tests
- [ ] Test with sample queries
- [ ] Add feature flag
- [ ] Update documentation
- [ ] Create PR and push to branch
