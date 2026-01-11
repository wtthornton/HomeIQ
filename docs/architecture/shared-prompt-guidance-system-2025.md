# Shared Prompt Guidance System Architecture (2025)

**Last Updated:** January 8, 2026  
**Status:** Architecture Design  
**Epic:** Automation System Consistency & Quality

## Executive Summary

This document defines the architecture for a **Shared Prompt Guidance System** that ensures consistent LLM communication across all HomeIQ services. The system establishes that:

1. **HomeIQ creates automations** (not "Home Assistant automations")
2. **HomeIQ JSON format is the standard** automation format
3. **Home Assistant YAML is only for deployment** (not for automation creation)

## Problem Statement

Currently, system prompts across services are inconsistent:

- **Proactive Agent Service**: Focuses on generating suggestions (good)
- **AI Automation Service New**: Mentions "Home Assistant automation expert" (confusing - should focus on HomeIQ)
- **HA AI Agent Service**: Very Home Assistant YAML focused (OK for YAML generation, but should clarify this is deployment-only)

This inconsistency leads to:
- Confusion about what HomeIQ does (creates automations vs. Home Assistant automations)
- Mixed messaging about format standards (HomeIQ JSON vs. YAML)
- Lack of shared vocabulary and principles

## Architecture Goals

1. **Consistency**: All services use shared vocabulary and principles
2. **Clarity**: Clear separation between automation creation (HomeIQ JSON) and deployment (Home Assistant YAML)
3. **Maintainability**: Single source of truth for prompt guidance
4. **Extensibility**: Easy to add new prompt templates and guidance

## Core Principles

### Principle 1: HomeIQ Creates Automations

**What HomeIQ Does:**
- HomeIQ creates **home automations**
- Automations control smart devices, respond to events, and automate home tasks
- Automations are platform-agnostic concepts

**What HomeIQ Does NOT Do:**
- HomeIQ does not create "Home Assistant automations"
- HomeIQ does not create YAML files (YAML is only for deployment)
- HomeIQ does not create platform-specific automations

### Principle 2: HomeIQ JSON is the Standard Format

**HomeIQ JSON Format:**
- **Primary format** for all automation data
- Used for automation creation, validation, storage, and communication
- Defined in `shared/homeiq_automation/schema.py`
- Includes: triggers, conditions, actions, metadata, device context, safety checks, energy impact

**HomeIQ JSON Schema:**
- `HomeIQAutomation` - Complete automation structure
- `HomeIQMetadata` - Creation metadata, confidence scores, use cases
- `DeviceContext` - Device IDs, entity IDs, areas, capabilities
- `PatternContext` - Pattern information (if generated from pattern)
- `SafetyChecks` - Safety validation information
- `EnergyImpact` - Energy consumption analysis

### Principle 3: Home Assistant YAML is Deployment-Only

**YAML Generation:**
- Home Assistant YAML is **only used for deployment**
- Generated from HomeIQ JSON (via `shared/homeiq_automation/yaml_transformer.py`)
- Not used for automation creation, validation, or communication
- Only the HA AI Agent Service generates YAML (deployment service)

**Deployment Flow:**
```
HomeIQ JSON Automation → YAML Transformer → Home Assistant YAML → Deploy to Home Assistant
```

## Architecture Components

### 1. Shared Prompt Guidance Module

**Location:** `shared/prompt_guidance/`

**Structure:**
```
shared/prompt_guidance/
├── __init__.py
├── core_principles.py          # Core principles (HomeIQ creates automations, JSON standard, YAML deployment-only)
├── vocabulary.py                # Shared vocabulary and terminology
├── homeiq_json_schema.py        # HomeIQ JSON schema documentation for prompts
├── templates/
│   ├── automation_generation.py    # Templates for automation generation
│   ├── suggestion_generation.py    # Templates for suggestion generation
│   └── yaml_generation.py          # Templates for YAML generation (deployment-only)
└── builder.py                  # Prompt builder utility
```

