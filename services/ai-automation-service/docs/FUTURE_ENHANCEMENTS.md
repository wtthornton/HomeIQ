# AI Automation Service - Future Enhancements

**Last Updated:** November 14, 2025
**Status:** Implementation Roadmap

This document outlines potential enhancements for the AI Automation Service that can be implemented in future iterations.

---

## 📊 Implementation Status Summary

**Completed (Phase 1 - YAML Creation Features):**
- ✅ Trigger Variables - Access trigger data in actions
- ✅ Continue_on_Error - Resilient action sequences
- ✅ wait_for_trigger - Sequential automation control
- ✅ Common Patterns Library - 10 pre-built patterns
- ✅ Pattern Matching & Composition - Intelligent pattern detection
- ✅ Automation Miner Integration - Community data integration
- ✅ Blueprint Parser - Modern HA blueprint support
- ✅ Safety Rule 7 - Timeout validation

**Pending (Phase 2 - Advanced Features):**
- 🔲 Template Support & Response Variables
- 🔲 Device Capability Integration
- 🔲 Validation Feedback Loop
- 🔲 Pattern Library Expansion (20+ more patterns)
- 🔲 LLM Prompt Optimization
- 🔲 Blueprint Quality Filtering
- 🔲 Advanced Pattern Features

---

## 🎯 Tier 1: High-Impact Quick Wins

### 1. Template Support & Response Variables

**Description:** Enable dynamic values in automations using Jinja2 templates and store action responses for later use.

**Current State:** Basic trigger variables implemented, but no response variable storage.

**Implementation:**

```python
# In contracts/models.py
class Action(BaseModel):
    # ... existing fields ...
    response_variable: Optional[str] = Field(
        None,
        description="Store action response in this variable for later use"
    )

# Example YAML generation:
actions:
  - action: weather.get_forecasts
    target:
      entity_id: weather.home
    data:
      type: daily
    response_variable: weather_forecast

  - action: notify.mobile_app
    data:
      message: >
        Tomorrow's forecast: {{ weather_forecast.forecast[0].condition }}
        High: {{ weather_forecast.forecast[0].temperature }}°F
```

**Benefits:**
- Pass data between actions dynamically
- Create more sophisticated automations
- Reduce redundant service calls

**Effort:** 2-3 hours
**Priority:** High
**Dependencies:** None

---

### 2. Enhanced Device Capability Integration

**Description:** Leverage device-intelligence-service to provide context-aware suggestions.

**Current State:** Device intelligence service exists but not integrated into YAML generation.

**Implementation:**

```python
# In nl_automation_generator.py
async def _enrich_with_device_capabilities(
    self,
    entities: List[Dict[str, Any]]
) -> str:
    """
    Fetch device capabilities and add to LLM prompt.

    Example enrichment:
    - light.kitchen supports: brightness (0-255), color_temp (153-500)
    - Common usage: brightness=255 in 73% of automations
    - Often paired with: motion_sensor (67%), schedule (45%)
    """
    device_intel = DeviceIntelligenceClient()

    enriched = []
    for entity in entities:
        capabilities = await device_intel.get_capabilities(entity['entity_id'])
        usage_stats = await miner.get_device_usage_stats(entity['domain'])

        enriched.append({
            'entity': entity,
            'capabilities': capabilities,
            'community_usage': usage_stats
        })

    return self._format_device_context(enriched)
```

**Benefits:**
- LLM knows exact device capabilities
- Suggests realistic values (brightness: 255 vs 100%)
- Learns from community usage patterns

**Effort:** 2-3 hours
**Priority:** High
**Dependencies:** Device Intelligence Service (Port 8028)

---

### 3. Validation Feedback Loop

**Description:** When safety validator finds issues, re-prompt LLM to fix them automatically.

**Current State:** Safety validator returns issues, but requires manual user intervention.

**Implementation:**

```python
# In enhanced_automation_generator.py
async def generate_with_validation_loop(
    self,
    request: NLAutomationRequest,
    max_retries: int = 2
) -> EnhancedGenerationResult:
    """
    Generate automation with automatic validation and retry.
    """
    for attempt in range(max_retries + 1):
        # Generate automation
        result = await self.generate(request)

        # Validate
        validation = await self.safety_validator.validate(result.automation)

        if not validation.has_errors:
            return result  # Success!

        if attempt < max_retries:
            # Re-prompt LLM with validation feedback
            feedback_prompt = self._build_feedback_prompt(
                original_yaml=result.automation,
                validation_issues=validation.issues
            )

            # Retry with enhanced prompt
            result = await self._retry_with_feedback(feedback_prompt)

    # Max retries exceeded
    return result  # Return with validation issues
```

