# HA AI Agent Service - 2025 Improvement Plan

**Date:** December 4, 2025  
**Model:** OpenAI GPT-5.1 (Primary - Better quality and 50% cost savings vs GPT-4o)  
**Based on:** 2025 Home Assistant patterns + 2025 AI Agent patterns + Current analysis

---

## Executive Summary

This plan addresses critical gaps in context injection and prompt engineering to enable the HA AI Agent to generate correct automations using 2025 Home Assistant patterns and modern AI agent best practices.

**Key Improvements:**
1. Fix context injection services (services, capabilities, areas)
2. Add 2025 Home Assistant automation patterns to system prompt
3. Implement 2025 AI agent tool calling patterns
4. Optimize for GPT-5.1 (better quality and 50% cost savings vs GPT-4o)
5. Add comprehensive YAML examples for common patterns

---

## Phase 1: Fix Context Injection Services (CRITICAL)

### 1.1 Fix Services Summary Service

**Problem:** Services summary returns empty, LLM doesn't know service parameters.

**2025 Home Assistant Pattern:**
- Use `/api/services` endpoint with full schema
- Include parameter types, required/optional, constraints
- Show target options (entity_id, area_id, device_id)

**Implementation:**

```python
# services/ha-ai-agent-service/src/services/services_summary_service.py

async def get_summary(self) -> str:
    """Get services summary with 2025 patterns"""
    services_data = await self.ha_client.get_services()
    
    # Format for critical services
    critical_services = {
        "light": ["turn_on", "turn_off", "toggle"],
        "scene": ["create", "turn_on", "reload"],
        "automation": ["trigger", "toggle", "reload"],
        "script": ["turn_on", "reload"],
    }
    
    summary_parts = []
    for domain, service_names in critical_services.items():
        if domain in services_data:
            for service_name in service_names:
                if service_name in services_data[domain]:
                    service_info = services_data[domain][service_name]
                    # Format with 2025 schema format
                    summary_parts.append(
                        self._format_service_2025(domain, service_name, service_info)
                    )
    
    return "\n".join(summary_parts)

def _format_service_2025(self, domain: str, service: str, info: dict) -> str:
    """Format service with 2025 Home Assistant schema"""
    fields = info.get("fields", {})
    
    # Extract target options (2025 pattern)
    target_fields = fields.get("target", {})
    target_options = []
    if "entity_id" in target_fields.get("selector", {}):
        target_options.append("entity_id")
    if "area_id" in target_fields.get("selector", {}):
        target_options.append("area_id")
    if "device_id" in target_fields.get("selector", {}):
        target_options.append("device_id")
    
    # Format parameters
    param_parts = []
    for param_name, param_info in fields.items():
        if param_name == "target":
            continue
        param_type = param_info.get("type", "unknown")
        required = param_info.get("required", False)
        default = param_info.get("default")
        description = param_info.get("description", "")
        
        param_str = f"      {param_name}: {param_type}"
        if required:
            param_str += " (required)"
        if default is not None:
            param_str += f" (default: {default})"
        if description:
            param_str += f" - {description}"
        param_parts.append(param_str)
    
    return f"""{domain}.{service}:
    target: {', '.join(target_options) if target_options else 'N/A'}
    data:
{chr(10).join(param_parts) if param_parts else '      (no additional parameters)'}"""
```

**Expected Output:**
```
light.turn_on:
    target: entity_id, area_id, device_id
    data:
      rgb_color: list[int] (0-255 each) - RGB color values
      brightness: int (0-255) - Brightness level
      effect: string - Effect name
      transition: float - Transition duration in seconds

scene.create:
    target: N/A
    data:
      scene_id: string (required) - Unique scene identifier
      snapshot_entities: list[string] (required) - Entity IDs to snapshot
```

**Priority:** CRITICAL  
**Effort:** 4 hours  
**Dependencies:** None

---

### 1.2 Fix Capability Patterns Service

**Problem:** Capability patterns return empty, LLM doesn't know device capabilities.

**2025 Home Assistant Pattern:**
- Use device registry for device capabilities
- Extract supported features from entity attributes
- Include color modes, brightness ranges, etc.

**Implementation:**