### 2. Core Principles Module

**File:** `shared/prompt_guidance/core_principles.py`

**Content:**
```python
"""
Core principles for HomeIQ automation system.

All LLM prompts should incorporate these principles to ensure consistency.
"""

CORE_IDENTITY = """HomeIQ is an intelligent home automation platform that creates home automations.

HomeIQ creates automations that:
- Control smart devices (lights, thermostats, locks, etc.)
- Respond to events (motion, time, state changes)
- Automate home tasks (energy management, comfort, security, convenience)
- Work with any smart home platform (primarily Home Assistant for deployment)

HomeIQ does NOT:
- Create "Home Assistant automations" (Home Assistant is only the deployment platform)
- Create platform-specific automations
- Focus on YAML syntax (YAML is only for deployment)
"""

AUTOMATION_FORMAT_STANDARD = """HomeIQ uses HomeIQ JSON format as the standard automation format.

HomeIQ JSON Format:
- Primary format for automation creation, validation, storage, and communication
- Includes: triggers, conditions, actions, metadata, device context, safety checks, energy impact
- Schema defined in shared/homeiq_automation/schema.py
- All services should work with HomeIQ JSON format

Home Assistant YAML:
- Only used for deployment to Home Assistant
- Generated from HomeIQ JSON (not created directly)
- Only the HA AI Agent Service generates YAML (deployment service)
- YAML generation is a deployment concern, not an automation creation concern
"""

AUTOMATION_CREATION_FLOW = """Automation Creation Flow:

1. **Suggestion Generation** (Proactive Agent Service):
   - Generates natural language automation suggestions
   - Suggestions describe automations in plain English
   - Suggestions reference devices, triggers, and actions

2. **Automation Generation** (AI Automation Service New):
   - Converts suggestions/descriptions to HomeIQ JSON format
   - Uses HomeIQ JSON schema (HomeIQAutomation, HomeIQMetadata, DeviceContext, etc.)
   - Validates automation structure, devices, safety, energy impact
   - Stores automations in HomeIQ JSON format

3. **YAML Generation** (HA AI Agent Service):
   - Converts HomeIQ JSON to Home Assistant YAML (deployment-only)
   - Uses yaml_transformer.py for conversion
   - Validates YAML syntax and Home Assistant compatibility
   - Deploys YAML to Home Assistant

Key Point: YAML generation is the LAST step (deployment), not the first step (creation).
"""
```

### 3. Vocabulary Module

**File:** `shared/prompt_guidance/vocabulary.py`

**Content:**
```python
"""
Shared vocabulary and terminology for HomeIQ automation system.

Use these terms consistently across all prompts.
"""

# Core Terms
TERMS = {
    "automation": "A set of rules that control smart devices and respond to events",
    "home automation": "Automation for home environments (lights, climate, security, etc.)",
    "HomeIQ automation": "An automation created by HomeIQ, stored in HomeIQ JSON format",
    "HomeIQ JSON": "The standard JSON format for HomeIQ automations (schema: shared/homeiq_automation/schema.py)",
    "Home Assistant YAML": "YAML format for deploying automations to Home Assistant (deployment-only)",
    "deployment": "The process of converting HomeIQ JSON to YAML and deploying to Home Assistant",
}

# What to Use
USE_TERMS = {
    "automation creation": "Creating home automations",
    "HomeIQ JSON format": "HomeIQ JSON Automation format",
    "automation data": "Automation in HomeIQ JSON format",
    "automation metadata": "HomeIQ metadata (use_case, complexity, confidence_score, etc.)",
}

# What NOT to Use
AVOID_TERMS = {
    "Home Assistant automation": "Use 'home automation' or 'HomeIQ automation' instead",
    "YAML creation": "Use 'YAML generation' or 'YAML deployment' instead",
    "automation YAML": "Use 'automation JSON' or 'HomeIQ JSON' instead (YAML is deployment-only)",
    "creating YAML": "Use 'generating YAML from JSON' or 'deploying to YAML' instead",
}
```

