# Data Sources & Structures Enhancement Guide
**Advanced Data Integration & Relationship Modeling for HA Ingestor**

**Date:** October 10, 2025  
**Purpose:** Identify additional data sources and implement complex relationship structures to enable advanced automation patterns and third-party integrations

---

## 📊 Executive Summary

Your current system collects Home Assistant events + weather data into InfluxDB. This document proposes **15 additional data sources** and **5 advanced data structures** that will:

✅ **Enrich existing data** with contextual information  
✅ **Enable predictive automation** through correlation analysis  
✅ **Provide 3rd party integration points** via standardized APIs  
✅ **Create relationship graphs** for complex automation rules  
✅ **Support advanced AI/ML** through feature engineering

---

## 🌐 Part 1: Additional Data Sources

### Category A: Energy & Sustainability Data

#### 1. **Electricity Grid Carbon Intensity**
**API:** WattTime, ElectricityMap, CO2 Signal  
**Value:** Enable carbon-aware automation

**Data Points:**
- Real-time grid carbon intensity (gCO2/kWh)
- Renewable energy percentage
- Grid frequency and load
- Regional grid operator data
- Future carbon intensity forecasts (24-48h)

**Use Cases:**
```python
# Example: Delay EV charging until lowest carbon intensity
if grid_carbon_intensity < 200:  # gCO2/kWh
    automation.start_ev_charging()
    
# Run dishwasher when renewable energy is highest
if renewable_percentage > 60:
    automation.start_dishwasher()
```

**Integration Complexity:** Low  
**API Cost:** Free tier available  
**Update Frequency:** Every 5-15 minutes

**Implementation:**
```python
# services/carbon-intensity-service/

class CarbonIntensityService:
    """Fetch and cache carbon intensity data"""
    
    async def get_carbon_intensity(self, location: str) -> dict:
        """Get current carbon intensity"""
        # WattTime API
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.watttime.org/v3/forecast",
                params={"region": location},
                headers={"Authorization": f"Bearer {API_TOKEN}"}
            ) as response:
                data = await response.json()
                
        return {
            'carbon_intensity': data['moer'],  # Marginal emissions rate
            'renewable_percentage': data['renewable_pct'],
            'timestamp': data['point_time'],
            'forecast_next_hour': data['forecast'][0]['value']
        }
```

**Schema Extension:**
```
Measurement: energy_carbon_intensity
Tags:
  region: "CA-CAISO"
  grid_operator: "CAISO"
Fields:
  carbon_intensity: 250.5  # gCO2/kWh
  renewable_percentage: 45.2
  fossil_percentage: 54.8
  nuclear_percentage: 0.0
  forecast_1h: 210.0
  forecast_24h: 180.0
```

---

#### 2. **Real-Time Electricity Pricing**
**API:** Awattar, Tibber, Octopus Energy, utility company APIs  
**Value:** Cost optimization for high-energy devices

**Data Points:**
- Current electricity price ($/kWh)
- Time-of-use pricing schedules
- Peak/off-peak designations
- Price forecasts (24-48h)
- Demand response events

**Use Cases:**
```python
# Shift high-energy tasks to cheap hours
if electricity_price < 0.08:  # $/kWh
    automation.preheat_water_heater()
    automation.run_pool_pump()
    automation.charge_ev()

# Respond to demand response events (get paid for reducing usage)
if demand_response_event:
    automation.increase_thermostat(2)  # Reduce AC load
    automation.pause_non_essential_devices()
```

**Integration Complexity:** Medium (varies by utility)  
**API Cost:** Usually free with account  
**Update Frequency:** Hourly or real-time

**Implementation:**
```python
class ElectricityPricingService:
    """Track real-time electricity pricing"""
    
    async def get_current_pricing(self) -> dict:
        """Get current and forecasted prices"""
        return {
            'current_price': 0.12,  # $/kWh
            'currency': 'USD',
            'peak_period': False,
            'forecast_24h': [
                {'hour': 0, 'price': 0.08},
                {'hour': 1, 'price': 0.07},
                # ... 24 hours
            ],
            'cheapest_hours': [2, 3, 4],  # 2am-5am
            'most_expensive_hours': [17, 18, 19]  # 5pm-8pm
        }
```

---

#### 3. **Solar Production Data**
**API:** PVOutput, SolarEdge, Enphase, Tesla Powerwall  
**Value:** Solar production forecasting and optimization

**Data Points:**
- Current solar production (W)
- Daily/monthly generation (kWh)
- Solar irradiance
- Panel efficiency
- Battery state of charge (if applicable)
- Production forecasts

**Use Cases:**
```python
# Use excess solar for hot water heating
if solar_production > home_consumption + 2000:  # 2kW excess
    automation.heat_water_with_excess_solar()

# Discharge battery during peak pricing
if electricity_price > 0.25 and battery_soc > 80:
    automation.discharge_battery()
```

**Schema:**
```
Measurement: solar_production
Tags:
  inverter_id: "solar_inverter_1"
  panel_array: "south_roof"
Fields:
  production_w: 4500
  daily_generation_kwh: 32.5
  panel_efficiency: 18.5
  irradiance: 850  # W/m²
  forecast_next_hour: 4200
```

---

### Category B: Environmental & Air Quality

#### 4. **Air Quality Index (AQI)**
**API:** AirNow, OpenAQ, WAQI, PurpleAir  
**Value:** Health-based automation decisions

**Data Points:**
- AQI score (0-500 scale)
- PM2.5, PM10 concentrations
- Ozone (O3) levels
- NO2, SO2, CO levels
- Pollen count
- UV index

