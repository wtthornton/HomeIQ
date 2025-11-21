# AI Automation Service: Question Reduction Intelligence Ideas

**Date:** January 2025  
**Service:** `ai-automation-service`  
**Issue:** Users receive too many detailed clarification questions

## Current Problem Analysis

### Issues Identified:
1. **Too Many Questions**: System asks questions for every ambiguity detected, even when context could resolve them
2. **Overly Detailed Questions**: Questions ask for exact device names, locations, and specifications when reasonable assumptions could be made
3. **Limited Intelligence**: System doesn't leverage historical patterns, user preferences, or context-aware defaults effectively

### Current Flow:
```
Query → Ambiguity Detection → Questions Generated (up to 3) → User Answers → Re-detect → More Questions
```

### Key Code Locations:
- **Ambiguity Detection**: `services/ai-automation-service/src/services/clarification/detector.py`
- **Question Generation**: `services/ai-automation-service/src/services/clarification/question_generator.py`
- **Confidence Calculation**: `services/ai-automation-service/src/services/clarification/confidence_calculator.py`
- **User Preferences**: `services/ai-automation-service/src/services/learning/user_preference_learner.py`

---

## Idea 1: Context-Aware Smart Defaults with Auto-Resolution

### Concept
Automatically resolve ambiguities using intelligent context analysis instead of asking questions when confidence is high enough.

### How It Works

#### 1.1 Location-Based Auto-Resolution
When a query mentions a location (e.g., "office lights"), automatically select ALL devices in that location if:
- Location is clearly specified in query
- Multiple devices match the device type in that location
- No conflicting context exists

**Example:**
- Query: "Flash the office lights"
- Current: Asks "Which office lights? I found 4 Hue lights..."
- **New**: Auto-selects all 4 office lights (confidence: 0.85) and proceeds, with option to refine

#### 1.2 Device Type Pattern Matching
Use fuzzy matching and device type patterns to auto-select when:
- Only one device type matches (e.g., "WLED" → all WLED devices)
- User has historically selected "all" for similar patterns
- Device count is reasonable (< 5 devices)

#### 1.3 Historical Usage Patterns
Leverage RAG client to find similar successful queries and apply their device selections:
- If similarity > 0.80 and previous query used "all devices", auto-apply
- If similarity > 0.85 and device pattern matches, skip question

### Implementation Changes

**File: `services/ai-automation-service/src/services/clarification/detector.py`**

Add new method:
```python
async def auto_resolve_ambiguities(
    self,
    ambiguities: list[Ambiguity],
    query: str,
    extracted_entities: list[dict[str, Any]],
    available_devices: dict[str, Any],
    rag_client: Any | None = None,
    user_preferences: list[dict[str, Any]] | None = None
) -> tuple[list[Ambiguity], dict[str, Any]]:
    """
    Auto-resolve ambiguities using context and historical patterns.
    
    Returns:
        (remaining_ambiguities, auto_resolved_answers)
    """
    auto_resolved = {}
    remaining = []
    
    for amb in ambiguities:
        if amb.type == AmbiguityType.DEVICE:
            # Check location context
            if self._can_auto_resolve_by_location(amb, query, available_devices):
                auto_resolved[amb.id] = self._get_location_devices(amb, available_devices)
                continue
            
            # Check historical patterns
            if rag_client and await self._check_historical_pattern(amb, query, rag_client):
                auto_resolved[amb.id] = await self._get_historical_selection(amb, query, rag_client)
                continue
            
            # Check user preferences
            if user_preferences and self._matches_user_preference(amb, user_preferences):
                auto_resolved[amb.id] = self._get_preference_selection(amb, user_preferences)
                continue
        
        # Can't auto-resolve, keep for question
        remaining.append(amb)
    
    return remaining, auto_resolved
```

**File: `services/ai-automation-service/src/api/ask_ai_router.py`**