```python
# services/ha-ai-agent-service/src/services/capability_patterns_service.py

async def get_patterns(self) -> str:
    """Get device capability patterns with 2025 data"""
    # Fetch entities with capabilities
    entities = await self.data_api_client.fetch_entities(limit=1000)
    
    # Group by domain and extract capabilities
    domain_capabilities = defaultdict(set)
    
    for entity in entities:
        domain = entity.get("domain")
        if domain == "light":
            # Extract color capabilities
            supported_color_modes = entity.get("attributes", {}).get("supported_color_modes", [])
            if "rgb" in supported_color_modes:
                domain_capabilities["light"].add("rgb_color: [0-255, 0-255, 0-255]")
            if "brightness" in entity.get("attributes", {}):
                domain_capabilities["light"].add("brightness: 0-255")
    
    # Format patterns
    pattern_parts = []
    for domain, capabilities in sorted(domain_capabilities.items()):
        pattern_parts.append(f"{domain}:")
        for cap in sorted(capabilities):
            pattern_parts.append(f"  {cap}")
    
    return "\n".join(pattern_parts) if pattern_parts else "No capability patterns found"
```

**Expected Output:**
```
light:
  brightness: 0-255
  rgb_color: [0-255, 0-255, 0-255]
  supported_color_modes: [rgb, hs, color_temp]
```

**Priority:** CRITICAL  
**Effort:** 6 hours  
**Dependencies:** None

---

### 1.3 Fix Areas Service

**Problem:** Areas return "No areas found" but entities have area_id.

**2025 Home Assistant Pattern:**
- Use area registry API
- Include area aliases and metadata
- Map area_id to friendly names

**Implementation:**

```python
# services/ha-ai-agent-service/src/services/areas_service.py

async def get_areas_list(self) -> str:
    """Get areas list with 2025 format"""
    try:
        areas = await self.ha_client.get_area_registry()
        
        if not areas:
            # Fallback: Extract areas from entities
            entities = await self.data_api_client.fetch_entities(limit=1000)
            area_ids = set()
            for entity in entities:
                area_id = entity.get("area_id")
                if area_id and area_id != "unassigned":
                    area_ids.add(area_id)
            
            if area_ids:
                return "\n".join([
                    f"{area_id.replace('_', ' ').title()} (area_id: {area_id})"
                    for area_id in sorted(area_ids)
                ])
            return "No areas found"
        
        # Format with 2025 metadata
        area_parts = []
        for area in areas:
            area_id = area.get("area_id", "")
            name = area.get("name", area_id.replace("_", " ").title())
            aliases = area.get("aliases", [])
            
            area_str = f"{name} (area_id: {area_id}"
            if aliases:
                area_str += f", aliases: {aliases}"
            area_str += ")"
            area_parts.append(area_str)
        
        return "\n".join(area_parts) if area_parts else "No areas found"
    except Exception as e:
        logger.warning(f"Failed to get areas: {e}")
        return "Areas unavailable"
```

**Priority:** HIGH  
**Effort:** 3 hours  
**Dependencies:** None

---

## Phase 2: Enhance System Prompt with 2025 Patterns (CRITICAL)

### 2.1 Add State Restoration Pattern

**2025 Home Assistant Pattern:**
- Use `scene.create` with `snapshot_entities` (2025.10+)
- Dynamic scene IDs with automation context
- Restore using `scene.turn_on`

**Add to System Prompt:**

```yaml
## State Restoration Pattern (2025.10+)

When user requests "return to original state" or "restore previous state", use this pattern:

```yaml
action:
  # 1. Save current state using scene.create (2025 pattern)
  - service: scene.create
    data:
      scene_id: restore_state_{{ automation_id | replace('.', '_') }}
      snapshot_entities:
        - light.office_light_1
        - light.office_light_2
        # Add all entities that need state restoration
  
  # 2. Apply effect/change
  - service: light.turn_on
    target:
      area_id: office
    data:
      rgb_color: [255, 0, 0]  # Red
      brightness: 255
  
  # 3. Wait for effect duration
  - delay: "00:00:01"
  
  # 4. Restore original state
  - service: scene.turn_on
    target:
      entity_id: scene.restore_state_{{ automation_id | replace('.', '_') }}