**Use Cases:**
```python
# Close windows when air quality is poor
if aqi > 150:  # Unhealthy
    automation.close_all_windows()
    automation.set_hvac_to_recirculate()
    automation.increase_air_purifier_speed()

# Limit outdoor activities
if aqi > 100:
    automation.send_notification("Poor air quality - avoid outdoor exercise")
```

**Integration Complexity:** Low  
**API Cost:** Free  
**Update Frequency:** Hourly

---

#### 5. **Pollen & Allergen Data**
**API:** Ambee, Tomorrow.io, Weather.com  
**Value:** Allergy management automation

**Data Points:**
- Pollen count by type (grass, tree, weed)
- Mold spore count
- Allergen risk levels
- Forecasts

**Use Cases:**
```python
# Adjust ventilation based on pollen levels
if pollen_count['grass'] > 'HIGH':
    automation.close_fresh_air_intake()
    automation.increase_hvac_filtration()
    automation.send_allergy_alert()
```

---

### Category C: Occupancy & Context

#### 6. **Calendar Integration (Google/Microsoft)**
**API:** Google Calendar API, Microsoft Graph API  
**Value:** Predictive occupancy and smart scheduling

**Data Points:**
- Upcoming events and meetings
- Location data (home, office, away)
- Travel time to next event
- Busy/free status
- Work from home days

**Use Cases:**
```python
# Prepare home before arrival
if next_calendar_event.location == "HOME" and travel_time == 15:
    automation.set_thermostat_to_comfortable()
    automation.turn_on_entry_lights()
    automation.start_coffee_maker()

# Energy savings when calendar shows away
if calendar.away_all_day():
    automation.set_thermostat_to_eco()
    automation.turn_off_non_essential_devices()
```

**Integration Complexity:** Medium (OAuth required)  
**API Cost:** Free  
**Update Frequency:** Real-time or hourly

**Implementation:**
```python
class CalendarService:
    """Google Calendar integration"""
    
    async def get_today_events(self) -> list:
        """Get today's calendar events"""
        service = build('calendar', 'v3', credentials=self.creds)
        
        events_result = service.events().list(
            calendarId='primary',
            timeMin=datetime.now().isoformat() + 'Z',
            maxResults=10,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        return [{
            'summary': event['summary'],
            'location': event.get('location', 'Unknown'),
            'start': event['start']['dateTime'],
            'end': event['end']['dateTime'],
            'is_work_from_home': 'WFH' in event['summary'].upper()
        } for event in events_result.get('items', [])]
    
    async def predict_home_arrival(self) -> dict:
        """Predict when user will arrive home"""
        events = await self.get_today_events()
        
        # Find last event with location != HOME
        last_away_event = None
        for event in reversed(events):
            if event['location'] != 'HOME':
                last_away_event = event
                break
        
        if last_away_event:
            # Estimate travel time using Google Maps API
            travel_time = await self.get_travel_time(
                last_away_event['location'],
                'HOME'
            )
            
            estimated_arrival = last_away_event['end'] + travel_time
            return {
                'estimated_arrival': estimated_arrival,
                'confidence': 0.85,
                'travel_time_minutes': travel_time.total_seconds() / 60
            }
```

**Schema:**
```
Measurement: occupancy_predictions
Tags:
  source: "calendar"
  user: "primary"
Fields:
  currently_home: false
  expected_arrival: "2025-10-10T18:30:00Z"
  travel_time_minutes: 25
  confidence: 0.85
  away_duration_hours: 9.5
```

---

#### 7. **Mobile Device Location**
**API:** Home Assistant Mobile App, OwnTracks, Life360  
**Value:** Precise occupancy and proximity automation

**Data Points:**
- GPS coordinates
- Proximity to home/zones
- Battery level
- Activity (driving, walking, stationary)
- Geofence triggers

**Use Cases:**
```python
# Start heating/cooling before arrival
if distance_from_home < 5 and moving_towards_home:
    automation.prepare_home_for_arrival()

# Security when everyone leaves
if all_users_away():
    automation.enable_security_mode()
    automation.set_thermostat_to_away()
```

---

### Category D: External Services & IoT

#### 8. **Smart Meter Data**
**API:** Utility company APIs, Sense, Emporia Vue  
**Value:** Real-time energy consumption by device

**Data Points:**
- Whole-home power consumption (W)
- Device-level consumption
- Peak demand tracking
- Cost calculations
- Usage patterns

**Use Cases:**
```python
# Detect phantom loads
if hour == 3 and power_consumption > 200:  # 3am baseline
    automation.identify_phantom_loads()
    automation.send_alert("Unusual power usage detected")

# Load shedding
if peak_demand > 10000:  # 10kW
    automation.shed_non_essential_loads()
```

**Schema:**
```
Measurement: smart_meter_data
Tags:
  meter_id: "main_panel"
  circuit: "whole_home"
Fields:
  power_w: 2450
  voltage: 240
  current_a: 10.2
  power_factor: 0.98
  daily_kwh: 45.3
  estimated_cost_today: 5.43
```

---

#### 9. **ISP/Network Performance**
**API:** Speedtest, ISP APIs, Router metrics  
**Value:** Network-aware automation

**Data Points:**
- Internet speed (up/down)
- Latency, jitter
- Packet loss
- Bandwidth usage
- Service outages

