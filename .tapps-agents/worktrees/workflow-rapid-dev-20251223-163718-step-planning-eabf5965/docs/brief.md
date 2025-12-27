# Project Brief: HA-Ingestor Device Intelligence Enhancement

**Project Name:** HA-Ingestor - AI-Powered Device Intelligence & Automation Optimization  
**Project Type:** Brownfield Enhancement  
**Created:** 2025-01-16  
**Status:** Planning Phase  
**Author:** Business Analyst (Mary)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Problem Statement](#problem-statement)
3. [Proposed Solution](#proposed-solution)
4. [Target Users](#target-users)
5. [Goals & Success Metrics](#goals--success-metrics)
6. [MVP Scope](#mvp-scope)
7. [Post-MVP Vision](#post-mvp-vision)
8. [Technical Considerations & Integration](#technical-considerations--integration)
9. [Resources & References](#resources--references)

---

## Executive Summary

### Overview

**Home Assistant Ingestor** is a production-ready microservices platform that captures, enriches, and stores Home Assistant event data with multi-source integration (weather, sports, energy, air quality). The system currently achieves 99.9% data capture reliability with hybrid database architecture (InfluxDB + SQLite) serving 50-1000+ entity smart homes.

### Core Enhancement Goal

Transform the platform from a **passive data collector** into an **active intelligence layer** that understands device capabilities and provides proactive, device-aware automation suggestions on daily/weekly/monthly/quarterly cadence.

### The Intelligence Gap

While the system captures every state change and event, it lacks understanding of what devices **can do** versus what they **are doing**. For example:

**Current Knowledge:**
- "Inovelli VZM31-SN switch turned on/off"
- "Aqara motion sensor detected movement"
- "IKEA bulb brightness changed to 75%"

**Missing Knowledge:**
- "This Inovelli switch has 7 programmable LEDs, supports 10+ button events, offers smart bulb mode, fan control, power monitoring, and auto-off timers"
- "This Aqara sensor supports configurable sensitivity, detection zones, and approach detection"
- "This IKEA bulb supports color temperature presets and scene memory"

### The Opportunity

**85% of advanced device features go unused** because users don't know they exist. Smart switches capable of LED notifications, multi-tap scenes, and power monitoring are used as simple on/off switches. Presence sensors with configurable sensitivity sit at default settings. Energy monitors track data but never trigger cost-saving automations.

### Primary Problem Being Solved

Users with sophisticated devices (Inovelli switches, Aqara sensors, IKEA bulbs, Xiaomi sensors, etc.) are missing 70-90% of their devices' capabilities because:

1. **They don't know what features exist**
2. **They don't know how to configure them optimally**
3. **They don't get proactive suggestions** based on usage patterns
4. **Generic AI assistants lack device-specific knowledge**

### Target User

Advanced Home Assistant users who have invested in feature-rich devices (50-1000+ entities) but lack the time/knowledge to optimize them. These users want their smart home to **teach them** about their devices and **suggest improvements** based on actual usage patterns.

### Key Enhancement Components

1. **Universal Device Capability Discovery** - Automatically discovers capabilities for ALL Zigbee devices via Zigbee2MQTT MQTT bridge
2. **Intelligent Suggestion Engine** - Analyzes usage patterns + capabilities → recommendations
3. **Proactive Notification System** - Daily/weekly/monthly/quarterly suggestions via HA notifications
4. **Device Intelligence Dashboard** - Visual representation of utilized vs. unutilized capabilities
5. **Multi-Integration Support** - Scalable architecture supporting Zigbee, Z-Wave, WiFi, native HA integrations

### Success Criteria

Within 30 days of deployment:
- **40%+ feature discovery** - Discover and configure at least one previously unknown device feature
- **Device utilization increase** - From ~20% to 25%+ (+5 points minimum)
- **Implementation rate** - Configure 2+ suggested features
- **"Aha moments"** - At least 1 "I didn't know my devices could do that!" experience

### Current System Strengths to Preserve

- ✅ Rock-solid data ingestion (99.9% capture rate)
- ✅ Hybrid database performance (5-10x faster queries)
- ✅ Multi-source enrichment (weather, sports, energy)
- ✅ Production-grade microservices architecture
- ✅ Comprehensive health dashboard

### Enhancement Impact

This shifts the platform from **infrastructure** (data collection) to **intelligence** (proactive optimization), transforming it into an AI-powered smart home advisor that understands both the data AND the devices generating it.

---

## Problem Statement

### Current State & Pain Points

**The Data Collection Paradox:**

The HA-Ingestor system successfully captures 99.9% of Home Assistant events with comprehensive historical storage, multi-source enrichment, and high-performance querying. However, this creates a paradox: **we have all the data but lack the intelligence to tell users what's missing**.

---

### Pain Point #1: The "Invisible Feature" Problem

**Current Reality:**  
Users purchase sophisticated smart devices (Inovelli switches, Aqara sensors, IKEA bulbs, Xiaomi sensors, Shelly relays) but use them as basic on/off switches because they don't know what features exist.

**Concrete Examples:**
- **Inovelli VZM31-SN switches** with 7 programmable LEDs, 10+ button events, smart bulb mode, fan control, and power monitoring → Used only for on/off
- **Aqara presence sensors** with configurable sensitivity, detection zones, and approach detection → Used only for basic motion
- **IKEA TRADFRI bulbs** with color temperature presets, scene memory, and smooth transitions → Used only for brightness
- **Xiaomi door sensors** with vibration detection, tamper alerts, and battery monitoring → Used only for open/close
- **Shelly relays** with power monitoring, temperature sensors, and overpower protection → Used only for switching

**Impact:**
- **Estimated 85% of device capabilities unused**
- Users pay premium prices for advanced features they never discover
- Smart homes remain "dumb" despite sophisticated hardware
- ROI on device investments is <20% of potential

**Quantified Impact:**  
If a user has diverse smart home devices totaling $2,000-$10,000 in investment, they're using ~$400-$2,000 worth of features and wasting $1,600-$8,000 in unused capabilities.

---

### Pain Point #2: No Proactive Discovery Mechanism

**Current Reality:**  
The system knows:
- ✅ Device exists (entity_id: `light.kitchen_switch`)
- ✅ Manufacturer: "Inovelli" (or "Aqara", "IKEA", "Xiaomi", etc.)
- ✅ Model: "VZM31-SN" (or specific model for any brand)
- ✅ State history (on/off, brightness over time)

The system doesn't know:
- ❌ This specific model supports LED notifications
- ❌ User has never configured a double-tap action
- ❌ Smart bulb mode would improve Hue integration
- ❌ Power monitoring could alert on abnormal draw
- ❌ Auto-off timer could save energy in rarely-used rooms

**Impact:**
- **No mechanism to suggest optimizations**
- Users must manually research each device model (every manufacturer)
- Discovery happens by accident (forums, Reddit) or never
- Automation opportunities remain invisible
- System collects patterns but can't act on them

**User Testimony (Hypothetical):**  
> "I've had these devices for 2 years and just discovered they can do so much more. Why didn't my system tell me this works with ALL my devices, not just one brand?"

---

### Pain Point #3: Pattern Recognition Without Action

**Current Reality:**  
The system detects patterns but can't connect them to device capabilities:

**Pattern Detected:** Bathroom light left on >30 minutes, 15 times/month  
**Current Action:** None (just stores the data)  
**Optimal Action:** "Your switch supports auto-off timer. Configure 30-min timeout?"

**Pattern Detected:** Kitchen motion sensor triggers, then manual switch press 2 seconds later  
**Current Action:** None  
**Optimal Action:** "Your Aqara sensor supports approach detection. Enable to trigger lights before you enter?"

**Pattern Detected:** Living room lights turn on/off 8+ times during movie night  
**Current Action:** None  
**Optimal Action:** "Configure double-tap down on any compatible switch to trigger 'Movie Mode' scene?"

**Impact:**
- **Analytics without actionability**
- Insights remain locked in InfluxDB
- Users see patterns in dashboards but don't know how to act
- No guidance on which patterns matter most
- Opportunity cost: ~10-20 automation improvements/month missed

---

### Pain Point #4: Generic Device Knowledge

**Current Reality:**  
The AI automation service generates pattern-based suggestions but lacks:
- **Device-specific knowledge** of what your actual hardware supports (across ALL brands)
- **Manufacturer feature sets** (Inovelli vs. Aqara vs. IKEA vs. Xiaomi differences)
- **Integration context** (Zigbee2MQTT vs. ZWave vs. native HA capabilities)
- **Current configuration state** (what's already enabled vs. available)

**Example of Generic vs. Device-Aware Suggestions:**

**Generic AI (Current):**  
> "You could automate your lights based on motion"

**Device-Aware AI (Proposed - Works for ALL Brands):**  
> **For your Inovelli VZM31-SN in kitchen:**
> - Supports LED notifications → Show red when garage open
> - Has 10+ button events → Double-tap up = cooking scene
> - Power monitoring enabled but not used → Alert if >500W
> - Pattern detected: On 6am daily → Auto-on at sunrise instead?
> 
> **For your Aqara MCCGQ11LM door sensor:**
> - Supports vibration detection → Enable for break-in attempts
> - Battery monitoring available → Low battery alerts
> - Pattern detected: Door opens 6:00-6:15am daily → Morning routine trigger?
>
> **For your IKEA LED1624G9 bulb:**
> - Supports color temperature presets → Configure warm/cool scenes
> - Has smooth transitions → Enable for gradual wake-up
> - Pattern detected: Brightness adjusts 3+ times nightly → Create bedtime scene?

**Impact:**
- **Low suggestion adoption** because generic suggestions don't match specific hardware
- Users waste time implementing suggestions that don't work with their devices
- Frustration: "My switch doesn't support that" (but another brand does)
- No personalization to actual device inventory
- Generic advice doesn't leverage premium hardware from any manufacturer

---

### Pain Point #5: Lack of Scheduled Intelligence

**Current Reality:**  
The system operates reactively:
- Data collected continuously ✅
- Dashboards show real-time status ✅
- Alerts fire on thresholds ✅
- Pattern-based automation suggestions ✅
- **No device capability discovery or feature suggestions** ❌
- **No scheduled feature discovery reports** ❌

**What Users Need:**

**Daily Check-in:**
- "Unused feature alert: 3 switches support LED notifications (Inovelli, Aqara compatible models)"
- "Pattern detected yesterday: Bathroom light left on 45 min (switch model X supports auto-off)"

**Weekly Summary:**
- "5 automation opportunities detected this week"
- "2 devices with abnormal power draw patterns"
- "Motion sensor configuration could be optimized (Aqara sensitivity tuning)"

**Monthly Review:**
- "Device utilization: 12 of 25 switches underutilized (across all brands)"
- "3 new firmware updates available with feature improvements"
- "Energy savings opportunity: $15/month with auto-off timers"

**Quarterly Deep Dive:**
- "Smart home optimization report: 40% capability utilization"
- "Top 10 ROI automation suggestions based on patterns (device-specific)"
- "Device upgrade recommendations based on usage (brand comparison)"

**Impact:**
- **Passive system** requires user to seek insights
- No habit formation around optimization
- Users forget about the platform after initial setup
- Valuable insights buried in data, never surfaced
- No engagement loop to drive continuous improvement

---

### Why Existing Solutions Fall Short

**Home Assistant Native:**
- ✅ Excellent device control and automation engine
- ❌ No device capability database
- ❌ No proactive suggestion engine for device features
- ❌ No pattern → device capability mapping
- ❌ Users must research each device manually (every manufacturer)

**Zigbee2MQTT / Z-Wave JS:**
- ✅ Excellent device integration
- ✅ Publishes device capabilities via MQTT
- ❌ No analysis of which features are unused
- ❌ No proactive suggestions
- ❌ No utilization tracking

**Home Assistant Community Add-ons:**
- ✅ Some add-ons provide specific analytics
- ❌ No unified intelligence layer
- ❌ Each add-on handles its own domain
- ❌ No cross-device capability awareness
- ❌ No scheduled suggestion system

**Generic AI Assistants (ChatGPT, Gemini):**
- ✅ Can generate automation ideas
- ❌ No access to your actual device inventory
- ❌ No historical pattern analysis
- ❌ Device-agnostic suggestions don't fit hardware
- ❌ Requires manual query, not proactive

**Manual Research (Forums, Reddit, Documentation):**
- ✅ Eventually find device capabilities (for specific brands)
- ❌ Time-consuming (hours per device model)
- ❌ Information scattered across manufacturers
- ❌ No pattern-based suggestions
- ❌ Not scalable for 50+ devices from multiple brands

**Current HA-Ingestor + AI Automation System:**
- ✅ Captures all data with 99.9% reliability
- ✅ Fast queries and comprehensive history
- ✅ Multi-source enrichment (weather, sports, energy)
- ✅ Pattern-based automation suggestions
- ❌ **No device capability intelligence** ← THE GAP
- ❌ **No feature-based suggestion engine** ← THE GAP
- ❌ **No proactive device optimization** ← THE GAP

---

### Urgency & Importance

**Why Now:**

1. **Device Sophistication Increasing**  
   - 2020: Smart switches = on/off  
   - 2025: Smart switches = LED bars, scenes, power monitoring, mmWave sensors  
   - Multi-brand ecosystem with varying feature sets
   - Feature gap growing exponentially across all manufacturers

2. **AI Capability Maturity**  
   - Pattern recognition models are production-ready
   - LLMs can generate contextual suggestions
   - Zigbee2MQTT/Z-Wave JS provide comprehensive device data via APIs
   - Infrastructure exists (InfluxDB, SQLite, FastAPI, MQTT)

3. **User Expectations Shifting**  
   - Users expect AI to be proactive, not reactive
   - "Tell me what I'm missing" vs. "Store my data"
   - Smart home fatigue: Too many options from too many brands, need guidance

4. **ROI Pressure**  
   - Premium devices cost 2-3x basic switches (across all brands)
   - Users need to justify investment in any manufacturer
   - Unused features = wasted money (regardless of brand)
   - Energy crisis makes optimization valuable

5. **Data Availability**
   - Zigbee2MQTT publishes complete device capability database via MQTT
   - Z-Wave JS provides similar data for Z-Wave devices
   - Home Assistant device registry provides manufacturer/model
   - All pieces exist, just need integration

**Cost of Inaction:**

- Users continue using <20% of device capabilities (all manufacturers)
- Premium hardware investments remain underutilized (any brand)
- Automation opportunities go undiscovered
- Platform remains passive data collector vs. active advisor
- Competitive advantage lost to commercial platforms
- User engagement drops after initial setup

**Market Timing:**  
Perfect storm of mature AI, sophisticated devices from multiple manufacturers, universal device databases (Zigbee2MQTT MQTT bridge), and user demand for proactive intelligence. Window of opportunity: Next 6-12 months before commercial platforms dominate this space.

---

## Proposed Solution

### Solution Vision

Transform HA-Ingestor from a passive data collection platform into an **AI-Powered Device Intelligence Layer** that understands device capabilities across ALL manufacturers, analyzes usage patterns, and proactively suggests optimizations on daily/weekly/monthly/quarterly cadence.

---

### High-Level Approach

**Core Principle:**  
**Device Intelligence = Universal Capability Discovery + Pattern Analysis + Proactive Suggestions**

The solution adds an intelligence layer on top of the existing rock-solid data infrastructure without disrupting current functionality.

**Architecture Enhancement:**

```
[Existing System] → [Intelligence Layer] → [Proactive Outputs]

InfluxDB (events)    ──┐
SQLite (metadata)    ──┼─→ Device Intelligence ─→ Daily Suggestions
Weather data         ──┤   Universal Discovery     Weekly Summaries
Sports data          ──┤   Pattern Analyzer        Monthly Reviews
Energy data          ──┤   Suggestion Engine       Quarterly Reports
Zigbee2MQTT Bridge   ──┘   Multi-Integration      HA Notifications
```

---

### Core Components

#### **1. Universal Device Capability Discovery (NEW - All Manufacturers)**

**The Breakthrough:** Zigbee2MQTT publishes a **complete device database** to MQTT topic `zigbee2mqtt/bridge/devices` that includes **ALL device capabilities** for **ALL manufacturers**:

**What You Get Automatically:**

```json
// Published to: zigbee2mqtt/bridge/devices
[
  {
    "friendly_name": "kitchen_switch",
    "definition": {
      "model": "VZM31-SN",
      "vendor": "Inovelli",
      "description": "mmWave Zigbee Dimmer",
      "exposes": [
        {"type": "light", "features": [...]},
        {"name": "led_effect", ...},
        {"name": "smartBulbMode", ...},
        {"name": "autoTimerOff", ...},
        {"name": "power", ...}
      ]
    }
  },
  {
    "friendly_name": "bedroom_sensor",
    "definition": {
      "model": "MCCGQ11LM",
      "vendor": "Aqara",
      "description": "Door & window contact sensor",
      "exposes": [
        {"name": "contact", ...},
        {"name": "vibration", ...},
        {"name": "battery", ...}
      ]
    }
  },
  {
    "friendly_name": "living_room_bulb",
    "definition": {
      "model": "LED1624G9",
      "vendor": "IKEA",
      "description": "TRADFRI LED bulb",
      "exposes": [
        {"type": "light", "features": [...]},
        {"name": "color_temp", ...}
      ]
    }
  }
]
```

**This solves the scalability problem!** One MQTT subscription gets capabilities for:
- ✅ **All Zigbee manufacturers** (Inovelli, Aqara, IKEA, Xiaomi, Sonoff, Tuya, Philips, Schneider, SmartThings, and 100+ more!)
- ✅ **All device types** (switches, sensors, bulbs, plugs, thermostats, locks, etc.)
- ✅ **Real-time updates** (when new devices are paired)
- ✅ **6,000+ device models** automatically supported
- ✅ **No manual research needed** for Zigbee devices

**Implementation:**

```python
# NEW: services/ai-automation-service/src/device_intelligence/mqtt_capability_listener.py

class MQTTCapabilityListener:
    """
    Listens to Zigbee2MQTT bridge for device capabilities.
    Automatically populates capability database for ALL Zigbee devices.
    """
    
    async def start(self):
        # Subscribe to Zigbee2MQTT device list
        self.client.subscribe("zigbee2mqtt/bridge/devices")
    
    def _on_message(self, client, userdata, msg):
        """Process device list from Zigbee2MQTT"""
        if msg.topic == "zigbee2mqtt/bridge/devices":
            devices = json.loads(msg.payload)
            
            # Automatically process ALL devices
            for device in devices:
                manufacturer = device['definition']['vendor']
                model = device['definition']['model']
                exposes = device['definition']['exposes']
                
                # Parse capabilities (works for ANY manufacturer)
                capabilities = self._parse_exposes(exposes)
                
                # Store in database
                await self._store_capabilities(model, manufacturer, capabilities)
```

**Coverage:**
- **Zigbee devices:** ~6,000 models (Inovelli, Aqara, IKEA, Xiaomi, Sonoff, Tuya, etc.)
- **Z-Wave devices:** ~3,000 models (Phase 2 - via Z-Wave JS API)
- **WiFi devices:** Varies (Phase 3 - via native HA integration APIs)
- **Fallback:** Context7 research for unsupported devices

---

#### **2. Universal Capability Database (NEW)**

**Schema Design:**

```sql
-- Stores capabilities for ALL device models (any manufacturer)
CREATE TABLE device_capabilities (
    device_model TEXT PRIMARY KEY,
    manufacturer TEXT NOT NULL,
    integration_type TEXT NOT NULL,  -- 'zigbee2mqtt', 'zwave_js', 'native_ha'
    description TEXT,
    capabilities JSON NOT NULL,       -- Unified capability format
    mqtt_exposes JSON,                -- Raw Zigbee2MQTT data (if applicable)
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source TEXT DEFAULT 'zigbee2mqtt_bridge',
    UNIQUE(manufacturer, device_model, integration_type)
);

-- Tracks feature usage per device instance
CREATE TABLE device_feature_usage (
    device_id TEXT,                   -- FK to devices.device_id
    feature_name TEXT,                -- "led_notifications", "auto_off_timer"
    configured BOOLEAN DEFAULT FALSE,
    discovered_date TIMESTAMP,
    last_checked TIMESTAMP,
    PRIMARY KEY (device_id, feature_name),
    FOREIGN KEY (device_id) REFERENCES devices(device_id)
);

-- Examples (automatically populated from MQTT):
-- Inovelli switch
-- Aqara sensor  
-- IKEA bulb
-- Xiaomi sensor
-- ANY Zigbee device from ANY manufacturer!
```

---

#### **3. Feature-Based Suggestion Generator (ENHANCED)**

**What It Does:**  
Generates suggestions for unused device features alongside existing pattern-based suggestions. **Works for all manufacturers automatically.**

**Implementation:**

```python
# ENHANCE EXISTING: services/ai-automation-service/src/suggestion_generator.py

class SuggestionGenerator:
    """EXISTING class - ADD new method"""
    
    async def generate_feature_suggestions(self) -> List[Dict]:
        """
        NEW METHOD: Generate suggestions for unused device features.
        Works for ALL manufacturers automatically.
        """
        
        # 1. Get all devices with known capabilities
        devices = await get_devices_with_capabilities()
        
        suggestions = []
        
        for device in devices:
            # 2. Check which features are unused
            unused_features = await get_unused_features(device.device_id)
            
            for feature in unused_features:
                # 3. Generate device-aware suggestion via LLM
                suggestion = await self.llm.generate_feature_suggestion(
                    device=device,  # Includes manufacturer, model
                    feature=feature,
                    context=await get_device_context(device.device_id)
                )
                
                suggestions.append({
                    'type': 'feature_discovery',
                    'manufacturer': device.manufacturer,  # Any brand
                    'device_id': device.device_id,
                    'feature_name': feature.name,
                    'title': suggestion['title'],
                    'description': suggestion['description'],
                    'confidence': calculate_feature_confidence(feature),
                    'category': 'optimization'
                })
        
        return suggestions
```

**Example Output (Multi-Brand):**

```
Daily Suggestions:
1. [Inovelli VZM31-SN - Kitchen] Enable LED notifications (unused)
2. [Aqara MCCGQ11LM - Front Door] Configure vibration detection
3. [IKEA LED1624G9 - Bedroom] Use color temperature presets
4. [Xiaomi WSDCGQ11LM - Living Room] Enable temperature alerts
5. [Sonoff BASICZBR3 - Garage] Configure power monitoring
```

---

#### **4. Combined Suggestion Pipeline (ENHANCED)**

**What It Does:**  
Merges pattern-based AND feature-based suggestions into unified daily report.

**Implementation:**

```python
# ENHANCE EXISTING: services/ai-automation-service/src/scheduler/daily_analysis.py

async def run_daily_analysis():
    """EXISTING function - ENHANCE to include feature suggestions"""
    
    # EXISTING: Pattern-based suggestions
    pattern_suggestions = await generate_pattern_suggestions()
    # Example: "Create automation when bedroom light turns on 6am daily"
    
    # NEW: Feature-based suggestions (ALL manufacturers)
    feature_suggestions = await generate_feature_suggestions()
    # Example: "Enable LED notifications on Inovelli switch"
    # Example: "Configure vibration detection on Aqara sensor"
    # Example: "Use color presets on IKEA bulb"
    
    # NEW: Merge and rank
    all_suggestions = merge_and_rank(
        pattern_suggestions,  # "Create automation when..."
        feature_suggestions   # "Enable feature X on device Y..."
    )
    
    # EXISTING: Store top 5-10
    await store_top_suggestions(all_suggestions[:10])
    
    # EXISTING: Notify via MQTT
    await publish_suggestions(all_suggestions[:5])
```

---

#### **5. Device Intelligence Dashboard Tab (NEW)**

**What It Does:**  
Adds "Device Intelligence" tab to existing Health Dashboard showing capability utilization across all manufacturers.

**Location:** `services/health-dashboard/src/pages/DeviceIntelligencePage.tsx` (NEW)

**UI Components:**

```typescript
export function DeviceIntelligencePage() {
  return (
    <div className="space-y-6">
      {/* Overall Utilization */}
      <Card>
        <h2>Your Device Utilization</h2>
        <Progress value={32} max={100} />
        <p>32% of available features configured (+12% this month)</p>
      </Card>
      
      {/* Breakdown by Manufacturer */}
      <Card>
        <h2>Utilization by Brand</h2>
        <Chart data={[
          { manufacturer: 'Inovelli', utilization: 28 },
          { manufacturer: 'Aqara', utilization: 42 },
          { manufacturer: 'IKEA', utilization: 35 },
          { manufacturer: 'Xiaomi', utilization: 31 },
          { manufacturer: 'Other', utilization: 25 }
        ]} />
      </Card>
      
      {/* Top Opportunities (All Brands) */}
      <Card>
        <h2>Top Feature Opportunities</h2>
        <FeatureList features={[
          { device: 'Kitchen Switch (Inovelli)', feature: 'LED Notifications' },
          { device: 'Front Door Sensor (Aqara)', feature: 'Vibration Detection' },
          { device: 'Bedroom Bulb (IKEA)', feature: 'Color Temperature' },
          { device: 'Living Room Sensor (Xiaomi)', feature: 'Temperature Alerts' }
        ]} />
      </Card>
    </div>
  );
}
```

---

### How It Works (End-to-End Flow)

**1. Automatic Capability Discovery:**
```
Zigbee2MQTT publishes device list to MQTT
  ↓
AI Automation Service subscribes
  ↓
Parse capabilities for ALL devices (any manufacturer)
  ↓
Store in device_capabilities table
  ↓
~6,000 device models supported automatically!
```

**2. Daily Pattern + Feature Analysis:**
```
Every morning at 6:00 AM:
  ↓
Pattern Analysis Engine runs (EXISTING)
  ↓
Feature Analysis Engine runs (NEW)
  ↓
Merge pattern + feature suggestions
  ↓
Rank by confidence and impact
```

**3. Proactive Notification:**
```
7:00 AM - Daily notification
  ↓
Fetch top suggestion (pattern OR feature)
  ↓
Send to HA notification service
  ↓
User sees notification on phone/dashboard
  ↓
User clicks [Configure Now] or [Dismiss]
  ↓
Feedback recorded in database
```

---

### Key Differentiators

**vs. Generic AI Assistants:**
- ✅ **Device-aware**: Knows your actual hardware capabilities (ALL brands)
- ✅ **Pattern-aware**: Uses your historical data
- ✅ **Proactive**: Scheduled suggestions vs. on-demand queries
- ✅ **Universal**: Works for 6,000+ device models automatically

**vs. Home Assistant Native:**
- ✅ **Intelligence layer**: Suggests what's possible (any manufacturer)
- ✅ **Cross-device analysis**: Sees patterns across entire home
- ✅ **Scheduled cadence**: Daily/weekly/monthly engagement
- ✅ **Capability knowledge**: Understands device capabilities universally

**vs. Current HA-Ingestor + AI Automation:**
- ✅ **Actionable insights**: From data → device-specific recommendations
- ✅ **Device intelligence**: Capability awareness for ALL brands
- ✅ **Feature discovery**: Not just patterns, but unused capabilities
- ✅ **Universal support**: One solution works for all Zigbee manufacturers

---

### Integration with Existing System

**No Breaking Changes:**
- All existing services continue unchanged
- New microservice enhancement to AI Automation Service
- Database additions (new tables in ai_automation.db)
- No modifications to InfluxDB schema
- Dashboard enhancement (new tab in existing dashboard)

**Enhanced Services:**
```
services/ai-automation-service/ (Port 8018)
├─ EXISTING: Pattern detection
├─ EXISTING: Suggestion generation (pattern-based)
├─ EXISTING: Daily scheduler
├─ EXISTING: OpenAI LLM integration
├─ NEW: MQTT capability listener
├─ NEW: Feature-based suggestion generator
└─ NEW: Device intelligence API endpoints

services/health-dashboard/ (Port 3000)
├─ EXISTING: 12 tabs
└─ NEW: Device Intelligence tab (13th tab)
```

**Database Additions:**
```
ai_automation.db (SQLite):
├─ patterns (EXISTING)
├─ suggestions (EXISTING)
├─ user_feedback (EXISTING)
├─ device_capabilities (NEW)
└─ device_feature_usage (NEW)
```

---

## Target Users

### Primary User Segment: The "Power User Plateau"

**Profile:**

**Demographics:**
- Age: 28-55 years old
- Technical background: Software developers, IT professionals, engineers, tech enthusiasts
- Home size: 1,500-4,000 sq ft (medium to large homes)
- Smart home investment: $2,000-$10,000+ in devices (multiple manufacturers)
- Time constraints: Full-time job, limited time for smart home tinkering

**Psychographics:**
- Early adopter mindset
- Values efficiency and optimization
- Enjoys technology but prioritizes "set it and forget it"
- Frustrated by unused potential
- ROI-conscious (wants to justify premium device purchases from any brand)
- Privacy-focused (self-hosted solutions preferred)

**Current Smart Home Setup:**
- **Home Assistant Experience:** 1-3+ years
- **Entity Count:** 50-1000+ devices/entities
- **Device Sophistication:** Premium and mid-range brands (Inovelli, Aqara, IKEA, Xiaomi, Sonoff, Shelly, Philips, etc.)
- **Integration Types:** Zigbee2MQTT, Z-Wave, MQTT, Native HA integrations
- **Automation Count:** 20-100+ automations (but mostly basic)
- **Dashboard Usage:** Regular monitoring via HA mobile app

**Current Behaviors:**

**What They Do Well:**
- ✅ Successfully deployed HA-Ingestor for data collection
- ✅ Monitor system health via dashboard
- ✅ Create basic automations (time-based, motion-triggered)
- ✅ Research new devices before purchase (various brands)
- ✅ Participate in HA community forums

**Where They Struggle:**
- ❌ Don't have time to research every device model from every manufacturer
- ❌ Purchase premium devices but use basic features only
- ❌ Create initial automations, then stop optimizing
- ❌ See patterns in dashboards but don't act on them
- ❌ Miss opportunities because they don't know what's possible (across all brands)
- ❌ Feel overwhelmed by configuration options (different for each manufacturer)
- ❌ Forget about advanced features after initial setup

**Specific Needs:**

1. **Proactive Guidance**
   - "Tell me what I'm missing across ALL my devices, don't make me search manufacturer docs"
   - Want system to suggest improvements based on actual usage
   - Need specific, actionable recommendations (not generic advice)

2. **Time Efficiency**
   - 15-30 minutes/week max for optimization
   - Prefer bite-sized daily suggestions over long research sessions
   - Want quick wins (5-minute configurations with immediate value)

3. **ROI Validation**
   - Need to justify expensive device purchases (any brand)
   - Want to see utilization metrics (am I using what I paid for?)
   - Appreciate energy savings calculations

4. **Learning & Discovery**
   - Enjoy discovering new capabilities (across all devices)
   - Want to be educated, not just automated
   - Appreciate "I didn't know that was possible!" moments

5. **Confidence Building**
   - Need reassurance that suggestions are safe to implement
   - Want to understand why a suggestion is relevant
   - Appreciate confidence scores and pattern explanations

**Goals They're Trying to Achieve:**

- 🎯 **Maximize device ROI**: Use features they paid for (all manufacturers)
- 🎯 **Reduce energy costs**: Find optimization opportunities
- 🎯 **Improve convenience**: Eliminate repetitive manual actions
- 🎯 **Enhance security**: Leverage monitoring and alerts
- 🎯 **Achieve satisfaction**: Feel smart home is truly "smart"

**Pain Points:**

**Quoted from User Research (Hypothetical):**

> "I have devices from 5 different manufacturers and just found out most of them have features I've never used. Why didn't I know this?" - Jake, Software Developer

> "I see patterns in my Grafana dashboard but have no idea what to do with them or which devices can help." - Sarah, IT Manager

> "I bought the best-rated devices from multiple brands, but I'm pretty sure I'm only using 20% of what they can do." - Mike, Network Engineer

> "Every few months I dive deep into Home Assistant for a weekend, but I can't research every manufacturer's documentation. I wish something would just tell me 'you could do this better'." - Alex, Data Analyst

**User Journey with Device Intelligence (Proposed):**

```
Initial Setup (Month 1):
✅ Deploy HA-Ingestor
✅ Configure all services
📚 Capability KB auto-populated (ALL devices, ALL brands)
😊 Excited about possibilities

Engagement Phase (Months 2-12):
📬 Daily suggestion notifications (multi-brand)
💡 "Discover" new features weekly (any manufacturer)
✅ Implement 2-3 suggestions/month
🎉 "Aha moments" regularly
📈 Device utilization increases
😊 Satisfaction with ROI

Mastery Phase (Year 2+):
🏆 High device utilization (40-60%)
🔁 Continuous optimization loop
📊 Quarterly deep dives
💰 Measurable energy savings
🎯 Feeling of smart home mastery
😃 Strong ROI justification
```

---

### Secondary User Segment: The "New Enthusiast"

**Profile:**

**Demographics:**
- Age: 25-45 years old
- Technical background: Hobbyist level, learning as they go
- Home size: 800-2,000 sq ft (apartments, small homes)
- Smart home investment: $500-$2,000 in devices (budget to mid-range brands)
- Time available: More flexible, weekends for projects

**Specific Needs:**

1. **Education & Onboarding**
   - "Teach me what's possible" (across all device types)
   - Need to learn device capabilities as they build
   - Want examples and use cases
   - Appreciate step-by-step guidance

2. **Multi-Brand Understanding**
   - Help navigate differences between manufacturers
   - Understand which brands offer which features
   - Learn best practices for each integration type

---

### Target User Summary

**Primary Focus:**
- **Power Users** who have hit a plateau (80% of focus)
- Multi-brand device inventory (Inovelli, Aqara, IKEA, Xiaomi, etc.)
- Need proactive guidance to continue optimizing
- Have sophisticated devices but lack time for manufacturer research
- Value ROI and measurable improvements

**Secondary Focus:**
- **New Enthusiasts** learning the ropes (20% of focus)
- Building multi-brand smart home
- Need educational guidance as they build
- Want to avoid mistakes and learn best practices
- Appreciate step-by-step suggestions

**Not Designed For:**
- Casual users with <20 entities (too simple)
- Single-brand ecosystems (though system still works)
- Users who prefer manual control (anti-automation)
- Users unwilling to engage with notifications (need interaction)

**Key Insight:**
Both segments share a common need: **Proactive intelligence that understands device capabilities across ALL manufacturers and suggests specific, actionable improvements based on actual usage patterns.** The system must be brand-agnostic and scalable.

---

## Goals & Success Metrics

### Personal Home Objectives

#### **Objective 1: Maximize Device ROI**

**Goal:** Utilize 45%+ of your devices' available capabilities within 12 months (up from current ~20%)

**Success Criteria:**
- **3 months:** Baseline measurement complete (know what % you're currently using)
- **6 months:** Device utilization reaches 30% (+10 percentage points)
- **9 months:** Device utilization reaches 38% (+18 percentage points)
- **12 months:** Device utilization reaches 45% (+25 percentage points)

**Example Measurement:**
```
Your Entire Home (Multi-Brand):
├─ Total Devices: 99 devices
├─ Total Available Features: ~400 features (across all manufacturers)
├─ Currently Configured: ~80 features = 20%
└─ Target by Month 12: 180 features = 45%

By Manufacturer:
├─ Inovelli devices: 25% → 50%
├─ Aqara devices: 30% → 45%
├─ IKEA devices: 20% → 40%
├─ Xiaomi devices: 15% → 35%
└─ Other brands: 18% → 40%
```

**Why This Matters:**  
You've invested $2,000-$10,000 in devices. Using 20% means ~$1,600-$8,000 in wasted capability. Hitting 45% doubles your ROI across ALL manufacturers.

---

#### **Objective 2: Reduce Energy Costs**

**Goal:** Achieve $150+ annual energy savings through device optimization

**Success Criteria:**
- **3 months:** $25 savings (auto-off timers, basic optimization)
- **6 months:** $50 savings (cumulative)
- **9 months:** $100 savings (cumulative)
- **12 months:** $150+ savings (cumulative)

---

#### **Objective 3: Discover Hidden Capabilities**

**Goal:** Configure 15+ previously unknown device features within 12 months (across all manufacturers)

**Success Criteria:**
- **Month 1:** Discover 2-3 features you didn't know existed
- **Quarter 1 (3 months):** Configure 5+ new features
- **Quarter 2 (6 months):** Configure 10+ new features (cumulative)
- **Quarter 4 (12 months):** Configure 15+ new features (cumulative)

**Example Discoveries (Multi-Brand):**
```
Month 1 Discoveries:
✅ LED notifications on Inovelli switches
✅ Vibration detection on Aqara sensors
✅ Color temperature presets on IKEA bulbs

Quarter 1 Discoveries:
✅ Auto-off timers on multiple switch brands
✅ Motion sensor sensitivity tuning (Aqara)
✅ Power monitoring alerts (Sonoff, Shelly)
✅ Scene memory on IKEA bulbs
✅ Temperature alerts on Xiaomi sensors

Quarter 2 Discoveries:
✅ Individual LED control (Inovelli)
✅ Approach detection (Aqara)
✅ Custom button events (various brands)
✅ Binding switches together (Zigbee2MQTT feature)
✅ Smooth transitions (IKEA)
```

---

#### **Objective 4: Reduce Manual Interventions**

**Goal:** Decrease manual device interactions by 40% through improved automations

**Success Criteria:**
- **Baseline:** Track manual interventions for 2 weeks (e.g., 150 manual switches/month)
- **3 months:** 20% reduction (120 manual switches/month)
- **6 months:** 30% reduction (105 manual switches/month)
- **12 months:** 40% reduction (90 manual switches/month)

---

### Personal Success Metrics

#### **Metric 1: Device Utilization Score (Your North Star)**

**Current Baseline:** ~20% (estimated)  
**Target:** 45% by month 12

**How It's Calculated:**
```python
# For your entire home
home_utilization = (
    total_configured_features / total_available_features
) * 100

# By manufacturer
brand_utilization = (
    configured_features_for_brand / available_features_for_brand
) * 100

# Example from your HA instance:
# 99 devices with ~400 total features (all brands)
# Currently: 80 configured = 20%
# Target: 180 configured = 45%
```

---

#### **Metric 2: Feature Discovery Rate**

**Definition:** How many new capabilities you discover and configure per month

**Targets:**
- **Month 1-3:** 2-3 features per month (learn what's possible)
- **Month 4-6:** 3-4 features per month (momentum building)
- **Month 7-9:** 2-3 features per month (diminishing new discoveries)
- **Month 10-12:** 1-2 features per month (final optimizations)

---

#### **Metric 3: Suggestion Implementation Rate**

**Definition:** What percentage of suggestions you actually implement

**Targets:**
- **Daily Suggestions:** 15% (1-2 per week)
- **Weekly Summaries:** 25% (1-2 per summary)
- **Monthly Reports:** 40% (3-5 per report)
- **Quarterly Deep Dives:** 60% (6+ per report)

---

#### **Metric 4: Energy Savings (Estimated)**

**Definition:** Monthly and cumulative energy cost savings from optimizations

**Monthly Tracking:**
```
Month 1: $8 (auto-off timers on 3 devices)
Month 2: $12 cumulative (+$4 this month)
Month 3: $25 cumulative (+$13 this month)
Month 6: $50 cumulative
Month 9: $100 cumulative
Month 12: $150+ cumulative (target)
```

---

#### **Metric 5: Multi-Brand Utilization**

**Definition:** Utilization score breakdown by manufacturer

**Targets:**
```
Manufacturer Utilization Goals:
├─ Inovelli: 25% → 50% (high-feature devices)
├─ Aqara: 30% → 45% (sensor-rich)
├─ IKEA: 20% → 40% (lighting)
├─ Xiaomi: 15% → 35% (sensors)
└─ Other: 18% → 40% (various)
```

---

### Key Performance Indicators (KPIs)

#### **Primary KPIs (Dashboard Display)**

**1. Device Utilization Score**
```
Current: 20% ──────────●───────── Target: 45%
Progress: 32% (Month 6) ↗️ +12% this month
```

**2. Monthly Feature Discoveries**
```
Target: 2-3 features/month
This Month: 4 features ✅ (Above target!)
Cumulative: 18 features since start
```

**3. Implementation Rate**
```
Daily: 18% (target: 15%) ✅
Weekly: 28% (target: 25%) ✅
Monthly: 35% (target: 40%) ⚠️ Close!
```

**4. Energy Savings**
```
Monthly: $12 (this month)
Cumulative: $67 (6 months) ↗️
Annual Projection: $134 (on track for $150 target)
```

**5. Brand-Specific Utilization**
```
Inovelli: 35% (up from 25%)
Aqara: 38% (up from 30%)
IKEA: 32% (up from 20%)
Xiaomi: 28% (up from 15%)
```

---

### Milestone-Based Success Criteria

#### **Week 1: First Value**
- ✅ Capability KB populated for your 99 devices (ALL brands automatically)
- ✅ First daily suggestion received
- ✅ Discovered 1 feature you didn't know existed
- ✅ "Aha moment" - "I didn't know my devices could do that!"

**Success Gate:** System understands your devices across all manufacturers

---

#### **Month 1: Quick Wins**
- ✅ 2-3 new features configured (any brand)
- ✅ Device utilization increased to 22% (+2 points)
- ✅ First energy savings detected ($8-10)
- ✅ Pattern + feature analysis running daily
- ✅ Engaged with 40%+ of daily suggestions

**Success Gate:** Clear value delivered (new features + savings)

---

#### **Month 3: Momentum**
- ✅ 5+ new features configured (cumulative, multi-brand)
- ✅ Device utilization reaches 25% (+5 points)
- ✅ $25 cumulative energy savings
- ✅ 20% reduction in manual interventions
- ✅ Positive sentiment: "This is actually useful across all my devices!"

**Success Gate:** Sustained engagement, measurable improvements

---

#### **Month 6: Habits Formed**
- ✅ 10+ new features configured (cumulative, across brands)
- ✅ Device utilization reaches 35% (+15 points)
- ✅ $50 cumulative energy savings
- ✅ 30% reduction in manual interventions
- ✅ Weekly summaries eagerly anticipated
- ✅ System is "trusted advisor" for all device types

**Success Gate:** Device Intelligence is part of daily routine

---

#### **Month 12: Optimized Home**
- ✅ 15+ new features configured (cumulative, all manufacturers)
- ✅ Device utilization reaches 45% (+25 points)
- ✅ $150 cumulative energy savings
- ✅ 40% reduction in manual interventions
- ✅ Quarterly reports drive continued optimization
- ✅ ROI clearly justified across all device investments
- ✅ Sharing success stories in HA community

**Success Gate:** Smart home operating at high efficiency, strong ROI

---

### Personal Dashboard (Your Intelligence Tab)

```
┌─────────────────────────────────────────────────────────┐
│ 🏠 Your Smart Home Intelligence                         │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ 📊 Device Utilization: 32% ↗️ (+12% this month)         │
│    🎯 Target: 45% by Month 12 (on track!)               │
│                                                          │
│ 💡 Features Discovered: 18 features                     │
│    This Month: +4 features ✅                            │
│                                                          │
│ 💰 Energy Savings: $67 (6 months)                       │
│    This Month: $12                                       │
│    Annual Projection: $134                               │
│                                                          │
│ ⚡ Automation Quality: 42% fewer manual actions         │
│    Time Saved: ~5 hours (6 months)                      │
│                                                          │
│ ─────────────────────────────────────────────────────   │
│                                                          │
│ 🎉 Recent Wins:                                         │
│ • Configured LED notifications on 3 Inovelli switches   │
│ • Enabled vibration detection on 2 Aqara sensors        │
│ • Set up color presets on IKEA bedroom bulbs            │
│                                                          │
│ ─────────────────────────────────────────────────────   │
│                                                          │
│ 🔥 Top Opportunities (This Month):                      │
│ 1. Auto-off timers on 4 switches (multi-brand)          │
│ 2. Temperature alerts on Xiaomi sensors                 │
│ 3. Scene memory on IKEA bulbs                           │
│ 4. Power monitoring on Sonoff plugs                     │
│ 5. Approach detection on Aqara sensors                  │
│                                                          │
│ ─────────────────────────────────────────────────────   │
│                                                          │
│ 📈 Utilization by Brand:                                │
│ • Inovelli Switches (12): 35% utilized ↗️               │
│ • Aqara Sensors (15): 38% utilized ✅                    │
│ • IKEA Bulbs (8): 32% utilized 📈                        │
│ • Xiaomi Sensors (20): 28% utilized 📈                   │
│ • Other Devices (44): 30% utilized 📈                    │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## MVP Scope

### What Already Exists ✅

**AI Automation Service (Port 8018):**
- ✅ Pattern detection (time-of-day, co-occurrence, anomaly)
- ✅ OpenAI LLM integration for automation suggestions
- ✅ Daily scheduler (APScheduler) running batch analysis
- ✅ SQLite database storing patterns and suggestions
- ✅ REST API for managing suggestions
- ✅ MQTT integration for HA communication
- ✅ Frontend UI (ai-automation-ui on port 3001)
- ✅ Suggestion approval workflow

**Data Infrastructure:**
- ✅ Device model in SQLite (`devices` table) with manufacturer, model
- ✅ Entity model with device relationships
- ✅ InfluxDB with full historical data
- ✅ Data API (port 8006) for querying events/devices

**Existing Capabilities:**
- ✅ "Create automation when bedroom light turns on 6:00-6:15am daily" (pattern-based)
- ✅ "Motion sensor + light correlation detected" (co-occurrence)
- ✅ "Bathroom light left on >30min frequently" (anomaly)

---

### What's MISSING ❌ (The Real Gap)

**Device Intelligence Layer:**
- ❌ No device capability knowledge (doesn't know what ANY device supports)
- ❌ No feature utilization tracking (can't tell if you're using 20% or 80% of capabilities)
- ❌ No device-specific suggestions ("enable feature X on your Y brand device")
- ❌ No universal capability discovery system
- ❌ No cadence for feature discovery (only pattern-based automation suggestions)

**Current Suggestions ARE:**
- ✅ "Based on your 6am pattern, create a sunrise automation" (pattern → automation)

**Current Suggestions ARE NOT:**
- ❌ "Your Inovelli VZM31-SN supports LED notifications - configure garage door alert" (capability → feature)
- ❌ "Your Aqara sensor supports vibration detection - enable for security" (capability → feature)
- ❌ "Your IKEA bulb has color temperature presets - create wake-up routine" (capability → feature)
- ❌ "You have 3 switches in smart bulb mode with non-smart bulbs - optimize" (configuration issue)

---

### MVP Scope: Universal Device Intelligence Enhancement

**Goal:** Add device capability awareness to the existing AI automation system, enabling feature-based suggestions alongside pattern-based automation suggestions. **Works automatically for ALL Zigbee manufacturers.**

---

### Core Features (Must Have for MVP)

#### **1. MQTT Device Capability Listener (NEW)**

**What It Does:**  
Subscribes to Zigbee2MQTT bridge and automatically populates capability database for ALL Zigbee devices from ALL manufacturers.

**The Breakthrough:**
```
One MQTT subscription = Capabilities for:
✅ Inovelli (all models)
✅ Aqara (all models)
✅ IKEA (all models)
✅ Xiaomi (all models)
✅ Sonoff (all models)
✅ Tuya (all models)
✅ Philips (all models)
✅ SmartThings (all models)
✅ 100+ more manufacturers
✅ ~6,000 device models total
```

**Implementation:**

```python
# NEW FILE: services/ai-automation-service/src/device_intelligence/mqtt_capability_listener.py

class MQTTCapabilityListener:
    """
    Listens to Zigbee2MQTT bridge for device capabilities.
    Automatically populates capability database for ALL Zigbee devices.
    """
    
    async def start(self):
        # Subscribe to device list from Zigbee2MQTT
        self.client.subscribe("zigbee2mqtt/bridge/devices")
    
    def _on_message(self, client, userdata, msg):
        """Process device list - works for ANY manufacturer"""
        if msg.topic == "zigbee2mqtt/bridge/devices":
            devices = json.loads(msg.payload)
            
            # Process ALL devices (any brand)
            for device in devices:
                self._process_device(device)
    
    def _process_device(self, device: dict):
        """Extract and store capabilities - universal parser"""
        definition = device.get('definition')
        if not definition:
            return  # Unsupported device
        
        # Works for ANY manufacturer
        manufacturer = definition.get('vendor', 'Unknown')
        model = definition.get('model', 'Unknown')
        exposes = definition.get('exposes', [])
        
        # Parse capabilities (universal format)
        capabilities = self._parse_exposes(exposes)
        
        # Store in database
        await self._store_capabilities(
            device_model=model,
            manufacturer=manufacturer,
            capabilities=capabilities,
            source='zigbee2mqtt_bridge'
        )
```

**Integration:**
- Start listener on service startup
- Automatically populates database on first run (~2-3 minutes for 99 devices)
- Updates when new devices paired
- No manual research needed for ANY Zigbee manufacturer!

**Effort:** 1 week

---

#### **2. Universal Capability Database (NEW)**

**What It Does:**  
Stores capabilities for ALL device models with unified schema.

**Database Schema:**

```sql
-- Stores capabilities for ALL manufacturers
CREATE TABLE device_capabilities (
    device_model TEXT PRIMARY KEY,
    manufacturer TEXT NOT NULL,
    integration_type TEXT NOT NULL,  -- 'zigbee2mqtt', 'zwave_js', etc.
    description TEXT,
    capabilities JSON NOT NULL,       -- Unified capability format
    mqtt_exposes JSON,                -- Raw Zigbee2MQTT exposes
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source TEXT DEFAULT 'zigbee2mqtt_bridge',
    UNIQUE(manufacturer, device_model, integration_type)
);

-- Tracks feature usage per device instance
CREATE TABLE device_feature_usage (
    device_id TEXT,                   -- Links to devices.device_id
    feature_name TEXT,                -- "led_notifications", "vibration_detection"
    configured BOOLEAN DEFAULT FALSE,
    discovered_date TIMESTAMP,
    last_checked TIMESTAMP,
    PRIMARY KEY (device_id, feature_name),
    FOREIGN KEY (device_id) REFERENCES devices(device_id)
);

-- Indexes for fast lookups
CREATE INDEX idx_capabilities_manufacturer ON device_capabilities(manufacturer);
CREATE INDEX idx_capabilities_integration ON device_capabilities(integration_type);

-- Automatically populated examples:
-- Inovelli VZM31-SN
-- Aqara MCCGQ11LM
-- IKEA LED1624G9
-- Xiaomi WSDCGQ11LM
-- Sonoff BASICZBR3
-- Tuya TS0601
-- ... 6,000+ more models!
```

**Integrates With:**
- ✅ Existing `devices` table (Foreign key relationship)
- ✅ Existing Data API for device queries
- ✅ MQTT listener for automatic population

**Out of MVP:**
- ❌ Z-Wave devices (Zigbee2MQTT only for MVP)
- ❌ Custom capability editing via UI
- ❌ Automatic monthly refresh (manual refresh command only)

**Effort:** 1 week

---

#### **3. Feature-Based Suggestion Generator (NEW)**

**What It Does:**  
Generates suggestions for unused device features. **Works automatically for ALL manufacturers.**

**Implementation:**

```python
# ENHANCE EXISTING: services/ai-automation-service/src/suggestion_generator.py

class SuggestionGenerator:
    """EXISTING class - ADD new method"""
    
    async def generate_feature_suggestions(self) -> List[Dict]:
        """
        NEW METHOD: Generate suggestions for unused device features.
        Works for ALL Zigbee manufacturers automatically.
        """
        
        # 1. Get all devices with known capabilities
        devices = await get_devices_with_capabilities()
        
        suggestions = []
        
        for device in devices:
            # 2. Check which features are unused
            unused_features = await get_unused_features(device.device_id)
            
            for feature in unused_features:
                # 3. Generate suggestion via LLM (device-aware)
                suggestion = await self.llm.generate_feature_suggestion(
                    device=device,  # Includes manufacturer, model
                    feature=feature,
                    context=await get_device_context(device.device_id)
                )
                
                suggestions.append({
                    'type': 'feature_discovery',
                    'manufacturer': device.manufacturer,  # ANY brand
                    'device_id': device.device_id,
                    'feature_name': feature.name,
                    'title': suggestion['title'],
                    'description': suggestion['description'],
                    'confidence': calculate_feature_confidence(feature),
                    'category': 'optimization',
                    'priority': feature.priority
                })
        
        return suggestions
```

**Example Output (Multi-Brand):**
```
Daily Suggestions (5 total):
1. [Pattern] Create sunrise automation (bedroom light 6am daily)
2. [Inovelli - Kitchen] Enable LED notifications (unused)
3. [Aqara - Front Door] Configure vibration detection (security)
4. [IKEA - Bedroom] Use color temperature presets (wake-up)
5. [Xiaomi - Living Room] Enable temperature alerts (unused)
```

**Integrates With:**
- ✅ Existing `SuggestionGenerator` class (extend, don't replace)
- ✅ Existing `generate_suggestions()` for pattern-based
- ✅ Existing LLM client (OpenAI)
- ✅ Existing `suggestions` table (new type: `feature_discovery`)

**Out of MVP:**
- ❌ Interactive configuration wizards
- ❌ Multi-device coordination suggestions
- ❌ Advanced confidence scoring (simple algorithm only)

**Effort:** 1-2 weeks

---

#### **4. Combined Suggestion Pipeline (ENHANCE EXISTING)**

**What It Does:**  
Merges pattern-based AND feature-based suggestions into unified daily report.

**Implementation:**

```python
# ENHANCE EXISTING: services/ai-automation-service/src/scheduler/daily_analysis.py

async def run_daily_analysis():
    """EXISTING function - ENHANCE to include feature suggestions"""
    
    # EXISTING: Pattern-based suggestions
    pattern_suggestions = await generate_pattern_suggestions()
    # Example: "Create automation when bedroom light turns on 6am daily"
    
    # NEW: Feature-based suggestions (ALL manufacturers)
    feature_suggestions = await generate_feature_suggestions()
    # Example: "Enable LED notifications on Inovelli switch"
    # Example: "Configure vibration detection on Aqara sensor"
    # Example: "Use color presets on IKEA bulb"
    
    # NEW: Merge and rank
    all_suggestions = merge_and_rank(
        pattern_suggestions,  # "Create automation when..."
        feature_suggestions   # "Enable feature X on device Y..."
    )
    
    # EXISTING: Store top 5-10
    await store_top_suggestions(all_suggestions[:10])
    
    # EXISTING: Notify via MQTT
    await publish_suggestions(all_suggestions[:5])
```

**Integrates With:**
- ✅ Existing daily scheduler
- ✅ Existing pattern detection
- ✅ Existing MQTT notification system
- ✅ Existing frontend UI (just shows new suggestion types)

**Out of MVP:**
- ❌ Weekly/monthly/quarterly separate reports (daily only)
- ❌ Custom cadence configuration
- ❌ Email notifications

**Effort:** 3-4 days

---

#### **5. Device Intelligence Dashboard Tab (NEW)**

**What It Does:**  
Adds "Device Intelligence" tab to existing Health Dashboard showing capability utilization across all manufacturers.

**Implementation:**

**Location:** `services/health-dashboard/src/pages/DeviceIntelligencePage.tsx` (NEW)

```typescript
// NEW TAB in existing Health Dashboard

export function DeviceIntelligencePage() {
  return (
    <div className="space-y-6">
      {/* Overall Device Utilization Score */}
      <Card>
        <h2>Your Device Utilization</h2>
        <Progress value={32} max={100} />
        <p>32% of available features configured (+12% this month)</p>
        <p className="text-sm text-gray-500">
          Across {deviceCount} devices from {manufacturerCount} manufacturers
        </p>
      </Card>
      
      {/* Utilization by Manufacturer */}
      <Card>
        <h2>Utilization by Brand</h2>
        <BarChart data={[
          { manufacturer: 'Inovelli', utilization: 35, devices: 12 },
          { manufacturer: 'Aqara', utilization: 38, devices: 15 },
          { manufacturer: 'IKEA', utilization: 32, devices: 8 },
          { manufacturer: 'Xiaomi', utilization: 28, devices: 20 },
          { manufacturer: 'Other', utilization: 30, devices: 44 }
        ]} />
      </Card>
      
      {/* Top Opportunities (All Brands) */}
      <Card>
        <h2>Top Feature Opportunities</h2>
        <FeatureList features={topOpportunities} />
      </Card>
      
      {/* Recent Discoveries */}
      <Card>
        <h2>Recently Configured</h2>
        <RecentFeaturesList />
      </Card>
      
      {/* Device Breakdown Table */}
      <Card>
        <h2>All Devices</h2>
        <DeviceUtilizationTable devices={allDevices} />
      </Card>
    </div>
  );
}
```

**Integrates With:**
- ✅ Existing Health Dashboard (12 tabs → 13 tabs)
- ✅ Existing React/TypeScript/Tailwind stack
- ✅ New Device Intelligence API endpoints
- ✅ Existing chart components (Recharts)

**Out of MVP:**
- ❌ Interactive configuration wizards
- ❌ Advanced filters and search
- ❌ Export to PDF/CSV
- ❌ Historical trend charts (current state only)

**Effort:** 1 week

---

#### **6. API Endpoints for Device Intelligence (NEW)**

**What It Does:**  
Adds REST endpoints to existing AI Automation Service for device intelligence.

**Implementation:**

**ENHANCE:** `services/ai-automation-service/src/api/` (add new router)

```python
# NEW FILE: services/ai-automation-service/src/api/device_intelligence_router.py

from fastapi import APIRouter

router = APIRouter(prefix="/api/device-intelligence", tags=["device-intelligence"])

@router.get("/utilization")
async def get_utilization_score():
    """Get overall device utilization percentage"""
    return {
        "score": 32,
        "configured_features": 45,
        "total_features": 140,
        "trend": "+12% this month",
        "by_manufacturer": {
            "Inovelli": 35,
            "Aqara": 38,
            "IKEA": 32,
            "Xiaomi": 28,
            "Other": 30
        }
    }

@router.get("/devices/{device_id}/capabilities")
async def get_device_capabilities(device_id: str):
    """Get all capabilities for a specific device (any manufacturer)"""
    return {
        "device_id": device_id,
        "manufacturer": "Inovelli",  # or Aqara, IKEA, etc.
        "model": "VZM31-SN",
        "capabilities": [...],
        "configured": [...],
        "unused": [...]
    }

@router.get("/opportunities")
async def get_top_opportunities():
    """Get top unused feature opportunities (all brands)"""
    return {
        "opportunities": [
            {
                "device_id": "...",
                "manufacturer": "Inovelli",
                "feature": "led_notifications",
                "impact": "high",
                "complexity": "easy"
            },
            {
                "device_id": "...",
                "manufacturer": "Aqara",
                "feature": "vibration_detection",
                "impact": "medium",
                "complexity": "easy"
            }
        ]
    }

@router.post("/capabilities/refresh")
async def refresh_device_capabilities():
    """Manually trigger MQTT re-sync for all devices"""
    return {"status": "refresh_started"}
```

**Integrates With:**
- ✅ Existing FastAPI app at port 8018
- ✅ Existing CORS configuration
- ✅ Existing database session management
- ✅ New `device_capabilities` and `device_feature_usage` tables

**Out of MVP:**
- ❌ GraphQL API
- ❌ WebSocket real-time updates
- ❌ Rate limiting
- ❌ Pagination (simple limits only)

**Effort:** 3-4 days

---

### MVP Feature Summary

**What Gets Added to Existing System:**

```
AI Automation Service (Port 8018):
├─ Database (SQLite - ai_automation.db)
│  ├─ patterns (EXISTING)
│  ├─ suggestions (EXISTING)
│  ├─ user_feedback (EXISTING)
│  ├─ device_capabilities (NEW - supports ALL manufacturers)
│  └─ device_feature_usage (NEW)
│
├─ Pattern Detection (EXISTING)
│  ├─ time_of_day_detector.py ✅
│  ├─ co_occurrence_detector.py ✅
│  └─ anomaly_detector.py ✅
│
├─ Suggestion Generation (ENHANCED)
│  ├─ generate_pattern_suggestions() ✅ EXISTING
│  └─ generate_feature_suggestions() 🆕 NEW (works for ALL brands)
│
├─ Device Intelligence (NEW)
│  ├─ mqtt_capability_listener.py 🆕 (universal)
│  ├─ capability_parser.py 🆕 (works for any manufacturer)
│  └─ utilization_calculator.py 🆕 (multi-brand)
│
├─ API Routes (ENHANCED)
│  ├─ /api/suggestions ✅ EXISTING
│  ├─ /api/patterns ✅ EXISTING
│  └─ /api/device-intelligence/* 🆕 NEW
│
└─ Scheduler (ENHANCED)
   └─ Daily job generates pattern + feature suggestions ✅+🆕

Health Dashboard (Port 3000):
└─ New Tab: "Device Intelligence" 🆕 (multi-brand aware)
```

**What You Get:**

```
Daily Suggestions (7:00 AM):
├─ Pattern-Based (EXISTING):
│  └─ "Create sunrise automation (bedroom light turns on 6am daily)"
│
└─ Feature-Based (NEW - Works for ALL brands):
   ├─ "[Inovelli - Kitchen] Enable LED notifications (unused)"
   ├─ "[Aqara - Front Door] Configure vibration detection"
   ├─ "[IKEA - Bedroom] Use color temperature presets"
   ├─ "[Xiaomi - Living Room] Enable temperature alerts"
   └─ "[Sonoff - Garage] Configure power monitoring"

Dashboard (NEW TAB):
├─ Device Utilization Score: 32% (all brands combined)
├─ Utilization by Manufacturer (chart)
├─ Top Feature Opportunities (ranked, multi-brand)
└─ Device Breakdown (all devices, all manufacturers)
```

**Coverage:**

| Integration | Device Count | MVP Support | Data Source |
|-------------|--------------|-------------|-------------|
| **Zigbee2MQTT** | **~6,000 models** | **✅ Full** | **MQTT Bridge (Auto)** |
| Z-Wave JS | ~3,000 models | ❌ Phase 2 | Z-Wave JS API |
| Native HA | Varies | ❌ Phase 3 | Integration APIs |
| Manual | Unlimited | ✅ Fallback | Context7/Manual |

---

### Out of Scope for MVP

**Deferred to Phase 2:**

1. ❌ Weekly/Monthly/Quarterly separate reports (daily only for MVP)
2. ❌ Z-Wave device support (Zigbee2MQTT only)
3. ❌ Automated capability refresh (manual trigger only)
4. ❌ Interactive configuration wizards (links to HA only)
5. ❌ Advanced pattern detection enhancements
6. ❌ Custom notification timing
7. ❌ Historical utilization trends (current state only)
8. ❌ Device health monitoring integration
9. ❌ Multi-device coordination suggestions
10. ❌ Custom capability editing UI

---

### MVP Development Timeline

**Total Development Time:** 5 weeks

```
Week 1: MQTT Capability Listener + Database
├─ MQTT subscription to Zigbee2MQTT bridge
├─ Parse 'exposes' format (universal parser)
├─ Database schema + tables
└─ Store capabilities for ALL devices (auto-populate)

Week 2: Feature Analysis + Matching
├─ Match devices to capabilities (by model)
├─ Feature usage tracking logic
├─ Utilization calculator (multi-brand)
└─ Unused feature detection

Week 3: Suggestion Engine Enhancement
├─ Feature-based suggestion generator (universal)
├─ Merge with pattern suggestions
├─ Confidence scoring
└─ Combined suggestion pipeline

Week 4: Dashboard + API
├─ Device Intelligence dashboard tab
├─ API endpoints (utilization, capabilities, opportunities)
├─ Charts and visualizations (multi-brand)
└─ Integration with existing dashboard

Week 5: Testing + Polish
├─ End-to-end testing (multi-brand devices)
├─ Bug fixes and refinements
├─ Documentation updates
└─ Production deployment

Total: 5 weeks to MVP deployment
```

---

### MVP Success Criteria (30 Days)

**Technical:**
- ✅ Capabilities populated for 95%+ of your 99 devices (ALL brands automatically)
- ✅ Daily suggestions include 2-3 feature-based (not just pattern)
- ✅ Dashboard tab loads in <2 seconds
- ✅ MQTT listener handles real-time device additions

**Value:**
- ✅ You discover 3+ features you didn't know existed (any brand)
- ✅ Device utilization increases from 20% to 25%+ (+5 points minimum)
- ✅ You configure 2+ suggested features
- ✅ At least 1 "I didn't know my devices could do that!" moment

**Engagement:**
- ✅ You check Device Intelligence tab 2+ times/week
- ✅ Feature suggestions feel relevant (not generic)
- ✅ You don't dismiss all feature suggestions
- ✅ System complements existing pattern suggestions well
- ✅ Works seamlessly across all your device brands

---

### What This Solves

**Before (Single Brand Example Approach):**
```
❌ Hard-coded manufacturer examples
❌ Requires manual Context7 lookup per manufacturer
❌ No scalability for multi-brand homes
❌ No real-time capability discovery
❌ Research burden increases with each new brand
```

**After (Universal Approach):**
```
✅ Works for ALL Zigbee manufacturers automatically
✅ One MQTT subscription = 6,000+ device models
✅ Real-time updates when new devices paired
✅ No manual research for 95%+ of devices
✅ Scalable to Z-Wave, WiFi, native integrations
✅ Brand-agnostic intelligence
✅ Future-proof as new manufacturers added to Zigbee2MQTT
```

---

## Post-MVP Vision

### Evolution Roadmap

#### **Phase 1: MVP (Months 1-2)** ✅

**Focus:** Universal device capability awareness + feature discovery

**Deliverables:**
- MQTT capability listener (ALL Zigbee manufacturers)
- Universal capability database
- Feature-based suggestions (works for all brands)
- Daily cadence (combined pattern + feature suggestions)
- Device Intelligence dashboard tab
- Utilization tracking (multi-brand)

**Coverage:** ~6,000 Zigbee device models from 100+ manufacturers

**Success Metric:** 25% device utilization (+5 points from 20%)

---

#### **Phase 2: Enhanced Intelligence (Months 3-4)**

**Focus:** Weekly summaries + Z-Wave support + advanced patterns

**New Features:**

**1. Weekly Summary Report**
```yaml
Every Sunday, 9:00 AM:
Title: "📊 Weekly Smart Home Summary"
Content:
  Patterns This Week:
    - 5 automation opportunities detected
    - 3 energy savings opportunities
  
  Features Discovered (Multi-Brand):
    - 4 LED notification configurations (Inovelli)
    - 2 vibration detection enabled (Aqara)
    - 3 color presets configured (IKEA)
    - Estimated $8/week energy savings
  
  Next Week Focus:
    - Motion sensor optimization (Aqara sensitivity)
    - Scene button configuration (various brands)
    - Smart bulb mode review (Inovelli + IKEA)
```

**2. Z-Wave Device Support**
- Integrate with Z-Wave JS API
- Parse Z-Wave device definitions
- Support Inovelli Z-Wave, Zooz, Fibaro, Aeotec, etc.
- ~3,000 additional device models

**3. Advanced Pattern Detection**
- **Spatial Patterns:** "Motion sensor + light in same room trigger together 95% of time"
- **Device Interaction:** "When switch A turns on, switch B turns on within 5 seconds"
- **Seasonal Patterns:** "HVAC usage correlates with weather patterns"

**4. Multi-Brand Coordination**
- **Cross-manufacturer suggestions:** "Bind Inovelli switch with IKEA bulb for better control"
- **Scene orchestration:** "5 devices from 3 brands used together during 'Movie Night'"
- **Area optimization:** "Living room has devices from 4 manufacturers - optimize as zone"

**Deliverables:**
- Weekly summary notifications
- Z-Wave capability discovery
- Advanced pattern detectors
- Multi-brand coordination engine

**Coverage:** ~9,000 device models (Zigbee + Z-Wave)

**Success Metric:** 35% device utilization (+10 points from Phase 1)

---

#### **Phase 3: Proactive Optimization (Months 5-6)**

**Focus:** Monthly reviews + native HA integration support + energy optimization

**New Features:**

**1. Monthly Optimization Reports**
```yaml
First Sunday of Month, 10:00 AM:
Title: "📈 Monthly Smart Home Report"
Content:
  This Month's Progress:
    - Device Utilization: 38% (+3% vs. last month)
    - Features Configured: 6 new (across 4 manufacturers)
    - Energy Savings: $23 estimated
    - Automation Quality: 35% fewer manual interventions
  
  Top Opportunities (Multi-Brand):
    1. LED notifications (8 Inovelli switches) - High impact
    2. Vibration detection (5 Aqara sensors) - Security boost
    3. Color presets (6 IKEA bulbs) - Convenience
    4. Power monitoring (4 Sonoff plugs) - $15/month potential
    5. Temperature alerts (10 Xiaomi sensors) - Comfort
```

**2. Native HA Integration Support**
- Philips Hue native integration capabilities
- Shelly native integration features
- TP-Link Kasa capabilities
- ESPHome custom device definitions

**3. Energy Optimization Engine**
- Auto-off timer recommendations (any brand)
- Power monitoring configurations (Sonoff, Shelly, Inovelli)
- Time-of-use optimization
- HVAC correlation with weather

**4. Device Health Integration**
- Battery level tracking (all sensor brands)
- Offline detection and alerts
- Firmware update notifications
- Unusual power draw warnings

**Deliverables:**
- Monthly report scheduler
- Native HA integration support
- Energy savings calculator
- Device health monitoring

**Coverage:** 9,000+ models + native HA integrations

**Success Metric:** 42% device utilization (+7 points from Phase 2), $50+ energy savings

---

#### **Phase 4: Mastery & Automation (Months 7-12)**

**Focus:** Quarterly deep dives + automation quality + learning loops

**New Features:**

**1. Quarterly Optimization Reviews**
```yaml
First Sunday of Quarter, 10:00 AM:
Title: "🎯 Quarterly Smart Home Deep Dive"
Content:
  Q2 2025 Summary:
    - Overall Utilization: 45% (target achieved!)
    - Features Added: 18 features across all brands
    - Energy Savings: $67 cumulative
    - Time Saved: 5 hours (fewer manual interventions)
  
  Top 10 Opportunities (Ranked by ROI, Multi-Brand):
    1. LED Notifications (12 devices) - High engagement
    2. Auto-off Timers (8 devices) - $45/year savings
    3. Vibration Detection (6 sensors) - Security value
    4. Color Presets (8 bulbs) - High convenience
    5. Power Monitoring (5 plugs) - Energy insights
    ...
```

**2. Interactive Configuration Wizards**
- Step-by-step guides for complex features (any brand)
- Pre-filled automation YAML from suggestions
- One-click deployment to HA
- Rollback support

**3. Advanced Analytics**
- Utilization trends over time (by brand)
- Feature adoption heatmaps
- Energy savings forecasting
- Cost-benefit analysis per device

**4. Learning & Personalization**
- User feedback influences future suggestions
- Dismissed suggestions not repeated
- Brand preferences learned
- Personal priority optimization

**Deliverables:**
- Quarterly report scheduler
- Interactive wizards (multi-brand aware)
- Advanced analytics dashboard
- Personalization engine

**Success Metric:** 45%+ device utilization, $150+ annual savings

---

### Long-Term Vision (12+ Months)

**The Ultimate Goal:**  
Transform HA-Ingestor into a **Smart Home Intelligence Platform** that:

1. **Understands Your Devices (Universal)**
   - Knows every capability of every device (any manufacturer)
   - Tracks utilization in real-time (multi-brand)
   - Suggests optimizations proactively

2. **Learns Your Patterns**
   - Temporal, spatial, behavioral patterns
   - Predictive suggestions based on history
   - Personalized to your habits and device mix

3. **Optimizes Continuously**
   - Daily feature discoveries (all brands)
   - Weekly pattern analysis
   - Monthly optimization reviews
   - Quarterly ROI validation

4. **Provides Measurable Value**
   - Energy savings tracked and reported
   - Time savings quantified
   - Device ROI validated (per manufacturer)
   - Automation quality improved

5. **Enables Mastery**
   - 45%+ device utilization (all brands)
   - Sophisticated automations made easy
   - Confidence in multi-brand configuration
   - Community knowledge sharing

**Positioning Statement:**

> "HA-Ingestor started as a data collection platform. It evolved into an AI-powered automation advisor. It culminates as a **Smart Home Intelligence Platform** that ensures you maximize the value of every device from every manufacturer, every automation, and every watt of energy in your home."

---

## Technical Considerations & Integration

### What Home Assistant Already Provides

Based on [Home Assistant's official documentation](https://www.home-assistant.io/docs/) and [developer documentation](https://developers.home-assistant.io/), here's how Device Intelligence integrates with Home Assistant's existing architecture.

#### **Device Registry (Built-in)**

Home Assistant maintains a **device registry** that stores basic device metadata:

```python
# From HA DeviceInfo TypedDict
device_info = {
    "identifiers": {("domain", "unique_id")},
    "name": "Kitchen Switch",
    "manufacturer": "Inovelli",     # ✅ We have this
    "model": "VZM31-SN",              # ✅ We have this
    "model_id": "VZM31-SN",           # ✅ We have this
    "sw_version": "1.2.3",            # ✅ We have this
    "hw_version": "1.0",              # ✅ We have this
    "connections": {("mac", "...")},
    "via_device": ("domain", "hub_id"),
    "suggested_area": "Kitchen"
}
```

**What's Stored:**
- ✅ Manufacturer name
- ✅ Model name and ID
- ✅ Firmware/hardware versions
- ✅ MAC address
- ✅ Area/room assignment
- ✅ Connection topology

**What's NOT Stored:**
- ❌ Device capabilities (features it supports)
- ❌ Configuration options available
- ❌ Feature utilization status
- ❌ Best practices for device
- ❌ Advanced features documentation

---

### The Missing Layer: Device Capabilities

#### **The Gap**

Home Assistant knows **what** your device is (manufacturer, model), but not **what it can do**:

```yaml
# What HA Knows (Device Registry):
Manufacturer: Inovelli
Model: VZM31-SN
Firmware: 2.15
Area: Kitchen

# What HA DOESN'T Know (Capabilities):
LED Notifications: Supported (7 individual LEDs)
Button Events: Supported (10+ tap patterns)
Smart Bulb Mode: Supported (disable relay)
Fan Control Mode: Supported (3-speed presets)
Auto-Off Timer: Supported (configurable)
Power Monitoring: Supported (real-time watts)
```

**This gap exists for ALL manufacturers** - not just Inovelli, but also Aqara, IKEA, Xiaomi, Sonoff, and 100+ more.

---

### Our Solution: Universal Capability Discovery

#### **Data Sources**

**1. Zigbee2MQTT MQTT Bridge (Primary for Zigbee devices)**

**The Breakthrough:** Zigbee2MQTT publishes comprehensive device capabilities for **ALL Zigbee manufacturers** via MQTT topic `zigbee2mqtt/bridge/devices`.

**Access Method:**
```python
# Subscribe to MQTT topic
mqtt_client.subscribe("zigbee2mqtt/bridge/devices")

# Receive complete device database
devices = [
  {
    "friendly_name": "kitchen_switch",
    "definition": {
      "vendor": "Inovelli",
      "model": "VZM31-SN",
      "exposes": [...]  # ALL capabilities
    }
  },
  {
    "friendly_name": "front_door_sensor",
    "definition": {
      "vendor": "Aqara",
      "model": "MCCGQ11LM",
      "exposes": [...]  # ALL capabilities
    }
  },
  # ... for EVERY Zigbee device from EVERY manufacturer!
]
```

**What You Get:**
- Complete capability definitions
- Configuration options
- MQTT topics for control
- Value templates
- Usage examples

**Coverage:** ~6,000 Zigbee device models from 100+ manufacturers

---

**2. Z-Wave JS (Phase 2 - For Z-Wave Devices)**

**Access Method:** Query Z-Wave JS API or Context7 library `/zwave-js/zwave-js`

**What You Get:**
- Device configuration parameters
- Command classes (capabilities)
- Manufacturer-specific features

**Coverage:** ~3,000+ Z-Wave device models

---

**3. Home Assistant Integration APIs (Phase 3 - For Native Integrations)**

**Access Method:** Query HA Integration documentation or device attributes

**Examples:**
- Philips Hue (native integration)
- Shelly (native integration)
- TP-Link Kasa
- ESPHome

---

**4. Context7 Fallback (For Edge Cases)**

**Access Method:** Query Context7 when device not in MQTT bridge

**Use Cases:**
- WiFi devices without MQTT representation
- Proprietary integrations
- Custom/DIY devices

---

### Integration Architecture

#### **Data Flow**

```
Home Assistant Device Registry (Existing)
  ↓
  ├─ Device discovered via Zigbee2MQTT
  ├─ Device metadata stored (manufacturer, model)
  ↓
Zigbee2MQTT MQTT Bridge
  ↓
  ├─ Publishes complete device list to MQTT
  ├─ Includes ALL capabilities for ALL manufacturers
  ├─ Topic: zigbee2mqtt/bridge/devices
  ↓
AI Automation Service (Enhanced)
  ↓
  ├─ MQTT listener subscribes to bridge topic
  ├─ Parses capabilities for ALL devices (universal parser)
  ├─ Stores in device_capabilities table
  ├─ Links via devices.model → device_capabilities.device_model
  ├─ Tracks feature usage in device_feature_usage table
  └─ Generates capability-based suggestions (any brand)
```

---

### Constraints & Limitations

#### **Technical Constraints**

**1. MQTT Bridge Dependency**
- Requires Zigbee2MQTT integration in Home Assistant
- **Mitigation:** Already in use for Zigbee devices

**2. Data Accuracy**
- Zigbee2MQTT docs may lag firmware updates
- **Mitigation:** Manual refresh capability, Context7 fallback

**3. Single-Home Scope**
- Not designed for multi-tenant
- **Benefit:** Simpler architecture, no scale concerns

**4. Integration Type Coverage**
- MVP: Zigbee2MQTT only (~6,000 models)
- Phase 2: Z-Wave JS (~3,000 models)
- Phase 3+: Native HA integrations

---

### Security & Privacy

**Data Storage:**
- ✅ All data stored locally (SQLite)
- ✅ No cloud dependencies (except Context7 fallback research)
- ✅ No telemetry or phone-home

**API Access:**
- ✅ Local network only (no internet exposure)
- ✅ No authentication required (trusted network)

**Privacy:**
- ✅ Device model names only (no personal data)
- ✅ No usage patterns sent externally
- ✅ All analysis happens locally

---

### Performance Considerations

**Initial Capability Population:**
- ~99 devices × <1 second per MQTT message
- Estimated: 2-3 minutes one-time setup
- **Benefit:** Instant for devices already in Zigbee2MQTT

**Daily Suggestion Generation:**
- Pattern detection: ~30 seconds (InfluxDB queries)
- Feature analysis: ~10 seconds (SQLite queries)
- LLM suggestion generation: ~30 seconds (OpenAI API)
- **Total:** <2 minutes daily batch job

**Dashboard Load Time:**
- Device utilization query: <500ms
- Opportunity list: <1 second
- Charts rendering: <1 second
- **Total:** <2 seconds page load

---

## Resources & References

### Home Assistant Official Documentation

Based on [Home Assistant documentation structure](https://www.home-assistant.io/docs/):

| **Purpose** | **Documentation** | **When to Use** |
|-------------|-------------------|-----------------|
| **User Setup & Config** | [Home Assistant Docs](https://www.home-assistant.io/docs/) | Understanding HA basics, automation structure |
| **Integrations & Devices** | [Integrations Page](https://www.home-assistant.io/integrations/) | Finding integration-specific capabilities |
| **Developer / Advanced** | [Developer Docs](https://developers.home-assistant.io/) | Understanding device registry, entity registry, API structure |
| **Installation** | [Installation Docs](https://www.home-assistant.io/installation/) | Initial setup, deployment planning |

**Critical Developer Documentation:**

- [Device Registry Index](https://developers.home-assistant.io/docs/device_registry_index) - Understanding `DeviceInfo` TypedDict
- [Entity Documentation](https://developers.home-assistant.io/docs/core/entity) - Entity-to-device relationships
- [Home Assistant REST API](https://developers.home-assistant.io/docs/api/rest/) - Query device registry programmatically

---

### Zigbee2MQTT Documentation

**Primary Source for Device Capabilities**

- **GitHub:** https://github.com/koenkk/zigbee2mqtt.io
- **Documentation:** https://www.zigbee2mqtt.io/
- **Device Database:** https://www.zigbee2mqtt.io/supported-devices/

**MQTT Bridge Topic:**
```
Topic: zigbee2mqtt/bridge/devices
Format: JSON array with complete device list
Contains: ALL capabilities for ALL Zigbee manufacturers
Coverage: ~6,000 device models from 100+ manufacturers
```

**Context7 Access:**
- Library ID: `/koenkk/zigbee2mqtt.io`
- Trust Score: 9.3/10
- Code Snippets: 29,927

---

### Z-Wave JS Documentation (Phase 2)

**For Z-Wave Device Support**

- **Context7 ID:** `/zwave-js/zwave-js`
- **Trust Score:** 9.4/10
- **Coverage:** ~3,000 Z-Wave device models

---

### Existing Project Documentation

**Location:** `docs/architecture/`

**Key Files:**
- `tech-stack.md` - Technology stack overview
- `database-schema.md` - Database design
- `data-models.md` - Data structures

**AI Automation Stories:**
- `docs/stories/story-ai1-*` - Existing AI automation implementation
- Reference for patterns to follow

---

### Quick Reference Links

**Daily:**
- [Zigbee2MQTT Supported Devices](https://www.zigbee2mqtt.io/supported-devices/)
- [HA Developer Docs - Device Registry](https://developers.home-assistant.io/docs/device_registry_index)
- Existing AI Automation Service code

**Weekly:**
- [HA Integration Documentation](https://www.home-assistant.io/integrations/)
- [FastAPI Docs](https://fastapi.tiangolo.com/)

---

## Next Steps

### Immediate Actions

1. **Review and Approve Brief** - Stakeholder review of this document
2. **Technical Validation** - Verify MQTT bridge accessibility and data format
3. **Create Development Stories** - Break down MVP into implementable stories
4. **Set Up Development Environment** - Prepare for implementation
5. **Begin Week 1: MQTT Listener** - Start with capability discovery

### Success Criteria for Brief

- ✅ Clear understanding of problem (device capability gap)
- ✅ Universal solution defined (works for ALL Zigbee manufacturers)
- ✅ MVP scope realistic and achievable (5 weeks)
- ✅ Integration approach non-invasive (enhances existing system)
- ✅ Success metrics defined (utilization, discovery, savings)
- ✅ Post-MVP vision outlined (roadmap to mastery)

---

**Document Status:** Ready for Review  
**Next Update:** After stakeholder feedback  
**Version:** 1.0  
**Last Updated:** 2025-01-16

