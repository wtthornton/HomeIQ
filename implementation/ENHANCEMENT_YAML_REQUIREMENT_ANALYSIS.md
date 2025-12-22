# Enhancement YAML Requirement Analysis

**Date:** December 8, 2025  
**Status:** 🔍 Analysis Complete - Design Issue Identified  
**Issue:** Enhancement feature requires YAML, but users want to enhance prompts BEFORE creating YAML

---

## Problem Statement

The enhancement feature currently requires `automation_yaml` to be present before allowing enhancement. However, users want to enhance their **prompt** before creating the automation YAML, not after. This creates a chicken-and-egg problem:

1. User types a prompt
2. User wants to enhance the prompt to get better automation suggestions
3. System blocks enhancement because no YAML exists yet
4. User must create YAML first (defeats the purpose)

---

## Current Implementation Analysis

### Frontend Validation (EnhancementButton.tsx)

```37:40:services/ai-automation-ui/src/components/ha-agent/EnhancementButton.tsx
    if (!automationYaml || !originalPrompt) {
      toast.error('Automation YAML and original prompt are required for enhancements.', { icon: '❌' });
      return;
    }
```

```142:146:services/ai-automation-ui/src/components/ha-agent/EnhancementButton.tsx
  const hasPrerequisites = !!(automationYaml && originalPrompt && conversationId);
  const missingPrerequisites: string[] = [];
  if (!conversationId) missingPrerequisites.push('active conversation');
  if (!automationYaml) missingPrerequisites.push('automation YAML');
  if (!originalPrompt) missingPrerequisites.push('original prompt');
```

**Issue:** Button is disabled if `automationYaml` is missing, even though `originalPrompt` is available.

### Tool Schema Definition (tool_schemas.py)

```81:81:services/ha-ai-agent-service/src/tools/tool_schemas.py
                "required": ["automation_yaml", "original_prompt", "conversation_id"]
```

**Issue:** The tool schema itself marks `automation_yaml` as required, which means OpenAI's function calling will enforce this requirement before the tool is even called.

### Backend Validation (ha_tools.py)

```677:686:services/ha-ai-agent-service/src/tools/ha_tools.py
        automation_yaml = arguments.get("automation_yaml")
        original_prompt = arguments.get("original_prompt")
        conversation_id = arguments.get("conversation_id")
        
        if not automation_yaml or not original_prompt:
            return {
                "success": False,
                "error": "automation_yaml and original_prompt are required",
                "conversation_id": conversation_id
            }
```

**Issue:** Backend also requires both `automation_yaml` and `original_prompt`.

### Enhancement Service (enhancement_service.py)

```89:95:services/ha-ai-agent-service/src/services/enhancement_service.py
    async def generate_enhancements(
        self,
        automation_yaml: str,
        original_prompt: str,
        entities: list[str],
        areas: list[str]
    ) -> list[Enhancement]:
```

```180:228:services/ha-ai-agent-service/src/services/enhancement_service.py
            prompt = f"""You are an automation enhancement expert. Given this automation:

Original Request: {original_prompt}

Automation YAML:
```yaml
{automation_yaml}
```

Generate 3 enhancement suggestions with increasing complexity:
```

**Issue:** The LLM prompt includes the YAML as a required context. The service extracts entities/areas from YAML (lines 699-700 in ha_tools.py).

---

## Root Cause

The enhancement feature was designed with a **single use case** in mind:
- **Enhance an existing automation YAML** to add features, improve it, or make it more sophisticated

However, users want a **different use case**:
- **Enhance the user's prompt** to generate better automation suggestions before creating the YAML

This is similar to TappsCodingAgents' enhancer agent, which enhances prompts to make them more comprehensive and context-aware.

---

## Design Mismatch

### Current Design (YAML Enhancement)
```
User Prompt → Generate YAML → Enhance YAML → Apply Enhancement
```

### Desired Design (Prompt Enhancement)
```
User Prompt → Enhance Prompt → Generate Better YAML → (Optional) Enhance YAML Further
```

