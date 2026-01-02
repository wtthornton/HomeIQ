# YAML Automation Fix Recommendations

**Generated:** 2026-01-02  
**Source:** Office motion-based dimming lights automation  
**Review Tool:** TappsCodingAgents Reviewer Agent  
**Overall Score:** 83/100 (Quality Gate: Failed - Security threshold not met)

---

## Executive Summary

The automation YAML has **6 critical issues** that prevent it from working correctly:

1. **Incomplete YAML structure** - Missing closing brackets
2. **Entity ID mismatch** - `light.office` doesn't exist (should check area lights)
3. **Logic flaw in condition timing** - Individual `for:` checks don't work together
4. **Brightness step overflow** - No bounds checking for brightness values
5. **Missing default branch** - No fallback if conditions aren't met
6. **Restart mode interaction** - May cause unexpected behavior during dimming

---

## Detailed Issues

### Issue 1: Incomplete YAML Structure ⚠️ CRITICAL

**Problem:**
The YAML is missing closing brackets for the `choose` action and `repeat` block.

**Current Code:**
```yaml
action:
  - choose:
      - conditions: [...]
        sequence: [...]
      - conditions: [...]
        sequence:
          - repeat:
              sequence: [...]
              until: [...]
# Missing closing brackets
```

**Impact:** YAML parsing will fail or automation won't execute properly.

**Fix:** Add proper closing brackets:
```yaml
action:
  - choose:
      - conditions: [...]
        sequence: [...]
      - conditions: [...]
        sequence:
          - repeat:
              sequence: [...]
              until: [...]
```

---

### Issue 2: Entity ID Mismatch ⚠️ CRITICAL

**Problem:**
The `until` condition checks `light.office`, but:
- The action uses `target.area_id: office` (targets all lights in the area)
- There may not be a single entity called `light.office`
- The condition will fail if the entity doesn't exist

**Current Code:**
```yaml
until:
  - condition: or
    conditions:
      - condition: state
        entity_id: light.office  # ❌ May not exist
        state: "off"
```

**Impact:** The dimming sequence may never stop, or the condition will always fail.

**Fix Options:**

**Option A: Check all lights in area (Recommended)**
```yaml
until:
  - condition: template
    value_template: >
      {% set office_lights = area_entities('office') | selectattr('entity_id', 'match', '^light\\..*') | list %}
      {{ office_lights | selectattr('state', 'eq', 'off') | list | length == office_lights | length }}
```

**Option B: Check brightness level**
```yaml
until:
  - condition: template
    value_template: >
      {% set office_lights = area_entities('office') | selectattr('entity_id', 'match', '^light\\..*') | list %}
      {{ office_lights | selectattr('attributes.brightness', 'le', 0) | list | length == office_lights | length }}
```

**Option C: Use brightness threshold (Simplest)**
```yaml
until:
  - condition: template
    value_template: >
      {% set lights = area_entities('office') | selectattr('entity_id', 'match', '^light\\..*') | list %}
      {% set all_off = lights | selectattr('state', 'eq', 'off') | list | length == lights | length %}
      {% set all_dim = lights | selectattr('attributes.brightness', 'le', 10) | list | length == lights | length %}
      {{ all_off or all_dim }}
```

---

### Issue 3: Logic Flaw in Condition Timing ⚠️ CRITICAL

**Problem:**
Each condition checks independently if a sensor has been "off" for 1 minute. This means:
- Sensor 1 off for 1 min → condition passes
- Sensor 2 off for 1 min → condition passes  
- Sensor 3 off for 1 min → condition passes

But they don't check if **all sensors have been off together** for 1 minute. If sensors turn on/off at different times, the automation may trigger prematurely.

**Current Code:**
```yaml
- conditions:
    - condition: and
      conditions:
        - condition: state
          entity_id: binary_sensor.office_motion_1
          state: "off"
          for: "00:01:00"  # ❌ Checks independently
        - condition: state
          entity_id: binary_sensor.office_motion_2
          state: "off"
          for: "00:01:00"  # ❌ Checks independently
        - condition: state
          entity_id: binary_sensor.office_motion_3
          state: "off"
          for: "00:01:00"  # ❌ Checks independently
```

**Impact:** Automation may start dimming before all sensors have been off for the full minute.

**Fix:** Use a template condition that checks all sensors together:
```yaml
- conditions:
    - condition: template
      value_template: >
        {% set sensors = [
          'binary_sensor.office_motion_1',
          'binary_sensor.office_motion_2',
          'binary_sensor.office_motion_3'
        ] %}
        {% set now = now().timestamp() %}
        {% set all_off_for_minute = true %}
        {% for sensor in sensors %}
          {% if states(sensor) != 'off' %}
            {% set all_off_for_minute = false %}
          {% else %}
            {% set last_changed = states[sensor].last_changed.timestamp() %}
            {% if (now - last_changed) < 60 %}
              {% set all_off_for_minute = false %}
            {% endif %}
          {% endif %}
        {% endfor %}
        {{ all_off_for_minute }}
```

