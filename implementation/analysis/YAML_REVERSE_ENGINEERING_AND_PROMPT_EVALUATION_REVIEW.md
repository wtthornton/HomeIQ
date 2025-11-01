# YAML Reverse Engineering & Prompt Evaluation Review

**Date:** November 1, 2025  
**Status:** Comprehensive Review

---

## Executive Summary

This review examines two critical components of the AI automation system:
1. **Reverse Engineering** - Converting generated YAML back to natural language for validation
2. **Prompt Evaluation** - How prompts are built and evaluated for YAML generation

Both systems use advanced AI techniques to ensure generated automations match user intent.

---

## Part 1: YAML Reverse Engineering

### Overview

**Location:** `services/ai-automation-service/src/services/yaml_self_correction.py`

The reverse engineering system implements **iterative self-correction** based on research:
- **Self-Refine** (arxiv.org/abs/2303.17651)
- **RPE - Reverse Prompt Engineering** (learnprompting.org/docs/language-model-inversion/reverse-prompt-engineering)
- **PASR - ProActive Self-Refinement** (arxiv.org/abs/2508.12903)

### Architecture

```
Generate YAML → Reverse Engineer → Compare Similarity → Generate Feedback → Refine → Repeat
```

### Key Components

#### 1. Reverse Engineering Process (`_reverse_engineer_yaml`)

```194:255:services/ai-automation-service/src/services/yaml_self_correction.py
    async def _reverse_engineer_yaml(
        self,
        yaml_content: str,
        context: Optional[Dict] = None
    ) -> str:
        """
        Reverse engineer YAML back to natural language description.
        
        Uses Reverse Prompt Engineering (RPE) techniques to reconstruct intent.
        """
        # Parse YAML to extract key information
        try:
            parsed_yaml = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML in reverse engineering: {e}")
            return "Invalid YAML configuration"
        
        # Build prompt for OpenAI reverse engineering
        context_section = ""
        if context:
            context_section = f"\n\nAdditional Context:\n{self._format_context(context)}"
        
        reverse_engineering_prompt = f"""Analyze this Home Assistant automation YAML and describe what it does in natural language.

YAML:
```yaml
{yaml_content}
```
{context_section}

Your task: Write a clear, concise paragraph describing:
1. What trigger starts this automation
2. What conditions must be met (if any)
3. What actions are performed
4. Any special features (delays, repeats, sequences, etc.)

Write as if explaining to a user who asked for this automation."""

        try:
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a Home Assistant expert who explains automations clearly in plain English."
                    },
                    {
                        "role": "user",
                        "content": reverse_engineering_prompt
                    }
                ],
                temperature=0.3,  # Low temperature for consistency
                max_tokens=300
            )
            
            reverse_description = response.choices[0].message.content.strip()
            logger.debug(f"Reverse engineered: {reverse_description[:100]}...")
            return reverse_description
            
        except Exception as e:
            logger.error(f"Reverse engineering failed: {e}")
            return "Failed to analyze YAML"
```

**Analysis:**
- ✅ **Strengths:**
  - Clear structured prompt asking for specific information
  - Low temperature (0.3) for consistency
  - Handles YAML parsing errors gracefully
  - Includes context support for better understanding

- ⚠️ **Issues:**
  - No validation that reverse-engineered text is useful
  - Limited token count (300) may truncate complex automations
  - Single-shot approach - no verification step

#### 2. Similarity Calculation (`_calculate_similarity`)

```257:290:services/ai-automation-service/src/services/yaml_self_correction.py
    async def _calculate_similarity(
        self,
        original_prompt: str,
        reverse_engineered: str
    ) -> float:
        """
        Calculate semantic similarity between two texts using embeddings.
        
        Uses SentenceTransformers for fast, accurate comparison.
        """
        try:
            # Generate embeddings
            embeddings = self.similarity_model.encode(
                [original_prompt, reverse_engineered]
            )
            
            # Calculate cosine similarity
            from sklearn.metrics.pairwise import cosine_similarity
            similarity_matrix = cosine_similarity(
                embeddings[0:1],
                embeddings[1:2]
            )
            
            similarity_score = float(similarity_matrix[0][0])
            
            # Clip to valid range
            similarity_score = max(0.0, min(1.0, similarity_score))
            
            logger.debug(f"Similarity score: {similarity_score:.4f}")
            return similarity_score
            
        except Exception as e:
            logger.error(f"Similarity calculation failed: {e}")
            return 0.0
```