### 4. HomeIQ JSON Schema Documentation

**File:** `shared/prompt_guidance/homeiq_json_schema.py`

**Content:**
```python
"""
HomeIQ JSON schema documentation for LLM prompts.

Provides structured documentation of HomeIQ JSON format for use in system prompts.
"""

HOMEIQ_JSON_SCHEMA_DOC = """HomeIQ JSON Automation Format

Core Structure:
- alias (required): Automation name/alias
- description: Automation description
- version: HomeIQ JSON schema version (default: "1.0.0")
- triggers (required): List of triggers (HomeIQTrigger)
- conditions (optional): List of conditions (HomeIQCondition)
- actions (required): List of actions (HomeIQAction)
- mode: Execution mode (single, restart, queued, parallel)
- initial_state: Initial state (true/false, required for 2025.10+)

HomeIQ Metadata (homeiq_metadata):
- created_by: Service that created this automation
- created_at: Creation timestamp
- pattern_id: Pattern ID (if generated from pattern)
- suggestion_id: Suggestion ID (if generated from suggestion)
- confidence_score: Confidence score (0-1)
- safety_score: Safety score (0-100)
- use_case: "energy", "comfort", "security", or "convenience"
- complexity: "low", "medium", or "high"

Device Context (device_context):
- device_ids: List of device IDs involved
- entity_ids: List of entity IDs involved
- device_types: List of device types (light, sensor, etc.)
- area_ids: List of area IDs
- device_capabilities: Device capabilities (effects, modes, ranges, etc.)

Pattern Context (pattern_context, optional):
- pattern_type: Pattern type (time_of_day, co_occurrence, etc.)
- pattern_id: Pattern ID
- pattern_metadata: Pattern-specific metadata
- confidence: Pattern confidence (0-1)
- occurrences: Number of pattern occurrences

Safety Checks (safety_checks, optional):
- requires_confirmation: Require user confirmation before deployment
- critical_devices: List of critical device IDs
- time_constraints: Time-based safety constraints
- safety_warnings: List of safety warnings

Energy Impact (energy_impact, optional):
- estimated_power_w: Estimated power consumption (watts)
- estimated_daily_kwh: Estimated daily energy (kWh)
- peak_hours: Peak consumption hours (0-23)

For complete schema, see: shared/homeiq_automation/schema.py
"""
```

### 5. Prompt Templates

**File:** `shared/prompt_guidance/templates/automation_generation.py`

**Content:**
```python
"""
Prompt templates for automation generation.

Templates for generating HomeIQ JSON automations from descriptions/suggestions.
"""

AUTOMATION_GENERATION_SYSTEM_PROMPT = """You are HomeIQ's Automation Generation Assistant.

Your role is to create home automations in HomeIQ JSON format based on user descriptions or suggestions.

## Core Principles

{CORE_IDENTITY}

{AUTOMATION_FORMAT_STANDARD}

## Your Task

Generate HomeIQ JSON Automation format from the provided description/suggestion.

HomeIQ JSON Format Requirements:
- Use HomeIQ JSON schema (HomeIQAutomation, HomeIQMetadata, DeviceContext, etc.)
- Include all required fields: alias, triggers, actions, mode, initial_state
- Include HomeIQ metadata: use_case, complexity, confidence_score, safety_score
- Include device context: device_ids, entity_ids, device_types, area_ids
- Include safety checks if automation uses critical devices
- Include energy impact if automation involves power-consuming devices
- Include pattern context if automation is generated from a pattern

## Response Format

Return ONLY valid JSON matching the HomeIQ Automation schema. Include all relevant HomeIQ metadata and context.

Do NOT:
- Generate Home Assistant YAML (YAML is only for deployment, not creation)
- Use Home Assistant-specific terminology (focus on automation concepts)
- Skip HomeIQ metadata (all automations must include metadata)

For HomeIQ JSON schema reference: {HOMEIQ_JSON_SCHEMA_DOC}
"""
```

