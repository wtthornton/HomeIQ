# AI Suggestion Improvement Research

**Date:** 2025-10-28  
**Status:** Analysis In Progress  
**Goal:** Review Hugging Face and GitHub approaches to build better AI automation suggestions

---

## Current Issues Identified

### 1. Entity Extraction Problems
**Problem:** AI generates YAML with placeholder entities instead of real ones
**Example:**
```
User: "Flash the living room lights"
AI Output: entity_id: light.office_light_placeholder
Expected: entity_id: light.living_room
```

**Root Causes:**
- Entity extraction relies on simple pattern matching
- No fuzzy matching to map natural language to entity IDs
- YAML generation doesn't have access to real entity list
- Tokenization issues with underscores (`living_room` vs `living room`)

### 2. YAML Generation Accuracy
**Problem:** Generated YAML often has syntax errors or invalid Home Assistant automation structure

**Common Issues:**
- Missing required fields
- Invalid trigger/action syntax
- Incorrect service calls
- Wrong entity types

### 3. Test Button Limitations
**Problem:** Test button traps:
- Doesn't create actual automations
- Relies on HA Conversation API (can't handle complex patterns)
- Returns success even when it fails
- Doesn't flash lights for complex commands

### 4. Temperature Settings
**Current Approach:**
- Entity extraction: 0.1 (deterministic)
- YAML generation: 0.3 (consistent)
- Creative suggestions: 0.7 (varied)

**Issues:**
- 0.7 too high for consistent suggestions
- No domain-specific model training
- Generic prompts not leveraging HA-specific patterns

---

## Improvements from Hugging Face Research

### 1. Fine-Tuned Sentence Transformers
**Approach:** Use sentence transformers for entity matching

**Benefits:**
- Better semantic understanding of device names
- Handles synonyms and variations naturally
- Fast embeddings for similarity matching

**Models to Consider:**
- `sentence-transformers/all-MiniLM-L6-v2` (fast, 384-dim)
- `sentence-transformers/all-mpnet-base-v2` (better accuracy, 768-dim)

**Implementation:**
```python
from sentence_transformers import SentenceTransformer
import numpy as np

# Load pre-trained model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Generate embeddings for all entities
entities = ["light.living_room", "light.kitchen", "switch.bedroom_fan"]
entity_embeddings = model.encode(entities)

# Query embedding
query = "living room lights"
query_embedding = model.encode([query])[0]

# Find best match via cosine similarity
similarities = np.dot(query_embedding, entity_embeddings.T)
best_match_idx = np.argmax(similarities)
matched_entity = entities[best_match_idx]
```

### 2. Few-Shot Learning with Examples
**Approach:** Provide domain-specific examples in prompts

**Current:** Generic prompts with minimal context
**Improved:** Include real HA examples in context

**Example:**
```python
FEW_SHOT_EXAMPLES = """
Input: "Turn on fries when door opens"
Output: 
  alias: Turn on lights when door opens
  trigger:
    - platform: state
      entity_id: binary_sensor.front_door
      to: 'on'
  action:
    - service: light.turn_on
      target:
        entity_id: light.foyer

Input: "Flash office lights every 30 seconds"
Output:
  alias: Flash Office Lights
  mode: restart
  trigger:
    - platform: time_pattern
      seconds: '/30'
  action:
    - service: light.turn_on
      target:
        entity_id: light.office
      data:
        flash: long
"""
```

### 3. Fine-Tune a Text Classification Model
While web search didn't show specific HA models, we can:
- Fine-tune BERT/DistilBERT on automation descriptions
- Label training data with correct entity mappings
- Train to classify "intent" (e.g., flash, dim, schedule)

**Approach:**
```python
from transformers import AutoModelForSequenceClassification, AutoTokenizer

# Fine-tune on labeled examples
training_examples = [
    ("Flash the office lights", "flash", ["light.office"]),
    ("Turn on kitchen lights when motion detected", "trigger_action", ["binary_sensor.kitchen_motion", "light.kitchen"]),
]

# Use DeBERTa or BERT for better understanding
model = AutoModelForSequenceClassification.from_pretrained(
    "microsoft/deberta-base", 
    num_labels=len(intent_classes)
)
```

### 4. Hybrid Architecture
**Current:** Single OpenAI call for everything
**Improved:** Multi-stage pipeline

**Stages:**
1. **Entity Matching** (Sentence Transformer - ~50ms)
2. **Intent Classification** (Fine-tuned BERT - ~100ms)
3. **YAML Generation** (OpenAI GPT-4o-mini - ~500ms)

**Benefits:**
- More accurate entity extraction
- Better intent understanding
- Higher-quality YAML
- Faster processing (avoiding failed attempts)

---

## Recommended Improvements (Prioritized)

### Priority 1: Entity Matching with Sentence Transformers (Quick Win)
**Effort:** Low-Medium  
**Impact:** High  
**Time:** 1-2 days

**Steps:**
1. Add `sentence-transformers` library
2. Load pre-trained model
3. Generate embeddings for all HA entities on startup
4. Use cosine similarity for entity matching
5. Cache embeddings in memory

**Files to Modify:**
- `services/ai-automation-service/src/entity_extraction/enhanced_extractor.py`
- Add new `SentenceTransformerEntityMatcher` class

### Priority 2: Few-Shot Learning Examples (Quick Win)
**Effort:** Low  
**Impact:** Medium  
**Time:** 1 day

**Steps:**
1. Collect 20-30 real automation examples
2. Add to prompt templates
3. Update YAML generation prompts
4. Test accuracy improvements

**Files to Modify:**
- `services/ai-automation-service/src/prompt_building/unified_prompt_builder.py`

### Priority 3: Intent Classification Model (Medium Term)
**Effort:** Medium-High  
**Impact:** High  
**Time:** 1-2 weeks

**Steps:**
1. Label training data (100-200 examples)
2. Fine-tune DistilBERT on automation patterns
3. Create intent categories (flash, schedule, trigger_action, etc.)
4. Integrate into suggestion pipeline
5. Use intent to select appropriate YAML templates

**Files to Create:**
- `services/ai-automation-service/src/ml/intent_classifier.py`
- `training_data/automation_intents.csv`

### Priority 4: Fix Test Button Workflow (High Impact)
**Effort:** Medium  
**Impact:** High  
**Time:** 2-3 days

**Steps:**
1. Change test button to create temporary automations
2. Add YAML generation to test flow
3. Create automation with `mode: single`
4. Trigger and delete after execution
5. Handle cleanup on errors

**Files to Modify:**
- `services/ai-automation-service/src/api/ask_ai_router.py`

---

## GitHub Integration Opportunities

### 1. Community Automation Database
**Approach:** Maintain a curated GitHub repo of Home Assistant automations

**Structure:**
```
automations/
├── lighting/
│   ├── flash_on_motion.yaml
│   └── dim_sunset.yaml
├── security/
│   ├── door_alert.yaml
│   └── motion_lights.yaml
└── comfort/
    ├── temp_control.yaml
    └── fan_auto.yaml
```

**Benefits:**
- Real-world tested automations
- Better few-shot examples
- Community validation
- Version control

### 2. Sync with Hugging Face
**Approach:** Store training data on Hugging Face Datasets

**Benefits:**
- Version control for training data
- Easy sharing and collaboration
- Access to HF training infrastructure
- Community contributions

### 3. GitHub Actions for Model Training
**Approach:** Automated retraining on new data

**Workflow:**
```
Trigger: New automation added to repo
→ Label training data
→ Fine-tune model
→ Test accuracy
→ Deploy if improved
→ Update production
```

---

## Next Steps

### Immediate Actions (This Week)
1. ✅ Research Hugging Face approaches (done)
2. ⏳ Implement sentence transformer entity matching
3. ⏳ Add few-shot examples to prompts
4. ⏳ Fix test button workflow

### Short Term (Next 2 Weeks)
1. Collect 100 automation examples for training
2. Fine-tune intent classification model
3. Set up GitHub repo for community automations
4. Implement hybrid entity matching approach

### Medium Term (Next Month)
1. Deploy fine-tuned model in production
2. Set up automated training pipeline
3. Create Hugging Face dataset
4. Integrate community automation database

---

## References

- Hugging Face Transformers: https://huggingface.co/transformers
- Sentence Transformers: https://www.sbert.net/
- Context7: Best practices for AI prompt engineering
- Home Assistant Automation Docs: https://www.home-assistant.io/docs/automation/

---

**Status:** Ready for implementation  
**Next Review:** After Priority 1 implementation

