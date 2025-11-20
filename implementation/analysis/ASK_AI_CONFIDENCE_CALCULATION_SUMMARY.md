# Ask AI - Confidence Calculation & Clarification Questions Summary

**Last Updated:** January 2025  
**Service:** ai-automation-service  
**File:** `services/ai-automation-service/src/services/clarification/confidence_calculator.py`

## Overview

The Ask AI system uses a **multi-factor confidence scoring system** to determine how well it understands a user's automation request. When confidence is below a threshold (default: 85%), the system asks clarification questions to gather more information, which improves confidence and leads to better automation suggestions.

---

## How Confidence is Calculated

### Initial Confidence Calculation

**Location:** `services/ai-automation-service/src/api/ask_ai_router.py` (lines 4633-4645)

The confidence calculation starts with a **base confidence** that gets adjusted by multiple factors:

```python
# Step 1: Calculate base confidence from entity extraction
base_confidence = min(0.9, 0.5 + (len(entities) * 0.1))
# More entities = higher base confidence (max 0.9)

# Step 2: Calculate full confidence with all factors
confidence = await confidence_calculator.calculate_confidence(
    query=request.query,
    extracted_entities=entities,
    ambiguities=ambiguities,
    base_confidence=base_confidence,
    rag_client=rag_client_for_confidence
)
```

### Confidence Calculation Formula

**Location:** `services/ai-automation-service/src/services/clarification/confidence_calculator.py` (lines 26-173)

The confidence score is calculated using the following multi-factor approach:

#### 1. **Base Confidence** (Starting Point)
- **Initial Formula**: `base_confidence = min(0.9, 0.5 + (len(entities) * 0.1))`
  - Minimum: 0.5 (50%)
  - Maximum: 0.9 (90%)
  - Each extracted entity adds 10% up to the maximum
  - **Example**: 4 entities → 0.5 + (4 * 0.1) = 0.9 (90%)

#### 2. **Historical Success Boost** (RAG-Based)
- **Maximum Boost**: +20% (0.20)
- **Formula**: `boost = min(0.20, similarity * success_score * 0.20)`
- **How it works**:
  - Searches RAG (Retrieval-Augmented Generation) for similar successful queries
  - If similarity > 0.75 and success_score is high, adds boost
  - **Example**: Similarity 0.85, success_score 0.9 → boost = 0.85 * 0.9 * 0.20 = +0.15 (15%)

#### 3. **Ambiguity Penalty** (Reduces Confidence)

Each ambiguity reduces confidence by a multiplier based on severity:

| Severity | Penalty Multiplier | Impact |
|----------|-------------------|---------|
| **CRITICAL** | × 0.7 (30% reduction) | Major impact - must be clarified |
| **IMPORTANT** | × 0.85 (15% reduction) | Significant impact - should be clarified |
| **OPTIONAL** | × 0.95 (5% reduction) | Minor impact - nice to have |

**Calculation**: Confidence is multiplied by each ambiguity's penalty
- **Example**: Base 0.85 with 1 CRITICAL ambiguity → 0.85 × 0.7 = 0.595 (59.5%)
- **Example**: Base 0.85 with 2 IMPORTANT ambiguities → 0.85 × 0.85 × 0.85 = 0.614 (61.4%)

#### 4. **Clarification Answers Boost** (Increases Confidence)

When users answer clarification questions, confidence increases based on:

**A. Critical Ambiguity Completion** (40% weight)
- **Formula**: `boost = (1.0 - confidence) * completion_rate * 0.4`
- **Example**: Confidence 0.6, answered 2/2 critical → boost = (1.0 - 0.6) * 1.0 * 0.4 = +0.16 → new confidence = 0.76

**B. Important Ambiguity Completion** (20% weight)
- **Formula**: `boost = (1.0 - confidence) * completion_rate * 0.2`
- **Example**: Confidence 0.6, answered 3/3 important → boost = (1.0 - 0.6) * 1.0 * 0.2 = +0.08 → new confidence = 0.68

