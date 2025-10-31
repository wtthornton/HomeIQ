# Home Assistant Blueprint Engine Implementation Plan

**Date:** 2025-01-XX  
**Status:** Planning  
**Goal:** Implement a blueprint engine in HomeIQ to enhance YAML generation from customer suggestions

 prospects

---

## Executive Summary

Home Assistant Blueprints are reusable automation templates that define automation logic with configurable inputs. We can implement a blueprint engine in HomeIQ to:
1. **Parse and store** blueprint templates from community sources
2. **Match** customer suggestions to appropriate blueprints
3. **Fill** blueprint inputs with user's actual devices/entities
4. **Generate** valid HA YAML without loading into HA
5. **Enhance** our AI-driven YAML generation with blueprint knowledge

This creates a **hybrid approach**: AI suggestions + Blueprint templates = Better YAML

---

## Understanding Home Assistant Blueprints

### Blueprint Structure

```yaml
blueprint:
  name: Motion-Activated Light
  description: Turn on lights when motion detected
  domain: automation
  input:
    motion_sensor:
      name: Motion Sensor
      selector:
        entity:
          domain: binary_sensor
          device_class: motion
    target_light:
      name: Light to Control
      selector:
        entity:
          domain: light
    brightness:
      name: Brightness
      selector:
        number:
          min: 1
          max: 100
          unit_of_measurement: "%"

# Template variables use !input syntax
trigger:
  - platform: state
    entity_id: !input motion_sensor
    to: 'on'

action:
  - service: light.turn_on
    target:
      entity_id: !input target_light
    data:
      brightness_pct: !input brightness
```

### Key Blueprint Components

1. **Metadata** (`blueprint.name`, `blueprint.description`, `blueprint.domain`)
2. **Input Definitions** (`blueprint.input.*`) - Define what user must provide
3. **Input Selectors** - UI widgets for selecting entities/devices/values
4. **Template Variables** (`!input variable_name`) - Placeholders for user inputs
5. **Automation Logic** - Standard HA automation YAML with template variables

### Input Selector Types

- `selector.entity` - Select entity by domain/device_class
- `selector.device` - Select device
- `selector.number` - Numeric input (brightness, timeout, etc.)
- `selector.boolean` - True/false checkbox
- `selector.text` - Text input
- `selector.select` - Dropdown choices
- `selector.time` - Time picker
- `selector.target` - Target entity/area/device

---

## Implementation Strategy

### Phase 1: Blueprint Storage & Parsing

**Goal:** Parse blueprints from community sources and store in database

#### 1.1 Enhance Automation Miner

**Current State:** `services/automation-miner` already crawls blueprints from Discourse

**Enhancements Needed:**
- Extract blueprint `input` definitions
- Parse input selectors (entity selectors, number ranges, etc.)
- Store blueprint metadata separately from automation metadata
- Create blueprint template storage (with `!input` variables intact)

**Database Schema Addition:**

```sql
CREATE TABLE blueprint_templates (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  domain TEXT DEFAULT 'automation',
  blueprint_yaml TEXT NOT NULL,  -- Full blueprint YAML
  inputs_definition JSON NOT NULL,  -- Parsed input structure
  source_url TEXT,
  source_id TEXT,
  quality_score REAL,
  use_cases TEXT,  -- JSON array: ["motion_lighting", "security"]
  device_types TEXT,  -- JSON array: ["binary_sensor", "light"]
  integrations TEXT,  -- JSON array: ["zha", "hue"]
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);

CREATE TABLE blueprint_exists (
  blueprint_id INTEGER REFERENCES blueprint_templates(id),
  user_device_type TEXT,  -- e.g., "binary_sensor.motion", "light"
  user_integration TEXT,  -- e.g., "zha"
  fit_score REAL  -- How well this blueprint fits user's setup
);
```

#### 1.2 Blueprint Parser Service