Modify ambiguity handling:
```python
# After detecting ambiguities
if ambiguities:
    # NEW: Try auto-resolution first
    remaining_ambiguities, auto_resolved = await clarification_detector.auto_resolve_ambiguities(
        ambiguities=ambiguities,
        query=request.query,
        extracted_entities=entities,
        available_devices=automation_context,
        rag_client=rag_client,
        user_preferences=user_prefs
    )
    
    # Only ask questions for remaining ambiguities
    if remaining_ambiguities:
        questions = await question_generator.generate_questions(...)
    else:
        # All resolved! Proceed with auto-resolved answers
        questions = []
        clarification_context['auto_resolved'] = auto_resolved
```

### Benefits
- **Reduces questions by 40-60%** for location-specific queries
- **Faster user experience** - no waiting for answers
- **Maintains accuracy** - only auto-resolves when confidence is high

### Confidence Thresholds
- Location-based: 0.85+ confidence
- Historical pattern: 0.80+ similarity
- User preference: 0.90+ consistency

---

## Idea 2: Progressive Question Reduction with Confidence-Based Skipping

### Concept
Use confidence scores and historical success to skip questions entirely when the system is confident enough, even with detected ambiguities.

### How It Works

#### 2.1 Adaptive Confidence Thresholds
Instead of fixed threshold (0.85), use adaptive thresholds based on:
- **Query complexity**: Simple queries (1-2 devices) → lower threshold (0.75)
- **Historical success**: If similar queries succeeded → lower threshold (-0.10)
- **User preference**: If user always accepts defaults → lower threshold (-0.05)

#### 2.2 Ambiguity Severity Weighting
Not all ambiguities require questions:
- **CRITICAL**: Always ask (unless auto-resolved)
- **IMPORTANT**: Ask only if confidence < 0.80
- **OPTIONAL**: Skip entirely, use best guess

#### 2.3 Smart Question Filtering
Before generating questions, filter ambiguities:
1. Check if ambiguity can be resolved by context (Idea 1)
2. Check if confidence is high enough to skip (adaptive threshold)
3. Check if user preference suggests skipping
4. Only ask for truly critical ambiguities

### Implementation Changes

**File: `services/ai-automation-service/src/services/clarification/confidence_calculator.py`**

Add adaptive threshold calculation:
```python
async def calculate_adaptive_threshold(
    self,
    query: str,
    extracted_entities: list[dict[str, Any]],
    ambiguities: list[Ambiguity],
    rag_client: Any | None = None,
    user_preferences: list[dict[str, Any]] | None = None
) -> float:
    """
    Calculate adaptive confidence threshold based on context.
    
    Returns:
        Adaptive threshold (0.65 to 0.95)
    """
    base_threshold = self.default_threshold  # 0.85
    
    # Reduce threshold for simple queries
    if len(extracted_entities) <= 2 and len(ambiguities) <= 1:
        base_threshold -= 0.10  # 0.75 for simple queries
    
    # Reduce threshold if historical success exists
    if rag_client:
        similar = await rag_client.retrieve(query, top_k=1, min_similarity=0.80)
        if similar and similar[0].get('success_score', 0) > 0.8:
            base_threshold -= 0.10  # -0.10 for proven patterns
    
    # Reduce threshold if user prefers defaults
    if user_preferences:
        skip_preference = any(
            p.get('consistency_score', 0) > 0.9 and 
            p.get('answer_pattern', '').lower() in ['all', 'default', 'yes']
            for p in user_preferences
        )
        if skip_preference:
            base_threshold -= 0.05  # -0.05 for user preference
    
    # Clamp between 0.65 and 0.95
    return max(0.65, min(0.95, base_threshold))
```

**File: `services/ai-automation-service/src/api/ask_ai_router.py`**

