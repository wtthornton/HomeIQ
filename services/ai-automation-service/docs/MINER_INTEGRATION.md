# Automation Miner Integration

**Integration between AI Automation Service and Automation Miner corpus**

## Overview

The AI Automation Service now integrates with the Automation Miner to leverage community knowledge for better automation generation. This creates a **self-improving system** that learns from proven community automations.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   AI Automation Service                       │
│  ┌───────────────┐  ┌─────────────────┐  ┌─────────────────┐│
│  │  Common       │  │  Pattern        │  │  Miner          ││
│  │  Patterns     │←─┤  Discovery      │←─┤  Integration    ││
│  │  Library      │  │  (Auto-learns)  │  │  (Community)    ││
│  └───────────────┘  └─────────────────┘  └────────┬────────┘│
└──────────────────────────────────────────────────── │ ────────┘
                                                      │
                                                      ↓ HTTP
                                            ┌─────────────────┐
                                            │  Automation     │
                                            │  Miner Service  │
                                            │  (Port 8029)    │
                                            │                 │
                                            │  2,000+ curated │
                                            │  automations    │
                                            └─────────────────┘
```

## Features

### 1. Pattern Discovery
Automatically discovers new patterns from community corpus:

```python
from pattern_discovery import get_pattern_learner

learner = get_pattern_learner()
discovered_patterns = await learner.discover_patterns(
    min_quality=0.8,
    min_occurrences=20
)

# Returns PatternDefinition objects for common patterns
# Example: "motion_sensor + light" appearing 150+ times
```

### 2. Usage Statistics
Get community usage data for device types:

```python
from utils.miner_integration import get_miner_integration

miner = get_miner_integration()
stats = await miner.get_device_usage_stats('light')

# Returns:
# {
#   "device": "light",
#   "total_automations": 847,
#   "common_use_cases": {"comfort": 512, "security": 245},
#   "common_complexity": "low",
#   "avg_quality": 0.82
# }
```

### 3. Similar Automation Search
Find proven examples for user requests:

```python
similar = await miner.get_similar_automations(
    devices=['motion_sensor', 'light'],
    limit=5
)

# Returns top 5 quality automations using these devices
```

### 4. LLM Prompt Enrichment
Enhance LLM prompts with community examples:

```python
enriched_prompt = await miner.enrich_llm_prompt(
    base_prompt=original_prompt,
    devices=['light', 'motion_sensor']
)

# Adds section with 2-3 similar community automations
# Gives LLM real-world examples to learn from
```

## Integration Points

### A. Pattern Library Enhancement
**Current:** 10 hand-crafted patterns
**With Miner:** Automatically discovers 50-100+ patterns

```python
# Periodic pattern discovery (e.g., weekly)
learner = get_pattern_learner()
new_patterns = await learner.discover_patterns(min_quality=0.7)

# Add to pattern library
from patterns import PATTERNS
for pattern in new_patterns:
    PATTERNS[pattern.id] = pattern
```

### B. Device Capability Enrichment
**Current:** Device capabilities from device-intelligence
**With Miner:** + Community usage patterns

```python
# Not just "what's possible" but "what works in practice"
capabilities = device_intelligence.get_capabilities('light.kitchen')
community_usage = await miner.get_device_usage_stats('light')

# Combine for LLM:
# "For light entities you can use:"
# - brightness: 0-255 (technical capability)
# - Commonly used: brightness=255 in 73% of automations (community data)
# - Often paired with: motion_sensor (67%), schedule (45%)
```

### C. Enhanced Automation Generator
The `EnhancedAutomationGenerator` can now use miner data:

```python
generator = EnhancedAutomationGenerator(
    nl_generator=nl_generator,
    enable_miner_enrichment=True  # NEW!
)

# Flow:
# 1. Try pattern matching (instant, free)
# 2. Check miner for similar automations
# 3. Enrich LLM prompt with community examples
# 4. Generate with better context
```

## Blueprint Specifications

**IMPORTANT:** When populating the automation-miner corpus, only include blueprints that conform to the latest Home Assistant specification:

**Reference:** https://www.home-assistant.io/docs/blueprint/tutorial/

### Latest Blueprint Format (2024+)

```yaml
blueprint:
  name: "Blueprint Name"
  description: "Description"
  domain: automation
  input:
    motion_sensor:
      name: "Motion Sensor"
      selector:
        entity:
          domain: binary_sensor
          device_class: motion
    light:
      name: "Light"
      selector:
        entity:
          domain: light

# Actual automation
trigger:
  - platform: state
    entity_id: !input motion_sensor
    to: "on"

action:
  - service: light.turn_on
    target:
      entity_id: !input light
