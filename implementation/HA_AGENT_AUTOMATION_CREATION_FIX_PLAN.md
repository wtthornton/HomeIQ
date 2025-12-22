# HA Agent Automation Creation Fix Plan

## Problem Analysis

**Error:** "user_prompt, automation_yaml, and alias are all required"

**Root Cause:** 
The `CTAActionButtons` component calls `create_automation_from_prompt` but only passes:
- `automation_yaml` ✅
- `conversation_id` (not required by backend)
- Missing: `user_prompt` ❌
- Missing: `alias` ❌

**Location:** `services/ai-automation-ui/src/components/ha-agent/CTAActionButtons.tsx` (lines 64-69)

## Solution

### Step 1: Extract alias from YAML
- Parse YAML to extract `alias` field (similar to `AutomationPreview` component)
- Use regex pattern: `/alias:\s*['"]?([^'\n"]+)['"]?/i`

### Step 2: Extract user_prompt
- Option A: Extract `description` from YAML as fallback
- Option B: Pass `originalUserPrompt` as prop from `HAAgentChat`
- Option C: Use alias as user_prompt if description not available

### Step 3: Update CTAActionButtons
- Add function to extract alias from YAML
- Add function to extract description/user_prompt from YAML
- Update `handleCreateAutomation` to include all required fields

### Step 4: Update HAAgentChat (if needed)
- Pass `originalUserPrompt` prop to `CTAActionButtons` if available
- Extract from messages array (most recent user message)

## Implementation

### Changes Required

1. **CTAActionButtons.tsx**
   - Add `extractAliasFromYaml()` function
   - Add `extractDescriptionFromYaml()` function  
   - Update `handleCreateAutomation()` to include `user_prompt` and `alias`
   - Add prop `originalUserPrompt?: string` (optional)

2. **HAAgentChat.tsx** (optional enhancement)
   - Pass `originalUserPrompt` to `CTAActionButtons` when available
   - Extract from messages: `messages.find(m => m.role === 'user')?.content`

## Testing

1. Test with YAML containing alias and description
2. Test with YAML containing only alias (no description)
3. Test with YAML containing neither (should use fallbacks)
4. Verify error no longer appears
5. Verify automation creation succeeds

## Files to Modify

- `services/ai-automation-ui/src/components/ha-agent/CTAActionButtons.tsx`
- `services/ai-automation-ui/src/pages/HAAgentChat.tsx` (optional)