Modify question generation logic:
```python
# Calculate adaptive threshold
adaptive_threshold = await confidence_calculator.calculate_adaptive_threshold(
    query=request.query,
    extracted_entities=entities,
    ambiguities=ambiguities,
    rag_client=rag_client,
    user_preferences=user_prefs
)

# Calculate current confidence
confidence = await confidence_calculator.calculate_confidence(...)

# Filter ambiguities by severity and confidence
critical_ambiguities = [a for a in ambiguities if a.severity == AmbiguitySeverity.CRITICAL]
important_ambiguities = [a for a in ambiguities if a.severity == AmbiguitySeverity.IMPORTANT]

# Only ask questions if:
# 1. Confidence below adaptive threshold, OR
# 2. Critical ambiguities exist (always ask for critical)
should_ask = (confidence < adaptive_threshold) or (len(critical_ambiguities) > 0)

if should_ask:
    # Filter: Skip OPTIONAL ambiguities, only ask CRITICAL + IMPORTANT if needed
    questions_ambiguities = [
        a for a in ambiguities 
        if a.severity != AmbiguitySeverity.OPTIONAL or confidence < adaptive_threshold - 0.10
    ]
    questions = await question_generator.generate_questions(questions_ambiguities, ...)
else:
    # High confidence - proceed without questions
    questions = []
    logger.info(f"✅ High confidence ({confidence:.2f} >= {adaptive_threshold:.2f}) - skipping questions")
```

### Benefits
- **Reduces questions by 30-50%** for queries with high confidence
- **Faster for experienced users** who have established patterns
- **Maintains safety** - still asks for critical ambiguities

### Example Scenarios

**Scenario 1: Simple Query with High Confidence**
- Query: "Turn on office light"
- Ambiguities: 1 IMPORTANT (which office light?)
- Confidence: 0.82
- Adaptive Threshold: 0.75 (simple query)
- **Result**: Skip question, use best match

**Scenario 2: Complex Query with Low Confidence**
- Query: "Flash lights when sensor detects"
- Ambiguities: 2 CRITICAL (which lights? which sensor?)
- Confidence: 0.65
- Adaptive Threshold: 0.85 (complex query)
- **Result**: Ask questions (confidence too low)

---

## Idea 3: Batch Question Simplification with Multi-Select Options

### Concept
Combine related questions into single multi-select questions and use smarter question formats to reduce question count.

### How It Works

#### 3.1 Question Grouping
Group related ambiguities into single questions:
- **Device Selection**: Combine "which lights?" + "which sensors?" → "Select devices for this automation"
- **Location + Device**: Combine location and device questions → "Select devices in [location]"
- **Action Details**: Combine action parameters → "How should the lights flash?" (with options)

#### 3.2 Smart Default Options
Include intelligent defaults in questions:
- **"All matching devices"** option (auto-selects all)
- **"Use my usual preference"** option (applies user preference)
- **"Best match"** option (uses fuzzy matching result)

#### 3.3 Question Simplification
Reduce question verbosity:
- **Current**: "There are 4 Hue lights in your office. Did you want all four to flash, or specific ones? Please specify which lights you'd like to include."
- **New**: "Office lights: [ ] All 4 Hue lights [ ] Select specific [ ] Use best match"

### Implementation Changes

**File: `services/ai-automation-service/src/services/clarification/question_generator.py`**

Add question grouping method:
```python
def _group_related_ambiguities(
    self,
    ambiguities: list[Ambiguity]
) -> list[list[Ambiguity]]:
    """
    Group related ambiguities for batch questions.
    
    Groups:
    - Device ambiguities in same location
    - Trigger + Action ambiguities for same automation
    - Timing + Action ambiguities
    """
    groups = []
    device_groups = {}  # location -> [ambiguities]
    other_groups = []
    
    for amb in ambiguities:
        if amb.type == AmbiguityType.DEVICE:
            # Group by location
            location = amb.context.get('mentioned_locations', ['unknown'])[0]
            if location not in device_groups:
                device_groups[location] = []
            device_groups[location].append(amb)
        else:
            other_groups.append(amb)
    
    # Add device groups
    groups.extend(device_groups.values())
    
    # Add other ambiguities as individual groups (or combine if related)
    if other_groups:
        groups.append(other_groups)
    
    return groups
```