**Use Cases:**
```python
# Switch to backup internet if primary fails
if internet_down_duration > 60:  # 1 minute
    automation.switch_to_lte_backup()
    automation.notify_users("Switched to backup internet")

# Defer updates during video calls
if bandwidth_usage > 80_percent and video_call_active:
    automation.defer_system_updates()
```

---

#### 10. **Garbage/Recycling Schedule**
**API:** Waste management company APIs, local municipality  
**Value:** Automated reminders and smart scheduling

**Data Points:**
- Collection day/time
- Type (trash, recycling, compost)
- Special pickups
- Holidays affecting schedule

**Use Cases:**
```python
# Night-before reminder
if tomorrow_is_garbage_day():
    automation.send_reminder("Take out garbage tonight")
    automation.turn_on_garage_light_at_sunset()
```

---

### Category E: Financial & Market Data

#### 11. **Cryptocurrency/Stock Prices**
**API:** CoinGecko, Alpha Vantage, Yahoo Finance  
**Value:** Context for financial decision automation

**Data Points:**
- Crypto/stock prices
- Portfolio value
- Market volatility
- Trading volumes

**Use Cases:**
```python
# Visual indicators
if bitcoin_price > target_price:
    automation.set_office_lights_green()  # Portfolio up
elif bitcoin_price < stop_loss:
    automation.set_office_lights_red()  # Alert
```

---

#### 12. **Public Transportation Data**
**API:** Transit APIs, Uber/Lyft, local transit authority  
**Value:** Commute optimization

**Data Points:**
- Next bus/train arrival times
- Service delays
- Route disruptions
- Ride-share pricing surge

**Use Cases:**
```python
# Adjust departure time based on transit delays
if next_train_delayed > 10_minutes:
    automation.delay_morning_routine(10)
    automation.send_notification("Train delayed - adjust schedule")
```

---

### Category F: Health & Wellness

#### 13. **Sleep Tracking Data**
**API:** Fitbit, Oura Ring, Apple Health, Withings  
**Value:** Circadian rhythm optimization

**Data Points:**
- Sleep stages (deep, REM, light)
- Sleep quality score
- Wake-up time
- Heart rate variability
- Respiratory rate

**Use Cases:**
```python
# Gradual wake-up lighting
if sleep_stage == "LIGHT" and within_30min_of_alarm:
    automation.gradually_brighten_bedroom_lights()

# Optimize bedroom conditions
if sleep_quality < 70:
    automation.adjust_bedroom_temperature(-1)
    automation.increase_white_noise()
```

**Schema:**
```
Measurement: sleep_data
Tags:
  user: "primary"
  device: "oura_ring"
Fields:
  sleep_quality_score: 85
  deep_sleep_minutes: 95
  rem_sleep_minutes: 110
  light_sleep_minutes: 240
  wake_time: "2025-10-10T07:15:00Z"
  hrv: 55
  resting_hr: 52
```

---

#### 14. **Air Pressure / Barometric Trends**
**API:** Weather APIs with barometric data  
**Value:** Health correlation (migraines, joint pain)

**Data Points:**
- Barometric pressure
- Pressure change rate
- Pressure trends (rising/falling)

**Use Cases:**
```python
# Migraine warning
if pressure_drop_rate > 5:  # hPa/hour
    automation.send_health_alert("Rapid pressure drop - migraine risk")
    automation.dim_lights()
    automation.reduce_noise()
```

---

#### 15. **Appliance Maintenance Tracking**
**API:** Manual input, smart appliance APIs  
**Value:** Predictive maintenance

**Data Points:**
- Filter replacement dates
- Last maintenance date
- Runtime hours
- Error codes
- Warranty expiration

**Use Cases:**
```python
# Remind to replace HVAC filter
if hvac_filter_days > 90:
    automation.send_reminder("Time to replace HVAC filter")
    automation.order_filter_on_amazon()

# Predict appliance failure
if washer_vibration_anomaly and age_years > 8:
    automation.alert_potential_failure("Washer showing unusual vibration")
```

---

## 🏗️ Part 2: Advanced Data Structures

### Current Structure: InfluxDB Time-Series (Good for time-based queries)

```
Strengths:
✅ Fast time-range queries
✅ Automatic downsampling
✅ Compression
✅ Tag-based filtering

Limitations:
❌ No complex relationships
❌ Difficult joins across measurements
❌ No graph traversal
❌ Limited event correlation
```

### Proposed: Hybrid Architecture

---

## Structure 1: **Graph Database Layer (Neo4j)**

**Purpose:** Model complex relationships between entities, devices, rooms, users, and events

**Why Add This:**
- Represent device dependencies (e.g., "thermostat controls HVAC which affects bedroom temperature")
- Trace automation chains (e.g., "motion sensor → light → energy consumption")
- Enable question-answering: "What affects my energy bill?"
- Support recommendation systems
- Enable complex path finding

**Implementation:**

