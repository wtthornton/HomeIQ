# ML Models & Enriched Context Analysis

**Created:** January 2025  
**Status:** Design Review  
**Purpose:** Comprehensive analysis of ML models used and enriched context data availability/usage

---

## 1. ML Models Used in the System

### ❌ OpenAI is NOT the Only ML Model

The system uses a **hybrid multi-model approach** with **8+ different ML/AI technologies**:

---

### 1.1 Entity Extraction Models (Primary Workflow)

#### **Model 1: Hugging Face BERT-base-NER** (Primary - 90% of queries)

**Location:** `services/ai-automation-service/src/entity_extraction/multi_model_extractor.py`

**Model:** `dslim/bert-base-NER`  
**Framework:** Hugging Face Transformers  
**Architecture:** BERT-based Named Entity Recognition  
**Cost:** FREE  
**Speed:** ~50ms per query  
**Accuracy:** 90%+ for standard queries

**Usage:**
- Primary entity extraction method
- Extracts device names, locations, and entities from user queries
- Uses confidence threshold (0.8) to determine if results are reliable
- Falls back to OpenAI if confidence is low

**Code Reference:**
```python
# From multi_model_extractor.py:68-78
def _get_ner_pipeline(self):
    if self._ner_pipeline is None:
        self._ner_pipeline = pipeline("ner", model=self.ner_model)
    return self._ner_pipeline
```

---

#### **Model 2: OpenAI GPT-4o-mini** (Fallback - 10% of queries)

**Location:** `services/ai-automation-service/src/entity_extraction/multi_model_extractor.py`

**Model:** `gpt-4o-mini`  
**Cost:** ~$0.0004 per query  
**Speed:** 1-2 seconds  
**Usage:** Complex or ambiguous queries where NER confidence is low

**When Used:**
- NER confidence < 0.8
- Complex queries with ambiguous references
- Queries requiring context understanding

---

#### **Model 3: Pattern Matching** (Emergency Fallback - 0% of queries)

**Location:** `services/ai-automation-service/src/entity_extraction/pattern_extractor.py`

**Method:** Regex-based pattern matching  
**Cost:** FREE  
**Speed:** <1ms  
**Usage:** Emergency fallback if both NER and OpenAI fail

---

#### **Model 4: spaCy** (Mentioned, but usage unclear)

**Location:** `services/ai-automation-service/src/entity_extraction/multi_model_extractor.py:91-99`

**Model:** `en_core_web_sm`  
**Status:** Loaded but usage not clear from code  
**Purpose:** Emergency NLP fallback

---

### 1.2 Suggestion Generation Models

#### **Model 5: OpenAI GPT-4o-mini** (Suggestion Generation)

**Location:** `services/ai-automation-service/src/llm/openai_client.py`

**Model:** `gpt-4o-mini`  
**Cost:** ~$0.000137 per suggestion  
**Temperature:** 0.7 (creative suggestions) or 0.3 (YAML generation)  
**Usage:** 
- Generates automation suggestions from user queries
- Converts descriptions to YAML
- Reverse engineering self-correction

---

### 1.3 Embedding Models (Synergy Detection)

#### **Model 6: Sentence Transformers** (Device Embeddings)

**Location:** `services/ai-automation-service/src/nlevel_synergy/embedding_model.py`

**Model:** `sentence-transformers/all-MiniLM-L6-v2`  
**Optimization:** INT8 quantized (OpenVINO)  
**Size:** ~20MB (INT8) vs ~80MB (FP32)  
**Speed:** ~50ms per batch (32 devices)  
**Purpose:** Device relationship embeddings for synergy detection

**Usage:**
- Generates 384-dim embeddings for device descriptions
- Used in synergy detection (Epic AI-4)
- Enables similarity search for device relationships

---

#### **Model 7: BGE Reranker** (Path Re-ranking)

**Location:** `services/ai-automation-service/src/nlevel_synergy/` (implied)

**Model:** `OpenVINO/bge-reranker-base-int8-ov`  
**Size:** ~280MB (pre-quantized)  
**Speed:** ~80ms for 100 candidates  
**Purpose:** Re-ranks top 100 device paths → best 10 chains  
**Quality Boost:** +10-15% over embedding similarity alone

---

#### **Model 8: FLAN-T5** (Chain Categorization)

**Location:** `services/ai-automation-service/src/nlevel_synergy/` (implied)

**Model:** `google/flan-t5-small` (INT8/OpenVINO)  
**Size:** ~80MB  
**Speed:** ~100ms per classification  
**Purpose:** Automation chain categorization  
**Accuracy:** 75-80%

---

### 1.4 Model Usage Summary

| Model | Purpose | Cost | Speed | Usage % |
|-------|---------|------|-------|---------|
| BERT-base-NER | Entity extraction | FREE | 50ms | 90% |
| GPT-4o-mini | Entity extraction (fallback) | $0.0004 | 1-2s | 10% |
| GPT-4o-mini | Suggestion generation | $0.000137 | 500ms | 100% |
| GPT-4o-mini | YAML generation | $0.000137 | 500ms | 100% |
| Pattern matching | Entity extraction (emergency) | FREE | <1ms | 0% |
| Sentence Transformers | Device embeddings | FREE | 50ms | For synergy |
| BGE Reranker | Path re-ranking | FREE | 80ms | For synergy |
| FLAN-T5 | Chain categorization | FREE | 100ms | For synergy |