**New Service:** `services/ai-automation-service/src/blueprints/blueprint_parser.py`

```python
class BlueprintParser:
    """Parse Home Assistant blueprint structure"""
    
    def parse_blueprint(self, yaml_str: str) -> BlueprintTemplate:
        """
        Parse blueprint YAML and extract:
        - Input definitions with selectors
        - Template variable references (!input)
        - Required vs optional inputs
        - Input validation rules
        """
        
    def extract_inputs(self, blueprint: Dict) -> List[InputDefinition]:
        """
        Extract input definitions:
        - Input name and description
        - Selector type and constraints
        - Default values
        - Required/optional flag
        """
        
    def validate_blueprint(self, blueprint: Dict) -> Tuple[bool, List[str]]:
        """Validate blueprint structure and syntax"""
```

### Phase 2: Blueprint Matching Engine

**Goal:** Match customer suggestions to appropriate blueprints

#### 2.1 Blueprint Matcher Service

**New Service:** `services/ai-automation-service/src/blueprints/blueprint_matcher.py`

```python
class BlueprintMatcher:
    """Match user suggestions to available blueprints"""
    
    async def find_matching_blueprints(
        self,
        suggestion: Dict[str, Any],
        user_devices: List[Dict[str, Any]],
        top_k: int = 5
    ) -> List[BlueprintMatch]:
        """
        Match suggestion to blueprints based on:
        1. Device type compatibility
        2. Use case alignment
        3. Integration compatibility
        4. Input requirements vs available devices
        """
        
    def calculate_fit_score(
        self,
        blueprint: BlueprintTemplate,
        suggestion: Dict,
        user_devices: List[Dict]
    ) -> float:
        """
        Calculate how well blueprint fits:
        - Device types match (e.g., blueprint needs "light" → user has "light")
        - Required inputs can be filled (user has compatible entities)
        - Use case matches (motion_lighting → motion_lighting blueprint)
        """
```

**Matching Algorithm:**

```
For each blueprint:
  1. Extract required device types from blueprint.input
  2. Check if user has compatible devices
  3. Extract use case keywords from suggestion
  4. Match against blueprint use_cases metadata
  5. Calculate fit_score:
     - device_match_score * 0.6
     + use_case_match_score * 0.3
     + integration_match_score * 0.1
  
Sort by fit_score, return top_k
```

#### 2.2 Integration with Suggestion Pipeline

**Enhance:** `services/ai-automation-service/src/prompt_building/unified_prompt_builder.py`

Add blueprint context to suggestions:

```python
async def build_query_prompt(
    self,
    query: str,
    entities: List[Dict],
    blueprint_matches: Optional[List[BlueprintMatch]] = None  # NEW
) -> Dict[str, str]:
    """
    Add blueprint context to prompts:
    - Show available blueprints that match the query
    - Suggest using blueprint templates for better YAML
    - Provide blueprint-based examples in prompts
    """
```

### Phase 3: Blueprint Input Filling Engine

**Goal:** Fill blueprint templates with user's actual devices/entities

#### 3.1 Input Filler Service

**New Service:** `services/ai-automation-service/src/blueprints/input_filler.py`

```python
class BlueprintInputFiller:
    """Fill blueprint inputs with user's devices"""
    
    async def fill_blueprint_inputs(
        self,
        blueprint: BlueprintTemplate,
        suggestion: Dict[str, Any],
        user_devices: List[Dict[str, Any]],
        entity_mapping: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Fill blueprint inputs:
        
        1. For entity selectors:
           - Match suggestion devices to blueprint input requirements
           - Use entity_mapping to get exact entity_ids
           - Validate device class compatibility
        
        2. For number selectors:
           - Extract from suggestion text (e.g., "50% brightness")
           - Use defaults if not specified
        
        3. For boolean selectors:
           - Extract from suggestion (e.g., "only at night" → True)
           - Use defaults if not specified
        
        4. For text selectors:
           - Extract from suggestion (e.g., notification message)
        """
        
    def match_entity_to_input(
        self,
        input_selector: Dict[str, Any],
        user_devices: List[Dict[str, Any]]
    ) -> Optional[str]:
        """
        Match user device to blueprint input requirement:
        - Check domain match (light → light)
        - Check device_class match (motion → motion斥)
        - Check integration compatibility
        - Return best matching entity_id
        """
```