```python
# services/graph-database-service/

from neo4j import GraphDatabase

class HomeAutomationGraph:
    """Neo4j graph database for relationship modeling"""
    
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    async def create_device_relationships(self):
        """Model home automation relationships"""
        with self.driver.session() as session:
            # Create device nodes
            session.run("""
                CREATE (thermostat:Device {
                    id: 'climate.living_room',
                    type: 'thermostat',
                    location: 'living_room'
                })
                
                CREATE (hvac:Device {
                    id: 'hvac_system',
                    type: 'hvac',
                    power_rating: 3500
                })
                
                CREATE (temp_sensor:Sensor {
                    id: 'sensor.living_room_temp',
                    type: 'temperature'
                })
                
                CREATE (motion:Sensor {
                    id: 'binary_sensor.living_room_motion',
                    type: 'motion'
                })
                
                CREATE (room:Room {
                    name: 'living_room',
                    size_sqft: 350
                })
                
                // Create relationships
                CREATE (thermostat)-[:CONTROLS]->(hvac)
                CREATE (thermostat)-[:READS_FROM]->(temp_sensor)
                CREATE (temp_sensor)-[:LOCATED_IN]->(room)
                CREATE (motion)-[:LOCATED_IN]->(room)
                CREATE (hvac)-[:HEATS]->(room)
                CREATE (hvac)-[:CONSUMES {unit: 'kWh'}]->(energy:Resource {type: 'electricity'})
                
                // Occupancy affects temperature
                CREATE (motion)-[:INDICATES_OCCUPANCY_IN]->(room)
                CREATE (room)-[:AFFECTS_COMFORT_VIA]->(thermostat)
            """)
    
    async def find_energy_consumers(self, threshold_watts: int):
        """Find all devices consuming energy above threshold"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (device:Device)-[:CONSUMES]->(energy:Resource {type: 'electricity'})
                WHERE device.power_rating > $threshold
                RETURN device.id AS device_id, 
                       device.power_rating AS power,
                       device.location AS location
                ORDER BY power DESC
            """, threshold=threshold_watts)
            
            return [dict(record) for record in result]
    
    async def find_automation_chain(self, trigger_entity: str, target_entity: str):
        """Find automation chain from trigger to target"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH path = (trigger {id: $trigger})-[*1..5]->(target {id: $target})
                RETURN path
                LIMIT 10
            """, trigger=trigger_entity, target=target_entity)
            
            chains = []
            for record in result:
                path = record['path']
                chain = []
                for node in path.nodes:
                    chain.append({
                        'id': node['id'],
                        'type': list(node.labels)[0]
                    })
                chains.append(chain)
            
            return chains
    
    async def recommend_automation(self, room: str):
        """Recommend automation based on device relationships"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (room:Room {name: $room})
                MATCH (device)-[:LOCATED_IN]->(room)
                MATCH (device)-[r]->(other)
                WHERE type(r) IN ['CONTROLS', 'AFFECTS', 'TRIGGERS']
                RETURN device.id AS device,
                       type(r) AS relationship,
                       other.id AS related_device,
                       other.type AS related_type
            """, room=room)
            
            recommendations = []
            for record in result:
                recommendations.append({
                    'suggestion': f"Create automation: {record['device']} {record['relationship']} {record['related_device']}",
                    'confidence': 0.75
                })
            
            return recommendations
```

**Graph Schema Example:**

```cypher
// Rooms and zones
(living_room:Room {name: 'living_room', size: 350})
(bedroom:Room {name: 'bedroom', size: 200})
(home:Zone {name: 'home', type: 'house'})

// Devices
(thermostat:Device:Thermostat {id: 'climate.living_room'})
(hvac:Device:HVAC {power_rating: 3500})
(lamp:Device:Light {power_rating: 60})
(motion:Sensor:Motion {id: 'binary_sensor.motion_living'})

// Users
(user:Person {name: 'primary_user'})

// Resources
(electricity:Resource {type: 'electricity', unit: 'kWh'})
(gas:Resource {type: 'gas', unit: 'therms'})

// Relationships
(thermostat)-[:CONTROLS]->(hvac)
(hvac)-[:HEATS]->(living_room)
(hvac)-[:CONSUMES {rate_kwh: 3.5}]->(electricity)
(motion)-[:LOCATED_IN]->(living_room)
(motion)-[:DETECTED_BY]->(user)
(user)-[:PREFERS_TEMP {value: 72, unit: 'F'}]->(living_room)
(lamp)-[:ILLUMINATES]->(living_room)
(lamp)-[:TRIGGERED_BY]->(motion)
(living_room)-[:PART_OF]->(home)
```

**Query Examples:**

```cypher
// Find all devices that affect energy consumption in living room
MATCH (room:Room {name: 'living_room'})<-[:HEATS|ILLUMINATES]-(device)
MATCH (device)-[:CONSUMES]->(electricity:Resource)
RETURN device.id, device.power_rating
ORDER BY device.power_rating DESC

// Find automation chains (what happens when motion is detected?)
MATCH path = (motion:Sensor {type: 'motion'})-[*1..4]->(target)
RETURN path

// Find rooms that share devices
MATCH (room1:Room)<-[:LOCATED_IN]-(device)-[:AFFECTS]->(room2:Room)
WHERE room1 <> room2
RETURN room1.name, device.id, room2.name

// Recommend energy savings
MATCH (device:Device)-[:CONSUMES]->(electricity)
WHERE device.power_rating > 1000
MATCH (device)-[:LOCATED_IN]->(room)
MATCH (sensor:Sensor {type: 'motion'})-[:LOCATED_IN]->(room)
RETURN "Turn off " + device.id + " when no motion detected in " + room.name AS recommendation
```

**Benefits:**
- Answer questions like "What affects my bedroom temperature?"
- Find circular dependencies in automations
- Discover unused devices
- Recommend automations based on device proximity
- Trace energy consumption chains

---

## Structure 2: **Event Sourcing + CQRS Pattern**

**Purpose:** Complete event history with time-travel capabilities

**Why Add This:**
- Never lose data (append-only)
- Audit trail for all state changes
- Rebuild state at any point in time
- Support multiple read models
- Enable event replay for ML training

**Implementation:**