**Benefits:**
- Reduces user back-and-forth
- Improves success rate (90%+ valid YAML on first try)
- LLM learns from validation errors

**Effort:** 1.5-2 hours
**Priority:** High
**Dependencies:** None

---

## 🚀 Tier 2: Pattern Library Expansion

### 4. Add 20+ Common Automation Patterns

**Description:** Expand pattern library from 10 to 30+ patterns covering more use cases.

**Current Patterns (10):**
1. Motion-activated light with auto-off
2. Door/window open alert
3. Climate control pause on window open
4. Presence-based lighting
5. Schedule-based automation
6. Low battery notification
7. Water leak alert
8. Temperature-based fan control
9. Night mode automation
10. Multi-sensor correlation

**New Patterns to Add (20):**

**Energy Management:**
11. Solar export automation (export when battery full)
12. Off-peak charging schedule (charge during cheap electricity)
13. High consumption alert (notify when usage spikes)
14. Vampire power elimination (turn off standby devices)

**Security:**
15. Vacation mode (randomize lights, security alerts)
16. Door left open reminder (after 5min)
17. Arrival notification (notify when person arrives)
18. Camera motion recording (start recording on motion)

**Comfort:**
19. Morning routine (lights, coffee, heating)
20. Evening routine (dim lights, lock doors)
21. Circadian lighting (adjust color temperature by time)
22. Humidity-based fan control

**Convenience:**
23. Doorbell to lights (flash lights when doorbell rings)
24. Appliance done notification (washer/dryer complete)
25. Plant watering reminder (based on moisture sensor)
26. Garage door left open (close after 10min)

**Advanced:**
27. Multi-room occupancy lighting (progressive lighting)
28. Weather-based automation (close blinds on hot days)
29. Air quality response (turn on purifier when AQI high)
30. Synergy pattern (multi-hop device coordination)

**Implementation:**

Each pattern requires:
- `PatternDefinition` in `common_patterns.py`
- YAML template with variables
- Keyword matching for pattern detection
- Test cases

**Effort:** 1.5 hours (30min per 10 patterns)
**Priority:** Medium
**Dependencies:** None

---

### 5. Pattern Suggestions API

**Description:** Endpoint to suggest patterns based on available entities.

**Implementation:**

```python
# In api/patterns.py
@router.get("/api/patterns/suggestions")
async def suggest_patterns(
    available_entities: List[str] = Query(...)
) -> List[PatternSuggestion]:
    """
    Suggest applicable patterns based on user's entities.

    Example:
    - User has: motion_sensor.living_room, light.living_room
    - Suggests: "Motion-Activated Light" pattern (90% match)
    """
    matcher = PatternMatcher()
    entities = await fetch_entity_details(available_entities)

    suggestions = []
    for pattern_id, pattern in PATTERNS.items():
        # Check if user has required entities
        match_score = matcher.calculate_entity_match(
            pattern.variables,
            entities
        )

        if match_score > 0.5:  # 50% match
            suggestions.append(PatternSuggestion(
                pattern_id=pattern_id,
                pattern_name=pattern.name,
                match_score=match_score,
                missing_entities=matcher.get_missing_entities(pattern, entities),
                example_yaml=pattern.template
            ))

    return sorted(suggestions, key=lambda s: s.match_score, reverse=True)
```

**UI Integration:**

```typescript
// In ai-automation-ui
const PatternSuggestions: React.FC = () => {
  const [suggestions, setSuggestions] = useState<PatternSuggestion[]>([]);

  useEffect(() => {
    fetchPatternSuggestions();
  }, []);

  return (
    <div className="pattern-suggestions">
      <h3>Suggested Automations</h3>
      {suggestions.map(pattern => (
        <PatternCard
          key={pattern.pattern_id}
          pattern={pattern}
          onApply={() => applyPattern(pattern)}
        />
      ))}
    </div>
  );
};
```

**Benefits:**
- Proactive pattern recommendations
- Faster automation creation
- Educates users about possibilities

**Effort:** 1 hour
**Priority:** Medium
**Dependencies:** Pattern library

---

## 🔬 Tier 3: Advanced Features

### 6. Pattern Confidence Boosting with Community Data

**Description:** Boost pattern confidence when community data supports the pattern.

**Implementation:**