**Total ML Models:** 8+ models across different tasks

**Cost Breakdown:**
- Entity extraction: ~90% FREE (NER), ~10% paid (OpenAI)
- Suggestion/YAML generation: 100% paid (OpenAI)
- Synergy detection: 100% FREE (local models)

---

## 2. Enriched Context Data Available

### Complete Enriched Entity Data Structure

**Location:** `services/ai-automation-service/src/services/comprehensive_entity_enrichment.py`

The comprehensive enrichment combines **3 data sources**:

---

### 2.1 Home Assistant Attributes (Source 1)

**From:** HA API (`EntityAttributeService`)

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `friendly_name` | string | Human-readable entity name | "WLED Office" |
| `icon` | string | Entity icon identifier | "mdi:lightbulb" |
| `device_class` | string | Device classification | "light" |
| `unit_of_measurement` | string | Measurement unit | "%", "°C" |
| `state` | string | Current state | "on", "off", "25.5" |
| `last_changed` | datetime | Last state change time | ISO timestamp |
| `last_updated` | datetime | Last update time | ISO timestamp |
| `attributes` | dict | All HA attributes | `{brightness: 128, ...}` |
| `is_group` | boolean | Is group entity | `true`/`false` |
| `integration` | string | HA integration | "wled", "homekit" |
| `supported_features` | integer | Feature bitmask | 255 (all features) |
| `device_id` | string | Device ID | "wled_office_device" |
| `area_id` | string | Area/room ID | "office" |

---

### 2.2 Device Intelligence Data (Source 2)

**From:** Device Intelligence Service (`DeviceIntelligenceClient`)

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `device_name` | string | Device name | "WLED Office" |
| `manufacturer` | string | Manufacturer | "WLED", "Apple" |
| `model` | string | Device model | "ESP8266", "HomeKit Light" |
| `sw_version` | string | Software version | "0.14.0" |
| `hw_version` | string | Hardware version | "v1.0" |
| `power_source` | string | Power source | "battery", "mains" |
| `area_name` | string | Area/room name | "Office", "Living Room" |
| `capabilities` | array | Device capabilities | `[{type: "numeric", name: "brightness", ...}]` |
| `health_score` | integer | Device health (0-100) | 95 |
| `last_seen` | datetime | Last seen timestamp | ISO timestamp |
| `device_class_from_intel` | string | Device class | "light" |

---

### 2.3 Historical Patterns (Source 3 - Optional)

**From:** Data API (`DataAPIClient`)

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `usage_frequency` | float | Usage frequency | 0.85 |
| `common_states` | array | Common state values | `["on", "off"]` |
| `typical_usage_times` | array | Typical usage times | `["18:00", "22:00"]` |
| `recent_activity` | datetime | Recent activity timestamp | ISO timestamp |

---

### 2.4 Complete Enriched Entity Structure

**Full Combined Structure:**
```json
{
  "entity_id": "light.wled_office",
  "domain": "light",
  
  // HA Attributes (Source 1)
  "friendly_name": "WLED Office",
  "icon": "mdi:lightbulb",
  "device_class": "light",
  "unit_of_measurement": null,
  "state": "on",
  "last_changed": "2025-11-03T17:30:00.000Z",
  "last_updated": "2025-11-03T17:30:00.000Z",
  "attributes": {
    "friendly_name": "WLED Office",
    "supported_features": 255,
    "brightness": 128,
    "color_mode": "rgb",
    "rgb_color": [255, 0, 0],
    "effect_list": ["fireworks", "rainbow", "solid", ...],
    "min_mireds": 153,
    "max_mireds": 500,
    ...
  },
  "is_group": false,
  "integration": "wled",
  "supported_features": 255,
  "device_id": "wled_office_device",
  "area_id": "office",
  
  // Device Intelligence (Source 2)
  "device_name": "WLED Office",
  "manufacturer": "WLED",
  "model": "ESP8266",
  "sw_version": "0.14.0",
  "hw_version": "v1.0",
  "power_source": "mains",
  "area_name": "Office",
  "capabilities": [
    {
      "type": "numeric",
      "name": "brightness",
      "feature": "brightness",
      "supported": true,
      "properties": {
        "min": 0,
        "max": 255,
        "unit": "brightness"
      }
    },
    {
      "type": "enum",
      "name": "effect",
      "feature": "effect",
      "supported": true,
      "properties": {
        "values": ["fireworks", "rainbow", "solid", ...]
      }
    },
    {
      "type": "composite",
      "name": "rgb_color",
      "feature": "rgb_color",
      "supported": true,
      "properties": {
        "components": ["r", "g", "b"],
        "r": {"min": 0, "max": 255},
        "g": {"min": 0, "max": 255},
        "b": {"min": 0, "max": 255}
      }
    }
  ],
  "health_score": 95,
  "last_seen": "2025-11-03T17:30:00.000Z",
  "device_class_from_intel": "light",
  
  // Historical Patterns (Source 3 - Optional)
  "usage_frequency": 0.85,
  "common_states": ["on", "off"],
  "typical_usage_times": ["18:00", "22:00"],
  "recent_activity": "2025-11-03T17:30:00.000Z"
}
```

---

### 2.5 Capability Details Structure