---

## Solution Options

### Option 1: Dual-Mode Enhancement (Recommended)

Support both modes:

1. **Prompt Enhancement Mode** (no YAML required):
   - Enhance the user's prompt to make it more comprehensive
   - Generate enhanced prompt suggestions
   - User can select an enhanced prompt to generate automation

2. **YAML Enhancement Mode** (YAML required):
   - Enhance an existing automation YAML
   - Current behavior (add features, improve functionality)

**Implementation:**
- Make `automation_yaml` optional in backend
- Detect mode based on presence of YAML
- For prompt mode: Generate enhanced prompt suggestions
- For YAML mode: Generate enhanced YAML suggestions (current behavior)

### Option 2: Prompt-Only Enhancement

Remove YAML requirement entirely and always enhance prompts:

**Pros:**
- Simpler implementation
- Matches user expectation

**Cons:**
- Loses ability to enhance existing automations
- Less flexible

### Option 3: Two Separate Features

Create separate "Enhance Prompt" and "Enhance Automation" buttons:

**Pros:**
- Clear separation of concerns
- No confusion about what's being enhanced

**Cons:**
- More UI complexity
- Two buttons to maintain

---

## Recommended Solution: Option 1 (Dual-Mode)

### Changes Required

#### 1. Backend Changes

**File:** `services/ha-ai-agent-service/src/tools/ha_tools.py`

```python
async def suggest_automation_enhancements(self, arguments: dict[str, Any]) -> dict[str, Any]:
    automation_yaml = arguments.get("automation_yaml")  # Optional
    original_prompt = arguments.get("original_prompt")  # Required
    conversation_id = arguments.get("conversation_id")
    
    if not original_prompt:
        return {
            "success": False,
            "error": "original_prompt is required",
            "conversation_id": conversation_id
        }
    
    # Determine mode
    if automation_yaml:
        # YAML Enhancement Mode (existing behavior)
        entities = AutomationEnhancementService.extract_entities_from_yaml(automation_yaml)
        areas = AutomationEnhancementService.extract_areas_from_yaml(automation_yaml)
        
        enhancements = await self.enhancement_service.generate_enhancements(
            automation_yaml=automation_yaml,
            original_prompt=original_prompt,
            entities=entities,
            areas=areas
        )
    else:
        # Prompt Enhancement Mode (new behavior)
        enhancements = await self.enhancement_service.generate_prompt_enhancements(
            original_prompt=original_prompt
        )
    
    return {
        "success": True,
        "enhancements": [e.to_dict() for e in enhancements],
        "conversation_id": conversation_id,
        "mode": "yaml" if automation_yaml else "prompt"
    }
```

**File:** `services/ha-ai-agent-service/src/services/enhancement_service.py`

Add new method:

```python
async def generate_prompt_enhancements(
    self,
    original_prompt: str
) -> list[Enhancement]:
    """
    Generate prompt enhancement suggestions (no YAML required).
    
    Enhances the user's prompt to make it more comprehensive, specific, and
    context-aware. Returns enhanced prompt suggestions that can be used to
    generate better automations.
    """
    try:
        prompt = f"""You are a prompt enhancement expert for Home Assistant automations. 
Given this user prompt, generate 5 enhancement suggestions that make the prompt more comprehensive:

Original Prompt: {original_prompt}

Generate 5 enhancement suggestions with increasing detail:

1. **Small Enhancement**: Add minor details (timing, colors, brightness, simple conditions)
2. **Medium Enhancement**: Add functional details (notifications, multi-room, time conditions)
3. **Large Enhancement**: Add feature details (multi-device coordination, scenes, weather triggers)
4. **Advanced Enhancement**: Add smart features (time-based conditions, energy optimization, adaptive behavior)
5. **Creative Enhancement**: Add fun/creative elements (themed effects, interactive patterns, surprise elements)

For each enhancement, provide:
- Title: Short descriptive name
- Description: What the enhanced prompt does
- Enhanced Prompt: Complete enhanced prompt text (more detailed than original)
- Changes: List of 2-3 key additions made

Return your response as a JSON object with this structure:
{{
  "enhancements": [
    {{
      "level": "small",
      "title": "...",
      "description": "...",
      "enhanced_prompt": "...",
      "changes": ["...", "..."]
    }},
    ...
  ]
}}

Ensure enhanced prompts are more comprehensive and specific than the original."""

        response = await self.openai_client.chat.completions.create(
            model=self.settings.openai_model,
            messages=[
                {"role": "system", "content": "You are an expert at enhancing Home Assistant automation prompts. Always return valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from OpenAI")
        
        import json
        data = json.loads(content)
        
        enhancements = []
        for enh_data in data.get("enhancements", []):
            enhancements.append(Enhancement(
                level=enh_data.get("level", "small"),
                title=enh_data.get("title", "Enhancement"),
                description=enh_data.get("description", ""),
                enhanced_yaml=enh_data.get("enhanced_prompt", original_prompt),  # Store enhanced prompt in yaml field for compatibility
                changes=enh_data.get("changes", []),
                source="llm"
            ))
        
        # Ensure we have at least 3 enhancements
        while len(enhancements) < 3:
            enhancements.append(self._create_fallback_prompt_enhancement(
                original_prompt, len(enhancements) + 1
            ))
        
        return enhancements[:5]
        
    except Exception as e:
        logger.error(f"Error generating prompt enhancements: {e}", exc_info=True)
        # Return fallback enhancements
        return [
            self._create_fallback_prompt_enhancement(original_prompt, 1),
            self._create_fallback_prompt_enhancement(original_prompt, 2),
            self._create_fallback_prompt_enhancement(original_prompt, 3),
            self._create_fallback_prompt_enhancement(original_prompt, 4),
            self._create_fallback_prompt_enhancement(original_prompt, 5)
        ]

def _create_fallback_prompt_enhancement(
    self,
    original_prompt: str,
    level_num: int
) -> Enhancement:
    """Create a simple fallback prompt enhancement"""
    level_map = {
        1: ("small", "Small Enhancement", "Add minor details"),
        2: ("medium", "Medium Enhancement", "Add functional details"),
        3: ("large", "Large Enhancement", "Add feature details"),
        4: ("advanced", "Advanced Enhancement", "Add smart features"),
        5: ("fun", "Creative Enhancement", "Add creative elements")
    }
    
    level, title, description = level_map.get(level_num, ("small", "Enhancement", "Prompt enhancement"))
    
    return Enhancement(
        level=level,
        title=title,
        description=description,
        enhanced_yaml=original_prompt,  # Store prompt in yaml field for compatibility
        changes=["Enhancement applied"],
        source="fallback"
    )
```

#### 2. Frontend Changes

**File:** `services/ai-automation-ui/src/components/ha-agent/EnhancementButton.tsx`

```typescript
// Make automationYaml optional
interface EnhancementButtonProps {
  automationYaml?: string;  // Optional
  originalPrompt: string;   // Required
  conversationId: string;   // Required
  darkMode: boolean;
  onEnhancementSelected: (enhancement: Enhancement) => void;
}

// Update prerequisite check
const hasPrerequisites = !!(originalPrompt && conversationId);
const missingPrerequisites: string[] = [];
if (!conversationId) missingPrerequisites.push('active conversation');
if (!originalPrompt) missingPrerequisites.push('original prompt');
// Note: automationYaml is optional - enhancement works with or without it

// Update handleEnhance
const handleEnhance = async () => {
  if (!conversationId) {
    toast.error('No conversation active. Please start a conversation first.', { icon: '❌' });
    return;
  }
  
  if (!originalPrompt) {
    toast.error('Original prompt is required for enhancements.', { icon: '❌' });
    return;
  }
  
  // automationYaml is optional - pass it if available
  const result = await executeToolCall({
    tool_name: 'suggest_automation_enhancements',
    arguments: {
      automation_yaml: automationYaml || undefined,  // Optional
      original_prompt: originalPrompt,
      conversation_id: conversationId,
    },
  });
  
  // Handle result...
};
```