**Simpler Alternative (if template is too complex):**
Use a delay trigger instead:
```yaml
trigger:
  - platform: state
    entity_id:
      - binary_sensor.office_motion_1
      - binary_sensor.office_motion_2
      - binary_sensor.office_motion_3
    to: "off"
    for: "00:01:00"
condition:
  - condition: and
    conditions:
      - condition: state
        entity_id: binary_sensor.office_motion_1
        state: "off"
      - condition: state
        entity_id: binary_sensor.office_motion_2
        state: "off"
      - condition: state
        entity_id: binary_sensor.office_motion_3
        state: "off"
```

---

### Issue 4: Brightness Step Overflow ⚠️ HIGH

**Problem:**
Using `brightness_step: -40` repeatedly will eventually cause:
- Negative brightness values (invalid)
- Lights may not turn off properly
- No bounds checking

**Current Code:**
```yaml
- repeat:
    sequence:
      - service: light.turn_on
        target:
          area_id: office
        data:
          brightness_step: -40  # ❌ No bounds checking
          transition: 2
      - delay: "00:00:03"
```

**Impact:** Lights may get stuck in an invalid state or not turn off completely.

**Fix:** Add bounds checking in the `until` condition or use absolute brightness values:
```yaml
- repeat:
    count: 7  # 255 / 40 ≈ 6.4, round up to 7 steps
    sequence:
      - service: light.turn_on
        target:
          area_id: office
        data:
          brightness_step: -40
          transition: 2
      - delay: "00:00:03"
  # After repeat, ensure lights are off
- service: light.turn_off
  target:
    area_id: office
```

**Better Alternative:** Use absolute brightness values:
```yaml
- repeat:
    sequence:
      - service: light.turn_on
        target:
          area_id: office
        data:
          brightness: "{{ (255 - (repeat.index * 40)) | max(0) }}"
          transition: 2
      - delay: "00:00:03"
    until:
      - condition: template
        value_template: "{{ repeat.index >= 6 }}"
- service: light.turn_off
  target:
    area_id: office
```

---

### Issue 5: Missing Default Branch ⚠️ MEDIUM

**Problem:**
The `choose` action has no default branch. If neither condition is met (edge case), nothing happens.

**Current Code:**
```yaml
action:
  - choose:
      - conditions: [...]  # Branch 1
        sequence: [...]
      - conditions: [...]  # Branch 2
        sequence: [...]
      # ❌ No default branch
```

**Impact:** In edge cases (e.g., sensors in unknown state), automation does nothing.

**Fix:** Add a default branch (optional, but recommended):
```yaml
action:
  - choose:
      - conditions: [...]
        sequence: [...]
      - conditions: [...]
        sequence: [...]
      default:
        - service: system_log.write
          data:
            message: "Office motion automation: No conditions met"
            level: warning
```

---

### Issue 6: Restart Mode Interaction ⚠️ MEDIUM

**Problem:**
With `mode: restart`, if a sensor changes state during dimming:
- The automation restarts
- The dimming sequence is cancelled
- Lights may jump back to full brightness unexpectedly

**Current Code:**
```yaml
mode: restart
trigger:
  - platform: state
    entity_id: [...]
    to: ["on", "off"]  # Triggers on both on and off
```

**Impact:** During dimming, if any sensor changes state (even briefly), the automation restarts and lights jump back to full brightness.

**Fix Options:**

**Option A: Separate triggers (Recommended)**
```yaml
mode: restart
trigger:
  # Trigger on motion detected
  - platform: state
    entity_id:
      - binary_sensor.office_motion_1
      - binary_sensor.office_motion_2
      - binary_sensor.office_motion_3
    to: "on"
  # Trigger when all sensors have been off for 1 minute
  - platform: state
    entity_id:
      - binary_sensor.office_motion_1
      - binary_sensor.office_motion_2
      - binary_sensor.office_motion_3
    to: "off"
    for: "00:01:00"
```

**Option B: Use `mode: single` for dimming branch**
Not possible with current structure, but could split into two automations.

**Option C: Add condition to prevent restart during dimming**
Use a helper input_boolean to track dimming state.

---

## Recommended Fixed YAML

Here's the complete corrected automation:

```yaml
alias: "Office motion-based dimming lights"
description: "Use all office motion sensors to turn office lights on with motion and gradually dim them to off after 1 minute of no motion."
initial_state: true
mode: restart
trigger:
  # Trigger when any motion sensor detects motion
  - platform: state
    entity_id:
      - binary_sensor.office_motion_1
      - binary_sensor.office_motion_2
      - binary_sensor.office_motion_3
    to: "on"
  # Trigger when all sensors have been off for 1 minute
  - platform: state
    entity_id:
      - binary_sensor.office_motion_1
      - binary_sensor.office_motion_2
      - binary_sensor.office_motion_3
    to: "off"
    for: "00:01:00"

condition: []

action:
  - choose:
      # Branch 1: Any motion sensor turns lights fully on
      - conditions:
          - condition: or
            conditions:
              - condition: state
                entity_id: binary_sensor.office_motion_1
                state: "on"
              - condition: state
                entity_id: binary_sensor.office_motion_2
                state: "on"
              - condition: state
                entity_id: binary_sensor.office_motion_3
                state: "on"
        sequence:
          - service: light.turn_on
            target:
              area_id: office
            data:
              brightness: 255

      # Branch 2: All sensors off for 1 minute -> start dimming to off
      - conditions:
          - condition: and
            conditions:
              - condition: state
                entity_id: binary_sensor.office_motion_1
                state: "off"
              - condition: state
                entity_id: binary_sensor.office_motion_2
                state: "off"
              - condition: state
                entity_id: binary_sensor.office_motion_3
                state: "off"
        sequence:
          # Dim lights down in 7 steps (255 / 40 ≈ 6.4, round up)
          # Restart mode cancels this if motion returns
          - repeat:
              count: 7
              sequence:
                - service: light.turn_on
                  target:
                    area_id: office
                  data:
                    brightness_step: -40
                    transition: 2
                - delay: "00:00:03"
          # Ensure lights are completely off after dimming
          - service: light.turn_off
            target:
              area_id: office
```

---

## Alternative Approach: Two Separate Automations

For better reliability, consider splitting into two automations:

### Automation 1: Turn On Lights
```yaml
alias: "Office motion - turn on lights"
description: "Turn office lights on when motion detected"
initial_state: true
mode: restart
trigger:
  - platform: state
    entity_id:
      - binary_sensor.office_motion_1
      - binary_sensor.office_motion_2
      - binary_sensor.office_motion_3
    to: "on"
action:
  - service: light.turn_on
    target:
      area_id: office
    data:
      brightness: 255
```

### Automation 2: Dim Lights After No Motion
```yaml
alias: "Office motion - dim lights after no motion"
description: "Dim office lights to off after 1 minute of no motion"
initial_state: true
mode: single  # Don't restart - let dimming complete
trigger:
  - platform: state
    entity_id:
      - binary_sensor.office_motion_1
      - binary_sensor.office_motion_2
      - binary_sensor.office_motion_3
    to: "off"
    for: "00:01:00"
condition:
  - condition: and
    conditions:
      - condition: state
        entity_id: binary_sensor.office_motion_1
        state: "off"
      - condition: state
        entity_id: binary_sensor.office_motion_2
        state: "off"
      - condition: state
        entity_id: binary_sensor.office_motion_3
        state: "off"
action:
  - repeat:
      count: 7
      sequence:
        - service: light.turn_on
          target:
            area_id: office
          data:
            brightness_step: -40
            transition: 2
        - delay: "00:00:03"
  - service: light.turn_off
    target:
      area_id: office
```

**Benefits:**
- Simpler logic per automation
- Dimming won't be interrupted by motion detection
- Easier to debug and maintain
- Better separation of concerns

---

## Testing Recommendations

1. **Test motion detection**: Verify lights turn on immediately when any sensor detects motion
2. **Test dimming sequence**: Verify lights dim smoothly over ~21 seconds (7 steps × 3 seconds)
3. **Test restart behavior**: Verify dimming cancels and lights return to full brightness if motion detected during dimming
4. **Test edge cases**: 
   - All sensors off simultaneously
   - Sensors turning on/off at different times
   - Lights already off when automation triggers
   - Multiple rapid motion detections

---

## Quality Metrics

**TappsCodingAgents Review Scores:**
- Overall Score: 83/100 ✅ (Passes threshold: 70)
- Complexity: 5.0/10 ✅ (Below threshold: 5.0)
- Security: 8.0/10 ⚠️ (Below threshold: 8.5)
- Maintainability: 7.0/10 ✅ (Meets threshold: 7.0)
- Test Coverage: 0.0/10 ❌ (Below threshold: 80%)
- Performance: 10.0/10 ✅

**Issues Found:**
- Security: Entity ID validation missing (potential for invalid entity references)
- Test Coverage: No automated tests for this automation

---

## Next Steps

1. ✅ **COMPLETED**: Fix YAML structure (Issue 1)
2. ✅ **COMPLETED**: Fix entity ID mismatch (Issue 2)
3. ✅ **COMPLETED**: Fix condition timing logic (Issue 3)
4. ✅ **COMPLETED**: Add brightness bounds checking (Issue 4)
5. ✅ **COMPLETED**: Updated system prompt with motion-based dimming patterns
6. ⚠️ **Medium Priority**: Consider splitting into two automations
7. ⚠️ **Medium Priority**: Add default branch (Issue 5)
8. 📋 **Future**: Add automated tests for automation generation
9. 📋 **Future**: Improve entity resolution for area-based conditions
10. 📋 **Future**: Add validation checks to catch these patterns in generated YAML

---

## References

- [Home Assistant Automation Documentation](https://www.home-assistant.io/docs/automation/)
- [Home Assistant Choose Action](https://www.home-assistant.io/docs/scripts/#choose)
- [Home Assistant Repeat Action](https://www.home-assistant.io/docs/scripts/#repeat)
- [Home Assistant Template Conditions](https://www.home-assistant.io/docs/automation/using-templates/)