```python
# services/event-store/

from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any
import json

@dataclass
class DomainEvent:
    """Base class for all domain events"""
    event_id: str
    event_type: str
    aggregate_id: str
    aggregate_type: str
    timestamp: datetime
    data: Dict[str, Any]
    metadata: Dict[str, Any]
    version: int

class EventStore:
    """Append-only event store"""
    
    def __init__(self, influxdb_client):
        self.client = influxdb_client
    
    async def append_event(self, event: DomainEvent):
        """Append event to store (immutable)"""
        point = Point("domain_events") \
            .tag("aggregate_type", event.aggregate_type) \
            .tag("aggregate_id", event.aggregate_id) \
            .tag("event_type", event.event_type) \
            .field("event_id", event.event_id) \
            .field("data", json.dumps(event.data)) \
            .field("metadata", json.dumps(event.metadata)) \
            .field("version", event.version) \
            .time(event.timestamp)
        
        await self.client.write(point)
    
    async def get_events_for_aggregate(
        self, 
        aggregate_id: str,
        from_version: int = 0
    ) -> List[DomainEvent]:
        """Get all events for an aggregate (entity)"""
        query = f"""
        from(bucket: "events")
          |> range(start: 0)
          |> filter(fn: (r) => 
              r._measurement == "domain_events" and
              r.aggregate_id == "{aggregate_id}" and
              r.version > {from_version}
          )
          |> sort(columns: ["version"])
        """
        
        tables = await self.client.query(query)
        events = []
        
        for record in tables:
            events.append(DomainEvent(
                event_id=record['event_id'],
                event_type=record['event_type'],
                aggregate_id=record['aggregate_id'],
                aggregate_type=record['aggregate_type'],
                timestamp=record['_time'],
                data=json.loads(record['data']),
                metadata=json.loads(record['metadata']),
                version=record['version']
            ))
        
        return events
    
    async def rebuild_aggregate_state(
        self, 
        aggregate_id: str
    ) -> Dict[str, Any]:
        """Rebuild current state by replaying all events"""
        events = await self.get_events_for_aggregate(aggregate_id)
        
        state = {}
        for event in events:
            # Apply event to state
            state = self._apply_event(state, event)
        
        return state
    
    def _apply_event(self, state: dict, event: DomainEvent) -> dict:
        """Apply single event to state"""
        if event.event_type == "DeviceStateChanged":
            state['current_state'] = event.data['new_state']
            state['last_changed'] = event.timestamp
        elif event.event_type == "DeviceConfigured":
            state['configuration'] = event.data['config']
        # ... more event types
        
        return state

# Example domain events
class DeviceStateChangedEvent(DomainEvent):
    """Device state changed"""
    pass

class AutomationTriggeredEvent(DomainEvent):
    """Automation was triggered"""
    pass

class EnergyThresholdExceededEvent(DomainEvent):
    """Energy usage exceeded threshold"""
    pass

# Usage
event_store = EventStore(influxdb_client)

# Record events
await event_store.append_event(DeviceStateChangedEvent(
    event_id="evt_12345",
    event_type="DeviceStateChanged",
    aggregate_id="switch.living_room_lamp",
    aggregate_type="Device",
    timestamp=datetime.now(),
    data={
        'old_state': 'off',
        'new_state': 'on',
        'triggered_by': 'automation.evening_lights'
    },
    metadata={
        'user': 'system',
        'source': 'automation'
    },
    version=152
))

# Rebuild state at any point in time
historical_state = await event_store.rebuild_aggregate_state(
    "switch.living_room_lamp"
)
```

**Read Models (CQRS):**

```python
class CurrentStateReadModel:
    """Optimized for current state queries"""
    
    async def get_current_state(self, entity_id: str) -> dict:
        # Fast query from materialized view
        pass

class HistoricalAnalysisReadModel:
    """Optimized for historical analysis"""
    
    async def get_state_changes_count(
        self, 
        entity_id: str,
        start: datetime,
        end: datetime
    ) -> int:
        # Pre-computed aggregates
        pass

class EnergyConsumptionReadModel:
    """Optimized for energy queries"""
    
    async def get_daily_energy_by_device(
        self,
        date: datetime
    ) -> Dict[str, float]:
        # Denormalized for fast energy queries
        pass
```

**Benefits:**
- Complete audit trail
- Time-travel debugging ("What was the state at 3pm yesterday?")
- Event replay for ML model training
- Multiple optimized views of same data
- Never lose data (append-only)

---

## Structure 3: **Entity-Attribute-Value (EAV) + JSON Schema**

**Purpose:** Flexible schema for heterogeneous IoT devices

**Why Add This:**
- Support new device types without schema changes
- Handle device-specific attributes
- Enable dynamic queries
- Support plugin architecture

**Implementation:**

