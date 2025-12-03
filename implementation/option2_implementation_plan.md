# Option 2 Implementation Plan

**Date:** December 3, 2025  
**Status:** In Progress  
**Approach:** Make mqtt_broker and openai_api_key optional with conditional validation

## Implementation Strategy

### Phase 1: Core Configuration Changes
1. Make `mqtt_broker` and `openai_api_key` optional in `config.py`
2. Add training mode detection logic
3. Update `validate_required_fields` to conditionally validate

### Phase 2: Runtime Code Fixes
1. Fix `suggestion_router.py` - handles None openai_api_key
2. Fix `service_container.py` - update validation logic
3. Audit other files for None handling

### Phase 3: Testing
1. Test training scripts work without environment variables
2. Verify runtime services still validate correctly
3. Test edge cases

## Files to Modify

### Core Changes
- `services/ai-automation-service/src/config.py` - Main configuration changes

### Runtime Fixes
- `services/ai-automation-service/src/api/suggestion_router.py` - Add None check
- `services/ai-automation-service/src/services/service_container.py` - Update validation
- `services/ai-automation-service/src/api/nl_generation_router.py` - Add None check (if needed)

## Implementation Details

### Training Mode Detection
- Check for `TRAINING_MODE` environment variable
- Check if script name contains "train_"
- Allow explicit training mode flag

### Validation Logic
- Only validate mqtt_broker and openai_api_key for runtime services
- Training scripts can run without these values
- Runtime services will fail fast if values are missing