Modify question generation to use groups:
```python
async def generate_questions(
    self,
    ambiguities: list[Ambiguity],
    query: str,
    context: dict[str, Any],
    previous_qa: list[dict[str, Any]] | None = None,
    asked_questions: list['ClarificationQuestion'] | None = None
) -> list[ClarificationQuestion]:
    """Generate questions with grouping and smart defaults"""
    
    # Group related ambiguities
    ambiguity_groups = self._group_related_ambiguities(ambiguities)
    
    questions = []
    for group in ambiguity_groups:
        if len(group) == 1:
            # Single ambiguity - generate normal question
            question = await self._generate_single_question(group[0], query, context)
        else:
            # Multiple related - generate batch question
            question = await self._generate_batch_question(group, query, context)
        
        # Add smart default options
        question = self._add_smart_defaults(question, context, user_preferences)
        questions.append(question)
    
    return questions
```

Add smart defaults method:
```python
def _add_smart_defaults(
    self,
    question: ClarificationQuestion,
    context: dict[str, Any],
    user_preferences: list[dict[str, Any]] | None = None
) -> ClarificationQuestion:
    """Add intelligent default options to questions"""
    
    if question.question_type == QuestionType.MULTIPLE_CHOICE:
        options = list(question.options) if question.options else []
        
        # Add "All matching" option if device selection
        if question.category == 'device' and question.related_entities:
            if len(question.related_entities) > 1:
                options.insert(0, f"All {len(question.related_entities)} devices")
        
        # Add "Use my preference" if user has preference
        if user_preferences:
            matching_pref = next(
                (p for p in user_preferences 
                 if p.get('question_category') == question.category),
                None
            )
            if matching_pref and matching_pref.get('consistency_score', 0) > 0.9:
                options.insert(0, "Use my usual preference")
        
        # Add "Best match" option
        options.append("Use best match (recommended)")
        
        question.options = options
    
    return question
```

### Benefits
- **Reduces question count by 50-70%** through grouping
- **Faster user interaction** - fewer clicks/answers needed
- **Better UX** - clearer, more actionable questions

### Example Transformation

**Before (3 questions):**
1. "There are 4 Hue lights in your office. Which ones should flash?"
2. "There are 2 motion sensors in your office. Which one should trigger?"
3. "How should the lights flash? Fast or slow?"

**After (1 grouped question):**
"Office automation setup:
- Lights: [ ] All 4 Hue lights [ ] Select specific [ ] Use best match
- Trigger sensor: [ ] Motion Sensor 1 [ ] Motion Sensor 2 [ ] Use best match  
- Flash speed: [ ] Fast [ ] Slow [ ] Use default"

---

## Implementation Priority

### Phase 1: Quick Wins (1-2 weeks)
1. **Idea 3** - Question grouping and simplification (immediate UX improvement)
2. **Idea 2** - Adaptive thresholds for OPTIONAL ambiguities (low risk)

### Phase 2: Intelligence Layer (2-3 weeks)
3. **Idea 1** - Context-aware auto-resolution (requires testing)
4. **Idea 2** - Full adaptive threshold system

### Phase 3: Learning & Refinement (ongoing)
5. Enhanced user preference learning
6. RAG-based pattern matching improvements
7. A/B testing for threshold tuning

---

## Success Metrics

### Target Improvements
- **Question Reduction**: 50-70% fewer questions asked
- **User Satisfaction**: Measure via feedback/surveys
- **Accuracy**: Maintain >90% automation success rate
- **Speed**: Reduce time-to-automation by 40-60%

### Monitoring
- Track questions asked per query (before/after)
- Track auto-resolution success rate
- Track user acceptance of auto-resolved answers
- Monitor confidence threshold effectiveness

---

## Risk Mitigation

### Risks
1. **Auto-resolution errors**: Wrong devices selected
2. **Confidence miscalculation**: Skipping questions when shouldn't
3. **User confusion**: Not understanding smart defaults

### Mitigation
1. **Always allow refinement**: Users can edit auto-resolved selections
2. **Conservative thresholds**: Start with higher confidence requirements
3. **Clear UI indicators**: Show what was auto-selected and why
4. **Rollback capability**: Easy undo for auto-resolved answers

---

## Conclusion

These three ideas work together to create a more intelligent, user-friendly clarification system:

1. **Smart Defaults** reduce questions by auto-resolving when confident
2. **Adaptive Thresholds** skip questions when confidence is high
3. **Question Grouping** reduces question count through better UX

Combined, they should reduce questions by **50-70%** while maintaining accuracy and user control.