```

### Filtering Criteria

When crawling blueprints:
- ✅ **Include:** Blueprints using `!input` syntax
- ✅ **Include:** Modern trigger/action format (`trigger:` not `platform:`)
- ✅ **Include:** Blueprints with selectors (`selector:` blocks)
- ❌ **Exclude:** Legacy format (pre-2021)
- ❌ **Exclude:** Deprecated syntax
- ❌ **Exclude:** Blueprints without `blueprint:` block

### Parser Enhancement Needed

The automation-miner parser should be updated to:

1. **Detect Blueprint Format:**
   ```python
   if 'blueprint' in yaml_data:
       # Extract blueprint metadata
       blueprint = yaml_data['blueprint']
       inputs = blueprint.get('input', {})

       # Parse automation section (below blueprint block)
       # Convert !input references to variable placeholders
   ```

2. **Version Detection:**
   ```python
   # Check for modern syntax indicators
   has_modern_syntax = (
       'selector' in str(yaml_data) or
       '!input' in raw_yaml or
       'trigger:' in yaml_data  # Not 'platform:'
   )
   ```

3. **Quality Filtering:**
   - Minimum likes: 100+ (proven valuable)
   - Recent: Updated within 2 years
   - Complete: Has description + YAML + inputs
   - Modern: Uses latest blueprint spec

## Usage Examples

### Example 1: Pattern Discovery (Weekly Job)

```python
# scripts/discover_patterns.py
import asyncio
from pattern_discovery import get_pattern_learner
from patterns import PATTERNS

async def weekly_pattern_discovery():
    learner = get_pattern_learner()

    # Discover patterns with strict quality requirements
    patterns = await learner.discover_patterns(
        min_quality=0.8,  # High quality only
        min_occurrences=20  # Proven pattern (20+ examples)
    )

    print(f"Discovered {len(patterns)} new patterns")

    for pattern in patterns:
        # Add to library if not already present
        if pattern.id not in PATTERNS:
            PATTERNS[pattern.id] = pattern
            print(f"  Added: {pattern.name} ({pattern.id})")

    await learner.close()

if __name__ == "__main__":
    asyncio.run(weekly_pattern_discovery())
```

### Example 2: Enriched LLM Generation

```python
# In nl_automation_generator.py
async def generate_with_miner_enrichment(self, request):
    # Extract devices from request
    devices = extract_devices_from_request(request.request_text)

    # Get miner integration
    miner = get_miner_integration()

    # Enrich prompt with community examples
    enriched_prompt = await miner.enrich_llm_prompt(
        base_prompt=self._build_prompt(request),
        devices=devices
    )

    # Generate with enriched context
    response = await self.openai_client.generate(enriched_prompt)

    await miner.close()
    return response
```

### Example 3: Pattern Confidence Boosting

```python
# In pattern_matcher.py
async def match_patterns_with_community_data(self, request, entities):
    # Normal pattern matching
    matches = await self.match_patterns(request, entities)

    # Boost confidence if community data supports pattern
    miner = get_miner_integration()

    for match in matches:
        devices = [v.domain for v in match.pattern.variables]
        community_count = len(await miner.search_automations(
            device=devices[0],
            min_quality=0.7
        ))

        if community_count > 50:
            # Strong community support → boost confidence
            match.confidence *= 1.2

    return matches
```

## Performance Impact

| Metric | Without Miner | With Miner | Improvement |
|--------|---------------|------------|-------------|
| **Pattern Count** | 10 hand-crafted | 50-100+ discovered | 5-10x |
| **Pattern Quality** | Expert designed | Community-proven | Validated |
| **LLM Context** | Generic examples | Real-world examples | Better accuracy |
| **Generation Cost** | $0.001/request | $0.001/request | No change |
| **Latency** | 50-150ms (pattern) | 50-200ms (pattern + lookup) | +50ms max |

## Configuration

Enable miner integration in config:

```python
# src/config.py
class Settings(BaseSettings):
    # Automation Miner Integration
    enable_miner_integration: bool = Field(
        default=True,
        description="Enable automation-miner integration"
    )

    miner_base_url: str = Field(
        default="http://localhost:8029",
        description="Automation miner service URL"
    )

    miner_min_quality: float = Field(
        default=0.7,
        description="Minimum quality for miner automations"
    )
```

## Deployment Considerations

### Initial Setup

1. **Populate Miner Corpus** (one-time, ~3-6 hours):
   ```bash
   cd services/automation-miner
   python -m src.cli crawl --initial --min-likes 100
   ```

2. **Verify Data Quality**:
   ```bash
   curl http://localhost:8029/api/automation-miner/corpus/stats
   ```

3. **Run Pattern Discovery**:
   ```bash
   cd services/ai-automation-service
   python scripts/discover_patterns.py
   ```

### Ongoing Maintenance

- **Weekly:** Run pattern discovery to find new patterns
- **Monthly:** Refresh miner corpus with new community automations
- **Quarterly:** Review and prune low-quality patterns

## Future Enhancements

1. **Automatic Template Extraction** - Analyze YAML structures to generate exact templates
2. **User Pattern Contribution** - Users can promote their automations to patterns
3. **A/B Testing** - Compare community patterns vs hand-crafted
4. **Pattern Versioning** - Track pattern evolution over time
5. **Cross-Service Patterns** - Patterns that span multiple HA integrations

## Troubleshooting

### Miner Not Available
```python
miner = get_miner_integration()
if not await miner.is_available():
    logger.warning("Miner not available, using fallback")
    # System continues without miner enrichment
```

### Empty Corpus
```
# Check corpus size
curl http://localhost:8029/api/automation-miner/corpus/stats

# If count < 100, run initial crawl
cd services/automation-miner
python -m src.cli crawl --initial
```

### Low Quality Data
```
# Increase quality threshold
miner = get_miner_integration()
automations = await miner.search_automations(min_quality=0.9)
```

## License

See project LICENSE file.

## Authors

- Community Pattern Learner: Implementation (Option 8)
- Miner Integration: Implementation (Option 8)
- Based on Automation Miner Service (Epic AI-4)