**C. Answer Quality Boost** (Based on average answer confidence)
- High quality (avg > 0.8): +15% of remaining gap
- Medium quality (avg > 0.6): +10% of remaining gap
- **Example**: Confidence 0.6, avg answer confidence 0.85 → boost = (1.0 - 0.6) * 0.15 = +0.06 → new confidence = 0.66

**D. Validation Bonus**
- Each validated answer: +5% of remaining gap (up to +20%)
- **Example**: Confidence 0.6, 3 validated answers → boost = (1.0 - 0.6) * min(0.20, 3 * 0.05) = +0.12 → new confidence = 0.72

#### 5. **Query Clarity Adjustment** (Word Count)
- Very short query (< 5 words): × 0.85 (15% reduction)
- Short query (< 8 words): × 0.95 (5% reduction)
- Normal query (≥ 8 words): No adjustment

#### 6. **Final Bounds**
- **Minimum**: 0.0 (0%)
- **Maximum**: 1.0 (100%)
- Confidence is clamped to this range

### Complete Example Calculation

**Scenario**: User query "Turn on office lights"

1. **Base Confidence**: 2 entities extracted → 0.5 + (2 * 0.1) = **0.7** (70%)
2. **Historical Boost**: No similar queries found → +0.0 → **0.7**
3. **Ambiguity Penalty**: 1 IMPORTANT ambiguity (which lights?) → 0.7 × 0.85 = **0.595** (59.5%)
4. **Query Clarity**: 4 words (< 5) → 0.595 × 0.85 = **0.506** (50.6%)
5. **Final Confidence**: **0.506** (50.6%) → **Below threshold (0.85), ask questions**

**After User Answers Clarification**:
- User selects "Office Ceiling Lights" → Answer validated, confidence 0.9
- **Critical Completion**: 1/1 answered → boost = (1.0 - 0.506) * 1.0 * 0.4 = **+0.198** → 0.704
- **Answer Quality**: avg confidence 0.9 > 0.8 → boost = (1.0 - 0.704) * 0.15 = **+0.044** → 0.748
- **Validation Bonus**: 1 validated → boost = (1.0 - 0.748) * 0.05 = **+0.013** → **0.761** (76.1%)
- **Still below threshold** → May ask more questions or proceed based on remaining ambiguities

---

## How Questions Help Improve Confidence

### Question Generation Process

**Location:** `services/ai-automation-service/src/services/clarification/question_generator.py`

**Flow:**
1. **Ambiguities Detected** → System identifies unclear aspects of the query
2. **Prioritization** → Ambiguities sorted by severity (CRITICAL → IMPORTANT → OPTIONAL)
3. **Question Generation** → OpenAI generates natural questions based on ambiguities
4. **User Answers** → Answers are validated and confidence is recalculated

### How Answers Improve Confidence

#### 1. **Resolving Ambiguities**
- Each answered question resolves one or more ambiguities
- Resolved ambiguities are **removed from confidence calculation**
- **Example**: 3 ambiguities reduce confidence to 0.6 → Answer 2 questions → Only 1 ambiguity remains → Confidence recalculates with only 1 ambiguity penalty

#### 2. **Answer Validation Boost**
- **Validated answers** (entity IDs verified, structured responses) get higher confidence
- **High-confidence answers** (>0.8) provide bigger boosts
- **Structured answers** (multiple choice, entity selection) are more reliable than free text

#### 3. **Completeness Tracking**
- System tracks which ambiguities are resolved
- **Completion rate** for critical/important ambiguities directly increases confidence
- **Example**: 2 critical ambiguities, answered both → 100% completion → Large boost

#### 4. **Enriched Query Rebuilding**
- After answers, system rebuilds the query with user's clarifications
- **Example**: 
  - Original: "Turn on office lights"
  - After answer: "Turn on office lights - specifically Office Ceiling Lights (light.office_ceiling)"
- Rebuilt query is used for:
  - **RAG similarity search** (may find similar successful queries)
  - **Entity re-extraction** (more accurate entity matching)
  - **Final suggestion generation** (better context)

### Confidence Improvement Example

**Initial State:**
- Query: "Flash the lights when motion detected"
- Ambiguities:
  - CRITICAL: Which lights? (multiple options found)
  - IMPORTANT: Flash duration? (not specified)