```python
# Flexible entity storage

class DynamicEntityStore:
    """Store any entity with any attributes"""
    
    async def store_entity(
        self,
        entity_id: str,
        entity_type: str,
        attributes: Dict[str, Any]
    ):
        """Store entity with flexible attributes"""
        
        # Core entity record
        await self.db.execute("""
            INSERT INTO entities (entity_id, entity_type, schema_version)
            VALUES (?, ?, ?)
            ON CONFLICT (entity_id) DO UPDATE SET
                entity_type = excluded.entity_type,
                updated_at = NOW()
        """, (entity_id, entity_type, "1.0"))
        
        # Store attributes (EAV pattern)
        for key, value in attributes.items():
            await self.db.execute("""
                INSERT INTO entity_attributes (
                    entity_id, 
                    attribute_name, 
                    attribute_value,
                    attribute_type
                )
                VALUES (?, ?, ?, ?)
                ON CONFLICT (entity_id, attribute_name) DO UPDATE SET
                    attribute_value = excluded.attribute_value,
                    updated_at = NOW()
            """, (
                entity_id, 
                key, 
                json.dumps(value),
                type(value).__name__
            ))
    
    async def get_entity(self, entity_id: str) -> Dict[str, Any]:
        """Reconstruct entity from EAV"""
        attributes = await self.db.fetch("""
            SELECT attribute_name, attribute_value, attribute_type
            FROM entity_attributes
            WHERE entity_id = ?
        """, (entity_id,))
        
        return {
            'entity_id': entity_id,
            'attributes': {
                attr['attribute_name']: json.loads(attr['attribute_value'])
                for attr in attributes
            }
        }
    
    async def query_by_attribute(
        self,
        attribute_name: str,
        attribute_value: Any
    ) -> List[str]:
        """Find entities with specific attribute value"""
        results = await self.db.fetch("""
            SELECT DISTINCT entity_id
            FROM entity_attributes
            WHERE attribute_name = ? 
            AND attribute_value = ?
        """, (attribute_name, json.dumps(attribute_value)))
        
        return [r['entity_id'] for r in results]
```

**Schema:**
```sql
CREATE TABLE entities (
    entity_id VARCHAR(255) PRIMARY KEY,
    entity_type VARCHAR(100),
    schema_version VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE entity_attributes (
    entity_id VARCHAR(255),
    attribute_name VARCHAR(100),
    attribute_value JSONB,
    attribute_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (entity_id, attribute_name),
    FOREIGN KEY (entity_id) REFERENCES entities(entity_id)
);

CREATE INDEX idx_attributes_name_value ON entity_attributes(attribute_name, attribute_value);
```

**Benefits:**
- Add new device types instantly
- No schema migrations for new attributes
- Support vendor-specific features
- Enable dynamic filtering

---

## Structure 4: **Materialized Views & Projections**

**Purpose:** Pre-computed aggregates for fast queries

**Why Add This:**
- Instant dashboards (no computation)
- Complex aggregations pre-calculated
- Support multiple query patterns
- Reduce database load

**Implementation:**

```python
# Pre-computed views updated by events

class MaterializedViewManager:
    """Manage pre-computed views"""
    
    async def update_daily_energy_view(self, date: datetime):
        """Update daily energy consumption view"""
        await self.db.execute("""
            INSERT INTO mv_daily_energy (
                date,
                entity_id,
                total_kwh,
                peak_power_w,
                average_power_w,
                cost_usd
            )
            SELECT 
                DATE(timestamp) as date,
                entity_id,
                SUM(energy_kwh) as total_kwh,
                MAX(power_w) as peak_power_w,
                AVG(power_w) as average_power_w,
                SUM(energy_kwh * electricity_rate) as cost_usd
            FROM energy_measurements
            WHERE DATE(timestamp) = ?
            GROUP BY DATE(timestamp), entity_id
            ON CONFLICT (date, entity_id) DO UPDATE SET
                total_kwh = excluded.total_kwh,
                peak_power_w = excluded.peak_power_w,
                average_power_w = excluded.average_power_w,
                cost_usd = excluded.cost_usd
        """, (date,))
    
    async def get_daily_energy_fast(
        self,
        entity_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict]:
        """Fast query from materialized view"""
        result = await self.db.fetch("""
            SELECT * FROM mv_daily_energy
            WHERE entity_id = ?
            AND date BETWEEN ? AND ?
            ORDER BY date
        """, (entity_id, start_date, end_date))
        
        return [dict(r) for r in result]
```

**Example Views:**

```sql
-- Hourly summary view
CREATE MATERIALIZED VIEW mv_hourly_summary AS
SELECT 
    date_trunc('hour', timestamp) as hour,
    entity_id,
    domain,
    COUNT(*) as event_count,
    AVG(normalized_value) as avg_value,
    MIN(normalized_value) as min_value,
    MAX(normalized_value) as max_value
FROM home_assistant_events
GROUP BY date_trunc('hour', timestamp), entity_id, domain;

-- Room occupancy summary
CREATE MATERIALIZED VIEW mv_room_occupancy AS
SELECT 
    area,
    COUNT(DISTINCT entity_id) as device_count,
    SUM(CASE WHEN state_value = 'on' THEN 1 ELSE 0 END) as active_devices,
    MAX(last_motion_time) as last_activity
FROM home_assistant_events
WHERE domain = 'binary_sensor' AND device_class = 'motion'
GROUP BY area;

-- Energy cost by day/hour
CREATE MATERIALIZED VIEW mv_energy_cost AS
SELECT 
    DATE(timestamp) as date,
    EXTRACT(HOUR FROM timestamp) as hour,
    SUM(energy_kwh * electricity_rate) as cost
FROM energy_measurements
GROUP BY DATE(timestamp), EXTRACT(HOUR FROM timestamp);
```

**Refresh Strategy:**
```python
# Incremental refresh (only new data)
async def refresh_hourly_summary_incremental():
    """Refresh only recent hours"""
    await db.execute("""
        REFRESH MATERIALIZED VIEW CONCURRENTLY mv_hourly_summary
        WHERE hour >= NOW() - INTERVAL '24 hours'
    """)

# Full refresh (nightly)
async def refresh_all_views_nightly():
    """Full refresh during low-traffic hours"""
    await db.execute("REFRESH MATERIALIZED VIEW mv_daily_energy")
    await db.execute("REFRESH MATERIALIZED VIEW mv_room_occupancy")
    await db.execute("REFRESH MATERIALIZED VIEW mv_energy_cost")
```

