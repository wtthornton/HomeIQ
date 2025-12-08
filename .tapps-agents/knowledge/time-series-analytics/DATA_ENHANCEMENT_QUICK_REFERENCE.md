# Data Enhancement Quick Reference
**Visual Guide: Data Sources & Structures**

---

## 📊 15 Additional Data Sources

### ⚡ Energy & Sustainability (5 sources)
```
┌────────────────────────────────────────────────────┐
│ 1. Carbon Intensity (WattTime, ElectricityMap)    │
│    → Enable carbon-aware automation               │
│    → Schedule tasks during cleanest energy        │
│                                                    │
│ 2. Real-Time Electricity Pricing (Awattar)        │
│    → Optimize costs, shift high-energy tasks      │
│    → Respond to demand response events            │
│                                                    │
│ 3. Solar Production (SolarEdge, Enphase)          │
│    → Use excess solar for heating/charging        │
│    → Battery optimization                         │
│                                                    │
│ 4. Smart Meter (Sense, Emporia Vue)               │
│    → Device-level consumption tracking            │
│    → Phantom load detection                       │
│                                                    │
│ 5. Grid Operator Data                             │
│    → Peak demand alerts                           │
│    → Grid stability monitoring                    │
└────────────────────────────────────────────────────┘
```

### 🌤️ Environmental & Air Quality (3 sources)
```
┌────────────────────────────────────────────────────┐
│ 4. Air Quality Index (AirNow, WAQI)               │
│    → Close windows when AQI is poor               │
│    → Control air purifier speed                   │
│                                                    │
│ 5. Pollen & Allergen Data (Ambee)                 │
│    → Adjust ventilation                           │
│    → Send allergy alerts                          │
│                                                    │
│ 6. Barometric Pressure Trends                     │
│    → Migraine warnings                            │
│    → Weather-sensitive health tracking            │
└────────────────────────────────────────────────────┘
```

### 📍 Occupancy & Context (3 sources)
```
┌────────────────────────────────────────────────────┐
│ 6. Calendar Integration (Google/Microsoft)        │
│    → Predictive home preparation                  │
│    → Work-from-home detection                     │
│    → Automatic away mode                          │
│                                                    │
│ 7. Mobile Device Location (Life360, OwnTracks)    │
│    → Proximity-based automation                   │
│    → Geofence triggers                            │
│    → ETA calculations                             │
│                                                    │
│ 8. Sleep Tracking (Oura, Fitbit, Apple Health)    │
│    → Circadian rhythm optimization                │
│    → Gradual wake-up lighting                     │
│    → Sleep quality automation                     │
└────────────────────────────────────────────────────┘
```

### 🚗 Transportation & Services (2 sources)
```
┌────────────────────────────────────────────────────┐
│ 11. Public Transportation (Transit APIs)          │
│     → Adjust departure time for delays            │
│     → Commute optimization                        │
│                                                    │
│ 12. Garbage/Recycling Schedule (Municipal APIs)   │
│     → Night-before reminders                      │
│     → Smart lighting triggers                     │
└────────────────────────────────────────────────────┘
```

### 🏥 Health & Maintenance (2 sources)
```
┌────────────────────────────────────────────────────┐
│ 9. ISP/Network Performance (Speedtest)            │
│    → Failover to backup internet                  │
│    → Bandwidth-aware automation                   │
│                                                    │
│ 15. Appliance Maintenance Tracking                │
│     → Filter replacement reminders                │
│     → Predictive failure detection                │
└────────────────────────────────────────────────────┘
```

---

## 🏗️ 5 Advanced Data Structures

### Current: InfluxDB Time-Series Only
```
[Home Assistant Events] → [InfluxDB] → [Health Dashboard]
                            ↓
                    Time-based queries only
                    No relationships
                    Limited correlations
```