**Analysis:**
- ✅ **Strengths:**
  - Uses semantic embeddings (not just text matching)
  - Fast SentenceTransformers model (`all-MiniLM-L6-v2`)
  - Proper error handling
  - Cosine similarity is industry standard

- ⚠️ **Considerations:**
  - Model choice: `all-MiniLM-L6-v2` is fast but may miss nuanced differences
  - No domain-specific fine-tuning (HA automation terminology)
  - Could benefit from entity-aware similarity (match entity IDs separately)

#### 3. Feedback Generation (`_generate_correction_feedback`)

```292:366:services/ai-automation-service/src/services/yaml_self_correction.py
    async def _generate_correction_feedback(
        self,
        original_prompt: str,
        reverse_engineered: str,
        similarity_score: float,
        current_yaml: str
    ) -> Dict[str, List[str]]:
        """
        Generate actionable feedback for improving YAML.
        
        Uses ProActive Self-Refinement (PASR) techniques.
        """
        feedback_prompt = f"""Analyze why these two descriptions differ and provide actionable corrections.

Original Request:
"{original_prompt}"

What the YAML Actually Does:
"{reverse_engineered}"

Current Similarity: {similarity_score:.2%}

Your task:
1. Identify the key differences
2. Explain why they differ (missing features, wrong interpretation, etc.)
3. Provide specific actions to align the YAML with the original request

Format your response as:
FEEDBACK: [brief explanation of main issues]
ACTION 1: [specific change needed]
ACTION 2: [specific change needed]
..."""

        try:
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at identifying discrepancies in automation logic and providing precise corrections."
                    },
                    {
                        "role": "user",
                        "content": feedback_prompt
                    }
                ],
                temperature=0.5,
                max_tokens=400
            )
            
            feedback_text = response.choices[0].message.content
            
            # Parse feedback and actions
            feedback = ""
            actions = []
            
            lines = feedback_text.split("\n")
            for line in lines:
                if line.startswith("FEEDBACK:"):
                    feedback = line.replace("FEEDBACK:", "").strip()
                elif line.startswith("ACTION"):
                    action = line.split(":", 1)[-1].strip()
                    actions.append(action)
            
            return {
                "feedback": feedback or "No specific feedback generated",
                "actions": actions if actions else ["Review and adjust YAML manually"]
            }
            
        except Exception as e:
            logger.error(f"Feedback generation failed: {e}")
            return {
                "feedback": f"Error generating feedback: {str(e)}",
                "actions": ["Manual review recommended"]
            }
```

**Analysis:**
- ✅ **Strengths:**
  - Structured format (FEEDBACK + ACTIONS) for parsing
  - Medium temperature (0.5) balances creativity and consistency
  - Parsing handles multiple actions

- ⚠️ **Issues:**
  - Fragile parsing (relies on exact format)
  - No validation of action quality
  - Limited token count (400) may truncate complex feedback

#### 4. Iterative Correction Loop (`correct_yaml`)

