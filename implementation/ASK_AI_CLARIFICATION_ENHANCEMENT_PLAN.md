# Ask AI Clarification Enhancement - Detailed Implementation Plan

**Created:** December 19, 2025  
**Status:** Planning  
**Epic:** AI Automation Enhancement  
**Story:** ASK-AI-CLARIFY-1 - Conversational Clarification System

---

## 🎯 Executive Summary

Enhance the Ask AI interface (`http://localhost:3001/ask-ai`) to implement a **conversational clarification system** that:

1. **Reviews** natural language automation requests
2. **Generates intelligent clarifying questions** based on detected ambiguities
3. **Engages in Q&A** until confidence threshold is met
4. **Creates suggestions** with full conversation history (prompt, questions, answers)

### Example Flow

**User Input:**
```
"When the presents sensor triggers at my desk flash office lights for 15 secs - Flash them fast and multi-color then return them to their original attributes. Also make the office led show fireworks for 30 secs."
```

**System Response (Clarification Mode):**
```
I found some ambiguities in your request. Let me clarify:

1. There are 4 Hue lights and 1 WLED LED light in your office. Did you want all four lights to flash at the same time, or just specific ones?

2. I couldn't find a "presents sensor" - did you mean:
   - Presence sensor (motion/presence detection)?
   - If so, which sensor? (I found: binary_sensor.desk_presence, binary_sensor.office_motion)

3. For the WLED LED strip fireworks effect - should this start at the same time as the light flash, or run independently?

Please answer these questions so I can create the automation accurately.
```

**After User Answers:**
```
Great! Based on your answers, I'll create an automation that:
- Triggers when binary_sensor.desk_presence becomes 'on'
- Flashes all 4 Hue lights in multi-color pattern for 15 seconds
- Returns lights to original state
- Shows fireworks on WLED strip for 30 seconds

Confidence: 92% - Ready to create suggestion!
```

---

## 📋 Current State Analysis

### Existing Implementation

**Frontend (`services/ai-automation-ui/src/pages/AskAI.tsx`):**
- ✅ Chat-based interface
- ✅ Conversation history tracking
- ✅ Suggestion display with refine/approve actions
- ✅ Basic follow-up prompts (generated client-side)
- ❌ No structured clarification Q&A flow
- ❌ No confidence-based decision making for clarification

**Backend (`services/ai-automation-service/src/api/ask_ai_router.py`):**
- ✅ `/api/v1/ask-ai/query` endpoint
- ✅ Entity extraction with confidence scoring
- ✅ Basic `clarification_needed` field in responses
- ✅ `/api/nl/clarify/{suggestion_id}` endpoint for follow-up
- ❌ No structured question generation
- ❌ No confidence threshold logic for clarification
- ❌ No Q&A conversation tracking

**NL Generator (`services/ai-automation-service/src/nl_automation_generator.py`):**
- ✅ `clarification_needed` field in prompt
- ✅ Confidence calculation (reduces if clarification needed)
- ✅ `regenerate_with_clarification()` method
- ❌ Single clarification question only
- ❌ No structured question format
- ❌ No multi-round Q&A support

### Gaps Identified

1. **No structured question generation** - Questions are free-form text in `clarification` field
2. **No confidence threshold** - System doesn't decide when to ask vs. proceed
3. **No multi-round Q&A** - Only one clarification round supported
4. **No question categorization** - Questions not categorized (device, trigger, action, etc.)
5. **No answer validation** - Answers not validated against system capabilities
6. **No conversation history storage** - Q&A not stored with suggestions

---

## 🏗️ Architecture Design

### High-Level Flow

```
User Query
    ↓
1. Parse & Extract Entities (existing)
    ↓
2. Detect Ambiguities (NEW)
    ↓
3. Calculate Confidence (enhanced)
    ↓
4. Decision Point: Confidence < Threshold?
    ├─ YES → Generate Clarification Questions (NEW)
    │   ↓
    │   Present Questions to User
    │   ↓
    │   Wait for Answers
    │   ↓
    │   Incorporate Answers into Context
    │   ↓
    │   Recalculate Confidence
    │   ↓
    │   Loop back to Decision Point
    │
    └─ NO → Generate Suggestion (existing)
        ↓
        Store Suggestion with Full Conversation History
```

### Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (AskAI.tsx)                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  ClarificationDialog Component (NEW)                 │  │
│  │  - Displays questions in structured format          │  │
│  │  - Collects answers with validation                 │  │
│  │  - Shows confidence meter                           │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↕
┌─────────────────────────────────────────────────────────────┐
│              Backend API (ask_ai_router.py)                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  POST /api/v1/ask-ai/query                          │  │
│  │  - Enhanced with clarification detection            │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  POST /api/v1/ask-ai/clarify                        │  │
│  │  - NEW: Multi-round clarification support           │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↕
┌─────────────────────────────────────────────────────────────┐
│         Clarification Service (NEW)                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  ClarificationDetector                               │  │
│  │  - Detects ambiguities in query                     │  │
│  │  - Categorizes ambiguity types                      │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  QuestionGenerator                                   │  │
│  │  - Generates structured questions                   │  │
│  │  - Uses OpenAI for intelligent question generation  │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  AnswerValidator                                     │  │
│  │  - Validates answers against system capabilities    │  │
│  │  - Checks entity availability                       │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  ConfidenceCalculator                                │  │
│  │  - Enhanced confidence calculation                  │  │
│  │  - Considers Q&A completeness                       │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↕
┌─────────────────────────────────────────────────────────────┐
│         NL Automation Generator (enhanced)                   │
│  - Incorporates clarification answers into prompt           │
│  - Generates suggestions with full context                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 📐 Detailed Design

### 1. Data Models

#### ClarificationQuestion (NEW)

```python
@dataclass
class ClarificationQuestion:
    """Structured clarification question"""
    id: str  # Unique question ID
    category: str  # 'device', 'trigger', 'action', 'timing', 'condition'
    question_text: str  # Human-readable question
    question_type: str  # 'multiple_choice', 'text', 'entity_selection', 'boolean'
    options: Optional[List[str]] = None  # For multiple choice
    context: Dict[str, Any]  # Additional context (detected entities, etc.)
    priority: int  # 1=critical, 2=important, 3=optional
    related_entities: Optional[List[str]] = None  # Entity IDs mentioned
```

#### ClarificationAnswer (NEW)

```python
@dataclass
class ClarificationAnswer:
    """User's answer to a clarification question"""
    question_id: str
    answer_text: str
    selected_entities: Optional[List[str]] = None  # For entity selection
    confidence: float  # How confident we are in interpreting the answer
    validated: bool = False  # Whether answer was validated
```

#### ClarificationSession (NEW)

```python
@dataclass
class ClarificationSession:
    """Multi-round clarification conversation"""
    session_id: str
    original_query: str
    questions: List[ClarificationQuestion]
    answers: List[ClarificationAnswer]
    current_confidence: float
    confidence_threshold: float = 0.85  # Default threshold
    rounds_completed: int = 0
    max_rounds: int = 3  # Maximum clarification rounds
    status: str  # 'in_progress', 'complete', 'abandoned'
```

#### Enhanced AskAIQueryResponse

```python
class AskAIQueryResponse(BaseModel):
    """Enhanced response with clarification support"""
    query_id: str
    original_query: str
    parsed_intent: str
    extracted_entities: List[Dict[str, Any]]
    suggestions: List[Dict[str, Any]]  # Empty if clarification needed
    confidence: float
    processing_time_ms: int
    created_at: str
    
    # NEW: Clarification fields
    clarification_needed: bool = False
    clarification_session: Optional[ClarificationSession] = None
    questions: Optional[List[ClarificationQuestion]] = None
    message: str  # User-friendly message explaining status
```

### 2. Clarification Detection Logic

#### Ambiguity Types