### Enhanced: Hybrid Architecture
```
                    ┌─────────────────┐
                    │  Event Stream   │
                    └────────┬────────┘
                             │
            ┌────────────────┼────────────────┐
            │                │                │
      ┌─────▼─────┐    ┌────▼────┐    ┌────▼────┐
      │ InfluxDB  │    │  Neo4j  │    │ Postgres│
      │Time-Series│    │  Graph  │    │Relations│
      └─────┬─────┘    └────┬────┘    └────┬────┘
            │                │                │
            └────────────────┼────────────────┘
                             │
                    ┌────────▼────────┐
                    │  Unified API    │
                    │ (Read Models)   │
                    └─────────────────┘
                             │
                    ┌────────▼────────┐
                    │  3rd Party Apps │
                    │Node-RED, HA, etc│
                    └─────────────────┘
```

---

### Structure 1: **Neo4j Graph Database** ⭐⭐⭐
**Score: 9/10 | Complexity: 6/10**

```
Use Cases:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ "What devices affect my energy bill?"
✅ "Find all motion sensors that trigger lights"
✅ "Which rooms share HVAC zones?"
✅ "Trace automation chains"
✅ "Recommend automations based on device proximity"

Example Graph:
┌──────────┐  CONTROLS   ┌──────────┐
│Thermostat├────────────►│   HVAC   │
└────┬─────┘             └────┬─────┘
     │                        │
     │ READS_FROM        HEATS│
     │                        │
┌────▼─────┐             ┌───▼──────┐
│TempSensor│             │LivingRoom│
└──────────┘             └──────────┘
     │                        │
     └────────LOCATED_IN──────┘

Query Example (Cypher):
MATCH (motion:Sensor {type: 'motion'})-[*1..3]->(device)
WHERE device.power_rating > 100
RETURN motion.id, device.id, device.power_rating
ORDER BY device.power_rating DESC

Implementation Time: 2-3 weeks
ROI: 4.5x (enables complex automation logic)
```

---

### Structure 2: **Event Sourcing + CQRS** ⭐⭐⭐⭐
**Score: 10/10 | Complexity: 7/10**

```
Concept: Store events, not state
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Current:  state = "on" (overwrites previous)
Enhanced: [DeviceCreated, StateChanged(off→on), 
           StateChanged(on→off), ...]

Benefits:
✅ Complete audit trail
✅ Time-travel debugging
✅ Replay events for ML training
✅ Multiple read models from same data
✅ Never lose data (append-only)

Event Types:
┌───────────────────────────────────────┐
│ • DeviceStateChanged                  │
│ • AutomationTriggered                 │
│ • EnergyThresholdExceeded             │
│ • AnomalyDetected                     │
│ • UserCommandReceived                 │
│ • ScheduledTaskExecuted               │
└───────────────────────────────────────┘

Read Models (CQRS):
┌─────────────────┬──────────────────┐
│CurrentStateModel│HistoricalAnalysis│
├─────────────────┼──────────────────┤
│Fast state lookup│Trend analysis    │
│Simple queries   │Complex aggregates│
│Real-time updates│Pre-computed stats│
└─────────────────┴──────────────────┘

Implementation Time: 3-4 weeks
ROI: 5.0x (enables ML training, debugging)
```

---

### Structure 3: **Materialized Views** ⭐⭐⭐⭐⭐
**Score: 10/10 | Complexity: 4/10**

```
Concept: Pre-compute expensive queries
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Instead of computing on-demand:
SELECT AVG(temp) FROM events 
WHERE timestamp > NOW() - 30 days
GROUP BY entity_id, DATE(timestamp)
(Takes 5 seconds every time)

Pre-compute daily:
CREATE MATERIALIZED VIEW daily_temp_avg ...
(Query takes 50ms)

Examples:
┌──────────────────────────────────────────┐
│ mv_daily_energy_by_device                │
│ mv_hourly_temperature_stats              │
│ mv_room_occupancy_patterns               │
│ mv_device_runtime_hours                  │
│ mv_automation_success_rate               │
└──────────────────────────────────────────┘

Refresh Strategy:
• Incremental: Every hour (recent data)
• Full: Nightly at 3am (all data)
• On-demand: After bulk import

Performance Gain:
Raw Query:   3,500ms ████████████████████
Cached View:    45ms █

Implementation Time: 1-2 weeks
ROI: 6.0x (massive performance improvement)
```

