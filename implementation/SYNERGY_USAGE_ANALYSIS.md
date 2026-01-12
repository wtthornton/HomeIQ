# Synergy Usage Analysis: Recommendations and Automation Creation

**Date:** January 16, 2026  
**Status:** 📊 **ANALYSIS COMPLETE**

---

## Executive Summary

Synergies are device interaction patterns detected from Home Assistant event data. They are used to:
1. **Provide Recommendations** - Suggest automation opportunities to users
2. **Generate Automations** - Create Home Assistant automation code/blueprints
3. **Context Enhancement** - Provide context to AI agents for automation generation

---

## Synergy Flow: Detection → Storage → Usage

### 1. Detection Phase

**Service:** `ai-pattern-service`

**Process:**
- Analyzes Home Assistant event data
- Detects device interaction patterns (device_pair, device_chain, scene_based)
- Calculates quality scores (impact, confidence, pattern support)
- Filters low-quality synergies (quality_score >= 0.50)

**Output:** Synergy opportunities stored in database

---

### 2. Storage Phase

**Database:** SQLite (`ai_automation.db`)

**Table:** `synergy_opportunities`

**Key Fields:**
- `synergy_type` - Type of synergy (device_pair, device_chain, scene_based)
- `device_ids` - Devices involved in the synergy
- `impact_score` - Potential benefit (0.0-1.0)
- `confidence` - Reliability score (0.0-1.0)
- `quality_score` - Overall quality (0.0-1.0)
- `quality_tier` - Quality tier (high, medium, low)
- `explanation` - XAI explanation (human-readable)
- `context_breakdown` - Multi-modal context (temporal, weather, energy)

**Filtering:**
- Only medium+ quality synergies stored (quality_score >= 0.50)
- Low-quality synergies filtered during storage

---

### 3. Usage Phase: Recommendations

**API Endpoint:** `GET /api/v1/synergies`

**Service:** `ai-pattern-service`

**Features:**
- List synergies with filtering (type, quality, confidence)
- Order by priority score (impact + confidence + quality)
- Filter by active devices
- Quality tier filtering

**Usage:**
- UI displays synergies as recommendations
- Users can browse automation opportunities
- Filter by quality, type, area

---

### 4. Usage Phase: Automation Creation

**Services Involved:**

#### A. HA AI Agent Service (Primary Automation Generator)

**Service:** `ha-ai-agent-service`

**Synergy Usage:**
- Synergies provided as context to AI agent
- Context builder includes synergy information
- AI agent uses synergies to generate automation code

**Flow:**
1. User requests automation
2. Context builder fetches relevant synergies
3. Synergies included in prompt context
4. AI agent generates automation code
5. Automation code returned to user

#### B. AI Automation Service (Legacy/Alternative)

**Service:** `ai-automation-service-new`

**Note:** This service may have alternative automation generation paths

---

## Code Analysis: How Synergies Are Used

### API Endpoints

**Pattern Service (`ai-pattern-service`):**

1. **GET /api/v1/synergies** - List synergies
   - Filters: type, quality_score, quality_tier, confidence
   - Orders by priority score
   - Returns synergy opportunities

2. **GET /api/v1/synergies/statistics** - Synergy statistics
   - Counts by type
   - Quality distribution
   - Overall statistics

### Synergy Retrieval

**Function:** `get_synergy_opportunities()` in `services/ai-pattern-service/src/crud/synergies.py`

**Parameters:**
- `synergy_type` - Filter by type
- `min_confidence` - Minimum confidence threshold
- `min_quality_score` - Minimum quality threshold (default: None)
- `quality_tier` - Filter by tier ('high', 'medium', 'low')
- `order_by_priority` - Order by priority score

**Priority Score Calculation:**
```python
priority_score = (
    impact_score * 0.30 +
    confidence * 0.20 +
    pattern_support_score * 0.20 +
    quality_score * 0.20 +
    validation_bonus * 0.10
)
```

---

## Recommendation Flow

