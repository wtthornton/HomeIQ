# Ask AI - YAML Generation Debug Deployment

**Date**: November 19, 2025, 1:42 PM PST
**Status**: 🔍 Enhanced Logging Deployed - Ready for Debug Test

## Problem Identified

Previous test revealed:
- ✅ YAML generation function was called
- ✅ OpenAI API was called
- ❌ **YAML returned was EMPTY (0 chars)**
- ❌ HA validation failed: "Invalid YAML: must be a dictionary"

## New Debug Logging Added

Added detailed logging at every step of YAML generation to pinpoint where the content disappears:

### 1. Raw OpenAI Response
```python
logger.info(f"📥 [YAML_RAW] OpenAI returned {len(yaml_content)} chars")
logger.info(f"📄 [YAML_RAW] First 300 chars: {yaml_content[:300]}")
```

### 2. After Markdown Cleanup
```python
logger.info(f"🧹 [YAML_CLEANED] After cleanup: {len(yaml_content)} chars")
```

### 3. Before/After Validator
```python
logger.info(f"🔍 [VALIDATOR] Before validation: {len(yaml_content)} chars")
logger.info(f"🔍 [VALIDATOR] Validation complete: is_valid={validation.is_valid}, has_fixed={bool(validation.fixed_yaml)}")
logger.info(f"🔍 [VALIDATOR] Fixed YAML length: {len(validation.fixed_yaml)} chars")
```

### 4. When No Fixed YAML
```python
logger.info(f"⚠️ [VALIDATOR] No fixed YAML available - keeping original (errors: {len(validation.errors)})")
logger.info(f"⚠️ [VALIDATOR] Original YAML length: {len(yaml_content)} chars")
```

## Expected Log Sequence

This will tell us EXACTLY where the YAML disappears:

```
📥 [YAML_RAW] OpenAI returned 1234 chars
📄 [YAML_RAW] First 300 chars: id: 'office_wled_random_effect'...
🧹 [YAML_CLEANED] After cleanup: 1234 chars
✅ Generated valid YAML syntax
🔍 [VALIDATOR] Before validation: 1234 chars
🔍 [VALIDATOR] Validation complete: is_valid=False, has_fixed=True
🔍 [VALIDATOR] Fixed YAML length: 1250 chars
🔧 Using fixed YAML from validator (original had 2 errors)
```

OR if OpenAI returns empty:

```
📥 [YAML_RAW] OpenAI returned 0 chars
📄 [YAML_RAW] First 300 chars: 
🧹 [YAML_CLEANED] After cleanup: 0 chars
```

## Testing Instructions

### Step 1: Start Log Monitoring
```powershell
docker compose logs -f ai-automation-service | Select-String -Pattern "\[YAML_RAW\]|\[YAML_CLEANED\]|\[VALIDATOR\]" -Context 0,1
```

### Step 2: Test Approval
1. Go to: http://localhost:3001/ask-ai
2. Click **"APPROVE & CREATE"**
3. Watch the logs

## What We'll Learn

This debug session will tell us:
1. **Is OpenAI returning empty YAML?**
   - If yes → Problem is in the prompt or model response
   - If no → Problem is in our processing

2. **Does the validator clear the YAML?**
   - If yes → Problem in YAMLStructureValidator
   - If no → YAML was already empty

3. **Is the prompt missing context?**
   - Check validated entities in logs
   - Check original query text

## Possible Root Causes

### Cause A: OpenAI Returns Empty
**Symptom**: `📥 [YAML_RAW] OpenAI returned 0 chars`
**Fix**: Review and improve prompt, check model constraints

### Cause B: Validator Clears YAML
**Symptom**: 
```
🔍 [VALIDATOR] Before validation: 1234 chars
⚠️ [VALIDATOR] No fixed YAML available - keeping original (errors: 1)
📄 [YAML_GEN] First 200 chars: 
```
**Fix**: Fix YAMLStructureValidator logic

### Cause C: Markdown Cleanup Issue
**Symptom**: 
```
📥 [YAML_RAW] OpenAI returned 1234 chars
🧹 [YAML_CLEANED] After cleanup: 0 chars
```
**Fix**: Adjust markdown removal logic

## Next Steps After Test

Based on the logs, we'll implement the appropriate fix:
1. Fix OpenAI prompt (if empty response)
2. Fix YAMLStructureValidator (if it clears YAML)
3. Fix cleanup logic (if markdown removal breaks)
4. Verify 2025 YAML format compliance

---

**Ready to test!** Click "APPROVE & CREATE" and share the logs! 🔍