#### 3.2 Template Variable Substitution

```python
class BlueprintRenderer:
    """Render blueprint YAML with filled inputs"""
    
    def render_blueprint(
        self,
        blueprint_yaml: str,
        inputs: Dict[str, Any]
    ) -> str:
        """
        Replace !input variable_name with actual values:
        
        !input motion_sensor → binary_sensor.front_door_motion
        !input target_light → light.living_room
        !input brightness → 75
        
        Returns: Valid HA automation YAML
        """
```

### Phase 4: Hybrid AI + Blueprint YAML Generation

**Goal:** Combine AI suggestions with blueprint templates for better YAML

#### 4.1 Enhanced YAML Generation Flow

```
Customer Suggestion
    ↓
AI Suggestion Generation (Phase 1)
    ↓
Blueprint Matching (NEW)
    ├─→ Found matching blueprint?
    │   ├─ Yes → Fill blueprint inputs
    │   │   ↓
    │   └─→ Generate YAML from blueprint (FAST, RELIABLE)
    │
    └─→ No matching blueprint?
        ↓
        AI YAML Generation (Phase 2 - Fallback)
        └─→ Generate YAML from scratch (SLOWER, BUT CREATIVE)
```

#### 4.2 Blueprint-Enhanced Prompt Builder

Add blueprint examples to AI prompts:

```python
async def build_yaml_generation_prompt(
    self,
    suggestion: Dict[str, Any],
    entities: List[Dict[str, Any]],
    matching_blueprints: Optional[List[BlueprintMatch]] = None
) -> Dict[str, str]:
    """
    Include blueprint templates as examples:
    
    PROMPT ENHANCEMENT:
    "Similar blueprints that match this suggestion:
     - Motion-Activated Light: Uses motion sensor + light
     - Time-Based Lighting: Uses time trigger + light
    
    Use these patterns as inspiration, or reference
    the exact structure if it closely matches."
    """
```

### Phase 5: Blueprint Library & Community Integration

**Goal:** Build a curated blueprint library in HomeIQ

#### 5.1 Blueprint Sources

1. **Automation Miner** (Existing)
   - Discourse Blueprints Exchange (category 53)
   - GitHub blueprint repositories
   
2. **Manual Curation**
   - Home Assistant Official Blueprints
   - Top-rated community blueprints
   - Custom HomeIQ-specific blueprints

#### 5.2 Blueprint Categories

Organize blueprints by:
- **Use Case:** Motion lighting, presence simulation, energy saving, security
- **Device Type:** Lights, sensors, climate, locks, media players
- **Complexity:** Simple (1-3 inputs), Medium (4-6 inputs), Complex (7+ inputs)
- **Integration:** ZHA, Z-Wave, MQTT, Hue, etc.

---

## Enhanced Flow: Customer Suggestion → YAML

### Current Flow (AI-Only)

```
Customer: "Flash lights when door opens"
    ↓
1. AI Suggestion Generation
   - Generates 3-5 creative suggestions
   - Uses device capabilities
   - Provides descriptions
    ↓
2. User Selects Suggestion
    ↓
3. AI YAML Generation
   - Prompts GPT-4o-mini
   - Generates YAML from scratch
   - Sometimes makes mistakes
    ↓
4. YAML Validation
   - Syntax check
   - Entity validation
    ↓
5. User Reviews & Deploys
```

### Enhanced Flow (AI + Blueprints)