**File:** `shared/prompt_guidance/templates/suggestion_generation.py`

**Content:**
```python
"""
Prompt templates for suggestion generation.

Templates for generating automation suggestions (natural language descriptions).
"""

SUGGESTION_GENERATION_SYSTEM_PROMPT = """You are HomeIQ's Proactive Automation Intelligence.

Your role is to analyze home context and generate personalized automation suggestions.

## Core Principles

{CORE_IDENTITY}

## What Makes a Great Suggestion

1. **Specific**: Reference actual devices/areas by their exact friendly names
2. **Timely**: Based on current conditions, not generic advice
3. **Actionable**: Something that can become a home automation
4. **Valuable**: Saves money, increases comfort, or improves safety
5. **Novel**: Not something the user is already doing

## Suggestion Format

Suggestions should describe automations in plain English:
- What devices are involved
- What triggers the automation
- What actions should occur
- Why this automation is valuable

## Response Format

Return a JSON array of suggestions. Each suggestion:
{{
    "prompt": "DETAILED natural language suggestion describing the automation",
    "context_type": "weather|sports|energy|pattern|device|synergy",
    "trigger": "unique_identifier_for_deduplication",
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation of why this suggestion is valuable",
    "referenced_devices": ["exact_device_name_from_list"],
    "automation_hints": {{
        "trigger_type": "state_change|time|template",
        "trigger_entity": "sensor.entity_id if applicable",
        "trigger_condition": "state value or time",
        "target_color": "#hexcode if lighting",
        "game_time": "HH:MM if sports"
    }}
}}

Remember: Suggestions describe automations (not "Home Assistant automations"). Automations will be created in HomeIQ JSON format.
"""
```

**File:** `shared/prompt_guidance/templates/yaml_generation.py`

**Content:**
```python
"""
Prompt templates for YAML generation (deployment-only).

Templates for converting HomeIQ JSON to Home Assistant YAML.
"""

YAML_GENERATION_SYSTEM_PROMPT = """You are HomeIQ's YAML Deployment Assistant.

Your role is to convert HomeIQ JSON automations to Home Assistant YAML format for deployment.

## Core Principles

{AUTOMATION_FORMAT_STANDARD}

## Your Task

Convert HomeIQ JSON Automation to Home Assistant YAML format.

Important:
- YAML generation is the LAST step (deployment), not the first step (creation)
- Automations are already created in HomeIQ JSON format
- Your job is to convert JSON to YAML for Home Assistant deployment
- Use yaml_transformer.py for conversion (deterministic conversion)

## Home Assistant YAML Requirements (2025.10+)

- alias: Automation name
- description: Automation description
- initial_state: true (REQUIRED)
- mode: single|restart|queued|parallel
- trigger: (singular) List of triggers with platform field
- condition: (optional) List of conditions
- action: (singular) List of actions with service field

## Conversion Process

1. Extract triggers from HomeIQ JSON triggers
2. Extract conditions from HomeIQ JSON conditions (if any)
3. Extract actions from HomeIQ JSON actions
4. Convert to Home Assistant YAML format (2025.10+ structure)
5. Validate YAML syntax and entity IDs

Remember: You are converting existing automations (JSON → YAML), not creating new automations. Automation creation happens in HomeIQ JSON format.
"""
```

### 6. Prompt Builder Utility

**File:** `shared/prompt_guidance/builder.py`