### UI Display (User View)

1. **User browses synergies** via UI
2. **Synergies displayed** with:
   - Quality tier (high/medium/low)
   - Impact score
   - Confidence score
   - Explanation (XAI)
   - Context breakdown

3. **User selects synergy** for automation creation
4. **Automation generation** triggered with synergy context

---

## Automation Creation Flow

### Step 1: Synergy Selection

User selects a synergy from recommendations:
- Synergy ID
- Device IDs
- Type and metadata

### Step 2: Context Building

**Service:** `ha-ai-agent-service` → Context Builder

Context includes:
- Selected synergy information
- Device metadata
- Area information
- Historical patterns
- Multi-modal context (weather, energy, temporal)

### Step 3: AI Prompt Generation

AI prompt includes:
- Synergy explanation
- Device context
- Automation goal
- Quality indicators

### Step 4: Automation Code Generation

AI agent generates:
- Home Assistant automation YAML
- Blueprint configuration
- Device configuration
- Trigger conditions
- Action sequences

### Step 5: Automation Delivery

Generated automation:
- Returned to user
- Can be imported to Home Assistant
- Includes documentation

---

## Quality-Based Filtering

### Storage Filtering

**Threshold:** quality_score >= 0.50 (medium+ quality)

**Impact:**
- Only useful synergies stored
- Low-quality synergies filtered out
- Database focused on automation-worthy synergies

### Retrieval Filtering

**Optional Filters:**
- `min_quality_score` - Minimum quality threshold
- `quality_tier` - Filter by tier ('high', 'medium', 'low')
- `order_by_priority` - Sort by priority score

**Usage:**
- UI can filter by quality tier
- API can request high-quality only
- Default: All stored synergies (already filtered at storage)

---

## Synergy Types and Usage

### device_pair (Most Common)

**Usage:**
- Two-device interactions
- Most validated and reliable
- High quality scores
- Primary recommendation source

### device_chain (Multi-Device)

**Usage:**
- 3+ device interactions
- More complex automations
- Lower quality scores (less validation)
- Secondary recommendations

### scene_based

**Usage:**
- Scene-based interactions
- Scene automations
- Context-aware recommendations

---

## Multi-Modal Context Enhancement

**Fields:**
- `context_breakdown` - Temporal, weather, energy boosts
- `explanation` - XAI explanation with evidence

**Usage:**
- Enhances automation context
- Provides timing insights
- Energy efficiency considerations
- Weather-based triggers

---

## Summary: Synergy → Automation Pipeline

```
1. Event Data (Home Assistant)
   ↓
2. Pattern Detection (ai-pattern-service)
   ↓
3. Synergy Calculation (quality scores, validation)
   ↓
4. Storage (medium+ quality only, quality_score >= 0.50)
   ↓
5. Recommendation Display (UI - user browses)
   ↓
6. Synergy Selection (user chooses synergy)
   ↓
7. Context Building (ha-ai-agent-service)
   ↓
8. AI Prompt Generation (includes synergy context)
   ↓
9. Automation Code Generation (AI agent)
   ↓
10. Automation Delivery (YAML/Blueprint to user)
```

---

## Key Integration Points

1. **Pattern Service API** - Provides synergy data
2. **UI Dashboard** - Displays recommendations
3. **HA AI Agent Service** - Uses synergies for automation generation
4. **Context Builder** - Incorporates synergy information
5. **Quality Filtering** - Ensures only useful synergies used

---

## Recommendations for Automation Creation

**Quality Threshold:**
- Storage: >= 0.50 (medium+ quality)
- Display: All stored synergies (already filtered)
- Prioritization: Priority score (impact + confidence + quality)

**Best Practices:**
- Focus on high-quality synergies (>= 0.70)
- Use validated synergies (pattern_support_score > 0)
- Consider multi-modal context for timing
- Use XAI explanations for user understanding

---

**Status:** ✅ **ANALYSIS COMPLETE**  
**Last Updated:** January 16, 2026