**Capability Types:**
- **Numeric:** `{type: "numeric", name: "brightness", properties: {min: 0, max: 255, unit: "%"}}`
- **Enum:** `{type: "enum", name: "effect", properties: {values: ["fireworks", "rainbow", ...]}}`
- **Composite:** `{type: "composite", name: "rgb_color", properties: {components: ["r", "g", "b"], ...}}`
- **Binary:** `{type: "binary", name: "on_off", supported: true}`

---

## 3. How Enriched Context is Currently Used

### Current Usage in Prompts

**Location:** `services/ai-automation-service/src/prompt_building/unified_prompt_builder.py`

#### 3.1 Entity Context Section (Text Format)

**Method:** `_build_entity_context_section()` (Lines 411-455)

**What's Included:**
- ✅ Entity name
- ✅ Manufacturer and model
- ✅ Capabilities (with detailed formatting)
- ✅ Health score
- ✅ Area/location

**What's MISSING:**
- ❌ Full attributes (only friendly_name, capabilities)
- ❌ Device class details
- ❌ Integration information
- ❌ Supported features details
- ❌ Historical usage patterns
- ❌ Software/hardware versions
- ❌ Power source
- ❌ State information
- ❌ Last seen timestamps

---

#### 3.2 Enriched Entity Context JSON (Full Data)

**Location:** `services/ai-automation-service/src/prompt_building/entity_context_builder.py`

**Method:** `build_entity_context_json()` (Lines 121-198)

**What's Included:**
- ✅ Entity ID
- ✅ Friendly name
- ✅ Domain
- ✅ Type (individual/group/scene)
- ✅ State
- ✅ Description
- ✅ Capabilities (array)
- ✅ Attributes (full passthrough)
- ✅ Is group flag
- ✅ Integration

**What's MISSING:**
- ❌ Manufacturer/model
- ❌ Health score
- ❌ Area name
- ❌ Device Intelligence data
- ❌ Historical patterns
- ❌ Software/hardware versions

---

#### 3.3 Comprehensive Enrichment Format (Full Data)

**Location:** `services/ai-automation-service/src/services/comprehensive_entity_enrichment.py`

**Method:** `format_comprehensive_enrichment_for_prompt()` (Lines 370-461)

**What's Included:**
- ✅ Entity ID
- ✅ Friendly name
- ✅ Device class
- ✅ Domain
- ✅ Current state
- ✅ Location (area_name/area_id)
- ✅ Device info (manufacturer, model)
- ✅ Integration
- ✅ Health score
- ✅ Capabilities (detailed)
- ✅ Supported features
- ✅ Group indicator
- ✅ Software version
- ✅ Last seen

**What's MISSING:**
- ❌ Historical usage patterns (if not enabled)
- ❌ Full attributes dump (only selected fields)
- ❌ Hardware version
- ❌ Power source

---

### 3.4 Usage Analysis

#### ✅ **What's Being Used:**

1. **For Suggestion Generation:**
   - Entity context section (text format) - basic info
   - Enriched entity context JSON - full entity data
   - Capability examples - dynamic based on devices

2. **For YAML Generation:**
   - Enriched entity context JSON (if cached)
   - Comprehensive enrichment format (if available)
   - Validated entities mapping

#### ⚠️ **What's NOT Being Used Optimally:**

1. **Historical Patterns:**
   - Available but `include_historical=False` by default
   - Could help with timing-based automations
   - Could inform "typical usage times" for suggestions

2. **Health Scores:**
   - Included in text format but not prominently emphasized
   - Prompt says "avoid devices with health_score < 50" but not enforced
   - Could be used to filter out unhealthy devices

3. **Manufacturer/Model:**
   - Included but not leveraged for device-specific features
   - Could enable manufacturer-specific automation patterns

4. **Full Attributes:**
   - Available but only selected fields shown
   - Could provide more context for automation generation

5. **State Information:**
   - Current state available but not used
   - Could help with "current state aware" suggestions

---

## 4. Recommendations: Are We Using It Correctly?

### Current State Assessment

**Strengths:**
- ✅ Comprehensive enrichment combines multiple data sources
- ✅ Rich capability data with types and ranges
- ✅ Health scores included (though not enforced)
- ✅ Manufacturer/model information available
- ✅ Multiple formatting options for different use cases

**Weaknesses:**
- ⚠️ Historical patterns not used (even though available)
- ⚠️ Health scores not enforced (just mentioned in prompt)
- ⚠️ Full attributes not always included in prompts
- ⚠️ State information not utilized
- ⚠️ Some enrichment data is duplicated across sources

---

## 5. Recommendations (All Priorities)

### 🔴 HIGH PRIORITY Recommendations

---

#### **Recommendation 1.1: Enable Historical Patterns**

**Current State:** `include_historical=False` by default  
**Impact:** Medium - Better timing suggestions

**What to Change:**
```python
# File: services/ai-automation-service/src/api/ask_ai_router.py
# Location: generate_suggestions_from_query() function, ~line 2054

# Current:
enriched_data = await enrich_entities_comprehensively(
    entity_ids=set(entity_ids),
    ha_client=ha_client,
    device_intelligence_client=device_intelligence_client,
    data_api_client=data_api_client,
    include_historical=False  # ← Currently disabled
)

# Recommended:
enriched_data = await enrich_entities_comprehensively(
    entity_ids=set(entity_ids),
    ha_client=ha_client,
    device_intelligence_client=device_intelligence_client,
    data_api_client=data_api_client,
    include_historical=True  # ← Enable for better suggestions
)
```