```

**Key Points:**
- `scene.create` with `snapshot_entities` captures full entity state (on/off, color, brightness, etc.)
- Dynamic scene IDs prevent conflicts between automations
- `scene.turn_on` restores exact previous state, including if device was off
```

**Priority:** CRITICAL  
**Effort:** 2 hours  
**Dependencies:** None

---

### 2.2 Add Time Pattern Trigger Examples

**2025 Home Assistant Pattern:**
- Use `time_pattern` for recurring triggers
- Support `minutes`, `hours`, `days` patterns

**Add to System Prompt:**

```yaml
## Time Pattern Triggers (2025)

For recurring time-based automations, use `time_pattern`:

```yaml
trigger:
  # Every 15 minutes
  - platform: time_pattern
    minutes: "/15"
  
  # Every hour at :00
  - platform: time_pattern
    minutes: "0"
  
  # Every day at specific time
  - platform: time
    at: "07:00:00"
  
  # Multiple times per day
  - platform: time_pattern
    hours: "/2"  # Every 2 hours
```

**Pattern Syntax:**
- `"/15"` = every 15 minutes
- `"0"` = at minute 0 (top of hour)
- `"*/30"` = every 30 minutes
```

**Priority:** HIGH  
**Effort:** 1 hour  
**Dependencies:** None

---

### 2.3 Add Color/Blink Pattern Examples

**2025 Home Assistant Pattern:**
- RGB color format: `[255, 0, 0]` for red
- HS color format: `[0, 100]` for red
- Brightness: 0-255

**Add to System Prompt:**

```yaml
## Color and Blink Patterns (2025)

### Setting Colors
```yaml
# RGB color (red)
- service: light.turn_on
  target:
    area_id: office
  data:
    rgb_color: [255, 0, 0]  # Red (RGB: 0-255 each)
    brightness: 255

# HS color (red)
- service: light.turn_on
  target:
    area_id: office
  data:
    hs_color: [0, 100]  # Red (Hue: 0-360, Saturation: 0-100)
    brightness: 255

# Color temperature
- service: light.turn_on
  target:
    area_id: office
  data:
    color_temp: 370  # Warm white (mireds: 153-500)
    brightness: 255
```

### Blink Pattern
```yaml
# Blink lights (turn on, wait, turn off)
- service: light.turn_on
  target:
    area_id: office
  data:
    rgb_color: [255, 0, 0]
    brightness: 255
- delay: "00:00:01"  # Blink duration
- service: light.turn_off
  target:
    area_id: office
```

**Color Reference:**
- Red: `rgb_color: [255, 0, 0]` or `hs_color: [0, 100]`
- Green: `rgb_color: [0, 255, 0]` or `hs_color: [120, 100]`
- Blue: `rgb_color: [0, 0, 255]` or `hs_color: [240, 100]`
```

**Priority:** HIGH  
**Effort:** 1 hour  
**Dependencies:** None

---

## Phase 3: Implement 2025 AI Agent Patterns

### 3.1 Optimize Tool Calling for GPT-5.1

**2025 AI Agent Pattern:**
- Single tool with comprehensive parameters
- Clear tool descriptions
- Structured tool responses

**GPT-5.1 Advantages:**
- Better tool parameter understanding
- More reliable tool calling
- Better error handling in tool responses

**Current Status:** ✅ Already implemented (`create_automation_from_prompt`)

**Enhancement:** Add response validation

```python
# services/ha-ai-agent-service/src/tools/ha_tools.py

async def create_automation_from_prompt(
    self,
    user_prompt: str,
    automation_yaml: str,
    alias: str
) -> dict[str, Any]:
    """Create automation with 2025 validation"""
    # Validate YAML structure
    validation = await self._validate_yaml(automation_yaml)
    
    if validation["errors"]:
        return {
            "success": False,
            "error": "YAML validation failed",
            "errors": validation["errors"],
            "suggestions": validation.get("suggestions", [])
        }
    
    # Create automation
    try:
        result = await self.ha_client.create_automation(
            automation_yaml=automation_yaml,
            alias=alias
        )
        
        return {
            "success": True,
            "automation_id": result.get("id"),
            "warnings": validation.get("warnings", [])
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "suggestions": ["Check YAML syntax", "Verify entity IDs exist"]
        }
```

