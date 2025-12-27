# Story AI3.5: Weather Context Integration

**Epic:** Epic-AI-3 - Cross-Device Synergy & Contextual Opportunities  
**Story ID:** AI3.5  
**Priority:** Medium  
**Estimated Effort:** 8-10 hours  
**Dependencies:** Story AI3.1 (Synergy Detector Foundation)

---

## User Story

**As a** user  
**I want** weather-aware automation suggestions  
**so that** my smart home responds intelligently to weather conditions

---

## Business Value

- **Unlocks Enrichment Data:** Weather data already flows into system but unused in automations
- **Climate Intelligence:** Suggests frost protection, pre-heating/cooling, weather-responsive lighting
- **Energy Savings:** Proactive climate adjustments reduce waste
- **Comfort:** Automated responses to weather changes

**Example Suggestions:**
- "Enable frost protection when forecast shows temp < 32°F tonight"
- "Pre-cool house at 2 PM when forecast shows 90°F+ afternoon"
- "Close blinds when UV index >8 (reduce cooling load)"

---

## Acceptance Criteria

### Weather Opportunity Detection

1. ✅ **WeatherOpportunityDetector Class:**
   - Queries weather data from InfluxDB
   - Identifies climate devices (thermostats, HVAC, fans)
   - Detects weather-responsive opportunities
   - Returns ranked weather-aware suggestions

2. ✅ **Weather Patterns to Detect:**
   - **Frost Protection:** Climate device + forecast temp < 32°F
   - **Pre-Heating/Cooling:** Climate device + significant temp change forecast
   - **Weather-Based Lighting:** Outdoor lights + rain/clouds detected
   - **Sun Protection:** Blinds/shades + high UV index or hot afternoon forecast

3. ✅ **Weather Data Sources:**
   - Current conditions (from InfluxDB `weather` measurement)
   - Forecast data (if available)
   - Historical weather patterns (last 30 days)
   - Weather anomalies (sudden changes)

4. ✅ **Opportunity Structure:**
   ```python
   {
       'synergy_type': 'weather_context',
       'device_id': 'climate.living_room',
       'device_name': 'Living Room Thermostat',
       'weather_trigger': {
           'type': 'forecast_temp',
           'condition': 'temp < 32°F',
           'timeframe': 'tonight (6 PM - 6 AM)'
       },
       'suggested_action': 'Set minimum temp to 62°F',
       'benefit': 'Prevent frozen pipes, maintain comfort',
       'impact_score': 0.88,
       'complexity': 'medium',
       'confidence': 0.82
   }
   ```

5. ✅ **Integration with Daily Batch:**
   - Run as part of Phase 3c (Synergy Detection)
   - Query weather data from InfluxDB
   - Detect weather-aware opportunities
   - Store in `synergy_opportunities` table
   - Feed into Phase 5 (Suggestion Generation)