- Base confidence: 0.7
- After penalties: 0.7 × 0.7 (critical) = 0.49 (49%)
- **Below threshold (0.85) → Ask questions**

**After User Answers Question 1:**
- Question: "Which lights do you want to flash?"
- Answer: "Office Ceiling Lights" (validated, confidence 0.9)
- **Remaining ambiguities**: 1 IMPORTANT (duration)
- Recalculation:
  - Base: 0.7
  - Only 1 IMPORTANT ambiguity → 0.7 × 0.85 = 0.595
  - Critical completion boost (1/1): (1.0 - 0.595) * 1.0 * 0.4 = +0.162 → 0.757
  - Answer quality boost (0.9 > 0.8): (1.0 - 0.757) * 0.15 = +0.036 → **0.793** (79.3%)
- **Still below threshold → Ask Question 2**

**After User Answers Question 2:**
- Question: "How long should the flash last?"
- Answer: "2 seconds" (validated, confidence 0.8)
- **Remaining ambiguities**: 0
- Recalculation:
  - Base: 0.7
  - No ambiguities → 0.7 (no penalty)
  - Important completion boost (1/1): (1.0 - 0.7) * 1.0 * 0.2 = +0.06 → 0.76
  - Answer quality boost (avg 0.85 > 0.8): (1.0 - 0.76) * 0.15 = +0.036 → 0.796
  - Validation bonus (2 validated): (1.0 - 0.796) * min(0.20, 2 * 0.05) = +0.020 → **0.816** (81.6%)
- **Above threshold (0.85) → Proceed to generate suggestions**

---

## Clarification Decision Logic

### When Questions Are Asked

**Location:** `services/ai-automation-service/src/services/clarification/confidence_calculator.py` (lines 175-205)

**Decision Rules:**

1. **Always Ask if Critical Ambiguities Exist**
   ```python
   has_critical = any(amb.severity == AmbiguitySeverity.CRITICAL for amb in ambiguities)
   if has_critical:
       return True  # Always ask questions
   ```

2. **Ask if Confidence Below Threshold**
   ```python
   threshold = 0.85  # Default: 85%
   return confidence < threshold
   ```

**Combined Logic:**
- If ANY critical ambiguity → **Always ask** (regardless of confidence)
- If confidence < 0.85 → **Ask questions**
- If confidence ≥ 0.85 AND no critical ambiguities → **Proceed without questions**

### When Questions Stop

**Location:** `services/ai-automation-service/src/api/ask_ai_router.py` (lines 5492-5493)

**Stop Conditions:**
1. **Confidence ≥ Threshold**: `session.current_confidence >= session.confidence_threshold`
2. **Max Rounds Reached**: `session.rounds_completed >= session.max_rounds` (default: 3 rounds)
3. **All Critical Ambiguities Resolved**: No remaining CRITICAL ambiguities AND confidence acceptable

---

## Ambiguity Types & Severity

### Ambiguity Types

| Type | Description | Example |
|------|-------------|---------|
| **DEVICE** | Unclear which device/entity | "office lights" (multiple matches) |
| **TRIGGER** | Unclear trigger condition | "when motion detected" (which sensor?) |
| **ACTION** | Unclear action details | "flash" (duration? color? pattern?) |
| **TIMING** | Unclear timing | "in the morning" (what time?) |
| **CONDITION** | Unclear conditions | "if door opens" (which door?) |

### Ambiguity Severity Levels

| Severity | Description | Impact on Confidence | Must Clarify? |
|----------|-------------|---------------------|---------------|
| **CRITICAL** | Cannot proceed without clarification | × 0.7 (30% reduction) | **Always** |
| **IMPORTANT** | Should be clarified for best results | × 0.85 (15% reduction) | If confidence < 0.85 |
| **OPTIONAL** | Nice to have, not required | × 0.95 (5% reduction) | No |

---

## Confidence Score Breakdown

### Typical Confidence Ranges