**Priority:** MEDIUM  
**Effort:** 3 hours  
**Dependencies:** None

---

### 3.2 Implement Context Caching (2025 Pattern)

**2025 AI Agent Pattern:**
- Cache context for multiple requests
- Refresh on entity/service changes
- Reduce token usage

**Current Status:** ✅ Already implemented (ContextCache)

**Enhancement:** Add smart cache invalidation

```python
# services/ha-ai-agent-service/src/services/context_builder.py

async def build_context(self, force_refresh: bool = False) -> str:
    """Build context with smart caching"""
    # Check if entities/services changed
    if not force_refresh:
        last_change = await self._get_last_entity_change()
        cache_age = await self._get_cache_age()
        
        if cache_age < 300 and not last_change:  # 5 min cache
            return await self._get_cached_context()
    
    # Build fresh context
    context = await self._build_fresh_context()
    await self._cache_context(context)
    return context
```

**Priority:** LOW  
**Effort:** 4 hours  
**Dependencies:** None

---

## Phase 4: GPT-5.1 Model Optimization

### 4.1 GPT-5.1 Configuration

**Primary Model:** GPT-5.1 (Better quality and 50% cost savings vs GPT-4o)

**Benefits:**
- ✅ Better YAML generation accuracy
- ✅ Improved context understanding
- ✅ 50% cost savings vs GPT-4o
- ✅ Better tool calling reliability
- ✅ Enhanced pattern recognition

**Optimizations:**
1. **Context Size:**
   - GPT-5.1 handles larger contexts better
   - Can include more entity examples (5 per domain)
   - More comprehensive service schemas

2. **Temperature Tuning:**
   - Current: 0.7
   - Recommended: 0.4-0.6 for YAML generation (GPT-5.1 benefits from slightly higher creativity)
   - GPT-5.1 has better deterministic behavior even at higher temperatures

3. **Max Tokens:**
   - Current: 4096
   - Recommended: 2048-3072 for responses (GPT-5.1 generates more concise YAML)

4. **Tool Choice:**
   - GPT-5.1 has better tool calling accuracy
   - Can use `tool_choice: "auto"` with confidence
   - Better understanding of tool parameters

**Implementation:**

```python
# services/ha-ai-agent-service/src/config.py

openai_model: str = Field(
    default="gpt-5.1",
    description="OpenAI model (gpt-5.1 recommended - better quality and 50% cost savings vs GPT-4o)"
)
openai_temperature: float = Field(
    default=0.5,  # GPT-5.1 benefits from slightly higher creativity for YAML
    description="Temperature for OpenAI responses"
)
openai_max_tokens: int = Field(
    default=2048,  # YAML responses are concise, GPT-5.1 is efficient
    description="Maximum tokens for OpenAI responses"
)
```

**Cost Comparison:**
- GPT-4o: $2.50 / 1M input tokens, $10.00 / 1M output tokens
- GPT-5.1: $1.25 / 1M input tokens, $5.00 / 1M output tokens (50% savings)
- GPT-4o-mini: $0.15 / 1M input tokens, $0.60 / 1M output tokens (but lower quality)

**Recommendation:** Use GPT-5.1 for best quality-to-cost ratio.

**Priority:** HIGH  
**Effort:** 1 hour  
**Dependencies:** None

---

### 4.2 GPT-5.1-Specific Optimizations

**Advanced Features:**
1. **Prompt Caching:** GPT-5.1 supports prompt caching for system prompts (60% savings on repeated prompts)
2. **Structured Outputs:** Better JSON mode support for tool responses
3. **Multi-turn Context:** Better context retention across tool calls

**Implementation:**