6. ✅ **Graceful Degradation:**
   - If weather data unavailable: Skip weather opportunities (don't fail)
   - If forecast missing: Use current conditions only
   - If InfluxDB query fails: Continue with other synergy types
   - Log warnings but don't block batch job

7. ✅ **Performance:**
   - Weather query <5 seconds
   - Opportunity detection <10 seconds
   - Memory usage <50MB
   - Total addition to batch <15 seconds

8. ✅ **Configuration:**
   - User-configurable weather thresholds
   - Enable/disable weather opportunities
   - Minimum confidence threshold
   - Weather API fallback if InfluxDB stale

---

## Tasks / Subtasks

### Task 1: Create Weather Opportunity Detector (AC: 1, 2)

- [ ] Create `src/contextual_patterns/weather_opportunities.py`
- [ ] Implement `WeatherOpportunityDetector` class
- [ ] Build weather data query from InfluxDB:
  ```python
  async def get_weather_data(self):
      """
      Query last 7 days of weather from InfluxDB
      
      Returns:
      - Current conditions (temp, humidity, conditions)
      - Forecast data (if available)
      - Historical averages
      """
  ```
- [ ] Implement pattern detection methods:
  - [ ] `detect_frost_protection_opportunities()`
  - [ ] `detect_preheating_opportunities()`
  - [ ] `detect_precooling_opportunities()`
  - [ ] `detect_weather_lighting_opportunities()`

### Task 2: Implement Weather Pattern Logic (AC: 2, 3, 4)

**Frost Protection Detection:**
```python
async def detect_frost_protection_opportunities(self):
    """
    Detect when climate devices should enable frost protection.
    
    Conditions:
    - Has climate device (thermostat, HVAC)
    - Forecast shows temp < 32°F in next 12 hours
    - No existing automation for frost protection
    
    Returns: List of frost protection opportunities
    """
    climate_devices = await self._get_climate_devices()
    weather_forecast = await self._get_weather_forecast()
    
    opportunities = []
    for device in climate_devices:
        # Check if frost risk tonight
        if weather_forecast.overnight_low < 32:
            # Check if device already has frost protection automation
            has_automation = await self._check_frost_automation(device['device_id'])
            
            if not has_automation:
                opportunities.append({
                    'synergy_type': 'weather_context',
                    'device_id': device['device_id'],
                    'weather_trigger': {
                        'type': 'forecast_temp',
                        'condition': f"temp < 32°F",
                        'timeframe': 'tonight',
                        'forecast_low': weather_forecast.overnight_low
                    },
                    'suggested_action': 'Enable frost protection (min 62°F)',
                    'impact_score': 0.9,  # High - prevents damage
                    'complexity': 'medium',
                    'confidence': 0.85
                })
    
    return opportunities
```

**Pre-Cooling Detection:**
```python
async def detect_precooling_opportunities(self):
    """
    Detect when to pre-cool before hot afternoon.
    
    Conditions:
    - Has climate device
    - Forecast shows temp >85°F afternoon (12-6 PM)
    - No pre-cooling automation exists
    
    Benefit: Reduce energy by cooling earlier when temps lower
    """
    # Implementation similar to frost protection
    pass
```

### Task 3: Query InfluxDB Weather Data (AC: 3, 5)

- [ ] Create weather data query function
- [ ] Handle missing forecast data gracefully
- [ ] Cache weather data during batch run
- [ ] Parse weather conditions from InfluxDB schema:
  ```python
  # Weather data structure from enrichment-pipeline
  {
      'measurement': 'weather',
      'fields': {
          'temperature': float,
          'humidity': float,
          'conditions': str,
          'forecast_high': float,  # If available
          'forecast_low': float,   # If available
          'uv_index': float
      },
      'time': timestamp
  }
  ```

### Task 4: Integrate with Daily Batch (AC: 5, 6)

- [ ] Modify `src/scheduler/daily_analysis.py`
- [ ] Add weather opportunity detection to Phase 3c:
  ```python
  # Phase 3c: Synergy Detection
  
  # Part A: Device Synergies (AI3.1)
  device_synergies = await device_synergy_detector.detect()
  
  # Part B: Weather Opportunities (AI3.5) - NEW
  try:
      weather_detector = WeatherOpportunityDetector(
          influxdb_client=influxdb_client,
          data_api_client=data_api_client
      )
      weather_opportunities = await weather_detector.detect_opportunities()
      logger.info(f"✅ Found {len(weather_opportunities)} weather opportunities")
  except Exception as e:
      logger.warning(f"⚠️ Weather opportunity detection failed: {e}")
      weather_opportunities = []  # Graceful degradation
  
  # Combine all synergies
  all_synergies = device_synergies + weather_opportunities
  ```

### Task 5: Configuration & Settings (AC: 8)

- [ ] Add to `src/config.py`:
  ```python
  class Settings(BaseSettings):
      # ... existing settings ...
      
      # Weather opportunity settings (Epic AI-3)
      weather_opportunities_enabled: bool = True
      weather_frost_threshold_f: float = 32.0
      weather_heat_threshold_f: float = 85.0
      weather_uv_threshold: float = 8.0
      weather_confidence_threshold: float = 0.7
  ```
- [ ] Document configuration options
- [ ] Add enable/disable toggle

### Task 6: Testing (AC: 6, 7)

- [ ] Unit tests for `WeatherOpportunityDetector`:
  - [ ] Test frost protection detection
  - [ ] Test pre-cooling detection
  - [ ] Test with missing weather data
  - [ ] Test graceful degradation
- [ ] Integration tests:
  - [ ] Test with real InfluxDB weather data
  - [ ] Test batch integration
  - [ ] Test error handling
- [ ] Performance tests:
  - [ ] Measure query time
  - [ ] Measure memory usage
  - [ ] Verify <15 second addition to batch

---

## Dev Notes

### InfluxDB Weather Schema

**Measurement:** `weather`  
**Fields:** temperature, humidity, conditions, forecast_high, forecast_low, uv_index  
**Tags:** location (usually "home")  
**Source:** enrichment-pipeline (websocket-ingestion adds weather data)

**Query Example:**
```python
from influxdb_client import InfluxDBClient

async def query_weather_forecast():
    """Get next 24 hours weather forecast from InfluxDB"""
    query = '''
    from(bucket: "home_assistant_events")
      |> range(start: -1h)
      |> filter(fn: (r) => r["_measurement"] == "weather")
      |> filter(fn: (r) => r["_field"] == "forecast_low" or r["_field"] == "forecast_high")
      |> last()
    '''
    # Returns most recent forecast data
```

### Climate Device Types

**Compatible Domains:**
- `climate.*` - Thermostats, HVAC systems
- `fan.*` - Ceiling fans, portable fans
- `cover.*` - Blinds, shades (for sun protection)
- `switch.*` - Smart plugs controlling heaters/fans

### Weather Opportunity Examples

**1. Frost Protection:**
```python
{
    'device_name': 'Living Room Thermostat',
    'weather_trigger': 'Forecast low 28°F tonight',
    'suggested_action': 'Set minimum temp to 62°F from 10 PM - 6 AM',
    'benefit': 'Prevent frozen pipes, maintain comfort',
    'automation_complexity': 'medium',  # Needs time condition + temp threshold
    'estimated_cost_savings': '$0 (prevents damage)'
}
```

**2. Pre-Cooling:**
```python
{
    'device_name': 'Whole House AC',
    'weather_trigger': 'Forecast high 92°F this afternoon',
    'suggested_action': 'Cool to 72°F at 1 PM (before peak heat)',
    'benefit': 'Reduce energy usage by 15-20% vs cooling at peak',
    'automation_complexity': 'medium',
    'estimated_cost_savings': '$2-3 per hot day'
}
```

**3. Sun Protection:**
```python
{
    'device_name': 'Living Room Blinds',
    'weather_trigger': 'UV index >8, sunny afternoon',
    'suggested_action': 'Close blinds 12 PM - 4 PM',
    'benefit': 'Reduce cooling load, protect furniture',
    'automation_complexity': 'low',
    'estimated_cost_savings': '$1-2 per day in summer'
}
```

### Testing Standards

**Test Location:** `services/ai-automation-service/tests/test_weather_opportunities.py`  
**Framework:** pytest with pytest-asyncio  
**Coverage Target:** >80%

**Mock Weather Data:**
```python
@pytest.fixture
def mock_weather_data():
    return {
        'current_temp': 45.0,
        'forecast_low': 28.0,  # Below freezing
        'forecast_high': 35.0,
        'conditions': 'clear',
        'timestamp': datetime.now()
    }

@pytest.mark.asyncio
async def test_frost_protection_detection(mock_weather_data):
    """Test detection of frost protection opportunity"""
    detector = WeatherOpportunityDetector(influxdb_client, data_api_client)
    
    opportunities = await detector.detect_frost_protection_opportunities()
    
    assert len(opportunities) > 0
    frost_opp = opportunities[0]
    assert frost_opp['synergy_type'] == 'weather_context'
    assert frost_opp['weather_trigger']['condition'] == 'temp < 32°F'
    assert frost_opp['impact_score'] > 0.8  # High impact
```

---

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-10-18 | 1.0 | Initial story creation | BMad Master |

---

**Story Status:** Ready for Development  
**Created:** 2025-10-18