**Benefits:**
- ✅ Can suggest automations based on usage patterns
- ✅ Can recommend optimal timing for automations
- ✅ Can identify "typical usage times" for better suggestions
- ✅ More context-aware automation ideas

**Example Usage:**
- If device is typically used at 18:00, suggest "Turn on at 6 PM"
- If device is frequently "on", suggest "Turn off when not in use"
- Use `typical_usage_times` to suggest scheduling automations

**Risks:**
- ⚠️ Slightly slower (queries Data API for historical data)
- ⚠️ May add 100-200ms to enrichment time
- ⚠️ Data API must be available

**Implementation Steps:**
1. Change `include_historical=False` to `include_historical=True`
2. Add timeout handling for Data API queries
3. Add fallback if historical data unavailable
4. Test with real queries to verify improvement

**Files to Modify:**
- `services/ai-automation-service/src/api/ask_ai_router.py` (line ~2054)

---

#### **Recommendation 1.2: Enforce Health Score Filtering**

**Current State:** Health scores mentioned but not enforced  
**Impact:** High - Prevents unreliable automations

**What to Change:**
```python
# File: services/ai-automation-service/src/api/ask_ai_router.py
# Location: generate_suggestions_from_query() function, after entity enrichment

# Current:
# No filtering - all entities passed to OpenAI

# Recommended:
# Filter entities by health score before prompt generation
HEALTH_SCORE_THRESHOLD = 50  # Minimum health score

# Filter out unhealthy devices
healthy_entities = []
unhealthy_entities = []

for entity in entities:
    health_score = entity.get('health_score', 100)  # Default to 100 if not available
    if health_score >= HEALTH_SCORE_THRESHOLD:
        healthy_entities.append(entity)
    else:
        unhealthy_entities.append(entity)
        logger.warning(f"⚠️ Excluding unhealthy device: {entity.get('name', entity.get('entity_id'))} (health_score: {health_score})")

# Use only healthy entities for prompt generation
entities = healthy_entities

# Log summary
if unhealthy_entities:
    logger.info(f"📊 Filtered {len(unhealthy_entities)} unhealthy devices (health_score < {HEALTH_SCORE_THRESHOLD})")
```

**Benefits:**
- ✅ Prevents suggesting automations for unreliable devices
- ✅ Improves user experience (fewer failed automations)
- ✅ Reduces frustration from non-functional automations
- ✅ Better automation success rate

**Configuration Options:**
- Make threshold configurable via settings
- Add option to warn instead of filter
- Allow user override for specific devices

**Example:**
```python
# In config.py
health_score_threshold: int = 50  # Minimum health score for suggestions
health_score_filter_mode: str = "filter"  # "filter" | "warn" | "none"
```

**Implementation Steps:**
1. Add health score filtering logic
2. Add configuration options
3. Add logging for filtered devices
4. Update prompt to mention filtering (if any devices were filtered)
5. Test with devices of varying health scores

**Files to Modify:**
- `services/ai-automation-service/src/api/ask_ai_router.py` (after entity enrichment)
- `services/ai-automation-service/src/config.py` (add settings)

---

### 🟡 MEDIUM PRIORITY Recommendations

---

#### **Recommendation 2.1: Use State Information for Context-Aware Suggestions**

**Current State:** State available but not used  
**Impact:** Medium - More context-aware suggestions

**What to Change:**
```python
# File: services/ai-automation-service/src/prompt_building/unified_prompt_builder.py
# Location: _build_entity_context_section() method, ~line 411

# Current:
# State information not included in entity context

# Recommended:
# Add state information to entity context
if entity.get('state') and entity.get('state') != 'unknown':
    entity_info += f" [Current State: {entity['state']}]"
```

**Also, add state-aware guidance in prompts:**
```python
# In build_query_prompt() method
state_awareness_section = """
CURRENT DEVICE STATES:
"""
for entity in entities:
    if entity.get('state') and entity.get('state') != 'unknown':
        state_awareness_section += f"- {entity.get('name', entity.get('entity_id'))}: {entity['state']}\n"

state_awareness_section += """
Use current device states to make context-aware suggestions:
- If device is currently "on", consider suggesting "turn off" scenarios
- If device is currently "off", consider suggesting "turn on" scenarios
- Use state information to suggest complementary actions
"""
```

**Benefits:**
- ✅ Can suggest automations based on current state
- ✅ Can recommend "turn off" if device is currently "on"
- ✅ More context-aware suggestions
- ✅ Better user experience (suggests relevant actions)

**Example:**
- Device is "on" → Suggest "Turn off when leaving room"
- Device is "off" → Suggest "Turn on when entering room"
- Device is "25°C" → Suggest "Set to 22°C for comfort"

**Implementation Steps:**
1. Add state information to entity context section
2. Add state awareness section to prompts
3. Update prompt instructions to use state information
4. Test with devices in different states

**Files to Modify:**
- `services/ai-automation-service/src/prompt_building/unified_prompt_builder.py` (lines 411-455)

---

#### **Recommendation 2.2: Leverage Manufacturer/Model Information**

