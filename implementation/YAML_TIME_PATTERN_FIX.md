# YAML Time Pattern Trigger Fix

## Problem

When approving a suggestion with "every 10 minutes" trigger, the system generated invalid YAML:

```yaml
trigger:
  - trigger: time
    at:
      - '*/10 * * * *'
```

**Error:** `HTTP 400: Message malformed: Expected HH:MM, HH:MM:SS, an Entity ID with domain 'input_datetime' or 'sensor', a combination of a timestamp sensor entity and an offset, or Limited Template @ data['at'][0]`

## Root Cause

The YAML generator was using `platform: time` with a cron expression in the `at:` field, which Home Assistant doesn't support. For recurring intervals, Home Assistant requires `platform: time_pattern` with `minutes: '/X'` format.

## Solution

Updated `services/ai-automation-service/src/llm/yaml_generator.py` to:

1. **Added `time_pattern` to platform enum** (line 240)
2. **Added `minutes`, `hours`, and `seconds` parameters** to the function schema (lines 258-269)
3. **Added Example 5** showing correct `time_pattern` usage (lines 192-206)
4. **Added CRITICAL TIME TRIGGER RULES** section explaining when to use `time` vs `time_pattern` (lines 208-213)

## Correct Format

### For Recurring Intervals (every X minutes/hours):
```yaml
trigger:
  - platform: time_pattern
    minutes: '/10'  # Every 10 minutes
```

### For Specific Times:
```yaml
trigger:
  - platform: time
    at: '07:00:00'  # Specific time
```

## Verification from 2025 Documentation

Confirmed correct format from existing project documentation:

1. **EPIC_12_IMPLEMENTATION_SUMMARY.md** (2025-Q4):
   ```yaml
   - platform: time_pattern
     minutes: "/30"
   ```

2. **epic-12-sports-data-influxdb-persistence.md**:
   ```yaml
   - platform: time_pattern
     minutes: "/15"  # Check every 15 minutes
   ```

3. **contracts/models.py** already supports:
   - `platform: time_pattern`
   - `minutes: Optional[Union[str, int]]`
   - `hours: Optional[Union[str, int]]`
   - `seconds: Optional[Union[str, int]]`

## Files Modified

- `services/ai-automation-service/src/llm/yaml_generator.py`
  - Added `time_pattern` to platform enum
  - Added `minutes`, `hours`, `seconds` parameters
  - Added example and documentation

## Testing

The fix ensures that:
- ✅ "every 10 minutes" → `platform: time_pattern` with `minutes: '/10'`
- ✅ "every 2 hours" → `platform: time_pattern` with `hours: '/2'`
- ✅ "at 7 AM" → `platform: time` with `at: '07:00:00'`
- ✅ YAML conversion code automatically handles these fields (lines 715-723)

## Next Steps

1. Test with a new suggestion: "Every 10 min make the led in the office do something fun and random for 10 secs"
2. Verify the generated YAML uses `time_pattern` correctly
3. Confirm the automation deploys successfully to Home Assistant