**File:** `services/ai-automation-ui/src/pages/HAAgentChat.tsx`

```typescript
// Update to pass automationYaml only if available
<EnhancementButton
  automationYaml={automationYaml || undefined}  // Optional
  originalPrompt={originalPrompt || userMsg?.content || ''}
  conversationId={currentConversationId}
  darkMode={darkMode}
  onEnhancementSelected={handleEnhancementSelected}
/>
```

#### 3. Enhancement Selection Handler

When user selects a prompt enhancement (no YAML mode), the enhanced prompt should be inserted into the input field or sent as a new message, not applied as YAML.

**File:** `services/ai-automation-ui/src/pages/HAAgentChat.tsx`

```typescript
const handleEnhancementSelected = (enhancement: Enhancement) => {
  // Check if this is a prompt enhancement (no YAML) or YAML enhancement
  const isPromptEnhancement = !automationYaml && enhancement.enhanced_yaml && 
                               !enhancement.enhanced_yaml.includes('alias:') &&
                               !enhancement.enhanced_yaml.includes('trigger:');
  
  if (isPromptEnhancement) {
    // Prompt enhancement: Insert enhanced prompt into input field
    setInputValue(enhancement.enhanced_yaml);
    toast.success(`Enhanced prompt applied: ${enhancement.title}`, { icon: '✨' });
  } else {
    // YAML enhancement: Apply YAML (existing behavior)
    // ... existing YAML application logic
  }
};
```

---

## Benefits of Dual-Mode Approach

1. **Flexibility**: Supports both use cases (prompt enhancement and YAML enhancement)
2. **Backward Compatible**: Existing YAML enhancement behavior remains unchanged
3. **User-Friendly**: Users can enhance prompts before creating YAML
4. **Progressive Enhancement**: Users can enhance prompts, then enhance the resulting YAML

---

## Implementation Priority

**High Priority** - This is a core UX issue that blocks users from using the enhancement feature as intended.

**Estimated Effort:**
- Backend changes: 2-3 hours
- Frontend changes: 1-2 hours
- Testing: 1-2 hours
- **Total: 4-7 hours**

---

## Testing Checklist

- [ ] Enhancement button enabled with only `originalPrompt` (no YAML)
- [ ] Enhancement button enabled with both `originalPrompt` and `automationYaml`
- [ ] Prompt enhancement mode generates 5 enhanced prompt suggestions
- [ ] YAML enhancement mode generates 5 enhanced YAML suggestions (existing behavior)
- [ ] Selecting prompt enhancement inserts enhanced prompt into input field
- [ ] Selecting YAML enhancement applies YAML (existing behavior)
- [ ] Error handling for missing `originalPrompt`
- [ ] Error handling for API failures
- [ ] UI shows appropriate mode indicator (prompt vs YAML enhancement)

---

## Related Files

- `services/ai-automation-ui/src/components/ha-agent/EnhancementButton.tsx`
- `services/ai-automation-ui/src/pages/HAAgentChat.tsx`
- `services/ha-ai-agent-service/src/tools/ha_tools.py`
- `services/ha-ai-agent-service/src/services/enhancement_service.py`
- `services/ha-ai-agent-service/src/tools/tool_schemas.py` (may need update for optional YAML)

---

## Next Steps

1. ✅ Analysis complete
2. ⏳ Review and approve solution approach
3. ⏳ Implement backend changes (make YAML optional, add prompt enhancement mode)
4. ⏳ Implement frontend changes (make YAML optional, handle prompt enhancements)
5. ⏳ Update enhancement selection handler
6. ⏳ Test both modes
7. ⏳ Update documentation

---

## References

- TappsCodingAgents Enhancer Agent: Similar concept of prompt enhancement
- Current Enhancement Feature: `implementation/AUTOMATION_ENHANCEMENT_FEATURE_COMPLETE.md`
- Enhancement Button Fix: `implementation/ENHANCE_BUTTON_FIX.md`