```78:192:services/ai-automation-service/src/services/yaml_self_correction.py
    async def correct_yaml(
        self,
        user_prompt: str,
        generated_yaml: str,
        context: Optional[Dict] = None
    ) -> SelfCorrectionResponse:
        """
        Main self-correction loop.
        
        Args:
            user_prompt: Original user request
            generated_yaml: Initial YAML to refine
            context: Optional context (devices, entities, etc.)
        
        Returns:
            SelfCorrectionResponse with refined YAML and history
        """
        logger.info(f"🔄 Starting self-correction for prompt: {user_prompt[:60]}...")
        
        iteration_history: List[CorrectionResult] = []
        current_yaml = generated_yaml
        total_tokens = 0
        previous_similarity = 0.0
        
        for iteration in range(1, self.max_iterations + 1):
            logger.info(f"🔄 Iteration {iteration}/{self.max_iterations}")
            
            # Step 1: Reverse engineer YAML to natural language
            reverse_engineered_prompt = await self._reverse_engineer_yaml(
                current_yaml,
                context
            )
            
            # Step 2: Calculate semantic similarity
            similarity_score = await self._calculate_similarity(
                user_prompt,
                reverse_engineered_prompt
            )
            
            # Step 3: Check convergence
            improvement = similarity_score - previous_similarity
            
            logger.info(
                f"Iteration {iteration}: Similarity = {similarity_score:.2%}, "
                f"Improvement = {improvement:.2%}"
            )
            
            # Step 4: Store iteration result
            correction_result = CorrectionResult(
                iteration=iteration,
                similarity_score=similarity_score,
                original_prompt=user_prompt,
                reverse_engineered_prompt=reverse_engineered_prompt,
                yaml_content=current_yaml,
                correction_feedback="",
                improvement_actions=[]
            )
            
            # Step 5: Check if we should stop
            if similarity_score >= self.min_similarity_threshold:
                logger.info("✅ Target similarity achieved - stopping")
                correction_result.correction_feedback = (
                    f"Target similarity ({self.min_similarity_threshold:.0%}) achieved"
                )
                iteration_history.append(correction_result)
                break
            
            # Check if improvement is minimal
            if iteration > 1 and improvement < self.improvement_threshold:
                logger.warning(
                    f"⚠️ Minimal improvement ({improvement:.2%}) - near convergence"
                )
                correction_result.correction_feedback = (
                    "Minimal improvement detected - likely at optimal level"
                )
                iteration_history.append(correction_result)
                break
            
            # Step 6: Generate feedback and refine YAML
            feedback_and_actions = await self._generate_correction_feedback(
                user_prompt,
                reverse_engineered_prompt,
                similarity_score,
                current_yaml
            )
            
            correction_result.correction_feedback = feedback_and_actions["feedback"]
            correction_result.improvement_actions = feedback_and_actions["actions"]
            
            # Step 7: Refine YAML based on feedback
            if iteration < self.max_iterations:
                refined_yaml = await self._refine_yaml(
                    user_prompt,
                    current_yaml,
                    feedback_and_actions,
                    context
                )
                current_yaml = refined_yaml
            else:
                logger.info("Max iterations reached - using best result")
            
            previous_similarity = similarity_score
            iteration_history.append(correction_result)
        
        final_similarity = iteration_history[-1].similarity_score if iteration_history else 0.0
        
        return SelfCorrectionResponse(
            final_yaml=current_yaml,
            final_similarity=final_similarity,
            iterations_completed=len(iteration_history),
            max_iterations=self.max_iterations,
            convergence_achieved=final_similarity >= self.min_similarity_threshold,
            iteration_history=iteration_history,
            total_tokens_used=total_tokens
        )
```

**Configuration:**
- `max_iterations = 5` - Reasonable limit
- `min_similarity_threshold = 0.85` - 85% similarity target (high bar)
- `improvement_threshold = 0.02` - 2% minimum improvement per iteration

**Analysis:**
- ✅ **Strengths:**
  - Early stopping on convergence
  - Tracks improvement per iteration
  - Comprehensive iteration history
  - Prevents infinite loops

- ⚠️ **Issues:**
  - `total_tokens` is calculated but never updated (bug)
  - No cost tracking (important for 5 iterations × 3 API calls)
  - May iterate unnecessarily if similarity is already high

### Recommendations for Reverse Engineering

1. **Fix Token Tracking**
   ```python
   # After each API call, add tokens
   total_tokens += response.usage.total_tokens
   ```

2. **Add Entity-Aware Similarity**
   - Extract entity IDs from both prompts
   - Check entity ID matching separately
   - Weight entity match higher than semantic similarity

3. **Improve Feedback Parsing**
   - Use regex or structured output (JSON mode)
   - Validate action quality before using

4. **Cost Optimization**
   - Skip reverse engineering if initial similarity > 0.90
   - Cache embeddings for common patterns

---

## Part 2: Prompt Evaluation & Generation

### Overview

**Location:** `services/ai-automation-service/src/api/ask_ai_router.py` (lines 395-850)

The prompt generation system builds comprehensive prompts for YAML generation with:
- Entity validation
- Device capabilities
- Advanced HA features
- Safety constraints

### Key Components

#### 1. Prompt Builder (`generate_automation_yaml`)

The prompt building process:

```585:763:services/ai-automation-service/src/api/ask_ai_router.py
    prompt = f"""
You are a Home Assistant automation YAML generator expert with deep knowledge of advanced HA features.

User's original request: "{original_query}"

Automation suggestion:
- Description: {suggestion.get('description', '')}
- Trigger: {suggestion.get('trigger_summary', '')}
- Action: {suggestion.get('action_summary', '')}
- Devices: {', '.join(suggestion.get('devices_involved', []))}

{validated_entities_text}

{"🔴 TEST MODE WITH SEQUENCES: For quick testing - Generate automation YAML with shortened delays (10x faster):" if is_sequence_test else ("🔴 TEST MODE: For manual testing - Generate simple automation YAML:" if is_test else "Generate a sophisticated Home Assistant automation YAML configuration that brings this creative suggestion to life.")}
{"- Use event trigger that fires immediately on manual trigger" if is_test else ""}
{"- SHORTEN all delays by 10x (e.g., 2 seconds → 0.2 seconds, 30 seconds → 3 seconds)" if is_sequence_test else ("- NO delays or timing components" if is_test else "")}
{"- REDUCE repeat counts (e.g., 5 times → 2 times, 10 times → 3 times) for quick preview" if is_sequence_test else ("- NO repeat loops or sequences (just execute once)" if is_test else "")}
{"- Keep sequences and repeat blocks but execute faster" if is_sequence_test else ("- Action should execute the device control immediately" if is_test else "")}
{"- Example: If original has 'delay: 00:00:05', use 'delay: 00:00:00.5' (or 0.5 seconds)" if is_sequence_test else ("- Example trigger: platform: event, event_type: test_trigger" if is_test else "")}

Requirements:
1. Use YAML format (not JSON)
2. Include: id, alias, trigger, action
3. CRITICAL: Use ONLY the validated entity IDs provided above - do NOT create new entity IDs
4. Add appropriate conditions if needed
5. Include mode: single or restart
6. Add description field
7. Use advanced HA features for creative implementations:
   - `sequence` for multi-step actions
   - `choose` for conditional logic
   - `template` for dynamic values
   - `condition` for complex triggers
   - `delay` for timing
   - `repeat` for patterns
   - `parallel` for simultaneous actions

CRITICAL YAML STRUCTURE RULES:
1. Entity IDs MUST be in format: domain.entity (e.g., light.office, binary_sensor.door)
2. Service calls ALWAYS use target.entity_id structure:
   ```yaml
   - service: light.turn_on
     target:
       entity_id: light.kitchen
   ```
   NEVER use entity_id directly in the action!
3. Multiple entities use list format:
   ```yaml
   target:
     entity_id:
       - light.kitchen
       - light.living_room
   ```
4. Required fields: alias, trigger, action
5. Always include mode: single (or restart, queued, parallel)

Advanced YAML Examples:

Example 1 - Simple time trigger (CORRECT):
```yaml
alias: Morning Kitchen Light
description: Turn on kitchen light at 7 AM
mode: single
trigger:
  - platform: time
    at: '07:00:00'
action:
  - service: light.turn_on
    target:
      entity_id: light.kitchen
    data:
      brightness_pct: 100
```

Example 2 - State trigger with condition (CORRECT):
```yaml
alias: Motion-Activated Office Light
description: Turn on office light when motion detected after 6 PM
mode: single
trigger:
  - platform: state
    entity_id: binary_sensor.office_motion
    to: 'on'
condition:
  - condition: time
    after: '18:00:00'
action:
  - service: light.turn_on
    target:
      entity_id: light.office
    data:
      brightness_pct: 75
      color_name: warm_white
```

Example 3 - Repeat with sequence (CORRECT):
```yaml
alias: Flash Pattern
description: Flash lights 3 times
mode: single
trigger:
  - platform: event
    event_type: test_trigger
action:
  - repeat:
      count: 3
      sequence:
        - service: light.turn_on
          target:
            entity_id: light.office
          data:
            brightness_pct: 100
        - delay: '00:00:01'
        - service: light.turn_off
          target:
            entity_id: light.office
        - delay: '00:00:01'
```

Example 4 - Choose with multiple triggers (CORRECT):
```yaml
alias: Color-Coded Door Notifications
description: Different colors for different doors
mode: single
trigger:
  - platform: state
    entity_id: binary_sensor.front_door
    to: 'on'
    id: front_door
  - platform: state
    entity_id: binary_sensor.back_door
    to: 'on'
    id: back_door
condition:
  - condition: time
    after: "18:00:00"
    before: "06:00:00"
action:
  - choose:
      - conditions:
          - condition: trigger
            id: front_door
        sequence:
          - service: light.turn_on
            target:
              entity_id: light.office_lights
            data:
              brightness_pct: 100
              color_name: red
      - conditions:
          - condition: trigger
            id: back_door
        sequence:
          - service: light.turn_on
            target:
              entity_id: light.office_lights
            data:
              brightness_pct: 100
              color_name: blue
    default:
      - service: light.turn_on
        target:
          entity_id: light.office_lights
        data:
          brightness_pct: 50
          color_name: white
