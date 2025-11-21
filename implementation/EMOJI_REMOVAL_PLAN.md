# Emoji Removal Plan

## Problem
Emoji characters in Python source code are causing syntax errors during deployment. The errors occur in:
1. `ask_ai_router.py` line 2102 - emojis in f-string prompt strings
2. `yaml_generation_service.py` - emojis still present in prompt strings (logger statements already fixed)

## Root Cause
Emoji characters (✅, ❌, ⚠️, 🔍, 🔧, 📋, ⏭️, 🚀, 🔴) in f-string prompt definitions are causing Python syntax errors. Python cannot parse these Unicode characters in certain contexts.

## Scope Analysis

### Critical Files (Syntax Errors)
1. **ask_ai_router.py**
   - Lines 2102-2105: Emojis in f-string prompt (COMMON MISTAKES section)
   - Line 2192: Emojis in conditional f-string expression
   - Lines 2236-2243: Emojis in f-string prompt (TIME TRIGGER RULES)
   - Lines 2308-2313: Emojis in f-string prompt (YAML FORMAT section)
   - Lines 2319-2324: Emojis in CRITICAL RULES section
   - Additional prompt sections with emojis

2. **yaml_generation_service.py**
   - Lines 728-731: Emojis in prompt string (already in strings, but should be fixed)
   - Line 818: Emoji in conditional f-string expression
   - Lines 862-869: Emojis in prompt string (TIME TRIGGER RULES)
   - Lines 934+: Emojis in YAML FORMAT section

### Non-Critical (Logger Statements)
- Many logger statements have emojis, but these are in regular strings so they're safer
- Should be replaced for consistency and to prevent future issues

## Strategy

### Phase 1: Fix Critical Syntax Errors (ask_ai_router.py)
1. Replace emojis in f-string prompt definitions with plain text equivalents:
   - ✅ → `[OK]` or `CORRECT:`
   - ❌ → `[ERROR]` or `WRONG:`
   - ⚠️ → `[WARNING]`
   - 🔍 → `[SEARCH]` or `[DEBUG]`
   - 🔧 → `[TOOL]` or `[INIT]`
   - 📋 → `[INFO]` or `[LIST]`
   - ⏭️ → `[SKIP]`
   - 🚀 → `[START]`
   - 🔴 → `[CRITICAL]` or `[TEST]`

2. Replace emojis in logger statements for consistency

### Phase 2: Fix yaml_generation_service.py
1. Replace remaining emojis in prompt strings
2. Ensure all logger statements are already fixed (verify)

### Phase 3: Verification
1. Run `python -m py_compile` on both files
2. Build Docker image
3. Verify service starts successfully

## Implementation Steps

### Step 1: Fix ask_ai_router.py Prompt Strings
- [ ] Replace emojis in COMMON MISTAKES section (lines 2102-2105)
- [ ] Replace emoji in TEST MODE conditional (line 2192)
- [ ] Replace emojis in TIME TRIGGER RULES (lines 2236-2243)
- [ ] Replace emojis in YAML FORMAT section (lines 2308+)
- [ ] Replace emojis in CRITICAL RULES section (lines 2319+)
- [ ] Search and replace all remaining emojis in f-string prompts

### Step 2: Fix ask_ai_router.py Logger Statements
- [ ] Replace all emojis in logger statements with plain text tags
- [ ] Use consistent format: `[TAG] message` for all logger statements

### Step 3: Fix yaml_generation_service.py
- [ ] Replace emojis in prompt strings (lines 728-731, 818, 862-869, 934+)
- [ ] Verify all logger statements are already fixed

### Step 4: Verification
- [ ] Run syntax check: `python -m py_compile ask_ai_router.py`
- [ ] Run syntax check: `python -m py_compile yaml_generation_service.py`
- [ ] Build Docker image
- [ ] Deploy and verify service starts

## Replacement Mapping

| Emoji | Replacement | Context |
|-------|-------------|---------|
| ✅ | `[OK]` or `CORRECT:` | Success/Correct examples |
| ❌ | `[ERROR]` or `WRONG:` | Errors/Wrong examples |
| ⚠️ | `[WARNING]` | Warnings |
| 🔍 | `[SEARCH]` or `[DEBUG]` | Debug/search operations |
| 🔧 | `[TOOL]` or `[INIT]` | Tool initialization |
| 📋 | `[INFO]` or `[LIST]` | Information listings |
| ⏭️ | `[SKIP]` | Skip operations |
| 🚀 | `[START]` | Start operations |
| 🔴 | `[CRITICAL]` or `[TEST]` | Critical/Test mode |

## Files to Modify
1. `services/ai-automation-service/src/api/ask_ai_router.py`
2. `services/ai-automation-service/src/services/automation/yaml_generation_service.py`

## Success Criteria
- [ ] No syntax errors when compiling Python files
- [ ] Docker image builds successfully
- [ ] Service starts without errors
- [ ] All emojis replaced with plain text equivalents
- [ ] Code functionality preserved (emojis were only in prompts/logs)