---

### Structure 4: **Entity-Attribute-Value (EAV)** ⭐⭐⭐
**Score: 8/10 | Complexity: 5/10**

```
Concept: Support any device without schema changes
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Traditional:
CREATE TABLE sensors (
  id, temp, humidity, pressure  -- Fixed schema
)
Problem: New device with 'pm25' attribute? 
         Need schema migration!

EAV Pattern:
┌──────────┬────────────┬──────────┐
│entity_id │attribute   │value     │
├──────────┼────────────┼──────────┤
│sensor.1  │temperature │22.5      │
│sensor.1  │humidity    │65        │
│sensor.2  │temperature │21.0      │
│sensor.2  │pm25        │12        │  ← New!
│sensor.3  │co2         │450       │  ← New!
└──────────┴────────────┴──────────┘

Benefits:
✅ Add new devices instantly
✅ No schema migrations
✅ Support vendor-specific attributes
✅ Dynamic querying

Trade-offs:
⚠️ Queries are more complex
⚠️ Need indexing strategy
⚠️ Type safety requires validation

Implementation Time: 2-3 weeks
ROI: 3.5x (flexibility for diverse IoT devices)
```

---

### Structure 5: **TimescaleDB Hybrid** ⭐⭐⭐⭐
**Score: 9/10 | Complexity: 6/10**

```
Concept: Time-series + Relational in one
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Problem: InfluxDB great for time-series, 
         but can't JOIN with metadata

TimescaleDB Solution:
┌────────────────────────────────────────────┐
│ PostgreSQL + Automatic partitioning        │
│ SQL + Time-series optimizations            │
│ JOINs + Continuous aggregates              │
└────────────────────────────────────────────┘

Example Query:
SELECT 
  r.room_name,
  d.device_name,
  AVG(dm.value) as avg_temp
FROM device_measurements dm
JOIN devices d ON dm.device_id = d.id
JOIN rooms r ON d.room_id = r.id
WHERE dm.timestamp > NOW() - INTERVAL '7 days'
AND dm.measurement_type = 'temperature'
GROUP BY r.room_name, d.device_name
ORDER BY avg_temp DESC;

Features:
✅ SQL (everyone knows it)
✅ ACID transactions
✅ Foreign keys
✅ Automatic compression
✅ Continuous aggregates
✅ Retention policies

vs InfluxDB:
┌──────────────┬──────────┬──────────────┐
│Feature       │InfluxDB  │TimescaleDB   │
├──────────────┼──────────┼──────────────┤
│Speed         │⚡⚡⚡    │⚡⚡         │
│SQL Support   │Flux only │Full SQL      │
│JOINs         │Limited   │Native        │
│Relations     │No        │Yes           │
│Learn Curve   │Medium    │Low (SQL)     │
└──────────────┴──────────┴──────────────┘

Implementation Time: 2-3 weeks
ROI: 4.0x (best of both worlds)
```

---

## 🔌 Third-Party Integration Points

### RESTful API v2.0
```http
GET  /api/v2/devices
GET  /api/v2/devices/{id}/history
GET  /api/v2/rooms
GET  /api/v2/rooms/{id}/devices
GET  /api/v2/energy/consumption
GET  /api/v2/automation/rules
POST /api/v2/automation/rules
GET  /api/v2/relationships
POST /api/v2/query
GET  /api/v2/insights/energy-savings
GET  /api/v2/insights/anomalies
GET  /api/v2/external/carbon-intensity
GET  /api/v2/external/electricity-pricing
WS   /api/v2/stream  (WebSocket)
```

### Integration Examples