| Range | Meaning | Action |
|-------|---------|--------|
| **0.85 - 1.0** | High confidence | Proceed with suggestions |
| **0.70 - 0.84** | Moderate confidence | May ask 1-2 questions |
| **0.50 - 0.69** | Low confidence | Ask clarification questions |
| **0.00 - 0.49** | Very low confidence | Ask multiple clarification questions |

### Factors That Increase Confidence

✅ **More entities extracted** → Higher base confidence  
✅ **Similar successful queries found** → Historical boost  
✅ **Answers to critical questions** → Large boost (40% weight)  
✅ **High-quality validated answers** → Additional boost  
✅ **Resolving all ambiguities** → Removes penalties  

### Factors That Decrease Confidence

❌ **Critical ambiguities** → 30% reduction per ambiguity  
❌ **Important ambiguities** → 15% reduction per ambiguity  
❌ **Very short queries** (< 5 words) → 15% reduction  
❌ **No historical matches** → No boost  

---

## Multi-Round Clarification Flow

### Round 1: Initial Query

1. **User submits query** → "Turn on office lights"
2. **System detects ambiguities** → CRITICAL: Which lights? (3 matches)
3. **Calculate confidence** → 0.7 base × 0.7 (critical) = 0.49 (49%)
4. **Below threshold** → Generate questions
5. **User answers** → Selects "Office Ceiling Lights"
6. **Recalculate confidence** → 0.793 (79.3%)
7. **Still below threshold** → Continue to Round 2

### Round 2: Follow-up Questions

1. **Remaining ambiguities** → IMPORTANT: Brightness level?
2. **Generate follow-up question** → "How bright should the lights be?"
3. **User answers** → "100%" (validated)
4. **Recalculate confidence** → 0.85 (85%)
5. **Meets threshold** → Proceed to suggestions

### Round 3: Maximum Rounds

- **Max rounds**: 3 (configurable)
- If confidence still < threshold after 3 rounds → **Proceed anyway** (best effort)
- System generates suggestions with available information

---

## Confidence Threshold Configuration

### Default Threshold

**Location:** `services/ai-automation-service/src/services/clarification/confidence_calculator.py` (line 15)

```python
default_threshold: float = 0.85  # 85% confidence required
```

### Per-Session Threshold

**Location:** `services/ai-automation-service/src/services/clarification/models.py` (line 79)

```python
confidence_threshold: float = 0.85  # Can be customized per session
```

### When Threshold Is Lowered

- **User explicitly asks to proceed** despite low confidence
- **Max rounds reached** → System proceeds anyway
- **All critical ambiguities resolved** → Threshold may be relaxed slightly

---

## Summary: How Questions Help

### Direct Benefits

1. **Resolve Ambiguities**
   - Each answered question removes ambiguity penalties
   - Critical ambiguities resolved → Large confidence boost (+40% weight)
   - Important ambiguities resolved → Moderate boost (+20% weight)

2. **Improve Entity Matching**
   - User selects specific entities → Validated entity IDs
   - More accurate entity matching → Better suggestions
   - Reduces "Entity not found" errors

3. **Enrich Query Context**
   - Original query + answers = Enriched query
   - Enriched query used for:
     - RAG similarity search (find similar successful automations)
     - Better entity extraction
     - More accurate suggestion generation

4. **Increase Answer Quality**
   - Structured answers (multiple choice, entity selection) → Higher confidence
   - Validated answers (entity IDs verified) → Bigger boost
   - High-quality answers (>0.8 confidence) → Additional boost

### Indirect Benefits

1. **Better Suggestions**
   - More context = Better automation suggestions
   - Specific entities = More accurate YAML generation
   - Resolved ambiguities = Fewer edge cases

2. **Higher User Satisfaction**
   - Questions ensure system understands intent
   - Validated answers prevent errors
   - Confidence increases → User trusts suggestions

3. **Historical Learning**
   - Successful Q&A pairs stored in RAG
   - Future similar queries get historical boost
   - System learns from user preferences

---

## Example: Complete Flow with Confidence Tracking

### Query: "Flash the office lights when I get home"

**Initial State:**
- Entities extracted: 3 (office, lights, get home)
- Base confidence: 0.5 + (3 * 0.1) = **0.8** (80%)
- Ambiguities detected:
  - CRITICAL: Which office lights? (6 matches found)
  - IMPORTANT: How to detect "get home"? (presence sensor? location?)