```python
# In pattern_matcher.py
async def match_patterns_with_community_data(
    self,
    request: str,
    entities: List[Dict]
) -> List[PatternMatch]:
    """
    Match patterns and boost confidence based on community usage.
    """
    matches = await self.match_patterns(request, entities)
    miner = get_miner_integration()

    for match in matches:
        # Get devices from pattern
        devices = [v.domain for v in match.pattern.variables]

        # Check community data
        community_automations = await miner.search_automations(
            device=devices[0] if devices else None,
            min_quality=0.7
        )

        # Boost confidence if pattern is popular in community
        if len(community_automations) > 50:
            match.confidence *= 1.2  # 20% boost
            logger.info(
                f"Boosted {match.pattern.name} confidence: "
                f"{len(community_automations)} community examples"
            )
        elif len(community_automations) < 10:
            match.confidence *= 0.9  # 10% penalty for rare patterns

    return sorted(matches, key=lambda m: m.confidence, reverse=True)
```

**Benefits:**
- Prioritizes proven patterns
- Reduces novel pattern suggestions
- Learns from community

**Effort:** 1 hour
**Priority:** Medium
**Dependencies:** Automation Miner

---

### 7. Advanced Wait_for_Trigger Examples

**Description:** Add more sophisticated wait_for_trigger examples to LLM prompt.

**Current State:** Basic examples (motion sensor, door sensor)

**New Examples:**

```yaml
# Multi-trigger wait (any of these triggers)
- wait_for_trigger:
    - trigger: state
      entity_id: binary_sensor.door
      to: "off"
    - trigger: state
      entity_id: input_boolean.override
      to: "on"
    - trigger: event
      event_type: custom_cancel
  timeout: "00:10:00"
  continue_on_timeout: false  # Stop if no trigger

# Wait with template condition
- wait_for_trigger:
    - trigger: template
      value_template: "{{ states('sensor.temperature') | float < 20 }}"
  timeout:
    minutes: 30

# Chained waits (sequential timing)
- action: light.turn_on
  target:
    entity_id: light.hallway
- wait_for_trigger:
    - trigger: state
      entity_id: binary_sensor.motion_bedroom
      to: "on"
  timeout: "00:02:00"  # Wait 2min for bedroom motion
- action: light.turn_on
  target:
    entity_id: light.bedroom
```

**Benefits:**
- LLM generates more sophisticated automations
- Better use of wait_for_trigger feature
- Covers edge cases

**Effort:** 30 minutes
**Priority:** Low
**Dependencies:** None

---

### 8. Blueprint Quality Filtering for Miner

**Description:** When populating automation-miner, filter blueprints by quality criteria.

**Implementation:**

```python
# In automation-miner/src/miner/parser.py
class BlueprintQualityFilter:
    """Filter blueprints to only include latest spec (2024+)"""

    def is_modern_blueprint(self, yaml_data: Dict[str, Any]) -> bool:
        """
        Check if blueprint uses modern syntax (2024+ spec).

        Criteria:
        - Has 'blueprint' block
        - Uses 'selector' blocks in inputs
        - Uses 'trigger:' not 'platform:' (2025 syntax)
        - Has proper input validation
        """
        if 'blueprint' not in yaml_data:
            return False

        blueprint = yaml_data['blueprint']
        inputs = blueprint.get('input', {})

        # Check for selectors
        has_selectors = any(
            'selector' in input_def
            for input_def in inputs.values()
        )

        if not has_selectors:
            return False  # Legacy format

        # Check for modern trigger syntax
        triggers = yaml_data.get('trigger', [])
        if isinstance(triggers, list) and triggers:
            # Modern: trigger: - platform: state
            # Legacy: platform: state (at root)
            return True

        return False

    def calculate_quality_score(
        self,
        blueprint: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> float:
        """
        Calculate quality score (0.0-1.0) based on:
        - Likes/votes (popularity)
        - Age (recency, prefer <2 years)
        - Completeness (description, inputs, etc.)
        - Modern syntax compliance
        """
        likes = metadata.get('likes', 0)
        age_days = metadata.get('age_days', 0)

        # Popularity score (log scale)
        popularity = min(1.0, (likes / 100) ** 0.5)

        # Recency score (decay over 2 years)
        recency = max(0.0, 1.0 - (age_days / 730))

        # Completeness score
        has_description = bool(blueprint.get('blueprint', {}).get('description'))
        has_inputs = bool(blueprint.get('blueprint', {}).get('input'))
        has_triggers = bool(blueprint.get('trigger'))
        has_actions = bool(blueprint.get('action'))

        completeness = (
            (0.3 if has_description else 0) +
            (0.3 if has_inputs else 0) +
            (0.2 if has_triggers else 0) +
            (0.2 if has_actions else 0)
        )

        # Modern syntax bonus
        modern_bonus = 0.1 if self.is_modern_blueprint(blueprint) else 0

        # Weighted score
        quality = (
            0.4 * popularity +
            0.3 * recency +
            0.3 * completeness +
            modern_bonus
        )

        return min(1.0, quality)
```