**Node-RED:**
```
[HTTP Request] → [Parse JSON] → [Filter] → [Automation]
     ↓
GET /api/v2/devices?domain=light&state=on
```

**Home Assistant:**
```yaml
sensor:
  - platform: rest
    resource: https://homeiq/api/v2/energy/consumption
    value_template: "{{ value_json.total_kwh }}"
```

**Python:**
```python
async with aiohttp.ClientSession() as session:
    resp = await session.get(
        f"{API_URL}/api/v2/relationships",
        params={"entity_id": "sensor.temp", "depth": 2}
    )
    relationships = await resp.json()
```

---

## 📈 Value Comparison

### Data Source Impact

```
Carbon Intensity      ████████████ Energy savings 15-30%
Electricity Pricing   ███████████  Cost reduction 20-40%
Calendar Integration  ██████████   Predictive accuracy +60%
Air Quality          █████████    Health improvements
Solar Production     ████████     Self-consumption +45%
Sleep Tracking       ███████      Comfort optimization
Location Data        ███████      Response time -80%
Smart Meter          ██████       Device-level insights
```

### Structure Impact

```
Neo4j Graph          ████████████ Complex queries enabled
Event Sourcing       ███████████  Complete audit trail
Materialized Views   █████████████ 100x query speed
EAV Pattern          ████████     Device flexibility
TimescaleDB          ██████████   SQL + Time-series
```

---

## 🎯 Implementation Priority

### Phase 1: Quick Wins (Month 1)
```
Week 1-2: Add 5 data sources
  ✓ Carbon Intensity
  ✓ Electricity Pricing
  ✓ Air Quality
  ✓ Calendar API
  ✓ Enhanced InfluxDB schema

Week 3-4: Materialized Views
  ✓ Daily energy view
  ✓ Hourly summaries
  ✓ Room occupancy patterns
```

### Phase 2: Advanced Structures (Month 2-3)
```
Week 5-8: Neo4j Graph Database
  ✓ Deploy Neo4j
  ✓ Model relationships
  ✓ Build query API
  ✓ Integration with InfluxDB

Week 9-12: Event Sourcing
  ✓ Event store
  ✓ Event replay
  ✓ Read models (CQRS)
```

### Phase 3: Integration API (Month 4)
```
Week 13-16: REST API v2
  ✓ Comprehensive endpoints
  ✓ WebSocket streaming
  ✓ Documentation
  ✓ Client libraries
```

---

## 💰 ROI Summary

**Investment:** ~$45,000 (9 weeks development)

**Returns Year 1:**
- Energy savings: $2,000-4,000
- Time savings: $5,000
- New capabilities: $10,000+
- 3rd party revenue: $5,000+

**Total ROI:** 150% Year 1, 400% Year 3

---

## 🤔 Decision Matrix

**Choose Graph DB (Neo4j) if:**
- ✅ Need relationship queries
- ✅ Building recommendation engine
- ✅ Complex automation logic
- ✅ Want "what affects what" answers

**Choose Event Sourcing if:**
- ✅ Need audit trail
- ✅ Time-travel debugging required
- ✅ ML training from history
- ✅ Regulatory compliance

**Choose Materialized Views if:**
- ✅ Dashboard performance critical
- ✅ Running same queries repeatedly
- ✅ Need instant reports
- ✅ Limited query variety

**Choose EAV if:**
- ✅ Many device types
- ✅ Frequent new devices
- ✅ Vendor-specific attributes
- ✅ Schema flexibility needed

**Choose TimescaleDB if:**
- ✅ Team knows SQL well
- ✅ Need relational + time-series
- ✅ Complex JOINs required
- ✅ ACID transactions important

---

**Quick Start:** Begin with **Materialized Views** (1-2 weeks, huge performance gain)  
**Best Long-term:** **Neo4j + Event Sourcing** (enables advanced AI/automation)  
**Easiest Migration:** **Add data sources first**, structures second

---

**Document Version:** 1.0  
**Last Updated:** October 10, 2025  