```

COMMON MISTAKES TO AVOID:
❌ WRONG: entity_id: light.kitchen (in action directly)
✅ CORRECT: target: { entity_id: light.kitchen }

❌ WRONG: entity_id: "office" (missing domain)
✅ CORRECT: entity_id: light.office (full format)

❌ WRONG: service: light.turn_on without target
✅ CORRECT: service: light.turn_on with target.entity_id

Generate ONLY the YAML content, no explanations or markdown code blocks. Use the validated entity IDs provided above. Follow the structure examples exactly.
"""
```

**Analysis:**
- ✅ **Strengths:**
  - Comprehensive examples (4 different patterns)
  - Clear "do's and don'ts" section
  - Test mode support for faster iteration
  - Strong emphasis on validated entity IDs

- ⚠️ **Issues:**
  - Very long prompt (risk of token limits)
  - Examples take significant space
  - No dynamic example selection based on suggestion type
  - Could benefit from few-shot learning optimization

#### 2. Entity Validation Integration

```423:577:services/ai-automation-service/src/api/ask_ai_router.py
    # NEW: Validate entities before generating YAML
    from ..services.entity_validator import EntityValidator
    from ..clients.data_api_client import DataAPIClient
    
    try:
        logger.info("🔍 Starting entity validation...")
        # Initialize entity validator with data API client and optional db_session for alias support
        data_api_client = DataAPIClient()
        ha_client = HomeAssistantClient(
            ha_url=settings.ha_url,
            access_token=settings.ha_token
        ) if settings.ha_url and settings.ha_token else None
        entity_validator = EntityValidator(data_api_client, db_session=db_session, ha_client=ha_client)
        logger.info("✅ Entity validator initialized")
        
        # Map query devices to real entities
        devices_involved = suggestion.get('devices_involved', [])
        logger.info(f"🔍 DEVICES INVOLVED: {devices_involved}")
        logger.info(f"🔍 ORIGINAL QUERY: {original_query}")
        
        # Always try to map entities from the query, even if devices_involved is empty
        entity_mapping = await entity_validator.map_query_to_entities(original_query, devices_involved)
        logger.info(f"🔍 ENTITY MAPPING RESULT: {entity_mapping}")
        logger.info(f"🔍 ENTITY MAPPING TYPE: {type(entity_mapping)}")
        logger.info(f"🔍 ENTITY MAPPING BOOL: {bool(entity_mapping)}")
        
        # Deduplicate entity mapping before using it
        if entity_mapping:
            entity_mapping = deduplicate_entity_mapping(entity_mapping)
        
        # Validate entity ID formats before using them
        validated_mapping = {}
        if entity_mapping:
            for term, entity_id in entity_mapping.items():
                # Ensure entity_id is in proper format (domain.entity)
                if isinstance(entity_id, str) and '.' in entity_id and not entity_id.startswith('.'):
                    validated_mapping[term] = entity_id
                else:
                    logger.warning(f"⚠️ Skipping invalid entity_id format: {term} -> {entity_id}")
            
            if validated_mapping:
                suggestion['validated_entities'] = validated_mapping
                logger.info(f"✅ VALIDATED ENTITIES ADDED TO SUGGESTION: {suggestion.get('validated_entities')}")
            else:
                logger.warning(f"⚠️ No valid entity IDs after format validation")
        else:
            logger.warning(f"⚠️ No valid entities found - mapping was: {entity_mapping}")
    except Exception as e:
        logger.error(f"❌ Error validating entities: {e}", exc_info=True)
        # Continue without validation if there's an error
```

**Analysis:**
- ✅ **Strengths:**
  - Validates entities before YAML generation
  - Proper error handling (continues if validation fails)
  - Format validation (domain.entity)
  - Comprehensive logging

- ⚠️ **Issues:**
  - Entity validation happens synchronously (adds latency)
  - No caching of entity mappings
  - Silent failure if validation errors occur

#### 3. Unified Prompt Builder

**Location:** `services/ai-automation-service/src/prompt_building/unified_prompt_builder.py`

The unified prompt builder centralizes prompt generation:

```27:69:services/ai-automation-service/src/prompt_building/unified_prompt_builder.py
    # Unified system prompt for all AI interactions
    UNIFIED_SYSTEM_PROMPT = """You are a HIGHLY CREATIVE and experienced Home Assistant automation expert with deep knowledge of device capabilities and smart home best practices.

Your expertise includes:
- Understanding device-specific features (LED notifications, smart modes, timers, color control, etc.)
- Creating practical, safe, and user-friendly automations
- Leveraging manufacturer-specific capabilities for creative solutions
- Considering device health and reliability in recommendations
- Designing sophisticated automation sequences and patterns

ADVANCED CAPABILITY EXAMPLES:

Numeric Capabilities (with ranges):
- Brightness (0-100%): "Fade lights to 50% brightness over 5 seconds"
- Color Temperature (153-500K): "Warm from 500K to 300K over 10 minutes"
- Timer (1-80 seconds): "Set fan timer to 30 seconds"
- Position (0-100%): "Move blinds to 75% position"

Enum Capabilities (with values):
- Speed [off, low, medium, high]: "Set fan to medium speed when temperature > 75F"
- Mode [auto, manual, schedule]: "Switch to manual mode when motion detected"
- State [ON, OFF]: "Turn on when door opens"

Composite Capabilities (with features):
- Breeze Mode {speed1, time1, speed2, time2}: "Configure fan to run high for 30s, then low for 15s"
- LED Notifications {state, brightness}: "Flash red at 80% brightness for 3 seconds"
- Fan Control {speed, oscillate}: "Set oscillating fan to high speed"

Binary Capabilities:
- LED Notifications (ON/OFF): "Flash LED when door opens"
- Power State (ON/OFF): "Toggle device when condition met"

Guidelines:
- Use device friendly names, not entity IDs in descriptions
- Leverage ACTUAL capability types, ranges, and values from device intelligence
- Use capability properties (min/max, enum values) for precise automations
- Consider device health scores (prioritize devices with health_score > 70, avoid devices with health_score < 50)
- Keep automations simple, practical, and easy to understand
- Always include proper service calls and valid Home Assistant syntax
- Be creative and think beyond basic on/off patterns
- Create sophisticated sequences using composite capabilities
- Use numeric ranges for smooth transitions and graduated effects
- Leverage enum values for state-specific automations"""
```

**Analysis:**
- ✅ **Strengths:**
  - Centralized system prompt (consistency)
  - Capability examples with ranges
  - Device health awareness
  - Creative guidance

- ⚠️ **Issues:**
  - Very long system prompt (may reduce model attention to user prompt)
  - Could be optimized with prompt compression

### Recommendations for Prompt Evaluation

1. **Optimize Prompt Length**
   - Use prompt compression techniques
   - Dynamically select examples based on suggestion type
   - Consider function calling instead of examples

2. **Cache Entity Mappings**
   - Cache validated entities per query pattern
   - Reduce redundant API calls

3. **Add Prompt Evaluation Metrics**
   - Track token usage per prompt type
   - Measure YAML correctness rate
   - A/B test prompt variations

4. **Improve Few-Shot Learning**
   - Select examples most similar to current suggestion
   - Use embedding-based example selection
   - Limit to 2-3 most relevant examples

---

## Overall Assessment

### Strengths

1. **Research-Based Approach** - Reverse engineering uses proven techniques
2. **Iterative Refinement** - Multiple passes improve quality
3. **Entity Validation** - Prevents invalid entity usage
4. **Comprehensive Examples** - Clear guidance for LLM
5. **Error Handling** - Graceful degradation on failures

### Weaknesses

1. **Cost** - Multiple API calls per automation (expensive)
2. **Latency** - Sequential processing adds delay
3. **Token Usage** - Very long prompts (risk of truncation)
4. **No Metrics** - Limited tracking of success rates
5. **Token Tracking Bug** - `total_tokens` never updated

### Priority Fixes

1. **High Priority:**
   - Fix token tracking bug
   - Add cost monitoring
   - Optimize prompt length

2. **Medium Priority:**
   - Cache entity mappings
   - Add entity-aware similarity
   - Improve feedback parsing

3. **Low Priority:**
   - Fine-tune similarity model
   - Add prompt A/B testing
   - Implement prompt compression

---

## Conclusion

The reverse engineering and prompt evaluation systems are **well-designed and research-backed**, but have room for optimization:

- **Reverse Engineering:** Solid foundation, needs cost/token tracking fixes
- **Prompt Evaluation:** Comprehensive but verbose, could benefit from optimization

Both systems demonstrate good software engineering practices (error handling, logging, modularity) but need performance and cost improvements.