**Content:**
```python
"""
Prompt builder utility for constructing consistent prompts.

Provides utilities for building prompts with shared principles and templates.
"""

from typing import Any
from .core_principles import CORE_IDENTITY, AUTOMATION_FORMAT_STANDARD, AUTOMATION_CREATION_FLOW
from .vocabulary import TERMS, USE_TERMS, AVOID_TERMS
from .homeiq_json_schema import HOMEIQ_JSON_SCHEMA_DOC
from .templates.automation_generation import AUTOMATION_GENERATION_SYSTEM_PROMPT
from .templates.suggestion_generation import SUGGESTION_GENERATION_SYSTEM_PROMPT
from .templates.yaml_generation import YAML_GENERATION_SYSTEM_PROMPT


class PromptBuilder:
    """
    Builder for constructing consistent prompts with shared principles.
    """
    
    @staticmethod
    def build_automation_generation_prompt(
        additional_context: str = "",
        entity_context: dict[str, Any] | None = None
    ) -> str:
        """
        Build system prompt for automation generation.
        
        Args:
            additional_context: Additional context to include
            entity_context: Entity context (entities by domain)
        
        Returns:
            Complete system prompt for automation generation
        """
        prompt = AUTOMATION_GENERATION_SYSTEM_PROMPT.format(
            CORE_IDENTITY=CORE_IDENTITY,
            AUTOMATION_FORMAT_STANDARD=AUTOMATION_FORMAT_STANDARD,
            HOMEIQ_JSON_SCHEMA_DOC=HOMEIQ_JSON_SCHEMA_DOC
        )
        
        if additional_context:
            prompt += f"\n\n## Additional Context\n\n{additional_context}"
        
        if entity_context:
            entity_section = "\n\n## Available Entities\n\n"
            entity_section += "You MUST use ONLY the entity IDs listed below:\n\n"
            for domain, entities in entity_context.items():
                if entities:
                    entity_ids = [e.get("entity_id", "") for e in entities[:30] if e.get("entity_id")]
                    if entity_ids:
                        entity_section += f"{domain.upper()}: {', '.join(entity_ids)}\n"
            prompt += entity_section
        
        return prompt
    
    @staticmethod
    def build_suggestion_generation_prompt(
        device_inventory: dict[str, Any] | None = None,
        home_context: str = ""
    ) -> str:
        """
        Build system prompt for suggestion generation.
        
        Args:
            device_inventory: Device inventory for validation
            home_context: Home context information
        
        Returns:
            Complete system prompt for suggestion generation
        """
        prompt = SUGGESTION_GENERATION_SYSTEM_PROMPT.format(
            CORE_IDENTITY=CORE_IDENTITY
        )
        
        if device_inventory:
            device_section = "\n\n## Available Devices\n\n"
            device_section += "You may ONLY suggest automations for devices that exist in this list:\n\n"
            # Add device list formatting
            prompt += device_section
        
        if home_context:
            prompt += f"\n\n## Home Context\n\n{home_context}"
        
        return prompt
    
    @staticmethod
    def build_yaml_generation_prompt(
        ha_version: str = "2025.10",
        additional_instructions: str = ""
    ) -> str:
        """
        Build system prompt for YAML generation (deployment-only).
        
        Args:
            ha_version: Home Assistant version
            additional_instructions: Additional YAML generation instructions
        
        Returns:
            Complete system prompt for YAML generation
        """
        prompt = YAML_GENERATION_SYSTEM_PROMPT.format(
            AUTOMATION_FORMAT_STANDARD=AUTOMATION_FORMAT_STANDARD
        )
        
        prompt += f"\n\n## Home Assistant Version\n\nTarget version: {ha_version}\n"
        
        if additional_instructions:
            prompt += f"\n\n## Additional Instructions\n\n{additional_instructions}"
        
        return prompt
```

## Service Integration

### 1. Proactive Agent Service

**Current:** Uses `SUGGESTION_SYSTEM_PROMPT` in `services/proactive-agent-service/src/services/ai_prompt_generation_service.py`