```
Customer: "Flash lights when door opens"
    ↓
1. AI Suggestion Generation
   - Generates 3-5 creative suggestions
   - INCLUDES blueprint hints:
     * "💡 Similar to: Motion-Activated Light blueprint"
     * "💡 Could use: Door Alert blueprint pattern"
    ↓
2. User Selects Suggestion
    ↓
3. Blueprint Matching (NEW)
   - Searches blueprint library
   - Finds: "Door-Triggered Notification" blueprint
   - Fit score: 0.92 (excellent match)
    ↓
4. Blueprint Input Filling (NEW)
   - motion_sensor → binary_sensor.front_door
   - target_light → light.living_room
   - flash_duration → 2 (extracted from "flash")
    ↓
5. Blueprint Rendering (NEW)
   - Replaces !input variables
   - Generates valid YAML instantly
   - ✅ Reliable, tested pattern
    ↓
6. Fallback to AI (if no blueprint match)
   - AI YAML generation (current method)
    ↓
7. YAML Validation
   - Syntax check (usually passes for blueprints)
   - Entity validation
    ↓
8. User Reviews & Deploys
```

---

## Implementation Plan

### Sprint 1: Blueprint Parser & Storage (Week 1)

**Tasks:**
1. ✅ Enhance `automation-miner` parser to extract blueprint inputs
2. Create `blueprint_parser.py` service
3. Add blueprint storage to database
4. Store blueprints from automation-miner output

**Deliverables:**
- Blueprint parser that extracts input definitions
- Database schema for blueprint templates
- 50+ blueprints loaded from Discourse

### Sprint 2: Blueprint Matching Engine (Week 2)

**Tasks:**
1. Implement `blueprint_matcher.py`
2. Create matching algorithm (device type, use case, integration)
3. Integrate with suggestion pipeline
4. Add blueprint context to AI prompts

**Deliverables:**
- Blueprint matching service
- Integration with `UnifiedPromptBuilder`
- Blueprint hints in AI suggestions

### Sprint 3: Input Filling & Rendering (Week 3)

**Tasks:**
1. Implement `input_filler.py`
2. Create entity-to-input matching logic
3. Implement `blueprint_renderer.py` for template substitution
4. Test with real user devices

**Deliverables:**
- Input filling service
- Blueprint rendering engine
- Working YAML generation from blueprints

### Sprint 4: Hybrid Generation & Testing (Week 4)

**Tasks:**
1. Integrate blueprint generation into main YAML flow
2. Add fallback to AI when no blueprint matches
3. Comprehensive testing with real suggestions
4. Performance optimization

**Deliverables:**
- Complete hybrid YAML generation
- Fallback mechanisms
- Performance benchmarks
- Documentation

---

## Benefits of Blueprint Approach

### For Users

1. **Reliability:** Blueprints are community-tested patterns
2. **Speed:** Instant YAML generation (no AI latency)
3. **Consistency:** Same pattern always produces valid YAML
4. **Learning:** Users see proven automation patterns

### For System

1. **Lower Costs:** Fewer AI API calls when blueprints match
2. **Better Quality:** Blueprints are pre-validated patterns
3. **Scalability:** Blueprint matching is fast (database query vs AI call)
4. **Hybrid Approach:** AI fills gaps where blueprints don't exist

### Hybrid Strategy

- **Blueprints** for common patterns (80% of requests)
- **AI Generation** for creative/unique requests (20% of requests)
- **Best of both worlds:** Speed + Reliability + Creativity

---

## GitHub Projects & Resources

### Existing Projects

1. **Home Assistant Official Blueprints**
   - Repository: Community-maintained blueprint exchange
   - Location: Discourse category 53
   - Use: Source for blueprint templates

2. proto blueprint-parser
   - Generic YAML template engine
   - Could adapt for HA blueprints
   - Needs: Blueprint-specific logic

3. **Custom Implementation** (Recommended)
   - Build blueprint engine specific to HA2025-04 structure
   - Leverage existing automation-miner infrastructure
   - Integrate with current AI automation service