**Current State:** Included but not actively used  
**Impact:** Medium - Better device-specific features

**What to Change:**
```python
# File: services/ai-automation-service/src/prompt_building/unified_prompt_builder.py
# Location: build_query_prompt() method, ~line 118

# Add manufacturer-specific examples section
manufacturer_examples = """
MANUFACTURER-SPECIFIC CAPABILITIES:
"""

# Group entities by manufacturer
manufacturers = {}
for entity in entities:
    manufacturer = entity.get('manufacturer')
    if manufacturer:
        if manufacturer not in manufacturers:
            manufacturers[manufacturer] = []
        manufacturers[manufacturer].append(entity)

# Add manufacturer-specific guidance
for manufacturer, mfg_entities in manufacturers.items():
    manufacturer_examples += f"\n{manufacturer} devices:\n"
    for entity in mfg_entities:
        model = entity.get('model', '')
        capabilities = entity.get('capabilities', [])
        if capabilities:
            cap_names = [cap.get('name', str(cap)) if isinstance(cap, dict) else str(cap) for cap in capabilities[:3]]
            manufacturer_examples += f"  - {entity.get('name')} ({model}): {', '.join(cap_names)}\n"
    
    # Add manufacturer-specific suggestions
    if manufacturer.lower() == 'wled':
        manufacturer_examples += "    → WLED-specific: Use effects like 'fireworks', 'rainbow', 'pride'\n"
    elif manufacturer.lower() == 'philips' or 'hue' in manufacturer.lower():
        manufacturer_examples += "    → Hue-specific: Use color temperature, scenes, transitions\n"
    elif 'homekit' in manufacturer.lower():
        manufacturer_examples += "    → HomeKit-specific: Use color temperature, brightness, scenes\n"
```

**Benefits:**
- ✅ Can suggest manufacturer-specific features
- ✅ Can provide better integration-specific guidance
- ✅ Better understanding of device capabilities
- ✅ More accurate automation suggestions

**Examples:**
- WLED: Suggest effects like "fireworks", "rainbow", "pride"
- Philips Hue: Suggest color temperature, scenes, transitions
- HomeKit: Suggest HomeKit-specific features

**Implementation Steps:**
1. Add manufacturer grouping logic
2. Create manufacturer-specific examples
3. Add manufacturer-specific guidance to prompts
4. Test with different manufacturers

**Files to Modify:**
- `services/ai-automation-service/src/prompt_building/unified_prompt_builder.py` (build_query_prompt method)

---

#### **Recommendation 2.3: Better Integration-Specific Guidance**

**Current State:** Integration info available but not leveraged  
**Impact:** Medium - Better integration-specific features

**What to Change:**
```python
# File: services/ai-automation-service/src/prompt_building/unified_prompt_builder.py
# Location: build_query_prompt() method

# Add integration-specific guidance
integration_guidance = """
INTEGRATION-SPECIFIC NOTES:
"""

integrations = set(entity.get('integration', 'unknown') for entity in entities)

for integration in integrations:
    if integration == 'wled':
        integration_guidance += """
- WLED: Use light.turn_on service (NOT wled.turn_on)
- WLED supports effects: fireworks, rainbow, solid, etc.
- WLED brightness range: 0-255
"""
    elif integration == 'homekit':
        integration_guidance += """
- HomeKit: Use light.turn_on service
- HomeKit supports color temperature (mireds: 200-500)
- HomeKit supports brightness (0-255)
"""
    elif integration == 'hue':
        integration_guidance += """
- Hue: Use light.turn_on service
- Hue supports scenes, transitions, color temperature
- Hue group entities control multiple lights
"""
```

**Benefits:**
- ✅ Better integration-specific automation suggestions
- ✅ More accurate service calls
- ✅ Better understanding of integration capabilities

**Implementation Steps:**
1. Add integration detection logic
2. Create integration-specific guidance
3. Add to prompts
4. Test with different integrations

**Files to Modify:**
- `services/ai-automation-service/src/prompt_building/unified_prompt_builder.py`

---

### 🟢 LOW PRIORITY Recommendations

---

#### **Recommendation 3.1: Include Full Attributes When Needed**

**Current State:** Selected attributes only  
**Impact:** Low - More context but larger prompts

**What to Change:**
```python
# File: services/ai-automation-service/src/services/comprehensive_entity_enrichment.py
# Location: format_comprehensive_enrichment_for_prompt() method, ~line 370

# Add option to include full attributes
def format_comprehensive_enrichment_for_prompt(
    enriched_entities: Dict[str, Dict[str, Any]],
    include_full_attributes: bool = False  # ← New parameter
) -> str:
    ...
    
    # Add full attributes section if requested
    if include_full_attributes and data.get('attributes'):
        entity_section.append("  Full Attributes:")
        # Format attributes nicely (limit size for readability)
        attrs = data['attributes']
        important_attrs = {
            k: v for k, v in attrs.items() 
            if k in ['brightness', 'color_temp', 'rgb_color', 'effect_list', 'temperature', 'humidity']
        }
        for key, value in important_attrs.items():
            if isinstance(value, (list, dict)):
                value_str = str(value)[:100] + "..." if len(str(value)) > 100 else str(value)
            else:
                value_str = str(value)
            entity_section.append(f"    {key}: {value_str}")
```