**Usage:**

```python
# In crawler
filter = BlueprintQualityFilter()

for post in discourse_posts:
    blueprint = parser.parse_yaml(post['yaml'])

    if not filter.is_modern_blueprint(blueprint):
        logger.info(f"Skipping legacy blueprint: {post['title']}")
        continue

    quality = filter.calculate_quality_score(blueprint, post)

    if quality < 0.5:
        logger.info(f"Skipping low quality ({quality:.2f}): {post['title']}")
        continue

    # Store high-quality modern blueprint
    await store_automation(blueprint, quality)
```

**Benefits:**
- Only store high-quality blueprints
- Prefer modern syntax (2024+ spec)
- Better pattern learning from quality data

**Effort:** 2 hours
**Priority:** Medium
**Dependencies:** Automation Miner

---

### 9. Pattern Merge Strategy Implementation

**Description:** When multiple patterns apply, intelligently merge them into a single automation.

**Current State:** Pattern composer has merge strategy placeholder.

**Implementation:**

```python
# In pattern_composer.py
async def _merge_strategy(
    self,
    matches: List[PatternMatch]
) -> ComposedAutomation:
    """
    Merge multiple patterns with same trigger into one automation.

    Example:
    - Pattern 1: Motion → Light (turn on)
    - Pattern 2: Motion → Notify (send alert)

    Merged:
    trigger: motion
    actions:
      - light.turn_on
      - notify.send
    """
    # Verify all patterns share trigger type
    trigger_types = set(m.pattern.template.split('trigger:')[1].split('\n')[0]
                       for m in matches)

    if len(trigger_types) > 1:
        raise ValueError("Cannot merge patterns with different trigger types")

    # Use first pattern as base
    base_pattern = matches[0].pattern
    base_yaml = yaml.safe_load(base_pattern.template)

    # Merge actions from other patterns
    for match in matches[1:]:
        pattern_yaml = yaml.safe_load(match.pattern.template)
        additional_actions = pattern_yaml.get('action', [])

        base_yaml['action'].extend(additional_actions)

    # Combine descriptions
    descriptions = [m.pattern.name for m in matches]
    base_yaml['description'] = f"Combined: {', '.join(descriptions)}"

    return ComposedAutomation(
        automations=[base_yaml],
        strategy='merged_patterns',
        patterns_used=[m.pattern.id for m in matches],
        confidence=sum(m.confidence for m in matches) / len(matches)
    )
```

**Benefits:**
- Creates comprehensive automations
- Reduces automation count
- Logical grouping of related actions

**Effort:** 2 hours
**Priority:** Low
**Dependencies:** Pattern library

---

### 10. Cross-Service Pattern Detection

**Description:** Detect patterns that span multiple Home Assistant integrations.

**Example Patterns:**

```python
# Pattern: Solar Export to Battery
{
    'devices': ['sensor.solar_production', 'sensor.battery_level', 'switch.battery_charge'],
    'condition': 'solar_production > home_consumption AND battery < 90%',
    'action': 'Start battery charging'
}

# Pattern: Weather-Based Climate Control
{
    'devices': ['weather.home', 'climate.living_room', 'cover.blinds'],
    'condition': 'temperature > 85°F AND sunny',
    'action': 'Close blinds, set AC to 72°F'
}

# Pattern: Multi-Room Audio Follow
{
    'devices': ['media_player.bedroom', 'media_player.kitchen', 'binary_sensor.motion'],
    'condition': 'Motion detected in kitchen, music playing in bedroom',
    'action': 'Transfer playback to kitchen speaker'
}
```

**Implementation:**