1. **Device Ambiguity**
   - Multiple devices match query (e.g., "office lights" when there are 4 Hue lights)
   - Device not found (e.g., "presents sensor" doesn't exist)
   - Generic device reference (e.g., "the light" without context)

2. **Trigger Ambiguity**
   - Sensor not found
   - Multiple sensors match
   - Timing unclear (e.g., "when I arrive" vs specific time)

3. **Action Ambiguity**
   - Multiple actions possible (e.g., "flash" could mean different patterns)
   - Action parameters unclear (e.g., "fast" - how fast?)
   - Capability mismatch (e.g., device doesn't support requested feature)

4. **Timing Ambiguity**
   - Duration unclear
   - Sequence unclear (simultaneous vs sequential)
   - Timing constraints missing

5. **Condition Ambiguity**
   - Conditions not specified
   - Multiple condition options

#### Detection Algorithm

```python
class ClarificationDetector:
    """Detects ambiguities in automation requests"""
    
    async def detect_ambiguities(
        self,
        query: str,
        extracted_entities: List[Dict],
        available_devices: Dict,
        automation_context: Dict
    ) -> List[Ambiguity]:
        """
        Detect ambiguities in query.
        
        Returns:
            List of Ambiguity objects with type, severity, and context
        """
        ambiguities = []
        
        # 1. Check device references
        device_ambiguities = await self._detect_device_ambiguities(
            query, extracted_entities, available_devices
        )
        ambiguities.extend(device_ambiguities)
        
        # 2. Check trigger references
        trigger_ambiguities = await self._detect_trigger_ambiguities(
            query, extracted_entities, automation_context
        )
        ambiguities.extend(trigger_ambiguities)
        
        # 3. Check action clarity
        action_ambiguities = await self._detect_action_ambiguities(
            query, extracted_entities, automation_context
        )
        ambiguities.extend(action_ambiguities)
        
        # 4. Check timing clarity
        timing_ambiguities = self._detect_timing_ambiguities(query)
        ambiguities.extend(timing_ambiguities)
        
        return ambiguities
```

### 3. Question Generation

#### Question Generation Strategy

**Use OpenAI GPT-4o-mini** to generate intelligent, contextual questions:

```python
class QuestionGenerator:
    """Generates structured clarification questions"""
    
    async def generate_questions(
        self,
        ambiguities: List[Ambiguity],
        query: str,
        context: Dict
    ) -> List[ClarificationQuestion]:
        """
        Generate questions based on detected ambiguities.
        
        Uses OpenAI to create natural, contextual questions.
        """
        prompt = self._build_question_generation_prompt(
            ambiguities, query, context
        )
        
        response = await self.openai_client.generate(
            prompt=prompt,
            temperature=0.3,  # Low temperature for consistent questions
            response_format={"type": "json_object"}
        )
        
        questions = self._parse_questions(response)
        return questions
```

#### Question Generation Prompt Template

```
You are a Home Assistant automation assistant helping users clarify their automation requests.

**User Query:**
"{query}"

**Detected Ambiguities:**
{ambiguities_json}

**Available Devices:**
{devices_summary}

**Task:**
Generate 1-3 clarification questions that will help clarify the ambiguities above.

**Guidelines:**
1. Ask ONE question per ambiguity (prioritize critical ambiguities)
2. Use natural, conversational language
3. Provide helpful context (e.g., "I found 4 Hue lights - which ones?")
4. Offer suggestions when possible (e.g., "Did you mean: presence sensor or motion sensor?")
5. Be specific but concise

**Output Format (JSON):**
{
  "questions": [
    {
      "id": "q1",
      "category": "device",
      "question_text": "There are 4 Hue lights in your office. Did you want all four to flash, or specific ones?",
      "question_type": "multiple_choice",
      "options": ["All four lights", "Only specific lights (please specify)", "Just the main light"],
      "priority": 1,
      "related_entities": ["light.office_hue_1", "light.office_hue_2", ...]
    }
  ]
}
```

### 4. Confidence Calculation Enhancement

```python
class ConfidenceCalculator:
    """Enhanced confidence calculation with clarification support"""
    
    def calculate_confidence(
        self,
        query: str,
        extracted_entities: List[Dict],
        ambiguities: List[Ambiguity],
        clarification_answers: Optional[List[ClarificationAnswer]] = None,
        base_confidence: float = 0.75
    ) -> float:
        """
        Calculate confidence score.
        
        Factors:
        - Base confidence (from entity extraction)
        - Ambiguity severity (reduces confidence)
        - Clarification completeness (increases confidence)
        - Answer quality (validated answers increase confidence)
        """
        confidence = base_confidence
        
        # Reduce for ambiguities
        for ambiguity in ambiguities:
            if ambiguity.severity == 'critical':
                confidence *= 0.7
            elif ambiguity.severity == 'important':
                confidence *= 0.85
            elif ambiguity.severity == 'optional':
                confidence *= 0.95
        
        # Increase for complete clarifications
        if clarification_answers:
            answered_critical = sum(
                1 for a in clarification_answers 
                if a.question.priority == 1 and a.validated
            )
            total_critical = sum(
                1 for a in ambiguities 
                if a.severity == 'critical'
            )
            
            if total_critical > 0:
                completion_rate = answered_critical / total_critical
                confidence += (1.0 - confidence) * completion_rate * 0.3
        
        return min(1.0, max(0.0, confidence))
```

### 5. API Endpoints

#### Enhanced POST /api/v1/ask-ai/query

**Request:**
```json
{
  "query": "When the presents sensor triggers at my desk flash office lights...",
  "conversation_history": [...],
  "clarification_session_id": null  // NEW: For continuing existing session
}
```

**Response (Clarification Needed):**
```json
{
  "query_id": "ask-ai-abc123",
  "original_query": "...",
  "confidence": 0.65,
  "clarification_needed": true,
  "message": "I found some ambiguities. Please answer these questions:",
  "questions": [
    {
      "id": "q1",
      "category": "device",
      "question_text": "There are 4 Hue lights and 1 WLED LED light in your office. Did you want all four lights to flash at the same time?",
      "question_type": "multiple_choice",
      "options": ["All four lights", "Only specific lights", "Just the WLED"],
      "priority": 1
    },
    {
      "id": "q2",
      "category": "trigger",
      "question_text": "I couldn't find a 'presents sensor'. Did you mean a presence sensor? I found: binary_sensor.desk_presence, binary_sensor.office_motion",
      "question_type": "entity_selection",
      "options": ["binary_sensor.desk_presence", "binary_sensor.office_motion", "Other (please specify)"],
      "priority": 1
    }
  ],
  "suggestions": [],  // Empty until clarification complete
  "clarification_session": {
    "session_id": "clarify-xyz789",
    "confidence_threshold": 0.85,
    "current_confidence": 0.65,
    "rounds_completed": 0
  }
}
```

#### NEW: POST /api/v1/ask-ai/clarify

**Request:**
```json
{
  "session_id": "clarify-xyz789",
  "answers": [
    {
      "question_id": "q1",
      "answer_text": "All four lights",
      "selected_entities": null
    },
    {
      "question_id": "q2",
      "answer_text": "binary_sensor.desk_presence",
      "selected_entities": ["binary_sensor.desk_presence"]
    }
  ]
}
```

**Response:**
```json
{
  "session_id": "clarify-xyz789",
  "confidence": 0.92,
  "confidence_threshold": 0.85,
  "clarification_complete": true,
  "message": "Great! Based on your answers, I'll create the automation.",
  "suggestions": [
    {
      "suggestion_id": "sug-123",
      "description": "Flash all 4 office Hue lights when desk presence sensor triggers...",
      "confidence": 0.92,
      "automation_yaml": "...",
      "conversation_history": {
        "original_query": "...",
        "questions": [...],
        "answers": [...]
      }
    }
  ]
}
```

### 6. Frontend Components

#### ClarificationDialog Component (NEW)

```typescript
interface ClarificationDialogProps {
  questions: ClarificationQuestion[];
  sessionId: string;
  currentConfidence: number;
  confidenceThreshold: number;
  onAnswer: (answers: ClarificationAnswer[]) => Promise<void>;
  onCancel: () => void;
}

const ClarificationDialog: React.FC<ClarificationDialogProps> = ({
  questions,
  sessionId,
  currentConfidence,
  confidenceThreshold,
  onAnswer,
  onCancel
}) => {
  // Component implementation
  // - Displays questions in structured format
  // - Shows confidence meter
  // - Collects answers
  // - Validates answers client-side
  // - Submits answers to backend
};
```

#### Enhanced AskAI Component

- Integrates ClarificationDialog
- Shows confidence meter during clarification
- Displays conversation history including Q&A
- Handles multi-round clarification flow

---

## 🔧 Implementation Steps

### Phase 1: Backend Foundation (Week 1)

1. **Create Clarification Service**
   - `services/ai-automation-service/src/services/clarification/`
   - `clarification_detector.py` - Ambiguity detection
   - `question_generator.py` - Question generation
   - `answer_validator.py` - Answer validation
   - `confidence_calculator.py` - Enhanced confidence calculation

2. **Data Models**
   - Add Pydantic models for ClarificationQuestion, ClarificationAnswer, ClarificationSession
   - Update database schema (if needed) for storing clarification sessions

3. **Enhanced API Endpoints**
   - Update `POST /api/v1/ask-ai/query` with clarification detection
   - Create `POST /api/v1/ask-ai/clarify` for multi-round clarification

### Phase 2: Question Generation (Week 1-2)

1. **OpenAI Integration**
   - Create question generation prompt templates
   - Implement question parsing and validation
   - Test with various ambiguity types

2. **Answer Validation**
   - Validate entity selections against available entities
   - Check capability matches
   - Provide helpful error messages

### Phase 3: Frontend Integration (Week 2)

1. **ClarificationDialog Component**
   - Create component with question display
   - Implement answer collection
   - Add confidence meter
   - Handle different question types

2. **Enhanced AskAI Page**
   - Integrate ClarificationDialog
   - Update message flow to show clarification questions
   - Display conversation history with Q&A

### Phase 4: Testing & Refinement (Week 2-3)

1. **Unit Tests**
   - Test ambiguity detection
   - Test question generation
   - Test answer validation
   - Test confidence calculation

2. **Integration Tests**
   - Test full clarification flow
   - Test multi-round clarification
   - Test edge cases (no answers, invalid answers)

3. **User Testing**
   - Test with real user queries
   - Refine question generation based on feedback
   - Adjust confidence thresholds

---

## 📊 Success Metrics

1. **Clarification Rate**: % of queries requiring clarification (target: 30-40%)
2. **Question Quality**: User satisfaction with questions (target: 4.0/5.0)
3. **Completion Rate**: % of clarification sessions completed (target: >80%)
4. **Confidence Improvement**: Avg confidence increase after clarification (target: +0.15)
5. **Suggestion Quality**: % of suggestions approved after clarification (target: >85%)

---

## 🔍 Research Findings

### Context7 KB Patterns

Based on Context7 KB research, best practices for conversational AI clarification:

1. **Structured Questions**: Use structured formats (multiple choice, entity selection) for better answer parsing
2. **Contextual Questions**: Include detected entities/options in questions
3. **Progressive Disclosure**: Ask critical questions first, optional ones later
4. **Confidence Thresholds**: Use 0.85 as default threshold for proceeding
5. **Multi-round Support**: Support up to 3 rounds of clarification

### Web/GitHub Examples

1. **Home Assistant Conversation API**: Uses structured intents with slots for clarification
2. **SAGE (Smart Home Agent)**: Uses LLM-based clarification with confidence scoring
3. **Harmony**: Uses locally deployed LLMs for privacy-aware clarification

---

## 🚀 Next Steps

1. **Review with Context7**: Use `*context7-docs` to check OpenAI GPT-4o-mini best practices for question generation
2. **Prototype**: Create minimal prototype of clarification flow
3. **User Testing**: Test with real queries like the example provided
4. **Iterate**: Refine based on feedback

---

## 📝 Notes

- **Confidence Threshold**: Default 0.85, configurable per user/system
- **Max Rounds**: Limit to 3 rounds to avoid frustration
- **Fallback**: If clarification fails, generate best-effort suggestion with warnings
- **Storage**: Store full conversation history with suggestions for audit/debugging

---

**Status**: Ready for review and Context7 validation

---

## ✅ Context7 Validation

### Temperature Settings (Validated from Codebase)

Based on codebase analysis, recommended temperature settings:

- **Question Generation**: `temperature=0.3` (consistent with YAML generation)
  - Natural enough for conversational questions
  - Consistent enough for structured output
  - Matches existing `nl_automation_generator.py` pattern

- **Answer Validation/Interpretation**: `temperature=0.2` (low for deterministic parsing)
  - Ensures consistent answer interpretation
  - Matches existing entity extraction patterns

- **Final Suggestion Generation**: `temperature=0.3` (consistent with existing NL generation)
  - Maintains consistency with current implementation

### JSON Response Format

Use `response_format={"type": "json_object"}` for structured outputs:
- Question generation responses
- Clarification session state
- Answer validation results

### Token Budgets

Based on existing patterns:
- **Question Generation**: `max_tokens=400` (questions are concise)
- **Answer Validation**: `max_tokens=200` (validation is brief)
- **Enhanced Prompt**: ~500-800 tokens (includes context)

### Cost Estimation

Per clarification session:
- **Initial Query + Detection**: ~$0.0001 (existing)
- **Question Generation**: ~$0.00005 (1 OpenAI call)
- **Answer Validation**: ~$0.00003 (1 OpenAI call)
- **Final Generation**: ~$0.0001 (existing)

**Total per clarification session**: ~$0.00028 (~$0.28 per 1000 sessions)

---

## 📚 References

1. **Existing Codebase Patterns**:
   - `services/ai-automation-service/src/nl_automation_generator.py` - NL generation pattern
   - `services/ai-automation-service/src/api/ask_ai_router.py` - Query processing
   - `services/ai-automation-service/src/llm/openai_client.py` - OpenAI client patterns

2. **Architecture Documentation**:
   - `docs/architecture/ai-automation-suggestion-call-tree.md` - System architecture
   - `implementation/analysis/AI_AUTOMATION_CALL_TREE_INDEX.md` - Complete call tree

3. **Research Sources**:
   - Web search: Conversational AI clarification patterns
   - Web search: Home Assistant automation clarification
   - GitHub: SAGE, Harmony frameworks

---

**Status**: ✅ **READY FOR IMPLEMENTATION** - Plan validated with Context7 patterns and codebase analysis