- Confidence after penalties: 0.8 × 0.7 (critical) × 0.85 (important) = **0.476** (47.6%)
- **Decision**: Below 0.85 threshold → Ask questions

**Round 1 - Question 1:**
- Question: "Which office lights should flash?"
- Options: [Office Ceiling, Office Desk, Office Window, All Office Lights]
- User selects: "Office Ceiling Lights"
- Answer validated: ✅ (entity_id: light.office_ceiling, confidence: 0.9)

**Recalculation after Round 1:**
- Remaining ambiguities: 1 IMPORTANT (get home detection)
- Base: 0.8
- Penalties: 0.8 × 0.85 (important) = 0.68
- Critical completion (1/1): (1.0 - 0.68) * 1.0 * 0.4 = +0.128 → 0.808
- Answer quality (0.9 > 0.8): (1.0 - 0.808) * 0.15 = +0.029 → 0.837
- Validation bonus (1 validated): (1.0 - 0.837) * 0.05 = +0.008 → **0.845** (84.5%)
- **Still slightly below threshold → Ask Question 2**

**Round 2 - Question 2:**
- Question: "How should I detect when you get home?"
- Options: [Presence sensor, Phone location, Manual trigger]
- User selects: "Presence sensor"
- Answer validated: ✅ (entity_id: binary_sensor.presence_home, confidence: 0.85)

**Recalculation after Round 2:**
- Remaining ambiguities: 0
- Base: 0.8
- No penalties → 0.8
- Important completion (1/1): (1.0 - 0.8) * 1.0 * 0.2 = +0.04 → 0.84
- Answer quality (avg 0.875 > 0.8): (1.0 - 0.84) * 0.15 = +0.024 → 0.864
- Validation bonus (2 validated): (1.0 - 0.864) * min(0.20, 2 * 0.05) = +0.013 → **0.877** (87.7%)
- **Above threshold (0.85) → Proceed to suggestions**

**Final State:**
- Confidence: **0.877** (87.7%)
- All ambiguities resolved: ✅
- Enriched query: "Flash the Office Ceiling Lights (light.office_ceiling) when presence sensor (binary_sensor.presence_home) detects home"
- **Generate high-quality suggestions** → Better automation YAML

---

## Key Takeaways

1. **Confidence starts with entity extraction** → More entities = higher base confidence
2. **Ambiguities reduce confidence** → Critical (30%) and Important (15%) have significant impact
3. **Questions resolve ambiguities** → Each answer removes penalties and adds boosts
4. **Answer quality matters** → Validated, structured answers provide bigger boosts
5. **Multi-round clarification** → System asks questions until confidence ≥ 0.85 or max rounds reached
6. **Threshold: 0.85 (85%)** → System needs high confidence before generating suggestions
7. **Historical learning** → Similar successful queries boost confidence via RAG

---

## Configuration

### Adjustable Parameters

- **Confidence Threshold**: Default 0.85 (can be customized per session)
- **Max Clarification Rounds**: Default 3 (prevents endless questioning)
- **Ambiguity Penalties**: Hardcoded but could be configurable
- **Answer Quality Weights**: Hardcoded (critical: 40%, important: 20%)

### Current Settings

```python
# services/ai-automation-service/src/services/clarification/confidence_calculator.py
default_threshold = 0.85  # 85% required
max_boost = 0.20  # 20% max historical boost
critical_completion_weight = 0.4  # 40% weight for critical completion
important_completion_weight = 0.2  # 20% weight for important completion
```

---

## Code References

- **Confidence Calculator**: `services/ai-automation-service/src/services/clarification/confidence_calculator.py`
- **Ambiguity Detector**: `services/ai-automation-service/src/services/clarification/detector.py`
- **Question Generator**: `services/ai-automation-service/src/services/clarification/question_generator.py`
- **Answer Validator**: `services/ai-automation-service/src/services/clarification/answer_validator.py`
- **Main Flow**: `services/ai-automation-service/src/api/ask_ai_router.py` (lines 4633-5493)