```python
# In pattern_discovery/cross_service_learner.py
class CrossServicePatternLearner:
    """Learn patterns that span multiple HA integrations"""

    async def discover_synergy_patterns(
        self,
        min_quality: float = 0.8
    ) -> List[PatternDefinition]:
        """
        Discover patterns involving multiple integrations.

        Uses graph analysis to find common device combinations
        across different HA domains.
        """
        automations = await self.miner.search_automations(min_quality=min_quality)

        # Build integration graph
        integration_graph = self._build_integration_graph(automations)

        # Find strongly connected components
        clusters = self._find_clusters(integration_graph, min_cluster_size=10)

        patterns = []
        for cluster in clusters:
            pattern = await self._extract_cross_service_pattern(cluster)
            if pattern:
                patterns.append(pattern)

        return patterns
```

**Benefits:**
- Discovers advanced multi-integration patterns
- Learns complex home automation strategies
- Creates sophisticated automations

**Effort:** 4-5 hours
**Priority:** Low
**Dependencies:** Automation Miner, Graph analysis library

---

## 📝 Implementation Priority Matrix

| Feature | Effort | Impact | Priority | Dependencies |
|---------|--------|--------|----------|--------------|
| Template Support & Response Variables | 2-3h | High | **P0** | None |
| Device Capability Integration | 2-3h | High | **P0** | Device Intelligence |
| Validation Feedback Loop | 1.5-2h | High | **P0** | None |
| Pattern Library Expansion (+20) | 1.5h | Medium | **P1** | None |
| Pattern Suggestions API | 1h | Medium | **P1** | Pattern Library |
| Pattern Confidence Boosting | 1h | Medium | **P1** | Miner |
| Enhanced Wait Examples | 30m | Low | **P2** | None |
| Blueprint Quality Filtering | 2h | Medium | **P2** | Miner |
| Pattern Merge Strategy | 2h | Low | **P2** | Pattern Library |
| Cross-Service Patterns | 4-5h | Low | **P3** | Miner, Graph lib |

**Total Effort Estimate:** 18-21 hours

---

## 🎯 Recommended Implementation Order

### Sprint 1 (6-8 hours) - High-Impact Features
1. **Validation Feedback Loop** (1.5-2h)
   - Immediate improvement to success rate
   - No dependencies

2. **Template Support & Response Variables** (2-3h)
   - Enables advanced automations
   - High user value

3. **Device Capability Integration** (2-3h)
   - Better context-aware generation
   - Leverages existing service

### Sprint 2 (3-4 hours) - Pattern Enhancement
4. **Pattern Library Expansion** (1.5h)
   - Expand from 10 to 30 patterns
   - Quick wins for coverage

5. **Pattern Suggestions API** (1h)
   - Proactive recommendations
   - Great UX improvement

6. **Pattern Confidence Boosting** (1h)
   - Better pattern prioritization
   - Uses community data

### Sprint 3 (4-5 hours) - Polish & Advanced
7. **Blueprint Quality Filtering** (2h)
   - Improves miner data quality
   - Better pattern learning

8. **Pattern Merge Strategy** (2h)
   - Sophisticated automation composition
   - Reduces automation count

9. **Enhanced Wait Examples** (30m)
   - Better LLM prompt coverage
   - Edge case handling

### Sprint 4 (4-5 hours) - Research & Experiment
10. **Cross-Service Patterns** (4-5h)
    - Research spike for advanced patterns
    - May reveal new opportunities

---

## 📚 Documentation Updates Needed

When implementing these features, update:

1. **API_REFERENCE.md** - Add new endpoints
2. **MINER_INTEGRATION.md** - Update integration examples
3. **User documentation** - Add new automation capabilities
4. **LLM prompts** - Include new examples and features

---

## 🧪 Testing Strategy

For each feature:
1. **Unit tests** - Core functionality
2. **Integration tests** - End-to-end flows
3. **Manual verification** - Real automation generation
4. **Performance tests** - Latency impact (<10% overhead)

---

## 📊 Success Metrics

Track these metrics after implementation:

| Metric | Current | Target |
|--------|---------|--------|
| Pattern match rate | ~30% | >60% |
| First-attempt success rate | ~75% | >90% |
| Validation errors | ~15% | <5% |
| Average generation time | ~3s | <5s |
| User satisfaction | N/A | >4.5/5 |

---

## 🔗 Related Documentation

- [MINER_INTEGRATION.md](./MINER_INTEGRATION.md) - Community data integration
- [API_REFERENCE.md](../../docs/api/API_REFERENCE.md) - API endpoints
- [QUICK_START.md](../../docs/QUICK_START.md) - Getting started guide

---

**Document Version:** 1.0.0
**Last Review:** November 14, 2025
**Next Review:** After Sprint 1 completion