**Benefits:**
- ✅ More context for complex automations
- ✅ Can access any attribute value
- ✅ Better understanding of device capabilities

**Trade-offs:**
- ⚠️ Larger prompts (more tokens)
- ⚠️ May not be needed for all use cases
- ⚠️ Increased cost per OpenAI call

**Implementation Steps:**
1. Add `include_full_attributes` parameter
2. Add full attributes section to formatted output
3. Make it optional (default: False)
4. Test with complex automations

**Files to Modify:**
- `services/ai-automation-service/src/services/comprehensive_entity_enrichment.py` (format_comprehensive_enrichment_for_prompt method)

---

#### **Recommendation 3.2: Include Power Source Information**

**Current State:** Available but not included in prompts  
**Impact:** Low - Useful for battery-aware automations

**What to Change:**
```python
# File: services/ai-automation-service/src/prompt_building/unified_prompt_builder.py
# Location: _build_entity_context_section() method

# Add power source information
if entity.get('power_source'):
    power_source = entity['power_source']
    if power_source == 'battery':
        entity_info += f" [Battery-powered - consider power-saving automations]"
    elif power_source == 'mains':
        entity_info += f" [Mains-powered]"
```

**Benefits:**
- ✅ Can suggest battery-saving automations for battery devices
- ✅ Can suggest more frequent automations for mains-powered devices
- ✅ Better power management suggestions

**Example:**
- Battery device → Suggest "Turn off after 5 minutes" instead of "Always on"
- Mains device → Can suggest "Always on" or frequent automations

**Implementation Steps:**
1. Add power source to entity context section
2. Add power source guidance to prompts
3. Test with battery and mains devices

**Files to Modify:**
- `services/ai-automation-service/src/prompt_building/unified_prompt_builder.py` (_build_entity_context_section method)

---

#### **Recommendation 3.3: Include Software/Hardware Version Information**

**Current State:** Available but not included in prompts  
**Impact:** Low - Useful for version-specific features

**What to Change:**
```python
# File: services/ai-automation-service/src/prompt_building/unified_prompt_builder.py
# Location: _build_entity_context_section() method

# Add version information
version_info = []
if entity.get('sw_version'):
    version_info.append(f"SW: {entity['sw_version']}")
if entity.get('hw_version'):
    version_info.append(f"HW: {entity['hw_version']}")
if version_info:
    entity_info += f" [{' '.join(version_info)}]"
```

**Benefits:**
- ✅ Can suggest version-specific features
- ✅ Better understanding of device capabilities
- ✅ Can avoid suggesting features not available in older versions

**Example:**
- WLED 0.14+ supports new effects
- HomeKit devices have different capabilities by version

**Implementation Steps:**
1. Add version information to entity context
2. Test with different device versions

**Files to Modify:**
- `services/ai-automation-service/src/prompt_building/unified_prompt_builder.py` (_build_entity_context_section method)

---

#### **Recommendation 3.4: Include Last Seen Information**

**Current State:** Available but not included in prompts  
**Impact:** Low - Useful for device availability awareness

**What to Change:**
```python
# File: services/ai-automation-service/src/prompt_building/unified_prompt_builder.py
# Location: _build_entity_context_section() method

# Add last seen information
if entity.get('last_seen'):
    from datetime import datetime
    last_seen = entity['last_seen']
    if isinstance(last_seen, str):
        try:
            last_seen_dt = datetime.fromisoformat(last_seen.replace('Z', '+00:00'))
            now = datetime.now(last_seen_dt.tzinfo)
            hours_ago = (now - last_seen_dt).total_seconds() / 3600
            if hours_ago > 24:
                entity_info += f" [⚠️ Last seen {int(hours_ago/24)} days ago - may be offline]"
            elif hours_ago > 1:
                entity_info += f" [Last seen {int(hours_ago)} hours ago]"
        except:
            pass
```

**Benefits:**
- ✅ Can warn about potentially offline devices
- ✅ Can suggest checking device availability
- ✅ Better reliability awareness

**Implementation Steps:**
1. Add last seen calculation logic
2. Add warnings for old last_seen timestamps
3. Test with devices of varying last_seen times

**Files to Modify:**
- `services/ai-automation-service/src/prompt_building/unified_prompt_builder.py` (_build_entity_context_section method)

---

#### **Recommendation 3.5: Optimize Prompt Size with Tiered Enrichment**

**Current State:** All or nothing enrichment  
**Impact:** Low - Cost optimization

**What to Change:**
```python
# File: services/ai-automation-service/src/services/comprehensive_entity_enrichment.py
# Location: format_comprehensive_enrichment_for_prompt() method

# Add enrichment level parameter
def format_comprehensive_enrichment_for_prompt(
    enriched_entities: Dict[str, Dict[str, Any]],
    enrichment_level: str = "standard"  # "basic" | "standard" | "comprehensive"
) -> str:
    """
    Format enrichment data with different detail levels.
    
    - basic: Essential info only (name, capabilities, health)
    - standard: Basic + manufacturer, model, area (current default)
    - comprehensive: Everything including historical patterns
    """
    
    if enrichment_level == "basic":
        # Include only essential fields
        include_fields = ['friendly_name', 'capabilities', 'health_score', 'entity_id']
    elif enrichment_level == "standard":
        # Current default behavior
        include_fields = None  # Include all standard fields
    elif enrichment_level == "comprehensive":
        # Include everything including historical
        include_fields = None
        include_historical = True
    else:
        include_fields = None
    
    # Format accordingly
    ...
```