---

## Structure 5: **Time-Series + Relational Hybrid (TimescaleDB)**

**Purpose:** Combine time-series performance with relational integrity

**Why Add This:**
- ACID transactions on time-series data
- Foreign key relationships
- JOINs between time-series and metadata
- Better data integrity

**Implementation:**

```sql
-- Device metadata (relational)
CREATE TABLE devices (
    device_id VARCHAR(255) PRIMARY KEY,
    device_name VARCHAR(255),
    device_type VARCHAR(100),
    room_id INTEGER REFERENCES rooms(room_id),
    manufacturer VARCHAR(100),
    model VARCHAR(100),
    install_date DATE,
    warranty_expiry DATE,
    power_rating_w INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Room metadata
CREATE TABLE rooms (
    room_id SERIAL PRIMARY KEY,
    room_name VARCHAR(100),
    floor INTEGER,
    size_sqft INTEGER,
    hvac_zone VARCHAR(50)
);

-- Time-series measurements (hypertable)
CREATE TABLE device_measurements (
    timestamp TIMESTAMPTZ NOT NULL,
    device_id VARCHAR(255) REFERENCES devices(device_id),
    measurement_type VARCHAR(50),
    value DOUBLE PRECISION,
    unit VARCHAR(20),
    quality INTEGER,  -- 0-100
    PRIMARY KEY (timestamp, device_id, measurement_type)
);

-- Convert to hypertable (TimescaleDB)
SELECT create_hypertable('device_measurements', 'timestamp');

-- Create continuous aggregates
CREATE MATERIALIZED VIEW device_hourly_avg
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 hour', timestamp) AS bucket,
    device_id,
    measurement_type,
    AVG(value) as avg_value,
    MIN(value) as min_value,
    MAX(value) as max_value,
    COUNT(*) as sample_count
FROM device_measurements
GROUP BY bucket, device_id, measurement_type;

-- Refresh policy
SELECT add_continuous_aggregate_policy('device_hourly_avg',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');
```

**Query Examples:**

```sql
-- Join time-series with metadata
SELECT 
    d.device_name,
    d.room_id,
    r.room_name,
    dm.timestamp,
    dm.value,
    dm.unit
FROM device_measurements dm
JOIN devices d ON dm.device_id = d.device_id
JOIN rooms r ON d.room_id = r.room_id
WHERE dm.timestamp > NOW() - INTERVAL '24 hours'
AND r.room_name = 'living_room';

-- Energy consumption by room
SELECT 
    r.room_name,
    SUM(dm.value * d.power_rating_w / 1000.0) as total_kwh
FROM device_measurements dm
JOIN devices d ON dm.device_id = d.device_id
JOIN rooms r ON d.room_id = r.room_id
WHERE dm.measurement_type = 'runtime_hours'
AND dm.timestamp > NOW() - INTERVAL '30 days'
GROUP BY r.room_name
ORDER BY total_kwh DESC;

-- Devices due for maintenance
SELECT 
    d.device_name,
    d.device_type,
    r.room_name,
    d.install_date,
    AGE(NOW(), d.install_date) as age
FROM devices d
JOIN rooms r ON d.room_id = r.room_id
WHERE d.warranty_expiry < NOW() + INTERVAL '30 days'
OR AGE(NOW(), d.install_date) > INTERVAL '5 years';
```

---

## 🔌 Part 3: Third-Party Integration Architecture

### API Design for 3rd Party Automation

```python
# services/integration-api/

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(
    title="HA Ingestor Integration API",
    version="2.0",
    description="Comprehensive API for 3rd party automation platforms"
)

# Standardized response models
class DeviceState(BaseModel):
    entity_id: str
    state: str
    attributes: dict
    last_changed: datetime
    last_updated: datetime

class AutomationRule(BaseModel):
    rule_id: str
    trigger: dict
    condition: dict
    action: dict
    enabled: bool

class DataQuery(BaseModel):
    measurement: str
    filters: dict
    time_range: dict
    aggregation: Optional[str]

# Endpoints for 3rd party platforms

@app.get("/api/v2/devices")
async def list_devices(
    domain: Optional[str] = None,
    room: Optional[str] = None
) -> List[DeviceState]:
    """List all devices with current state"""
    # Returns device list with complete state
    pass

@app.get("/api/v2/devices/{entity_id}/history")
async def get_device_history(
    entity_id: str,
    start: datetime,
    end: datetime,
    granularity: str = "5m"
) -> List[dict]:
    """Get historical data for device"""
    # Returns time-series data
    pass

@app.get("/api/v2/rooms")
async def list_rooms() -> List[dict]:
    """List all rooms with devices"""
    # Returns room hierarchy from graph DB
    pass

@app.get("/api/v2/rooms/{room_id}/devices")
async def get_room_devices(room_id: str) -> List[DeviceState]:
    """Get all devices in a room"""
    pass

@app.get("/api/v2/energy/consumption")
async def get_energy_consumption(
    start: datetime,
    end: datetime,
    group_by: str = "device"  # device, room, hour, day
) -> dict:
    """Get energy consumption data"""
    # Returns aggregated energy data
    pass

@app.get("/api/v2/automation/rules")
async def list_automation_rules() -> List[AutomationRule]:
    """List all automation rules"""
    pass

@app.post("/api/v2/automation/rules")
async def create_automation_rule(rule: AutomationRule) -> dict:
    """Create new automation rule"""
    # Allows 3rd parties to create automations
    pass

@app.get("/api/v2/relationships")
async def query_relationships(
    entity_id: str,
    relationship_type: Optional[str] = None,
    depth: int = 1
) -> dict:
    """Query Neo4j for entity relationships"""
    # Returns graph of related entities
    pass

@app.post("/api/v2/query")
async def execute_custom_query(query: DataQuery) -> List[dict]:
    """Execute custom data query"""
    # Flexible query endpoint
    pass

@app.websocket("/api/v2/stream")
async def websocket_stream(
    websocket: WebSocket,
    filters: Optional[str] = None
):
    """Real-time event stream"""
    await websocket.accept()
    
    # Stream events matching filters
    async for event in event_stream:
        if matches_filters(event, filters):
            await websocket.send_json(event)

@app.get("/api/v2/insights/energy-savings")
async def get_energy_savings_recommendations() -> List[dict]:
    """Get AI-powered energy saving recommendations"""
    # Returns ML-generated recommendations
    pass

@app.get("/api/v2/insights/anomalies")
async def get_anomalies(
    lookback_hours: int = 24
) -> List[dict]:
    """Get detected anomalies"""
    # Returns anomalies from ML service
    pass

@app.get("/api/v2/external/carbon-intensity")
async def get_carbon_intensity() -> dict:
    """Get current carbon intensity"""
    # Exposes external data source
    pass

@app.get("/api/v2/external/electricity-pricing")
async def get_electricity_pricing() -> dict:
    """Get current electricity pricing"""
    # Exposes pricing data
    pass
```