### Useful Resources

- **HA Blueprint Schema Docs:** https://www.home-assistant.io/docs/blueprint/schema/
- **Blueprint Tutorial:** https://www.home-assistant.io/docs/blueprint/tutorial/
- **Blueprint Exchange:** https://community.home-assistant.io/c/blueprints-exchange/53
- **Blueprint Hub:** https://hablueprints.directory/

---

## Technical Considerations

### Blueprint Input Matching Challenges

**Problem:** Matching user's natural language to blueprint inputs

**Solution:** AI-assisted matching
```
User: "Flash living room lights when front door opens"
    ↓
AI extracts: motion_sensor="front door", target_light="living room"
    ↓
Blueprint matcher: Finds blueprint needing "binary_sensor" + "light"
    ↓
Input filler: Maps "front door" → binary_sensor.front_door
              Maps "living room" → light.living_room
```

### Handling Blueprint Variants

**Problem:** Multiple blueprints for same use case (different approaches)

**Solution:** Show all variants, let AI choose best fit
```
Motion Lighting Blueprints:
1. Simple Motion → Light (1 input: brightness)
2. Motion + Time Conditions (3 inputs: brightness, after_time, before_time)
3. Motion + Illuminance (4 inputs: brightness, max_lux, timeout)

AI selects: #2 if user mentions "night" or "evening"
```

### Validation & Safety

**Problem:** Blueprint inputs might not match user's setup exactly

**Solution:** Multi-layer validation
1. **Input Validation:** Check entity exists, domain matches
2. **Capability Validation:** Check device supports required features
3. **Health Score:** Prefer devices with health_score > 70
4. **Fallback:** If validation fails, fall back to AI generation

---

## Next Steps

### Immediate Actions

1. **Review & Approve** this implementation plan
2. **Enhance automation-miner** to extract blueprint inputs
3. **Create database schema** for blueprint templates
4. **Prototype** blueprint parser with 5-10 sample blueprints

### Research Tasks

1. **Analyze** blueprints from automation-miner output
2. **Identify** most common blueprint patterns
3. **Test** blueprint parsing on real Discourse blueprints
4. **Validate** input matching accuracy with sample devices

### Questions to Resolve

1. Should we store full blueprint YAML or just metadata?
2. How to handle blueprint updates from community?
3. Should we create custom HomeIQ blueprints?
4. How to handle blueprint licensing/attribution?

---

## Success Metrics

### Quality Metrics

- **Blueprint Match Rate:** % of suggestions with matching blueprints (>60% target)
- **YAML Validity:** % of generated YAML that passes validation (>95% target)
- **User Satisfaction:** User ratings of generated automations (>4.0/5.0 target)

### Performance Metrics

- **Generation Speed:** Average time to generate YAML
  - Blueprint: <100ms (target)
  - AI: 500-1000ms (current)
- **Cost Reduction:** % reduction in AI API calls (>40% target)

### Coverage Metrics

- **Blueprint Library Size:** Number of unique blueprints (>100 target)
- **Use Case Coverage:** % of common use cases with blueprints (>80% target)

---

## Conclusion

Implementing a blueprint engine in HomeIQ will significantly enhance our YAML generation capabilities:

1. **Faster** generation for common patterns
2. **More reliable** YAML (community-tested blueprints)
3. **Lower costs** (fewer AI API calls)
4. **Better user experience** (instant results for common requests)

The hybrid approach (Blueprints + AI) provides the best of both worlds:
- **Blueprints** for speed and reliability
- **AI** for creativity and unique requests

This positions HomeIQ as a powerful tool for HA automation creation, leveraging both community wisdom (blueprints) and AI innovation.

---

**Status:** Ready for Sprint Planning  
**Priority:** High  
**Estimated Implementation:** 4 weeks (1 sprint per phase)