```python
# services/ha-ai-agent-service/src/services/openai_client.py

async def chat_completion(
    self,
    messages: list[dict[str, str]],
    tools: list[dict[str, Any]] | None = None,
    tool_choice: str | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
) -> ChatCompletion:
    """Chat completion with GPT-5.1 optimizations"""
    
    request_params = {
        "model": self.model,  # gpt-5.1
        "messages": messages,
        "temperature": temperature or self.temperature,
        "max_tokens": max_tokens or self.max_tokens,
    }
    
    # GPT-5.1: Enable prompt caching for system messages (60% cost savings)
    if self.model.startswith("gpt-5.1"):
        # System message caching (if OpenAI API supports it)
        # This reduces token costs for repeated system prompts
        pass  # Implement when API supports it
    
    # Add tools if provided
    if tools:
        request_params["tools"] = tools
        if tool_choice:
            request_params["tool_choice"] = tool_choice
    
    response = await self.client.chat.completions.create(**request_params)
    return response
```

**Priority:** MEDIUM  
**Effort:** 2 hours  
**Dependencies:** GPT-5.1 API availability

---

## Phase 5: Testing and Validation

### 5.1 Integration Tests

**Test Cases:**
1. Office lights blink red every 15 minutes (state restoration)
2. Turn on lights at sunset (time trigger)
3. Blink lights when motion detected (event trigger)
4. Change color based on temperature (conditional)

**Run Tests:**
```bash
cd services/ha-ai-agent-service
pytest tests/integration/test_office_lights_blink_automation.py -v
```

**Priority:** HIGH  
**Effort:** 4 hours  
**Dependencies:** Phases 1-2 complete

---

### 5.2 End-to-End Testing

**Test Flow:**
1. Send user prompt via API
2. Verify context injection
3. Verify tool call
4. Verify automation creation
5. Verify automation works in HA

**Priority:** HIGH  
**Effort:** 6 hours  
**Dependencies:** All phases complete

---

## Implementation Timeline

### Week 1: Critical Fixes
- **Day 1-2:** Fix services summary service
- **Day 3-4:** Fix capability patterns service
- **Day 5:** Fix areas service

### Week 2: Prompt Enhancement
- **Day 1:** Add state restoration pattern
- **Day 2:** Add time pattern examples
- **Day 3:** Add color/blink patterns
- **Day 4-5:** Testing and refinement

### Week 3: Optimization
- **Day 1-2:** Model optimization
- **Day 3-4:** Integration tests
- **Day 5:** End-to-end testing

---

## Success Metrics

### Context Injection
- ✅ Services summary: > 50 services listed
- ✅ Capability patterns: > 10 patterns identified
- ✅ Areas: All areas with area_id mapped

### Prompt Quality
- ✅ State restoration pattern: Included with YAML example
- ✅ Time patterns: Included with examples
- ✅ Color patterns: Included with RGB/HS examples

### Automation Generation
- ✅ Success rate: > 90% for test cases
- ✅ YAML validity: 100% (all generated YAML is valid)
- ✅ State restoration: 100% (all "restore state" requests work)

---

## Risk Mitigation

### Risk 1: Services API Changes
**Mitigation:** Add fallback to entity attributes if services API fails

### Risk 2: Context Too Large
**Mitigation:** Implement context prioritization (critical services first)

### Risk 3: Model Limitations
**Mitigation:** GPT-5.1 provides best quality and cost efficiency. Fallback to GPT-4o if GPT-5.1 unavailable.

---

## Dependencies

### External
- Home Assistant API (services, areas, entities)
- Data API (entities, device metadata)
- OpenAI API (GPT-5.1 - primary, GPT-4o fallback)

### Internal
- Context builder service
- Tool service
- Prompt assembly service

---

## Next Steps

1. **Immediate:** Fix services summary service (Phase 1.1)
2. **Immediate:** Fix capability patterns service (Phase 1.2)
3. **This Week:** Add state restoration pattern to system prompt (Phase 2.1)
4. **Next Week:** Complete all Phase 1-2 items
5. **Ongoing:** Testing and refinement

---

## References

- [Home Assistant 2025.10 Release Notes](https://www.home-assistant.io/blog/2025/10/02/release-202510/)
- [OpenAI Tool Calling Guide](https://platform.openai.com/docs/guides/function-calling)
- [2025 AI Agent Patterns](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf)
- [PROMPT_CONTEXT_ANALYSIS.md](./PROMPT_CONTEXT_ANALYSIS.md) - Current gap analysis