### Integration Examples

**Node-RED Flow:**
```json
{
  "flow": [
    {
      "type": "http request",
      "url": "https://homeiq/api/v2/devices",
      "method": "GET",
      "headers": {"Authorization": "Bearer TOKEN"}
    },
    {
      "type": "function",
      "func": "msg.payload = msg.payload.filter(d => d.state === 'on'); return msg;"
    },
    {
      "type": "http request",
      "url": "https://homeiq/api/v2/automation/rules",
      "method": "POST",
      "payload": "automation_rule"
    }
  ]
}
```

**Home Assistant Integration:**
```yaml
# configuration.yaml
sensor:
  - platform: rest
    resource: https://homeiq/api/v2/energy/consumption
    name: "Total Energy Today"
    value_template: "{{ value_json.total_kwh }}"
    unit_of_measurement: "kWh"

automation:
  - alias: "Low Carbon Automation"
    trigger:
      - platform: rest
        resource: https://homeiq/api/v2/external/carbon-intensity
    condition:
      - condition: template
        value_template: "{{ states('sensor.carbon_intensity') | int < 200 }}"
    action:
      - service: switch.turn_on
        entity_id: switch.ev_charger
```

**Python Script Integration:**
```python
import aiohttp

class HAIngestorClient:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {api_key}"}
    
    async def get_room_temperature(self, room_name):
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/api/v2/rooms/{room_name}/devices",
                headers=self.headers
            ) as response:
                devices = await response.json()
                
                temp_sensors = [d for d in devices if d['domain'] == 'sensor' and d['device_class'] == 'temperature']
                return sum(float(s['state']) for s in temp_sensors) / len(temp_sensors)
    
    async def create_energy_automation(self):
        rule = {
            "rule_id": "energy_saver_1",
            "trigger": {
                "type": "numeric_state",
                "entity_id": "sensor.electricity_price",
                "below": 0.10
            },
            "condition": {
                "type": "and",
                "conditions": [
                    {"type": "time", "after": "22:00"},
                    {"type": "state", "entity_id": "binary_sensor.someone_home", "state": "on"}
                ]
            },
            "action": {
                "type": "service",
                "service": "switch.turn_on",
                "entity_id": "switch.water_heater"
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/v2/automation/rules",
                json=rule,
                headers=self.headers
            ) as response:
                return await response.json()
```

---

## 📈 Implementation Roadmap

### Phase 1: Quick Data Source Additions (Weeks 1-4)
1. ✅ Carbon Intensity API
2. ✅ Electricity Pricing API
3. ✅ Air Quality API
4. ✅ Calendar Integration
5. ✅ Enhanced schema in InfluxDB

### Phase 2: Graph Database (Weeks 5-8)
1. ✅ Deploy Neo4j container
2. ✅ Model device relationships
3. ✅ Implement relationship queries
4. ✅ Build recommendation engine

### Phase 3: Advanced Structures (Weeks 9-14)
1. ✅ Event sourcing implementation
2. ✅ Materialized views
3. ✅ CQRS read models
4. ✅ TimescaleDB hybrid (optional)

### Phase 4: External Integration API (Weeks 15-18)
1. ✅ REST API v2
2. ✅ WebSocket streaming
3. ✅ Documentation
4. ✅ Client libraries (Python, JS)

---

## 🎯 Success Metrics

**Data Enrichment:**
- 15+ external data sources integrated
- 3x more context per event
- 50% improvement in prediction accuracy

**Query Performance:**
- Relationship queries: <100ms
- Complex aggregations: <500ms (from materialized views)
- Real-time streaming: <50ms latency

**3rd Party Adoption:**
- 5+ integration examples
- Comprehensive API documentation
- Client libraries for 3 languages

---

**Document Version:** 1.0  
**Last Updated:** October 10, 2025  
**Next Review:** January 2026

This enhancement will transform your system from simple event storage to a comprehensive **home intelligence platform**! 🚀