**Benefits:**
- ✅ Cost optimization (smaller prompts for simple queries)
- ✅ Flexibility based on query complexity
- ✅ Faster processing for basic queries

**Implementation Steps:**
1. Add enrichment_level parameter
2. Implement tiered formatting logic
3. Determine level based on query complexity
4. Test with different enrichment levels

**Files to Modify:**
- `services/ai-automation-service/src/services/comprehensive_entity_enrichment.py` (format_comprehensive_enrichment_for_prompt method)
- `services/ai-automation-service/src/api/ask_ai_router.py` (determine enrichment level)

---

## 6. Enriched Context Data Availability Matrix

| Data Field | Source | Included in Text Format | Included in JSON Format | Included in Comprehensive | Used in Prompts | Priority |
|------------|--------|------------------------|------------------------|---------------------------|-----------------|----------|
| **Basic Info** |
| entity_id | HA | ✅ | ✅ | ✅ | ✅ | - |
| friendly_name | HA | ✅ | ✅ | ✅ | ✅ | - |
| domain | HA | ✅ | ✅ | ✅ | ✅ | - |
| state | HA | ❌ | ✅ | ✅ | ❌ | 🟡 Medium |
| **Device Info** |
| manufacturer | Device Intel | ✅ | ❌ | ✅ | ✅ | - |
| model | Device Intel | ✅ | ❌ | ✅ | ✅ | - |
| integration | HA | ❌ | ✅ | ✅ | ⚠️ | 🟡 Medium |
| sw_version | Device Intel | ❌ | ❌ | ✅ | ❌ | 🟢 Low |
| hw_version | Device Intel | ❌ | ❌ | ✅ | ❌ | 🟢 Low |
| power_source | Device Intel | ❌ | ❌ | ✅ | ❌ | 🟢 Low |
| **Capabilities** |
| capabilities | Device Intel | ✅ (Formatted) | ✅ (Array) | ✅ (Detailed) | ✅ | - |
| supported_features | HA | ❌ | ⚠️ | ✅ | ⚠️ | 🟡 Medium |
| attributes | HA | ❌ | ✅ (Full) | ⚠️ (Selected) | ⚠️ | 🟢 Low |
| **Location** |
| area_name | Device Intel | ✅ | ❌ | ✅ | ✅ | - |
| area_id | HA | ❌ | ❌ | ✅ | ❌ | - |
| **Health & Status** |
| health_score | Device Intel | ✅ | ❌ | ✅ | ⚠️ | 🔴 High |
| last_seen | Device Intel | ❌ | ❌ | ✅ | ❌ | 🟢 Low |
| **Historical** |
| usage_frequency | Data API | ❌ | ❌ | ⚠️ (Optional) | ❌ | 🔴 High |
| common_states | Data API | ❌ | ❌ | ⚠️ (Optional) | ❌ | 🔴 High |
| typical_usage_times | Data API | ❌ | ❌ | ⚠️ (Optional) | ❌ | 🔴 High |
| **Other** |
| is_group | HA | ❌ | ✅ | ✅ | ✅ | - |
| device_class | HA | ❌ | ❌ | ✅ | ⚠️ | - |

**Legend:**
- ✅ = Included and used
- ⚠️ = Included but underutilized
- ❌ = Not included or not used
- 🔴 High = Should be prioritized
- 🟡 Medium = Worth implementing
- 🟢 Low = Nice to have

---

## 7. Implementation Priority Summary

### 🔴 HIGH PRIORITY (Implement First)

1. **Enable Historical Patterns** (Recommendation 1.1)
   - **Impact:** Better timing-based suggestions
   - **Effort:** Low (one line change)
   - **Risk:** Low (adds timeout handling)
   - **Files:** `ask_ai_router.py`

2. **Enforce Health Score Filtering** (Recommendation 1.2)
   - **Impact:** Prevents unreliable automations
   - **Effort:** Medium (add filtering logic + config)
   - **Risk:** Low (improves quality)
   - **Files:** `ask_ai_router.py`, `config.py`

---

### 🟡 MEDIUM PRIORITY (Implement Next)

3. **Use State Information** (Recommendation 2.1)
   - **Impact:** Context-aware suggestions
   - **Effort:** Low (add to prompt)
   - **Risk:** Low
   - **Files:** `unified_prompt_builder.py`

4. **Leverage Manufacturer/Model** (Recommendation 2.2)
   - **Impact:** Device-specific features
   - **Effort:** Medium (add manufacturer examples)
   - **Risk:** Low
   - **Files:** `unified_prompt_builder.py`

5. **Better Integration-Specific Guidance** (Recommendation 2.3)
   - **Impact:** Better integration support
   - **Effort:** Medium (add integration guidance)
   - **Risk:** Low
   - **Files:** `unified_prompt_builder.py`

---

### 🟢 LOW PRIORITY (Nice to Have)

6. **Include Full Attributes** (Recommendation 3.1)
   - **Impact:** More context, larger prompts
   - **Effort:** Low (add parameter)
   - **Risk:** Medium (cost increase)
   - **Files:** `comprehensive_entity_enrichment.py`