**Changes:**
- Import `PromptBuilder` from `shared.prompt_guidance.builder`
- Use `PromptBuilder.build_suggestion_generation_prompt()` instead of hardcoded prompt
- Ensure prompt emphasizes that suggestions describe automations (not "Home Assistant automations")

**Example:**
```python
from shared.prompt_guidance.builder import PromptBuilder

# Replace SUGGESTION_SYSTEM_PROMPT with:
system_prompt = PromptBuilder.build_suggestion_generation_prompt(
    device_inventory=device_inventory,
    home_context=home_context
)
```

### 2. AI Automation Service New

**Current:** Uses hardcoded prompts in `services/ai-automation-service-new/src/clients/openai_client.py`

**Changes:**
- Import `PromptBuilder` from `shared.prompt_guidance.builder`
- Replace `generate_homeiq_automation_json()` system prompt with `PromptBuilder.build_automation_generation_prompt()`
- Remove "Home Assistant automation expert" language (use "HomeIQ Automation Generation Assistant" instead)
- Ensure prompt focuses on HomeIQ JSON format

**Example:**
```python
from shared.prompt_guidance.builder import PromptBuilder

# In generate_homeiq_automation_json():
system_prompt = PromptBuilder.build_automation_generation_prompt(
    additional_context=context_section,
    entity_context=entity_context
)
```

### 3. HA AI Agent Service

**Current:** Uses `SYSTEM_PROMPT` in `services/ha-ai-agent-service/src/prompts/system_prompt.py`

**Changes:**
- Import `PromptBuilder` from `shared.prompt_guidance.builder`
- Update system prompt to clarify that YAML generation is deployment-only
- Emphasize that automations are created in HomeIQ JSON format first
- Keep YAML-specific instructions (this is the deployment service)

**Example:**
```python
from shared.prompt_guidance.builder import PromptBuilder

# Add to system prompt construction:
yaml_generation_context = PromptBuilder.build_yaml_generation_prompt(
    ha_version=settings.ha_version,
    additional_instructions="[existing YAML-specific instructions]"
)
```

## Migration Plan

### Phase 1: Create Shared Module (Week 1)

1. Create `shared/prompt_guidance/` directory structure
2. Implement core modules:
   - `core_principles.py`
   - `vocabulary.py`
   - `homeiq_json_schema.py`
   - `templates/` (automation_generation.py, suggestion_generation.py, yaml_generation.py)
   - `builder.py`
3. Add unit tests

### Phase 2: Integrate with Services (Week 2)

1. **Proactive Agent Service:**
   - Update `ai_prompt_generation_service.py` to use `PromptBuilder.build_suggestion_generation_prompt()`
   - Test suggestion generation

2. **AI Automation Service New:**
   - Update `openai_client.py` to use `PromptBuilder.build_automation_generation_prompt()`
   - Update `generate_homeiq_automation_json()` method
   - Test JSON generation

3. **HA AI Agent Service:**
   - Update `system_prompt.py` to incorporate shared principles
   - Add clarification that YAML generation is deployment-only
   - Test YAML generation

### Phase 3: Validation & Testing (Week 3)

1. Test all services with new prompts
2. Validate consistency across services
3. Review generated automations for adherence to principles
4. Update documentation

## Benefits

1. **Consistency**: All services use shared vocabulary and principles
2. **Clarity**: Clear separation between automation creation (JSON) and deployment (YAML)
3. **Maintainability**: Single source of truth for prompt guidance
4. **Extensibility**: Easy to add new prompt templates and guidance
5. **Quality**: Better automation generation through consistent principles

## Related Documentation

- HomeIQ JSON Schema: `shared/homeiq_automation/schema.py`
- YAML Transformer: `shared/homeiq_automation/yaml_transformer.py`
- Proactive Agent Service: `services/proactive-agent-service/README.md`
- AI Automation Service: `services/ai-automation-service-new/README.md`
- HA AI Agent Service: `services/ha-ai-agent-service/README.md`