7. **Include Power Source** (Recommendation 3.2)
   - **Impact:** Battery-aware suggestions
   - **Effort:** Low (add to prompt)
   - **Risk:** Low
   - **Files:** `unified_prompt_builder.py`

8. **Include Software/Hardware Version** (Recommendation 3.3)
   - **Impact:** Version-specific features
   - **Effort:** Low (add to prompt)
   - **Risk:** Low
   - **Files:** `unified_prompt_builder.py`

9. **Include Last Seen** (Recommendation 3.4)
   - **Impact:** Device availability awareness
   - **Effort:** Low (add calculation)
   - **Risk:** Low
   - **Files:** `unified_prompt_builder.py`

10. **Tiered Enrichment Levels** (Recommendation 3.5)
    - **Impact:** Cost optimization
    - **Effort:** Medium (add levels)
    - **Risk:** Low
    - **Files:** `comprehensive_entity_enrichment.py`, `ask_ai_router.py`

---

## 8. Estimated Implementation Effort

| Priority | Recommendation | Effort | Impact | Risk |
|----------|----------------|--------|--------|------|
| 🔴 High | Enable Historical Patterns | 1 hour | Medium | Low |
| 🔴 High | Enforce Health Score Filtering | 2-3 hours | High | Low |
| 🟡 Medium | Use State Information | 1 hour | Medium | Low |
| 🟡 Medium | Leverage Manufacturer/Model | 2-3 hours | Medium | Low |
| 🟡 Medium | Integration-Specific Guidance | 2-3 hours | Medium | Low |
| 🟢 Low | Include Full Attributes | 1 hour | Low | Medium |
| 🟢 Low | Include Power Source | 30 min | Low | Low |
| 🟢 Low | Include Software/Hardware Version | 30 min | Low | Low |
| 🟢 Low | Include Last Seen | 1 hour | Low | Low |
| 🟢 Low | Tiered Enrichment Levels | 3-4 hours | Low | Low |

**Total Estimated Effort:**
- High Priority: 3-4 hours
- Medium Priority: 5-7 hours
- Low Priority: 6-8 hours
- **Total: 14-19 hours**

---

## 9. Success Metrics

### How to Measure Improvement

**Before Implementation:**
- Baseline: Track current suggestion quality
- Measure: Automation success rate, user satisfaction, entity utilization

**After Implementation:**

**High Priority:**
- Historical patterns enabled → Measure timing accuracy of suggestions
- Health score filtering → Measure reduction in failed automations

**Medium Priority:**
- State information → Measure context-aware suggestion relevance
- Manufacturer/model → Measure device-specific feature usage

**Low Priority:**
- Full attributes → Measure cost increase vs. quality improvement
- Power source → Measure battery-aware suggestion adoption

---

## 10. Questions for Design Review

1. **Historical Patterns:**
   - Should we enable `include_historical=True` by default?
   - What's the performance impact?
   - How valuable is historical data for suggestions?

2. **Health Score Enforcement:**
   - Should we filter out unhealthy devices or just warn?
   - What's the threshold? (currently 50, but prompt says < 50)
   - Should it be configurable?

3. **State Awareness:**
   - Should suggestions be state-aware?
   - Should we suggest "turn off" if device is currently "on"?

4. **Prompt Size:**
   - Are we including too much or too little data?
   - What's the token cost of comprehensive enrichment?
   - Should we have different enrichment levels (basic, standard, comprehensive)?

5. **Model Selection:**
   - Are we using the right models for each task?
   - Should we consider GPT-4o for critical YAML generation?
   - Are the local models (NER, embeddings) sufficient?

6. **Cost Optimization:**
   - Should we use tiered enrichment (basic/standard/comprehensive)?
   - Should we cache enrichment data more aggressively?
   - Should we reduce prompt size for simple queries?

---

## 11. Code References

### ML Models:
- **Multi-Model Extractor:** `services/ai-automation-service/src/entity_extraction/multi_model_extractor.py`
- **OpenAI Client:** `services/ai-automation-service/src/llm/openai_client.py`
- **Embedding Model:** `services/ai-automation-service/src/nlevel_synergy/embedding_model.py`
- **Pattern Extractor:** `services/ai-automation-service/src/entity_extraction/pattern_extractor.py`

### Enriched Context:
- **Comprehensive Enrichment:** `services/ai-automation-service/src/services/comprehensive_entity_enrichment.py`
- **Entity Context Builder:** `services/ai-automation-service/src/prompt_building/entity_context_builder.py`
- **Prompt Builder:** `services/ai-automation-service/src/prompt_building/unified_prompt_builder.py`
- **Entity Attribute Service:** `services/ai-automation-service/src/services/entity_attribute_service.py`

### Related Documentation:
- **Multi-Model Guide:** `services/ai-automation-service/MULTI_MODEL_IMPLEMENTATION_GUIDE.md`
- **Call Tree:** `docs/architecture/ai-automation-suggestion-call-tree.md`
- **Service Review:** `implementation/analysis/AI_AUTOMATION_SERVICE_REVIEW.md`

---

**Next Steps:**
1. Review and prioritize recommendations
2. Implement High Priority items first
3. Test improvements with real queries
4. Measure impact on suggestion quality
5. Iterate based on results

